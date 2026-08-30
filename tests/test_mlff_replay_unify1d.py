from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tomllib

import numpy as np
import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as campaign_core
from mdstats.training_data._common import sha256_file_cached
from mdstats.training_data.foundation import FoundationInferenceIdentity, FoundationPotentialIdentity


def _write_source(path: Path, count: int = 12) -> None:
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
    write(path, frames, format="extxyz")


def _write_config(tmp_path: Path, source: Path, *, label_mode: str) -> tuple[dict, campaign_cli.CampaignPaths]:
    training = tmp_path / "training"
    training.mkdir(exist_ok=True)
    model = tmp_path / "foundation.model"
    model.write_bytes(b"foundation-fixture")
    text = campaign_cli._config_template(
        workspace=str(tmp_path / "work"),
        training_root=str(training),
        foundation_model=str(model),
        replay_set=str(source),
        foundation_family="mace_mpa_0",
        foundation_head="default",
        training_acceleration_backend="e3nn",
        default_device="cpu",
    )
    text = text.replace('label_mode = "foundation_pseudolabel"', f'label_mode = "{label_mode}"')
    config = tmp_path / "campaign.toml"
    config.write_text(text, encoding="utf-8")
    return campaign_cli._load_config(config)


def test_generated_config_exposes_only_single_replay_source(tmp_path: Path):
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_set="replay_fps_12000.extxyz",
    )
    cfg = tomllib.loads(text)
    assert cfg["paths"]["replay_set"] == "replay_fps_12000.extxyz"
    assert "replay_train" not in cfg["paths"]
    assert "replay_monitor" not in cfg["paths"]
    assert "replay_true_labels" not in cfg["paths"]
    assert cfg["replay"]["label_mode"] == "foundation_pseudolabel"
    assert cfg["replay"]["split_ratio"] == "5:1"
    assert cfg["replay"]["split_seed"] == 42


def test_true_label_single_source_builds_internal_10k_style_split_and_persists_authority(tmp_path: Path):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _write_config(tmp_path, source_path, label_mode="true_dft")

    plan = campaign_cli._build_replay_plan(cfg, paths)
    assert plan.mode is mdstats.ReplayMode.EXTERNAL_TRUE_LABEL
    assert plan.train_count == 10
    assert plan.monitor_count == 2
    assert Path(plan.train_artifact.path).parent.name == "views"
    assert Path(plan.monitor_artifact.path).parent.name == "views"
    assert Path(plan.train_artifact.path).resolve() != source_path.resolve()
    assert set(plan.train_artifact.geometry_identities).isdisjoint(plan.monitor_artifact.geometry_identities)

    resolution = campaign_cli._resolve_true_label_replay_inputs(cfg, paths, require_train=True)
    assert resolution is not None
    assert resolution.train_artifact.configuration_count == 10
    assert resolution.monitor_artifact.configuration_count == 2
    assert resolution.source_path == str(source_path.resolve())

    store = campaign_cli.CampaignStore(paths.state_db)
    campaign_cli._persist_single_source_replay_authority(store, cfg, paths)
    assert store.has_record("replay_single_source_config")
    assert store.has_record("replay_source")
    assert store.has_record("replay_true_label_cache")
    assert store.has_record("replay_split_manifest")
    restored = store.get_record("replay_split_manifest", mdstats.ReplaySplitManifest)
    assert restored.train_count == 10
    assert restored.monitor_count == 2


class _FakeProvider:
    def __init__(self, policy):
        self.policy = policy
        self.calls: list[int] = []
        self.checkpoint_identity = SimpleNamespace(
            checkpoint_sha256=policy.foundation_potential.sha256,
            default_dtype=policy.foundation_inference.default_dtype,
            foundation_potential_digest=policy.foundation_potential.canonical_content_digest,
            foundation_inference_digest=policy.foundation_inference.content_digest,
            foundation_head=policy.foundation_potential.foundation_head,
        )

    def set_head(self, head: str) -> None:
        assert head == "default"

    def predict_batch(self, atoms_batch, **kwargs):
        self.calls.append(len(atoms_batch))
        results = []
        for atoms in atoms_batch:
            marker = float(atoms.positions[-1, 2])
            scale = marker - 0.69
            results.append(SimpleNamespace(
                energy_ev=-float(len(atoms)) - marker,
                forces_ev_per_angstrom=np.full((len(atoms), 3), scale, dtype=np.float64),
                stress_ev_per_angstrom3=np.eye(3, dtype=np.float64) * scale * 0.1,
            ))
        return tuple(results)


