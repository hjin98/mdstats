from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes

import mdstats
from tests.test_mlff_data5_partition_roles import _build


class _CountingCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def __init__(self, *, fail_after: int | None = None):
        super().__init__()
        self.descriptor_calls = 0
        self.prediction_calls = 0
        self.fail_after = fail_after

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        self.prediction_calls += 1
        if self.fail_after is not None and self.prediction_calls > self.fail_after:
            raise RuntimeError("intentional production-sweep interruption")
        super().calculate(atoms, properties, system_changes)
        positions = np.asarray(self.atoms.positions, dtype=float)
        self.results = {
            "energy": float(np.sum(positions**2)),
            "forces": -2.0 * positions,
            "stress": np.asarray([0.01, 0.02, 0.03, 0.004, 0.005, 0.006]),
        }

    def get_descriptors(self, atoms, *, invariants_only=True, num_layers=None):
        self.descriptor_calls += 1
        positions = np.asarray(atoms.positions, dtype=float)
        numbers = np.asarray(atoms.numbers, dtype=float)[:, None]
        return np.column_stack((numbers, positions, np.linalg.norm(positions, axis=1)))


def _provider(calculator: _CountingCalculator) -> mdstats.MaceCalculatorProvider:
    identity = mdstats.ModelCheckpointIdentity(
        model_family="fake-mace",
        checkpoint_locator="memory://production-sweep",
        checkpoint_sha256="b" * 64,
        calculator_class="tests._CountingCalculator",
        model_version="0.test",
        supported_atomic_numbers=(3, 8, 11, 13, 14, 19),
        device="cpu",
        default_dtype="float64",
    )
    return mdstats.MaceCalculatorProvider.from_calculator(calculator, checkpoint_identity=identity)


def _inputs(tmp_path: Path):
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    policy = mdstats.Data6Policy(
        build_lta_selection_features=False,
        build_mace_descriptors=True,
        build_training_difficulty=True,
        build_blinded_predictions=True,
    )
    return sources, frames, frame_data, data4, data5, policy


def test_model_sweep_plan_binds_exact_authorized_union(tmp_path: Path) -> None:
    _, frames, _, _, data5, policy = _inputs(tmp_path)
    provider = _provider(_CountingCalculator())
    plan = mdstats.build_data6_model_sweep_plan(
        frames, data5, policy, provider.checkpoint_identity
    )
    assert plan.requested_frame_uids
    assert set(plan.requested_frame_uids) == set(plan.descriptor_frame_uids) | set(plan.prediction_frame_uids)
    assert not set(plan.requested_frame_uids) & set(plan.sealed_or_excluded_frame_uids)
    locked = {
        frame_uid
        for outer in data5.outer_partitions
        for unit_id in outer.units_for(mdstats.OuterRole.LOCKED_INTERPOLATION_TEST)
        for frame_uid in data5.unit_catalog.unit(unit_id).frame_uids
    }
    assert locked <= set(plan.sealed_or_excluded_frame_uids)
    assert mdstats.Data6ModelSweepPlan.from_dict(plan.to_dict()) == plan


