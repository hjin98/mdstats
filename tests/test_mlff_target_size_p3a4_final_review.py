"""Final-review P3A4 evidence for real MACE reconstruction and authentication."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace

import ase
import pytest
import torch
from torch_ema import ExponentialMovingAverage

import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3e as p3e
from mdstats.training_data._common import TrainingDataInputError, digest
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
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    initial_target_size_continuation_request,
    materialize_target_size_candidate,
    promote_target_size_boundary_snapshot,
    record_candidate_boundary_outcome,
    run_target_size_direct_boundary_inference,
    target_size_rung_plan,
    translate_target_size_eval2_failure,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.train2_runtime import (
    TRAIN2_RUNTIME_COMPANION_SCHEMA,
    _tensor_state_digest,
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
    evaluation_model_state: str = EVALUATION_MODEL_STATE_LIVE,
):
    config = _configuration()
    model = build_mace_model_from_configuration(config)
    architecture_digest = mace_model_execution_architecture_digest(model)
    tmp_path.mkdir(parents=True, exist_ok=True)
    raw_checkpoint_path = tmp_path / "checkpoint-epoch-0.pt"

    if with_ema or evaluation_model_state == EVALUATION_MODEL_STATE_EMA:
        ema = ExponentialMovingAverage(model.parameters(), decay=0.9)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.05)
        ema.update()
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.add_(0.10)

        with ema.average_parameters():
            state = OrderedDict(
                (str(name), value.detach().cpu().clone())
                for name, value in model.state_dict().items()
            )
            torch.save(
                {
                    "model": state,
                    "optimizer": {},
                    "lr_scheduler": {},
                },
                raw_checkpoint_path,
            )

        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = [value.detach().cpu().clone() for value in ema.shadow_params]

        # Section 4.5 anti-proxy invariant
        assert not all(
            torch.equal(l, s) for l, s in zip(live, shadow, strict=True)
        ), "Fixture invariant failed: live parameters must differ from EMA shadow"
        state_params = [
            state[name] for name, _ in model.named_parameters()
        ]
        assert all(
            torch.equal(r, s) for r, s in zip(state_params, shadow, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must equal EMA shadow"
        assert not all(
            torch.equal(r, l) for r, l in zip(state_params, live, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must differ from live state"
        assert all(
            torch.equal(m.detach().cpu(), l)
            for m, l in zip(model.parameters(), live, strict=True)
        ), "Fixture invariant failed: model parameters must return to live state outside context"

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
        state = OrderedDict(
            (str(name), value.detach().cpu().clone())
            for name, value in model.state_dict().items()
        )
        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = None
        ema_state = None
        ema_digest = None
        torch.save(
            {
                "model": state,
                "optimizer": {},
                "lr_scheduler": {},
            },
            raw_checkpoint_path,
        )

    companion = {
        "schema": TRAIN2_RUNTIME_COMPANION_SCHEMA,
        "live_parameters": live,
        "ema_state": ema_state,
        "rng_state": {},
        "model_architecture_digest": architecture_digest,
    }
    companion_path = tmp_path / "checkpoint-epoch-0-companion.pt"
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
        "state": state,
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
    """Real MACE EMA checkpoint-semantics reproducer (Section 4.1).

    Proves that:
    1. A real MACE model reconstructed through candidate config with real EMA
       has divergent live vs shadow parameter states.
    2. Saving under real ``ema.average_parameters()`` produces checkpoint model
       parameters equal to the EMA shadow, differing from live parameters.
    3. Exiting ``ema.average_parameters()`` restores live parameters.
    4. The production target-size provider authentication path authenticates the
       raw checkpoint parameters against the EMA shadow, restores the provider
       to the authenticated live state, and tiny CPU forward succeeds with no override.
    """
    fixture = _fixture(
        tmp_path, with_ema=True, evaluation_model_state=EVALUATION_MODEL_STATE_LIVE
    )

    provider, evaluated_digest, _companion = _authenticate(
        fixture, allow_forward_override=False
    )

    assert isinstance(provider, MaceCalculatorProvider)
    assert not isinstance(provider.model, _AuthenticatedParameterShell)
    assert provider.model is provider._calculator.models[0]
    assert provider.runtime_architecture_digest
    assert evaluated_digest == fixture["summary"].live_parameter_digest
    assert all(
        torch.equal(p.detach().cpu(), l)
        for p, l in zip(provider.model.parameters(), fixture["live"], strict=True)
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
    evaluation_model_state: str,
) -> None:
    env = p3e._env(tmp_path)
    definition = env["aggregate"].definition
    requirements = p3e.derive_active_boundary_requirements(
        definition, env["aggregate"].reducer_state
    )
    assert requirements is not None
    boundary, evaluation_size, keys = requirements
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
    if trajectory.evaluation_model_state != evaluation_model_state:
        trajectory = replace(trajectory, evaluation_model_state=evaluation_model_state)
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
        optimizer_policy=env["optimizer"],
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
    raw_checkpoint_path = checkpoint_directory / "model_run-7_epoch-0.pt"

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
            state = OrderedDict(
                (str(name), value.detach().cpu().clone())
                for name, value in model.state_dict().items()
            )
            torch.save(
                {"model": state, "optimizer": {}, "lr_scheduler": {}},
                raw_checkpoint_path,
            )

        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = [value.detach().cpu().clone() for value in ema.shadow_params]

        assert not all(
            torch.equal(l, s) for l, s in zip(live, shadow, strict=True)
        ), "Fixture invariant failed: live parameters must differ from EMA shadow"
        state_params = [state[name] for name, _ in model.named_parameters()]
        assert all(
            torch.equal(r, s) for r, s in zip(state_params, shadow, strict=True)
        ), "Fixture invariant failed: checkpoint parameters must equal EMA shadow"

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
        state = OrderedDict(
            (str(name), value.detach().cpu().clone())
            for name, value in model.state_dict().items()
        )
        live = [parameter.detach().cpu().clone() for parameter in model.parameters()]
        shadow = None
        ema_state = None
        ema_digest = None
        torch.save(
            {"model": state, "optimizer": {}, "lr_scheduler": {}},
            raw_checkpoint_path,
        )

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
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
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

    if evaluation_model_state == EVALUATION_MODEL_STATE_EMA:
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


def test_p3a4_real_mace_no_override_direct_inference_live_with_ema_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production direct inference: LIVE evaluation with EMA enabled in TRAIN2 (Section 4.2)."""
    _run_direct_inference_test(
        tmp_path,
        monkeypatch,
        with_ema=True,
        evaluation_model_state=EVALUATION_MODEL_STATE_LIVE,
    )


