from __future__ import annotations

import inspect
import math

import numpy as np

import mdstats
from mdstats.training_data.selection import (
    ExactFPSState,
    _extend_selected_neighbor_matrix,
    _extend_selected_neighbor_minima,
    _fps_order_matrix,
)
from mdstats.training_data.target_coverage import (
    score_target_nested_subsets_coverage,
    score_target_subset_coverage,
)
from mdstats.training_data.target_ladder import (
    _build_target_data_ladder_exhaustive_v1,
    _fused_required_family_matrix,
    _weighted_median,
)
from tests.test_mlff_data7_selection_scaling import _legacy_fps_prefix
from tests.test_mlff_target_data2c_ladder import _reference_and_role


LEGACY_TARGET2C_PLAN_DIGEST = "dbbbc0587fdf0e2574d433086b014c6f9a62ceebaed1173bf4588c9f0fd8d24e"
LEGACY_TARGET2C_COVERAGE_DIGESTS = (
    "60065050f709026fbe7b1e5054e09f8976c3cc4cd5fbf06e44ca5802c1adf086",
    "bbf8cf375082dd486b153308cf1f23b31edefe5d8f8cbd7e5d2ebb9428240b3e",
    "6044ff32aa0f2ab0e902a53792d99604ba3301815c332ee394942c25da37523f",
    "7867ac26bf382fad70f985a70860ca6b9149eb9051b1cadb8b6c6c6d47eeda32",
)


def _legacy_fused_matrix(domain: object) -> np.ndarray:
    required = tuple(
        sorted(
            (item for item in domain.families if item.required),
            key=lambda item: item.family_id,
        )
    )
    by_semantic: dict[str, list[object]] = {}
    for family in required:
        by_semantic.setdefault(family.semantic_family, []).append(family)
    semantic_ids = tuple(sorted(by_semantic))
    blocks: list[np.ndarray] = []
    for semantic in semantic_ids:
        families = tuple(
            sorted(by_semantic[semantic], key=lambda item: item.family_id)
        )
        family_factor = 1.0 / math.sqrt(float(len(families)))
        for family in families:
            values = np.asarray(family.values, dtype=np.float64)
            weights = np.asarray(family.weights, dtype=np.float64)
            scales = np.asarray(family.scales, dtype=np.float64)
            scaled = values / scales[None, :]
            center = _weighted_median(scaled, weights)
            d = scaled.shape[1]
            block = np.zeros((len(domain.frame_uids), d + 1), dtype=np.float64)
            rows = np.asarray(family.frame_indices, dtype=np.int64)
            block[rows, :d] = scaled - center[None, :]
            if len(rows) < len(domain.frame_uids):
                block[:, d] = -0.5
                block[rows, d] = 0.5
            block *= family_factor / math.sqrt(float(d + 1))
            blocks.append(block)
    matrix = np.concatenate(blocks, axis=1)
    matrix /= math.sqrt(float(len(semantic_ids)))
    return matrix


def test_perf_p1_exact_fps_state_matches_legacy_seeded_order() -> None:
    rng = np.random.default_rng(2026081501)
    uids = tuple(f"{index:064x}" for index in range(96))
    X = rng.normal(size=(96, 17))
    X[12] = X[11]
    X[48] = X[47]
    initial = (uids[3], uids[21], uids[77])
    expected = _legacy_fps_prefix(
        uids,
        {uid: X[index] for index, uid in enumerate(uids)},
        initial,
        1.0e-12,
        31,
    )
    observed = _fps_order_matrix(uids, X, initial, 1.0e-12, limit=31)
    assert observed == expected

    state = ExactFPSState.from_matrix(uids, X, 1.0e-12)
    state.seed_indices([3, 21, 77])
    state_order = [uids[index] for index in state.continue_fps(31)]
    assert state_order == expected
    assert state.row_norm_squared.shape == (len(uids),)
    assert state.min_squared_distance.shape == (len(uids),)
    assert state.selected_rank.shape == (len(uids),)
    assert state.lexical_uid_rank.shape == (len(uids),)


def test_perf_p1_preallocated_fused_matrix_is_byte_exact() -> None:
    reference, _ = _reference_and_role(40)
    domain = reference.domain("target")
    legacy = _legacy_fused_matrix(domain)
    current, family_ids, semantic_ids = _fused_required_family_matrix(domain)
    assert np.array_equal(current, legacy)
    assert family_ids == tuple(
        item.family_id for item in sorted(domain.families, key=lambda item: item.family_id)
    )
    assert semantic_ids == tuple(sorted({item.semantic_family for item in domain.families}))


def test_perf_p1_target2c_preserves_frozen_plan_and_rung_digests() -> None:
    reference, role = _reference_and_role(40)
    policy = mdstats.TargetDataLadderPolicy(
        ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3
    )
    plan = _build_target_data_ladder_exhaustive_v1(
        reference, role, policy=policy, coverage_query_workers=1
    )
    assert plan.content_digest == LEGACY_TARGET2C_PLAN_DIGEST
    assert tuple(
        rung.coverage_report.content_digest for rung in plan.domain("target").materialized_rungs
    ) == LEGACY_TARGET2C_COVERAGE_DIGESTS


def test_perf_p1_progressive_coverage_matches_independent_rungs_exactly() -> None:
    reference, role = _reference_and_role(40)
    policy = mdstats.TargetDataLadderPolicy(
        ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3
    )
    plan = mdstats.build_target_data_ladder(reference, role, policy=policy)
    subsets = tuple(rung.frame_uids for rung in plan.domain("target").materialized_rungs)
    progressive = score_target_nested_subsets_coverage(
        reference, "target", subsets, query_workers=1
    )
    independent = tuple(
        score_target_subset_coverage(reference, "target", subset) for subset in subsets
    )
    assert [item.content_digest for item in progressive] == [
        item.content_digest for item in independent
    ]
    assert [item.to_dict() for item in progressive] == [
        item.to_dict() for item in independent
    ]


def test_perf_p1_progressive_coverage_worker_count_is_execution_only() -> None:
    reference, role = _reference_and_role(40)
    policy = mdstats.TargetDataLadderPolicy(
        ladder_exponents=(2, 3, 4, 5), minimum_materializable_rungs=3
    )
    one = mdstats.build_target_data_ladder(
        reference, role, policy=policy, coverage_query_workers=1
    )
    two = mdstats.build_target_data_ladder(
        reference, role, policy=policy, coverage_query_workers=2
    )
    assert one.content_digest == two.content_digest
    assert one.to_dict() == two.to_dict()


def test_perf_p1_selected_neighbor_minima_are_dense_matrix_exact() -> None:
    rng = np.random.default_rng(2026081502)
    values = rng.normal(size=(257, 23))
    squared = np.full((len(values), len(values)), np.inf, dtype=np.float64)
    minima = np.full(len(values), np.inf, dtype=np.float64)
    previous = 0
    for current in (1, 7, 31, 97, 257):
        _extend_selected_neighbor_matrix(values, squared, previous, current)
        _extend_selected_neighbor_minima(
            values,
            minima,
            previous,
            current,
            memory_budget_bytes=128 * 1024,
        )
        if current > 1:
            assert np.array_equal(
                minima[:current], np.min(squared[:current, :current], axis=1)
            )
        previous = current


def test_perf_p1_data7_coverage_persists_only_linear_neighbor_state() -> None:
    source = inspect.getsource(mdstats.build_selection_coverage_report)
    assert "_extend_selected_neighbor_minima" in source
    assert "selected_neighbor_min_squared" in source
    assert "selected_pair_squared" not in source
