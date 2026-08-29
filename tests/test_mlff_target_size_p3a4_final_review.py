"""Final-review P3A4 evidence for real MACE reconstruction and authentication."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

import ase
from mace.tools.checkpoint import CheckpointHandler, CheckpointState
import pytest
import torch
from torch_ema import ExponentialMovingAverage

import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
import tests.test_mlff_target_size_execution_p3e as p3e
import tests.test_mlff_target_size_execution_p3f as p3f
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.eval2 import Eval2NumericalEvaluationError
from mdstats.training_data.model_features import (
    MaceCalculatorProvider,
    MaceModelStateCompatibilityError,
    _AuthenticatedParameterShell,
    build_mace_model_from_configuration,
    mace_candidate_architecture_defaults,
    mace_model_execution_architecture_digest,
)
from mdstats.training_data.target_size_execution.evaluation import (
    _authenticate_target_size_provider,
)
from mdstats.training_data.target_size_execution.execution import (
    EVALUATION_MODEL_STATE_EMA,
    EVALUATION_MODEL_STATE_LIVE,
)
from mdstats.training_data.target_size_execution import (
    TargetSizeBoundarySnapshot,
    TargetSizeCandidateMaterialization,
    TargetSizeCandidateOutcome,
    TargetSizeCandidateTrajectory,
    TargetSizeCellCompletionRecord,
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    collect_boundary_cell_completion_records,
    commit_target_size_boundary_batch,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initial_target_size_continuation_request,
    materialize_target_size_candidate,
    promote_target_size_boundary_snapshot,
    reconcile_target_size_screen_root,
    record_candidate_boundary_outcome,
    resolve_target_size_candidate_for_resume,
    run_target_size_direct_boundary_inference,
    run_target_size_eval2_reduction,
    target_size_rung_plan,
    translate_target_size_eval2_failure,
    validate_target_size_candidate_trajectory,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_COMPANION_SCHEMA,
    _tensor_state_digest,
    verify_train2_checkpoint_model_parameters,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configuration() -> dict[str, object]:
    architecture = _small_architecture()
    return {
        "name": "p3a4-real-mace",
        "atomic_numbers": [1, 8],
        "E0s": {"1": 0.1, "8": 0.2},
        "device": "cpu",
        "default_dtype": "float64",
        "mace_architecture": architecture,
    }


def _small_architecture() -> dict[str, object]:
    architecture = mace_candidate_architecture_defaults()
    architecture.update(
        {
            "r_max": 3.0,
            "num_radial_basis": 4,
            "num_cutoff_basis": 4,
            "max_ell": 1,
            "num_interactions": 2,
            "hidden_irreps": "8x0e + 8x1o",
            "MLP_irreps": "4x0e",
            "radial_MLP": [4, 4],
            "correlation": 2,
            "avg_num_neighbors": 3.0,
        }
    )
    return architecture


def _fixture(
    tmp_path: Path,
    *,
    with_ema: bool = False,
):
    config = _configuration()
    model = build_mace_model_from_configuration(config)
    architecture_digest = mace_model_execution_architecture_digest(model)
    tmp_path.mkdir(parents=True, exist_ok=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    lr_scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.99)
    tag = "model_fixture"
    handler = CheckpointHandler(directory=str(tmp_path), tag=tag, keep=True)

    if with_ema:
        ema = ExponentialMovingAverage(model.parameters(), decay=0.9)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.05)
        ema.update()
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.10)

        with ema.average_parameters():
            handler.save(
                state=CheckpointState(model, optimizer, lr_scheduler),
                epochs=0,
                keep_last=True,
            )

        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = [value.detach().cpu().clone() for value in ema.shadow_params]

        ema_state = {
            "decay": 0.9,
            "num_updates": 1,
            "shadow_params": shadow,
            "collected_params": None,
        }
        ema_digest = _tensor_state_digest(
            shadow, schema="mdstats.train2-ema-state.v1"
        )
        evaluation_model_state = EVALUATION_MODEL_STATE_EMA
    else:
        handler.save(
            state=CheckpointState(model, optimizer, lr_scheduler),
            epochs=0,
            keep_last=True,
        )
        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = None
        ema_state = None
        ema_digest = None
        evaluation_model_state = EVALUATION_MODEL_STATE_LIVE

    raw_checkpoint_path = tmp_path / f"{tag}_epoch-0.pt"

    # Mandatory Section B3 fixture invariants
    assert raw_checkpoint_path.is_file(), "Fixture invariant failed: checkpoint file missing"
    saved_ckpt = torch.load(raw_checkpoint_path, map_location="cpu", weights_only=False)
    assert isinstance(saved_ckpt, dict), "Fixture invariant failed: checkpoint must be a dict"
    assert set(saved_ckpt.keys()) >= {"model", "optimizer", "lr_scheduler"}, "Fixture invariant failed: top-level checkpoint keys"
    assert isinstance(saved_ckpt["model"], (dict, OrderedDict)), "Fixture invariant failed: model must be state dict mapping"
    saved_model_params = [saved_ckpt["model"][name] for name, _ in model.named_parameters()]

    if with_ema:
        assert not all(
            torch.equal(l, s) for l, s in zip(live, shadow, strict=True)
        ), "Fixture invariant failed: live parameters must differ from EMA shadow"
        assert all(
            torch.equal(r, s) for r, s in zip(saved_model_params, shadow, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must equal EMA shadow"
        assert not all(
            torch.equal(r, l) for r, l in zip(saved_model_params, live, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must differ from live state"
        assert all(
            torch.equal(m.detach().cpu(), l)
            for m, l in zip(model.parameters(), live, strict=True)
        ), "Fixture invariant failed: model parameters must return to live state outside context"
    else:
        assert all(
            torch.equal(r, l) for r, l in zip(saved_model_params, live, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must equal live state"

    companion = {
        "schema": TRAIN2_RUNTIME_COMPANION_SCHEMA,
        "live_parameters": live,
        "ema_state": ema_state,
        "rng_state": {},
        "model_architecture_digest": architecture_digest,
    }
    companion_path = tmp_path / f"{tag}_epoch-0-companion.pt"
    torch.save(companion, companion_path)
    summary = SimpleNamespace(
        model_architecture_digest=architecture_digest,
        live_parameter_digest=_tensor_state_digest(
            live, schema="mdstats.train2-live-parameters.v1"
        ),
        ema_state_digest=ema_digest,
    )
    trajectory = SimpleNamespace(evaluation_model_state=evaluation_model_state)
    return {
        "config": config,
        "model": model,
        "state": saved_ckpt["model"],
        "live": live,
        "shadow": shadow,
        "architecture_digest": architecture_digest,
        "companion": companion,
        "summary": summary,
        "trajectory": trajectory,
        "raw_checkpoint_path": raw_checkpoint_path,
        "companion_path": companion_path,
    }


def _authenticate(fixture, *, allow_forward_override: bool = False, config=None):
    return _authenticate_target_size_provider(
        raw_checkpoint_path=fixture["raw_checkpoint_path"],
        raw_checkpoint_sha256=_sha256(fixture["raw_checkpoint_path"]),
        companion_path=fixture["companion_path"],
        companion_sha256=_sha256(fixture["companion_path"]),
        summary=fixture["summary"],
        trajectory=fixture["trajectory"],
        config_payload=fixture["config"] if config is None else config,
        allow_forward_override=allow_forward_override,
    )


def test_p3a4_real_mace_state_dict_reconstructs_one_provider_and_forwards(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, with_ema=False)

    provider, evaluated_digest, _companion = _authenticate(fixture)

    assert isinstance(provider, MaceCalculatorProvider)
    assert not isinstance(provider.model, _AuthenticatedParameterShell)
    assert provider.model is provider._calculator.models[0]
    assert provider.runtime_architecture_digest
    assert evaluated_digest == fixture["summary"].live_parameter_digest

    prediction = provider.predict(
        ase.Atoms("H2", positions=((0.0, 0.0, 0.0), (0.0, 0.0, 0.74)))
    )
    assert torch.isfinite(torch.as_tensor(prediction.energy_ev))
    assert torch.isfinite(
        torch.as_tensor(prediction.forces_ev_per_angstrom.copy())
    ).all()
    assert (
        evaluated_digest
        == _tensor_state_digest(
            tuple(provider.model.parameters()),
            schema="mdstats.train2-live-parameters.v1",
        )
    )


def test_p3a4_real_mace_ema_checkpoint_semantics_reproducer(
    tmp_path: Path,
) -> None:
    """Real MACE EMA checkpoint-semantics reproducer (Section B1-B5).

    Proves through the pinned real MACE CheckpointHandler.save() that:
    1. A real MACE model reconstructed through candidate config with real EMA
       has divergent live vs shadow parameter states.
    2. Saving under real ``ema.average_parameters()`` through real MACE CheckpointHandler
       produces checkpoint model parameters equal to the EMA shadow, differing from live parameters.
    3. Exiting ``ema.average_parameters()`` restores live parameters.
    4. The production target-size provider authentication path authenticates the
       raw checkpoint parameters against the EMA shadow, applies EMA shadow,
       and tiny CPU forward succeeds with no override.
    """
    fixture = _fixture(tmp_path, with_ema=True)

    provider, evaluated_digest, _companion = _authenticate(
        fixture, allow_forward_override=False
    )

    assert isinstance(provider, MaceCalculatorProvider)
    assert not isinstance(provider.model, _AuthenticatedParameterShell)
    assert provider.model is provider._calculator.models[0]
    assert provider.runtime_architecture_digest
    assert evaluated_digest == fixture["summary"].ema_state_digest
    assert all(
        torch.equal(p.detach().cpu(), s)
        for p, s in zip(provider.model.parameters(), fixture["shadow"], strict=True)
    )

    prediction = provider.predict(
        ase.Atoms("H2", positions=((0.0, 0.0, 0.0), (0.0, 0.0, 0.74)))
    )
    assert torch.isfinite(torch.as_tensor(prediction.energy_ev))
    assert torch.isfinite(
        torch.as_tensor(prediction.forces_ev_per_angstrom.copy())
    ).all()


def _run_direct_inference_test(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    with_ema: bool,
) -> None:
    env = p3e._env(tmp_path)
    definition = env["aggregate"].definition
    requirements = p3e.derive_active_boundary_requirements(
        definition, env["aggregate"].reducer_state
    )
    assert requirements is not None
    boundary, evaluation_size, keys = requirements
    size, seed = keys[0]

    optimizer_policy = replace(env["optimizer"], ema=with_ema)
    context = build_target_size_execution_context(
        definition,
        env["common"],
        env["schedule"],
        seed_neutral_optimizer_policy=optimizer_policy,
    )

    trajectory = build_target_size_candidate_trajectory(
        definition,
        context,
        env["common"],
        env["schedule"],
        target_size=size,
        optimizer_policy=optimizer_policy,
        optimizer_seed=seed,
    )
    expected_eval_state = (
        EVALUATION_MODEL_STATE_EMA if with_ema else EVALUATION_MODEL_STATE_LIVE
    )
    assert trajectory.evaluation_model_state == expected_eval_state

    projection = project_target_size_candidate_preparation(
        env["common"], definition, size
    )
    materialization_directory = tmp_path / "materialization"
    materialization = materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=materialization_directory,
        optimizer_policy=optimizer_policy,
        extxyz_policy=env["authority"].extxyz_policy,
        frame_array_index=env["index"],
        mace_architecture=_small_architecture(),
    )
    config_payload = json.loads(
        (
            materialization_directory
            / materialization.mace_config_relative_path
        ).read_text(encoding="utf-8")
    )
    model = build_mace_model_from_configuration(config_payload)
    architecture_digest = mace_model_execution_architecture_digest(model)

    checkpoint_directory = tmp_path / "real-boundary-source"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    plan = target_size_rung_plan(
        trajectory, env["schedule"], boundary_epoch=boundary
    )
    _runtime, base_summary, _restored, _rng = p3c._run_rung(
        plan,
        checkpoint_directory,
        start_epoch=0,
        updates_per_epoch=trajectory.realization.updates_per_epoch,
        seed=1,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    lr_scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.99)
    tag = "model_run-7"
    handler = CheckpointHandler(directory=str(checkpoint_directory), tag=tag, keep=True)

    if with_ema:
        ema = ExponentialMovingAverage(model.parameters(), decay=0.9)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.05)
        ema.update()
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.10)

        with ema.average_parameters():
            handler.save(
                state=CheckpointState(model, optimizer, lr_scheduler),
                epochs=0,
                keep_last=True,
            )

        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = [value.detach().cpu().clone() for value in ema.shadow_params]

        assert not all(
            torch.equal(l, s) for l, s in zip(live, shadow, strict=True)
        ), "Fixture invariant failed: live parameters must differ from EMA shadow"

        ema_state = {
            "decay": 0.9,
            "num_updates": 1,
            "shadow_params": shadow,
            "collected_params": None,
        }
        ema_digest = _tensor_state_digest(
            shadow, schema="mdstats.train2-ema-state.v1"
        )
    else:
        handler.save(
            state=CheckpointState(model, optimizer, lr_scheduler),
            epochs=0,
            keep_last=True,
        )
        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = None
        ema_state = None
        ema_digest = None

    raw_checkpoint_path = checkpoint_directory / f"{tag}_epoch-0.pt"
    raw_sha = _sha256(raw_checkpoint_path)
    live_digest = _tensor_state_digest(
        live, schema="mdstats.train2-live-parameters.v1"
    )
    companion_path = checkpoint_directory / "train2_runtime.pt"
    companion = torch.load(
        companion_path, map_location="cpu", weights_only=False
    )
    companion["raw_checkpoint_sha256"] = raw_sha
    companion["live_parameters"] = live
    companion["ema_state"] = ema_state
    companion["model_architecture_digest"] = architecture_digest
    torch.save(companion, companion_path)
    optimizer_state_digest = digest(
        {
            "schema": "mdstats.train2-optimizer-state-reference.v1",
            "raw_checkpoint_sha256": raw_sha,
            "training_protocol_digest": plan.training_protocol_digest,
            "optimizer_policy_digest": plan.optimizer_policy_digest,
            "completed_updates": base_summary.completed_updates,
        }
    )
    summary = replace(
        base_summary,
        raw_checkpoint_sha256=raw_sha,
        optimizer_state_digest=optimizer_state_digest,
        live_parameter_digest=live_digest,
        ema_state_digest=ema_digest,
        model_architecture_digest=architecture_digest,
    )
    (checkpoint_directory / "train2_runtime.json").write_text(
        json.dumps(summary.to_dict(), sort_keys=True), encoding="utf-8"
    )
    boundary_state = bind_target_size_boundary_state(
        trajectory,
        env["schedule"],
        summary,
        checkpoint_directory=checkpoint_directory,
    )
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=checkpoint_directory,
        snapshot_root=env["root"],
    )
    evaluation_directory = tmp_path / "evaluation"
    evaluation_directory.mkdir(parents=True, exist_ok=True)
    evaluation_data = write_target_size_evaluation_artifact(
        evaluation_directory,
        definition=definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=env["blocks"],
        evaluation_data=evaluation_data,
    )

    seen_providers: list[MaceCalculatorProvider] = []
    original_predict_batch = MaceCalculatorProvider.predict_batch

    def _record_provider(provider, atoms_batch, **kwargs):
        seen_providers.append(provider)
        return original_predict_batch(provider, atoms_batch, **kwargs)

    def _forbid_shell(*args, **kwargs):
        del args, kwargs
        raise AssertionError("no-override direct inference attempted shell reconstruction")

    monkeypatch.setattr(MaceCalculatorProvider, "predict_batch", _record_provider)
    monkeypatch.setattr(
        MaceCalculatorProvider,
        "from_authenticated_parameter_state",
        _forbid_shell,
    )
    evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=evaluation_data,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=context,
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=optimizer_policy,
        materialization_directory=materialization_directory,
        snapshot_root=env["root"],
        evaluation_directory=evaluation_directory,
        root_directory=env["root"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )

    assert len(seen_providers) == 1
    provider = seen_providers[0]
    assert not isinstance(provider.model, _AuthenticatedParameterShell)
    assert provider.model is provider._calculator.models[0]
    assert evidence.execution_architecture == provider.runtime_architecture_digest
    assert evidence.device == provider.device == "cpu"
    assert evidence.default_dtype == provider.default_dtype == "float64"
    assert evidence.backend_policy == provider.backend_policy == "eager"

    if with_ema:
        assert evidence.evaluated_model_state_digest == ema_digest
        assert all(
            torch.equal(p.detach().cpu(), s)
            for p, s in zip(provider.model.parameters(), shadow, strict=True)
        )
    else:
        assert evidence.evaluated_model_state_digest == live_digest
        assert all(
            torch.equal(p.detach().cpu(), l)
            for p, l in zip(provider.model.parameters(), live, strict=True)
        )


def test_p3a4_real_mace_no_override_direct_inference_canonical_ema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production direct inference: canonical EMA evaluation with EMA enabled (Section A4 #7, Section B4)."""
    _run_direct_inference_test(tmp_path, monkeypatch, with_ema=True)


