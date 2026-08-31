from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _template(profile: str) -> dict:
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay-train.xyz",
        replay_monitor="replay-monitor.xyz",
        precision_profile=profile,
    )
    return tomllib.loads(text)




def test_canonical_profiles_generate_binary_model_dtypes_without_staged_schedule() -> None:
    single = _template("single")
    double = _template("double")

    assert (single["model"]["dtype"], single["training"]["dtype"], single["evaluation"]["dtype"],
            single["verification"]["dtype"], single["export"]["dtype"]) == ("float32",) * 5
    assert "precision" not in single["training"]
    assert (double["model"]["dtype"], double["training"]["dtype"], double["evaluation"]["dtype"],
            double["verification"]["dtype"], double["export"]["dtype"]) == ("float64",) * 5
    assert "precision" not in double["training"]

    with pytest.raises(campaign_cli.CampaignCliError, match="retired"):
        _template("refine")


def test_canonical_single_critical_policy_is_fp64():
    policy = mdstats.canonical_precision_schedule_policy("single")
    optimizer = mdstats.MaceOptimizerPolicy(
        default_dtype="float32",
        critical_precision_policy=mdstats.MaceCriticalPrecisionPolicy.for_dtype(
            policy.critical_operation_dtype
        ),
        precision_schedule_policy=policy,
    )
    assert optimizer.critical_precision_policy.canonical_dtype == "float64"
    assert optimizer.critical_precision_policy.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1"


def test_precision_schedule_rejects_critical_policy_dtype_mismatch() -> None:
    policy = mdstats.canonical_precision_schedule_policy("single")
    with pytest.raises(mdstats.TrainingDataInputError, match="critical-precision policy dtype"):
        mdstats.MaceOptimizerPolicy(
            default_dtype="float32",
            precision_schedule_policy=policy,
            critical_precision_policy=mdstats.MaceCriticalPrecisionPolicy.for_dtype("float32"),
        )

def test_refine_30_epochs_resolves_to_24_plus_6_and_update_bounds() -> None:
    policy = mdstats.canonical_precision_schedule_policy("refine")
    resolved = policy.resolve(max_num_epochs=30, updates_per_epoch=5223, require_update_floor=True)
    assert [stage.epoch_count for stage in resolved.stages] == [24, 6]
    assert [stage.dtype for stage in resolved.stages] == ["float32", "float64"]
    assert resolved.stages[0].start_update == 0
    assert resolved.stages[0].stop_update == 24 * 5223
    assert resolved.stages[1].start_update == 24 * 5223
    assert resolved.stages[1].stop_update == 30 * 5223
    assert resolved.stages[1].update_count == 6 * 5223
    assert mdstats.ResolvedPrecisionSchedule.from_dict(resolved.to_dict()) == resolved


def test_refinement_floor_expands_deterministically_and_fails_closed() -> None:
    policy = mdstats.canonical_precision_schedule_policy("refine")
    # 12 epochs nominally gives 9/3. A 15k update floor at 3000 updates/epoch
    # expands the final stage to five epochs while retaining a nonempty FP32 stage.
    resolved = policy.resolve(max_num_epochs=12, updates_per_epoch=3000, require_update_floor=True)
    assert [stage.epoch_count for stage in resolved.stages] == [7, 5]
    with pytest.raises(mdstats.TrainingDataInputError, match="cannot satisfy"):
        policy.resolve(max_num_epochs=4, updates_per_epoch=3000, require_update_floor=True)
    with pytest.raises(mdstats.TrainingDataInputError, match="without updates_per_epoch"):
        policy.resolve(max_num_epochs=30, require_update_floor=True)


def test_canonical_refine_small_exposure_preserves_nominal_tail_when_reference_update_floor_is_impossible() -> None:
    policy = mdstats.canonical_precision_schedule_policy("refine")
    # Default n512 target-only fine tuning with batch_size=2 has about 256
    # updates/epoch.  The entire 30-epoch budget therefore contains fewer than
    # 15k updates, so the replay-calibrated reference floor cannot be literal.
    # The canonical profile must remain usable and retain its explicit 24/6
    # schedule because the nominal FP64 tail already exceeds the hard 3-epoch
    # floor.  The resolved contract records the achievable effective floor.
    resolved = policy.resolve(max_num_epochs=30, updates_per_epoch=256, require_update_floor=True)
    assert [stage.epoch_count for stage in resolved.stages] == [24, 6]
    assert resolved.stages[-1].update_count == 1536
    assert resolved.minimum_final_stage_gradient_updates == 1536
    assert policy.minimum_final_stage_gradient_updates == 15000


