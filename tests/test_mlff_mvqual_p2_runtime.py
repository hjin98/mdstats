from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data import mvqual_p2_runtime as runtime
from mdstats.training_data import target_multi_view_qualification as mvqual


@dataclass(frozen=True)
class _SparseFamily:
    family_id: str
    rows: tuple[tuple[int, ...], ...]
    witness_count: int

    def __post_init__(self) -> None:
        offsets = np.zeros(len(self.rows) + 1, dtype=np.uint64)
        for index, row in enumerate(self.rows, start=1):
            offsets[index] = offsets[index - 1] + len(row)
        witnesses = np.asarray(
            [witness for row in self.rows for witness in row], dtype=np.uint32
        )
        object.__setattr__(self, "candidate_offsets", offsets)
        object.__setattr__(self, "candidate_witnesses", witnesses)


def _fixture() -> tuple[object, object, np.ndarray, np.ndarray, tuple[np.ndarray, ...]]:
    frame_uids = ("f0", "f1", "f2", "f3", "f4")
    family_a = _SparseFamily(
        "family-a",
        (
            (0, 1, 2),
            (1, 3),
            (0, 3, 4),
            (2, 4, 5),
            (5, 6),
        ),
        7,
    )
    # Repeated witness 0 in one row is deliberately adversarial.  It freezes
    # edge-multiplicity semantics rather than assuming CSR rows are deduplicated.
    family_b = _SparseFamily(
        "family-b",
        (
            (0, 0, 1),
            (1, 2, 3),
            (0, 3, 4),
            (2, 4, 5),
            (5, 6, 7),
        ),
        8,
    )
    weights = {
        "family-a": np.asarray(
            (0.07, 0.11, 0.13, 0.17, 0.19, 0.14, 0.19), dtype=np.float64
        ),
        "family-b": np.asarray(
            (0.05, 0.08, 0.11, 0.13, 0.17, 0.16, 0.14, 0.16), dtype=np.float64
        ),
    }
    reference = SimpleNamespace(
        frame_uids=frame_uids,
        family=lambda family_id: SimpleNamespace(weights=weights[family_id]),
    )
    sparse = SimpleNamespace(
        families=(family_a, family_b),
        candidate_correlation_unit_codes=np.asarray((0, 0, 1, 2, 2), dtype=np.int32),
        correlation_unit_ids=("u0", "u1", "u2"),
    )
    run_codes = np.asarray((0, 0, 1, 2, 2), dtype=np.int32)
    condition_codes = np.asarray((0, 0, 0, 1, 1), dtype=np.int32)
    selected = (
        np.asarray((0,), dtype=np.int64),
        np.asarray((0, 1), dtype=np.int64),
        np.asarray((0, 1, 2), dtype=np.int64),
        np.asarray((0, 1, 2, 3, 4), dtype=np.int64),
    )
    return reference, sparse, run_codes, condition_codes, selected


def _scientific_projection(result: object) -> tuple[object, object]:
    return result.telemetry, result.covered_mass_by_family


@pytest.mark.parametrize("edge_limit", (1, 2, 3, 7, 1_000_000))
def test_p2_progressive_sparse_matches_independent_m2_every_rung(edge_limit: int) -> None:
    reference, sparse, run_codes, condition_codes, selected_by_rung = _fixture()

    progressive = runtime._progressive_sparse_results_for_group(
        reference,
        sparse,
        selected_by_rung,
        run_codes,
        condition_codes,
        max_edges=edge_limit,
        workers=1,
    )

    assert len(progressive) == len(selected_by_rung)
    independent_streamed = 0
    for selected, actual in zip(selected_by_rung, progressive, strict=True):
        expected = mvqual._selector_telemetry_indices_bounded(
            reference,
            sparse,
            selected,
            run_codes,
            condition_codes,
            max_edges=edge_limit,
        )
        assert _scientific_projection(actual) == _scientific_projection(expected)
        assert actual.maximum_selected_row_edges == expected.maximum_selected_row_edges
        assert actual.maximum_chunk_edges <= edge_limit
        independent_streamed += expected.streamed_edge_count

    # Across a nested ladder P2 streams every edge in the largest selected set
    # exactly once.  M2 necessarily rescans prefixes and, when uniqueness exists,
    # performs its second owner pass as well.
    largest = selected_by_rung[-1]
    expected_progressive_edges = 0
    for family in sparse.families:
        lengths = family.candidate_offsets[largest + 1] - family.candidate_offsets[largest]
        expected_progressive_edges += int(np.sum(lengths, dtype=np.uint64))
    progressive_streamed = sum(item.streamed_edge_count for item in progressive)
    assert progressive_streamed == expected_progressive_edges
    assert progressive_streamed < independent_streamed


