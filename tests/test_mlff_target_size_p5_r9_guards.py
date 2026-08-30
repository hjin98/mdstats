"""Direct owner and assembled guards for the reopened P5 revision-9 workplan."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._common import TrainingDataInputError, sha256_file_cached
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.campaign_post_selection_runtime import (
    PostSelectionReplayResolution,
    _resolve_post_selection_replay_resolution,
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.foundation import MaceFoundationInspection
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    compute_replay_lineage_digest,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from mdstats.training_data.replay import (
    ReplayLabelMode,
    canonical_replay_geometry_identity,
)
from mdstats.training_data.model_features import MaceCalculatorProvider
from tests._mlff_post_selection_fixture import (
    build_selected_campaign,
    fixture_config_text,
    load_context,
    rewrite_config,
)
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from tests._mlff_post_selection_fixture import PostSelectionHarness


def _write_replay_file(path: Path, indices: list[int], *, energy_offset: float) -> None:
    from ase import Atoms
    from ase.io import write

    frames = []
    for index in indices:
        atoms = Atoms(
            "LiO",
            positions=(
                (0.8 + 0.35 * index, 0.8, 0.8),
                (4.5, 4.5, 4.5),
            ),
            cell=np.eye(3) * 10.0,
            pbc=True,
        )
        atoms.info["REF_energy"] = -10.0 + energy_offset + 0.01 * index
        atoms.arrays["REF_forces"] = np.asarray(
            [[0.1 + 0.001 * index, 0.0, 0.0], [-0.1 - 0.001 * index, 0.0, 0.0]],
            dtype=np.float64,
        )
        frames.append(atoms)
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, frames, format="extxyz")


def _legacy_fixture(tmp_path: Path, *, mode: str) -> tuple[dict, cli.CampaignPaths, dict[str, Path]]:
    root = tmp_path / "legacy-replay"
    foundation = root / "foundation.model"
    foundation.parent.mkdir(parents=True, exist_ok=True)
    foundation.write_bytes(b"bounded-foundation-checkpoint")
    pseudo_train = root / "pseudo-train.extxyz"
    pseudo_monitor = root / "pseudo-monitor.extxyz"
    true_root = root / "true-replay"
    true_train = true_root / "true_labels" / "replay_train.extxyz"
    true_monitor = true_root / "true_labels" / "replay_monitor.extxyz"
    _write_replay_file(pseudo_train, [0, 1], energy_offset=0.25)
    _write_replay_file(pseudo_monitor, [2, 3], energy_offset=0.25)
    _write_replay_file(true_train, [0, 1], energy_offset=0.0)
    _write_replay_file(true_monitor, [2, 3], energy_offset=0.0)
    config_path = root / "campaign.toml"
    cfg = {
        "campaign": {"workspace": str(root / "workspace")},
        "paths": {
            "foundation_model": str(foundation),
            "replay_train": str(pseudo_train),
            "replay_monitor": str(pseudo_monitor),
            "replay_true_labels": str(true_root),
        },
        "foundation": {
            "family": "mace_mpa_0",
            "head": "default",
            "legacy_normalized": True,
        },
        "model": {"family": "mace_mpa_0"},
        "training": {"mode": "multihead_replay", "device": "cpu"},
        "replay": {"mode": mode},
        "acceleration": {"backend": "e3nn"},
    }
    config_path.write_text("", encoding="utf-8")
    paths = cli.CampaignPaths.from_config(config_path, cfg)
    paths.ensure()
    return cfg, paths, {
        "foundation": foundation,
        "pseudo_train": pseudo_train,
        "pseudo_monitor": pseudo_monitor,
        "true_train": true_train,
        "true_monitor": true_monitor,
    }


def _foundation_inspection(path: Path) -> MaceFoundationInspection:
    return MaceFoundationInspection(
        reference=str(path.resolve()),
        sha256=sha256_file_cached(path),
        model_class="ScaleShiftMACE",
        model_module="mace.modules.models",
        available_heads=("default",),
        atomic_numbers=(3, 8),
        r_max_angstrom=5.0,
        num_interactions=2,
        model_dtype="float64",
        atomic_energies_shape=(2,),
        interaction_signatures=(
            {"class": "RealAgnosticDensityResidualInteractionBlock"},
        ),
        product_signatures=({"class": "EquivariantProductBasisBlock"},),
        readout_signatures=({"class": "LinearReadoutBlock"},),
        edge_irreps="128x0e",
        use_agnostic_product=False,
        use_last_readout_only=False,
        state_shape_digest="55" * 32,
    )


def test_r9a_legacy_training_and_true_monitor_roles_are_real_owner_resolutions(
    tmp_path: Path, monkeypatch
):
    pseudo_cfg, pseudo_paths, files = _legacy_fixture(
        tmp_path / "pseudo", mode="external_pseudolabel"
    )
    true_cfg, true_paths, true_files = _legacy_fixture(
        tmp_path / "true", mode="external_true_label"
    )
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )

    pseudo_identity = resolve_post_selection_method_identity(pseudo_cfg)
    true_identity = resolve_post_selection_method_identity(true_cfg)
    assert pseudo_identity.content_digest != true_identity.content_digest

    pseudo_policies = resolve_post_selection_method_policies(pseudo_cfg)
    true_policies = resolve_post_selection_method_policies(true_cfg)
    assert pseudo_policies.replay_training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert true_policies.replay_training_label_mode is ReplayLabelMode.TRUE_DFT

    pseudo_context = SimpleNamespace(cfg=pseudo_cfg, paths=pseudo_paths)
    true_context = SimpleNamespace(cfg=true_cfg, paths=true_paths)
    pseudo_resolution = _resolve_post_selection_replay_resolution(pseudo_context)
    true_resolution = _resolve_post_selection_replay_resolution(true_context)
    assert isinstance(pseudo_resolution, PostSelectionReplayResolution)
    assert isinstance(true_resolution, PostSelectionReplayResolution)

    assert pseudo_resolution.train_artifact.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert pseudo_resolution.train_path == str(files["pseudo_train"].resolve())
    assert pseudo_resolution.monitor_artifact.label_mode is ReplayLabelMode.TRUE_DFT
    assert pseudo_resolution.monitor_path == str(files["true_monitor"].resolve())
    assert true_resolution.train_artifact.label_mode is ReplayLabelMode.TRUE_DFT
    assert true_resolution.train_path == str(true_files["true_train"].resolve())
    assert true_resolution.monitor_artifact.label_mode is ReplayLabelMode.TRUE_DFT
    assert true_resolution.monitor_path == str(true_files["true_monitor"].resolve())

    pseudo_lineage = compute_replay_lineage_digest(pseudo_resolution)
    true_lineage = compute_replay_lineage_digest(true_resolution)
    assert pseudo_lineage != true_lineage
    assert pseudo_lineage == compute_replay_lineage_digest(
        _resolve_post_selection_replay_resolution(pseudo_context)
    )


def test_r9a_mace_translation_uses_training_artifact_and_true_monitor_separately(
    tmp_path: Path, monkeypatch
):
    cfg, paths, files = _legacy_fixture(tmp_path, mode="external_pseudolabel")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    policies = resolve_post_selection_method_policies(cfg)
    method = resolve_post_selection_method_identity(cfg, policies=policies)
    resolution = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=cfg, paths=paths)
    )

    internal = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "r9a",
        "seed": 1,
        "target_train_file": "target-train.extxyz",
        "target_valid_file": "target-valid.extxyz",
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
        "multiheads_finetuning": True,
        "pt_train_file": resolution.train_path,
        "pt_valid_file": resolution.monitor_path,
        "heads": {
            POST_SELECTION_TARGET_HEAD_NAME: {},
            POST_SELECTION_REPLAY_HEAD_NAME: {},
        },
    }
    translated = post_selection_mace_run_configuration(internal)
    assert translated["pt_train_file"] == str(files["pseudo_train"].resolve())
    assert translated["pt_valid_file"] == str(files["true_monitor"].resolve())
    assert set(translated["heads"]) == {
        POST_SELECTION_TARGET_HEAD_NAME,
        POST_SELECTION_REPLAY_HEAD_NAME,
    }
    assert method.replay_exposure_policy_digest == resolve_post_selection_method_identity(
        cfg, policies=policies
    ).replay_exposure_policy_digest


def test_r9a_identity_and_lineage_are_path_free_and_mutations_are_detected(
    tmp_path: Path, monkeypatch
):
    cfg, paths, files = _legacy_fixture(tmp_path, mode="external_pseudolabel")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    original_resolution = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=cfg, paths=paths)
    )
    original_identity = resolve_post_selection_method_identity(cfg)
    original_lineage = compute_replay_lineage_digest(original_resolution)

    relocated_root = tmp_path / "relocated"
    relocated_root.mkdir()
    relocated_files = {}
    for key, source in files.items():
        destination = relocated_root / source.name
        if key == "true_train" or key == "true_monitor":
            destination = relocated_root / "true-replay" / "true_labels" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        relocated_files[key] = destination
    relocated_cfg = json.loads(json.dumps(cfg))
    relocated_cfg["paths"] = {
        "foundation_model": str(relocated_files["foundation"]),
        "replay_train": str(relocated_files["pseudo_train"]),
        "replay_monitor": str(relocated_files["pseudo_monitor"]),
        "replay_true_labels": str(relocated_root / "true-replay"),
    }
    relocated_path = relocated_root / "campaign.toml"
    relocated_path.write_text("", encoding="utf-8")
    relocated_paths = cli.CampaignPaths.from_config(relocated_path, relocated_cfg)
    relocated_paths.ensure()
    relocated_resolution = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=relocated_cfg, paths=relocated_paths)
    )
    assert resolve_post_selection_method_identity(relocated_cfg).content_digest == original_identity.content_digest
    assert compute_replay_lineage_digest(relocated_resolution) == original_lineage

    _write_replay_file(files["pseudo_train"], [0, 1], energy_offset=0.35)
    changed_resolution = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=cfg, paths=paths)
    )
    assert compute_replay_lineage_digest(changed_resolution) != original_lineage


def test_r9a_unsupported_legacy_mode_fails_before_replay_materialization(tmp_path: Path):
    cfg, _paths, _files = _legacy_fixture(tmp_path, mode="preselected")
    with pytest.raises((TrainingDataInputError, PostSelectionError)):
        resolve_post_selection_method_policies(cfg)


def test_r9b_head_namespace_is_one_owner_across_policy_and_mace_translation(
    tmp_path: Path, monkeypatch
):
    cfg, _paths, _files = _legacy_fixture(tmp_path, mode="external_true_label")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    omitted = resolve_post_selection_method_identity(cfg)
    explicit_cfg = json.loads(json.dumps(cfg))
    explicit_cfg["training"]["selected_head_name"] = POST_SELECTION_TARGET_HEAD_NAME
    explicit = resolve_post_selection_method_identity(explicit_cfg)
    assert omitted.content_digest == explicit.content_digest

    noncanonical = json.loads(json.dumps(cfg))
    noncanonical["training"]["selected_head_name"] = "custom-target"
    with pytest.raises(TrainingDataInputError):
        resolve_post_selection_method_policies(noncanonical)

    noncanonical_replay = json.loads(json.dumps(cfg))
    noncanonical_replay["training"]["replay_head_name"] = "custom-replay"
    with pytest.raises(TrainingDataInputError):
        resolve_post_selection_method_policies(noncanonical_replay)

    internal = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "r9b",
        "seed": 1,
        "target_train_file": "train.extxyz",
        "target_valid_file": "valid.extxyz",
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
        "multiheads_finetuning": True,
        "heads": {
            POST_SELECTION_TARGET_HEAD_NAME: {},
            POST_SELECTION_REPLAY_HEAD_NAME: {},
        },
    }
    translated = post_selection_mace_run_configuration(internal)
    assert set(translated["heads"]) == {
        POST_SELECTION_TARGET_HEAD_NAME,
        POST_SELECTION_REPLAY_HEAD_NAME,
    }


def _write_fake_train_wrapper(path: Path, marker: Path, pseudo_train: Path, true_monitor: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path.write_text(
        f"""#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import sys