def test_p3a4_real_mace_no_override_direct_inference_canonical_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production direct inference: canonical LIVE evaluation with EMA disabled (Section A4 #8, Section B4)."""
    _run_direct_inference_test(tmp_path, monkeypatch, with_ema=False)


def test_p3a4_candidate_trajectory_evaluation_model_state_derivation_and_validation(
    tmp_path: Path,
) -> None:
    """Mandatory Section A4 items 1-5: canonical derivation and rejection of variant/tampered states."""
    env = p3e._env(tmp_path)
    definition = env["aggregate"].definition
    context = env["context"]
    common = env["common"]
    schedule = env["schedule"]
    optimizer_ema = env["optimizer"]
    optimizer_live = replace(optimizer_ema, ema=False)
    context_live = build_target_size_execution_context(
        definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=optimizer_live,
    )

    # 1. EMA enabled produces 'ema'
    traj_ema = build_target_size_candidate_trajectory(
        definition,
        context,
        common,
        schedule,
        target_size=definition.qualified_candidate_sizes[0],
        optimizer_policy=optimizer_ema,
        optimizer_seed=definition.policy.optimizer_seeds[0],
    )
    assert traj_ema.evaluation_model_state == EVALUATION_MODEL_STATE_EMA
    validate_target_size_candidate_trajectory(
        traj_ema,
        definition,
        context,
        common,
        schedule,
        optimizer_policy=optimizer_ema,
    )

    # 2. EMA disabled produces 'live'
    traj_live = build_target_size_candidate_trajectory(
        definition,
        context_live,
        common,
        schedule,
        target_size=definition.qualified_candidate_sizes[0],
        optimizer_policy=optimizer_live,
        optimizer_seed=definition.policy.optimizer_seeds[0],
    )
    assert traj_live.evaluation_model_state == EVALUATION_MODEL_STATE_LIVE
    validate_target_size_candidate_trajectory(
        traj_live,
        definition,
        context_live,
        common,
        schedule,
        optimizer_policy=optimizer_live,
    )

    # 3. validate_target_size_candidate_trajectory rejects tampered EMA-enabled trajectory changed to 'live'
    tampered_live = replace(
        traj_ema, evaluation_model_state=EVALUATION_MODEL_STATE_LIVE
    )
    with pytest.raises(
        TrainingDataInputError, match="does not match optimizer policy EMA convention"
    ):
        validate_target_size_candidate_trajectory(
            tampered_live,
            definition,
            context,
            common,
            schedule,
            optimizer_policy=optimizer_ema,
        )

    # 4. Trajectory validation rejects unsupported state string
    with pytest.raises(
        TrainingDataInputError, match="evaluation model-state representation"
    ):
        replace(traj_ema, evaluation_model_state="unknown_state")

    # 5. Two different N values and two authorized optimizer seeds under same seed-neutral policy
    # consistently evaluate the exact same convention
    for n in definition.qualified_candidate_sizes[:2]:
        for seed in definition.policy.optimizer_seeds[:2]:
            candidate_policy = replace(optimizer_ema, seed=seed)
            t = build_target_size_candidate_trajectory(
                definition,
                context,
                common,
                schedule,
                target_size=n,
                optimizer_policy=candidate_policy,
                optimizer_seed=seed,
            )
            assert t.evaluation_model_state == EVALUATION_MODEL_STATE_EMA
            validate_target_size_candidate_trajectory(
                t,
                definition,
                context,
                common,
                schedule,
                optimizer_policy=candidate_policy,
            )


def test_p3a4_durable_trajectory_tampered_evaluation_state_rejected(
    tmp_path: Path,
) -> None:
    """Mandatory owner-level test (P3A7 repair instructions Section 1-3):

    Proves that a durable EMA-enabled candidate trajectory whose self-digest and all
    restart-facing content-addressed references (trajectory, materialization, snapshot,
    completion, progress) have been recomputed consistently, but whose
    `evaluation_model_state` has been changed from canonical `ema` to noncanonical
    `live`, is rejected by the real production restart/resume path
    ``resolve_target_size_candidate_for_resume(...)`` specifically when that path
    re-authenticates the trajectory against the canonical optimizer policy.
    """
    # 2.1 Establish a valid control root first through boundary n1
    env = p3f._screen_env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    state = env["aggregate"].reducer_state
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    n1, evaluation_size_n1, keys_n1 = requirements
    assert n1 == schedule.n1

    eval_dir_n1 = tmp_path / f"eval_data_{n1}"
    eval_dir_n1.mkdir(parents=True, exist_ok=True)
    eval_artifact_n1 = write_target_size_evaluation_artifact(
        eval_dir_n1,
        definition=definition,
        evaluation_size=evaluation_size_n1,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )

    lanes: dict[tuple[int, int], p3f._CandidateLane] = {}
    materialized: dict[tuple[int, int], object] = {}

    for size, seed in keys_n1:
        lane = p3f._CandidateLane(env, tmp_path, size, seed)
        lanes[(size, seed)] = lane
        mat = lane.materialize(env, tmp_path)
        materialized[(size, seed)] = mat
        boundary_state = lane.train_to_boundary(env, n1)
        snapshot = promote_target_size_boundary_snapshot(
            lane.trajectory,
            boundary_state,
            checkpoint_directory=lane.checkpoint_dir,
            snapshot_root=env["root"],
        )
        role = build_target_size_eval2_role(
            trajectory=lane.trajectory,
            boundary_state=snapshot,
            definition=definition,
            schedule=schedule,
            correlation_blocks=env["blocks"],
            evaluation_data=eval_artifact_n1,
        )
        view = eval_artifact_n1.build_evaluation_view(eval_dir_n1)
        evaluator = p3d._predictions_evaluator(view, epsilon=p3f._epsilon(size, seed))
        mat_lane_dir = tmp_path / f"mat-{lane.trajectory.target_size}-{lane.trajectory.optimizer_seed}"
        pred_evidence = run_target_size_direct_boundary_inference(
            trajectory=lane.trajectory,
            materialization=mat,
            boundary_state=snapshot,
            role=role,
            evaluation_data=eval_artifact_n1,
            canonical_frame_authority=env["frame_authority"],
            definition=definition,
            context=env["context"],
            common=env["common"],
            schedule=schedule,
            optimizer_policy=lane.policy,
            extxyz_policy=env["authority"].extxyz_policy,
            frame_catalog=env["frames"],
            frame_data_by_run=env["frame_data_by_run"],
            frame_array_index=env["index"],
            materialization_directory=mat_lane_dir,
            snapshot_root=env["root"],
            evaluation_directory=eval_dir_n1,
            inference_evaluator=evaluator,
        )
        metric_record = run_target_size_eval2_reduction(
            role, eval_artifact_n1, pred_evidence, root_directory=eval_dir_n1
        )
        outcome = evaluate_target_size_boundary(
            role, eval_artifact_n1, pred_evidence, root_directory=eval_dir_n1
        )
        planned_rung, predecessor = p3f._rung_provenance(env, lane.trajectory, n1)
        completion_record = build_target_size_cell_completion_record(
            window=env["window"],
            trajectory=lane.trajectory,
            materialization=mat,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact_n1,
            outcome=outcome,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
            planned_rung=planned_rung,
            schedule=schedule,
            predecessor_continuation=predecessor,
        )
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            lane.trajectory,
            completion_record,
            materialization=mat,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact_n1,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
            planned_rung=planned_rung,
            predecessor_continuation=predecessor,
            restart_authority=env["authority"],
        )

    collected_n1 = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=n1
    )
    batch_n1 = build_complete_boundary_batch(definition, state, collected_n1)
    head_n1 = commit_target_size_boundary_batch(env["root"], definition, state, batch_n1)
    reconciled_n1 = reconcile_target_size_screen_root(env["root"], env["authority"])
    assert reconciled_n1 is not None
    assert reconciled_n1.content_digest == head_n1.content_digest
    authenticated_n1_state = reconciled_n1.post_state

    # Confirm requirements for n2 and select target surviving candidate
    req_n2 = derive_active_boundary_requirements(definition, authenticated_n1_state)
    assert req_n2 is not None
    n2, _eval_size_n2, keys_n2 = req_n2
    assert n2 == schedule.fidelity_epochs[1]
    target_size, optimizer_seed = keys_n2[0]

    resolver = env["authority"].resolver
    progress_file = resolver.progress_path(
        env["window"].content_digest, n1, target_size, optimizer_seed
    )
    orig_progress = resolver.load_progress(progress_file)
    orig_completion = resolver.load_typed_content_addressed(
        resolver.completion_path(n1, orig_progress.completion_record_digest),
        orig_progress.completion_record_digest,
        TargetSizeCellCompletionRecord.from_dict,
    )
    orig_traj = resolver.load_typed_content_addressed(
        resolver.trajectory_path(orig_completion.trajectory_digest),
        orig_completion.trajectory_digest,
        TargetSizeCandidateTrajectory.from_dict,
    )
    orig_mat = resolver.load_typed_content_addressed(
        resolver.materialization_path(orig_completion.materialization_digest),
        orig_completion.materialization_digest,
        TargetSizeCandidateMaterialization.from_dict,
    )
    orig_snap = resolver.load_typed_content_addressed(
        resolver.snapshot_path(orig_completion.boundary_snapshot_digest),
        orig_completion.boundary_snapshot_digest,
        TargetSizeBoundarySnapshot.from_dict,
    )

    # 2.2 Recomputed noncanonical trajectory: ema -> live
    assert env["authority"].seed_neutral_optimizer_policy.ema is True
    tampered_traj_dict = orig_traj.to_dict()
    tampered_traj_dict["evaluation_model_state"] = EVALUATION_MODEL_STATE_LIVE
    tampered_traj_dict.pop("content_digest", None)
    tampered_traj = TargetSizeCandidateTrajectory.from_dict(tampered_traj_dict)
    assert tampered_traj.evaluation_model_state == EVALUATION_MODEL_STATE_LIVE
    assert tampered_traj.content_digest != orig_traj.content_digest
    tampered_traj_path = resolver.trajectory_path(tampered_traj.content_digest)
    tampered_traj_path.parent.mkdir(parents=True, exist_ok=True)
    tampered_traj_path.write_text(
        json.dumps(tampered_traj.to_dict(), sort_keys=True), encoding="utf-8"
    )

    # 2.3 Re-key materialization to tampered trajectory
    tampered_mat_dict = orig_mat.to_dict()
    tampered_mat_dict["trajectory_digest"] = tampered_traj.content_digest
    tampered_mat_dict.pop("content_digest", None)
    tampered_mat = TargetSizeCandidateMaterialization.from_dict(tampered_mat_dict)
    tampered_mat_path = resolver.materialization_path(tampered_mat.content_digest)
    tampered_mat_path.parent.mkdir(parents=True, exist_ok=True)
    tampered_mat_path.write_text(
        json.dumps(tampered_mat.to_dict(), sort_keys=True), encoding="utf-8"
    )

    # 2.4 Re-key snapshot to tampered trajectory and live evaluation state
    tampered_snap_dict = orig_snap.to_dict()
    tampered_snap_dict["trajectory_digest"] = tampered_traj.content_digest
    tampered_snap_dict["evaluation_model_state"] = EVALUATION_MODEL_STATE_LIVE
    tampered_snap_dict.pop("content_digest", None)
    tampered_snap = TargetSizeBoundarySnapshot.from_dict(tampered_snap_dict)
    tampered_snap_path = resolver.snapshot_path(tampered_snap.content_digest)
    tampered_snap_path.parent.mkdir(parents=True, exist_ok=True)
    tampered_snap_path.write_text(
        json.dumps(tampered_snap.to_dict(), sort_keys=True), encoding="utf-8"
    )

    # 2.5 Re-key previous-boundary completion record
    tampered_comp_dict = orig_completion.to_dict()
    tampered_comp_dict["trajectory_digest"] = tampered_traj.content_digest
    tampered_comp_dict["materialization_digest"] = tampered_mat.content_digest
    tampered_comp_dict["boundary_snapshot_digest"] = tampered_snap.content_digest
    tampered_comp_dict.pop("content_digest", None)
    tampered_comp = TargetSizeCellCompletionRecord.from_dict(tampered_comp_dict)
    tampered_comp_path = resolver.completion_path(n1, tampered_comp.content_digest)
    tampered_comp_path.parent.mkdir(parents=True, exist_ok=True)
    tampered_comp_path.write_text(
        json.dumps(tampered_comp.to_dict(), sort_keys=True), encoding="utf-8"
    )

    # 2.6 Re-key progress pointer
    tampered_prog_dict = orig_progress.to_dict()
    tampered_prog_dict["trajectory_digest"] = tampered_traj.content_digest
    tampered_prog_dict["completion_record_digest"] = tampered_comp.content_digest
    tampered_prog_dict.pop("content_digest", None)
    tampered_prog = TargetSizeCandidateOutcome.from_dict(tampered_prog_dict)
    progress_file.write_text(
        json.dumps(tampered_prog.to_dict(), sort_keys=True), encoding="utf-8"
    )

    # 3. Mandatory owner-level negative execution
    fresh_workspace_root = tmp_path / "resume_worker_workspace"
    with pytest.raises(
        TrainingDataInputError,
        match="Trajectory evaluation_model_state 'live' does not match optimizer policy EMA convention 'ema'",
    ):
        resolve_target_size_candidate_for_resume(
            env["root"],
            env["authority"],
            boundary_epoch=n2,
            target_size=target_size,
            optimizer_seed=optimizer_seed,
            state=authenticated_n1_state,
            workspace_root=fresh_workspace_root,
        )

    # 3.2 Failure ordering / no side effects: workspace must not be populated
    assert (
        not fresh_workspace_root.exists()
        or len(list(fresh_workspace_root.iterdir())) == 0
    )


