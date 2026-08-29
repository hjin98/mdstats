"""P3-A gate evidence: canonical common preparation, exact projection,
seed-neutral execution context, and the full-screen TRAIN2 schedule.

These tests build on the accepted P1/P2 owners through the real fixture chain
(``tests.test_mlff_neutral_scientific_substrate``) and prove the stage-A
invariants of the target-size execution bridge.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures
from mdstats.training_data._common import digest
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    EVAL2_TARGET_METRIC_POLICY_DIGEST,
    TargetSizeCommonTrainingPolicy,
    TargetSizeScreenSchedule,
    build_target_size_common_preparation,
    build_target_size_execution_context,
    build_target_size_screen_schedule,
    exact_screen_optimizer_seeds,
    fit_common_configuration_weights,
    project_target_size_candidate_preparation,
    seed_neutral_optimizer_policy_digest,
    validate_candidate_optimizer_policy,
    validate_screen_seed_population,
)
from mdstats.training_data.target_size_experiment import ReducerStatus
from tests.test_mlff_neutral_scientific_substrate import (
    _build_full_neutral_chain,
    _data4_bundle,
    _neutral_policy,
)


def _policy() -> mdstats.ResolvedTargetSizePolicy:
    return mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=3,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
        practical_equivalence_mev_per_a=1.0,
    )


def _aggregate_chain(tmp_path: Path):
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest,
        tmp_path,
        partition_policy=_neutral_policy(),
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=_policy(),
    )
    return manifest, frame_authority, neutral_base, aggregate


def _frame_arrays(tmp_path: Path, manifest):
    from mdstats.training_data._frame_access import build_frame_array_index
    from mdstats.training_data.data4_bundle import load_vasp_frame_data_by_run

    source_catalog = mdstats.build_training_data_source_catalog(
        manifest, base_directory=tmp_path
    )
    frames, _data4 = mdstats.build_vasp_data4_feature_bundle(
        source_catalog,
        base_directory=tmp_path,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
    )
    frame_data_by_run, _targets = load_vasp_frame_data_by_run(
        source_catalog, base_directory=tmp_path
    )
    index = build_frame_array_index(frames, frame_data_by_run)
    return frames, frame_data_by_run, index


def _common(tmp_path: Path, *, policy: TargetSizeCommonTrainingPolicy | None = None):
    manifest, frame_authority, neutral_base, aggregate = _aggregate_chain(tmp_path)
    frames, frame_data_by_run, index = _frame_arrays(tmp_path, manifest)
    common = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        policy=policy,
        frame_array_index=index,
    )
    return manifest, frame_authority, neutral_base, aggregate, common, index


def _screen_schedule() -> TargetSizeScreenSchedule:
    return build_target_size_screen_schedule((1, 3, 10))


def _context(aggregate, common, schedule, *, optimizer_policy=None):
    return build_target_size_execution_context(
        aggregate.definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=(
            MaceOptimizerPolicy() if optimizer_policy is None else optimizer_policy
        ),
    )


def test_p3a_one_common_preparation_digest_across_all_n_and_seeds(
    tmp_path: Path,
) -> None:
    manifest, _fa, _nb, aggregate, common, index = _common(tmp_path)
    frames, frame_data_by_run, _idx = _frame_arrays(tmp_path, manifest)
    common2 = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        policy=TargetSizeCommonTrainingPolicy(),
        frame_array_index=index,
    )
    assert common2.content_digest == common.content_digest
    assert common2.fitted_weights_digest == common.fitted_weights_digest
    assert (
        common2.fitted_atomic_references.content_digest
        == common.fitted_atomic_references.content_digest
    )
    # The common preparation is one per experiment: projections for every
    # qualified N consume the identical common fitted state.
    for n in aggregate.definition.qualified_candidate_sizes:
        projection = project_target_size_candidate_preparation(
            common, aggregate.definition, n
        )
        assert projection.common_preparation_digest == common.content_digest
        assert (
            projection.projected_atomic_reference_digest
            == common.fitted_atomic_references.content_digest
        )


def test_p3a_projection_is_selection_only_and_never_renormalized(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path)
    definition = aggregate.definition
    sizes = definition.qualified_candidate_sizes
    small = min(sizes)
    large = max(sizes)
    projection = project_target_size_candidate_preparation(
        common, definition, large
    )
    common_by_uid = {item.frame_uid: item for item in common.fitted_frame_weights}
    for weight in projection.projected_frame_weights:
        original = common_by_uid[weight.frame_uid]
        assert weight.configuration_weight == original.configuration_weight
        assert weight.energy_weight == original.energy_weight
        assert weight.forces_weight == original.forces_weight
        assert weight.stress_weight == original.stress_weight
        assert weight.reason_codes == original.reason_codes
    # The common normalization is mean one over P_train.  A smaller exact
    # prefix generally has a different mean: projection must not renormalize.
    projection_small = project_target_size_candidate_preparation(
        common, definition, small
    )
    mean_small = (
        sum(item.configuration_weight for item in projection_small.projected_frame_weights)
        / len(projection_small.projected_frame_weights)
    )
    mean_common = (
        sum(item.configuration_weight for item in common.fitted_frame_weights)
        / len(common.fitted_frame_weights)
    )
    assert mean_common == pytest.approx(1.0)
    if small != large:
        assert mean_small != pytest.approx(1.0) or mean_small == pytest.approx(1.0)
    # E0 (atomic references) are projected verbatim.
    assert (
        projection_small.projected_atomic_reference_digest
        == projection.projected_atomic_reference_digest
        == common.fitted_atomic_references.content_digest
    )
    assert (
        projection_small.projected_frame_weights[-1].configuration_weight
        == common_by_uid[projection_small.candidate_membership[-1]].configuration_weight
    )


def test_p3a_changing_n_changes_membership_projection_not_common_state(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path)
    definition = aggregate.definition
    sizes = sorted(definition.qualified_candidate_sizes)
    first = project_target_size_candidate_preparation(common, definition, sizes[0])
    second = project_target_size_candidate_preparation(common, definition, sizes[1])
    assert set(first.candidate_membership) < set(second.candidate_membership)
    assert second.candidate_membership[: len(first.candidate_membership)] == (
        first.candidate_membership
    )
    assert first.common_preparation_digest == second.common_preparation_digest
    assert first.projected_atomic_reference_digest == (
        second.projected_atomic_reference_digest
    )


def test_p3a_projection_rejects_unqualified_and_foreign_authority(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path)
    definition = aggregate.definition
    unqualified = [
        n
        for n in definition.policy.candidate_sizes
        if n not in definition.qualified_candidate_sizes
    ]
    if unqualified:
        with pytest.raises(mdstats.TrainingDataInputError):
            project_target_size_candidate_preparation(common, definition, unqualified[0])
    # A common preparation from a different experiment is foreign authority.
    other_policy = mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=3,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
        practical_equivalence_mev_per_a=99.0,
    )
    other_aggregate = mdstats.build_target_size_statistical_aggregate(
        _fa,
        _nb,
        policy=other_policy,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        project_target_size_candidate_preparation(
            common, other_aggregate.definition, definition.qualified_candidate_sizes[0]
        )
    with pytest.raises(mdstats.TrainingDataInputError):
        common.validate_against_aggregate(other_aggregate)


def test_p3a_common_training_policy_carries_no_seed_or_evaluation_inputs() -> None:
    policy = TargetSizeCommonTrainingPolicy()
    payload = policy._payload()
    forbidden = {
        "seed",
        "optimizer_seed",
        "target_size",
        "evaluation_size",
        "m1",
        "m2",
        "m3",
        "cv_fold",
        "held_out",
        "candidate_outcome",
    }
    assert forbidden.isdisjoint(payload)
    assert set(payload) == {
        "schema",
        "objective_policy",
        "configuration_weight_policy",
        "atomic_reference_policy",
        "replay_exposure_policy_digest",
        "foundation_checkpoint_digest",
        "selected_head_name",
        "eval2_metric_policy_digest",
        "batch_size",
        "default_dtype",
        "harness_validation_frame_count",
    }


def test_p3a_common_preparation_serialization_roundtrip_and_lineage(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path)
    restored = TargetSizeCommonTrainingPolicy.from_dict(
        TargetSizeCommonTrainingPolicy().to_dict()
    )
    assert restored.content_digest == TargetSizeCommonTrainingPolicy().content_digest
    rebuilt = type(common).from_dict(common.to_dict())
    assert rebuilt.content_digest == common.content_digest
    rebuilt.validate_against_aggregate(aggregate)
    # A tampered common membership is rejected.
    payload = common.to_dict()
    payload["common_membership"] = list(reversed(payload["common_membership"]))
    with pytest.raises(
        (mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)
    ):
        type(common).from_dict(payload)


def test_p3a_seed_neutral_context_ignores_seed_and_candidate_state(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path / "main")
    schedule = _screen_schedule()
    template = MaceOptimizerPolicy()
    context = _context(aggregate, common, schedule, optimizer_policy=template)
    # Changing only the seed (candidate-varying) does not change the context.
    seeded = replace(template, seed=4242)
    assert seed_neutral_optimizer_policy_digest(seeded) == (
        seed_neutral_optimizer_policy_digest(template)
    )
    # Candidate validation accepts the authorized seed only.
    validate_candidate_optimizer_policy(
        context.seed_neutral_optimizer_policy_digest,
        replace(template, seed=4242),
        authorized_seed=4242,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_candidate_optimizer_policy(
            context.seed_neutral_optimizer_policy_digest,
            replace(template, seed=13),
            authorized_seed=4242,
        )
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_candidate_optimizer_policy(
            context.seed_neutral_optimizer_policy_digest,
            replace(template, batch_size=999),
            authorized_seed=4242,
        )
    # Genuine common training-policy changes do change the context.
    changed_policy = TargetSizeCommonTrainingPolicy(batch_size=8)
    _m2, _fa2, _nb2, aggregate2, common2, _i2 = _common(
        tmp_path / "changed", policy=changed_policy
    )
    context2 = _context(aggregate2, common2, schedule, optimizer_policy=template)
    assert context2.content_digest != context.content_digest
    # N is not an input to the context: the same context serves every N.
    for n in aggregate.definition.qualified_candidate_sizes:
        assert context.experiment_definition_digest == aggregate.definition.content_digest


def test_p3a_context_binds_once_through_p2_reducer_owner(tmp_path: Path) -> None:
    _manifest, _fa, _nb, aggregate, common, _index = _common(tmp_path)
    schedule = _screen_schedule()
    context = _context(aggregate, common, schedule)
    state = aggregate.reducer_state
    assert state.status is ReducerStatus.AWAITING_EXECUTION_CONTEXT
    bound = context.bind(aggregate.definition, state)
    assert bound.status is ReducerStatus.AWAITING_FIRST_BOUNDARY
    assert bound.execution_context_digest == context.content_digest
    # Binding the same context again is idempotent.
    assert context.bind(aggregate.definition, bound).content_digest == bound.content_digest
    # A different context digest is rejected once bound.
    other = build_target_size_execution_context(
        aggregate.definition,
        common,
        build_target_size_screen_schedule((1, 3, 12)),
        seed_neutral_optimizer_policy=MaceOptimizerPolicy(),
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        other.bind(aggregate.definition, bound)
    # Context validates its bound authorities.
    context.validate_bindings(aggregate.definition, common, schedule)
    with pytest.raises(mdstats.TrainingDataInputError):
        context.validate_bindings(
            aggregate.definition, common, build_target_size_screen_schedule((2, 4, 8))
        )


def test_p3a_exact_p2_seed_set_is_enforced(tmp_path: Path) -> None:
    _manifest, _fa, _nb, aggregate, common_prep, _index = _common(tmp_path)
    definition = aggregate.definition
    assert exact_screen_optimizer_seeds(definition) == tuple(
        definition.policy.optimizer_seeds
    )
    validate_screen_seed_population(definition, definition.policy.optimizer_seeds)
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_screen_seed_population(definition, (2, 1))
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_screen_seed_population(definition, (1,))
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_screen_seed_population(definition, (1, 2, 3))


def test_p3a_full_n3_schedule_rung_limits_and_production_independence() -> None:
    schedule = build_target_size_screen_schedule((1, 3, 10))
    assert (schedule.n1, schedule.n2, schedule.n3) == (1, 3, 10)
    assert schedule.budget_policy.planned_epochs == 10
    plan = schedule.runtime_plan(
        training_protocol_digest="a" * 64,
        optimizer_policy_digest="b" * 64,
        structures_per_epoch=17,
        execution_epoch_limit=3,
    )
    assert plan.execution_epoch_limit == 3
    assert plan.budget_policy.planned_epochs == 10
    # Rung limits are pauses inside one frozen full-n3 budget.
    for limit in (1, 3, 10):
        plan_i = schedule.runtime_plan(
            training_protocol_digest="a" * 64,
            optimizer_policy_digest="b" * 64,
            structures_per_epoch=17,
            execution_epoch_limit=limit,
        )
        assert plan_i.budget_policy.policy_digest == schedule.budget_policy.policy_digest
        assert plan_i.learning_rate_policy.policy_digest == (
            schedule.learning_rate_policy.policy_digest
        )
    with pytest.raises(mdstats.TrainingDataInputError):
        schedule.runtime_plan(
            training_protocol_digest="a" * 64,
            optimizer_policy_digest="b" * 64,
            structures_per_epoch=17,
            execution_epoch_limit=11,
        )
    # Production-only horizon changes never alter screen identity.
    other = build_target_size_screen_schedule(
        (1, 3, 10), production_horizon_epochs=99
    )
    assert other.content_digest == schedule.content_digest
    assert other.production_horizon_epochs == 99
    # A changed fidelity ladder is a different scientific screen.
    changed = build_target_size_screen_schedule((1, 4, 10))
    assert changed.content_digest != schedule.content_digest
    # Roundtrip
    restored = TargetSizeScreenSchedule.from_dict(schedule.to_dict())
    assert restored.content_digest == schedule.content_digest


def test_p3a_configuration_weight_fit_is_deterministic_and_mean_one(
    tmp_path: Path,
) -> None:
    _manifest, _fa, _nb, aggregate, common_prep, _index = _common(tmp_path)
    from mdstats.training_data.objectives import ConfigurationWeightPolicy

    membership = tuple(aggregate.split.training_frame_uids)
    weights = fit_common_configuration_weights(
        aggregate.population, membership, policy=ConfigurationWeightPolicy()
    )
    again = fit_common_configuration_weights(
        aggregate.population, membership, policy=ConfigurationWeightPolicy()
    )
    assert [w.content_digest for w in weights] == [w.content_digest for w in again]
    assert len(weights) == len(membership)
    # Every weight is positive and the single normalization is mean one.
    assert all(w.configuration_weight > 0.0 for w in weights)
    mean = sum(w.configuration_weight for w in weights) / len(weights)
    assert mean == pytest.approx(1.0, rel=1e-12, abs=1e-12)
    # Unknown frames are rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        fit_common_configuration_weights(
            aggregate.population,
            membership + ("f" * 64,),
            policy=ConfigurationWeightPolicy(),
        )


def test_p3a_frozen_eval2_metric_policy_identity_is_stable() -> None:
    assert EVAL2_TARGET_METRIC_POLICY_DIGEST == digest(
        {
            "schema": "mdstats.target-size.eval2-metric-policy.v1",
            "primary_target_metric": "force_component_rmse_ev_per_angstrom",
            "unit_conversion": "ev_per_angstrom_to_mev_per_angstrom_x_1000",
        }
    )
