from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import hashlib
import json
import os
import shutil
import threading
import time

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.work_queue import DeterministicWorkQueueMemoryError
from tests.test_mlff_data5_partition_roles import _build
from tests.test_mlff_data8_mace_artifacts import _probe, _write_replay


class _Calculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def __init__(self):
        super().__init__()
        self.descriptor_calls = 0
        self.prediction_calls = 0

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        self.prediction_calls += 1
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
        return np.column_stack((np.asarray(atoms.numbers, dtype=float), positions))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resources(cpu_budget: int, ram_budget: int = 8 * 1024**3) -> SystemResourceSnapshot:
    return SystemResourceSnapshot(
        cpu_threads_available=max(1, int(cpu_budget)),
        cpu_fraction=1.0,
        cpu_threads_budget=max(1, int(cpu_budget)),
        ram_available_bytes=int(ram_budget),
        ram_fraction=1.0,
        ram_budget_bytes=int(ram_budget),
        gpu_memory_fraction=0.9,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "test"),
    )


def test_variant_cv_planning_reuses_authenticated_data5_authority(tmp_path, monkeypatch) -> None:
    from mdstats.training_data._campaign_cli_core import (
        _VariantSpec,
        _variant_cross_validation_plans,
    )

    _sources, frames, data4, data5 = _build(tmp_path / "cv-authority")
    canonical_folds = len(data5.cross_validation_plans[0].folds)
    variant = _VariantSpec(
        mode="multihead_replay",
        selection_size=512,
        seed=1,
        cross_validation_folds=canonical_folds,
        fold_partition_seed=data5.partition_policy.cross_validation_seed,
    )

    def _unexpected(*args, **kwargs):
        raise AssertionError("canonical DATA5 CV authority must not be rebuilt or re-audited")

    monkeypatch.setattr(mdstats, "build_cross_validation_plans", _unexpected)
    monkeypatch.setattr(mdstats, "audit_partition_leakage", _unexpected)

    observed = _variant_cross_validation_plans(data5, frames, data4, variant)
    assert observed is data5.cross_validation_plans


def test_variant_cv_planning_still_builds_and_audits_noncanonical_folds(tmp_path, monkeypatch) -> None:
    from mdstats.training_data._campaign_cli_core import (
        _VariantSpec,
        _variant_cross_validation_plans,
    )

    _sources, frames, data4, data5 = _build(tmp_path / "cv-derived")
    canonical_folds = len(data5.cross_validation_plans[0].folds)
    variant = _VariantSpec(
        mode="multihead_replay",
        selection_size=512,
        seed=1,
        cross_validation_folds=canonical_folds,
        fold_partition_seed=data5.partition_policy.cross_validation_seed + 1,
    )
    original_build = mdstats.build_cross_validation_plans
    original_audit = mdstats.audit_partition_leakage
    calls = {"build": 0, "audit": 0}

    def _build_counted(*args, **kwargs):
        calls["build"] += 1
        return original_build(*args, **kwargs)

    def _audit_counted(*args, **kwargs):
        calls["audit"] += 1
        return original_audit(*args, **kwargs)

    monkeypatch.setattr(mdstats, "build_cross_validation_plans", _build_counted)
    monkeypatch.setattr(mdstats, "audit_partition_leakage", _audit_counted)

    observed = _variant_cross_validation_plans(data5, frames, data4, variant)
    assert calls == {"build": 1, "audit": 1}
    assert observed != data5.cross_validation_plans


def test_data8_stale_staging_cleanup_is_dead_pid_and_age_guarded(tmp_path):
    from mdstats.training_data.data8_bundle import _cleanup_stale_data8_staging

    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    old = time.time() - 2.0 * 24.0 * 60.0 * 60.0

    dead = cache_root / ".data8-worker-context-99999999-dead"
    dead.mkdir()
    (dead / "spill.bin").write_bytes(b"x" * 1024)
    os.utime(dead, (old, old))

    live = cache_root / f".data8-worker-context-{os.getpid()}-live"
    live.mkdir()
    (live / "spill.bin").write_bytes(b"y" * 1024)
    os.utime(live, (old, old))

    young = cache_root / ".data8-worker-context-99999998-young"
    young.mkdir()
    (young / "spill.bin").write_bytes(b"z" * 1024)

    removed_count, removed_bytes = _cleanup_stale_data8_staging(cache_root)

    assert removed_count == 1
    assert removed_bytes == 1024
    assert not dead.exists()
    assert live.is_dir()
    assert young.is_dir()