def test_p3a4_checkpoint_parameter_validator_independent_of_evaluation_choice(
    tmp_path: Path,
) -> None:
    """Section B5: TRAIN2 checkpoint parameter validator derives expectations from summary EMA presence."""
    fixture_ema = _fixture(tmp_path / "ema-val", with_ema=True)
    raw_params_ema = [
        fixture_ema["state"][name]
        for name, _ in fixture_ema["model"].named_parameters()
    ]
    # Under EMA: raw parameters equal shadow != live. Validator accepts them based on summary.ema_state_digest
    verify_train2_checkpoint_model_parameters(
        raw_params_ema,
        companion=fixture_ema["companion"],
        summary=fixture_ema["summary"],
    )

    # Corrupt copy where parameter differs from shadow -> rejected
    bad_raw_params_ema = [p.clone() for p in raw_params_ema]
    bad_raw_params_ema[0].reshape(-1)[0] += 1e-3
    with pytest.raises(
        TrainingDataInputError,
        match="checkpoint model parameters do not match the authenticated EMA shadow",
    ):
        verify_train2_checkpoint_model_parameters(
            bad_raw_params_ema,
            companion=fixture_ema["companion"],
            summary=fixture_ema["summary"],
        )

    fixture_live = _fixture(tmp_path / "live-val", with_ema=False)
    raw_params_live = [
        fixture_live["state"][name]
        for name, _ in fixture_live["model"].named_parameters()
    ]
    # Under non-EMA: raw parameters equal live. Validator accepts them based on summary.ema_state_digest is None
    verify_train2_checkpoint_model_parameters(
        raw_params_live,
        companion=fixture_live["companion"],
        summary=fixture_live["summary"],
    )

    # Corrupt copy where parameter differs from live -> rejected
    bad_raw_params_live = [p.clone() for p in raw_params_live]
    bad_raw_params_live[0].reshape(-1)[0] += 1e-3
    with pytest.raises(
        TrainingDataInputError,
        match="checkpoint model parameters do not match the authenticated live",
    ):
        verify_train2_checkpoint_model_parameters(
            bad_raw_params_live,
            companion=fixture_live["companion"],
            summary=fixture_live["summary"],
        )


