"""TARGET-DATA2C-MVSEL1 deterministic progressive multi-view selector.

This gate consumes the exact sparse MVIDX1 scientific substrate and constructs
one ordered nested coreset.  It is deliberately diagnostic/pre-migration: the
legacy TARGET-DATA2C v4 ladder remains the production selection authority until
MVQUAL1/SIZE-HALVE2/SIZE-FIDELITY2/MVMIGRATE1 close.

Selection is exact and deterministic:

* required hard obligations are serviced first;
* while hard coverage is incomplete, the current worst normalized required
  view is improved first, followed by total newly covered reference mass;
* after all hard predicates pass, a density-aware harmonic representation
  objective fills the remaining cardinality with diminishing returns;
* provenance balance and sparse-neighborhood diversity are deterministic
  secondary tie-breakers; stable frame UID is the final tie-break;
* coverage and harmonic gains are maintained incrementally from MVIDX1 inverse
  adjacency instead of recomputing candidate x witness coverage globally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import mmap
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ._sparse_vector_kernels import csr_gather_rows, iter_csr_gather_batches
from .progress_timing import format_progress_fraction, format_progress_time
from .target_multi_view_selection_state import (
    TargetMultiViewSelectionDomainStateCache,
    TargetMultiViewSelectionStateCache,
    checkpoint_from_domain_state,
)


TARGET_MULTI_VIEW_SELECTOR_POLICY_SCHEMA = "mdstats.target-multi-view-selector-policy.v1"
TARGET_MULTI_VIEW_SELECTION_ENTRY_SCHEMA = "mdstats.target-multi-view-selection-entry.v1"
TARGET_MULTI_VIEW_SELECTION_RUNG_SCHEMA = "mdstats.target-multi-view-selection-rung.v1"
TARGET_MULTI_VIEW_SELECTION_DOMAIN_SCHEMA = "mdstats.target-multi-view-selection-domain.v1"
TARGET_MULTI_VIEW_SELECTION_PLAN_SCHEMA = "mdstats.target-multi-view-selection-plan.v1"
TARGET_MULTI_VIEW_SELECTOR_VERSION = "mdstats.target-data2c-mvsel1.progressive-selector.2026-08.v1"

_DEFAULT_TARGET_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
_DEFAULT_COVERAGE_THRESHOLD = 0.95
_DEFAULT_TIE_TOLERANCE = 1.0e-14
# MVPERF1 execution-only sparse scatter budget. This value is deliberately
# excluded from scientific policy/digests; changing batch boundaries preserves
# witness order and therefore exact floating-point update order.
_MVPERF1_MAX_SCATTER_EDGES = 262_144
# Production MVIDX families can contain more than a billion inverse edges.
# Bound the transient FP64 weight gather used during selector initialization;
# row boundaries preserve the exact row-local reduction authority.
_MVSEL1_MAX_INITIAL_WEIGHT_BYTES = 512 * 1024 * 1024
# A dense-run update is selected only where at most two percent of the complete
# candidate/witness rectangle is absent.  This conservative measured crossover
# avoids replacing compact sparse gathers with fragmented Python run traversal.
_MVSEL1_DENSE_RUN_MIN_DENSITY = 0.98


def _validate_target_sizes(values: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(v) for v in values)
    if not sizes or any(v < 1 for v in sizes) or tuple(sorted(set(sizes))) != sizes:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 target_sizes must be unique positive increasing integers.")
    if sizes[-1] > 16384:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 target-size ceiling is frozen at 16384.")
    return sizes


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectorPolicy:
    """Frozen MVSEL1 scientific selection policy."""

    target_sizes: tuple[int, ...] = _DEFAULT_TARGET_SIZES
    coverage_threshold: float = _DEFAULT_COVERAGE_THRESHOLD
    gain_tie_tolerance: float = _DEFAULT_TIE_TOLERANCE
    representative_gain: str = "harmonic_witness_multiplicity"
    provenance_balance: str = "least_selected_correlation_unit"
    diversity_tie_break: str = "sparse_neighborhood_inverse_multiplicity"
    authority_version: str = TARGET_MULTI_VIEW_SELECTOR_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_sizes", _validate_target_sizes(self.target_sizes))
        threshold = float(self.coverage_threshold)
        if not math.isclose(threshold, _DEFAULT_COVERAGE_THRESHOLD, rel_tol=0.0, abs_tol=0.0):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 v1 freezes coverage_threshold at 0.95.")
        tol = float(self.gain_tie_tolerance)
        if not np.isfinite(tol) or tol <= 0.0 or tol > 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 gain_tie_tolerance is invalid.")
        if self.representative_gain != "harmonic_witness_multiplicity":
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 v1 freezes harmonic witness-multiplicity representative gain.")
        if self.provenance_balance != "least_selected_correlation_unit":
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 v1 freezes least-selected correlation-unit provenance balance.")
        if self.diversity_tie_break != "sparse_neighborhood_inverse_multiplicity":
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 v1 freezes sparse-neighborhood inverse-multiplicity diversity.")
        if self.authority_version != TARGET_MULTI_VIEW_SELECTOR_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL1 authority version.")
        object.__setattr__(self, "coverage_threshold", threshold)
        object.__setattr__(self, "gain_tie_tolerance", tol)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTOR_POLICY_SCHEMA,
            "target_sizes": list(self.target_sizes),
            "coverage_threshold": self.coverage_threshold,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "representative_gain": self.representative_gain,
            "provenance_balance": self.provenance_balance,
            "diversity_tie_break": self.diversity_tie_break,
            "authority_version": self.authority_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectorPolicy":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTOR_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVSEL1 policy schema.")
        result = cls(
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            coverage_threshold=float(payload["coverage_threshold"]),
            gain_tie_tolerance=float(payload["gain_tie_tolerance"]),
            representative_gain=str(payload["representative_gain"]),
            provenance_balance=str(payload["provenance_balance"]),
            diversity_tie_break=str(payload["diversity_tie_break"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVSEL1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionEntry:
    rank: int
    frame_uid: str
    phase: str
    primary_reason: str
    bottleneck_family_id: str | None
    hard_obligation_gain: int
    bottleneck_coverage_gain: float
    total_coverage_gain: float
    representative_gain: float
    normalized_diversity: float
    correlation_unit_code: int

    def __post_init__(self) -> None:
        if int(self.rank) < 0:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 entry rank must be nonnegative.")
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        if self.phase not in {"hard_coverage", "representative_fill"}:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 entry phase is invalid.")
        if not self.primary_reason.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 entry reason cannot be empty.")
        if int(self.hard_obligation_gain) < 0 or int(self.correlation_unit_code) < 0:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 entry integer score is invalid.")
        for name in ("bottleneck_coverage_gain", "total_coverage_gain", "representative_gain", "normalized_diversity"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < -1.0e-12:
                raise TrainingDataInputError(f"TARGET-DATA2C-MVSEL1 entry {name} is invalid.")
            object.__setattr__(self, name, max(0.0, value))
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(self, "hard_obligation_gain", int(self.hard_obligation_gain))
        object.__setattr__(self, "correlation_unit_code", int(self.correlation_unit_code))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_ENTRY_SCHEMA,
            "rank": self.rank,
            "frame_uid": self.frame_uid,
            "phase": self.phase,
            "primary_reason": self.primary_reason,
            "bottleneck_family_id": self.bottleneck_family_id,
            "hard_obligation_gain": self.hard_obligation_gain,
            "bottleneck_coverage_gain": self.bottleneck_coverage_gain,
            "total_coverage_gain": self.total_coverage_gain,
            "representative_gain": self.representative_gain,
            "normalized_diversity": self.normalized_diversity,
            "correlation_unit_code": self.correlation_unit_code,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionEntry":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTION_ENTRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVSEL1 entry schema.")
        return cls(
            rank=int(payload["rank"]),
            frame_uid=str(payload["frame_uid"]),
            phase=str(payload["phase"]),
            primary_reason=str(payload["primary_reason"]),
            bottleneck_family_id=None if payload.get("bottleneck_family_id") is None else str(payload["bottleneck_family_id"]),
            hard_obligation_gain=int(payload["hard_obligation_gain"]),
            bottleneck_coverage_gain=float(payload["bottleneck_coverage_gain"]),
            total_coverage_gain=float(payload["total_coverage_gain"]),
            representative_gain=float(payload["representative_gain"]),
            normalized_diversity=float(payload["normalized_diversity"]),
            correlation_unit_code=int(payload["correlation_unit_code"]),
        )


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionRung:
    target_size: int
    materializable: bool
    frame_uids: tuple[str, ...] = ()
    family_coverage: tuple[tuple[str, float], ...] = ()
    hard_obligations_passed: bool = False
    unsatisfied_obligation_ids: tuple[str, ...] = ()
    hard_coverage_qualified: bool = False
    phase_at_boundary: str | None = None
    shell_coverage_gain: float = 0.0
    shell_representative_gain: float = 0.0
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 rung target_size must be positive.")
        object.__setattr__(self, "target_size", size)
        uids = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if self.materializable:
            if len(uids) != size or len(set(uids)) != size or self.unavailable_reason is not None:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 materializable rung identity is invalid.")
            if self.phase_at_boundary not in {"hard_coverage", "representative_fill"}:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 rung phase is invalid.")
        else:
            if uids or self.family_coverage or self.phase_at_boundary is not None or not self.unavailable_reason:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 unavailable rung payload is invalid.")
        coverage = tuple((str(k), float(v)) for k, v in self.family_coverage)
        if coverage and (tuple(sorted(k for k, _ in coverage)) != tuple(k for k, _ in coverage) or any(not np.isfinite(v) or v < -1e-12 or v > 1.0 + 1e-10 for _, v in coverage)):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 rung coverage is invalid.")
        object.__setattr__(self, "frame_uids", uids)
        object.__setattr__(self, "family_coverage", coverage)
        object.__setattr__(self, "unsatisfied_obligation_ids", tuple(sorted(str(v) for v in self.unsatisfied_obligation_ids)))
        object.__setattr__(self, "shell_coverage_gain", max(0.0, float(self.shell_coverage_gain)))
        object.__setattr__(self, "shell_representative_gain", max(0.0, float(self.shell_representative_gain)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_RUNG_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "frame_uids": list(self.frame_uids),
            "family_coverage": [[k, v] for k, v in self.family_coverage],
            "hard_obligations_passed": self.hard_obligations_passed,
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "hard_coverage_qualified": self.hard_coverage_qualified,
            "phase_at_boundary": self.phase_at_boundary,
            "shell_coverage_gain": self.shell_coverage_gain,
            "shell_representative_gain": self.shell_representative_gain,
            "unavailable_reason": self.unavailable_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionRung":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTION_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVSEL1 rung schema.")
        return cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            frame_uids=tuple(str(v) for v in payload.get("frame_uids", ())),
            family_coverage=tuple((str(v[0]), float(v[1])) for v in payload.get("family_coverage", ())),
            hard_obligations_passed=bool(payload.get("hard_obligations_passed", False)),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload.get("unsatisfied_obligation_ids", ())),
            hard_coverage_qualified=bool(payload.get("hard_coverage_qualified", False)),
            phase_at_boundary=None if payload.get("phase_at_boundary") is None else str(payload["phase_at_boundary"]),
            shell_coverage_gain=float(payload.get("shell_coverage_gain", 0.0)),
            shell_representative_gain=float(payload.get("shell_representative_gain", 0.0)),
            unavailable_reason=None if payload.get("unavailable_reason") is None else str(payload["unavailable_reason"]),
        )


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionDomainPlan:
    label_domain_id: str
    reference_domain_digest: str
    sparse_domain_digest: str
    candidate_count: int
    required_family_ids: tuple[str, ...]
    master_order: tuple[TargetMultiViewSelectionEntry, ...]
    rungs: tuple[TargetMultiViewSelectionRung, ...]
    phase_a_completed_at: int | None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 domain label cannot be empty.")
        object.__setattr__(self, "reference_domain_digest", validate_digest(self.reference_domain_digest, name="reference_domain_digest"))
        object.__setattr__(self, "sparse_domain_digest", validate_digest(self.sparse_domain_digest, name="sparse_domain_digest"))
        n = int(self.candidate_count)
        if n < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 candidate_count must be positive.")
        families = tuple(sorted(str(v) for v in self.required_family_ids))
        if not families or len(set(families)) != len(families):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 required family identities are invalid.")
        order = tuple(self.master_order)
        if any(item.rank != rank for rank, item in enumerate(order)) or len({item.frame_uid for item in order}) != len(order):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 master order is not a unique zero-based sequence.")
        rungs = tuple(self.rungs)
        if not rungs:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 domain requires planned rungs.")
        completed = self.phase_a_completed_at
        if completed is not None and (int(completed) < 1 or int(completed) > len(order)):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 phase-A completion cardinality is invalid.")
        object.__setattr__(self, "candidate_count", n)
        object.__setattr__(self, "required_family_ids", families)
        object.__setattr__(self, "master_order", order)
        object.__setattr__(self, "rungs", rungs)
        object.__setattr__(self, "phase_a_completed_at", None if completed is None else int(completed))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "sparse_domain_digest": self.sparse_domain_digest,
            "candidate_count": self.candidate_count,
            "required_family_ids": list(self.required_family_ids),
            "master_order": [item.to_dict() for item in self.master_order],
            "rungs": [item.to_dict() for item in self.rungs],
            "phase_a_completed_at": self.phase_a_completed_at,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionDomainPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTION_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVSEL1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            sparse_domain_digest=str(payload["sparse_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            required_family_ids=tuple(str(v) for v in payload["required_family_ids"]),
            master_order=tuple(TargetMultiViewSelectionEntry.from_dict(item) for item in payload["master_order"]),
            rungs=tuple(TargetMultiViewSelectionRung.from_dict(item) for item in payload["rungs"]),
            phase_a_completed_at=None if payload.get("phase_a_completed_at") is None else int(payload["phase_a_completed_at"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVSEL1 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewSelectionPlan:
    dataset_id: str
    target_coverage_reference_digest: str
    target_coverage_sparse_index_digest: str
    policy: TargetMultiViewSelectorPolicy
    domains: tuple[TargetMultiViewSelectionDomainPlan, ...]
    authority_version: str = TARGET_MULTI_VIEW_SELECTOR_VERSION
    _domain_by_id: Mapping[str, TargetMultiViewSelectionDomainPlan] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 dataset_id cannot be empty.")
        ref_digest = validate_digest(self.target_coverage_reference_digest, name="target_coverage_reference_digest")
        sparse_digest = validate_digest(self.target_coverage_sparse_index_digest, name="target_coverage_sparse_index_digest")
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 requires unique domains.")
        if self.authority_version != TARGET_MULTI_VIEW_SELECTOR_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVSEL1 plan authority version.")
        object.__setattr__(self, "target_coverage_reference_digest", ref_digest)
        object.__setattr__(self, "target_coverage_sparse_index_digest", sparse_digest)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewSelectionDomainPlan:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_SELECTION_PLAN_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest": self.target_coverage_sparse_index_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._digest_payload(), "domains": [item.to_dict() for item in self.domains], "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_SELECTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVSEL1 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_coverage_sparse_index_digest=str(payload["target_coverage_sparse_index_digest"]),
            policy=TargetMultiViewSelectorPolicy.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewSelectionDomainPlan.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("domain_digests") not in (None, [item.content_digest for item in result.domains]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVSEL1 domain digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVSEL1 plan digest mismatch.")
        return result


@dataclass(slots=True)
class _FamilyState:
    family_id: str
    weights: np.ndarray
    covered: np.ndarray
    multiplicity: np.ndarray
    coverage_gain: np.ndarray
    representative_gain: np.ndarray
    coverage_mass: float = 0.0
    use_dense_runs: bool = False


@dataclass(slots=True)
class _DomainSelectorState:
    available: np.ndarray
    family_states: list[_FamilyState]
    total_coverage_gain: np.ndarray
    total_representative_gain: np.ndarray
    hard_gain: np.ndarray
    obligation_counts: np.ndarray
    required_obligation_mask: np.ndarray
    unsatisfied_required_obligation_count: int
    unit_counts: np.ndarray


def _row_weight_sums(offsets: np.ndarray, indices: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Return exact row-local FP64 sums with a bounded gather temporary."""

    starts = np.asarray(offsets[:-1], dtype=np.int64)
    stops = np.asarray(offsets[1:], dtype=np.int64)
    sums = np.zeros(starts.size, dtype=np.float64)
    max_edges = max(1, _MVSEL1_MAX_INITIAL_WEIGHT_BYTES // np.dtype(np.float64).itemsize)
    row_start = 0
    while row_start < starts.size:
        edge_start = int(starts[row_start])
        edge_limit = edge_start + max_edges
        row_stop = int(np.searchsorted(stops, edge_limit, side="right"))
        row_stop = max(row_start + 1, min(starts.size, row_stop))
        edge_stop = int(stops[row_stop - 1])
        edge_weights = weights[np.asarray(indices[edge_start:edge_stop], dtype=np.int64)]
        local_starts = starts[row_start:row_stop] - edge_start
        local_stops = stops[row_start:row_stop] - edge_start
        nonempty = local_starts < local_stops
        if np.any(nonempty):
            # Every CSR row remains one independent reduceat segment.  Chunking
            # only between complete rows cannot change FP64 operation order.
            local_sums = sums[row_start:row_stop]
            local_sums[nonempty] = np.add.reduceat(
                edge_weights, local_starts[nonempty], dtype=np.float64
            )
        row_start = row_stop
    return sums


def _drop_file_backed_pages(array: np.ndarray) -> None:
    """Release scanned mmap pages when the platform exposes MADV_DONTNEED."""

    root: Any = array
    while isinstance(getattr(root, "base", None), np.ndarray):
        root = root.base
    mapped = getattr(root, "_mmap", None)
    advice = getattr(mmap, "MADV_DONTNEED", None)
    if mapped is not None and advice is not None and hasattr(mapped, "madvise"):
        try:
            mapped.madvise(advice)
        except (BufferError, OSError, ValueError):
            pass


def _build_domain_state(
    reference_domain: Any,
    sparse_domain: Any,
    *,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
) -> _DomainSelectorState:
    n = sparse_domain.candidate_count
    family_states: list[_FamilyState] = []
    total_coverage = np.zeros(n, dtype=np.float64)
    total_rep = np.zeros(n, dtype=np.float64)
    family_count = len(sparse_domain.families)
    edge_total = sum(int(item.edge_count) for item in sparse_domain.families)
    started = time.monotonic()
    last_progress = started
    completed_edges = 0
    if progress_callback is not None:
        progress_callback(
            f"status=initializing; domain={reference_domain.label_domain_id}; "
            f"families={format_progress_fraction(0, family_count)}; edges=0/{edge_total:,}; "
            f"elapsed={format_progress_time(0.0)}; eta=--:--:--"
        )
    for family_number, sparse_family in enumerate(sparse_domain.families, start=1):
        family = reference_domain.family(sparse_family.family_id)
        weights = np.asarray(family.weights, dtype=np.float64)
        if weights.shape != (sparse_family.witness_count,):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 family weight/index cardinality mismatch.")
        initial = _row_weight_sums(sparse_family.candidate_offsets, sparse_family.candidate_witnesses, weights)
        coverage_gain = initial.copy()
        representative_gain = initial.copy()
        total_coverage += coverage_gain
        total_rep += representative_gain
        dense_denominator = int(sparse_family.candidate_count) * int(sparse_family.witness_count)
        use_dense_runs = (
            dense_denominator > 0
            and float(sparse_family.edge_count) / float(dense_denominator)
            >= _MVSEL1_DENSE_RUN_MIN_DENSITY
        )
        family_states.append(_FamilyState(
            family_id=sparse_family.family_id,
            weights=weights,
            covered=np.zeros(sparse_family.witness_count, dtype=np.bool_),
            multiplicity=np.zeros(sparse_family.witness_count, dtype=np.int32),
            coverage_gain=coverage_gain,
            representative_gain=representative_gain,
            use_dense_runs=use_dense_runs,
        ))
        completed_edges += int(sparse_family.edge_count)
        _drop_file_backed_pages(np.asarray(sparse_family.candidate_witnesses))
        now = time.monotonic()
        if progress_callback is not None and (
            family_number == family_count or now - last_progress >= progress_interval_seconds
        ):
            elapsed = now - started
            rate = completed_edges / elapsed if elapsed > 0.0 else 0.0
            eta = (edge_total - completed_edges) / rate if rate > 0.0 else None
            progress_callback(
                f"status=initializing; domain={reference_domain.label_domain_id}; "
                f"families={format_progress_fraction(family_number, family_count)}; "
                f"edges={completed_edges:,}/{edge_total:,}; "
                f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}"
            )
            last_progress = now

    required_mask = np.asarray([bool(item.required) for item in sparse_domain.obligations], dtype=np.bool_)
    hard_gain = np.zeros(n, dtype=np.int32)
    for oi, obligation in enumerate(sparse_domain.obligations):
        if not obligation.required:
            continue
        candidates = np.asarray(sparse_domain.obligation_candidate_indices(oi), dtype=np.int64)
        hard_gain[candidates] += 1
    return _DomainSelectorState(
        available=np.ones(n, dtype=np.bool_),
        family_states=family_states,
        total_coverage_gain=total_coverage,
        total_representative_gain=total_rep,
        hard_gain=hard_gain,
        obligation_counts=np.zeros(len(sparse_domain.obligations), dtype=np.int32),
        required_obligation_mask=required_mask,
        unsatisfied_required_obligation_count=int(np.count_nonzero(required_mask)),
        unit_counts=np.zeros(len(sparse_domain.correlation_unit_ids), dtype=np.int32),
    )


