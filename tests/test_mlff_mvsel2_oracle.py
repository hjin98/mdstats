from __future__ import annotations

import pytest

from tests.support.mlff_mvsel2_oracle import (
    OracleObligation,
    OracleProblem,
    best_relative_contenders,
    exact_forward_order,
)


def _problem(
    *,
    frame_uids: tuple[str, ...] = ("b", "a", "c"),
    family_ids: tuple[str, ...] = ("f0",),
    family_weights: tuple[tuple[float, ...], ...] = ((0.5, 0.5),),
    forward_rows: tuple[tuple[tuple[int, ...], ...], ...] = (
        ((0,), (1,), (0, 1)),
    ),
    correlation_unit_codes: tuple[int, ...] = (0, 0, 0),
    obligations: tuple[OracleObligation, ...] = (),
    coverage_threshold: float = 0.95,
    epsilon: float = 1.0e-14,
) -> OracleProblem:
    return OracleProblem(
        frame_uids=frame_uids,
        family_ids=family_ids,
        family_weights=family_weights,
        forward_rows=forward_rows,
        correlation_unit_codes=correlation_unit_codes,
        obligations=obligations,
        coverage_threshold=coverage_threshold,
        epsilon=epsilon,
    )


def test_mvsel2_oracle_best_relative_rule_covers_exact_inside_and_outside_epsilon() -> None:
    epsilon = 1.0e-14
    values = (1.0, 1.0 - epsilon, 1.0 - 0.5 * epsilon, 1.0 - 2.0 * epsilon)
    assert best_relative_contenders(values, range(4), epsilon) == (0, 1, 2)


def test_mvsel2_oracle_uses_uid_for_a_complete_score_tie() -> None:
    problem = _problem(
        frame_uids=("uid-b", "uid-a"),
        family_weights=((1.0,),),
        forward_rows=(((0,), (0,)),),
        correlation_unit_codes=(0, 0),
    )
    assert exact_forward_order(problem, 1)[0].frame_uid == "uid-a"


def test_mvsel2_oracle_chooses_first_canonical_tied_bottleneck_family() -> None:
    problem = _problem(
        frame_uids=("uid-0", "uid-1"),
        family_ids=("canonical-first", "canonical-second"),
        family_weights=((1.0,), (1.0,)),
        forward_rows=(((0,), ()), ((), (0,))),
        correlation_unit_codes=(0, 0),
    )
    first = exact_forward_order(problem, 1)[0]
    assert first.bottleneck_family_id == "canonical-first"
    assert first.candidate_index == 0


def test_mvsel2_oracle_hard_gain_stops_at_obligation_threshold() -> None:
    problem = _problem(
        frame_uids=("uid-a", "uid-b", "uid-c"),
        family_weights=((1.0,),),
        forward_rows=(((0,), (0,), (0,)),),
        correlation_unit_codes=(0, 0, 0),
        obligations=(OracleObligation("required", 2, (0, 1)),),
    )
    order = exact_forward_order(problem, 3)
    assert [item.candidate_index for item in order[:2]] == [0, 1]
    assert [item.hard_gain for item in order] == [1, 1, 0]
    assert order[2].phase == "representative_fill"


def test_mvsel2_oracle_balances_correlation_units_before_uid() -> None:
    problem = _problem(
        frame_uids=("uid-a", "uid-z", "uid-b"),
        family_weights=((1.0,),),
        forward_rows=(((0,), (0,), (0,)),),
        correlation_unit_codes=(0, 1, 0),
    )
    order = exact_forward_order(problem, 2)
    assert [item.candidate_index for item in order] == [0, 1]


def test_mvsel2_oracle_uses_unweighted_sparse_diversity_after_rep_tie() -> None:
    problem = _problem(
        frame_uids=("seed", "lower-diversity", "higher-diversity"),
        family_weights=((0.9, 0.1, 0.55),),
        forward_rows=(((0,), (0, 1), (2,)),),
        correlation_unit_codes=(0, 0, 0),
        obligations=(OracleObligation("seed-first", 1, (0,)),),
        coverage_threshold=0.5,
    )
    order = exact_forward_order(problem, 2)
    assert order[0].candidate_index == 0
    assert order[1].candidate_index == 2
    assert order[1].diversity > 0.5


def test_mvsel2_oracle_accepts_zero_degree_rows_and_reports_zero_scores() -> None:
    problem = _problem(
        frame_uids=("empty", "cover"),
        family_weights=((1.0,),),
        forward_rows=(((), (0,)),),
        correlation_unit_codes=(0, 0),
    )
    order = exact_forward_order(problem, 2)
    assert order[0].candidate_index == 1
    assert order[1].candidate_index == 0
    assert order[1].representative_gain == 0.0
    assert order[1].diversity == 0.0


@pytest.mark.parametrize("row", [(1, 0), (0, 0), (2,)])
def test_mvsel2_oracle_rejects_invalid_forward_row_contract(row: tuple[int, ...]) -> None:
    problem = _problem(
        frame_uids=("uid",),
        family_weights=((0.5, 0.5),),
        forward_rows=((row,),),
        correlation_unit_codes=(0,),
        coverage_threshold=0.5,
    )
    with pytest.raises(ValueError, match="strictly sorted|out-of-range"):
        exact_forward_order(problem, 1)


def test_mvsel2_oracle_tau_minus_epsilon_boundary_enters_phase_b() -> None:
    epsilon = 1.0e-14
    problem = _problem(
        frame_uids=("boundary", "rest"),
        family_weights=((0.95 - epsilon, 0.05 + epsilon),),
        forward_rows=(((0,), (1,)),),
        correlation_unit_codes=(0, 0),
        epsilon=epsilon,
    )
    order = exact_forward_order(problem, 2)
    assert order[0].phase == "hard_coverage"
    assert order[1].phase == "representative_fill"
