from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib
import time
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data._sparse_vector_kernels import (
    csr_gather_rows,
    iter_csr_edge_batches,
)
from mdstats.training_data.resources import StageResourceScope
from mdstats.training_data.target_multi_view_qualification import (
    TargetMultiViewSelectorTelemetry,
    _qualification_provenance_codes,
    _selector_telemetry_indices,
    _selector_telemetry_indices_bounded,
    _selector_telemetry_reference,
    build_target_multi_view_qualification_plan,
)


_mvqual_module = importlib.import_module(
    "mdstats.training_data.target_multi_view_qualification"
)


@dataclass(frozen=True)
class _SparseFamily:
    family_id: str
    rows: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        offsets = np.zeros(len(self.rows) + 1, dtype=np.uint64)
        for index, row in enumerate(self.rows, start=1):
            offsets[index] = offsets[index - 1] + len(row)
        witnesses = np.asarray(
            [witness for row in self.rows for witness in row], dtype=np.uint32
        )
        object.__setattr__(self, "candidate_offsets", offsets)
        object.__setattr__(self, "candidate_witnesses", witnesses)

    @property
    def witness_count(self) -> int:
        return 6

    @property
    def candidate_count(self) -> int:
        return len(self.rows)

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        return np.asarray(self.rows[candidate_index], dtype=np.uint32)


