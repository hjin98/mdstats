from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data._common import TrainingDataInputError, sha256_file_cached
from mdstats.training_data.foundation import FoundationInferenceIdentity, FoundationPotentialIdentity
from mdstats.training_data.replay import (
    ReplaySplitRole,
    build_replay_split_manifest,
    canonical_replay_geometry_identity,
    inspect_replay_source_extxyz,
)
from mdstats.training_data.replay_pseudolabel import (
    REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA,
    REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA,
    REPLAY_PSEUDOLABEL_VIEW_SCHEMA,
    ReplayFoundationPredictionCache,
    ReplayFoundationPredictionPolicy,
    ReplayPseudolabelQualification,
    ReplayPseudolabelQualificationPolicy,
    ReplayPseudolabelViewArtifact,
    build_replay_foundation_prediction_cache,
    build_replay_pseudolabel_qualification,
    materialize_replay_pseudolabel_views,
)


def _write_source(path: Path, count: int = 12, *, reverse: bool = False) -> None:
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    frames = []
    for index in range(count):
        atoms = Atoms(
            "H2",
            positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.70 + 0.01 * index]],
            cell=[5.0, 5.0, 5.0],
            pbc=True,
        )
        atoms.calc = SinglePointCalculator(
            atoms,
            energy=-10.0 - index,
            forces=np.full((2, 3), 0.02 * (index + 1), dtype=np.float64),
            stress=np.eye(3, dtype=np.float64) * 0.001 * (index + 1),
        )
        frames.append(atoms)
    if reverse:
        frames.reverse()
    write(path, frames, format="extxyz")


def _prediction_policy(tmp_path: Path, *, model_tag: str = "model-a", device: str = "cpu") -> ReplayFoundationPredictionPolicy:
    model = tmp_path / f"{model_tag}.model"
    model.write_bytes((model_tag * 17).encode("ascii"))
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
        adapter_version="replay-unify1c-test",
    )
    return ReplayFoundationPredictionPolicy(potential, inference, device=device)


class _FakeProvider:
    def __init__(self, policy: ReplayFoundationPredictionPolicy, *, max_batch: int | None = None, no_stress: bool = False):
        self.policy = policy
        self.max_batch = max_batch
        self.no_stress = no_stress
        self.calls: list[int] = []
        self.heads: list[str] = []
        self.checkpoint_identity = SimpleNamespace(
            checkpoint_sha256=policy.foundation_potential.sha256,
            default_dtype=policy.foundation_inference.default_dtype,
            foundation_potential_digest=policy.foundation_potential.canonical_content_digest,
            foundation_inference_digest=policy.foundation_inference.content_digest,
            foundation_head=policy.foundation_potential.foundation_head,
        )

    def set_head(self, head: str) -> None:
        self.heads.append(head)

    def predict_batch(self, atoms_batch, **kwargs):
        self.calls.append(len(atoms_batch))
        if self.max_batch is not None and len(atoms_batch) > self.max_batch:
            raise RuntimeError("CUDA out of memory: synthetic backoff fixture")
        result = []
        for atoms in atoms_batch:
            marker = float(atoms.positions[-1, 2])
            scale = marker - 0.69
            forces = np.full((len(atoms), 3), scale, dtype=np.float64)
            stress = None if self.no_stress else np.eye(3, dtype=np.float64) * scale * 0.1
            result.append(
                SimpleNamespace(
                    energy_ev=-float(len(atoms)) - marker,
                    forces_ev_per_angstrom=forces,
                    stress_ev_per_angstrom3=stress,
                )
            )
        return tuple(result)


