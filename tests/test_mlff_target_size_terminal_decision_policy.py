"""P2 terminal-decision acceptance for the practical-ceiling selection rule.

Every case here drives the **real** reducer owner
(``advance_target_size_reducer``) from a real ``TargetSizeExperimentDefinition``
through the real exact-boundary funnel, so the practical-equivalence ranking and
the paired arithmetic-mean aggregation actually execute.  No test seeds a
post-decision reducer state or bypasses ``_equivalence_order``.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.target_size_experiment import (
    HISTORICAL_BLOCKING_CEILING_STATUS,
    TARGET_SIZE_TERMINAL_DECISION_POLICY,
)
from tests.test_mlff_target_size_statistical_authorities import (
    _aggregate,
    _boundary_outcomes,
)

CEILING_CODE = mdstats.CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE


def _bound(aggregate):
    definition = aggregate.definition
    return definition, mdstats.bind_target_size_execution_context(
        definition, aggregate.reducer_state, digest({"p3": "terminal-decision"})
    )


def _drive(definition, state, first, second, terminal):
    """Run the real three-boundary funnel with the given paired-mean scores."""

    for scores in (first, second):
        state = mdstats.advance_target_size_reducer(
            definition, state, _boundary_outcomes(definition, state, scores)
        )
    return mdstats.advance_target_size_reducer(
        definition, state, _boundary_outcomes(definition, state, terminal)
    )


def _failures(definition, state, sizes, scores):
    """Authenticated numerical failures for ``sizes``; metrics for the rest."""

    index = len(state.completed_boundary_epochs)
    epoch = definition.policy.fidelity_epochs[index]
    membership = definition.evaluation_order.membership_digest(
        definition.policy.evaluation_sizes[index]
    )
    outcomes = []
    for size in state.active_candidate_sizes:
        for seed in definition.policy.optimizer_seeds:
            if size in sizes:
                outcomes.append(
                    mdstats.TargetSizeNumericalFailure(
                        experiment_definition_digest=definition.content_digest,
                        execution_context_digest=state.execution_context_digest,
                        target_size=size,
                        optimizer_seed=seed,
                        boundary_epoch=epoch,
                        evaluation_membership_digest=membership,
                        kind=mdstats.NumericalFailureKind.EVAL_NONFINITE_TARGET_METRIC,
                        classification_evidence_digest=digest(
                            {"size": size, "seed": seed}
                        ),
                    )
                )
            else:
                outcomes.append(
                    mdstats.TargetSizeBoundaryMetric(
                        experiment_definition_digest=definition.content_digest,
                        execution_context_digest=state.execution_context_digest,
                        target_size=size,
                        optimizer_seed=seed,
                        boundary_epoch=epoch,
                        evaluation_membership_digest=membership,
                        target_force_rmse_mev_per_a=float(scores[size]) + 0.01 * seed,
                    )
                )
    return tuple(outcomes)


def test_materially_superior_ceiling_is_selected_with_warning(tmp_path) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    terminal = _drive(
        definition,
        state,
        {2: 3.0, 4: 2.0, 8: 1.0},
        {2: 3.0, 4: 2.0, 8: 1.0},
        {4: 1.0, 8: 0.1},
    )
    assert terminal.status is mdstats.ReducerStatus.SELECTED
    assert terminal.selected_target_size == definition.policy.nmax
    assert terminal.selected_membership_digest == (
        definition.training_order.candidate_digest(definition.policy.nmax)
    )
    assert terminal.terminal_reason_codes == (CEILING_CODE,)
    # Case 7: the warning survives serialization and deterministic replay.
    mdstats.validate_target_size_reducer_state(definition, terminal)
    round_tripped = mdstats.TargetSizeReducerState.from_dict(terminal.to_dict())
    assert round_tripped.terminal_reason_codes == (CEILING_CODE,)
    assert round_tripped.content_digest == terminal.content_digest


def test_ceiling_inside_equivalence_band_selects_the_smaller_finalist(
    tmp_path,
) -> None:
    """Nmax is raw-best but within epsilon: that is a plateau, not a ceiling."""

    definition, state = _bound(_aggregate(tmp_path, epsilon=1.0)[2])
    terminal = _drive(
        definition,
        state,
        {2: 3.0, 4: 2.0, 8: 1.0},
        {2: 3.0, 4: 2.0, 8: 1.0},
        {4: 1.0, 8: 0.6},
    )
    assert terminal.status is mdstats.ReducerStatus.SELECTED
    assert terminal.selected_target_size == 4
    assert terminal.terminal_reason_codes == ()


def test_interior_finalist_with_the_best_score_is_selected_normally(tmp_path) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    terminal = _drive(
        definition,
        state,
        {2: 1.0, 4: 2.0, 8: 3.0},
        {2: 1.0, 4: 2.0, 8: 3.0},
        {2: 0.2, 4: 2.0},
    )
    assert terminal.status is mdstats.ReducerStatus.SELECTED
    assert terminal.selected_target_size == 2
    assert terminal.terminal_reason_codes == ()


def test_ceiling_absent_from_the_terminal_matrix_yields_no_warning(tmp_path) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    for scores in ({2: 1.0, 4: 1.2, 8: 3.0}, {2: 1.0, 4: 1.2, 8: 3.0}):
        state = mdstats.advance_target_size_reducer(
            definition, state, _boundary_outcomes(definition, state, scores)
        )
    # Nmax was eliminated at the second boundary, so it is not a finalist.
    assert definition.policy.nmax not in state.active_candidate_sizes
    terminal = mdstats.advance_target_size_reducer(
        definition, state, _boundary_outcomes(definition, state, {2: 1.0, 4: 0.1})
    )
    assert terminal.status is mdstats.ReducerStatus.SELECTED
    assert terminal.selected_target_size == 4
    assert terminal.terminal_reason_codes == ()


def test_reordered_terminal_matrix_never_fabricates_a_ceiling_selection(
    tmp_path,
) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    for scores in ({2: 3.0, 4: 2.0, 8: 1.0}, {2: 3.0, 4: 2.0, 8: 1.0}):
        state = mdstats.advance_target_size_reducer(
            definition, state, _boundary_outcomes(definition, state, scores)
        )
    reordered = tuple(
        reversed(_boundary_outcomes(definition, state, {4: 1.0, 8: 0.1}))
    )
    terminal = mdstats.advance_target_size_reducer(definition, state, reordered)
    assert terminal.status is mdstats.ReducerStatus.INSUFFICIENT_COMPARISON
    assert terminal.selected_target_size is None
    assert CEILING_CODE not in terminal.terminal_reason_codes


def test_numerical_failure_leaving_one_finalist_remains_blocking(tmp_path) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    for scores in ({2: 3.0, 4: 2.0, 8: 1.0}, {2: 3.0, 4: 2.0, 8: 1.0}):
        state = mdstats.advance_target_size_reducer(
            definition, state, _boundary_outcomes(definition, state, scores)
        )
    assert state.active_candidate_sizes == (4, 8)
    terminal = mdstats.advance_target_size_reducer(
        definition, state, _failures(definition, state, {4}, {8: 0.1})
    )
    assert terminal.status is mdstats.ReducerStatus.INSUFFICIENT_COMPARISON
    assert terminal.terminal_reason_codes == (
        "too_few_complete_comparable_candidates",
    )
    assert terminal.selected_target_size is None


def test_terminal_decision_policy_participates_in_p2_identity() -> None:
    policy = mdstats.resolve_target_size_policy(
        target_size_power_min=1, target_size_power_max=3
    )
    assert policy.terminal_decision_policy == TARGET_SIZE_TERMINAL_DECISION_POLICY
    payload = policy.to_dict()
    assert payload["terminal_decision_policy"] == TARGET_SIZE_TERMINAL_DECISION_POLICY
    # An old-rule token cannot be resolved, so no reducer can run under it.
    with pytest.raises(mdstats.TrainingDataInputError):
        replace(policy, terminal_decision_policy="blocking_configured_ceiling.v1")
    # And the token really is part of the digest, not decorative metadata.
    without = {k: v for k, v in payload.items() if k != "terminal_decision_policy"}
    assert digest(without) != policy.content_digest


def test_retired_blocking_ceiling_evidence_is_not_relabelled_as_a_selection(
    tmp_path,
) -> None:
    definition, state = _bound(_aggregate(tmp_path, epsilon=0.1)[2])
    terminal = _drive(
        definition,
        state,
        {2: 3.0, 4: 2.0, 8: 1.0},
        {2: 3.0, 4: 2.0, 8: 1.0},
        {4: 1.0, 8: 0.1},
    )
    historical = dict(terminal.to_dict())
    historical["status"] = HISTORICAL_BLOCKING_CEILING_STATUS
    historical.pop("content_digest")
    with pytest.raises(
        mdstats.TrainingDataSerializationError, match="retired blocking"
    ):
        mdstats.TargetSizeReducerState.from_dict(historical)
    assert not hasattr(
        mdstats.ReducerStatus, "NONCONVERGED_AT_CONFIGURED_CEILING"
    )
