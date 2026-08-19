"""DEPLOY-VERIFY1 numerical parity for TRAIN2/EVAL2 deployment artifacts.

The gate is deliberately narrower than PES/relaxation/dynamics verification:
it proves that one selected checkpoint, its exported target-only MACE model, and
its ML-IAP/LAMMPS deployment representation produce the same energy/force (and,
where available, stress) predictions on one frozen probe cohort.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

DEPLOY_VERIFY_POLICY_SCHEMA = "mdstats.deploy-verify-policy.v1"
DEPLOY_VERIFY_PROBE_SET_SCHEMA = "mdstats.deploy-verify-probe-set.v1"
DEPLOY_VERIFY_COMPARISON_SCHEMA = "mdstats.deploy-verify-comparison.v1"
DEPLOY_VERIFY_RUN0_SCHEMA = "mdstats.deploy-verify-lammps-run0.v1"
DEPLOY_VERIFY_RUN_SCHEMA_V1 = "mdstats.deploy-verify-run.v1"
DEPLOY_VERIFY_RUN_SCHEMA_V2 = "mdstats.deploy-verify-run.v2"
DEPLOY_VERIFY_RUN_SCHEMA = DEPLOY_VERIFY_RUN_SCHEMA_V2
TARGET_HEAD_DEPLOYMENT_IDENTITY_SCHEMA = "mdstats.target-head-deployment-identity.v1"
MLIAP_EXPORT_RUNTIME_CAPABILITY_SCHEMA = "mdstats.mliap-export-runtime-capability.v1"
DEPLOY_VERIFY_CAMPAIGN_SCHEMA = "mdstats.deploy-verify-campaign.v1"
DEPLOY_VERIFY_IMPLEMENTATION_VERSION = "mdstats.deploy-verify1.2026-08.v1"


@dataclass(frozen=True, slots=True)
class TargetHeadDeploymentIdentity:
    """Scientific role identity of one learned target-only deployment model.

    This deliberately cannot describe the EXTRACT1 selected-foundation artifact:
    the source role is a trained multi-head candidate and the target role is the
    learned target head selected by EVAL2.
    """

    run_plan_digest: str
    eval2_run_record_digest: str
    source_model_sha256: str
    target_model_sha256: str
    target_head: str
    deployment_dtype: str
    source_artifact_role: str = "trained_candidate_multihead"
    target_artifact_role: str = "learned_target_head"
    serialization_schema: str = field(default=TARGET_HEAD_DEPLOYMENT_IDENTITY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != TARGET_HEAD_DEPLOYMENT_IDENTITY_SCHEMA:
            raise TrainingDataInputError("Unsupported target-head deployment identity schema.")
        for name in ("run_plan_digest", "eval2_run_record_digest", "source_model_sha256", "target_model_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not str(self.target_head).strip():
            raise TrainingDataInputError("Target-head deployment identity requires a non-empty learned head name.")
        if self.deployment_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Target-head deployment identity dtype must be float32 or float64.")
        if self.source_artifact_role != "trained_candidate_multihead":
            raise TrainingDataInputError("Target-head deployment source must be a trained candidate model.")
        if self.target_artifact_role != "learned_target_head":
            raise TrainingDataInputError("Target-head deployment target must be the learned target head.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "eval2_run_record_digest": self.eval2_run_record_digest,
            "source_model_sha256": self.source_model_sha256,
            "target_model_sha256": self.target_model_sha256,
            "target_head": self.target_head,
            "deployment_dtype": self.deployment_dtype,
            "source_artifact_role": self.source_artifact_role,
            "target_artifact_role": self.target_artifact_role,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetHeadDeploymentIdentity":
        if payload.get("schema") != TARGET_HEAD_DEPLOYMENT_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-head deployment identity schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            eval2_run_record_digest=str(payload["eval2_run_record_digest"]),
            source_model_sha256=str(payload["source_model_sha256"]),
            target_model_sha256=str(payload["target_model_sha256"]),
            target_head=str(payload["target_head"]),
            deployment_dtype=str(payload["deployment_dtype"]),
            source_artifact_role=str(payload.get("source_artifact_role", "trained_candidate_multihead")),
            target_artifact_role=str(payload.get("target_artifact_role", "learned_target_head")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-head deployment identity digest mismatch.")
        return result


def target_head_export_digest(
    *,
    source_model_sha256: str,
    target_model_sha256: str,
    target_head: str,
    deployment_dtype: str,
    target_head_deployment_identity_digest: str | None = None,
) -> str:
    """Freeze the identity of the target-head extraction/export transform.

    Historical callers retain the exact v1 digest.  Canonical DEPLOY1 callers
    additionally bind the learned-target deployment-role identity.
    """
    source = validate_digest(source_model_sha256, name="source_model_sha256")
    target = validate_digest(target_model_sha256, name="target_model_sha256")
    head = str(target_head).strip()
    dtype = str(deployment_dtype).strip()
    if not head or dtype not in {"float32", "float64"}:
        raise TrainingDataInputError("DEPLOY-VERIFY1 target-head export identity is invalid.")
    payload = {
        "schema": "mdstats.deploy-verify-target-head-export.v1",
        "source_model_sha256": source,
        "target_model_sha256": target,
        "target_head": head,
        "deployment_dtype": dtype,
        "exporter": "mdstats.export_target_head_model_artifact",
    }
    if target_head_deployment_identity_digest is not None:
        payload["schema"] = "mdstats.deploy-verify-target-head-export.v2"
        payload["target_head_deployment_identity_digest"] = validate_digest(
            target_head_deployment_identity_digest, name="target_head_deployment_identity_digest"
        )
    return digest(payload)


def _sha256_file(path: str | Path) -> str:
    target = Path(path)
    hasher = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _record_digest(payload: Mapping[str, Any], *, name: str) -> str:
    value = payload.get("content_digest")
    if value is None:
        raise TrainingDataSerializationError(f"{name} is missing content_digest.")
    return validate_digest(str(value), name="content_digest")


@dataclass(frozen=True, slots=True)
class DeployVerifyPolicy:
    model_dtype: str
    maximum_probe_configurations: int = 16
    require_stress_when_available: bool = True
    require_lammps_run0: bool = True
    float32_rtol: float = 1.0e-5
    float32_atol: float = 1.0e-6
    float64_rtol: float = 1.0e-9
    float64_atol: float = 1.0e-10
    implementation_version: str = DEPLOY_VERIFY_IMPLEMENTATION_VERSION
    serialization_schema: str = field(default=DEPLOY_VERIFY_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DEPLOY_VERIFY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 policy schema.")
        if self.model_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("DEPLOY-VERIFY1 model dtype must be float32 or float64.")
        if int(self.maximum_probe_configurations) <= 0:
            raise TrainingDataInputError("DEPLOY-VERIFY1 requires a positive probe-set size.")
        object.__setattr__(self, "maximum_probe_configurations", int(self.maximum_probe_configurations))
        for name in ("float32_rtol", "float32_atol", "float64_rtol", "float64_atol"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and non-negative.")
            object.__setattr__(self, name, value)
        if not self.implementation_version.strip():
            raise TrainingDataInputError("DEPLOY-VERIFY1 implementation version is empty.")

    @property
    def tolerances(self) -> tuple[float, float]:
        if self.model_dtype == "float32":
            return self.float32_rtol, self.float32_atol
        return self.float64_rtol, self.float64_atol

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "model_dtype": self.model_dtype,
            "maximum_probe_configurations": self.maximum_probe_configurations,
            "require_stress_when_available": self.require_stress_when_available,
            "require_lammps_run0": self.require_lammps_run0,
            "float32_rtol": self.float32_rtol,
            "float32_atol": self.float32_atol,
            "float64_rtol": self.float64_rtol,
            "float64_atol": self.float64_atol,
            "implementation_version": self.implementation_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DeployVerifyPolicy":
        if payload.get("schema") != DEPLOY_VERIFY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DEPLOY-VERIFY1 policy schema.")
        result = cls(
            model_dtype=str(payload["model_dtype"]),
            maximum_probe_configurations=int(payload["maximum_probe_configurations"]),
            require_stress_when_available=bool(payload["require_stress_when_available"]),
            require_lammps_run0=bool(payload["require_lammps_run0"]),
            float32_rtol=float(payload["float32_rtol"]),
            float32_atol=float(payload["float32_atol"]),
            float64_rtol=float(payload["float64_rtol"]),
            float64_atol=float(payload["float64_atol"]),
            implementation_version=str(payload["implementation_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("DEPLOY-VERIFY1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DeployVerifyProbeSet:
    target_role_digest: str
    target_artifact_digest: str
    target_artifact_sha256: str
    frame_uids: tuple[str, ...]
    correlation_block_ids: tuple[str, ...]
    configuration_indices: tuple[int, ...]
    selection_method: str = "correlation_block_round_robin_v1"
    serialization_schema: str = field(default=DEPLOY_VERIFY_PROBE_SET_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DEPLOY_VERIFY_PROBE_SET_SCHEMA:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 probe-set schema.")
        for name in ("target_role_digest", "target_artifact_digest", "target_artifact_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        blocks = tuple(validate_digest(v, name="correlation_block_id") for v in self.correlation_block_ids)
        indices = tuple(int(v) for v in self.configuration_indices)
        if not frames or len(frames) != len(blocks) or len(frames) != len(indices):
            raise TrainingDataInputError("DEPLOY-VERIFY1 probe membership is empty or inconsistent.")
        if len(set(frames)) != len(frames) or len(set(indices)) != len(indices) or any(v < 0 for v in indices):
            raise TrainingDataInputError("DEPLOY-VERIFY1 probe membership must be unique and non-negative.")
        if not self.selection_method.strip():
            raise TrainingDataInputError("DEPLOY-VERIFY1 probe selection method is empty.")
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "correlation_block_ids", blocks)
        object.__setattr__(self, "configuration_indices", indices)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "target_role_digest": self.target_role_digest,
            "target_artifact_digest": self.target_artifact_digest,
            "target_artifact_sha256": self.target_artifact_sha256,
            "frame_uids": list(self.frame_uids),
            "correlation_block_ids": list(self.correlation_block_ids),
            "configuration_indices": list(self.configuration_indices),
            "selection_method": self.selection_method,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DeployVerifyProbeSet":
        if payload.get("schema") != DEPLOY_VERIFY_PROBE_SET_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DEPLOY-VERIFY1 probe-set schema.")
        result = cls(
            target_role_digest=str(payload["target_role_digest"]),
            target_artifact_digest=str(payload["target_artifact_digest"]),
            target_artifact_sha256=str(payload["target_artifact_sha256"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            correlation_block_ids=tuple(str(v) for v in payload["correlation_block_ids"]),
            configuration_indices=tuple(int(v) for v in payload["configuration_indices"]),
            selection_method=str(payload.get("selection_method", "correlation_block_round_robin_v1")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DEPLOY-VERIFY1 probe-set digest mismatch.")
        return result


def build_deploy_verify_probe_set(
    target_role: Any,
    *,
    target_artifact_digest: str,
    target_artifact_sha256: str,
    maximum_configurations: int = 16,
) -> DeployVerifyProbeSet:
    """Choose a deterministic, correlation-block-balanced subset of an EVAL2 role."""

    frames = tuple(target_role.evaluation_frame_uids)
    blocks = tuple(target_role.correlation_block_ids)
    if not frames or len(frames) != len(blocks):
        raise TrainingDataInputError("DEPLOY-VERIFY1 requires a non-empty EVAL2 target role.")
    limit = min(int(maximum_configurations), len(frames))
    if limit <= 0:
        raise TrainingDataInputError("DEPLOY-VERIFY1 maximum probe configurations must be positive.")
    by_block: dict[str, list[tuple[int, str]]] = {}
    for index, (uid, block) in enumerate(zip(frames, blocks)):
        by_block.setdefault(block, []).append((index, uid))
    role_digest = str(target_role.content_digest)
    ordered_blocks = sorted(
        by_block,
        key=lambda block: digest({"schema": "mdstats.deploy-verify-block-order.v1", "role": role_digest, "block": block}),
    )
    for block, members in by_block.items():
        members.sort(
            key=lambda item: digest({
                "schema": "mdstats.deploy-verify-member-order.v1",
                "role": role_digest,
                "block": block,
                "frame_uid": item[1],
            })
        )
    selected: list[tuple[int, str, str]] = []
    rank = 0
    while len(selected) < limit:
        progressed = False
        for block in ordered_blocks:
            members = by_block[block]
            if rank < len(members):
                index, uid = members[rank]
                selected.append((index, uid, block))
                progressed = True
                if len(selected) == limit:
                    break
        if not progressed:
            break
        rank += 1
    return DeployVerifyProbeSet(
        target_role_digest=role_digest,
        target_artifact_digest=target_artifact_digest,
        target_artifact_sha256=target_artifact_sha256,
        frame_uids=tuple(uid for _, uid, _ in selected),
        correlation_block_ids=tuple(block for _, _, block in selected),
        configuration_indices=tuple(index for index, _, _ in selected),
    )


@dataclass(frozen=True, slots=True)
class DeployVerifyComparison:
    reference_identity: str
    observed_identity: str
    rtol: float
    atol: float
    channel_metrics: tuple[tuple[str, float, float, float, bool], ...]
    serialization_schema: str = field(default=DEPLOY_VERIFY_COMPARISON_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DEPLOY_VERIFY_COMPARISON_SCHEMA:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 comparison schema.")
        if not self.reference_identity.strip() or not self.observed_identity.strip():
            raise TrainingDataInputError("DEPLOY-VERIFY1 comparison identities must be non-empty.")
        if not np.all(np.isfinite([self.rtol, self.atol])) or min(self.rtol, self.atol) < 0.0:
            raise TrainingDataInputError("DEPLOY-VERIFY1 comparison tolerances are invalid.")
        metrics = tuple(sorted((str(n), float(a), float(r), float(m), bool(p)) for n, a, r, m, p in self.channel_metrics))
        if not metrics:
            raise TrainingDataInputError("DEPLOY-VERIFY1 comparison requires at least one channel.")
        if {m[0] for m in metrics} < {"energy", "forces"}:
            raise TrainingDataInputError("DEPLOY-VERIFY1 comparison requires energy and force channels.")
        for name, max_abs, rmse, ref_max, _ in metrics:
            if not name or not np.all(np.isfinite([max_abs, rmse, ref_max])) or min(max_abs, rmse, ref_max) < 0.0:
                raise TrainingDataInputError("DEPLOY-VERIFY1 comparison metrics are invalid.")
        object.__setattr__(self, "channel_metrics", metrics)

    @property
    def passed(self) -> bool:
        return all(v[4] for v in self.channel_metrics)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "reference_identity": self.reference_identity,
            "observed_identity": self.observed_identity,
            "rtol": self.rtol,
            "atol": self.atol,
            "channel_metrics": [list(v) for v in self.channel_metrics],
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DeployVerifyComparison":
        if payload.get("schema") != DEPLOY_VERIFY_COMPARISON_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DEPLOY-VERIFY1 comparison schema.")
        result = cls(
            reference_identity=str(payload["reference_identity"]),
            observed_identity=str(payload["observed_identity"]),
            rtol=float(payload["rtol"]),
            atol=float(payload["atol"]),
            channel_metrics=tuple((str(v[0]), float(v[1]), float(v[2]), float(v[3]), bool(v[4])) for v in payload["channel_metrics"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DEPLOY-VERIFY1 comparison digest mismatch.")
        return result


def compare_prediction_channels(
    reference: Mapping[str, np.ndarray],
    observed: Mapping[str, np.ndarray],
    *,
    reference_identity: str,
    observed_identity: str,
    rtol: float,
    atol: float,
) -> DeployVerifyComparison:
    required = {"energy", "forces"}
    reference_channels = set(reference)
    observed_channels = set(observed)
    if not required <= reference_channels or not required <= observed_channels:
        raise TrainingDataInputError("DEPLOY-VERIFY1 predictions require energy and forces.")
    if reference_channels != observed_channels:
        raise TrainingDataInputError(
            "DEPLOY-VERIFY1 prediction channel availability changed across representations."
        )
    shared = sorted(reference_channels)
    metrics: list[tuple[str, float, float, float, bool]] = []
    for name in shared:
        expected = np.asarray(reference[name], dtype=np.float64)
        actual = np.asarray(observed[name], dtype=np.float64)
        if expected.shape != actual.shape:
            raise TrainingDataInputError(f"DEPLOY-VERIFY1 {name} channel changed shape.")
        if expected.size == 0 or not np.all(np.isfinite(expected)) or not np.all(np.isfinite(actual)):
            raise TrainingDataInputError(f"DEPLOY-VERIFY1 {name} channel is empty or non-finite.")
        diff = actual - expected
        metrics.append((
            name,
            float(np.max(np.abs(diff))),
            float(np.sqrt(np.mean(np.square(diff)))),
            float(np.max(np.abs(expected))),
            bool(np.allclose(actual, expected, rtol=rtol, atol=atol)),
        ))
    return DeployVerifyComparison(
        reference_identity=reference_identity,
        observed_identity=observed_identity,
        rtol=rtol,
        atol=atol,
        channel_metrics=tuple(metrics),
    )


def _load_probe_atoms(path: str | Path, indices: Sequence[int]) -> tuple[Any, ...]:
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for DEPLOY-VERIFY1.") from exc
    target = Path(path).resolve()
    if not target.is_file():
        raise TrainingDataInputError("DEPLOY-VERIFY1 target artifact is missing.")
    all_atoms = tuple(read(target, index=":"))
    result = tuple(all_atoms[int(i)] for i in indices)
    if not result:
        raise TrainingDataInputError("DEPLOY-VERIFY1 probe set is empty.")
    return result


def predict_mace_model_on_probe(
    model_path: str | Path,
    probe_atoms: Sequence[Any],
    *,
    device: str,
    model_dtype: str,
    head: str | None,
    calculator_kwargs: Mapping[str, Any] | None = None,
    foundation_potential_identity: Any | None = None,
    foundation_inference_identity: Any | None = None,
) -> dict[str, np.ndarray]:
    """Predict energy/forces/stress through the deployable MACE calculator.

    EVAL1 may bind a source-foundation prediction to the exact scientific and
    inference identities. Candidate/deployment callers retain the historical
    head-only interface.
    """
    try:
        from mace.calculators import MACECalculator
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("mace-torch is required for DEPLOY-VERIFY1.") from exc
    resolved_path = Path(model_path).resolve()
    kwargs: dict[str, Any] = dict(calculator_kwargs or {})
    if foundation_potential_identity is not None:
        if foundation_inference_identity is None:
            raise TrainingDataInputError("Canonical foundation probe inference requires FoundationInferenceIdentity.")
        from ._common import sha256_file_cached
        if sha256_file_cached(resolved_path) != foundation_potential_identity.sha256:
            raise TrainingDataInputError("Foundation probe model bytes disagree with FoundationPotentialIdentity.")
        if foundation_inference_identity.foundation_potential_digest != foundation_potential_identity.canonical_content_digest:
            raise TrainingDataInputError("Foundation probe inference/potential identities disagree.")
        if foundation_inference_identity.default_dtype != str(model_dtype):
            raise TrainingDataInputError("Foundation probe inference dtype disagrees with requested model dtype.")
        if head not in (None, "", foundation_potential_identity.foundation_head):
            raise TrainingDataInputError("Foundation probe head conflicts with canonical potential identity.")
        head = foundation_potential_identity.foundation_head
        expected_backend = "cueq" if bool(kwargs.get("enable_cueq", False)) else "e3nn"
        if foundation_inference_identity.backend != expected_backend:
            raise TrainingDataInputError("Foundation probe calculator backend disagrees with inference identity.")
    if head is not None:
        kwargs["head"] = head
    calculator = MACECalculator(
        model_paths=str(resolved_path),
        device=str(device),
        default_dtype=str(model_dtype),
        **kwargs,
    )
    energies: list[float] = []
    forces: list[np.ndarray] = []
    stresses: list[np.ndarray] = []
    stress_available = True
    for source in probe_atoms:
        atoms = source.copy()
        atoms.calc = calculator
        energies.append(float(atoms.get_potential_energy()))
        forces.append(np.asarray(atoms.get_forces(), dtype=np.float64))
        if bool(np.all(atoms.pbc)) and float(abs(atoms.get_volume())) > 1.0e-12:
            try:
                stresses.append(np.asarray(atoms.get_stress(voigt=False), dtype=np.float64))
            except Exception:
                stress_available = False
        else:
            stress_available = False
    result: dict[str, np.ndarray] = {
        "energy": np.asarray(energies, dtype=np.float64),
        "forces": np.concatenate([v.reshape(-1) for v in forces]),
    }
    if stress_available and len(stresses) == len(probe_atoms):
        result["stress"] = np.stack(stresses, axis=0)
    return result


@dataclass(frozen=True, slots=True)
class MliapExportRuntimeCapability:
    python_executable: str
    mace_version: str | None
    cuequivariance_available: bool
    cuequivariance_torch_available: bool
    supported_mace_version: bool
    failure_reasons: tuple[str, ...] = ()
    serialization_schema: str = field(default=MLIAP_EXPORT_RUNTIME_CAPABILITY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != MLIAP_EXPORT_RUNTIME_CAPABILITY_SCHEMA:
            raise TrainingDataInputError("Unsupported ML-IAP export-runtime capability schema.")
        if not str(self.python_executable).strip():
            raise TrainingDataInputError("ML-IAP export-runtime capability requires a Python executable.")
        object.__setattr__(self, "failure_reasons", tuple(str(v) for v in self.failure_reasons))

    @property
    def passed(self) -> bool:
        return (
            self.supported_mace_version
            and self.cuequivariance_available
            and self.cuequivariance_torch_available
            and not self.failure_reasons
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "python_executable": self.python_executable,
            "mace_version": self.mace_version,
            "cuequivariance_available": self.cuequivariance_available,
            "cuequivariance_torch_available": self.cuequivariance_torch_available,
            "supported_mace_version": self.supported_mace_version,
            "failure_reasons": list(self.failure_reasons),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MliapExportRuntimeCapability":
        if payload.get("schema") != MLIAP_EXPORT_RUNTIME_CAPABILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported ML-IAP export-runtime capability schema.")
        result = cls(
            python_executable=str(payload["python_executable"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            cuequivariance_available=bool(payload["cuequivariance_available"]),
            cuequivariance_torch_available=bool(payload["cuequivariance_torch_available"]),
            supported_mace_version=bool(payload["supported_mace_version"]),
            failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("ML-IAP export-runtime capability digest mismatch.")
        return result


def probe_mliap_export_runtime(
    python_executable: str | Path | None = None,
) -> MliapExportRuntimeCapability:
    """Qualify the MACE 0.3.16 official ML-IAP exporter runtime.

    MACE 0.3.16 unconditionally converts an e3nn model to CuEquivariance before
    wrapping it for ML-IAP. Even an e3nn-trained campaign therefore needs the
    CuEq core and torch packages at deployment-export time.
    """
    python = str(Path(python_executable or sys.executable).absolute())
    code = (
        "import importlib.metadata, importlib.util, json\n"
        "try:\n"
        "    version = importlib.metadata.version('mace-torch')\n"
        "except Exception:\n"
        "    version = None\n"
        "print(json.dumps({\n"
        "    'mace_version': version,\n"
        "    'cuequivariance': importlib.util.find_spec('cuequivariance') is not None,\n"
        "    'cuequivariance_torch': importlib.util.find_spec('cuequivariance_torch') is not None,\n"
        "}, sort_keys=True))\n"
    )
    try:
        completed = subprocess.run(
            [python, "-c", code],
            capture_output=True,
            text=True,
            check=False,
            timeout=30.0,
        )
        payload = (
            json.loads(completed.stdout.strip().splitlines()[-1])
            if completed.returncode == 0 and completed.stdout.strip()
            else {}
        )
    except Exception:
        payload = {}
    version = None if payload.get("mace_version") is None else str(payload.get("mace_version"))
    cueq = bool(payload.get("cuequivariance", False))
    cueq_torch = bool(payload.get("cuequivariance_torch", False))
    reasons: list[str] = []
    supported = version == "0.3.16"
    if not supported:
        reasons.append("unsupported_or_missing_mace_0.3.16_runtime")
    if not cueq:
        reasons.append("cuequivariance_unavailable")
    if not cueq_torch:
        reasons.append("cuequivariance_torch_unavailable")
    return MliapExportRuntimeCapability(
        python_executable=python,
        mace_version=version,
        cuequivariance_available=cueq,
        cuequivariance_torch_available=cueq_torch,
        supported_mace_version=supported,
        failure_reasons=tuple(reasons),
    )

def export_mliap_lammps_artifact(
    target_model_path: str | Path,
    output_directory: str | Path,
    *,
    model_dtype: str,
    target_head: str | None = None,
    source_identity_digest: str | None = None,
    python_executable: str | Path | None = None,
    require_runtime_capability: bool = True,
    timeout_seconds: float = 1800.0,
) -> tuple[Path, str]:
    """Convert one target-only MACE model using MACE's official ML-IAP exporter."""
    source = Path(target_model_path).resolve()
    if not source.is_file():
        raise TrainingDataInputError("DEPLOY-VERIFY1 target-only model is missing.")
    runtime_capability = None
    if require_runtime_capability:
        runtime_capability = probe_mliap_export_runtime(python_executable)
        if not runtime_capability.passed:
            raise TrainingDataInputError(
                "MACE 0.3.16 ML-IAP export runtime is not qualified: "
                + "; ".join(runtime_capability.failure_reasons)
                + ". The official 0.3.16 exporter requires CuEquivariance even for an e3nn-trained model."
            )
    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    staged = root / "target-only.model"
    if staged.resolve() != source:
        shutil.copy2(source, staged)
    else:
        staged = source
    command = [
        str(python_executable or sys.executable),
        "-m", "mace.cli.create_lammps_model",
        str(staged),
        "--format=mliap",
        f"--dtype={model_dtype}",
    ]
    if target_head is not None:
        command.append(f"--head={target_head}")
    completed = subprocess.run(
        command,
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=float(timeout_seconds),
    )
    output = Path(str(staged) + "-mliap_lammps.pt")
    if completed.returncode != 0 or not output.is_file():
        tail = (completed.stderr or completed.stdout)[-4000:]
        raise TrainingDataInputError("MACE ML-IAP export failed. Last output:\n" + tail)
    export_payload = {
        "schema": "mdstats.deploy-verify-mliap-export.v1",
        "source_sha256": _sha256_file(source),
        "output_sha256": _sha256_file(output),
        "model_dtype": model_dtype,
        "target_head": target_head,
        "command": command[1:],
    }
    if source_identity_digest is not None:
        export_payload["schema"] = "mdstats.deploy-verify-mliap-export.v2"
        export_payload["source_identity_digest"] = validate_digest(
            source_identity_digest, name="source_identity_digest"
        )
        if runtime_capability is not None:
            export_payload["runtime_capability_digest"] = runtime_capability.content_digest
            export_payload["mace_version"] = runtime_capability.mace_version
    return output.resolve(), digest(export_payload)