def test_prediction_cache_is_batched_content_authenticated_and_restart_reusable(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    source = inspect_replay_source_extxyz(source_path)
    policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(policy)

    cache = build_replay_foundation_prediction_cache(
        source,
        policy,
        tmp_path / "cache",
        provider=provider,
        batch_size=4,
        shard_size=5,
    )
    assert cache.serialization_schema == REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA
    assert cache.configuration_count == 12
    assert provider.calls == [4, 4, 4]
    assert provider.heads == ["default"]
    assert len(cache.shards) == 3
    assert ReplayFoundationPredictionCache.from_dict(cache.to_dict()).content_digest == cache.content_digest

    forbidden = _FakeProvider(policy)
    def fail(*args, **kwargs):
        raise AssertionError("prediction cache hit must not invoke provider")
    forbidden.predict_batch = fail
    source_path.rename(tmp_path / "replay-relocated.extxyz")
    hit = build_replay_foundation_prediction_cache(
        source,
        policy,
        tmp_path / "cache",
        provider=forbidden,
        batch_size=1,
        shard_size=1,
    )
    assert hit.content_digest == cache.content_digest
    assert forbidden.heads == []


def test_prediction_logical_cache_identity_is_source_order_independent(tmp_path: Path):
    first_path = tmp_path / "first.extxyz"
    second_path = tmp_path / "second.extxyz"
    _write_source(first_path, 9)
    _write_source(second_path, 9, reverse=True)
    first = inspect_replay_source_extxyz(first_path)
    second = inspect_replay_source_extxyz(second_path)
    assert first.geometry_set_digest == second.geometry_set_digest
    assert first.source_index_digest != second.source_index_digest
    policy = _prediction_policy(tmp_path)

    cache_a = build_replay_foundation_prediction_cache(
        first, policy, tmp_path / "cache-a", provider=_FakeProvider(policy), batch_size=4, shard_size=3
    )
    cache_b = build_replay_foundation_prediction_cache(
        second, policy, tmp_path / "cache-b", provider=_FakeProvider(policy), batch_size=2, shard_size=4
    )
    assert cache_a.content_digest == cache_b.content_digest
    assert cache_a.prediction_mapping_digest == cache_b.prediction_mapping_digest
    assert cache_a.audit_mapping_digest == cache_b.audit_mapping_digest
    assert cache_a.storage_manifest_digest != cache_b.storage_manifest_digest


def test_oom_backoff_preserves_prediction_authority(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 7)
    source = inspect_replay_source_extxyz(source_path)
    policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(policy, max_batch=2)
    cache = build_replay_foundation_prediction_cache(
        source, policy, tmp_path / "cache", provider=provider, batch_size=5, shard_size=3
    )
    assert cache.configuration_count == 7
    assert 5 in provider.calls
    assert all(value <= 2 for value in provider.calls if value != 5 and value != 3)


def test_threshold_only_reclassification_reuses_prediction_cache_without_inference(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    source = inspect_replay_source_extxyz(source_path)
    prediction_policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(prediction_policy)
    cache = build_replay_foundation_prediction_cache(
        source, prediction_policy, tmp_path / "cache", provider=provider, batch_size=6, shard_size=4
    )
    calls = list(provider.calls)

    permissive = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=10.0,
            force_component_rms_ev_per_angstrom=10.0,
            maximum_abs_stress_ev_per_angstrom3=10.0,
        ),
    )
    strict = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=0.12,
            force_component_rms_ev_per_angstrom=0.08,
            maximum_abs_stress_ev_per_angstrom3=10.0,
        ),
    )
    assert permissive.serialization_schema == REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA
    assert permissive.eligible_count == 12
    assert strict.rejected_count > 0
    assert strict.prediction_cache_digest == permissive.prediction_cache_digest == cache.content_digest
    assert strict.audit_mapping_digest == permissive.audit_mapping_digest == cache.audit_mapping_digest
    assert provider.calls == calls
    assert ReplayPseudolabelQualification.from_dict(strict.to_dict()) == strict


def test_require_stress_reclassifies_missing_stress_without_reinference(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 6)
    source = inspect_replay_source_extxyz(source_path)
    prediction_policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(prediction_policy, no_stress=True)
    cache = build_replay_foundation_prediction_cache(
        source, prediction_policy, tmp_path / "cache", provider=provider, batch_size=3
    )
    calls = list(provider.calls)
    relaxed = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=None,
            force_component_rms_ev_per_angstrom=None,
            maximum_abs_stress_ev_per_angstrom3=None,
            require_stress=False,
        ),
    )
    strict = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=None,
            force_component_rms_ev_per_angstrom=None,
            maximum_abs_stress_ev_per_angstrom3=None,
            require_stress=True,
        ),
    )
    assert relaxed.eligible_count == 6
    assert strict.eligible_count == 0
    assert strict.reason_counts == {"missing_stress": 6}
    assert provider.calls == calls