import yaml

sys.path.insert(0, {str(repo_root)!r})

from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
    TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
    Train2RuntimePlan,
)
from tests._mlff_post_selection_fixture import train_like_mace
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--model_dir', required=True)
parser.add_argument('--checkpoints_dir', required=True)
parser.add_argument('--log_dir', required=True)
parser.add_argument('--results_dir', required=True)
args = parser.parse_args()
config_path = Path.cwd() / args.config
payload = yaml.safe_load(config_path.read_text(encoding='utf-8'))
if set(payload.get('heads', {{}})) != {{{POST_SELECTION_TARGET_HEAD_NAME!r}, {POST_SELECTION_REPLAY_HEAD_NAME!r}}}:
    raise RuntimeError('noncanonical MACE head map')
for key in ('train_file', 'valid_file', 'pt_train_file', 'pt_valid_file'):
    candidate = Path(payload[key])
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if not candidate.is_file():
        raise RuntimeError(f'missing {{key}}: {{candidate}}')
pseudo_train = Path({str(pseudo_train.resolve())!r})
true_monitor = Path({str(true_monitor.resolve())!r})
if Path(payload['pt_train_file']).resolve() != pseudo_train:
    raise RuntimeError('pseudolabel training artifact was replaced')
if Path(payload['pt_valid_file']).resolve() != true_monitor:
    raise RuntimeError('TRUE_DFT monitor was not carried to MACE')
