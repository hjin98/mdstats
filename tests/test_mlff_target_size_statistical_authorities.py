from __future__ import annotations

import inspect
import json
import time
import tracemalloc
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures
from mdstats.training_data._common import digest
from mdstats.training_data.neutral_substrate import (
    NeutralSplitExclusionEvidence,
    NeutralSplitExclusionGroup,
    RELATION_KIND_CORRELATION_UNIT,
    RELATION_KIND_GEOMETRY_DUPLICATE,
    RELATION_KIND_STRUCTURAL_REALIZATION,
    build_neutral_split_exclusion_evidence,
)
from mdstats.training_data.target_size_experiment import (
    _constraint_components,
    _exact_component_subset,
)
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


def _synthetic_split_exclusion(
    frame_authority_digest: str,
    unit_catalog_digest: str,
    unit_frames: dict[str, list[str]],
) -> mdstats.NeutralSplitExclusionEvidence:
    """Synthetic P1 relation evidence bound to a synthetic population."""

    return NeutralSplitExclusionEvidence(
        dataset_id="bounded-default-scale",
        frame_authority_digest=frame_authority_digest,
        unit_catalog_digest=unit_catalog_digest,
        groups=tuple(
            NeutralSplitExclusionGroup(
                relation_kind=RELATION_KIND_CORRELATION_UNIT,
                relation_key=unit_id,
                frame_uids=tuple(sorted(uids)),
            )
            for unit_id, uids in sorted(unit_frames.items())
            if len(uids) >= 2
        ),
    )


def test_p2_default_scale_split_and_orders_are_bounded() -> None:
    policy = mdstats.ResolvedTargetSizePolicy()
    frame_count = policy.nmax + policy.m3
    unit_frames: dict[str, list[str]] = {}
    frames = []
    for index in range(frame_count):
        unit_id = digest({"unit": index})
        uid = digest({"frame": index})
        unit_frames.setdefault(unit_id, []).append(uid)
        frames.append(
            mdstats.TargetSizePopulationFrame(
                frame_uid=uid,
                unit_id=unit_id,
                condition_id=digest({"condition": index % 8}),
                geometry_fingerprint=digest({"geometry": index}),
                canonical_label_payload_digest=digest({"label": index}),
                frame_record_digest=digest({"record": index}),
                condition_attributes=(
                    ("condition_id", digest({"condition": index % 8})),
                    ("reduced_formula", "LiO"),
                    ("regime", "production"),
                    ("strain_class", "none"),
                    ("temperature_condition", "700K"),
                ),
            )
        )
    frames = tuple(frames)
    frame_authority_digest = digest({"p1": "frames"})
    unit_catalog_digest = digest({"p1": "units"})
    split_exclusion = _synthetic_split_exclusion(
        frame_authority_digest, unit_catalog_digest, unit_frames
    )
    population = mdstats.TargetSizePopulation(
        dataset_id="bounded-default-scale",
        frame_authority_digest=frame_authority_digest,
        neutral_statistical_base_digest=digest({"p1": "base"}),
        neutral_unit_catalog_digest=unit_catalog_digest,
        frames=frames,
    )
    tracemalloc.start()
    started = time.perf_counter()
    split = mdstats.split_target_size_population(population, policy, split_exclusion)
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




# =========================================================================
# Revision 3 R3.1: complete inherited P1 split-exclusion relation authority
# =========================================================================


_RELATION_OFFSETS = {"run-a": 0.0, "run-b": 0.17, "run-c": 0.31, "run-d": 0.47}


def _relation_chain(
    tmp_path: Path,
    assertion_sets: dict[str, tuple[tuple[str, str], ...]],
    *,
    dataset_id: str = "relation-fixture",
    offsets: dict[str, float] | None = None,
):
    active_offsets = offsets if offsets is not None else _RELATION_OFFSETS
    for run_id in assertion_sets:
        neutral_fixtures._write(
            tmp_path,
            run_id,
            ("Li", "O"),
            n_frames=48,
            position_offset=active_offsets[run_id],
        )
    manifest = mdstats.TrainingDataManifest(
        dataset_id=dataset_id,
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=run_id,
                vasprun=f"{run_id}/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),) + extra,
            )
            for run_id, extra in assertion_sets.items()
        ),
    )
    return _build_full_neutral_chain(
        manifest,
        tmp_path,
        partition_policy=_neutral_policy(),
    )


