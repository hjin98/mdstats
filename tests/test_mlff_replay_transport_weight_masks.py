"""G12A replay-transport falsification: source weights never reach MACE.

Pinned MACE ``UniversalLoss`` consumes the per-property ``config_*_weight``
values of every replay frame.  Each test drives a real replay owner with source
frames carrying deliberately contaminated weight metadata and checks the
transport MACE would load: ``config_weight=1`` and exact 0/1 availability
masks derived from the labels actually rendered.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("ase")

from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator
from ase.io import iread, write

from mdstats.training_data._common import TrainingDataInputError, sha256_file_cached
from mdstats.training_data.foundation import FoundationInferenceIdentity, FoundationPotentialIdentity
from mdstats.training_data.replay import (
    ReplayLabelMode,
    ReplayMode,
    ReplaySplitRole,
    build_local_replay_plan,
    build_replay_split_manifest,
    build_replay_true_label_cache,
    canonical_replay_geometry_identity,
    inspect_replay_extxyz,
    inspect_replay_source_extxyz,
    materialize_replay_true_label_views,
    resolve_true_label_replay_directory,
)
from mdstats.training_data.replay_pseudolabel import (
    ReplayFoundationPredictionPolicy,
    ReplayPseudolabelQualificationPolicy,
    build_replay_foundation_prediction_cache,
    build_replay_pseudolabel_qualification,
    materialize_replay_pseudolabel_views,
)

_STRESSLESS = 3
_CONTAMINATION = {
    "config_weight": 4.0,
    "config_energy_weight": 0.3,
    "config_forces_weight": 2.5,
    "config_virials_weight": 9.0,
}


def _geometry(index: int) -> Atoms:
    return Atoms(
        "H2",
        positions=((0.0, 0.0, 0.0), (0.75 + 0.01 * index, 0.0, 0.0)),
        cell=(8.0, 8.0, 8.0),
        pbc=True,
    )


def _write_source(path: Path, count: int = 12, *, contaminate: bool = True) -> None:
    frames = []
    for index in range(count):
        atoms = _geometry(index)
        atoms.calc = SinglePointCalculator(
            atoms,
            energy=-10.0 - 0.1 * index,
            forces=np.full((2, 3), 0.02 * (index + 1)),
            **({} if index == _STRESSLESS else {"stress": np.arange(6) * 0.001 * (index + 1)}),
        )
        if contaminate:
            atoms.info.update(_CONTAMINATION)
            # Wrong in both directions: zero where stress exists, positive where absent.
            atoms.info["config_stress_weight"] = 7.0 if index == _STRESSLESS else 0.0
        frames.append(atoms)
    write(path, frames, format="extxyz")


def _assert_canonical_transport(path: str | Path) -> dict[str, dict]:
    frames = {}
    for atoms in iread(path, index=":", format="extxyz"):
        stress_present = "REF_stress" in atoms.info
        weights = {key: value for key, value in atoms.info.items() if key.startswith("config_") and key.endswith("weight")}
        assert weights == {
            "config_weight": 1.0,
            "config_energy_weight": 1.0,
            "config_forces_weight": 1.0,
            "config_stress_weight": 1.0 if stress_present else 0.0,
        }
        assert "REF_energy" in atoms.info and "REF_forces" in atoms.arrays
        frames[canonical_replay_geometry_identity(atoms)] = {
            "stress_present": stress_present,
            "energy": float(atoms.info["REF_energy"]),
        }
    # The inspection boundary accepts exactly this transport.
    inspect_replay_extxyz(path)
    return frames


def _stressless_identity() -> str:
    return canonical_replay_geometry_identity(_geometry(_STRESSLESS))


def test_true_dft_single_source_views_canonicalize_contaminated_source_weights(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path)
    source = inspect_replay_source_extxyz(source_path)
    cache = build_replay_true_label_cache(source)
    split = build_replay_split_manifest(source, split_ratio=(1, 1), split_seed=5)
    views = materialize_replay_true_label_views(source, cache, split, tmp_path / "views")

    rendered: dict[str, dict] = {}
    for role in (ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR):
        rendered.update(_assert_canonical_transport(views[role].path))
    assert set(rendered) == set(source.geometry_identities)
    # Stress availability follows the rendered label: no stress is fabricated.
    assert rendered.pop(_stressless_identity())["stress_present"] is False
    assert all(frame["stress_present"] for frame in rendered.values())


class _PseudoProvider:
    """Foundation double that omits pseudo stress for one geometry only."""

    def __init__(self, policy: ReplayFoundationPredictionPolicy, *, stressless_marker: float) -> None:
        self.calls: list[int] = []
        self.stressless_marker = stressless_marker
        self.checkpoint_identity = SimpleNamespace(
            checkpoint_sha256=policy.foundation_potential.sha256,
            default_dtype=policy.foundation_inference.default_dtype,
            foundation_potential_digest=policy.foundation_potential.canonical_content_digest,
            foundation_inference_digest=policy.foundation_inference.content_digest,
            foundation_head=policy.foundation_potential.foundation_head,
        )

    def set_head(self, head: str) -> None:
        pass

    def predict_batch(self, atoms_batch, **kwargs):
        self.calls.append(len(atoms_batch))
        results = []
        for atoms in atoms_batch:
            marker = float(atoms.positions[-1, 0])
            results.append(
                SimpleNamespace(
                    energy_ev=100.0 + marker,
                    forces_ev_per_angstrom=np.full((len(atoms), 3), marker - 0.7),
                    stress_ev_per_angstrom3=(
                        None if marker == self.stressless_marker else np.eye(3) * 0.01
                    ),
                )
            )
        return tuple(results)


def _prediction_policy(tmp_path: Path) -> ReplayFoundationPredictionPolicy:
    model = tmp_path / "foundation.model"
    model.write_bytes(b"g12a-foundation" * 8)
    potential = FoundationPotentialIdentity(
        reference=str(model),
        sha256=sha256_file_cached(model),
        foundation_head="default",
        model_family="mace_custom",
        model_atomic_numbers=(1,),
        available_heads=("default",),
        inspection_state="inspected",
    )
    inference = FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.16-test",
        adapter_version="g12a-test",
    )
    return ReplayFoundationPredictionPolicy(potential, inference, device="cpu")


def test_pseudolabel_views_canonicalize_masks_from_pseudo_payload_without_source_leak(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path)
    source = inspect_replay_source_extxyz(source_path)
    policy = _prediction_policy(tmp_path)
    # Pseudo stress is absent for a geometry whose *source* has stress, and
    # present for the geometry whose source lacks it.
    pseudo_stressless = _geometry(0)
    provider = _PseudoProvider(policy, stressless_marker=float(pseudo_stressless.positions[-1, 0]))
    cache = build_replay_foundation_prediction_cache(
        source, policy, tmp_path / "cache", provider=provider, batch_size=4, shard_size=4
    )
    qualification = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=10.0,
            force_component_rms_ev_per_angstrom=10.0,
            maximum_abs_stress_ev_per_angstrom3=10.0,
        ),
    )
    split = build_replay_split_manifest(
        source,
        eligible_geometry_identities=qualification.eligible_geometry_identities,
        qualification_authority_digest=qualification.content_digest,
        split_ratio=(1, 1),
        split_seed=5,
    )
    views = materialize_replay_pseudolabel_views(source, cache, qualification, split, tmp_path / "views")
    calls = list(provider.calls)

    rendered: dict[str, dict] = {}
    for role in (ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR):
        rendered.update(_assert_canonical_transport(views[role].path))
    assert set(rendered) == set(qualification.eligible_geometry_identities)
    assert rendered[canonical_replay_geometry_identity(pseudo_stressless)]["stress_present"] is False
    assert rendered[_stressless_identity()]["stress_present"] is True
    # Pseudo labels, not source truth, are rendered.
    assert all(frame["energy"] > 50.0 for frame in rendered.values())
    assert provider.calls == calls


def _write_labelled_split(path: Path, indices: tuple[int, ...], *, weights: dict | None) -> None:
    frames = []
    for index in indices:
        atoms = _geometry(index)
        atoms.info["REF_energy"] = 1.0 + index
        atoms.arrays["REF_forces"] = np.zeros((2, 3))
        if index != _STRESSLESS:
            atoms.info["REF_stress"] = np.zeros(6)
        atoms.info["replay_source_index"] = index
        if weights:
            atoms.info.update(weights)
        frames.append(atoms)
    write(path, frames, format="extxyz")


def test_legacy_true_label_rematerialization_canonicalizes_split_and_source_weights(tmp_path: Path):
    root = tmp_path / "replay-root"
    root.mkdir()
    _write_source(root / "mp_replay_selected.extxyz")
    _write_labelled_split(tmp_path / "train.extxyz", (0, 1, 2, 3), weights=_CONTAMINATION)
    _write_labelled_split(tmp_path / "monitor.extxyz", (4, 5), weights=_CONTAMINATION)

    resolution = resolve_true_label_replay_directory(
        root,
        replay_train_path=tmp_path / "train.extxyz",
        replay_monitor_path=tmp_path / "monitor.extxyz",
        output_directory=tmp_path / "out",
        require_train=True,
    )
    assert resolution.materialized is True
    train = _assert_canonical_transport(resolution.train_path)
    _assert_canonical_transport(resolution.monitor_path)
    assert train[_stressless_identity()]["stress_present"] is False
    assert resolution.train_artifact.label_mode is ReplayLabelMode.TRUE_DFT


def test_pre_repair_legacy_rematerialization_receipt_is_not_reused(tmp_path: Path):
    import json

    root = tmp_path / "replay-root"
    root.mkdir()
    _write_source(root / "mp_replay_selected.extxyz")
    _write_labelled_split(tmp_path / "monitor.extxyz", (4, 5), weights=None)
    kwargs = dict(
        replay_train_path=None,
        replay_monitor_path=tmp_path / "monitor.extxyz",
        output_directory=tmp_path / "out",
    )
    first = resolve_true_label_replay_directory(root, **kwargs)
    output = Path(first.monitor_path)
    provenance_path = output.with_name(output.name + ".provenance.json")
    # Seed a pre-repair output: inherited weights plus a v1 provenance receipt
    # that authenticates exactly those bytes.
    frames = list(iread(output, index=":", format="extxyz"))
    for atoms in frames:
        atoms.info["config_forces_weight"] = 2.5
    write(output, frames, format="extxyz")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance.update(
        schema="mdstats.true-label-replay-materialization.v1",
        output_sha256=sha256_file_cached(output),
    )
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    again = resolve_true_label_replay_directory(root, **kwargs)
    _assert_canonical_transport(again.monitor_path)


@pytest.mark.parametrize(
    "weights",
    [
        {"config_weight": 4.0},
        {"config_energy_weight": 0.3},
        {"config_forces_weight": 2.5},
        {"config_stress_weight": 0.5},
        {"config_stress_weight": 0.0},
    ],
)
def test_direct_legacy_split_files_with_noncanonical_weights_fail_closed(tmp_path: Path, weights):
    _write_labelled_split(tmp_path / "train.extxyz", (0, 1, 2, 3), weights=weights)
    _write_labelled_split(tmp_path / "monitor.extxyz", (4, 5), weights=None)
    for mode in (ReplayMode.PRESELECTED, ReplayMode.EXTERNAL_TRUE_LABEL, ReplayMode.EXTERNAL_PSEUDOLABEL):
        with pytest.raises(TrainingDataInputError, match="neutral-binary-mask"):
            build_local_replay_plan(tmp_path / "train.extxyz", tmp_path / "monitor.extxyz", mode=mode)

    # Already-split TRUE_DFT candidates are consumed directly, so they fail too.
    root = tmp_path / "root"
    (root / "true_labels").mkdir(parents=True)
    _write_labelled_split(root / "true_labels" / "replay_train.extxyz", (0, 1, 2, 3), weights=weights)
    _write_labelled_split(root / "true_labels" / "replay_monitor.extxyz", (4, 5), weights=None)
    with pytest.raises(TrainingDataInputError, match="neutral-binary-mask"):
        resolve_true_label_replay_directory(
            root,
            replay_train_path=None,
            replay_monitor_path=root / "true_labels" / "replay_monitor.extxyz",
            output_directory=tmp_path / "out",
            require_train=False,
        )


def test_direct_split_files_whose_mace_resolved_weights_are_canonical_are_admitted(tmp_path: Path):
    # Absent keys resolve to MACE defaults; a stress weight on a stressless
    # frame resolves to zero because MACE masks absent properties.
    _write_labelled_split(tmp_path / "absent.extxyz", (0, 1, 2, 3), weights=None)
    _write_labelled_split(tmp_path / "explicit.extxyz", (4, 5), weights={"config_weight": 1.0, "config_energy_weight": 1.0})
    frames = list(iread(tmp_path / "absent.extxyz", index=":", format="extxyz"))
    frames[_STRESSLESS].info["config_stress_weight"] = 1.0
    write(tmp_path / "absent.extxyz", frames, format="extxyz")
    plan = build_local_replay_plan(
        tmp_path / "absent.extxyz", tmp_path / "explicit.extxyz", mode=ReplayMode.EXTERNAL_TRUE_LABEL
    )
    assert plan.train_artifact.stress_present_count == 3
