"""Revision-10 owner guards for P5 lineage, mode parity, and providers."""

from __future__ import annotations

import ast

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from mdstats.training_data.objectives import TrainingObjectivePolicy

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
        ),
        # The fitted preparation carries the resolved global objective, which the
        # generated MACE config must emit explicitly.
        objective_policy=TrainingObjectivePolicy(),
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
    assert post_selection_mace_run_configuration(scratch_internal)[
        "multiheads_finetuning"
    ] is False

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
        foundation_head=naive_policies.foundation_head,
    )
    assert "multiheads_finetuning" not in naive_internal
    assert "pt_train_file" not in naive_internal
    assert "heads" not in naive_internal
    # The runtime locator is never stored in the immutable representation; the
    # launch projection receives the authenticated current one.
    assert "foundation_model" not in naive_internal
    assert post_selection_mace_run_configuration(
        naive_internal, foundation_model_path=naive_policies.foundation_model
    )["foundation_model"] == str(foundation.resolve())

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
        foundation_head=multi_policies.foundation_head,
        multiheads_finetuning=True,
        replay_train=SimpleNamespace(relative_path="replay-train.extxyz"),
        replay_monitor=SimpleNamespace(relative_path="replay-monitor.extxyz"),
    )
    executable = post_selection_mace_run_configuration(
        multi_internal, foundation_model_path=multi_policies.foundation_model
    )
    assert executable["multiheads_finetuning"] is True
    assert executable["pt_train_file"] == "replay-train.extxyz"
    assert executable["pt_valid_file"] == "replay-monitor.extxyz"
    # MACE's parser declares --heads as a scalar type=str action and reads it
    # with ast.literal_eval, so the executable spelling is one literal.
    assert isinstance(executable["heads"], str)
    assert set(ast.literal_eval(executable["heads"])) == {
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


# --- R10c / Single-source replay lineage adapter repair (Section 7) -----------


def _single_source_replay_fixture_config(
    tmp_path: Path,
    source: Path,
    *,
    label_mode: str = "true_dft",
    split_seed: int = 42,
    split_ratio: str = "5:1",
) -> tuple[dict, Any]:
    from mdstats.training_data import campaign_cli

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
    if split_seed != 42:
        text = text.replace("split_seed = 42", f"split_seed = {split_seed}")
    if split_ratio != "5:1":
        text = text.replace('split_ratio = "5:1"', f'split_ratio = "{split_ratio}"')
    config = tmp_path / "campaign.toml"
    config.write_text(text, encoding="utf-8")
    return campaign_cli._load_config(config)


def test_r10c_real_single_source_true_dft_lineage_resolves_and_authenticates(
    tmp_path: Path,
):
    from tests.test_mlff_replay_unify1d import _write_source
    from mdstats.training_data import campaign_cli
    from mdstats.training_data._campaign_cli_core import _single_source_replay_context
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )

    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _single_source_replay_fixture_config(
        tmp_path, source_path, label_mode="true_dft"
    )

    single_ctx = _single_source_replay_context(cfg, paths)
    assert single_ctx is not None
    assert "source" in single_ctx
    assert "split" in single_ctx

    context = SimpleNamespace(cfg=cfg, paths=paths)
    resolution = _resolve_post_selection_replay_resolution(context)
    assert resolution is not None
    assert resolution.interface == "single_source"

    assert resolution.source_content_digest == single_ctx["source"].content_digest
    assert resolution.source_sha256 == single_ctx["source"].sha256
    assert resolution.split_manifest_digest == single_ctx["split"].content_digest

    lineage_digest = compute_replay_lineage_digest(resolution)
    assert lineage_digest is not None
    assert len(lineage_digest) == 64