def _fixture(tmp_path: Path):
    sources, frames, data4, data5 = _build(tmp_path / "target")
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path / "target")
    foundation_path = tmp_path / "foundation.model"
    foundation_path.write_bytes(b"data9a9b-foundation-fixture")
    foundation = mdstats.FoundationCheckpointIdentity.from_file(foundation_path)
    calc = _Calculator()
    provider = mdstats.MaceCalculatorProvider.from_calculator(
        calc,
        checkpoint_identity=mdstats.ModelCheckpointIdentity(
            model_family="fake-mace",
            checkpoint_locator=str(foundation_path),
            checkpoint_sha256=foundation.sha256,
            calculator_class="tests._Calculator",
            model_version="0.test",
            supported_atomic_numbers=(3, 8, 11, 13, 14, 19),
            device="cpu",
            default_dtype="float64",
        ),
    )
    policy = mdstats.Data6Policy(
        build_lta_selection_features=False,
        build_mace_descriptors=True,
        build_training_difficulty=True,
        build_blinded_predictions=True,
    )
    sweep = mdstats.run_restartable_data6_model_sweep(
        frames, frame_data, data5, policy, provider, tmp_path / "sweep"
    )
    data6 = mdstats.build_data6_feature_bundle(
        sources, frames, frame_data, data4, data5,
        policy=policy, model_provider=provider, model_sweep_artifacts=sweep,
    )
    replay_train = tmp_path / "replay_train.xyz"
    replay_monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(replay_train, offset=0.25, count=4)
    _write_replay(replay_monitor, offset=0.40, count=2)
    replay = mdstats.build_local_replay_plan(replay_train, replay_monitor)
    plan = mdstats.build_production_materialization_plan(
        sources, frames, data4, data5, data6, sweep,
        foundation_checkpoint=foundation,
        compatibility_probe=_probe(),
        replay_plan=replay,
        feature_metric_policy=mdstats.FeatureMetricPolicyTemplate(
            blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
        ),
        atomic_reference_policy=mdstats.AtomicReferenceFitPolicy(),
        selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(4, 8)),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
    )
    return sources, frames, frame_data, data4, data5, data6, sweep, plan, calc


def test_restartable_data7_then_atomic_data8_materialization(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    partial = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root,
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(max_new_data7_domains=1),
    )
    assert not partial.complete
    assert len(partial.checkpoint.data7_artifacts) == 1
    assert partial.checkpoint.data8_artifact is None
    assert not (root / "data8").exists()

    complete = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root
    )
    assert complete.complete
    assert len(complete.checkpoint.data7_artifacts) == len(complete.checkpoint.plan.domains) == 4
    assert complete.checkpoint.data8_artifact is not None
    data8_payload = json.loads((root / "data8" / "data8_preparation_bundle.json").read_text())
    data8 = mdstats.Data8PreparationBundle.from_dict(data8_payload)
    # The immutable bundle records its assembly-time staging locator. Runtime
    # consumers must use the promoted directory exposed by the materialization
    # record rather than this deleted path.
    assert not Path(data8.output_directory).exists()
    assert complete.data8_runtime_directory is not None
    assert Path(complete.data8_runtime_directory).is_dir()
    assert len(data8.jobs) == 4
    assert data8.replay_plan.mode is mdstats.ReplayMode.PRESELECTED
    assert all(job.protocol.replay_plan_digest == data8.replay_plan.content_digest for job in data8.jobs)
    restored = mdstats.load_production_materialization(root)
    assert restored.checkpoint.content_digest == complete.checkpoint.content_digest
    assert mdstats.ProductionMaterializationRecord.from_dict(complete.to_dict()) == complete
    assert len(complete.load_data7_bundles()) == 4
    assert complete.load_data8_bundle().content_digest == data8.content_digest


