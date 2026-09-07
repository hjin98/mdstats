"""Historical DATA8 MACE records remain readable but never become current evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from mdstats.training_data.data8_bundle import (
    DATA8_PREPARATION_BUNDLE_SCHEMA,
    DATA8_PREPARATION_BUNDLE_V3_SCHEMA,
    MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION,
    Data8PreparationBundle,
)
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.foundation import FoundationCheckpointIdentity
from mdstats.training_data.mace_export import MaceExtxyzArtifact
from mdstats.training_data.mace_compatibility import (
    MACE_EXECUTION_SEMANTICS_VERSION,
    MaceCheckpointControlPolicy,
    MaceCompatibilityPolicy,
    MaceExposureBackend,
    MaceLoaderDryRun,
    MaceSourceProbe,
    emulate_mace_v0316_loader_dry_run,
)
from mdstats.training_data.protocol import (
    MaceJobArtifact,
    MaceJobKind,
    MaceOptimizerPolicy,
    TrainingMode,
    TrainingProtocolIdentity,
)
from mdstats.training_data.replay import ReplayMode, ReplayPreparationPlan


_FIXTURE = Path(__file__).parent / "fixtures" / "mace_compatibility_v1.json"


def _historical_records() -> tuple[dict, dict, MaceCompatibilityPolicy, MaceSourceProbe]:
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    policy_payload = payload["policy"]
    probe_payload = payload["probe"]
    policy = MaceCompatibilityPolicy.from_dict(policy_payload)
    probe = MaceSourceProbe.from_dict(probe_payload)
    return policy_payload, probe_payload, policy, probe


def test_exact_pre_repair_v1_payloads_round_trip_without_current_fields() -> None:
    policy_payload, probe_payload, policy, probe = _historical_records()

    assert policy.to_dict() == policy_payload
    assert probe.to_dict() == probe_payload
    assert policy.policy_digest == probe.policy_digest
    assert policy.execution_semantics_version is None
    assert not policy.current_execution_compatible
    assert not probe.current_execution_compatible
    assert "execution_semantics_version" not in policy.to_dict()
    assert "multihead_forced_universal_loss_present" not in probe.to_dict()
    assert "target_combined_loader_drop_last_present" not in probe.to_dict()


def test_historical_digest_tampering_is_rejected() -> None:
    policy_payload, probe_payload, _policy, _probe = _historical_records()

    tampered_policy = copy.deepcopy(policy_payload)
    tampered_policy["release_commit"] = "changed"
    with pytest.raises(TrainingDataSerializationError):
        MaceCompatibilityPolicy.from_dict(tampered_policy)

    tampered_probe = copy.deepcopy(probe_payload)
    tampered_probe["dry_run_supported"] = False
    with pytest.raises(TrainingDataSerializationError):
        MaceSourceProbe.from_dict(tampered_probe)


def test_historical_probe_cannot_authorize_loader_execution() -> None:
    _policy_payload, _probe_payload, _policy, probe = _historical_records()

    with pytest.raises(TrainingDataInputError, match="historical|current fixed-file"):
        emulate_mace_v0316_loader_dry_run(
            compatibility_probe=probe,
            target_train_count=2,
            target_validation_count=1,
        )


def test_data8_readability_and_current_execution_authority_are_separate() -> None:
    _policy_payload, _probe_payload, policy, probe = _historical_records()

    # The method is deliberately exercised at the existing DATA8 value-object
    # owner without constructing unrelated artifact graphs.  from_dict routes
    # the nested records through the same method-owned compatibility objects.
    bundle = object.__new__(Data8PreparationBundle)
    object.__setattr__(bundle, "compatibility_policy", policy)
    object.__setattr__(bundle, "compatibility_probe", probe)
    with pytest.raises(TrainingDataInputError, match="Historical DATA8"):
        bundle.require_current_mace_execution_compatibility()


def _historical_data8_v5_payload() -> dict:
    """Build a valid outer bundle while retaining the exact nested v1 records."""

    policy_payload, probe_payload, policy, probe = _historical_records()
    train_uid = "1" * 64
    valid_uid = "2" * 64
    train = MaceExtxyzArtifact(
        role="target_train",
        relative_path="target-train.extxyz",
        sha256="3" * 64,
        configuration_count=1,
        frame_uids=(train_uid,),
        atomic_numbers=(1,),
        policy_digest="4" * 64,
        sidecar_relative_path="target-train.extxyz.manifest.json",
        sidecar_sha256="5" * 64,
        sidecar_digest="6" * 64,
    )
    valid = MaceExtxyzArtifact(
        role="target_valid",
        relative_path="target-valid.extxyz",
        sha256="7" * 64,
        configuration_count=1,
        frame_uids=(valid_uid,),
        atomic_numbers=(1,),
        policy_digest="8" * 64,
        sidecar_relative_path="target-valid.extxyz.manifest.json",
        sidecar_sha256="9" * 64,
        sidecar_digest="a" * 64,
    )
    replay_plan = ReplayPreparationPlan(mode=ReplayMode.NONE)
    optimizer = MaceOptimizerPolicy(
        device="cpu",
        default_dtype="float32",
        max_num_epochs=1,
    )
    protocol = TrainingProtocolIdentity(
        training_mode=TrainingMode.NAIVE_FINE_TUNING,
        foundation_checkpoint=FoundationCheckpointIdentity(
            reference="foundation.model",
            sha256="b" * 64,
        ),
        compatibility_probe_digest=probe.content_digest,
        data7_bundle_digest="c" * 64,
        target_train_artifact_digest=train.content_digest,
        target_valid_artifact_digest=valid.content_digest,
        replay_plan_digest=None,
        training_objective_policy_digest="d" * 64,
        configuration_weight_policy_digest="e" * 64,
        checkpoint_metric_policy_digest="f" * 64,
        checkpoint_control_policy=MaceCheckpointControlPolicy(),
        optimizer_policy=optimizer,
        selection_size=1,
    )
    loader = MaceLoaderDryRun(
        compatibility_probe_digest=probe.content_digest,
        exposure_backend=MaceExposureBackend.NATIVE_MACE_FIXED,
        target_head_name="target_head",
        replay_head_name=None,
        head_order=("target_head",),
        validation_head_order=("target_head",),
        native_checkpoint_head="target_head",
        target_train_count_exported=1,
        target_train_count_effective=1,
        replay_train_count_exported=0,
        replay_train_count_effective=0,
        real_pt_data_ratio_threshold=0.0,
        implicit_target_duplication_factor=1,
        target_validation_count=1,
        replay_validation_count=0,
        dry_run_command=("mace_run_train", "--dry_run"),
    )
    job = MaceJobArtifact(
        job_id="historical-final",
        kind=MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        relative_directory="final",
        config_relative_path="final/config.yaml",
        config_sha256="1" * 64,
        command_relative_path="final/command.json",
        command_sha256="2" * 64,
        target_train_artifact_digest=train.content_digest,
        target_valid_artifact_digest=valid.content_digest,
        fold_evaluation_artifact_digest=None,
        replay_plan_digest=None,
        protocol=protocol,
        loader_dry_run=loader,
    )
    bundle = Data8PreparationBundle(
        dataset_id="historical-data8",
        source_catalog_digest="3" * 64,
        frame_catalog_digest="4" * 64,
        data5_bundle_digest="5" * 64,
        compatibility_policy=policy,
        compatibility_probe=probe,
        replay_plan=replay_plan,
        jobs=(job,),
        target_artifacts=(train, valid),
        fold_evaluation_artifacts=(),
        sealed_outer_evaluations=(),
        output_directory="data8",
    )
    payload = bundle.to_dict()
    # Assert that this helper has not accidentally replaced the exact fixture
    # records with current constructors before returning the serialized case.
    assert payload["compatibility_policy"] == policy_payload
    assert payload["compatibility_probe"] == probe_payload
    assert payload["schema"] == DATA8_PREPARATION_BUNDLE_SCHEMA
    return payload


def test_historical_data8_v5_digest_and_supported_outer_schema_round_trip() -> None:
    historical_v5 = _historical_data8_v5_payload()
    restored = Data8PreparationBundle.from_dict(historical_v5)

    assert restored.to_dict() == historical_v5
    assert restored.content_digest == historical_v5["content_digest"]
    assert restored.compatibility_policy.to_dict() == historical_v5["compatibility_policy"]
    assert restored.compatibility_probe.to_dict() == historical_v5["compatibility_probe"]
    with pytest.raises(TrainingDataInputError, match="Historical DATA8"):
        restored.require_current_mace_execution_compatibility()

    older_outer = copy.deepcopy(historical_v5)
    older_outer["schema"] = DATA8_PREPARATION_BUNDLE_V3_SCHEMA
    older_outer["parser_version"] = MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION
    older_outer["content_digest"] = digest(
        {key: value for key, value in older_outer.items() if key != "content_digest"}
    )
    older_restored = Data8PreparationBundle.from_dict(older_outer)
    assert older_restored.compatibility_policy.to_dict() == historical_v5["compatibility_policy"]
    assert older_restored.compatibility_probe.to_dict() == historical_v5["compatibility_probe"]

    outer_tamper = copy.deepcopy(historical_v5)
    outer_tamper["dataset_id"] = "tampered"
    with pytest.raises(TrainingDataSerializationError):
        Data8PreparationBundle.from_dict(outer_tamper)

    nested_tamper = copy.deepcopy(historical_v5)
    nested_tamper["compatibility_probe"]["dry_run_supported"] = False
    with pytest.raises(TrainingDataSerializationError):
        Data8PreparationBundle.from_dict(nested_tamper)


def test_current_compatibility_builder_emits_only_current_evidence() -> None:
    policy = MaceCompatibilityPolicy()
    probe = MaceSourceProbe(
        policy_digest=policy.policy_digest,
        run_train_sha256="11" * 32,
        train_sha256="22" * 32,
        multihead_sha256="33" * 32,
        pt_head_sorted_first=True,
        target_validation_head_is_last=True,
        native_checkpoint_uses_last_validation_head=True,
        implicit_target_duplication_present=True,
        multihead_forced_universal_loss_present=True,
        multihead_lr_ema_override_present=True,
        target_per_head_drop_last_present=True,
        target_distributed_sampler_drop_last_present=True,
        target_combined_loader_drop_last_present=True,
        dry_run_supported=True,
        save_all_checkpoints_supported=True,
        fixed_file_adapter_supported=True,
    )

    assert policy.current_execution_compatible
    assert policy.to_dict()["execution_semantics_version"] == MACE_EXECUTION_SEMANTICS_VERSION
    assert probe.current_execution_compatible
    assert probe.to_dict()["schema"] == "mdstats.mace-source-probe.v2"