def _relation_policy() -> mdstats.ResolvedTargetSizePolicy:
    return mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=3,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
    )


def _run_frames(neutral_base, population, run_id):
    catalog = neutral_base.unit_catalog
    return frozenset(
        uid
        for uid in population.frame_uids
        if catalog.unit_for_frame(uid).run_id == run_id
    )


def test_p2_r31_relation_only_protection_keeps_related_frames_together(
    tmp_path,
) -> None:
    """Frames joined only by an additional P1 protected relation never separate."""
    _source, frame_authority, _features, neutral_base = _relation_chain(
        tmp_path,
        {
            "run-a": (("structural_realization_id", "shared-real"),),
            "run-b": (("structural_realization_id", "shared-real"),),
            "run-c": (("structural_realization_id", "unrelated-real"),),
            "run-d": (),
        },
    )
    evidence = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    population = mdstats.build_target_size_population(frame_authority, neutral_base)
    structural = [
        group
        for group in evidence.groups
        if group.relation_kind == RELATION_KIND_STRUCTURAL_REALIZATION
    ]
    assert len(structural) == 1
    frames_a = _run_frames(neutral_base, population, "run-a")
    frames_b = _run_frames(neutral_base, population, "run-b")
    joined = set(structural[0].frame_uids)
    assert joined & set(frames_a) and joined & set(frames_b)

    # Different units and different geometry fingerprints: only the protected
    # relation joins them, and they always land in one constraint component.
    components = _constraint_components(population, evidence)
    a_components = {
        index for index, group in enumerate(components) if set(group) & set(frames_a)
    }
    b_components = {
        index for index, group in enumerate(components) if set(group) & set(frames_b)
    }
    assert a_components == b_components

    policy = _relation_policy()
    split = mdstats.split_target_size_population(population, policy, evidence)
    for frames in (frames_a, frames_b):
        sides = {
            "train" if uid in split.training_frame_uids else "eval"
            for uid in frames
        }
        assert len(sides) == 1


def test_p2_r31_transitive_mixed_closure_is_indivisible(tmp_path) -> None:
    """A unit -> geometry-duplicate -> protected-relation chain is one component."""
    _source, frame_authority, _features, neutral_base = _relation_chain(
        tmp_path,
        {
            # run-a/run-b share exact geometry (identical offsets); run-b and
            # run-c share one structural realization; run-d shares nothing.
            "run-a": (),
            "run-b": (("structural_realization_id", "shared-real"),),
            "run-c": (("structural_realization_id", "shared-real"),),
            "run-d": (),
        },
        offsets={"run-a": 0.0, "run-b": 0.0, "run-c": 0.31, "run-d": 0.47},
    )
    evidence = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    assert {group.relation_kind for group in evidence.groups} == {
        RELATION_KIND_CORRELATION_UNIT,
        RELATION_KIND_GEOMETRY_DUPLICATE,
        RELATION_KIND_STRUCTURAL_REALIZATION,
    }
    population = mdstats.build_target_size_population(frame_authority, neutral_base)
    components = _constraint_components(population, evidence)
    component_index = {
        uid: index for index, group in enumerate(components) for uid in group
    }
    catalog = neutral_base.unit_catalog
    # One indivisible chain: A frame --(geometry duplicate)--> B frame, then
    # B unit --(protected realization)--> C frame, even though no single
    # relation spans A to C.
    chain_frame = None
    for group in evidence.groups:
        if group.relation_kind != RELATION_KIND_GEOMETRY_DUPLICATE:
            continue
        runs = {catalog.unit_for_frame(uid).run_id for uid in group.frame_uids}
        if {"run-a", "run-b"} <= runs and group.frame_uids[0] in component_index:
            chain_frame = group.frame_uids[0]
            break
    assert chain_frame is not None
    b_twin = next(
        uid
        for uid in next(
            g
            for g in evidence.groups
            if g.relation_kind == RELATION_KIND_GEOMETRY_DUPLICATE
            and chain_frame in g.frame_uids
        ).frame_uids
        if catalog.unit_for_frame(uid).run_id == "run-b"
    )
    c_frames = _run_frames(neutral_base, population, "run-c")
    d_frames = _run_frames(neutral_base, population, "run-d")
    assert component_index[chain_frame] == component_index[b_twin]
    assert component_index[chain_frame] == component_index[next(iter(c_frames))]
    # run-d shares nothing with the chain and stays in separate components.
    assert all(
        component_index[uid] != component_index[chain_frame] for uid in d_frames
    )

    policy = _relation_policy()
    split = mdstats.split_target_size_population(population, policy, evidence)
    assert len(split.evaluation_reserve_frame_uids) == policy.m3
    assert len(split.training_frame_uids) >= policy.nmax
    chain_component = component_index[chain_frame]
    for uid, index in component_index.items():
        if index == chain_component:
            assert uid in split.training_frame_uids


