"""Immutable FP32/FP64 deployment artifacts for fine-tuned MACE models.

This module owns only serialized model precision and provenance.  It does not
claim or inspect the execution precision of downstream consumers such as
LAMMPS, ML-IAP, Kokkos, LibTorch, or a particular accelerator backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib
import json
import os
import tempfile

import numpy as np

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    canonical_json,
    digest,
    validate_digest,
)
from .mace_compatibility import mace_runtime_warning_handled
from .precision import (
    SUPPORTED_MACE_FLOAT_DTYPES,
    MaceModelPrecisionRecord,
    inspect_mace_model_precision,
)

MACE_DEPLOYMENT_EXPORT_POLICY_SCHEMA = "mdstats.mace-deployment-export-policy.v1"
MACE_INFERENCE_COMPARISON_SCHEMA = "mdstats.mace-inference-comparison.v1"
MACE_DEPLOYMENT_ARTIFACT_SCHEMA = "mdstats.mace-deployment-artifact.v1"
MACE_DEPLOYMENT_EXPORTER_VERSION = "mdstats.mlff-data9a5.deployment.2026-07.v1"

InferenceProbe = Callable[[Any], Any]


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _torch_dtype(name: str, torch: Any) -> Any:
    if name == "float32":
        return torch.float32
    if name == "float64":
        return torch.float64
    raise TrainingDataInputError("MACE deployment dtype must be float32 or float64.")


def _conversion_kind(source_dtype: str, deployment_dtype: str) -> str:
    if source_dtype == deployment_dtype:
        return "identity"
    if source_dtype == "float64" and deployment_dtype == "float32":
        return "demotion_float64_to_float32"
    if source_dtype == "float32" and deployment_dtype == "float64":
        return "promotion_float32_to_float64"
    raise TrainingDataInputError("Unsupported MACE precision conversion.")


def _state_dict_digest(state: Mapping[str, Any]) -> str:
    """Hash tensor names, dtypes, shapes, and exact CPU bytes deterministically."""

    hasher = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name]
        if not hasattr(tensor, "detach"):
            raise TrainingDataInputError(f"State entry {name!r} is not a tensor.")
        array = tensor.detach().cpu().contiguous().numpy()
        metadata = json.dumps(
            {
                "name": str(name),
                "dtype": str(array.dtype),
                "shape": list(array.shape),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        hasher.update(len(metadata).to_bytes(8, "big"))
        hasher.update(metadata)
        payload = array.tobytes(order="C")
        hasher.update(len(payload).to_bytes(8, "big"))
        hasher.update(payload)
    return hasher.hexdigest()


def _clone_state_dict(model: Any) -> dict[str, Any]:
    return {
        str(name): tensor.detach().cpu().clone()
        for name, tensor in model.state_dict().items()
    }


def _state_conversion_is_exact(
    source_state: Mapping[str, Any],
    deployed_state: Mapping[str, Any],
    *,
    deployment_dtype: str,
    torch: Any,
) -> bool:
    if tuple(sorted(source_state)) != tuple(sorted(deployed_state)):
        return False
    target_dtype = _torch_dtype(deployment_dtype, torch)
    for name in sorted(source_state):
        source = source_state[name].detach().cpu()
        observed = deployed_state[name].detach().cpu()
        expected = source.to(dtype=target_dtype) if torch.is_floating_point(source) else source
        if expected.dtype != observed.dtype or expected.shape != observed.shape:
            return False
        if not torch.equal(expected, observed):
            return False
    return True


def _flatten_probe_output(value: Any, *, prefix: str = "output") -> dict[str, np.ndarray]:
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - package contract
        raise TrainingDataInputError("PyTorch is required for MACE deployment export.") from exc

    if torch.is_tensor(value):
        return {prefix: np.asarray(value.detach().cpu(), dtype=np.float64)}
    if isinstance(value, np.ndarray):
        return {prefix: np.asarray(value, dtype=np.float64)}
    if isinstance(value, (float, int, np.floating, np.integer)):
        return {prefix: np.asarray(value, dtype=np.float64)}
    if isinstance(value, Mapping):
        result: dict[str, np.ndarray] = {}
        for key in sorted(value, key=str):
            result.update(_flatten_probe_output(value[key], prefix=f"{prefix}.{key}"))
        return result
    if isinstance(value, (tuple, list)):
        result = {}
        for index, item in enumerate(value):
            result.update(_flatten_probe_output(item, prefix=f"{prefix}[{index}]"))
        return result
    raise TrainingDataInputError(
        f"Inference probe returned unsupported value {type(value).__name__}."
    )


def _run_probe(model: Any, probe: InferenceProbe) -> dict[str, np.ndarray]:
    import torch

    model.eval()
    # MACE force, virial, and stress probes require autograd during inference.
    with torch.enable_grad():
        outputs = _flatten_probe_output(probe(model))
    if not outputs:
        raise TrainingDataInputError("Inference probe returned no numeric outputs.")
    for name, value in outputs.items():
        if value.size == 0:
            raise TrainingDataInputError(f"Inference probe output {name!r} is empty.")
        if not np.all(np.isfinite(value)):
            raise TrainingDataInputError(f"Inference probe output {name!r} is non-finite.")
    return outputs


@dataclass(frozen=True, slots=True)
class MaceDeploymentExportPolicy:
    deployment_dtype: str
    require_inference_probe: bool = True
    float32_rtol: float = 1.0e-5
    float32_atol: float = 1.0e-6
    float64_rtol: float = 1.0e-10
    float64_atol: float = 1.0e-10
    serialization_format: str = "torch_save_full_model"
    exporter_version: str = MACE_DEPLOYMENT_EXPORTER_VERSION

    def __post_init__(self) -> None:
        if self.deployment_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
            raise TrainingDataInputError("MACE deployment dtype must be float32 or float64.")
        for name in ("float32_rtol", "float32_atol", "float64_rtol", "float64_atol"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and non-negative.")
        if self.serialization_format != "torch_save_full_model":
            raise TrainingDataInputError("Unsupported MACE serialization format.")
        if not self.exporter_version.strip():
            raise TrainingDataInputError("MACE deployment exporter version must be non-empty.")

    def comparison_tolerances(self, source_dtype: str) -> tuple[str, float, float]:
        comparison_dtype = (
            "float32"
            if "float32" in {source_dtype, self.deployment_dtype}
            else "float64"
        )
        if comparison_dtype == "float32":
            return comparison_dtype, self.float32_rtol, self.float32_atol
        return comparison_dtype, self.float64_rtol, self.float64_atol

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DEPLOYMENT_EXPORT_POLICY_SCHEMA,
            "deployment_dtype": self.deployment_dtype,
            "require_inference_probe": self.require_inference_probe,
            "float32_rtol": self.float32_rtol,
            "float32_atol": self.float32_atol,
            "float64_rtol": self.float64_rtol,
            "float64_atol": self.float64_atol,
            "serialization_format": self.serialization_format,
            "exporter_version": self.exporter_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDeploymentExportPolicy":
        if payload.get("schema") != MACE_DEPLOYMENT_EXPORT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE deployment-export policy schema.")
        result = cls(
            deployment_dtype=str(payload["deployment_dtype"]),
            require_inference_probe=bool(payload["require_inference_probe"]),
            float32_rtol=float(payload["float32_rtol"]),
            float32_atol=float(payload["float32_atol"]),
            float64_rtol=float(payload["float64_rtol"]),
            float64_atol=float(payload["float64_atol"]),
            serialization_format=str(payload["serialization_format"]),
            exporter_version=str(payload["exporter_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE deployment-export policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceInferenceComparisonRecord:
    comparison_dtype: str
    rtol: float
    atol: float
    output_metrics: tuple[tuple[str, float, float, float, bool], ...]

    def __post_init__(self) -> None:
        if self.comparison_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
            raise TrainingDataInputError("Inference comparison dtype must be float32 or float64.")
        if not np.all(np.isfinite([self.rtol, self.atol])) or self.rtol < 0.0 or self.atol < 0.0:
            raise TrainingDataInputError("Inference comparison tolerances must be finite and non-negative.")
        normalized = tuple(
            sorted(
                (
                    str(name),
                    float(max_abs),
                    float(rmse),
                    float(reference_max_abs),
                    bool(passed),
                )
                for name, max_abs, rmse, reference_max_abs, passed in self.output_metrics
            )
        )
        if not normalized:
            raise TrainingDataInputError("Inference comparison requires at least one output.")
        for name, max_abs, rmse, reference_max_abs, _ in normalized:
            if not name or not np.all(np.isfinite([max_abs, rmse, reference_max_abs])):
                raise TrainingDataInputError("Inference comparison metrics must be named and finite.")
            if min(max_abs, rmse, reference_max_abs) < 0.0:
                raise TrainingDataInputError("Inference comparison metrics cannot be negative.")
        object.__setattr__(self, "output_metrics", normalized)

    @property
    def passed(self) -> bool:
        return all(metric[4] for metric in self.output_metrics)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_INFERENCE_COMPARISON_SCHEMA,
            "comparison_dtype": self.comparison_dtype,
            "rtol": self.rtol,
            "atol": self.atol,
            "output_metrics": [list(metric) for metric in self.output_metrics],
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceInferenceComparisonRecord":
        if payload.get("schema") != MACE_INFERENCE_COMPARISON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE inference-comparison schema.")
        result = cls(
            comparison_dtype=str(payload["comparison_dtype"]),
            rtol=float(payload["rtol"]),
            atol=float(payload["atol"]),
            output_metrics=tuple(
                (str(v[0]), float(v[1]), float(v[2]), float(v[3]), bool(v[4]))
                for v in payload["output_metrics"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE inference-comparison digest mismatch.")
        return result


def _compare_probe_outputs(
    reference: Mapping[str, np.ndarray],
    observed: Mapping[str, np.ndarray],
    *,
    comparison_dtype: str,
    rtol: float,
    atol: float,
) -> MaceInferenceComparisonRecord:
    if tuple(sorted(reference)) != tuple(sorted(observed)):
        raise TrainingDataInputError("Reloaded inference outputs do not match the reference output structure.")
    metrics = []
    for name in sorted(reference):
        expected = np.asarray(reference[name], dtype=np.float64)
        actual = np.asarray(observed[name], dtype=np.float64)
        if expected.shape != actual.shape:
            raise TrainingDataInputError(f"Reloaded inference output {name!r} changed shape.")
        difference = actual - expected
        metrics.append(
            (
                name,
                float(np.max(np.abs(difference))),
                float(np.sqrt(np.mean(np.square(difference)))),
                float(np.max(np.abs(expected))),
                bool(np.allclose(actual, expected, rtol=rtol, atol=atol)),
            )
        )
    return MaceInferenceComparisonRecord(
        comparison_dtype=comparison_dtype,
        rtol=rtol,
        atol=atol,
        output_metrics=tuple(metrics),
    )


@dataclass(frozen=True, slots=True)
class MaceDeploymentArtifact:
    policy: MaceDeploymentExportPolicy
    source_artifact_path: str
    source_artifact_sha256: str
    source_training_dtype: str
    source_precision: MaceModelPrecisionRecord
    source_state_sha256: str
    precision_transition_digest: str | None
    target_head: str | None
    deployment_relative_path: str
    deployment_artifact_sha256: str
    deployment_precision: MaceModelPrecisionRecord
    deployment_state_sha256: str
    manifest_relative_path: str
    conversion_kind: str
    state_conversion_exact: bool
    inference_comparison: MaceInferenceComparisonRecord | None
    torch_version: str
    downstream_runtime_precision_claimed: bool = False
    byte_determinism_claimed: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_artifact_sha256",
            "source_state_sha256",
            "deployment_artifact_sha256",
            "deployment_state_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.precision_transition_digest is not None:
            object.__setattr__(
                self,
                "precision_transition_digest",
                validate_digest(self.precision_transition_digest, name="precision_transition_digest"),
            )
        if self.source_training_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
            raise TrainingDataInputError("Source training dtype must be float32 or float64.")
        for field_name in (
            "source_artifact_path",
            "deployment_relative_path",
            "manifest_relative_path",
            "torch_version",
        ):
            if not str(getattr(self, field_name)).strip():
                raise TrainingDataInputError(f"{field_name} must be non-empty.")
        if self.target_head is not None and not self.target_head.strip():
            raise TrainingDataInputError("Target head must be non-empty when supplied.")
        if self.source_precision.artifact_sha256 != self.source_artifact_sha256:
            raise TrainingDataInputError("Source precision evidence does not match source artifact bytes.")
        if self.deployment_precision.artifact_sha256 != self.deployment_artifact_sha256:
            raise TrainingDataInputError("Deployment precision evidence does not match deployment artifact bytes.")
        source_dtype = self.source_precision.uniform_floating_dtype
        if source_dtype is None:
            raise TrainingDataInputError("Deployment source model must have one uniform floating dtype.")
        expected_kind = _conversion_kind(source_dtype, self.policy.deployment_dtype)
        if self.conversion_kind != expected_kind:
            raise TrainingDataInputError("Deployment conversion kind is inconsistent with model dtypes.")
        if self.downstream_runtime_precision_claimed:
            raise TrainingDataInputError(
                "mdstats deployment artifacts cannot claim downstream runtime precision semantics."
            )
        if self.byte_determinism_claimed:
            raise TrainingDataInputError(
                "Full PyTorch model pickle bytes are not claimed deterministic across reloads."
            )
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    @property
    def deployment_dtype(self) -> str:
        return self.policy.deployment_dtype

    @property
    def precision_recovery_claimed(self) -> bool:
        return False

    @property
    def inference_qualified(self) -> bool:
        return self.inference_comparison is not None and self.inference_comparison.passed

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.source_precision.passed:
            reasons.append("source_precision_failed")
        if not self.deployment_precision.passed:
            reasons.append("deployment_precision_failed")
        if self.deployment_precision.uniform_floating_dtype != self.deployment_dtype:
            reasons.append("deployment_dtype_mismatch")
        if not self.state_conversion_exact:
            reasons.append("state_conversion_mismatch")
        if self.policy.require_inference_probe and self.inference_comparison is None:
            reasons.append("inference_probe_missing")
        if self.inference_comparison is not None and not self.inference_comparison.passed:
            reasons.append("inference_probe_failed")
        if self.downstream_runtime_precision_claimed:
            reasons.append("downstream_runtime_precision_overclaim")
        if self.byte_determinism_claimed:
            reasons.append("model_pickle_byte_determinism_overclaim")
        return tuple(reasons)

    @property
    def passed(self) -> bool:
        return not self.failure_reasons

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DEPLOYMENT_ARTIFACT_SCHEMA,
            "policy": self.policy.to_dict(),
            "source_artifact_path": self.source_artifact_path,
            "source_artifact_sha256": self.source_artifact_sha256,
            "source_training_dtype": self.source_training_dtype,
            "source_precision": self.source_precision.to_dict(),
            "source_state_sha256": self.source_state_sha256,
            "precision_transition_digest": self.precision_transition_digest,
            "target_head": self.target_head,
            "deployment_relative_path": self.deployment_relative_path,
            "deployment_artifact_sha256": self.deployment_artifact_sha256,
            "deployment_precision": self.deployment_precision.to_dict(),
            "deployment_state_sha256": self.deployment_state_sha256,
            "manifest_relative_path": self.manifest_relative_path,
            "conversion_kind": self.conversion_kind,
            "state_conversion_exact": self.state_conversion_exact,
            "inference_comparison": None if self.inference_comparison is None else self.inference_comparison.to_dict(),
            "torch_version": self.torch_version,
            "downstream_runtime_precision_claimed": self.downstream_runtime_precision_claimed,
            "byte_determinism_claimed": self.byte_determinism_claimed,
            "precision_recovery_claimed": self.precision_recovery_claimed,
            "inference_qualified": self.inference_qualified,
            "failure_reasons": list(self.failure_reasons),
            "passed": self.passed,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDeploymentArtifact":
        if payload.get("schema") != MACE_DEPLOYMENT_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE deployment-artifact schema.")
        result = cls(
            policy=MaceDeploymentExportPolicy.from_dict(payload["policy"]),
            source_artifact_path=str(payload["source_artifact_path"]),
            source_artifact_sha256=str(payload["source_artifact_sha256"]),
            source_training_dtype=str(payload["source_training_dtype"]),
            source_precision=MaceModelPrecisionRecord.from_dict(payload["source_precision"]),
            source_state_sha256=str(payload["source_state_sha256"]),
            precision_transition_digest=None if payload.get("precision_transition_digest") is None else str(payload["precision_transition_digest"]),
            target_head=None if payload.get("target_head") is None else str(payload["target_head"]),
            deployment_relative_path=str(payload["deployment_relative_path"]),
            deployment_artifact_sha256=str(payload["deployment_artifact_sha256"]),
            deployment_precision=MaceModelPrecisionRecord.from_dict(payload["deployment_precision"]),
            deployment_state_sha256=str(payload["deployment_state_sha256"]),
            manifest_relative_path=str(payload["manifest_relative_path"]),
            conversion_kind=str(payload["conversion_kind"]),
            state_conversion_exact=bool(payload["state_conversion_exact"]),
            inference_comparison=None if payload.get("inference_comparison") is None else MaceInferenceComparisonRecord.from_dict(payload["inference_comparison"]),
            torch_version=str(payload["torch_version"]),
            downstream_runtime_precision_claimed=bool(payload.get("downstream_runtime_precision_claimed", False)),
            byte_determinism_claimed=bool(payload.get("byte_determinism_claimed", False)),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE deployment-artifact digest mismatch.")
        return result


@mace_runtime_warning_handled("MACE deployment export")
def export_mace_deployment_artifact(
    source_model_path: str | Path,
    output_directory: str | Path,
    *,
    deployment_dtype: str,
    training_dtype: str | None = None,
    filename: str | None = None,
    target_head: str | None = None,
    precision_transition_digest: str | None = None,
    inference_probe: InferenceProbe | None = None,
    policy: MaceDeploymentExportPolicy | None = None,
    overwrite: bool = False,
) -> MaceDeploymentArtifact:
    """Convert, reload, verify, and manifest one MACE deployment model.

    The serialized model is suitable for downstream consumption according to
    the consumer's own interface contract.  This function makes no claim about
    downstream reduction, integration, accelerator, or mixed-precision behavior.
    """

    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - package contract
        raise TrainingDataInputError("PyTorch is required for MACE deployment export.") from exc

    active = MaceDeploymentExportPolicy(deployment_dtype=deployment_dtype) if policy is None else policy
    if active.deployment_dtype != deployment_dtype:
        raise TrainingDataInputError("Deployment dtype and export policy disagree.")
    if active.require_inference_probe and inference_probe is None:
        raise TrainingDataInputError("A deployment inference probe is required by policy.")

    source = Path(source_model_path).resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"MACE source model does not exist: {source!s}.")
    source_sha256 = _sha256_file(source)
    source_precision = inspect_mace_model_precision(source)
    if not source_precision.passed or source_precision.uniform_floating_dtype is None:
        raise TrainingDataInputError(
            f"MACE source precision is not deployable: {source_precision.failure_reasons!r}."
        )
    source_dtype = source_precision.uniform_floating_dtype
    resolved_training_dtype = source_dtype if training_dtype is None else str(training_dtype)
    if resolved_training_dtype not in SUPPORTED_MACE_FLOAT_DTYPES:
        raise TrainingDataInputError("Training dtype must be float32 or float64.")
    if precision_transition_digest is not None:
        validate_digest(precision_transition_digest, name="precision_transition_digest")
    if target_head is not None and not str(target_head).strip():
        raise TrainingDataInputError("Target head must be non-empty when supplied.")

    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    output_name = filename or f"deployment_{deployment_dtype}.model"
    if Path(output_name).name != output_name or not output_name.strip():
        raise TrainingDataInputError("Deployment filename must be one non-empty basename.")
    target = root / output_name
    manifest = root / f"{output_name}.manifest.json"
    if target.resolve() == source:
        raise TrainingDataInputError("Deployment output cannot overwrite the source model.")
    if not overwrite and (target.exists() or manifest.exists()):
        raise TrainingDataInputError("Deployment output already exists; pass overwrite=True explicitly.")

    reference_model = None
    conversion_model = None
    reloaded_model = None
    temporary_model: Path | None = None
    temporary_manifest: Path | None = None
    try:
        reference_model = torch.load(source, map_location="cpu", weights_only=False)
        conversion_model = torch.load(source, map_location="cpu", weights_only=False)
        source_state = _clone_state_dict(reference_model)
        source_state_sha256 = _state_dict_digest(source_state)
        reference_outputs = None if inference_probe is None else _run_probe(reference_model, inference_probe)

        conversion_model.to(dtype=_torch_dtype(deployment_dtype, torch))
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_name}.", suffix=".tmp", dir=root, delete=False
        ) as handle:
            temporary_model = Path(handle.name)
        torch.save(conversion_model, temporary_model)
        with temporary_model.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary_model, target)
        temporary_model = None

        deployment_precision = inspect_mace_model_precision(
            target, expected_dtype=deployment_dtype
        )
        if not deployment_precision.passed:
            raise TrainingDataInputError(
                f"Exported MACE precision failed: {deployment_precision.failure_reasons!r}."
            )
        reloaded_model = torch.load(target, map_location="cpu", weights_only=False)
        deployment_state = _clone_state_dict(reloaded_model)
        state_exact = _state_conversion_is_exact(
            source_state,
            deployment_state,
            deployment_dtype=deployment_dtype,
            torch=torch,
        )
        if not state_exact:
            raise TrainingDataInputError("Reloaded MACE state does not equal the requested exact dtype conversion.")
        deployment_state_sha256 = _state_dict_digest(deployment_state)

        comparison = None
        if inference_probe is not None:
            observed_outputs = _run_probe(reloaded_model, inference_probe)
            comparison_dtype, rtol, atol = active.comparison_tolerances(source_dtype)
            comparison = _compare_probe_outputs(
                reference_outputs or {},
                observed_outputs,
                comparison_dtype=comparison_dtype,
                rtol=rtol,
                atol=atol,
            )
            if not comparison.passed:
                raise TrainingDataInputError(
                    "Reloaded deployment inference differs from the source beyond policy tolerances."
                )

        notes: list[str] = []
        if training_dtype is None:
            notes.append("source_training_dtype_inferred_from_source_model")
        if source_dtype == "float32" and deployment_dtype == "float64":
            notes.append("float32_to_float64_promotion_does_not_restore_lost_precision")
        notes.append("downstream_runtime_precision_semantics_are_owned_by_the_consumer")

        record = MaceDeploymentArtifact(
            policy=active,
            source_artifact_path=str(source),
            source_artifact_sha256=source_sha256,
            source_training_dtype=resolved_training_dtype,
            source_precision=source_precision,
            source_state_sha256=source_state_sha256,
            precision_transition_digest=precision_transition_digest,
            target_head=None if target_head is None else str(target_head),
            deployment_relative_path=str(target.relative_to(root)),
            deployment_artifact_sha256=_sha256_file(target),
            deployment_precision=deployment_precision,
            deployment_state_sha256=deployment_state_sha256,
            manifest_relative_path=str(manifest.relative_to(root)),
            conversion_kind=_conversion_kind(source_dtype, deployment_dtype),
            state_conversion_exact=state_exact,
            inference_comparison=comparison,
            torch_version=str(torch.__version__),
            downstream_runtime_precision_claimed=False,
            byte_determinism_claimed=False,
            notes=tuple(notes),
        )
        if not record.passed:
            raise TrainingDataInputError(
                f"MACE deployment artifact failed qualification: {record.failure_reasons!r}."
            )
        with tempfile.NamedTemporaryFile(
            prefix=f".{manifest.name}.", suffix=".tmp", dir=root, mode="w", encoding="utf-8", delete=False
        ) as handle:
            temporary_manifest = Path(handle.name)
            handle.write(canonical_json(record.to_dict()))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_manifest, manifest)
        temporary_manifest = None
        if _sha256_file(source) != source_sha256:
            raise TrainingDataInputError("MACE source artifact changed during deployment export.")
        return record
    except Exception:
        target.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    finally:
        for path in (temporary_model, temporary_manifest):
            if path is not None:
                path.unlink(missing_ok=True)
        del reference_model, conversion_model, reloaded_model
