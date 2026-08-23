from __future__ import annotations

import numpy as np
import pytest
from types import SimpleNamespace

import mdstats
from mdstats.training_data import target_coverage_sparse_index_store as mvidx_store
from mdstats.training_data.target_coverage_sparse_forward_view import (
    target_coverage_sparse_forward_view,
)
from mdstats.training_data.target_multi_view_selector_v2 import (
    TargetMultiViewSelectorPolicyV2,
    TargetMultiViewSelectionPlanV2,
    build_target_multi_view_selection_plan_v2,
    build_target_multi_view_forward_state_v2,
    build_target_multi_view_lazy_frontier_v2,
    choose_target_multi_view_phase_a_candidate_v2,
    choose_target_multi_view_phase_b_candidate_v2,
    choose_target_multi_view_phase_b_full_forward_v2,
    deselect_target_multi_view_candidate_v2,
    score_target_multi_view_candidate_v2,
    score_target_multi_view_candidates_v2,
    select_target_multi_view_candidate_v2,
    validate_target_multi_view_selection_authority_v2,
)
from tests.support.mlff_mvsel2_oracle import (
    OracleObligation,
    OracleProblem,
    exact_forward_order,
)
from tests.test_mlff_target_data2b_feas1 import _reference_and_role


def _forward_fixture():
    reference, role = _reference_and_role(split_units=True)
    feasibility = mdstats.build_target_coverage_feasibility_report(reference, role)
    index = mdstats.build_target_coverage_sparse_index(reference, role, feasibility)
    forward = target_coverage_sparse_forward_view(index)
    return reference, index, forward


def _oracle_problem(reference_domain, forward_domain) -> OracleProblem:
    obligation_candidates: list[list[int]] = [
        [] for _ in forward_domain.obligations
    ]
    for candidate in range(forward_domain.candidate_count):
        for obligation_index in forward_domain.candidate_obligation_indices(candidate):
            obligation_candidates[int(obligation_index)].append(candidate)
    return OracleProblem(
        frame_uids=tuple(reference_domain.frame_uids),
        family_ids=tuple(item.family_id for item in forward_domain.families),
        family_weights=tuple(
            tuple(float(value) for value in reference_domain.family(item.family_id).weights)
            for item in forward_domain.families
        ),
        forward_rows=tuple(
            tuple(
                tuple(int(value) for value in family.candidate_witness_indices(candidate))
                for candidate in range(forward_domain.candidate_count)
            )
            for family in forward_domain.families
        ),
        correlation_unit_codes=tuple(
            int(value) for value in forward_domain.candidate_correlation_unit_codes
        ),
        obligations=tuple(
            OracleObligation(
                obligation.obligation_id,
                obligation.minimum_selected_frames,
                tuple(obligation_candidates[index]),
                required=obligation.required,
            )
            for index, obligation in enumerate(forward_domain.obligations)
        ),
    )


def _assert_score_matches_direct(reference_domain, forward_domain, state, candidate: int) -> None:
    score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
    expected_coverage: list[float] = []
    expected_rep = 0.0
    expected_diversity: list[float] = []
    for family_view, family_state in zip(
        forward_domain.families, state.family_states, strict=True
    ):
        witnesses = np.asarray(family_view.candidate_witness_indices(candidate), dtype=np.int64)
        multiplicity = family_state.multiplicity[witnesses]
        weights = np.asarray(reference_domain.family(family_view.family_id).weights)[witnesses]
        expected_coverage.append(float(np.sum(weights[multiplicity == 0], dtype=np.float64)))
        expected_rep += float(
            np.sum(weights / (multiplicity.astype(np.float64) + 1.0), dtype=np.float64)
        )
        if witnesses.size:
            expected_diversity.append(
                float(np.mean(1.0 / (multiplicity.astype(np.float64) + 1.0), dtype=np.float64))
            )
    assert score.family_coverage_gains == pytest.approx(expected_coverage, abs=1.0e-15)
    assert score.total_coverage_gain == pytest.approx(sum(expected_coverage), abs=1.0e-15)
    assert score.representative_gain == pytest.approx(expected_rep, abs=1.0e-15)
    assert score.sparse_diversity == pytest.approx(
        0.0 if not expected_diversity else np.mean(expected_diversity), abs=1.0e-15
    )


def test_mvsel2_forward_view_exposes_no_inverse_adjacency() -> None:
    _, index, forward = _forward_fixture()
    assert forward.mvidx1_content_digest == index.content_digest
    domain = forward.domain("target")
    assert not hasattr(domain, "obligation_candidates")
    assert not hasattr(domain, "obligation_offsets")
    for family in domain.families:
        assert not hasattr(family, "witness_candidates")
        assert not hasattr(family, "witness_offsets")


