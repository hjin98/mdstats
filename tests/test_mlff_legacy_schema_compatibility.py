from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import digest


FIXTURE_ROOT = Path(__file__).with_name("fixtures") / "legacy_schema_0_20_76"


def _load(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _rehash(payload: dict[str, object], field: str) -> None:
    body = dict(payload)
    body.pop(field, None)
    payload[field] = digest(body)


def test_actual_02076_data5_bundle_round_trips_exactly() -> None:
    payload = _load("data5.json")
    bundle = mdstats.Data5PartitionBundle.from_dict(payload)

    assert bundle.partition_policy.cross_validation_seed == 104729
    assert bundle.content_digest == payload["content_digest"]
    assert bundle.to_dict() == payload


def test_actual_02076_production_plan_round_trips_exactly() -> None:
    payload = _load("production_plan.json")
    plan = mdstats.ProductionMaterializationPlan.from_dict(payload)

    assert plan.feature_metric_policy.randomized_projection_seed == 0
    assert plan.content_digest == payload["content_digest"]
    assert plan.to_dict() == payload


def test_legacy_feature_metric_policy_tampering_is_rejected() -> None:
    payload = _load("production_plan.json")["feature_metric_policy"]
    assert isinstance(payload, dict)
    tampered = copy.deepcopy(payload)
    tampered["minimum_scale"] = float(tampered["minimum_scale"]) * 2.0

    with pytest.raises(
        mdstats.TrainingDataSerializationError,
        match="Feature-metric policy digest mismatch",
    ):
        mdstats.FeatureMetricPolicyTemplate.from_dict(tampered)


def test_legacy_partition_policy_tampering_is_rejected() -> None:
    payload = _load("data5.json")["partition_policy"]
    assert isinstance(payload, dict)
    tampered = copy.deepcopy(payload)
    tampered["allow_global_role_fallback"] = not bool(
        tampered["allow_global_role_fallback"]
    )

    with pytest.raises(
        mdstats.TrainingDataSerializationError,
        match="Partition-policy digest mismatch",
    ):
        mdstats.PartitionPolicy.from_dict(tampered)


def test_legacy_nested_policy_can_be_validly_reissued_only_with_new_digests() -> None:
    """A deliberate edit is accepted only when every affected identity is rebuilt."""

    payload = _load("production_plan.json")
    policy = payload["feature_metric_policy"]
    assert isinstance(policy, dict)
    policy["minimum_scale"] = float(policy["minimum_scale"]) * 2.0
    _rehash(policy, "policy_digest")
    _rehash(payload, "content_digest")

    plan = mdstats.ProductionMaterializationPlan.from_dict(payload)
    assert plan.feature_metric_policy.minimum_scale == float(policy["minimum_scale"])
    assert plan.to_dict() == payload


def test_training_execution_policy_v1_preserves_legacy_identity() -> None:
    current = mdstats.TrainingExecutionPolicy()
    payload = current.to_dict()
    payload["schema"] = "mdstats.training-execution-policy.v1"
    payload.pop("runtime_layout_version")
    _rehash(payload, "policy_digest")

    loaded = mdstats.TrainingExecutionPolicy.from_dict(payload)
    assert loaded.runtime_layout_version == "legacy-run-cwd.v1"
    assert loaded.to_dict() == payload


def test_historical_data7_parser_identity_is_readable_and_preserved() -> None:
    # The full DATA7 archive tests exercise arrays and archive checksums.  This
    # focused contract verifies the accepted release parser identities directly.
    assert mdstats.MLFF_DATA7_PARSER_VERSION == "0.20.64a0"
    from mdstats.training_data.data7_bundle import MLFF_DATA7_V63_PARSER_VERSION

    assert MLFF_DATA7_V63_PARSER_VERSION == "0.20.63a0"


def test_historical_data8_parser_identity_is_registered() -> None:
    assert mdstats.MLFF_DATA8_PARSER_VERSION == "0.20.132a0"
    from mdstats.training_data.data8_bundle import (
        MLFF_DATA8_LEGACY_PARSER_VERSION,
        MLFF_DATA8_PRE_ADAPT_MON1_PARSER_VERSION,
        MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION,
    )

    assert MLFF_DATA8_PRE_MLCV_ROLE1_PARSER_VERSION == "0.20.126a0"
    assert MLFF_DATA8_PRE_ADAPT_MON1_PARSER_VERSION == "0.20.66a0"
    assert MLFF_DATA8_LEGACY_PARSER_VERSION == "0.20.39a0"


def test_legacy_production_plan_remains_valid_through_checkpoint_and_record() -> None:
    plan_payload = _load("production_plan.json")
    checkpoint: dict[str, object] = {
        "schema": "mdstats.production-materialization-checkpoint.v2",
        "plan": plan_payload,
        "data7_artifacts": [],
        "data8_artifact": None,
        "status": "incomplete",
        "failure_type": None,
        "failure_message": None,
    }
    _rehash(checkpoint, "content_digest")
    record: dict[str, object] = {
        "schema": "mdstats.production-materialization-record.v2",
        "checkpoint": checkpoint,
        "root_directory": "/tmp/legacy-materialization",
    }
    identity = {
        "schema": record["schema"],
        "checkpoint": checkpoint,
    }
    record["content_digest"] = digest(identity)

    loaded = mdstats.ProductionMaterializationRecord.from_dict(record)
    assert loaded.checkpoint.plan.feature_metric_policy.randomized_projection_seed == 0
    assert loaded.to_dict() == record
