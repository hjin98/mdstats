"""TARGET-DATA2B-FEAS1 support-fragility and cardinality diagnostics.

This gate deliberately does *not* select target subsets.  It consumes the
immutable TARGET-DATA2A role freeze and TARGET-DATA2B coverage reference and
asks three narrower questions before multi-view optimization is introduced:

1. Is the reference/candidate domain internally self-consistent?
2. How much witness mass is fragile after removing self support and the
   witness's own correlation-aware DATA5 partition unit?
3. What conservative lower bound on subset cardinality follows from exact
   coverage neighborhoods plus the currently frozen hard obligations?

The lower bound is optimistic by construction: overlap between singleton
coverage gains is ignored.  Therefore a bound above the fixed 16,384 ceiling
is a proof of capacity infeasibility, while a bound below the ceiling is only a
reason to proceed to optimization, never evidence that a feasible subset
already exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .target_coverage import target_coverage_role_domain_view
from .resources import StageResourceScope, available_cpu_threads
from .progress_timing import format_progress_fraction, format_progress_time
from .target_coverage_exact_neighborhood import (
    ExactNeighborhoodBlockResult,
    ExactNeighborhoodCSRStream,
    ExactNeighborhoodEngine,
    ExactNeighborhoodPreparedFamily,
    TargetCoverageExactNeighborhoodDomain,
    TargetCoverageExactNeighborhoodFamily,
    TargetCoverageExactNeighborhoodStore,
)
from .work_queue import (
    DeterministicOrderedReducer,
    DeterministicWorkQueue,
    DeterministicWorkQueueSnapshot,
)


TARGET_COVERAGE_FEASIBILITY_POLICY_SCHEMA = "mdstats.target-coverage-feas1-policy.v1"
TARGET_COVERAGE_SUPPORT_SCHEMA = "mdstats.target-coverage-feas1-support.v1"
TARGET_COVERAGE_FAMILY_FEASIBILITY_SCHEMA = "mdstats.target-coverage-feas1-family.v1"
TARGET_COVERAGE_DOMAIN_FEASIBILITY_SCHEMA = "mdstats.target-coverage-feas1-domain.v1"
TARGET_COVERAGE_FEASIBILITY_SCHEMA = "mdstats.target-coverage-feas1-report.v1"
TARGET_COVERAGE_FEASIBILITY_VERSION = "mdstats.target-data2b-feas1.2026-08.v1"

_STATE_SELF_CONSISTENT = "self_consistent"
_STATE_CROSS_SUPPORT_FRAGILE = "cross_support_fragile"
_STATE_OPTIMIZATION_REQUIRED = "optimization_required"
_STATE_CAPACITY_INFEASIBLE = "provably_capacity_infeasible"
_ALLOWED_STATES = {
    _STATE_SELF_CONSISTENT,
    _STATE_CROSS_SUPPORT_FRAGILE,
    _STATE_OPTIMIZATION_REQUIRED,
    _STATE_CAPACITY_INFEASIBLE,
}


class _GlobalFeasibilityProgress:
    """Campaign-wide FEAS1 progress backed by PARCORE1 queue telemetry."""

    __slots__ = (
        "callback", "completed_blocks", "completed_profiles",
        "completed_witnesses", "interval", "last_emit", "prepared_profiles",
        "started", "total_blocks", "total_profiles", "total_witnesses",
    )

    def __init__(
        self,
        *,
        total_profiles: int,
        total_blocks: int,
        total_witnesses: int,
        interval_seconds: float,
        callback: Callable[[str], None] | None,
    ) -> None:
        self.callback = callback
        self.completed_blocks = 0
        self.completed_profiles = 0
        self.completed_witnesses = 0
        self.interval = max(0.1, float(interval_seconds))
        self.last_emit = time.monotonic()
        self.prepared_profiles = 0
        self.started = self.last_emit
        self.total_blocks = max(1, int(total_blocks))
        self.total_profiles = max(1, int(total_profiles))
        self.total_witnesses = max(1, int(total_witnesses))

    @staticmethod
    def _duration(seconds: float) -> str:
        return format_progress_time(seconds)

    def _message(
        self,
        *,
        kind: str,
        active_profiles: int,
        snapshot: DeterministicWorkQueueSnapshot,
    ) -> str:
        now = time.monotonic()
        elapsed = max(0.0, now - self.started)
        rate = self.completed_witnesses / elapsed if elapsed > 0.0 else 0.0
        remaining = max(0, self.total_witnesses - self.completed_witnesses)
        eta = remaining / rate if rate > 0.0 else None
        percent = 100.0 * self.completed_witnesses / self.total_witnesses
        eta_text = format_progress_time(eta)
        memory = snapshot.accounted_memory_bytes
        budget = snapshot.memory_budget_bytes
        memory_text = (
            f"{memory}" if budget is None else f"{memory}/{budget}"
        )
        return (
            f"status={kind}; progress={format_progress_fraction(self.completed_witnesses, self.total_witnesses)}; "
            f"elapsed={self._duration(elapsed)}; eta={eta_text}; rate={rate:.1f} witness/s; "
            f"profiles={self.completed_profiles}/{self.total_profiles}; prepared={self.prepared_profiles}/{self.total_profiles}; "
            f"active={active_profiles}; blocks={self.completed_blocks}/{self.total_blocks}; "
            f"workers-busy={snapshot.busy_workers}/{snapshot.allocated_workers}; pending={snapshot.inflight_tasks}; "
            f"queued={snapshot.ready_tasks + max(0, snapshot.inflight_tasks - snapshot.busy_workers)}; "
            f"buffered={snapshot.completed_tasks}; memory-admitted={memory_text}; "
            f"backpressure={snapshot.memory_backpressure_events + snapshot.queue_backpressure_events}"
        )

    def start(self, *, global_workers: int, tree_workers: int, queue_depth: int) -> None:
        if self.callback is not None:
            self.callback(
                f"status=start; progress={format_progress_fraction(0, self.total_witnesses)}; "
                f"elapsed=00:00:00; eta=--:--:--; profiles={self.total_profiles}; blocks={self.total_blocks}; "
                f"global-workers={global_workers}; block-workers={global_workers}; tree-workers/task={tree_workers}; "
                f"queue-depth={queue_depth}; backend=parcore1-deterministic-work-queue"
            )

    def profile_prepared(self) -> None:
        self.prepared_profiles += 1

    def block_done(
        self,
        witness_count: int,
        *,
        active_profiles: int,
        snapshot: DeterministicWorkQueueSnapshot,
    ) -> None:
        previous_bucket = self.completed_blocks * 20 // self.total_blocks
        self.completed_blocks += 1
        self.completed_witnesses += int(witness_count)
        now = time.monotonic()
        milestone = (
            self.completed_blocks == self.total_blocks
            or self.completed_blocks == 1
            or self.completed_blocks * 20 // self.total_blocks > previous_bucket
        )
        if self.callback is not None and (milestone or now - self.last_emit >= self.interval):
            self.callback(
                self._message(
                    kind="progress",
                    active_profiles=active_profiles,
                    snapshot=snapshot,
                )
            )
            self.last_emit = now

    def profile_done(
        self,
        *,
        domain_id: str,
        family_id: str,
        profile_index: int,
        active_profiles: int,
        snapshot: DeterministicWorkQueueSnapshot,
    ) -> None:
        self.completed_profiles += 1
        if self.callback is not None:
            elapsed = max(0.0, time.monotonic() - self.started)
            rate = self.completed_witnesses / elapsed if elapsed > 0.0 else 0.0
            remaining = max(0, self.total_witnesses - self.completed_witnesses)
            eta = remaining / rate if rate > 0.0 else None
            self.callback(
                f"status=profile-complete; progress={format_progress_fraction(self.completed_witnesses, self.total_witnesses)}; "
                f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}; rate={rate:.1f} witness/s; "
                f"profile={self.completed_profiles}/{self.total_profiles}; domain={domain_id}; family={family_id}; "
                f"manifest={profile_index}/{self.total_profiles}; blocks={self.completed_blocks}/{self.total_blocks}; "
                f"active={active_profiles}; pending={snapshot.inflight_tasks}; "
                f"queued={snapshot.ready_tasks + max(0, snapshot.inflight_tasks - snapshot.busy_workers)}"
            )
            self.last_emit = time.monotonic()

    def heartbeat(
        self,
        *,
        active_profiles: int,
        snapshot: DeterministicWorkQueueSnapshot,
    ) -> None:
        if self.callback is not None:
            self.callback(
                self._message(
                    kind="heartbeat",
                    active_profiles=active_profiles,
                    snapshot=snapshot,
                )
            )
            self.last_emit = time.monotonic()


def _validate_state_tuple(values: Sequence[str]) -> tuple[str, ...]:
    states = tuple(str(v) for v in values)
    if not states or len(states) != len(set(states)) or any(v not in _ALLOWED_STATES for v in states):
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 states are invalid.")
    if states[0] != _STATE_SELF_CONSISTENT:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 state list must begin with self_consistent.")
    terminal = [v for v in states if v != _STATE_SELF_CONSISTENT]
    if len(terminal) != 1:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 requires exactly one terminal diagnostic state.")
    return states


@dataclass(frozen=True, slots=True)
class TargetCoverageFeasibilityPolicy:
    """Frozen FEAS1 diagnostic policy.

    ``support_degree_bins`` are cumulative diagnostic bins; zero and exact-one
    masses are stored separately.  The 16,384 ceiling is architectural, not a
    generated tuning knob.
    """

    maximum_candidate_size: int = 16384
    support_degree_bins: tuple[int, ...] = (2, 4, 8, 16, 32)
    exclude_own_correlation_unit: bool = True
    fragile_zero_mass_tolerance: float = 1.0e-12
    authority_version: str = TARGET_COVERAGE_FEASIBILITY_VERSION

    def __post_init__(self) -> None:
        maximum = int(self.maximum_candidate_size)
        if maximum != 16384:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 v1 freezes maximum_candidate_size at 16384.")
        bins = tuple(int(v) for v in self.support_degree_bins)
        if not bins or bins != tuple(sorted(set(bins))) or bins[0] < 2:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support_degree_bins must be sorted unique integers >= 2.")
        tolerance = float(self.fragile_zero_mass_tolerance)
        if not math.isfinite(tolerance) or tolerance < 0.0 or tolerance > 1.0e-6:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 fragile_zero_mass_tolerance is invalid.")
        if self.authority_version != TARGET_COVERAGE_FEASIBILITY_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2B-FEAS1 authority version.")
        object.__setattr__(self, "maximum_candidate_size", maximum)
        object.__setattr__(self, "support_degree_bins", bins)
        object.__setattr__(self, "fragile_zero_mass_tolerance", tolerance)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_FEASIBILITY_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "maximum_candidate_size": self.maximum_candidate_size,
            "support_degree_bins": list(self.support_degree_bins),
            "exclude_own_correlation_unit": bool(self.exclude_own_correlation_unit),
            "fragile_zero_mass_tolerance": self.fragile_zero_mass_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFeasibilityPolicy":
        if payload.get("schema") != TARGET_COVERAGE_FEASIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B-FEAS1 policy schema.")
        result = cls(
            maximum_candidate_size=int(payload["maximum_candidate_size"]),
            support_degree_bins=tuple(int(v) for v in payload["support_degree_bins"]),
            exclude_own_correlation_unit=bool(payload["exclude_own_correlation_unit"]),
            fragile_zero_mass_tolerance=float(payload["fragile_zero_mass_tolerance"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B-FEAS1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageSupportDegreeReport:
    """Weighted witness-mass distribution as a function of candidate degree."""

    witness_count: int
    zero_support_mass: float
    exact_one_support_mass: float
    cumulative_mass_by_max_degree: tuple[tuple[int, float], ...]
    minimum_degree: int
    maximum_degree: int

    def __post_init__(self) -> None:
        count = int(self.witness_count)
        if count < 1:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support report requires witnesses.")
        zero = float(self.zero_support_mass)
        one = float(self.exact_one_support_mass)
        if not (0.0 <= zero <= 1.0 + 1.0e-10) or not (0.0 <= one <= 1.0 + 1.0e-10):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support masses are invalid.")
        bins = tuple((int(k), float(v)) for k, v in self.cumulative_mass_by_max_degree)
        if bins != tuple(sorted(bins)) or len({k for k, _ in bins}) != len(bins):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support bins are invalid.")
        previous = -1.0
        for _, value in bins:
            if value < previous - 1.0e-12 or value < 0.0 or value > 1.0 + 1.0e-10:
                raise TrainingDataInputError("TARGET-DATA2B-FEAS1 cumulative support masses are invalid.")
            previous = value
        minimum = int(self.minimum_degree)
        maximum = int(self.maximum_degree)
        if minimum < 0 or maximum < minimum:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support degree range is invalid.")
        object.__setattr__(self, "witness_count", count)
        object.__setattr__(self, "zero_support_mass", zero)
        object.__setattr__(self, "exact_one_support_mass", one)
        object.__setattr__(self, "cumulative_mass_by_max_degree", bins)
        object.__setattr__(self, "minimum_degree", minimum)
        object.__setattr__(self, "maximum_degree", maximum)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_SUPPORT_SCHEMA,
            "witness_count": self.witness_count,
            "zero_support_mass": self.zero_support_mass,
            "exact_one_support_mass": self.exact_one_support_mass,
            "cumulative_mass_by_max_degree": [
                {"maximum_degree": k, "weighted_mass": value}
                for k, value in self.cumulative_mass_by_max_degree
            ],
            "minimum_degree": self.minimum_degree,
            "maximum_degree": self.maximum_degree,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageSupportDegreeReport":
        if payload.get("schema") != TARGET_COVERAGE_SUPPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B-FEAS1 support schema.")
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
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B-FEAS1 support digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageFamilyFeasibilityReport:
    family_id: str
    family_digest: str
    required: bool
    witness_count: int
    candidate_frame_count: int
    neighborhood_edge_count: int
    self_excluded_support: TargetCoverageSupportDegreeReport
    correlation_excluded_support: TargetCoverageSupportDegreeReport
    optimistic_max_singleton_gain: float
    coverage_cardinality_lower_bound: int
    hard_extent_obligation_count: int
    cross_support_fragile: bool

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 family_id cannot be empty.")
        object.__setattr__(self, "family_digest", validate_digest(self.family_digest, name="family_digest"))
        for name in ("witness_count", "candidate_frame_count", "neighborhood_edge_count", "coverage_cardinality_lower_bound", "hard_extent_obligation_count"):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"TARGET-DATA2B-FEAS1 {name} cannot be negative.")
            object.__setattr__(self, name, value)
        gain = float(self.optimistic_max_singleton_gain)
        if not math.isfinite(gain) or gain < 0.0 or gain > 1.0 + 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 singleton gain is invalid.")
        object.__setattr__(self, "optimistic_max_singleton_gain", gain)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_FAMILY_FEASIBILITY_SCHEMA,
            "family_id": self.family_id,
            "family_digest": self.family_digest,
            "required": bool(self.required),
            "witness_count": self.witness_count,
            "candidate_frame_count": self.candidate_frame_count,
            "neighborhood_edge_count": self.neighborhood_edge_count,
            "self_excluded_support": self.self_excluded_support.to_dict(),
            "correlation_excluded_support": self.correlation_excluded_support.to_dict(),
            "optimistic_max_singleton_gain": self.optimistic_max_singleton_gain,
            "coverage_cardinality_lower_bound": self.coverage_cardinality_lower_bound,
            "hard_extent_obligation_count": self.hard_extent_obligation_count,
            "cross_support_fragile": bool(self.cross_support_fragile),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFamilyFeasibilityReport":
        if payload.get("schema") != TARGET_COVERAGE_FAMILY_FEASIBILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B-FEAS1 family schema.")
        result = cls(
            family_id=str(payload["family_id"]),
            family_digest=str(payload["family_digest"]),
            required=bool(payload["required"]),
            witness_count=int(payload["witness_count"]),
            candidate_frame_count=int(payload["candidate_frame_count"]),
            neighborhood_edge_count=int(payload["neighborhood_edge_count"]),
            self_excluded_support=TargetCoverageSupportDegreeReport.from_dict(payload["self_excluded_support"]),
            correlation_excluded_support=TargetCoverageSupportDegreeReport.from_dict(payload["correlation_excluded_support"]),
            optimistic_max_singleton_gain=float(payload["optimistic_max_singleton_gain"]),
            coverage_cardinality_lower_bound=int(payload["coverage_cardinality_lower_bound"]),
            hard_extent_obligation_count=int(payload["hard_extent_obligation_count"]),
            cross_support_fragile=bool(payload["cross_support_fragile"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B-FEAS1 family digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageDomainFeasibilityReport:
    label_domain_id: str
    candidate_frame_count: int
    effective_candidate_ceiling: int
    family_reports: tuple[TargetCoverageFamilyFeasibilityReport, ...]
    required_stratum_count: int
    correlation_interval_count: int
    hard_obligation_slot_count: int
    hard_obligation_max_per_candidate: int
    hard_obligation_lower_bound: int
    coverage_cardinality_lower_bound: int
    k_min_lower_bound: int
    fragile_required_family_ids: tuple[str, ...]
    states: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 label_domain_id cannot be empty.")
        for name in (
            "candidate_frame_count", "effective_candidate_ceiling", "required_stratum_count",
            "correlation_interval_count", "hard_obligation_slot_count",
            "hard_obligation_max_per_candidate", "hard_obligation_lower_bound",
            "coverage_cardinality_lower_bound", "k_min_lower_bound",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"TARGET-DATA2B-FEAS1 {name} cannot be negative.")
            object.__setattr__(self, name, value)
        reports = tuple(sorted(self.family_reports, key=lambda item: item.family_id))
        if not reports or len({item.family_id for item in reports}) != len(reports):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 family reports must be non-empty and unique.")
        fragile = tuple(sorted(str(v) for v in self.fragile_required_family_ids))
        if len(fragile) != len(set(fragile)):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 fragile family IDs must be unique.")
        states = _validate_state_tuple(self.states)
        object.__setattr__(self, "family_reports", reports)
        object.__setattr__(self, "fragile_required_family_ids", fragile)
        object.__setattr__(self, "states", states)

    @property
    def terminal_state(self) -> str:
        return self.states[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_DOMAIN_FEASIBILITY_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "candidate_frame_count": self.candidate_frame_count,
            "effective_candidate_ceiling": self.effective_candidate_ceiling,
            "family_reports": [item.to_dict() for item in self.family_reports],
            "required_stratum_count": self.required_stratum_count,
            "correlation_interval_count": self.correlation_interval_count,
            "hard_obligation_slot_count": self.hard_obligation_slot_count,
            "hard_obligation_max_per_candidate": self.hard_obligation_max_per_candidate,
            "hard_obligation_lower_bound": self.hard_obligation_lower_bound,
            "coverage_cardinality_lower_bound": self.coverage_cardinality_lower_bound,
            "k_min_lower_bound": self.k_min_lower_bound,
            "fragile_required_family_ids": list(self.fragile_required_family_ids),
            "states": list(self.states),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageDomainFeasibilityReport":
        if payload.get("schema") != TARGET_COVERAGE_DOMAIN_FEASIBILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B-FEAS1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            candidate_frame_count=int(payload["candidate_frame_count"]),
            effective_candidate_ceiling=int(payload["effective_candidate_ceiling"]),
            family_reports=tuple(TargetCoverageFamilyFeasibilityReport.from_dict(item) for item in payload["family_reports"]),
            required_stratum_count=int(payload["required_stratum_count"]),
            correlation_interval_count=int(payload["correlation_interval_count"]),
            hard_obligation_slot_count=int(payload["hard_obligation_slot_count"]),
            hard_obligation_max_per_candidate=int(payload["hard_obligation_max_per_candidate"]),
            hard_obligation_lower_bound=int(payload["hard_obligation_lower_bound"]),
            coverage_cardinality_lower_bound=int(payload["coverage_cardinality_lower_bound"]),
            k_min_lower_bound=int(payload["k_min_lower_bound"]),
            fragile_required_family_ids=tuple(str(v) for v in payload["fragile_required_family_ids"]),
            states=tuple(str(v) for v in payload["states"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B-FEAS1 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetCoverageFeasibilityReport:
    dataset_id: str
    target_coverage_reference_digest: str
    target_data_role_freeze_digest: str
    policy: TargetCoverageFeasibilityPolicy
    coverage_threshold: float
    domains: tuple[TargetCoverageDomainFeasibilityReport, ...]
    states: tuple[str, ...]
    authority_version: str = TARGET_COVERAGE_FEASIBILITY_VERSION

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 dataset_id cannot be empty.")
        object.__setattr__(self, "target_coverage_reference_digest", validate_digest(self.target_coverage_reference_digest, name="target_coverage_reference_digest"))
        object.__setattr__(self, "target_data_role_freeze_digest", validate_digest(self.target_data_role_freeze_digest, name="target_data_role_freeze_digest"))
        threshold = float(self.coverage_threshold)
        if not math.isfinite(threshold) or not 0.0 < threshold <= 1.0:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 coverage_threshold is invalid.")
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 domains must be non-empty and unique.")
        states = _validate_state_tuple(self.states)
        if self.authority_version != TARGET_COVERAGE_FEASIBILITY_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2B-FEAS1 report version.")
        object.__setattr__(self, "coverage_threshold", threshold)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "states", states)

    @property
    def terminal_state(self) -> str:
        return self.states[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_COVERAGE_FEASIBILITY_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "policy": self.policy.to_dict(),
            "coverage_threshold": self.coverage_threshold,
            "domains": [item.to_dict() for item in self.domains],
            "states": list(self.states),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetCoverageFeasibilityReport":
        if payload.get("schema") != TARGET_COVERAGE_FEASIBILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2B-FEAS1 report schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            policy=TargetCoverageFeasibilityPolicy.from_dict(payload["policy"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            domains=tuple(TargetCoverageDomainFeasibilityReport.from_dict(item) for item in payload["domains"]),
            states=tuple(str(v) for v in payload["states"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2B-FEAS1 report digest mismatch.")
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

    def add(self, degree: int, weight: float) -> None:
        value = int(degree)
        mass = np.float64(weight)
        self.count += 1
        if self.minimum is None or value < self.minimum:
            self.minimum = value
        if value > self.maximum:
            self.maximum = value
        if value == 0:
            self.zero += mass
        if value == 1:
            self.one += mass
        for i, upper in enumerate(self.bins):
            if value <= upper:
                self.cumulative[i] += mass

    def add_many(self, degrees: np.ndarray, weights: np.ndarray) -> None:
        """Accumulate one complete family in historical witness order.

        ``np.add.accumulate`` preserves the scalar FP64 addition order for each
        support class while moving the degree/bin classification out of Python.
        Calling this once per family also makes the result independent of query
        block partitioning.
        """

        values = np.asarray(degrees, dtype=np.int64)
        masses = np.asarray(weights, dtype=np.float64)
        if values.ndim != 1 or masses.ndim != 1 or values.shape != masses.shape:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support batch shape mismatch.")
        if np.any(values < 0):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 support degree cannot be negative.")
        if values.size == 0:
            return
        self.count += int(values.size)
        local_minimum = int(np.min(values))
        local_maximum = int(np.max(values))
        self.minimum = local_minimum if self.minimum is None else min(self.minimum, local_minimum)
        self.maximum = max(self.maximum, local_maximum)

        def ordered_sum(mask: np.ndarray) -> np.float64:
            selected = masses[mask]
            if selected.size == 0:
                return np.float64(0.0)
            return np.add.accumulate(selected, dtype=np.float64)[-1]

        self.zero += ordered_sum(values == 0)
        self.one += ordered_sum(values == 1)
        for i, upper in enumerate(self.bins):
            self.cumulative[i] += ordered_sum(values <= upper)

    def freeze(self) -> TargetCoverageSupportDegreeReport:
        return TargetCoverageSupportDegreeReport(
            witness_count=self.count,
            zero_support_mass=float(self.zero),
            exact_one_support_mass=float(self.one),
            cumulative_mass_by_max_degree=tuple((upper, float(value)) for upper, value in zip(self.bins, self.cumulative, strict=True)),
            minimum_degree=0 if self.minimum is None else self.minimum,
            maximum_degree=self.maximum,
        )


def _role_domain_frame_units(role_domain: Any, frame_uids: Sequence[str]) -> np.ndarray:
    unit_by_uid: dict[str, str] = {}
    for interval in role_domain.development_intervals:
        for uid in interval.frame_uids:
            if uid in unit_by_uid:
                raise TrainingDataInputError("TARGET-DATA2B-FEAS1 development intervals overlap in frame membership.")
            unit_by_uid[uid] = interval.unit_id
    if set(unit_by_uid) != set(frame_uids):
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 role/coverage development-frame domains disagree.")
    unit_ids = tuple(sorted({unit_by_uid[uid] for uid in frame_uids}))
    unit_code = {unit_id: index for index, unit_id in enumerate(unit_ids)}
    return np.asarray([unit_code[unit_by_uid[uid]] for uid in frame_uids], dtype=np.int64)


def _coverage_cardinality_lower_bound(candidate_gain: np.ndarray, threshold: float) -> int:
    gains = np.sort(np.asarray(candidate_gain, dtype=np.float64))[::-1]
    positive = gains[gains > 0.0]
    if positive.size == 0:
        return int(np.iinfo(np.int32).max)
    cumulative = np.cumsum(positive, dtype=np.float64)
    index = int(np.searchsorted(cumulative, float(threshold) - 1.0e-12, side="left"))
    if index >= len(cumulative):
        return int(np.iinfo(np.int32).max)
    return index + 1


@dataclass(frozen=True)
class _FamilyFeasibilityJob:
    job_index: int
    profile_index: int
    domain_id: str
    frame_domain_digest: str
    family: Any
    domain_candidate_count: int
    unit_code_by_frame_index: np.ndarray
    threshold: float
    policy: TargetCoverageFeasibilityPolicy
    query_block_size: int


@dataclass
class _FamilyFeasibilityState:
    job: _FamilyFeasibilityJob
    values: np.ndarray
    frame_indices: np.ndarray
    weights: np.ndarray
    scaled: np.ndarray
    candidate_gain: np.ndarray
    self_degree_by_witness: np.ndarray
    correlation_degree_by_witness: np.ndarray
    blocks: tuple[tuple[int, int], ...]
    neighborhood: ExactNeighborhoodPreparedFamily = field(repr=False)
    neighborhood_stream: ExactNeighborhoodCSRStream = field(repr=False)
    edge_count: int = 0
    next_submit_index: int = 0
    inflight_blocks: int = 0
    reducer: DeterministicOrderedReducer | None = field(default=None, repr=False)


def _prepare_family_feasibility_state(job: _FamilyFeasibilityJob) -> _FamilyFeasibilityState:
    family = job.family
    engine = ExactNeighborhoodEngine()
    neighborhood = engine.prepare_family(
        label_domain_id=job.domain_id,
        frame_domain_digest=job.frame_domain_digest,
        family=family,
        candidate_count=job.domain_candidate_count,
        query_block_size=job.query_block_size,
    )
    # TARGET-DATA2 family records do not themselves own the candidate-domain
    # digest; the scheduler patches the domain digest before construction.
    values = np.asarray(family.values, dtype=np.float64)
    frame_indices = np.asarray(family.frame_indices, dtype=np.int64)
    weights = np.asarray(family.weights, dtype=np.float64)
    return _FamilyFeasibilityState(
        job=job,
        values=values,
        frame_indices=frame_indices,
        weights=weights,
        scaled=neighborhood.scaled,
        candidate_gain=np.zeros(job.domain_candidate_count, dtype=np.float64),
        self_degree_by_witness=np.empty(len(neighborhood.scaled), dtype=np.int64),
        correlation_degree_by_witness=np.empty(len(neighborhood.scaled), dtype=np.int64),
        blocks=neighborhood.blocks,
        neighborhood=neighborhood,
        neighborhood_stream=engine.open_stream(neighborhood),
    )

def _query_family_feasibility_block(
    state: _FamilyFeasibilityState,
    task: tuple[int, int],
    *,
    tree_workers: int,
) -> tuple[int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray, ExactNeighborhoodBlockResult]:
    block = ExactNeighborhoodEngine().query_block(
        state.neighborhood,
        task,
        tree_workers=tree_workers,
        context=f"TARGET-DATA2B-FEAS1 family {state.job.family.family_id!r}",
    )
    start, stop = block.start, block.stop
    local_rows = block.local_rows
    candidate_frames = block.candidate_indices
    self_degrees = block.unique_counts - 1
    if state.job.policy.exclude_own_correlation_unit:
        own_frames = state.frame_indices[start:stop]
        own_units = state.job.unit_code_by_frame_index[own_frames]
        cross_unit = (
            state.job.unit_code_by_frame_index[candidate_frames]
            != own_units[local_rows]
        )
        correlation_degrees = np.bincount(
            local_rows[cross_unit], minlength=stop - start
        ).astype(np.int64, copy=False)
    else:
        correlation_degrees = self_degrees.copy()
    return start, stop, local_rows, candidate_frames, self_degrees, correlation_degrees, block

def _reduce_family_feasibility_block(
    state: _FamilyFeasibilityState,
    result: tuple[int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray, ExactNeighborhoodBlockResult],
) -> None:
    start, stop, local_rows, candidate_frames, self_degrees, correlation_degrees, neighborhood_block = result
    state.neighborhood_stream.append(neighborhood_block)
    state.edge_count += int(candidate_frames.size)
    # Results can complete globally and across profiles in any order, but each
    # profile reduces strictly in witness-block order. Within a block the
    # canonical compressor is row-major/candidate-major, preserving the exact
    # historical FP64 np.add.at arithmetic order and therefore FEAS1 digests.
    np.add.at(state.candidate_gain, candidate_frames, state.weights[start + local_rows])
    state.self_degree_by_witness[start:stop] = self_degrees
    state.correlation_degree_by_witness[start:stop] = correlation_degrees


def _finalize_family_feasibility_state(
    state: _FamilyFeasibilityState,
) -> tuple[
    TargetCoverageFamilyFeasibilityReport,
    list[tuple[np.ndarray, int]],
    TargetCoverageExactNeighborhoodFamily,
]:
    family = state.job.family
    policy = state.job.policy
    self_support = _SupportAccumulator(policy.support_degree_bins)
    correlation_support = _SupportAccumulator(policy.support_degree_bins)
    self_support.add_many(state.self_degree_by_witness, state.weights)
    correlation_support.add_many(state.correlation_degree_by_witness, state.weights)

    coverage_lb = _coverage_cardinality_lower_bound(state.candidate_gain, state.job.threshold)
    if coverage_lb == int(np.iinfo(np.int32).max):
        raise TrainingDataInputError(
            f"TARGET-DATA2B-FEAS1 family {family.family_id!r} cannot reach its own coverage threshold even under optimistic singleton summation."
        )

    extent_obligations: list[tuple[np.ndarray, int]] = []
    for channel in family.extent_channels:
        column = state.values[:, int(channel.feature_index)]
        lower_rows = np.flatnonzero(
            column <= float(channel.lower_reference_quantile) + 1.0e-12
        )
        upper_rows = np.flatnonzero(
            column >= float(channel.upper_reference_quantile) - 1.0e-12
        )
        lower_frames = np.unique(state.frame_indices[lower_rows])
        upper_frames = np.unique(state.frame_indices[upper_rows])
        if lower_frames.size == 0 or upper_frames.size == 0:
            raise TrainingDataInputError(
                f"TARGET-DATA2B-FEAS1 extent obligation {family.family_id}:{channel.feature_name} has no candidate support."
            )
        extent_obligations.append((lower_frames, 1))
        extent_obligations.append((upper_frames, 1))

    self_report = self_support.freeze()
    correlation_report = correlation_support.freeze()
    fragile = bool(
        family.required
        and correlation_report.zero_support_mass > policy.fragile_zero_mass_tolerance
    )
    neighborhood_family = state.neighborhood_stream.finalize()
    if neighborhood_family.edge_count != state.edge_count:
        raise TrainingDataInputError(
            f"TARGET-DATA2B-FEAS1/NEIGHBOR1 edge-count mismatch for {family.family_id!r}."
        )
    return (
        TargetCoverageFamilyFeasibilityReport(
            family_id=family.family_id,
            family_digest=family.content_digest,
            required=bool(family.required),
            witness_count=len(state.values),
            candidate_frame_count=int(np.count_nonzero(state.candidate_gain > 0.0)),
            neighborhood_edge_count=state.edge_count,
            self_excluded_support=self_report,
            correlation_excluded_support=correlation_report,
            optimistic_max_singleton_gain=float(np.max(state.candidate_gain)),
            coverage_cardinality_lower_bound=coverage_lb,
            hard_extent_obligation_count=len(extent_obligations),
            cross_support_fragile=fragile,
        ),
        extent_obligations,
        neighborhood_family,
    )


def _family_state_memory_estimate(job: _FamilyFeasibilityJob) -> int:
    """Conservative execution-only RAM estimate for one active FEAS1 profile."""

    values = np.asarray(job.family.values)
    witness_count = int(len(job.family.values))
    feature_count = int(values.shape[1]) if values.ndim == 2 else 1
    candidate_count = int(job.domain_candidate_count)
    # Scaled FP64 workspace + cKDTree's point/index storage + output arrays.
    scaled_bytes = witness_count * feature_count * np.dtype(np.float64).itemsize
    tree_bytes = 2 * scaled_bytes + witness_count * np.dtype(np.int64).itemsize
    outputs = (
        candidate_count * np.dtype(np.float64).itemsize
        + 2 * witness_count * np.dtype(np.int64).itemsize
    )
    return max(1, int(scaled_bytes + tree_bytes + outputs))


def _family_block_memory_estimate(state: _FamilyFeasibilityState, task: tuple[int, int]) -> int:
    """Bounded scratch/result estimate used only for scheduler admission."""

    start, stop = task
    rows = max(1, int(stop) - int(start))
    features = max(1, int(state.scaled.shape[1]))
    # Query points/radii plus compressed row/candidate/degree arrays. The exact
    # ragged edge store is addressed by NEIGHBOR1; PARCORE1 supplies the common
    # admission mechanism without redefining FEAS1 neighborhood authority.
    return max(64 * 1024, rows * (features * 8 + 64))


def _default_feasibility_resource_scope(
    *,
    worker_count: int,
    tree_workers: int,
) -> StageResourceScope:
    nested = max(1, int(worker_count) * max(1, int(tree_workers)))
    visible = max(1, int(available_cpu_threads()))
    # A direct API call has no caller-supplied RAM contract.  Keep its
    # historical semantics independent of transient host/cgroup free-memory
    # readings; campaign execution passes an explicit StageResourceScope when
    # RAM admission/backpressure is required.  Otherwise a momentarily nearly
    # full shared host can make the exact same scientific call fail before its
    # first tiny task is dispatched.
    return StageResourceScope(
        stage_name="TARGET-DATA2B-FEAS1",
        cpu_threads_available=max(visible, nested),
        cpu_threads_budget=nested,
        python_workers=max(1, int(worker_count)),
        tree_workers=max(1, int(tree_workers)),
        blas_threads=1,
        ram_budget_bytes=None,
    )


def _evaluate_family_jobs_global(
    jobs: Sequence[_FamilyFeasibilityJob],
    *,
    global_workers: int,
    query_workers: int,
    progress_interval_seconds: float,
    progress_callback: Callable[[str], None] | None,
    resource_scope: StageResourceScope | None = None,
) -> list[tuple[
    TargetCoverageFamilyFeasibilityReport,
    list[tuple[np.ndarray, int]],
    TargetCoverageExactNeighborhoodFamily,
]]:
    """Evaluate every FEAS1 profile through the PARCORE1 shared work queue.

    Parallel execution remains single-level: each queue lane owns one profile
    preparation or witness-block task and exact cKDTree queries use one native
    worker whenever more than one outer lane is active.  Completed blocks are
    committed through a per-profile :class:`DeterministicOrderedReducer`, so
    historical FP64 ``np.add.at`` arithmetic order remains exact.
    """

    if not jobs:
        return []
    worker_count = max(1, int(global_workers))
    tree_workers = max(1, int(query_workers)) if worker_count == 1 else 1
    explicit_resource_scope = resource_scope is not None
    scope = (
        _default_feasibility_resource_scope(
            worker_count=worker_count, tree_workers=tree_workers
        )
        if resource_scope is None
        else resource_scope
    )
    if int(scope.python_workers) != worker_count:
        raise TrainingDataInputError(
            "TARGET-DATA2B-FEAS1 StageResourceScope python_workers does not match the global queue width."
        )
    if int(scope.tree_workers) != tree_workers:
        raise TrainingDataInputError(
            "TARGET-DATA2B-FEAS1 StageResourceScope tree_workers does not match the single-level tree width."
        )

    total_profiles = len(jobs)
    total_blocks = sum(
        math.ceil(len(job.family.values) / max(1, int(job.query_block_size)))
        for job in jobs
    )
    total_witnesses = sum(len(job.family.values) for job in jobs)
    progress = _GlobalFeasibilityProgress(
        total_profiles=total_profiles,
        total_blocks=total_blocks,
        total_witnesses=total_witnesses,
        interval_seconds=progress_interval_seconds,
        callback=progress_callback,
    )
    max_pending = max(worker_count, 2 * worker_count)
    max_buffered = max_pending + 2 * worker_count
    progress.start(
        global_workers=worker_count,
        tree_workers=tree_workers,
        queue_depth=max_pending,
    )
    results: list[
        tuple[
            TargetCoverageFamilyFeasibilityReport,
            list[tuple[np.ndarray, int]],
            TargetCoverageExactNeighborhoodFamily,
        ] | None
    ] = [None] * total_profiles

    def prepare_task(job: _FamilyFeasibilityJob) -> _FamilyFeasibilityState:
        return _prepare_family_feasibility_state(job)

    def block_task(
        state: _FamilyFeasibilityState,
        task: tuple[int, int],
    ) -> tuple[int, int, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        return _query_family_feasibility_block(
            state, task, tree_workers=tree_workers
        )

    active: dict[int, _FamilyFeasibilityState] = {}
    owners: dict[str, tuple[str, Any, Any]] = {}
    reservation_by_job: dict[int, str] = {}
    output_reservation_ids: list[str] = []
    next_job_to_prepare = 0
    preparing = 0
    rr_cursor = 0

    def ready_buffer_count() -> int:
        return sum(
            0 if state.reducer is None else state.reducer.buffered_count
            for state in active.values()
        )

    with DeterministicWorkQueue(
        scope,
        max_ready_tasks=max_pending,
        max_inflight_tasks=max_pending,
        max_completed_tasks=max_pending,
        heartbeat_interval_seconds=progress_interval_seconds,
        thread_name_prefix="mdstats-feas1-parcore1",
        manage_resource_scope=explicit_resource_scope,
    ) as queue:

        def buffered_count() -> int:
            return queue.outstanding_tasks + ready_buffer_count()

        def can_enqueue() -> bool:
            return queue.can_submit() and buffered_count() < max_buffered

        def submit_prepare(job: _FamilyFeasibilityJob) -> bool:
            nonlocal preparing
            if not can_enqueue():
                return False
            task_id = f"prepare:{job.job_index:08d}"
            queue.submit(
                task_id=task_id,
                canonical_order=(job.job_index, 0, 0),
                function=prepare_task,
                args=(job,),
                task_kind="profile-prepare",
                estimated_memory_bytes=_family_state_memory_estimate(job),
                locality_key=f"{job.domain_id}/{job.family.family_id}",
            )
            owners[task_id] = ("prepare", job, None)
            preparing += 1
            return True

        def submit_block(state: _FamilyFeasibilityState) -> bool:
            if state.next_submit_index >= len(state.blocks) or not can_enqueue():
                return False
            task = state.blocks[state.next_submit_index]
            task_id = f"block:{state.job.job_index:08d}:{int(task[0]):012d}"
            queue.submit(
                task_id=task_id,
                canonical_order=(state.job.job_index, 1, int(task[0])),
                function=block_task,
                args=(state, task),
                task_kind="witness-block",
                estimated_memory_bytes=_family_block_memory_estimate(state, task),
                locality_key=f"{state.job.domain_id}/{state.job.family.family_id}",
            )
            owners[task_id] = ("block", state, task)
            state.next_submit_index += 1
            state.inflight_blocks += 1
            return True

        def refill() -> None:
            nonlocal next_job_to_prepare, rr_cursor
            if buffered_count() >= max_buffered:
                return

            # Keep a small preparation stream in front of exact query work.
            # Startup may prepare one profile per lane; once active profiles
            # exist, no more than roughly one eighth of lanes is targeted at
            # future profile setup.
            if not active:
                prep_target = min(
                    worker_count, total_profiles - next_job_to_prepare + preparing
                )
            else:
                prep_target = min(
                    max(1, worker_count // 8),
                    total_profiles - next_job_to_prepare + preparing,
                )
            while (
                next_job_to_prepare < total_profiles
                and preparing < prep_target
                and can_enqueue()
            ):
                if not submit_prepare(jobs[next_job_to_prepare]):
                    break
                next_job_to_prepare += 1

            while active and can_enqueue():
                states = sorted(active.values(), key=lambda item: item.job.job_index)
                if not states:
                    break
                scheduled = False
                count = len(states)
                for offset in range(count):
                    index = (rr_cursor + offset) % count
                    state = states[index]
                    if submit_block(state):
                        rr_cursor = (index + 1) % count
                        scheduled = True
                        break
                if not scheduled:
                    break

            # If no active profile can currently feed blocks, use spare queue
            # capacity for additional deterministic profile preparation.
            while (
                next_job_to_prepare < total_profiles
                and can_enqueue()
                and not any(
                    state.next_submit_index < len(state.blocks)
                    for state in active.values()
                )
            ):
                if not submit_prepare(jobs[next_job_to_prepare]):
                    break
                next_job_to_prepare += 1

        while next_job_to_prepare < total_profiles and queue.outstanding_tasks < worker_count:
            if not submit_prepare(jobs[next_job_to_prepare]):
                break
            next_job_to_prepare += 1

        while any(item is None for item in results):
            refill()
            if not queue.has_outstanding_work:
                raise TrainingDataInputError(
                    "TARGET-DATA2B-FEAS1 PARCORE1 scheduler exhausted work before every profile completed."
                )
            timeout = max(
                0.05,
                progress.interval - (time.monotonic() - progress.last_emit),
            )
            if not queue.wait_for_completion(timeout=timeout):
                progress.heartbeat(
                    active_profiles=len(active), snapshot=queue.snapshot()
                )
                continue

            # Do not dispatch between releasing a completed prepare task's
            # memory estimate and promoting that memory to an active-profile
            # reservation. This keeps memory admission fail-closed.
            completions = queue.drain_completed(dispatch=False)
            for completion in completions:
                kind, owner, task = owners.pop(completion.task_id)
                if kind == "prepare":
                    preparing -= 1
                    state = completion.value
                    state.reducer = DeterministicOrderedReducer(
                        tuple(int(start) for start, _ in state.blocks),
                        commit=lambda _key, result, state=state: _reduce_family_feasibility_block(
                            state, result
                        ),
                    )
                    reservation_id = f"profile:{state.job.job_index:08d}"
                    queue.reserve_memory(
                        reservation_id, _family_state_memory_estimate(state.job)
                    )
                    reservation_by_job[state.job.job_index] = reservation_id
                    active[state.job.job_index] = state
                    progress.profile_prepared()
                    queue.dispatch_ready()
                    continue

                state = owner
                state.inflight_blocks -= 1
                result = completion.value
                if state.reducer is None:
                    raise TrainingDataInputError(
                        "TARGET-DATA2B-FEAS1 missing ordered reducer for active profile."
                    )
                state.reducer.push(int(result[0]), result)
                queue.dispatch_ready()
                progress.block_done(
                    int(result[1]) - int(result[0]),
                    active_profiles=len(active),
                    snapshot=queue.snapshot(),
                )

                if (
                    state.reducer.complete
                    and state.next_submit_index == len(state.blocks)
                    and state.inflight_blocks == 0
                ):
                    output_id = f"neighbor-output:{state.job.job_index:08d}"
                    # Reserve the exact final CSR bytes *before* the streamed
                    # edge payload is materialized into RAM.
                    queue.reserve_memory(
                        output_id, state.neighborhood_stream.final_array_memory_bytes
                    )
                    output_reservation_ids.append(output_id)
                    finalized = _finalize_family_feasibility_state(state)
                    results[state.job.job_index] = finalized
                    neighborhood_family = finalized[2]
                    actual_output_bytes = int(
                        neighborhood_family.witness_offsets.nbytes
                        + neighborhood_family.witness_candidates.nbytes
                    )
                    if actual_output_bytes != state.neighborhood_stream.final_array_memory_bytes:
                        raise TrainingDataInputError(
                            "TARGET-DATA2B-FEAS1/NEIGHBOR1 final CSR memory accounting changed during materialization."
                        )
                    del active[state.job.job_index]
                    reservation_id = reservation_by_job.pop(state.job.job_index)
                    queue.release_memory(reservation_id)
                    progress.profile_done(
                        domain_id=state.job.domain_id,
                        family_id=state.job.family.family_id,
                        profile_index=state.job.profile_index,
                        active_profiles=len(active),
                        snapshot=queue.snapshot(),
                    )
            refill()

        if reservation_by_job:
            raise TrainingDataInputError(
                "TARGET-DATA2B-FEAS1 PARCORE1 scheduler retained profile memory reservations after completion."
            )
        for reservation_id in output_reservation_ids:
            queue.release_memory(reservation_id)

    if any(item is None for item in results):
        raise TrainingDataInputError(
            "TARGET-DATA2B-FEAS1 PARCORE1 scheduler did not finalize every profile."
        )
    return [item for item in results if item is not None]


def _hard_obligation_lower_bound(
    domain: Any,
    role_domain: Any,
    *,
    extent_obligations: Sequence[tuple[np.ndarray, int]],
) -> tuple[int, int, int, int, int]:
    n = len(domain.frame_uids)
    memberships = np.zeros(n, dtype=np.int64)
    total_slots = 0
    required_strata = 0
    max_stratum_minimum = 0

    for stratum in domain.strata:
        if not stratum.required:
            continue
        rows = np.unique(np.asarray(stratum.frame_indices, dtype=np.int64))
        minimum = int(stratum.minimum_selected_frames)
        if rows.size < minimum or np.any(rows < 0) or np.any(rows >= n):
            raise TrainingDataInputError(f"TARGET-DATA2B-FEAS1 required stratum {stratum.stratum_id!r} is not self-consistent.")
        required_strata += 1
        total_slots += minimum
        max_stratum_minimum = max(max_stratum_minimum, minimum)
        memberships[rows] += 1

    interval_count = 0
    index_by_uid = {uid: index for index, uid in enumerate(domain.frame_uids)}
    for interval in role_domain.development_intervals:
        rows = np.asarray([index_by_uid[uid] for uid in interval.frame_uids if uid in index_by_uid], dtype=np.int64)
        if rows.size == 0:
            raise TrainingDataInputError(
                f"TARGET-DATA2B-FEAS1 development interval {interval.unit_id[:12]} has no candidate frame."
            )
        interval_count += 1
        total_slots += 1
        memberships[rows] += 1

    extent_disjoint_lb = 0
    for row, (frames, minimum) in enumerate(extent_obligations):
        candidate_rows = np.unique(np.asarray(frames, dtype=np.int64))
        if candidate_rows.size < minimum or np.any(candidate_rows < 0) or np.any(candidate_rows >= n):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 hard extent obligation is invalid.")
        total_slots += int(minimum)
        memberships[candidate_rows] += 1
        if row % 2 == 1:
            previous = np.unique(np.asarray(extent_obligations[row - 1][0], dtype=np.int64))
            if np.intersect1d(previous, candidate_rows, assume_unique=True).size == 0:
                extent_disjoint_lb = max(extent_disjoint_lb, 2)

    max_per_candidate = int(np.max(memberships)) if total_slots else 0
    packing_lb = int(math.ceil(total_slots / max_per_candidate)) if max_per_candidate else 0
    # Development intervals are pairwise disjoint by TARGET-DATA2A contract,
    # so satisfying one-frame-per-interval reservations requires at least one
    # selected frame for every interval regardless of overlap with other
    # obligation classes.
    lower_bound = max(packing_lb, max_stratum_minimum, extent_disjoint_lb, interval_count)
    return required_strata, interval_count, total_slots, max_per_candidate, lower_bound


def _domain_state(*, fragile: bool, lower_bound: int, ceiling: int) -> tuple[str, ...]:
    if lower_bound > ceiling:
        return (_STATE_SELF_CONSISTENT, _STATE_CAPACITY_INFEASIBLE)
    if fragile:
        return (_STATE_SELF_CONSISTENT, _STATE_CROSS_SUPPORT_FRAGILE)
    return (_STATE_SELF_CONSISTENT, _STATE_OPTIMIZATION_REQUIRED)


def build_target_coverage_feasibility_artifacts(
    target_coverage_reference: Any,
    target_data_role_freeze: Any,
    *,
    policy: TargetCoverageFeasibilityPolicy | None = None,
    query_workers: int = 1,
    query_block_size: int = 512,
    family_workers: int = 1,
    block_workers: int | None = None,
    progress_interval_seconds: float = 30.0,
    progress_callback: Callable[[str], None] | None = None,
    resource_scope: StageResourceScope | None = None,
) -> tuple[TargetCoverageFeasibilityReport, TargetCoverageExactNeighborhoodStore]:
    """Build exact FEAS1 authority plus the NEIGHBOR1 forward-CSR execution cache.

    ``query_workers``, ``query_block_size``, ``family_workers`` /
    ``block_workers``, and progress settings are execution-only. They are not
    serialized and cannot change the scientific digest. In parallel mode,
    ``block_workers`` is the size of one campaign-wide single-level FEAS1 work
    queue and cKDTree queries run with one native worker per queue lane.
    ``family_workers`` remains a compatibility alias for this global worker
    count.
    """

    active = TargetCoverageFeasibilityPolicy() if policy is None else policy
    workers = int(query_workers)
    block = int(query_block_size)
    block_parallelism = int(family_workers if block_workers is None else block_workers)
    interval = float(progress_interval_seconds)
    if workers < 1 or block < 1 or block_parallelism < 1 or interval <= 0.0:
        raise TrainingDataInputError(
            "TARGET-DATA2B-FEAS1 query_workers/query_block_size/block_workers/progress_interval_seconds must be positive."
        )
    if target_coverage_reference.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 dataset identity mismatch.")
    if target_coverage_reference.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 TARGET-DATA2A lineage mismatch.")

    domain_reports: list[TargetCoverageDomainFeasibilityReport] = []
    neighborhood_domains: list[TargetCoverageExactNeighborhoodDomain] = []
    domain_inputs: list[tuple[Any, Any, tuple[Any, ...], tuple[int, ...]]] = []
    jobs: list[_FamilyFeasibilityJob] = []
    profile_index = 1
    threshold = float(target_coverage_reference.policy.coverage_threshold)

    # Build a complete deterministic job manifest before starting expensive
    # work. This gives the reporter true campaign-wide profile/block/witness
    # totals and lets all domains/families feed one shared executor queue.
    for domain in target_coverage_reference.domains:
        role_domain = target_coverage_role_domain_view(target_data_role_freeze, domain)
        if set(domain.frame_uids) != set(role_domain.size_development_frame_uids):
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 coverage/role frame-domain mismatch.")
        unit_codes = _role_domain_frame_units(role_domain, domain.frame_uids)
        ordered_families = tuple(sorted(domain.families, key=lambda item: item.family_id))
        job_indices: list[int] = []
        for family in ordered_families:
            job_index = len(jobs)
            job_indices.append(job_index)
            jobs.append(
                _FamilyFeasibilityJob(
                    job_index=job_index,
                    profile_index=profile_index,
                    domain_id=domain.label_domain_id,
                    frame_domain_digest=domain.frame_domain_digest,
                    family=family,
                    domain_candidate_count=len(domain.frame_uids),
                    unit_code_by_frame_index=unit_codes,
                    threshold=threshold,
                    policy=active,
                    query_block_size=block,
                )
            )
            profile_index += 1
        domain_inputs.append((domain, role_domain, ordered_families, tuple(job_indices)))

    family_results = _evaluate_family_jobs_global(
        jobs,
        global_workers=block_parallelism,
        query_workers=workers,
        progress_interval_seconds=interval,
        progress_callback=progress_callback,
        resource_scope=resource_scope,
    )

    for domain, role_domain, ordered_families, job_indices in domain_inputs:
        family_reports: list[TargetCoverageFamilyFeasibilityReport] = []
        neighborhood_families: list[TargetCoverageExactNeighborhoodFamily] = []
        extent_obligations: list[tuple[np.ndarray, int]] = []
        for family, job_index in zip(ordered_families, job_indices, strict=True):
            family_report, family_extents, neighborhood_family = family_results[job_index]
            family_reports.append(family_report)
            neighborhood_families.append(neighborhood_family)
            if family.required:
                extent_obligations.extend(family_extents)

        required_family_lbs = [
            item.coverage_cardinality_lower_bound for item in family_reports if item.required
        ]
        if not required_family_lbs:
            raise TrainingDataInputError("TARGET-DATA2B-FEAS1 requires at least one hard coverage family.")
        coverage_lb = max(required_family_lbs)
        required_strata, interval_count, total_slots, max_per_candidate, hard_lb = _hard_obligation_lower_bound(
            domain,
            role_domain,
            extent_obligations=extent_obligations,
        )
        k_lb = max(coverage_lb, hard_lb)
        ceiling = min(active.maximum_candidate_size, len(domain.frame_uids))
        fragile_ids = tuple(sorted(
            item.family_id for item in family_reports if item.required and item.cross_support_fragile
        ))
        states = _domain_state(fragile=bool(fragile_ids), lower_bound=k_lb, ceiling=ceiling)
        domain_reports.append(
            TargetCoverageDomainFeasibilityReport(
                label_domain_id=domain.label_domain_id,
                candidate_frame_count=len(domain.frame_uids),
                effective_candidate_ceiling=ceiling,
                family_reports=tuple(family_reports),
                required_stratum_count=required_strata,
                correlation_interval_count=interval_count,
                hard_obligation_slot_count=total_slots,
                hard_obligation_max_per_candidate=max_per_candidate,
                hard_obligation_lower_bound=hard_lb,
                coverage_cardinality_lower_bound=coverage_lb,
                k_min_lower_bound=k_lb,
                fragile_required_family_ids=fragile_ids,
                states=states,
            )
        )
        neighborhood_domains.append(
            TargetCoverageExactNeighborhoodDomain(
                label_domain_id=domain.label_domain_id,
                frame_domain_digest=domain.frame_domain_digest,
                candidate_count=len(domain.frame_uids),
                families=tuple(neighborhood_families),
            )
        )

    terminal_states = {item.terminal_state for item in domain_reports}
    if _STATE_CAPACITY_INFEASIBLE in terminal_states:
        overall = _STATE_CAPACITY_INFEASIBLE
    elif _STATE_CROSS_SUPPORT_FRAGILE in terminal_states:
        overall = _STATE_CROSS_SUPPORT_FRAGILE
    else:
        overall = _STATE_OPTIMIZATION_REQUIRED
    report = TargetCoverageFeasibilityReport(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        policy=active,
        coverage_threshold=float(target_coverage_reference.policy.coverage_threshold),
        domains=tuple(domain_reports),
        states=(_STATE_SELF_CONSISTENT, overall),
    )
    neighborhoods = TargetCoverageExactNeighborhoodStore(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        domains=tuple(neighborhood_domains),
    )
    return report, neighborhoods


def build_target_coverage_feasibility_report(
    target_coverage_reference: Any,
    target_data_role_freeze: Any,
    *,
    policy: TargetCoverageFeasibilityPolicy | None = None,
    query_workers: int = 1,
    query_block_size: int = 512,
    family_workers: int = 1,
    block_workers: int | None = None,
    progress_interval_seconds: float = 30.0,
    progress_callback: Callable[[str], None] | None = None,
    resource_scope: StageResourceScope | None = None,
) -> TargetCoverageFeasibilityReport:
    """Compatibility FEAS1 API; computes through NEIGHBOR1 and returns the report only."""

    report, _ = build_target_coverage_feasibility_artifacts(
        target_coverage_reference,
        target_data_role_freeze,
        policy=policy,
        query_workers=query_workers,
        query_block_size=query_block_size,
        family_workers=family_workers,
        block_workers=block_workers,
        progress_interval_seconds=progress_interval_seconds,
        progress_callback=progress_callback,
        resource_scope=resource_scope,
    )
    return report


def validate_target_coverage_feasibility_authority(
    report: TargetCoverageFeasibilityReport,
    *,
    target_coverage_reference: Any,
    target_data_role_freeze: Any,
    policy: TargetCoverageFeasibilityPolicy | None = None,
) -> None:
    """Validate FEAS1 lineage/policy without replaying expensive tree queries."""

    active = TargetCoverageFeasibilityPolicy() if policy is None else policy
    if report.dataset_id != target_coverage_reference.dataset_id or report.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report dataset identity mismatch.")
    if report.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report coverage-reference digest mismatch.")
    if report.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report role-freeze digest mismatch.")
    if report.policy.policy_digest != active.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report policy changed.")
    if abs(report.coverage_threshold - float(target_coverage_reference.policy.coverage_threshold)) > 1.0e-15:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report coverage threshold changed.")
    expected_domains = tuple(sorted(item.label_domain_id for item in target_coverage_reference.domains))
    actual_domains = tuple(item.label_domain_id for item in report.domains)
    if actual_domains != expected_domains:
        raise TrainingDataInputError("TARGET-DATA2B-FEAS1 report domain set changed.")