def test_pseudolabel_materialization_is_lazy_qualification_bound_and_preserves_source_truth_namespace(tmp_path: Path):
    pytest.importorskip("ase")
    from ase.io import iread

    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    source = inspect_replay_source_extxyz(source_path)
    prediction_policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(prediction_policy)
    cache = build_replay_foundation_prediction_cache(
        source, prediction_policy, tmp_path / "cache", provider=provider, batch_size=4, shard_size=4
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
        split_ratio=(5, 1),
        split_seed=42,
    )
    output = tmp_path / "views"
    view = materialize_replay_pseudolabel_views(
        source, cache, qualification, split, output, roles=(ReplaySplitRole.MONITOR,), buffer_size=2
    )[ReplaySplitRole.MONITOR]
    assert view.serialization_schema == REPLAY_PSEUDOLABEL_VIEW_SCHEMA
    assert view.configuration_count == 2
    assert ReplayPseudolabelViewArtifact.from_dict(view.to_dict()) == view
    assert not (output / "replay_train.pseudolabel.extxyz").exists()

    source_truth = {g: l for g, l in zip(source.geometry_identities, source.source_label_identities, strict=True)}
    seen = set()
    for atoms in iread(view.path, index=":", format="extxyz"):
        identity = canonical_replay_geometry_identity(atoms)
        seen.add(identity)
        assert source_truth[identity] is not None
        assert atoms.info["replay_label_mode"] == "foundation_pseudolabel"
        assert atoms.info["replay_label_namespace"] == "foundation_pseudolabel"
        assert atoms.info["replay_pseudolabel_model_sha256"] == prediction_policy.foundation_potential.sha256
        assert atoms.info["replay_pseudolabel_foundation_head"] == "default"
        assert atoms.info["replay_pseudolabel_cache_digest"] == cache.content_digest
        assert atoms.info["replay_pseudolabel_qualification_digest"] == qualification.content_digest
        assert np.asarray(atoms.arrays["REF_forces"]).shape == (2, 3)
    assert seen == set(split.monitor_geometry_identities)

    # A transport cache hit must not open the source or invoke the model.
    source_path.rename(tmp_path / "source-hidden.extxyz")
    again = materialize_replay_pseudolabel_views(
        source, cache, qualification, split, output, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]
    assert again == view
    assert provider.calls == [4, 4, 4]


def test_deleted_pseudolabel_view_reconstructs_from_prediction_cache_without_reinference(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 8)
    source = inspect_replay_source_extxyz(source_path)
    prediction_policy = _prediction_policy(tmp_path)
    provider = _FakeProvider(prediction_policy)
    cache = build_replay_foundation_prediction_cache(
        source, prediction_policy, tmp_path / "cache", provider=provider, batch_size=4
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
    )
    output = tmp_path / "views"
    first = materialize_replay_pseudolabel_views(
        source, cache, qualification, split, output, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]
    calls = list(provider.calls)
    Path(first.path).unlink()
    rebuilt = materialize_replay_pseudolabel_views(
        source, cache, qualification, split, output, roles=(ReplaySplitRole.MONITOR,)
    )[ReplaySplitRole.MONITOR]
    assert rebuilt.logical_digest == first.logical_digest
    assert provider.calls == calls


def test_materialization_rejects_unbound_or_stale_qualification_split(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 8)
    source = inspect_replay_source_extxyz(source_path)
    prediction_policy = _prediction_policy(tmp_path)
    cache = build_replay_foundation_prediction_cache(
        source, prediction_policy, tmp_path / "cache", provider=_FakeProvider(prediction_policy)
    )
    qualification = build_replay_pseudolabel_qualification(
        cache,
        ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=10.0,
            force_component_rms_ev_per_angstrom=10.0,
            maximum_abs_stress_ev_per_angstrom3=10.0,
        ),
    )
    unbound = build_replay_split_manifest(source)
    with pytest.raises(TrainingDataInputError, match="not bound"):
        materialize_replay_pseudolabel_views(source, cache, qualification, unbound, tmp_path / "bad")


