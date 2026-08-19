"""TARGET-DATA2E production target-corpus decision and provenance authority.

This gate is deliberately pure and fail-closed.  It does not run target-size
training and it never invents a winner.  It can be materialized only after
TARGET-DATA2D has completed with a genuine ``selected`` outcome.  The resulting
authority freezes the exact winning nested-corpus membership plus enough
upstream evidence to audit the decision independently of the later production
CV/seed campaign.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .foundation_audit import FoundationTargetAudit
from .target_coverage import TargetCoveragePolicy, TargetCoverageReference, TargetCoverageReport
from .target_data_roles import TargetDataRoleFreeze
from .target_ladder import (
    TARGET_DATA_LADDER_VERSION, TARGET_DATA_LADDER_MV_VERSION, TargetDataLadderPlan, TargetDataLadderRung,
    validate_target_data_ladder_authority, validate_migrated_target_data_ladder_authority,
)
from .target_size_convergence import (
    TARGET_SIZE_CONVERGENCE_VERSION, TARGET_SIZE_CONVERGENCE_MV_VERSION,
    TargetSizeConvergencePlan,
    TargetSizeTrainingEvidence,
    validate_target_size_convergence_authority,
)

TARGET_PRODUCTION_RUNG_PROVENANCE_SCHEMA = "mdstats.target-production-rung-provenance.v1"
TARGET_PRODUCTION_EQUIVALENCE_COMPARISON_SCHEMA = "mdstats.target-production-equivalence-comparison.v1"
TARGET_PRODUCTION_DOMAIN_DECISION_SCHEMA = "mdstats.target-production-domain-decision.v1"
TARGET_PRODUCTION_CORPUS_DECISION_SCHEMA = "mdstats.target-production-corpus-decision.v2"
TARGET_PRODUCTION_CORPUS_MV_DECISION_SCHEMA = "mdstats.target-production-corpus-decision.v3"
TARGET_PRODUCTION_CORPUS_VERSION = "mdstats.target-data2e.production-corpus.2026-08.v2"
TARGET_PRODUCTION_CORPUS_MV_VERSION = "mdstats.target-data2e.production-corpus.2026-08.v3"


class TargetProductionCorpusDecisionError(TrainingDataInputError):
    """TARGET-DATA2E cannot make a qualified production-corpus decision."""


def _membership_digest(label_domain_id: str, target_size: int, frame_uids: Sequence[str]) -> str:
    return digest(
        {
            "schema": "mdstats.target-production-membership.v1",
            "label_domain_id": str(label_domain_id),
            "target_size": int(target_size),
            "frame_uids": list(frame_uids),
        }
    )


@dataclass(frozen=True, slots=True)
class TargetProductionRungProvenance:
    """Auditable identity for one requested rung in one label domain."""

    target_size: int
    materializable: bool
    membership_digest: str | None
    rung_content_digest: str
    coverage_report_digest: str | None
    coverage_passed: bool | None
    mandatory_obligations_passed: bool | None

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size <= 0:
            raise TrainingDataInputError("TARGET-DATA2E rung target_size must be positive.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "rung_content_digest", validate_digest(self.rung_content_digest, name="rung_content_digest"))
        if self.materializable:
            if self.membership_digest is None or self.coverage_report_digest is None:
                raise TrainingDataInputError("TARGET-DATA2E materialized rung requires membership and coverage digests.")
            object.__setattr__(self, "membership_digest", validate_digest(self.membership_digest, name="membership_digest"))
            object.__setattr__(self, "coverage_report_digest", validate_digest(self.coverage_report_digest, name="coverage_report_digest"))
            if self.coverage_passed is None or self.mandatory_obligations_passed is None:
                raise TrainingDataInputError("TARGET-DATA2E materialized rung requires pass/fail evidence.")
        else:
            if any(value is not None for value in (
                self.membership_digest,
                self.coverage_report_digest,
                self.coverage_passed,
                self.mandatory_obligations_passed,
            )):
                raise TrainingDataInputError("TARGET-DATA2E unavailable rung cannot carry fabricated evidence.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_PRODUCTION_RUNG_PROVENANCE_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "membership_digest": self.membership_digest,
            "rung_content_digest": self.rung_content_digest,
            "coverage_report_digest": self.coverage_report_digest,
            "coverage_passed": self.coverage_passed,
            "mandatory_obligations_passed": self.mandatory_obligations_passed,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetProductionRungProvenance":
        if payload.get("schema") != TARGET_PRODUCTION_RUNG_PROVENANCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2E rung-provenance schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            membership_digest=None if payload.get("membership_digest") is None else str(payload["membership_digest"]),
            rung_content_digest=str(payload["rung_content_digest"]),
            coverage_report_digest=None if payload.get("coverage_report_digest") is None else str(payload["coverage_report_digest"]),
            coverage_passed=None if payload.get("coverage_passed") is None else bool(payload["coverage_passed"]),
            mandatory_obligations_passed=None if payload.get("mandatory_obligations_passed") is None else bool(payload["mandatory_obligations_passed"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2E rung-provenance digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetProductionEquivalenceComparison:
    """Explicit audit record for a practical-equivalence comparison."""

    stage: str
    smaller_target_size: int
    larger_target_size: int
    smaller_target_score_mev_per_a: float
    larger_target_score_mev_per_a: float
    absolute_score_delta_mev_per_a: float
    threshold_mev_per_a: float
    practically_equivalent: bool
    smaller_preferred_when_equivalent: bool

    def __post_init__(self) -> None:
        stage = str(self.stage).strip().lower()
        if stage not in {"short", "final"}:
            raise TrainingDataInputError("TARGET-DATA2E comparison stage must be short or final.")
        smaller, larger = int(self.smaller_target_size), int(self.larger_target_size)
        if smaller <= 0 or larger <= smaller:
            raise TrainingDataInputError("TARGET-DATA2E equivalence comparison sizes are invalid.")
        s0, s1 = float(self.smaller_target_score_mev_per_a), float(self.larger_target_score_mev_per_a)
        delta, threshold = float(self.absolute_score_delta_mev_per_a), float(self.threshold_mev_per_a)
        if any(not math.isfinite(v) or v < 0.0 for v in (s0, s1, delta)) or not math.isfinite(threshold) or threshold <= 0.0:
            raise TrainingDataInputError("TARGET-DATA2E equivalence comparison values are invalid.")
        expected_delta = abs(s0 - s1)
        if abs(delta - expected_delta) > 1.0e-12:
            raise TrainingDataInputError("TARGET-DATA2E equivalence comparison delta is inconsistent.")
        expected_equivalent = delta <= threshold + 1.0e-12
        if bool(self.practically_equivalent) != expected_equivalent:
            raise TrainingDataInputError("TARGET-DATA2E practical-equivalence flag is inconsistent.")
        if bool(self.smaller_preferred_when_equivalent) != expected_equivalent:
            raise TrainingDataInputError("TARGET-DATA2E smaller-size preference must match practical equivalence.")
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "smaller_target_size", smaller)
        object.__setattr__(self, "larger_target_size", larger)
        object.__setattr__(self, "smaller_target_score_mev_per_a", s0)
        object.__setattr__(self, "larger_target_score_mev_per_a", s1)
        object.__setattr__(self, "absolute_score_delta_mev_per_a", delta)
        object.__setattr__(self, "threshold_mev_per_a", threshold)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_PRODUCTION_EQUIVALENCE_COMPARISON_SCHEMA,
            "stage": self.stage,
            "smaller_target_size": self.smaller_target_size,
            "larger_target_size": self.larger_target_size,
            "smaller_target_score_mev_per_a": self.smaller_target_score_mev_per_a,
            "larger_target_score_mev_per_a": self.larger_target_score_mev_per_a,
            "absolute_score_delta_mev_per_a": self.absolute_score_delta_mev_per_a,
            "threshold_mev_per_a": self.threshold_mev_per_a,
            "practically_equivalent": self.practically_equivalent,
            "smaller_preferred_when_equivalent": self.smaller_preferred_when_equivalent,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetProductionEquivalenceComparison":
        if payload.get("schema") != TARGET_PRODUCTION_EQUIVALENCE_COMPARISON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2E equivalence-comparison schema.")
        result = cls(
            stage=str(payload["stage"]),
            smaller_target_size=int(payload["smaller_target_size"]),
            larger_target_size=int(payload["larger_target_size"]),
            smaller_target_score_mev_per_a=float(payload["smaller_target_score_mev_per_a"]),
            larger_target_score_mev_per_a=float(payload["larger_target_score_mev_per_a"]),
            absolute_score_delta_mev_per_a=float(payload["absolute_score_delta_mev_per_a"]),
            threshold_mev_per_a=float(payload["threshold_mev_per_a"]),
            practically_equivalent=bool(payload["practically_equivalent"]),
            smaller_preferred_when_equivalent=bool(payload["smaller_preferred_when_equivalent"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2E equivalence-comparison digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetProductionDomainDecision:
    """Winning corpus and complete rung provenance for one label domain."""

    label_domain_id: str
    target_size: int
    frame_uids: tuple[str, ...]
    membership_digest: str
    role_domain_digest: str
    outer_partition_digest: str
    cross_validation_plan_digest: str
    reference_domain_digest: str
    ladder_domain_digest: str
    master_order_digest: str
    selected_rung_digest: str
    selected_coverage_report: TargetCoverageReport
    coverage_family_reference_digests: tuple[tuple[str, str], ...]
    foundation_residual_family_reference_digests: tuple[tuple[str, str], ...]
    stratum_reference_digests: tuple[tuple[str, str], ...]
    foundation_audit_domain_digest: str
    rung_provenance: tuple[TargetProductionRungProvenance, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.label_domain_id).strip():
            raise TrainingDataInputError("TARGET-DATA2E label_domain_id must be non-empty.")
        size = int(self.target_size)
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if size <= 0 or len(frames) != size or len(set(frames)) != len(frames):
            raise TrainingDataInputError("TARGET-DATA2E winning corpus membership is inconsistent.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "frame_uids", frames)
        for name in (
            "membership_digest",
            "role_domain_digest",
            "outer_partition_digest",
            "cross_validation_plan_digest",
            "reference_domain_digest",
            "ladder_domain_digest",
            "master_order_digest",
            "selected_rung_digest",
            "foundation_audit_domain_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        expected_membership = _membership_digest(self.label_domain_id, size, frames)
        if self.membership_digest != expected_membership:
            raise TrainingDataInputError("TARGET-DATA2E winning membership digest is inconsistent.")
        report = self.selected_coverage_report
        if report.label_domain_id != self.label_domain_id or report.selected_frame_uids != frames or not report.passed:
            raise TrainingDataInputError("TARGET-DATA2E selected coverage report does not authenticate the winning corpus.")
        family_refs = tuple(sorted((str(k), validate_digest(v, name="coverage_family_reference_digest")) for k, v in self.coverage_family_reference_digests))
        residual_refs = tuple(sorted((str(k), validate_digest(v, name="foundation_residual_family_reference_digest")) for k, v in self.foundation_residual_family_reference_digests))
        strata = tuple(sorted((str(k), validate_digest(v, name="stratum_reference_digest")) for k, v in self.stratum_reference_digests))
        if len({k for k, _ in family_refs}) != len(family_refs) or len({k for k, _ in strata}) != len(strata):
            raise TrainingDataInputError("TARGET-DATA2E reference provenance contains duplicate identities.")
        if any(item not in family_refs for item in residual_refs):
            raise TrainingDataInputError("TARGET-DATA2E residual-family provenance is not a subset of family provenance.")
        rung_prov = tuple(sorted(self.rung_provenance, key=lambda item: item.target_size))
        if not rung_prov or len({item.target_size for item in rung_prov}) != len(rung_prov):
            raise TrainingDataInputError("TARGET-DATA2E rung provenance must be unique and non-empty.")
        selected = [item for item in rung_prov if item.target_size == size]
        if len(selected) != 1 or not selected[0].materializable or selected[0].membership_digest != self.membership_digest:
            raise TrainingDataInputError("TARGET-DATA2E selected rung provenance is inconsistent.")
        object.__setattr__(self, "coverage_family_reference_digests", family_refs)
        object.__setattr__(self, "foundation_residual_family_reference_digests", residual_refs)
        object.__setattr__(self, "stratum_reference_digests", strata)
        object.__setattr__(self, "rung_provenance", rung_prov)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_PRODUCTION_DOMAIN_DECISION_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "target_size": self.target_size,
            "frame_uids": list(self.frame_uids),
            "membership_digest": self.membership_digest,
            "role_domain_digest": self.role_domain_digest,
            "outer_partition_digest": self.outer_partition_digest,
            "cross_validation_plan_digest": self.cross_validation_plan_digest,
            "reference_domain_digest": self.reference_domain_digest,
            "ladder_domain_digest": self.ladder_domain_digest,
            "master_order_digest": self.master_order_digest,
            "selected_rung_digest": self.selected_rung_digest,
            "selected_coverage_report": self.selected_coverage_report.to_dict(),
            "coverage_family_reference_digests": [[k, v] for k, v in self.coverage_family_reference_digests],
            "foundation_residual_family_reference_digests": [[k, v] for k, v in self.foundation_residual_family_reference_digests],
            "stratum_reference_digests": [[k, v] for k, v in self.stratum_reference_digests],
            "foundation_audit_domain_digest": self.foundation_audit_domain_digest,
            "rung_provenance": [item.to_dict() for item in self.rung_provenance],
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetProductionDomainDecision":
        if payload.get("schema") != TARGET_PRODUCTION_DOMAIN_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2E domain-decision schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            target_size=int(payload["target_size"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            membership_digest=str(payload["membership_digest"]),
            role_domain_digest=str(payload["role_domain_digest"]),
            outer_partition_digest=str(payload["outer_partition_digest"]),
            cross_validation_plan_digest=str(payload["cross_validation_plan_digest"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            ladder_domain_digest=str(payload["ladder_domain_digest"]),
            master_order_digest=str(payload["master_order_digest"]),
            selected_rung_digest=str(payload["selected_rung_digest"]),
            selected_coverage_report=TargetCoverageReport.from_dict(payload["selected_coverage_report"]),
            coverage_family_reference_digests=tuple((str(v[0]), str(v[1])) for v in payload["coverage_family_reference_digests"]),
            foundation_residual_family_reference_digests=tuple((str(v[0]), str(v[1])) for v in payload.get("foundation_residual_family_reference_digests", ())),
            stratum_reference_digests=tuple((str(v[0]), str(v[1])) for v in payload.get("stratum_reference_digests", ())),
            foundation_audit_domain_digest=str(payload["foundation_audit_domain_digest"]),
            rung_provenance=tuple(TargetProductionRungProvenance.from_dict(item) for item in payload["rung_provenance"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2E domain-decision digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetProductionCorpusDecision:
    """Immutable production target-corpus decision and audit report."""

    dataset_id: str
    selected_target_size: int
    source_catalog_digest: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    partition_policy_digest: str
    partition_unit_catalog_digest: str
    leakage_audit_digest: str
    target_data_role_freeze_digest: str
    foundation_target_audit_digest: str
    target_coverage_reference_digest: str
    target_data_ladder_digest: str
    target_size_convergence_digest: str
    coverage_policy: TargetCoveragePolicy
    ladder_policy_digest: str
    convergence_policy_digest: str
    stage_a_rung_digests: tuple[tuple[int, str], ...]
    stage_a_survivor_sizes: tuple[int, ...]
    stage_b0_survivor_sizes: tuple[int, ...]
    stage_b0_evidence: tuple[TargetSizeTrainingEvidence, ...]
    stage_b_finalist_sizes: tuple[int, ...]
    stage_b_evidence: tuple[TargetSizeTrainingEvidence, ...]
    stage_c_evidence: tuple[TargetSizeTrainingEvidence, ...]
    equivalence_comparisons: tuple[TargetProductionEquivalenceComparison, ...]
    domains: tuple[TargetProductionDomainDecision, ...]
    bounded_ladder_converged: bool
    decision_reason: str
    authority_version: str = TARGET_PRODUCTION_CORPUS_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip() or self.authority_version not in {TARGET_PRODUCTION_CORPUS_VERSION, TARGET_PRODUCTION_CORPUS_MV_VERSION}:
            raise TrainingDataInputError("TARGET-DATA2E authority identity/version is invalid.")
        size = int(self.selected_target_size)
        if size <= 0:
            raise TrainingDataInputError("TARGET-DATA2E selected_target_size must be positive.")
        object.__setattr__(self, "selected_target_size", size)
        for name in (
            "source_catalog_digest", "frame_catalog_digest", "data5_bundle_digest",
            "partition_policy_digest", "partition_unit_catalog_digest", "leakage_audit_digest",
            "target_data_role_freeze_digest", "foundation_target_audit_digest",
            "target_coverage_reference_digest", "target_data_ladder_digest",
            "target_size_convergence_digest", "ladder_policy_digest", "convergence_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        rungs = tuple(sorted((int(k), validate_digest(v, name="stage_a_rung_digest")) for k, v in self.stage_a_rung_digests))
        if not rungs or len({k for k, _ in rungs}) != len(rungs):
            raise TrainingDataInputError("TARGET-DATA2E Stage-A rung provenance is invalid.")
        survivors = tuple(int(v) for v in self.stage_a_survivor_sizes)
        coarse_survivors = tuple(int(v) for v in self.stage_b0_survivor_sizes)
        finalists = tuple(int(v) for v in self.stage_b_finalist_sizes)
        if tuple(sorted(set(survivors))) != survivors or not coarse_survivors or len(coarse_survivors) > 4 or any(v not in survivors for v in coarse_survivors) or len(finalists) != 2 or len(set(finalists)) != 2 or any(v not in coarse_survivors for v in finalists):
            raise TrainingDataInputError("TARGET-DATA2E Stage-A/B0/B1 size provenance is invalid.")
        if size not in finalists:
            raise TrainingDataInputError("TARGET-DATA2E selected size is not a Stage-C finalist.")
        coarse = tuple(sorted(self.stage_b0_evidence, key=lambda item: item.target_size))
        short = tuple(sorted(self.stage_b_evidence, key=lambda item: item.target_size))
        final = tuple(sorted(self.stage_c_evidence, key=lambda item: item.target_size))
        if any(item.stage != "coarse" for item in coarse) or any(item.stage != "short" for item in short) or any(item.stage != "final" for item in final):
            raise TrainingDataInputError("TARGET-DATA2E training evidence is attached to the wrong stage.")
        if {item.target_size for item in coarse} != set(survivors):
            raise TrainingDataInputError("TARGET-DATA2E Stage-B0 evidence is incomplete.")
        if {item.target_size for item in short} != set(coarse_survivors):
            raise TrainingDataInputError("TARGET-DATA2E Stage-B1 evidence is incomplete.")
        if {item.target_size for item in final} != set(finalists):
            raise TrainingDataInputError("TARGET-DATA2E Stage-C evidence is incomplete.")
        selected_final = [item for item in final if item.target_size == size]
        if len(selected_final) != 1 or not selected_final[0].admissible_for_stage_c:
            raise TrainingDataInputError("TARGET-DATA2E selected Stage-C evidence is not admissible.")
        comparisons = tuple(sorted(self.equivalence_comparisons, key=lambda item: (item.stage, item.smaller_target_size, item.larger_target_size)))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or any(item.target_size != size for item in domains) or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2E domain decisions are inconsistent with the selected size.")
        if not bool(self.bounded_ladder_converged):
            raise TrainingDataInputError("TARGET-DATA2E can only exist after bounded-ladder convergence is demonstrated.")
        reason = str(self.decision_reason).strip()
        if not reason:
            raise TrainingDataInputError("TARGET-DATA2E decision_reason must be non-empty.")
        object.__setattr__(self, "stage_a_rung_digests", rungs)
        object.__setattr__(self, "stage_a_survivor_sizes", survivors)
        object.__setattr__(self, "stage_b0_survivor_sizes", coarse_survivors)
        object.__setattr__(self, "stage_b0_evidence", coarse)
        object.__setattr__(self, "stage_b_finalist_sizes", finalists)
        object.__setattr__(self, "stage_b_evidence", short)
        object.__setattr__(self, "stage_c_evidence", final)
        object.__setattr__(self, "equivalence_comparisons", comparisons)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "decision_reason", reason)

    @property
    def selected_frame_uids_by_domain(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple((item.label_domain_id, item.frame_uids) for item in self.domains)

    @property
    def total_selected_configurations(self) -> int:
        return sum(len(item.frame_uids) for item in self.domains)

    def domain(self, label_domain_id: str) -> TargetProductionDomainDecision:
        for item in self.domains:
            if item.label_domain_id == label_domain_id:
                return item
        raise KeyError(label_domain_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (TARGET_PRODUCTION_CORPUS_MV_DECISION_SCHEMA if self.authority_version == TARGET_PRODUCTION_CORPUS_MV_VERSION else TARGET_PRODUCTION_CORPUS_DECISION_SCHEMA),
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "selected_target_size": self.selected_target_size,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "partition_policy_digest": self.partition_policy_digest,
            "partition_unit_catalog_digest": self.partition_unit_catalog_digest,
            "leakage_audit_digest": self.leakage_audit_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "foundation_target_audit_digest": self.foundation_target_audit_digest,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_data_ladder_digest": self.target_data_ladder_digest,
            "target_size_convergence_digest": self.target_size_convergence_digest,
            "coverage_policy": self.coverage_policy.to_dict(),
            "ladder_policy_digest": self.ladder_policy_digest,
            "convergence_policy_digest": self.convergence_policy_digest,
            "stage_a_rung_digests": [[k, v] for k, v in self.stage_a_rung_digests],
            "stage_a_survivor_sizes": list(self.stage_a_survivor_sizes),
            "stage_b0_survivor_sizes": list(self.stage_b0_survivor_sizes),
            "stage_b0_evidence": [item.to_dict() for item in self.stage_b0_evidence],
            "stage_b_finalist_sizes": list(self.stage_b_finalist_sizes),
            "stage_b_evidence": [item.to_dict() for item in self.stage_b_evidence],
            "stage_c_evidence": [item.to_dict() for item in self.stage_c_evidence],
            "equivalence_comparisons": [item.to_dict() for item in self.equivalence_comparisons],
            "domains": [item.to_dict() for item in self.domains],
            "bounded_ladder_converged": self.bounded_ladder_converged,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetProductionCorpusDecision":
        schema = payload.get("schema")
        if schema not in {TARGET_PRODUCTION_CORPUS_DECISION_SCHEMA, TARGET_PRODUCTION_CORPUS_MV_DECISION_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2E production-corpus schema.")
        expected_version = TARGET_PRODUCTION_CORPUS_MV_VERSION if schema == TARGET_PRODUCTION_CORPUS_MV_DECISION_SCHEMA else TARGET_PRODUCTION_CORPUS_VERSION
        if str(payload.get("authority_version")) != expected_version:
            raise TrainingDataSerializationError("TARGET-DATA2E production-corpus schema/version generation mismatch.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            selected_target_size=int(payload["selected_target_size"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            partition_policy_digest=str(payload["partition_policy_digest"]),
            partition_unit_catalog_digest=str(payload["partition_unit_catalog_digest"]),
            leakage_audit_digest=str(payload["leakage_audit_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            foundation_target_audit_digest=str(payload["foundation_target_audit_digest"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_data_ladder_digest=str(payload["target_data_ladder_digest"]),
            target_size_convergence_digest=str(payload["target_size_convergence_digest"]),
            coverage_policy=TargetCoveragePolicy.from_dict(payload["coverage_policy"]),
            ladder_policy_digest=str(payload["ladder_policy_digest"]),
            convergence_policy_digest=str(payload["convergence_policy_digest"]),
            stage_a_rung_digests=tuple((int(v[0]), str(v[1])) for v in payload["stage_a_rung_digests"]),
            stage_a_survivor_sizes=tuple(int(v) for v in payload["stage_a_survivor_sizes"]),
            stage_b0_survivor_sizes=tuple(int(v) for v in payload["stage_b0_survivor_sizes"]),
            stage_b0_evidence=tuple(TargetSizeTrainingEvidence.from_dict(item) for item in payload["stage_b0_evidence"]),
            stage_b_finalist_sizes=tuple(int(v) for v in payload["stage_b_finalist_sizes"]),
            stage_b_evidence=tuple(TargetSizeTrainingEvidence.from_dict(item) for item in payload["stage_b_evidence"]),
            stage_c_evidence=tuple(TargetSizeTrainingEvidence.from_dict(item) for item in payload["stage_c_evidence"]),
            equivalence_comparisons=tuple(TargetProductionEquivalenceComparison.from_dict(item) for item in payload.get("equivalence_comparisons", ())),
            domains=tuple(TargetProductionDomainDecision.from_dict(item) for item in payload["domains"]),
            bounded_ladder_converged=bool(payload["bounded_ladder_converged"]),
            decision_reason=str(payload["decision_reason"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2E production-corpus digest mismatch.")
        return result


def _rung_provenance(label_domain_id: str, rung: TargetDataLadderRung) -> TargetProductionRungProvenance:
    rung_digest = rung.to_dict()["content_digest"]
    if not rung.materializable:
        return TargetProductionRungProvenance(
            target_size=rung.target_size,
            materializable=False,
            membership_digest=None,
            rung_content_digest=rung_digest,
            coverage_report_digest=None,
            coverage_passed=None,
            mandatory_obligations_passed=None,
        )
    assert rung.coverage_report is not None
    return TargetProductionRungProvenance(
        target_size=rung.target_size,
        materializable=True,
        membership_digest=_membership_digest(label_domain_id, rung.target_size, rung.frame_uids),
        rung_content_digest=rung_digest,
        coverage_report_digest=rung.coverage_report.content_digest,
        coverage_passed=bool(rung.coverage_report.passed),
        mandatory_obligations_passed=bool(rung.mandatory_obligations_passed),
    )


def _equivalence_comparisons(
    evidence: Sequence[TargetSizeTrainingEvidence],
    *,
    threshold: float,
) -> tuple[TargetProductionEquivalenceComparison, ...]:
    admissible = []
    for item in evidence:
        if item.stage == "short":
            ok = item.admissible_for_stage_b
        else:
            ok = item.admissible_for_stage_c
        if ok:
            admissible.append(item)
    admissible.sort(key=lambda item: item.target_size)
    result: list[TargetProductionEquivalenceComparison] = []
    for left_index, left in enumerate(admissible):
        for right in admissible[left_index + 1 :]:
            delta = abs(left.target_force_score_mev_per_a - right.target_force_score_mev_per_a)
            equivalent = delta <= threshold + 1.0e-12
            result.append(
                TargetProductionEquivalenceComparison(
                    stage=left.stage,
                    smaller_target_size=left.target_size,
                    larger_target_size=right.target_size,
                    smaller_target_score_mev_per_a=left.target_force_score_mev_per_a,
                    larger_target_score_mev_per_a=right.target_force_score_mev_per_a,
                    absolute_score_delta_mev_per_a=delta,
                    threshold_mev_per_a=threshold,
                    practically_equivalent=equivalent,
                    smaller_preferred_when_equivalent=equivalent,
                )
            )
    return tuple(result)


def build_target_production_corpus_decision(
    *,
    target_data_role_freeze: TargetDataRoleFreeze,
    foundation_target_audit: FoundationTargetAudit,
    target_coverage_reference: TargetCoverageReference,
    target_data_ladder: TargetDataLadderPlan,
    target_size_convergence: TargetSizeConvergencePlan,
    target_multi_view_repair: Any | None = None,
    target_multi_view_qualification: Any | None = None,
    migration_authority_digest: str | None = None,
) -> TargetProductionCorpusDecision:
    """Freeze TARGET-DATA2E after (and only after) bounded-ladder convergence."""

    dataset_ids = {
        target_data_role_freeze.dataset_id,
        foundation_target_audit.dataset_id,
        target_coverage_reference.dataset_id,
        target_data_ladder.dataset_id,
        target_size_convergence.dataset_id,
    }
    if len(dataset_ids) != 1:
        raise TargetProductionCorpusDecisionError("TARGET-DATA2E upstream dataset identities disagree.")
    if foundation_target_audit.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TargetProductionCorpusDecisionError("TARGET-DATA2E FOUNDATION-AUDIT1 role-freeze lineage changed.")
    if target_coverage_reference.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TargetProductionCorpusDecisionError("TARGET-DATA2E TARGET-DATA2B role-freeze lineage changed.")
    if target_coverage_reference.foundation_target_audit_digest != foundation_target_audit.content_digest:
        raise TargetProductionCorpusDecisionError("TARGET-DATA2E TARGET-DATA2B foundation-audit lineage changed.")
    if target_data_ladder.authority_version == TARGET_DATA_LADDER_VERSION:
        validate_target_data_ladder_authority(
            target_data_ladder,
            reference=target_coverage_reference,
            target_data_role_freeze=target_data_role_freeze,
        )
        expected_decision_version = TARGET_PRODUCTION_CORPUS_VERSION
        if target_size_convergence.authority_version != TARGET_SIZE_CONVERGENCE_VERSION:
            raise TargetProductionCorpusDecisionError("TARGET-DATA2E v2 cannot bind a migrated TARGET-DATA2D v3 authority.")
    elif target_data_ladder.authority_version == TARGET_DATA_LADDER_MV_VERSION:
        if target_multi_view_repair is None or target_multi_view_qualification is None or migration_authority_digest is None:
            raise TargetProductionCorpusDecisionError("Migrated TARGET-DATA2E v3 requires REPAIR1, MVQUAL1, and MVMIGRATE1 provenance.")
        validate_migrated_target_data_ladder_authority(
            target_data_ladder,
            reference=target_coverage_reference,
            target_data_role_freeze=target_data_role_freeze,
            target_multi_view_repair=target_multi_view_repair,
            target_multi_view_qualification=target_multi_view_qualification,
            migration_authority_digest=migration_authority_digest,
        )
        expected_decision_version = TARGET_PRODUCTION_CORPUS_MV_VERSION
        if target_size_convergence.authority_version != TARGET_SIZE_CONVERGENCE_MV_VERSION:
            raise TargetProductionCorpusDecisionError("TARGET-DATA2E v3 requires migrated TARGET-DATA2D v3 authority.")
    else:
        raise TargetProductionCorpusDecisionError("Unsupported TARGET-DATA2C generation for TARGET-DATA2E.")
    validate_target_size_convergence_authority(target_size_convergence, ladder=target_data_ladder)

    if target_size_convergence.outcome != "selected" or target_size_convergence.selected_target_size is None:
        raise TargetProductionCorpusDecisionError(
            "TARGET-DATA2E requires a completed TARGET-DATA2D selected outcome; "
            f"current outcome={target_size_convergence.outcome!r}."
        )
    selected_size = int(target_size_convergence.selected_target_size)
    if len(target_size_convergence.final_training_evidence) != 2:
        raise TargetProductionCorpusDecisionError("TARGET-DATA2E requires complete Stage-C evidence for both finalists.")

    domains: list[TargetProductionDomainDecision] = []
    for ladder_domain in target_data_ladder.domains:
        role_domain = target_data_role_freeze.domain(ladder_domain.label_domain_id)
        reference_domain = target_coverage_reference.domain(ladder_domain.label_domain_id)
        audit_domain = foundation_target_audit.domain(ladder_domain.label_domain_id)
        rung = next((item for item in ladder_domain.rungs if item.target_size == selected_size), None)
        if rung is None or not rung.materializable or rung.coverage_report is None:
            raise TargetProductionCorpusDecisionError(
                f"TARGET-DATA2E selected rung n{selected_size} is not materializable in {ladder_domain.label_domain_id}."
            )
        if not rung.coverage_report.passed or rung.mandatory_obligations_passed is not True:
            raise TargetProductionCorpusDecisionError(
                f"TARGET-DATA2E selected rung n{selected_size} no longer passes coverage/mandatory evidence in {ladder_domain.label_domain_id}."
            )
        target_data_role_freeze.require_size_selection_frames(
            rung.frame_uids,
            label_domain_id=ladder_domain.label_domain_id,
            context="TARGET-DATA2E winning corpus",
        )
        if rung.coverage_report.reference_digest != target_coverage_reference.content_digest:
            raise TargetProductionCorpusDecisionError("TARGET-DATA2E winning coverage report references stale TARGET-DATA2B evidence.")
        if reference_domain.content_digest != ladder_domain.reference_domain_digest:
            raise TargetProductionCorpusDecisionError("TARGET-DATA2E ladder/reference-domain identity mismatch.")
        if audit_domain.frame_domain_digest != reference_domain.frame_domain_digest:
            raise TargetProductionCorpusDecisionError("TARGET-DATA2E foundation-audit/reference frame domain changed.")

        family_refs = tuple((item.family_id, item.content_digest) for item in reference_domain.families)
        residual_refs = tuple((item.family_id, item.content_digest) for item in reference_domain.families if item.family_kind == "foundation_residual")
        strata = tuple((item.stratum_id, item.to_dict()["content_digest"]) for item in reference_domain.strata)
        master_order_digest = digest(
            {
                "schema": "mdstats.target-production-master-order.v1",
                "label_domain_id": ladder_domain.label_domain_id,
                "frame_uids": [item.frame_uid for item in ladder_domain.master_order],
                "entry_digests": [item.to_dict()["content_digest"] for item in ladder_domain.master_order],
            }
        )
        membership = _membership_digest(ladder_domain.label_domain_id, selected_size, rung.frame_uids)
        domains.append(
            TargetProductionDomainDecision(
                label_domain_id=ladder_domain.label_domain_id,
                target_size=selected_size,
                frame_uids=rung.frame_uids,
                membership_digest=membership,
                role_domain_digest=role_domain.to_dict()["content_digest"],
                outer_partition_digest=role_domain.outer_partition_digest,
                cross_validation_plan_digest=role_domain.cross_validation_plan_digest,
                reference_domain_digest=reference_domain.content_digest,
                ladder_domain_digest=ladder_domain.content_digest,
                master_order_digest=master_order_digest,
                selected_rung_digest=rung.to_dict()["content_digest"],
                selected_coverage_report=rung.coverage_report,
                coverage_family_reference_digests=family_refs,
                foundation_residual_family_reference_digests=residual_refs,
                stratum_reference_digests=strata,
                foundation_audit_domain_digest=audit_domain.content_digest,
                rung_provenance=tuple(_rung_provenance(ladder_domain.label_domain_id, item) for item in ladder_domain.rungs),
            )
        )

    threshold = target_size_convergence.policy.practical_equivalence_mev_per_a
    comparisons = _equivalence_comparisons(
        target_size_convergence.final_training_evidence, threshold=threshold
    )
    return TargetProductionCorpusDecision(
        dataset_id=target_data_ladder.dataset_id,
        selected_target_size=selected_size,
        source_catalog_digest=target_data_role_freeze.source_catalog_digest,
        frame_catalog_digest=target_data_role_freeze.frame_catalog_digest,
        data5_bundle_digest=target_data_role_freeze.data5_bundle_digest,
        partition_policy_digest=target_data_role_freeze.partition_policy_digest,
        partition_unit_catalog_digest=target_data_role_freeze.partition_unit_catalog_digest,
        leakage_audit_digest=target_data_role_freeze.leakage_audit_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        foundation_target_audit_digest=foundation_target_audit.content_digest,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_data_ladder_digest=target_data_ladder.content_digest,
        target_size_convergence_digest=target_size_convergence.content_digest,
        coverage_policy=target_coverage_reference.policy,
        ladder_policy_digest=target_data_ladder.policy.policy_digest,
        convergence_policy_digest=target_size_convergence.policy.policy_digest,
        stage_a_rung_digests=tuple((item.target_size, item.to_dict()["content_digest"]) for item in target_size_convergence.stage_a_rungs),
        stage_a_survivor_sizes=target_size_convergence.stage_a_survivor_sizes,
        stage_b0_survivor_sizes=target_size_convergence.stage_b_survivor_sizes,
        stage_b0_evidence=target_size_convergence.coarse_training_evidence,
        stage_b_finalist_sizes=target_size_convergence.stage_b_finalist_sizes,
        stage_b_evidence=target_size_convergence.short_training_evidence,
        stage_c_evidence=target_size_convergence.final_training_evidence,
        equivalence_comparisons=comparisons,
        domains=tuple(domains),
        bounded_ladder_converged=True,
        decision_reason=target_size_convergence.decision_reason,
        authority_version=expected_decision_version,
    )


def validate_target_production_corpus_decision(
    decision: TargetProductionCorpusDecision,
    *,
    target_data_role_freeze: TargetDataRoleFreeze,
    foundation_target_audit: FoundationTargetAudit,
    target_coverage_reference: TargetCoverageReference,
    target_data_ladder: TargetDataLadderPlan,
    target_size_convergence: TargetSizeConvergencePlan,
    target_multi_view_repair: Any | None = None,
    target_multi_view_qualification: Any | None = None,
    migration_authority_digest: str | None = None,
) -> None:
    """Rebuild TARGET-DATA2E from live authorities and require exact identity."""

    rebuilt = build_target_production_corpus_decision(
        target_data_role_freeze=target_data_role_freeze,
        foundation_target_audit=foundation_target_audit,
        target_coverage_reference=target_coverage_reference,
        target_data_ladder=target_data_ladder,
        target_size_convergence=target_size_convergence,
        target_multi_view_repair=target_multi_view_repair,
        target_multi_view_qualification=target_multi_view_qualification,
        migration_authority_digest=migration_authority_digest,
    )
    if decision.content_digest != rebuilt.content_digest:
        raise TargetProductionCorpusDecisionError(
            "TARGET-DATA2E production-corpus authority is stale or differs from the live frozen evidence."
        )
