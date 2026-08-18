"""TARGET-DATA2C-REPAIR1 exact active-shell multi-view repair.

REPAIR1 consumes MVSEL1 + MVIDX1 evidence and repairs only the newly added
shell of each planned rung.  Lower prefixes are immutable.  Removal candidates
must have negligible exact unique coverage and may not own a required hard
obligation.  Replacement candidates are chosen from the exact current deficit
frontier.  Every accepted exchange strictly improves the frozen lexicographic
objective and the replacement inherits the removed rank.

This authority is diagnostic/pre-migration.  TARGET-DATA2C v4 remains the
production selector until MVPERF1/MVQUAL1/SIZE-HALVE2/SIZE-FIDELITY2 and the
explicit MVMIGRATE1 policy gate close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from contextlib import nullcontext
import math
from threading import local
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .resources import StageResourceScope, available_cpu_threads
from .work_queue import DeterministicWorkQueue
from ._sparse_vector_kernels import csr_gather_rows
from . import target_multi_view_selector as _mvsel
from .target_multi_view_selection_state import restore_domain_state, validate_target_multi_view_selection_state_cache


TARGET_MULTI_VIEW_REPAIR_POLICY_SCHEMA = "mdstats.target-multi-view-repair-policy.v1"
TARGET_MULTI_VIEW_REPAIR_SWAP_SCHEMA = "mdstats.target-multi-view-repair-swap.v1"
TARGET_MULTI_VIEW_REPAIR_RUNG_SCHEMA = "mdstats.target-multi-view-repair-rung.v1"
TARGET_MULTI_VIEW_REPAIR_DOMAIN_SCHEMA = "mdstats.target-multi-view-repair-domain.v1"
TARGET_MULTI_VIEW_REPAIR_PLAN_SCHEMA = "mdstats.target-multi-view-repair-plan.v1"
TARGET_MULTI_VIEW_REPAIR_VERSION = "mdstats.target-data2c-repair1.deficit-exchange.2026-08.v1"

_DEFAULT_UNIQUE_TOLERANCE = 1.0e-14
_DEFAULT_GAIN_TOLERANCE = 1.0e-14
_REPAIR_PARALLEL_EDGE_WORK_THRESHOLD = 10_000_000


class _RepairProposalScratch:
    """Thread-private epoch/stamp membership for one sparse repair domain.

    Proposal evaluation repeatedly asks whether a replacement witness is also
    covered by the frame being considered for removal.  REPAIR1 historically
    allocated ``intersect1d``/``isin`` temporaries for every replacement.  A
    worker-private stamp vector turns those membership checks into O(k) indexed
    reads while remaining completely outside scientific state.
    """

    __slots__ = ("_marks", "_epoch")

    def __init__(self, sparse_domain: Any) -> None:
        self._marks = tuple(
            np.zeros(int(family.witness_count), dtype=np.uint32)
            for family in sparse_domain.families
        )
        self._epoch = np.uint32(0)

    def mark_removed(self, sparse_domain: Any, removed: int) -> None:
        next_epoch = int(self._epoch) + 1
        if next_epoch >= np.iinfo(np.uint32).max:
            for marks in self._marks:
                marks.fill(0)
            next_epoch = 1
        self._epoch = np.uint32(next_epoch)
        for marks, family in zip(self._marks, sparse_domain.families, strict=True):
            witnesses = np.asarray(family.candidate_witness_indices(removed), dtype=np.int64)
            if witnesses.size:
                marks[witnesses] = self._epoch

    def shared_mask(self, family_index: int, witnesses: np.ndarray) -> np.ndarray:
        if witnesses.size == 0:
            return np.zeros(0, dtype=bool)
        return self._marks[int(family_index)][witnesses] == self._epoch


def _repair_parallel_scope(workers: int) -> StageResourceScope:
    available = max(1, int(available_cpu_threads()))
    resolved = max(1, min(int(workers), available))
    return StageResourceScope(
        stage_name="TARGET-DATA2C-REPAIR-PAR1",
        cpu_threads_available=available,
        cpu_threads_budget=resolved,
        python_workers=resolved,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        gpu_jobs=0,
        ram_budget_bytes=None,
    )


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPolicy:
    """Frozen REPAIR1 scientific/algorithmic policy."""

    unique_coverage_tolerance: float = _DEFAULT_UNIQUE_TOLERANCE
    gain_tie_tolerance: float = _DEFAULT_GAIN_TOLERANCE
    max_passes_per_shell: int = 2
    max_swaps_per_shell: int = 32
    removal_shortlist_limit: int = 64
    active_shell_only: bool = True
    replacement_rank_inheritance: bool = True
    strict_no_coverage_regression: bool = True
    clustering_score_authority: str = "diagnostic_only"
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_VERSION

    def __post_init__(self) -> None:
        unique_tol = float(self.unique_coverage_tolerance)
        gain_tol = float(self.gain_tie_tolerance)
        if not np.isfinite(unique_tol) or unique_tol <= 0.0 or unique_tol > 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 unique_coverage_tolerance is invalid.")
        if not np.isfinite(gain_tol) or gain_tol <= 0.0 or gain_tol > 1.0e-10:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 gain_tie_tolerance is invalid.")
        if int(self.max_passes_per_shell) < 1 or int(self.max_passes_per_shell) > 16:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 max_passes_per_shell is invalid.")
        if int(self.max_swaps_per_shell) < 1 or int(self.max_swaps_per_shell) > 1024:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 max_swaps_per_shell is invalid.")
        if int(self.removal_shortlist_limit) < 1 or int(self.removal_shortlist_limit) > 4096:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 removal_shortlist_limit is invalid.")
        if not self.active_shell_only or not self.replacement_rank_inheritance or not self.strict_no_coverage_regression:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 v1 freezes active-shell/rank-inheritance/non-regression behavior.")
        if self.clustering_score_authority != "diagnostic_only":
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 clustering score cannot become scientific authority.")
        if self.authority_version != TARGET_MULTI_VIEW_REPAIR_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR1 authority version.")
        object.__setattr__(self, "unique_coverage_tolerance", unique_tol)
        object.__setattr__(self, "gain_tie_tolerance", gain_tol)
        object.__setattr__(self, "max_passes_per_shell", int(self.max_passes_per_shell))
        object.__setattr__(self, "max_swaps_per_shell", int(self.max_swaps_per_shell))
        object.__setattr__(self, "removal_shortlist_limit", int(self.removal_shortlist_limit))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_POLICY_SCHEMA,
            "unique_coverage_tolerance": self.unique_coverage_tolerance,
            "gain_tie_tolerance": self.gain_tie_tolerance,
            "max_passes_per_shell": self.max_passes_per_shell,
            "max_swaps_per_shell": self.max_swaps_per_shell,
            "removal_shortlist_limit": self.removal_shortlist_limit,
            "active_shell_only": self.active_shell_only,
            "replacement_rank_inheritance": self.replacement_rank_inheritance,
            "strict_no_coverage_regression": self.strict_no_coverage_regression,
            "clustering_score_authority": self.clustering_score_authority,
            "authority_version": self.authority_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairPolicy":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-REPAIR1 policy schema.")
        result = cls(
            unique_coverage_tolerance=float(payload["unique_coverage_tolerance"]),
            gain_tie_tolerance=float(payload["gain_tie_tolerance"]),
            max_passes_per_shell=int(payload["max_passes_per_shell"]),
            max_swaps_per_shell=int(payload["max_swaps_per_shell"]),
            removal_shortlist_limit=int(payload["removal_shortlist_limit"]),
            active_shell_only=bool(payload["active_shell_only"]),
            replacement_rank_inheritance=bool(payload["replacement_rank_inheritance"]),
            strict_no_coverage_regression=bool(payload["strict_no_coverage_regression"]),
            clustering_score_authority=str(payload["clustering_score_authority"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-REPAIR1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairSwap:
    target_size: int
    pass_index: int
    swap_index: int
    rank: int
    removed_frame_uid: str
    replacement_frame_uid: str
    removed_unique_coverage: float
    removed_representative_loss: float
    hard_deficit_before: int
    hard_deficit_after: int
    minimum_coverage_before: float
    minimum_coverage_after: float
    total_coverage_before: float
    total_coverage_after: float
    representative_utility_before: float
    representative_utility_after: float
    unit_balance_before: int
    unit_balance_after: int
    bottleneck_family_id: str
    displaced_future_rank: int | None = None

    def __post_init__(self) -> None:
        if int(self.target_size) < 1 or int(self.rank) < 0 or int(self.rank) >= int(self.target_size):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap rank/target_size is invalid.")
        if int(self.pass_index) < 0 or int(self.swap_index) < 0:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap pass/index is invalid.")
        object.__setattr__(self, "removed_frame_uid", validate_digest(self.removed_frame_uid, name="removed_frame_uid"))
        object.__setattr__(self, "replacement_frame_uid", validate_digest(self.replacement_frame_uid, name="replacement_frame_uid"))
        if self.removed_frame_uid == self.replacement_frame_uid:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap must exchange distinct frames.")
        for name in (
            "removed_unique_coverage", "removed_representative_loss", "minimum_coverage_before",
            "minimum_coverage_after", "total_coverage_before", "total_coverage_after",
            "representative_utility_before", "representative_utility_after",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < -1.0e-12:
                raise TrainingDataInputError(f"TARGET-DATA2C-REPAIR1 swap {name} is invalid.")
            object.__setattr__(self, name, max(0.0, value))
        if int(self.hard_deficit_after) > int(self.hard_deficit_before):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap cannot increase hard deficit.")
        if self.displaced_future_rank is not None and int(self.displaced_future_rank) < int(self.target_size):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 displaced future rank must lie beyond the active rung.")
        if not self.bottleneck_family_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 bottleneck family identity is invalid.")
        object.__setattr__(self, "target_size", int(self.target_size))
        object.__setattr__(self, "pass_index", int(self.pass_index))
        object.__setattr__(self, "swap_index", int(self.swap_index))
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(self, "hard_deficit_before", int(self.hard_deficit_before))
        object.__setattr__(self, "hard_deficit_after", int(self.hard_deficit_after))
        object.__setattr__(self, "unit_balance_before", int(self.unit_balance_before))
        object.__setattr__(self, "unit_balance_after", int(self.unit_balance_after))
        object.__setattr__(self, "displaced_future_rank", None if self.displaced_future_rank is None else int(self.displaced_future_rank))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_SWAP_SCHEMA,
            "target_size": self.target_size,
            "pass_index": self.pass_index,
            "swap_index": self.swap_index,
            "rank": self.rank,
            "removed_frame_uid": self.removed_frame_uid,
            "replacement_frame_uid": self.replacement_frame_uid,
            "removed_unique_coverage": self.removed_unique_coverage,
            "removed_representative_loss": self.removed_representative_loss,
            "hard_deficit_before": self.hard_deficit_before,
            "hard_deficit_after": self.hard_deficit_after,
            "minimum_coverage_before": self.minimum_coverage_before,
            "minimum_coverage_after": self.minimum_coverage_after,
            "total_coverage_before": self.total_coverage_before,
            "total_coverage_after": self.total_coverage_after,
            "representative_utility_before": self.representative_utility_before,
            "representative_utility_after": self.representative_utility_after,
            "unit_balance_before": self.unit_balance_before,
            "unit_balance_after": self.unit_balance_after,
            "bottleneck_family_id": self.bottleneck_family_id,
            "displaced_future_rank": self.displaced_future_rank,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairSwap":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_SWAP_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-REPAIR1 swap schema.")
        return cls(
            target_size=int(payload["target_size"]),
            pass_index=int(payload["pass_index"]),
            swap_index=int(payload["swap_index"]),
            rank=int(payload["rank"]),
            removed_frame_uid=str(payload["removed_frame_uid"]),
            replacement_frame_uid=str(payload["replacement_frame_uid"]),
            removed_unique_coverage=float(payload["removed_unique_coverage"]),
            removed_representative_loss=float(payload["removed_representative_loss"]),
            hard_deficit_before=int(payload["hard_deficit_before"]),
            hard_deficit_after=int(payload["hard_deficit_after"]),
            minimum_coverage_before=float(payload["minimum_coverage_before"]),
            minimum_coverage_after=float(payload["minimum_coverage_after"]),
            total_coverage_before=float(payload["total_coverage_before"]),
            total_coverage_after=float(payload["total_coverage_after"]),
            representative_utility_before=float(payload["representative_utility_before"]),
            representative_utility_after=float(payload["representative_utility_after"]),
            unit_balance_before=int(payload["unit_balance_before"]),
            unit_balance_after=int(payload["unit_balance_after"]),
            bottleneck_family_id=str(payload["bottleneck_family_id"]),
            displaced_future_rank=None if payload.get("displaced_future_rank") is None else int(payload["displaced_future_rank"]),
        )


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairRung:
    target_size: int
    materializable: bool
    active_shell_start: int
    frame_uids: tuple[str, ...] = ()
    family_coverage: tuple[tuple[str, float], ...] = ()
    hard_obligations_passed: bool = False
    unsatisfied_obligation_ids: tuple[str, ...] = ()
    hard_coverage_qualified: bool = False
    swaps: tuple[TargetMultiViewRepairSwap, ...] = ()
    zero_unique_shell_fraction: float = 0.0
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        size = int(self.target_size)
        start = int(self.active_shell_start)
        if size < 1 or start < 0 or start > size:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 rung size/shell boundary is invalid.")
        uids = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        swaps = tuple(self.swaps)
        coverage = tuple((str(k), float(v)) for k, v in self.family_coverage)
        if self.materializable:
            if len(uids) != size or len(set(uids)) != size or self.unavailable_reason is not None:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 materializable rung identity is invalid.")
            if any(item.target_size != size or item.rank < start or item.rank >= size for item in swaps):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap escaped the active shell.")
        else:
            if uids or coverage or swaps or not self.unavailable_reason:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 unavailable rung payload is invalid.")
        if coverage and (
            tuple(sorted(k for k, _ in coverage)) != tuple(k for k, _ in coverage)
            or any(not np.isfinite(v) or v < -1e-12 or v > 1.0 + 1e-10 for _, v in coverage)
        ):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 rung coverage is invalid.")
        zero_fraction = float(self.zero_unique_shell_fraction)
        if not np.isfinite(zero_fraction) or zero_fraction < -1e-12 or zero_fraction > 1.0 + 1e-12:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 zero-unique shell fraction is invalid.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "active_shell_start", start)
        object.__setattr__(self, "frame_uids", uids)
        object.__setattr__(self, "family_coverage", coverage)
        object.__setattr__(self, "unsatisfied_obligation_ids", tuple(sorted(str(v) for v in self.unsatisfied_obligation_ids)))
        object.__setattr__(self, "swaps", swaps)
        object.__setattr__(self, "zero_unique_shell_fraction", min(1.0, max(0.0, zero_fraction)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_RUNG_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "active_shell_start": self.active_shell_start,
            "frame_uids": list(self.frame_uids),
            "family_coverage": [[k, v] for k, v in self.family_coverage],
            "hard_obligations_passed": self.hard_obligations_passed,
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "hard_coverage_qualified": self.hard_coverage_qualified,
            "swaps": [item.to_dict() for item in self.swaps],
            "zero_unique_shell_fraction": self.zero_unique_shell_fraction,
            "unavailable_reason": self.unavailable_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairRung":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-REPAIR1 rung schema.")
        return cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            active_shell_start=int(payload["active_shell_start"]),
            frame_uids=tuple(str(v) for v in payload.get("frame_uids", ())),
            family_coverage=tuple((str(v[0]), float(v[1])) for v in payload.get("family_coverage", ())),
            hard_obligations_passed=bool(payload.get("hard_obligations_passed", False)),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload.get("unsatisfied_obligation_ids", ())),
            hard_coverage_qualified=bool(payload.get("hard_coverage_qualified", False)),
            swaps=tuple(TargetMultiViewRepairSwap.from_dict(v) for v in payload.get("swaps", ())),
            zero_unique_shell_fraction=float(payload.get("zero_unique_shell_fraction", 0.0)),
            unavailable_reason=None if payload.get("unavailable_reason") is None else str(payload["unavailable_reason"]),
        )


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewRepairDomainPlan:
    label_domain_id: str
    reference_domain_digest: str
    sparse_domain_digest: str
    selection_domain_digest: str
    candidate_count: int
    repaired_master_order: tuple[str, ...]
    rungs: tuple[TargetMultiViewRepairRung, ...]
    total_swaps: int
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 domain label cannot be empty.")
        object.__setattr__(self, "reference_domain_digest", validate_digest(self.reference_domain_digest, name="reference_domain_digest"))
        object.__setattr__(self, "sparse_domain_digest", validate_digest(self.sparse_domain_digest, name="sparse_domain_digest"))
        object.__setattr__(self, "selection_domain_digest", validate_digest(self.selection_domain_digest, name="selection_domain_digest"))
        n = int(self.candidate_count)
        order = tuple(validate_digest(v, name="frame_uid") for v in self.repaired_master_order)
        if n < 1 or len(order) > n or len(set(order)) != len(order):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 repaired order is invalid.")
        rungs = tuple(self.rungs)
        if not rungs:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 domain requires planned rungs.")
        total_swaps = sum(len(item.swaps) for item in rungs)
        if int(self.total_swaps) != total_swaps:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 total swap count is inconsistent.")
        object.__setattr__(self, "candidate_count", n)
        object.__setattr__(self, "repaired_master_order", order)
        object.__setattr__(self, "rungs", rungs)
        object.__setattr__(self, "total_swaps", total_swaps)

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "sparse_domain_digest": self.sparse_domain_digest,
            "selection_domain_digest": self.selection_domain_digest,
            "candidate_count": self.candidate_count,
            "repaired_master_order": list(self.repaired_master_order),
            "rungs": [item.to_dict() for item in self.rungs],
            "total_swaps": self.total_swaps,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairDomainPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-REPAIR1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            sparse_domain_digest=str(payload["sparse_domain_digest"]),
            selection_domain_digest=str(payload["selection_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            repaired_master_order=tuple(str(v) for v in payload["repaired_master_order"]),
            rungs=tuple(TargetMultiViewRepairRung.from_dict(v) for v in payload["rungs"]),
            total_swaps=int(payload["total_swaps"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-REPAIR1 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewRepairPlan:
    dataset_id: str
    target_coverage_reference_digest: str
    target_coverage_sparse_index_digest: str
    target_multi_view_selection_digest: str
    policy: TargetMultiViewRepairPolicy
    domains: tuple[TargetMultiViewRepairDomainPlan, ...]
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_VERSION
    _domain_by_id: Mapping[str, TargetMultiViewRepairDomainPlan] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 dataset_id cannot be empty.")
        object.__setattr__(self, "target_coverage_reference_digest", validate_digest(self.target_coverage_reference_digest, name="target_coverage_reference_digest"))
        object.__setattr__(self, "target_coverage_sparse_index_digest", validate_digest(self.target_coverage_sparse_index_digest, name="target_coverage_sparse_index_digest"))
        object.__setattr__(self, "target_multi_view_selection_digest", validate_digest(self.target_multi_view_selection_digest, name="target_multi_view_selection_digest"))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 requires unique domains.")
        if self.authority_version != TARGET_MULTI_VIEW_REPAIR_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR1 plan authority version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewRepairDomainPlan:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_REPAIR_PLAN_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest": self.target_coverage_sparse_index_digest,
            "target_multi_view_selection_digest": self.target_multi_view_selection_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewRepairPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-REPAIR1 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_coverage_sparse_index_digest=str(payload["target_coverage_sparse_index_digest"]),
            target_multi_view_selection_digest=str(payload["target_multi_view_selection_digest"]),
            policy=TargetMultiViewRepairPolicy.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewRepairDomainPlan.from_dict(v) for v in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("domain_digests") not in (None, [item.content_digest for item in result.domains]):
            raise TrainingDataSerializationError("TARGET-DATA2C-REPAIR1 domain digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-REPAIR1 plan digest mismatch.")
        return result


def _increment_candidates_reference(array: np.ndarray, candidate_indices: np.ndarray, amount: float) -> None:
    if candidate_indices.size == 0 or amount == 0.0:
        return
    array[np.asarray(candidate_indices, dtype=np.int64)] += float(amount)


def _deselect_and_update_reference(candidate: int, sparse_domain: Any, state: Any) -> None:
    """Exact inverse of MVSEL1's sparse select update for one selected frame."""

    if state.available[candidate]:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 attempted to remove an unselected candidate.")
    for sparse_family, family_state in zip(sparse_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        for witness in witnesses:
            wi = int(witness)
            old_multiplicity = int(family_state.multiplicity[wi])
            if old_multiplicity < 1:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 witness multiplicity underflow.")
            covering = np.asarray(sparse_family.witness_candidate_indices(wi), dtype=np.int64)
            weight = float(family_state.weights[wi])
            # Before removal an unselected candidate would add weight/(n+1).
            # After removal it would add weight/n.
            representative_increment = weight / old_multiplicity - weight / (old_multiplicity + 1.0)
            _increment_candidates_reference(family_state.representative_gain, covering, representative_increment)
            _increment_candidates_reference(state.total_representative_gain, covering, representative_increment)
            new_multiplicity = old_multiplicity - 1
            family_state.multiplicity[wi] = new_multiplicity
            if new_multiplicity == 0:
                family_state.covered[wi] = False
                family_state.coverage_mass = max(0.0, float(family_state.coverage_mass) - weight)
                _increment_candidates_reference(family_state.coverage_gain, covering, weight)
                _increment_candidates_reference(state.total_coverage_gain, covering, weight)

    for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        oi_int = int(oi)
        obligation = sparse_domain.obligations[oi_int]
        if not obligation.required:
            continue
        before = int(state.obligation_counts[oi_int])
        if before < 1:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 hard-obligation count underflow.")
        after = before - 1
        state.obligation_counts[oi_int] = after
        minimum = int(obligation.minimum_selected_frames)
        if before >= minimum and after < minimum:
            candidates = np.asarray(sparse_domain.obligation_candidate_indices(oi_int), dtype=np.int64)
            state.hard_gain[candidates] += 1

    unit_code = int(sparse_domain.candidate_correlation_unit_codes[candidate])
    if int(state.unit_counts[unit_code]) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 correlation-unit count underflow.")
    state.unit_counts[unit_code] -= 1
    state.available[candidate] = True



def _scatter_increment_exact(
    array: np.ndarray,
    offsets: np.ndarray,
    indices: np.ndarray,
    witness_indices: np.ndarray,
    witness_amounts: np.ndarray,
) -> None:
    """MVPERF1 exact inverse-edge batched increment in witness order."""

    for rows, edge_amounts in _mvsel._iter_inverse_scatter_batches(
        offsets, indices, witness_indices, witness_amounts
    ):
        np.add.at(array, rows, edge_amounts)


def _deselect_and_update(candidate: int, sparse_domain: Any, state: Any) -> None:
    """MVPERF1 exact batched inverse of the frozen MVSEL1 selection update."""

    if state.available[candidate]:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 attempted to remove an unselected candidate.")
    for sparse_family, family_state in zip(sparse_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size:
            old_values = np.asarray([int(family_state.multiplicity[int(w)]) for w in witnesses], dtype=np.int64)
            if np.any(old_values < 1):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 witness multiplicity underflow.")
            representative_amounts = np.asarray([
                float(family_state.weights[int(w)]) / int(old_n)
                - float(family_state.weights[int(w)]) / (int(old_n) + 1.0)
                for w, old_n in zip(witnesses, old_values, strict=True)
            ], dtype=np.float64)
            _scatter_increment_exact(
                family_state.representative_gain,
                sparse_family.witness_offsets,
                sparse_family.witness_candidates,
                witnesses,
                representative_amounts,
            )
            _scatter_increment_exact(
                state.total_representative_gain,
                sparse_family.witness_offsets,
                sparse_family.witness_candidates,
                witnesses,
                representative_amounts,
            )
            new_values = old_values - 1
            family_state.multiplicity[witnesses] = new_values.astype(family_state.multiplicity.dtype, copy=False)
            uncovered = witnesses[new_values == 0]
            if uncovered.size:
                coverage_amounts = np.asarray(
                    [float(family_state.weights[int(w)]) for w in uncovered], dtype=np.float64
                )
                family_state.covered[uncovered] = False
                # Reference code subtracts each newly uncovered witness weight
                # in witness order from coverage_mass. Preserve that scalar order.
                for amount in coverage_amounts:
                    family_state.coverage_mass = max(0.0, float(family_state.coverage_mass) - float(amount))
                _scatter_increment_exact(
                    family_state.coverage_gain,
                    sparse_family.witness_offsets,
                    sparse_family.witness_candidates,
                    uncovered,
                    coverage_amounts,
                )
                _scatter_increment_exact(
                    state.total_coverage_gain,
                    sparse_family.witness_offsets,
                    sparse_family.witness_candidates,
                    uncovered,
                    coverage_amounts,
                )

    for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        oi_int = int(oi)
        obligation = sparse_domain.obligations[oi_int]
        if not obligation.required:
            continue
        before = int(state.obligation_counts[oi_int])
        if before < 1:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 hard-obligation count underflow.")
        after = before - 1
        state.obligation_counts[oi_int] = after
        minimum = int(obligation.minimum_selected_frames)
        if before >= minimum and after < minimum:
            candidates = np.asarray(sparse_domain.obligation_candidate_indices(oi_int), dtype=np.int64)
            state.hard_gain[candidates] += 1

    unit_code = int(sparse_domain.candidate_correlation_unit_codes[candidate])
    if int(state.unit_counts[unit_code]) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 correlation-unit count underflow.")
    state.unit_counts[unit_code] -= 1
    state.available[candidate] = True

def _hard_deficit(sparse_domain: Any, state: Any) -> int:
    return int(sum(
        max(0, int(item.minimum_selected_frames) - int(state.obligation_counts[oi]))
        for oi, item in enumerate(sparse_domain.obligations)
        if item.required
    ))


def _unit_balance(state: Any) -> int:
    # Higher is better.  Negative sum-of-squares penalizes concentration while
    # remaining an exact integer tie-break.
    values = np.asarray(state.unit_counts, dtype=np.int64)
    return -int(np.dot(values, values))


def _representative_utility(reference_domain: Any, state: Any) -> float:
    total = 0.0
    for family_state in state.family_states:
        multiplicity = np.asarray(family_state.multiplicity, dtype=np.int64)
        if multiplicity.size == 0:
            continue
        max_n = int(np.max(multiplicity))
        harmonic = np.zeros(max_n + 1, dtype=np.float64)
        if max_n:
            harmonic[1:] = np.cumsum(1.0 / np.arange(1, max_n + 1, dtype=np.float64), dtype=np.float64)
        total += float(np.sum(family_state.weights * harmonic[multiplicity], dtype=np.float64))
    return total


def _candidate_removal_metrics(candidate: int, sparse_domain: Any, state: Any) -> tuple[float, float]:
    """Return exact unique coverage and representative removal loss in one CSR pass."""

    unique_total = 0.0
    loss_total = 0.0
    for sparse_family, family_state in zip(sparse_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(sparse_family.candidate_witness_indices(candidate), dtype=np.int64)
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64, copy=False)
        if np.any(multiplicity < 1.0):
            raise TrainingDataInputError(
                "TARGET-DATA2C-REPAIR1 removal loss observed an uncovered selected witness."
            )
        weights = family_state.weights[witnesses]
        unique_mask = multiplicity == 1.0
        if np.any(unique_mask):
            unique_total += float(np.sum(weights[unique_mask], dtype=np.float64))
        loss_total += float(np.sum(weights / multiplicity, dtype=np.float64))
    return unique_total, loss_total


def _candidate_unique_coverage(candidate: int, sparse_domain: Any, state: Any) -> float:
    # Retained public-private helper for exact REPAIR1/MVPERF qualification.
    return _candidate_removal_metrics(candidate, sparse_domain, state)[0]


def _candidate_representative_removal_loss(candidate: int, sparse_domain: Any, state: Any) -> float:
    # Retained public-private helper for exact REPAIR1/MVPERF qualification.
    return _candidate_removal_metrics(candidate, sparse_domain, state)[1]


def _candidate_removal_is_hard_safe(candidate: int, sparse_domain: Any, state: Any) -> bool:
    for oi in np.asarray(sparse_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        oi_int = int(oi)
        obligation = sparse_domain.obligations[oi_int]
        if not obligation.required:
            continue
        before = int(state.obligation_counts[oi_int])
        before_deficit = max(0, int(obligation.minimum_selected_frames) - before)
        after_deficit = max(0, int(obligation.minimum_selected_frames) - (before - 1))
        if after_deficit > before_deficit:
            return False
    return True


def _shell_removal_scan(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    order_indices: Sequence[int],
    shell_start: int,
    target_size: int,
    policy: TargetMultiViewRepairPolicy,
) -> tuple[int, tuple[tuple[int, int, float, float], ...]]:
    """One exact shell pass for zero-unique telemetry and removal shortlist.

    REPAIR1 previously traversed every selected witness twice before the first
    swap attempt: once for telemetry and again for the shortlist. MVPERF1
    combines those scientifically identical queries.
    """
    zero_unique_count = 0
    rows: list[tuple[int, int, float, float]] = []
    for rank in range(shell_start, target_size):
        candidate = int(order_indices[rank])
        unique, loss = _candidate_removal_metrics(candidate, sparse_domain, state)
        if unique > policy.unique_coverage_tolerance:
            continue
        zero_unique_count += 1
        if not _candidate_removal_is_hard_safe(candidate, sparse_domain, state):
            continue
        rows.append((rank, candidate, unique, loss))
    rows.sort(key=lambda item: (
        item[3],
        -int(state.unit_counts[int(sparse_domain.candidate_correlation_unit_codes[item[1]])]),
        reference_domain.frame_uids[item[1]],
    ))
    return zero_unique_count, tuple(rows[: policy.removal_shortlist_limit])


def _shell_zero_unique_count(
    sparse_domain: Any,
    state: Any,
    order_indices: Sequence[int],
    shell_start: int,
    target_size: int,
    policy: TargetMultiViewRepairPolicy,
) -> int:
    count = 0
    for rank in range(shell_start, target_size):
        candidate = int(order_indices[rank])
        if _candidate_unique_coverage(candidate, sparse_domain, state) <= policy.unique_coverage_tolerance:
            count += 1
    return count


def _removal_shortlist(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    order_indices: Sequence[int],
    shell_start: int,
    target_size: int,
    policy: TargetMultiViewRepairPolicy,
) -> tuple[tuple[int, int, float, float], ...]:
    return _shell_removal_scan(
        reference_domain, sparse_domain, state, order_indices, shell_start, target_size, policy
    )[1]

def _coverage_objective(state: Any) -> tuple[float, float]:
    values = np.asarray([float(item.coverage_mass) for item in state.family_states], dtype=np.float64)
    return float(np.min(values)), float(np.sum(values, dtype=np.float64))


def _pair_specific_representative_gain(
    replacement: int,
    removed: int,
    sparse_domain: Any,
    state: Any,
    *,
    proposal_scratch: _RepairProposalScratch | None = None,
) -> float:
    total = float(state.total_representative_gain[replacement])
    # Removing a zero-unique frame decreases multiplicity n -> n-1 on its
    # witnesses. For replacement candidates sharing such a witness, the
    # add-gain changes from w/(n+1) to w/n. REPAIR-PAR1 uses thread-private
    # epoch/stamp membership to avoid allocating a sorted intersection for each
    # replacement while preserving the same witness order in the FP64 sum.
    for family_index, (sparse_family, family_state) in enumerate(
        zip(sparse_domain.families, state.family_states, strict=True)
    ):
        replacement_w = np.asarray(sparse_family.candidate_witness_indices(replacement), dtype=np.int64)
        if replacement_w.size == 0:
            continue
        if proposal_scratch is None:
            removed_w = np.asarray(sparse_family.candidate_witness_indices(removed), dtype=np.int64)
            if removed_w.size == 0:
                continue
            shared = np.intersect1d(removed_w, replacement_w, assume_unique=True)
        else:
            shared = replacement_w[proposal_scratch.shared_mask(family_index, replacement_w)]
        if shared.size == 0:
            continue
        n = family_state.multiplicity[shared].astype(np.float64, copy=False)
        if np.any(n < 2.0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 zero-unique removal invariant failed.")
        weights = family_state.weights[shared]
        total += float(np.sum(weights * (1.0 / n - 1.0 / (n + 1.0)), dtype=np.float64))
    return total


def _pair_specific_diversity(
    replacement: int,
    removed: int,
    sparse_domain: Any,
    state: Any,
    *,
    proposal_scratch: _RepairProposalScratch | None = None,
) -> float:
    values: list[float] = []
    for family_index, (sparse_family, family_state) in enumerate(
        zip(sparse_domain.families, state.family_states, strict=True)
    ):
        witnesses = np.asarray(sparse_family.candidate_witness_indices(replacement), dtype=np.int64)
        if witnesses.size == 0:
            continue
        multiplicity = family_state.multiplicity[witnesses].astype(np.int64, copy=True)
        if proposal_scratch is None:
            removed_w = np.asarray(sparse_family.candidate_witness_indices(removed), dtype=np.int64)
            if removed_w.size:
                shared_mask = np.isin(witnesses, removed_w, assume_unique=True)
                multiplicity[shared_mask] -= 1
        else:
            shared_mask = proposal_scratch.shared_mask(family_index, witnesses)
            if np.any(shared_mask):
                multiplicity[shared_mask] -= 1
        if np.any(multiplicity < 0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 diversity multiplicity underflow.")
        values.append(float(np.mean(1.0 / (1.0 + multiplicity), dtype=np.float64)))
    return 0.0 if not values else float(np.mean(values, dtype=np.float64))


def _segment_row_sums(values: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    """Return one FP64 sum per complete gathered CSR row."""

    lengths = np.asarray(lengths, dtype=np.int64)
    result = np.zeros(lengths.size, dtype=np.float64)
    if lengths.size == 0 or values.size == 0:
        return result
    ends = np.cumsum(lengths, dtype=np.int64)
    starts = ends - lengths
    nonzero = lengths > 0
    if np.any(nonzero):
        # reduceat starts each non-empty row at its canonical first edge and the
        # next non-empty start is exactly the previous row end, even across
        # intervening zero-length rows.
        result[nonzero] = np.add.reduceat(
            np.asarray(values, dtype=np.float64), starts[nonzero]
        )
    return result


def _frontier_representative_gain_vectorized(
    frontier: np.ndarray,
    removed: int,
    sparse_domain: Any,
    state: Any,
    proposal_scratch: _RepairProposalScratch,
) -> np.ndarray:
    values = np.asarray(state.total_representative_gain[frontier], dtype=np.float64).copy()
    for family_index, (sparse_family, family_state) in enumerate(
        zip(sparse_domain.families, state.family_states, strict=True)
    ):
        if not hasattr(sparse_family, "candidate_offsets"):
            return np.asarray([
                _pair_specific_representative_gain(
                    int(candidate), removed, sparse_domain, state, proposal_scratch=proposal_scratch
                )
                for candidate in frontier
            ], dtype=np.float64)
        witnesses, lengths = csr_gather_rows(
            sparse_family.candidate_offsets, sparse_family.candidate_witnesses, frontier
        )
        if witnesses.size == 0:
            continue
        wi = witnesses.astype(np.int64, copy=False)
        shared = proposal_scratch.shared_mask(family_index, wi)
        if not np.any(shared):
            continue
        multiplicity = family_state.multiplicity[wi].astype(np.float64, copy=False)
        if np.any(multiplicity[shared] < 2.0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 zero-unique removal invariant failed.")
        edge_values = np.zeros(wi.size, dtype=np.float64)
        n = multiplicity[shared]
        edge_values[shared] = family_state.weights[wi[shared]] * (1.0 / n - 1.0 / (n + 1.0))
        values += _segment_row_sums(edge_values, lengths)
    return values


def _frontier_diversity_vectorized(
    frontier: np.ndarray,
    sparse_domain: Any,
    state: Any,
    proposal_scratch: _RepairProposalScratch,
) -> np.ndarray:
    totals = np.zeros(frontier.size, dtype=np.float64)
    counts = np.zeros(frontier.size, dtype=np.int64)
    for family_index, (sparse_family, family_state) in enumerate(
        zip(sparse_domain.families, state.family_states, strict=True)
    ):
        if not hasattr(sparse_family, "candidate_offsets"):
            return np.asarray([
                _pair_specific_diversity(
                    int(candidate), -1, sparse_domain, state, proposal_scratch=proposal_scratch
                )
                for candidate in frontier
            ], dtype=np.float64)
        witnesses, lengths = csr_gather_rows(
            sparse_family.candidate_offsets, sparse_family.candidate_witnesses, frontier
        )
        nonzero = lengths > 0
        if witnesses.size == 0 or not np.any(nonzero):
            continue
        wi = witnesses.astype(np.int64, copy=False)
        multiplicity = family_state.multiplicity[wi].astype(np.int64, copy=True)
        shared = proposal_scratch.shared_mask(family_index, wi)
        if np.any(shared):
            multiplicity[shared] -= 1
        if np.any(multiplicity < 0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 diversity multiplicity underflow.")
        row_sums = _segment_row_sums(1.0 / (1.0 + multiplicity), lengths)
        totals[nonzero] += row_sums[nonzero] / lengths[nonzero].astype(np.float64)
        counts[nonzero] += 1
    result = np.zeros(frontier.size, dtype=np.float64)
    active = counts > 0
    result[active] = totals[active] / counts[active].astype(np.float64)
    return result


def _replacement_frontier(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    removed: int,
    policy: TargetMultiViewRepairPolicy,
) -> np.ndarray:
    candidates = np.flatnonzero(state.available)
    # The removed frame is selected in the current state, so it is already not
    # available.  Keep it excluded explicitly for clarity if callers change.
    candidates = candidates[candidates != int(removed)]
    if candidates.size == 0:
        return candidates
    tol = policy.gain_tie_tolerance
    hard_pending = _hard_deficit(sparse_domain, state) > 0
    if hard_pending:
        best = int(np.max(state.hard_gain[candidates]))
        candidates = candidates[state.hard_gain[candidates] == best]
    coverage_values = np.asarray([float(item.coverage_mass) for item in state.family_states], dtype=np.float64)
    bottleneck_index = int(np.flatnonzero(coverage_values <= float(np.min(coverage_values)) + tol)[0])
    candidates = _mvsel._filter_best(state.family_states[bottleneck_index].coverage_gain, candidates, tol)
    candidates = _mvsel._filter_best(state.total_coverage_gain, candidates, tol)
    # Deficit-directed repair stops if no hard deficit and no uncovered mass can
    # be improved.  Phase-B density optimization already belongs to MVSEL1.
    if not hard_pending and candidates.size and float(np.max(state.total_coverage_gain[candidates])) <= tol:
        return np.empty(0, dtype=np.int64)
    return candidates


def _strictly_better(
    before: tuple[int, float, float, float, int],
    after: tuple[int, float, float, float, int],
    tolerance: float,
) -> bool:
    # hard deficit is minimized; all following values are maximized.
    if after[0] < before[0]:
        return True
    if after[0] > before[0]:
        return False
    for b, a in zip(before[1:4], after[1:4], strict=True):
        if a > b + tolerance:
            return True
        if a < b - tolerance:
            return False
    return after[4] > before[4]


def _candidate_swap(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    removal: tuple[int, int, float, float],
    representative_utility: float,
    policy: TargetMultiViewRepairPolicy,
    *,
    proposal_scratch: _RepairProposalScratch | None = None,
) -> dict[str, Any] | None:
    rank, removed, unique, removal_loss = removal
    frontier = _replacement_frontier(reference_domain, sparse_domain, state, removed, policy)
    if frontier.size == 0:
        return None
    tol = policy.gain_tie_tolerance
    hard_before = _hard_deficit(sparse_domain, state)
    min_before, total_before = _coverage_objective(state)
    balance_before = _unit_balance(state)
    removed_unit = int(sparse_domain.candidate_correlation_unit_codes[removed])

    # Hard and coverage gains are unchanged by removal because only exact
    # zero-unique, hard-safe removals are admitted.  Narrow to the scientific
    # frontier before evaluating pair-specific representative overlap.
    if hard_before > 0:
        best_hard = int(np.max(state.hard_gain[frontier]))
        frontier = frontier[state.hard_gain[frontier] == best_hard]
    coverage_values = np.asarray([float(item.coverage_mass) for item in state.family_states], dtype=np.float64)
    bottleneck_index = int(np.flatnonzero(coverage_values <= float(np.min(coverage_values)) + tol)[0])
    frontier = _mvsel._filter_best(state.family_states[bottleneck_index].coverage_gain, frontier, tol)
    frontier = _mvsel._filter_best(state.total_coverage_gain, frontier, tol)

    # Provenance balance is evaluated after the hypothetical removal.
    if frontier.size > 1:
        replacement_units = np.asarray(sparse_domain.candidate_correlation_unit_codes[frontier], dtype=np.int64)
        counts = state.unit_counts[replacement_units].astype(np.int64, copy=True)
        counts[replacement_units == removed_unit] -= 1
        minimum = int(np.min(counts))
        frontier = frontier[counts == minimum]

    if proposal_scratch is None:
        rep_values = np.asarray([
            _pair_specific_representative_gain(
                int(candidate), removed, sparse_domain, state
            )
            for candidate in frontier
        ], dtype=np.float64)
    else:
        rep_values = _frontier_representative_gain_vectorized(
            frontier, removed, sparse_domain, state, proposal_scratch
        )
    if frontier.size > 1:
        best_rep = float(np.max(rep_values))
        keep = rep_values >= best_rep - tol
        frontier = frontier[keep]
        rep_values = rep_values[keep]

    if proposal_scratch is None:
        diversity_values = np.asarray([
            _pair_specific_diversity(int(candidate), removed, sparse_domain, state)
            for candidate in frontier
        ], dtype=np.float64)
    else:
        diversity_values = _frontier_diversity_vectorized(
            frontier, sparse_domain, state, proposal_scratch
        )
    if frontier.size > 1:
        best_div = float(np.max(diversity_values))
        keep = diversity_values >= best_div - tol
        frontier = frontier[keep]
        rep_values = rep_values[keep]
        diversity_values = diversity_values[keep]

    replacement = min((int(v) for v in frontier), key=lambda c: reference_domain.frame_uids[c])
    local = int(np.flatnonzero(frontier == replacement)[0])
    replacement_rep_gain = float(rep_values[local])
    if proposal_scratch is not None:
        # Persist the exact historical scalar arithmetic for the winning pair.
        # The vector kernel is execution-only shortlist evaluation.
        replacement_rep_gain = _pair_specific_representative_gain(
            replacement, removed, sparse_domain, state, proposal_scratch=proposal_scratch
        )

    hard_after = max(0, hard_before - int(state.hard_gain[replacement]))
    coverage_after = [
        min(1.0, float(item.coverage_mass) + float(item.coverage_gain[replacement]))
        for item in state.family_states
    ]
    min_after = float(min(coverage_after))
    total_after = float(sum(coverage_after))
    rep_after = float(representative_utility - removal_loss + replacement_rep_gain)
    replacement_unit = int(sparse_domain.candidate_correlation_unit_codes[replacement])
    if replacement_unit == removed_unit:
        balance_after = balance_before
    else:
        cr = int(state.unit_counts[removed_unit])
        ca = int(state.unit_counts[replacement_unit])
        balance_after = balance_before + 2 * (cr - ca - 1)

    before_objective = (hard_before, min_before, total_before, representative_utility, balance_before)
    after_objective = (hard_after, min_after, total_after, rep_after, balance_after)
    if policy.strict_no_coverage_regression:
        for family_state, value_after in zip(state.family_states, coverage_after, strict=True):
            if value_after + tol < float(family_state.coverage_mass):
                return None
    if not _strictly_better(before_objective, after_objective, tol):
        return None
    return {
        "rank": rank,
        "removed": removed,
        "replacement": replacement,
        "unique": unique,
        "removal_loss": removal_loss,
        "hard_before": hard_before,
        "hard_after": hard_after,
        "min_before": min_before,
        "min_after": min_after,
        "total_before": total_before,
        "total_after": total_after,
        "rep_before": representative_utility,
        "rep_after": rep_after,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "bottleneck_family_id": state.family_states[bottleneck_index].family_id,
        "objective": after_objective,
        "removed_uid": reference_domain.frame_uids[removed],
        "replacement_uid": reference_domain.frame_uids[replacement],
    }


def _proposal_worker_scope(resource_scope: StageResourceScope | None, workers: int) -> StageResourceScope:
    workers = max(1, int(workers))
    if resource_scope is None:
        return _repair_parallel_scope(workers)
    if int(resource_scope.python_workers) < workers:
        raise TrainingDataInputError(
            "TARGET-DATA2C-REPAIR-PAR1 resource scope has fewer Python workers than requested."
        )
    return StageResourceScope(
        stage_name=resource_scope.stage_name,
        cpu_threads_available=resource_scope.cpu_threads_available,
        cpu_threads_budget=resource_scope.cpu_threads_budget,
        python_workers=workers,
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        pytorch_cpu_workers=1,
        gpu_jobs=resource_scope.gpu_jobs,
        ram_budget_bytes=resource_scope.ram_budget_bytes,
    )


def _best_repair_proposal(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    removals: Sequence[tuple[int, int, float, float]],
    representative_utility: float,
    policy: TargetMultiViewRepairPolicy,
    *,
    proposal_workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    optimized: bool = True,
    proposal_queue: DeterministicWorkQueue | None = None,
    proposal_batch_id: int = 0,
) -> dict[str, Any] | None:
    """Evaluate immutable removal proposals and reduce in canonical REPAIR1 order.

    The state is read-only for the entire call.  Arbitrary worker completion is
    therefore execution-only; proposals are reduced in exactly the historical
    shortlist order with ``_better_swap`` before any state mutation occurs.
    """

    removals = tuple(removals)
    if not removals:
        return None
    if not optimized:
        best: dict[str, Any] | None = None
        for removal in removals:
            proposal = _candidate_swap(
                reference_domain, sparse_domain, state, removal, representative_utility, policy
            )
            if proposal is not None:
                best = _better_swap(best, proposal, policy.gain_tie_tolerance)
        return best
    workers = max(1, min(int(proposal_workers), len(removals)))
    # Thread launch/synchronization is counterproductive for small frontiers.
    # Estimate immutable sparse edge work and keep those iterations serial;
    # large 8k-16k candidate rungs expose enough NumPy work for PARCORE1 lanes.
    edge_count = sum(
        int(getattr(family, "edge_count", len(getattr(family, "candidate_witnesses", ()))))
        for family in sparse_domain.families
    )
    if workers > 1 and len(removals) * max(1, edge_count) < _REPAIR_PARALLEL_EDGE_WORK_THRESHOLD:
        workers = 1
    thread_scratch = local()

    def evaluate(removal: tuple[int, int, float, float]) -> dict[str, Any] | None:
        scratch = getattr(thread_scratch, "repair_scratch", None)
        if scratch is None:
            scratch = _RepairProposalScratch(sparse_domain)
            thread_scratch.repair_scratch = scratch
        scratch.mark_removed(sparse_domain, int(removal[1]))
        return _candidate_swap(
            reference_domain,
            sparse_domain,
            state,
            removal,
            representative_utility,
            policy,
            proposal_scratch=scratch,
        )

    if workers == 1:
        best: dict[str, Any] | None = None
        for removal in removals:
            proposal = evaluate(removal)
            if proposal is not None:
                best = _better_swap(best, proposal, policy.gain_tie_tolerance)
        return best

    scope = _proposal_worker_scope(resource_scope, workers)
    results: dict[int, dict[str, Any] | None] = {}
    scratch_bytes = workers * sum(int(family.witness_count) * np.dtype(np.uint32).itemsize for family in sparse_domain.families)
    max_family_edges = max(
        (int(getattr(family, "edge_count", len(getattr(family, "candidate_witnesses", ())))) for family in sparse_domain.families),
        default=0,
    )
    per_task_memory = max(1, max_family_edges * 48 + int(sparse_domain.candidate_count) * 64)
    owned_queue = proposal_queue is None
    queue_context = DeterministicWorkQueue(
        scope,
        max_ready_tasks=max(len(removals), 2 * workers),
        max_inflight_tasks=max(1, 2 * workers),
        max_completed_tasks=max(1, 2 * workers),
        heartbeat_interval_seconds=30.0,
        thread_name_prefix="mdstats-repair-par1",
    ) if owned_queue else nullcontext(proposal_queue)
    with queue_context as queue:
        assert queue is not None
        memory_key = f"repair-proposal-thread-stamps-{int(proposal_batch_id):06d}"
        if scratch_bytes:
            queue.reserve_memory(memory_key, scratch_bytes)
        finished_before = int(queue.snapshot().finished_tasks)
        for position, removal in enumerate(removals):
            queue.submit(
                task_id=f"repair-proposal-b{int(proposal_batch_id):06d}-{position:04d}-rank-{int(removal[0]):08d}",
                canonical_order=(position,),
                function=evaluate,
                args=(removal,),
                task_kind="repair-proposal",
                estimated_memory_bytes=per_task_memory,
                locality_key=f"{reference_domain.label_domain_id}:repair",
            )
        expected = len(removals)
        while int(queue.snapshot().finished_tasks) < finished_before + expected:
            queue.wait_for_completion()
            for completion in queue.drain_completed():
                results[int(completion.canonical_order[0])] = completion.value
        for completion in queue.drain_completed():
            results[int(completion.canonical_order[0])] = completion.value
        if scratch_bytes:
            queue.release_memory(memory_key)

    best = None
    for position in range(len(removals)):
        proposal = results[position]
        if proposal is not None:
            best = _better_swap(best, proposal, policy.gain_tie_tolerance)
    return best


def _better_swap(left: dict[str, Any] | None, right: dict[str, Any], tolerance: float) -> dict[str, Any]:
    if left is None:
        return right
    if _strictly_better(left["objective"], right["objective"], tolerance):
        return right
    if _strictly_better(right["objective"], left["objective"], tolerance):
        return left
    # Same scientific objective: lower representative removal loss, then stable
    # removed/replacement UIDs yield deterministic bounded-search behavior.
    left_key = (left["removal_loss"], left["rank"], left["removed_uid"], left["replacement_uid"])
    right_key = (right["removal_loss"], right["rank"], right["removed_uid"], right["replacement_uid"])
    return left if left_key <= right_key else right


def _apply_swap(
    order_indices: list[int],
    state: Any,
    sparse_domain: Any,
    repair: dict[str, Any],
    representative_utility: float,
    target_size: int,
    *,
    rank_by_candidate: np.ndarray | None = None,
    deselect_function: Any = _deselect_and_update,
    select_function: Any = _mvsel._select_and_update,
) -> tuple[float, int | None]:
    rank = int(repair["rank"])
    removed = int(repair["removed"])
    replacement = int(repair["replacement"])
    if order_indices[rank] != removed:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 removal rank no longer matches the active order.")
    deselect_function(removed, sparse_domain, state)
    representative_utility -= float(repair["removal_loss"])
    add_gain = float(state.total_representative_gain[replacement])
    expected_add = float(repair["rep_after"] - representative_utility)
    if not math.isclose(add_gain, expected_add, rel_tol=0.0, abs_tol=5.0e-12):
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 analytic replacement gain disagrees with incremental sparse state.")
    if not state.available[replacement]:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 replacement is already selected.")
    select_function(replacement, sparse_domain, state)
    representative_utility += add_gain

    displaced_rank: int | None = None
    if rank_by_candidate is None:
        try:
            future_rank = order_indices.index(replacement, target_size)
        except ValueError:
            future_rank = -1
    else:
        future_rank = int(rank_by_candidate[replacement])
    if future_rank >= target_size:
        order_indices[future_rank] = removed
        displaced_rank = future_rank
        if rank_by_candidate is not None:
            rank_by_candidate[removed] = future_rank
    elif rank_by_candidate is not None:
        rank_by_candidate[removed] = -1
    order_indices[rank] = replacement
    if rank_by_candidate is not None:
        rank_by_candidate[replacement] = rank
    return representative_utility, displaced_rank


def _rung_evidence(
    reference_domain: Any,
    sparse_domain: Any,
    state: Any,
    order_indices: Sequence[int],
    target_size: int,
    shell_start: int,
    swaps: Sequence[TargetMultiViewRepairSwap],
    zero_unique_fraction: float,
    coverage_threshold: float,
    tolerance: float,
) -> TargetMultiViewRepairRung:
    unsatisfied = _mvsel._unsatisfied_required_obligations(sparse_domain, state)
    coverage = tuple(sorted((item.family_id, min(1.0, max(0.0, float(item.coverage_mass)))) for item in state.family_states))
    hard_pass = not unsatisfied
    coverage_pass = all(value >= coverage_threshold - tolerance for _, value in coverage)
    return TargetMultiViewRepairRung(
        target_size=target_size,
        materializable=True,
        active_shell_start=shell_start,
        frame_uids=tuple(reference_domain.frame_uids[int(v)] for v in order_indices[:target_size]),
        family_coverage=coverage,
        hard_obligations_passed=hard_pass,
        unsatisfied_obligation_ids=unsatisfied,
        hard_coverage_qualified=bool(hard_pass and coverage_pass),
        swaps=tuple(swaps),
        zero_unique_shell_fraction=zero_unique_fraction,
    )


def _build_domain_repair(
    reference_domain: Any,
    sparse_domain: Any,
    selection_domain: Any,
    selector_policy: Any,
    policy: TargetMultiViewRepairPolicy,
    *,
    progress_callback: Any = None,
    select_function: Any = _mvsel._select_and_update,
    deselect_function: Any = _deselect_and_update,
    proposal_workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    proposal_optimized: bool = True,
    selection_state_domain_cache: Any | None = None,
) -> TargetMultiViewRepairDomainPlan:
    if reference_domain.content_digest != selection_domain.reference_domain_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 reference/MVSEL domain lineage mismatch.")
    if sparse_domain.content_digest != selection_domain.sparse_domain_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 MVIDX/MVSEL domain lineage mismatch.")
    uid_to_candidate = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
    order_indices = [uid_to_candidate[item.frame_uid] for item in selection_domain.master_order]
    if len(set(order_indices)) != len(order_indices):
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 MVSEL order is not unique.")
    rank_by_candidate = np.full(int(sparse_domain.candidate_count), -1, dtype=np.int64)
    if order_indices:
        rank_by_candidate[np.asarray(order_indices, dtype=np.int64)] = np.arange(len(order_indices), dtype=np.int64)

    state = None
    representative_utility = 0.0
    previous_size = 0
    rungs: list[TargetMultiViewRepairRung] = []
    repair_has_diverged = False
    proposal_batch_id = 0

    queue_context: Any = nullcontext(None)
    if proposal_optimized and int(proposal_workers) > 1:
        scope = _proposal_worker_scope(resource_scope, int(proposal_workers))
        queue_context = DeterministicWorkQueue(
            scope,
            max_ready_tasks=max(int(policy.removal_shortlist_limit), 2 * int(proposal_workers)),
            max_inflight_tasks=max(1, 2 * int(proposal_workers)),
            max_completed_tasks=max(1, 2 * int(proposal_workers)),
            heartbeat_interval_seconds=30.0,
            thread_name_prefix="mdstats-repair-par1",
        )

    with queue_context as shared_proposal_queue:
        for base_rung in selection_domain.rungs:
            size = int(base_rung.target_size)
            if not base_rung.materializable:
                rungs.append(TargetMultiViewRepairRung(
                    target_size=size,
                    materializable=False,
                    active_shell_start=previous_size,
                    unavailable_reason=base_rung.unavailable_reason or "unavailable_in_mvsel1",
                ))
                continue

            checkpoint_used = False
            if selection_state_domain_cache is not None and not repair_has_diverged:
                try:
                    checkpoint = selection_state_domain_cache.checkpoint(size)
                except KeyError:
                    checkpoint = None
                if checkpoint is not None:
                    state = restore_domain_state(checkpoint, reference_domain, sparse_domain)
                    representative_utility = float(checkpoint.representative_utility)
                    checkpoint_used = True

            if not checkpoint_used:
                if state is None:
                    state = _mvsel._build_domain_state(reference_domain, sparse_domain)
                    representative_utility = 0.0
                    replay_start = 0
                else:
                    replay_start = previous_size
                replay_candidates = order_indices[replay_start:size]
                if select_function is _mvsel._select_and_update and replay_candidates:
                    representative_utility = _mvsel._select_many_and_update_exact(
                        replay_candidates, sparse_domain, state, representative_utility
                    )
                else:
                    for rank in range(replay_start, size):
                        candidate = int(order_indices[rank])
                        if not state.available[candidate]:
                            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 repaired order contains an already-selected candidate.")
                        representative_utility += float(state.total_representative_gain[candidate])
                        select_function(candidate, sparse_domain, state)

            assert state is not None
            shell_size = size - previous_size
            zero_unique_count, first_removals = _shell_removal_scan(
                reference_domain, sparse_domain, state, order_indices, previous_size, size, policy
            )
            zero_unique_fraction = 0.0 if shell_size == 0 else min(1.0, zero_unique_count / float(shell_size))
            accepted: list[TargetMultiViewRepairSwap] = []
            swap_index = 0
            pending_removals: tuple[tuple[int, int, float, float], ...] | None = first_removals
            for pass_index in range(policy.max_passes_per_shell):
                changed = False
                while len(accepted) < policy.max_swaps_per_shell:
                    if pending_removals is None:
                        removals = _removal_shortlist(
                            reference_domain, sparse_domain, state, order_indices, previous_size, size, policy
                        )
                    else:
                        removals = pending_removals
                        pending_removals = None
                    if not removals:
                        break
                    best = _best_repair_proposal(
                        reference_domain,
                        sparse_domain,
                        state,
                        removals,
                        representative_utility,
                        policy,
                        proposal_workers=proposal_workers,
                        resource_scope=resource_scope,
                        optimized=proposal_optimized,
                        proposal_queue=shared_proposal_queue,
                        proposal_batch_id=proposal_batch_id,
                    )
                    proposal_batch_id += 1
                    if best is None:
                        break
                    removed_uid = reference_domain.frame_uids[int(best["removed"])]
                    replacement_uid = reference_domain.frame_uids[int(best["replacement"])]
                    representative_utility, displaced_rank = _apply_swap(
                        order_indices, state, sparse_domain, best, representative_utility, size,
                        rank_by_candidate=rank_by_candidate,
                        deselect_function=deselect_function, select_function=select_function,
                    )
                    accepted.append(TargetMultiViewRepairSwap(
                        target_size=size,
                        pass_index=pass_index,
                        swap_index=swap_index,
                        rank=int(best["rank"]),
                        removed_frame_uid=removed_uid,
                        replacement_frame_uid=replacement_uid,
                        removed_unique_coverage=float(best["unique"]),
                        removed_representative_loss=float(best["removal_loss"]),
                        hard_deficit_before=int(best["hard_before"]),
                        hard_deficit_after=int(best["hard_after"]),
                        minimum_coverage_before=float(best["min_before"]),
                        minimum_coverage_after=float(best["min_after"]),
                        total_coverage_before=float(best["total_before"]),
                        total_coverage_after=float(best["total_after"]),
                        representative_utility_before=float(best["rep_before"]),
                        representative_utility_after=float(best["rep_after"]),
                        unit_balance_before=int(best["balance_before"]),
                        unit_balance_after=int(best["balance_after"]),
                        bottleneck_family_id=str(best["bottleneck_family_id"]),
                        displaced_future_rank=displaced_rank,
                    ))
                    swap_index += 1
                    changed = True
                    repair_has_diverged = True
                if not changed:
                    break

            rung = _rung_evidence(
                reference_domain, sparse_domain, state, order_indices, size, previous_size,
                accepted, zero_unique_fraction, selector_policy.coverage_threshold, policy.gain_tie_tolerance,
            )
            base_cov = dict(base_rung.family_coverage)
            for family_id, value in rung.family_coverage:
                if value + policy.gain_tie_tolerance < float(base_cov[family_id]):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 same-N coverage regressed below MVSEL1.")
            if base_rung.hard_obligations_passed and not rung.hard_obligations_passed:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 same-N hard obligations regressed below MVSEL1.")
            rungs.append(rung)
            if progress_callback is not None:
                minimum = min(value for _, value in rung.family_coverage)
                cache_note = "; state=MVSTATE-cache" if checkpoint_used else ""
                progress_callback(
                    f"status=rung; domain={reference_domain.label_domain_id}; target_size={size}; swaps={len(accepted)}; "
                    f"zero_unique_shell_fraction={zero_unique_fraction:.4f}; min_required_coverage={minimum:.6f}{cache_note}"
                )
            previous_size = size

    return TargetMultiViewRepairDomainPlan(
        label_domain_id=reference_domain.label_domain_id,
        reference_domain_digest=reference_domain.content_digest,
        sparse_domain_digest=sparse_domain.content_digest,
        selection_domain_digest=selection_domain.content_digest,
        candidate_count=sparse_domain.candidate_count,
        repaired_master_order=tuple(reference_domain.frame_uids[int(v)] for v in order_indices),
        rungs=tuple(rungs),
        total_swaps=sum(len(item.swaps) for item in rungs),
    )

def build_target_multi_view_repair_plan(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_multi_view_selection: Any,
    *,
    policy: TargetMultiViewRepairPolicy | None = None,
    progress_callback: Any = None,
    execution_mode: str = "optimized",
    proposal_workers: int = 1,
    resource_scope: StageResourceScope | None = None,
    selection_state_cache: Any | None = None,
) -> TargetMultiViewRepairPlan:
    """Build deterministic REPAIR1 evidence without migrating TARGET-DATA2C."""

    policy = policy or TargetMultiViewRepairPolicy()
    if execution_mode not in {"optimized", "reference"}:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR-PAR1 execution_mode must be optimized or reference.")
    proposal_workers = int(proposal_workers)
    if proposal_workers < 1:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR-PAR1 proposal_workers must be positive.")
    select_function = _mvsel._select_and_update if execution_mode == "optimized" else _mvsel._select_and_update_reference
    deselect_function = _deselect_and_update if execution_mode == "optimized" else _deselect_and_update_reference
    if target_coverage_reference.dataset_id != target_coverage_sparse_index.dataset_id or target_coverage_reference.dataset_id != target_multi_view_selection.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 dataset identity mismatch.")
    if target_multi_view_selection.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 MVSEL/reference lineage mismatch.")
    if target_multi_view_selection.target_coverage_sparse_index_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 MVSEL/MVIDX lineage mismatch.")
    if selection_state_cache is not None:
        validate_target_multi_view_selection_state_cache(
            selection_state_cache,
            target_coverage_reference=target_coverage_reference,
            target_coverage_sparse_index=target_coverage_sparse_index,
            target_multi_view_selection=target_multi_view_selection,
        )

    domains = []
    for reference_domain in target_coverage_reference.domains:
        sparse_domain = target_coverage_sparse_index.domain(reference_domain.label_domain_id)
        selection_domain = target_multi_view_selection.domain(reference_domain.label_domain_id)
        domains.append(_build_domain_repair(
            reference_domain,
            sparse_domain,
            selection_domain,
            target_multi_view_selection.policy,
            policy,
            progress_callback=progress_callback,
            select_function=select_function,
            deselect_function=deselect_function,
            proposal_workers=proposal_workers,
            resource_scope=resource_scope,
            proposal_optimized=(execution_mode == "optimized"),
            selection_state_domain_cache=(None if selection_state_cache is None else selection_state_cache.domain(reference_domain.label_domain_id)),
        ))
    return TargetMultiViewRepairPlan(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_coverage_sparse_index_digest=target_coverage_sparse_index.content_digest,
        target_multi_view_selection_digest=target_multi_view_selection.content_digest,
        policy=policy,
        domains=tuple(domains),
    )


def validate_target_multi_view_repair_authority(
    plan: TargetMultiViewRepairPlan,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_multi_view_selection: Any,
    policy: TargetMultiViewRepairPolicy | None = None,
    verify_repair_replay: bool = False,
) -> None:
    """Validate lineage, frozen-prefix invariants, exact sparse evidence and replay."""

    from .target_coverage_sparse_index import indexed_family_covered_mass, indexed_obligation_selected_counts

    policy = policy or TargetMultiViewRepairPolicy()
    if plan.dataset_id != target_coverage_reference.dataset_id or plan.dataset_id != target_coverage_sparse_index.dataset_id or plan.dataset_id != target_multi_view_selection.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 dataset identity mismatch.")
    if plan.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 reference digest mismatch.")
    if plan.target_coverage_sparse_index_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 sparse-index digest mismatch.")
    if plan.target_multi_view_selection_digest != target_multi_view_selection.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 selector digest mismatch.")
    if plan.policy.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 policy digest mismatch.")

    for domain in plan.domains:
        reference_domain = target_coverage_reference.domain(domain.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(domain.label_domain_id)
        selection_domain = target_multi_view_selection.domain(domain.label_domain_id)
        if domain.reference_domain_digest != reference_domain.content_digest or domain.sparse_domain_digest != sparse_domain.content_digest or domain.selection_domain_digest != selection_domain.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 domain lineage changed.")
        if domain.candidate_count != sparse_domain.candidate_count:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 candidate cardinality changed.")
        eligible = set(reference_domain.frame_uids)
        if len(set(domain.repaired_master_order)) != len(domain.repaired_master_order) or any(uid not in eligible for uid in domain.repaired_master_order):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 repaired order contains invalid frames.")
        uid_to_index = {uid: i for i, uid in enumerate(reference_domain.frame_uids)}
        previous_uids: tuple[str, ...] = ()
        previous_coverage: dict[str, float] = {item.family_id: 0.0 for item in sparse_domain.families}
        base_rungs = {item.target_size: item for item in selection_domain.rungs}
        for rung in domain.rungs:
            base_rung = base_rungs[rung.target_size]
            if not rung.materializable:
                if base_rung.materializable:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 unexpectedly made a base rung unavailable.")
                continue
            if tuple(domain.repaired_master_order[:rung.target_size]) != rung.frame_uids:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 rung is not the repaired master-order prefix.")
            if previous_uids and rung.frame_uids[:len(previous_uids)] != previous_uids:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 changed a frozen lower prefix.")
            selected = tuple(uid_to_index[uid] for uid in rung.frame_uids)
            observed = []
            for sparse_family in sparse_domain.families:
                family = reference_domain.family(sparse_family.family_id)
                mass = indexed_family_covered_mass(sparse_family, family.weights, selected)
                observed.append((sparse_family.family_id, mass))
                if mass + policy.gain_tie_tolerance < previous_coverage[sparse_family.family_id]:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 coverage decreased across nested repaired rungs.")
                previous_coverage[sparse_family.family_id] = mass
            observed = tuple(sorted(observed))
            for (expected_id, expected_mass), (observed_id, observed_mass) in zip(rung.family_coverage, observed, strict=True):
                if expected_id != observed_id or not math.isclose(expected_mass, observed_mass, rel_tol=0.0, abs_tol=5.0e-12):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 persisted rung coverage is inconsistent with MVIDX1.")
            base_cov = dict(base_rung.family_coverage)
            for family_id, mass in observed:
                if mass + policy.gain_tie_tolerance < float(base_cov[family_id]):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 same-N coverage regressed below MVSEL1.")
            counts = indexed_obligation_selected_counts(sparse_domain, selected)
            unsatisfied = tuple(sorted(
                obligation.obligation_id
                for oi, obligation in enumerate(sparse_domain.obligations)
                if obligation.required and int(counts[oi]) < int(obligation.minimum_selected_frames)
            ))
            if unsatisfied != rung.unsatisfied_obligation_ids or (not unsatisfied) != rung.hard_obligations_passed:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 persisted hard-obligation state is inconsistent.")
            if base_rung.hard_obligations_passed and not rung.hard_obligations_passed:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 hard obligations regressed below MVSEL1.")
            coverage_pass = all(mass >= target_multi_view_selection.policy.coverage_threshold - policy.gain_tie_tolerance for _, mass in observed)
            if rung.hard_coverage_qualified != bool((not unsatisfied) and coverage_pass):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 hard-qualification state is inconsistent.")
            if len(rung.swaps) > policy.max_swaps_per_shell:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap budget was exceeded.")
            for swap in rung.swaps:
                if not (rung.active_shell_start <= swap.rank < rung.target_size):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 swap escaped the active shell.")
                if swap.removed_unique_coverage > policy.unique_coverage_tolerance:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 removed frame had non-negligible unique coverage.")
                if swap.minimum_coverage_after + policy.gain_tie_tolerance < swap.minimum_coverage_before or swap.total_coverage_after + policy.gain_tie_tolerance < swap.total_coverage_before:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 accepted a coverage-regressing swap.")
                before = (swap.hard_deficit_before, swap.minimum_coverage_before, swap.total_coverage_before, swap.representative_utility_before, swap.unit_balance_before)
                after = (swap.hard_deficit_after, swap.minimum_coverage_after, swap.total_coverage_after, swap.representative_utility_after, swap.unit_balance_after)
                if not _strictly_better(before, after, policy.gain_tie_tolerance):
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 persisted swap is not strictly improving.")
            previous_uids = rung.frame_uids

    if verify_repair_replay:
        rebuilt = build_target_multi_view_repair_plan(
            target_coverage_reference,
            target_coverage_sparse_index,
            target_multi_view_selection,
            policy=policy,
        )
        if rebuilt.content_digest != plan.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR1 exact replay changed the repair digest.")
