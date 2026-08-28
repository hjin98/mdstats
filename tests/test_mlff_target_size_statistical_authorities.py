from __future__ import annotations

import json
import time
import tracemalloc
from copy import deepcopy
from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.target_size_experiment import _exact_component_subset
from tests.test_mlff_neutral_scientific_substrate import (
    _build_full_neutral_chain,
    _data4_bundle,
    _neutral_policy,
)


def _policy(*, epsilon: float = 1.0) -> mdstats.ResolvedTargetSizePolicy:
    return mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=3,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
        practical_equivalence_mev_per_a=epsilon,
    )


def _aggregate(tmp_path, *, epsilon: float = 1.0):
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest,
        tmp_path,
        partition_policy=_neutral_policy(),
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=_policy(epsilon=epsilon),
    )
    return frame_authority, neutral_base, aggregate


def _boundary_outcomes(definition, state, scores):
    index = len(state.completed_boundary_epochs)
    epoch = definition.policy.fidelity_epochs[index]
    evaluation_size = definition.policy.evaluation_sizes[index]
    membership = definition.evaluation_order.membership_digest(evaluation_size)
    return tuple(
        mdstats.TargetSizeBoundaryMetric(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            target_size=size,
            optimizer_seed=seed,
            boundary_epoch=epoch,
            evaluation_membership_digest=membership,
            target_force_rmse_mev_per_a=float(scores[size]) + 0.01 * seed,
        )
        for size in state.active_candidate_sizes
        for seed in definition.policy.optimizer_seeds
    )