def test_resume_reuses_valid_data7_and_repairs_tamper(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    first = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    records = {item.domain_digest: item for item in first.checkpoint.data7_artifacts}
    hashes = {key: item.file_sha256 for key, item in records.items()}
    second = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert {item.domain_digest: item.file_sha256 for item in second.checkpoint.data7_artifacts} == hashes

    victim = next(iter(second.checkpoint.data7_artifacts))
    (root / victim.relative_path).write_text("{}\n", encoding="utf-8")
    tampered_sha = _sha(root / victim.relative_path)
    repaired = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert repaired.complete
    repaired_record = next(item for item in repaired.checkpoint.data7_artifacts if item.domain_digest == victim.domain_digest)
    assert repaired_record.file_sha256 != tampered_sha
    assert repaired_record.file_sha256 == _sha(root / repaired_record.relative_path)
    assert mdstats.load_production_materialization(root).complete


def test_plan_requires_complete_sweep_and_exact_replay(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, data6, sweep, plan, _ = _fixture(tmp_path)
    assert mdstats.ProductionMaterializationPlan.from_dict(plan.to_dict()) == plan
    with pytest.raises(mdstats.TrainingDataInputError, match="requires an exact replay corpus"):
        replace(plan, replay_plan=mdstats.ReplayPreparationPlan(mode=mdstats.ReplayMode.NONE))


def test_materialization_plan_content_digest_is_cached(tmp_path: Path, monkeypatch) -> None:
    from mdstats.training_data import production_materialization as module

    plan = _fixture(tmp_path)[7]
    assert plan._content_digest_cache == ""
    original_payload = module.ProductionMaterializationPlan._payload
    calls = {"payload": 0}

    def _payload_counted(self):
        calls["payload"] += 1
        return original_payload(self)

    monkeypatch.setattr(module.ProductionMaterializationPlan, "_payload", _payload_counted)
    serialized = plan.to_dict()
    expected = serialized["content_digest"]
    assert calls == {"payload": 1}
    assert plan._content_digest_cache == expected

    def _unexpected_digest(_payload):
        raise AssertionError("cached materialization identity must not rebuild the large plan payload")

    monkeypatch.setattr(module, "digest", _unexpected_digest)
    assert plan.content_digest == expected


def test_naive_materialization_drops_replay_and_emits_naive_protocol(tmp_path: Path) -> None:
    sources, frames, frame_data, data4, data5, data6, sweep, replay_plan, _ = _fixture(tmp_path)
    naive_plan = mdstats.build_production_materialization_plan(
        sources,
        frames,
        data4,
        data5,
        data6,
        sweep,
        foundation_checkpoint=replay_plan.foundation_checkpoint,
        compatibility_probe=replay_plan.compatibility_probe,
        replay_plan=replay_plan.replay_plan,
        feature_metric_policy=replay_plan.feature_metric_policy,
        atomic_reference_policy=replay_plan.atomic_reference_policy,
        objective_policy=replay_plan.objective_policy,
        configuration_weight_policy=replay_plan.configuration_weight_policy,
        checkpoint_metric_policy=replay_plan.checkpoint_metric_policy,
        selection_budget_policy=replay_plan.selection_budget_policy,
        compatibility_policy=replay_plan.compatibility_policy,
        optimizer_policy=replay_plan.optimizer_policy,
        checkpoint_control_policy=replay_plan.checkpoint_control_policy,
        extxyz_policy=replay_plan.extxyz_policy,
        foundation_reference_energies=dict(replay_plan.foundation_reference_energies),
        selection_size=replay_plan.selection_size,
        require_foundation_residual_e0=replay_plan.require_foundation_residual_e0,
        require_replay=False,
    )
    assert naive_plan.replay_plan.mode is mdstats.ReplayMode.NONE
    materialized = mdstats.run_restartable_production_materialization(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        data6,
        sweep,
        naive_plan,
        tmp_path / "naive-materialized",
    )
    bundle = materialized.load_data8_bundle()
    assert bundle.replay_plan.mode is mdstats.ReplayMode.NONE
    assert all(
        job.protocol.training_mode is mdstats.TrainingMode.NAIVE_FINE_TUNING
        for job in bundle.jobs
    )
    assert all(job.protocol.replay_plan_digest is None for job in bundle.jobs)


def test_existing_plan_mismatch_fails_closed(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root,
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(max_new_data7_domains=1),
    )
    changed = mdstats.ProductionMaterializationPlan.from_dict({
        **inputs[7].to_dict(),
        "selection_size": 4,
        "content_digest": None,
    })
    with pytest.raises(mdstats.TrainingDataInputError, match="another plan"):
        mdstats.run_restartable_production_materialization(*inputs[:7], changed, root)


def test_materialization_updates_production_qualification(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    sources, frames, _, data4, data5, data6 = inputs[:6]
    run_evidence = {
        "runs": [
            {
                "run_id": "bounded-run-001",
                "frame_count": len(frames.frames),
                "energy_complete": True,
                "forces_complete": True,
                "stress_complete": True,
                "ensemble_status": "resolved",
                "quality_outcome": "qualified",
                "production_status": "accepted",
                "reduced_formula": "LiO",
                "ensemble": "NVT",
                "target_start_kelvin": 300.0,
                "target_end_kelvin": 300.0,
            }
        ]
    }
    normalization = {"version": 1}
    reference = {"version": 1}
    production_plan = mdstats.ProductionCorpusPlan(
        plan_id="bounded-data9a9b-fixture",
        dataset_id=frames.dataset_id,
        source_catalog_digest=sources.content_digest,
        frame_catalog_digest=frames.content_digest,
        normalization_manifest_digest=digest(normalization),
        reference_manifest_digest=digest(reference),
        expected_runs=(mdstats.ProductionExpectedRun(
            run_id="bounded-run-001", frame_count=len(frames.frames), reduced_formula="LiO",
            ensemble="NVT", target_start_kelvin=300.0, target_end_kelvin=300.0,
        ),),
        expected_cross_validation_fold_count=sum(len(v.folds) for v in data5.cross_validation_plans),
    )
    qualification = mdstats.build_production_corpus_qualification_record(
        production_plan=production_plan,
        normalization_manifest=normalization,
        reference_manifest=reference,
        run_evidence_manifest=run_evidence,
        source_catalog=sources,
        frame_catalog=frames,
        data4_bundle=data4,
        data5_bundle=data5,
        data6_bundle=data6,
        production_materialization=record,
    )
    assert qualification.data7_bundle_digests == record.data7_bundle_digests
    assert qualification.data8_bundle_digest == record.data8_bundle_digest
    assert qualification.data8_artifacts_materialized
    assert qualification.replay_corpus_bound
    assert qualification.foundation_features_materialized
    assert not qualification.foundation_residual_e0_materialized
    assert "foundation_residual_e0_not_materialized" in qualification.blockers
    assert not qualification.full_data9a_passed


def test_data8_tree_tamper_is_detected_and_rebuilt(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    complete = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    data8 = complete.checkpoint.data8_artifact
    assert data8 is not None
    victim_rel = next(path for path, _ in data8.tree_entries if path.endswith("mace_config.yaml"))
    victim = root / data8.relative_directory / victim_rel
    victim.write_text(victim.read_text(encoding="utf-8") + "# tamper\n", encoding="utf-8")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="DATA8 artifact"):
        mdstats.load_production_materialization(root)
    repaired = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert repaired.complete
    assert mdstats.load_production_materialization(root).complete


def test_shared_data7_cache_reuses_scientific_artifacts_across_variants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_data7_preparation_bundle", counted)
    shared: dict[str, object] = {}
    cache = tmp_path / "shared-data7"
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-one",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=shared,
    )
    first_calls = calls
    assert first.complete
    assert first_calls == len(first.checkpoint.plan.domains)

    second = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-two",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=shared,
    )
    assert second.complete
    assert calls == first_calls
    assert second.data7_bundle_digests == first.data7_bundle_digests
    assert len(shared) == len(first.checkpoint.plan.domains)

    restored_shared: dict[str, object] = {}
    third = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-three",
        shared_data7_cache_directory=cache,
        shared_data7_artifacts=restored_shared,
    )
    assert third.complete
    assert calls == first_calls
    assert third.data7_bundle_digests == first.data7_bundle_digests
    assert len(restored_shared) == len(first.checkpoint.plan.domains)