def test_mvsel2_native_forward_restore_never_opens_inverse_arrays(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, index, _ = _forward_fixture()
    pointer = mdstats.write_target_coverage_sparse_index_native_record(
        index, tmp_path / "records"
    )
    labels: list[str] = []
    packed_labels: list[str] = []
    original = mvidx_store._read_npy
    original_packed = mvidx_store._read_packed_npy

    def sentinel(*args, label: str, **kwargs):
        labels.append(label)
        if label in {"obligation_offsets", "obligation_candidates"}:
            raise AssertionError(f"inverse array opened: {label}")
        return original(*args, label=label, **kwargs)

    def packed_sentinel(*args, label: str, **kwargs):
        packed_labels.append(label)
        if "witness_offsets" in label or "witness_candidates" in label:
            raise AssertionError(f"inverse packed array opened: {label}")
        return original_packed(*args, label=label, **kwargs)

    monkeypatch.setattr(mvidx_store, "_read_npy", sentinel)
    monkeypatch.setattr(mvidx_store, "_read_packed_npy", packed_sentinel)
    restored = mvidx_store.read_target_coverage_sparse_index_forward_view_native_record(
        pointer, tmp_path, mmap_threshold_bytes=0
    )
    assert restored.mvidx1_content_digest == index.content_digest
    assert set(labels) == {
        "candidate_obligation_offsets",
        "candidate_obligations",
        "candidate_correlation_unit_codes",
    }
    assert set(packed_labels) == {
        "packed family candidate_offsets",
        "packed family candidate_witnesses",
    }
    for family in restored.domain("target").families:
        root = family.candidate_witnesses
        while isinstance(getattr(root, "base", None), np.ndarray):
            root = root.base
        assert isinstance(root, np.memmap)


def test_mvsel2_forward_scoring_and_mutation_match_direct_random_sequence() -> None:
    reference, index, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    sparse_domain = index.domain("target")
    forward_domain = forward.domain("target")
    state = build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain, requested_cardinality=8
    )
    rng = np.random.default_rng(20260818)
    selected: list[int] = []
    for candidate in rng.choice(forward_domain.candidate_count, size=8, replace=False):
        candidate = int(candidate)
        _assert_score_matches_direct(reference_domain, forward_domain, state, candidate)
        select_target_multi_view_candidate_v2(candidate, forward_domain, state)
        selected.append(candidate)

        for family_view, family_state in zip(
            forward_domain.families, state.family_states, strict=True
        ):
            expected_multiplicity = np.zeros(family_view.witness_count, dtype=np.int32)
            for selected_candidate in selected:
                expected_multiplicity[
                    np.asarray(
                        family_view.candidate_witness_indices(selected_candidate), dtype=np.int64
                    )
                ] += 1
            np.testing.assert_array_equal(family_state.multiplicity, expected_multiplicity)
            expected_mass = float(
                np.sum(
                    np.asarray(reference_domain.family(family_view.family_id).weights)[
                        expected_multiplicity > 0
                    ],
                    dtype=np.float64,
                )
            )
            assert family_state.coverage_mass == pytest.approx(expected_mass, abs=2.0e-15)
        np.testing.assert_array_equal(
            state.obligation_counts,
            mdstats.indexed_obligation_selected_counts(sparse_domain, selected),
        )

    for candidate in reversed(selected):
        deselect_target_multi_view_candidate_v2(candidate, forward_domain, state)
    assert state.selected_order == []
    assert np.all(state.available)
    assert state.representative_utility == 0.0
    assert state.unsatisfied_required_obligation_count == sum(
        item.required for item in forward_domain.obligations
    )
    assert not np.any(state.obligation_counts)
    assert not np.any(state.correlation_unit_counts)
    for family_state in state.family_states:
        assert family_state.coverage_mass == 0.0
        assert not np.any(family_state.multiplicity)


def test_mvsel2_batch_and_worker_settings_preserve_canonical_scores() -> None:
    reference, _, forward = _forward_fixture()
    domain = forward.domain("target")
    state = build_target_multi_view_forward_state_v2(reference.domain("target"), domain)
    candidates = (7, 1, 12, 4)
    baseline = score_target_multi_view_candidates_v2(
        candidates, domain, state, batch_size=1, workers=1
    )
    alternate = score_target_multi_view_candidates_v2(
        reversed(candidates), domain, state, batch_size=3, workers=4
    )
    assert baseline == alternate
    assert [item.candidate_index for item in baseline] == sorted(candidates)


