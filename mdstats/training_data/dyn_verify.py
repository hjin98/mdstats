"""DYN-VERIFY2 short finite-temperature structural qualification for TRAIN2 candidates.

This gate runs the already deployment-qualified ML-IAP artifact through the exact
LAMMPS executable authenticated by DEPLOY-VERIFY1.  Candidate-independent DFT-
relaxed bases are heated briefly under Langevin NVT and then propagated under
NVE.  Numerical diagnostics are necessary, but persistent protected-framework
or motif damage is the decisive structural failure mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence
import hashlib
import json
import math
import os
import signal
import shutil
import subprocess
import tempfile

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .relax_verify import _edge_map, _angle_map, _periodic_displacements
from .artifact_staging import stage_immutable_artifact

DYN_VERIFY_POLICY_SCHEMA = "mdstats.dyn-verify-policy.v1"
DYN_VERIFY_PLAN_SCHEMA = "mdstats.dyn-verify-plan.v1"
DYN_VERIFY_CASE_SCHEMA = "mdstats.dyn-verify-case-metric.v1"
DYN_CASE_COMPLETION_SCHEMA = "mdstats.dyn-case-completion.v1"
DYN_VERIFY_RUN_SCHEMA = "mdstats.dyn-verify-run.v1"
DYN_VERIFY_CAMPAIGN_SCHEMA = "mdstats.dyn-verify-campaign.v1"
DYN_VERIFY_IMPLEMENTATION_VERSION = "mdstats.dyn-verify2.2026-08.v1"


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite_nonnegative(value: float, *, name: str) -> float:
    x = float(value)
    if not math.isfinite(x) or x < 0.0:
        raise TrainingDataInputError(f"DYN-VERIFY2 {name} must be finite and non-negative.")
    return x


@dataclass(frozen=True, slots=True)
class DynVerifyPolicy:
    maximum_base_configurations: int = 2
    temperatures_kelvin: tuple[float, ...] = (300.0, 800.0)
    timestep_fs: float = 0.5
    nvt_steps: int = 400
    nvt_damping_fs: float = 100.0
    nve_steps: int = 2000
    sample_interval_steps: int = 10
    velocity_seed_base: int = 314159
    maximum_energy_drift_ev_per_atom_per_ps: float = 0.026
    minimum_pair_distance_angstrom: float = 0.8
    maximum_force_ev_per_angstrom: float = 100.0
    nvt_mean_temperature_relative_tolerance: float = 0.20
    nve_mean_temperature_relative_tolerance: float = 0.30
    topology_cutoff_scale: float = 1.20
    reference_bond_break_ratio: float = 1.35
    new_bond_cutoff_scale: float = 1.10
    persistent_damage_samples: int = 10
    protected_rms_displacement_tolerance_angstrom: float = 0.60
    protected_max_displacement_tolerance_angstrom: float = 1.50
    protected_bond_rmse_tolerance_angstrom: float = 0.15
    protected_angle_rmse_tolerance_degrees: float = 15.0
    require_all_cases: bool = True
    implementation_version: str = DYN_VERIFY_IMPLEMENTATION_VERSION
    serialization_schema: str = field(default=DYN_VERIFY_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_VERIFY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN-VERIFY2 policy schema.")
        object.__setattr__(self, "maximum_base_configurations", int(self.maximum_base_configurations))
        object.__setattr__(self, "nvt_steps", int(self.nvt_steps))
        object.__setattr__(self, "nve_steps", int(self.nve_steps))
        object.__setattr__(self, "sample_interval_steps", int(self.sample_interval_steps))
        object.__setattr__(self, "persistent_damage_samples", int(self.persistent_damage_samples))
        object.__setattr__(self, "velocity_seed_base", int(self.velocity_seed_base))
        if self.maximum_base_configurations <= 0 or self.nvt_steps <= 0 or self.nve_steps <= 0 or self.sample_interval_steps <= 0:
            raise TrainingDataInputError("DYN-VERIFY2 base/step counts must be positive.")
        if self.persistent_damage_samples <= 0:
            raise TrainingDataInputError("DYN-VERIFY2 persistence window must be positive.")
        if self.velocity_seed_base <= 0:
            raise TrainingDataInputError("DYN-VERIFY2 velocity seed must be positive.")
        temps = tuple(float(v) for v in self.temperatures_kelvin)
        if not temps or len(set(temps)) != len(temps) or any(not math.isfinite(v) or v <= 0.0 for v in temps):
            raise TrainingDataInputError("DYN-VERIFY2 temperatures must be unique positive finite values.")
        object.__setattr__(self, "temperatures_kelvin", temps)
        for name in (
            "timestep_fs", "nvt_damping_fs", "maximum_energy_drift_ev_per_atom_per_ps",
            "minimum_pair_distance_angstrom", "maximum_force_ev_per_angstrom",
            "nvt_mean_temperature_relative_tolerance", "nve_mean_temperature_relative_tolerance",
            "topology_cutoff_scale", "reference_bond_break_ratio", "new_bond_cutoff_scale",
            "protected_rms_displacement_tolerance_angstrom", "protected_max_displacement_tolerance_angstrom",
            "protected_bond_rmse_tolerance_angstrom", "protected_angle_rmse_tolerance_degrees",
        ):
            value = _finite_nonnegative(getattr(self, name), name=name)
            if value == 0.0 and name not in {"nvt_mean_temperature_relative_tolerance", "nve_mean_temperature_relative_tolerance"}:
                raise TrainingDataInputError(f"DYN-VERIFY2 {name} must be positive.")
            object.__setattr__(self, name, value)
        if self.new_bond_cutoff_scale >= self.topology_cutoff_scale:
            raise TrainingDataInputError("DYN-VERIFY2 new-bond cutoff must be tighter than the frozen reference topology cutoff.")
        if self.reference_bond_break_ratio <= 1.0:
            raise TrainingDataInputError("DYN-VERIFY2 reference-bond break ratio must exceed one.")

    def _payload(self) -> dict[str, Any]:
        result = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "serialization_schema"}
        result["schema"] = self.serialization_schema
        result["temperatures_kelvin"] = list(self.temperatures_kelvin)
        return result

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynVerifyPolicy":
        if payload.get("schema") != DYN_VERIFY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DYN-VERIFY2 policy schema.")
        kwargs = {name: payload[name] for name in cls.__dataclass_fields__ if name != "serialization_schema" and name in payload}
        kwargs["temperatures_kelvin"] = tuple(float(v) for v in payload["temperatures_kelvin"])
        result = cls(**kwargs)
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("DYN-VERIFY2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DynVerifyPlan:
    relax_verify_campaign_digest: str
    relax_reference_digest: str
    relax_reference_sha256: str
    policy_digest: str
    base_frame_uids: tuple[str, ...]
    base_reference_indices: tuple[int, ...]
    topology_atom_indices_by_base: tuple[tuple[int, ...], ...]
    temperatures_kelvin: tuple[float, ...]
    case_velocity_seeds: tuple[int, ...]
    selection_method: str = "relax_reference_prefix_correlation_balanced_v1"
    serialization_schema: str = field(default=DYN_VERIFY_PLAN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_VERIFY_PLAN_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN-VERIFY2 plan schema.")
        for name in ("relax_verify_campaign_digest", "relax_reference_digest", "relax_reference_sha256", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        uids = tuple(validate_digest(v, name="base_frame_uid") for v in self.base_frame_uids)
        indices = tuple(int(v) for v in self.base_reference_indices)
        groups = tuple(tuple(int(i) for i in g) for g in self.topology_atom_indices_by_base)
        temps = tuple(float(v) for v in self.temperatures_kelvin)
        seeds = tuple(int(v) for v in self.case_velocity_seeds)
        if not uids or len(uids) != len(indices) or len(uids) != len(groups):
            raise TrainingDataInputError("DYN-VERIFY2 base plan inventory is inconsistent.")
        if len(seeds) != len(uids) * len(temps) or any(v <= 0 for v in seeds):
            raise TrainingDataInputError("DYN-VERIFY2 case seed inventory is inconsistent.")
        object.__setattr__(self, "base_frame_uids", uids)
        object.__setattr__(self, "base_reference_indices", indices)
        object.__setattr__(self, "topology_atom_indices_by_base", groups)
        object.__setattr__(self, "temperatures_kelvin", temps)
        object.__setattr__(self, "case_velocity_seeds", seeds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema, "relax_verify_campaign_digest": self.relax_verify_campaign_digest,
            "relax_reference_digest": self.relax_reference_digest, "relax_reference_sha256": self.relax_reference_sha256,
            "policy_digest": self.policy_digest, "base_frame_uids": list(self.base_frame_uids),
            "base_reference_indices": list(self.base_reference_indices),
            "topology_atom_indices_by_base": [list(v) for v in self.topology_atom_indices_by_base],
            "temperatures_kelvin": list(self.temperatures_kelvin), "case_velocity_seeds": list(self.case_velocity_seeds),
            "selection_method": self.selection_method,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynVerifyPlan":
        result = cls(
            relax_verify_campaign_digest=str(payload["relax_verify_campaign_digest"]),
            relax_reference_digest=str(payload["relax_reference_digest"]), relax_reference_sha256=str(payload["relax_reference_sha256"]),
            policy_digest=str(payload["policy_digest"]), base_frame_uids=tuple(str(v) for v in payload["base_frame_uids"]),
            base_reference_indices=tuple(int(v) for v in payload["base_reference_indices"]),
            topology_atom_indices_by_base=tuple(tuple(int(i) for i in g) for g in payload["topology_atom_indices_by_base"]),
            temperatures_kelvin=tuple(float(v) for v in payload["temperatures_kelvin"]),
            case_velocity_seeds=tuple(int(v) for v in payload["case_velocity_seeds"]),
            selection_method=str(payload.get("selection_method", "relax_reference_prefix_correlation_balanced_v1")),
        )
        if payload.get("schema") != DYN_VERIFY_PLAN_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DYN-VERIFY2 plan record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class DynCaseMetric:
    base_frame_uid: str
    temperature_kelvin: float
    velocity_seed: int
    sample_count: int
    nvt_mean_temperature_kelvin: float
    nve_mean_temperature_kelvin: float
    absolute_energy_drift_ev_per_atom_per_ps: float
    minimum_pair_distance_angstrom: float
    maximum_force_ev_per_angstrom: float
    maximum_protected_rms_displacement_angstrom: float
    maximum_protected_displacement_angstrom: float
    maximum_protected_bond_rmse_angstrom: float
    maximum_protected_angle_rmse_degrees: float
    damaged_sample_count: int
    maximum_consecutive_damage_samples: int
    persistent_structural_damage: bool
    finite: bool
    passed: bool
    failure_reasons: tuple[str, ...] = ()
    trajectory_path: str = ""
    trajectory_sha256: str = ""
    log_sha256: str = ""
    serialization_schema: str = field(default=DYN_VERIFY_CASE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_VERIFY_CASE_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN-VERIFY2 case metric schema.")
        object.__setattr__(self, "base_frame_uid", validate_digest(self.base_frame_uid, name="base_frame_uid"))
        object.__setattr__(self, "temperature_kelvin", float(self.temperature_kelvin))
        object.__setattr__(self, "velocity_seed", int(self.velocity_seed))
        object.__setattr__(self, "sample_count", int(self.sample_count))
        object.__setattr__(self, "damaged_sample_count", int(self.damaged_sample_count))
        object.__setattr__(self, "maximum_consecutive_damage_samples", int(self.maximum_consecutive_damage_samples))
        for name in (
            "nvt_mean_temperature_kelvin", "nve_mean_temperature_kelvin", "absolute_energy_drift_ev_per_atom_per_ps",
            "minimum_pair_distance_angstrom", "maximum_force_ev_per_angstrom", "maximum_protected_rms_displacement_angstrom",
            "maximum_protected_displacement_angstrom", "maximum_protected_bond_rmse_angstrom", "maximum_protected_angle_rmse_degrees",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))
        if self.trajectory_sha256:
            object.__setattr__(self, "trajectory_sha256", validate_digest(self.trajectory_sha256, name="trajectory_sha256"))
        if self.log_sha256:
            object.__setattr__(self, "log_sha256", validate_digest(self.log_sha256, name="log_sha256"))

    def _payload(self) -> dict[str, Any]:
        result = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "serialization_schema"}
        result["schema"] = self.serialization_schema
        result["failure_reasons"] = list(self.failure_reasons)
        return result

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynCaseMetric":
        kwargs = {name: payload[name] for name in cls.__dataclass_fields__ if name != "serialization_schema" and name in payload}
        kwargs["failure_reasons"] = tuple(str(v) for v in payload.get("failure_reasons", ()))
        result = cls(**kwargs)
        if payload.get("schema") != DYN_VERIFY_CASE_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DYN-VERIFY2 case record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class DynCaseCompletionReceipt:
    run_plan_digest: str
    plan_digest: str
    policy_digest: str
    mliap_artifact_sha256: str
    lammps_executable_sha256: str
    lammps_arguments_digest: str
    metric: DynCaseMetric
    serialization_schema: str = field(default=DYN_CASE_COMPLETION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_CASE_COMPLETION_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN case-completion schema.")
        for name in (
            "run_plan_digest", "plan_digest", "policy_digest", "mliap_artifact_sha256",
            "lammps_executable_sha256", "lammps_arguments_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "plan_digest": self.plan_digest,
            "policy_digest": self.policy_digest,
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "lammps_executable_sha256": self.lammps_executable_sha256,
            "lammps_arguments_digest": self.lammps_arguments_digest,
            "metric": self.metric.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynCaseCompletionReceipt":
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            plan_digest=str(payload["plan_digest"]),
            policy_digest=str(payload["policy_digest"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]),
            lammps_executable_sha256=str(payload["lammps_executable_sha256"]),
            lammps_arguments_digest=str(payload["lammps_arguments_digest"]),
            metric=DynCaseMetric.from_dict(payload["metric"]),
        )
        if payload.get("schema") != DYN_CASE_COMPLETION_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DYN case-completion receipt is corrupt.")
        return result


def write_dyn_case_completion_receipt(
    path: str | Path, receipt: DynCaseCompletionReceipt
) -> None:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(receipt.to_dict(), handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def reusable_dyn_case_metric(
    path: str | Path,
    *,
    run_plan_digest: str,
    plan_digest: str,
    policy_digest: str,
    mliap_artifact_sha256: str,
    lammps_executable_sha256: str,
    lammps_arguments_digest: str,
    base_frame_uid: str,
    temperature_kelvin: float,
    velocity_seed: int,
) -> DynCaseMetric | None:
    """Return only a fully authenticated completed case; stale/corrupt means miss."""
    try:
        receipt = DynCaseCompletionReceipt.from_dict(
            json.loads(Path(path).read_text(encoding="utf-8"))
        )
        expected = (
            receipt.run_plan_digest == run_plan_digest,
            receipt.plan_digest == plan_digest,
            receipt.policy_digest == policy_digest,
            receipt.mliap_artifact_sha256 == mliap_artifact_sha256,
            receipt.lammps_executable_sha256 == lammps_executable_sha256,
            receipt.lammps_arguments_digest == lammps_arguments_digest,
            receipt.metric.base_frame_uid == base_frame_uid,
            receipt.metric.temperature_kelvin == float(temperature_kelvin),
            receipt.metric.velocity_seed == int(velocity_seed),
        )
        trajectory = Path(receipt.metric.trajectory_path).resolve()
        if not all(expected) or not trajectory.is_file() or _sha256_file(trajectory) != receipt.metric.trajectory_sha256:
            return None
        log_path = trajectory.parent / "log.lammps"
        if not log_path.is_file() or _sha256_file(log_path) != receipt.metric.log_sha256:
            return None
        return receipt.metric
    except (OSError, ValueError, KeyError, TypeError, TrainingDataInputError, TrainingDataSerializationError):
        return None

@dataclass(frozen=True, slots=True)
class DynVerifyRunRecord:
    run_plan_digest: str
    relax_verify_run_digest: str
    deploy_verify_run_digest: str
    mliap_artifact_path: str
    mliap_artifact_sha256: str
    lammps_executable_path: str
    lammps_executable_sha256: str
    lammps_arguments: tuple[str, ...]
    policy_digest: str
    plan_digest: str
    case_metrics: tuple[DynCaseMetric, ...]
    serialization_schema: str = field(default=DYN_VERIFY_RUN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_VERIFY_RUN_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN-VERIFY2 run schema.")
        for name in ("run_plan_digest", "relax_verify_run_digest", "deploy_verify_run_digest", "mliap_artifact_sha256", "lammps_executable_sha256", "policy_digest", "plan_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        metrics = tuple(sorted(self.case_metrics, key=lambda v: (v.base_frame_uid, v.temperature_kelvin)))
        if not metrics or len({(v.base_frame_uid, v.temperature_kelvin) for v in metrics}) != len(metrics):
            raise TrainingDataInputError("DYN-VERIFY2 run requires unique case metrics.")
        object.__setattr__(self, "case_metrics", metrics)
        object.__setattr__(self, "lammps_arguments", tuple(str(v) for v in self.lammps_arguments))

    @property
    def passed(self) -> bool:
        return all(v.passed for v in self.case_metrics)

    @property
    def failed_case_count(self) -> int:
        return sum(not v.passed for v in self.case_metrics)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema, "run_plan_digest": self.run_plan_digest,
            "relax_verify_run_digest": self.relax_verify_run_digest, "deploy_verify_run_digest": self.deploy_verify_run_digest,
            "mliap_artifact_path": self.mliap_artifact_path, "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "lammps_executable_path": self.lammps_executable_path, "lammps_executable_sha256": self.lammps_executable_sha256,
            "lammps_arguments": list(self.lammps_arguments), "policy_digest": self.policy_digest, "plan_digest": self.plan_digest,
            "case_metrics": [v.to_dict() for v in self.case_metrics], "passed": self.passed, "failed_case_count": self.failed_case_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynVerifyRunRecord":
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]), relax_verify_run_digest=str(payload["relax_verify_run_digest"]),
            deploy_verify_run_digest=str(payload["deploy_verify_run_digest"]), mliap_artifact_path=str(payload["mliap_artifact_path"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]), lammps_executable_path=str(payload["lammps_executable_path"]),
            lammps_executable_sha256=str(payload["lammps_executable_sha256"]), lammps_arguments=tuple(str(v) for v in payload["lammps_arguments"]),
            policy_digest=str(payload["policy_digest"]), plan_digest=str(payload["plan_digest"]),
            case_metrics=tuple(DynCaseMetric.from_dict(v) for v in payload["case_metrics"]),
        )
        if payload.get("schema") != DYN_VERIFY_RUN_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DYN-VERIFY2 run record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class DynVerifyCampaignRecord:
    campaign_plan_digest: str
    relax_verify_campaign_digest: str
    deploy_verify_campaign_digest: str
    policy: DynVerifyPolicy
    plan: DynVerifyPlan
    run_records: tuple[DynVerifyRunRecord, ...]
    stage_context: str
    serialization_schema: str = field(default=DYN_VERIFY_CAMPAIGN_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != DYN_VERIFY_CAMPAIGN_SCHEMA:
            raise TrainingDataInputError("Unsupported DYN-VERIFY2 campaign schema.")
        for name in ("campaign_plan_digest", "relax_verify_campaign_digest", "deploy_verify_campaign_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.plan.policy_digest != self.policy.policy_digest or self.plan.relax_verify_campaign_digest != self.relax_verify_campaign_digest:
            raise TrainingDataInputError("DYN-VERIFY2 campaign policy/plan identity mismatch.")
        records = tuple(sorted(self.run_records, key=lambda v: v.run_plan_digest))
        if not records or len({v.run_plan_digest for v in records}) != len(records):
            raise TrainingDataInputError("DYN-VERIFY2 campaign requires unique run records.")
        if self.stage_context != "production":
            raise TrainingDataInputError("DYN-VERIFY2 is post-selection production verification only.")
        object.__setattr__(self, "run_records", records)

    @property
    def passed_run_count(self) -> int:
        return sum(v.passed for v in self.run_records)

    @property
    def all_candidates_failed(self) -> bool:
        return self.passed_run_count == 0

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema, "campaign_plan_digest": self.campaign_plan_digest,
            "relax_verify_campaign_digest": self.relax_verify_campaign_digest, "deploy_verify_campaign_digest": self.deploy_verify_campaign_digest,
            "policy": self.policy.to_dict(), "plan": self.plan.to_dict(), "run_records": [v.to_dict() for v in self.run_records],
            "stage_context": self.stage_context, "passed_run_count": self.passed_run_count, "all_candidates_failed": self.all_candidates_failed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DynVerifyCampaignRecord":
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]), relax_verify_campaign_digest=str(payload["relax_verify_campaign_digest"]),
            deploy_verify_campaign_digest=str(payload["deploy_verify_campaign_digest"]), policy=DynVerifyPolicy.from_dict(payload["policy"]),
            plan=DynVerifyPlan.from_dict(payload["plan"]), run_records=tuple(DynVerifyRunRecord.from_dict(v) for v in payload["run_records"]),
            stage_context=str(payload["stage_context"]),
        )
        if payload.get("schema") != DYN_VERIFY_CAMPAIGN_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("DYN-VERIFY2 campaign record is corrupt.")
        return result


def _case_seed(base_seed: int, uid: str, temperature: float) -> int:
    token = digest({"schema": "mdstats.dyn-verify-seed.v1", "base_seed": int(base_seed), "uid": uid, "temperature": float(temperature)})
    return 10000 + (int(token[:12], 16) % 899_000_000)


def build_dyn_verify_plan(relax_campaign: Any, *, policy: DynVerifyPolicy) -> DynVerifyPlan:
    """Freeze the common DFT-relaxed rollout bases and deterministic velocity seeds."""
    count = min(int(policy.maximum_base_configurations), len(relax_campaign.base_set.base_frame_uids))
    uids = tuple(relax_campaign.base_set.base_frame_uids[:count])
    indices = tuple(range(count))
    groups = tuple(relax_campaign.base_set.topology_atom_indices_by_base[:count])
    seeds = tuple(_case_seed(policy.velocity_seed_base, uid, temp) for uid in uids for temp in policy.temperatures_kelvin)
    return DynVerifyPlan(
        relax_verify_campaign_digest=relax_campaign.content_digest,
        relax_reference_digest=relax_campaign.reference_artifact.content_digest,
        relax_reference_sha256=relax_campaign.reference_artifact.reference_sha256,
        policy_digest=policy.policy_digest,
        base_frame_uids=uids,
        base_reference_indices=indices,
        topology_atom_indices_by_base=groups,
        temperatures_kelvin=policy.temperatures_kelvin,
        case_velocity_seeds=seeds,
    )


def _minimum_pair_distance(atoms: Any) -> float:
    try:
        from ase.neighborlist import neighbor_list
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for DYN-VERIFY2 structural analysis.") from exc
    values = np.asarray(neighbor_list("d", atoms, cutoff=3.0, self_interaction=False), dtype=float)
    if values.size:
        return float(np.min(values))
    # An unusually expanded configuration can have no pair below the fast 3 A
    # neighbor-list cutoff.  Fall back to the exact periodic all-pairs minimum
    # rather than interpreting that situation as an infinite separation.
    distances = np.asarray(atoms.get_all_distances(mic=True), dtype=float)
    if distances.shape[0] < 2:
        raise TrainingDataInputError("DYN-VERIFY2 minimum-distance analysis requires at least two atoms.")
    upper = distances[np.triu_indices(distances.shape[0], k=1)]
    return float(np.min(upper))


def _max_force(atoms: Any) -> tuple[float, bool]:
    try:
        forces = np.asarray(atoms.get_forces(), dtype=float)
    except Exception:
        return 0.0, False
    if not forces.size or not np.all(np.isfinite(forces)):
        return 0.0, False
    return float(np.max(np.linalg.norm(forces, axis=1))), True


def _max_consecutive(flags: Sequence[bool]) -> int:
    best = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def assess_dyn_trajectory(
    reference: Any,
    frames: Iterable[Any],
    thermo_rows: Sequence[Sequence[float]],
    *,
    base_frame_uid: str,
    topology_atom_indices: Sequence[int],
    temperature_kelvin: float,
    velocity_seed: int,
    policy: DynVerifyPolicy,
    trajectory_path: str = "",
    trajectory_sha256: str = "",
    log_sha256: str = "",
) -> DynCaseMetric:
    """Reduce one common short rollout into numerical and persistent-structure gates."""
    rows = np.asarray(tuple(tuple(float(x) for x in row) for row in thermo_rows), dtype=float)
    if rows.ndim != 2 or rows.shape[1] < 5:
        raise TrainingDataInputError("DYN-VERIFY2 trajectory/thermo evidence is empty or malformed.")
    selected = tuple(int(v) for v in topology_atom_indices)
    ref_edges = _edge_map(reference, selected, policy.topology_cutoff_scale)
    if not ref_edges:
        raise TrainingDataInputError("DYN-VERIFY2 protected topology resolved to no reference bonds.")
    ref_angles = _angle_map(reference, ref_edges)
    sample_count = damaged_count = consecutive_damage = maximum_consecutive = 0
    maximum_rms = maximum_displacement = maximum_bond_rmse = maximum_angle_rmse = 0.0
    minimum_distance = float("inf")
    maximum_force = 0.0
    finite = bool(np.all(np.isfinite(rows)))

    ref_keys = tuple(sorted(ref_edges))
    ref_pairs = np.asarray(ref_keys, dtype=np.int64)
    for atoms in frames:
        if sample_count == 0 and tuple(int(v) for v in reference.numbers) != tuple(int(v) for v in atoms.numbers):
            raise TrainingDataInputError("DYN-VERIFY2 reference and trajectory atom identities disagree.")
        sample_count += 1
        finite = finite and bool(np.all(np.isfinite(np.asarray(atoms.positions, dtype=float))))
        minimum_distance = min(minimum_distance, _minimum_pair_distance(atoms))
        max_force, force_valid = _max_force(atoms)
        maximum_force = max(maximum_force, max_force)
        finite = finite and force_valid
        disp = _periodic_displacements(reference, atoms, selected)
        norms = np.linalg.norm(disp, axis=1) if len(disp) else np.zeros(0)
        rms = float(np.sqrt(np.mean(norms ** 2))) if len(norms) else 0.0
        max_disp = float(np.max(norms)) if len(norms) else 0.0
        maximum_rms = max(maximum_rms, rms)
        maximum_displacement = max(maximum_displacement, max_disp)
        current_distances = np.asarray(
            atoms.get_distances(ref_pairs[:, 0], ref_pairs[:, 1], mic=True), dtype=np.float64
        )
        current_ref_bonds = dict(zip(ref_keys, current_distances.tolist()))
        broken = any(current_ref_bonds[key] > policy.reference_bond_break_ratio * ref_edges[key] for key in ref_edges)
        new_edges = set(_edge_map(atoms, selected, policy.new_bond_cutoff_scale)) - set(ref_edges)
        bond_err = np.asarray([current_ref_bonds[key] - ref_edges[key] for key in sorted(ref_edges)], dtype=float)
        bond_rmse = float(np.sqrt(np.mean(bond_err ** 2))) if bond_err.size else 0.0
        maximum_bond_rmse = max(maximum_bond_rmse, bond_rmse)
        current_angles = _angle_map(atoms, current_ref_bonds)
        common_angles = sorted(set(ref_angles) & set(current_angles))
        angle_err = np.asarray([current_angles[k] - ref_angles[k] for k in common_angles], dtype=float)
        angle_rmse = float(np.sqrt(np.mean(angle_err ** 2))) if angle_err.size else 0.0
        maximum_angle_rmse = max(maximum_angle_rmse, angle_rmse)
        damaged = bool(
            broken or new_edges or rms > policy.protected_rms_displacement_tolerance_angstrom
            or max_disp > policy.protected_max_displacement_tolerance_angstrom
            or bond_rmse > policy.protected_bond_rmse_tolerance_angstrom
            or angle_rmse > policy.protected_angle_rmse_tolerance_degrees
        )
        damaged_count += int(damaged)
        consecutive_damage = consecutive_damage + 1 if damaged else 0
        maximum_consecutive = max(maximum_consecutive, consecutive_damage)

    if sample_count == 0:
        raise TrainingDataInputError("DYN-VERIFY2 trajectory/thermo evidence is empty or malformed.")

    steps = rows[:, 0]
    temps = rows[:, 1]
    etotal = rows[:, 4]
    nvt_mask = (steps >= max(0.0, policy.nvt_steps / 2.0)) & (steps <= policy.nvt_steps)
    nve_mask = steps > policy.nvt_steps
    if not np.any(nvt_mask) or np.count_nonzero(nve_mask) < 2:
        raise TrainingDataInputError("DYN-VERIFY2 thermo stream does not contain both NVT and NVE evidence.")
    nvt_mean = float(np.mean(temps[nvt_mask])); nve_mean = float(np.mean(temps[nve_mask]))
    nve_steps = steps[nve_mask]
    nve_times_ps = (nve_steps - policy.nvt_steps) * policy.timestep_fs / 1000.0
    energy_per_atom = etotal[nve_mask] / max(1, len(reference))
    drift = float(abs(np.polyfit(nve_times_ps, energy_per_atom, 1)[0]))
    persistent = maximum_consecutive >= policy.persistent_damage_samples
    finite = bool(finite and math.isfinite(minimum_distance) and math.isfinite(maximum_force) and bool(np.isfinite(drift)))
    reasons: list[str] = []
    if not finite:
        reasons.append("nonfinite_dynamics")
    if drift > policy.maximum_energy_drift_ev_per_atom_per_ps:
        reasons.append("nve_energy_drift_exceeded")
    if minimum_distance < policy.minimum_pair_distance_angstrom:
        reasons.append("minimum_pair_distance_violated")
    if maximum_force > policy.maximum_force_ev_per_angstrom:
        reasons.append("maximum_force_exceeded")
    if abs(nvt_mean - temperature_kelvin) / temperature_kelvin > policy.nvt_mean_temperature_relative_tolerance:
        reasons.append("nvt_temperature_out_of_range")
    if abs(nve_mean - temperature_kelvin) / temperature_kelvin > policy.nve_mean_temperature_relative_tolerance:
        reasons.append("nve_temperature_out_of_range")
    if persistent:
        reasons.append("persistent_structural_damage")
    return DynCaseMetric(
        base_frame_uid=base_frame_uid, temperature_kelvin=temperature_kelvin, velocity_seed=velocity_seed,
        sample_count=sample_count, nvt_mean_temperature_kelvin=nvt_mean, nve_mean_temperature_kelvin=nve_mean,
        absolute_energy_drift_ev_per_atom_per_ps=drift, minimum_pair_distance_angstrom=minimum_distance,
        maximum_force_ev_per_angstrom=maximum_force,
        maximum_protected_rms_displacement_angstrom=maximum_rms,
        maximum_protected_displacement_angstrom=maximum_displacement,
        maximum_protected_bond_rmse_angstrom=maximum_bond_rmse,
        maximum_protected_angle_rmse_degrees=maximum_angle_rmse,
        damaged_sample_count=damaged_count, maximum_consecutive_damage_samples=maximum_consecutive,
        persistent_structural_damage=persistent, finite=finite, passed=not reasons, failure_reasons=tuple(reasons),
        trajectory_path=str(trajectory_path), trajectory_sha256=str(trajectory_sha256), log_sha256=str(log_sha256),
    )


def _parse_thermo_log(path: Path) -> tuple[tuple[float, ...], ...]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: list[tuple[float, ...]] = []
    active = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Step ") and "Temp" in stripped and "TotEng" in stripped:
            active = True
            continue
        if not active:
            continue
        fields = stripped.split()
        if len(fields) < 5:
            if rows and (stripped.startswith("Loop time") or stripped.startswith("WARNING") or stripped.startswith("Performance")):
                active = False
            continue
        try:
            row = tuple(float(v) for v in fields[:5])
        except ValueError:
            continue
        rows.append(row)
    if not rows:
        raise TrainingDataInputError("DYN-VERIFY2 LAMMPS log contains no thermo rows.")
    # Consecutive run commands may repeat the boundary row; deduplicate by step, keeping the last value.
    by_step: dict[int, tuple[float, ...]] = {int(row[0]): row for row in rows}
    return tuple(by_step[key] for key in sorted(by_step))


def _iter_deduplicated_lammps_frames(
    path: Path, *, elements: Sequence[str]
) -> Iterator[Any]:
    """Stream normal ordered dumps; retain the exact sorted/last-wins fallback."""
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for DYN-VERIFY2 trajectory streaming.") from exc

    previous_step: int | None = None
    out_of_order = False
    for index, atoms in enumerate(
        iread(path, index=":", format="lammps-dump-text", specorder=list(elements))
    ):
        step = int(atoms.info.get("timestep", index))
        if previous_step is not None and step < previous_step:
            out_of_order = True
            break
        previous_step = step
    if out_of_order:
        # Noncanonical external dumps retain the historical sorted, last-wins
        # semantics. LAMMPS-produced evidence takes the bounded path below.
        by_step: dict[int, Any] = {}
        for index, atoms in enumerate(
            iread(path, index=":", format="lammps-dump-text", specorder=list(elements))
        ):
            by_step[int(atoms.info.get("timestep", index))] = atoms
        for step in sorted(by_step):
            yield by_step[step]
        return

    pending: Any | None = None
    pending_step: int | None = None
    for index, atoms in enumerate(
        iread(path, index=":", format="lammps-dump-text", specorder=list(elements))
    ):
        step = int(atoms.info.get("timestep", index))
        if pending is not None and step != pending_step:
            yield pending
        pending = atoms
        pending_step = step
    if pending is not None:
        yield pending


def _file_tail(path: Path, maximum_bytes: int = 5000) -> str:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - int(maximum_bytes)))
        return handle.read().decode("utf-8", errors="replace")


def _run_file_backed_process(
    command: Sequence[str], *, cwd: Path, environment: Mapping[str, str],
    stdout_path: Path, stderr_path: Path, timeout_seconds: float,
) -> subprocess.CompletedProcess[Any]:
    """Run one external case in a cancellable process group with bounded RAM."""
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            list(command), cwd=cwd, env=dict(environment), stdout=stdout_handle,
            stderr=stderr_handle, text=True, start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=float(timeout_seconds))
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                process.wait()
            raise
    return subprocess.CompletedProcess(list(command), returncode)


def run_lammps_mliap_dynamics_case(
    mliap_artifact_path: str | Path,
    reference_atoms: Any,
    *,
    base_frame_uid: str,
    topology_atom_indices: Sequence[int],
    temperature_kelvin: float,
    velocity_seed: int,
    element_order: Sequence[str],
    policy: DynVerifyPolicy,
    lammps_executable: str | Path,
    lammps_arguments: Sequence[str] = (),
    work_directory: str | Path,
    timeout_seconds: float = 3600.0,
    expected_executable_sha256: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> DynCaseMetric:
    """Run one NVT→NVE ML-IAP/LAMMPS case and reduce it to DYN-VERIFY2 evidence."""
    try:
        from ase.io import write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for DYN-VERIFY2 LAMMPS dynamics.") from exc
    executable_text = str(lammps_executable)
    executable = Path(executable_text).expanduser()
    if not executable.is_file():
        resolved = shutil.which(executable_text)
        if resolved is None:
            raise TrainingDataInputError(f"DYN-VERIFY2 LAMMPS executable is unavailable: {executable_text!r}.")
        executable = Path(resolved)
    executable = executable.resolve()
    exe_sha = _sha256_file(executable)
    if expected_executable_sha256 is not None and exe_sha != validate_digest(expected_executable_sha256, name="expected_executable_sha256"):
        raise TrainingDataInputError("DYN-VERIFY2 LAMMPS executable bytes changed after DEPLOY-VERIFY1.")
    mliap = Path(mliap_artifact_path).resolve()
    if not mliap.is_file():
        raise TrainingDataInputError("DYN-VERIFY2 ML-IAP artifact is missing.")
    root = Path(work_directory).resolve(); root.mkdir(parents=True, exist_ok=True)
    local_model = root / "deployment-mliap.pt"
    stage_immutable_artifact(mliap, local_model)
    data_path = root / "structure.data"
    elements = tuple(str(v) for v in element_order)
    write(data_path, reference_atoms, format="lammps-data", atom_style="atomic", specorder=list(elements), masses=True)
    boundary = " ".join("p" if bool(v) else "f" for v in reference_atoms.pbc)
    dt_ps = policy.timestep_fs / 1000.0
    damp_ps = policy.nvt_damping_fs / 1000.0
    trajectory = root / "trajectory.dump"; log_path = root / "log.lammps"
    input_text = "\n".join([
        "units metal", "atom_style atomic", f"boundary {boundary}", "newton on", "atom_modify map yes",
        "read_data structure.data", "pair_style mliap unified deployment-mliap.pt 0", "pair_coeff * * " + " ".join(elements),
        f"timestep {dt_ps:.12g}", f"thermo {policy.sample_interval_steps}", "thermo_style custom step temp pe ke etotal",
        f"dump dyndump all custom {policy.sample_interval_steps} trajectory.dump id type x y z fx fy fz", "dump_modify dyndump sort id",
        # Guarantee that trajectory frame zero is the exact common DFT-relaxed start before velocities/integration.
        "run 0",
        f"velocity all create {float(temperature_kelvin):.12g} {int(velocity_seed)} mom yes rot yes dist gaussian",
        "fix dynint all nve", f"fix dynbath all langevin {float(temperature_kelvin):.12g} {float(temperature_kelvin):.12g} {damp_ps:.12g} {int(velocity_seed)+1} zero yes",
        f"run {policy.nvt_steps}", "unfix dynbath", f"run {policy.nve_steps}", "",
    ])
    input_path = root / "dyn.in"; input_path.write_text(input_text, encoding="utf-8")
    merged_env = dict(os.environ)
    if environment is not None:
        merged_env.update({str(k): str(v) for k, v in environment.items()})
    command = [str(executable), *[str(v) for v in lammps_arguments], "-log", str(log_path.name), "-in", str(input_path.name)]
    stdout_path = root / "lammps.stdout.log"
    stderr_path = root / "lammps.stderr.log"
    completed = _run_file_backed_process(
        command, cwd=root, environment=merged_env, stdout_path=stdout_path,
        stderr_path=stderr_path, timeout_seconds=float(timeout_seconds),
    )
    if completed.returncode != 0:
        tail = _file_tail(stderr_path) or _file_tail(stdout_path)
        raise TrainingDataInputError(f"DYN-VERIFY2 LAMMPS dynamics failed. Last output:\n{tail}")
    if not trajectory.is_file() or not log_path.is_file():
        raise TrainingDataInputError("DYN-VERIFY2 LAMMPS run did not create trajectory/log evidence.")
    frames = _iter_deduplicated_lammps_frames(trajectory, elements=elements)
    try:
        first_frame = next(frames)
    except StopIteration as exc:
        raise TrainingDataInputError("DYN-VERIFY2 LAMMPS trajectory is empty.") from exc
    from itertools import chain
    thermo = _parse_thermo_log(log_path)
    return assess_dyn_trajectory(
        first_frame, chain((first_frame,), frames), thermo,
        base_frame_uid=base_frame_uid, topology_atom_indices=topology_atom_indices,
        temperature_kelvin=temperature_kelvin, velocity_seed=velocity_seed, policy=policy,
        trajectory_path=str(trajectory), trajectory_sha256=_sha256_file(trajectory), log_sha256=_sha256_file(log_path),
    )


__all__ = [
    "DYN_VERIFY_IMPLEMENTATION_VERSION", "DynVerifyPolicy", "DynVerifyPlan", "DynCaseMetric",
    "DynCaseCompletionReceipt", "write_dyn_case_completion_receipt", "reusable_dyn_case_metric",
    "DynVerifyRunRecord", "DynVerifyCampaignRecord", "build_dyn_verify_plan", "assess_dyn_trajectory",
    "run_lammps_mliap_dynamics_case",
]
