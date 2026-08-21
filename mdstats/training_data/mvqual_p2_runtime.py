"""Execution-only progressive sparse telemetry for MVQUAL PERF1/P2.

P2 preserves the canonical MVQUAL scientific builder but replaces repeated
per-rung MVIDX rescans for exactly nested selector ladders.  One family state
carries witness multiplicity, sole-owner identity and per-candidate unique
witness counts forward.  Each newly added candidate edge is streamed once;
canonical full-witness float64 reductions are still performed at every rung.
Nonnested groups fall back to the historical bounded scorer.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
from functools import wraps
import inspect
import threading
import time
from typing import Any, Mapping, Sequence

import numpy as np

from ._sparse_vector_kernels import csr_row_lengths, iter_csr_edge_batches
from . import target_multi_view_qualification as _mvqual
from .progress_timing import format_progress_time
from .resources import stage_resource_scope


@dataclass(frozen=True, slots=True)
class MvqualP2ExecutionTelemetry:
    group_count: int
    progressive_group_count: int
    fallback_group_count: int
    family_task_count: int
    requested_workers: int
    effective_workers: int
    report_count: int
    streamed_edge_count: int
    maximum_chunk_edges: int
    maximum_selected_row_edges: int
    wall_seconds: float
    group_seconds: tuple[tuple[str, str, float], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_count": int(self.group_count),
            "progressive_group_count": int(self.progressive_group_count),
            "fallback_group_count": int(self.fallback_group_count),
            "family_task_count": int(self.family_task_count),
            "requested_workers": int(self.requested_workers),
            "effective_workers": int(self.effective_workers),
            "report_count": int(self.report_count),
            "streamed_edge_count": int(self.streamed_edge_count),
            "maximum_chunk_edges": int(self.maximum_chunk_edges),
            "maximum_selected_row_edges": int(self.maximum_selected_row_edges),
            "wall_seconds": float(self.wall_seconds),
            "wall_hhmmss": format_progress_time(self.wall_seconds),
            "group_seconds": [
                {
                    "label_domain_id": label,
                    "selector": selector,
                    "wall_seconds": float(seconds),
                    "wall_hhmmss": format_progress_time(seconds),
                }
                for label, selector, seconds in self.group_seconds
            ],
        }


@dataclass(frozen=True, slots=True)
class _SparseGroup:
    label_domain_id: str
    selector: str
    selected_frame_uids: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class _FamilyResult:
    family_id: str
    uncovered_count: tuple[int, ...]
    uncovered_mass: tuple[float, ...]
    unique_mass: tuple[float, ...]
    reference_mass: float
    covered_mass: tuple[float, ...]
    owner_bits: tuple[bytes, ...]
    streamed_edges: tuple[int, ...]
    maximum_chunk_edges: tuple[int, ...]
    maximum_selected_row_edges: tuple[int, ...]


_INSTALL_LOCK = threading.RLock()
_LAST_TELEMETRY: MvqualP2ExecutionTelemetry | None = None


def last_mvqual_p2_execution_telemetry() -> MvqualP2ExecutionTelemetry | None:
    return _LAST_TELEMETRY


def _is_exact_nested_indices(values: Sequence[np.ndarray]) -> bool:
    previous: set[int] = set()
    if not values:
        return False
    for raw in values:
        selected = np.asarray(raw, dtype=np.int64)
        if selected.ndim != 1 or selected.size < 1:
            return False
        items = [int(value) for value in selected]
        current = set(items)
        if len(current) != len(items) or not previous.issubset(current):
            return False
        previous = current
    return True


def _added_rows_by_rung(values: Sequence[np.ndarray]) -> tuple[np.ndarray, ...]:
    if not _is_exact_nested_indices(values):
        raise _mvqual.TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL-P2 requires exactly nested selected sets."
        )
    previous: set[int] = set()
    result: list[np.ndarray] = []
    for raw in values:
        selected = np.asarray(raw, dtype=np.int64)
        added = np.asarray(
            [int(value) for value in selected if int(value) not in previous],
            dtype=np.int64,
        )
        previous.update(int(value) for value in selected)
        result.append(added)
    return tuple(result)


def _progressive_family_rungs(
    sparse_family: Any,
    weights: np.ndarray,
    added_rows: Sequence[np.ndarray],
    *,
    candidate_count: int,
    max_edges: int,
) -> _FamilyResult:
    edge_limit = int(max_edges)
    if edge_limit < 1:
        raise _mvqual.TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL1 sparse edge limit must be positive."
        )
    witness_count = int(sparse_family.witness_count)
    weights = np.asarray(weights, dtype=np.float64)
    if witness_count < 0 or weights.ndim != 1 or weights.size != witness_count:
        raise _mvqual.TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL1 sparse/reference witness cardinality mismatch."
        )
    candidate_count = int(candidate_count)
    multiplicity = np.zeros(witness_count, dtype=np.int32)
    sole_owner = np.full(witness_count, -1, dtype=np.int32)
    unique_count = np.zeros(candidate_count, dtype=np.int32)
    last_added_owner = np.full(witness_count, -1, dtype=np.int32)
    lost_unique = np.zeros(witness_count, dtype=np.bool_)
    started_zero = np.zeros(witness_count, dtype=np.bool_)

    reference_mass = float(np.sum(weights, dtype=np.float64))
    uncovered_count: list[int] = []
    uncovered_mass: list[float] = []
    unique_mass: list[float] = []
    covered_mass: list[float] = []
    owner_bits: list[bytes] = []
    streamed_edges: list[int] = []
    max_chunks: list[int] = []
    max_rows: list[int] = []
    cumulative_max_row = 0

    for raw_added in added_rows:
        added = np.asarray(raw_added, dtype=np.int64)
        if added.ndim != 1 or (
            added.size and (np.any(added < 0) or np.any(added >= candidate_count))
        ):
            raise _mvqual.TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL-P2 added candidates are invalid."
            )
        lengths = csr_row_lengths(sparse_family.candidate_offsets, added)
        if lengths.size:
            cumulative_max_row = max(cumulative_max_row, int(np.max(lengths)))

        np.equal(multiplicity, 0, out=started_zero)
        lost_unique.fill(False)
        rung_streamed = 0
        rung_max_chunk = 0
        for witnesses, owner_positions in iter_csr_edge_batches(
            sparse_family.candidate_offsets,
            sparse_family.candidate_witnesses,
            added,
            max_edges=edge_limit,
        ):
            witnesses = np.asarray(witnesses)
            owner_positions = np.asarray(owner_positions, dtype=np.int64)
            chunk_edges = int(witnesses.size)
            if not chunk_edges:
                continue
            rung_streamed += chunk_edges
            rung_max_chunk = max(rung_max_chunk, chunk_edges)
            if chunk_edges > edge_limit:
                raise _mvqual.TrainingDataInputError(
                    "TARGET-DATA2C-MVQUAL-P2 strict sparse chunk bound was violated."
                )
            if int(np.max(witnesses)) >= witness_count:
                raise _mvqual.TrainingDataInputError(
                    "TARGET-DATA2C-MVQUAL1 MVIDX witness is outside the reference family."
                )

            current = multiplicity[witnesses]
            old_unique_edges = current == 1
            if np.any(old_unique_edges):
                old_unique_witnesses = witnesses[old_unique_edges]
                old_owners = sole_owner[old_unique_witnesses]
                valid = old_owners >= 0
                if np.any(valid):
                    lost_unique[old_unique_witnesses[valid]] = True

            # Repeated witness assignments are irrelevant for final gains:
            # a gained witness has exactly one new edge in this whole rung.
            last_added_owner[witnesses] = added[owner_positions]
            np.add.at(multiplicity, witnesses, 1)

        lost = np.flatnonzero(lost_unique)
        if lost.size:
            owners = sole_owner[lost].astype(np.int64, copy=False)
            if np.any(owners < 0):
                raise _mvqual.TrainingDataInputError(
                    "TARGET-DATA2C-MVQUAL-P2 sole-owner state is inconsistent."
                )
            np.add.at(unique_count, owners, -1)
            sole_owner[lost] = -1

        gained = np.flatnonzero(started_zero & (multiplicity == 1))
        if gained.size:
            owners = last_added_owner[gained].astype(np.int64, copy=False)
            if np.any(owners < 0):
                raise _mvqual.TrainingDataInputError(
                    "TARGET-DATA2C-MVQUAL-P2 new unique witness has no owner."
                )
            np.add.at(unique_count, owners, 1)
            sole_owner[gained] = owners.astype(np.int32)

        if np.any(unique_count < 0):
            raise _mvqual.TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL-P2 unique-owner count became negative."
            )
        covered = multiplicity > 0
        unique = multiplicity == 1
        if int(np.sum(unique_count, dtype=np.int64)) != int(np.count_nonzero(unique)):
            raise _mvqual.TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL-P2 unique-owner accounting mismatch."
            )

        uncovered_count.append(int(np.count_nonzero(~covered)))
        uncovered_mass.append(float(np.sum(weights[~covered], dtype=np.float64)))
        unique_mass.append(float(np.sum(weights[unique], dtype=np.float64)))
        covered_mass.append(float(np.sum(weights[covered], dtype=np.float64)))
        owner_bits.append(np.packbits(unique_count > 0, bitorder="little").tobytes())
        streamed_edges.append(rung_streamed)
        max_chunks.append(rung_max_chunk)
        max_rows.append(cumulative_max_row)

    return _FamilyResult(
        family_id=str(sparse_family.family_id),
        uncovered_count=tuple(uncovered_count),
        uncovered_mass=tuple(uncovered_mass),
        unique_mass=tuple(unique_mass),
        reference_mass=reference_mass,
        covered_mass=tuple(covered_mass),
        owner_bits=tuple(owner_bits),
        streamed_edges=tuple(streamed_edges),
        maximum_chunk_edges=tuple(max_chunks),
        maximum_selected_row_edges=tuple(max_rows),
    )


def _progressive_sparse_results_for_group(
    reference_domain: Any,
    sparse_domain: Any,
    selected_by_rung: Sequence[np.ndarray],
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    *,
    max_edges: int,
    workers: int,
    resource_scope: Any = None,
) -> tuple[_mvqual._MvqualSparseTelemetryResult, ...]:
    selected_values = tuple(np.asarray(value, dtype=np.int64) for value in selected_by_rung)
    added = _added_rows_by_rung(selected_values)
    family_count = len(sparse_domain.families)
    if family_count < 1:
        raise _mvqual.TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL-P2 sparse domain has no families."
        )
    effective = min(max(1, int(workers)), family_count)
    if resource_scope is not None:
        effective = min(effective, max(1, int(resource_scope.python_workers)))

    def evaluate(item: tuple[int, Any]) -> tuple[int, _FamilyResult]:
        index, sparse_family = item
        family = reference_domain.family(sparse_family.family_id)
        return index, _progressive_family_rungs(
            sparse_family,
            np.asarray(family.weights, dtype=np.float64),
            added,
            candidate_count=len(reference_domain.frame_uids),
            max_edges=max_edges,
        )

    indexed = tuple(enumerate(sparse_domain.families))
    by_index: dict[int, _FamilyResult] = {}
    scope_context = nullcontext() if resource_scope is None else stage_resource_scope(resource_scope)
    with scope_context:
        if effective == 1:
            for item in indexed:
                index, value = evaluate(item)
                by_index[index] = value
        else:
            with ThreadPoolExecutor(
                max_workers=effective,
                thread_name_prefix="mdstats-mvqual-p2-family",
            ) as executor:
                futures = [executor.submit(evaluate, item) for item in indexed]
                for future in futures:  # canonical family submission order
                    index, value = future.result()
                    by_index[index] = value

    family_results = tuple(by_index[index] for index in range(family_count))
    candidate_count = len(reference_domain.frame_uids)
    packed_size = (candidate_count + 7) // 8
    owner_union = np.zeros((len(selected_values), packed_size), dtype=np.uint8)
    output: list[_mvqual._MvqualSparseTelemetryResult] = []

    for rung_index, selected in enumerate(selected_values):
        total_uncovered_count = 0
        total_uncovered_mass = np.float64(0.0)
        total_unique_mass = np.float64(0.0)
        total_reference_mass = np.float64(0.0)
        covered_by_family: list[tuple[str, float]] = []
        streamed = 0
        max_chunk = 0
        max_row = 0
        for result in family_results:  # canonical float64 family order
            total_uncovered_count += int(result.uncovered_count[rung_index])
            total_uncovered_mass += np.float64(result.uncovered_mass[rung_index])
            total_unique_mass += np.float64(result.unique_mass[rung_index])
            total_reference_mass += np.float64(result.reference_mass)
            covered_by_family.append((result.family_id, float(result.covered_mass[rung_index])))
            owner_union[rung_index] |= np.frombuffer(
                result.owner_bits[rung_index], dtype=np.uint8, count=packed_size
            )
            streamed += int(result.streamed_edges[rung_index])
            max_chunk = max(max_chunk, int(result.maximum_chunk_edges[rung_index]))
            max_row = max(max_row, int(result.maximum_selected_row_edges[rung_index]))

        unique_owner = np.unpackbits(
            owner_union[rung_index], bitorder="little", count=candidate_count
        ).astype(np.bool_, copy=False)
        zero_unique = 1.0 - float(np.count_nonzero(unique_owner[selected])) / float(len(selected))
        unique_fraction = (
            0.0 if total_reference_mass <= 0.0
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
        telemetry = _mvqual.TargetMultiViewSelectorTelemetry(
            uncovered_witness_count=int(total_uncovered_count),
            uncovered_reference_mass=float(total_uncovered_mass),
            unique_reference_mass_fraction=unique_fraction,
            zero_unique_candidate_fraction=zero_unique,
            correlation_unit_count=int(nonzero.size),
            maximum_correlation_unit_fraction=max_unit_fraction,
            run_count=int(np.unique(np.asarray(run_codes, dtype=np.int64)[selected]).size),
            condition_count=int(
                np.unique(np.asarray(condition_codes, dtype=np.int64)[selected]).size
            ),
        )
        output.append(
            _mvqual._MvqualSparseTelemetryResult(
                telemetry=telemetry,
                covered_mass_by_family=tuple(covered_by_family),
                streamed_edge_count=int(streamed),
                maximum_chunk_edges=int(max_chunk),
                maximum_selected_row_edges=int(max_row),
            )
        )
    return tuple(output)


def _qualification_groups(
    reference: Any, legacy_ladder: Any, repair_plan: Any
) -> tuple[_SparseGroup, ...]:
    groups: list[_SparseGroup] = []
    for reference_domain in reference.domains:
        label = str(reference_domain.label_domain_id)
        legacy = {
            int(rung.target_size): rung
            for rung in legacy_ladder.domain(label).rungs
            if bool(rung.materializable)
        }
        mv = {
            int(rung.target_size): rung
            for rung in repair_plan.domain(label).rungs
            if bool(rung.materializable)
        }
        common = tuple(sorted(set(legacy) & set(mv)))
        if not common:
            continue
        groups.append(
            _SparseGroup(
                label,
                "legacy",
                tuple(tuple(str(uid) for uid in legacy[size].frame_uids) for size in common),
            )
        )
        groups.append(
            _SparseGroup(
                label,
                "mv",
                tuple(tuple(str(uid) for uid in mv[size].frame_uids) for size in sorted(mv)),
            )
        )
    return tuple(groups)


def _progressive_sparse_cache(
    reference: Any,
    sparse_index: Any,
    role_freeze: Any,
    legacy_ladder: Any,
    repair_plan: Any,
    *,
    sparse_max_edges: int,
    scoring_workers: int,
    resource_scope: Any = None,
) -> tuple[
    dict[tuple[int, int, tuple[int, ...]], _mvqual._MvqualSparseTelemetryResult],
    MvqualP2ExecutionTelemetry,
]:
    groups = _qualification_groups(reference, legacy_ladder, repair_plan)
    requested = max(1, int(scoring_workers))
    effective = requested
    if resource_scope is not None:
        effective = min(effective, max(1, int(resource_scope.python_workers)))
    cache: dict[
        tuple[int, int, tuple[int, ...]], _mvqual._MvqualSparseTelemetryResult
    ] = {}
    group_seconds: list[tuple[str, str, float]] = []
    progressive = 0
    fallback = 0
    family_tasks = 0
    streamed = 0
    max_chunk = 0
    max_row = 0
    started = time.perf_counter()

    for group in groups:
        reference_domain = reference.domain(group.label_domain_id)
        sparse_domain = sparse_index.domain(group.label_domain_id)
        role_domain = role_freeze.domain(group.label_domain_id)
        uid_to_index, run_codes, condition_codes = _mvqual._qualification_provenance_codes(
            reference_domain, role_domain
        )
        try:
            selected_by_rung = tuple(
                np.asarray([uid_to_index[uid] for uid in uids], dtype=np.int64)
                for uids in group.selected_frame_uids
            )
        except KeyError:
            fallback += 1
            continue
        if not _is_exact_nested_indices(selected_by_rung):
            fallback += 1
            continue

        group_started = time.perf_counter()
        results = _progressive_sparse_results_for_group(
            reference_domain,
            sparse_domain,
            selected_by_rung,
            run_codes,
            condition_codes,
            max_edges=sparse_max_edges,
            workers=effective,
            resource_scope=resource_scope,
        )
        group_seconds.append(
            (group.label_domain_id, group.selector, time.perf_counter() - group_started)
        )
        progressive += 1
        family_tasks += len(sparse_domain.families)
        for selected, result in zip(selected_by_rung, results, strict=True):
            cache[(id(reference_domain), id(sparse_domain), tuple(int(v) for v in selected))] = result
            streamed += int(result.streamed_edge_count)
            max_chunk = max(max_chunk, int(result.maximum_chunk_edges))
            max_row = max(max_row, int(result.maximum_selected_row_edges))

    telemetry = MvqualP2ExecutionTelemetry(
        group_count=len(groups),
        progressive_group_count=progressive,
        fallback_group_count=fallback,
        family_task_count=family_tasks,
        requested_workers=requested,
        effective_workers=max(1, effective),
        report_count=len(cache),
        streamed_edge_count=streamed,
        maximum_chunk_edges=max_chunk,
        maximum_selected_row_edges=max_row,
        wall_seconds=time.perf_counter() - started,
        group_seconds=tuple(group_seconds),
    )
    return cache, telemetry


def _supports_p2_authority(reference: Any) -> bool:
    return (
        hasattr(reference, "domain")
        and hasattr(reference, "domains")
        and all(
            hasattr(domain, "frame_uids") and hasattr(domain, "family")
            for domain in reference.domains
        )
    )


def install_mvqual_p2_runtime(mdstats_module: Any) -> None:
    """Wrap only the public campaign-facing builder; direct scientific imports stay unchanged."""
    current = mdstats_module.build_target_multi_view_qualification_plan
    if bool(getattr(current, "_mdstats_mvqual_p2_installed", False)):
        return
    original_builder = current
    signature = inspect.signature(original_builder)
    original_sparse = _mvqual._selector_telemetry_indices_bounded

    @wraps(original_builder)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        global _LAST_TELEMETRY
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        values: Mapping[str, Any] = bound.arguments
        reference = values["target_coverage_reference"]
        if not _supports_p2_authority(reference):
            _LAST_TELEMETRY = None
            return original_builder(*args, **kwargs)

        with _INSTALL_LOCK:
            cache, telemetry = _progressive_sparse_cache(
                reference,
                values["target_coverage_sparse_index"],
                values["target_data_role_freeze"],
                values["legacy_target_data_ladder"],
                values["target_multi_view_repair"],
                sparse_max_edges=int(values["sparse_max_edges"]),
                scoring_workers=int(values["scoring_workers"]),
                resource_scope=values.get("resource_scope"),
            )
            _LAST_TELEMETRY = telemetry
            progress = values.get("progress_callback")
            if progress is not None:
                progress(
                    "status=p2-sparse; "
                    f"groups={telemetry.progressive_group_count}/{telemetry.group_count}; "
                    f"fallback={telemetry.fallback_group_count}; "
                    f"workers={telemetry.effective_workers}; "
                    f"family_tasks={telemetry.family_task_count}; "
                    f"reports={telemetry.report_count}; "
                    f"streamed_edges={telemetry.streamed_edge_count}; "
                    f"elapsed={format_progress_time(telemetry.wall_seconds)}"
                )

            def cached_sparse(
                reference_domain: Any,
                sparse_domain: Any,
                selected: np.ndarray,
                run_codes: np.ndarray,
                condition_codes: np.ndarray,
                *,
                max_edges: int,
            ) -> _mvqual._MvqualSparseTelemetryResult:
                selected_array = np.asarray(selected, dtype=np.int64)
                key = (
                    id(reference_domain),
                    id(sparse_domain),
                    tuple(int(value) for value in selected_array),
                )
                result = cache.get(key)
                if result is not None:
                    return result
                return original_sparse(
                    reference_domain,
                    sparse_domain,
                    selected_array,
                    run_codes,
                    condition_codes,
                    max_edges=max_edges,
                )

            _mvqual._selector_telemetry_indices_bounded = cached_sparse
            try:
                return original_builder(*args, **kwargs)
            finally:
                _mvqual._selector_telemetry_indices_bounded = original_sparse

    wrapped._mdstats_mvqual_p2_installed = True  # type: ignore[attr-defined]
    wrapped._mdstats_mvqual_p2_original = original_builder  # type: ignore[attr-defined]
    mdstats_module.build_target_multi_view_qualification_plan = wrapped