def test_promoted_data7_artifacts_can_seed_optimizer_only_variant_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_data7_preparation_bundle", counted)
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "seed-one"
    )
    first_calls = calls
    assert first.complete
    assert first_calls == len(first.checkpoint.plan.domains)

    shared: dict[str, object] = {}
    registered = mdstats.register_reusable_data7_artifacts(first, shared)
    assert registered == len(first.checkpoint.plan.domains)

    changed_plan = replace(
        inputs[7],
        optimizer_policy=replace(inputs[7].optimizer_policy, seed=97),
    )
    assert changed_plan.content_digest != inputs[7].content_digest
    second = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        changed_plan,
        tmp_path / "seed-ninety-seven",
        shared_data7_artifacts=shared,
    )
    assert second.complete
    assert calls == first_calls
    assert second.data7_bundle_digests == first.data7_bundle_digests


def test_atomic_json_hash_is_computed_during_streaming_write(tmp_path: Path) -> None:
    import mdstats.training_data.production_materialization as module

    path = tmp_path / "large.json"
    payload = {"records": [{"index": index, "value": "x" * 64} for index in range(500)]}
    observed = module._atomic_json(path, payload)
    assert observed == hashlib.sha256(path.read_bytes()).hexdigest()
    assert json.loads(path.read_text(encoding="utf-8")) == payload


def test_campaign_rejects_legacy_naive_variant_with_replay_protocol(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    bundle = record.load_data8_bundle()
    with pytest.raises(campaign_cli.CampaignCliError, match="naive/replay aliasing"):
        campaign_cli._validate_data8_variant_identity(
            "naive_fine_tuning-n8-seed1", bundle
        )


def test_campaign_resolves_promoted_data8_configs_without_reprepare(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root
    )
    bundle = record.load_data8_bundle()
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)

    entries = campaign_cli._current_data8_entries(store)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.root == (root / "data8").resolve()
    for job in entry.bundle.jobs:
        config = entry.root / job.config_relative_path
        assert config.is_file()
        assert campaign_cli._sha256(config) == job.config_sha256


def test_preflight_completion_is_bound_to_current_data8_matrix(tmp_path: Path) -> None:
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    bundle = record.load_data8_bundle()
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    store.put_record(
        "preflight_smoke",
        {"passed": True, "data8_matrix_digest": "0" * 64},
    )
    campaign_cli._mark_stage(
        store,
        paths,
        "preflight",
        campaign_cli.StageState.COMPLETE,
        "legacy DATA8 smoke",
    )
    state, message = campaign_cli._effective_stage(store, paths, "preflight")
    assert state is campaign_cli.StageState.WAITING
    assert "DATA8 variants changed" in message


def test_check_only_preflight_reuses_promoted_data8_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    materialization_root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], materialization_root
    )
    bundle = record.load_data8_bundle()

    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    campaign_cli._mark_stage(
        store, paths, "prepare", campaign_cli.StageState.COMPLETE,
        "production data gate passed",
    )
    monkeypatch.setattr(campaign_cli, "command_doctor", lambda args: 0)
    # These tests isolate promoted-DATA8 preflight behavior. Gate authorities are
    # exercised in their dedicated suites, so provide authenticated-looking
    # records rather than constructing a second full prepare graph here.
    authority = SimpleNamespace(content_digest="a" * 64)
    study = SimpleNamespace(
        content_digest="d" * 64, qualified_sizes=(128, 256, 512),
        outcome="awaiting_epoch_10", decision_reason="test target-size study",
    )
    monkeypatch.setattr(campaign_cli, "_load_verified_foundation_audit_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_coverage_reference_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_size_study_authority", lambda store: study)

    result = campaign_cli.command_preflight(
        argparse.Namespace(config=str(config), check_only=True)
    )
    assert result == 2
    output = capsys.readouterr().out
    assert "verified 4 MACE job configurations across 1 variants" in output
    assert "DATA8 config failed byte verification" not in output


def test_preflight_prints_variant_qualified_config_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import argparse
    from mdstats.training_data import campaign_cli

    inputs = _fixture(tmp_path / "fixture")
    materialization_root = tmp_path / "materialized"
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], materialization_root
    )
    bundle = record.load_data8_bundle()
    victim = next(job for job in bundle.jobs if job.job_id == "final")
    config_path = materialization_root / "data8" / victim.config_relative_path
    config_path.write_text(config_path.read_text(encoding="utf-8") + "# tampered\n", encoding="utf-8")

    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="workspace",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay_train.xyz",
            replay_monitor="replay_monitor.xyz",
            acceleration_backend="e3nn",
        ),
        encoding="utf-8",
    )
    _, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    variant_id = "multihead_replay-n8-seed1"
    store.put_record(f"materialization:{variant_id}", record)
    store.put_record(f"data8:{variant_id}", bundle)
    campaign_cli._mark_stage(
        store, paths, "prepare", campaign_cli.StageState.COMPLETE,
        "production data gate passed",
    )
    monkeypatch.setattr(campaign_cli, "command_doctor", lambda args: 0)
    # These tests isolate promoted-DATA8 preflight behavior. Gate authorities are
    # exercised in their dedicated suites, so provide authenticated-looking
    # records rather than constructing a second full prepare graph here.
    authority = SimpleNamespace(content_digest="a" * 64)
    study = SimpleNamespace(
        content_digest="d" * 64, qualified_sizes=(128, 256, 512),
        outcome="awaiting_epoch_10", decision_reason="test target-size study",
    )
    monkeypatch.setattr(campaign_cli, "_load_verified_foundation_audit_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_coverage_reference_authority", lambda store: authority)
    monkeypatch.setattr(campaign_cli, "_load_verified_target_size_study_authority", lambda store: study)

    result = campaign_cli.command_preflight(
        argparse.Namespace(config=str(config), check_only=True)
    )
    assert result == 1
    output = capsys.readouterr().out
    assert "[FAIL] DATA8 config failed byte verification" in output
    assert "multihead_replay-n8-seed1/final" in output
    assert "stopped before launching MACE" in output



