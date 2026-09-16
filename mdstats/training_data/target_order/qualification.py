"""MVQUAL: independent configured-prefix membership qualification (D2 section 10).

Restored from MVQUAL2 (``target_multi_view_qualification_v2`` and the
progressive nested-rung path of ``mvqual_p2_runtime``, carrier ``3937881e``),
integrated directly instead of through the historical runtime monkeypatch, and
rebound to canonical obligations.

For every configured ``N`` the exact repaired nested prefix ``T_N`` is scored
from the immutable :class:`TargetCoverageReference` (direct nearest-selected
distance against local radii, plus extents) and from canonical obligation
incidence ``q_o(T_N) >= k_o``.  Selector/repair counters are never consulted.
The MVIDX forward relation is an exact secondary cross-check of every family
mass (``rtol=0``, ``atol=5e-12``).  Rungs evolve serially inside each family;
families are independent state owners and may run concurrently, reduced in
canonical family order.  Qualification must be ``FAIL* -> PASS*``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest
from ..resources import StageResourceScope
from ..work_queue import DeterministicWorkQueue
from .coverage_reference import ProgressiveFamilyCoverageState, TargetCoverageFamilyReport
from .selector import prefix_digest
from .sparse_index import indexed_family_covered_mass

MVQUAL_VERSION = "mdstats.target-order.mvqual.configured-prefix.v1"
MVQUAL_RUNG_SCHEMA = "mdstats.target-membership-qualification-rung.v1"
MVQUAL_PLAN_SCHEMA = "mdstats.target-membership-qualification-plan.v1"
MVIDX_CROSS_CHECK_ATOL = 5.0e-12


@dataclass(frozen=True, slots=True)
class TargetMembershipQualificationRung:
    target_size: int
    frame_uids_digest: str
    family_reports: tuple[TargetCoverageFamilyReport, ...]
    obligation_count: int
    unsatisfied_obligation_ids: tuple[str, ...]
    mvidx_max_abs_mass_difference: float

    @property
    def coverage_passed(self) -> bool:
        return all(item.coverage_passed for item in self.family_reports)

    @property
    def extent_passed(self) -> bool:
        return all(item.extent_passed for item in self.family_reports)

    @property
    def hard_obligations_passed(self) -> bool:
        return not self.unsatisfied_obligation_ids

    @property
    def qualified(self) -> bool:
        return self.coverage_passed and self.extent_passed and self.hard_obligations_passed

    @property
    def minimum_family_coverage(self) -> float:
        return min(item.covered_reference_mass for item in self.family_reports)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MVQUAL_RUNG_SCHEMA,
            "target_size": int(self.target_size),
            "frame_uids_digest": self.frame_uids_digest,
            "family_reports": [item.to_dict() for item in self.family_reports],
            "obligation_count": int(self.obligation_count),
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "mvidx_max_abs_mass_difference": float(self.mvidx_max_abs_mass_difference),
            "coverage_passed": self.coverage_passed,
            "extent_passed": self.extent_passed,
            "hard_obligations_passed": self.hard_obligations_passed,
            "qualified": self.qualified,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMembershipQualificationRung":
        if payload.get("schema") != MVQUAL_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVQUAL rung schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            frame_uids_digest=str(payload["frame_uids_digest"]),
            family_reports=tuple(TargetCoverageFamilyReport.from_dict(v) for v in payload["family_reports"]),
            obligation_count=int(payload["obligation_count"]),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload["unsatisfied_obligation_ids"]),
            mvidx_max_abs_mass_difference=float(payload["mvidx_max_abs_mass_difference"]),
        )
        if bool(payload.get("qualified")) != result.qualified:
            raise TrainingDataSerializationError("MVQUAL rung qualification state is inconsistent.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMembershipQualificationPlan:
    target_coverage_reference_digest: str
    obligation_authority_digest: str
    mvidx_content_digest: str
    rungs: tuple[TargetMembershipQualificationRung, ...]
    authority_version: str = MVQUAL_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(item.target_size for item in self.rungs)
        if not sizes or sizes != tuple(sorted(set(sizes))):
            raise TrainingDataInputError("MVQUAL rungs must follow the strictly increasing configured ladder.")
        passed = False
        for item in self.rungs:
            if item.qualified:
                passed = True
            elif passed:
                raise TrainingDataInputError(
                    f"MVQUAL monotonic qualification violated: n{item.target_size} failed after a smaller prefix passed."
                )
        if self.authority_version != MVQUAL_VERSION:
            raise TrainingDataInputError("Unsupported MVQUAL authority version.")

    @property
    def qualified_sizes(self) -> tuple[int, ...]:
        return tuple(item.target_size for item in self.rungs if item.qualified)

    def rung(self, target_size: int) -> TargetMembershipQualificationRung:
        for item in self.rungs:
            if item.target_size == int(target_size):
                return item
        raise KeyError(target_size)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": MVQUAL_PLAN_SCHEMA,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "obligation_authority_digest": self.obligation_authority_digest,
            "mvidx_content_digest": self.mvidx_content_digest,
            "rungs": [item.to_dict() for item in self.rungs],
            "authority_version": self.authority_version,
        }
        return {**payload, "content_digest": digest(payload)}

    @property
    def content_digest(self) -> str:
        return str(self.to_dict()["content_digest"])

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMembershipQualificationPlan":
        if payload.get("schema") != MVQUAL_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVQUAL plan schema.")
        result = cls(
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            obligation_authority_digest=str(payload["obligation_authority_digest"]),
            mvidx_content_digest=str(payload["mvidx_content_digest"]),
            rungs=tuple(TargetMembershipQualificationRung.from_dict(v) for v in payload["rungs"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("MVQUAL plan digest mismatch.")
        return result


def _progressive_family(
    family: Any, prefixes: Sequence[np.ndarray], threshold: float, *, query_workers: int
) -> tuple[TargetCoverageFamilyReport, ...]:
    """Serial nested-rung evolution for one family state owner."""

    state = ProgressiveFamilyCoverageState.build(family)
    reports: list[TargetCoverageFamilyReport] = []
    previous = 0
    for prefix in prefixes:
        state.add_frame_indices(prefix[previous:], query_workers=query_workers)
        previous = prefix.size
        reports.append(state.report(threshold=threshold))
    return tuple(reports)


def build_membership_qualification(
    reference: Any,
    authority: Any,
    forward: Any,
    configured_prefixes: Mapping[int, Sequence[str]],
    *,
    workers: int = 1,
    query_workers: int = 1,
    resource_scope: StageResourceScope | None = None,
) -> TargetMembershipQualificationPlan:
    """Qualify every configured nested prefix independently of selector state."""

    sizes = tuple(sorted(int(v) for v in configured_prefixes))
    if not sizes:
        raise TrainingDataInputError("MVQUAL requires at least one configured prefix.")
    if forward.frame_domain_digest != reference.frame_domain_digest:
        raise TrainingDataInputError("MVQUAL MVIDX frame domain differs from the coverage reference.")
    if tuple(item.family_id for item in forward.families) != tuple(item.family_id for item in reference.families):
        raise TrainingDataInputError("MVQUAL MVIDX family identity differs from the coverage reference.")
    uid_prefixes = [tuple(str(v) for v in configured_prefixes[size]) for size in sizes]
    for size, uids in zip(sizes, uid_prefixes, strict=True):
        if len(uids) != size or len(set(uids)) != size:
            raise TrainingDataInputError(f"MVQUAL prefix n{size} is not an exact unique prefix.")
    for smaller, larger in zip(uid_prefixes, uid_prefixes[1:]):
        if larger[: len(smaller)] != smaller:
            raise TrainingDataInputError("MVQUAL configured prefixes are not nested.")
    try:
        indices = [np.asarray([reference.frame_index(uid) for uid in uids], dtype=np.int64) for uids in uid_prefixes]
    except KeyError as exc:
        raise TrainingDataInputError("MVQUAL prefix member lies outside exact P_train.") from exc
    threshold = float(reference.policy.coverage_threshold)
    families = tuple(reference.families)
    width = max(1, min(int(workers), len(families)))
    if width == 1:
        by_family = [_progressive_family(family, indices, threshold, query_workers=query_workers) for family in families]
    else:
        # An inherited scope supplies the CPU/RAM budget; MVQUAL still owns and
        # applies the native-thread limits its own lanes run under.
        owned = resource_scope is None
        scope = StageResourceScope(
            stage_name="TARGET-ORDER-MVQUAL" if owned else f"{resource_scope.stage_name}/mvqual",
            cpu_threads_available=width if owned else int(resource_scope.cpu_threads_available),
            cpu_threads_budget=width if owned else int(resource_scope.cpu_threads_budget),
            python_workers=width,
            ram_budget_bytes=None if owned else resource_scope.ram_budget_bytes,
        )
        results: dict[int, tuple[TargetCoverageFamilyReport, ...]] = {}
        with DeterministicWorkQueue(
            scope,
            max_ready_tasks=2 * width,
            max_inflight_tasks=width,
            max_completed_tasks=2 * width,
            thread_name_prefix="mdstats-mvqual",
        ) as queue:
            position = 0
            while len(results) < len(families):
                while position < len(families) and queue.can_submit():
                    family = families[position]
                    queue.submit(
                        task_id=f"mvqual-family-{position:05d}",
                        canonical_order=(position,),
                        function=_progressive_family,
                        args=(family, indices, threshold),
                        kwargs={"query_workers": 1},
                        task_kind="mvqual-family",
                        estimated_memory_bytes=int(3 * np.asarray(family.values).nbytes),
                    )
                    position += 1
                queue.wait_for_completion()
                for completion in queue.drain_completed():
                    results[int(completion.canonical_order[0])] = completion.value
        by_family = [results[position] for position in range(len(families))]
    rungs: list[TargetMembershipQualificationRung] = []
    for rung_index, (size, prefix) in enumerate(zip(sizes, indices, strict=True)):
        reports = tuple(item[rung_index] for item in by_family)
        difference = 0.0
        for family, report in zip(forward.families, reports, strict=True):
            indexed = indexed_family_covered_mass(family, reference.family(family.family_id).weights, prefix)
            delta = abs(indexed - report.covered_reference_mass)
            if not delta <= MVIDX_CROSS_CHECK_ATOL:
                raise TrainingDataInputError(
                    f"MVQUAL invariant: MVIDX mass for {family.family_id} at n{size} differs from direct coverage by {delta:.3e}."
                )
            difference = max(difference, delta)
        counts = authority.selected_counts(prefix)
        unsatisfied = tuple(
            sorted(
                item.obligation_id
                for item, count in zip(authority.obligations, counts, strict=True)
                if int(count) < int(item.minimum_count)
            )
        )
        rungs.append(
            TargetMembershipQualificationRung(
                target_size=size,
                frame_uids_digest=prefix_digest(uid_prefixes[rung_index]),
                family_reports=reports,
                obligation_count=len(authority.obligations),
                unsatisfied_obligation_ids=unsatisfied,
                mvidx_max_abs_mass_difference=difference,
            )
        )
    return TargetMembershipQualificationPlan(
        target_coverage_reference_digest=reference.content_digest,
        obligation_authority_digest=authority.content_digest,
        mvidx_content_digest=forward.mvidx_content_digest,
        rungs=tuple(rungs),
    )


__all__ = [
    "MVIDX_CROSS_CHECK_ATOL",
    "MVQUAL_VERSION",
    "TargetMembershipQualificationPlan",
    "TargetMembershipQualificationRung",
    "build_membership_qualification",
]