def _filter_best(values: np.ndarray, candidates: np.ndarray, tolerance: float) -> np.ndarray:
    if candidates.size <= 1:
        return candidates
    local = values[candidates]
    best = float(np.max(local))
    return candidates[local >= best - tolerance]


def _candidate_sparse_diversity(candidate: int, sparse_domain: Any, state: _DomainSelectorState) -> float:
    values: list[float] = []
    for sparse_family, family_state in zip(sparse_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        # Unweighted inverse multiplicity is deliberately distinct from the
        # weighted harmonic representative objective. It is only a late tie-break.
        values.append(float(np.mean(1.0 / (1.0 + family_state.multiplicity[witnesses]), dtype=np.float64)))
    return 0.0 if not values else float(np.mean(values, dtype=np.float64))


def _hard_obligations_satisfied(sparse_domain: Any, state: _DomainSelectorState) -> bool:
    # MVKERNEL1 maintains the threshold-transition count incrementally; the
    # sparse-domain argument is retained for the frozen private call signature.
    return int(state.unsatisfied_required_obligation_count) == 0


def _unsatisfied_required_obligations(sparse_domain: Any, state: _DomainSelectorState) -> tuple[str, ...]:
    return tuple(sorted(
        obligation.obligation_id
        for oi, obligation in enumerate(sparse_domain.obligations)
        if obligation.required and int(state.obligation_counts[oi]) < int(obligation.minimum_selected_frames)
    ))


def _coverage_satisfied(state: _DomainSelectorState, threshold: float, tolerance: float) -> bool:
    return all(item.coverage_mass >= threshold - tolerance for item in state.family_states)


def _bottleneck_family_index(state: _DomainSelectorState, threshold: float, tolerance: float) -> int:
    ratios = np.asarray([item.coverage_mass / threshold for item in state.family_states], dtype=np.float64)
    minimum = float(np.min(ratios))
    tied = np.flatnonzero(ratios <= minimum + tolerance)
    return int(tied[0])


def _choose_candidate(reference_domain: Any, sparse_domain: Any, state: _DomainSelectorState, policy: TargetMultiViewSelectorPolicy) -> tuple[int, str, str | None, float]:
    candidates = np.flatnonzero(state.available)
    if candidates.size == 0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 exhausted candidate pool before the requested cardinality.")
    tol = policy.gain_tie_tolerance

    hard_pending = not _hard_obligations_satisfied(sparse_domain, state)
    coverage_pending = not _coverage_satisfied(state, policy.coverage_threshold, tol)
    phase = "hard_coverage" if (hard_pending or coverage_pending) else "representative_fill"

    if hard_pending:
        best_hard = int(np.max(state.hard_gain[candidates]))
        candidates = candidates[state.hard_gain[candidates] == best_hard]

    bottleneck_index: int | None = None
    bottleneck_id: str | None = None
    if phase == "hard_coverage":
        bottleneck_index = _bottleneck_family_index(state, policy.coverage_threshold, tol)
        bottleneck_id = state.family_states[bottleneck_index].family_id
        candidates = _filter_best(state.family_states[bottleneck_index].coverage_gain, candidates, tol)
        candidates = _filter_best(state.total_coverage_gain, candidates, tol)
    else:
        candidates = _filter_best(state.total_representative_gain, candidates, tol)

    # Provenance balance: lower selected count in a candidate's correlation unit is better.
    if candidates.size > 1:
        unit_codes = np.asarray(sparse_domain.candidate_correlation_unit_codes[candidates], dtype=np.int64)
        counts = state.unit_counts[unit_codes]
        minimum = int(np.min(counts))
        candidates = candidates[counts == minimum]

    if phase == "hard_coverage":
        # Representative utility remains a late tie-break in phase A.
        candidates = _filter_best(state.total_representative_gain, candidates, tol)

    best_diversity = -1.0
    if candidates.size > 1:
        diversities = np.asarray([_candidate_sparse_diversity(int(c), sparse_domain, state) for c in candidates], dtype=np.float64)
        best_diversity = float(np.max(diversities))
        candidates = candidates[diversities >= best_diversity - tol]
    elif candidates.size == 1:
        best_diversity = _candidate_sparse_diversity(int(candidates[0]), sparse_domain, state)

    # Stable frame UID is the final deterministic tie-break.
    chosen = min((int(c) for c in candidates), key=lambda c: reference_domain.frame_uids[c])
    primary = "hard_obligation_gain" if hard_pending and int(state.hard_gain[chosen]) > 0 else (
        "worst_view_coverage" if phase == "hard_coverage" else "density_aware_representative_fill"
    )
    return chosen, phase, bottleneck_id, best_diversity


def _decrement_candidates_reference(array: np.ndarray, candidate_indices: np.ndarray, amount: float) -> None:
    if candidate_indices.size == 0 or amount == 0.0:
        return
    rows = np.asarray(candidate_indices, dtype=np.int64)
    array[rows] -= float(amount)
    near = rows[np.abs(array[rows]) <= 5.0e-13]
    if near.size:
        array[near] = 0.0
    if np.any(array[rows] < -5.0e-12):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 incremental gain bookkeeping became negative.")


def _select_and_update_reference(candidate: int, sparse_domain: Any, state: _DomainSelectorState) -> None:
    if not state.available[candidate]:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 attempted to select a duplicate candidate.")

    # Snapshot candidate gains before mutation for coverage accounting.
    marginal_by_family = [float(item.coverage_gain[candidate]) for item in state.family_states]

    for sparse_family, family_state, marginal in zip(sparse_domain.families, state.family_states, marginal_by_family, strict=True):
        family_state.coverage_mass = min(1.0, family_state.coverage_mass + marginal)
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        for witness in witnesses:
            wi = int(witness)
            covering_candidates = np.asarray(sparse_family.witness_candidate_indices(wi), dtype=np.int64)
            weight = float(family_state.weights[wi])
            if not family_state.covered[wi]:
                _decrement_candidates_reference(family_state.coverage_gain, covering_candidates, weight)
                _decrement_candidates_reference(state.total_coverage_gain, covering_candidates, weight)
                family_state.covered[wi] = True
            old_multiplicity = int(family_state.multiplicity[wi])
            old_gain = weight / (1.0 + old_multiplicity)
            new_gain = weight / (2.0 + old_multiplicity)
            decrement = old_gain - new_gain
            _decrement_candidates_reference(family_state.representative_gain, covering_candidates, decrement)
            _decrement_candidates_reference(state.total_representative_gain, covering_candidates, decrement)
            family_state.multiplicity[wi] = old_multiplicity + 1

    for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        oi_int = int(oi)
        obligation = sparse_domain.obligations[oi_int]
        if not obligation.required:
            continue
        before = int(state.obligation_counts[oi_int])
        after = before + 1
        state.obligation_counts[oi_int] = after
        minimum = int(obligation.minimum_selected_frames)
        # Keep the exact selected multiplicity even after an obligation is
        # satisfied.  MVSEL1 itself only needs the threshold transition, but
        # REPAIR1 requires the true count to determine whether a removal can
        # preserve a hard obligation without rescanning the subset.
        if before < minimum and after >= minimum:
            state.unsatisfied_required_obligation_count -= 1
            if state.unsatisfied_required_obligation_count < 0:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation pending count became negative.")
            candidates = np.asarray(sparse_domain.obligation_candidate_indices(oi_int), dtype=np.int64)
            state.hard_gain[candidates] -= 1
            if np.any(state.hard_gain[candidates] < 0):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation gain bookkeeping became negative.")

    unit_code = int(sparse_domain.candidate_correlation_unit_codes[candidate])
    state.unit_counts[unit_code] += 1
    state.available[candidate] = False



def _iter_inverse_scatter_batches(
    offsets: np.ndarray,
    indices: np.ndarray,
    witness_indices: np.ndarray,
    witness_amounts: np.ndarray,
    *,
    max_edges: int = _MVPERF1_MAX_SCATTER_EDGES,
):
    """Yield exact witness-ordered inverse-edge scatter batches.

    MVKERNEL1 keeps the frozen MVPERF1 batching semantics but replaces the
    Python list-of-slices gather with a vectorized ragged-CSR gather.  Witness
    order and canonical candidate-edge order remain unchanged.
    """

    witnesses = np.asarray(witness_indices, dtype=np.int64)
    amounts = np.asarray(witness_amounts, dtype=np.float64)
    if witnesses.ndim != 1 or amounts.shape != witnesses.shape:
        raise TrainingDataInputError("TARGET-DATA2C-MVKERNEL1 scatter witness/amount shape mismatch.")
    for rows, lengths, row_slice in iter_csr_gather_batches(
        offsets, indices, witnesses, max_edges=max_edges
    ):
        if rows.size:
            yield rows.astype(np.int64, copy=False), np.repeat(amounts[row_slice], lengths)


def _scatter_decrement_exact(
    array: np.ndarray,
    offsets: np.ndarray,
    indices: np.ndarray,
    witness_indices: np.ndarray,
    witness_amounts: np.ndarray,
) -> None:
    """Apply exact MVSEL1 decrements with bounded vectorized scatter batches."""

    touched = np.zeros(array.size, dtype=np.bool_)
    for rows, edge_amounts in _iter_inverse_scatter_batches(
        offsets, indices, witness_indices, witness_amounts
    ):
        np.add.at(array, rows, -edge_amounts)
        touched[rows] = True
    rows = np.flatnonzero(touched)
    if rows.size == 0:
        return
    # Reference MVSEL1 clamps only numerical zero noise.  Delaying this check to
    # the end of the selected-candidate update is arithmetic-equivalent because
    # all updates are non-positive and witness order is preserved.
    near = rows[np.abs(array[rows]) <= 5.0e-13]
    if near.size:
        array[near] = 0.0
    if np.any(array[rows] < -5.0e-12):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 incremental gain bookkeeping became negative.")


def _scatter_decrement_pair_exact(
    left: np.ndarray,
    right: np.ndarray,
    offsets: np.ndarray,
    indices: np.ndarray,
    witness_indices: np.ndarray,
    witness_amounts: np.ndarray,
) -> None:
    """Apply one exact ragged gather to two MVSEL gain arrays.

    MVSEL updates the per-family and domain-total gain arrays with identical
    edge/amount streams.  MVKERNEL1 gathers that stream once, then applies the
    frozen ordered ``np.add.at`` operation independently to both arrays.
    """

    touched = np.zeros(left.size, dtype=np.bool_)
    for rows, edge_amounts in _iter_inverse_scatter_batches(
        offsets, indices, witness_indices, witness_amounts
    ):
        np.add.at(left, rows, -edge_amounts)
        np.add.at(right, rows, -edge_amounts)
        touched[rows] = True
    rows = np.flatnonzero(touched)
    if rows.size == 0:
        return
    _clamp_and_validate_touched((left, right), rows)


def _clamp_and_validate_touched(arrays: Sequence[np.ndarray], rows: np.ndarray) -> None:
    """Apply the frozen MVSEL numerical guard once to unique touched rows."""

    for array in arrays:
        near = rows[np.abs(array[rows]) <= 5.0e-13]
        if near.size:
            array[near] = 0.0
        if np.any(array[rows] < -5.0e-12):
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL1 incremental gain bookkeeping became negative."
            )