def test_p3a4_real_mace_no_override_direct_inference_ema_with_divergent_shadow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production direct inference: EMA evaluation with divergent shadow (Section 4.3)."""
    _run_direct_inference_test(
        tmp_path,
        monkeypatch,
        with_ema=True,
        evaluation_model_state=EVALUATION_MODEL_STATE_EMA,
    )


def test_p3a4_ema_enabled_raw_state_mismatch_rejected(tmp_path: Path) -> None:
    """EMA-enabled raw-state mismatch is rejected before forward (Section 4.4 #1)."""
    fixture = _fixture(
        tmp_path, with_ema=True, evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
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
    """EMA-disabled raw-state mismatch is rejected before forward (Section 4.4 #2)."""
    fixture = _fixture(
        tmp_path, with_ema=False, evaluation_model_state=EVALUATION_MODEL_STATE_LIVE
    )
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
    """Altered live companion is rejected (Section 4.4 #3)."""
    fixture = _fixture(tmp_path, with_ema=True)
    altered_live = [value.clone() for value in fixture["live"]]
    altered_live[0].reshape(-1)[0] += 1.0e-3
    altered_companion = dict(fixture["companion"])
    altered_companion["live_parameters"] = altered_live
    torch.save(altered_companion, fixture["companion_path"])

    with pytest.raises(TrainingDataInputError, match="live parameter digest"):
        _authenticate(fixture)


def test_p3a4_altered_ema_shadow_is_rejected(tmp_path: Path) -> None:
    """Altered EMA shadow is rejected (Section 4.4 #4)."""
    # 1. Altered shadow values in companion
    fixture = _fixture(
        tmp_path / "altered-val", with_ema=True, evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
    altered_shadow = [value.clone() for value in fixture["shadow"]]
    altered_shadow[0].reshape(-1)[0] += 1.0e-3
    altered_companion = dict(fixture["companion"])
    altered_companion["ema_state"] = {
        **fixture["companion"]["ema_state"],
        "shadow_params": altered_shadow,
    }
    torch.save(altered_companion, fixture["companion_path"])

    with pytest.raises(TrainingDataInputError, match="(checkpoint model parameters|EMA state digest|EMA shadow)"):
        _authenticate(fixture)

    # 2. Altered shadow cardinality (missing parameter)
    fixture_card = _fixture(
        tmp_path / "altered-card", with_ema=True, evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
    altered_companion_card = dict(fixture_card["companion"])
    altered_companion_card["ema_state"] = {
        **fixture_card["companion"]["ema_state"],
        "shadow_params": list(fixture_card["shadow"][:-1]),
    }
    torch.save(altered_companion_card, fixture_card["companion_path"])

    with pytest.raises(TrainingDataInputError, match="(cardinality|checkpoint parameter cardinality|EMA shadow)"):
        _authenticate(fixture_card)

    # 3. Altered shadow shape
    fixture_shape = _fixture(
        tmp_path / "altered-shape", with_ema=True, evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
    bad_shape_shadow = [value.clone() for value in fixture_shape["shadow"]]
    bad_shape_shadow[0] = bad_shape_shadow[0].unsqueeze(0)
    altered_companion_shape = dict(fixture_shape["companion"])
    altered_companion_shape["ema_state"] = {
        **fixture_shape["companion"]["ema_state"],
        "shadow_params": bad_shape_shadow,
    }
    torch.save(altered_companion_shape, fixture_shape["companion_path"])

    with pytest.raises((TrainingDataInputError, MaceModelStateCompatibilityError), match="(shape|checkpoint parameter)"):
        _authenticate(fixture_shape)


def test_p3a4_checkpoint_semantics_independent_of_evaluation_choice(
    tmp_path: Path,
) -> None:
    """Raw checkpoint expectations depend on TRAIN2 EMA state, not EVAL2 choice (Section 4.4 #5)."""
    live_eval_fixture = _fixture(
        tmp_path / "live-eval",
        with_ema=True,
        evaluation_model_state=EVALUATION_MODEL_STATE_LIVE,
    )
    provider_live, digest_live, _ = _authenticate(live_eval_fixture)
    assert digest_live == live_eval_fixture["summary"].live_parameter_digest
    assert all(
        torch.equal(p.detach().cpu(), l)
        for p, l in zip(
            provider_live.model.parameters(),
            live_eval_fixture["live"],
            strict=True,
        )
    )

    ema_eval_fixture = dict(live_eval_fixture)
    ema_eval_fixture["trajectory"] = SimpleNamespace(
        evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
    provider_ema, digest_ema, _ = _authenticate(ema_eval_fixture)
    assert digest_ema == live_eval_fixture["summary"].ema_state_digest
    assert all(
        torch.equal(p.detach().cpu(), s)
        for p, s in zip(
            provider_ema.model.parameters(),
            live_eval_fixture["shadow"],
            strict=True,
        )
    )

    bad_checkpoint_fixture = _fixture(
        tmp_path / "bad-raw",
        with_ema=True,
        evaluation_model_state=EVALUATION_MODEL_STATE_LIVE,
    )
    live_param_state = OrderedDict(bad_checkpoint_fixture["state"])
    for (name, _), live_val in zip(
        bad_checkpoint_fixture["model"].named_parameters(),
        bad_checkpoint_fixture["live"],
        strict=True,
    ):
        live_param_state[name] = live_val.clone()
    torch.save(
        {"model": live_param_state, "optimizer": {}, "lr_scheduler": {}},
        bad_checkpoint_fixture["raw_checkpoint_path"],
    )

    with pytest.raises(TrainingDataInputError, match="checkpoint model parameters"):
        _authenticate(bad_checkpoint_fixture)

    bad_checkpoint_fixture["trajectory"] = SimpleNamespace(
        evaluation_model_state=EVALUATION_MODEL_STATE_EMA
    )
    with pytest.raises(TrainingDataInputError, match="checkpoint model parameters"):
        _authenticate(bad_checkpoint_fixture)


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
