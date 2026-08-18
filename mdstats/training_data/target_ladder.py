"""TARGET-DATA2C deterministic nested target-size ladder authority.

This gate consumes the frozen TARGET-DATA2A development-role authority and the
TARGET-DATA2B reference/scoring authority.  It creates one deterministic ranked
ordering per target label domain and materializes the fixed 2^7..2^13 ladder as
exact prefixes.  It does *not* decide which rungs survive Stage A; that remains
TARGET-DATA2D.

Selection is quota-first and diversity-second.  Required TARGET-DATA2B strata
and TARGET-DATA2A correlation-aware development intervals are front-loaded by a
deterministic greedy reservation.  Remaining slots are filled by exact maximin
FPS in one hierarchically normalized fused feature space assembled from every
required TARGET-DATA2B family.  This gives equal top-level distance budget to
semantic families, equal budget to individual authorities within a semantic
family, and dimension-normalized coordinates within each authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .selection import ExactFPSState, _centroid_squared_distances_bounded
from .target_coverage import (
    TargetCoverageReference,
    TargetCoverageReport,
    assert_nested_coverage_monotonicity,
    score_target_nested_subsets_coverage,
    score_target_subset_coverage,
)

TARGET_DATA_LADDER_POLICY_SCHEMA = "mdstats.target-data-ladder-policy.v1"
TARGET_DATA_LADDER_MV_POLICY_SCHEMA = "mdstats.target-data-ladder-policy.v2"
TARGET_DATA_LADDER_ENTRY_SCHEMA = "mdstats.target-data-ladder-entry.v1"
TARGET_DATA_LADDER_RUNG_SCHEMA = "mdstats.target-data-ladder-rung.v1"
TARGET_DATA_LADDER_DOMAIN_SCHEMA = "mdstats.target-data-ladder-domain.v1"
TARGET_DATA_LADDER_LEGACY_PLAN_SCHEMA = "mdstats.target-data-ladder-plan.v1"
TARGET_DATA_LADDER_V2_PLAN_SCHEMA = "mdstats.target-data-ladder-plan.v2"
TARGET_DATA_LADDER_V3_PLAN_SCHEMA = "mdstats.target-data-ladder-plan.v3"
TARGET_DATA_LADDER_PLAN_SCHEMA = "mdstats.target-data-ladder-plan.v4"
TARGET_DATA_LADDER_MV_PLAN_SCHEMA = "mdstats.target-data-ladder-plan.v5"
TARGET_DATA_LADDER_QUALIFICATION_SCHEMA = "mdstats.target-data-ladder-rung-qualification.v1"
TARGET_DATA_LADDER_LEGACY_VERSION = "mdstats.target-data2c.ladder.2026-08.v1"
TARGET_DATA_LADDER_V2_VERSION = "mdstats.target-data2c.ladder.2026-08.v2"
TARGET_DATA_LADDER_V3_VERSION = "mdstats.target-data2c.ladder.2026-08.v3"
TARGET_DATA_LADDER_VERSION = "mdstats.target-data2c.ladder.2026-08.v4"
TARGET_DATA_LADDER_MV_VERSION = "mdstats.target-data2c.ladder.2026-08.v5"
TARGET_DATA_LADDER_POLICY_VERSION = TARGET_DATA_LADDER_LEGACY_VERSION
TARGET_DATA_LADDER_MV_POLICY_VERSION = "mdstats.target-data2c.mv-fixed8.2026-08.v1"
TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION = "mdstats.target-data2c.stage-a-monotonicity.2026-08.v1"

_RANKING_ALGORITHM = "hierarchical_quota_fused_exact_fps"
_MV_RANKING_ALGORITHM = "exact_sparse_multi_view_repair1"
_STOP_EARLY = "stage_a_survivor_limit_qualified"
_STOP_EXHAUSTED = "configured_materializable_rungs_exhausted"
_STOP_FULL_LADDER = "all_materializable_rungs_materialized"
_COVERAGE_RESCUE_NUMERATORS = (3, 4, 5, 6, 7)
_COVERAGE_RESCUE_DENOMINATOR = 8


@dataclass(frozen=True, slots=True)
class TargetDataLadderPolicy:
    """Frozen TARGET-DATA2C ladder/ranking policy."""

    ladder_exponents: tuple[int, ...] = (7, 8, 9, 10, 11, 12, 13)
    minimum_materializable_rungs: int = 3
    reserve_required_strata: bool = True
    reserve_correlation_intervals: bool = True
    ranking_algorithm: str = _RANKING_ALGORITHM
    fps_tie_tolerance: float = 1.0e-12
    policy_version: str = TARGET_DATA_LADDER_POLICY_VERSION

    def __post_init__(self) -> None:
        exponents = tuple(int(v) for v in self.ladder_exponents)
        if not exponents or any(v < 0 for v in exponents) or any(b <= a for a, b in zip(exponents, exponents[1:])):
            raise TrainingDataInputError("TARGET-DATA2C ladder exponents must be nonnegative and strictly increasing.")
        if len(set(exponents)) != len(exponents):
            raise TrainingDataInputError("TARGET-DATA2C ladder exponents must be unique.")
        minimum = int(self.minimum_materializable_rungs)
        if minimum < 1 or minimum > len(exponents):
            raise TrainingDataInputError("TARGET-DATA2C minimum_materializable_rungs is invalid.")
        tolerance = float(self.fps_tie_tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise TrainingDataInputError("TARGET-DATA2C fps_tie_tolerance must be positive and finite.")
        if self.policy_version == TARGET_DATA_LADDER_POLICY_VERSION:
            if self.ranking_algorithm != _RANKING_ALGORITHM:
                raise TrainingDataInputError("Historical TARGET-DATA2C policy requires the fused exact-FPS ranking algorithm.")
        elif self.policy_version == TARGET_DATA_LADDER_MV_POLICY_VERSION:
            if self.ranking_algorithm != _MV_RANKING_ALGORITHM:
                raise TrainingDataInputError("Migrated TARGET-DATA2C policy requires the exact sparse multi-view REPAIR1 ranking authority.")
            if exponents != (7, 8, 9, 10, 11, 12, 13, 14):
                raise TrainingDataInputError("Migrated TARGET-DATA2C policy freezes exactly the 128..16384 power-of-two ladder.")
            if minimum < 4:
                raise TrainingDataInputError("Migrated TARGET-DATA2C policy requires at least four materializable rungs.")
        else:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C policy version.")
        object.__setattr__(self, "ladder_exponents", exponents)
        object.__setattr__(self, "minimum_materializable_rungs", minimum)
        object.__setattr__(self, "fps_tie_tolerance", tolerance)

    @property
    def target_sizes(self) -> tuple[int, ...]:
        return tuple(1 << exponent for exponent in self.ladder_exponents)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                TARGET_DATA_LADDER_MV_POLICY_SCHEMA
                if self.policy_version == TARGET_DATA_LADDER_MV_POLICY_VERSION
                else TARGET_DATA_LADDER_POLICY_SCHEMA
            ),
            "policy_version": self.policy_version,
            "ladder_exponents": list(self.ladder_exponents),
            "minimum_materializable_rungs": self.minimum_materializable_rungs,
            "reserve_required_strata": self.reserve_required_strata,
            "reserve_correlation_intervals": self.reserve_correlation_intervals,
            "ranking_algorithm": self.ranking_algorithm,
            "fps_tie_tolerance": self.fps_tie_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderPolicy":
        schema = payload.get("schema")
        if schema not in {TARGET_DATA_LADDER_POLICY_SCHEMA, TARGET_DATA_LADDER_MV_POLICY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C policy schema.")
        expected_version = TARGET_DATA_LADDER_MV_POLICY_VERSION if schema == TARGET_DATA_LADDER_MV_POLICY_SCHEMA else TARGET_DATA_LADDER_POLICY_VERSION
        if str(payload.get("policy_version")) != expected_version:
            raise TrainingDataSerializationError("TARGET-DATA2C policy schema/version generation mismatch.")
        result = cls(
            ladder_exponents=tuple(int(v) for v in payload["ladder_exponents"]),
            minimum_materializable_rungs=int(payload["minimum_materializable_rungs"]),
            reserve_required_strata=bool(payload["reserve_required_strata"]),
            reserve_correlation_intervals=bool(payload["reserve_correlation_intervals"]),
            ranking_algorithm=str(payload["ranking_algorithm"]),
            fps_tie_tolerance=float(payload["fps_tie_tolerance"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C policy digest mismatch.")
        return result

    @classmethod
    def migrated_fixed8(cls) -> "TargetDataLadderPolicy":
        """Return the frozen MVMIGRATE1 generated TARGET-DATA2C policy.

        The policy is intentionally explicit rather than changing the class
        default before the final GPU migration latch is authorized.
        """

        return cls(
            ladder_exponents=(7, 8, 9, 10, 11, 12, 13, 14),
            minimum_materializable_rungs=4,
            reserve_required_strata=True,
            reserve_correlation_intervals=True,
            ranking_algorithm=_MV_RANKING_ALGORITHM,
            fps_tie_tolerance=1.0e-12,
            policy_version=TARGET_DATA_LADDER_MV_POLICY_VERSION,
        )


@dataclass(frozen=True, slots=True)
class TargetDataLadderEntry:
    rank: int
    frame_uid: str
    primary_reason: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if int(self.rank) < 0:
            raise TrainingDataInputError("TARGET-DATA2C rank must be nonnegative.")
        object.__setattr__(self, "rank", int(self.rank))
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        reason = str(self.primary_reason).strip()
        if not reason:
            raise TrainingDataInputError("TARGET-DATA2C selection reason must be non-empty.")
        reasons = tuple(sorted(set((reason, *(str(v).strip() for v in self.reason_codes if str(v).strip())))))
        object.__setattr__(self, "primary_reason", reason)
        object.__setattr__(self, "reason_codes", reasons)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_DATA_LADDER_ENTRY_SCHEMA,
            "rank": self.rank,
            "frame_uid": self.frame_uid,
            "primary_reason": self.primary_reason,
            "reason_codes": list(self.reason_codes),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderEntry":
        if payload.get("schema") != TARGET_DATA_LADDER_ENTRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C entry schema.")
        result = cls(
            rank=int(payload["rank"]),
            frame_uid=str(payload["frame_uid"]),
            primary_reason=str(payload["primary_reason"]),
            reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C entry digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataLadderRung:
    target_size: int
    materializable: bool
    frame_uids: tuple[str, ...] = ()
    coverage_report: TargetCoverageReport | None = None
    mandatory_obligations_passed: bool | None = None
    unsatisfied_obligation_ids: tuple[str, ...] = ()
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size <= 0:
            raise TrainingDataInputError("TARGET-DATA2C rung target_size must be positive.")
        object.__setattr__(self, "target_size", size)
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if self.materializable:
            if len(frames) != size or len(set(frames)) != len(frames):
                raise TrainingDataInputError("TARGET-DATA2C materialized rung has inconsistent membership.")
            if self.coverage_report is None:
                raise TrainingDataInputError("TARGET-DATA2C materialized rung requires a coverage report.")
            if set(self.coverage_report.selected_frame_uids) != set(frames):
                raise TrainingDataInputError("TARGET-DATA2C rung coverage report membership differs from the rung.")
            unsatisfied = tuple(sorted(set(str(v) for v in self.unsatisfied_obligation_ids)))
            passed = not unsatisfied
            if self.mandatory_obligations_passed is None or bool(self.mandatory_obligations_passed) != passed:
                raise TrainingDataInputError("TARGET-DATA2C rung mandatory-obligation status is inconsistent.")
            object.__setattr__(self, "mandatory_obligations_passed", passed)
            object.__setattr__(self, "unsatisfied_obligation_ids", unsatisfied)
            if self.unavailable_reason is not None:
                raise TrainingDataInputError("TARGET-DATA2C materialized rung cannot have an unavailable reason.")
        else:
            if frames or self.coverage_report is not None or self.mandatory_obligations_passed is not None or self.unsatisfied_obligation_ids:
                raise TrainingDataInputError("TARGET-DATA2C unavailable rung cannot carry fabricated membership/evidence.")
            if not str(self.unavailable_reason or "").strip():
                raise TrainingDataInputError("TARGET-DATA2C unavailable rung requires an explicit reason.")
        object.__setattr__(self, "frame_uids", frames)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_DATA_LADDER_RUNG_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "frame_uids": list(self.frame_uids),
            "coverage_report": None if self.coverage_report is None else self.coverage_report.to_dict(),
            "mandatory_obligations_passed": self.mandatory_obligations_passed,
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
            "unavailable_reason": self.unavailable_reason,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderRung":
        if payload.get("schema") != TARGET_DATA_LADDER_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C rung schema.")
        report_payload = payload.get("coverage_report")
        result = cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            frame_uids=tuple(str(v) for v in payload.get("frame_uids", ())),
            coverage_report=None if report_payload is None else TargetCoverageReport.from_dict(report_payload),
            mandatory_obligations_passed=None if payload.get("mandatory_obligations_passed") is None else bool(payload["mandatory_obligations_passed"]),
            unsatisfied_obligation_ids=tuple(str(v) for v in payload.get("unsatisfied_obligation_ids", ())),
            unavailable_reason=None if payload.get("unavailable_reason") is None else str(payload["unavailable_reason"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C rung digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataLadderDomainPlan:
    label_domain_id: str
    reference_domain_digest: str
    role_domain_digest: str
    pool_frame_count: int
    required_family_ids: tuple[str, ...]
    semantic_family_ids: tuple[str, ...]
    mandatory_obligation_count: int
    mandatory_reserved_count: int
    unsatisfied_obligation_ids_at_largest_rung: tuple[str, ...]
    master_order: tuple[TargetDataLadderEntry, ...]
    rungs: tuple[TargetDataLadderRung, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.label_domain_id).strip():
            raise TrainingDataInputError("TARGET-DATA2C label_domain_id must be non-empty.")
        object.__setattr__(self, "reference_domain_digest", validate_digest(self.reference_domain_digest, name="reference_domain_digest"))
        object.__setattr__(self, "role_domain_digest", validate_digest(self.role_domain_digest, name="role_domain_digest"))
        count = int(self.pool_frame_count)
        if count <= 0:
            raise TrainingDataInputError("TARGET-DATA2C pool_frame_count must be positive.")
        object.__setattr__(self, "pool_frame_count", count)
        families = tuple(str(v) for v in self.required_family_ids)
        semantics = tuple(str(v) for v in self.semantic_family_ids)
        if not families or any(not v for v in families) or len(set(families)) != len(families):
            raise TrainingDataInputError("TARGET-DATA2C required family IDs must be unique and non-empty.")
        if not semantics or any(not v for v in semantics) or len(set(semantics)) != len(semantics):
            raise TrainingDataInputError("TARGET-DATA2C semantic family IDs must be unique and non-empty.")
        object.__setattr__(self, "required_family_ids", families)
        object.__setattr__(self, "semantic_family_ids", semantics)
        order = tuple(self.master_order)
        if tuple(item.rank for item in order) != tuple(range(len(order))) or len({item.frame_uid for item in order}) != len(order):
            raise TrainingDataInputError("TARGET-DATA2C master order must have contiguous ranks and unique frames.")
        if len(order) > count:
            raise TrainingDataInputError("TARGET-DATA2C master order exceeds the authorized pool.")
        rungs = tuple(self.rungs)
        if not rungs:
            raise TrainingDataInputError("TARGET-DATA2C domain requires rung records.")
        last_size = 0
        previous_frames: set[str] = set()
        for rung in rungs:
            if rung.target_size <= last_size:
                raise TrainingDataInputError("TARGET-DATA2C rung sizes must be strictly increasing.")
            last_size = rung.target_size
            if rung.materializable:
                expected = tuple(item.frame_uid for item in order[: rung.target_size])
                if rung.frame_uids != expected:
                    raise TrainingDataInputError("TARGET-DATA2C materialized rungs must be exact master-order prefixes.")
                current = set(rung.frame_uids)
                if not previous_frames.issubset(current):
                    raise TrainingDataInputError("TARGET-DATA2C materialized rungs are not exactly nested.")
                previous_frames = current
        mandatory_count = int(self.mandatory_obligation_count)
        reserved_count = int(self.mandatory_reserved_count)
        if mandatory_count < 0 or reserved_count < 0 or reserved_count > len(order):
            raise TrainingDataInputError("TARGET-DATA2C mandatory reservation counts are invalid.")
        object.__setattr__(self, "mandatory_obligation_count", mandatory_count)
        object.__setattr__(self, "mandatory_reserved_count", reserved_count)
        object.__setattr__(self, "unsatisfied_obligation_ids_at_largest_rung", tuple(sorted(set(str(v) for v in self.unsatisfied_obligation_ids_at_largest_rung))))
        object.__setattr__(self, "master_order", order)
        object.__setattr__(self, "rungs", rungs)

    @property
    def materialized_rungs(self) -> tuple[TargetDataLadderRung, ...]:
        return tuple(item for item in self.rungs if item.materializable)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_DATA_LADDER_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": self.reference_domain_digest,
            "role_domain_digest": self.role_domain_digest,
            "pool_frame_count": self.pool_frame_count,
            "required_family_ids": list(self.required_family_ids),
            "semantic_family_ids": list(self.semantic_family_ids),
            "mandatory_obligation_count": self.mandatory_obligation_count,
            "mandatory_reserved_count": self.mandatory_reserved_count,
            "unsatisfied_obligation_ids_at_largest_rung": list(self.unsatisfied_obligation_ids_at_largest_rung),
            "master_order": [item.to_dict() for item in self.master_order],
            "rungs": [item.to_dict() for item in self.rungs],
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderDomainPlan":
        if payload.get("schema") != TARGET_DATA_LADDER_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            role_domain_digest=str(payload["role_domain_digest"]),
            pool_frame_count=int(payload["pool_frame_count"]),
            required_family_ids=tuple(str(v) for v in payload["required_family_ids"]),
            semantic_family_ids=tuple(str(v) for v in payload["semantic_family_ids"]),
            mandatory_obligation_count=int(payload["mandatory_obligation_count"]),
            mandatory_reserved_count=int(payload["mandatory_reserved_count"]),
            unsatisfied_obligation_ids_at_largest_rung=tuple(str(v) for v in payload.get("unsatisfied_obligation_ids_at_largest_rung", ())),
            master_order=tuple(TargetDataLadderEntry.from_dict(item) for item in payload["master_order"]),
            rungs=tuple(TargetDataLadderRung.from_dict(item) for item in payload["rungs"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataLadderRungQualification:
    """Global Stage-A-equivalent qualification evidence for one materialized rung.

    This record does not select Stage-A survivors.  It freezes the monotone
    predicate that PERF-P2 uses to decide whether any larger rung can enter the
    smallest-survivor set.
    """

    target_size: int
    qualified: bool
    domain_coverage_passed: tuple[tuple[str, bool], ...]
    domain_mandatory_passed: tuple[tuple[str, bool], ...]
    coverage_report_digests: tuple[tuple[str, str], ...]
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size <= 0:
            raise TrainingDataInputError("TARGET-DATA2C qualification target_size must be positive.")
        coverage = tuple(sorted((str(k), bool(v)) for k, v in self.domain_coverage_passed))
        mandatory = tuple(sorted((str(k), bool(v)) for k, v in self.domain_mandatory_passed))
        reports = tuple(sorted((str(k), validate_digest(v, name="coverage_report_digest")) for k, v in self.coverage_report_digests))
        domain_ids = tuple(k for k, _ in coverage)
        if not domain_ids or domain_ids != tuple(k for k, _ in mandatory) or domain_ids != tuple(k for k, _ in reports):
            raise TrainingDataInputError("TARGET-DATA2C rung qualification domain evidence is incomplete or misaligned.")
        expected = all(value for _, value in coverage) and all(value for _, value in mandatory)
        if bool(self.qualified) != expected:
            raise TrainingDataInputError("TARGET-DATA2C rung qualification contradicts its domain evidence.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "domain_coverage_passed", coverage)
        object.__setattr__(self, "domain_mandatory_passed", mandatory)
        object.__setattr__(self, "coverage_report_digests", reports)
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_DATA_LADDER_QUALIFICATION_SCHEMA,
            "target_size": self.target_size,
            "qualified": self.qualified,
            "domain_coverage_passed": [[k, v] for k, v in self.domain_coverage_passed],
            "domain_mandatory_passed": [[k, v] for k, v in self.domain_mandatory_passed],
            "coverage_report_digests": [[k, v] for k, v in self.coverage_report_digests],
            "failure_reasons": list(self.failure_reasons),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderRungQualification":
        if payload.get("schema") != TARGET_DATA_LADDER_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C rung qualification schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            qualified=bool(payload["qualified"]),
            domain_coverage_passed=tuple((str(v[0]), bool(v[1])) for v in payload["domain_coverage_passed"]),
            domain_mandatory_passed=tuple((str(v[0]), bool(v[1])) for v in payload["domain_mandatory_passed"]),
            coverage_report_digests=tuple((str(v[0]), str(v[1])) for v in payload["coverage_report_digests"]),
            failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2C rung qualification digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetDataLadderPlan:
    dataset_id: str
    target_coverage_reference_digest: str
    target_data_role_freeze_digest: str
    policy: TargetDataLadderPolicy
    domains: tuple[TargetDataLadderDomainPlan, ...]
    configured_candidate_sizes: tuple[int, ...] = ()
    materialized_target_sizes: tuple[int, ...] = ()
    rung_qualifications: tuple[TargetDataLadderRungQualification, ...] = ()
    coverage_rescue_activated: bool = False
    coverage_rescue_candidate_sizes: tuple[int, ...] = ()
    coverage_rescue_min_qualifiers: int = 3
    target_multi_view_repair_digest: str | None = None
    target_multi_view_qualification_digest: str | None = None
    migration_authority_digest: str | None = None
    # PERF-P2 v2 compatibility fields.  They are non-authoritative under v3/v4.
    stage_a_survivor_limit: int = 4
    early_stop_qualifying_sizes: tuple[int, ...] = ()
    intentionally_unmaterialized_target_sizes: tuple[int, ...] = ()
    unavailable_target_sizes: tuple[int, ...] = ()
    monotonicity_contract_version: str = TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION
    last_materialized_target_size: int | None = None
    materialization_stop_reason: str = _STOP_EXHAUSTED
    authority_version: str = TARGET_DATA_LADDER_LEGACY_VERSION
    _domain_by_id: Mapping[str, TargetDataLadderDomainPlan] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("TARGET-DATA2C dataset_id must be non-empty.")
        object.__setattr__(self, "target_coverage_reference_digest", validate_digest(self.target_coverage_reference_digest, name="target_coverage_reference_digest"))
        object.__setattr__(self, "target_data_role_freeze_digest", validate_digest(self.target_data_role_freeze_digest, name="target_data_role_freeze_digest"))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C domains must be non-empty and unique.")
        allowed_versions = {
            TARGET_DATA_LADDER_MV_VERSION,
            TARGET_DATA_LADDER_VERSION,
            TARGET_DATA_LADDER_V3_VERSION,
            TARGET_DATA_LADDER_V2_VERSION,
            TARGET_DATA_LADDER_LEGACY_VERSION,
        }
        if self.authority_version not in allowed_versions:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C authority version.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})
        if self.authority_version == TARGET_DATA_LADDER_LEGACY_VERSION:
            return

        configured = tuple(int(v) for v in self.configured_candidate_sizes)
        materialized = tuple(int(v) for v in self.materialized_target_sizes)
        intentional = tuple(int(v) for v in self.intentionally_unmaterialized_target_sizes)
        unavailable = tuple(int(v) for v in self.unavailable_target_sizes)
        early = tuple(int(v) for v in self.early_stop_qualifying_sizes)
        qualifications = tuple(self.rung_qualifications)
        survivor_limit = int(self.stage_a_survivor_limit)
        rescue_activated = bool(self.coverage_rescue_activated)
        rescue_candidates = tuple(int(v) for v in self.coverage_rescue_candidate_sizes)
        rescue_min = int(self.coverage_rescue_min_qualifiers)
        mv_repair_digest = self.target_multi_view_repair_digest
        mv_qualification_digest = self.target_multi_view_qualification_digest
        migration_digest = self.migration_authority_digest
        for name, value in (
            ("target_multi_view_repair_digest", mv_repair_digest),
            ("target_multi_view_qualification_digest", mv_qualification_digest),
            ("migration_authority_digest", migration_digest),
        ):
            if value is not None:
                value = validate_digest(value, name=name)
                if name == "target_multi_view_repair_digest":
                    mv_repair_digest = value
                elif name == "target_multi_view_qualification_digest":
                    mv_qualification_digest = value
                else:
                    migration_digest = value
        if rescue_min < 1:
            raise TrainingDataInputError("TARGET-DATA2C coverage rescue minimum qualifier count must be positive.")
        if not materialized or any(b <= a for a, b in zip(materialized, materialized[1:])):
            raise TrainingDataInputError("TARGET-DATA2C materialized rung sequence must be non-empty and strictly increasing.")
        if tuple(item.target_size for item in qualifications) != materialized:
            raise TrainingDataInputError("TARGET-DATA2C qualification evidence must exactly cover materialized rungs.")
        global_pool_limit = min(item.pool_frame_count for item in domains)
        if self.authority_version in {TARGET_DATA_LADDER_V2_VERSION, TARGET_DATA_LADDER_V3_VERSION}:
            if configured != self.policy.target_sizes:
                raise TrainingDataInputError("TARGET-DATA2C v2/v3 configured candidate sequence must equal the frozen ladder policy.")
            if rescue_activated or rescue_candidates:
                raise TrainingDataInputError("TARGET-DATA2C v2/v3 authority cannot carry coverage-rescue evidence.")
        elif self.authority_version == TARGET_DATA_LADDER_VERSION:
            expected_rescue = _coverage_rescue_candidate_sizes(global_pool_limit, self.policy)
            base_sizes = self.policy.target_sizes
            base_qualified = sum(1 for item in qualifications if item.target_size in set(base_sizes) and item.qualified)
            if rescue_activated:
                if rescue_candidates != expected_rescue:
                    raise TrainingDataInputError("TARGET-DATA2C v4 coverage-rescue candidate sequence is not deterministic for the frozen pool.")
                expected_configured = tuple(sorted(set((*base_sizes, *expected_rescue))))
                if configured != expected_configured:
                    raise TrainingDataInputError("TARGET-DATA2C v4 configured sequence disagrees with the bounded coverage-rescue rule.")
                if base_qualified >= rescue_min:
                    raise TrainingDataInputError("TARGET-DATA2C v4 coverage rescue was activated even though the base ladder already had enough qualifiers.")
            else:
                if rescue_candidates:
                    raise TrainingDataInputError("TARGET-DATA2C v4 inactive coverage rescue cannot carry rescue candidates.")
                if configured != base_sizes:
                    raise TrainingDataInputError("TARGET-DATA2C v4 base configured sequence must equal the frozen ladder policy.")
            if any(v is not None for v in (mv_repair_digest, mv_qualification_digest, migration_digest)):
                raise TrainingDataInputError("Historical TARGET-DATA2C v4 cannot carry MVMIGRATE1 provenance.")
        elif self.authority_version == TARGET_DATA_LADDER_MV_VERSION:
            if self.policy.policy_version != TARGET_DATA_LADDER_MV_POLICY_VERSION:
                raise TrainingDataInputError("TARGET-DATA2C v5 requires the migrated fixed-eight policy.")
            if configured != self.policy.target_sizes:
                raise TrainingDataInputError("TARGET-DATA2C v5 configured sequence must equal the fixed-eight migrated ladder.")
            if configured != (128, 256, 512, 1024, 2048, 4096, 8192, 16384):
                raise TrainingDataInputError("TARGET-DATA2C v5 freezes exactly 128..16384 and cannot carry dynamic rescue sizes.")
            if rescue_activated or rescue_candidates:
                raise TrainingDataInputError("TARGET-DATA2C v5 retires revision-64 dynamic coverage rescue.")
            if rescue_min != 4:
                raise TrainingDataInputError("TARGET-DATA2C v5 freezes the generated minimum hard-qualifier count at four.")
            if any(v is None for v in (mv_repair_digest, mv_qualification_digest, migration_digest)):
                raise TrainingDataInputError("TARGET-DATA2C v5 requires REPAIR1, MVQUAL1, and migration-authority provenance digests.")
        expected_unavailable = tuple(v for v in configured if v > global_pool_limit)
        if unavailable != expected_unavailable:
            raise TrainingDataInputError("TARGET-DATA2C unavailable sequence disagrees with the global domain-pool limit.")
        materializable_configured = tuple(v for v in configured if v <= global_pool_limit)
        if self.last_materialized_target_size != materialized[-1]:
            raise TrainingDataInputError("TARGET-DATA2C last_materialized_target_size is inconsistent.")
        if self.monotonicity_contract_version != TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION:
            raise TrainingDataInputError("Unsupported TARGET-DATA2C monotonicity contract version.")
        domain_ids = tuple(item.label_domain_id for item in domains)
        for qualification in qualifications:
            if tuple(k for k, _ in qualification.domain_coverage_passed) != domain_ids:
                raise TrainingDataInputError("TARGET-DATA2C qualification domain identities differ from the plan.")
        for domain in domains:
            domain_materialized = tuple(item.target_size for item in domain.materialized_rungs)
            if domain_materialized != materialized:
                raise TrainingDataInputError("TARGET-DATA2C domains must materialize the same global rung sequence.")
            if len(domain.master_order) != materialized[-1]:
                raise TrainingDataInputError("TARGET-DATA2C master order must stop exactly at the last materialized rung.")
        seen_qualified = False
        for item in qualifications:
            if seen_qualified and not item.qualified:
                raise TrainingDataInputError("TARGET-DATA2C observed hard-coverage qualification is non-monotone.")
            seen_qualified = seen_qualified or item.qualified

        if self.authority_version == TARGET_DATA_LADDER_V2_VERSION:
            if survivor_limit < 1:
                raise TrainingDataInputError("TARGET-DATA2C v2 stage_a_survivor_limit must be positive.")
            materialized_set = set(materialized)
            intentional_set = set(intentional)
            unavailable_set = set(unavailable)
            if materialized_set & intentional_set or materialized_set & unavailable_set or intentional_set & unavailable_set:
                raise TrainingDataInputError("TARGET-DATA2C v2 candidate-size classifications overlap.")
            if materialized_set | intentional_set | unavailable_set != set(configured):
                raise TrainingDataInputError("TARGET-DATA2C v2 candidate-size classifications must exactly cover the configured sequence.")
            if materialized != tuple(v for v in materializable_configured if v <= materialized[-1]):
                raise TrainingDataInputError("TARGET-DATA2C v2 materialized rungs must be an exact configured prefix.")
            if self.materialization_stop_reason == _STOP_EARLY:
                if len(early) != survivor_limit:
                    raise TrainingDataInputError("TARGET-DATA2C v2 early-stop evidence must contain exactly stage_a_survivor_limit qualifiers.")
                qualified_sizes = tuple(item.target_size for item in qualifications if item.qualified)
                if early != qualified_sizes[:survivor_limit] or materialized[-1] != early[-1]:
                    raise TrainingDataInputError("TARGET-DATA2C v2 early-stop qualifiers are inconsistent with the materialized evidence.")
                expected_intentional = tuple(v for v in configured if v > materialized[-1] and v not in set(unavailable))
                if intentional != expected_intentional:
                    raise TrainingDataInputError("TARGET-DATA2C v2 intentionally unmaterialized sequence is inconsistent with early stop.")
            elif self.materialization_stop_reason == _STOP_EXHAUSTED:
                if early or intentional:
                    raise TrainingDataInputError("TARGET-DATA2C exhausted v2 authority cannot claim early-stop evidence.")
            else:
                raise TrainingDataInputError("Unsupported TARGET-DATA2C v2 materialization stop reason.")
        else:
            # v3/v4/v5 retain every globally materializable rung for the
            # epoch-3 learning screen. v4 can extend the base ladder with a
            # bounded upper-ladder coverage rescue; v5 is fixed-eight and
            # cannot rescue beyond 16,384.
            if materialized != materializable_configured:
                raise TrainingDataInputError("TARGET-DATA2C v3/v4/v5 must materialize every globally materializable configured rung.")
            if intentional or early:
                raise TrainingDataInputError("TARGET-DATA2C v3/v4/v5 cannot intentionally omit larger materializable rungs.")
            if self.materialization_stop_reason != _STOP_FULL_LADDER:
                raise TrainingDataInputError("TARGET-DATA2C v3/v4/v5 requires all-materializable-rungs stop evidence.")

        object.__setattr__(self, "configured_candidate_sizes", configured)
        object.__setattr__(self, "materialized_target_sizes", materialized)
        object.__setattr__(self, "rung_qualifications", qualifications)
        object.__setattr__(self, "stage_a_survivor_limit", survivor_limit)
        object.__setattr__(self, "early_stop_qualifying_sizes", early)
        object.__setattr__(self, "intentionally_unmaterialized_target_sizes", intentional)
        object.__setattr__(self, "unavailable_target_sizes", unavailable)
        object.__setattr__(self, "coverage_rescue_activated", rescue_activated)
        object.__setattr__(self, "coverage_rescue_candidate_sizes", rescue_candidates)
        object.__setattr__(self, "coverage_rescue_min_qualifiers", rescue_min)
        object.__setattr__(self, "target_multi_view_repair_digest", mv_repair_digest)
        object.__setattr__(self, "target_multi_view_qualification_digest", mv_qualification_digest)
        object.__setattr__(self, "migration_authority_digest", migration_digest)

    @property
    def early_stopped(self) -> bool:
        return self.authority_version == TARGET_DATA_LADDER_V2_VERSION and self.materialization_stop_reason == _STOP_EARLY

    def domain(self, label_domain_id: str) -> TargetDataLadderDomainPlan:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _payload(self) -> dict[str, Any]:
        if self.authority_version == TARGET_DATA_LADDER_LEGACY_VERSION:
            schema = TARGET_DATA_LADDER_LEGACY_PLAN_SCHEMA
        elif self.authority_version == TARGET_DATA_LADDER_V2_VERSION:
            schema = TARGET_DATA_LADDER_V2_PLAN_SCHEMA
        elif self.authority_version == TARGET_DATA_LADDER_V3_VERSION:
            schema = TARGET_DATA_LADDER_V3_PLAN_SCHEMA
        elif self.authority_version == TARGET_DATA_LADDER_VERSION:
            schema = TARGET_DATA_LADDER_PLAN_SCHEMA
        else:
            schema = TARGET_DATA_LADDER_MV_PLAN_SCHEMA
        base = {
            "schema": schema,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "policy": self.policy.to_dict(),
            "domains": [item.to_dict() for item in self.domains],
        }
        if self.authority_version == TARGET_DATA_LADDER_LEGACY_VERSION:
            return base
        common = {
            **base,
            "configured_candidate_sizes": list(self.configured_candidate_sizes),
            "materialized_target_sizes": list(self.materialized_target_sizes),
            "rung_qualifications": [item.to_dict() for item in self.rung_qualifications],
            "unavailable_target_sizes": list(self.unavailable_target_sizes),
            "monotonicity_contract_version": self.monotonicity_contract_version,
            "last_materialized_target_size": self.last_materialized_target_size,
            "materialization_stop_reason": self.materialization_stop_reason,
        }
        if self.authority_version == TARGET_DATA_LADDER_V2_VERSION:
            return {
                **common,
                "stage_a_survivor_limit": self.stage_a_survivor_limit,
                "early_stop_qualifying_sizes": list(self.early_stop_qualifying_sizes),
                "intentionally_unmaterialized_target_sizes": list(self.intentionally_unmaterialized_target_sizes),
            }
        if self.authority_version == TARGET_DATA_LADDER_VERSION:
            return {
                **common,
                "coverage_rescue_activated": self.coverage_rescue_activated,
                "coverage_rescue_candidate_sizes": list(self.coverage_rescue_candidate_sizes),
                "coverage_rescue_min_qualifiers": self.coverage_rescue_min_qualifiers,
            }
        if self.authority_version == TARGET_DATA_LADDER_MV_VERSION:
            return {
                **common,
                "coverage_rescue_activated": False,
                "coverage_rescue_candidate_sizes": [],
                "coverage_rescue_min_qualifiers": 4,
                "target_multi_view_repair_digest": self.target_multi_view_repair_digest,
                "target_multi_view_qualification_digest": self.target_multi_view_qualification_digest,
                "migration_authority_digest": self.migration_authority_digest,
            }
        return common

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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetDataLadderPlan":
        schema = payload.get("schema")
        if schema not in {
            TARGET_DATA_LADDER_MV_PLAN_SCHEMA,
            TARGET_DATA_LADDER_PLAN_SCHEMA,
            TARGET_DATA_LADDER_V3_PLAN_SCHEMA,
            TARGET_DATA_LADDER_V2_PLAN_SCHEMA,
            TARGET_DATA_LADDER_LEGACY_PLAN_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2C plan schema.")
        if schema == TARGET_DATA_LADDER_LEGACY_PLAN_SCHEMA:
            authority_version = str(payload.get("authority_version", TARGET_DATA_LADDER_LEGACY_VERSION))
            if authority_version != TARGET_DATA_LADDER_LEGACY_VERSION:
                raise TrainingDataSerializationError("TARGET-DATA2C legacy schema carries a conflicting authority version.")
        elif schema == TARGET_DATA_LADDER_V2_PLAN_SCHEMA:
            authority_version = str(payload.get("authority_version", TARGET_DATA_LADDER_V2_VERSION))
            if authority_version != TARGET_DATA_LADDER_V2_VERSION:
                raise TrainingDataSerializationError("TARGET-DATA2C v2 schema carries a conflicting authority version.")
        elif schema == TARGET_DATA_LADDER_V3_PLAN_SCHEMA:
            authority_version = str(payload.get("authority_version", TARGET_DATA_LADDER_V3_VERSION))
            if authority_version != TARGET_DATA_LADDER_V3_VERSION:
                raise TrainingDataSerializationError("TARGET-DATA2C v3 schema carries a conflicting authority version.")
        elif schema == TARGET_DATA_LADDER_PLAN_SCHEMA:
            authority_version = str(payload.get("authority_version", TARGET_DATA_LADDER_VERSION))
            if authority_version != TARGET_DATA_LADDER_VERSION:
                raise TrainingDataSerializationError("TARGET-DATA2C v4 schema requires the v4 authority version.")
        else:
            authority_version = str(payload.get("authority_version", TARGET_DATA_LADDER_MV_VERSION))
            if authority_version != TARGET_DATA_LADDER_MV_VERSION:
                raise TrainingDataSerializationError("TARGET-DATA2C v5 schema requires the v5 migrated authority version.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            policy=TargetDataLadderPolicy.from_dict(payload["policy"]),
            domains=tuple(TargetDataLadderDomainPlan.from_dict(item) for item in payload["domains"]),
            configured_candidate_sizes=tuple(int(v) for v in payload.get("configured_candidate_sizes", ())),
            materialized_target_sizes=tuple(int(v) for v in payload.get("materialized_target_sizes", ())),
            rung_qualifications=tuple(TargetDataLadderRungQualification.from_dict(item) for item in payload.get("rung_qualifications", ())),
            coverage_rescue_activated=bool(payload.get("coverage_rescue_activated", False)),
            coverage_rescue_candidate_sizes=tuple(int(v) for v in payload.get("coverage_rescue_candidate_sizes", ())),
            coverage_rescue_min_qualifiers=int(payload.get("coverage_rescue_min_qualifiers", 3)),
            target_multi_view_repair_digest=(None if payload.get("target_multi_view_repair_digest") is None else str(payload["target_multi_view_repair_digest"])),
            target_multi_view_qualification_digest=(None if payload.get("target_multi_view_qualification_digest") is None else str(payload["target_multi_view_qualification_digest"])),
            migration_authority_digest=(None if payload.get("migration_authority_digest") is None else str(payload["migration_authority_digest"])),
            stage_a_survivor_limit=int(payload.get("stage_a_survivor_limit", 4)),
            early_stop_qualifying_sizes=tuple(int(v) for v in payload.get("early_stop_qualifying_sizes", ())),
            intentionally_unmaterialized_target_sizes=tuple(int(v) for v in payload.get("intentionally_unmaterialized_target_sizes", ())),
            unavailable_target_sizes=tuple(int(v) for v in payload.get("unavailable_target_sizes", ())),
            monotonicity_contract_version=str(payload.get("monotonicity_contract_version", TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION)),
            last_materialized_target_size=None if payload.get("last_materialized_target_size") is None else int(payload["last_materialized_target_size"]),
            materialization_stop_reason=str(payload.get("materialization_stop_reason", _STOP_EXHAUSTED)),
            authority_version=authority_version,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2C plan digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class _Obligation:
    obligation_id: str
    frame_indices: tuple[int, ...]
    minimum_selected_frames: int
    reason_code: str


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    result = np.empty(values.shape[1], dtype=np.float64)
    for column in range(values.shape[1]):
        order = np.argsort(values[:, column], kind="mergesort")
        ordered_values = values[order, column]
        ordered_weights = weights[order]
        cumulative = np.cumsum(ordered_weights)
        index = int(np.searchsorted(cumulative, 0.5 * cumulative[-1], side="left"))
        result[column] = float(ordered_values[min(index, len(ordered_values) - 1)])
    return result


def _fused_required_family_matrix(domain: Any) -> tuple[np.ndarray, tuple[str, ...], tuple[str, ...]]:
    """Assemble one hierarchical family-normalized matrix for exact FPS.

    PERF-P1 computes the final FP64 width first and fills one preallocated
    matrix.  The previous list-of-blocks plus ``concatenate`` path transiently
    retained every family block and a second complete fused matrix.
    """

    required = tuple(sorted((item for item in domain.families if item.required), key=lambda item: item.family_id))
    if not required:
        raise TrainingDataInputError("TARGET-DATA2C requires at least one TARGET-DATA2B required family.")
    by_semantic: dict[str, list[Any]] = {}
    for family in required:
        by_semantic.setdefault(family.semantic_family, []).append(family)
    semantic_ids = tuple(sorted(by_semantic))
    n_frames = len(domain.frame_uids)
    ordered_families: list[tuple[Any, float, int]] = []
    total_width = 0
    for semantic in semantic_ids:
        families = tuple(sorted(by_semantic[semantic], key=lambda item: item.family_id))
        family_factor = 1.0 / math.sqrt(float(len(families)))
        for family in families:
            scales = np.asarray(family.scales, dtype=np.float64)
            width = int(scales.size) + 1
            ordered_families.append((family, family_factor, width))
            total_width += width
    matrix = np.empty((n_frames, total_width), dtype=np.float64)
    first_column = 0
    for family, family_factor, width in ordered_families:
        values = np.asarray(family.values, dtype=np.float64)
        weights = np.asarray(family.weights, dtype=np.float64)
        scales = np.asarray(family.scales, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != scales.size or values.shape[0] != len(family.frame_indices):
            raise TrainingDataInputError(f"TARGET-DATA2C family {family.family_id!r} is internally misaligned.")
        scaled = values / scales[None, :]
        center = _weighted_median(scaled, weights)
        d = scaled.shape[1]
        # Presence is a real chemical/context signal when a species/pair family
        # is not defined on every frame.  Centered coordinates are imputed at
        # zero so absence does not invent an extreme geometry.
        block = matrix[:, first_column : first_column + width]
        block.fill(0.0)
        rows = np.asarray(family.frame_indices, dtype=np.int64)
        block[rows, :d] = scaled - center[None, :]
        if len(rows) < n_frames:
            block[:, d] = -0.5
            block[rows, d] = 0.5
        # Equal coordinate budget within family, equal family budget within
        # semantic family, equal semantic-family budget globally.
        block *= family_factor / math.sqrt(float(d + 1))
        first_column += width
    matrix /= math.sqrt(float(len(semantic_ids)))
    if np.any(~np.isfinite(matrix)):
        raise TrainingDataInputError("TARGET-DATA2C fused selector matrix contains non-finite values.")
    return matrix, tuple(item.family_id for item in required), semantic_ids


def _obligations_for_domain(domain: Any, role_domain: Any, policy: TargetDataLadderPolicy) -> tuple[_Obligation, ...]:
    obligations: list[_Obligation] = []
    if policy.reserve_required_strata:
        for stratum in domain.strata:
            if not stratum.required:
                continue
            obligations.append(
                _Obligation(
                    obligation_id=f"stratum:{stratum.stratum_id}",
                    frame_indices=tuple(stratum.frame_indices),
                    minimum_selected_frames=int(stratum.minimum_selected_frames),
                    reason_code=f"mandatory_{stratum.stratum_kind}",
                )
            )
    if policy.reserve_correlation_intervals:
        index_by_uid = {uid: index for index, uid in enumerate(domain.frame_uids)}
        for interval in role_domain.development_intervals:
            indices = tuple(index_by_uid[uid] for uid in interval.frame_uids if uid in index_by_uid)
            if not indices:
                raise TrainingDataInputError(
                    f"TARGET-DATA2C development interval {interval.unit_id[:12]} has no frame in the coverage reference."
                )
            obligations.append(
                _Obligation(
                    obligation_id=f"correlation_interval:{interval.unit_id}",
                    frame_indices=tuple(sorted(set(indices))),
                    minimum_selected_frames=1,
                    reason_code="mandatory_correlation_interval",
                )
            )
    ids = [item.obligation_id for item in obligations]
    if len(ids) != len(set(ids)):
        raise TrainingDataInputError("TARGET-DATA2C mandatory obligation IDs are not unique.")
    return tuple(sorted(obligations, key=lambda item: item.obligation_id))


def _quota_first_order(
    frame_uids: Sequence[str],
    matrix: np.ndarray,
    obligations: Sequence[_Obligation],
    *,
    limit: int,
    tie_tolerance: float,
    fps_state: ExactFPSState | None = None,
) -> tuple[list[int], dict[int, set[str]], tuple[str, ...]]:
    """Greedily satisfy the most remaining hard obligations before FPS."""

    n = len(frame_uids)
    limit = min(max(0, int(limit)), n)
    if limit == 0:
        return [], {}, tuple(item.obligation_id for item in obligations)
    memberships: list[list[int]] = [[] for _ in range(n)]
    obligation_rows: list[np.ndarray] = []
    needed = np.zeros(len(obligations), dtype=np.int64)
    for oi, obligation in enumerate(obligations):
        rows = np.asarray(obligation.frame_indices, dtype=np.int64)
        if rows.size < obligation.minimum_selected_frames or np.any(rows < 0) or np.any(rows >= n):
            raise TrainingDataInputError(f"TARGET-DATA2C obligation {obligation.obligation_id!r} is invalid.")
        obligation_rows.append(rows)
        needed[oi] = obligation.minimum_selected_frames
        for row in rows:
            memberships[int(row)].append(oi)

    gain = np.fromiter((len(items) for items in memberships), dtype=np.int64, count=n)
    state = fps_state or ExactFPSState.from_matrix(frame_uids, matrix, tie_tolerance)
    if state.selected_order:
        raise TrainingDataInputError("TARGET-DATA2C quota-first FPS state must start empty.")
    if state.matrix.shape != np.asarray(matrix).shape or state.frame_uids != tuple(str(uid) for uid in frame_uids):
        raise TrainingDataInputError("TARGET-DATA2C quota-first FPS workspace is misaligned.")
    selected_mask = state.selected_mask
    selected = state.selected_order
    reasons: dict[int, set[str]] = {}
    centroid = np.mean(matrix, axis=0)
    novelty = _centroid_squared_distances_bounded(matrix, centroid)
    min_squared = state.min_squared_distance

    while len(selected) < limit and np.any(needed > 0):
        available = np.flatnonzero(~selected_mask & (gain > 0))
        if available.size == 0:
            break
        best_gain = int(np.max(gain[available]))
        tied = available[gain[available] == best_gain]
        scores = novelty[tied] if not selected else min_squared[tied]
        best_score = float(np.max(scores))
        score_tied = tied[np.abs(scores - best_score) <= tie_tolerance]
        best = min((int(row) for row in score_tied), key=lambda row: str(frame_uids[row]))
        state.append_index(best)
        touched_codes: set[str] = {"mandatory_quota"}
        for oi in memberships[best]:
            if needed[oi] <= 0:
                continue
            needed[oi] -= 1
            touched_codes.add(obligations[oi].reason_code)
            touched_codes.add(obligations[oi].obligation_id)
            if needed[oi] == 0:
                # This obligation no longer contributes gain to any candidate.
                gain[obligation_rows[oi]] -= 1
        reasons[best] = touched_codes

    unsatisfied = tuple(
        obligations[index].obligation_id
        for index, count in enumerate(needed)
        if int(count) > 0
    )
    return list(selected), reasons, unsatisfied


def _unsatisfied_obligation_ids(
    obligations: Sequence[_Obligation],
    selected_frame_indices: frozenset[int],
) -> tuple[str, ...]:
    result = []
    for obligation in obligations:
        represented = sum(index in selected_frame_indices for index in obligation.frame_indices)
        if represented < obligation.minimum_selected_frames:
            result.append(obligation.obligation_id)
    return tuple(sorted(result))


def _build_domain_plan_exhaustive_v1(
    reference: TargetCoverageReference,
    role_freeze: Any,
    label_domain_id: str,
    policy: TargetDataLadderPolicy,
    *,
    coverage_query_workers: int,
) -> TargetDataLadderDomainPlan:
    """Frozen PERF-P1/TARGET-DATA2C v1 exhaustive reference implementation."""

    domain = reference.domain(label_domain_id)
    role_domain = role_freeze.domain(label_domain_id)
    if tuple(domain.frame_uids) != tuple(sorted(role_domain.size_development_frame_uids)):
        raise TrainingDataInputError("TARGET-DATA2C role/reference frame domains disagree.")
    sizes = policy.target_sizes
    pool_size = len(domain.frame_uids)
    materializable_sizes = tuple(size for size in sizes if size <= pool_size)
    if len(materializable_sizes) < policy.minimum_materializable_rungs:
        raise TrainingDataInputError(
            "TARGET-DATA2C target-size study requires at least "
            f"{policy.minimum_materializable_rungs} materializable rungs; pool={pool_size}, "
            f"available={materializable_sizes or 'none'}."
        )
    limit = materializable_sizes[-1]
    matrix, family_ids, semantic_ids = _fused_required_family_matrix(domain)
    fps_state = ExactFPSState.from_matrix(domain.frame_uids, matrix, policy.fps_tie_tolerance)
    obligations = _obligations_for_domain(domain, role_domain, policy)
    reserved, reason_by_index, unsatisfied = _quota_first_order(
        domain.frame_uids,
        matrix,
        obligations,
        limit=limit,
        tie_tolerance=policy.fps_tie_tolerance,
        fps_state=fps_state,
    )
    remaining = limit - len(reserved)
    fps_indices = fps_state.continue_fps(remaining) if remaining > 0 else []
    selected_indices = list(reserved) + fps_indices
    if len(selected_indices) != limit or len(set(selected_indices)) != limit:
        raise TrainingDataInputError("TARGET-DATA2C deterministic FPS did not fill the largest materializable rung.")

    entries: list[TargetDataLadderEntry] = []
    reserved_set = set(reserved)
    for rank, index in enumerate(selected_indices):
        if index in reserved_set:
            codes = tuple(sorted(reason_by_index.get(index, {"mandatory_quota"})))
            primary = "mandatory_quota"
        else:
            codes = ("hierarchical_fused_fps",)
            primary = "hierarchical_fused_fps"
        entries.append(TargetDataLadderEntry(rank=rank, frame_uid=domain.frame_uids[index], primary_reason=primary, reason_codes=codes))

    order_uids = tuple(item.frame_uid for item in entries)
    rungs: list[TargetDataLadderRung] = []
    materializable_subsets = tuple(order_uids[:size] for size in materializable_sizes)
    reports = list(score_target_nested_subsets_coverage(reference, label_domain_id, materializable_subsets, query_workers=coverage_query_workers))
    report_by_size = dict(zip(materializable_sizes, reports, strict=True))
    for size in sizes:
        if size > pool_size:
            rungs.append(TargetDataLadderRung(target_size=size, materializable=False, unavailable_reason=f"authorized_pool_has_{pool_size}_frames_below_required_{size}"))
            continue
        subset = order_uids[:size]
        report = report_by_size[size]
        selected_indices_for_rung = frozenset(domain.frame_index(uid) for uid in subset)
        rung_unsatisfied = _unsatisfied_obligation_ids(obligations, selected_indices_for_rung)
        rungs.append(TargetDataLadderRung(target_size=size, materializable=True, frame_uids=subset, coverage_report=report, mandatory_obligations_passed=not rung_unsatisfied, unsatisfied_obligation_ids=rung_unsatisfied))
    assert_nested_coverage_monotonicity(reports)
    return TargetDataLadderDomainPlan(
        label_domain_id=label_domain_id,
        reference_domain_digest=domain.content_digest,
        role_domain_digest=role_domain.content_digest,
        pool_frame_count=pool_size,
        required_family_ids=family_ids,
        semantic_family_ids=semantic_ids,
        mandatory_obligation_count=len(obligations),
        mandatory_reserved_count=len(reserved),
        unsatisfied_obligation_ids_at_largest_rung=unsatisfied,
        master_order=tuple(entries),
        rungs=tuple(rungs),
    )


def _build_target_data_ladder_exhaustive_v1(
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
    *,
    policy: TargetDataLadderPolicy,
    coverage_query_workers: int = 1,
) -> TargetDataLadderPlan:
    """Qualification-only exhaustive v1 authority used as the PERF-P2 oracle."""

    workers = int(coverage_query_workers)
    domains = tuple(
        _build_domain_plan_exhaustive_v1(reference, target_data_role_freeze, label_domain_id, policy, coverage_query_workers=workers)
        for label_domain_id in sorted(item.label_domain_id for item in reference.domains)
    )
    return TargetDataLadderPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        policy=policy,
        domains=domains,
        authority_version=TARGET_DATA_LADDER_LEGACY_VERSION,
    )


@dataclass(slots=True)
class _LazyDomainWorkspace:
    domain: Any
    role_domain: Any
    matrix: np.ndarray
    family_ids: tuple[str, ...]
    semantic_ids: tuple[str, ...]
    fps_state: ExactFPSState
    obligations: tuple[_Obligation, ...]
    reserved: list[int]
    reason_by_index: dict[int, set[str]]
    unsatisfied_at_global_limit: tuple[str, ...]
    rungs: list[TargetDataLadderRung]

    def extend_to(self, size: int) -> tuple[str, ...]:
        target = int(size)
        if target > len(self.domain.frame_uids):
            raise TrainingDataInputError("TARGET-DATA2C lazy selector exceeded the authorized domain pool.")
        if len(self.fps_state.selected_order) < target:
            self.fps_state.continue_fps(target - len(self.fps_state.selected_order))
        if len(self.fps_state.selected_order) < target:
            raise TrainingDataInputError("TARGET-DATA2C lazy exact FPS could not fill the requested rung.")
        return tuple(self.domain.frame_uids[index] for index in self.fps_state.selected_order[:target])


def _stage_a_qualification_for_rungs(size: int, rungs_by_domain: Mapping[str, TargetDataLadderRung]) -> TargetDataLadderRungQualification:
    coverage: list[tuple[str, bool]] = []
    mandatory: list[tuple[str, bool]] = []
    reports: list[tuple[str, str]] = []
    reasons: list[str] = []
    for domain_id in sorted(rungs_by_domain):
        rung = rungs_by_domain[domain_id]
        if not rung.materializable or rung.coverage_report is None:
            raise TrainingDataInputError("TARGET-DATA2C v2 qualification cannot consume an unavailable rung.")
        coverage_ok = bool(rung.coverage_report.passed)
        mandatory_ok = bool(rung.mandatory_obligations_passed)
        coverage.append((domain_id, coverage_ok))
        mandatory.append((domain_id, mandatory_ok))
        reports.append((domain_id, rung.coverage_report.content_digest))
        if not coverage_ok:
            reasons.append(f"{domain_id}:coverage_or_extent_or_stratum_failed")
        if not mandatory_ok:
            reasons.append(f"{domain_id}:mandatory_obligation_failed")
    return TargetDataLadderRungQualification(
        target_size=size,
        qualified=all(v for _, v in coverage) and all(v for _, v in mandatory),
        domain_coverage_passed=tuple(coverage),
        domain_mandatory_passed=tuple(mandatory),
        coverage_report_digests=tuple(reports),
        failure_reasons=tuple(reasons),
    )


def _assert_stage_a_rung_monotonicity(previous: TargetDataLadderRung, current: TargetDataLadderRung) -> None:
    """Audit the exact monotone predicates relied on by PERF-P2 early stop."""

    if previous.coverage_report is None or current.coverage_report is None:
        raise TrainingDataInputError("TARGET-DATA2C v2 monotonicity audit requires materialized rung reports.")
    assert_nested_coverage_monotonicity((previous.coverage_report, current.coverage_report))
    prev_families = {item.family_id: item for item in previous.coverage_report.family_reports}
    cur_families = {item.family_id: item for item in current.coverage_report.family_reports}
    if prev_families.keys() != cur_families.keys():
        raise TrainingDataInputError("TARGET-DATA2C v2 monotonicity audit family identity changed.")
    for family_id in prev_families:
        before = prev_families[family_id]
        after = cur_families[family_id]
        if before.coverage_passed and not after.coverage_passed:
            raise TrainingDataInputError(f"TARGET-DATA2C v2 coverage-pass reversal for family {family_id!r}.")
        if before.extent_passed and not after.extent_passed:
            raise TrainingDataInputError(f"TARGET-DATA2C v2 extent-pass reversal for family {family_id!r}.")
    prev_strata = {item.stratum_id: item for item in previous.coverage_report.stratum_reports}
    cur_strata = {item.stratum_id: item for item in current.coverage_report.stratum_reports}
    if prev_strata.keys() != cur_strata.keys():
        raise TrainingDataInputError("TARGET-DATA2C v2 monotonicity audit stratum identity changed.")
    for stratum_id in prev_strata:
        if prev_strata[stratum_id].passed and not cur_strata[stratum_id].passed:
            raise TrainingDataInputError(f"TARGET-DATA2C v2 stratum-pass reversal for {stratum_id!r}.")
    if previous.mandatory_obligations_passed and not current.mandatory_obligations_passed:
        raise TrainingDataInputError("TARGET-DATA2C v2 mandatory-obligation pass reversed on a larger nested rung.")
    if previous.coverage_report.passed and not current.coverage_report.passed:
        raise TrainingDataInputError("TARGET-DATA2C v2 aggregate coverage pass reversed on a larger nested rung.")


def _validate_ladder_inputs(reference: TargetCoverageReference, target_data_role_freeze: Any, workers: int) -> tuple[str, ...]:
    if workers < 1:
        raise TrainingDataInputError("TARGET-DATA2C coverage_query_workers must be positive.")
    if reference.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C dataset identity differs between TARGET-DATA2A and TARGET-DATA2B.")
    if reference.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C TARGET-DATA2B reference is bound to another role-freeze authority.")
    reference_domains = {item.label_domain_id for item in reference.domains}
    role_domains = {item.label_domain_id for item in target_data_role_freeze.domains}
    if reference_domains != role_domains:
        raise TrainingDataInputError("TARGET-DATA2C label-domain identities differ between role and coverage authorities.")
    return tuple(sorted(reference_domains))


def _coverage_rescue_candidate_sizes(global_pool_limit: int, policy: TargetDataLadderPolicy) -> tuple[int, ...]:
    """Return deterministic upper-ladder rescue sizes while preserving EVAL2.

    The base power-of-two ladder remains authoritative.  When its hard-coverage
    evidence is insufficient, v4 may add 3/8..7/8 development-pool prefixes,
    aligned down to the smallest base rung.  The 7/8 ceiling guarantees at
    least a 1/8 development complement for leakage-safe EVAL2.
    """

    pool = int(global_pool_limit)
    base = policy.target_sizes
    if pool <= 0 or not base:
        return ()
    alignment = min(base)
    base_max = max(base)
    candidates: list[int] = []
    for numerator in _COVERAGE_RESCUE_NUMERATORS:
        raw = (pool * numerator) // _COVERAGE_RESCUE_DENOMINATOR
        aligned = (raw // alignment) * alignment
        if aligned > base_max and aligned < pool and aligned not in candidates:
            candidates.append(aligned)
    return tuple(candidates)


def _build_target_data_ladder_for_sizes(
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
    *,
    policy: TargetDataLadderPolicy,
    configured_sizes: Sequence[int],
    coverage_query_workers: int,
    coverage_rescue_activated: bool,
    coverage_rescue_candidate_sizes: tuple[int, ...],
    coverage_rescue_min_qualifiers: int,
) -> TargetDataLadderPlan:
    """Materialize one complete deterministic nested ladder for explicit sizes."""

    workers = int(coverage_query_workers)
    domain_ids = _validate_ladder_inputs(reference, target_data_role_freeze, workers)
    sizes = tuple(int(v) for v in configured_sizes)
    pool_sizes = {domain_id: len(reference.domain(domain_id).frame_uids) for domain_id in domain_ids}
    global_pool_limit = min(pool_sizes.values())
    materializable_sizes = tuple(size for size in sizes if size <= global_pool_limit)
    unavailable_sizes = tuple(size for size in sizes if size > global_pool_limit)
    if len(materializable_sizes) < policy.minimum_materializable_rungs:
        raise TrainingDataInputError(
            "TARGET-DATA2C target-size study requires at least "
            f"{policy.minimum_materializable_rungs} materializable rungs globally; smallest_domain_pool={global_pool_limit}, "
            f"available={materializable_sizes or 'none'}."
        )
    global_limit = materializable_sizes[-1]

    domains: list[TargetDataLadderDomainPlan] = []
    rung_by_size: dict[int, dict[str, TargetDataLadderRung]] = {size: {} for size in materializable_sizes}
    for domain_id in domain_ids:
        domain = reference.domain(domain_id)
        role_domain = target_data_role_freeze.domain(domain_id)
        if tuple(domain.frame_uids) != tuple(sorted(role_domain.size_development_frame_uids)):
            raise TrainingDataInputError("TARGET-DATA2C role/reference frame domains disagree.")
        matrix, family_ids, semantic_ids = _fused_required_family_matrix(domain)
        fps_state = ExactFPSState.from_matrix(domain.frame_uids, matrix, policy.fps_tie_tolerance)
        obligations = _obligations_for_domain(domain, role_domain, policy)
        reserved, reason_by_index, unsatisfied = _quota_first_order(
            domain.frame_uids,
            matrix,
            obligations,
            limit=global_limit,
            tie_tolerance=policy.fps_tie_tolerance,
            fps_state=fps_state,
        )
        if len(fps_state.selected_order) < global_limit:
            fps_state.continue_fps(global_limit - len(fps_state.selected_order))
        selected_indices = fps_state.selected_order[:global_limit]
        if len(selected_indices) != global_limit or len(set(selected_indices)) != global_limit:
            raise TrainingDataInputError("TARGET-DATA2C exact FPS did not fill the largest globally materializable rung.")
        reserved_set = set(reserved)
        entries: list[TargetDataLadderEntry] = []
        for rank, index in enumerate(selected_indices):
            if index in reserved_set:
                codes = tuple(sorted(reason_by_index.get(index, {"mandatory_quota"})))
                primary = "mandatory_quota"
            else:
                codes = ("hierarchical_fused_fps",)
                primary = "hierarchical_fused_fps"
            entries.append(TargetDataLadderEntry(rank=rank, frame_uid=domain.frame_uids[index], primary_reason=primary, reason_codes=codes))
        order_uids = tuple(item.frame_uid for item in entries)
        subsets = tuple(order_uids[:size] for size in materializable_sizes)
        reports = tuple(score_target_nested_subsets_coverage(reference, domain_id, subsets, query_workers=workers))
        assert_nested_coverage_monotonicity(reports)
        rungs: list[TargetDataLadderRung] = []
        for size, subset, report in zip(materializable_sizes, subsets, reports, strict=True):
            selected_set = frozenset(domain.frame_index(uid) for uid in subset)
            rung_unsatisfied = _unsatisfied_obligation_ids(obligations, selected_set)
            rung = TargetDataLadderRung(
                target_size=size,
                materializable=True,
                frame_uids=subset,
                coverage_report=report,
                mandatory_obligations_passed=not rung_unsatisfied,
                unsatisfied_obligation_ids=rung_unsatisfied,
            )
            if rungs:
                _assert_stage_a_rung_monotonicity(rungs[-1], rung)
            rungs.append(rung)
            rung_by_size[size][domain_id] = rung
        for size in unavailable_sizes:
            reason = (
                f"authorized_pool_has_{len(domain.frame_uids)}_frames_below_required_{size}"
                if size > len(domain.frame_uids)
                else f"global_stage_a_pool_limit_{global_pool_limit}_below_required_{size}"
            )
            rungs.append(TargetDataLadderRung(target_size=size, materializable=False, unavailable_reason=reason))
        selected_at_last = frozenset(domain.frame_index(uid) for uid in order_uids)
        unsatisfied_at_last = _unsatisfied_obligation_ids(obligations, selected_at_last)
        domains.append(TargetDataLadderDomainPlan(
            label_domain_id=domain_id,
            reference_domain_digest=domain.content_digest,
            role_domain_digest=role_domain.content_digest,
            pool_frame_count=len(domain.frame_uids),
            required_family_ids=family_ids,
            semantic_family_ids=semantic_ids,
            mandatory_obligation_count=len(obligations),
            mandatory_reserved_count=len(reserved),
            unsatisfied_obligation_ids_at_largest_rung=unsatisfied_at_last,
            master_order=tuple(entries),
            rungs=tuple(rungs),
        ))

    qualifications = tuple(_stage_a_qualification_for_rungs(size, rung_by_size[size]) for size in materializable_sizes)
    seen_qualified = False
    for item in qualifications:
        if seen_qualified and not item.qualified:
            raise TrainingDataInputError("TARGET-DATA2C v4 global hard-coverage qualification reversed on a larger nested rung.")
        seen_qualified = seen_qualified or item.qualified
    return TargetDataLadderPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        policy=policy,
        domains=tuple(domains),
        configured_candidate_sizes=sizes,
        materialized_target_sizes=materializable_sizes,
        rung_qualifications=qualifications,
        coverage_rescue_activated=coverage_rescue_activated,
        coverage_rescue_candidate_sizes=coverage_rescue_candidate_sizes,
        coverage_rescue_min_qualifiers=coverage_rescue_min_qualifiers,
        unavailable_target_sizes=unavailable_sizes,
        monotonicity_contract_version=TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION,
        last_materialized_target_size=materializable_sizes[-1],
        materialization_stop_reason=_STOP_FULL_LADDER,
        authority_version=TARGET_DATA_LADDER_VERSION,
    )



def build_target_data_ladder(
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
    *,
    policy: TargetDataLadderPolicy | None = None,
    coverage_query_workers: int = 1,
    stage_a_survivor_limit: int | None = None,
    minimum_coverage_qualifiers: int = 3,
) -> TargetDataLadderPlan:
    """Build TARGET-DATA2C v4 with a bounded upper-ladder coverage rescue.

    The frozen base ladder is always evaluated first.  If it supplies fewer
    than ``minimum_coverage_qualifiers`` hard-coverage qualifiers, v4 rebuilds
    the same exact nested authority with deterministic 3/8..7/8 development-
    pool rescue prefixes.  The scientific 0.95 coverage rule is unchanged;
    rescue expands only candidate density and always preserves at least 1/8 of
    the common development pool for leakage-safe EVAL2.

    ``coverage_query_workers`` is execution-only.  The deprecated
    ``stage_a_survivor_limit`` remains accepted for stale callers but does not
    truncate v4 candidates.
    """

    policy = policy or TargetDataLadderPolicy()
    workers = int(coverage_query_workers)
    if stage_a_survivor_limit is not None and int(stage_a_survivor_limit) < 1:
        raise TrainingDataInputError("TARGET-DATA2C deprecated stage_a_survivor_limit must be positive when supplied.")
    minimum = int(minimum_coverage_qualifiers)
    if minimum < 1:
        raise TrainingDataInputError("TARGET-DATA2C minimum_coverage_qualifiers must be positive.")

    base = _build_target_data_ladder_for_sizes(
        reference,
        target_data_role_freeze,
        policy=policy,
        configured_sizes=policy.target_sizes,
        coverage_query_workers=workers,
        coverage_rescue_activated=False,
        coverage_rescue_candidate_sizes=(),
        coverage_rescue_min_qualifiers=minimum,
    )
    base_qualified = sum(1 for item in base.rung_qualifications if item.qualified)
    if base_qualified >= minimum:
        return base

    global_pool_limit = min(item.pool_frame_count for item in base.domains)
    rescue = _coverage_rescue_candidate_sizes(global_pool_limit, policy)
    if not rescue:
        return base
    configured = tuple(sorted(set((*policy.target_sizes, *rescue))))
    return _build_target_data_ladder_for_sizes(
        reference,
        target_data_role_freeze,
        policy=policy,
        configured_sizes=configured,
        coverage_query_workers=workers,
        coverage_rescue_activated=True,
        coverage_rescue_candidate_sizes=rescue,
        coverage_rescue_min_qualifiers=minimum,
    )


def build_migrated_target_data_ladder(
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
    *,
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    migration_authority_digest: str,
    policy: TargetDataLadderPolicy | None = None,
    coverage_query_workers: int = 1,
) -> TargetDataLadderPlan:
    """Build the MVMIGRATE1 fixed-eight TARGET-DATA2C v5 candidate authority.

    The scientific membership comes only from the exact REPAIR1 master order.
    Coverage and hard-obligation evidence are independently reconstructed from
    TARGET-DATA2B/TARGET-DATA2A rather than trusting selector-internal scores.
    This function is safe to execute before the final GPU migration latch: the
    returned v5 record is a candidate authority until the supplied migration
    digest is itself authorized by MVMIGRATE1.
    """

    active = policy or TargetDataLadderPolicy.migrated_fixed8()
    if active.policy_version != TARGET_DATA_LADDER_MV_POLICY_VERSION:
        raise TrainingDataInputError("MVMIGRATE1 requires the migrated fixed-eight TARGET-DATA2C policy.")
    workers = int(coverage_query_workers)
    domain_ids = _validate_ladder_inputs(reference, target_data_role_freeze, workers)
    migration_digest = validate_digest(migration_authority_digest, name="migration_authority_digest")
    if target_multi_view_repair.dataset_id != reference.dataset_id:
        raise TrainingDataInputError("MVMIGRATE1 REPAIR1 dataset identity differs from TARGET-DATA2B.")
    if target_multi_view_repair.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 REPAIR1 references stale TARGET-DATA2B evidence.")
    if target_multi_view_qualification.dataset_id != reference.dataset_id:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 dataset identity differs from TARGET-DATA2B.")
    if target_multi_view_qualification.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 references stale TARGET-DATA2B evidence.")
    if target_multi_view_qualification.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 references a stale TARGET-DATA2A role freeze.")
    if target_multi_view_qualification.target_multi_view_repair_digest != target_multi_view_repair.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 does not qualify the supplied REPAIR1 authority.")

    configured = active.target_sizes
    pool_sizes = {domain_id: len(reference.domain(domain_id).frame_uids) for domain_id in domain_ids}
    global_pool_limit = min(pool_sizes.values())
    materializable_sizes = tuple(size for size in configured if size <= global_pool_limit)
    unavailable_sizes = tuple(size for size in configured if size > global_pool_limit)
    if len(materializable_sizes) < active.minimum_materializable_rungs:
        raise TrainingDataInputError(
            "MVMIGRATE1 fixed-eight target-size study requires at least four materializable rungs globally; "
            f"smallest_domain_pool={global_pool_limit}, available={materializable_sizes or 'none'}."
        )

    domains: list[TargetDataLadderDomainPlan] = []
    rung_by_size: dict[int, dict[str, TargetDataLadderRung]] = {size: {} for size in materializable_sizes}
    for domain_id in domain_ids:
        domain = reference.domain(domain_id)
        role_domain = target_data_role_freeze.domain(domain_id)
        repair_domain = target_multi_view_repair.domain(domain_id)
        qualification_domain = next(
            (item for item in target_multi_view_qualification.domains if item.label_domain_id == domain_id),
            None,
        )
        if qualification_domain is None:
            raise TrainingDataInputError(f"MVMIGRATE1 MVQUAL1 lacks domain {domain_id!r}.")
        if repair_domain.reference_domain_digest != domain.content_digest:
            raise TrainingDataInputError(f"MVMIGRATE1 REPAIR1 reference domain changed for {domain_id!r}.")
        if qualification_domain.mv_repair_domain_digest != repair_domain.content_digest:
            raise TrainingDataInputError(f"MVMIGRATE1 MVQUAL1 does not qualify the live REPAIR1 domain {domain_id!r}.")
        if tuple(domain.frame_uids) != tuple(sorted(role_domain.size_development_frame_uids)):
            raise TrainingDataInputError("MVMIGRATE1 role/reference frame domains disagree.")

        required = tuple(sorted((item for item in domain.families if item.required), key=lambda item: item.family_id))
        if not required:
            raise TrainingDataInputError("MVMIGRATE1 requires at least one required TARGET-DATA2B family.")
        family_ids = tuple(item.family_id for item in required)
        semantic_ids = tuple(sorted({item.semantic_family for item in required}))
        obligations = _obligations_for_domain(domain, role_domain, active)
        max_materialized = materializable_sizes[-1]
        order_uids = tuple(repair_domain.repaired_master_order[:max_materialized])
        if len(order_uids) != max_materialized or len(set(order_uids)) != max_materialized:
            raise TrainingDataInputError(f"MVMIGRATE1 REPAIR1 order cannot materialize n{max_materialized} for {domain_id!r}.")
        if any(uid not in set(domain.frame_uids) for uid in order_uids):
            raise TrainingDataInputError(f"MVMIGRATE1 REPAIR1 order escaped the TARGET-DATA2B domain {domain_id!r}.")

        swapped_replacements = {
            swap.replacement_frame_uid
            for rung in repair_domain.rungs
            for swap in rung.swaps
        }
        entries = tuple(
            TargetDataLadderEntry(
                rank=rank,
                frame_uid=uid,
                primary_reason="multi_view_repair1",
                reason_codes=(
                    "exact_sparse_multi_view",
                    "shell_exchange" if uid in swapped_replacements else "progressive_mvsel1",
                ),
            )
            for rank, uid in enumerate(order_uids)
        )
        subsets = tuple(order_uids[:size] for size in materializable_sizes)
        reports = tuple(score_target_nested_subsets_coverage(reference, domain_id, subsets, query_workers=workers))
        assert_nested_coverage_monotonicity(reports)
        index_by_uid = {uid: index for index, uid in enumerate(domain.frame_uids)}
        obligation_indices = set(index for item in obligations for index in item.frame_indices)
        selected_indices_at_last = frozenset(index_by_uid[uid] for uid in order_uids)
        hard_contributor_count = sum(1 for index in selected_indices_at_last if index in obligation_indices)

        rungs: list[TargetDataLadderRung] = []
        for size, subset, report in zip(materializable_sizes, subsets, reports, strict=True):
            selected_set = frozenset(index_by_uid[uid] for uid in subset)
            rung_unsatisfied = _unsatisfied_obligation_ids(obligations, selected_set)
            rung = TargetDataLadderRung(
                target_size=size,
                materializable=True,
                frame_uids=subset,
                coverage_report=report,
                mandatory_obligations_passed=not rung_unsatisfied,
                unsatisfied_obligation_ids=rung_unsatisfied,
            )
            if rungs:
                _assert_stage_a_rung_monotonicity(rungs[-1], rung)
            rungs.append(rung)
            rung_by_size[size][domain_id] = rung
        for size in unavailable_sizes:
            reason = (
                f"authorized_pool_has_{len(domain.frame_uids)}_frames_below_required_{size}"
                if size > len(domain.frame_uids)
                else f"global_stage_a_pool_limit_{global_pool_limit}_below_required_{size}"
            )
            rungs.append(TargetDataLadderRung(target_size=size, materializable=False, unavailable_reason=reason))

        unsatisfied_at_last = _unsatisfied_obligation_ids(obligations, selected_indices_at_last)
        domains.append(
            TargetDataLadderDomainPlan(
                label_domain_id=domain_id,
                reference_domain_digest=domain.content_digest,
                role_domain_digest=role_domain.content_digest,
                pool_frame_count=len(domain.frame_uids),
                required_family_ids=family_ids,
                semantic_family_ids=semantic_ids,
                mandatory_obligation_count=len(obligations),
                mandatory_reserved_count=hard_contributor_count,
                unsatisfied_obligation_ids_at_largest_rung=unsatisfied_at_last,
                master_order=entries,
                rungs=tuple(rungs),
            )
        )

    qualifications = tuple(_stage_a_qualification_for_rungs(size, rung_by_size[size]) for size in materializable_sizes)
    seen_qualified = False
    for item in qualifications:
        if seen_qualified and not item.qualified:
            raise TrainingDataInputError("MVMIGRATE1 independently rescored hard coverage regressed on a larger nested rung.")
        seen_qualified = seen_qualified or item.qualified

    plan = TargetDataLadderPlan(
        dataset_id=reference.dataset_id,
        target_coverage_reference_digest=reference.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        policy=active,
        domains=tuple(domains),
        configured_candidate_sizes=configured,
        materialized_target_sizes=materializable_sizes,
        rung_qualifications=qualifications,
        coverage_rescue_activated=False,
        coverage_rescue_candidate_sizes=(),
        coverage_rescue_min_qualifiers=4,
        target_multi_view_repair_digest=target_multi_view_repair.content_digest,
        target_multi_view_qualification_digest=target_multi_view_qualification.content_digest,
        migration_authority_digest=migration_digest,
        unavailable_target_sizes=unavailable_sizes,
        monotonicity_contract_version=TARGET_DATA_LADDER_MONOTONICITY_CONTRACT_VERSION,
        last_materialized_target_size=materializable_sizes[-1],
        materialization_stop_reason=_STOP_FULL_LADDER,
        authority_version=TARGET_DATA_LADDER_MV_VERSION,
    )
    return plan


def validate_migrated_target_data_ladder_authority(
    plan: TargetDataLadderPlan,
    *,
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    migration_authority_digest: str,
    coverage_query_workers: int = 1,
) -> None:
    """Rebuild and authenticate a TARGET-DATA2C v5 MVMIGRATE1 candidate."""

    if plan.authority_version != TARGET_DATA_LADDER_MV_VERSION:
        raise TrainingDataInputError("MVMIGRATE1 validation requires TARGET-DATA2C v5.")
    rebuilt = build_migrated_target_data_ladder(
        reference,
        target_data_role_freeze,
        target_multi_view_repair=target_multi_view_repair,
        target_multi_view_qualification=target_multi_view_qualification,
        migration_authority_digest=migration_authority_digest,
        policy=plan.policy,
        coverage_query_workers=coverage_query_workers,
    )
    if rebuilt.content_digest != plan.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C v5 differs from recomputed MVMIGRATE1 authority.")

def validate_target_data_ladder_authority(
    plan: TargetDataLadderPlan,
    *,
    reference: TargetCoverageReference,
    target_data_role_freeze: Any,
) -> None:
    """Authenticate a stored TARGET-DATA2C v2 plan against live upstream authority."""

    if plan.authority_version != TARGET_DATA_LADDER_VERSION:
        raise TrainingDataInputError("TARGET-DATA2C pre-v4 authority is stale under the bounded upper-ladder coverage-rescue correction and must be rebuilt as v4.")
    if plan.dataset_id != reference.dataset_id or plan.dataset_id != target_data_role_freeze.dataset_id:
        raise TrainingDataInputError("TARGET-DATA2C dataset identity changed.")
    if plan.target_coverage_reference_digest != reference.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C authority mismatch: target coverage reference changed.")
    if plan.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("TARGET-DATA2C authority mismatch: target role freeze changed.")
    if {item.label_domain_id for item in plan.domains} != {item.label_domain_id for item in reference.domains}:
        raise TrainingDataInputError("TARGET-DATA2C domain identities changed.")
    for frozen in plan.domains:
        reference_domain = reference.domain(frozen.label_domain_id)
        role_domain = target_data_role_freeze.domain(frozen.label_domain_id)
        if frozen.reference_domain_digest != reference_domain.content_digest:
            raise TrainingDataInputError(f"TARGET-DATA2C reference domain changed for {frozen.label_domain_id!r}.")
        if frozen.role_domain_digest != role_domain.content_digest:
            raise TrainingDataInputError(f"TARGET-DATA2C role domain changed for {frozen.label_domain_id!r}.")
        if frozen.pool_frame_count != len(reference_domain.frame_uids):
            raise TrainingDataInputError(f"TARGET-DATA2C pool size changed for {frozen.label_domain_id!r}.")
        reports = tuple(item.coverage_report for item in frozen.materialized_rungs if item.coverage_report is not None)
        for rung in frozen.materialized_rungs:
            if rung.coverage_report is None or rung.coverage_report.reference_digest != reference.content_digest:
                raise TrainingDataInputError("TARGET-DATA2C stored rung coverage evidence is stale.")
        assert_nested_coverage_monotonicity(reports)
        for before, after in zip(frozen.materialized_rungs, frozen.materialized_rungs[1:]):
            _assert_stage_a_rung_monotonicity(before, after)