def _scatter_decrement_pair_dense_runs_exact(
    left: np.ndarray,
    right: np.ndarray,
    offsets: np.ndarray,
    indices: np.ndarray,
    witness_indices: np.ndarray,
    witness_amounts: np.ndarray,
) -> None:
    """Apply canonical witness updates as contiguous candidate runs.

    MVIDX rows are strictly sorted and duplicate-free.  A contiguous slice add
    therefore applies the same scalar add once to each candidate, while the
    outer witness traversal preserves the reference FP64 order exactly.
    """

    witnesses = np.asarray(witness_indices, dtype=np.int64)
    amounts = np.asarray(witness_amounts, dtype=np.float64)
    if witnesses.ndim != 1 or amounts.shape != witnesses.shape:
        raise TrainingDataInputError("TARGET-DATA2C-MVKERNEL1 scatter witness/amount shape mismatch.")
    touched = np.zeros(left.size, dtype=np.bool_)
    for witness, amount in zip(witnesses, amounts, strict=True):
        start = int(offsets[int(witness)])
        stop = int(offsets[int(witness) + 1])
        row = np.asarray(indices[start:stop])
        if row.size == 0:
            continue
        gaps = np.flatnonzero(row[1:] != row[:-1] + 1)
        run_starts = np.concatenate((np.asarray([0], dtype=np.int64), gaps + 1))
        run_stops = np.concatenate((gaps + 1, np.asarray([row.size], dtype=np.int64)))
        negative_amount = -float(amount)
        for local_start, local_stop in zip(run_starts, run_stops, strict=True):
            candidate_start = int(row[int(local_start)])
            candidate_stop = int(row[int(local_stop) - 1]) + 1
            np.add(
                left[candidate_start:candidate_stop],
                negative_amount,
                out=left[candidate_start:candidate_stop],
            )
            np.add(
                right[candidate_start:candidate_stop],
                negative_amount,
                out=right[candidate_start:candidate_stop],
            )
            touched[candidate_start:candidate_stop] = True
    rows = np.flatnonzero(touched)
    if rows.size:
        _clamp_and_validate_touched((left, right), rows)