def test_mvsel2_phase_a_matches_independent_full_forward_oracle_at_every_rank() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    oracle = exact_forward_order(
        _oracle_problem(reference_domain, forward_domain),
        forward_domain.candidate_count,
    )
    state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    rank = 0
    while state.unsatisfied_required_obligation_count > 0 or any(
        item.coverage_mass < 0.95 - 1.0e-14 for item in state.family_states
    ):
        choice = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain, forward_domain, state
        )
        expected = oracle[rank]
        assert choice.candidate_index == expected.candidate_index
        assert choice.bottleneck_family_id == expected.bottleneck_family_id
        assert choice.score.hard_obligation_gain == expected.hard_gain
        assert choice.score.total_coverage_gain == pytest.approx(
            expected.total_coverage_gain, abs=2.0e-15
        )
        assert choice.score.representative_gain == pytest.approx(
            expected.representative_gain, abs=2.0e-15
        )
        assert choice.score.sparse_diversity == pytest.approx(
            expected.diversity, abs=2.0e-15
        )
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )
        rank += 1
    assert rank > 0
    assert oracle[rank].phase == "representative_fill"


def test_mvsel2_phase_a_worker_and_batch_settings_preserve_prefix_and_telemetry() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    left = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    right = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    for _ in range(6):
        first = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain, forward_domain, left, batch_size=1, workers=1
        )
        second = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain, forward_domain, right, batch_size=7, workers=4
        )
        assert first == second
        assert first.telemetry.candidate_evaluation_forward_edges > 0
        select_target_multi_view_candidate_v2(
            first.candidate_index, forward_domain, left, score=first.score
        )
        select_target_multi_view_candidate_v2(
            second.candidate_index, forward_domain, right, score=second.score
        )


def _advance_phase_a(reference_domain, forward_domain, state) -> None:
    while state.unsatisfied_required_obligation_count > 0 or any(
        item.coverage_mass < 0.95 - 1.0e-14 for item in state.family_states
    ):
        choice = choose_target_multi_view_phase_a_candidate_v2(
            reference_domain, forward_domain, state
        )
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )


def test_mvsel2_phase_b_lazy_matches_full_forward_and_independent_oracle() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    oracle = exact_forward_order(
        _oracle_problem(reference_domain, forward_domain),
        forward_domain.candidate_count,
    )
    lazy_state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    full_state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    _advance_phase_a(reference_domain, forward_domain, lazy_state)
    _advance_phase_a(reference_domain, forward_domain, full_state)
    assert lazy_state.selected_order == full_state.selected_order
    transition = lazy_state.selected_count
    frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, lazy_state)

    while lazy_state.selected_count < forward_domain.candidate_count:
        lazy = choose_target_multi_view_phase_b_candidate_v2(
            reference_domain, forward_domain, lazy_state, frontier
        )
        full = choose_target_multi_view_phase_b_full_forward_v2(
            reference_domain, forward_domain, full_state
        )
        expected = oracle[lazy_state.selected_count]
        assert lazy.candidate_index == full.candidate_index == expected.candidate_index
        assert lazy.score.representative_gain == pytest.approx(
            full.score.representative_gain, abs=2.0e-15
        )
        assert lazy.score.sparse_diversity == pytest.approx(
            full.score.sparse_diversity, abs=2.0e-15
        )
        assert not lazy.telemetry.fallback_used
        select_target_multi_view_candidate_v2(
            lazy.candidate_index, forward_domain, lazy_state, score=lazy.score
        )
        select_target_multi_view_candidate_v2(
            full.candidate_index, forward_domain, full_state, score=full.score
        )
    assert transition > 0
    assert lazy_state.selected_order == full_state.selected_order == [
        item.candidate_index for item in oracle
    ]


def test_mvsel2_phase_b_frontier_rebuild_preserves_authority() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    left = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    right = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    _advance_phase_a(reference_domain, forward_domain, left)
    _advance_phase_a(reference_domain, forward_domain, right)
    left_frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, left)
    right_frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, right)
    for rank in range(5):
        if rank in {1, 3}:
            right_frontier = build_target_multi_view_lazy_frontier_v2(
                forward_domain, right
            )
        left_choice = choose_target_multi_view_phase_b_candidate_v2(
            reference_domain, forward_domain, left, left_frontier
        )
        right_choice = choose_target_multi_view_phase_b_candidate_v2(
            reference_domain, forward_domain, right, right_frontier
        )
        assert left_choice.candidate_index == right_choice.candidate_index
        select_target_multi_view_candidate_v2(
            left_choice.candidate_index, forward_domain, left, score=left_choice.score
        )
        select_target_multi_view_candidate_v2(
            right_choice.candidate_index, forward_domain, right, score=right_choice.score
        )


