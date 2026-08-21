"""TARGET-DATA2C-MVQUAL1 independent same-N scientific qualification.

The authority compares the current production TARGET-DATA2C v4 selector with
TARGET-DATA2C-REPAIR1 at identical cardinality.  Scientific pass/fail evidence
is recomputed through the immutable TARGET-DATA2B scorer; MVIDX1 is used only
for exact secondary telemetry (uncovered witnesses, unique contribution and
correlation-unit diversity) and its covered mass is cross-checked against the
independent scorer.

This gate is pre-migration.  It cannot change DATA8 membership, TARGET-DATA2D
survivors, generated target-size policy, or TRAIN2 behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ._sparse_vector_kernels import csr_row_lengths, iter_csr_edge_batches
from .target_coverage import score_target_subset_coverage
from .target_coverage_sparse_index import indexed_obligation_selected_counts
from .resources import StageResourceScope, available_cpu_threads, stage_resource_scope
from .work_queue import DeterministicWorkQueue

TARGET_MULTI_VIEW_QUALIFICATION_POLICY_SCHEMA = "mdstats.target-multi-view-qualification-policy.v1"
TARGET_MULTI_VIEW_QUALIFICATION_FAMILY_SCHEMA = "mdstats.target-multi-view-qualification-family.v1"
TARGET_MULTI_VIEW_QUALIFICATION_STRATUM_SCHEMA = "mdstats.target-multi-view-qualification-stratum.v1"
TARGET_MULTI_VIEW_QUALIFICATION_TELEMETRY_SCHEMA = "mdstats.target-multi-view-qualification-telemetry.v1"
TARGET_MULTI_VIEW_QUALIFICATION_RUNG_SCHEMA = "mdstats.target-multi-view-qualification-rung.v1"
TARGET_MULTI_VIEW_QUALIFICATION_DOMAIN_SCHEMA = "mdstats.target-multi-view-qualification-domain.v1"
TARGET_MULTI_VIEW_QUALIFICATION_PLAN_SCHEMA = "mdstats.target-multi-view-qualification-plan.v1"
TARGET_MULTI_VIEW_QUALIFICATION_VERSION = "mdstats.target-data2c.mvqual1.2026-08.v1"

_OUTCOME_QUALIFIED = "scientific_coverage_qualified"
_OUTCOME_QUALIFIED_LEARNING_DEFERRED = "scientific_coverage_qualified_learning_controls_deferred"
_OUTCOME_NONREGRESSION_FAILED = "same_n_nonregression_failed"
_OUTCOME_CAPACITY_LIMITED = "capacity_limited_within_16384"
_OUTCOME_PROVABLY_CAPACITY_INFEASIBLE = "provably_capacity_infeasible"
_OUTCOME_INCOMPLETE = "incomplete_ceiling_evidence"
_LEARNING_DEFERRED = "deferred_final_gpu_qualification"
_MVQUAL_STRICT_EDGE_LIMIT = 1_048_576
_MVQUAL_PERSISTENT_RESERVATION_ID = "mvqual-persistent-results"


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationPolicy:
    coverage_threshold: float = 0.95
    comparison_tolerance: float = 1.0e-12
    capacity_ceiling: int = 16384
    max_learning_control_sizes: int = 2
    policy_version: str = TARGET_MULTI_VIEW_QUALIFICATION_VERSION

    def __post_init__(self) -> None:
        threshold = float(self.coverage_threshold)
        tolerance = float(self.comparison_tolerance)
        ceiling = int(self.capacity_ceiling)
        controls = int(self.max_learning_control_sizes)
        if not math.isfinite(threshold) or not 0.0 < threshold <= 1.0:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 coverage threshold is invalid.")
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 comparison tolerance must be positive and finite.")
        if ceiling < 1 or controls < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 capacity/control counts are invalid.")
        if self.policy_version != TARGET_MULTI_VIEW_QUALIFICATION_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVQUAL1 policy version.")
        object.__setattr__(self, "coverage_threshold", threshold)
        object.__setattr__(self, "comparison_tolerance", tolerance)
        object.__setattr__(self, "capacity_ceiling", ceiling)
        object.__setattr__(self, "max_learning_control_sizes", controls)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "coverage_threshold": self.coverage_threshold,
            "comparison_tolerance": self.comparison_tolerance,
            "capacity_ceiling": self.capacity_ceiling,
            "max_learning_control_sizes": self.max_learning_control_sizes,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationPolicy":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 policy schema.")
        result = cls(
            coverage_threshold=float(payload["coverage_threshold"]),
            comparison_tolerance=float(payload["comparison_tolerance"]),
            capacity_ceiling=int(payload["capacity_ceiling"]),
            max_learning_control_sizes=int(payload["max_learning_control_sizes"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationFamilyComparison:
    family_id: str
    required: bool
    legacy_covered_mass: float
    mv_covered_mass: float
    legacy_coverage_passed: bool
    mv_coverage_passed: bool
    legacy_extent_passed: bool
    mv_extent_passed: bool
    legacy_extent_failures: tuple[str, ...] = ()
    mv_extent_failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("legacy_covered_mass", "mv_covered_mass"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < -1e-12 or value > 1.0 + 1e-10:
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 family coverage is invalid.")
            object.__setattr__(self, name, min(1.0, max(0.0, value)))
        object.__setattr__(self, "legacy_extent_failures", tuple(sorted(set(str(v) for v in self.legacy_extent_failures))))
        object.__setattr__(self, "mv_extent_failures", tuple(sorted(set(str(v) for v in self.mv_extent_failures))))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_FAMILY_SCHEMA,
            "family_id": self.family_id,
            "required": self.required,
            "legacy_covered_mass": self.legacy_covered_mass,
            "mv_covered_mass": self.mv_covered_mass,
            "legacy_coverage_passed": self.legacy_coverage_passed,
            "mv_coverage_passed": self.mv_coverage_passed,
            "legacy_extent_passed": self.legacy_extent_passed,
            "mv_extent_passed": self.mv_extent_passed,
            "legacy_extent_failures": list(self.legacy_extent_failures),
            "mv_extent_failures": list(self.mv_extent_failures),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationFamilyComparison":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_FAMILY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 family schema.")
        result = cls(
            family_id=str(payload["family_id"]), required=bool(payload["required"]),
            legacy_covered_mass=float(payload["legacy_covered_mass"]), mv_covered_mass=float(payload["mv_covered_mass"]),
            legacy_coverage_passed=bool(payload["legacy_coverage_passed"]), mv_coverage_passed=bool(payload["mv_coverage_passed"]),
            legacy_extent_passed=bool(payload["legacy_extent_passed"]), mv_extent_passed=bool(payload["mv_extent_passed"]),
            legacy_extent_failures=tuple(str(v) for v in payload.get("legacy_extent_failures", ())),
            mv_extent_failures=tuple(str(v) for v in payload.get("mv_extent_failures", ())),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 family digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationStratumComparison:
    stratum_id: str
    required: bool
    legacy_selected_count: int
    mv_selected_count: int
    minimum_selected_frames: int
    legacy_passed: bool
    mv_passed: bool

    def __post_init__(self) -> None:
        if min(int(self.legacy_selected_count), int(self.mv_selected_count), int(self.minimum_selected_frames)) < 0:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 stratum counts are invalid.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_STRATUM_SCHEMA,
            "stratum_id": self.stratum_id,
            "required": self.required,
            "legacy_selected_count": int(self.legacy_selected_count),
            "mv_selected_count": int(self.mv_selected_count),
            "minimum_selected_frames": int(self.minimum_selected_frames),
            "legacy_passed": self.legacy_passed,
            "mv_passed": self.mv_passed,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationStratumComparison":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_STRATUM_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 stratum schema.")
        result = cls(
            stratum_id=str(payload["stratum_id"]), required=bool(payload["required"]),
            legacy_selected_count=int(payload["legacy_selected_count"]), mv_selected_count=int(payload["mv_selected_count"]),
            minimum_selected_frames=int(payload["minimum_selected_frames"]),
            legacy_passed=bool(payload["legacy_passed"]), mv_passed=bool(payload["mv_passed"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 stratum digest mismatch.")
        return result


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
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 telemetry counts are invalid.")
        for name in ("uncovered_reference_mass", "unique_reference_mass_fraction", "zero_unique_candidate_fraction", "maximum_correlation_unit_fraction"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < -1e-12:
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 telemetry mass/fraction is invalid.")
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
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 telemetry schema.")
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
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 telemetry digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationRung:
    target_size: int
    legacy_report_digest: str
    mv_report_digest: str
    family_comparisons: tuple[TargetMultiViewQualificationFamilyComparison, ...]
    stratum_comparisons: tuple[TargetMultiViewQualificationStratumComparison, ...]
    legacy_passed: bool
    mv_passed: bool
    legacy_hard_obligations_passed: bool
    mv_hard_obligations_passed: bool
    legacy_unsatisfied_obligation_ids: tuple[str, ...]
    mv_unsatisfied_obligation_ids: tuple[str, ...]
    legacy_d_max: float
    mv_d_max: float
    legacy_d_sum: float
    mv_d_sum: float
    hard_non_regression_passed: bool
    worst_deficit_non_regression_passed: bool
    same_n_qualified: bool
    legacy_telemetry: TargetMultiViewSelectorTelemetry
    mv_telemetry: TargetMultiViewSelectorTelemetry

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 target size must be positive.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "legacy_report_digest", validate_digest(self.legacy_report_digest, name="legacy_report_digest"))
        object.__setattr__(self, "mv_report_digest", validate_digest(self.mv_report_digest, name="mv_report_digest"))
        families = tuple(sorted(self.family_comparisons, key=lambda v: v.family_id))
        strata = tuple(sorted(self.stratum_comparisons, key=lambda v: v.stratum_id))
        object.__setattr__(self, "legacy_unsatisfied_obligation_ids", tuple(sorted(set(str(v) for v in self.legacy_unsatisfied_obligation_ids))))
        object.__setattr__(self, "mv_unsatisfied_obligation_ids", tuple(sorted(set(str(v) for v in self.mv_unsatisfied_obligation_ids))))
        if not families:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 rung requires family comparisons.")
        for name in ("legacy_d_max", "mv_d_max", "legacy_d_sum", "mv_d_sum"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < -1e-12:
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 deficit metric is invalid.")
            object.__setattr__(self, name, max(0.0, value))
        if bool(self.same_n_qualified) != bool(self.hard_non_regression_passed and self.worst_deficit_non_regression_passed):
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 same-N result contradicts component authorities.")
        object.__setattr__(self, "family_comparisons", families)
        object.__setattr__(self, "stratum_comparisons", strata)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_RUNG_SCHEMA,
            "target_size": self.target_size,
            "legacy_report_digest": self.legacy_report_digest,
            "mv_report_digest": self.mv_report_digest,
            "family_comparisons": [v.to_dict() for v in self.family_comparisons],
            "stratum_comparisons": [v.to_dict() for v in self.stratum_comparisons],
            "legacy_passed": self.legacy_passed, "mv_passed": self.mv_passed,
            "legacy_hard_obligations_passed": self.legacy_hard_obligations_passed,
            "mv_hard_obligations_passed": self.mv_hard_obligations_passed,
            "legacy_unsatisfied_obligation_ids": list(self.legacy_unsatisfied_obligation_ids),
            "mv_unsatisfied_obligation_ids": list(self.mv_unsatisfied_obligation_ids),
            "legacy_d_max": self.legacy_d_max, "mv_d_max": self.mv_d_max,
            "legacy_d_sum": self.legacy_d_sum, "mv_d_sum": self.mv_d_sum,
            "hard_non_regression_passed": self.hard_non_regression_passed,
            "worst_deficit_non_regression_passed": self.worst_deficit_non_regression_passed,
            "same_n_qualified": self.same_n_qualified,
            "legacy_telemetry": self.legacy_telemetry.to_dict(),
            "mv_telemetry": self.mv_telemetry.to_dict(),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationRung":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 rung schema.")
        result = cls(
            target_size=int(payload["target_size"]), legacy_report_digest=str(payload["legacy_report_digest"]), mv_report_digest=str(payload["mv_report_digest"]),
            family_comparisons=tuple(TargetMultiViewQualificationFamilyComparison.from_dict(v) for v in payload["family_comparisons"]),
            stratum_comparisons=tuple(TargetMultiViewQualificationStratumComparison.from_dict(v) for v in payload.get("stratum_comparisons", ())),
            legacy_passed=bool(payload["legacy_passed"]), mv_passed=bool(payload["mv_passed"]),
            legacy_hard_obligations_passed=bool(payload["legacy_hard_obligations_passed"]),
            mv_hard_obligations_passed=bool(payload["mv_hard_obligations_passed"]),
            legacy_unsatisfied_obligation_ids=tuple(str(v) for v in payload.get("legacy_unsatisfied_obligation_ids", ())),
            mv_unsatisfied_obligation_ids=tuple(str(v) for v in payload.get("mv_unsatisfied_obligation_ids", ())),
            legacy_d_max=float(payload["legacy_d_max"]), mv_d_max=float(payload["mv_d_max"]),
            legacy_d_sum=float(payload["legacy_d_sum"]), mv_d_sum=float(payload["mv_d_sum"]),
            hard_non_regression_passed=bool(payload["hard_non_regression_passed"]),
            worst_deficit_non_regression_passed=bool(payload["worst_deficit_non_regression_passed"]), same_n_qualified=bool(payload["same_n_qualified"]),
            legacy_telemetry=TargetMultiViewSelectorTelemetry.from_dict(payload["legacy_telemetry"]),
            mv_telemetry=TargetMultiViewSelectorTelemetry.from_dict(payload["mv_telemetry"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 rung digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewQualificationDomainPlan:
    label_domain_id: str
    reference_domain_digest: str
    sparse_domain_digest: str
    legacy_domain_digest: str
    mv_repair_domain_digest: str
    common_target_sizes: tuple[int, ...]
    comparisons: tuple[TargetMultiViewQualificationRung, ...]
    legacy_n95_common: int | None
    mv_n95_common: int | None
    n95_non_regression_passed: bool
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("reference_domain_digest", "sparse_domain_digest", "legacy_domain_digest", "mv_repair_domain_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        sizes = tuple(int(v) for v in self.common_target_sizes)
        if not sizes or sizes != tuple(sorted(set(sizes))) or any(v < 1 for v in sizes):
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 common target sizes are invalid.")
        comparisons = tuple(self.comparisons)
        if tuple(v.target_size for v in comparisons) != sizes:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 comparison sizes are misaligned.")
        object.__setattr__(self, "common_target_sizes", sizes)
        object.__setattr__(self, "comparisons", comparisons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "sparse_domain_digest": self.sparse_domain_digest,
            "legacy_domain_digest": self.legacy_domain_digest,
            "mv_repair_domain_digest": self.mv_repair_domain_digest,
            "common_target_sizes": list(self.common_target_sizes),
            "comparison_digests": [v.to_dict()["content_digest"] for v in self.comparisons],
            "legacy_n95_common": self.legacy_n95_common,
            "mv_n95_common": self.mv_n95_common,
            "n95_non_regression_passed": self.n95_non_regression_passed,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "comparisons": [v.to_dict() for v in self.comparisons], "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationDomainPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]), reference_domain_digest=str(payload["reference_domain_digest"]),
            sparse_domain_digest=str(payload["sparse_domain_digest"]), legacy_domain_digest=str(payload["legacy_domain_digest"]),
            mv_repair_domain_digest=str(payload["mv_repair_domain_digest"]), common_target_sizes=tuple(int(v) for v in payload["common_target_sizes"]),
            comparisons=tuple(TargetMultiViewQualificationRung.from_dict(v) for v in payload["comparisons"]),
            legacy_n95_common=None if payload.get("legacy_n95_common") is None else int(payload["legacy_n95_common"]),
            mv_n95_common=None if payload.get("mv_n95_common") is None else int(payload["mv_n95_common"]),
            n95_non_regression_passed=bool(payload["n95_non_regression_passed"]),
        )
        if payload.get("comparison_digests") not in (None, [v.to_dict()["content_digest"] for v in result.comparisons]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 comparison digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetMultiViewQualificationPlan:
    dataset_id: str
    target_coverage_reference_digest: str
    target_coverage_sparse_index_digest: str
    target_coverage_feasibility_digest: str
    target_data_role_freeze_digest: str
    legacy_target_data_ladder_digest: str
    target_multi_view_repair_digest: str
    policy: TargetMultiViewQualificationPolicy
    domains: tuple[TargetMultiViewQualificationDomainPlan, ...]
    global_common_target_sizes: tuple[int, ...]
    legacy_n95_common: int | None
    mv_n95_common: int | None
    n95_non_regression_passed: bool
    same_n_non_regression_passed: bool
    mv_qualified_sizes: tuple[int, ...]
    learning_control_target_sizes: tuple[int, ...]
    learning_control_status: str
    capacity_diagnosis: str
    outcome: str
    authority_version: str = TARGET_MULTI_VIEW_QUALIFICATION_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 dataset_id cannot be empty.")
        for name in ("target_coverage_reference_digest", "target_coverage_sparse_index_digest", "target_coverage_feasibility_digest", "target_data_role_freeze_digest", "legacy_target_data_ladder_digest", "target_multi_view_repair_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        domains = tuple(sorted(self.domains, key=lambda v: v.label_domain_id))
        if not domains or len({v.label_domain_id for v in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 domains must be unique and non-empty.")
        sizes = tuple(int(v) for v in self.global_common_target_sizes)
        if not sizes or sizes != tuple(sorted(set(sizes))):
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 global common target sizes are invalid.")
        qualified = tuple(sorted(set(int(v) for v in self.mv_qualified_sizes)))
        controls = tuple(sorted(set(int(v) for v in self.learning_control_target_sizes)))
        if any(v not in sizes for v in controls):
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 learning controls must be common target sizes.")
        valid_outcomes = {_OUTCOME_QUALIFIED, _OUTCOME_QUALIFIED_LEARNING_DEFERRED, _OUTCOME_NONREGRESSION_FAILED, _OUTCOME_CAPACITY_LIMITED, _OUTCOME_PROVABLY_CAPACITY_INFEASIBLE, _OUTCOME_INCOMPLETE}
        if self.outcome not in valid_outcomes:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 outcome is invalid.")
        if self.learning_control_status != _LEARNING_DEFERRED:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 v1 learning controls must remain deferred to final GPU qualification.")
        if self.authority_version != TARGET_MULTI_VIEW_QUALIFICATION_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C-MVQUAL1 plan version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "global_common_target_sizes", sizes)
        object.__setattr__(self, "mv_qualified_sizes", qualified)
        object.__setattr__(self, "learning_control_target_sizes", controls)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_PLAN_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest": self.target_coverage_sparse_index_digest,
            "target_coverage_feasibility_digest": self.target_coverage_feasibility_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "legacy_target_data_ladder_digest": self.legacy_target_data_ladder_digest,
            "target_multi_view_repair_digest": self.target_multi_view_repair_digest,
            "policy": self.policy.to_dict(),
            "domain_digests": [v.content_digest for v in self.domains],
            "global_common_target_sizes": list(self.global_common_target_sizes),
            "legacy_n95_common": self.legacy_n95_common,
            "mv_n95_common": self.mv_n95_common,
            "n95_non_regression_passed": self.n95_non_regression_passed,
            "same_n_non_regression_passed": self.same_n_non_regression_passed,
            "mv_qualified_sizes": list(self.mv_qualified_sizes),
            "learning_control_target_sizes": list(self.learning_control_target_sizes),
            "learning_control_status": self.learning_control_status,
            "capacity_diagnosis": self.capacity_diagnosis,
            "outcome": self.outcome,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "domains": [v.to_dict() for v in self.domains], "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationPlan":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C-MVQUAL1 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_coverage_sparse_index_digest=str(payload["target_coverage_sparse_index_digest"]),
            target_coverage_feasibility_digest=str(payload["target_coverage_feasibility_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            legacy_target_data_ladder_digest=str(payload["legacy_target_data_ladder_digest"]),
            target_multi_view_repair_digest=str(payload["target_multi_view_repair_digest"]),
            policy=TargetMultiViewQualificationPolicy.from_dict(payload["policy"]),
            domains=tuple(TargetMultiViewQualificationDomainPlan.from_dict(v) for v in payload["domains"]),
            global_common_target_sizes=tuple(int(v) for v in payload["global_common_target_sizes"]),
            legacy_n95_common=None if payload.get("legacy_n95_common") is None else int(payload["legacy_n95_common"]),
            mv_n95_common=None if payload.get("mv_n95_common") is None else int(payload["mv_n95_common"]),
            n95_non_regression_passed=bool(payload["n95_non_regression_passed"]),
            same_n_non_regression_passed=bool(payload["same_n_non_regression_passed"]),
            mv_qualified_sizes=tuple(int(v) for v in payload.get("mv_qualified_sizes", ())),
            learning_control_target_sizes=tuple(int(v) for v in payload.get("learning_control_target_sizes", ())),
            learning_control_status=str(payload["learning_control_status"]), capacity_diagnosis=str(payload["capacity_diagnosis"]),
            outcome=str(payload["outcome"]), authority_version=str(payload["authority_version"]),
        )
        if payload.get("domain_digests") not in (None, [v.content_digest for v in result.domains]):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 domain digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C-MVQUAL1 plan digest mismatch.")
        return result


def _deficits(report: Any, threshold: float) -> tuple[float, float]:
    deficits = [max(0.0, threshold - float(item.covered_reference_mass)) for item in report.family_reports if item.required]
    if not deficits:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 requires at least one required coverage family.")
    return max(deficits), float(sum(deficits))


def _selector_telemetry_reference(reference_domain: Any, sparse_domain: Any, role_domain: Any, selected_uids: Sequence[str]) -> TargetMultiViewSelectorTelemetry:
    """Frozen scalar/ragged MVQUAL1 telemetry reference for MVKERNEL1 tests."""

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
            witnesses = np.asarray(sparse_family.candidate_witness_indices(int(candidate)), dtype=np.int64)
            covered[witnesses] = True
            multiplicity[witnesses] += 1
        total_uncovered_count += int(np.count_nonzero(~covered))
        total_uncovered_mass += np.sum(weights[~covered], dtype=np.float64)
        total_reference_mass += np.sum(weights, dtype=np.float64)
        unique_witness = multiplicity == 1
        total_unique_mass += np.sum(weights[unique_witness], dtype=np.float64)
        if np.any(unique_witness):
            for candidate in selected:
                witnesses = np.asarray(sparse_family.candidate_witness_indices(int(candidate)), dtype=np.int64)
                if witnesses.size and np.any(unique_witness[witnesses]):
                    unique_owner[int(candidate)] = True
    zero_unique = 1.0 - float(np.count_nonzero(unique_owner[selected])) / float(len(selected))
    unique_fraction = 0.0 if total_reference_mass <= 0.0 else float(total_unique_mass / total_reference_mass)
    unit_codes = np.asarray(sparse_domain.candidate_correlation_unit_codes, dtype=np.int64)[selected]
    counts = np.bincount(unit_codes, minlength=len(sparse_domain.correlation_unit_ids))
    nonzero = counts[counts > 0]
    max_unit_fraction = 0.0 if nonzero.size == 0 else float(np.max(nonzero)) / float(len(selected))

    frame_to_run: dict[str, str] = {}
    frame_to_condition: dict[str, str] = {}
    for interval in role_domain.development_intervals:
        for uid in interval.frame_uids:
            if uid in uid_to_index:
                frame_to_run[uid] = str(getattr(interval, "run_id", interval.unit_id))
                frame_to_condition[uid] = str(getattr(interval, "condition_id", interval.unit_id))
    missing = [uid for uid in selected_uids if uid not in frame_to_run or uid not in frame_to_condition]
    if missing:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 selected frame lacks DATA2A provenance mapping.")
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
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 selected candidates must be nonempty and one-dimensional.")
    if selected.size > np.iinfo(np.int32).max:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 selected cardinality exceeds int32 multiplicity capacity.")
    edge_limit = int(max_edges)
    if edge_limit < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 sparse edge limit must be positive.")

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
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 sparse/reference witness cardinality mismatch.")
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
                raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 MVIDX witness is outside the reference family.")
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
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 selected frame lacks DATA2A provenance mapping.")
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


def _selector_telemetry_indices(
    reference_domain: Any,
    sparse_domain: Any,
    selected: np.ndarray,
    run_codes: np.ndarray,
    condition_codes: np.ndarray,
    *,
    max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
) -> TargetMultiViewSelectorTelemetry:
    """Bounded exact MVIDX telemetry compatibility wrapper."""

    return _selector_telemetry_indices_bounded(
        reference_domain,
        sparse_domain,
        selected,
        run_codes,
        condition_codes,
        max_edges=max_edges,
    ).telemetry


def _selector_telemetry(reference_domain: Any, sparse_domain: Any, role_domain: Any, selected_uids: Sequence[str]) -> TargetMultiViewSelectorTelemetry:
    uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(reference_domain, role_domain)
    try:
        selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)
    except KeyError as exc:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 selected frame is outside the reference domain.") from exc
    return _selector_telemetry_indices(
        reference_domain, sparse_domain, selected, run_codes, condition_codes
    )


def _hard_obligation_state(sparse_domain: Any, selected_candidate_indices: Sequence[int]) -> tuple[bool, tuple[str, ...]]:
    counts = indexed_obligation_selected_counts(sparse_domain, selected_candidate_indices)
    unsatisfied = tuple(sorted(
        obligation.obligation_id
        for oi, obligation in enumerate(sparse_domain.obligations)
        if obligation.required and int(counts[oi]) < int(obligation.minimum_selected_frames)
    ))
    return (not unsatisfied), unsatisfied


def _compare_reports(legacy: Any, mv: Any, *, threshold: float, tolerance: float, legacy_telemetry: TargetMultiViewSelectorTelemetry, mv_telemetry: TargetMultiViewSelectorTelemetry, legacy_hard_state: tuple[bool, tuple[str, ...]], mv_hard_state: tuple[bool, tuple[str, ...]]) -> TargetMultiViewQualificationRung:
    if legacy.label_domain_id != mv.label_domain_id or len(legacy.selected_frame_uids) != len(mv.selected_frame_uids):
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 same-N reports are misaligned.")
    legacy_families = {v.family_id: v for v in legacy.family_reports}
    mv_families = {v.family_id: v for v in mv.family_reports}
    if legacy_families.keys() != mv_families.keys():
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 family authorities differ between selectors.")
    family_comparisons = []
    hard_ok = True
    for family_id in sorted(legacy_families):
        left = legacy_families[family_id]; right = mv_families[family_id]
        family_comparisons.append(TargetMultiViewQualificationFamilyComparison(
            family_id=family_id, required=left.required,
            legacy_covered_mass=left.covered_reference_mass, mv_covered_mass=right.covered_reference_mass,
            legacy_coverage_passed=left.coverage_passed, mv_coverage_passed=right.coverage_passed,
            legacy_extent_passed=left.extent_passed, mv_extent_passed=right.extent_passed,
            legacy_extent_failures=left.extent_failures, mv_extent_failures=right.extent_failures,
        ))
        if left.required:
            if left.coverage_passed and not right.coverage_passed:
                hard_ok = False
            if left.extent_passed and not right.extent_passed:
                hard_ok = False
    legacy_strata = {v.stratum_id: v for v in legacy.stratum_reports}
    mv_strata = {v.stratum_id: v for v in mv.stratum_reports}
    if legacy_strata.keys() != mv_strata.keys():
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 stratum authorities differ between selectors.")
    stratum_comparisons = []
    for stratum_id in sorted(legacy_strata):
        left = legacy_strata[stratum_id]; right = mv_strata[stratum_id]
        stratum_comparisons.append(TargetMultiViewQualificationStratumComparison(
            stratum_id=stratum_id, required=left.required,
            legacy_selected_count=left.selected_frame_count, mv_selected_count=right.selected_frame_count,
            minimum_selected_frames=left.minimum_selected_frames, legacy_passed=left.passed, mv_passed=right.passed,
        ))
        if left.required and left.passed and not right.passed:
            hard_ok = False
    legacy_hard_pass, legacy_unsatisfied = legacy_hard_state
    mv_hard_pass, mv_unsatisfied = mv_hard_state
    if legacy_hard_pass and not mv_hard_pass:
        hard_ok = False
    legacy_dmax, legacy_dsum = _deficits(legacy, threshold)
    mv_dmax, mv_dsum = _deficits(mv, threshold)
    worst_ok = mv_dmax <= legacy_dmax + tolerance
    return TargetMultiViewQualificationRung(
        target_size=len(legacy.selected_frame_uids), legacy_report_digest=legacy.content_digest, mv_report_digest=mv.content_digest,
        family_comparisons=tuple(family_comparisons), stratum_comparisons=tuple(stratum_comparisons),
        legacy_passed=bool(legacy.passed and legacy_hard_pass), mv_passed=bool(mv.passed and mv_hard_pass),
        legacy_hard_obligations_passed=legacy_hard_pass, mv_hard_obligations_passed=mv_hard_pass,
        legacy_unsatisfied_obligation_ids=legacy_unsatisfied, mv_unsatisfied_obligation_ids=mv_unsatisfied,
        legacy_d_max=legacy_dmax, mv_d_max=mv_dmax, legacy_d_sum=legacy_dsum, mv_d_sum=mv_dsum,
        hard_non_regression_passed=hard_ok, worst_deficit_non_regression_passed=worst_ok,
        same_n_qualified=hard_ok and worst_ok, legacy_telemetry=legacy_telemetry, mv_telemetry=mv_telemetry,
    )


def _first_qualified_size(comparisons: Sequence[TargetMultiViewQualificationRung], *, selector: str) -> int | None:
    attr = "legacy_passed" if selector == "legacy" else "mv_passed"
    for item in comparisons:
        if bool(getattr(item, attr)):
            return item.target_size
    return None


def _n95_nonregression(legacy_n95: int | None, mv_n95: int | None) -> bool:
    if legacy_n95 is None:
        return True
    return mv_n95 is not None and mv_n95 <= legacy_n95


@dataclass(frozen=True, slots=True)
class _MvqualMemoryEstimate:
    """Execution-only peak-live memory model for one MVQUAL scoring task."""

    persistent_bytes: int
    direct_scratch_bytes: int
    sparse_scratch_bytes: int
    hard_scratch_bytes: int

    @property
    def peak_bytes(self) -> int:
        return int(
            self.persistent_bytes
            + max(
                self.direct_scratch_bytes,
                self.sparse_scratch_bytes,
                self.hard_scratch_bytes,
            )
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "persistent_bytes": int(self.persistent_bytes),
            "direct_scratch_bytes": int(self.direct_scratch_bytes),
            "sparse_scratch_bytes": int(self.sparse_scratch_bytes),
            "hard_scratch_bytes": int(self.hard_scratch_bytes),
            "peak_bytes": int(self.peak_bytes),
        }


def _estimate_mvqual_score_memory(
    reference_domain: Any,
    sparse_domain: Any,
    selected_count: int,
    *,
    sparse_max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
) -> _MvqualMemoryEstimate:
    """Conservative phase-aware temporary-memory estimate for one score job."""

    selected_count = max(1, int(selected_count))
    edge_limit = max(1, int(sparse_max_edges))

    # The direct TARGET-DATA2B scorer traverses families sequentially.  Model
    # the largest family rather than summing mutually exclusive family scratch.
    direct_scratch = 1
    for family in reference_domain.families:
        values = np.asarray(family.values)
        if values.ndim == 1:
            n, width = int(values.shape[0]), 1
        elif values.ndim == 2:
            n, width = int(values.shape[0]), max(1, int(values.shape[1]))
        else:
            n, width = len(family.values), max(1, len(family.feature_names))
        # scaled values, selected/raw selected copies, cKDTree storage,
        # representative/covered/distance arrays and fidelity scratch.
        family_scratch = n * (64 * width + 160)
        direct_scratch = max(direct_scratch, family_scratch)

    # The bounded sparse phase holds one family's witness state and one strict
    # chunk.  The 48-byte/edge term conservatively covers stream position and
    # owner buffers, gathered uint32 indices, unique-edge mask and second-pass
    # owner-selection temporaries.  Read-only MVIDX arrays are shared mappings.
    sparse_scratch = 1
    for family in sparse_domain.families:
        witness_count = max(0, int(family.witness_count))
        family_scratch = (
            witness_count * 14
            + edge_limit * 48
            + selected_count * 16
            + max(1, int(getattr(sparse_domain, "candidate_count", selected_count)))
        )
        sparse_scratch = max(sparse_scratch, family_scratch)

    obligation_offsets = np.asarray(
        getattr(sparse_domain, "candidate_obligation_offsets", np.zeros(1, dtype=np.uint64))
    )
    if obligation_offsets.size > 1:
        max_obligations_per_candidate = int(
            np.max(np.diff(obligation_offsets.astype(np.int64, copy=False)))
        )
    else:
        max_obligations_per_candidate = 0
    obligation_edge_bound = selected_count * max(0, max_obligations_per_candidate)
    hard_scratch = (
        obligation_edge_bound * 32
        + max(1, len(getattr(sparse_domain, "obligations", ()))) * 16
        + selected_count * 16
    )

    # Per-task state that can span phases: selected indices, compact telemetry,
    # report/result objects and Python container overhead.  The larger retained
    # result-set lifetime is reserved once at the coordinator level below.
    persistent = (
        selected_count * 32
        + max(1, len(reference_domain.families)) * 1024
        + max(1, len(getattr(reference_domain, "strata", ()))) * 256
        + 64 * 1024
    )
    return _MvqualMemoryEstimate(
        persistent_bytes=max(1, int(persistent)),
        direct_scratch_bytes=max(1, int(direct_scratch)),
        sparse_scratch_bytes=max(1, int(sparse_scratch)),
        hard_scratch_bytes=max(1, int(hard_scratch)),
    )


def _estimate_mvqual_score_memory_bytes(
    reference_domain: Any,
    sparse_domain: Any,
    selected_count: int,
    *,
    sparse_max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
) -> int:
    """Compatibility scalar for PARCORE1 task admission."""

    return _estimate_mvqual_score_memory(
        reference_domain,
        sparse_domain,
        selected_count,
        sparse_max_edges=sparse_max_edges,
    ).peak_bytes


def _estimate_mvqual_retained_result_bytes(reference_domain: Any, selected_count: int) -> int:
    """Conservative bytes retained after one score task is drained."""

    return int(
        16 * max(1, int(selected_count))
        + 1024 * max(1, len(reference_domain.families))
        + 512 * max(1, len(getattr(reference_domain, "strata", ())))
        + 16 * 1024
    )


@dataclass(frozen=True, slots=True)
class _MvqualJobExecutionTelemetry:
    """Execution-only per-job meter; never serialized into scientific authority."""

    label_domain_id: str
    selector: str
    target_size: int
    sparse_max_edges: int
    streamed_edge_count: int
    maximum_chunk_edges: int
    maximum_selected_row_edges: int
    direct_seconds: float
    sparse_seconds: float
    crosscheck_seconds: float
    hard_seconds: float
    estimated_peak_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_domain_id": self.label_domain_id,
            "selector": self.selector,
            "target_size": int(self.target_size),
            "sparse_max_edges": int(self.sparse_max_edges),
            "streamed_edge_count": int(self.streamed_edge_count),
            "maximum_chunk_edges": int(self.maximum_chunk_edges),
            "maximum_selected_row_edges": int(self.maximum_selected_row_edges),
            "direct_seconds": float(self.direct_seconds),
            "sparse_seconds": float(self.sparse_seconds),
            "crosscheck_seconds": float(self.crosscheck_seconds),
            "hard_seconds": float(self.hard_seconds),
            "estimated_peak_bytes": int(self.estimated_peak_bytes),
        }


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


def _mvqual_parallel_scope(
    resource_scope: StageResourceScope | None,
    workers: int,
) -> StageResourceScope:
    """Return one single-level MVQUAL-PAR1 CPU scope.

    Direct API calls without an explicit campaign scope remain independent of
    transient host free-memory state.  Campaign callers pass their explicit RAM
    contract through ``resource_scope``.
    """

    workers = max(1, int(workers))
    if resource_scope is None:
        available = max(1, int(available_cpu_threads()))
        resolved = min(workers, available)
        return StageResourceScope(
            stage_name="TARGET-DATA2C-MVQUAL-PAR1",
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
    if int(resource_scope.python_workers) < workers:
        raise TrainingDataInputError(
            "TARGET-DATA2C-MVQUAL-PAR1 resource scope has fewer Python workers than requested."
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
    """Compute one immutable MVQUAL same-N scoring job."""

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
            "TARGET-DATA2C-MVQUAL1 selected frame is outside the reference domain."
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
                "TARGET-DATA2C-MVQUAL1 independent scorer disagrees with MVIDX telemetry."
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


def build_target_multi_view_qualification_plan(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_coverage_feasibility: Any,
    target_data_role_freeze: Any,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
    *,
    policy: TargetMultiViewQualificationPolicy | None = None,
    coverage_query_workers: int = 1,
    scoring_workers: int = 1,
    sparse_max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
    resource_scope: StageResourceScope | None = None,
    execution_telemetry_callback: Any = None,
    job_telemetry_callback: Any = None,
    progress_callback: Any = None,
) -> TargetMultiViewQualificationPlan:
    """Build independent same-N legacy-vs-MV qualification evidence.

    ``scoring_workers`` and ``sparse_max_edges`` are execution-only.  When
    scoring is parallel, independent domain/selector/size jobs share one
    PARCORE1 queue and every nested TARGET-DATA2B cKDTree query is constrained
    to one native worker.  Results are reassembled in historical order before
    any scientific comparison or progress emission occurs.
    """

    policy = policy or TargetMultiViewQualificationPolicy(
        coverage_threshold=float(target_coverage_reference.policy.coverage_threshold)
    )
    query_workers = int(coverage_query_workers)
    if query_workers < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 coverage workers must be positive.")
    requested_scoring_workers = int(scoring_workers)
    if requested_scoring_workers < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL-PAR1 scoring workers must be positive.")
    sparse_edge_limit = int(sparse_max_edges)
    if sparse_edge_limit < 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 sparse edge limit must be positive.")
    dataset_ids = {
        target_coverage_reference.dataset_id,
        target_coverage_sparse_index.dataset_id,
        target_coverage_feasibility.dataset_id,
        legacy_target_data_ladder.dataset_id,
        target_multi_view_repair.dataset_id,
    }
    if len(dataset_ids) != 1:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 dataset identity mismatch.")
    if target_coverage_sparse_index.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 MVIDX/reference lineage mismatch.")
    if target_coverage_feasibility.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 FEAS/reference lineage mismatch.")
    if target_coverage_feasibility.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 FEAS/DATA2A lineage mismatch.")
    if legacy_target_data_ladder.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 legacy/reference lineage mismatch.")
    if (
        target_multi_view_repair.target_coverage_reference_digest != target_coverage_reference.content_digest
        or target_multi_view_repair.target_coverage_sparse_index_digest != target_coverage_sparse_index.content_digest
    ):
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 repair lineage mismatch.")
    if not math.isclose(
        policy.coverage_threshold,
        float(target_coverage_reference.policy.coverage_threshold),
        rel_tol=0.0,
        abs_tol=5e-15,
    ):
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 threshold differs from TARGET-DATA2B authority.")

    # Freeze all job inputs before execution.  The dictionaries below are
    # execution-only and preserve the canonical domain/rung ordering supplied by
    # the scientific authorities.
    domain_contexts: list[dict[str, Any]] = []
    global_common: set[int] | None = None
    jobs: list[tuple[int, int, int, str, str, int, Sequence[str], dict[str, Any]]] = []
    job_position = 0
    for domain_index, reference_domain in enumerate(target_coverage_reference.domains):
        label = reference_domain.label_domain_id
        sparse_domain = target_coverage_sparse_index.domain(label)
        legacy_domain = legacy_target_data_ladder.domain(label)
        repair_domain = target_multi_view_repair.domain(label)
        role_domain = target_data_role_freeze.domain(label)
        uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(
            reference_domain, role_domain
        )
        legacy_rungs = {v.target_size: v for v in legacy_domain.rungs if v.materializable}
        mv_rungs = {v.target_size: v for v in repair_domain.rungs if v.materializable}
        common = tuple(sorted(set(legacy_rungs) & set(mv_rungs)))
        if not common:
            raise TrainingDataInputError(
                f"TARGET-DATA2C-MVQUAL1 {label} has no common materializable target sizes."
            )
        global_common = set(common) if global_common is None else global_common & set(common)
        context = {
            "domain_index": domain_index,
            "label": label,
            "reference_domain": reference_domain,
            "sparse_domain": sparse_domain,
            "legacy_domain": legacy_domain,
            "repair_domain": repair_domain,
            "uid_to_index": uid_to_index,
            "run_codes": run_codes,
            "condition_codes": condition_codes,
            "legacy_rungs": legacy_rungs,
            "mv_rungs": mv_rungs,
            "common": common,
        }
        domain_contexts.append(context)
        for size in common:
            for selector_index, (selector, rung) in enumerate(
                (("legacy", legacy_rungs[size]), ("mv", mv_rungs[size]))
            ):
                jobs.append(
                    (
                        job_position,
                        domain_index,
                        selector_index,
                        label,
                        selector,
                        int(size),
                        rung.frame_uids,
                        context,
                    )
                )
                job_position += 1
        for size in sorted(set(mv_rungs) - set(common)):
            jobs.append(
                (
                    job_position,
                    domain_index,
                    1,
                    label,
                    "mv",
                    int(size),
                    mv_rungs[size].frame_uids,
                    context,
                )
            )
            job_position += 1

    job_memory: dict[tuple[str, str, int], _MvqualMemoryEstimate] = {}
    retained_result_bytes = 0
    for _, _, _, label, selector, size, selected_uids, context in jobs:
        key = (label, selector, int(size))
        job_memory[key] = _estimate_mvqual_score_memory(
            context["reference_domain"],
            context["sparse_domain"],
            len(selected_uids),
            sparse_max_edges=sparse_edge_limit,
        )
        retained_result_bytes += _estimate_mvqual_retained_result_bytes(
            context["reference_domain"], len(selected_uids)
        )
    # Context/provenance containers are also retained for the full build.  Do
    # not count the immutable reference/MVIDX mappings themselves per worker.
    coordinator_persistent_bytes = int(retained_result_bytes)
    for context in domain_contexts:
        candidate_count = len(context["reference_domain"].frame_uids)
        coordinator_persistent_bytes += candidate_count * 112 + 64 * 1024

    if resource_scope is not None and resource_scope.ram_budget_bytes is not None:
        ram_budget = int(resource_scope.ram_budget_bytes)
        largest_task = max(estimate.peak_bytes for estimate in job_memory.values())
        if coordinator_persistent_bytes + largest_task > ram_budget:
            raise TrainingDataInputError(
                "TARGET-DATA2C-MVQUAL-PAR1 bounded job plus persistent result state exceeds the stage RAM budget."
            )

    score_results: dict[tuple[str, str, int], _MvqualScoreResult] = {}
    effective_workers = max(1, min(requested_scoring_workers, len(jobs)))
    inner_query_workers = query_workers if effective_workers == 1 else 1

    def evaluate_job(job: tuple[int, int, int, str, str, int, Sequence[str], dict[str, Any]]) -> _MvqualScoreResult:
        _, _, _, label, selector, size, selected_uids, context = job
        return _mvqual_score_job(
            target_coverage_reference,
            context["reference_domain"],
            context["sparse_domain"],
            label=label,
            selector=selector,
            target_size=size,
            selected_uids=selected_uids,
            uid_to_index=context["uid_to_index"],
            run_codes=context["run_codes"],
            condition_codes=context["condition_codes"],
            query_workers=inner_query_workers,
            sparse_max_edges=sparse_edge_limit,
        )

    def consume_result(result: _MvqualScoreResult) -> None:
        key = (result.label_domain_id, result.selector, result.target_size)
        score_results[key] = result
        if job_telemetry_callback is not None:
            job_telemetry_callback(
                _MvqualJobExecutionTelemetry(
                    label_domain_id=result.label_domain_id,
                    selector=result.selector,
                    target_size=result.target_size,
                    sparse_max_edges=sparse_edge_limit,
                    streamed_edge_count=result.streamed_edge_count,
                    maximum_chunk_edges=result.maximum_chunk_edges,
                    maximum_selected_row_edges=result.maximum_selected_row_edges,
                    direct_seconds=result.direct_seconds,
                    sparse_seconds=result.sparse_seconds,
                    crosscheck_seconds=result.crosscheck_seconds,
                    hard_seconds=result.hard_seconds,
                    estimated_peak_bytes=job_memory[key].peak_bytes,
                )
            )

    if effective_workers == 1:
        if resource_scope is None:
            for job in jobs:
                consume_result(evaluate_job(job))
        else:
            serial_scope = _mvqual_parallel_scope(resource_scope, 1)
            with stage_resource_scope(serial_scope):
                for job in jobs:
                    consume_result(evaluate_job(job))
    else:
        scope = _mvqual_parallel_scope(resource_scope, effective_workers)
        with DeterministicWorkQueue(
            scope,
            max_ready_tasks=max(2, 2 * effective_workers),
            # One future per real worker keeps PARCORE1 scratch accounting tied
            # to possible concurrent live task memory rather than executor backlog.
            max_inflight_tasks=effective_workers,
            # MVQUAL drains immediately; one completion slot limits the brief
            # post-task over-accounting of scratch that is already dead.
            max_completed_tasks=1,
            heartbeat_interval_seconds=30.0,
            telemetry_callback=execution_telemetry_callback,
            thread_name_prefix="mdstats-mvqual-par1",
            manage_resource_scope=resource_scope is not None,
        ) as queue:
            if scope.ram_budget_bytes is not None and coordinator_persistent_bytes > 0:
                queue.reserve_memory(
                    _MVQUAL_PERSISTENT_RESERVATION_ID, coordinator_persistent_bytes
                )
            next_submit = 0
            expected = len(jobs)
            while queue.snapshot().finished_tasks < expected:
                while next_submit < expected and queue.can_submit():
                    (
                        position,
                        domain_index,
                        selector_index,
                        label,
                        selector,
                        size,
                        selected_uids,
                        context,
                    ) = jobs[next_submit]
                    memory = job_memory[(label, selector, int(size))]
                    queue.submit(
                        task_id=f"mvqual-score-{domain_index:04d}-{selector}-{size:08d}",
                        canonical_order=(domain_index, int(size), selector_index, position),
                        function=evaluate_job,
                        args=((position, domain_index, selector_index, label, selector, size, selected_uids, context),),
                        task_kind="mvqual-score",
                        estimated_memory_bytes=memory.peak_bytes,
                        locality_key=f"{label}:mvqual",
                    )
                    next_submit += 1
                queue.wait_for_completion()
                for completion in queue.drain_completed():
                    consume_result(completion.value)
            for completion in queue.drain_completed():
                consume_result(completion.value)
            final_queue_snapshot = queue.snapshot()
            if next_submit != expected or queue.has_outstanding_work:
                raise RuntimeError("TARGET-DATA2C-MVQUAL-PAR1 bounded queue did not drain exactly.")
            if execution_telemetry_callback is not None:
                execution_telemetry_callback(final_queue_snapshot)
            if scope.ram_budget_bytes is not None and coordinator_persistent_bytes > 0:
                queue.release_memory(_MVQUAL_PERSISTENT_RESERVATION_ID)

    domains: list[TargetMultiViewQualificationDomainPlan] = []
    mv_independent_passes: dict[str, dict[int, bool]] = {}
    for context in domain_contexts:
        label = context["label"]
        reference_domain = context["reference_domain"]
        sparse_domain = context["sparse_domain"]
        legacy_domain = context["legacy_domain"]
        repair_domain = context["repair_domain"]
        common = context["common"]
        mv_rungs = context["mv_rungs"]
        comparisons: list[TargetMultiViewQualificationRung] = []
        for size in common:
            legacy_result = score_results[(label, "legacy", int(size))]
            mv_result = score_results[(label, "mv", int(size))]
            comparison = _compare_reports(
                legacy_result.report,
                mv_result.report,
                threshold=policy.coverage_threshold,
                tolerance=policy.comparison_tolerance,
                legacy_telemetry=legacy_result.telemetry,
                mv_telemetry=mv_result.telemetry,
                legacy_hard_state=legacy_result.hard_state,
                mv_hard_state=mv_result.hard_state,
            )
            comparisons.append(comparison)
            if progress_callback is not None:
                progress_callback(
                    f"status=rung; domain={label}; target_size={size}; "
                    f"legacy_Dmax={comparison.legacy_d_max:.6f}; MV_Dmax={comparison.mv_d_max:.6f}; "
                    f"same_N={'PASS' if comparison.same_n_qualified else 'FAIL'}"
                )
        comparison_by_size = {item.target_size: item for item in comparisons}
        mv_domain_passes: dict[int, bool] = {}
        for size in mv_rungs:
            if size in comparison_by_size:
                mv_domain_passes[size] = bool(comparison_by_size[size].mv_passed)
                continue
            mv_result = score_results[(label, "mv", int(size))]
            mv_domain_passes[size] = bool(mv_result.report.passed and mv_result.hard_state[0])
        mv_independent_passes[label] = mv_domain_passes
        legacy_n95 = _first_qualified_size(comparisons, selector="legacy")
        mv_n95 = _first_qualified_size(comparisons, selector="mv")
        domains.append(
            TargetMultiViewQualificationDomainPlan(
                label_domain_id=label,
                reference_domain_digest=reference_domain.content_digest,
                sparse_domain_digest=sparse_domain.content_digest,
                legacy_domain_digest=legacy_domain.content_digest,
                mv_repair_domain_digest=repair_domain.content_digest,
                common_target_sizes=common,
                comparisons=tuple(comparisons),
                legacy_n95_common=legacy_n95,
                mv_n95_common=mv_n95,
                n95_non_regression_passed=_n95_nonregression(legacy_n95, mv_n95),
            )
        )

    assert global_common is not None
    common_sizes = tuple(sorted(global_common))
    if not common_sizes:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 has no globally common materializable target sizes.")
    by_domain = {v.label_domain_id: v for v in domains}
    legacy_common_n95 = next(
        (
            size
            for size in common_sizes
            if all(
                next(c for c in d.comparisons if c.target_size == size).legacy_passed
                for d in by_domain.values()
            )
        ),
        None,
    )
    mv_common_n95 = next(
        (
            size
            for size in common_sizes
            if all(
                next(c for c in d.comparisons if c.target_size == size).mv_passed
                for d in by_domain.values()
            )
        ),
        None,
    )
    same_n_pass = all(
        next(c for c in d.comparisons if c.target_size == size).same_n_qualified
        for d in by_domain.values()
        for size in common_sizes
    )
    n95_pass = _n95_nonregression(legacy_common_n95, mv_common_n95)
    mv_candidate_sizes = sorted(set.intersection(*(set(values) for values in mv_independent_passes.values())))
    mv_qualified_sizes = tuple(
        size
        for size in mv_candidate_sizes
        if size <= policy.capacity_ceiling
        and all(bool(mv_independent_passes[label][size]) for label in mv_independent_passes)
    )
    both_qualified = [
        size
        for size in common_sizes
        if all(
            (lambda c: c.legacy_passed and c.mv_passed)(
                next(c for c in d.comparisons if c.target_size == size)
            )
            for d in by_domain.values()
        )
    ]
    learning_controls = tuple(both_qualified[: policy.max_learning_control_sizes])

    if "provably_capacity_infeasible" in target_coverage_feasibility.states:
        capacity_diagnosis = _OUTCOME_PROVABLY_CAPACITY_INFEASIBLE
    elif mv_qualified_sizes:
        capacity_diagnosis = "coverage_qualified_within_ceiling"
    elif all(policy.capacity_ceiling in values for values in mv_independent_passes.values()):
        capacity_diagnosis = _OUTCOME_CAPACITY_LIMITED
    else:
        capacity_diagnosis = _OUTCOME_INCOMPLETE

    if not same_n_pass or not n95_pass:
        outcome = _OUTCOME_NONREGRESSION_FAILED
    elif capacity_diagnosis == _OUTCOME_PROVABLY_CAPACITY_INFEASIBLE:
        outcome = _OUTCOME_PROVABLY_CAPACITY_INFEASIBLE
    elif capacity_diagnosis == _OUTCOME_CAPACITY_LIMITED:
        outcome = _OUTCOME_CAPACITY_LIMITED
    elif capacity_diagnosis == _OUTCOME_INCOMPLETE and not mv_qualified_sizes:
        outcome = _OUTCOME_INCOMPLETE
    elif learning_controls:
        outcome = _OUTCOME_QUALIFIED_LEARNING_DEFERRED
    else:
        outcome = _OUTCOME_QUALIFIED

    return TargetMultiViewQualificationPlan(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_coverage_sparse_index_digest=target_coverage_sparse_index.content_digest,
        target_coverage_feasibility_digest=target_coverage_feasibility.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        legacy_target_data_ladder_digest=legacy_target_data_ladder.content_digest,
        target_multi_view_repair_digest=target_multi_view_repair.content_digest,
        policy=policy,
        domains=tuple(domains),
        global_common_target_sizes=common_sizes,
        legacy_n95_common=legacy_common_n95,
        mv_n95_common=mv_common_n95,
        n95_non_regression_passed=n95_pass,
        same_n_non_regression_passed=same_n_pass,
        mv_qualified_sizes=mv_qualified_sizes,
        learning_control_target_sizes=learning_controls,
        learning_control_status=_LEARNING_DEFERRED,
        capacity_diagnosis=capacity_diagnosis,
        outcome=outcome,
    )


def validate_target_multi_view_qualification_authority(
    plan: TargetMultiViewQualificationPlan,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_coverage_feasibility: Any,
    target_data_role_freeze: Any,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
    policy: TargetMultiViewQualificationPolicy | None = None,
    coverage_query_workers: int = 1,
    verify_replay: bool = False,
) -> None:
    """Validate MVQUAL lineage and, optionally, exact independent replay."""

    policy = policy or TargetMultiViewQualificationPolicy(coverage_threshold=float(target_coverage_reference.policy.coverage_threshold))
    expected = (
        target_coverage_reference.content_digest, target_coverage_sparse_index.content_digest,
        target_coverage_feasibility.content_digest, target_data_role_freeze.content_digest,
        legacy_target_data_ladder.content_digest, target_multi_view_repair.content_digest,
    )
    observed = (
        plan.target_coverage_reference_digest, plan.target_coverage_sparse_index_digest,
        plan.target_coverage_feasibility_digest, plan.target_data_role_freeze_digest,
        plan.legacy_target_data_ladder_digest, plan.target_multi_view_repair_digest,
    )
    if expected != observed or plan.dataset_id != target_coverage_reference.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 lineage changed.")
    if plan.policy.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 policy changed.")
    if any(not c.same_n_qualified for d in plan.domains for c in d.comparisons):
        if plan.same_n_non_regression_passed:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 global same-N state contradicts domain evidence.")
    if plan.n95_non_regression_passed != _n95_nonregression(plan.legacy_n95_common, plan.mv_n95_common):
        raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 N95 state is inconsistent.")
    if verify_replay:
        rebuilt = build_target_multi_view_qualification_plan(
            target_coverage_reference, target_coverage_sparse_index, target_coverage_feasibility,
            target_data_role_freeze, legacy_target_data_ladder, target_multi_view_repair,
            policy=policy, coverage_query_workers=coverage_query_workers,
        )
        if rebuilt.content_digest != plan.content_digest:
            raise TrainingDataInputError("TARGET-DATA2C-MVQUAL1 independent replay changed the authority digest.")