if Path(os.environ[TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE]).resolve() != true_monitor:
    raise RuntimeError('runtime TRUE_DFT monitor path mismatch')
if 'PYTHONHASHSEED' not in os.environ or not os.environ['PYTHONHASHSEED']:
    raise RuntimeError('TRAIN2 environment is incomplete')
with Path({str(marker.resolve())!r}).open('a', encoding='utf-8') as handle:
    handle.write(json.dumps({{
        'cwd': str(Path.cwd()),
        'plan': json.loads(os.environ[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE]),
        'heads': sorted(payload['heads']),
        'pt_train_file': str(Path(payload['pt_train_file']).resolve()),
        'pt_valid_file': str(Path(payload['pt_valid_file']).resolve()),
    }}) + '\\n')
plan = Train2RuntimePlan.from_dict(json.loads(os.environ[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE]))
request = SimpleNamespace(
    plan=plan,
    run_plan=SimpleNamespace(optimizer_seed=int(payload['seed'])),
    checkpoint_directory=Path(args.checkpoints_dir),
    materialization_directory=Path.cwd(),
    start_epoch=0,
)
if train_like_mace(request) is None:
    raise RuntimeError('TRAIN2 runtime produced no canonical summary')
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_r9c_assembled_replay_enabled_non_scratch_real_owner_lifecycle(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "assembled"
    foundation = root / "foundation.model"
    pseudo_train = root / "replay-pseudo-train.extxyz"
    pseudo_monitor = root / "replay-pseudo-monitor.extxyz"
    true_root = root / "true-replay"
    true_train = true_root / "true_labels" / "replay_train.extxyz"
    true_monitor = true_root / "true_labels" / "replay_monitor.extxyz"
    foundation.parent.mkdir(parents=True, exist_ok=True)
    foundation.write_bytes(b"assembled-foundation-checkpoint")
    _write_replay_file(pseudo_train, [0, 1], energy_offset=0.25)
    _write_replay_file(pseudo_monitor, [2, 3], energy_offset=0.25)
    _write_replay_file(true_train, [0, 1], energy_offset=0.0)
    _write_replay_file(true_monitor, [2, 3], energy_offset=0.0)

    config_text = fixture_config_text()
    config_text = config_text.replace(
        'training_root = "{training_root}"',
        '\n'.join(
            (
                'training_root = "{training_root}"',
                f'foundation_model = "{foundation}"',
                f'replay_train = "{pseudo_train}"',
                f'replay_monitor = "{pseudo_monitor}"',
                f'replay_true_labels = "{true_root}"',
            )
        ),
    )
    config_text = config_text.replace(
        "seeds = [1, 2]",
        "seeds = [1, 2]\nmode = \"multihead_replay\"",
    )
    config_text += """

[replay]
mode = "external_pseudolabel"
seed = 42
allow_small_corpus = true
minimum_train_configurations = 1
minimum_monitor_configurations = 1
require_target_elements = false

[foundation]
family = "mace_mpa_0"
head = "default"
legacy_normalized = true
"""

    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    config, workspace = build_selected_campaign(tmp_path / "campaign", config_text=config_text)

    wrapper = tmp_path / "mdstats-mace-train"
    marker = tmp_path / "wrapper-runs.jsonl"
    _write_fake_train_wrapper(wrapper, marker, pseudo_train, true_monitor)
    monkeypatch.setattr(
        cli,
        "_ensure_local_wrappers",
        lambda _paths: {"mdstats-mace-train": wrapper},
    )
    # The baseline provider still goes through the canonical construction
    # function; only its expensive checkpoint-to-calculator numerical boundary
    # is replaced by an authenticated parameter-shell provider.
    import torch

    def fake_foundation_provider(cls, model_path, **kwargs):
        assert kwargs["head"] == "default"
        assert kwargs["foundation_potential_identity"].foundation_head == "default"
        return cls.from_authenticated_parameter_state(
            [torch.zeros(1, dtype=torch.float64)],
            checkpoint_locator=model_path,
            checkpoint_sha256=sha256_file_cached(model_path),
            device=kwargs["device"],
            default_dtype=kwargs["default_dtype"],
            allow_forward_override=True,
        )

    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_model_path",
        classmethod(fake_foundation_provider),
    )

    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(
            cfg,
            paths,
            store,
            inference_evaluator=PostSelectionHarness().evaluate,
        )
        assert context.method.training_mode == "multihead_replay"
        assert context.method_policies.replay_training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        assert context.method_policies.target_head_name == POST_SELECTION_TARGET_HEAD_NAME
        assert context.method_policies.replay_head_name == POST_SELECTION_REPLAY_HEAD_NAME
    finally:
        store.close()

    class RecordingHarness(PostSelectionHarness):
        def __init__(self):
            super().__init__()
            self.geometry_signatures = []

        def evaluate(self, provider, atoms_list):
            self.geometry_signatures.append(
                tuple(canonical_replay_geometry_identity(atoms) for atoms in atoms_list)
            )
            return super().evaluate(provider, atoms_list)

    evaluator = RecordingHarness()
    assert p4d._run(
        config,
        "cross-validate",
        _external_inference_evaluator=evaluator.evaluate,
    ) == 0

    # Changing only the legacy replay training semantic makes the accepted CV
    # lineage/method stale before a wrapper can launch.
    rewrite_config(config, 'mode = "external_pseudolabel"', 'mode = "external_true_label"')
    before_failed_run_count = 0 if not marker.exists() else len(marker.read_text(encoding="utf-8").splitlines())
    with pytest.raises(Exception) as switched:
        p4d._run(
            config,
            "train-production",
            _external_inference_evaluator=evaluator.evaluate,
        )
    assert "replay" in str(switched.value).lower() or "current" in str(switched.value).lower()
    after_failed_run_count = 0 if not marker.exists() else len(marker.read_text(encoding="utf-8").splitlines())
    assert after_failed_run_count == before_failed_run_count

    rewrite_config(config, 'mode = "external_true_label"', 'mode = "external_pseudolabel"')
    assert p4d._run(
        config,
        "train-production",
        _external_inference_evaluator=evaluator.evaluate,
    ) == 0

    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(
            cfg,
            paths,
            store,
            inference_evaluator=evaluator.evaluate,
        )
        assert context.trainer.__class__.__name__ == "MacePostSelectionTrainer"
        cv_plan = resolve_current_cv_plan(context)
        cv_acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        assert cv_plan is not None and cv_acceptance is not None and cv_acceptance.accepted
        assert final_plan is not None
        resolution = _resolve_post_selection_replay_resolution(context)
        assert resolution.training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        assert resolution.train_path == str(pseudo_train.resolve())
        assert resolution.monitor_path == str(true_monitor.resolve())
        assert final_plan.replay_lineage_digest == compute_replay_lineage_digest(resolution)
        assert final_plan.method_identity_digest == context.method.content_digest
        assert final_plan.n_selected == context.selected.n_selected
        assert final_plan.target_membership_digest == context.selected.selected_membership_digest
        assert final_plan.planned_epochs == 3
    finally:
        store.close()

    records = [json.loads(line) for line in marker.read_text(encoding="utf-8").splitlines()]
    assert records
    assert all(set(item["heads"]) == {POST_SELECTION_TARGET_HEAD_NAME, POST_SELECTION_REPLAY_HEAD_NAME} for item in records)
    assert all(item["pt_train_file"] == str(pseudo_train.resolve()) for item in records)
    assert all(item["pt_valid_file"] == str(true_monitor.resolve()) for item in records)
    from ase.io import read

    true_monitor_signature = tuple(
        canonical_replay_geometry_identity(atoms)
        for atoms in read(true_monitor, index=":", format="extxyz")
    )
    assert sum(
        signature == true_monitor_signature
        for signature in evaluator.geometry_signatures
    ) >= 2
    assert workspace.is_dir()