def test_p2_r31_exact_allocation_preserved_and_impossible_fails(
    tmp_path,
) -> None:
    from mdstats.training_data.target_size_experiment import (
        reference_exact_split_feasible,
    )

    policy = _relation_policy()
    _source, frame_authority, _features, neutral_base = _relation_chain(
        tmp_path,
        {
            "run-a": (("structural_realization_id", "shared-real"),),
            "run-b": (("structural_realization_id", "shared-real"),),
            "run-c": (("structural_realization_id", "unrelated-real"),),
            "run-d": (),
        },
    )
    evidence = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    population = mdstats.build_target_size_population(frame_authority, neutral_base)
    components = _constraint_components(population, evidence)
    assert reference_exact_split_feasible(
        [len(group) for group in components], policy.m3
    )
    split = mdstats.split_target_size_population(population, policy, evidence)
    assert len(split.evaluation_reserve_frame_uids) == policy.m3
    assert len(split.training_frame_uids) >= policy.nmax
    assert set(split.training_frame_uids).isdisjoint(
        split.evaluation_reserve_frame_uids
    )

    impossible_root = tmp_path / "impossible"
    impossible_root.mkdir()
    _source, frame_authority, _features, neutral_base = _relation_chain(
        impossible_root,
        {
            run_id: (("structural_realization_id", "one-real"),)
            for run_id in ("run-a", "run-b", "run-c", "run-d")
        },
    )
    evidence = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    population = mdstats.build_target_size_population(frame_authority, neutral_base)
    components = _constraint_components(population, evidence)
    assert not reference_exact_split_feasible(
        [len(group) for group in components], policy.m3
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="No exact"):
        mdstats.split_target_size_population(population, policy, evidence)


def test_p2_r31_changed_relation_authority_rejects_stale_restart(
    tmp_path,
) -> None:
    _source, frame_authority, _features, neutral_base = _relation_chain(
        tmp_path,
        {
            "run-a": (("structural_realization_id", "shared-real"),),
            "run-b": (("structural_realization_id", "shared-real"),),
            "run-c": (("structural_realization_id", "unrelated-real"),),
            "run-d": (),
        },
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=_relation_policy(),
    )
    payload = json.loads(json.dumps(aggregate.to_dict()))

    changed_root = tmp_path / "changed"
    changed_root.mkdir()
    _source, changed_frames, _features, changed_base = _relation_chain(
        changed_root,
        {
            "run-a": (("structural_realization_id", "shared-real"),),
            # Only the inherited protected-relation content changes: run-b no
            # longer claims run-a's structural realization.
            "run-b": (("structural_realization_id", "moved-real"),),
            "run-c": (("structural_realization_id", "unrelated-real"),),
            "run-d": (),
        },
        dataset_id="relation-fixture",
    )
    changed_evidence = build_neutral_split_exclusion_evidence(
        changed_frames, changed_base
    )
    assert (
        changed_evidence.content_digest
        != aggregate.split.split_exclusion_evidence_digest
    )
    with pytest.raises(
        mdstats.TrainingDataSerializationError,
        match="split-exclusion relation authority",
    ):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            payload,
            frame_authority=changed_frames,
            neutral_base=changed_base,
        )


def test_p2_r31_split_owner_has_exactly_one_relation_input() -> None:
    signature = inspect.signature(mdstats.split_target_size_population)
    relation_inputs = [
        name for name in signature.parameters if "split_exclusion" in name
    ]
    assert relation_inputs == ["split_exclusion_evidence"]
    source = Path(
        mdstats.training_data.target_size_experiment.__file__
    ).read_text(encoding="utf-8")
    # The split owner never infers relations from provenance, CV, candidate,
    # or seed state; it consumes only the single P1 relation authority.
    for forbidden in (
        "label_domain",
        "cross_validation",
        "replica_id",
        "structural_realization",
        "reference_group",
        "event_ids",
    ):
        assert forbidden not in source
    # Unit/geometry population fields remain mapping evidence only and are not
    # read by the constraint-component owner.
    component_source = inspect.getsource(_constraint_components)
    for forbidden in ("geometry_fingerprint", "unit_id"):
        assert forbidden not in component_source