def test_r10c_foundation_pseudolabel_single_source_lineage_and_label_separation(
    tmp_path: Path, monkeypatch
):
    import mdstats
    from tests.test_mlff_replay_unify1d import _FakeProvider, _write_source
    from mdstats.training_data import campaign_cli
    from mdstats.training_data import _campaign_cli_core as campaign_core
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )
    from mdstats.training_data.foundation import (
        FoundationInferenceIdentity,
        FoundationPotentialIdentity,
    )

    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _single_source_replay_fixture_config(
        tmp_path, source_path, label_mode="foundation_pseudolabel"
    )

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
    monkeypatch.setattr(
        campaign_core, "_resolved_foundation_potential_identity", lambda cfg, paths: potential
    )
    monkeypatch.setattr(
        campaign_core,
        "_stored_acceleration_realization",
        lambda cfg, paths, require_qualified=False: realization,
    )
    monkeypatch.setattr(
        campaign_core,
        "_foundation_inference_identity",
        lambda cfg, potential_arg, **kwargs: inference,
    )

    original_builder = mdstats.build_replay_foundation_prediction_cache
    providers: list[_FakeProvider] = []

    def build_with_fake(source, policy, cache_root, **kwargs):
        provider = _FakeProvider(policy)
        providers.append(provider)
        return original_builder(source, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_fake)
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()

    single_ctx = campaign_core._single_source_replay_context(cfg, paths)
    assert single_ctx is not None
    context = SimpleNamespace(cfg=cfg, paths=paths)
    resolution = _resolve_post_selection_replay_resolution(context)
    assert resolution is not None
    assert resolution.interface == "single_source"

    # Replay training artifact remains foundation pseudolabel
    assert resolution.training_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    assert resolution.train_artifact.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL

    # Independent monitor remains TRUE_DFT
    assert ReplayLabelMode(resolution.true_label_mode) is ReplayLabelMode.TRUE_DFT
    assert ReplayLabelMode(resolution.monitor_artifact.label_mode) is ReplayLabelMode.TRUE_DFT

    # Canonical source/split lineage is complete
    assert resolution.source_content_digest == single_ctx["source"].content_digest
    assert resolution.source_sha256 == single_ctx["source"].sha256
    assert resolution.split_manifest_digest == single_ctx["split"].content_digest

    # Lineage digest succeeds without changing semantic label ownership
    digest = compute_replay_lineage_digest(resolution)
    assert digest is not None
    assert len(digest) == 64


def test_r10c_single_source_restart_stability_across_context_cache_clear(
    tmp_path: Path,
):
    from tests.test_mlff_replay_unify1d import _write_source
    from mdstats.training_data import campaign_cli
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )

    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _single_source_replay_fixture_config(
        tmp_path, source_path, label_mode="true_dft"
    )

    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    context = SimpleNamespace(cfg=cfg, paths=paths)
    first_resolution = _resolve_post_selection_replay_resolution(context)
    first_digest = compute_replay_lineage_digest(first_resolution)

    # Discard only the in-memory context cache to simulate restart
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    second_resolution = _resolve_post_selection_replay_resolution(context)
    second_digest = compute_replay_lineage_digest(second_resolution)

    assert first_digest == second_digest


def test_r10c_single_source_mutation_invalidates_lineage(
    tmp_path: Path,
):
    from tests.test_mlff_replay_unify1d import _write_source
    from mdstats.training_data import campaign_cli
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )

    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)
    cfg, paths = _single_source_replay_fixture_config(
        tmp_path, source_path, label_mode="true_dft", split_seed=42
    )

    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    context = SimpleNamespace(cfg=cfg, paths=paths)
    baseline_resolution = _resolve_post_selection_replay_resolution(context)
    baseline_digest = compute_replay_lineage_digest(baseline_resolution)

    # 1. Mutating source content bytes invalidates lineage
    mutated_source_dir = tmp_path / "mutated_source"
    mutated_source_dir.mkdir()
    mutated_source_path = mutated_source_dir / "replay.extxyz"
    _write_source(mutated_source_path, 14)
    cfg_mutated_source, paths_mutated_source = _single_source_replay_fixture_config(
        mutated_source_dir, mutated_source_path, label_mode="true_dft", split_seed=42
    )
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    mutated_source_res = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=cfg_mutated_source, paths=paths_mutated_source)
    )
    mutated_source_digest = compute_replay_lineage_digest(mutated_source_res)
    assert mutated_source_digest != baseline_digest

    # 2. Mutating split configuration (split_seed) invalidates lineage
    split_mutated_dir = tmp_path / "split_mutated"
    split_mutated_dir.mkdir()
    cfg_mutated_split, paths_mutated_split = _single_source_replay_fixture_config(
        split_mutated_dir, source_path, label_mode="true_dft", split_seed=999
    )
    campaign_cli._UNIFIED_REPLAY_CONTEXT_CACHE.clear()
    mutated_split_res = _resolve_post_selection_replay_resolution(
        SimpleNamespace(cfg=cfg_mutated_split, paths=paths_mutated_split)
    )
    mutated_split_digest = compute_replay_lineage_digest(mutated_split_res)
    assert mutated_split_digest != baseline_digest