def test_p3a4_ema_enabled_raw_state_mismatch_rejected(tmp_path: Path) -> None:
    """EMA-enabled raw-state mismatch is rejected before forward (Section B6 #1)."""
    fixture = _fixture(tmp_path, with_ema=True)
    # Corrupt copy of real owner-produced checkpoint
    bad_state = OrderedDict(fixture["state"])
    parameter_name = next(
        name for name in bad_state if name in dict(fixture["model"].named_parameters())
    )
    bad_state[parameter_name] = bad_state[parameter_name].clone()
    bad_state[parameter_name].reshape(-1)[0] += 1.0e-3
    torch.save(
        {"model": bad_state, "optimizer": {}, "lr_scheduler": {}},
        fixture["raw_checkpoint_path"],
    )

    with pytest.raises(TrainingDataInputError, match="checkpoint model parameters"):
        _authenticate(fixture)


def test_p3a4_ema_disabled_raw_state_mismatch_rejected(tmp_path: Path) -> None:
    """EMA-disabled raw-state mismatch is rejected before forward (Section B6 #2)."""
    fixture = _fixture(tmp_path, with_ema=False)
    # Corrupt copy of real owner-produced checkpoint
    bad_state = OrderedDict(fixture["state"])
    parameter_name = next(
        name for name in bad_state if name in dict(fixture["model"].named_parameters())
    )
    bad_state[parameter_name] = bad_state[parameter_name].clone()
    bad_state[parameter_name].reshape(-1)[0] += 1.0e-3
    torch.save(
        {"model": bad_state, "optimizer": {}, "lr_scheduler": {}},
        fixture["raw_checkpoint_path"],
    )

    with pytest.raises(TrainingDataInputError, match="checkpoint model parameters"):
        _authenticate(fixture)