# =========================================================================
# Revision 3 R3.2: canonical hard-support obligations and prefix qualification
# =========================================================================


def _obligation_policy(**overrides) -> mdstats.ResolvedTargetSizePolicy:
    return mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=5,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
        hard_support_obligations=(
            {
                "obligation_id": "liO-support",
                "attribute": "reduced_formula",
                "value": "LiO",
                "minimum_count": 5,
            },
        ),
    )


def test_p2_r32_empty_obligations_reproduce_current_qualification(
    tmp_path,
) -> None:
    frame_authority, neutral_base, aggregate = _aggregate(tmp_path)
    definition = aggregate.definition
    assert definition.policy.hard_support_obligations == ()
    assert definition.qualified_candidate_sizes == definition.policy.candidate_sizes
    for item in definition.candidate_qualification:
        assert item.qualified
        assert item.labels_training_usable
        assert item.obligation_counts == ()
        assert item.unsatisfied_obligation_ids == ()
    # The canonical empty collection is the default policy representation.
    assert mdstats.ResolvedTargetSizePolicy().hard_support_obligations == ()
    # pi_train is untouched by the (empty) obligation authority.
    plain = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_policy()
    )
    assert (
        aggregate.definition.training_order.frame_uids
        == mdstats.build_target_training_order(
            aggregate.population, aggregate.split, _policy()
        ).frame_uids
    )


def test_p2_r32_satisfied_obligation_and_first_satisfiable_prefix(
    tmp_path,
) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_obligation_policy()
    )
    definition = aggregate.definition
    # Exact prefixes: N=2 and N=4 carry fewer than the required five supported
    # frames; N=8, 16, 32 pass.  Qualification never reorders or repairs.
    assert [item.target_size for item in definition.candidate_qualification] == [
        2,
        4,
        8,
        16,
        32,
    ]
    assert not definition.qualification(2).qualified
    assert not definition.qualification(4).qualified
    assert definition.qualified_candidate_sizes == (8, 16, 32)
    assert definition.qualification(8).obligation_counts == (
        ("liO-support", 8),
    )
    plain = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=replace(_obligation_policy(), hard_support_obligations=()),
    )
    assert definition.training_order.frame_uids == plain.definition.training_order.frame_uids
    assert definition.candidate_membership(8) == plain.definition.candidate_membership(8)


def test_p2_r32_impossible_obligation_fails_before_funnel(tmp_path) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    policy = mdstats.resolve_target_size_policy(
        target_size_power_min=1,
        target_size_power_max=5,
        evaluation_size_powers=(0, 1, 2),
        fidelity_epochs=(1, 3, 10),
        optimizer_seeds=(1, 2),
        hard_support_obligations=(
            {
                "obligation_id": "impossible",
                "attribute": "reduced_formula",
                "value": "LiO",
                "minimum_count": 33,
            },
        ),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="requires at least 3"):
        mdstats.build_target_size_statistical_aggregate(
            frame_authority, neutral_base, policy=policy
        )