def test_require_update_floor_false_really_disables_update_floor() -> None:
    policy = mdstats.canonical_precision_schedule_policy("refine")
    resolved = policy.resolve(max_num_epochs=30, updates_per_epoch=1000, require_update_floor=False)
    assert [stage.epoch_count for stage in resolved.stages] == [24, 6]


def test_custom_infeasible_update_floor_remains_fail_closed() -> None:
    policy = mdstats.PrecisionSchedulePolicy(
        requested_profile="custom",
        stages=(
            mdstats.PrecisionStage("float32", 0.80, 1.0),
            mdstats.PrecisionStage("float64", 0.20, 0.5),
        ),
        minimum_final_stage_epochs=3,
        minimum_final_stage_gradient_updates=15000,
        model_dtype="float64",
        critical_operation_dtype="float64",
        evaluation_dtype="float64",
        verification_dtype="float64",
        export_dtype="float64",
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="maximum_feasible_final_stage_updates"):
        policy.resolve(max_num_epochs=30, updates_per_epoch=256, require_update_floor=True)


def _protocol(schedule: mdstats.PrecisionSchedulePolicy) -> mdstats.TrainingProtocolIdentity:
    optimizer = mdstats.MaceOptimizerPolicy(
        max_num_epochs=30,
        default_dtype=schedule.stages[0].dtype,
        precision_schedule_policy=schedule,
    )
    resolved = schedule.resolve(max_num_epochs=30, updates_per_epoch=1000)
    return mdstats.TrainingProtocolIdentity(
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        foundation_checkpoint=mdstats.FoundationCheckpointIdentity(
            reference="foundation.model", sha256="0" * 64
        ),
        compatibility_probe_digest="1" * 64,
        data7_bundle_digest="2" * 64,
        target_train_artifact_digest="3" * 64,
        target_valid_artifact_digest="4" * 64,
        replay_plan_digest=None,
        training_objective_policy_digest="5" * 64,
        configuration_weight_policy_digest="6" * 64,
        checkpoint_metric_policy_digest="7" * 64,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        optimizer_policy=optimizer,
        selection_size=512,
        resolved_precision_schedule=resolved,
    )


def test_resolved_schedule_is_training_protocol_identity() -> None:
    default = mdstats.canonical_precision_schedule_policy("refine")
    custom = mdstats.PrecisionSchedulePolicy(
        requested_profile="refine",
        stages=(
            mdstats.PrecisionStage("float32", 0.90, 1.0),
            mdstats.PrecisionStage("float64", 0.10, 0.5),
        ),
        minimum_final_stage_epochs=3,
        minimum_final_stage_gradient_updates=0,
        model_dtype="float64",
        critical_operation_dtype="float64",
        evaluation_dtype="float64",
        verification_dtype="float64",
        export_dtype="float64",
    )
    a = _protocol(default)
    b = _protocol(custom)
    assert a.content_digest != b.content_digest
    assert a.optimizer_policy.policy_digest != b.optimizer_policy.policy_digest
    assert mdstats.TrainingProtocolIdentity.from_dict(a.to_dict()) == a


def test_legacy_optimizer_serialization_remains_v4_and_maps_losslessly() -> None:
    legacy_optimizer = mdstats.MaceOptimizerPolicy(default_dtype="float32", num_workers=3)
    payload = legacy_optimizer.to_dict()
    assert payload["schema"] == "mdstats.mace-optimizer-policy.v4"
    assert "precision_schedule_policy" not in payload
    assert mdstats.MaceOptimizerPolicy.from_dict(payload) == legacy_optimizer

    mapped = mdstats.legacy_one_stage_precision_policy(
        training_dtype="float32",
        model_dtype="float32",
        critical_operation_dtype="float64",
        evaluation_dtype="float32",
        verification_dtype="float32",
        export_dtype="float32",
    )
    assert mapped.requested_profile == "legacy_custom"
    assert mapped.stages == (mdstats.PrecisionStage("float32", 1.0, 1.0),)
    assert mapped.critical_operation_dtype == "float64"