def test_p3a4_altered_live_companion_is_rejected(tmp_path: Path) -> None:
    """Altered live companion is rejected (Section B6 #3)."""
    # 1. Altered live values in companion
    fixture = _fixture(tmp_path / "altered-val", with_ema=False)
    altered_live = [value.clone() for value in fixture["live"]]
    altered_live[0].reshape(-1)[0] += 1.0e-3
    altered_companion = dict(fixture["companion"])
    altered_companion["live_parameters"] = altered_live
    torch.save(altered_companion, fixture["companion_path"])

    with pytest.raises(
        TrainingDataInputError,
        match="(live parameter digest|checkpoint model parameters|live continuation state)",
    ):
        _authenticate(fixture)

    # 2. Altered live cardinality (missing parameter)
    fixture_card = _fixture(tmp_path / "altered-card", with_ema=False)
    altered_companion_card = dict(fixture_card["companion"])
    altered_companion_card["live_parameters"] = list(fixture_card["live"][:-1])
    torch.save(altered_companion_card, fixture_card["companion_path"])

    with pytest.raises(
        TrainingDataInputError,
        match="(cardinality|checkpoint parameter cardinality|live continuation)",
    ):
        _authenticate(fixture_card)

    # 3. Altered live shape
    fixture_shape = _fixture(tmp_path / "altered-shape", with_ema=False)
    bad_shape_live = [value.clone() for value in fixture_shape["live"]]
    bad_shape_live[0] = bad_shape_live[0].unsqueeze(0)
    altered_companion_shape = dict(fixture_shape["companion"])
    altered_companion_shape["live_parameters"] = bad_shape_live
    torch.save(altered_companion_shape, fixture_shape["companion_path"])

    with pytest.raises(
        (TrainingDataInputError, MaceModelStateCompatibilityError),
        match="(shape|checkpoint parameter)",
    ):
        _authenticate(fixture_shape)


