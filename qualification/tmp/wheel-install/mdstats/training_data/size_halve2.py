"""SIZE-HALVE2 fixed eight-rung coverage-qualified successive-fidelity authority.

This gate is deliberately pre-migration.  It consumes the independently
qualified MV-selected ladder and freezes the future 3/10/30 candidate funnel,
but it does not replace TARGET-DATA2C v4 or the current TARGET-DATA2D v2
production authority.  Migration remains owned by TARGET-DATA2C-MVMIGRATE1.

The scientific contract is:

* the only possible target sizes are 128..16384 by powers of two;
* hard coverage is evaluated before TRAIN2 and only qualified sizes may train;
* fewer than four hard-qualified sizes blocks the future funnel;
* exact uninterrupted 30-epoch trajectories are paused at 3 and 10 epochs;
* survivor counts are q -> min(q, 4) -> 2 -> 1;
* the largest qualified boundary is tie-protected during 3/10-epoch promotion,
  but not against a materially better equivalence band;
* the final 30-epoch decision returns to the smaller-size preference inside a
  practical-equivalence band and reports boundary non-convergence when the
  largest qualified size remains materially superior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .target_size_convergence import TargetSizeTrainingEvidence

SIZE_HALVE2_FIXED_TARGET_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
SIZE_HALVE2_POLICY_SCHEMA = "mdstats.size-halve2-policy.v1"
SIZE_HALVE2_CANDIDATE_SCHEMA = "mdstats.size-halve2-candidate.v1"
SIZE_HALVE2_PLAN_SCHEMA = "mdstats.size-halve2-plan.v1"
SIZE_HALVE2_VERSION = "mdstats.size-halve2.2026-08.v1"

_READY = "ready_for_size_fidelity2"
_BLOCKED_MVQUAL = "blocked_mvqual_nonregression"
_BLOCKED_COVERAGE = "blocked_insufficient_hard_coverage"
_WAIT_SHORT = "awaiting_epoch10"
_WAIT_FINAL = "awaiting_epoch30"
_SELECTED = "selected"
_NONCONVERGED = "nonconverged_at_fixed_ceiling"
_FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SizeHalve2Policy:
    """Frozen pre-migration eight-rung 3/10/30 funnel policy."""

    target_sizes: tuple[int, ...] = SIZE_HALVE2_FIXED_TARGET_SIZES
    min_coverage_qualifiers: int = 4
    coarse_training_epochs: int = 3
    max_coarse_training_candidates: int = 4
    short_training_epochs: int = 10
    max_short_training_candidates: int = 2
    final_training_epochs: int = 30
    practical_equivalence_mev_per_a: float = 1.0
    coarse_practical_equivalence_mev_per_a: float | None = None
    screening_optimizer_seed: int = 1
    policy_version: str = SIZE_HALVE2_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.target_sizes)
        if sizes != SIZE_HALVE2_FIXED_TARGET_SIZES:
            raise TrainingDataInputError("SIZE-HALVE2 freezes exactly eight target sizes through 16384.")
        minimum = int(self.min_coverage_qualifiers)
        coarse = int(self.coarse_training_epochs)
        coarse_max = int(self.max_coarse_training_candidates)
        short = int(self.short_training_epochs)
        short_max = int(self.max_short_training_candidates)
        final = int(self.final_training_epochs)
        eps = float(self.practical_equivalence_mev_per_a)
        coarse_eps = eps if self.coarse_practical_equivalence_mev_per_a is None else float(self.coarse_practical_equivalence_mev_per_a)
        seed = int(self.screening_optimizer_seed)
        if minimum != 4:
            raise TrainingDataInputError("SIZE-HALVE2 freezes min_coverage_qualifiers at four.")
        if (coarse, coarse_max, short, short_max, final) != (3, 4, 10, 2, 30):
            raise TrainingDataInputError("SIZE-HALVE2 freezes q->4->2->1 at 3/10/30 epochs.")
        if not math.isfinite(eps) or eps <= 0.0 or not math.isfinite(coarse_eps) or coarse_eps <= 0.0:
            raise TrainingDataInputError("SIZE-HALVE2 practical-equivalence widths must be positive and finite.")
        if seed < 0:
            raise TrainingDataInputError("SIZE-HALVE2 screening seed must be nonnegative.")
        if self.policy_version != SIZE_HALVE2_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-HALVE2 policy version.")
        object.__setattr__(self, "target_sizes", sizes)
        object.__setattr__(self, "min_coverage_qualifiers", minimum)
        object.__setattr__(self, "coarse_training_epochs", coarse)
        object.__setattr__(self, "max_coarse_training_candidates", coarse_max)
        object.__setattr__(self, "short_training_epochs", short)
        object.__setattr__(self, "max_short_training_candidates", short_max)
        object.__setattr__(self, "final_training_epochs", final)
        object.__setattr__(self, "practical_equivalence_mev_per_a", eps)
        object.__setattr__(self, "coarse_practical_equivalence_mev_per_a", coarse_eps)
        object.__setattr__(self, "screening_optimizer_seed", seed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_HALVE2_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "target_sizes": list(self.target_sizes),
            "min_coverage_qualifiers": self.min_coverage_qualifiers,
            "coarse_training_epochs": self.coarse_training_epochs,
            "max_coarse_training_candidates": self.max_coarse_training_candidates,
            "short_training_epochs": self.short_training_epochs,
            "max_short_training_candidates": self.max_short_training_candidates,
            "final_training_epochs": self.final_training_epochs,
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "coarse_practical_equivalence_mev_per_a": self.coarse_practical_equivalence_mev_per_a,
            "screening_optimizer_seed": self.screening_optimizer_seed,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeHalve2Policy":
        if payload.get("schema") != SIZE_HALVE2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-HALVE2 policy schema.")
        result = cls(
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            min_coverage_qualifiers=int(payload["min_coverage_qualifiers"]),
            coarse_training_epochs=int(payload["coarse_training_epochs"]),
            max_coarse_training_candidates=int(payload["max_coarse_training_candidates"]),
            short_training_epochs=int(payload["short_training_epochs"]),
            max_short_training_candidates=int(payload["max_short_training_candidates"]),
            final_training_epochs=int(payload["final_training_epochs"]),
            practical_equivalence_mev_per_a=float(payload["practical_equivalence_mev_per_a"]),
            coarse_practical_equivalence_mev_per_a=float(payload["coarse_practical_equivalence_mev_per_a"]),
            screening_optimizer_seed=int(payload["screening_optimizer_seed"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("SIZE-HALVE2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SizeHalve2Candidate:
    target_size: int
    materializable: bool
    hard_coverage_qualified: bool
    repair_rung_digests: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size not in SIZE_HALVE2_FIXED_TARGET_SIZES:
            raise TrainingDataInputError("SIZE-HALVE2 candidate is outside the fixed eight-rung population.")
        digests = tuple(sorted((str(k), validate_digest(v, name="repair_rung_digest")) for k, v in self.repair_rung_digests))
        if not digests or len({k for k, _ in digests}) != len(digests):
            raise TrainingDataInputError("SIZE-HALVE2 candidate requires one repair-rung digest per domain.")
        if self.hard_coverage_qualified and not self.materializable:
            raise TrainingDataInputError("SIZE-HALVE2 unavailable candidate cannot be hard-qualified.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "repair_rung_digests", digests)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": SIZE_HALVE2_CANDIDATE_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "hard_coverage_qualified": self.hard_coverage_qualified,
            "repair_rung_digests": [list(v) for v in self.repair_rung_digests],
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeHalve2Candidate":
        if payload.get("schema") != SIZE_HALVE2_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-HALVE2 candidate schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            hard_coverage_qualified=bool(payload["hard_coverage_qualified"]),
            repair_rung_digests=tuple((str(v[0]), str(v[1])) for v in payload["repair_rung_digests"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("SIZE-HALVE2 candidate digest mismatch.")
        return result


def _evidence_map(evidence: Sequence[TargetSizeTrainingEvidence]) -> dict[int, TargetSizeTrainingEvidence]:
    out: dict[int, TargetSizeTrainingEvidence] = {}
    for item in evidence:
        if item.target_size in out:
            raise TrainingDataInputError(f"Duplicate SIZE-HALVE2 evidence for n{item.target_size}.")
        out[item.target_size] = item
    return out


def _common_screening_identity(evidence: Mapping[int, TargetSizeTrainingEvidence]) -> None:
    identities = (
        {x.foundation_identity_digest for x in evidence.values()},
        {x.evaluation_role_digest for x in evidence.values()},
        {x.training_policy_digest for x in evidence.values()},
        {x.schedule_digest for x in evidence.values()},
    )
    if any(len(v) != 1 for v in identities):
        raise TrainingDataInputError("SIZE-HALVE2 candidates must share foundation, evaluation role, TRAIN2 policy, and schedule identity.")


def _equivalence_aware_order(
    evidence: Sequence[TargetSizeTrainingEvidence], *, epsilon: float, boundary_preserve_size: int | None = None
) -> tuple[int, ...]:
    remaining = sorted(evidence, key=lambda x: (x.target_force_score_mev_per_a, x.target_size))
    ordered: list[int] = []
    boundary = None if boundary_preserve_size is None else int(boundary_preserve_size)
    while remaining:
        anchor = remaining[0].target_force_score_mev_per_a
        band = [x for x in remaining if x.target_force_score_mev_per_a <= anchor + float(epsilon) + 1.0e-12]
        band.sort(key=lambda x: (0 if boundary is not None and x.target_size == boundary else 1, x.target_size))
        ordered.extend(x.target_size for x in band)
        band_sizes = {x.target_size for x in band}
        remaining = [x for x in remaining if x.target_size not in band_sizes]
    return tuple(ordered)


@dataclass(frozen=True, slots=True, eq=False)
class SizeHalve2Plan:
    dataset_id: str
    target_multi_view_repair_digest: str
    target_multi_view_qualification_digest: str
    policy: SizeHalve2Policy
    candidates: tuple[SizeHalve2Candidate, ...]
    coverage_qualified_sizes: tuple[int, ...]
    coarse_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    stage_b0_survivor_sizes: tuple[int, ...] = ()
    short_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    stage_b1_finalist_sizes: tuple[int, ...] = ()
    final_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    selected_target_size: int | None = None
    outcome: str = _READY
    decision_reason: str = "hard-qualified fixed-size population frozen; awaiting SIZE-FIDELITY2"
    authority_version: str = SIZE_HALVE2_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("SIZE-HALVE2 dataset_id cannot be empty.")
        object.__setattr__(self, "target_multi_view_repair_digest", validate_digest(self.target_multi_view_repair_digest, name="target_multi_view_repair_digest"))
        object.__setattr__(self, "target_multi_view_qualification_digest", validate_digest(self.target_multi_view_qualification_digest, name="target_multi_view_qualification_digest"))
        candidates = tuple(sorted(self.candidates, key=lambda v: v.target_size))
        if tuple(v.target_size for v in candidates) != self.policy.target_sizes:
            raise TrainingDataInputError("SIZE-HALVE2 candidates must contain the exact fixed eight-rung population.")
        qualified = tuple(int(v) for v in self.coverage_qualified_sizes)
        expected_qualified = tuple(v.target_size for v in candidates if v.hard_coverage_qualified)
        if qualified != expected_qualified:
            raise TrainingDataInputError("SIZE-HALVE2 qualified-size list contradicts candidate evidence.")
        coarse = tuple(sorted(self.coarse_training_evidence, key=lambda v: v.target_size))
        stage_b0 = tuple(int(v) for v in self.stage_b0_survivor_sizes)
        short = tuple(sorted(self.short_training_evidence, key=lambda v: v.target_size))
        finalists = tuple(int(v) for v in self.stage_b1_finalist_sizes)
        finals = tuple(sorted(self.final_training_evidence, key=lambda v: v.target_size))
        selected = None if self.selected_target_size is None else int(self.selected_target_size)
        if any(v.target_size not in qualified for v in coarse):
            raise TrainingDataInputError("SIZE-HALVE2 coarse evidence contains a coverage-failing size.")
        if stage_b0 and (len(stage_b0) != self.policy.max_coarse_training_candidates or any(v not in qualified for v in stage_b0)):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-3 survivor set must contain exactly four hard-qualified sizes.")
        if any(v.target_size not in stage_b0 for v in short):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-10 evidence exists outside epoch-3 survivors.")
        if finalists and (len(finalists) != self.policy.max_short_training_candidates or any(v not in stage_b0 for v in finalists)):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-10 finalist set must contain exactly two epoch-3 survivors.")
        if any(v.target_size not in finalists for v in finals):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-30 evidence exists outside finalists.")
        if selected is not None and selected not in finalists:
            raise TrainingDataInputError("SIZE-HALVE2 selected target size is not a finalist.")
        allowed = {_READY, _BLOCKED_MVQUAL, _BLOCKED_COVERAGE, _WAIT_SHORT, _WAIT_FINAL, _SELECTED, _NONCONVERGED, _FAILED}
        if self.outcome not in allowed:
            raise TrainingDataInputError("Unsupported SIZE-HALVE2 outcome.")
        if self.outcome in {_READY, _BLOCKED_MVQUAL, _BLOCKED_COVERAGE} and (coarse or stage_b0 or short or finalists or finals or selected is not None):
            raise TrainingDataInputError("SIZE-HALVE2 pre-training state contains learning evidence.")
        if self.outcome == _READY and len(qualified) < self.policy.min_coverage_qualifiers:
            raise TrainingDataInputError("SIZE-HALVE2 ready state requires at least four hard qualifiers.")
        if self.outcome == _BLOCKED_COVERAGE and len(qualified) >= self.policy.min_coverage_qualifiers:
            raise TrainingDataInputError("SIZE-HALVE2 coverage-blocked state contradicts qualifier count.")
        if self.outcome == _WAIT_SHORT and (len(stage_b0) != 4 or short or finalists or finals or selected is not None):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-10 wait state is inconsistent.")
        if self.outcome == _WAIT_FINAL and (len(finalists) != 2 or finals or selected is not None):
            raise TrainingDataInputError("SIZE-HALVE2 epoch-30 wait state is inconsistent.")
        if self.outcome == _SELECTED and selected is None:
            raise TrainingDataInputError("SIZE-HALVE2 selected outcome requires selected_target_size.")
        if self.authority_version != SIZE_HALVE2_VERSION:
            raise TrainingDataInputError("Unsupported SIZE-HALVE2 authority version.")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "coverage_qualified_sizes", qualified)
        object.__setattr__(self, "coarse_training_evidence", coarse)
        object.__setattr__(self, "stage_b0_survivor_sizes", stage_b0)
        object.__setattr__(self, "short_training_evidence", short)
        object.__setattr__(self, "stage_b1_finalist_sizes", finalists)
        object.__setattr__(self, "final_training_evidence", finals)
        object.__setattr__(self, "selected_target_size", selected)

    @property
    def training_candidate_sizes(self) -> tuple[int, ...]:
        """Only independently hard-qualified sizes are allowed to purchase TRAIN2."""
        return self.coverage_qualified_sizes if self.outcome not in {_BLOCKED_MVQUAL, _BLOCKED_COVERAGE} else ()

    @property
    def complete(self) -> bool:
        return self.outcome in {_BLOCKED_MVQUAL, _BLOCKED_COVERAGE, _SELECTED, _NONCONVERGED, _FAILED}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIZE_HALVE2_PLAN_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_multi_view_repair_digest": self.target_multi_view_repair_digest,
            "target_multi_view_qualification_digest": self.target_multi_view_qualification_digest,
            "policy": self.policy.to_dict(),
            "candidates": [v.to_dict() for v in self.candidates],
            "coverage_qualified_sizes": list(self.coverage_qualified_sizes),
            "coarse_training_evidence": [v.to_dict() for v in self.coarse_training_evidence],
            "stage_b0_survivor_sizes": list(self.stage_b0_survivor_sizes),
            "short_training_evidence": [v.to_dict() for v in self.short_training_evidence],
            "stage_b1_finalist_sizes": list(self.stage_b1_finalist_sizes),
            "final_training_evidence": [v.to_dict() for v in self.final_training_evidence],
            "selected_target_size": self.selected_target_size,
            "outcome": self.outcome,
            "decision_reason": self.decision_reason,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SizeHalve2Plan":
        if payload.get("schema") != SIZE_HALVE2_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SIZE-HALVE2 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_multi_view_repair_digest=str(payload["target_multi_view_repair_digest"]),
            target_multi_view_qualification_digest=str(payload["target_multi_view_qualification_digest"]),
            policy=SizeHalve2Policy.from_dict(payload["policy"]),
            candidates=tuple(SizeHalve2Candidate.from_dict(v) for v in payload["candidates"]),
            coverage_qualified_sizes=tuple(int(v) for v in payload["coverage_qualified_sizes"]),
            coarse_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("coarse_training_evidence", ())),
            stage_b0_survivor_sizes=tuple(int(v) for v in payload.get("stage_b0_survivor_sizes", ())),
            short_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("short_training_evidence", ())),
            stage_b1_finalist_sizes=tuple(int(v) for v in payload.get("stage_b1_finalist_sizes", ())),
            final_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("final_training_evidence", ())),
            selected_target_size=None if payload.get("selected_target_size") is None else int(payload["selected_target_size"]),
            outcome=str(payload["outcome"]),
            decision_reason=str(payload.get("decision_reason", "")),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("SIZE-HALVE2 plan digest mismatch.")
        return result


def _repair_candidate_rows(target_multi_view_repair: Any, mv_qualified_sizes: Sequence[int]) -> tuple[SizeHalve2Candidate, ...]:
    domains = tuple(target_multi_view_repair.domains)
    if not domains:
        raise TrainingDataInputError("SIZE-HALVE2 requires at least one repaired target domain.")
    by_domain: dict[str, dict[int, Any]] = {}
    for domain in domains:
        rungs = {int(v.target_size): v for v in domain.rungs}
        if tuple(sorted(rungs)) != SIZE_HALVE2_FIXED_TARGET_SIZES:
            raise TrainingDataInputError("SIZE-HALVE2 requires the exact fixed eight-rung MV repair population in every domain.")
        by_domain[str(domain.label_domain_id)] = rungs
    qualified_set = set(int(v) for v in mv_qualified_sizes)
    if any(v not in SIZE_HALVE2_FIXED_TARGET_SIZES for v in qualified_set):
        raise TrainingDataInputError("SIZE-HALVE2 MVQUAL contains a size outside the frozen fixed population.")
    rows: list[SizeHalve2Candidate] = []
    for size in SIZE_HALVE2_FIXED_TARGET_SIZES:
        rungs = [(label, by_domain[label][size]) for label in sorted(by_domain)]
        materializable = all(bool(r.materializable) for _, r in rungs)
        if size in qualified_set and not materializable:
            raise TrainingDataInputError("SIZE-HALVE2 MVQUAL marked an unavailable MV rung as hard-qualified.")
        rows.append(SizeHalve2Candidate(
            target_size=size,
            materializable=materializable,
            hard_coverage_qualified=size in qualified_set,
            repair_rung_digests=tuple((label, digest(r.to_dict())) for label, r in rungs),
        ))
    return tuple(rows)


def build_size_halve2_plan(
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    *,
    policy: SizeHalve2Policy | None = None,
) -> SizeHalve2Plan:
    """Freeze the future fixed-eight candidate population without migrating production authority."""

    policy = policy or SizeHalve2Policy()
    if target_multi_view_repair.dataset_id != target_multi_view_qualification.dataset_id:
        raise TrainingDataInputError("SIZE-HALVE2 repair/MVQUAL dataset identities differ.")
    if target_multi_view_qualification.target_multi_view_repair_digest != target_multi_view_repair.content_digest:
        raise TrainingDataInputError("SIZE-HALVE2 MVQUAL no longer matches REPAIR1.")
    rows = _repair_candidate_rows(target_multi_view_repair, target_multi_view_qualification.mv_qualified_sizes)
    qualified = tuple(v.target_size for v in rows if v.hard_coverage_qualified)
    nonregression = bool(
        target_multi_view_qualification.same_n_non_regression_passed
        and target_multi_view_qualification.n95_non_regression_passed
    )
    if not nonregression:
        outcome = _BLOCKED_MVQUAL
        reason = "MVQUAL1 same-N/N95 non-regression did not pass; SIZE-HALVE2 cannot purchase training"
    elif len(qualified) < policy.min_coverage_qualifiers:
        outcome = _BLOCKED_COVERAGE
        reason = (
            f"only {len(qualified)} of eight fixed sizes are independently hard-qualified; "
            f"at least {policy.min_coverage_qualifiers} are required before TRAIN2"
        )
    else:
        outcome = _READY
        reason = (
            f"{len(qualified)} hard-qualified fixed sizes frozen for future epoch-3 admission; "
            "only these sizes may purchase TRAIN2"
        )
    return SizeHalve2Plan(
        dataset_id=target_multi_view_repair.dataset_id,
        target_multi_view_repair_digest=target_multi_view_repair.content_digest,
        target_multi_view_qualification_digest=target_multi_view_qualification.content_digest,
        policy=policy,
        candidates=rows,
        coverage_qualified_sizes=qualified,
        outcome=outcome,
        decision_reason=reason,
    )


def with_size_halve2_epoch3_evidence(plan: SizeHalve2Plan, evidence: Sequence[TargetSizeTrainingEvidence]) -> SizeHalve2Plan:
    """Apply the exact 3-of-30 screen and retain exactly four candidates."""

    if plan.outcome != _READY:
        raise TrainingDataInputError("SIZE-HALVE2 epoch-3 evidence can only attach to a ready plan.")
    by_size = _evidence_map(evidence)
    expected = set(plan.coverage_qualified_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(
            "SIZE-HALVE2 epoch-3 evidence must cover exactly the hard-qualified sizes; "
            f"missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}."
        )
    expected_progress = plan.policy.coarse_training_epochs / plan.policy.final_training_epochs
    for item in by_size.values():
        if item.stage != "coarse" or item.completed_epochs != plan.policy.coarse_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("SIZE-HALVE2 coarse evidence is not the exact 3-of-30 screening boundary.")
        if not math.isclose(item.normalized_schedule_progress, expected_progress, rel_tol=0.0, abs_tol=1.0e-12):
            raise TrainingDataInputError("SIZE-HALVE2 coarse evidence is not at exact 3/30 normalized schedule progress.")
    _common_screening_identity(by_size)
    admissible = tuple(v for v in by_size.values() if v.admissible_for_screening)
    if len(admissible) < plan.policy.max_coarse_training_candidates:
        return SizeHalve2Plan(
            plan.dataset_id, plan.target_multi_view_repair_digest, plan.target_multi_view_qualification_digest,
            plan.policy, plan.candidates, plan.coverage_qualified_sizes,
            coarse_training_evidence=tuple(by_size.values()), outcome=_FAILED,
            decision_reason="epoch-3 screen left fewer than four numerically valid hard-qualified candidates",
        )
    boundary = max(plan.coverage_qualified_sizes)
    ranking = _equivalence_aware_order(
        admissible,
        epsilon=float(plan.policy.coarse_practical_equivalence_mev_per_a),
        boundary_preserve_size=boundary,
    )
    survivors = tuple(ranking[: plan.policy.max_coarse_training_candidates])
    return SizeHalve2Plan(
        plan.dataset_id, plan.target_multi_view_repair_digest, plan.target_multi_view_qualification_digest,
        plan.policy, plan.candidates, plan.coverage_qualified_sizes,
        coarse_training_evidence=tuple(by_size.values()), stage_b0_survivor_sizes=survivors,
        outcome=_WAIT_SHORT,
        decision_reason="epoch-3 hard-qualified-only screen retained " + ", ".join(f"n{v}" for v in survivors),
    )


def with_size_halve2_epoch10_evidence(plan: SizeHalve2Plan, evidence: Sequence[TargetSizeTrainingEvidence]) -> SizeHalve2Plan:
    """Continue the four epoch-3 survivors to epoch 10 and retain two."""

    if plan.outcome != _WAIT_SHORT:
        raise TrainingDataInputError("SIZE-HALVE2 epoch-10 evidence can only attach while awaiting epoch 10.")
    by_size = _evidence_map(evidence)
    expected = set(plan.stage_b0_survivor_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(
            f"SIZE-HALVE2 epoch-10 evidence must cover all four epoch-3 survivors; missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}."
        )
    coarse = {v.target_size: v for v in plan.coarse_training_evidence}
    for size, item in by_size.items():
        if item.stage != "short" or item.completed_epochs != plan.policy.short_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("SIZE-HALVE2 short evidence is not the exact 10-of-30 boundary.")
        parent = coarse.get(size)
        if parent is None or (item.parent_checkpoint_digest, item.parent_optimizer_state_digest, item.parent_rng_state_digest) != (parent.checkpoint_digest, parent.optimizer_state_digest, parent.rng_state_digest):
            raise TrainingDataInputError(f"SIZE-HALVE2 epoch-10 continuation ancestry differs from epoch 3 for n{size}.")
        for attr, label in (("foundation_identity_digest", "foundation"), ("evaluation_role_digest", "evaluation role"), ("training_policy_digest", "TRAIN2 policy"), ("training_run_digest", "training run"), ("schedule_digest", "schedule")):
            if getattr(item, attr) != getattr(parent, attr):
                raise TrainingDataInputError(f"SIZE-HALVE2 {label} identity changed between epoch 3 and epoch 10 for n{size}.")
        if item.optimizer_update_count <= parent.optimizer_update_count or item.structures_presented <= parent.structures_presented:
            raise TrainingDataInputError(f"SIZE-HALVE2 epoch-10 exposure did not advance beyond epoch 3 for n{size}.")
        expected_progress = plan.policy.short_training_epochs / plan.policy.final_training_epochs
        if not math.isclose(item.normalized_schedule_progress, expected_progress, rel_tol=0.0, abs_tol=1.0e-12):
            raise TrainingDataInputError("SIZE-HALVE2 short evidence is not at exact 10/30 normalized schedule progress.")
    _common_screening_identity(by_size)
    admissible = tuple(v for v in by_size.values() if v.admissible_for_screening)
    if len(admissible) < 2:
        return SizeHalve2Plan(
            plan.dataset_id, plan.target_multi_view_repair_digest, plan.target_multi_view_qualification_digest,
            plan.policy, plan.candidates, plan.coverage_qualified_sizes,
            plan.coarse_training_evidence, plan.stage_b0_survivor_sizes, tuple(by_size.values()),
            outcome=_FAILED, decision_reason="epoch-10 screen left fewer than two numerically valid candidates",
        )
    ranking = _equivalence_aware_order(
        admissible,
        epsilon=plan.policy.practical_equivalence_mev_per_a,
        boundary_preserve_size=max(plan.coverage_qualified_sizes),
    )
    finalists = tuple(ranking[:2])
    return SizeHalve2Plan(
        plan.dataset_id, plan.target_multi_view_repair_digest, plan.target_multi_view_qualification_digest,
        plan.policy, plan.candidates, plan.coverage_qualified_sizes,
        plan.coarse_training_evidence, plan.stage_b0_survivor_sizes, tuple(by_size.values()), finalists,
        outcome=_WAIT_FINAL,
        decision_reason="epoch-10 continuation screen retained " + ", ".join(f"n{v}" for v in finalists),
    )


def with_size_halve2_epoch30_evidence(plan: SizeHalve2Plan, evidence: Sequence[TargetSizeTrainingEvidence]) -> SizeHalve2Plan:
    """Complete both finalists at epoch 30 and select one or diagnose ceiling non-convergence."""

    if plan.outcome != _WAIT_FINAL:
        raise TrainingDataInputError("SIZE-HALVE2 epoch-30 evidence can only attach while awaiting epoch 30.")
    by_size = _evidence_map(evidence)
    expected = set(plan.stage_b1_finalist_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(
            f"SIZE-HALVE2 epoch-30 evidence must cover both finalists; missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}."
        )
    short = {v.target_size: v for v in plan.short_training_evidence}
    for size, item in by_size.items():
        if item.stage != "final" or item.completed_epochs != plan.policy.final_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("SIZE-HALVE2 final evidence is not the exact 30-of-30 boundary.")
        parent = short.get(size)
        if parent is None or (item.parent_checkpoint_digest, item.parent_optimizer_state_digest, item.parent_rng_state_digest) != (parent.checkpoint_digest, parent.optimizer_state_digest, parent.rng_state_digest):
            raise TrainingDataInputError(f"SIZE-HALVE2 epoch-30 continuation ancestry differs from epoch 10 for n{size}.")
        for attr, label in (("foundation_identity_digest", "foundation"), ("evaluation_role_digest", "evaluation role"), ("training_policy_digest", "TRAIN2 policy"), ("training_run_digest", "training run"), ("schedule_digest", "schedule")):
            if getattr(item, attr) != getattr(parent, attr):
                raise TrainingDataInputError(f"SIZE-HALVE2 {label} identity changed after epoch 10 for n{size}.")
        if item.optimizer_update_count <= parent.optimizer_update_count or item.structures_presented <= parent.structures_presented:
            raise TrainingDataInputError(f"SIZE-HALVE2 epoch-30 exposure did not advance beyond epoch 10 for n{size}.")
    admissible = tuple(v for v in by_size.values() if v.admissible_for_stage_c)
    common = dict(
        dataset_id=plan.dataset_id,
        target_multi_view_repair_digest=plan.target_multi_view_repair_digest,
        target_multi_view_qualification_digest=plan.target_multi_view_qualification_digest,
        policy=plan.policy,
        candidates=plan.candidates,
        coverage_qualified_sizes=plan.coverage_qualified_sizes,
        coarse_training_evidence=plan.coarse_training_evidence,
        stage_b0_survivor_sizes=plan.stage_b0_survivor_sizes,
        short_training_evidence=plan.short_training_evidence,
        stage_b1_finalist_sizes=plan.stage_b1_finalist_sizes,
        final_training_evidence=tuple(by_size.values()),
    )
    if not admissible:
        return SizeHalve2Plan(**common, outcome=_FAILED, decision_reason="both epoch-30 finalists failed final admissibility")
    ranking = _equivalence_aware_order(admissible, epsilon=plan.policy.practical_equivalence_mev_per_a)
    winner = ranking[0]
    boundary = max(plan.coverage_qualified_sizes)
    if winner == boundary:
        smaller = [v for v in admissible if v.target_size < boundary]
        if not smaller:
            return SizeHalve2Plan(**common, outcome=_NONCONVERGED, decision_reason=f"fixed-ceiling boundary n{boundary} is the only admissible finalist")
        best_smaller = min(smaller, key=lambda v: (v.target_force_score_mev_per_a, v.target_size))
        improvement = best_smaller.target_force_score_mev_per_a - by_size[boundary].target_force_score_mev_per_a
        if improvement > plan.policy.practical_equivalence_mev_per_a + 1.0e-12:
            return SizeHalve2Plan(**common, outcome=_NONCONVERGED, decision_reason=f"fixed-ceiling boundary n{boundary} improves target force score by {improvement:.6g} meV/A beyond practical equivalence")
    return SizeHalve2Plan(**common, selected_target_size=winner, outcome=_SELECTED, decision_reason=f"epoch-30 selected n{winner} after target/replay/physical qualification")


def build_size_halve2_execution_stage_plan(plan: SizeHalve2Plan) -> Any:
    """Translate SIZE-HALVE2 state into the existing PERF-P2R work geometry."""

    from .perf_p2r import PerfP2RStagePlan

    common = dict(
        convergence_digest=plan.content_digest,
        planned_final_epoch=plan.policy.final_training_epochs,
    )
    if plan.outcome == _READY:
        return PerfP2RStagePlan(
            **common, stage="coarse", candidate_sizes=plan.coverage_qualified_sizes,
            start_epoch=0, target_epoch=plan.policy.coarse_training_epochs,
            screening_optimizer_seed=plan.policy.screening_optimizer_seed, continuation_required=False,
            target_only_evaluation=True, replay_diagnostic_authorized=False, physical_qualification_authorized=False,
        )
    if plan.outcome == _WAIT_SHORT:
        return PerfP2RStagePlan(
            **common, stage="short", candidate_sizes=plan.stage_b0_survivor_sizes,
            start_epoch=plan.policy.coarse_training_epochs, target_epoch=plan.policy.short_training_epochs,
            screening_optimizer_seed=plan.policy.screening_optimizer_seed, continuation_required=True,
            target_only_evaluation=False, replay_diagnostic_authorized=True, physical_qualification_authorized=False,
        )
    if plan.outcome == _WAIT_FINAL:
        return PerfP2RStagePlan(
            **common, stage="final", candidate_sizes=plan.stage_b1_finalist_sizes,
            start_epoch=plan.policy.short_training_epochs, target_epoch=plan.policy.final_training_epochs,
            screening_optimizer_seed=plan.policy.screening_optimizer_seed, continuation_required=True,
            target_only_evaluation=False, replay_diagnostic_authorized=True, physical_qualification_authorized=True,
        )
    if plan.outcome == _SELECTED:
        return PerfP2RStagePlan(
            **common, stage="production", candidate_sizes=(int(plan.selected_target_size),),
            start_epoch=0, target_epoch=plan.policy.final_training_epochs, screening_optimizer_seed=None,
            continuation_required=False, target_only_evaluation=False, replay_diagnostic_authorized=True,
            physical_qualification_authorized=True,
        )
    raise TrainingDataInputError(f"SIZE-HALVE2 outcome {plan.outcome!r} does not authorize training work.")


def validate_size_halve2_authority(
    plan: SizeHalve2Plan,
    *,
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    policy: SizeHalve2Policy | None = None,
) -> None:
    """Validate fixed population, lineage, and pre-migration hard-admission evidence."""

    policy = policy or SizeHalve2Policy()
    if plan.dataset_id != target_multi_view_repair.dataset_id or plan.dataset_id != target_multi_view_qualification.dataset_id:
        raise TrainingDataInputError("SIZE-HALVE2 dataset lineage changed.")
    if plan.target_multi_view_repair_digest != target_multi_view_repair.content_digest or plan.target_multi_view_qualification_digest != target_multi_view_qualification.content_digest:
        raise TrainingDataInputError("SIZE-HALVE2 upstream authority changed.")
    if plan.policy.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("SIZE-HALVE2 policy changed.")
    expected_rows = _repair_candidate_rows(target_multi_view_repair, target_multi_view_qualification.mv_qualified_sizes)
    if tuple(v.to_dict()["content_digest"] for v in plan.candidates) != tuple(v.to_dict()["content_digest"] for v in expected_rows):
        raise TrainingDataInputError("SIZE-HALVE2 candidate evidence changed.")
    expected_qualified = tuple(v.target_size for v in expected_rows if v.hard_coverage_qualified)
    if plan.coverage_qualified_sizes != expected_qualified:
        raise TrainingDataInputError("SIZE-HALVE2 hard-qualified population changed.")
    if any(v.target_size not in plan.coverage_qualified_sizes for v in plan.coarse_training_evidence):
        raise TrainingDataInputError("SIZE-HALVE2 contains training evidence for a coverage-failing candidate.")