@dataclass(frozen=True, slots=True)
class LammpsRun0Record:
    executable_path: str
    executable_sha256: str
    command_arguments: tuple[str, ...]
    mliap_artifact_sha256: str
    element_order: tuple[str, ...]
    probe_set_digest: str
    predictions_sha256: str
    serialization_schema: str = field(default=DEPLOY_VERIFY_RUN0_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DEPLOY_VERIFY_RUN0_SCHEMA:
            raise TrainingDataInputError("Unsupported LAMMPS run-0 schema.")
        for name in ("executable_sha256", "mliap_artifact_sha256", "probe_set_digest", "predictions_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not self.executable_path.strip() or not self.element_order:
            raise TrainingDataInputError("LAMMPS run-0 identity is incomplete.")
        object.__setattr__(self, "command_arguments", tuple(str(v) for v in self.command_arguments))
        object.__setattr__(self, "element_order", tuple(str(v) for v in self.element_order))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "executable_path": self.executable_path,
            "executable_sha256": self.executable_sha256,
            "command_arguments": list(self.command_arguments),
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "element_order": list(self.element_order),
            "probe_set_digest": self.probe_set_digest,
            "predictions_sha256": self.predictions_sha256,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LammpsRun0Record":
        if payload.get("schema") != DEPLOY_VERIFY_RUN0_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LAMMPS run-0 schema.")
        result = cls(
            executable_path=str(payload["executable_path"]),
            executable_sha256=str(payload["executable_sha256"]),
            command_arguments=tuple(str(v) for v in payload["command_arguments"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]),
            element_order=tuple(str(v) for v in payload["element_order"]),
            probe_set_digest=str(payload["probe_set_digest"]),
            predictions_sha256=str(payload["predictions_sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("LAMMPS run-0 digest mismatch.")
        return result


def _prediction_digest(predictions: Mapping[str, np.ndarray]) -> str:
    hasher = hashlib.sha256()
    for name in sorted(predictions):
        array = np.asarray(predictions[name], dtype=np.float64)
        meta = json.dumps({"name": name, "shape": list(array.shape)}, sort_keys=True).encode("ascii")
        hasher.update(meta)
        hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _model_element_order(model_path: str | Path) -> tuple[str, ...]:
    try:
        import torch
        from ase.data import chemical_symbols
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("PyTorch and ASE are required for ML-IAP deployment verification.") from exc
    model = torch.load(Path(model_path).resolve(), map_location="cpu", weights_only=False)
    values = [int(v) for v in model.atomic_numbers.detach().cpu().reshape(-1).tolist()]
    return tuple(chemical_symbols[v] for v in values)


def run_lammps_mliap_run0(
    mliap_artifact_path: str | Path,
    target_model_path: str | Path,
    probe_atoms: Sequence[Any],
    *,
    probe_set_digest: str,
    lammps_executable: str | Path,
    lammps_arguments: Sequence[str] = (),
    work_directory: str | Path,
    timeout_seconds: float = 600.0,
    environment: Mapping[str, str] | None = None,
) -> tuple[dict[str, np.ndarray], LammpsRun0Record]:
    """Run one LAMMPS ``run 0`` per frozen probe configuration through ML-IAP."""
    try:
        from ase.io import write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for LAMMPS run-0 verification.") from exc
    executable_text = str(lammps_executable)
    executable = Path(executable_text).expanduser()
    if not executable.is_file():
        resolved = shutil.which(executable_text)
        if resolved is None:
            raise TrainingDataInputError(
                f"DEPLOY-VERIFY1 requires a LAMMPS ML-IAP executable; not found: {executable_text!r}."
            )
        executable = Path(resolved)
    executable = executable.resolve()
    mliap = Path(mliap_artifact_path).resolve()
    if not mliap.is_file():
        raise TrainingDataInputError("DEPLOY-VERIFY1 ML-IAP artifact is missing.")
    elements = _model_element_order(target_model_path)
    root = Path(work_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    energies: list[float] = []
    forces: list[np.ndarray] = []
    stresses: list[np.ndarray] = []
    all_stress = True
    merged_env = dict(os.environ)
    if environment is not None:
        merged_env.update({str(k): str(v) for k, v in environment.items()})

    # LAMMPS metal-unit pressure -> ASE stress eV/A^3 (opposite sign convention).
    bar_to_ev_a3 = 1.0e5 / 1.602176634e11
    for index, source in enumerate(probe_atoms):
        case = root / f"case-{index:03d}"
        case.mkdir(parents=True, exist_ok=True)
        data_path = case / "structure.data"
        local_model = case / "deployment-mliap.pt"
        shutil.copy2(mliap, local_model)
        write(data_path, source, format="lammps-data", atom_style="atomic", specorder=list(elements), masses=True)
        boundary = " ".join("p" if bool(v) else "f" for v in source.pbc)
        input_text = "\n".join([
            "units metal",
            "atom_style atomic",
            f"boundary {boundary}",
            "newton on",
            "atom_modify map yes",
            "read_data structure.data",
            "pair_style mliap unified deployment-mliap.pt 0",
            "pair_coeff * * " + " ".join(elements),
            "thermo 1",
            "thermo_style custom step pe pxx pyy pzz pxy pxz pyz",
            "run 0",
            "write_dump all custom forces.dump id type fx fy fz modify sort id",
            "variable de equal pe",
            "variable dpxx equal pxx",
            "variable dpyy equal pyy",
            "variable dpzz equal pzz",
            "variable dpxy equal pxy",
            "variable dpxz equal pxz",
            "variable dpyz equal pyz",
            'print "${de} ${dpxx} ${dpyy} ${dpzz} ${dpxy} ${dpxz} ${dpyz}" file metrics.txt screen no',
            "",
        ])
        (case / "run0.in").write_text(input_text, encoding="utf-8")
        command = [str(executable), *[str(v) for v in lammps_arguments], "-in", "run0.in"]
        completed = subprocess.run(
            command,
            cwd=case,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=float(timeout_seconds),
        )
        if completed.returncode != 0:
            tail = (completed.stderr or completed.stdout)[-5000:]
            raise TrainingDataInputError(f"LAMMPS ML-IAP run 0 failed for probe {index}. Last output:\n{tail}")
        metrics_path = case / "metrics.txt"
        dump_path = case / "forces.dump"
        if not metrics_path.is_file() or not dump_path.is_file():
            raise TrainingDataInputError("LAMMPS run 0 did not create the required parity outputs.")
        values = np.loadtxt(metrics_path, dtype=float).reshape(-1)
        if values.size != 7:
            raise TrainingDataInputError("LAMMPS run-0 metric output has unexpected shape.")
        energies.append(float(values[0]))
        lines = dump_path.read_text(encoding="utf-8", errors="replace").splitlines()
        marker = next((i for i, line in enumerate(lines) if line.startswith("ITEM: ATOMS")), None)
        if marker is None:
            raise TrainingDataInputError("LAMMPS run-0 force dump is malformed.")
        rows = []
        for line in lines[marker + 1:]:
            if line.startswith("ITEM:"):
                break
            fields = line.split()
            if len(fields) >= 5:
                rows.append((int(fields[0]), float(fields[2]), float(fields[3]), float(fields[4])))
        rows.sort(key=lambda v: v[0])
        if len(rows) != len(source):
            raise TrainingDataInputError("LAMMPS run-0 force dump atom count changed.")
        forces.append(np.asarray([[v[1], v[2], v[3]] for v in rows], dtype=np.float64))
        if bool(np.all(source.pbc)) and float(abs(source.get_volume())) > 1.0e-12:
            pxx, pyy, pzz, pxy, pxz, pyz = values[1:]
            stress = -bar_to_ev_a3 * np.asarray(
                [[pxx, pxy, pxz], [pxy, pyy, pyz], [pxz, pyz, pzz]], dtype=np.float64
            )
            stresses.append(stress)
        else:
            all_stress = False
    predictions: dict[str, np.ndarray] = {
        "energy": np.asarray(energies, dtype=np.float64),
        "forces": np.concatenate([v.reshape(-1) for v in forces]),
    }
    if all_stress and len(stresses) == len(probe_atoms):
        predictions["stress"] = np.stack(stresses, axis=0)
    pred_digest = _prediction_digest(predictions)
    return predictions, LammpsRun0Record(
        executable_path=str(executable),
        executable_sha256=_sha256_file(executable),
        command_arguments=tuple(str(v) for v in lammps_arguments),
        mliap_artifact_sha256=_sha256_file(mliap),
        element_order=elements,
        probe_set_digest=probe_set_digest,
        predictions_sha256=pred_digest,
    )


@dataclass(frozen=True, slots=True)
class DeployVerifyRunRecord:
    run_plan_digest: str
    eval2_run_record_digest: str
    policy: DeployVerifyPolicy
    probe_set: DeployVerifyProbeSet
    selected_checkpoint_sha256: str
    selected_checkpoint_epoch: int
    selected_checkpoint_model_sha256: str
    target_head_name: str
    target_only_model_path: str
    target_only_model_sha256: str
    target_head_export_digest: str
    mliap_artifact_path: str
    mliap_artifact_sha256: str
    mliap_export_digest: str
    checkpoint_to_target_comparison: DeployVerifyComparison
    target_to_lammps_comparison: DeployVerifyComparison
    lammps_run0: LammpsRun0Record
    target_head_deployment_identity: TargetHeadDeploymentIdentity | None = None
    mliap_source_identity_digest: str | None = None
    serialization_schema: str = field(default=DEPLOY_VERIFY_RUN_SCHEMA_V1, repr=False, compare=False)

    def __post_init__(self) -> None:
        schema = self.serialization_schema
        if self.target_head_deployment_identity is not None and schema == DEPLOY_VERIFY_RUN_SCHEMA_V1:
            schema = DEPLOY_VERIFY_RUN_SCHEMA_V2
            object.__setattr__(self, "serialization_schema", schema)
        if schema not in {DEPLOY_VERIFY_RUN_SCHEMA_V1, DEPLOY_VERIFY_RUN_SCHEMA_V2}:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 run schema.")
        if schema == DEPLOY_VERIFY_RUN_SCHEMA_V2 and self.target_head_deployment_identity is None:
            raise TrainingDataInputError("DEPLOY-VERIFY1 v2 requires learned target-head deployment identity.")
        if schema == DEPLOY_VERIFY_RUN_SCHEMA_V1 and (self.target_head_deployment_identity is not None or self.mliap_source_identity_digest is not None):
            raise TrainingDataInputError("Legacy DEPLOY-VERIFY1 run cannot carry DEPLOY1 identity fields.")
        for name in (
            "run_plan_digest", "eval2_run_record_digest", "selected_checkpoint_sha256",
            "selected_checkpoint_model_sha256", "target_only_model_sha256", "target_head_export_digest",
            "mliap_artifact_sha256", "mliap_export_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.selected_checkpoint_epoch) < 0 or not self.target_head_name.strip():
            raise TrainingDataInputError("DEPLOY-VERIFY1 selected checkpoint identity is invalid.")
        object.__setattr__(self, "selected_checkpoint_epoch", int(self.selected_checkpoint_epoch))
        identity_digest = None
        if self.target_head_deployment_identity is not None:
            identity = self.target_head_deployment_identity
            if identity.run_plan_digest != self.run_plan_digest or identity.eval2_run_record_digest != self.eval2_run_record_digest:
                raise TrainingDataInputError("DEPLOY-VERIFY1 learned target-head lineage does not belong to this run/EVAL2 record.")
            if identity.source_model_sha256 != self.selected_checkpoint_model_sha256:
                raise TrainingDataInputError("DEPLOY-VERIFY1 learned target-head source model mismatch.")
            if identity.target_model_sha256 != self.target_only_model_sha256:
                raise TrainingDataInputError("DEPLOY-VERIFY1 learned target-head artifact mismatch.")
            if identity.target_head != self.target_head_name or identity.deployment_dtype != self.policy.model_dtype:
                raise TrainingDataInputError("DEPLOY-VERIFY1 learned target-head role/head/dtype mismatch.")
            identity_digest = identity.content_digest
            if self.mliap_source_identity_digest != identity_digest:
                raise TrainingDataInputError("DEPLOY-VERIFY1 ML-IAP source identity is not the learned target-head deployment identity.")
        expected_target_export = target_head_export_digest(
            source_model_sha256=self.selected_checkpoint_model_sha256,
            target_model_sha256=self.target_only_model_sha256,
            target_head=self.target_head_name,
            deployment_dtype=self.policy.model_dtype,
            target_head_deployment_identity_digest=identity_digest,
        )
        if self.target_head_export_digest != expected_target_export:
            raise TrainingDataInputError("DEPLOY-VERIFY1 target-head export identity mismatch.")
        if self.lammps_run0.probe_set_digest != self.probe_set.content_digest:
            raise TrainingDataInputError("DEPLOY-VERIFY1 run-0 probe identity mismatch.")
        if self.lammps_run0.mliap_artifact_sha256 != self.mliap_artifact_sha256:
            raise TrainingDataInputError("DEPLOY-VERIFY1 run-0 ML-IAP identity mismatch.")
        if not self.checkpoint_to_target_comparison.passed or not self.target_to_lammps_comparison.passed:
            raise TrainingDataInputError("DEPLOY-VERIFY1 cannot freeze a failed numerical parity record.")

    @property
    def passed(self) -> bool:
        return self.checkpoint_to_target_comparison.passed and self.target_to_lammps_comparison.passed

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "eval2_run_record_digest": self.eval2_run_record_digest,
            "policy": self.policy.to_dict(),
            "probe_set": self.probe_set.to_dict(),
            "selected_checkpoint_sha256": self.selected_checkpoint_sha256,
            "selected_checkpoint_epoch": self.selected_checkpoint_epoch,
            "selected_checkpoint_model_sha256": self.selected_checkpoint_model_sha256,
            "target_head_name": self.target_head_name,
            "target_only_model_path": self.target_only_model_path,
            "target_only_model_sha256": self.target_only_model_sha256,
            "target_head_export_digest": self.target_head_export_digest,
            "mliap_artifact_path": self.mliap_artifact_path,
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "mliap_export_digest": self.mliap_export_digest,
            "checkpoint_to_target_comparison": self.checkpoint_to_target_comparison.to_dict(),
            "target_to_lammps_comparison": self.target_to_lammps_comparison.to_dict(),
            "lammps_run0": self.lammps_run0.to_dict(),
            **({
                "target_head_deployment_identity": self.target_head_deployment_identity.to_dict(),
                "mliap_source_identity_digest": self.mliap_source_identity_digest,
            } if self.target_head_deployment_identity is not None else {}),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DeployVerifyRunRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {DEPLOY_VERIFY_RUN_SCHEMA_V1, DEPLOY_VERIFY_RUN_SCHEMA_V2}:
            raise TrainingDataSerializationError("Unsupported DEPLOY-VERIFY1 run schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            eval2_run_record_digest=str(payload["eval2_run_record_digest"]),
            policy=DeployVerifyPolicy.from_dict(payload["policy"]),
            probe_set=DeployVerifyProbeSet.from_dict(payload["probe_set"]),
            selected_checkpoint_sha256=str(payload["selected_checkpoint_sha256"]),
            selected_checkpoint_epoch=int(payload["selected_checkpoint_epoch"]),
            selected_checkpoint_model_sha256=str(payload["selected_checkpoint_model_sha256"]),
            target_head_name=str(payload["target_head_name"]),
            target_only_model_path=str(payload["target_only_model_path"]),
            target_only_model_sha256=str(payload["target_only_model_sha256"]),
            target_head_export_digest=str(payload["target_head_export_digest"]),
            mliap_artifact_path=str(payload["mliap_artifact_path"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]),
            mliap_export_digest=str(payload["mliap_export_digest"]),
            checkpoint_to_target_comparison=DeployVerifyComparison.from_dict(payload["checkpoint_to_target_comparison"]),
            target_to_lammps_comparison=DeployVerifyComparison.from_dict(payload["target_to_lammps_comparison"]),
            lammps_run0=LammpsRun0Record.from_dict(payload["lammps_run0"]),
            target_head_deployment_identity=(
                None if payload.get("target_head_deployment_identity") is None
                else TargetHeadDeploymentIdentity.from_dict(payload["target_head_deployment_identity"])
            ),
            mliap_source_identity_digest=(
                None if payload.get("mliap_source_identity_digest") is None
                else str(payload["mliap_source_identity_digest"])
            ),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DEPLOY-VERIFY1 run digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DeployVerifyCampaignRecord:
    campaign_plan_digest: str
    target_size_convergence_digest: str
    run_records: tuple[DeployVerifyRunRecord, ...]
    stage_context: str
    serialization_schema: str = field(default=DEPLOY_VERIFY_CAMPAIGN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DEPLOY_VERIFY_CAMPAIGN_SCHEMA:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 campaign schema.")
        for name in ("campaign_plan_digest", "target_size_convergence_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        records = tuple(sorted(self.run_records, key=lambda v: (v.run_plan_digest, v.selected_checkpoint_sha256)))
        if not records or len({v.run_plan_digest for v in records}) != len(records):
            raise TrainingDataInputError("DEPLOY-VERIFY1 campaign record requires unique run evidence.")
        if not all(v.passed for v in records):
            raise TrainingDataInputError("DEPLOY-VERIFY1 campaign record cannot contain failed runs.")
        if self.stage_context not in {"target_size_stage_c", "production"}:
            raise TrainingDataInputError("Unsupported DEPLOY-VERIFY1 campaign stage context.")
        object.__setattr__(self, "run_records", records)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "target_size_convergence_digest": self.target_size_convergence_digest,
            "run_records": [v.to_dict() for v in self.run_records],
            "stage_context": self.stage_context,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DeployVerifyCampaignRecord":
        if payload.get("schema") != DEPLOY_VERIFY_CAMPAIGN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DEPLOY-VERIFY1 campaign schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            target_size_convergence_digest=str(payload["target_size_convergence_digest"]),
            run_records=tuple(DeployVerifyRunRecord.from_dict(v) for v in payload["run_records"]),
            stage_context=str(payload["stage_context"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DEPLOY-VERIFY1 campaign digest mismatch.")
        return result


__all__ = [
    "DEPLOY_VERIFY_IMPLEMENTATION_VERSION",
    "DeployVerifyPolicy",
    "DeployVerifyProbeSet",
    "DeployVerifyComparison",
    "LammpsRun0Record",
    "TargetHeadDeploymentIdentity",
    "MliapExportRuntimeCapability",
    "probe_mliap_export_runtime",
    "DeployVerifyRunRecord",
    "DeployVerifyCampaignRecord",
    "build_deploy_verify_probe_set",
    "target_head_export_digest",
    "compare_prediction_channels",
    "predict_mace_model_on_probe",
    "export_mliap_lammps_artifact",
    "run_lammps_mliap_run0",
]