def test_r10c_multi_size_cv_admission_resolves_shared_single_source_replay_lineage(
    tmp_path: Path, monkeypatch
):
    import tests._mlff_post_selection_fixture as fx
    import tests.test_mlff_target_size_multi_size_integration as msi
    from tests.test_mlff_replay_unify1d import _write_source
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        build_post_selection_cv_plan,
        build_selected_relation_projection,
        _resolve_post_selection_replay_resolution,
    )

    config = msi._two_size_campaign(tmp_path)

    source_path = tmp_path / "replay.extxyz"
    _write_source(source_path, 12)

    foundation_path = tmp_path / "foundation.model"
    foundation_path.write_bytes(b"foundation-checkpoint-fixture")

    config_text = config.read_text(encoding="utf-8")
    config_text = config_text.replace(
        'mode = "scratch_training"',
        'mode = "multihead_replay"',
    )
    config_text = config_text.replace(
        "[paths]\n",
        f'[paths]\nreplay_set = "{source_path}"\nfoundation_model = "{foundation_path}"\n',
    )
    config_text += """
[foundation]
family = "mace_mpa_0"
head = "default"

[replay]
label_mode = "true_dft"
split_ratio = "5:1"
split_seed = 42
"""
    config.write_text(config_text, encoding="utf-8")

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        monkeypatch.setattr(
            "mdstats.training_data.foundation.inspect_mace_foundation",
            lambda path: _foundation_inspection(Path(path)),
        )
        harness = fx.PostSelectionHarness()
        contexts = build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )
        assert len(contexts) == 2
        ctx8, ctx16 = contexts
        assert ctx8.selected.n_selected == 8
        assert ctx16.selected.n_selected == 16

        # Shared replay lineage resolves successfully before/for per-size CV orchestration
        res8 = _resolve_post_selection_replay_resolution(ctx8)
        res16 = _resolve_post_selection_replay_resolution(ctx16)
        assert res8 is not None
        assert res16 is not None
        digest8 = compute_replay_lineage_digest(res8)
        digest16 = compute_replay_lineage_digest(res16)

        # Repaired shared replay resolution is identical in scientific identity for the same replay source/split
        assert digest8 == digest16

        # Build CV plans for both sizes
        plan8 = build_post_selection_cv_plan(
            ctx8.selected,
            ctx8.method,
            ctx8.cv_policy,
            projection=build_selected_relation_projection(ctx8.selected),
            replay_lineage_digest=digest8,
        )
        plan16 = build_post_selection_cv_plan(
            ctx16.selected,
            ctx16.method,
            ctx16.cv_policy,
            projection=build_selected_relation_projection(ctx16.selected),
            replay_lineage_digest=digest16,
        )

        assert plan8.replay_lineage_digest == digest8
        assert plan16.replay_lineage_digest == digest16

        # Both selected entries retain their independent (N_selected, H_cv, H_prod) bindings
        assert plan8.binding.n_selected == 8
        assert plan16.binding.n_selected == 16
        assert plan8.binding.content_digest != plan16.binding.content_digest
    finally:
        store.close()

