"""Shared exact scoring kernel for the direct MVQUAL2 authority.

This module owns only local scoring/telemetry mechanics. It deliberately contains
no qualification plan, target-size population, migration, ladder, or rescue authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest
from ._sparse_vector_kernels import csr_row_lengths, iter_csr_edge_batches
from .target_coverage import score_target_subset_coverage
from .target_coverage_sparse_index import indexed_obligation_selected_counts

TARGET_MULTI_VIEW_QUALIFICATION_TELEMETRY_SCHEMA = "mdstats.target-multi-view-qualification-telemetry.v2"
_MVQUAL_STRICT_EDGE_LIMIT = 1_048_576

@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectorTelemetry:
    uncovered_witness_count: int
    uncovered_reference_mass: float
    unique_reference_mass_fraction: float
    zero_unique_candidate_fraction: float
    correlation_unit_count: int
    maximum_correlation_unit_fraction: float
    run_count: int
    condition_count: int

    def __post_init__(self) -> None:
        if int(self.uncovered_witness_count) < 0 or min(int(self.correlation_unit_count), int(self.run_count), int(self.condition_count)) < 0:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 telemetry counts are invalid.")
        for name in ("uncovered_reference_mass", "unique_reference_mass_fraction", "zero_unique_candidate_fraction", "maximum_correlation_unit_fraction"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < -1e-12:
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 telemetry mass/fraction is invalid.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_TELEMETRY_SCHEMA,
            "uncovered_witness_count": int(self.uncovered_witness_count),
            "uncovered_reference_mass": self.uncovered_reference_mass,
            "unique_reference_mass_fraction": self.unique_reference_mass_fraction,
            "zero_unique_candidate_fraction": self.zero_unique_candidate_fraction,
            "correlation_unit_count": int(self.correlation_unit_count),
            "maximum_correlation_unit_fraction": self.maximum_correlation_unit_fraction,
            "run_count": int(self.run_count),
            "condition_count": int(self.condition_count),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectorTelemetry":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_TELEMETRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL2 telemetry schema.")
        result = cls(
            uncovered_witness_count=int(payload["uncovered_witness_count"]),
            uncovered_reference_mass=float(payload["uncovered_reference_mass"]),
            unique_reference_mass_fraction=float(payload["unique_reference_mass_fraction"]),
            zero_unique_candidate_fraction=float(payload["zero_unique_candidate_fraction"]),
            correlation_unit_count=int(payload["correlation_unit_count"]),
            maximum_correlation_unit_fraction=float(payload["maximum_correlation_unit_fraction"]),
            run_count=int(payload["run_count"]), condition_count=int(payload["condition_count"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL2 telemetry digest mismatch.")
        return result



def _selector_telemetry_reference(
    reference_domain: Any, sparse_domain: Any, role_domain: Any, selected_uids: Sequence[str]
) -> TargetMultiViewSelectorTelemetry:
    """Frozen scalar reference for exact MVQUAL telemetry regression tests."""

    uid_to_index = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
    selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    total_uncovered_count = 0
    total_uncovered_mass = np.float64(0.0)
    total_unique_mass = np.float64(0.0)
    total_reference_mass = np.float64(0.0)
    unique_owner = np.zeros(len(reference_domain.frame_uids), dtype=np.bool_)
    for sparse_family in sparse_domain.families:
        family = reference_domain.family(sparse_family.family_id)
        weights = np.asarray(family.weights, dtype=np.float64)
        covered = np.zeros(sparse_family.witness_count, dtype=np.bool_)
        multiplicity = np.zeros(sparse_family.witness_count, dtype=np.int32)
        for candidate in selected:
            witnesses = np.asarray(
                sparse_family.candidate_witness_indices(int(candidate)), dtype=np.int64
            )
            covered[witnesses] = True
            multiplicity[witnesses] += 1
        total_uncovered_count += int(np.count_nonzero(~covered))
        total_uncovered_mass += np.sum(weights[~covered], dtype=np.float64)
        total_reference_mass += np.sum(weights, dtype=np.float64)
        unique_witness = multiplicity == 1
        total_unique_mass += np.sum(weights[unique_witness], dtype=np.float64)
        if np.any(unique_witness):
            for candidate in selected:
                witnesses = np.asarray(
                    sparse_family.candidate_witness_indices(int(candidate)), dtype=np.int64
                )
                if witnesses.size and np.any(unique_witness[witnesses]):
                    unique_owner[int(candidate)] = True
    zero_unique = 1.0 - float(np.count_nonzero(unique_owner[selected])) / float(len(selected))
    unique_fraction = (
        0.0
        if total_reference_mass <= 0.0
        else float(total_unique_mass / total_reference_mass)
    )
    unit_codes = np.asarray(
        sparse_domain.candidate_correlation_unit_codes, dtype=np.int64
    )[selected]
    counts = np.bincount(unit_codes, minlength=len(sparse_domain.correlation_unit_ids))
    nonzero = counts[counts > 0]
    max_unit_fraction = (
        0.0 if nonzero.size == 0 else float(np.max(nonzero)) / float(len(selected))
    )

    frame_to_run: dict[str, str] = {}
    frame_to_condition: dict[str, str] = {}
    for interval in role_domain.development_intervals:
        for uid in interval.frame_uids:
            if uid in uid_to_index:
                frame_to_run[uid] = str(getattr(interval, "run_id", interval.unit_id))
                frame_to_condition[uid] = str(
                    getattr(interval, "condition_id", interval.unit_id)
                )
    missing = [
        uid
        for uid in selected_uids
        if uid not in frame_to_run or uid not in frame_to_condition
    ]
    if missing:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL2 selected frame lacks DATA2A provenance mapping."
        )
    return TargetMultiViewSelectorTelemetry(
        uncovered_witness_count=total_uncovered_count,
        uncovered_reference_mass=float(total_uncovered_mass),
        unique_reference_mass_fraction=unique_fraction,
        zero_unique_candidate_fraction=zero_unique,
        correlation_unit_count=int(nonzero.size),
        maximum_correlation_unit_fraction=max_unit_fraction,
        run_count=len({frame_to_run[uid] for uid in selected_uids}),
        condition_count=len({frame_to_condition[uid] for uid in selected_uids}),
    )


def _selector_telemetry_indices(
    reference_domain: Any,
    sparse_domain: Any,
    selected: np.ndarray,
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    *,
    max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
) -> TargetMultiViewSelectorTelemetry:
    return _selector_telemetry_indices_bounded(
        reference_domain,
        sparse_domain,
        selected,
        run_codes,
        condition_codes,
        max_edges=max_edges,
    ).telemetry


def _selector_telemetry(
    reference_domain: Any, sparse_domain: Any, role_domain: Any, selected_uids: Sequence[str]
) -> TargetMultiViewSelectorTelemetry:
    uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(
        reference_domain, role_domain
    )
    try:
        selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    except KeyError as exc:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL2 selected frame is outside the reference domain."
        ) from exc
    return _selector_telemetry_indices(
        reference_domain, sparse_domain, selected, run_codes, condition_codes
    )

def _qualification_provenance_codes(reference_domain: Any, role_domain: Any) -> tuple[dict[str, int], np.ndarray, np.ndarray]:
    """Build immutable DATA2A provenance codes once per qualification domain."""

    uid_to_index = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
    run_codes = np.full(len(reference_domain.frame_uids), -1, dtype=np.int32)
    condition_codes = np.full(len(reference_domain.frame_uids), -1, dtype=np.int32)
    run_lookup: dict[str, int] = {}
    condition_lookup: dict[str, int] = {}
    for interval in role_domain.development_intervals:
        run_id = str(getattr(interval, "run_id", interval.unit_id))
        condition_id = str(getattr(interval, "condition_id", interval.unit_id))
        run_code = run_lookup.setdefault(run_id, len(run_lookup))
        condition_code = condition_lookup.setdefault(condition_id, len(condition_lookup))
        for uid in interval.frame_uids:
            index = uid_to_index.get(uid)
            if index is not None:
                run_codes[index] = run_code
                condition_codes[index] = condition_code
    return uid_to_index, run_codes, condition_codes

@dataclass(frozen=True, slots=True)
class _MvqualSparseTelemetryResult:
    """Execution-only bounded sparse telemetry and exact family cross-check state."""

    telemetry: TargetMultiViewSelectorTelemetry
    covered_mass_by_family: tuple[tuple[str, float], ...]
    streamed_edge_count: int
    maximum_chunk_edges: int
    maximum_selected_row_edges: int

def _selector_telemetry_indices_bounded(
    reference_domain: Any,
    sparse_domain: Any,
    selected: np.ndarray,
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    *,
    max_edges: int,
) -> _MvqualSparseTelemetryResult:
    """Bounded exact MVIDX telemetry for one selected candidate set.

    Integer witness multiplicity is accumulated through strict edge chunks.
    Scientific floating-point reductions remain one canonical full-witness
    reduction per family, so chunk size cannot change reduction association.
    """

    selected = np.asarray(selected, dtype=np.int64)
    if selected.ndim != 1 or selected.size < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 selected candidates must be nonempty and one-dimensional.")
    if selected.size > np.iinfo(np.int32).max:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 selected cardinality exceeds int32 multiplicity capacity.")
    edge_limit = int(max_edges)
    if edge_limit < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 sparse edge limit must be positive.")

    total_uncovered_count = 0
    total_uncovered_mass = np.float64(0.0)
    total_unique_mass = np.float64(0.0)
    total_reference_mass = np.float64(0.0)
    unique_owner = np.zeros(len(reference_domain.frame_uids), dtype=np.bool_)
    covered_mass_by_family: list[tuple[str, float]] = []
    streamed_edge_count = 0
    maximum_chunk_edges = 0
    maximum_selected_row_edges = 0

    for sparse_family in sparse_domain.families:
        family = reference_domain.family(sparse_family.family_id)
        weights = np.asarray(family.weights, dtype=np.float64)
        witness_count = int(sparse_family.witness_count)
        if witness_count < 0 or weights.ndim != 1 or weights.size != witness_count:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 sparse/reference witness cardinality mismatch.")
        multiplicity = np.zeros(witness_count, dtype=np.int32)
        row_lengths = csr_row_lengths(sparse_family.candidate_offsets, selected)
        if row_lengths.size:
            maximum_selected_row_edges = max(
                maximum_selected_row_edges, int(np.max(row_lengths))
            )

        for witness_indices, _owner_positions in iter_csr_edge_batches(
            sparse_family.candidate_offsets,
            sparse_family.candidate_witnesses,
            selected,
            max_edges=edge_limit,
        ):
            chunk_edges = int(witness_indices.size)
            streamed_edge_count += chunk_edges
            maximum_chunk_edges = max(maximum_chunk_edges, chunk_edges)
            witness_indices = np.asarray(witness_indices)
            if witness_indices.size and int(np.max(witness_indices)) >= witness_count:
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 MVIDX witness is outside the reference family.")
            np.add.at(multiplicity, witness_indices, 1)

        covered = multiplicity > 0
        unique_witness = multiplicity == 1
        total_uncovered_count += int(np.count_nonzero(~covered))
        total_uncovered_mass += np.sum(weights[~covered], dtype=np.float64)
        total_reference_mass += np.sum(weights, dtype=np.float64)
        total_unique_mass += np.sum(weights[unique_witness], dtype=np.float64)
        covered_mass_by_family.append(
            (
                str(sparse_family.family_id),
                float(np.sum(weights[covered], dtype=np.float64)),
            )
        )

        if np.any(unique_witness):
            for witness_indices, owner_positions in iter_csr_edge_batches(
                sparse_family.candidate_offsets,
                sparse_family.candidate_witnesses,
                selected,
                max_edges=edge_limit,
            ):
                chunk_edges = int(witness_indices.size)
                streamed_edge_count += chunk_edges
                maximum_chunk_edges = max(maximum_chunk_edges, chunk_edges)
                unique_edges = unique_witness[np.asarray(witness_indices)]
                if np.any(unique_edges):
                    unique_owner[
                        selected[np.asarray(owner_positions, dtype=np.int64)[unique_edges]]
                    ] = True

    zero_unique = 1.0 - float(np.count_nonzero(unique_owner[selected])) / float(len(selected))
    unique_fraction = 0.0 if total_reference_mass <= 0.0 else float(total_unique_mass / total_reference_mass)
    unit_codes = np.asarray(sparse_domain.candidate_correlation_unit_codes, dtype=np.int64)[selected]
    counts = np.bincount(unit_codes, minlength=len(sparse_domain.correlation_unit_ids))
    nonzero = counts[counts > 0]
    max_unit_fraction = 0.0 if nonzero.size == 0 else float(np.max(nonzero)) / float(len(selected))

    selected_run_codes = run_codes[selected]
    selected_condition_codes = condition_codes[selected]
    if np.any(selected_run_codes < 0) or np.any(selected_condition_codes < 0):
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL2 selected frame lacks DATA2A provenance mapping.")
    telemetry = TargetMultiViewSelectorTelemetry(
        uncovered_witness_count=total_uncovered_count,
        uncovered_reference_mass=float(total_uncovered_mass),
        unique_reference_mass_fraction=unique_fraction,
        zero_unique_candidate_fraction=zero_unique,
        correlation_unit_count=int(nonzero.size),
        maximum_correlation_unit_fraction=max_unit_fraction,
        run_count=int(np.unique(selected_run_codes).size),
        condition_count=int(np.unique(selected_condition_codes).size),
    )
    return _MvqualSparseTelemetryResult(
        telemetry=telemetry,
        covered_mass_by_family=tuple(covered_mass_by_family),
        streamed_edge_count=int(streamed_edge_count),
        maximum_chunk_edges=int(maximum_chunk_edges),
        maximum_selected_row_edges=int(maximum_selected_row_edges),
    )

def _hard_obligation_state(sparse_domain: Any, selected_candidate_indices: Sequence[int]) -> tuple[bool, tuple[str, ...]]:
    counts = indexed_obligation_selected_counts(sparse_domain, selected_candidate_indices)
    unsatisfied = tuple(sorted(
        obligation.obligation_id
        for oi, obligation in enumerate(sparse_domain.obligations)
        if obligation.required and int(counts[oi]) < int(obligation.minimum_selected_frames)
    ))
    return (not unsatisfied), unsatisfied

@dataclass(frozen=True, slots=True)
class _MvqualScoreResult:
    """Execution-only independent score result for one domain/selector/size job."""

    label_domain_id: str
    selector: str
    target_size: int
    report: Any = field(repr=False, compare=False)
    selected_indices: np.ndarray = field(repr=False, compare=False)
    telemetry: TargetMultiViewSelectorTelemetry = field(repr=False, compare=False)
    hard_state: tuple[bool, tuple[str, ...]] = field(repr=False, compare=False)
    streamed_edge_count: int = field(default=0, repr=False, compare=False)
    maximum_chunk_edges: int = field(default=0, repr=False, compare=False)
    maximum_selected_row_edges: int = field(default=0, repr=False, compare=False)
    direct_seconds: float = field(default=0.0, repr=False, compare=False)
    sparse_seconds: float = field(default=0.0, repr=False, compare=False)
    crosscheck_seconds: float = field(default=0.0, repr=False, compare=False)
    hard_seconds: float = field(default=0.0, repr=False, compare=False)

def _mvqual_score_job(
    target_coverage_reference: Any,
    reference_domain: Any,
    sparse_domain: Any,
    *,
    label: str,
    selector: str,
    target_size: int,
    selected_uids: Sequence[str],
    uid_to_index: Mapping[str, int],
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    query_workers: int,
    sparse_max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
) -> _MvqualScoreResult:
    """Compute one immutable MVQUAL2 exact-prefix scoring job."""

    direct_started = time.perf_counter()
    report = score_target_subset_coverage(
        target_coverage_reference,
        label,
        selected_uids,
        query_workers=int(query_workers),
    )
    direct_seconds = time.perf_counter() - direct_started
    try:
        selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    except KeyError as exc:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL2 selected frame is outside the reference domain."
        ) from exc

    sparse_started = time.perf_counter()
    sparse_result = _selector_telemetry_indices_bounded(
        reference_domain,
        sparse_domain,
        selected,
        run_codes,
        condition_codes,
        max_edges=sparse_max_edges,
    )
    sparse_seconds = time.perf_counter() - sparse_started

    crosscheck_started = time.perf_counter()
    # MVIDX remains secondary telemetry only.  Every independent coverage mass
    # must agree with the TARGET-DATA2B scorer exactly within the historical tol.
    report_by_family = {item.family_id: item for item in report.family_reports}
    indexed_mass_by_family = dict(sparse_result.covered_mass_by_family)
    for sparse_family in sparse_domain.families:
        indexed_mass = indexed_mass_by_family[sparse_family.family_id]
        direct_mass = report_by_family[sparse_family.family_id].covered_reference_mass
        if not math.isclose(indexed_mass, direct_mass, rel_tol=0.0, abs_tol=5.0e-12):
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL2 independent scorer disagrees with MVIDX telemetry."
            )
    crosscheck_seconds = time.perf_counter() - crosscheck_started

    hard_started = time.perf_counter()
    hard_state = _hard_obligation_state(sparse_domain, selected)
    hard_seconds = time.perf_counter() - hard_started
    return _MvqualScoreResult(
        label_domain_id=str(label),
        selector=str(selector),
        target_size=int(target_size),
        report=report,
        selected_indices=selected,
        telemetry=sparse_result.telemetry,
        hard_state=hard_state,
        streamed_edge_count=sparse_result.streamed_edge_count,
        maximum_chunk_edges=sparse_result.maximum_chunk_edges,
        maximum_selected_row_edges=sparse_result.maximum_selected_row_edges,
        direct_seconds=direct_seconds,
        sparse_seconds=sparse_seconds,
        crosscheck_seconds=crosscheck_seconds,
        hard_seconds=hard_seconds,
    )