def test_p2_scientific_results_are_chunk_and_worker_invariant() -> None:
    reference, sparse, run_codes, condition_codes, selected_by_rung = _fixture()
    baseline = runtime._progressive_sparse_results_for_group(
        reference,
        sparse,
        selected_by_rung,
        run_codes,
        condition_codes,
        max_edges=1,
        workers=1,
    )

    for edge_limit, workers in ((2, 1), (3, 2), (1_000_000, 2)):
        actual = runtime._progressive_sparse_results_for_group(
            reference,
            sparse,
            selected_by_rung,
            run_codes,
            condition_codes,
            max_edges=edge_limit,
            workers=workers,
        )
        assert tuple(map(_scientific_projection, actual)) == tuple(
            map(_scientific_projection, baseline)
        )


def test_p2_owner_state_handles_loss_without_second_edge_pass() -> None:
    reference, sparse, run_codes, condition_codes, selected_by_rung = _fixture()
    actual = runtime._progressive_sparse_results_for_group(
        reference,
        sparse,
        selected_by_rung,
        run_codes,
        condition_codes,
        max_edges=2,
        workers=2,
    )

    # The independent implementation is the semantic oracle.  In this fixture
    # witnesses repeatedly move 0->1->2 and candidates lose their last unique
    # witness as later candidates enter the ladder.
    zero_unique = []
    for selected, value in zip(selected_by_rung, actual, strict=True):
        expected = mvqual._selector_telemetry_indices_bounded(
            reference,
            sparse,
            selected,
            run_codes,
            condition_codes,
            max_edges=2,
        )
        zero_unique.append(value.telemetry.zero_unique_candidate_fraction)
        assert value.telemetry.zero_unique_candidate_fraction == (
            expected.telemetry.zero_unique_candidate_fraction
        )
        assert value.telemetry.unique_reference_mass_fraction == (
            expected.telemetry.unique_reference_mass_fraction
        )
    assert len(set(zero_unique)) > 1


def test_p2_rejects_nonnested_progression() -> None:
    values = (
        np.asarray((0, 1), dtype=np.int64),
        np.asarray((1, 2), dtype=np.int64),
    )
    assert not runtime._is_exact_nested_indices(values)
    with pytest.raises(mvqual.TrainingDataInputError, match="exactly nested"):
        runtime._added_rows_by_rung(values)


def test_p2_installer_does_not_replace_direct_scientific_builder() -> None:
    canonical = mvqual.build_target_multi_view_qualification_plan
    sentinel = object()

    def fake_builder(
        target_coverage_reference: object,
        target_coverage_sparse_index: object,
        target_coverage_feasibility: object,
        target_data_role_freeze: object,
        legacy_target_data_ladder: object,
        target_multi_view_repair: object,
        *,
        policy: object = None,
        coverage_query_workers: int = 1,
        scoring_workers: int = 1,
        sparse_max_edges: int = 8,
        resource_scope: object = None,
        execution_telemetry_callback: object = None,
        job_telemetry_callback: object = None,
        progress_callback: object = None,
    ) -> object:
        del (
            target_coverage_reference,
            target_coverage_sparse_index,
            target_coverage_feasibility,
            target_data_role_freeze,
            legacy_target_data_ladder,
            target_multi_view_repair,
            policy,
            coverage_query_workers,
            scoring_workers,
            sparse_max_edges,
            resource_scope,
            execution_telemetry_callback,
            job_telemetry_callback,
            progress_callback,
        )
        return sentinel

    fake_mdstats = SimpleNamespace(build_target_multi_view_qualification_plan=fake_builder)
    runtime.install_mvqual_p2_runtime(fake_mdstats)
    partial_reference = SimpleNamespace(domains=(SimpleNamespace(),))
    result = fake_mdstats.build_target_multi_view_qualification_plan(
        partial_reference,
        object(),
        object(),
        object(),
        object(),
        object(),
    )

    assert result is sentinel
    assert mvqual.build_target_multi_view_qualification_plan is canonical
    assert runtime.last_mvqual_p2_execution_telemetry() is None