def _fixture() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    frame_uids = ("f0", "f1", "f2", "f3", "f4")
    family_a = _SparseFamily(
        "family-a",
        (
            (0, 1, 2),
            (1, 2, 3),
            (2, 4),
            (3, 4, 5),
            (0, 5),
        ),
    )
    family_b = _SparseFamily(
        "family-b",
        (
            (0, 3),
            (1, 4),
            (2, 3, 5),
            (0, 2, 4),
            (1, 5),
        ),
    )
    weights = {
        "family-a": np.asarray((0.07, 0.11, 0.19, 0.23, 0.17, 0.23), dtype=np.float64),
        "family-b": np.asarray((0.13, 0.17, 0.20, 0.09, 0.18, 0.23), dtype=np.float64),
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
    role = SimpleNamespace(
        development_intervals=(
            SimpleNamespace(
                frame_uids=("f0", "f1"), run_id="run-a", condition_id="cond-x", unit_id="a"
            ),
            SimpleNamespace(
                frame_uids=("f2",), run_id="run-b", condition_id="cond-x", unit_id="b"
            ),
            SimpleNamespace(
                frame_uids=("f3", "f4"), run_id="run-c", condition_id="cond-y", unit_id="c"
            ),
        )
    )
    return reference, sparse, role


def _selected_inputs(
    reference: SimpleNamespace,
    role: SimpleNamespace,
    selected_uids: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(
        reference, role
    )
    selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    return selected, run_codes, condition_codes


def test_mvqual_mem1_current_vectorized_telemetry_matches_frozen_reference() -> None:
    reference, sparse, role = _fixture()
    selected_uids = ("f0", "f2", "f3")
    expected = _selector_telemetry_reference(reference, sparse, role, selected_uids)
    selected, run_codes, condition_codes = _selected_inputs(reference, role, selected_uids)

    actual = _selector_telemetry_indices(
        reference,
        sparse,
        selected,
        run_codes,
        condition_codes,
    )

    assert actual == expected


def test_mvqual_mem1_reference_locks_unique_owner_and_provenance_semantics() -> None:
    reference, sparse, role = _fixture()
    telemetry = _selector_telemetry_reference(
        reference, sparse, role, ("f0", "f2", "f3")
    )

    assert telemetry.uncovered_witness_count == 1
    assert telemetry.uncovered_reference_mass == np.float64(0.17)
    assert telemetry.unique_reference_mass_fraction == np.float64(1.05 / 2.0)
    assert telemetry.zero_unique_candidate_fraction == 0.0
    assert telemetry.correlation_unit_count == 3
    assert telemetry.maximum_correlation_unit_fraction == 1.0 / 3.0
    assert telemetry.run_count == 3
    assert telemetry.condition_count == 2


@pytest.mark.parametrize("edge_limit", (1, 2, 3, 4, 7, 1_000_000))
@pytest.mark.parametrize(
    "selected_uids",
    (
        ("f0",),
        ("f0", "f2", "f3"),
        ("f0", "f1", "f2", "f3", "f4"),
    ),
)
def test_mvqual_mem1_bounded_telemetry_is_exact_for_all_chunk_sizes(
    edge_limit: int,
    selected_uids: tuple[str, ...],
) -> None:
    reference, sparse, role = _fixture()
    expected = _selector_telemetry_reference(reference, sparse, role, selected_uids)
    selected, run_codes, condition_codes = _selected_inputs(reference, role, selected_uids)

    result = _selector_telemetry_indices_bounded(
        reference,
        sparse,
        selected,
        run_codes,
        condition_codes,
        max_edges=edge_limit,
    )

    assert result.telemetry == expected
    assert result.maximum_chunk_edges <= edge_limit
    assert result.maximum_selected_row_edges <= 3


def test_mvqual_mem1_bounded_telemetry_reuses_exact_covered_mask_for_mass() -> None:
    reference, sparse, role = _fixture()
    selected_uids = ("f0", "f2", "f3")
    selected, run_codes, condition_codes = _selected_inputs(reference, role, selected_uids)

    result = _selector_telemetry_indices_bounded(
        reference,
        sparse,
        selected,
        run_codes,
        condition_codes,
        max_edges=2,
    )

    masses = dict(result.covered_mass_by_family)
    expected_a = float(np.sum(reference.family("family-a").weights, dtype=np.float64))
    expected_b = float(
        np.sum(reference.family("family-b").weights[[0, 2, 3, 4, 5]], dtype=np.float64)
    )
    assert masses == {"family-a": expected_a, "family-b": expected_b}
    assert result.streamed_edge_count == 32
    assert result.maximum_chunk_edges == 2
    assert result.maximum_selected_row_edges == 3


def test_mvqual_mem1_all_selected_candidates_have_no_unique_owner() -> None:
    reference, sparse, role = _fixture()
    selected_uids = tuple(reference.frame_uids)
    selected, run_codes, condition_codes = _selected_inputs(reference, role, selected_uids)

    telemetry = _selector_telemetry_indices(
        reference,
        sparse,
        selected,
        run_codes,
        condition_codes,
        max_edges=1,
    )

    assert telemetry.uncovered_witness_count == 0
    assert telemetry.unique_reference_mass_fraction == 0.0
    assert telemetry.zero_unique_candidate_fraction == 1.0


def test_strict_csr_edge_stream_reconstructs_canonical_gather_and_owners() -> None:
    offsets = np.asarray((0, 0, 5, 7, 17, 18), dtype=np.uint64)
    indices = np.arange(100, 118, dtype=np.uint32)
    rows = np.asarray((0, 3, 1, 4), dtype=np.int64)
    expected_indices, expected_lengths = csr_gather_rows(offsets, indices, rows)
    expected_owners = np.repeat(
        np.arange(rows.size, dtype=np.int64), expected_lengths
    )

    for edge_limit in (1, 2, 3, 4, 32):
        chunks = list(
            iter_csr_edge_batches(offsets, indices, rows, max_edges=edge_limit)
        )
        assert chunks
        assert all(0 < chunk_indices.size <= edge_limit for chunk_indices, _ in chunks)
        actual_indices = np.concatenate([chunk_indices for chunk_indices, _ in chunks])
        actual_owners = np.concatenate([owners for _, owners in chunks])
        np.testing.assert_array_equal(actual_indices, expected_indices)
        np.testing.assert_array_equal(actual_owners, expected_owners)


def test_strict_csr_edge_stream_splits_one_oversized_row_and_preserves_repeats() -> None:
    offsets = np.asarray((0, 2, 11, 11, 14), dtype=np.uint64)
    indices = np.arange(14, dtype=np.uint32)
    rows = np.asarray((1, 2, 1, 3), dtype=np.int64)
    expected_indices, expected_lengths = csr_gather_rows(offsets, indices, rows)
    expected_owners = np.repeat(
        np.arange(rows.size, dtype=np.int64), expected_lengths
    )

    chunks = list(iter_csr_edge_batches(offsets, indices, rows, max_edges=3))

    assert max(chunk_indices.size for chunk_indices, _ in chunks) == 3
    np.testing.assert_array_equal(
        np.concatenate([chunk_indices for chunk_indices, _ in chunks]), expected_indices
    )
    np.testing.assert_array_equal(
        np.concatenate([owners for _, owners in chunks]), expected_owners
    )


def test_strict_csr_edge_stream_validates_obvious_contract_errors() -> None:
    offsets = np.asarray((0, 1, 2), dtype=np.uint64)
    indices = np.asarray((3, 4), dtype=np.uint32)

    with pytest.raises(ValueError, match="positive"):
        list(iter_csr_edge_batches(offsets, indices, np.asarray((0,)), max_edges=0))
    with pytest.raises(ValueError, match="outside"):
        list(iter_csr_edge_batches(offsets, indices, np.asarray((2,)), max_edges=1))
    with pytest.raises(ValueError, match="one-dimensional"):
        list(
            iter_csr_edge_batches(
                offsets, indices, np.asarray(((0,),)), max_edges=1
            )
        )


def _hex_digest(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _qualification_builder_fixture() -> tuple[object, ...]:
    frame_uids = ("f0", "f1", "f2", "f3", "f4")
    reference_family = SimpleNamespace(
        family_id="family-a",
        values=np.linspace(0.0, 1.0, 6, dtype=np.float64),
        feature_names=("x",),
    )
    reference_domain = SimpleNamespace(
        label_domain_id="domain-a",
        frame_uids=frame_uids,
        families=(reference_family,),
        strata=(SimpleNamespace(stratum_id="stratum-a"),),
        content_digest=_hex_digest("reference-domain"),
    )
    target_coverage_reference = SimpleNamespace(
        dataset_id="dataset-a",
        content_digest=_hex_digest("reference"),
        policy=SimpleNamespace(coverage_threshold=0.95),
        domains=(reference_domain,),
    )

    sparse_domain = SimpleNamespace(
        content_digest=_hex_digest("sparse-domain"),
        families=(SimpleNamespace(family_id="family-a", witness_count=6),),
        candidate_count=len(frame_uids),
        candidate_obligation_offsets=np.zeros(len(frame_uids) + 1, dtype=np.uint64),
        obligations=(),
    )
    target_coverage_sparse_index = SimpleNamespace(
        dataset_id="dataset-a",
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        content_digest=_hex_digest("sparse-index"),
        domain=lambda label: sparse_domain,
    )

    target_data_role_freeze = SimpleNamespace(
        content_digest=_hex_digest("role-freeze"),
        domain=lambda label: SimpleNamespace(
            development_intervals=(
                SimpleNamespace(
                    frame_uids=frame_uids,
                    run_id="run-a",
                    condition_id="condition-a",
                    unit_id="unit-a",
                ),
            )
        ),
    )
    target_coverage_feasibility = SimpleNamespace(
        dataset_id="dataset-a",
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        content_digest=_hex_digest("feasibility"),
        states=(),
    )

    legacy_domain = SimpleNamespace(
        content_digest=_hex_digest("legacy-domain"),
        rungs=(
            SimpleNamespace(
                target_size=2,
                materializable=True,
                frame_uids=("f0", "f1"),
            ),
        ),
    )
    legacy_target_data_ladder = SimpleNamespace(
        dataset_id="dataset-a",
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        content_digest=_hex_digest("legacy-ladder"),
        domain=lambda label: legacy_domain,
    )

    repair_domain = SimpleNamespace(
        content_digest=_hex_digest("repair-domain"),
        rungs=(
            SimpleNamespace(
                target_size=2,
                materializable=True,
                frame_uids=("f0", "f2"),
            ),
        ),
    )
    target_multi_view_repair = SimpleNamespace(
        dataset_id="dataset-a",
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_coverage_sparse_index_digest=target_coverage_sparse_index.content_digest,
        content_digest=_hex_digest("repair"),
        domain=lambda label: repair_domain,
    )
    return (
        target_coverage_reference,
        target_coverage_sparse_index,
        target_coverage_feasibility,
        target_data_role_freeze,
        legacy_target_data_ladder,
        target_multi_view_repair,
    )


def _fake_mvqual_score_job(
    _target_coverage_reference: object,
    _reference_domain: object,
    _sparse_domain: object,
    *,
    label: str,
    selector: str,
    target_size: int,
    selected_uids: tuple[str, ...],
    uid_to_index: dict[str, int],
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    query_workers: int,
    sparse_max_edges: int,
) -> object:
    del run_codes, condition_codes, query_workers
    # Keep two nominal workers overlapped long enough for a constrained-RAM
    # test to prove that PARCORE1, rather than task duration, limits admission.
    time.sleep(0.02)
    selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    report = SimpleNamespace(
        label_domain_id=label,
        selected_frame_uids=tuple(selected_uids),
        family_reports=(
            SimpleNamespace(
                family_id="family-a",
                required=True,
                covered_reference_mass=0.97,
                coverage_passed=True,
                extent_passed=True,
                extent_failures=(),
            ),
        ),
        stratum_reports=(
            SimpleNamespace(
                stratum_id="stratum-a",
                required=True,
                selected_frame_count=len(selected_uids),
                minimum_selected_frames=1,
                passed=True,
            ),
        ),
        passed=True,
        content_digest=_hex_digest(
            f"report:{label}:{selector}:{target_size}:{','.join(selected_uids)}"
        ),
    )
    telemetry = TargetMultiViewSelectorTelemetry(
        uncovered_witness_count=0,
        uncovered_reference_mass=0.0,
        unique_reference_mass_fraction=0.25,
        zero_unique_candidate_fraction=0.0,
        correlation_unit_count=1,
        maximum_correlation_unit_fraction=1.0,
        run_count=1,
        condition_count=1,
    )
    return _mvqual_module._MvqualScoreResult(
        label_domain_id=label,
        selector=selector,
        target_size=target_size,
        report=report,
        selected_indices=selected,
        telemetry=telemetry,
        hard_state=(True, ()),
        streamed_edge_count=20 * len(selected_uids),
        maximum_chunk_edges=min(int(sparse_max_edges), 3),
        maximum_selected_row_edges=3,
        direct_seconds=0.001,
        sparse_seconds=0.002,
        crosscheck_seconds=0.0001,
        hard_seconds=0.0001,
    )


def test_mvqual_mem1_full_authority_is_identical_across_chunks_and_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _qualification_builder_fixture()
    monkeypatch.setattr(_mvqual_module, "_mvqual_score_job", _fake_mvqual_score_job)

    baseline = build_target_multi_view_qualification_plan(
        *inputs,
        scoring_workers=1,
        sparse_max_edges=1,
    )
    two_worker_scope = StageResourceScope(
        stage_name="TARGET-DATA2C-MVQUAL-PAR1",
        cpu_threads_available=2,
        cpu_threads_budget=2,
        python_workers=2,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        gpu_jobs=0,
        ram_budget_bytes=None,
    )

    for edge_limit, workers, scope in (
        (4, 1, None),
        (1, 2, two_worker_scope),
        (4, 2, two_worker_scope),
    ):
        plan = build_target_multi_view_qualification_plan(
            *inputs,
            scoring_workers=workers,
            sparse_max_edges=edge_limit,
            resource_scope=scope,
        )
        assert plan.content_digest == baseline.content_digest
        assert plan.to_dict() == baseline.to_dict()


def test_mvqual_mem1_ram_admission_backpressures_without_changing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _qualification_builder_fixture()
    monkeypatch.setattr(_mvqual_module, "_mvqual_score_job", _fake_mvqual_score_job)
    reference_domain = inputs[0].domains[0]
    sparse_domain = inputs[1].domain("domain-a")
    edge_limit = 4
    selected_count = 2
    task_bytes = _mvqual_module._estimate_mvqual_score_memory(
        reference_domain,
        sparse_domain,
        selected_count,
        sparse_max_edges=edge_limit,
    ).peak_bytes
    retained_bytes = 2 * _mvqual_module._estimate_mvqual_retained_result_bytes(
        reference_domain, selected_count
    )
    coordinator_bytes = (
        retained_bytes + len(reference_domain.frame_uids) * 112 + 64 * 1024
    )
    ram_budget = coordinator_bytes + task_bytes + max(1, task_bytes // 2)
    assert coordinator_bytes + task_bytes <= ram_budget
    assert coordinator_bytes + 2 * task_bytes > ram_budget

    snapshots: list[object] = []
    constrained_scope = StageResourceScope(
        stage_name="TARGET-DATA2C-MVQUAL-PAR1",
        cpu_threads_available=2,
        cpu_threads_budget=2,
        python_workers=2,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        gpu_jobs=0,
        ram_budget_bytes=ram_budget,
    )
    constrained = build_target_multi_view_qualification_plan(
        *inputs,
        scoring_workers=2,
        sparse_max_edges=edge_limit,
        resource_scope=constrained_scope,
        execution_telemetry_callback=snapshots.append,
    )
    serial = build_target_multi_view_qualification_plan(
        *inputs,
        scoring_workers=1,
        sparse_max_edges=edge_limit,
    )

    assert constrained.content_digest == serial.content_digest
    assert constrained.to_dict() == serial.to_dict()
    assert snapshots
    assert max(snapshot.allocated_workers for snapshot in snapshots) == 2
    assert max(snapshot.max_busy_workers for snapshot in snapshots) == 1
    assert max(snapshot.memory_backpressure_events for snapshot in snapshots) >= 1
    assert max(snapshot.peak_accounted_memory_bytes for snapshot in snapshots) <= ram_budget