def test_prescribed_target_prefixes_drive_final_and_cv_data7_without_reselection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources, frames, frame_data, data4, data5, data6, sweep, plan, _ = _fixture(tmp_path)
    selected_size = 4

    import mdstats.training_data.data7_bundle as data7_bundle_module

    def forbidden_selector(*args, **kwargs):
        raise AssertionError("target-size-controlled DATA7 must not invoke independent selection")

    monkeypatch.setattr(
        data7_bundle_module, "build_training_selection_plan", forbidden_selector
    )
    observed_kinds = set()
    for domain in plan.domains:
        prefix = tuple(domain.frame_uids[:selected_size])
        bundle = mdstats.build_data7_preparation_bundle(
            sources,
            frames,
            frame_data,
            data4,
            data5,
            data6,
            domain,
            feature_metric_policy=plan.feature_metric_policy,
            atomic_reference_policy=plan.atomic_reference_policy,
            objective_policy=plan.objective_policy,
            configuration_weight_policy=plan.configuration_weight_policy,
            checkpoint_metric_policy=plan.checkpoint_metric_policy,
            selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(selected_size,)),
            mace_descriptor_root=sweep.root_directory,
            prescribed_selection_frame_uids=prefix,
            prescribed_selection_role="selected_production_prefix",
        )
        observed_kinds.add(bundle.domain.kind)
        assert tuple(item.frame_uid for item in bundle.selection_plan.master_order) == prefix
        assert bundle.selection_plan.ladder_levels[-1].frame_uids == prefix
    assert observed_kinds == {
        mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        mdstats.FeatureFitDomainKind.CROSS_VALIDATION_TRAINING,
    }


def test_data7_parallel_domains_preserve_serial_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    serial = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "serial",
        execution_resources=_resources(1),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )

    original = module.build_data7_preparation_bundle
    active = 0
    maximum = 0
    lock = threading.Lock()

    def observed(*args, **kwargs):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        try:
            time.sleep(0.05)
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(module, "build_data7_preparation_bundle", observed)
    parallel = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "parallel",
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    assert maximum >= 2
    assert parallel.data7_bundle_digests == serial.data7_bundle_digests
    assert [item.file_sha256 for item in parallel.checkpoint.data7_artifacts] == [
        item.file_sha256 for item in serial.checkpoint.data7_artifacts
    ]


def test_data7_ram_admission_rejects_intrinsically_impossible_domain(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    with pytest.raises(DeterministicWorkQueueMemoryError):
        mdstats.run_restartable_production_materialization(
            *inputs[:7],
            inputs[7],
            tmp_path / "too-small",
            execution_resources=_resources(2, ram_budget=32 * 1024**2),
            execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
        )


def test_max_new_domains_counts_verified_shared_cache_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    cache = tmp_path / "shared-data7"
    seed = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "seed",
        shared_data7_cache_directory=cache,
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    assert len(seed.checkpoint.data7_artifacts) == len(seed.checkpoint.plan.domains)
    assert not tuple(cache.glob("*.manifest.json"))
    assert len(tuple(cache.glob("*/*/cache.json"))) == len(seed.checkpoint.plan.domains)

    def forbidden(*args, **kwargs):
        raise AssertionError("shared-cache hit unexpectedly rebuilt DATA7")

    monkeypatch.setattr(module, "build_data7_preparation_bundle", forbidden)
    partial = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "partial-from-cache",
        shared_data7_cache_directory=cache,
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(
            max_new_data7_domains=2,
            materialize_data8=False,
        ),
    )
    assert len(partial.checkpoint.data7_artifacts) == 2


def test_data7_shared_cache_accepts_legacy_flat_generations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    current_cache = tmp_path / "current-data7"
    seed = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "legacy-seed",
        shared_data7_cache_directory=current_cache,
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    legacy_cache = tmp_path / "legacy-data7"
    legacy_cache.mkdir()
    for metadata_path in current_cache.glob("*/*/cache.json"):
        metadata = json.loads(metadata_path.read_text())
        recipe_digest = metadata["recipe_digest"]
        artifact_name = f"{recipe_digest}.data7.zip"
        shutil.copy2(metadata_path.parent / metadata["artifact_name"], legacy_cache / artifact_name)
        metadata["schema"] = module.SHARED_DATA7_ARTIFACT_V2_SCHEMA
        metadata["artifact_name"] = artifact_name
        (legacy_cache / f"{recipe_digest}.manifest.json").write_text(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n"
        )
    assert len(tuple(legacy_cache.glob("*.manifest.json"))) == len(seed.checkpoint.plan.domains)

    def forbidden(*args, **kwargs):
        raise AssertionError("legacy DATA7 cache hit unexpectedly rebuilt DATA7")

    monkeypatch.setattr(module, "build_data7_preparation_bundle", forbidden)
    restored = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "legacy-restored",
        shared_data7_cache_directory=legacy_cache,
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    assert restored.data7_bundle_digests == seed.data7_bundle_digests


