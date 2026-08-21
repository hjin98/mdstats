"""TARGET-DATA2C-MVMIGRATE1 fail-closed generated-policy migration authority.

MVMIGRATE1 is the only gate allowed to replace the revision-64 TARGET-DATA2C
v4 dynamic-rescue production path with the exact sparse multi-view fixed-eight
candidate ladder.  The migration is intentionally two-phase:

* CPU/control-plane development can freeze the migration decision, exact v5
  candidate membership, and all content-addressed upstream lineage.
* activation requires the deferred FINAL-GPU1 learning-control and
  SIZE-FIDELITY2 qualification evidence.  Until both pass, v4 remains the
  executable compatibility path and the v5 ladder is only an authenticated
  migration candidate.

This prevents synthetic or CPU-only evidence from masquerading as the final
accelerator qualification while allowing the expensive selector/index work to
be reused unchanged at final release qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .size_halve2 import SIZE_HALVE2_FIXED_TARGET_SIZES


TARGET_MV_MIGRATION_POLICY_SCHEMA = "mdstats.target-mv-migration-policy.v1"
TARGET_MV_LEARNING_CONTROL_ROW_SCHEMA = "mdstats.target-mv-learning-control-row.v1"
TARGET_MV_LEARNING_CONTROL_REPORT_SCHEMA = "mdstats.target-mv-learning-control-report.v1"
TARGET_MV_MIGRATION_PLAN_SCHEMA = "mdstats.target-mv-migration-plan.v1"
TARGET_MV_MIGRATION_ACTIVATION_SCHEMA = "mdstats.target-mv-migration-activation.v1"
TARGET_MV_MIGRATION_VERSION = "mdstats.target-data2c-mvmigrate1.2026-08.v1"

MIGRATED_TARGET_DATA2C_VERSION = "mdstats.target-data2c.ladder.2026-08.v5"
MIGRATED_TARGET_DATA2D_VERSION = "mdstats.target-data2d.size-convergence.2026-08.v3"
MIGRATED_TARGET_DATA2E_VERSION = "mdstats.target-data2e.production-corpus.2026-08.v3"

_MIGRATION_PENDING = "awaiting_final_gpu_qualification"
_MIGRATION_AUTHORIZED = "authorized_for_atomic_activation"
_MIGRATION_BLOCKED = "blocked_scientific_preconditions"
_GPU_PASSED = "passed"
_GPU_DEFERRED = "deferred_final_gpu_qualification"


@dataclass(frozen=True, slots=True)
class TargetMultiViewMigrationPolicy:
    """Frozen generated-policy replacement contract for MVMIGRATE1."""

    target_sizes: tuple[int, ...] = SIZE_HALVE2_FIXED_TARGET_SIZES
    minimum_hard_qualifiers: int = 4
    fixed_ceiling: int = 16384
    retire_dynamic_rescue: bool = True
    require_mvqual_learning_controls: bool = True
    require_size_fidelity2_gpu_pass: bool = True
    migrated_target_data2c_version: str = MIGRATED_TARGET_DATA2C_VERSION
    migrated_target_data2d_version: str = MIGRATED_TARGET_DATA2D_VERSION
    migrated_target_data2e_version: str = MIGRATED_TARGET_DATA2E_VERSION
    authority_version: str = TARGET_MV_MIGRATION_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.target_sizes)
        if sizes != SIZE_HALVE2_FIXED_TARGET_SIZES:
            raise TrainingDataInputError("MVMIGRATE1 freezes exactly the eight 128..16384 target sizes.")
        if int(self.minimum_hard_qualifiers) != 4:
            raise TrainingDataInputError("MVMIGRATE1 freezes the generated minimum hard-qualifier count at four.")
        if int(self.fixed_ceiling) != 16384 or max(sizes) != 16384:
            raise TrainingDataInputError("MVMIGRATE1 freezes 16,384 as the generated target-size ceiling.")
        if not self.retire_dynamic_rescue:
            raise TrainingDataInputError("MVMIGRATE1 must retire revision-64 dynamic rescue from generated semantics.")
        if not self.require_mvqual_learning_controls or not self.require_size_fidelity2_gpu_pass:
            raise TrainingDataInputError("MVMIGRATE1 cannot weaken final GPU qualification prerequisites.")
        if self.migrated_target_data2c_version != MIGRATED_TARGET_DATA2C_VERSION:
            raise TrainingDataInputError("Unsupported migrated TARGET-DATA2C version.")
        if self.migrated_target_data2d_version != MIGRATED_TARGET_DATA2D_VERSION:
            raise TrainingDataInputError("Unsupported migrated TARGET-DATA2D version.")
        if self.migrated_target_data2e_version != MIGRATED_TARGET_DATA2E_VERSION:
            raise TrainingDataInputError("Unsupported migrated TARGET-DATA2E version.")
        if self.authority_version != TARGET_MV_MIGRATION_VERSION:
            raise TrainingDataInputError("Unsupported MVMIGRATE1 authority version.")
        object.__setattr__(self, "target_sizes", sizes)
        object.__setattr__(self, "minimum_hard_qualifiers", 4)
        object.__setattr__(self, "fixed_ceiling", 16384)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MV_MIGRATION_POLICY_SCHEMA,
            "target_sizes": list(self.target_sizes),
            "minimum_hard_qualifiers": self.minimum_hard_qualifiers,
            "fixed_ceiling": self.fixed_ceiling,
            "retire_dynamic_rescue": self.retire_dynamic_rescue,
            "require_mvqual_learning_controls": self.require_mvqual_learning_controls,
            "require_size_fidelity2_gpu_pass": self.require_size_fidelity2_gpu_pass,
            "migrated_target_data2c_version": self.migrated_target_data2c_version,
            "migrated_target_data2d_version": self.migrated_target_data2d_version,
            "migrated_target_data2e_version": self.migrated_target_data2e_version,
            "authority_version": self.authority_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewMigrationPolicy":
        if payload.get("schema") != TARGET_MV_MIGRATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVMIGRATE1 policy schema.")
        result = cls(
            target_sizes=tuple(int(v) for v in payload["target_sizes"]),
            minimum_hard_qualifiers=int(payload["minimum_hard_qualifiers"]),
            fixed_ceiling=int(payload["fixed_ceiling"]),
            retire_dynamic_rescue=bool(payload["retire_dynamic_rescue"]),
            require_mvqual_learning_controls=bool(payload["require_mvqual_learning_controls"]),
            require_size_fidelity2_gpu_pass=bool(payload["require_size_fidelity2_gpu_pass"]),
            migrated_target_data2c_version=str(payload["migrated_target_data2c_version"]),
            migrated_target_data2d_version=str(payload["migrated_target_data2d_version"]),
            migrated_target_data2e_version=str(payload["migrated_target_data2e_version"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MVMIGRATE1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewLearningControlRow:
    """One paired legacy-vs-MV TRAIN2/EVAL2 control at identical N/seed."""

    target_size: int
    optimizer_seed: int
    legacy_target_force_score_mev_per_a: float
    mv_target_force_score_mev_per_a: float
    practical_equivalence_mev_per_a: float
    common_training_protocol_digest: str
    legacy_evaluation_digest: str
    mv_evaluation_digest: str

    def __post_init__(self) -> None:
        size = int(self.target_size)
        seed = int(self.optimizer_seed)
        legacy = float(self.legacy_target_force_score_mev_per_a)
        mv = float(self.mv_target_force_score_mev_per_a)
        epsilon = float(self.practical_equivalence_mev_per_a)
        if size < 1 or seed < 0:
            raise TrainingDataInputError("MVMIGRATE1 learning-control size/seed is invalid.")
        if any(not math.isfinite(v) or v < 0.0 for v in (legacy, mv)):
            raise TrainingDataInputError("MVMIGRATE1 learning-control target scores must be finite and nonnegative.")
        if not math.isfinite(epsilon) or epsilon <= 0.0:
            raise TrainingDataInputError("MVMIGRATE1 learning-control equivalence width must be positive and finite.")
        for name in ("common_training_protocol_digest", "legacy_evaluation_digest", "mv_evaluation_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "optimizer_seed", seed)
        object.__setattr__(self, "legacy_target_force_score_mev_per_a", legacy)
        object.__setattr__(self, "mv_target_force_score_mev_per_a", mv)
        object.__setattr__(self, "practical_equivalence_mev_per_a", epsilon)

    @property
    def passed(self) -> bool:
        return self.mv_target_force_score_mev_per_a <= (
            self.legacy_target_force_score_mev_per_a + self.practical_equivalence_mev_per_a + 1.0e-12
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MV_LEARNING_CONTROL_ROW_SCHEMA,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "legacy_target_force_score_mev_per_a": self.legacy_target_force_score_mev_per_a,
            "mv_target_force_score_mev_per_a": self.mv_target_force_score_mev_per_a,
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "common_training_protocol_digest": self.common_training_protocol_digest,
            "legacy_evaluation_digest": self.legacy_evaluation_digest,
            "mv_evaluation_digest": self.mv_evaluation_digest,
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewLearningControlRow":
        if payload.get("schema") != TARGET_MV_LEARNING_CONTROL_ROW_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVMIGRATE1 learning-control row schema.")
        result = cls(
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            legacy_target_force_score_mev_per_a=float(payload["legacy_target_force_score_mev_per_a"]),
            mv_target_force_score_mev_per_a=float(payload["mv_target_force_score_mev_per_a"]),
            practical_equivalence_mev_per_a=float(payload["practical_equivalence_mev_per_a"]),
            common_training_protocol_digest=str(payload["common_training_protocol_digest"]),
            legacy_evaluation_digest=str(payload["legacy_evaluation_digest"]),
            mv_evaluation_digest=str(payload["mv_evaluation_digest"]),
        )
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("MVMIGRATE1 learning-control pass flag mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVMIGRATE1 learning-control row digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewLearningControlReport:
    dataset_id: str
    target_multi_view_qualification_digest: str
    control_target_sizes: tuple[int, ...]
    rows: tuple[TargetMultiViewLearningControlRow, ...]
    gpu_qualification_status: str = _GPU_PASSED
    authority_version: str = TARGET_MV_MIGRATION_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("MVMIGRATE1 learning-control dataset_id cannot be empty.")
        object.__setattr__(
            self,
            "target_multi_view_qualification_digest",
            validate_digest(self.target_multi_view_qualification_digest, name="target_multi_view_qualification_digest"),
        )
        sizes = tuple(sorted(set(int(v) for v in self.control_target_sizes)))
        rows = tuple(sorted(self.rows, key=lambda v: (v.target_size, v.optimizer_seed)))
        if not sizes or any(v not in SIZE_HALVE2_FIXED_TARGET_SIZES for v in sizes):
            raise TrainingDataInputError("MVMIGRATE1 learning-control target sizes are invalid.")
        if set(v.target_size for v in rows) != set(sizes):
            raise TrainingDataInputError("MVMIGRATE1 learning-control report must contain evidence for every control size.")
        keys = [(v.target_size, v.optimizer_seed) for v in rows]
        if len(keys) != len(set(keys)):
            raise TrainingDataInputError("MVMIGRATE1 learning-control report contains duplicate N/seed rows.")
        if self.gpu_qualification_status != _GPU_PASSED:
            raise TrainingDataInputError("MVMIGRATE1 learning-control report is only authoritative after FINAL-GPU1 passes.")
        if self.authority_version != TARGET_MV_MIGRATION_VERSION:
            raise TrainingDataInputError("Unsupported MVMIGRATE1 learning-control authority version.")
        object.__setattr__(self, "control_target_sizes", sizes)
        object.__setattr__(self, "rows", rows)

    @property
    def passed(self) -> bool:
        return bool(self.rows) and all(v.passed for v in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MV_LEARNING_CONTROL_REPORT_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_multi_view_qualification_digest": self.target_multi_view_qualification_digest,
            "control_target_sizes": list(self.control_target_sizes),
            "rows": [v.to_dict() for v in self.rows],
            "passed": self.passed,
            "gpu_qualification_status": self.gpu_qualification_status,
            "authority_version": self.authority_version,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewLearningControlReport":
        if payload.get("schema") != TARGET_MV_LEARNING_CONTROL_REPORT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVMIGRATE1 learning-control report schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_multi_view_qualification_digest=str(payload["target_multi_view_qualification_digest"]),
            control_target_sizes=tuple(int(v) for v in payload["control_target_sizes"]),
            rows=tuple(TargetMultiViewLearningControlRow.from_dict(v) for v in payload["rows"]),
            gpu_qualification_status=str(payload["gpu_qualification_status"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("MVMIGRATE1 learning-control report pass flag mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVMIGRATE1 learning-control report digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewMigrationPlan:
    dataset_id: str
    legacy_target_data_ladder_digest: str
    target_multi_view_repair_digest: str
    target_multi_view_qualification_digest: str
    size_halve2_plan_digest: str
    size_fidelity2_execution_plan_digest: str
    policy: TargetMultiViewMigrationPolicy
    mv_qualified_sizes: tuple[int, ...]
    learning_control_report_digest: str | None = None
    size_fidelity2_qualification_digest: str | None = None
    status: str = _MIGRATION_PENDING
    decision_reason: str = "final GPU migration prerequisites are pending"
    authority_version: str = TARGET_MV_MIGRATION_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("MVMIGRATE1 dataset_id cannot be empty.")
        for name in (
            "legacy_target_data_ladder_digest",
            "target_multi_view_repair_digest",
            "target_multi_view_qualification_digest",
            "size_halve2_plan_digest",
            "size_fidelity2_execution_plan_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("learning_control_report_digest", "size_fidelity2_qualification_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        qualified = tuple(sorted(set(int(v) for v in self.mv_qualified_sizes)))
        if any(v not in self.policy.target_sizes for v in qualified):
            raise TrainingDataInputError("MVMIGRATE1 qualified sizes escape the fixed-eight policy.")
        if self.status not in {_MIGRATION_PENDING, _MIGRATION_AUTHORIZED, _MIGRATION_BLOCKED}:
            raise TrainingDataInputError("Unsupported MVMIGRATE1 migration status.")
        if self.status == _MIGRATION_AUTHORIZED:
            if len(qualified) < self.policy.minimum_hard_qualifiers:
                raise TrainingDataInputError("MVMIGRATE1 cannot authorize fewer than four hard-qualified sizes.")
            if self.learning_control_report_digest is None or self.size_fidelity2_qualification_digest is None:
                raise TrainingDataInputError("MVMIGRATE1 authorization requires both final GPU qualification digests.")
        reason = str(self.decision_reason).strip()
        if not reason:
            raise TrainingDataInputError("MVMIGRATE1 decision reason cannot be empty.")
        if self.authority_version != TARGET_MV_MIGRATION_VERSION:
            raise TrainingDataInputError("Unsupported MVMIGRATE1 plan authority version.")
        object.__setattr__(self, "mv_qualified_sizes", qualified)
        object.__setattr__(self, "decision_reason", reason)

    @property
    def activation_authorized(self) -> bool:
        return self.status == _MIGRATION_AUTHORIZED

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MV_MIGRATION_PLAN_SCHEMA,
            "dataset_id": self.dataset_id,
            "legacy_target_data_ladder_digest": self.legacy_target_data_ladder_digest,
            "target_multi_view_repair_digest": self.target_multi_view_repair_digest,
            "target_multi_view_qualification_digest": self.target_multi_view_qualification_digest,
            "size_halve2_plan_digest": self.size_halve2_plan_digest,
            "size_fidelity2_execution_plan_digest": self.size_fidelity2_execution_plan_digest,
            "policy": self.policy.to_dict(),
            "mv_qualified_sizes": list(self.mv_qualified_sizes),
            "learning_control_report_digest": self.learning_control_report_digest,
            "size_fidelity2_qualification_digest": self.size_fidelity2_qualification_digest,
            "status": self.status,
            "decision_reason": self.decision_reason,
            "authority_version": self.authority_version,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewMigrationPlan":
        if payload.get("schema") != TARGET_MV_MIGRATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVMIGRATE1 plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            legacy_target_data_ladder_digest=str(payload["legacy_target_data_ladder_digest"]),
            target_multi_view_repair_digest=str(payload["target_multi_view_repair_digest"]),
            target_multi_view_qualification_digest=str(payload["target_multi_view_qualification_digest"]),
            size_halve2_plan_digest=str(payload["size_halve2_plan_digest"]),
            size_fidelity2_execution_plan_digest=str(payload["size_fidelity2_execution_plan_digest"]),
            policy=TargetMultiViewMigrationPolicy.from_dict(payload["policy"]),
            mv_qualified_sizes=tuple(int(v) for v in payload["mv_qualified_sizes"]),
            learning_control_report_digest=(None if payload.get("learning_control_report_digest") is None else str(payload["learning_control_report_digest"])),
            size_fidelity2_qualification_digest=(None if payload.get("size_fidelity2_qualification_digest") is None else str(payload["size_fidelity2_qualification_digest"])),
            status=str(payload["status"]),
            decision_reason=str(payload["decision_reason"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVMIGRATE1 plan digest mismatch.")
        return result



@dataclass(frozen=True, slots=True)
class TargetMultiViewMigrationActivation:
    """Atomic live-alias promotion receipt after positive FINAL-GPU1 v2 evidence."""

    dataset_id: str
    final_gpu1_qualification_digest: str
    learning_control_report_digest: str
    size_fidelity2_qualification_digest: str
    migration_plan_digest: str
    legacy_target_data_ladder_digest: str
    migrated_target_data_ladder_digest: str
    migrated_target_size_convergence_digest: str
    prior_target_production_corpus_digest: str | None = None
    status: str = "activated"
    authority_version: str = TARGET_MV_MIGRATION_VERSION

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("MVMIGRATE1 activation dataset_id cannot be empty.")
        for name in (
            "final_gpu1_qualification_digest",
            "learning_control_report_digest",
            "size_fidelity2_qualification_digest",
            "migration_plan_digest",
            "legacy_target_data_ladder_digest",
            "migrated_target_data_ladder_digest",
            "migrated_target_size_convergence_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.prior_target_production_corpus_digest is not None:
            object.__setattr__(
                self, "prior_target_production_corpus_digest",
                validate_digest(self.prior_target_production_corpus_digest, name="prior_target_production_corpus_digest"),
            )
        if self.status != "activated":
            raise TrainingDataInputError("MVMIGRATE1 activation receipt must be terminally activated.")
        if self.authority_version != TARGET_MV_MIGRATION_VERSION:
            raise TrainingDataInputError("Unsupported MVMIGRATE1 activation authority version.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MV_MIGRATION_ACTIVATION_SCHEMA,
            "dataset_id": self.dataset_id,
            "final_gpu1_qualification_digest": self.final_gpu1_qualification_digest,
            "learning_control_report_digest": self.learning_control_report_digest,
            "size_fidelity2_qualification_digest": self.size_fidelity2_qualification_digest,
            "migration_plan_digest": self.migration_plan_digest,
            "legacy_target_data_ladder_digest": self.legacy_target_data_ladder_digest,
            "migrated_target_data_ladder_digest": self.migrated_target_data_ladder_digest,
            "migrated_target_size_convergence_digest": self.migrated_target_size_convergence_digest,
            "prior_target_production_corpus_digest": self.prior_target_production_corpus_digest,
            "status": self.status,
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewMigrationActivation":
        if payload.get("schema") != TARGET_MV_MIGRATION_ACTIVATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVMIGRATE1 activation schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            final_gpu1_qualification_digest=str(payload["final_gpu1_qualification_digest"]),
            learning_control_report_digest=str(payload["learning_control_report_digest"]),
            size_fidelity2_qualification_digest=str(payload["size_fidelity2_qualification_digest"]),
            migration_plan_digest=str(payload["migration_plan_digest"]),
            legacy_target_data_ladder_digest=str(payload["legacy_target_data_ladder_digest"]),
            migrated_target_data_ladder_digest=str(payload["migrated_target_data_ladder_digest"]),
            migrated_target_size_convergence_digest=str(payload["migrated_target_size_convergence_digest"]),
            prior_target_production_corpus_digest=(None if payload.get("prior_target_production_corpus_digest") is None else str(payload["prior_target_production_corpus_digest"])),
            status=str(payload.get("status", "activated")),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVMIGRATE1 activation digest mismatch.")
        return result

def build_target_multi_view_migration_plan(
    *,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    size_halve2_plan: Any,
    size_fidelity2_execution_plan: Any,
    learning_control_report: TargetMultiViewLearningControlReport | None = None,
    size_fidelity2_qualification: Any | None = None,
    policy: TargetMultiViewMigrationPolicy | None = None,
) -> TargetMultiViewMigrationPlan:
    """Reduce all MVMIGRATE1 prerequisites into one atomic activation latch."""

    active = policy or TargetMultiViewMigrationPolicy()
    dataset_id = str(legacy_target_data_ladder.dataset_id)
    upstream_dataset_ids = {
        dataset_id,
        str(target_multi_view_repair.dataset_id),
        str(target_multi_view_qualification.dataset_id),
        str(size_halve2_plan.dataset_id),
        str(size_fidelity2_execution_plan.dataset_id),
    }
    if len(upstream_dataset_ids) != 1:
        raise TrainingDataInputError("MVMIGRATE1 upstream dataset identities disagree.")
    if target_multi_view_qualification.legacy_target_data_ladder_digest != legacy_target_data_ladder.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 does not qualify the supplied legacy TARGET-DATA2C v4 ladder.")
    if target_multi_view_qualification.target_multi_view_repair_digest != target_multi_view_repair.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 MVQUAL1 does not qualify the supplied REPAIR1 authority.")
    if size_halve2_plan.target_multi_view_repair_digest != target_multi_view_repair.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 SIZE-HALVE2 references a different REPAIR1 authority.")
    if size_halve2_plan.target_multi_view_qualification_digest != target_multi_view_qualification.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 SIZE-HALVE2 references a different MVQUAL1 authority.")
    if size_fidelity2_execution_plan.size_halve2_digest != size_halve2_plan.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 SIZE-FIDELITY2 references a different SIZE-HALVE2 authority.")

    qualified = tuple(int(v) for v in target_multi_view_qualification.mv_qualified_sizes)
    blockers: list[str] = []
    if not bool(target_multi_view_qualification.same_n_non_regression_passed):
        blockers.append("MVQUAL1 same-N non-regression failed")
    if not bool(target_multi_view_qualification.n95_non_regression_passed):
        blockers.append("MVQUAL1 N95 non-regression failed")
    if len(qualified) < active.minimum_hard_qualifiers:
        blockers.append(f"only {len(qualified)} MV sizes independently hard-qualified")
    if str(size_halve2_plan.outcome) != "ready_for_size_fidelity2":
        blockers.append(f"SIZE-HALVE2 outcome={size_halve2_plan.outcome}")
    if str(size_fidelity2_execution_plan.status) != "ready_for_final_gpu_calibration":
        blockers.append(f"SIZE-FIDELITY2 execution status={size_fidelity2_execution_plan.status}")

    learning_digest = None
    fidelity_digest = None
    if learning_control_report is not None:
        if learning_control_report.dataset_id != dataset_id:
            raise TrainingDataInputError("MVMIGRATE1 learning-control dataset identity changed.")
        if learning_control_report.target_multi_view_qualification_digest != target_multi_view_qualification.content_digest:
            raise TrainingDataInputError("MVMIGRATE1 learning controls reference a different MVQUAL1 authority.")
        if tuple(learning_control_report.control_target_sizes) != tuple(target_multi_view_qualification.learning_control_target_sizes):
            raise TrainingDataInputError("MVMIGRATE1 learning-control sizes differ from the MVQUAL1 frozen controls.")
        learning_digest = learning_control_report.content_digest
        if not learning_control_report.passed:
            blockers.append("FINAL-GPU1 legacy-vs-MV learning controls failed")
    if size_fidelity2_qualification is not None:
        if size_fidelity2_qualification.dataset_id != dataset_id:
            raise TrainingDataInputError("MVMIGRATE1 SIZE-FIDELITY2 qualification dataset identity changed.")
        if size_fidelity2_qualification.execution_plan_digest != size_fidelity2_execution_plan.content_digest:
            raise TrainingDataInputError("MVMIGRATE1 SIZE-FIDELITY2 report references a different execution plan.")
        fidelity_digest = size_fidelity2_qualification.content_digest
        if not bool(size_fidelity2_qualification.passed):
            blockers.append("SIZE-FIDELITY2 survivor/ceiling qualification failed")
        if str(size_fidelity2_qualification.gpu_qualification_status) != _GPU_PASSED:
            blockers.append("SIZE-FIDELITY2 positive GPU qualification is not final")

    if blockers:
        return TargetMultiViewMigrationPlan(
            dataset_id=dataset_id,
            legacy_target_data_ladder_digest=legacy_target_data_ladder.content_digest,
            target_multi_view_repair_digest=target_multi_view_repair.content_digest,
            target_multi_view_qualification_digest=target_multi_view_qualification.content_digest,
            size_halve2_plan_digest=size_halve2_plan.content_digest,
            size_fidelity2_execution_plan_digest=size_fidelity2_execution_plan.content_digest,
            policy=active,
            mv_qualified_sizes=qualified,
            learning_control_report_digest=learning_digest,
            size_fidelity2_qualification_digest=fidelity_digest,
            status=_MIGRATION_BLOCKED,
            decision_reason="; ".join(blockers),
        )

    if learning_control_report is None or size_fidelity2_qualification is None:
        missing = []
        if learning_control_report is None:
            missing.append("MVQUAL1 legacy-vs-MV learning controls")
        if size_fidelity2_qualification is None:
            missing.append("SIZE-FIDELITY2 GPU qualification")
        return TargetMultiViewMigrationPlan(
            dataset_id=dataset_id,
            legacy_target_data_ladder_digest=legacy_target_data_ladder.content_digest,
            target_multi_view_repair_digest=target_multi_view_repair.content_digest,
            target_multi_view_qualification_digest=target_multi_view_qualification.content_digest,
            size_halve2_plan_digest=size_halve2_plan.content_digest,
            size_fidelity2_execution_plan_digest=size_fidelity2_execution_plan.content_digest,
            policy=active,
            mv_qualified_sizes=qualified,
            learning_control_report_digest=learning_digest,
            size_fidelity2_qualification_digest=fidelity_digest,
            status=_MIGRATION_PENDING,
            decision_reason="FINAL-GPU1 evidence pending: " + ", ".join(missing),
        )

    return TargetMultiViewMigrationPlan(
        dataset_id=dataset_id,
        legacy_target_data_ladder_digest=legacy_target_data_ladder.content_digest,
        target_multi_view_repair_digest=target_multi_view_repair.content_digest,
        target_multi_view_qualification_digest=target_multi_view_qualification.content_digest,
        size_halve2_plan_digest=size_halve2_plan.content_digest,
        size_fidelity2_execution_plan_digest=size_fidelity2_execution_plan.content_digest,
        policy=active,
        mv_qualified_sizes=qualified,
        learning_control_report_digest=learning_control_report.content_digest,
        size_fidelity2_qualification_digest=size_fidelity2_qualification.content_digest,
        status=_MIGRATION_AUTHORIZED,
        decision_reason=(
            "MVQUAL1 non-regression and learning controls passed; SIZE-HALVE2 has at least four hard qualifiers; "
            "SIZE-FIDELITY2 passed final GPU survivor/ceiling qualification; fixed-eight v5 activation is authorized"
        ),
    )


def validate_target_multi_view_migration_plan(
    plan: TargetMultiViewMigrationPlan,
    *,
    legacy_target_data_ladder: Any,
    target_multi_view_repair: Any,
    target_multi_view_qualification: Any,
    size_halve2_plan: Any,
    size_fidelity2_execution_plan: Any,
    learning_control_report: TargetMultiViewLearningControlReport | None = None,
    size_fidelity2_qualification: Any | None = None,
) -> None:
    rebuilt = build_target_multi_view_migration_plan(
        legacy_target_data_ladder=legacy_target_data_ladder,
        target_multi_view_repair=target_multi_view_repair,
        target_multi_view_qualification=target_multi_view_qualification,
        size_halve2_plan=size_halve2_plan,
        size_fidelity2_execution_plan=size_fidelity2_execution_plan,
        learning_control_report=learning_control_report,
        size_fidelity2_qualification=size_fidelity2_qualification,
        policy=plan.policy,
    )
    if rebuilt.content_digest != plan.content_digest:
        raise TrainingDataInputError("MVMIGRATE1 persisted plan differs from recomputed upstream authority.")
