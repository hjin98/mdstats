"""Revision-10 owner guards for P5 lineage, mode parity, and providers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    sha256_file_cached,
)
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.foundation import MaceFoundationInspection
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    PostSelectionExecutionError,
    _post_selection_mace_config,
    build_post_selection_foundation_baseline_provider,
    post_selection_mace_run_configuration,
    post_selection_runtime_plan,
)
from mdstats.training_data.post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    compute_replay_lineage_digest,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from mdstats.training_data.replay import ReplayLabelMode
from mdstats.training_data.train2_policy import TrainingBudgetPolicy


def _complete_lineage(
    *,
    interface: str = "single_source",
    source_content_digest: str | None = "aa" * 32,
    source_sha256: str | None = "bb" * 32,
    split_manifest_digest: str | None = "cc" * 32,
    training_label_mode: object = ReplayLabelMode.TRUE_DFT,
    true_label_mode: object = ReplayLabelMode.TRUE_DFT,
    train_sha256: str = "dd" * 32,
    train_content_digest: str | None = "ee" * 32,
    train_label_mode: object = ReplayLabelMode.TRUE_DFT,
    monitor_sha256: str = "ff" * 32,
    monitor_content_digest: str | None = "11" * 32,
    monitor_label_mode: object = ReplayLabelMode.TRUE_DFT,
) -> SimpleNamespace:
    return SimpleNamespace(
        interface=interface,
        source_path="/old/location/source.extxyz",
        train_path="/old/location/train.extxyz",
        monitor_path="/old/location/monitor.extxyz",
        source_content_digest=source_content_digest,
        source_sha256=source_sha256,
        split_manifest_digest=split_manifest_digest,
        training_label_mode=training_label_mode,
        true_label_mode=true_label_mode,
        train_artifact=SimpleNamespace(
            sha256=train_sha256,
            content_digest=train_content_digest,
            label_mode=train_label_mode,
        ),
        monitor_artifact=SimpleNamespace(
            sha256=monitor_sha256,
            content_digest=monitor_content_digest,
            label_mode=monitor_label_mode,
        ),
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda item: delattr(item, "interface"),
        lambda item: setattr(item, "interface", "inferred"),
        lambda item: delattr(item, "training_label_mode"),
        lambda item: setattr(item.train_artifact, "sha256", None),
        lambda item: setattr(item.train_artifact, "content_digest", None),
        lambda item: setattr(item.monitor_artifact, "sha256", None),
        lambda item: setattr(item.monitor_artifact, "content_digest", None),
        lambda item: setattr(item, "source_content_digest", None),
        lambda item: setattr(item, "source_sha256", None),
        lambda item: setattr(item, "split_manifest_digest", None),
        lambda item: setattr(
            item.train_artifact,
            "label_mode",
            ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        ),
        lambda item: setattr(
            item.monitor_artifact,
            "label_mode",
            ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        ),
        lambda item: setattr(item, "true_label_mode", ReplayLabelMode.FOUNDATION_PSEUDOLABEL),
    ),
)
def test_r10a_replay_lineage_incomplete_or_inconsistent_state_fails_closed(mutation):
    resolution = _complete_lineage()
    mutation(resolution)
    with pytest.raises((PostSelectionError, TrainingDataInputError)):
        compute_replay_lineage_digest(resolution)


def test_r10a_replay_lineage_legacy_and_single_source_are_path_free():
    single = _complete_lineage()
    relocated = _complete_lineage()
    relocated.source_path = "/new/location/source.extxyz"
    relocated.train_path = "/new/location/train.extxyz"
    relocated.monitor_path = "/new/location/monitor.extxyz"
    assert compute_replay_lineage_digest(single) == compute_replay_lineage_digest(relocated)

    legacy = _complete_lineage(
        interface="legacy_split",
        source_content_digest=None,
        source_sha256=None,
        split_manifest_digest=None,
    )
    legacy.true_label_source_sha256 = "22" * 32
    legacy_relocated = _complete_lineage(
        interface="legacy_split",
        source_content_digest=None,
        source_sha256=None,
        split_manifest_digest=None,
    )
    legacy_relocated.true_label_source_sha256 = "22" * 32
    legacy_relocated.train_path = "/new/location/train.extxyz"
    legacy_relocated.monitor_path = "/new/location/monitor.extxyz"
    assert compute_replay_lineage_digest(legacy) == compute_replay_lineage_digest(
        legacy_relocated
    )
    changed_source = _complete_lineage(source_content_digest="12" * 32)
    assert compute_replay_lineage_digest(single) != compute_replay_lineage_digest(
        changed_source
    )
    changed_train = _complete_lineage(train_content_digest="23" * 32)
    assert compute_replay_lineage_digest(single) != compute_replay_lineage_digest(
        changed_train
    )
    changed_monitor = _complete_lineage(monitor_content_digest="34" * 32)
    assert compute_replay_lineage_digest(single) != compute_replay_lineage_digest(
        changed_monitor
    )
    changed_split = _complete_lineage(split_manifest_digest="45" * 32)
    assert compute_replay_lineage_digest(single) != compute_replay_lineage_digest(
        changed_split
    )
    legacy_relocated.monitor_artifact.sha256 = "33" * 32
    assert compute_replay_lineage_digest(legacy) != compute_replay_lineage_digest(
        legacy_relocated
    )


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
        state_shape_digest="44" * 32,
    )


def _policy_config(
    mode: str,
    *,
    foundation: Path | None = None,
    replay: bool = False,
) -> dict:
    config = {
        "training": {
            "mode": mode,
            "device": "cpu",
            "dtype": "float64",
            "batch_size": 2,
            "valid_batch_size": 2,
        },
        "acceleration": {"backend": "e3nn", "training_backend": "e3nn"},
    }
    paths: dict[str, str] = {}
    if foundation is not None:
        paths["foundation_model"] = str(foundation)
    if replay:
        paths.update(
            {
                "replay_train": "/replay/train.extxyz",
                "replay_monitor": "/replay/monitor.extxyz",
                "replay_true_labels": "/replay/true-labels",
            }
        )
        config["replay"] = {"mode": "external_pseudolabel"}
    if paths:
        config["paths"] = paths
    return config


def _minimal_materialization_inputs() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    preparation = SimpleNamespace(
        fitted_atomic_references=SimpleNamespace(
            reference_energies_ev=((3, 0.0), (8, 0.0))
        )
    )
    target_train = SimpleNamespace(relative_path="target-train.extxyz", atomic_numbers=(3, 8))
    monitor = SimpleNamespace(relative_path="target-monitor.extxyz", atomic_numbers=(3, 8))
    return preparation, target_train, monitor


def _minimal_optimizer() -> SimpleNamespace:
    return SimpleNamespace(
        learning_rate=1.0e-4,
        batch_size=2,
        valid_batch_size=2,
        num_workers=0,
        ema=False,
        ema_decay=0.99,
        amsgrad=False,
        weight_decay=0.0,
        clip_grad=10.0,
        device="cpu",
    )


def _write_valid_replay_file(path: Path, *, offset: float) -> None:
    import numpy as np
    from ase import Atoms
    from ase.io import write

    atoms = Atoms(
        "LiO",
        positions=((0.8 + offset, 0.8, 0.8), (4.5, 4.5, 4.5)),
        cell=np.eye(3) * 10.0,
        pbc=True,
    )
    atoms.info["REF_energy"] = -10.0 + offset
    atoms.arrays["REF_forces"] = np.asarray(
        [[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]], dtype=np.float64
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, [atoms], format="extxyz")


def test_r10a_exact_mode_matrix_and_executable_head_parity(tmp_path: Path, monkeypatch):
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"bounded-foundation")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )

    scratch_policies = resolve_post_selection_method_policies(
        _policy_config("scratch")
    )
    scratch_method = resolve_post_selection_method_identity(
        _policy_config("scratch"), policies=scratch_policies
    )
    assert scratch_method.training_mode == "scratch"
    assert scratch_policies.foundation_model is None
    assert scratch_policies.replay_training_label_mode is None

    naive_cfg = _policy_config("naive_fine_tuning", foundation=foundation)
    naive_policies = resolve_post_selection_method_policies(naive_cfg)
    naive_method = resolve_post_selection_method_identity(
        naive_cfg, policies=naive_policies
    )
    assert naive_policies.foundation_model == str(foundation.resolve())
    assert naive_policies.replay_training_label_mode is None

    multi_cfg = _policy_config("multihead_replay", foundation=foundation, replay=True)
    multi_cfg["foundation"] = {"family": "mace_mpa_0", "head": "default"}
    multi_policies = resolve_post_selection_method_policies(multi_cfg)
    multi_method = resolve_post_selection_method_identity(
        multi_cfg, policies=multi_policies
    )
    assert multi_policies.replay_training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert multi_policies.checkpoint_admissibility.replay_enabled

    preparation, target_train, monitor = _minimal_materialization_inputs()
    optimizer = _minimal_optimizer()
    scratch_internal = _post_selection_mace_config(
        run_identity="scratch",
        optimizer_seed=1,
        planned_epochs=3,
        preparation=preparation,
        optimizer_policy=optimizer,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=scratch_policies.extxyz,
        method=scratch_method,
        mace_architecture=scratch_policies.mace_architecture,
    )
    assert "multiheads_finetuning" not in scratch_internal
    assert "pt_train_file" not in scratch_internal
    assert "heads" not in scratch_internal
    assert "multiheads_finetuning" not in post_selection_mace_run_configuration(
        scratch_internal
    )

    naive_internal = _post_selection_mace_config(
        run_identity="naive",
        optimizer_seed=1,
        planned_epochs=3,
        preparation=preparation,
        optimizer_policy=optimizer,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=naive_policies.extxyz,
        method=naive_method,
        mace_architecture=naive_policies.mace_architecture,
        foundation_model=naive_policies.foundation_model,
        foundation_head=naive_policies.foundation_head,
    )
    assert "multiheads_finetuning" not in naive_internal
    assert "pt_train_file" not in naive_internal
    assert "heads" not in naive_internal
    assert post_selection_mace_run_configuration(naive_internal)["foundation_model"] == str(
        foundation.resolve()
    )

    multi_internal = _post_selection_mace_config(
        run_identity="multi",
        optimizer_seed=1,
        planned_epochs=3,
        preparation=preparation,
        optimizer_policy=optimizer,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=multi_policies.extxyz,
        method=multi_method,
        mace_architecture=multi_policies.mace_architecture,
        foundation_model=multi_policies.foundation_model,
        foundation_head=multi_policies.foundation_head,
        multiheads_finetuning=True,
        replay_train=SimpleNamespace(relative_path="replay-train.extxyz"),
        replay_monitor=SimpleNamespace(relative_path="replay-monitor.extxyz"),
    )
    executable = post_selection_mace_run_configuration(multi_internal)
    assert executable["multiheads_finetuning"] is True
    assert executable["pt_train_file"] == "replay-train.extxyz"
    assert executable["pt_valid_file"] == "replay-monitor.extxyz"
    assert set(executable["heads"]) == {
        POST_SELECTION_TARGET_HEAD_NAME,
        POST_SELECTION_REPLAY_HEAD_NAME,
    }

    optimizer_policy = SimpleNamespace(policy_digest="12" * 32, seed=1)
    budget = TrainingBudgetPolicy(planned_epochs=3)
    with pytest.raises(PostSelectionExecutionError):
        post_selection_runtime_plan(
            method=scratch_method,
            optimizer_policy=optimizer_policy,
            budget_policy=budget,
            structures_per_epoch=1,
            replay_monitor_enabled=True,
            true_replay_monitor_sha256="34" * 32,
        )
    with pytest.raises(PostSelectionExecutionError):
        post_selection_runtime_plan(
            method=multi_method,
            optimizer_policy=optimizer_policy,
            budget_policy=budget,
            structures_per_epoch=1,
            replay_monitor_enabled=False,
        )


@pytest.mark.parametrize(
    "mode, foundation, replay",
    (
        ("scratch", True, False),
        ("scratch", False, True),
        ("naive_fine_tuning", False, False),
        ("naive_fine_tuning", True, True),
        ("multihead_replay", False, True),
        ("multihead_replay", True, False),
    ),
)
def test_r10a_illegal_mode_matrix_cells_reject_before_downstream_work(
    tmp_path: Path, monkeypatch, mode: str, foundation: bool, replay: bool
):
    foundation_path = tmp_path / "foundation.model"
    foundation_path.write_bytes(b"foundation")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    config = _policy_config(
        mode, foundation=foundation_path if foundation else None, replay=replay
    )
    with pytest.raises((PostSelectionError, TrainingDataInputError)):
        resolve_post_selection_method_policies(config)


def test_r10a_replay_policy_without_source_cannot_be_silent_monitor_only(
    tmp_path: Path, monkeypatch
):
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    for mode, foundation_path in (
        ("scratch", None),
        ("naive_fine_tuning", foundation),
    ):
        config = _policy_config(mode, foundation=foundation_path)
        config["replay"] = {"mode": "external_pseudolabel"}
        with pytest.raises((PostSelectionError, TrainingDataInputError)):
            resolve_post_selection_method_policies(config)


def test_r10a_multihead_requires_independent_true_dft_monitor_before_training(
    tmp_path: Path, monkeypatch
):
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )

    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    pseudo_train = tmp_path / "pseudo-train.extxyz"
    pseudo_monitor = tmp_path / "pseudo-monitor.extxyz"
    _write_valid_replay_file(pseudo_train, offset=0.1)
    _write_valid_replay_file(pseudo_monitor, offset=0.2)
    config_path = tmp_path / "campaign.toml"
    config = _policy_config("multihead_replay", foundation=foundation, replay=True)
    config["paths"].update(
        {
            "replay_train": str(pseudo_train),
            "replay_monitor": str(pseudo_monitor),
            "replay_true_labels": str(tmp_path / "missing-true-label-root"),
        }
    )
    config_path.write_text("", encoding="utf-8")
    paths = cli.CampaignPaths.from_config(config_path, config)
    paths.ensure()
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: _foundation_inspection(Path(path)),
    )
    missing_monitor_config = {
        **config,
        "paths": {**config["paths"], "replay_monitor": ""},
    }
    with pytest.raises(PostSelectionError, match="monitor path"):
        resolve_post_selection_method_policies(missing_monitor_config)
    missing_true_root_config = {
        **config,
        "paths": {**config["paths"], "replay_true_labels": ""},
    }
    with pytest.raises(PostSelectionError, match="TRUE_DFT monitor source"):
        resolve_post_selection_method_policies(missing_true_root_config)
    context = SimpleNamespace(cfg=config, paths=paths)
    with pytest.raises(Exception, match="TRUE_DFT|true-label|replay monitor"):
        _resolve_post_selection_replay_resolution(context)


def _write_tiny_mace_foundation(path: Path) -> None:
    import torch

    from tests._mlff_tiny_mace import _tiny_mace

    model = _tiny_mace(
        interaction_cls_name="RealAgnosticDensityResidualInteractionBlock",
        atomic_numbers=(3, 8),
        heads=["default"],
        seed=9,
        dtype=torch.float64,
    )
    torch.save(model, path)


def test_r10b_real_foundation_provider_owner_counterfactuals(
    tmp_path: Path, monkeypatch
):
    foundation = tmp_path / "foundation.model"
    _write_tiny_mace_foundation(foundation)
    foundation_bytes = foundation.read_bytes()

    from mdstats.training_data.post_selection_identity import (
        resolve_post_selection_foundation_identity,
    )

    identity = resolve_post_selection_foundation_identity(
        foundation, requested_head="default", model_family="mace_mpa_0"
    )
    provider = build_post_selection_foundation_baseline_provider(
        foundation_path=foundation,
        foundation_identity=identity,
        foundation_head="default",
        device="cpu",
        default_dtype="float64",
    )
    assert provider.__class__.__name__ == "MaceCalculatorProvider"
    provider.close()

    with pytest.raises(PostSelectionExecutionError, match="bytes changed"):
        foundation.write_bytes(b"tampered")
        build_post_selection_foundation_baseline_provider(
            foundation_path=foundation,
            foundation_identity=identity,
            foundation_head="default",
        )

    # Restore the authenticated bytes before provider-level counterfactuals.
    foundation.write_bytes(foundation_bytes)

    with pytest.raises(TrainingDataInputError, match="head"):
        build_post_selection_foundation_baseline_provider(
            foundation_path=foundation,
            foundation_identity=identity,
            foundation_head="unavailable-head",
        )

    import mace.calculators as mace_calculators

    def fail_mace_calculator(*_args, **_kwargs):
        raise RuntimeError("bounded provider-construction failure")

    monkeypatch.setattr(
        mace_calculators, "MACECalculator", fail_mace_calculator
    )
    with pytest.raises(RuntimeError, match="bounded provider-construction failure"):
        build_post_selection_foundation_baseline_provider(
            foundation_path=foundation,
            foundation_identity=identity,
            foundation_head="default",
        )