def test_p2a_policy_resolution_identity_and_seed_namespace() -> None:
    default = mdstats.ResolvedTargetSizePolicy()
    assert default.candidate_sizes == (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
    assert default.evaluation_sizes == (256, 512, 1024)
    assert default.fidelity_epochs == (1, 3, 10)
    assert default.optimizer_seeds == (1, 2)
    assert mdstats.ResolvedTargetSizePolicy.from_dict(default.to_dict()) == default

    changed_seed = replace(default, optimizer_seeds=(2, 1))
    changed_fidelity = replace(default, fidelity_epochs=(1, 4, 10))
    changed_metric_policy = replace(default, practical_equivalence_mev_per_a=0.5)
    assert (
        len(
            {
                default.content_digest,
                changed_seed.content_digest,
                changed_fidelity.content_digest,
                changed_metric_policy.content_digest,
            }
        )
        == 4
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="at least three"):
        mdstats.resolve_target_size_policy(
            target_size_power_min=2,
            target_size_power_max=3,
            evaluation_size_powers=(0, 1, 2),
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="unique"):
        replace(default, optimizer_seeds=(1, 1))


def test_p2a_config_resolver_uses_only_sole_method_seeds_and_excludes_cv() -> None:
    config = {
        "target_data": {
            "size_convergence": {
                "target_size_power_min": 1,
                "target_size_power_max": 3,
                "evaluation_size_powers": [0, 1, 2],
                "fidelity_epochs": [1, 3, 10],
            }
        },
        "training": {
            "max_num_epochs": 30,
            "naive_fine_tuning": {"enabled": False, "seeds": [99]},
            "multihead_replay": {
                "enabled": True,
                "seeds": [7, 11],
                "cross_validation_folds": 3,
                "fold_partition_seed": 104729,
            },
        },
        "random": {"projection_seed": 123, "bootstrap_seed": 456},
    }
    policy = mdstats.resolve_target_size_policy_from_config(config)
    assert policy.optimizer_seeds == (7, 11)
    cv_only = deepcopy(config)
    cv_only["training"]["multihead_replay"]["cross_validation_folds"] = 5
    cv_only["training"]["multihead_replay"]["fold_partition_seed"] = 17
    cv_only["random"] = {"projection_seed": 999, "bootstrap_seed": 888}
    cv_only["training"]["max_num_epochs"] = 100
    assert (
        mdstats.resolve_target_size_policy_from_config(cv_only).content_digest
        == policy.content_digest
    )
    changed_seed = deepcopy(config)
    changed_seed["training"]["multihead_replay"]["seeds"] = [11, 7]
    assert (
        mdstats.resolve_target_size_policy_from_config(changed_seed).content_digest
        != policy.content_digest
    )
    multiple = deepcopy(config)
    multiple["training"]["naive_fine_tuning"]["enabled"] = True
    with pytest.raises(mdstats.TrainingDataInputError, match="exactly one"):
        mdstats.resolve_target_size_policy_from_config(multiple)


def test_p2b_exact_allocator_finds_non_greedy_solution_and_rejects_impossible() -> None:
    assert mdstats.reference_exact_split_feasible((6, 4, 3), 7)
    assert not mdstats.reference_exact_split_feasible((6, 4, 2), 7)
    fixtures = ((1, 1, 2, 3), (2, 2, 5, 7), (3, 4, 6), (1, 5, 6, 8))
    for sizes in fixtures:
        components = tuple(
            tuple(digest((index, offset)) for offset in range(size))
            for index, size in enumerate(sizes)
        )
        for target in range(1, sum(sizes) + 1):
            assert (
                _exact_component_subset(components, target) is not None
            ) == mdstats.reference_exact_split_feasible(sizes, target)


def test_p2_integrated_p1_projection_split_orders_prefixes_and_roundtrip(
    tmp_path,
) -> None:
    frame_authority, neutral_base, aggregate = _aggregate(tmp_path)
    policy = aggregate.policy
    population = aggregate.population
    split = aggregate.split
    definition = aggregate.definition

    development_units = set(
        neutral_base.outer_partition.unit_ids_for_role(mdstats.OuterRole.DEVELOPMENT)
    )
    assert {item.unit_id for item in population.frames} <= development_units
    assert all(
        frame_authority.frame(uid).canonical_label_payload_digest is not None
        for uid in population.frame_uids
    )
    assert len(split.evaluation_reserve_frame_uids) == policy.m3
    assert len(split.training_frame_uids) >= policy.nmax
    assert set(split.training_frame_uids).isdisjoint(
        split.evaluation_reserve_frame_uids
    )
    train_set = set(split.training_frame_uids)
    eval_set = set(split.evaluation_reserve_frame_uids)
    for unit in neutral_base.unit_catalog.units:
        authorized = set(unit.frame_uids).intersection(population.frame_uids)
        assert not (
            authorized.intersection(train_set) and authorized.intersection(eval_set)
        )
    for group in frame_authority.duplicates.geometry_groups:
        authorized = set(group.frame_uids).intersection(population.frame_uids)
        assert not (
            authorized.intersection(train_set) and authorized.intersection(eval_set)
        )
    assert set(definition.training_order.frame_uids) == set(split.training_frame_uids)
    assert set(definition.evaluation_order.frame_uids) == set(
        split.evaluation_reserve_frame_uids
    )
    assert definition.candidate_membership(2) == definition.candidate_membership(4)[:2]
    assert definition.candidate_membership(4) == definition.candidate_membership(8)[:4]
    assert (
        definition.evaluation_membership(1) == definition.evaluation_membership(2)[:1]
    )
    assert (
        definition.evaluation_membership(2) == definition.evaluation_membership(4)[:2]
    )

    serialized = json.loads(json.dumps(aggregate.to_dict()))
    rebuilt = mdstats.TargetSizeStatisticalAggregate.from_dict(
        serialized,
        frame_authority=frame_authority,
        neutral_base=neutral_base,
    )
    assert rebuilt.content_digest == aggregate.content_digest
    text = json.dumps(aggregate.to_dict())
    for forbidden in (
        "label_domain",
        "cross_validation",
        "complement",
        "data7",
        "train2",
        "eval2",
    ):
        assert forbidden not in text.lower()


def test_p2_reducer_paired_smaller_n_terminal_and_context_binding(tmp_path) -> None:
    _frames, _base, aggregate = _aggregate(tmp_path)
    definition = aggregate.definition
    state = mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, digest({"p3": "synthetic-context"})
    )
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 2.0, 8: 1.0}),
    )
    assert state.status is mdstats.ReducerStatus.AWAITING_SECOND_BOUNDARY
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 1.0, 8: 0.7}),
    )
    assert state.active_candidate_sizes == (4, 8)
    state = mdstats.advance_target_size_reducer(
        definition, state, _boundary_outcomes(definition, state, {4: 1.0, 8: 0.5})
    )
    assert state.status is mdstats.ReducerStatus.SELECTED
    assert state.selected_target_size == 4
    assert (
        state.selected_membership_digest
        == definition.training_order.candidate_digest(4)
    )
    mdstats.validate_target_size_reducer_state(definition, state)
    with pytest.raises(mdstats.TrainingDataInputError, match="immutable"):
        mdstats.bind_target_size_execution_context(
            definition, state, digest({"p3": "different-context"})
        )


