"""Shared FEAS1/NEIGHBOR1 construction and FEAS1 diagnostics.

Restored from TARGET-DATA2B-FEAS1 (carrier ``3937881e`` blob ``238a96f7``).
One exact geometry pass per reference generation streams every family's
NEIGHBOR1 CSR while reducing the FEAS1 support/fragility/singleton-gain
diagnostics; nothing re-queries that geometry for MVIDX.  The pass depends
only on the reference: obligation capacity is a separate cheap reduction over
the canonical obligation authority, so an obligation-policy change reuses the
published geometry product.

FEAS1 is fail-closed diagnostic evidence.  It never mutates target sizes,
thresholds or minima.  The historical 16384 ceiling is retired; the configured
horizon is the current ``N_max``.  Scientific FP64 reductions commit each
family's blocks in canonical witness order through an ordered reducer, so
queue width, block size and completion order are execution-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ..progress_timing import format_progress_fraction, format_progress_time
from ..resources import StageResourceScope, available_cpu_threads
from ..work_queue import DeterministicOrderedReducer, DeterministicWorkQueue
from .artifact_store import PublishedArtifact, publish_artifact_directory, read_manifest
from .neighborhood import (
    NEIGHBOR1_ARTIFACT_SCHEMA,
    NeighborhoodBlockResult,
    NeighborhoodCSRStream,
    PreparedNeighborhoodFamily,
    StagedNeighborhoodFamily,
    TargetCoverageExactNeighborhoodStore,
    pack_staged_neighborhood_families,
    prepare_neighborhood_family,
    query_neighborhood_block,
    read_exact_neighborhood_store,
    write_exact_neighborhood_store,
)
from .obligations import KIND_CORRELATION_UNIT, KIND_EXTENT_LOWER, KIND_EXTENT_UPPER

FEAS1_POLICY_SCHEMA = "mdstats.target-coverage-feas1-policy.v2"
FEAS1_SUPPORT_SCHEMA = "mdstats.target-coverage-feas1-support.v1"
FEAS1_FAMILY_SCHEMA = "mdstats.target-coverage-feas1-family.v2"
FEAS1_REPORT_SCHEMA = "mdstats.target-coverage-feas1-report.v2"
FEAS1_GEOMETRY_ARTIFACT_SCHEMA = "mdstats.target-order-feas1-neighbor1-geometry.v1"
FEAS1_VERSION = "mdstats.target-order.feas1.current-ladder.v1"

STATE_SELF_CONSISTENT = "self_consistent"
STATE_CROSS_SUPPORT_FRAGILE = "cross_support_fragile"
STATE_OPTIMIZATION_REQUIRED = "optimization_required"
STATE_CAPACITY_INFEASIBLE = "provably_capacity_infeasible"
_TERMINAL_STATES = frozenset({STATE_CROSS_SUPPORT_FRAGILE, STATE_OPTIMIZATION_REQUIRED, STATE_CAPACITY_INFEASIBLE})


@dataclass(frozen=True, slots=True)
class TargetCoverageFeasibilityPolicy:
    """FEAS1 diagnostic policy; the retired fixed ceiling is absent."""

    support_degree_bins: tuple[int, ...] = (2, 4, 8, 16, 32)
    exclude_own_correlation_unit: bool = True
    fragile_zero_mass_tolerance: float = 1.0e-12
    authority_version: str = FEAS1_VERSION

    def __post_init__(self) -> None:
        bins = tuple(int(v) for v in self.support_degree_bins)
        if not bins or bins != tuple(sorted(set(bins))) or bins[0] < 2:
            raise TrainingDataInputError("FEAS1 support_degree_bins must be sorted unique integers >= 2.")
        tolerance = float(self.fragile_zero_mass_tolerance)
        if not math.isfinite(tolerance) or not 0.0 <= tolerance <= 1.0e-6:
            raise TrainingDataInputError("FEAS1 fragile_zero_mass_tolerance is invalid.")
        if self.authority_version != FEAS1_VERSION:
            raise TrainingDataInputError("Unsupported FEAS1 authority version.")
        object.__setattr__(self, "support_degree_bins", bins)
        object.__setattr__(self, "fragile_zero_mass_tolerance", tolerance)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEAS1_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "support_degree_bins": list(self.support_degree_bins),
            "exclude_own_correlation_unit": bool(self.exclude_own_correlation_unit),
            "fragile_zero_mass_tolerance": self.fragile_zero_mass_tolerance,
        }
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFeasibilityPolicy":
        if payload.get("schema") != FEAS1_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported FEAS1 policy schema.")
        result = cls(
            support_degree_bins=tuple(int(v) for v in payload["support_degree_bins"]),
            exclude_own_correlation_unit=bool(payload["exclude_own_correlation_unit"]),
            fragile_zero_mass_tolerance=float(payload["fragile_zero_mass_tolerance"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("FEAS1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageSupportDegreeReport:
    witness_count: int
    zero_support_mass: float
    exact_one_support_mass: float
    cumulative_mass_by_max_degree: tuple[tuple[int, float], ...]
    minimum_degree: int
    maximum_degree: int

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEAS1_SUPPORT_SCHEMA,
            "witness_count": int(self.witness_count),
            "zero_support_mass": float(self.zero_support_mass),
            "exact_one_support_mass": float(self.exact_one_support_mass),
            "cumulative_mass_by_max_degree": [
                {"maximum_degree": int(k), "weighted_mass": float(v)} for k, v in self.cumulative_mass_by_max_degree
            ],
            "minimum_degree": int(self.minimum_degree),
            "maximum_degree": int(self.maximum_degree),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSupportDegreeReport":
        if payload.get("schema") != FEAS1_SUPPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported FEAS1 support schema.")
        result = cls(
            witness_count=int(payload["witness_count"]),
            zero_support_mass=float(payload["zero_support_mass"]),
            exact_one_support_mass=float(payload["exact_one_support_mass"]),
            cumulative_mass_by_max_degree=tuple(
                (int(item["maximum_degree"]), float(item["weighted_mass"]))
                for item in payload["cumulative_mass_by_max_degree"]
            ),
            minimum_degree=int(payload["minimum_degree"]),
            maximum_degree=int(payload["maximum_degree"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("FEAS1 support digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageFamilyFeasibilityReport:
    family_id: str
    family_digest: str
    witness_count: int
    candidate_frame_count: int
    neighborhood_edge_count: int
    self_excluded_support: TargetCoverageSupportDegreeReport
    correlation_excluded_support: TargetCoverageSupportDegreeReport
    optimistic_max_singleton_gain: float
    coverage_cardinality_lower_bound: int
    cross_support_fragile: bool

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEAS1_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "family_digest": validate_digest(self.family_digest, name="family_digest"),
            "witness_count": int(self.witness_count),
            "candidate_frame_count": int(self.candidate_frame_count),
            "neighborhood_edge_count": int(self.neighborhood_edge_count),
            "self_excluded_support": self.self_excluded_support.to_dict(),
            "correlation_excluded_support": self.correlation_excluded_support.to_dict(),
            "optimistic_max_singleton_gain": float(self.optimistic_max_singleton_gain),
            "coverage_cardinality_lower_bound": int(self.coverage_cardinality_lower_bound),
            "cross_support_fragile": bool(self.cross_support_fragile),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFamilyFeasibilityReport":
        if payload.get("schema") != FEAS1_FAMILY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported FEAS1 family schema.")
        result = cls(
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            witness_count=int(payload["witness_count"]),
            candidate_frame_count=int(payload["candidate_frame_count"]),
            neighborhood_edge_count=int(payload["neighborhood_edge_count"]),
            self_excluded_support=TargetCoverageSupportDegreeReport.from_dict(payload["self_excluded_support"]),
            correlation_excluded_support=TargetCoverageSupportDegreeReport.from_dict(
                payload["correlation_excluded_support"]
            ),
            optimistic_max_singleton_gain=float(payload["optimistic_max_singleton_gain"]),
            coverage_cardinality_lower_bound=int(payload["coverage_cardinality_lower_bound"]),
            cross_support_fragile=bool(payload["cross_support_fragile"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("FEAS1 family digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageGeometry:
    """The shared FEAS1/NEIGHBOR1 construction product."""

    neighborhoods: TargetCoverageExactNeighborhoodStore
    family_reports: tuple[TargetCoverageFamilyFeasibilityReport, ...]
    policy: TargetCoverageFeasibilityPolicy

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": FEAS1_GEOMETRY_ARTIFACT_SCHEMA,
                "neighborhood_digest": self.neighborhoods.content_digest,
                "policy": self.policy.to_dict(),
                "family_reports": [item.to_dict()["content_digest"] for item in self.family_reports],
            }
        )


@dataclass(frozen=True, slots=True)
class TargetCoverageFeasibilityReport:
    dataset_id: str
    target_coverage_reference_digest: str
    geometry_digest: str
    obligation_authority_digest: str
    policy: TargetCoverageFeasibilityPolicy
    coverage_threshold: float
    candidate_count: int
    configured_ceiling: int
    family_reports: tuple[TargetCoverageFamilyFeasibilityReport, ...]
    obligation_slot_count: int
    obligation_max_per_candidate: int
    obligation_lower_bound: int
    coverage_cardinality_lower_bound: int
    k_min_lower_bound: int
    fragile_family_ids: tuple[str, ...]
    states: tuple[str, ...]

    def __post_init__(self) -> None:
        states = tuple(str(v) for v in self.states)
        if len(states) != 2 or states[0] != STATE_SELF_CONSISTENT or states[1] not in _TERMINAL_STATES:
            raise TrainingDataInputError("FEAS1 requires self_consistent plus exactly one terminal state.")
        object.__setattr__(self, "states", states)

    @property
    def terminal_state(self) -> str:
        return self.states[-1]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEAS1_REPORT_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "geometry_digest": self.geometry_digest,
            "obligation_authority_digest": self.obligation_authority_digest,
            "policy": self.policy.to_dict(),
            "coverage_threshold": float(self.coverage_threshold),
            "candidate_count": int(self.candidate_count),
            "configured_ceiling": int(self.configured_ceiling),
            "family_reports": [item.to_dict() for item in self.family_reports],
            "obligation_slot_count": int(self.obligation_slot_count),
            "obligation_max_per_candidate": int(self.obligation_max_per_candidate),
            "obligation_lower_bound": int(self.obligation_lower_bound),
            "coverage_cardinality_lower_bound": int(self.coverage_cardinality_lower_bound),
            "k_min_lower_bound": int(self.k_min_lower_bound),
            "fragile_family_ids": list(self.fragile_family_ids),
            "states": list(self.states),
        }
        return {**payload, "content_digest": digest(payload)}

    @property
    def content_digest(self) -> str:
        return str(self.to_dict()["content_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFeasibilityReport":
        if payload.get("schema") != FEAS1_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported FEAS1 report schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            geometry_digest=str(payload["geometry_digest"]),
            obligation_authority_digest=str(payload["obligation_authority_digest"]),
            policy=TargetCoverageFeasibilityPolicy.from_dict(payload["policy"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            candidate_count=int(payload["candidate_count"]),
            configured_ceiling=int(payload["configured_ceiling"]),
            family_reports=tuple(TargetCoverageFamilyFeasibilityReport.from_dict(v) for v in payload["family_reports"]),
            obligation_slot_count=int(payload["obligation_slot_count"]),
            obligation_max_per_candidate=int(payload["obligation_max_per_candidate"]),
            obligation_lower_bound=int(payload["obligation_lower_bound"]),
            coverage_cardinality_lower_bound=int(payload["coverage_cardinality_lower_bound"]),
            k_min_lower_bound=int(payload["k_min_lower_bound"]),
            fragile_family_ids=tuple(str(v) for v in payload["fragile_family_ids"]),
            states=tuple(str(v) for v in payload["states"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("FEAS1 report digest mismatch.")
        return result


class _SupportAccumulator:
    __slots__ = ("bins", "zero", "one", "cumulative", "minimum", "maximum", "count")

    def __init__(self, bins: tuple[int, ...]) -> None:
        self.bins = bins
        self.zero = np.float64(0.0)
        self.one = np.float64(0.0)
        self.cumulative = np.zeros(len(bins), dtype=np.float64)
        self.minimum: int | None = None
        self.maximum = 0
        self.count = 0

    def add_many(self, degrees: np.ndarray, weights: np.ndarray) -> None:
        """Accumulate one complete family in canonical witness order."""

        values = np.asarray(degrees, dtype=np.int64)
        masses = np.asarray(weights, dtype=np.float64)
        if values.size == 0:
            return
        self.count += int(values.size)
        self.minimum = int(np.min(values)) if self.minimum is None else min(self.minimum, int(np.min(values)))
        self.maximum = max(self.maximum, int(np.max(values)))

        def ordered_sum(mask: np.ndarray) -> np.float64:
            selected = masses[mask]
            return np.float64(0.0) if selected.size == 0 else np.add.accumulate(selected, dtype=np.float64)[-1]

        self.zero += ordered_sum(values == 0)
        self.one += ordered_sum(values == 1)
        for index, upper in enumerate(self.bins):
            self.cumulative[index] += ordered_sum(values <= upper)

    def freeze(self) -> TargetCoverageSupportDegreeReport:
        return TargetCoverageSupportDegreeReport(
            witness_count=self.count,
            zero_support_mass=float(self.zero),
            exact_one_support_mass=float(self.one),
            cumulative_mass_by_max_degree=tuple(
                (upper, float(value)) for upper, value in zip(self.bins, self.cumulative, strict=True)
            ),
            minimum_degree=0 if self.minimum is None else self.minimum,
            maximum_degree=self.maximum,
        )


def _coverage_cardinality_lower_bound(candidate_gain: np.ndarray, threshold: float) -> int | None:
    gains = np.sort(np.asarray(candidate_gain, dtype=np.float64))[::-1]
    positive = gains[gains > 0.0]
    if positive.size == 0:
        return None
    cumulative = np.cumsum(positive, dtype=np.float64)
    index = int(np.searchsorted(cumulative, float(threshold) - 1.0e-12, side="left"))
    return None if index >= len(cumulative) else index + 1


@dataclass
class _FamilyState:
    position: int
    family: Any
    prepared: PreparedNeighborhoodFamily
    stream: NeighborhoodCSRStream
    weights: np.ndarray
    candidate_gain: np.ndarray
    self_degree: np.ndarray
    correlation_degree: np.ndarray
    edge_count: int = 0
    next_block: int = 0
    inflight: int = 0
    reducer: DeterministicOrderedReducer | None = field(default=None, repr=False)


def _query_block(state: _FamilyState, task: tuple[int, int], unit_codes: np.ndarray, exclude_own: bool, tree_workers: int):
    block = query_neighborhood_block(
        state.prepared, task, tree_workers=tree_workers, context=f"FEAS1 family {state.family.family_id!r}"
    )
    self_degrees = block.unique_counts - 1
    if exclude_own:
        own_units = unit_codes[state.prepared.frame_indices[block.start:block.stop]]
        cross = unit_codes[block.candidate_indices] != own_units[block.local_rows]
        correlation = np.bincount(block.local_rows[cross], minlength=block.stop - block.start).astype(np.int64)
    else:
        correlation = self_degrees.copy()
    return block, self_degrees, correlation


def _reduce_block(state: _FamilyState, result: tuple[NeighborhoodBlockResult, np.ndarray, np.ndarray]) -> None:
    block, self_degrees, correlation = result
    state.stream.append(block)
    state.edge_count += int(block.candidate_indices.size)
    # Canonical witness-block order within one family preserves the exact
    # historical FP64 np.add.at arithmetic sequence.
    np.add.at(state.candidate_gain, block.candidate_indices, state.weights[block.start + block.local_rows])
    state.self_degree[block.start:block.stop] = self_degrees
    state.correlation_degree[block.start:block.stop] = correlation


def _finalize_family(
    state: _FamilyState, policy: TargetCoverageFeasibilityPolicy, threshold: float
) -> tuple[TargetCoverageFamilyFeasibilityReport, StagedNeighborhoodFamily]:
    self_support = _SupportAccumulator(policy.support_degree_bins)
    correlation_support = _SupportAccumulator(policy.support_degree_bins)
    self_support.add_many(state.self_degree, state.weights)
    correlation_support.add_many(state.correlation_degree, state.weights)
    lower_bound = _coverage_cardinality_lower_bound(state.candidate_gain, threshold)
    if lower_bound is None:
        raise TrainingDataInputError(
            f"FEAS1 family {state.family.family_id!r} cannot reach its coverage threshold even under "
            "optimistic singleton summation; exact P_train is infeasible for the accepted method."
        )
    correlation_report = correlation_support.freeze()
    staged = state.stream.finalize_staged()
    if staged.edge_count != state.edge_count:
        raise TrainingDataInputError(f"FEAS1/NEIGHBOR1 edge-count mismatch for {state.family.family_id!r}.")
    return (
        TargetCoverageFamilyFeasibilityReport(
            family_id=state.family.family_id,
            family_digest=state.family.content_digest,
            witness_count=len(state.weights),
            candidate_frame_count=int(np.count_nonzero(state.candidate_gain > 0.0)),
            neighborhood_edge_count=state.edge_count,
            self_excluded_support=self_support.freeze(),
            correlation_excluded_support=correlation_report,
            optimistic_max_singleton_gain=float(np.max(state.candidate_gain)),
            coverage_cardinality_lower_bound=int(lower_bound),
            cross_support_fragile=bool(correlation_report.zero_support_mass > policy.fragile_zero_mass_tolerance),
        ),
        staged,
    )


def _default_scope(workers: int, tree_workers: int) -> StageResourceScope:
    nested = max(1, int(workers) * max(1, int(tree_workers)))
    return StageResourceScope(
        stage_name="TARGET-ORDER-FEAS1-NEIGHBOR1",
        cpu_threads_available=max(int(available_cpu_threads()), nested),
        cpu_threads_budget=nested,
        python_workers=max(1, int(workers)),
        tree_workers=max(1, int(tree_workers)),
        blas_threads=1,
        ram_budget_bytes=None,
    )




def build_target_coverage_geometry(
    reference: Any,
    *,
    build_directory: Path,
    policy: TargetCoverageFeasibilityPolicy | None = None,
    global_workers: int = 1,
    query_workers: int = 1,
    query_block_size: int = 512,
    resource_scope: StageResourceScope | None = None,
    progress_interval_seconds: float = 30.0,
    progress_callback: Callable[[str], None] | None = None,
) -> TargetCoverageGeometry:
    """Run the one exact geometry pass shared by FEAS1 and MVIDX.

    ``build_directory`` is attempt-owned scratch.  The returned NEIGHBOR1
    families are views into packed roots inside it; publishing through
    :func:`write_target_coverage_geometry` hard-links or copies those roots,
    after which the caller removes the directory.
    """

    feas_policy = TargetCoverageFeasibilityPolicy() if policy is None else policy
    workers = max(1, int(global_workers))
    tree_workers = max(1, int(query_workers)) if workers == 1 else 1
    # An inherited scope supplies the campaign CPU/RAM budget; FEAS1 always owns
    # and applies the native-thread limits its own lanes run under, whether the
    # scope arrived from the caller or was synthesized here.
    scope = _default_scope(workers, tree_workers) if resource_scope is None else resource_scope
    if int(scope.python_workers) != workers or int(scope.tree_workers) != tree_workers:
        raise TrainingDataInputError("FEAS1 StageResourceScope does not match the single-level queue width.")
    build_directory = Path(build_directory)
    build_directory.mkdir(parents=True, exist_ok=True)
    threshold = float(reference.policy.coverage_threshold)
    code_by_unit = {unit: code for code, unit in enumerate(sorted(set(reference.correlation_unit_ids)))}
    unit_codes = np.asarray([code_by_unit[unit] for unit in reference.correlation_unit_ids], dtype=np.int64)
    families = tuple(reference.families)
    block = max(1, int(query_block_size))
    total_witnesses = sum(len(item.values) for item in families)
    total_blocks = sum(math.ceil(len(item.values) / block) for item in families)
    results: list[tuple[TargetCoverageFamilyFeasibilityReport, StagedNeighborhoodFamily] | None] = [None] * len(families)
    interval = max(0.05, float(progress_interval_seconds))
    started = time.monotonic()
    progress = {"witnesses": 0, "blocks": 0, "last": started}
    if progress_callback is not None:
        progress_callback(
            f"status=start; families={len(families)}; blocks={total_blocks}; witnesses={total_witnesses}; "
            f"global-workers={workers}; tree-workers/task={tree_workers}; query-block={block}"
        )

    def prepare(position: int) -> _FamilyState:
        family = families[position]
        prepared = prepare_neighborhood_family(family, candidate_count=reference.candidate_count, query_block_size=block)
        witness_count = len(prepared.scaled)
        return _FamilyState(
            position=position,
            family=family,
            prepared=prepared,
            stream=NeighborhoodCSRStream(prepared, directory=build_directory),
            weights=np.asarray(family.weights, dtype=np.float64),
            candidate_gain=np.zeros(reference.candidate_count, dtype=np.float64),
            self_degree=np.empty(witness_count, dtype=np.int64),
            correlation_degree=np.empty(witness_count, dtype=np.int64),
        )

    def state_memory(position: int) -> int:
        values = np.asarray(families[position].values)
        return max(1, int(3 * values.size * 8 + len(values) * 32 + reference.candidate_count * 8))

    exclude_own = bool(feas_policy.exclude_own_correlation_unit)
    max_pending = max(workers, 2 * workers)
    states: dict[int, _FamilyState] = {}
    owners: dict[str, tuple[str, int]] = {}
    pending_finalization: set[int] = set()
    cursor = {"next_prepare": 0, "preparing": 0}
    with DeterministicWorkQueue(
        scope,
        max_ready_tasks=max_pending,
        max_inflight_tasks=max_pending,
        max_completed_tasks=max_pending,
        heartbeat_interval_seconds=interval,
        thread_name_prefix="mdstats-feas1",
    ) as queue:

        def buffered() -> int:
            return queue.outstanding_tasks + sum(
                0 if state.reducer is None else state.reducer.buffered_count for state in states.values()
            )

        def can_enqueue() -> bool:
            return queue.can_submit() and buffered() < max_pending + 2 * workers

        def refill() -> None:
            if pending_finalization:
                return
            target = workers if not states else max(1, workers // 8)
            while cursor["next_prepare"] < len(families) and cursor["preparing"] < target and can_enqueue():
                position = cursor["next_prepare"]
                task_id = f"prepare:{position:08d}"
                queue.submit(
                    task_id=task_id,
                    canonical_order=(position, 0, 0),
                    function=prepare,
                    args=(position,),
                    task_kind="feas1-family-prepare",
                    estimated_memory_bytes=state_memory(position),
                )
                owners[task_id] = ("prepare", position)
                cursor["next_prepare"] += 1
                cursor["preparing"] += 1
            scheduled = True
            while scheduled and can_enqueue():
                scheduled = False
                for position in sorted(states):
                    state = states[position]
                    if state.next_block >= len(state.prepared.blocks) or not can_enqueue():
                        continue
                    task = state.prepared.blocks[state.next_block]
                    task_id = f"block:{position:08d}:{int(task[0]):012d}"
                    queue.submit(
                        task_id=task_id,
                        canonical_order=(position, 1, int(task[0])),
                        function=_query_block,
                        args=(state, task, unit_codes, exclude_own, tree_workers),
                        task_kind="feas1-witness-block",
                        estimated_memory_bytes=max(
                            64 * 1024, (int(task[1]) - int(task[0])) * (state.prepared.scaled.shape[1] * 8 + 64)
                        ),
                    )
                    owners[task_id] = ("block", position)
                    state.next_block += 1
                    state.inflight += 1
                    scheduled = True

        def finalize_pending() -> None:
            for position in sorted(tuple(pending_finalization)):
                state = states[position]
                reservation = f"finalize:{position:08d}"
                if not queue.try_reserve_memory(reservation, state.stream.finalization_memory_bytes):
                    continue
                try:
                    results[position] = _finalize_family(state, feas_policy, threshold)
                finally:
                    queue.release_memory(reservation)
                pending_finalization.discard(position)
                del states[position]
                queue.release_memory(f"state:{position:08d}")

        refill()
        while any(item is None for item in results):
            finalize_pending()
            refill()
            if not queue.has_outstanding_work:
                if pending_finalization:
                    raise TrainingDataInputError("FEAS1 finalization admission cannot fit the stage RAM budget.")
                raise TrainingDataInputError("FEAS1 scheduler exhausted work before every family completed.")
            if not queue.wait_for_completion(timeout=interval):
                continue
            for completion in queue.drain_completed(dispatch=False):
                kind, position = owners.pop(completion.task_id)
                if kind == "prepare":
                    cursor["preparing"] -= 1
                    state = completion.value
                    state.reducer = DeterministicOrderedReducer(
                        tuple(int(start) for start, _ in state.prepared.blocks),
                        commit=lambda _key, value, state=state: _reduce_block(state, value),
                    )
                    queue.reserve_memory(f"state:{position:08d}", state_memory(position))
                    states[position] = state
                    queue.dispatch_ready()
                    continue
                state = states[position]
                state.inflight -= 1
                value = completion.value
                state.reducer.push(int(value[0].start), value)
                progress["blocks"] += 1
                progress["witnesses"] += int(value[0].stop - value[0].start)
                queue.dispatch_ready()
                if state.reducer.complete and state.next_block == len(state.prepared.blocks) and state.inflight == 0:
                    pending_finalization.add(position)
                now = time.monotonic()
                if progress_callback is not None and now - progress["last"] >= interval:
                    elapsed = now - started
                    rate = progress["witnesses"] / elapsed if elapsed > 0 else 0.0
                    eta = (total_witnesses - progress["witnesses"]) / rate if rate > 0 else None
                    progress_callback(
                        f"status=progress; progress={format_progress_fraction(progress['witnesses'], total_witnesses)}; "
                        f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; "
                        f"blocks={progress['blocks']}/{total_blocks}"
                    )
                    progress["last"] = now
            finalize_pending()
            refill()
        # Read the admission disposition while the queue is still live, exactly
        # as COVREF already does for its own stage scope.
        queue_snapshot = queue.snapshot()
    completed = [item for item in results if item is not None]
    packed = pack_staged_neighborhood_families([item[1] for item in completed], directory=build_directory)
    store = TargetCoverageExactNeighborhoodStore(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        frame_domain_digest=reference.frame_domain_digest,
        candidate_count=reference.candidate_count,
        families=packed,
    )
    if progress_callback is not None:
        progress_callback(
            f"status=complete; families={len(families)}; edges={store.edge_count}; "
            f"elapsed={format_progress_time(time.monotonic() - started)}; "
            f"{scope.summary()}; "
            f"queue_lanes={queue_snapshot.allocated_workers}; "
            f"queue_max_busy={queue_snapshot.max_busy_workers}; "
            f"queue_peak_accounted_bytes={queue_snapshot.peak_accounted_memory_bytes}; "
            f"queue_memory_budget_bytes={queue_snapshot.memory_budget_bytes}; "
            f"queue_memory_backpressure={queue_snapshot.memory_backpressure_events}; "
            f"queue_backpressure={queue_snapshot.queue_backpressure_events}; "
            f"queue_tasks={queue_snapshot.committed_tasks}"
        )
    return TargetCoverageGeometry(
        neighborhoods=store,
        family_reports=tuple(item[0] for item in completed),
        policy=feas_policy,
    )


def _obligation_capacity(authority: Any) -> tuple[int, int, int]:
    """Conservative obligation cardinality bound over canonical obligations.

    Rebinds the historical packing bound: total required slots divided by the
    maximum number of obligations one candidate can advance, the strongest
    single minimum, disjoint extent sides (two frames) and pairwise disjoint
    P1 correlation units (one frame per unit per its minimum).
    """

    memberships = np.zeros(int(authority.candidate_count), dtype=np.int64)
    total_slots = 0
    strongest = 0
    unit_bound = 0
    extent_sides: dict[tuple[str | None, str], dict[str, np.ndarray]] = {}
    for item in authority.obligations:
        rows = np.asarray(item.candidate_indices, dtype=np.int64)
        total_slots += int(item.minimum_count)
        strongest = max(strongest, int(item.minimum_count))
        memberships[rows] += 1
        if item.locus.kind == KIND_CORRELATION_UNIT:
            unit_bound += int(item.minimum_count)
        elif item.locus.kind in (KIND_EXTENT_LOWER, KIND_EXTENT_UPPER):
            extent_sides.setdefault((item.locus.family_id, item.locus.target), {})[item.locus.relation] = rows
    disjoint_extent = 0
    for sides in extent_sides.values():
        if "lower" in sides and "upper" in sides and np.intersect1d(sides["lower"], sides["upper"]).size == 0:
            disjoint_extent = 2
    max_per_candidate = int(np.max(memberships)) if total_slots else 0
    packing = int(math.ceil(total_slots / max_per_candidate)) if max_per_candidate else 0
    return total_slots, max_per_candidate, max(packing, strongest, disjoint_extent, unit_bound)


def build_target_coverage_feasibility_report(
    reference: Any, geometry: TargetCoverageGeometry, authority: Any, *, configured_ceiling: int
) -> TargetCoverageFeasibilityReport:
    """Reduce geometry diagnostics plus canonical obligation capacity."""

    if geometry.neighborhoods.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("FEAS1 geometry/reference lineage mismatch.")
    if authority.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("FEAS1 obligation/reference lineage mismatch.")
    total_slots, max_per_candidate, obligation_bound = _obligation_capacity(authority)
    coverage_bound = max(item.coverage_cardinality_lower_bound for item in geometry.family_reports)
    k_bound = max(coverage_bound, obligation_bound)
    ceiling = min(int(configured_ceiling), int(reference.candidate_count))
    fragile = tuple(sorted(item.family_id for item in geometry.family_reports if item.cross_support_fragile))
    if k_bound > ceiling:
        terminal = STATE_CAPACITY_INFEASIBLE
    elif fragile:
        terminal = STATE_CROSS_SUPPORT_FRAGILE
    else:
        terminal = STATE_OPTIMIZATION_REQUIRED
    return TargetCoverageFeasibilityReport(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        geometry_digest=geometry.content_digest,
        obligation_authority_digest=authority.content_digest,
        policy=geometry.policy,
        coverage_threshold=float(reference.policy.coverage_threshold),
        candidate_count=int(reference.candidate_count),
        configured_ceiling=ceiling,
        family_reports=geometry.family_reports,
        obligation_slot_count=total_slots,
        obligation_max_per_candidate=max_per_candidate,
        obligation_lower_bound=obligation_bound,
        coverage_cardinality_lower_bound=coverage_bound,
        k_min_lower_bound=k_bound,
        fragile_family_ids=fragile,
        states=(STATE_SELF_CONSISTENT, terminal),
    )


def write_target_coverage_geometry(destination: Path, geometry: TargetCoverageGeometry) -> PublishedArtifact:
    """Publish NEIGHBOR1 plus FEAS1 family diagnostics as one shared product."""

    def write(directory: Path) -> Mapping[str, Any]:
        published = write_exact_neighborhood_store(directory / "neighbor1", geometry.neighborhoods)
        return {
            "schema": FEAS1_GEOMETRY_ARTIFACT_SCHEMA,
            "content_digest": geometry.content_digest,
            "neighborhood_manifest_digest": published.manifest_digest,
            "neighborhood_content_digest": geometry.neighborhoods.content_digest,
            "policy": geometry.policy.to_dict(),
            "family_reports": [item.to_dict() for item in geometry.family_reports],
        }

    return publish_artifact_directory(
        destination,
        schema=FEAS1_GEOMETRY_ARTIFACT_SCHEMA,
        write=write,
        verify_existing=lambda path, _manifest: read_target_coverage_geometry(path),
    )


def read_target_coverage_geometry(directory: Path) -> TargetCoverageGeometry:
    manifest = read_manifest(directory, schema=FEAS1_GEOMETRY_ARTIFACT_SCHEMA)
    neighborhood_manifest = read_manifest(Path(directory) / "neighbor1", schema=NEIGHBOR1_ARTIFACT_SCHEMA)
    if neighborhood_manifest["manifest_digest"] != manifest["neighborhood_manifest_digest"]:
        raise TrainingDataInputError("FEAS1 geometry does not bind its NEIGHBOR1 member.")
    geometry = TargetCoverageGeometry(
        neighborhoods=read_exact_neighborhood_store(Path(directory) / "neighbor1"),
        family_reports=tuple(TargetCoverageFamilyFeasibilityReport.from_dict(v) for v in manifest["family_reports"]),
        policy=TargetCoverageFeasibilityPolicy.from_dict(manifest["policy"]),
    )
    if geometry.content_digest != manifest["content_digest"]:
        raise TrainingDataInputError("FEAS1 geometry content identity mismatch.")
    return geometry


__all__ = [
    "STATE_CAPACITY_INFEASIBLE",
    "STATE_CROSS_SUPPORT_FRAGILE",
    "STATE_OPTIMIZATION_REQUIRED",
    "STATE_SELF_CONSISTENT",
    "TargetCoverageFamilyFeasibilityReport",
    "TargetCoverageFeasibilityPolicy",
    "TargetCoverageFeasibilityReport",
    "TargetCoverageGeometry",
    "TargetCoverageSupportDegreeReport",
    "build_target_coverage_feasibility_report",
    "build_target_coverage_geometry",
    "read_target_coverage_geometry",
    "write_target_coverage_geometry",
]