def test_data7_shared_cache_concurrent_publishers_validate_one_generation(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    seed = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "cache-race-seed",
        execution_resources=_resources(1),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    domain = seed.checkpoint.plan.domains[0]
    bundle = seed.load_data7_bundles()[0]
    recipe_digest = module._data7_recipe_digest(seed.checkpoint.plan, domain)
    cache = tmp_path / "cache-race"

    def publish(_index: int):
        return module._write_reusable_data7_artifact(
            cache, recipe_digest, domain, bundle, seed.checkpoint.plan
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        receipts = tuple(executor.map(publish, range(8)))
    assert len({item.path for item in receipts}) == 1
    assert len({item.file_sha256 for item in receipts}) == 1
    assert len({item.bundle_digest for item in receipts}) == 1
    assert len(tuple(cache.glob("*/*/cache.json"))) == 1
    loaded = module._load_reusable_data7_artifact(
        cache, recipe_digest, domain, seed.checkpoint.plan
    )
    assert loaded is not None
    assert loaded[0].file_sha256 == receipts[0].file_sha256


def test_data8_fixed_file_cache_uses_fresh_parallel_workers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.data8_bundle as module

    monkeypatch.setattr(module, "DATA8_PARALLEL_MIN_TOTAL_BYTES", 0)
    original = module.isolated_process_map
    observed_workers: list[int] = []

    def counted(*args, workers: int, **kwargs):
        observed_workers.append(int(workers))
        yield from original(*args, workers=workers, **kwargs)

    monkeypatch.setattr(module, "isolated_process_map", counted)
    cache = tmp_path / "shared-data8"
    progress: list[str] = []
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "parallel-data8",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
        progress_callback=progress.append,
    )
    assert record.complete
    assert observed_workers and max(observed_workers) >= 2
    assert any("DATA8 fixed-file cache; mode=parallel" in item for item in progress)
    assert any("completed_misses=" in item for item in progress)
    fixed_generations = tuple(
        path for path in cache.glob("*/*/cache.json")
        if "weighted-replay" not in path.parts
    )
    assert len(fixed_generations) > 1
    assert record.load_data8_bundle().content_digest == record.data8_bundle_digest


def test_data8_small_fixed_file_workload_avoids_fresh_process_overhead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.data8_bundle as module

    monkeypatch.setattr(
        module,
        "isolated_process_map",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("small DATA8 workload unexpectedly launched fresh workers")
        ),
    )
    progress: list[str] = []
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "small-data8",
        shared_data8_fixed_file_cache_directory=tmp_path / "small-data8-cache",
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
        progress_callback=progress.append,
    )
    assert record.complete
    assert any("reason=small-workload" in item for item in progress)


def test_data8_parallel_fixed_cache_preserves_serial_extxyz_bytes(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)

    def identities(record):
        bundle = record.load_data8_bundle()
        artifacts = tuple(bundle.target_artifacts) + tuple(bundle.fold_evaluation_artifacts)
        return tuple(
            sorted(
                (
                    item.role,
                    item.relative_path,
                    item.sha256,
                    item.sidecar_sha256,
                    item.content_digest,
                )
                for item in artifacts
            )
        )

    serial = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "serial-data8",
        shared_data8_fixed_file_cache_directory=tmp_path / "serial-data8-cache",
        execution_resources=_resources(1),
        minimum_free_disk_bytes=0,
    )
    parallel = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "parallel-data8-exact",
        shared_data8_fixed_file_cache_directory=tmp_path / "parallel-data8-cache-exact",
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
    )
    assert identities(parallel) == identities(serial)


def test_data8_shared_cache_reuses_weighted_replay_realization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.data8_bundle as module

    original = module._scale_extxyz_configuration_weights
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "_scale_extxyz_configuration_weights", counted)
    cache = tmp_path / "shared-data8"
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        inputs[7],
        tmp_path / "variant-one",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
    )
    assert first.complete
    assert calls == 1
    first_replay = first.load_data8_bundle().replay_plan.train_artifact
    assert first_replay is not None

    second = mdstats.run_restartable_production_materialization(
        *inputs[:7],
        replace(inputs[7], optimizer_policy=replace(inputs[7].optimizer_policy, seed=97)),
        tmp_path / "variant-two",
        shared_data8_fixed_file_cache_directory=cache,
        shared_data7_artifacts={},
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
    )
    assert second.complete
    assert calls == 1
    second_replay = second.load_data8_bundle().replay_plan.train_artifact
    assert second_replay is not None
    assert second_replay.content_digest == first_replay.content_digest
    assert second_replay.sha256 == first_replay.sha256