def test_p2_r32_policy_identity_normalization_and_config() -> None:
    base = _obligation_policy()
    reordered = replace(
        base,
        hard_support_obligations=(
            {
                "obligation_id": "second",
                "attribute": "regime",
                "value": "production",
                "minimum_count": 2,
            },
            {
                "obligation_id": "liO",
                "attribute": "reduced_formula",
                "value": "LiO",
                "minimum_count": 5,
            },
        ),
    )
    canonical = replace(
        base,
        hard_support_obligations=(
            mdstats.TargetSizeHardSupportObligation(
                obligation_id="liO",
                attribute="reduced_formula",
                value="LiO",
                minimum_count=5,
            ),
            mdstats.TargetSizeHardSupportObligation(
                obligation_id="second",
                attribute="regime",
                value="production",
                minimum_count=2,
            ),
        ),
    )
    assert reordered.hard_support_obligations == canonical.hard_support_obligations
    assert reordered.content_digest == canonical.content_digest
    # An exact duplicate alias normalizes away.
    duplicated = replace(
        base,
        hard_support_obligations=(
            {
                "obligation_id": "liO-support",
                "attribute": "reduced_formula",
                "value": "LiO",
                "minimum_count": 5,
            },
        )
        * 2,
    )
    assert duplicated.content_digest == base.content_digest
    with pytest.raises(mdstats.TrainingDataInputError, match="Contradictory"):
        replace(
            base,
            hard_support_obligations=(
                {
                    "obligation_id": "liO-support",
                    "attribute": "reduced_formula",
                    "value": "LiO",
                    "minimum_count": 5,
                },
                {
                    "obligation_id": "liO-support",
                    "attribute": "reduced_formula",
                    "value": "LiO",
                    "minimum_count": 6,
                },
            ),
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="Unknown hard-support"):
        mdstats.TargetSizeHardSupportObligation(
            obligation_id="bad",
            attribute="provenance_group",
            value="x",
            minimum_count=1,
        )
    # Editing only the normalized obligation definition changes policy identity.
    changed = replace(
        base,
        hard_support_obligations=(
            {
                "obligation_id": "liO-support",
                "attribute": "reduced_formula",
                "value": "LiO",
                "minimum_count": 6,
            },
        ),
    )
    assert changed.content_digest != base.content_digest
    assert mdstats.ResolvedTargetSizePolicy.from_dict(base.to_dict()) == base
    config = {
        "target_data": {
            "size_convergence": {
                "target_size_power_min": 1,
                "target_size_power_max": 5,
                "evaluation_size_powers": [0, 1, 2],
                "hard_support_obligations": [
                    {
                        "obligation_id": "liO-support",
                        "attribute": "reduced_formula",
                        "value": "LiO",
                        "minimum_count": 5,
                    }
                ],
            }
        },
        "training": {"modes": ["multihead_replay"], "seeds": [1, 2]},
    }
    resolved = mdstats.resolve_target_size_policy_from_config(config)
    assert resolved.hard_support_obligations == base.hard_support_obligations
    assert resolved.content_digest == base.content_digest


def test_p2_r32_restart_rejects_changed_obligations_and_forged_qualification(
    tmp_path,
) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_obligation_policy()
    )
    # A coordinated policy change with stale persisted definition/qualification
    # and reducer descendants is rejected through the real deserializer.
    changed = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=replace(
            _obligation_policy(),
            hard_support_obligations=(
                {
                    "obligation_id": "liO-support",
                    "attribute": "reduced_formula",
                    "value": "LiO",
                    "minimum_count": 6,
                },
            ),
        ),
    )
    payload = json.loads(json.dumps(changed.to_dict()))
    payload["definition"] = json.loads(json.dumps(aggregate.definition.to_dict()))
    payload["reducer_state"] = json.loads(
        json.dumps(aggregate.reducer_state.to_dict())
    )
    payload.pop("content_digest")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="definition"):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            payload, frame_authority=frame_authority, neutral_base=neutral_base
        )

    # Forged locally digest-valid qualified=true for a prefix that fails the
    # current hard-obligation policy is rejected at the real aggregate boundary.
    definition = changed.definition
    failing = definition.qualification(2)
    assert not failing.qualified
    forged_qualification = tuple(
        replace(item, unsatisfied_obligation_ids=())
        for item in definition.candidate_qualification
    )
    forged_definition = replace(
        definition, candidate_qualification=forged_qualification
    )
    payload = json.loads(json.dumps(changed.to_dict()))
    payload["definition"] = json.loads(json.dumps(forged_definition.to_dict()))
    payload.pop("content_digest")
    with pytest.raises(
        (mdstats.TrainingDataSerializationError, mdstats.TrainingDataInputError),
        match="derivation|qualification",
    ):
        mdstats.TargetSizeStatisticalAggregate.from_dict(
            payload, frame_authority=frame_authority, neutral_base=neutral_base
        )


def test_p2_r32_soft_diagnostic_isolation(tmp_path) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_obligation_policy()
    )
    # Changing diagnostic-only priority scores that are not hard obligations
    # cannot turn candidate eligibility on or off.
    diagnostic = {
        uid: 0.5 + 0.1 * index
        for index, uid in enumerate(aggregate.split.training_frame_uids)
    }
    other = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=_obligation_policy(),
        training_priority_evidence=diagnostic,
    )
    assert (
        tuple(item.content_digest for item in aggregate.definition.candidate_qualification)
        == tuple(item.content_digest for item in other.definition.candidate_qualification)
    )
    assert aggregate.definition.qualified_candidate_sizes == (
        other.definition.qualified_candidate_sizes
    )