def test_p3a4_altered_ema_shadow_is_rejected(tmp_path: Path) -> None:
    """Altered EMA shadow is rejected (Section B6 #4)."""
    # 1. Altered shadow values in companion
    fixture = _fixture(tmp_path / "altered-val", with_ema=True)
    altered_shadow = [value.clone() for value in fixture["shadow"]]
    altered_shadow[0].reshape(-1)[0] += 1.0e-3
    altered_companion = dict(fixture["companion"])
    altered_companion["ema_state"] = {
        **fixture["companion"]["ema_state"],
        "shadow_params": altered_shadow,
    }
    torch.save(altered_companion, fixture["companion_path"])

    with pytest.raises(
        TrainingDataInputError,
        match="(checkpoint model parameters|EMA state digest|EMA shadow)",
    ):
        _authenticate(fixture)

    # 2. Altered shadow cardinality (missing parameter)
    fixture_card = _fixture(tmp_path / "altered-card", with_ema=True)
    altered_companion_card = dict(fixture_card["companion"])
    altered_companion_card["ema_state"] = {
        **fixture_card["companion"]["ema_state"],
        "shadow_params": list(fixture_card["shadow"][:-1]),
    }
    torch.save(altered_companion_card, fixture_card["companion_path"])

    with pytest.raises(
        TrainingDataInputError,
        match="(cardinality|checkpoint parameter cardinality|EMA shadow)",
    ):
        _authenticate(fixture_card)

    # 3. Altered shadow shape
    fixture_shape = _fixture(tmp_path / "altered-shape", with_ema=True)
    bad_shape_shadow = [value.clone() for value in fixture_shape["shadow"]]
    bad_shape_shadow[0] = bad_shape_shadow[0].unsqueeze(0)
    altered_companion_shape = dict(fixture_shape["companion"])
    altered_companion_shape["ema_state"] = {
        **fixture_shape["companion"]["ema_state"],
        "shadow_params": bad_shape_shadow,
    }
    torch.save(altered_companion_shape, fixture_shape["companion_path"])

    with pytest.raises(
        (TrainingDataInputError, MaceModelStateCompatibilityError),
        match="(shape|checkpoint parameter)",
    ):
        _authenticate(fixture_shape)