def test_pseudolabel_single_source_materializes_training_views_and_independent_true_monitor(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _write_config(tmp_path, source_path, label_mode="foundation_pseudolabel")
    model_path = Path(cfg["paths"]["foundation_model"]).resolve()
    potential = FoundationPotentialIdentity(
        reference=str(model_path),
        sha256=sha256_file_cached(model_path),
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
        mace_version="test",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    realization = SimpleNamespace(
        resolved_kernel_mode="e3nn",
        foundation_inference_identity_digest=inference.content_digest,
    )
    monkeypatch.setattr(campaign_core, "_resolved_foundation_potential_identity", lambda cfg, paths: potential)
    monkeypatch.setattr(campaign_core, "_stored_acceleration_realization", lambda cfg, paths, require_qualified=False: realization)
    monkeypatch.setattr(campaign_core, "_foundation_inference_identity", lambda cfg, potential_arg, **kwargs: inference)

    original_builder = mdstats.build_replay_foundation_prediction_cache
    providers: list[_FakeProvider] = []

    def build_with_fake(source, policy, cache_root, **kwargs):
        provider = _FakeProvider(policy)
        providers.append(provider)
        return original_builder(source, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_fake)
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    plan = campaign_cli._build_replay_plan(cfg, paths)
    assert plan.mode is mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL
    assert plan.train_count == 10
    assert plan.monitor_count == 2
    assert plan.train_artifact.label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert plan.monitor_artifact.foundation_label_generator_identity_digest == inference.content_digest
    assert providers and sum(providers[0].calls) == 12

    true_resolution = campaign_cli._resolve_true_label_replay_inputs(cfg, paths, require_train=False)
    assert true_resolution is not None
    assert true_resolution.train_artifact is None
    assert true_resolution.monitor_artifact.label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert true_resolution.monitor_artifact.configuration_count == 2
    assert true_resolution.monitor_artifact.geometry_identities == plan.monitor_artifact.geometry_identities

    store = campaign_cli.CampaignStore(paths.state_db)
    campaign_cli._persist_single_source_replay_authority(store, cfg, paths)
    for key in (
        "replay_single_source_config",
        "replay_source",
        "replay_true_label_cache",
        "replay_foundation_prediction_policy",
        "replay_foundation_prediction_cache",
        "replay_pseudolabel_qualification",
        "replay_split_manifest",
        "replay_pseudolabel_train_view",
        "replay_pseudolabel_monitor_view",
        "replay_true_monitor_view",
    ):
        assert store.has_record(key), key


def test_new_and_legacy_replay_interfaces_cannot_be_mixed(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    source.touch()
    cfg = {
        "paths": {"replay_set": str(source), "replay_train": "old.extxyz"},
        "replay": {"label_mode": "true_dft"},
    }
    with pytest.raises(mdstats.TrainingDataInputError, match="cannot be combined"):
        mdstats.single_source_replay_config_from_campaign(cfg)


def test_single_source_inspection_receipt_avoids_extxyz_reparse_across_process_style_restart(tmp_path: Path, monkeypatch):
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _write_config(tmp_path, source_path, label_mode="true_dft")

    original = mdstats.inspect_replay_source_extxyz
    calls = {"count": 0}

    def counted(path):
        calls["count"] += 1
        return original(path)

    monkeypatch.setattr(mdstats, "inspect_replay_source_extxyz", counted)
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    first = campaign_cli._build_replay_plan(cfg, paths)
    assert first.train_count == 10
    assert calls["count"] == 1

    # Simulate a new command process: discard only the in-memory context.  The
    # persisted source receipt and materialized transport views remain.
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    second = campaign_cli._build_replay_plan(cfg, paths)
    assert second.train_count == 10
    assert second.monitor_count == 2
    assert calls["count"] == 1