def test_audit_and_prediction_transport_tamper_fail_closed_at_their_use_boundaries(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 6)
    source = inspect_replay_source_extxyz(source_path)
    policy = _prediction_policy(tmp_path)
    cache = build_replay_foundation_prediction_cache(
        source, policy, tmp_path / "cache", provider=_FakeProvider(policy), shard_size=2
    )

    # Threshold-only reclassification authenticates only the compact audit
    # sidecar; it does not touch ragged prediction payloads.
    audit_path = Path(cache.root_directory) / cache.audit_relative_path
    original_audit = audit_path.read_bytes()
    audit_path.write_bytes(original_audit + b"tamper")
    with pytest.raises(TrainingDataInputError, match="audit cache is missing or changed"):
        build_replay_pseudolabel_qualification(cache)
    audit_path.write_bytes(original_audit)

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
    )
    shard_path = Path(cache.root_directory) / cache.shards[0].relative_path
    shard_path.write_bytes(shard_path.read_bytes() + b"tamper")
    with pytest.raises(TrainingDataInputError, match="prediction shard is missing or changed"):
        materialize_replay_pseudolabel_views(source, cache, qualification, split, tmp_path / "views")


def test_foundation_model_identity_change_uses_distinct_cache_authority(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 6)
    source = inspect_replay_source_extxyz(source_path)
    first_policy = _prediction_policy(tmp_path, model_tag="first")
    second_policy = _prediction_policy(tmp_path, model_tag="second")
    first = build_replay_foundation_prediction_cache(
        source, first_policy, tmp_path / "cache", provider=_FakeProvider(first_policy)
    )
    second_provider = _FakeProvider(second_policy)
    second = build_replay_foundation_prediction_cache(
        source, second_policy, tmp_path / "cache", provider=second_provider
    )
    assert first.cache_key != second.cache_key
    assert first.prediction_policy.content_digest != second.prediction_policy.content_digest
    assert second_provider.calls

def test_default_provider_construction_binds_foundation_head_dtype_device_and_kernel(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 4)
    source = inspect_replay_source_extxyz(source_path)
    model = tmp_path / "cueq.model"
    model.write_bytes(b"cueq-model")
    potential = FoundationPotentialIdentity(
        reference=str(model),
        sha256=sha256_file_cached(model),
        foundation_head="omat_pbe",
        model_family="mace_custom",
        model_atomic_numbers=(1,),
        available_heads=("default", "omat_pbe"),
        inspection_state="inspected",
    )
    inference = FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="cueq",
        resolved_kernel_mode="cueq_pure",
        mace_version="0.3.16-test",
        adapter_version="replay-unify1c-test",
    )
    policy = ReplayFoundationPredictionPolicy(potential, inference, device="cuda")
    captured = {}

    class Provider(_FakeProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            for atoms in atoms_batch:
                assert atoms.calc is None
                assert "REF_energy" not in atoms.info
                assert "energy" not in atoms.info
                assert "REF_forces" not in atoms.arrays
                assert "forces" not in atoms.arrays
            return super().predict_batch(atoms_batch, **kwargs)

    provider = Provider(policy)

    def fake_from_model_path(model_path, **kwargs):
        captured["model_path"] = str(model_path)
        captured.update(kwargs)
        return provider

    import mdstats.training_data.model_features as model_features
    monkeypatch.setattr(model_features.MaceCalculatorProvider, "from_model_path", staticmethod(fake_from_model_path))
    cache = build_replay_foundation_prediction_cache(
        source,
        policy,
        tmp_path / "cache",
        batch_size=2,
        shard_size=2,
    )
    assert cache.configuration_count == 4
    assert captured["model_path"] == str(model)
    assert captured["device"] == "cuda"
    assert captured["default_dtype"] == "float32"
    assert captured["enable_cueq"] is True
    assert captured["enable_oeq"] is False
    assert captured["foundation_potential_identity"] == potential
    assert captured["foundation_inference_identity"] == inference
    assert captured["requested_atomic_numbers"] == source.atomic_numbers
    assert provider.heads == ["omat_pbe"]
