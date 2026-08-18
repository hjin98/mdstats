"""Protocol-bound precision profiles and deterministic staged schedule resolution.

PREC1 freezes configuration and identity semantics. PREC2 implements the runtime dtype
transition substrate; production profile activation remains gated by PREC3. Callers must
therefore distinguish an executable transition mechanism from a production-authorized profile.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest

PRECISION_STAGE_SCHEMA = "mdstats.precision-stage.v1"
PRECISION_SCHEDULE_POLICY_SCHEMA = "mdstats.precision-schedule-policy.v1"
RESOLVED_PRECISION_STAGE_SCHEMA = "mdstats.resolved-precision-stage.v1"
RESOLVED_PRECISION_SCHEDULE_SCHEMA = "mdstats.resolved-precision-schedule.v1"

_ALLOWED_DTYPES = {"float32", "float64"}
_FRACTION_TOLERANCE = 1.0e-9


class PrecisionProfile(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    REFINE = "refine"
    CUSTOM = "custom"
    LEGACY_CUSTOM = "legacy_custom"


@dataclass(frozen=True, slots=True)
class PrecisionStage:
    dtype: str
    fraction: float
    learning_rate_scale: float = 1.0

    def __post_init__(self) -> None:
        if self.dtype not in _ALLOWED_DTYPES:
            raise TrainingDataInputError(f"Unsupported precision-stage dtype {self.dtype!r}.")
        if not math.isfinite(self.fraction) or self.fraction <= 0.0:
            raise TrainingDataInputError("Precision-stage fractions must be finite and positive.")
        if not math.isfinite(self.learning_rate_scale) or self.learning_rate_scale <= 0.0:
            raise TrainingDataInputError("Precision-stage learning-rate scales must be finite and positive.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PRECISION_STAGE_SCHEMA,
            "dtype": self.dtype,
            "fraction": self.fraction,
            "learning_rate_scale": self.learning_rate_scale,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrecisionStage":
        if payload.get("schema") not in (None, PRECISION_STAGE_SCHEMA):
            raise TrainingDataSerializationError("Unsupported precision-stage schema.")
        return cls(
            dtype=str(payload["dtype"]),
            fraction=float(payload["fraction"]),
            learning_rate_scale=float(payload.get("learning_rate_scale", 1.0)),
        )


@dataclass(frozen=True, slots=True)
class ResolvedPrecisionStage:
    dtype: str
    source_fraction: float
    learning_rate_scale: float
    start_epoch: int
    stop_epoch: int
    start_update: int | None = None
    stop_update: int | None = None

    def __post_init__(self) -> None:
        if self.dtype not in _ALLOWED_DTYPES:
            raise TrainingDataInputError("Resolved precision stage has unsupported dtype.")
        if self.start_epoch < 0 or self.stop_epoch <= self.start_epoch:
            raise TrainingDataInputError("Resolved precision stage has invalid epoch bounds.")
        if (self.start_update is None) != (self.stop_update is None):
            raise TrainingDataInputError("Resolved precision update bounds must be both present or both absent.")
        if self.start_update is not None and (
            self.start_update < 0 or self.stop_update is None or self.stop_update <= self.start_update
        ):
            raise TrainingDataInputError("Resolved precision stage has invalid update bounds.")

    @property
    def epoch_count(self) -> int:
        return self.stop_epoch - self.start_epoch

    @property
    def update_count(self) -> int | None:
        if self.start_update is None or self.stop_update is None:
            return None
        return self.stop_update - self.start_update

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RESOLVED_PRECISION_STAGE_SCHEMA,
            "dtype": self.dtype,
            "source_fraction": self.source_fraction,
            "learning_rate_scale": self.learning_rate_scale,
            "start_epoch": self.start_epoch,
            "stop_epoch": self.stop_epoch,
            "epoch_count": self.epoch_count,
            "start_update": self.start_update,
            "stop_update": self.stop_update,
            "update_count": self.update_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResolvedPrecisionStage":
        if payload.get("schema") != RESOLVED_PRECISION_STAGE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported resolved precision-stage schema.")
        return cls(
            dtype=str(payload["dtype"]),
            source_fraction=float(payload["source_fraction"]),
            learning_rate_scale=float(payload["learning_rate_scale"]),
            start_epoch=int(payload["start_epoch"]),
            stop_epoch=int(payload["stop_epoch"]),
            start_update=None if payload.get("start_update") is None else int(payload["start_update"]),
            stop_update=None if payload.get("stop_update") is None else int(payload["stop_update"]),
        )


@dataclass(frozen=True, slots=True)
class ResolvedPrecisionSchedule:
    requested_profile: str
    stages: tuple[ResolvedPrecisionStage, ...]
    preserve_optimizer_state: bool
    preserve_scheduler_state: bool
    preserve_ema_state: bool
    model_dtype: str
    critical_operation_dtype: str
    evaluation_dtype: str
    verification_dtype: str
    export_dtype: str
    max_num_epochs: int
    updates_per_epoch: int | None
    minimum_final_stage_epochs: int
    minimum_final_stage_gradient_updates: int

    def __post_init__(self) -> None:
        if not self.stages:
            raise TrainingDataInputError("Resolved precision schedules require at least one stage.")
        if self.max_num_epochs <= 0:
            raise TrainingDataInputError("Resolved precision schedule requires positive max_num_epochs.")
        if self.stages[0].start_epoch != 0 or self.stages[-1].stop_epoch != self.max_num_epochs:
            raise TrainingDataInputError("Resolved precision stages must cover the complete epoch budget.")
        previous = 0
        for stage in self.stages:
            if stage.start_epoch != previous:
                raise TrainingDataInputError("Resolved precision stages must be contiguous.")
            previous = stage.stop_epoch
        for dtype in (
            self.model_dtype, self.critical_operation_dtype, self.evaluation_dtype,
            self.verification_dtype, self.export_dtype,
        ):
            if dtype not in _ALLOWED_DTYPES:
                raise TrainingDataInputError("Resolved pipeline precision contains an unsupported dtype.")
        if self.updates_per_epoch is not None and self.updates_per_epoch <= 0:
            raise TrainingDataInputError("updates_per_epoch must be positive when supplied.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RESOLVED_PRECISION_SCHEDULE_SCHEMA,
            "requested_profile": self.requested_profile,
            "stages": [stage.to_dict() for stage in self.stages],
            "preserve_optimizer_state": self.preserve_optimizer_state,
            "preserve_scheduler_state": self.preserve_scheduler_state,
            "preserve_ema_state": self.preserve_ema_state,
            "model_dtype": self.model_dtype,
            "critical_operation_dtype": self.critical_operation_dtype,
            "evaluation_dtype": self.evaluation_dtype,
            "verification_dtype": self.verification_dtype,
            "export_dtype": self.export_dtype,
            "max_num_epochs": self.max_num_epochs,
            "updates_per_epoch": self.updates_per_epoch,
            "minimum_final_stage_epochs": self.minimum_final_stage_epochs,
            "minimum_final_stage_gradient_updates": self.minimum_final_stage_gradient_updates,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResolvedPrecisionSchedule":
        if payload.get("schema") != RESOLVED_PRECISION_SCHEDULE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported resolved precision-schedule schema.")
        result = cls(
            requested_profile=str(payload["requested_profile"]),
            stages=tuple(ResolvedPrecisionStage.from_dict(item) for item in payload["stages"]),
            preserve_optimizer_state=bool(payload["preserve_optimizer_state"]),
            preserve_scheduler_state=bool(payload["preserve_scheduler_state"]),
            preserve_ema_state=bool(payload["preserve_ema_state"]),
            model_dtype=str(payload["model_dtype"]),
            critical_operation_dtype=str(payload["critical_operation_dtype"]),
            evaluation_dtype=str(payload["evaluation_dtype"]),
            verification_dtype=str(payload["verification_dtype"]),
            export_dtype=str(payload["export_dtype"]),
            max_num_epochs=int(payload["max_num_epochs"]),
            updates_per_epoch=None if payload.get("updates_per_epoch") is None else int(payload["updates_per_epoch"]),
            minimum_final_stage_epochs=int(payload.get("minimum_final_stage_epochs", 0)),
            minimum_final_stage_gradient_updates=int(payload.get("minimum_final_stage_gradient_updates", 0)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Resolved precision-schedule digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PrecisionSchedulePolicy:
    requested_profile: str
    stages: tuple[PrecisionStage, ...]
    minimum_final_stage_epochs: int = 0
    minimum_final_stage_gradient_updates: int = 0
    preserve_optimizer_state: bool = True
    preserve_scheduler_state: bool = True
    preserve_ema_state: bool = True
    model_dtype: str = "float64"
    critical_operation_dtype: str = "float64"
    evaluation_dtype: str = "float64"
    verification_dtype: str = "float64"
    export_dtype: str = "float64"

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        if not stages:
            raise TrainingDataInputError("Precision schedules require at least one stage.")
        object.__setattr__(self, "stages", stages)
        total = sum(stage.fraction for stage in stages)
        if abs(total - 1.0) > _FRACTION_TOLERANCE:
            raise TrainingDataInputError(
                f"Precision-stage fractions must sum to 1.0; got {total:.17g}."
            )
        if self.minimum_final_stage_epochs < 0 or self.minimum_final_stage_gradient_updates < 0:
            raise TrainingDataInputError("Precision refinement floors must be nonnegative.")
        for dtype in (
            self.model_dtype, self.critical_operation_dtype, self.evaluation_dtype,
            self.verification_dtype, self.export_dtype,
        ):
            if dtype not in _ALLOWED_DTYPES:
                raise TrainingDataInputError(f"Unsupported pipeline dtype {dtype!r}.")
        if not str(self.requested_profile).strip():
            raise TrainingDataInputError("Precision profile label must be non-empty.")

    @property
    def mode(self) -> str:
        return "single_stage" if len(self.stages) == 1 else "staged"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRECISION_SCHEDULE_POLICY_SCHEMA,
            "requested_profile": self.requested_profile,
            "mode": self.mode,
            "stages": [stage.to_dict() for stage in self.stages],
            "minimum_final_stage_epochs": self.minimum_final_stage_epochs,
            "minimum_final_stage_gradient_updates": self.minimum_final_stage_gradient_updates,
            "preserve_optimizer_state": self.preserve_optimizer_state,
            "preserve_scheduler_state": self.preserve_scheduler_state,
            "preserve_ema_state": self.preserve_ema_state,
            "model_dtype": self.model_dtype,
            "critical_operation_dtype": self.critical_operation_dtype,
            "evaluation_dtype": self.evaluation_dtype,
            "verification_dtype": self.verification_dtype,
            "export_dtype": self.export_dtype,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrecisionSchedulePolicy":
        if payload.get("schema") != PRECISION_SCHEDULE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported precision-schedule policy schema.")
        result = cls(
            requested_profile=str(payload["requested_profile"]),
            stages=tuple(PrecisionStage.from_dict(item) for item in payload["stages"]),
            minimum_final_stage_epochs=int(payload.get("minimum_final_stage_epochs", 0)),
            minimum_final_stage_gradient_updates=int(payload.get("minimum_final_stage_gradient_updates", 0)),
            preserve_optimizer_state=bool(payload.get("preserve_optimizer_state", True)),
            preserve_scheduler_state=bool(payload.get("preserve_scheduler_state", True)),
            preserve_ema_state=bool(payload.get("preserve_ema_state", True)),
            model_dtype=str(payload["model_dtype"]),
            critical_operation_dtype=str(payload["critical_operation_dtype"]),
            evaluation_dtype=str(payload["evaluation_dtype"]),
            verification_dtype=str(payload["verification_dtype"]),
            export_dtype=str(payload["export_dtype"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Precision-schedule policy digest mismatch.")
        return result

    def resolve(
        self,
        *,
        max_num_epochs: int,
        updates_per_epoch: int | None = None,
        require_update_floor: bool = False,
    ) -> ResolvedPrecisionSchedule:
        if max_num_epochs <= 0:
            raise TrainingDataInputError("Precision schedule requires a positive epoch budget.")
        if updates_per_epoch is not None and updates_per_epoch <= 0:
            raise TrainingDataInputError("updates_per_epoch must be positive when supplied.")
        if require_update_floor and self.minimum_final_stage_gradient_updates > 0 and updates_per_epoch is None:
            raise TrainingDataInputError(
                "The configured precision refinement update floor cannot be resolved without updates_per_epoch."
            )

        counts: list[int] = []
        assigned = 0
        for stage in self.stages[:-1]:
            count = int(math.floor(stage.fraction * max_num_epochs + 1.0e-12))
            counts.append(count)
            assigned += count
        counts.append(max_num_epochs - assigned)
        if any(count <= 0 for count in counts):
            raise TrainingDataInputError(
                "The epoch budget is too small to assign at least one epoch to every precision stage."
            )

        nominal_final_count = counts[-1]

        def _expand_final_stage(required_final: int) -> bool:
            if counts[-1] >= required_final:
                return True
            need = required_final - counts[-1]
            for index in range(len(counts) - 2, -1, -1):
                transferable = max(0, counts[index] - 1)
                moved = min(need, transferable)
                counts[index] -= moved
                counts[-1] += moved
                need -= moved
                if need == 0:
                    return True
            return False

        # The epoch floor is always a hard staged-training contract.  Resolve it
        # independently of the optional update floor so require_update_floor=False
        # really does disable update-count enforcement.
        required_final_epochs = max(1, self.minimum_final_stage_epochs)
        if not _expand_final_stage(required_final_epochs):
            raise TrainingDataInputError(
                "The epoch budget cannot satisfy the precision refinement epoch floor while retaining "
                "at least one epoch in every earlier stage."
            )

        effective_minimum_final_stage_gradient_updates = self.minimum_final_stage_gradient_updates
        if (
            require_update_floor
            and updates_per_epoch is not None
            and self.minimum_final_stage_gradient_updates > 0
        ):
            required_by_updates = int(
                math.ceil(self.minimum_final_stage_gradient_updates / updates_per_epoch)
            )
            if counts[-1] < required_by_updates:
                snapshot = list(counts)
                if not _expand_final_stage(required_by_updates):
                    # The original 15k reference floor was calibrated on replay-sized
                    # exposure.  For the exact canonical 80/20 refine profile, a small
                    # target-only DATA8 job (notably n512 naive fine tuning) can have
                    # fewer than 15k optimizer steps in the entire 30-epoch budget.
                    # Failing here makes the canonical profile unusable for the package's
                    # default selection size.  When the nominal 20% tail already meets
                    # the hard epoch floor, preserve that scientifically explicit split
                    # rather than collapsing almost the whole run into FP64.  Custom
                    # schedules remain strict and fail closed.
                    canonical_reference_refine = (
                        self.requested_profile == PrecisionProfile.REFINE.value
                        and len(self.stages) == 2
                        and self.stages[0].dtype == "float32"
                        and self.stages[1].dtype == "float64"
                        and abs(self.stages[0].fraction - 0.80) <= _FRACTION_TOLERANCE
                        and abs(self.stages[1].fraction - 0.20) <= _FRACTION_TOLERANCE
                        and abs(self.stages[0].learning_rate_scale - 1.0) <= _FRACTION_TOLERANCE
                        and abs(self.stages[1].learning_rate_scale - 0.5) <= _FRACTION_TOLERANCE
                        and self.minimum_final_stage_epochs == 3
                        and self.minimum_final_stage_gradient_updates == 15_000
                    )
                    if canonical_reference_refine and nominal_final_count >= required_final_epochs:
                        counts[:] = snapshot
                        effective_minimum_final_stage_gradient_updates = min(
                            self.minimum_final_stage_gradient_updates,
                            counts[-1] * updates_per_epoch,
                        )
                    else:
                        max_final_epochs = max_num_epochs - (len(counts) - 1)
                        max_final_updates = max_final_epochs * updates_per_epoch
                        raise TrainingDataInputError(
                            "The epoch budget cannot satisfy the precision refinement update floor while "
                            "retaining at least one epoch in every earlier stage: "
                            f"requested={self.minimum_final_stage_gradient_updates} updates, "
                            f"updates_per_epoch={updates_per_epoch}, "
                            f"maximum_feasible_final_stage_updates={max_final_updates}."
                        )

        resolved: list[ResolvedPrecisionStage] = []
        epoch_cursor = 0
        update_cursor = 0
        for source, count in zip(self.stages, counts):
            start_update = None if updates_per_epoch is None else update_cursor
            stop_update = None if updates_per_epoch is None else update_cursor + count * updates_per_epoch
            resolved.append(
                ResolvedPrecisionStage(
                    dtype=source.dtype,
                    source_fraction=source.fraction,
                    learning_rate_scale=source.learning_rate_scale,
                    start_epoch=epoch_cursor,
                    stop_epoch=epoch_cursor + count,
                    start_update=start_update,
                    stop_update=stop_update,
                )
            )
            epoch_cursor += count
            if stop_update is not None:
                update_cursor = stop_update

        return ResolvedPrecisionSchedule(
            requested_profile=self.requested_profile,
            stages=tuple(resolved),
            preserve_optimizer_state=self.preserve_optimizer_state,
            preserve_scheduler_state=self.preserve_scheduler_state,
            preserve_ema_state=self.preserve_ema_state,
            model_dtype=self.model_dtype,
            critical_operation_dtype=self.critical_operation_dtype,
            evaluation_dtype=self.evaluation_dtype,
            verification_dtype=self.verification_dtype,
            export_dtype=self.export_dtype,
            max_num_epochs=max_num_epochs,
            updates_per_epoch=updates_per_epoch,
            minimum_final_stage_epochs=self.minimum_final_stage_epochs,
            minimum_final_stage_gradient_updates=effective_minimum_final_stage_gradient_updates,
        )


def canonical_precision_schedule_policy(profile: PrecisionProfile | str) -> PrecisionSchedulePolicy:
    profile = PrecisionProfile(profile)
    if profile is PrecisionProfile.SINGLE:
        return PrecisionSchedulePolicy(
            requested_profile=profile.value,
            stages=(PrecisionStage("float32", 1.0, 1.0),),
            model_dtype="float32",
            critical_operation_dtype="float64",
            evaluation_dtype="float32",
            verification_dtype="float32",
            export_dtype="float32",
        )
    if profile is PrecisionProfile.DOUBLE:
        return PrecisionSchedulePolicy(
            requested_profile=profile.value,
            stages=(PrecisionStage("float64", 1.0, 1.0),),
            model_dtype="float64",
            critical_operation_dtype="float64",
            evaluation_dtype="float64",
            verification_dtype="float64",
            export_dtype="float64",
        )
    if profile is PrecisionProfile.REFINE:
        # Historical compatibility only. ADAPT-PREC1 removes this profile from
        # generated/production campaign configuration, but existing serialized
        # refine evidence still needs a deterministic constructor for audits and
        # migration tests. Production CLI validation rejects staged schedules.
        return PrecisionSchedulePolicy(
            requested_profile=profile.value,
            stages=(
                PrecisionStage("float32", 0.80, 1.0),
                PrecisionStage("float64", 0.20, 0.5),
            ),
            minimum_final_stage_epochs=3,
            minimum_final_stage_gradient_updates=15_000,
            preserve_optimizer_state=True,
            preserve_scheduler_state=True,
            preserve_ema_state=True,
            model_dtype="float64",
            critical_operation_dtype="float64",
            evaluation_dtype="float64",
            verification_dtype="float64",
            export_dtype="float64",
        )
    raise TrainingDataInputError(f"No canonical generated schedule exists for profile {profile.value!r}.")


def legacy_one_stage_precision_policy(
    *,
    training_dtype: str,
    model_dtype: str | None = None,
    critical_operation_dtype: str = "float64",
    evaluation_dtype: str | None = None,
    verification_dtype: str | None = None,
    export_dtype: str | None = None,
) -> PrecisionSchedulePolicy:
    """Losslessly describe a historical one-stage campaign as a generalized policy."""
    if training_dtype not in _ALLOWED_DTYPES:
        raise TrainingDataInputError("Unsupported legacy training dtype.")
    return PrecisionSchedulePolicy(
        requested_profile=PrecisionProfile.LEGACY_CUSTOM.value,
        stages=(PrecisionStage(training_dtype, 1.0, 1.0),),
        model_dtype=training_dtype if model_dtype is None else model_dtype,
        critical_operation_dtype=critical_operation_dtype,
        evaluation_dtype=training_dtype if evaluation_dtype is None else evaluation_dtype,
        verification_dtype=training_dtype if verification_dtype is None else verification_dtype,
        export_dtype=training_dtype if export_dtype is None else export_dtype,
    )