def test_p3a4_incompatible_real_mace_state_dict_is_rejected_before_forward(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    bad_state = OrderedDict(fixture["state"])
    first_name, first_value = next(iter(bad_state.items()))
    bad_state[first_name] = torch.empty(
        (int(first_value.numel()) + 1,), dtype=first_value.dtype
    )
    torch.save(
        {"model": bad_state, "optimizer": {}, "lr_scheduler": {}},
        fixture["raw_checkpoint_path"],
    )

    with pytest.raises(MaceModelStateCompatibilityError, match="shape"):
        _authenticate(fixture)


def test_p3a4_configuration_rmax_mismatch_is_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    bad_config = dict(fixture["config"])
    bad_architecture = dict(fixture["config"]["mace_architecture"])
    bad_architecture["r_max"] = 3.5
    bad_config["mace_architecture"] = bad_architecture

    with pytest.raises(TrainingDataInputError, match="architecture"):
        _authenticate(fixture, config=bad_config)


def test_p3a4_no_override_rejects_noncontract_checkpoint_without_shell(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    torch.save({"epoch": 0}, fixture["raw_checkpoint_path"])

    with pytest.raises(TrainingDataInputError, match="no-override"):
        _authenticate(fixture, allow_forward_override=False)


def test_p3a4_train2_failure_publication_requires_raw_checkpoint_parent(
    tmp_path: Path,
) -> None:
    env = p3e._env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    requirements = p3e.derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    boundary, _evaluation_size, keys = requirements
    size, seed = keys[0]
    trajectory = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=size,
        optimizer_policy=env["optimizer"],
        optimizer_seed=seed,
    )
    projection = project_target_size_candidate_preparation(env["common"], definition, size)
    materialization = materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=tmp_path / "materialization",
        optimizer_policy=env["optimizer"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_array_index=env["index"],
    )
    plan = target_size_rung_plan(trajectory, env["schedule"], boundary_epoch=boundary)
    failure_dir = tmp_path / "failure-checkpoint"
    failure_dir.mkdir(parents=True, exist_ok=True)
    raw = p3c._raw_checkpoint(failure_dir, 0)
    failure = replace(
        p3c._failure_record(
            trajectory,
            env["schedule"],
            boundary,
            code="train_nonfinite_model_state",
            failed_epoch=0,
            rung_plan=plan,
        ),
        raw_checkpoint_sha256=_sha256(raw),
    )
    predecessor = initial_target_size_continuation_request(trajectory)
    completion = build_target_size_cell_completion_record(
        kind="train2_failure",
        window=env["window"],
        trajectory=trajectory,
        materialization=materialization,
        failure_record=failure,
        planned_rung=plan,
        schedule=env["schedule"],
        definition=definition,
        predecessor_continuation=predecessor,
        checkpoint_directory=failure_dir,
    )
    resolver = env["authority"].resolver
    completion_path = resolver.completion_path(boundary, completion.content_digest)
    progress_path = resolver.progress_path(
        env["window"].content_digest, boundary, size, seed
    )

    with pytest.raises(TrainingDataInputError, match="raw checkpoint"):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion,
            materialization=materialization,
            failure_record=failure,
            planned_rung=plan,
            predecessor_continuation=predecessor,
            restart_authority=env["authority"],
        )
    assert not completion_path.exists()
    assert not progress_path.exists()

    first = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion,
        materialization=materialization,
        failure_record=failure,
        planned_rung=plan,
        predecessor_continuation=predecessor,
        failure_checkpoint_directory=failure_dir,
        restart_authority=env["authority"],
    )
    retry = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion,
        restart_authority=env["authority"],
    )
    assert retry == first