def _select_and_update(
    candidate: int,
    sparse_domain: Any,
    state: _DomainSelectorState,
    *,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
    rank: int | None = None,
    domain_id: str | None = None,
) -> None:
    """MVPERF1 exact batched implementation of the frozen MVSEL1 update."""

    if not state.available[candidate]:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 attempted to select a duplicate candidate.")

    marginal_by_family = [float(item.coverage_gain[candidate]) for item in state.family_states]
    update_started = time.monotonic()
    last_progress = update_started
    completed_edges = 0
    update_edge_total = sum(int(item.edge_count) for item in sparse_domain.families)
    family_rows = zip(
        sparse_domain.families, state.family_states, marginal_by_family, strict=True
    )
    for family_number, (sparse_family, family_state, marginal) in enumerate(
        family_rows, start=1
    ):
        scatter_pair = (
            _scatter_decrement_pair_dense_runs_exact
            if family_state.use_dense_runs
            else _scatter_decrement_pair_exact
        )
        family_state.coverage_mass = min(1.0, family_state.coverage_mass + marginal)
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size:
            newly_covered = witnesses[~family_state.covered[witnesses]]
            if newly_covered.size:
                coverage_amounts = np.asarray(
                    family_state.weights[newly_covered], dtype=np.float64
                )
                scatter_pair(
                    family_state.coverage_gain,
                    state.total_coverage_gain,
                    sparse_family.witness_offsets,
                    sparse_family.witness_candidates,
                    newly_covered,
                    coverage_amounts,
                )
                family_state.covered[newly_covered] = True

            # Compute every witness decrement with the same scalar operation
            # order as the MVSEL1 reference, then scatter edges in witness order.
            witness_weights = family_state.weights[witnesses]
            witness_multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
            representative_amounts = (
                witness_weights / (1.0 + witness_multiplicity)
                - witness_weights / (2.0 + witness_multiplicity)
            )
            scatter_pair(
                family_state.representative_gain,
                state.total_representative_gain,
                sparse_family.witness_offsets,
                sparse_family.witness_candidates,
                witnesses,
                representative_amounts,
            )
            family_state.multiplicity[witnesses] += 1
        completed_edges += int(sparse_family.edge_count)
        now = time.monotonic()
        if progress_callback is not None and now - last_progress >= progress_interval_seconds:
            elapsed = now - update_started
            rate = completed_edges / elapsed if elapsed > 0.0 else 0.0
            eta = (update_edge_total - completed_edges) / rate if rate > 0.0 else None
            progress_callback(
                f"status=updating; domain={domain_id or 'unknown'}; rank={rank if rank is not None else -1}; "
                f"families={format_progress_fraction(family_number, len(sparse_domain.families))}; "
                f"edges={completed_edges:,}/{update_edge_total:,}; "
                f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}"
            )
            last_progress = now

    for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        oi_int = int(oi)
        obligation = sparse_domain.obligations[oi_int]
        if not obligation.required:
            continue
        before = int(state.obligation_counts[oi_int])
        after = before + 1
        state.obligation_counts[oi_int] = after
        minimum = int(obligation.minimum_selected_frames)
        if before < minimum and after >= minimum:
            state.unsatisfied_required_obligation_count -= 1
            if state.unsatisfied_required_obligation_count < 0:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation pending count became negative.")
            candidates = np.asarray(sparse_domain.obligation_candidate_indices(oi_int), dtype=np.int64)
            state.hard_gain[candidates] -= 1
            if np.any(state.hard_gain[candidates] < 0):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation gain bookkeeping became negative.")

    unit_code = int(sparse_domain.candidate_correlation_unit_codes[candidate])
    state.unit_counts[unit_code] += 1
    state.available[candidate] = False


