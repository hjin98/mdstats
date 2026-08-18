"""REPAIR2 exact active-shell repair over compact MVSTATE2 forward state."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any

import numpy as np

from ._common import TrainingDataInputError, digest
from .target_multi_view_repair import TargetMultiViewRepairRung, TargetMultiViewRepairSwap
from .target_multi_view_selector_v2 import (
    TargetMultiViewForwardFamilyStateV2,
    TargetMultiViewForwardStateV2,
    TargetMultiViewSelectionPlanV2,
    build_target_multi_view_forward_state_v2,
    deselect_target_multi_view_candidate_v2,
    score_target_multi_view_candidate_v2,
    select_target_multi_view_candidate_v2,
)
from .progress_timing import format_progress_time


TARGET_MULTI_VIEW_REPAIR_V2_VERSION = "mdstats.target-data2c-repair2.forward-state.2026-08.v1"
TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA = "mdstats.target-multi-view-repair-plan.v2"


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPolicyV2:
    max_passes_per_shell: int = 2
    max_swaps_per_shell: int = 64
    removal_shortlist_limit: int = 32
    unique_coverage_tolerance: float = 1.0e-14
    gain_tie_tolerance: float = 1.0e-14
    strict_no_coverage_regression: bool = True
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_V2_VERSION

    def __post_init__(self) -> None:
        if min(self.max_passes_per_shell, self.max_swaps_per_shell, self.removal_shortlist_limit) < 1:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 bounded-search limits must be positive.")
        if not (math.isfinite(self.unique_coverage_tolerance) and math.isfinite(self.gain_tie_tolerance)) or min(self.unique_coverage_tolerance, self.gain_tie_tolerance) <= 0.0:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 tolerances must be positive and finite.")
        if self.authority_version != TARGET_MULTI_VIEW_REPAIR_V2_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 policy version.")

    def to_dict(self) -> dict[str, Any]:
        payload = {name: getattr(self, name) for name in self.__dataclass_fields__}
        payload["schema"] = "mdstats.target-multi-view-repair-policy.v2"
        return {**payload, "policy_digest": digest(payload)}

    @property
    def policy_digest(self) -> str:
        return str(self.to_dict()["policy_digest"])

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairPolicyV2":
        if payload.get("schema") != "mdstats.target-multi-view-repair-policy.v2":
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 policy schema.")
        result = cls(**{name: payload[name] for name in cls.__dataclass_fields__})
        if payload.get("policy_digest") != result.policy_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairDomainPlanV2:
    label_domain_id: str
    reference_domain_digest: str
    mvidx1_domain_digest: str
    selection_domain_digest: str
    candidate_count: int
    repaired_master_order: tuple[str, ...]
    rungs: tuple[TargetMultiViewRepairRung, ...]
    total_swaps: int

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": "mdstats.target-multi-view-repair-domain.v2",
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "mvidx1_domain_digest": self.mvidx1_domain_digest,
            "selection_domain_digest": self.selection_domain_digest,
            "candidate_count": self.candidate_count,
            "repaired_master_order": self.repaired_master_order,
            "rungs": [item.to_dict() for item in self.rungs],
            "total_swaps": self.total_swaps,
        }
        return {**payload, "content_digest": digest(payload)} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairDomainPlanV2":
        if payload.get("schema") != "mdstats.target-multi-view-repair-domain.v2":
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]), reference_domain_digest=str(payload["reference_domain_digest"]),
            mvidx1_domain_digest=str(payload["mvidx1_domain_digest"]), selection_domain_digest=str(payload["selection_domain_digest"]),
            candidate_count=int(payload["candidate_count"]), repaired_master_order=tuple(str(value) for value in payload["repaired_master_order"]),
            rungs=tuple(TargetMultiViewRepairRung.from_dict(item) for item in payload["rungs"]), total_swaps=int(payload["total_swaps"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewRepairPlanV2:
    dataset_id: str
    target_coverage_reference_digest: str
    mvidx1_content_digest: str
    target_multi_view_selection_v2_digest: str
    policy: TargetMultiViewRepairPolicyV2
    domains: tuple[TargetMultiViewRepairDomainPlanV2, ...]
    authority_version: str = TARGET_MULTI_VIEW_REPAIR_V2_VERSION
    _domain_by_id: dict[str, TargetMultiViewRepairDomainPlanV2] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewRepairDomainPlanV2:
        return self._domain_by_id[label_domain_id]

    @property
    def target_coverage_sparse_index_digest(self) -> str:
        return self.mvidx1_content_digest

    @property
    def target_multi_view_selection_digest(self) -> str:
        return self.target_multi_view_selection_v2_digest

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_domains=False, include_digest=False))

    def to_dict(self, *, include_domains: bool = True, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "mvidx1_content_digest": self.mvidx1_content_digest,
            "target_multi_view_selection_v2_digest": self.target_multi_view_selection_v2_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [item.content_digest for item in self.domains],
            "authority_version": self.authority_version,
        }
        if include_domains:
            payload["domains"] = [item.to_dict() for item in self.domains]
        return {**payload, "content_digest": digest({key: value for key, value in payload.items() if key != "domains"})} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TargetMultiViewRepairPlanV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-REPAIR2 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            mvidx1_content_digest=str(payload["mvidx1_content_digest"]),
            target_multi_view_selection_v2_digest=str(payload["target_multi_view_selection_v2_digest"]),
            policy=TargetMultiViewRepairPolicyV2.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewRepairDomainPlanV2.from_dict(item) for item in payload["domains"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 plan digest mismatch.")
        return result


def _copy_state(state: TargetMultiViewForwardStateV2) -> TargetMultiViewForwardStateV2:
    return TargetMultiViewForwardStateV2(
        available=np.array(state.available, copy=True),
        selected_order=list(state.selected_order),
        family_states=[TargetMultiViewForwardFamilyStateV2(
            family_id=item.family_id, weights=item.weights,
            multiplicity=np.array(item.multiplicity, copy=True),
            coverage_mass=float(item.coverage_mass),
        ) for item in state.family_states],
        obligation_counts=np.array(state.obligation_counts, copy=True),
        unsatisfied_required_obligation_count=int(state.unsatisfied_required_obligation_count),
        correlation_unit_counts=np.array(state.correlation_unit_counts, copy=True),
        representative_utility=float(state.representative_utility),
    )


def _hard_deficit(forward_domain: Any, state: TargetMultiViewForwardStateV2) -> int:
    return sum(max(0, int(item.minimum_selected_frames) - int(state.obligation_counts[index]))
               for index, item in enumerate(forward_domain.obligations) if item.required)


def _objective(forward_domain: Any, state: TargetMultiViewForwardStateV2) -> tuple[int, float, float, float, int]:
    coverage = [float(item.coverage_mass) for item in state.family_states]
    counts = state.correlation_unit_counts.astype(np.int64)
    return (_hard_deficit(forward_domain, state), min(coverage), float(np.sum(coverage, dtype=np.float64)),
            float(state.representative_utility), -int(np.dot(counts, counts)))


def _strictly_better(before: tuple[int, float, float, float, int], after: tuple[int, float, float, float, int], tolerance: float) -> bool:
    if after[0] != before[0]:
        return after[0] < before[0]
    for old, new in zip(before[1:4], after[1:4], strict=True):
        if new > old + tolerance:
            return True
        if new < old - tolerance:
            return False
    return after[4] > before[4]


def _removal_metrics(candidate: int, forward_domain: Any, state: TargetMultiViewForwardStateV2) -> tuple[float, float]:
    unique = 0.0
    loss = 0.0
    for family, family_state in zip(forward_domain.families, state.family_states, strict=True):
        witnesses = np.asarray(family.candidate_witness_indices(candidate), dtype=np.int64)
        multiplicity = family_state.multiplicity[witnesses].astype(np.float64)
        if np.any(multiplicity < 1.0):
            raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 selected witness multiplicity underflow.")
        weights = family_state.weights[witnesses]
        unique += float(np.sum(weights[multiplicity == 1.0], dtype=np.float64))
        loss += float(np.sum(weights / multiplicity, dtype=np.float64))
    return unique, loss


def _hard_safe(candidate: int, forward_domain: Any, state: TargetMultiViewForwardStateV2) -> bool:
    for index in np.asarray(forward_domain.candidate_obligation_indices(candidate), dtype=np.int64):
        item = forward_domain.obligations[int(index)]
        if item.required and int(state.obligation_counts[index]) <= int(item.minimum_selected_frames):
            return False
    return True


def _filter(candidates: tuple[int, ...], values: dict[int, float], tolerance: float) -> tuple[int, ...]:
    best = max(values[candidate] for candidate in candidates)
    return tuple(candidate for candidate in candidates if values[candidate] >= best - tolerance)


def _choose_replacement(reference_domain: Any, forward_domain: Any, state: TargetMultiViewForwardStateV2, policy: TargetMultiViewRepairPolicyV2) -> tuple[int, Any] | None:
    candidates = tuple(int(value) for value in np.flatnonzero(state.available))
    if not candidates:
        return None
    scores = {candidate: score_target_multi_view_candidate_v2(candidate, forward_domain, state) for candidate in candidates}
    hard_pending = _hard_deficit(forward_domain, state) > 0
    if hard_pending:
        maximum = max(scores[candidate].hard_obligation_gain for candidate in candidates)
        candidates = tuple(candidate for candidate in candidates if scores[candidate].hard_obligation_gain == maximum)
    masses = np.asarray([item.coverage_mass for item in state.family_states], dtype=np.float64)
    bottleneck = int(np.flatnonzero(masses <= float(np.min(masses)) + policy.gain_tie_tolerance)[0])
    candidates = _filter(candidates, {candidate: scores[candidate].family_coverage_gains[bottleneck] for candidate in candidates}, policy.gain_tie_tolerance)
    candidates = _filter(candidates, {candidate: scores[candidate].total_coverage_gain for candidate in candidates}, policy.gain_tie_tolerance)
    if not hard_pending and max(scores[candidate].total_coverage_gain for candidate in candidates) <= policy.gain_tie_tolerance:
        return None
    minimum_unit = min(int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])]) for candidate in candidates)
    candidates = tuple(candidate for candidate in candidates if int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[candidate])]) == minimum_unit)
    candidates = _filter(candidates, {candidate: scores[candidate].representative_gain for candidate in candidates}, policy.gain_tie_tolerance)
    candidates = _filter(candidates, {candidate: scores[candidate].sparse_diversity for candidate in candidates}, policy.gain_tie_tolerance)
    chosen = min(candidates, key=lambda candidate: reference_domain.frame_uids[candidate])
    return chosen, scores[chosen]


def _proposal(reference_domain: Any, forward_domain: Any, state: TargetMultiViewForwardStateV2,
              removal: tuple[int, int, float, float], policy: TargetMultiViewRepairPolicyV2) -> dict[str, Any] | None:
    rank, removed, unique, loss = removal
    before = _objective(forward_domain, state)
    trial = _copy_state(state)
    deselect_target_multi_view_candidate_v2(removed, forward_domain, trial)
    replacement_row = _choose_replacement(reference_domain, forward_domain, trial, policy)
    if replacement_row is None:
        return None
    replacement, score = replacement_row
    select_target_multi_view_candidate_v2(replacement, forward_domain, trial, score=score)
    after = _objective(forward_domain, trial)
    if policy.strict_no_coverage_regression and any(
        new.coverage_mass + policy.gain_tie_tolerance < old.coverage_mass
        for old, new in zip(state.family_states, trial.family_states, strict=True)
    ):
        return None
    if not _strictly_better(before, after, policy.gain_tie_tolerance):
        return None
    bottleneck = int(np.flatnonzero(np.asarray([item.coverage_mass for item in trial.family_states]) <= after[1] + policy.gain_tie_tolerance)[0])
    return {"rank": rank, "removed": removed, "replacement": replacement, "unique": unique,
            "loss": loss, "before": before, "after": after, "bottleneck": trial.family_states[bottleneck].family_id,
            "trial": trial}


def _better(left: dict[str, Any] | None, right: dict[str, Any], reference_domain: Any, tolerance: float) -> dict[str, Any]:
    if left is None or _strictly_better(left["after"], right["after"], tolerance):
        return right
    if _strictly_better(right["after"], left["after"], tolerance):
        return left
    lkey = (left["loss"], left["rank"], reference_domain.frame_uids[left["removed"]], reference_domain.frame_uids[left["replacement"]])
    rkey = (right["loss"], right["rank"], reference_domain.frame_uids[right["removed"]], reference_domain.frame_uids[right["replacement"]])
    return left if lkey <= rkey else right


def build_target_multi_view_repair_plan_v2(
    target_coverage_reference: Any,
    target_coverage_forward_index: Any,
    target_multi_view_selection: TargetMultiViewSelectionPlanV2,
    *,
    policy: TargetMultiViewRepairPolicyV2 | None = None,
    workers: int = 1,
    batch_size: int = 256,
    progress_callback: Any | None = None,
) -> TargetMultiViewRepairPlanV2:
    """Build REPAIR2 without inverse adjacency or MVSEL1 eager state."""

    del batch_size  # execution-only; scalar authority is canonical
    if int(workers) < 1:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 workers must be positive.")
    policy = policy or TargetMultiViewRepairPolicyV2()
    domains: list[TargetMultiViewRepairDomainPlanV2] = []
    for reference_domain in target_coverage_reference.domains:
        domain_started = time.monotonic()
        forward_domain = target_coverage_forward_index.domain(reference_domain.label_domain_id)
        selection_domain = target_multi_view_selection.domain(reference_domain.label_domain_id)
        uid_to_candidate = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
        order = [uid_to_candidate[item.frame_uid] for item in selection_domain.master_order]
        state = build_target_multi_view_forward_state_v2(reference_domain, forward_domain)
        previous_size = 0
        rungs: list[TargetMultiViewRepairRung] = []
        for base_rung in selection_domain.rungs:
            size = int(base_rung.target_size)
            if not base_rung.materializable:
                rungs.append(TargetMultiViewRepairRung(target_size=size, materializable=False,
                    active_shell_start=previous_size, unavailable_reason=base_rung.unavailable_reason or "unavailable_in_mvsel2"))
                continue
            for rank in range(previous_size, size):
                candidate = order[rank]
                score = score_target_multi_view_candidate_v2(candidate, forward_domain, state)
                select_target_multi_view_candidate_v2(candidate, forward_domain, state, score=score)
            shell_size = size - previous_size
            initial_zero = sum(_removal_metrics(order[rank], forward_domain, state)[0] <= policy.unique_coverage_tolerance for rank in range(previous_size, size))
            accepted: list[TargetMultiViewRepairSwap] = []
            for pass_index in range(policy.max_passes_per_shell):
                changed = False
                while len(accepted) < policy.max_swaps_per_shell:
                    removals = []
                    for rank in range(previous_size, size):
                        candidate = order[rank]
                        unique, loss = _removal_metrics(candidate, forward_domain, state)
                        if unique <= policy.unique_coverage_tolerance and _hard_safe(candidate, forward_domain, state):
                            removals.append((rank, candidate, unique, loss))
                    removals.sort(key=lambda row: (row[3], -int(state.correlation_unit_counts[int(forward_domain.candidate_correlation_unit_codes[row[1]])]), reference_domain.frame_uids[row[1]]))
                    best = None
                    for removal in removals[:policy.removal_shortlist_limit]:
                        proposal = _proposal(reference_domain, forward_domain, state, removal, policy)
                        if proposal is not None:
                            best = _better(best, proposal, reference_domain, policy.gain_tie_tolerance)
                    if best is None:
                        break
                    rank = int(best["rank"]); removed = int(best["removed"]); replacement = int(best["replacement"])
                    future = next((index for index in range(size, len(order)) if order[index] == replacement), -1)
                    displaced = None
                    if future >= size:
                        order[future] = removed
                        displaced = future
                    order[rank] = replacement
                    state = best["trial"]
                    before = best["before"]; after = best["after"]
                    accepted.append(TargetMultiViewRepairSwap(
                        target_size=size, pass_index=pass_index, swap_index=len(accepted), rank=rank,
                        removed_frame_uid=reference_domain.frame_uids[removed], replacement_frame_uid=reference_domain.frame_uids[replacement],
                        removed_unique_coverage=best["unique"], removed_representative_loss=best["loss"],
                        hard_deficit_before=before[0], hard_deficit_after=after[0], minimum_coverage_before=before[1], minimum_coverage_after=after[1],
                        total_coverage_before=before[2], total_coverage_after=after[2], representative_utility_before=before[3], representative_utility_after=after[3],
                        unit_balance_before=before[4], unit_balance_after=after[4], bottleneck_family_id=best["bottleneck"], displaced_future_rank=displaced,
                    ))
                    changed = True
                if not changed:
                    break
            coverage = tuple((item.family_id, min(1.0, max(0.0, item.coverage_mass))) for item in state.family_states)
            unsatisfied = tuple(sorted(item.obligation_id for index, item in enumerate(forward_domain.obligations)
                                       if item.required and int(state.obligation_counts[index]) < int(item.minimum_selected_frames)))
            for family_id, value in coverage:
                if value + policy.gain_tie_tolerance < dict(base_rung.family_coverage)[family_id]:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 same-N coverage regressed below MVSEL2.")
            if base_rung.hard_obligations_passed and unsatisfied:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 hard obligations regressed below MVSEL2.")
            rungs.append(TargetMultiViewRepairRung(
                target_size=size, materializable=True, active_shell_start=previous_size,
                frame_uids=tuple(reference_domain.frame_uids[candidate] for candidate in order[:size]),
                family_coverage=coverage, hard_obligations_passed=not unsatisfied,
                unsatisfied_obligation_ids=unsatisfied,
                hard_coverage_qualified=not unsatisfied and all(value >= target_multi_view_selection.policy.coverage_threshold - policy.gain_tie_tolerance for _, value in coverage),
                swaps=tuple(accepted), zero_unique_shell_fraction=0.0 if not shell_size else initial_zero / shell_size,
            ))
            if progress_callback is not None:
                progress_callback(
                    f"status=rung; progress={size}/{selection_domain.rungs[-1].target_size}; "
                    f"elapsed={format_progress_time(time.monotonic() - domain_started)}; eta=--:--:--; "
                    f"domain={reference_domain.label_domain_id}; target_size={size}; "
                    f"active_shell_start={previous_size}; swaps={len(accepted)}; "
                    f"zero_unique_shell_fraction={0.0 if not shell_size else initial_zero / shell_size:.6f}; "
                    f"inverse_mutation=false"
                )
            previous_size = size
        domains.append(TargetMultiViewRepairDomainPlanV2(
            label_domain_id=reference_domain.label_domain_id,
            reference_domain_digest=reference_domain.content_digest,
            mvidx1_domain_digest=forward_domain.mvidx1_domain_digest,
            selection_domain_digest=selection_domain.content_digest,
            candidate_count=forward_domain.candidate_count,
            repaired_master_order=tuple(reference_domain.frame_uids[candidate] for candidate in order),
            rungs=tuple(rungs), total_swaps=sum(len(rung.swaps) for rung in rungs),
        ))
    return TargetMultiViewRepairPlanV2(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        mvidx1_content_digest=target_coverage_forward_index.mvidx1_content_digest,
        target_multi_view_selection_v2_digest=target_multi_view_selection.content_digest,
        policy=policy, domains=tuple(domains),
    )


def validate_target_multi_view_repair_authority_v2(
    plan: TargetMultiViewRepairPlanV2,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_multi_view_selection: TargetMultiViewSelectionPlanV2,
) -> None:
    """Recompute repaired rung coverage, obligations, nesting, and lineage."""

    from .target_coverage_sparse_index import indexed_family_covered_mass, indexed_obligation_selected_counts

    if plan.dataset_id != target_coverage_reference.dataset_id or plan.dataset_id != target_coverage_sparse_index.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 dataset lineage mismatch.")
    if plan.target_coverage_reference_digest != target_coverage_reference.content_digest or plan.mvidx1_content_digest != target_coverage_sparse_index.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 reference/MVIDX lineage mismatch.")
    if plan.target_multi_view_selection_v2_digest != target_multi_view_selection.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 selector lineage mismatch.")
    for domain_plan in plan.domains:
        reference_domain = target_coverage_reference.domain(domain_plan.label_domain_id)
        sparse_domain = target_coverage_sparse_index.domain(domain_plan.label_domain_id)
        selection_domain = target_multi_view_selection.domain(domain_plan.label_domain_id)
        uid_to_candidate = {uid: index for index, uid in enumerate(reference_domain.frame_uids)}
        previous: tuple[str, ...] = ()
        for base, rung in zip(selection_domain.rungs, domain_plan.rungs, strict=True):
            if not rung.materializable:
                continue
            if rung.frame_uids[:len(previous)] != previous or len(rung.frame_uids) != rung.target_size:
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 immutable-prefix/nesting check failed.")
            selected = tuple(uid_to_candidate[uid] for uid in rung.frame_uids)
            coverage = tuple((family.family_id, indexed_family_covered_mass(
                sparse_domain.family(family.family_id), family.weights, selected
            )) for family in reference_domain.families)
            if not np.allclose([value for _, value in coverage], [value for _, value in rung.family_coverage], rtol=0.0, atol=5.0e-13):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 rung coverage mismatch.")
            if any(value + plan.policy.gain_tie_tolerance < dict(base.family_coverage)[family_id] for family_id, value in coverage):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 same-N coverage regression.")
            counts = indexed_obligation_selected_counts(sparse_domain, selected)
            unsatisfied = tuple(sorted(item.obligation_id for index, item in enumerate(sparse_domain.obligations)
                                       if item.required and int(counts[index]) < int(item.minimum_selected_frames)))
            if unsatisfied != rung.unsatisfied_obligation_ids or (base.hard_obligations_passed and unsatisfied):
                raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 hard-obligation evidence mismatch.")
            for swap in rung.swaps:
                if not rung.active_shell_start <= swap.rank < rung.target_size or rung.frame_uids[swap.rank] != swap.replacement_frame_uid:
                    raise TrainingDataInputError("TARGET-DATA2C-REPAIR2 swap rank inheritance is invalid.")
            previous = rung.frame_uids