def test_p3a4_eval2_failure_publication_requires_prediction_parent(
    tmp_path: Path,
) -> None:
    env = p3e._env(tmp_path)
    state = env["aggregate"].reducer_state
    requirements = p3e.derive_active_boundary_requirements(
        env["aggregate"].definition, state
    )
    assert requirements is not None
    boundary, _evaluation_size, keys = requirements
    (
        trajectory,
        role,
        snapshot,
        _success_completion,
        materialization,
        eval_artifact,
        prediction,
        _metric,
    ) = p3e._execute_candidate_boundary(env, tmp_path, keys[0][0], keys[0][1], boundary)
    failure = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "bounded final-review publication fixture",
        target_role_digest=role.content_digest,
        prediction_digest=prediction.prediction_payload_digest,
    )
    planned_rung, predecessor = p3e._rung_provenance(
        env, trajectory, boundary
    )
    completion = build_target_size_cell_completion_record(
        kind="eval2_failure",
        window=env["window"],
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=prediction,
        failure_record=failure,
        outcome=translate_target_size_eval2_failure(role, failure),
        planned_rung=planned_rung,
        schedule=env["schedule"],
        predecessor_continuation=predecessor,
    )
    resolver = env["authority"].resolver
    completion_path = resolver.completion_path(boundary, completion.content_digest)
    progress_path = resolver.progress_path(
        env["window"].content_digest,
        boundary,
        trajectory.target_size,
        trajectory.optimizer_seed,
    )

    with pytest.raises(TrainingDataInputError, match="prediction"):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            failure_record=failure,
            planned_rung=planned_rung,
            predecessor_continuation=predecessor,
            restart_authority=env["authority"],
        )
    assert not completion_path.exists()
    assert not progress_path.exists()

    first = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=prediction,
        failure_record=failure,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor,
        restart_authority=env["authority"],
    )
    retry = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion,
        restart_authority=env["authority"],
    )
    assert retry == first


def test_p3a4_publication_requires_exact_rung_and_predecessor_parents(
    tmp_path: Path,
) -> None:
    """Missing rung or later-rung ancestry fails before completion/progress."""

    for case, boundary, omit in (
        ("missing-rung", 1, "planned_rung"),
        ("missing-predecessor", 3, "predecessor_continuation"),
    ):
        root = tmp_path / case
        root.mkdir(parents=True, exist_ok=True)
        env = p3e._env(root)
        requirements = p3e.derive_active_boundary_requirements(
            env["aggregate"].definition, env["aggregate"].reducer_state
        )
        assert requirements is not None
        size, seed = requirements[2][0]
        (
            trajectory,
            role,
            snapshot,
            completion,
            materialization,
            eval_artifact,
            prediction,
            metric,
        ) = p3e._execute_candidate_boundary(
            env, root, size, seed, boundary
        )
        planned_rung, predecessor = p3e._rung_provenance(
            env, trajectory, boundary
        )
        kwargs = {
            "materialization": materialization,
            "boundary_snapshot": snapshot,
            "eval2_role": role,
            "evaluation_data": eval_artifact,
            "prediction_evidence": prediction,
            "eval2_metric_record": metric,
            "planned_rung": planned_rung,
            "predecessor_continuation": predecessor,
            "restart_authority": env["authority"],
        }
        kwargs[omit] = None
        completion_path = env["authority"].resolver.completion_path(
            boundary, completion.content_digest
        )
        progress_path = env["authority"].resolver.progress_path(
            env["window"].content_digest,
            boundary,
            trajectory.target_size,
            trajectory.optimizer_seed,
        )
        with pytest.raises(TrainingDataInputError):
            record_candidate_boundary_outcome(
                env["root"], env["window"], trajectory, completion, **kwargs
            )
        assert not completion_path.exists()
        assert not progress_path.exists()


def test_p3a4_publication_rejects_foreign_eval2_error_prediction_link(
    tmp_path: Path,
) -> None:
    env = p3e._env(tmp_path)
    requirements = p3e.derive_active_boundary_requirements(
        env["aggregate"].definition, env["aggregate"].reducer_state
    )
    assert requirements is not None
    boundary, _evaluation_size, keys = requirements
    (
        trajectory,
        role,
        snapshot,
        _success_completion,
        materialization,
        eval_artifact,
        prediction,
        _metric,
    ) = p3e._execute_candidate_boundary(
        env, tmp_path, keys[0][0], keys[0][1], boundary
    )
    linked_failure = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "foreign-link publication fixture",
        target_role_digest=role.content_digest,
        prediction_digest=prediction.prediction_payload_digest,
    )
    planned_rung, predecessor = p3e._rung_provenance(
        env, trajectory, boundary
    )
    valid_completion = build_target_size_cell_completion_record(
        kind="eval2_failure",
        window=env["window"],
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=prediction,
        failure_record=linked_failure,
        outcome=translate_target_size_eval2_failure(role, linked_failure),
        planned_rung=planned_rung,
        schedule=env["schedule"],
        predecessor_continuation=predecessor,
    )
    foreign_failure = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "foreign-link publication fixture",
        target_role_digest=role.content_digest,
        prediction_digest="0" * 64,
    )
    foreign_outcome = translate_target_size_eval2_failure(role, foreign_failure)
    completion = replace(
        valid_completion,
        failure_record_digest=foreign_failure.content_digest,
        outcome=foreign_outcome,
        outcome_digest=foreign_outcome.content_digest,
    )
    completion_path = env["authority"].resolver.completion_path(
        boundary, completion.content_digest
    )
    progress_path = env["authority"].resolver.progress_path(
        env["window"].content_digest,
        boundary,
        trajectory.target_size,
        trajectory.optimizer_seed,
    )
    with pytest.raises(TrainingDataInputError, match="prediction"):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=prediction,
            failure_record=foreign_failure,
            planned_rung=planned_rung,
            predecessor_continuation=predecessor,
            restart_authority=env["authority"],
        )
    assert not completion_path.exists()
    assert not progress_path.exists()