def test_mvsel2_plan_rungs_are_independently_qualified_and_setting_invariant() -> None:
    reference, index, forward = _forward_fixture()
    policy = TargetMultiViewSelectorPolicyV2(target_sizes=(4, 8, 12, 16))
    baseline = build_target_multi_view_selection_plan_v2(
        reference, forward, policy=policy, batch_size=1, workers=1
    )
    alternate = build_target_multi_view_selection_plan_v2(
        reference, forward, policy=policy, batch_size=7, workers=4,
        frontier_rebuild_interval=2,
    )
    assert [item.frame_uid for item in baseline.domain("target").master_order] == [
        item.frame_uid for item in alternate.domain("target").master_order
    ]
    assert TargetMultiViewSelectionPlanV2.from_dict(baseline.to_dict()).content_digest == baseline.content_digest
    validate_target_multi_view_selection_authority_v2(
        baseline,
        target_coverage_reference=reference,
        target_coverage_sparse_index=index,
        query_workers=2,
    )


@pytest.mark.parametrize("seed", [7, 29, 113])
def test_mvsel2_lazy_matches_full_forward_on_random_small_graphs(seed: int) -> None:
    rng = np.random.default_rng(seed)
    candidate_count = 12
    family_count = 3
    family_ids = tuple(f"f{index}" for index in range(family_count))
    reference_families = []
    forward_families = []
    oracle_rows = []
    oracle_weights = []
    for family_index, family_id in enumerate(family_ids):
        witness_count = 7 + family_index
        weights = rng.random(witness_count)
        weights /= np.sum(weights, dtype=np.float64)
        rows: list[tuple[int, ...]] = []
        for candidate in range(candidate_count):
            chosen = np.flatnonzero(rng.random(witness_count) < 0.4)
            if candidate < witness_count:
                chosen = np.unique(np.append(chosen, candidate))
            rows.append(tuple(int(value) for value in chosen))
        offsets = np.zeros(candidate_count + 1, dtype=np.uint64)
        offsets[1:] = np.cumsum([len(row) for row in rows], dtype=np.uint64)
        indices = np.asarray([value for row in rows for value in row], dtype=np.uint32)
        forward_families.append(SimpleNamespace(
            family_id=family_id,
            witness_count=witness_count,
            candidate_count=candidate_count,
            candidate_offsets=offsets,
            candidate_witnesses=indices,
            candidate_witness_indices=lambda candidate, rows=tuple(rows): np.asarray(
                rows[int(candidate)], dtype=np.uint32
            ),
        ))
        reference_families.append(SimpleNamespace(family_id=family_id, weights=weights))
        oracle_rows.append(tuple(rows))
        oracle_weights.append(tuple(float(value) for value in weights))
    obligations = (
        SimpleNamespace(obligation_id="o0", minimum_selected_frames=1, required=True),
        SimpleNamespace(obligation_id="o1", minimum_selected_frames=2, required=True),
    )
    candidate_obligation_rows = tuple(
        tuple(index for index, members in enumerate(((0, 3, 8), (1, 4, 7, 10))) if candidate in members)
        for candidate in range(candidate_count)
    )
    correlation_codes = rng.integers(0, 3, size=candidate_count, dtype=np.uint32)
    forward_domain = SimpleNamespace(
        candidate_count=candidate_count,
        families=tuple(forward_families),
        obligations=obligations,
        correlation_unit_ids=("u0", "u1", "u2"),
        candidate_correlation_unit_codes=correlation_codes,
        candidate_obligation_indices=lambda candidate: np.asarray(
            candidate_obligation_rows[int(candidate)], dtype=np.uint32
        ),
    )
    by_id = {family.family_id: family for family in reference_families}
    reference_domain = SimpleNamespace(
        frame_uids=tuple(f"uid-{candidate:02d}" for candidate in range(candidate_count)),
        families=tuple(reference_families),
        family=lambda family_id: by_id[family_id],
    )
    oracle = exact_forward_order(OracleProblem(
        frame_uids=reference_domain.frame_uids,
        family_ids=family_ids,
        family_weights=tuple(oracle_weights),
        forward_rows=tuple(oracle_rows),
        correlation_unit_codes=tuple(int(value) for value in correlation_codes),
        obligations=(
            OracleObligation("o0", 1, (0, 3, 8)),
            OracleObligation("o1", 2, (1, 4, 7, 10)),
        ),
    ), candidate_count)
    state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
    _advance_phase_a(reference_domain, forward_domain, state)
    frontier = build_target_multi_view_lazy_frontier_v2(forward_domain, state)
    while state.selected_count < candidate_count:
        choice = choose_target_multi_view_phase_b_candidate_v2(
            reference_domain, forward_domain, state, frontier
        )
        expected = oracle[state.selected_count]
        assert choice.candidate_index == expected.candidate_index
        select_target_multi_view_candidate_v2(
            choice.candidate_index, forward_domain, state, score=choice.score
        )