def test_p2_reducer_seed_matrix_failure_attrition_and_ceiling_semantics(
    tmp_path,
) -> None:
    _frames, _base, aggregate = _aggregate(tmp_path, epsilon=0.1)
    definition = aggregate.definition
    context = digest({"p3": "synthetic-context"})
    state = mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, context
    )
    reordered = tuple(
        reversed(_boundary_outcomes(definition, state, {2: 3.0, 4: 2.0, 8: 1.0}))
    )
    invalid = mdstats.advance_target_size_reducer(definition, state, reordered)
    assert invalid.status is mdstats.ReducerStatus.INSUFFICIENT_COMPARISON
    mdstats.validate_target_size_reducer_state(definition, invalid)
    aggregate.with_reducer_state(invalid)

    with pytest.raises(mdstats.TrainingDataInputError, match="authenticated"):
        mdstats.TargetSizeNumericalFailure(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=context,
            target_size=2,
            optimizer_seed=1,
            boundary_epoch=1,
            evaluation_membership_digest=definition.evaluation_order.membership_digest(
                1
            ),
            kind="programming_error",
            classification_evidence_digest=digest({"classification": "invalid"}),
        )

    state = mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, context
    )
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 2.0, 8: 1.0}),
    )
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 2.0, 8: 1.0}),
    )
    assert state.active_candidate_sizes == (4, 8)
    state = mdstats.advance_target_size_reducer(
        definition, state, _boundary_outcomes(definition, state, {4: 1.0, 8: 0.1})
    )
    assert state.status is mdstats.ReducerStatus.NONCONVERGED_AT_CONFIGURED_CEILING
    assert state.selected_target_size is None
    assert state.selected_membership_digest is None


def test_p2_aggregate_rejects_rehashed_split_stale_orders_and_forged_selection(
    tmp_path,
) -> None:
    frame_authority, neutral_base, aggregate = _aggregate(tmp_path)
    payload = deepcopy(aggregate.to_dict())
    split = aggregate.split
    changed_split = replace(
        split,
        training_frame_uids=(split.evaluation_reserve_frame_uids[0],)
        + split.training_frame_uids[1:],
        evaluation_reserve_frame_uids=(split.training_frame_uids[0],)
        + split.evaluation_reserve_frame_uids[1:],
    )
    payload["split"] = changed_split.to_dict()
    payload.pop("content_digest")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="split"):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            payload, frame_authority=frame_authority, neutral_base=neutral_base
        )

    changed_base = replace(
        neutral_base, notes=neutral_base.notes + ("different accepted lineage",)
    )
    with pytest.raises(
        mdstats.TrainingDataSerializationError, match="population|neutral base"
    ):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            aggregate.to_dict(),
            frame_authority=frame_authority,
            neutral_base=changed_base,
        )

    definition = aggregate.definition
    state = mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, digest({"p3": "synthetic-context"})
    )
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 2.0, 8: 1.0}),
    )
    state = mdstats.advance_target_size_reducer(
        definition,
        state,
        _boundary_outcomes(definition, state, {2: 3.0, 4: 1.0, 8: 0.7}),
    )
    state = mdstats.advance_target_size_reducer(
        definition, state, _boundary_outcomes(definition, state, {4: 1.0, 8: 0.5})
    )
    forged = replace(state, selected_membership_digest=digest({"forged": "not-prefix"}))
    payload = aggregate.with_reducer_state(state).to_dict()
    payload["reducer_state"] = forged.to_dict()
    payload.pop("content_digest")
    with pytest.raises(mdstats.TrainingDataInputError, match="history replay"):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            payload, frame_authority=frame_authority, neutral_base=neutral_base
        )


def test_p2_default_scale_split_and_orders_are_bounded() -> None:
    policy = mdstats.ResolvedTargetSizePolicy()
    frame_count = policy.nmax + policy.m3
    frames = tuple(
        mdstats.TargetSizePopulationFrame(
            frame_uid=digest({"frame": index}),
            unit_id=digest({"unit": index}),
            condition_id=digest({"condition": index % 8}),
            geometry_fingerprint=digest({"geometry": index}),
            canonical_label_payload_digest=digest({"label": index}),
            frame_record_digest=digest({"record": index}),
        )
        for index in range(frame_count)
    )
    population = mdstats.TargetSizePopulation(
        dataset_id="bounded-default-scale",
        frame_authority_digest=digest({"p1": "frames"}),
        neutral_statistical_base_digest=digest({"p1": "base"}),
        neutral_unit_catalog_digest=digest({"p1": "units"}),
        frames=frames,
    )
    tracemalloc.start()
    started = time.perf_counter()
    split = mdstats.split_target_size_population(population, policy)
    training = mdstats.build_target_training_order(population, split, policy)
    evaluation = mdstats.build_target_evaluation_order(population, split, policy)
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(split.training_frame_uids) == policy.nmax
    assert len(split.evaluation_reserve_frame_uids) == policy.m3
    assert len(training.frame_uids) == policy.nmax
    assert len(evaluation.frame_uids) == policy.m3
    assert elapsed < 30.0
    assert peak < 256 * 1024 * 1024
