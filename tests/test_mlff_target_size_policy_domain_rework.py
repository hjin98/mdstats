"""Revision 7 policy-domain acceptance for current configuration and records."""

from __future__ import annotations

import math

import pytest

from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.objectives import (
    ConfigurationWeightPolicy,
    TrainingObjectivePolicy,
    resolve_configuration_weight_policy,
    resolve_training_objective_policy,
)
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution.schedule import (
    TargetSizeOptimizerNormalizationPolicy,
    resolve_target_size_optimizer_normalization_policy,
)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_target_size", True),
        ("reference_target_size", 2.5),
        ("reference_target_size", "1024"),
        ("reference_learning_rate", True),
        ("reference_learning_rate", "1e-4"),
        ("reference_learning_rate", math.nan),
        ("reference_ema_decay", False),
        ("reference_ema_decay", "0.99"),
        ("reference_ema_decay", math.inf),
        ("algorithm", 1),
    ],
)
def test_target_size_normalization_rejects_current_schema_domain_coercions(
    field: str, value: object
) -> None:
    policy = TargetSizeOptimizerNormalizationPolicy().to_dict()
    policy.pop("content_digest")
    policy[field] = value
    with pytest.raises(TrainingDataInputError):
        TargetSizeOptimizerNormalizationPolicy.from_dict(policy)

    config = {
        "target_data": {
            "size_convergence": {"optimizer_normalization": {field: value}}
        }
    }
    with pytest.raises(TrainingDataInputError):
        resolve_target_size_optimizer_normalization_policy(config)


def test_target_size_normalization_positive_payload_round_trips_without_drift() -> None:
    policy = TargetSizeOptimizerNormalizationPolicy(
        reference_target_size=513,
        reference_learning_rate=2.5e-4,
        reference_ema_decay=0.997,
    )
    restored = TargetSizeOptimizerNormalizationPolicy.from_dict(policy.to_dict())
    assert restored == policy
    assert restored.content_digest == policy.content_digest


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("energy_weight", True),
        ("forces_weight", "10"),
        ("stress_weight", math.inf),
        ("group_aware_force_objective", "false"),
        ("focus_atom_group_ids", [1]),
        ("focus_atom_group_ids", "oxygen"),
        ("focus_atomic_numbers", [8.0]),
        ("focus_atomic_numbers", ["8"]),
        ("focus_atomic_numbers", [True]),
    ],
)
def test_training_objective_rejects_current_schema_domain_coercions(
    field: str, value: object
) -> None:
    policy = TrainingObjectivePolicy().to_dict()
    policy.pop("policy_digest")
    policy[field] = value
    with pytest.raises(TrainingDataInputError):
        TrainingObjectivePolicy.from_dict(policy)

    with pytest.raises(TrainingDataInputError):
        resolve_training_objective_policy({"objective": {field: value}})


def test_training_objective_positive_payload_round_trips_and_normalizes_declared_values() -> None:
    policy = TrainingObjectivePolicy(
        energy_weight=2,
        forces_weight=7.0,
        stress_weight=3,
        group_aware_force_objective=True,
        focus_atom_group_ids=(" oxygen ", "framework", "oxygen"),
        focus_atomic_numbers=(8, 3, 8),
    )
    assert policy.focus_atom_group_ids == ("framework", "oxygen")
    assert policy.focus_atomic_numbers == (3, 8)
    restored = TrainingObjectivePolicy.from_dict(policy.to_dict())
    assert restored == policy
    assert restored.policy_digest == policy.policy_digest


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("equalize_condition_strata", 1),
        ("equalize_condition_strata", "false"),
        ("event_anchor_multiplier", "2.0"),
        ("protected_event_multiplier", math.nan),
        ("degraded_frame_multiplier", True),
        ("minimum_configuration_weight", 0),
        ("maximum_configuration_weight", math.inf),
    ],
)
def test_configuration_weight_rejects_current_schema_domain_coercions(
    field: str, value: object
) -> None:
    policy = ConfigurationWeightPolicy().to_dict()
    policy.pop("policy_digest")
    policy[field] = value
    with pytest.raises(TrainingDataInputError):
        ConfigurationWeightPolicy.from_dict(policy)
    with pytest.raises(TrainingDataInputError):
        resolve_configuration_weight_policy({"weighting": {field: value}})


def test_configuration_weight_positive_payload_round_trips_without_drift() -> None:
    policy = ConfigurationWeightPolicy(
        equalize_condition_strata=False,
        event_anchor_multiplier=3,
        protected_event_multiplier=1.5,
        degraded_frame_multiplier=0.25,
        minimum_configuration_weight=0.1,
        maximum_configuration_weight=8,
    )
    restored = ConfigurationWeightPolicy.from_dict(policy.to_dict())
    assert restored == policy
    assert restored.policy_digest == policy.policy_digest


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("learning_rate", "1e-4"),
        ("batch_size", 2.5),
        ("valid_batch_size", "4"),
        ("num_workers", True),
        ("max_num_epochs", 3.5),
        ("eval_interval", False),
        ("ema", 1),
        ("ema_decay", "0.99"),
        ("amsgrad", "true"),
        ("weight_decay", math.nan),
        ("clip_grad", [10.0]),
        ("seed", "1"),
    ],
)
def test_persisted_mace_optimizer_rejects_current_schema_domain_coercions(
    field: str, value: object
) -> None:
    payload = MaceOptimizerPolicy(device="cpu").to_dict()
    payload[field] = value
    with pytest.raises(TrainingDataInputError):
        MaceOptimizerPolicy.from_dict(payload)


def test_persisted_mace_optimizer_positive_payload_round_trips_without_drift() -> None:
    policy = MaceOptimizerPolicy(
        device="cpu",
        learning_rate=2.5e-4,
        batch_size=4,
        valid_batch_size=3,
        num_workers=2,
        max_num_epochs=11,
        eval_interval=1,
        ema=False,
        amsgrad=False,
        seed=17,
    )
    restored = MaceOptimizerPolicy.from_dict(policy.to_dict())
    assert restored == policy
    assert restored.policy_digest == policy.policy_digest


def test_mace_optimizer_real_fields_have_one_integer_float_identity() -> None:
    integer_spelling = MaceOptimizerPolicy(
        device="cpu",
        learning_rate=1,
        ema_decay=1 - 1 / 100,
        weight_decay=2,
        clip_grad=10,
    )
    float_spelling = MaceOptimizerPolicy(
        device="cpu",
        learning_rate=1.0,
        ema_decay=0.99,
        weight_decay=2.0,
        clip_grad=10.0,
    )

    assert integer_spelling.to_dict() == float_spelling.to_dict()
    assert integer_spelling.policy_digest == float_spelling.policy_digest
    for field in ("learning_rate", "ema_decay", "weight_decay", "clip_grad"):
        assert isinstance(getattr(integer_spelling, field), float)

    restored = MaceOptimizerPolicy.from_dict(integer_spelling.to_dict())
    assert restored.to_dict() == float_spelling.to_dict()
    assert restored.policy_digest == float_spelling.policy_digest