def test_restart_reuses_verified_frames_and_recovers_corruption(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    calculator = _CountingCalculator()
    provider = _provider(calculator)
    root = tmp_path / "sweep"

    partial = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(max_new_frames=2),
    )
    assert not partial.complete
    assert len(partial.checkpoint.completed_frame_uids) == 2
    expected_pending = tuple(
        uid
        for uid in partial.checkpoint.plan.requested_frame_uids
        if uid not in set(partial.checkpoint.completed_frame_uids)
    )
    assert partial.checkpoint.pending_frame_uids == expected_pending
    # Immutable checkpoints cache the completed and pending UID sequences.
    # Repeated progress/status queries must not rebuild an O(N) set or scan.
    assert partial.checkpoint.pending_frame_uids is partial.checkpoint.pending_frame_uids
    assert partial.checkpoint.completed_frame_uids is partial.checkpoint.completed_frame_uids
    calls_after_partial = (calculator.descriptor_calls, calculator.prediction_calls)

    complete = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert complete.complete
    assert len(complete.checkpoint.completed_frame_uids) == len(complete.checkpoint.plan.requested_frame_uids)
    assert calculator.descriptor_calls == len(complete.checkpoint.plan.descriptor_frame_uids)
    assert calculator.prediction_calls == len(complete.checkpoint.plan.prediction_frame_uids)
    assert calculator.descriptor_calls >= calls_after_partial[0]
    assert calculator.prediction_calls >= calls_after_partial[1]

    restored = mdstats.load_data6_model_sweep_artifacts(root)
    assert restored.checkpoint.content_digest == complete.checkpoint.content_digest
    sample = restored.checkpoint.plan.prediction_frame_uids[0]
    prediction = mdstats.read_atomic_model_prediction(restored.prediction_manifest, root, sample)
    assert np.isfinite(prediction.energy_ev)
    assert prediction.forces_ev_per_angstrom.shape[1] == 3

    descriptor_uid = restored.checkpoint.plan.descriptor_frame_uids[0]
    descriptor_record = restored.descriptor_manifest.for_frame(descriptor_uid)
    descriptor_path = root / descriptor_record.relative_path
    descriptor_path.write_bytes(b"corrupted")
    before = (calculator.descriptor_calls, calculator.prediction_calls)
    repaired = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert repaired.complete
    assert calculator.descriptor_calls == before[0] + 1
    if descriptor_uid in repaired.checkpoint.plan.prediction_frame_uids:
        assert calculator.prediction_calls == before[1] + 1
    else:
        assert calculator.prediction_calls == before[1]


def test_data6_consumes_completed_sweep_without_reinference(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, policy = _inputs(tmp_path)
    calculator = _CountingCalculator()
    provider = _provider(calculator)
    root = tmp_path / "production"
    sweep = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    before = (calculator.descriptor_calls, calculator.prediction_calls)
    bundle = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=policy,
        model_provider=provider,
        model_sweep_artifacts=sweep,
    )
    assert (calculator.descriptor_calls, calculator.prediction_calls) == before
    assert bundle.model_sweep_plan == sweep.checkpoint.plan
    assert bundle.model_sweep_checkpoint_digest == sweep.checkpoint.content_digest
    assert bundle.prediction_manifest == sweep.prediction_manifest
    assert bundle.mace_descriptor_manifest == sweep.descriptor_manifest
    assert bundle.training_difficulty_catalogs
    assert bundle.blinded_prediction_catalogs
    assert mdstats.Data6FeatureBundle.from_dict(bundle.to_dict()) == bundle


def test_failed_sweep_persists_failure_and_can_resume(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    root = tmp_path / "failure"
    broken = _provider(_CountingCalculator(fail_after=1))
    with pytest.raises(RuntimeError, match="intentional"):
        mdstats.run_restartable_data6_model_sweep(
            frames, frame_data, data5, policy, broken, root
        )
    payload = (root / "data6_model_sweep_checkpoint.json").read_text()
    checkpoint = mdstats.Data6ModelSweepCheckpoint.from_dict(__import__("json").loads(payload))
    assert checkpoint.status is mdstats.Data6ModelSweepStatus.FAILED
    assert checkpoint.failure_type == "RuntimeError"

    healthy_calc = _CountingCalculator()
    healthy = _provider(healthy_calc)
    resumed = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, healthy, root
    )
    assert resumed.complete
    assert healthy_calc.prediction_calls < len(resumed.checkpoint.plan.prediction_frame_uids)