_MVSTATE_REPLAY_CANDIDATE_BLOCK = 32


def _scatter_decrement_pair_pregathered_exact(
    left: np.ndarray,
    right: np.ndarray,
    rows: np.ndarray,
    edge_amounts: np.ndarray,
) -> None:
    """Apply one already-gathered canonical edge stream with MVSEL arithmetic."""
    if rows.size == 0:
        return
    np.add.at(left, rows, -edge_amounts)
    np.add.at(right, rows, -edge_amounts)
    for array in (left, right):
        near = rows[np.abs(array[rows]) <= 5.0e-13]
        if near.size:
            array[near] = 0.0
        if np.any(array[rows] < -5.0e-12):
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVSEL1 incremental gain bookkeeping became negative."
            )


def _prepare_replay_family_block(sparse_family: Any, candidates: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Prepare canonical inverse-edge streams for a predetermined candidate block.

    Returns candidate-witness prefix, witness events, witness-edge prefix and
    pregathered inverse candidate rows.  This is execution-only preparation;
    arithmetic is still applied one selected candidate at a time.
    """
    witness_events, candidate_witness_lengths = csr_gather_rows(
        sparse_family.candidate_offsets, sparse_family.candidate_witnesses, candidates
    )
    candidate_witness_prefix = np.empty(candidates.size + 1, dtype=np.int64)
    candidate_witness_prefix[0] = 0
    np.cumsum(candidate_witness_lengths, dtype=np.int64, out=candidate_witness_prefix[1:])
    inverse_rows, witness_edge_lengths = csr_gather_rows(
        sparse_family.witness_offsets, sparse_family.witness_candidates,
        witness_events.astype(np.int64, copy=False),
    )
    witness_edge_prefix = np.empty(witness_events.size + 1, dtype=np.int64)
    witness_edge_prefix[0] = 0
    np.cumsum(witness_edge_lengths, dtype=np.int64, out=witness_edge_prefix[1:])
    return candidate_witness_prefix, witness_events.astype(np.int64, copy=False), witness_edge_prefix, inverse_rows.astype(np.int64, copy=False)


def _select_many_and_update_exact(
    candidates: Sequence[int] | np.ndarray,
    sparse_domain: Any,
    state: _DomainSelectorState,
    representative_utility: float,
    *,
    candidate_block_size: int = _MVSTATE_REPLAY_CANDIDATE_BLOCK,
) -> float:
    """Replay a predetermined selection sequence with batched CSR preparation.

    MVSTATE-REUSE1 may use this only after rank decisions are already frozen.
    Every state mutation remains candidate-major and uses the exact MVKERNEL1
    ``np.add.at``/clamp arithmetic.  Only repeated CSR gather construction is
    coalesced across a bounded block.
    """
    ordered = np.asarray(tuple(int(v) for v in candidates), dtype=np.int64)
    if ordered.ndim != 1:
        raise TrainingDataInputError("MVSTATE-REUSE1 replay candidates must be one-dimensional.")
    if ordered.size == 0:
        return float(representative_utility)
    if np.unique(ordered).size != ordered.size or np.any(ordered < 0) or np.any(ordered >= state.available.size):
        raise TrainingDataInputError("MVSTATE-REUSE1 replay candidate sequence is invalid.")
    if not np.all(state.available[ordered]):
        raise TrainingDataInputError("MVSTATE-REUSE1 replay sequence contains an already-selected candidate.")
    block_size = max(1, int(candidate_block_size))
    utility = float(representative_utility)

    for block_start in range(0, ordered.size, block_size):
        block = ordered[block_start:block_start + block_size]
        prepared = [_prepare_replay_family_block(sf, block) for sf in sparse_domain.families]
        for local_position, candidate_value in enumerate(block):
            candidate = int(candidate_value)
            utility += float(state.total_representative_gain[candidate])
            marginal_by_family = [float(item.coverage_gain[candidate]) for item in state.family_states]
            for sparse_family, family_state, marginal, prep in zip(
                sparse_domain.families, state.family_states, marginal_by_family, prepared, strict=True
            ):
                candidate_witness_prefix, witness_events, witness_edge_prefix, inverse_rows = prep
                w0 = int(candidate_witness_prefix[local_position])
                w1 = int(candidate_witness_prefix[local_position + 1])
                witnesses = witness_events[w0:w1]
                family_state.coverage_mass = min(1.0, family_state.coverage_mass + marginal)
                if witnesses.size:
                    newly_covered = witnesses[~family_state.covered[witnesses]]
                    if newly_covered.size:
                        coverage_amounts = np.asarray(family_state.weights[newly_covered], dtype=np.float64)
                        _scatter_decrement_pair_exact(
                            family_state.coverage_gain,
                            state.total_coverage_gain,
                            sparse_family.witness_offsets,
                            sparse_family.witness_candidates,
                            newly_covered,
                            coverage_amounts,
                        )
                        family_state.covered[newly_covered] = True

                    witness_weights = family_state.weights[witnesses]
                    witness_multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
                    representative_amounts = (
                        witness_weights / (1.0 + witness_multiplicity)
                        - witness_weights / (2.0 + witness_multiplicity)
                    )
                    e0 = int(witness_edge_prefix[w0])
                    e1 = int(witness_edge_prefix[w1])
                    rows = inverse_rows[e0:e1]
                    edge_lengths = np.diff(witness_edge_prefix[w0:w1 + 1])
                    edge_amounts = np.repeat(representative_amounts, edge_lengths)
                    _scatter_decrement_pair_pregathered_exact(
                        family_state.representative_gain,
                        state.total_representative_gain,
                        rows,
                        edge_amounts,
                    )
                    family_state.multiplicity[witnesses] += 1

            for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
                oi_int = int(oi)
                obligation = sparse_domain.obligations[oi_int]
                if not obligation.required:
                    continue
                before = int(state.obligation_counts[oi_int])
                after = before + 1
                state.obligation_counts[oi_int] = after
                minimum = int(obligation.minimum_selected_frames)
                if before < minimum and after >= minimum:
                    state.unsatisfied_required_obligation_count -= 1
                    if state.unsatisfied_required_obligation_count < 0:
                        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation pending count became negative.")
                    affected = np.asarray(sparse_domain.obligation_candidate_indices(oi_int), dtype=np.int64)
                    state.hard_gain[affected] -= 1
                    if np.any(state.hard_gain[affected] < 0):
                        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 hard-obligation gain bookkeeping became negative.")
            unit_code = int(sparse_domain.candidate_correlation_unit_codes[candidate])
            state.unit_counts[unit_code] += 1
            state.available[candidate] = False
    return utility


def _states_exactly_equal(left: _DomainSelectorState, right: _DomainSelectorState) -> bool:
    """Execution-only exact-state comparator used by MVPERF1 qualification."""
    if not (
        np.array_equal(left.available, right.available)
        and np.array_equal(left.total_coverage_gain, right.total_coverage_gain)
        and np.array_equal(left.total_representative_gain, right.total_representative_gain)
        and np.array_equal(left.hard_gain, right.hard_gain)
        and np.array_equal(left.obligation_counts, right.obligation_counts)
        and left.unsatisfied_required_obligation_count == right.unsatisfied_required_obligation_count
        and np.array_equal(left.unit_counts, right.unit_counts)
    ):
        return False
    for a, b in zip(left.family_states, right.family_states, strict=True):
        if a.family_id != b.family_id or a.coverage_mass != b.coverage_mass:
            return False
        if not (
            np.array_equal(a.covered, b.covered)
            and np.array_equal(a.multiplicity, b.multiplicity)
            and np.array_equal(a.coverage_gain, b.coverage_gain)
            and np.array_equal(a.representative_gain, b.representative_gain)
        ):
            return False
    return True

def _build_domain_plan(
    reference_domain: Any,
    sparse_domain: Any,
    policy: TargetMultiViewSelectorPolicy,
    *,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
    update_function: Callable[[int, Any, _DomainSelectorState], None] = _select_and_update,
    checkpoint_collector: list[Any] | None = None,
) -> TargetMultiViewSelectionDomainPlan:
    if reference_domain.content_digest != sparse_domain.frame_domain_digest and reference_domain.frame_domain_digest != sparse_domain.frame_domain_digest:
        # MVIDX binds frame_domain_digest, not the complete reference domain digest.
        if reference_domain.frame_domain_digest != sparse_domain.frame_domain_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 reference/sparse frame domains disagree.")
    if len(reference_domain.frame_uids) != sparse_domain.candidate_count:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 candidate cardinality mismatch.")

    materializable_sizes = tuple(size for size in policy.target_sizes if size <= sparse_domain.candidate_count)
    if not materializable_sizes:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 candidate pool is smaller than every requested target size.")
    limit = materializable_sizes[-1]
    target_set = set(materializable_sizes)
    state = _build_domain_state(
        reference_domain,
        sparse_domain,
        progress_callback=progress_callback,
        progress_interval_seconds=progress_interval_seconds,
    )
    entries: list[TargetMultiViewSelectionEntry] = []
    rung_by_size: dict[int, TargetMultiViewSelectionRung] = {}
    phase_a_completed_at: int | None = None
    previous_rung_size = 0
    representative_utility = 0.0
    selection_started = time.monotonic()
    last_rank_progress = selection_started
    if progress_callback is not None:
        dense_count = sum(int(item.use_dense_runs) for item in state.family_states)
        progress_callback(
            f"status=selecting; domain={reference_domain.label_domain_id}; "
            f"selected={format_progress_fraction(0, limit)}; dense_run_families={dense_count}; "
            f"elapsed={format_progress_time(0.0)}; eta=--:--:--"
        )

    for rank in range(limit):
        chosen, phase, bottleneck_id, diversity = _choose_candidate(reference_domain, sparse_domain, state, policy)
        bottleneck_gain = 0.0
        if bottleneck_id is not None:
            family_index = next(i for i, item in enumerate(state.family_states) if item.family_id == bottleneck_id)
            bottleneck_gain = float(state.family_states[family_index].coverage_gain[chosen])
        hard_gain = int(state.hard_gain[chosen])
        total_coverage_gain = float(state.total_coverage_gain[chosen])
        representative_gain = float(state.total_representative_gain[chosen])
        primary = "hard_obligation_gain" if hard_gain > 0 and not _hard_obligations_satisfied(sparse_domain, state) else (
            "worst_view_coverage" if phase == "hard_coverage" else "density_aware_representative_fill"
        )
        entry = TargetMultiViewSelectionEntry(
            rank=rank,
            frame_uid=reference_domain.frame_uids[chosen],
            phase=phase,
            primary_reason=primary,
            bottleneck_family_id=bottleneck_id,
            hard_obligation_gain=hard_gain,
            bottleneck_coverage_gain=bottleneck_gain,
            total_coverage_gain=total_coverage_gain,
            representative_gain=representative_gain,
            normalized_diversity=diversity,
            correlation_unit_code=int(sparse_domain.candidate_correlation_unit_codes[chosen]),
        )
        entries.append(entry)
        representative_utility += representative_gain
        if update_function is _select_and_update:
            _select_and_update(
                chosen,
                sparse_domain,
                state,
                progress_callback=progress_callback,
                progress_interval_seconds=progress_interval_seconds,
                rank=rank,
                domain_id=reference_domain.label_domain_id,
            )
        else:
            update_function(chosen, sparse_domain, state)

        if phase_a_completed_at is None and _hard_obligations_satisfied(sparse_domain, state) and _coverage_satisfied(state, policy.coverage_threshold, policy.gain_tie_tolerance):
            phase_a_completed_at = rank + 1

        size = rank + 1
        now = time.monotonic()
        if progress_callback is not None and (
            size == 1 or size == limit or now - last_rank_progress >= progress_interval_seconds
        ):
            elapsed = now - selection_started
            rate = size / elapsed if elapsed > 0.0 else 0.0
            eta = (limit - size) / rate if rate > 0.0 else None
            progress_callback(
                f"status=selecting; domain={reference_domain.label_domain_id}; "
                f"selected={format_progress_fraction(size, limit)}; phase={phase}; "
                f"elapsed={format_progress_time(elapsed)}; eta={format_progress_time(eta)}"
            )
            last_rank_progress = now
        if size in target_set:
            unsatisfied = _unsatisfied_required_obligations(sparse_domain, state)
            family_coverage = tuple((item.family_id, min(1.0, max(0.0, float(item.coverage_mass)))) for item in state.family_states)
            hard_pass = not unsatisfied
            coverage_pass = all(value >= policy.coverage_threshold - policy.gain_tie_tolerance for _, value in family_coverage)
            shell = entries[previous_rung_size:size]
            rung_by_size[size] = TargetMultiViewSelectionRung(
                target_size=size,
                materializable=True,
                frame_uids=tuple(item.frame_uid for item in entries[:size]),
                family_coverage=family_coverage,
                hard_obligations_passed=hard_pass,
                unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=bool(hard_pass and coverage_pass),
                phase_at_boundary=entries[-1].phase,
                shell_coverage_gain=float(np.sum([item.total_coverage_gain for item in shell], dtype=np.float64)),
                shell_representative_gain=float(np.sum([item.representative_gain for item in shell], dtype=np.float64)),
            )
            if checkpoint_collector is not None:
                checkpoint_collector.append(checkpoint_from_domain_state(
                    state,
                    target_size=size,
                    selected_frame_uids=tuple(item.frame_uid for item in entries[:size]),
                    representative_utility=representative_utility,
                ))
            previous_rung_size = size
            if progress_callback is not None:
                minimum = min(value for _, value in family_coverage)
                progress_callback(
                    f"status=rung; domain={reference_domain.label_domain_id}; target_size={size}; "
                    f"min_required_coverage={minimum:.6f}; hard_obligations={'PASS' if hard_pass else 'FAIL'}; "
                    f"phase={entries[-1].phase}"
                )

    rungs: list[TargetMultiViewSelectionRung] = []
    for size in policy.target_sizes:
        if size in rung_by_size:
            rungs.append(rung_by_size[size])
        else:
            rungs.append(TargetMultiViewSelectionRung(
                target_size=size,
                materializable=False,
                unavailable_reason=f"authorized_pool_has_{sparse_domain.candidate_count}_frames_below_required_{size}",
            ))

    return TargetMultiViewSelectionDomainPlan(
        label_domain_id=reference_domain.label_domain_id,
        reference_domain_digest=reference_domain.content_digest,
        sparse_domain_digest=sparse_domain.content_digest,
        candidate_count=sparse_domain.candidate_count,
        required_family_ids=tuple(item.family_id for item in state.family_states),
        master_order=tuple(entries),
        rungs=tuple(rungs),
        phase_a_completed_at=phase_a_completed_at,
    )


def _build_target_multi_view_selection(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    *,
    policy: TargetMultiViewSelectorPolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
    execution_mode: str = "optimized",
    capture_state_cache: bool = False,
) -> tuple[TargetMultiViewSelectionPlan, TargetMultiViewSelectionStateCache | None]:
    policy = policy or TargetMultiViewSelectorPolicy()
    if target_coverage_reference.dataset_id != target_coverage_sparse_index.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 dataset identity mismatch.")
    if target_coverage_sparse_index.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 MVIDX/reference lineage mismatch.")
    if not math.isclose(float(target_coverage_reference.policy.coverage_threshold), policy.coverage_threshold, rel_tol=0.0, abs_tol=0.0):
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 policy/reference coverage thresholds disagree.")
    if execution_mode not in {"optimized", "reference"}:
        raise TrainingDataInputError("TARGET-DATA2C-MVPERF1 execution_mode must be optimized or reference.")
    if not math.isfinite(float(progress_interval_seconds)) or float(progress_interval_seconds) <= 0.0:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 progress_interval_seconds must be positive.")
    update_function = _select_and_update if execution_mode == "optimized" else _select_and_update_reference
    domains = []
    checkpoint_rows: dict[str, tuple[Any, ...]] = {}
    for reference_domain in target_coverage_reference.domains:
        sparse_domain = target_coverage_sparse_index.domain(reference_domain.label_domain_id)
        collector: list[Any] | None = [] if capture_state_cache else None
        domain_plan = _build_domain_plan(
            reference_domain, sparse_domain, policy,
            progress_callback=progress_callback,
            progress_interval_seconds=float(progress_interval_seconds),
            update_function=update_function,
            checkpoint_collector=collector,
        )
        domains.append(domain_plan)
        if collector is not None:
            checkpoint_rows[reference_domain.label_domain_id] = tuple(collector)
    plan = TargetMultiViewSelectionPlan(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_coverage_sparse_index_digest=target_coverage_sparse_index.content_digest,
        policy=policy,
        domains=tuple(domains),
    )
    if not capture_state_cache:
        return plan, None
    cache_domains = []
    for domain_plan in plan.domains:
        cache_domains.append(TargetMultiViewSelectionDomainStateCache(
            label_domain_id=domain_plan.label_domain_id,
            reference_domain_digest=domain_plan.reference_domain_digest,
            sparse_domain_digest=domain_plan.sparse_domain_digest,
            selection_domain_digest=domain_plan.content_digest,
            candidate_count=domain_plan.candidate_count,
            checkpoints=checkpoint_rows[domain_plan.label_domain_id],
        ))
    cache = TargetMultiViewSelectionStateCache(
        dataset_id=plan.dataset_id,
        target_coverage_reference_digest=plan.target_coverage_reference_digest,
        target_coverage_sparse_index_digest=plan.target_coverage_sparse_index_digest,
        target_multi_view_selection_digest=plan.content_digest,
        selector_policy_digest=plan.policy.policy_digest,
        domains=tuple(cache_domains),
    )
    return plan, cache


def build_target_multi_view_selection_plan(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    *,
    policy: TargetMultiViewSelectorPolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
    execution_mode: str = "optimized",
) -> TargetMultiViewSelectionPlan:
    """Construct exact deterministic MVSEL1 evidence without migrating DATA2C."""
    plan, _ = _build_target_multi_view_selection(
        target_coverage_reference, target_coverage_sparse_index, policy=policy,
        progress_callback=progress_callback,
        progress_interval_seconds=progress_interval_seconds,
        execution_mode=execution_mode, capture_state_cache=False,
    )
    return plan


def build_target_multi_view_selection_artifacts(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    *,
    policy: TargetMultiViewSelectorPolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_interval_seconds: float = 30.0,
    execution_mode: str = "optimized",
) -> tuple[TargetMultiViewSelectionPlan, TargetMultiViewSelectionStateCache]:
    """Build MVSEL1 authority and exact reconstructible rung-state checkpoints once."""
    plan, cache = _build_target_multi_view_selection(
        target_coverage_reference, target_coverage_sparse_index, policy=policy,
        progress_callback=progress_callback,
        progress_interval_seconds=progress_interval_seconds,
        execution_mode=execution_mode, capture_state_cache=True,
    )
    assert cache is not None
    return plan, cache

def validate_target_multi_view_selection_authority(
    plan: TargetMultiViewSelectionPlan,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    policy: TargetMultiViewSelectorPolicy | None = None,
    verify_selection_replay: bool = False,
) -> None:
    """Validate MVSEL1 lineage, nested hard evidence, and optionally exact replay."""

    policy = policy or TargetMultiViewSelectorPolicy()
    if plan.dataset_id != target_coverage_reference.dataset_id or plan.dataset_id != target_coverage_sparse_index.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 dataset identity mismatch.")
    if plan.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 reference digest mismatch.")
    if plan.target_coverage_sparse_index_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 sparse-index digest mismatch.")
    if plan.policy.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 policy digest mismatch.")

    for domain_plan in plan.domains:
        reference_domain = target_coverage_reference.domain(domain_plan.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(domain_plan.label_domain_id)
        if domain_plan.reference_domain_digest != reference_domain.content_digest or domain_plan.sparse_domain_digest != sparse_domain.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 domain lineage changed.")
        if domain_plan.candidate_count != sparse_domain.candidate_count:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 domain cardinality changed.")
        if any(uid not in set(reference_domain.frame_uids) for uid in (item.frame_uid for item in domain_plan.master_order)):
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 master order contains an ineligible frame.")

        previous: set[str] = set()
        previous_coverage: dict[str, float] = {item.family_id: 0.0 for item in sparse_domain.families}
        uid_to_index = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
        for rung in domain_plan.rungs:
            if not rung.materializable:
                continue
            current = set(rung.frame_uids)
            if previous and not previous.issubset(current):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 nested-prefix invariant failed.")
            if tuple(item.frame_uid for item in domain_plan.master_order[:rung.target_size]) != rung.frame_uids:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 rung does not equal its master-order prefix.")
            selected = tuple(uid_to_index[uid] for uid in rung.frame_uids)
            observed_coverage = []
            from .target_coverage_sparse_index import indexed_family_covered_mass, indexed_obligation_selected_counts
            for sparse_family in sparse_domain.families:
                family = reference_domain.family(sparse_family.family_id)
                mass = indexed_family_covered_mass(sparse_family, family.weights, selected)
                observed_coverage.append((sparse_family.family_id, mass))
                if mass + policy.gain_tie_tolerance < previous_coverage[sparse_family.family_id]:
                    raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 coverage decreased across nested rungs.")
                previous_coverage[sparse_family.family_id] = mass
            for (expected_id, expected_mass), (observed_id, observed_mass) in zip(rung.family_coverage, observed_coverage, strict=True):
                if expected_id != observed_id or not math.isclose(expected_mass, observed_mass, rel_tol=0.0, abs_tol=5.0e-12):
                    raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 persisted rung coverage is inconsistent with MVIDX1.")
            counts = indexed_obligation_selected_counts(sparse_domain, selected)
            unsatisfied = tuple(sorted(
                obligation.obligation_id
                for oi, obligation in enumerate(sparse_domain.obligations)
                if obligation.required and int(counts[oi]) < int(obligation.minimum_selected_frames)
            ))
            if unsatisfied != rung.unsatisfied_obligation_ids or (not unsatisfied) != rung.hard_obligations_passed:
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 persisted hard-obligation state is inconsistent with MVIDX1.")
            coverage_pass = all(mass >= policy.coverage_threshold - policy.gain_tie_tolerance for _, mass in observed_coverage)
            if rung.hard_coverage_qualified != bool((not unsatisfied) and coverage_pass):
                raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 persisted hard-qualification state is inconsistent.")
            previous = current

    if verify_selection_replay:
        rebuilt = build_target_multi_view_selection_plan(
            target_coverage_reference,
            target_coverage_sparse_index,
            policy=policy,
        )
        if rebuilt.content_digest != plan.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVSEL1 exact replay changed the selection digest.")