def test_data8_parallel_cache_respects_free_disk_reserve(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    cache = tmp_path / "shared-data8"
    cache.mkdir()
    free = shutil.disk_usage(cache).free
    with pytest.raises(mdstats.TrainingDataInputError, match="lacks free disk"):
        mdstats.run_restartable_production_materialization(
            *inputs[:7],
            inputs[7],
            tmp_path / "disk-bound",
            shared_data8_fixed_file_cache_directory=cache,
            execution_resources=_resources(4),
            minimum_free_disk_bytes=free,
        )


def test_data8_external_inputs_are_inode_independent_snapshots(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    plan = inputs[7]
    foundation_source = Path(plan.foundation_checkpoint.reference)
    replay_monitor_source = Path(plan.replay_plan.monitor_artifact.path)
    foundation_bytes = foundation_source.read_bytes()
    replay_monitor_bytes = replay_monitor_source.read_bytes()
    cache = tmp_path / "shared-data8-snapshots"

    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], plan, tmp_path / "snapshot-variant",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4),
        minimum_free_disk_bytes=0,
    )
    assert record.complete and record.data8_runtime_directory is not None
    runtime = Path(record.data8_runtime_directory)
    staged_foundation = runtime / "shared" / "foundation" / foundation_source.name
    staged_monitor = runtime / "shared" / "replay" / "replay_monitor.xyz"
    assert staged_foundation.read_bytes() == foundation_bytes
    assert staged_monitor.read_bytes() == replay_monitor_bytes
    if foundation_source.stat().st_dev == staged_foundation.stat().st_dev:
        assert foundation_source.stat().st_ino != staged_foundation.stat().st_ino
    if replay_monitor_source.stat().st_dev == staged_monitor.stat().st_dev:
        assert replay_monitor_source.stat().st_ino != staged_monitor.stat().st_ino

    foundation_source.write_bytes(b"externally-mutated-foundation")
    replay_monitor_source.write_text("externally mutated\n", encoding="utf-8")
    assert staged_foundation.read_bytes() == foundation_bytes
    assert staged_monitor.read_bytes() == replay_monitor_bytes

    # Once the authenticated snapshot exists, equivalent variants no longer
    # depend on the externally owned path retaining those bytes.
    second_plan = replace(
        plan, optimizer_policy=replace(plan.optimizer_policy, seed=303)
    )
    second = mdstats.run_restartable_production_materialization(
        *inputs[:7], second_plan, tmp_path / "snapshot-variant-two",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4), minimum_free_disk_bytes=0,
    )
    assert second.complete


def test_data8_input_snapshots_reuse_content_across_optimizer_variants(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    cache = tmp_path / "shared-data8-snapshots"
    first = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "snapshot-v1",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4), minimum_free_disk_bytes=0,
    )
    assert first.complete
    snapshots_after_first = tuple(sorted(cache.glob("input-snapshots/*/*/artifact.bin")))
    assert snapshots_after_first

    second_plan = replace(
        inputs[7], optimizer_policy=replace(inputs[7].optimizer_policy, seed=101)
    )
    second = mdstats.run_restartable_production_materialization(
        *inputs[:7], second_plan, tmp_path / "snapshot-v2",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4), minimum_free_disk_bytes=0,
    )
    assert second.complete
    snapshots_after_second = tuple(sorted(cache.glob("input-snapshots/*/*/artifact.bin")))
    assert snapshots_after_second == snapshots_after_first


def test_data8_parallel_context_disk_pressure_falls_back_before_workers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.data8_bundle as module
    import mdstats.training_data._array_pickle as array_pickle

    monkeypatch.setattr(module, "DATA8_PARALLEL_MIN_TOTAL_BYTES", 0)
    cache = tmp_path / "shared-data8-context-disk"
    cache.mkdir()
    original_usage = module.shutil.disk_usage
    real = original_usage(cache)
    calls = 0

    def staged_usage(path):
        nonlocal calls
        calls += 1
        # Initial admission permits final files and estimated context.  Once
        # the context exists, emulate a filesystem whose remaining parallel
        # headroom disappeared; the code must fall back before worker launch.
        if calls == 1:
            return real
        return type(real)(real.total, real.used, 1 << 20)

    monkeypatch.setattr(module.shutil, "disk_usage", staged_usage)
    monkeypatch.setattr(array_pickle, "estimate_array_reference_spill_bytes", lambda value: 0)

    def forbidden(*args, **kwargs):
        raise AssertionError("DATA8 subprocesses launched despite context disk pressure")

    monkeypatch.setattr(module, "isolated_process_map", forbidden)
    progress: list[str] = []
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "context-disk-fallback",
        shared_data8_fixed_file_cache_directory=cache,
        execution_resources=_resources(4), minimum_free_disk_bytes=0,
        progress_callback=progress.append,
    )
    assert record.complete
    assert any("reason=measured-context-disk" in item for item in progress)


def test_data7_parallel_out_of_order_completion_commits_canonical_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    completion_order: list[str] = []
    completion_lock = threading.Lock()

    def delayed(*args, **kwargs):
        domain = args[6]
        bundle = original(*args, **kwargs)
        if domain.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT:
            time.sleep(0.15)
        elif domain.fold_index == 0:
            time.sleep(0.08)
        with completion_lock:
            completion_order.append(domain.content_digest)
        return bundle

    monkeypatch.setattr(module, "build_data7_preparation_bundle", delayed)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "out-of-order-data7",
        shared_data7_cache_directory=tmp_path / "out-of-order-cache",
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    canonical = [domain.content_digest for domain in record.checkpoint.plan.domains]
    committed = [item.domain_digest for item in record.checkpoint.data7_artifacts]
    assert completion_order != canonical
    assert committed == canonical