def test_rebuilt_catalog_lineage_reuses_verified_model_sidecars(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    calculator = _CountingCalculator()
    provider = _provider(calculator)
    root = tmp_path / "lineage-rebind"

    original = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert original.complete
    calls_before = (calculator.descriptor_calls, calculator.prediction_calls)

    # A DATA3 reference/strain correction changes the catalog and DATA5 lineage
    # while retaining the exact same immutable frame records and role requests.
    rebuilt_frames = replace(
        frames, notes=frames.notes + ("reference/strain lineage rebuilt",)
    )
    rebuilt_data5 = copy.deepcopy(data5)
    object.__setattr__(
        rebuilt_data5, "frame_catalog_digest", rebuilt_frames.content_digest
    )
    object.__setattr__(rebuilt_data5, "_content_digest_cache", "")
    assert rebuilt_frames.content_digest != frames.content_digest
    assert rebuilt_data5.content_digest != data5.content_digest

    rebound = mdstats.run_restartable_data6_model_sweep(
        rebuilt_frames, frame_data, rebuilt_data5, policy, provider, root
    )
    assert rebound.complete
    assert rebound.checkpoint.plan.frame_catalog_digest == rebuilt_frames.content_digest
    assert rebound.checkpoint.plan.data5_bundle_digest == rebuilt_data5.content_digest
    assert (calculator.descriptor_calls, calculator.prediction_calls) == calls_before


def test_sweep_plan_mismatch_fails_closed(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    provider = _provider(_CountingCalculator())
    root = tmp_path / "mismatch"
    mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(max_new_frames=1),
    )
    changed = mdstats.Data6Policy(
        build_lta_selection_features=False,
        build_mace_descriptors=True,
        build_training_difficulty=False,
        build_blinded_predictions=True,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="different plan"):
        mdstats.run_restartable_data6_model_sweep(
            frames, frame_data, data5, changed, provider, root
        )


def test_append_journal_recovers_without_compacted_checkpoint(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    calculator = _CountingCalculator()
    provider = _provider(calculator)
    root = tmp_path / "journal-recovery"

    partial = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            max_new_frames=2,
            checkpoint_interval=1,
        ),
    )
    assert len(partial.checkpoint.completed_frame_uids) == 2
    before = (calculator.descriptor_calls, calculator.prediction_calls)
    (root / "data6_model_sweep_checkpoint.json").unlink()

    complete = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert complete.complete
    assert calculator.descriptor_calls == len(complete.checkpoint.plan.descriptor_frame_uids)
    assert calculator.prediction_calls == len(complete.checkpoint.plan.prediction_frame_uids)
    assert calculator.descriptor_calls >= before[0]
    assert calculator.prediction_calls >= before[1]


def test_full_checkpoint_is_compacted_once_per_invocation(tmp_path: Path, monkeypatch) -> None:
    import mdstats.training_data.production_model_sweep as sweep_module

    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    provider = _provider(_CountingCalculator())
    root = tmp_path / "linear-checkpointing"
    checkpoint_writes = 0
    original_atomic_json = sweep_module._atomic_json

    def counted_atomic_json(path, payload):
        nonlocal checkpoint_writes
        if Path(path).name == "data6_model_sweep_checkpoint.json":
            checkpoint_writes += 1
        return original_atomic_json(path, payload)

    monkeypatch.setattr(sweep_module, "_atomic_json", counted_atomic_json)
    result = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            max_new_frames=3,
            checkpoint_interval=1,
        ),
    )
    assert not result.complete
    assert checkpoint_writes == 1
    journal_lines = (root / "data6_model_sweep_records.jsonl").read_text().splitlines()
    assert len(journal_lines) == 1 + len(result.checkpoint.completed_frame_uids)


def test_truncated_journal_tail_is_removed_before_resume(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    calculator = _CountingCalculator()
    provider = _provider(calculator)
    root = tmp_path / "truncated-journal"

    mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(max_new_frames=2),
    )
    (root / "data6_model_sweep_checkpoint.json").unlink()
    journal = root / "data6_model_sweep_records.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"schema":"truncated')

    complete = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert complete.complete
    # A second restore proves the repaired journal remains parseable.
    restored = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, root
    )
    assert restored.complete