def test_p2_r32_single_order_invariant(tmp_path) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_obligation_policy()
    )
    definition = aggregate.definition
    assert isinstance(definition.training_order, mdstats.TargetTrainingOrder)
    # Qualification evidence carries per-N satisfaction, never per-N orders.
    for item in definition.candidate_qualification:
        payload = item.to_dict()
        assert "frame_uids" not in json.dumps(payload)
        assert not any(
            key.startswith("order") or "order" in key for key in payload
        )
    source = inspect.getsource(
        mdstats.training_data.target_size_experiment.qualify_target_size_candidates
    )
    assert "build_target_training_order" not in source
    assert "TargetTrainingOrder(" not in source


def test_p2_r32_evidence_admission_rejects_unqualified_n(tmp_path) -> None:
    manifest, _sources, _frames, _data4 = _data4_bundle(tmp_path)
    _source, frame_authority, _features, neutral_base = _build_full_neutral_chain(
        manifest, tmp_path, partition_policy=_neutral_policy()
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority, neutral_base, policy=_obligation_policy()
    )
    definition = aggregate.definition
    assert definition.qualified_candidate_sizes == (8, 16, 32)
    state = mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, digest({"p3": "synthetic-context"})
    )
    assert state.active_candidate_sizes == (8, 16, 32)
    scores = {8: 3.0, 16: 2.0, 32: 1.0}
    outcomes = list(_boundary_outcomes(definition, state, scores))
    foreign = replace(outcomes[0], target_size=2)
    with pytest.raises(mdstats.TrainingDataInputError, match="unqualified"):
        mdstats.advance_target_size_reducer(definition, state, tuple(outcomes) + (foreign,))
    # Qualified evidence still advances the funnel.
    state = mdstats.advance_target_size_reducer(definition, state, tuple(outcomes))
    assert state.status is mdstats.ReducerStatus.AWAITING_SECOND_BOUNDARY




# =========================================================================
# Revision 3 R3.3: fidelity-agnostic funnel schema identity
# =========================================================================


def _stale_fidelity_literals() -> tuple[str, ...]:
    # Built from parts so this scanner never contains its own needles.
    return (
        "3" + "-" + "6" + "-" + "10",
        "3" + "/" + "6" + "/" + "10",
        "fixed" + "-" + "6",
        "middle" + "-" + "boundary" + "-" + "6",
    )


def test_p2_r33_funnel_schema_is_fidelity_agnostic() -> None:
    # The product funnel schema name encodes neither a generation nor a
    # historical fidelity ladder.
    assert mdstats.TARGET_SIZE_FUNNEL_POLICY_SCHEMA == "mdstats.target-size-funnel.v1"
    for digit in ("3", "6", "10"):
        assert digit not in mdstats.TARGET_SIZE_FUNNEL_POLICY_SCHEMA
    default = mdstats.ResolvedTargetSizePolicy()
    changed_fidelity = replace(default, fidelity_epochs=(2, 5, 11))
    # Actual fidelity boundaries remain the sole scientific identity of the
    # configured boundary values, while the funnel schema name stays unchanged.
    assert changed_fidelity.content_digest != default.content_digest
    assert (
        mdstats.ResolvedTargetSizePolicy.from_dict(changed_fidelity.to_dict())
        == changed_fidelity
    )


def test_p2_r33_no_superseded_fidelity_literals_and_stable_funnel_identity(
    tmp_path,
) -> None:
    # Static inspection: no superseded fidelity literal may appear in P2
    # product code or in this focused test module.
    p2_sources = (
        Path(mdstats.training_data.target_size_experiment.__file__).read_text(
            encoding="utf-8"
        ),
        Path(__file__).read_text(encoding="utf-8"),
    )
    for source in p2_sources:
        for stale in _stale_fidelity_literals():
            assert stale not in source

    frame_authority, neutral_base, aggregate = _aggregate(tmp_path)
    definition = aggregate.definition
    changed_definition = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=replace(aggregate.policy, fidelity_epochs=(2, 5, 11)),
    ).definition
    # The funnel transition identity itself is fidelity-agnostic: only the
    # resolved fidelity_epochs values changed target-size identity.
    assert definition.funnel_policy == changed_definition.funnel_policy
    assert definition.content_digest != changed_definition.content_digest