def test_data7_worker_failure_keeps_later_cache_reusable_without_checkpoint_jump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _fixture(tmp_path)
    import mdstats.training_data.production_materialization as module

    original = module.build_data7_preparation_bundle
    cache = tmp_path / "failure-data7-cache"
    root = tmp_path / "failure-data7"
    fail_digest = inputs[7].domains[1].content_digest

    def failing(*args, **kwargs):
        domain = args[6]
        if domain.content_digest == fail_digest:
            time.sleep(0.25)
            raise RuntimeError("injected DATA7 domain failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_data7_preparation_bundle", failing)
    with pytest.raises(RuntimeError, match="injected DATA7 domain failure"):
        mdstats.run_restartable_production_materialization(
            *inputs[:7], inputs[7], root,
            shared_data7_cache_directory=cache,
            execution_resources=_resources(4),
            execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
        )

    checkpoint_path = root / "production_materialization_checkpoint.json"
    if checkpoint_path.is_file():
        checkpoint = mdstats.ProductionMaterializationCheckpoint.from_dict(
            json.loads(checkpoint_path.read_text())
        )
        committed = [item.domain_digest for item in checkpoint.data7_artifacts]
        canonical = [domain.content_digest for domain in inputs[7].domains]
        assert committed == canonical[: len(committed)]
        assert fail_digest not in committed

    published = tuple(cache.glob("*/*/cache.json"))
    assert published, "nonfailing parallel domains should leave reusable cache generations"

    monkeypatch.setattr(module, "build_data7_preparation_bundle", original)
    restored = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], root,
        shared_data7_cache_directory=cache,
        execution_resources=_resources(4),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    assert [item.domain_digest for item in restored.checkpoint.data7_artifacts] == [
        domain.content_digest for domain in inputs[7].domains
    ]


def test_checkpoint_reads_legacy_lexical_data7_order_and_rewrites_plan_order(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "legacy-checkpoint-order",
        execution_resources=_resources(1),
        execution_policy=mdstats.ProductionMaterializationExecutionPolicy(materialize_data8=False),
    )
    checkpoint = record.checkpoint
    payload = checkpoint.to_dict()
    lexical = sorted(payload["data7_artifacts"], key=lambda item: item["domain_digest"])
    legacy_payload = {**payload, "data7_artifacts": lexical}
    legacy_payload["content_digest"] = digest(
        {key: value for key, value in legacy_payload.items() if key != "content_digest"}
    )
    restored = mdstats.ProductionMaterializationCheckpoint.from_dict(legacy_payload)
    assert [item.domain_digest for item in restored.data7_artifacts] == [
        domain.content_digest for domain in restored.plan.domains
    ]


def test_single_head_train2_target_prefix_uses_current_plan_schema(tmp_path: Path) -> None:
    sources, frames, _frame_data, data4, data5, data6, sweep, legacy_plan, _calc = _fixture(tmp_path)
    assert legacy_plan.selected_head_qualification is None

    domains = mdstats.build_feature_fit_domains(data5, cross_validation_plans=())
    assert len(domains) == 1
    selection_size = 4
    prescribed = {
        domain.content_digest: tuple(domain.frame_uids[:selection_size])
        for domain in domains
    }
    assert all(len(uids) == selection_size for uids in prescribed.values())

    true_replay = mdstats.inspect_replay_extxyz(
        Path(legacy_plan.replay_plan.monitor_artifact.path),
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    budget = mdstats.TrainingBudgetPolicy(
        planned_epochs=legacy_plan.optimizer_policy.max_num_epochs
    )
    learning_rate = mdstats.LearningRateSchedulePolicy(
        base_learning_rate=legacy_plan.optimizer_policy.learning_rate
    )
    admissibility = mdstats.CheckpointAdmissibilityPolicy(
        replay_enabled=legacy_plan.require_replay
    )
    selection = mdstats.CheckpointSelectionPolicy()

    plan = mdstats.build_production_materialization_plan(
        sources,
        frames,
        data4,
        data5,
        data6,
        sweep,
        foundation_checkpoint=legacy_plan.foundation_checkpoint,
        compatibility_probe=legacy_plan.compatibility_probe,
        replay_plan=legacy_plan.replay_plan,
        cross_validation_plans=(),
        online_monitor_policy=mdstats.OnlineMonitorPolicy(
            target_configurations=1,
            replay_configurations=1,
            training_diagnostic_configurations=1,
        ),
        true_replay_monitor_artifact=true_replay,
        training_budget_policy=budget,
        learning_rate_schedule_policy=learning_rate,
        checkpoint_admissibility_policy=admissibility,
        checkpoint_selection_policy=selection,
        feature_metric_policy=legacy_plan.feature_metric_policy,
        atomic_reference_policy=legacy_plan.atomic_reference_policy,
        objective_policy=legacy_plan.objective_policy,
        configuration_weight_policy=legacy_plan.configuration_weight_policy,
        checkpoint_metric_policy=legacy_plan.checkpoint_metric_policy,
        selection_budget_policy=legacy_plan.selection_budget_policy,
        compatibility_policy=legacy_plan.compatibility_policy,
        optimizer_policy=legacy_plan.optimizer_policy,
        checkpoint_control_policy=legacy_plan.checkpoint_control_policy,
        extxyz_policy=legacy_plan.extxyz_policy,
        foundation_reference_energies=dict(legacy_plan.foundation_reference_energies),
        selection_size=selection_size,
        selection_authority_role="selected_production_prefix",
        target_size_study_digest="a" * 64,
        prescribed_training_domain_prefixes=prescribed,
        require_foundation_residual_e0=False,
        require_replay=True,
    )

    assert plan.plan_schema == mdstats.PRODUCTION_MATERIALIZATION_PLAN_SCHEMA
    assert plan.plan_schema == "mdstats.production-materialization-plan.v10"
    assert plan.selected_head_qualification is None
    payload = plan.to_dict()
    assert payload["selected_head_qualification"] is None
    restored = mdstats.ProductionMaterializationPlan.from_dict(payload)
    assert restored.content_digest == plan.content_digest
