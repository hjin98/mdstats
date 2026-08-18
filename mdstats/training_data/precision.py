"""Precision inspection and transition evidence for MACE fine-tuning artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .protocol import FoundationCheckpointIdentity, MaceJobArtifact
from .mace_compatibility import mace_runtime_warning_handled

MACE_MODEL_PRECISION_RECORD_SCHEMA = "mdstats.mace-model-precision-record.v1"
MACE_PRECISION_TRANSITION_RECORD_SCHEMA = "mdstats.mace-precision-transition-record.v2"
MACE_PRECISION_TRANSITION_RECORD_V1_SCHEMA = "mdstats.mace-precision-transition-record.v1"
SUPPORTED_MACE_FLOAT_DTYPES = ("float32", "float64")


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _dtype_name(dtype: Any) -> str:
    text = str(dtype)
    return text.removeprefix("torch.")


def _count_dtypes(named_tensors: Any) -> tuple[tuple[tuple[str, int], ...], int]:
    counts: dict[str, int] = {}
    non_floating = 0
    for _, tensor in named_tensors:
        if bool(getattr(tensor, "is_floating_point", lambda: False)()):
            name = _dtype_name(tensor.dtype)
            counts[name] = counts.get(name, 0) + int(tensor.numel())
        else:
            non_floating += int(tensor.numel())
    return tuple(sorted(counts.items())), non_floating


@dataclass(frozen=True, slots=True)
class MaceModelPrecisionRecord:
    artifact_path: str
    artifact_sha256: str
    model_class: str | None
    floating_parameter_dtypes: tuple[tuple[str, int], ...]
    floating_buffer_dtypes: tuple[tuple[str, int], ...]
    non_floating_parameter_count: int
    non_floating_buffer_count: int
    expected_dtype: str | None = None
    load_error: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_sha256", validate_digest(self.artifact_sha256, name="artifact_sha256"))
        for field_name in ("floating_parameter_dtypes", "floating_buffer_dtypes"):
            values = tuple((str(name), int(count)) for name, count in getattr(self, field_name))
            if values != tuple(sorted(values)) or any(count <= 0 for _, count in values):
                raise TrainingDataInputError(f"{field_name} must be sorted positive dtype counts.")
            object.__setattr__(self, field_name, values)
        if self.non_floating_parameter_count < 0 or self.non_floating_buffer_count < 0:
            raise TrainingDataInputError("Non-floating tensor counts cannot be negative.")
        if self.expected_dtype is not None and self.expected_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
            raise TrainingDataInputError("Expected MACE dtype must be float32 or float64.")

    @property
    def observed_floating_dtypes(self) -> tuple[str, ...]:
        return tuple(sorted({name for name, _ in self.floating_parameter_dtypes + self.floating_buffer_dtypes}))

    @property
    def uniform_floating_dtype(self) -> str | None:
        values = self.observed_floating_dtypes
        return values[0] if len(values) == 1 else None

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.load_error is not None:
            reasons.append("model_load_failed")
        if not self.observed_floating_dtypes:
            reasons.append("no_floating_state")
        elif self.uniform_floating_dtype is None:
            reasons.append("mixed_floating_dtypes")
        if (
            self.expected_dtype is not None
            and self.uniform_floating_dtype is not None
            and self.uniform_floating_dtype != self.expected_dtype
        ):
            reasons.append("unexpected_floating_dtype")
        return tuple(reasons)

    @property
    def passed(self) -> bool:
        return not self.failure_reasons

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_MODEL_PRECISION_RECORD_SCHEMA,
            "artifact_path": self.artifact_path,
            "artifact_sha256": self.artifact_sha256,
            "model_class": self.model_class,
            "floating_parameter_dtypes": [list(v) for v in self.floating_parameter_dtypes],
            "floating_buffer_dtypes": [list(v) for v in self.floating_buffer_dtypes],
            "non_floating_parameter_count": self.non_floating_parameter_count,
            "non_floating_buffer_count": self.non_floating_buffer_count,
            "expected_dtype": self.expected_dtype,
            "load_error": self.load_error,
            "observed_floating_dtypes": list(self.observed_floating_dtypes),
            "uniform_floating_dtype": self.uniform_floating_dtype,
            "failure_reasons": list(self.failure_reasons),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceModelPrecisionRecord":
        if payload.get("schema") != MACE_MODEL_PRECISION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE model-precision schema.")
        result = cls(
            artifact_path=str(payload["artifact_path"]),
            artifact_sha256=str(payload["artifact_sha256"]),
            model_class=None if payload.get("model_class") is None else str(payload["model_class"]),
            floating_parameter_dtypes=tuple((str(v[0]), int(v[1])) for v in payload.get("floating_parameter_dtypes", ())),
            floating_buffer_dtypes=tuple((str(v[0]), int(v[1])) for v in payload.get("floating_buffer_dtypes", ())),
            non_floating_parameter_count=int(payload.get("non_floating_parameter_count", 0)),
            non_floating_buffer_count=int(payload.get("non_floating_buffer_count", 0)),
            expected_dtype=None if payload.get("expected_dtype") is None else str(payload["expected_dtype"]),
            load_error=None if payload.get("load_error") is None else str(payload["load_error"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE model-precision digest mismatch.")
        return result


@mace_runtime_warning_handled("MACE checkpoint precision inspection")
def inspect_mace_model_precision(
    path: str | Path,
    *,
    expected_dtype: str | None = None,
) -> MaceModelPrecisionRecord:
    source = Path(path).resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"MACE model artifact does not exist: {source!s}.")
    if expected_dtype is not None and expected_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
        raise TrainingDataInputError("Expected MACE dtype must be float32 or float64.")
    before = _sha256_file(source)
    model = None
    load_error = None
    try:
        import torch

        model = torch.load(source, map_location="cpu", weights_only=False)
        parameter_dtypes, non_float_parameters = _count_dtypes(model.named_parameters())
        buffer_dtypes, non_float_buffers = _count_dtypes(model.named_buffers())
        model_class = model.__class__.__name__
    except Exception as exc:  # fail-closed evidence rather than an opaque crash
        parameter_dtypes = ()
        buffer_dtypes = ()
        non_float_parameters = 0
        non_float_buffers = 0
        model_class = None
        load_error = f"{exc.__class__.__name__}: {exc}"
    finally:
        del model
    after = _sha256_file(source)
    if before != after:
        raise TrainingDataInputError("MACE model artifact changed during precision inspection.")
    return MaceModelPrecisionRecord(
        artifact_path=str(source),
        artifact_sha256=before,
        model_class=model_class,
        floating_parameter_dtypes=parameter_dtypes,
        floating_buffer_dtypes=buffer_dtypes,
        non_floating_parameter_count=non_float_parameters,
        non_floating_buffer_count=non_float_buffers,
        expected_dtype=expected_dtype,
        load_error=load_error,
    )


@dataclass(frozen=True, slots=True)
class MacePrecisionTransitionRecord:
    foundation_checkpoint: FoundationCheckpointIdentity
    job_digest: str
    optimizer_policy_digest: str
    requested_dtype: str
    foundation_precision: MaceModelPrecisionRecord
    trained_model_precision: MaceModelPrecisionRecord
    extracted_model_precision: MaceModelPrecisionRecord | None
    training_foundation_checkpoint_sha256: str | None = None
    selected_head_qualification_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_digest", validate_digest(self.job_digest, name="job_digest"))
        object.__setattr__(self, "optimizer_policy_digest", validate_digest(self.optimizer_policy_digest, name="optimizer_policy_digest"))
        if self.requested_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
            raise TrainingDataInputError("Requested MACE dtype must be float32 or float64.")
        if self.training_foundation_checkpoint_sha256 is not None:
            object.__setattr__(
                self,
                "training_foundation_checkpoint_sha256",
                validate_digest(self.training_foundation_checkpoint_sha256, name="training_foundation_checkpoint_sha256"),
            )
            if self.selected_head_qualification_digest is None:
                raise TrainingDataInputError(
                    "Derived training-foundation precision evidence requires selected-head qualification lineage."
                )
            object.__setattr__(
                self,
                "selected_head_qualification_digest",
                validate_digest(self.selected_head_qualification_digest, name="selected_head_qualification_digest"),
            )
        elif self.selected_head_qualification_digest is not None:
            raise TrainingDataInputError(
                "Selected-head qualification lineage cannot be supplied without a derived training foundation."
            )
        expected_foundation_sha = self.training_foundation_checkpoint_sha256 or self.foundation_checkpoint.sha256
        if self.foundation_precision.artifact_sha256 != expected_foundation_sha:
            raise TrainingDataInputError("Foundation precision record does not match the executable training checkpoint identity.")

    @property
    def conversion_performed(self) -> bool:
        source = self.foundation_precision.uniform_floating_dtype
        target = self.trained_model_precision.uniform_floating_dtype
        return source is not None and target is not None and source != target

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.foundation_precision.passed:
            reasons.append("foundation_precision_failed")
        if not self.trained_model_precision.passed:
            reasons.append("trained_model_precision_failed")
        if self.trained_model_precision.uniform_floating_dtype != self.requested_dtype:
            reasons.append("trained_model_dtype_mismatch")
        if self.extracted_model_precision is not None:
            if not self.extracted_model_precision.passed:
                reasons.append("extracted_model_precision_failed")
            if self.extracted_model_precision.uniform_floating_dtype != self.requested_dtype:
                reasons.append("extracted_model_dtype_mismatch")
        return tuple(reasons)

    @property
    def passed(self) -> bool:
        return not self.failure_reasons

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                MACE_PRECISION_TRANSITION_RECORD_SCHEMA
                if self.training_foundation_checkpoint_sha256 is not None
                else MACE_PRECISION_TRANSITION_RECORD_V1_SCHEMA
            ),
            "foundation_checkpoint": self.foundation_checkpoint.to_dict(),
            "job_digest": self.job_digest,
            "optimizer_policy_digest": self.optimizer_policy_digest,
            "requested_dtype": self.requested_dtype,
            "foundation_precision": self.foundation_precision.to_dict(),
            "trained_model_precision": self.trained_model_precision.to_dict(),
            "extracted_model_precision": None if self.extracted_model_precision is None else self.extracted_model_precision.to_dict(),
            "conversion_performed": self.conversion_performed,
            "failure_reasons": list(self.failure_reasons),
            "passed": self.passed,
        }
        if self.training_foundation_checkpoint_sha256 is not None:
            payload.update({
                "training_foundation_checkpoint_sha256": self.training_foundation_checkpoint_sha256,
                "selected_head_qualification_digest": self.selected_head_qualification_digest,
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MacePrecisionTransitionRecord":
        if payload.get("schema") not in {
            MACE_PRECISION_TRANSITION_RECORD_SCHEMA,
            MACE_PRECISION_TRANSITION_RECORD_V1_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported MACE precision-transition schema.")
        result = cls(
            foundation_checkpoint=FoundationCheckpointIdentity.from_dict(payload["foundation_checkpoint"]),
            job_digest=str(payload["job_digest"]),
            optimizer_policy_digest=str(payload["optimizer_policy_digest"]),
            requested_dtype=str(payload["requested_dtype"]),
            foundation_precision=MaceModelPrecisionRecord.from_dict(payload["foundation_precision"]),
            trained_model_precision=MaceModelPrecisionRecord.from_dict(payload["trained_model_precision"]),
            extracted_model_precision=None if payload.get("extracted_model_precision") is None else MaceModelPrecisionRecord.from_dict(payload["extracted_model_precision"]),
            training_foundation_checkpoint_sha256=(
                None if payload.get("training_foundation_checkpoint_sha256") is None
                else str(payload["training_foundation_checkpoint_sha256"])
            ),
            selected_head_qualification_digest=(
                None if payload.get("selected_head_qualification_digest") is None
                else str(payload["selected_head_qualification_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE precision-transition digest mismatch.")
        return result


def build_mace_precision_transition_record(
    job: MaceJobArtifact,
    foundation_path: str | Path,
    trained_model_path: str | Path,
    extracted_model_path: str | Path | None = None,
) -> MacePrecisionTransitionRecord:
    requested = job.protocol.optimizer_policy.default_dtype
    foundation = inspect_mace_model_precision(foundation_path)
    trained = inspect_mace_model_precision(trained_model_path, expected_dtype=requested)
    extracted = None if extracted_model_path is None else inspect_mace_model_precision(
        extracted_model_path, expected_dtype=requested
    )
    return MacePrecisionTransitionRecord(
        foundation_checkpoint=job.protocol.foundation_checkpoint,
        job_digest=job.content_digest,
        optimizer_policy_digest=job.protocol.optimizer_policy.policy_digest,
        requested_dtype=requested,
        foundation_precision=foundation,
        trained_model_precision=trained,
        extracted_model_precision=extracted,
        training_foundation_checkpoint_sha256=job.protocol.training_foundation_checkpoint_sha256,
        selected_head_qualification_digest=job.protocol.selected_head_qualification_digest,
    )
