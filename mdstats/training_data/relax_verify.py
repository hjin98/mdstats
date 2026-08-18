"""RELAX-VERIFY1 zero-K topology and geometry qualification for TRAIN2 candidates.

The gate consumes the candidate-independent PES-VERIFY1 base structures, requests
matched fixed-cell DFT ionic relaxations, and compares each PES-qualified target-
only model against those common references.  Topology preservation is a hard
safety condition; quantitative geometry fidelity is a separate accuracy gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .mace_compatibility import mace_runtime_warning_handled

RELAX_VERIFY_POLICY_SCHEMA = "mdstats.relax-verify-policy.v1"
RELAX_BASE_SET_SCHEMA = "mdstats.relax-verify-base-set.v1"
RELAX_REQUEST_SCHEMA = "mdstats.relax-verify-request.v1"
RELAX_REFERENCE_SCHEMA = "mdstats.relax-verify-reference.v1"
RELAX_BASE_METRIC_SCHEMA = "mdstats.relax-verify-base-metric.v1"
RELAX_MODEL_QUALIFICATION_SCHEMA = "mdstats.relax-model-qualification.v1"
RELAX_RUN_RECORD_SCHEMA = "mdstats.relax-verify-run.v1"
RELAX_CAMPAIGN_RECORD_SCHEMA = "mdstats.relax-verify-campaign.v1"
RELAX_VERIFY_IMPLEMENTATION_VERSION = "mdstats.relax-verify1.2026-08.v1"


def _sha256_file(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and non-negative.")
    return result


def _geometry_digest(atoms: Any) -> str:
    numbers = tuple(int(v) for v in np.asarray(atoms.numbers, dtype=int).tolist())
    cell = np.round(np.asarray(atoms.cell.array, dtype=np.float64), 8)
    scaled = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=np.float64)
    scaled = np.mod(scaled, 1.0)
    scaled = np.round(scaled, 8)
    return digest({
        "schema": "mdstats.relax-geometry-identity.v1",
        "atomic_numbers": list(numbers),
        "cell_angstrom": cell.tolist(),
        "scaled_positions": scaled.tolist(),
        "pbc": [bool(v) for v in atoms.pbc],
    })


def _copy_without_calculator(atoms: Any) -> Any:
    result = atoms.copy()
    result.calc = None
    return result


@dataclass(frozen=True, slots=True)
class RelaxVerifyPolicy:
    maximum_base_configurations: int = 4
    optimizer: str = "FIRE"
    force_convergence_ev_per_angstrom: float = 0.03
    maximum_steps: int = 500
    fixed_cell: bool = True
    topology_group_ids: tuple[str, ...] = ()
    topology_cutoff_scale: float = 1.20
    rms_displacement_tolerance_angstrom: float = 0.15
    max_displacement_tolerance_angstrom: float = 0.40
    bond_rmse_tolerance_angstrom: float = 0.08
    bond_max_error_tolerance_angstrom: float = 0.20
    angle_rmse_tolerance_degrees: float = 8.0
    angle_max_error_tolerance_degrees: float = 20.0
    cell_strain_tolerance: float = 1.0e-4
    reference_geometry_tolerance_angstrom: float = 1.0e-6
    require_exact_topology: bool = True
    implementation_version: str = RELAX_VERIFY_IMPLEMENTATION_VERSION
    serialization_schema: str = field(default=RELAX_VERIFY_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_VERIFY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 policy schema.")
        count = int(self.maximum_base_configurations)
        steps = int(self.maximum_steps)
        if count <= 0 or steps <= 0:
            raise TrainingDataInputError("RELAX-VERIFY1 base count and maximum steps must be positive.")
        object.__setattr__(self, "maximum_base_configurations", count)
        object.__setattr__(self, "maximum_steps", steps)
        if str(self.optimizer).upper() != "FIRE":
            raise TrainingDataInputError("RELAX-VERIFY1 v1 supports only the deterministic FIRE optimizer contract.")
        object.__setattr__(self, "optimizer", "FIRE")
        groups = tuple(str(v).strip() for v in self.topology_group_ids if str(v).strip())
        if len(set(groups)) != len(groups):
            raise TrainingDataInputError("RELAX-VERIFY1 topology group IDs must be unique.")
        object.__setattr__(self, "topology_group_ids", groups)
        for name in (
            "force_convergence_ev_per_angstrom", "topology_cutoff_scale",
            "rms_displacement_tolerance_angstrom", "max_displacement_tolerance_angstrom",
            "bond_rmse_tolerance_angstrom", "bond_max_error_tolerance_angstrom",
            "angle_rmse_tolerance_degrees", "angle_max_error_tolerance_degrees",
            "cell_strain_tolerance", "reference_geometry_tolerance_angstrom",
        ):
            value = _finite_nonnegative(getattr(self, name), name=name)
            if name == "topology_cutoff_scale" and value <= 0.0:
                raise TrainingDataInputError("RELAX-VERIFY1 topology cutoff scale must be positive.")
            object.__setattr__(self, name, value)
        if self.force_convergence_ev_per_angstrom <= 0.0:
            raise TrainingDataInputError("RELAX-VERIFY1 force convergence threshold must be positive.")
        if not self.fixed_cell:
            raise TrainingDataInputError("RELAX-VERIFY1 v1 requires fixed-cell relaxation; variable-cell support is deferred.")
        if not self.require_exact_topology:
            raise TrainingDataInputError("RELAX-VERIFY1 v1 requires exact preserved-group connectivity.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "maximum_base_configurations": self.maximum_base_configurations,
            "optimizer": self.optimizer,
            "force_convergence_ev_per_angstrom": self.force_convergence_ev_per_angstrom,
            "maximum_steps": self.maximum_steps,
            "fixed_cell": bool(self.fixed_cell),
            "topology_group_ids": list(self.topology_group_ids),
            "topology_cutoff_scale": self.topology_cutoff_scale,
            "rms_displacement_tolerance_angstrom": self.rms_displacement_tolerance_angstrom,
            "max_displacement_tolerance_angstrom": self.max_displacement_tolerance_angstrom,
            "bond_rmse_tolerance_angstrom": self.bond_rmse_tolerance_angstrom,
            "bond_max_error_tolerance_angstrom": self.bond_max_error_tolerance_angstrom,
            "angle_rmse_tolerance_degrees": self.angle_rmse_tolerance_degrees,
            "angle_max_error_tolerance_degrees": self.angle_max_error_tolerance_degrees,
            "cell_strain_tolerance": self.cell_strain_tolerance,
            "reference_geometry_tolerance_angstrom": self.reference_geometry_tolerance_angstrom,
            "require_exact_topology": bool(self.require_exact_topology),
            "implementation_version": self.implementation_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxVerifyPolicy":
        if payload.get("schema") != RELAX_VERIFY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported RELAX-VERIFY1 policy schema.")
        kwargs = {name: payload[name] for name in cls.__dataclass_fields__ if name != "serialization_schema" and name in payload}
        if "topology_group_ids" in kwargs:
            kwargs["topology_group_ids"] = tuple(str(v) for v in kwargs["topology_group_ids"])
        result = cls(**kwargs)
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxBaseSet:
    pes_probe_set_digest: str
    target_role_digest: str
    target_artifact_digest: str
    target_artifact_sha256: str
    policy_digest: str
    base_frame_uids: tuple[str, ...]
    base_configuration_indices: tuple[int, ...]
    base_geometry_digests: tuple[str, ...]
    topology_atom_indices_by_base: tuple[tuple[int, ...], ...]
    selection_method: str = "pes_verify1_common_bases_v1"
    serialization_schema: str = field(default=RELAX_BASE_SET_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_BASE_SET_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 base-set schema.")
        for name in ("pes_probe_set_digest", "target_role_digest", "target_artifact_digest", "target_artifact_sha256", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        uids = tuple(validate_digest(v, name="base_frame_uid") for v in self.base_frame_uids)
        indices = tuple(int(v) for v in self.base_configuration_indices)
        geoms = tuple(validate_digest(v, name="base_geometry_digest") for v in self.base_geometry_digests)
        groups = tuple(tuple(int(i) for i in values) for values in self.topology_atom_indices_by_base)
        if not uids or not (len(uids) == len(indices) == len(geoms) == len(groups)):
            raise TrainingDataInputError("RELAX-VERIFY1 base-set inventories disagree.")
        if len(set(uids)) != len(uids) or any(i < 0 for i in indices):
            raise TrainingDataInputError("RELAX-VERIFY1 base identities are invalid.")
        if any(not values or len(set(values)) != len(values) or any(i < 0 for i in values) for values in groups):
            raise TrainingDataInputError("RELAX-VERIFY1 preserved topology groups must contain unique atoms.")
        object.__setattr__(self, "base_frame_uids", uids)
        object.__setattr__(self, "base_configuration_indices", indices)
        object.__setattr__(self, "base_geometry_digests", geoms)
        object.__setattr__(self, "topology_atom_indices_by_base", groups)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "pes_probe_set_digest": self.pes_probe_set_digest,
            "target_role_digest": self.target_role_digest,
            "target_artifact_digest": self.target_artifact_digest,
            "target_artifact_sha256": self.target_artifact_sha256,
            "policy_digest": self.policy_digest,
            "base_frame_uids": list(self.base_frame_uids),
            "base_configuration_indices": list(self.base_configuration_indices),
            "base_geometry_digests": list(self.base_geometry_digests),
            "topology_atom_indices_by_base": [list(v) for v in self.topology_atom_indices_by_base],
            "selection_method": self.selection_method,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxBaseSet":
        result = cls(
            pes_probe_set_digest=str(payload["pes_probe_set_digest"]),
            target_role_digest=str(payload["target_role_digest"]),
            target_artifact_digest=str(payload["target_artifact_digest"]),
            target_artifact_sha256=str(payload["target_artifact_sha256"]),
            policy_digest=str(payload["policy_digest"]),
            base_frame_uids=tuple(str(v) for v in payload["base_frame_uids"]),
            base_configuration_indices=tuple(int(v) for v in payload["base_configuration_indices"]),
            base_geometry_digests=tuple(str(v) for v in payload["base_geometry_digests"]),
            topology_atom_indices_by_base=tuple(tuple(int(i) for i in v) for v in payload["topology_atom_indices_by_base"]),
            selection_method=str(payload.get("selection_method", "pes_verify1_common_bases_v1")),
        )
        if payload.get("schema") != RELAX_BASE_SET_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 base-set record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxRequestArtifact:
    base_set_digest: str
    extxyz_path: str
    extxyz_sha256: str
    manifest_path: str
    manifest_sha256: str
    configuration_count: int
    poscar_sha256s: tuple[tuple[str, str], ...]
    serialization_schema: str = field(default=RELAX_REQUEST_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_REQUEST_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 request schema.")
        for name in ("base_set_digest", "extxyz_sha256", "manifest_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        count = int(self.configuration_count)
        values = tuple((str(p), validate_digest(s, name="poscar_sha256")) for p, s in self.poscar_sha256s)
        if count <= 0 or len(values) != count:
            raise TrainingDataInputError("RELAX-VERIFY1 request inventory is inconsistent.")
        object.__setattr__(self, "configuration_count", count)
        object.__setattr__(self, "poscar_sha256s", values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "base_set_digest": self.base_set_digest,
            "extxyz_path": self.extxyz_path,
            "extxyz_sha256": self.extxyz_sha256,
            "manifest_path": self.manifest_path,
            "manifest_sha256": self.manifest_sha256,
            "configuration_count": self.configuration_count,
            "poscar_sha256s": [{"path": p, "sha256": s} for p, s in self.poscar_sha256s],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxRequestArtifact":
        result = cls(
            base_set_digest=str(payload["base_set_digest"]), extxyz_path=str(payload["extxyz_path"]),
            extxyz_sha256=str(payload["extxyz_sha256"]), manifest_path=str(payload["manifest_path"]),
            manifest_sha256=str(payload["manifest_sha256"]), configuration_count=int(payload["configuration_count"]),
            poscar_sha256s=tuple((str(v["path"]), str(v["sha256"])) for v in payload["poscar_sha256s"]),
        )
        if payload.get("schema") != RELAX_REQUEST_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 request artifact is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxReferenceArtifact:
    base_set_digest: str
    reference_path: str
    reference_sha256: str
    configuration_count: int
    protocol_digest: str
    protocol_source: str
    max_force_ev_per_angstrom: tuple[float, ...]
    source_file_sha256s: tuple[tuple[str, str], ...] = ()
    serialization_schema: str = field(default=RELAX_REFERENCE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_REFERENCE_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 reference schema.")
        for name in ("base_set_digest", "reference_sha256", "protocol_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        count = int(self.configuration_count)
        forces = tuple(_finite_nonnegative(v, name="reference_max_force") for v in self.max_force_ev_per_angstrom)
        if count <= 0 or len(forces) != count or not str(self.protocol_source).strip():
            raise TrainingDataInputError("RELAX-VERIFY1 reference identity is incomplete.")
        object.__setattr__(self, "configuration_count", count)
        object.__setattr__(self, "max_force_ev_per_angstrom", forces)
        object.__setattr__(self, "source_file_sha256s", tuple((str(p), validate_digest(s, name="source_file_sha256")) for p, s in self.source_file_sha256s))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "base_set_digest": self.base_set_digest,
            "reference_path": self.reference_path,
            "reference_sha256": self.reference_sha256,
            "configuration_count": self.configuration_count,
            "protocol_digest": self.protocol_digest,
            "protocol_source": self.protocol_source,
            "max_force_ev_per_angstrom": list(self.max_force_ev_per_angstrom),
            "source_file_sha256s": [{"path": p, "sha256": s} for p, s in self.source_file_sha256s],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxReferenceArtifact":
        result = cls(
            base_set_digest=str(payload["base_set_digest"]), reference_path=str(payload["reference_path"]),
            reference_sha256=str(payload["reference_sha256"]), configuration_count=int(payload["configuration_count"]),
            protocol_digest=str(payload["protocol_digest"]), protocol_source=str(payload["protocol_source"]),
            max_force_ev_per_angstrom=tuple(float(v) for v in payload["max_force_ev_per_angstrom"]),
            source_file_sha256s=tuple((str(v["path"]), str(v["sha256"])) for v in payload.get("source_file_sha256s", ())),
        )
        if payload.get("schema") != RELAX_REFERENCE_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 reference artifact is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxBaseMetric:
    base_frame_uid: str
    topology_passed: bool
    reference_edge_count: int
    candidate_edge_count: int
    missing_edge_count: int
    new_edge_count: int
    coordination_mismatch_count: int
    rms_displacement_angstrom: float
    max_displacement_angstrom: float
    bond_rmse_angstrom: float
    bond_max_error_angstrom: float
    angle_rmse_degrees: float
    angle_max_error_degrees: float
    cell_strain_norm: float
    final_max_force_ev_per_angstrom: float
    optimizer_steps: int
    converged: bool
    energy_drop_ev_per_atom: float | None
    passed: bool
    failure_reasons: tuple[str, ...] = ()
    serialization_schema: str = field(default=RELAX_BASE_METRIC_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_BASE_METRIC_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 base metric schema.")
        object.__setattr__(self, "base_frame_uid", validate_digest(self.base_frame_uid, name="base_frame_uid"))
        for name in ("reference_edge_count", "candidate_edge_count", "missing_edge_count", "new_edge_count", "coordination_mismatch_count", "optimizer_steps"):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError(f"RELAX-VERIFY1 {name} cannot be negative.")
            object.__setattr__(self, name, value)
        for name in ("rms_displacement_angstrom", "max_displacement_angstrom", "bond_rmse_angstrom", "bond_max_error_angstrom", "angle_rmse_degrees", "angle_max_error_degrees", "cell_strain_norm", "final_max_force_ev_per_angstrom"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        if self.energy_drop_ev_per_atom is not None and not math.isfinite(float(self.energy_drop_ev_per_atom)):
            raise TrainingDataInputError("RELAX-VERIFY1 energy-drop diagnostic must be finite when present.")
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))

    def _payload(self) -> dict[str, Any]:
        return {name: (list(getattr(self, name)) if name == "failure_reasons" else getattr(self, name)) for name in self.__dataclass_fields__ if name != "serialization_schema"} | {"schema": self.serialization_schema}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxBaseMetric":
        kwargs = {name: payload[name] for name in cls.__dataclass_fields__ if name != "serialization_schema" and name in payload}
        kwargs["failure_reasons"] = tuple(str(v) for v in payload.get("failure_reasons", ()))
        result = cls(**kwargs)
        if payload.get("schema") != RELAX_BASE_METRIC_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 base metric is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxModelQualification:
    model_sha256: str
    model_role: str
    base_metrics: tuple[RelaxBaseMetric, ...]
    policy_digest: str
    serialization_schema: str = field(default=RELAX_MODEL_QUALIFICATION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_MODEL_QUALIFICATION_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 qualification schema.")
        object.__setattr__(self, "model_sha256", validate_digest(self.model_sha256, name="model_sha256"))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        if self.model_role not in {"candidate", "foundation"}:
            raise TrainingDataInputError("RELAX-VERIFY1 model role is invalid.")
        metrics = tuple(self.base_metrics)
        if not metrics or len({v.base_frame_uid for v in metrics}) != len(metrics):
            raise TrainingDataInputError("RELAX-VERIFY1 qualification requires unique base metrics.")
        object.__setattr__(self, "base_metrics", metrics)

    @property
    def passed(self) -> bool:
        return all(v.passed for v in self.base_metrics)

    @property
    def failed_base_count(self) -> int:
        return sum(not v.passed for v in self.base_metrics)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema, "model_sha256": self.model_sha256, "model_role": self.model_role,
            "base_metrics": [v.to_dict() for v in self.base_metrics], "policy_digest": self.policy_digest,
            "passed": bool(self.passed), "failed_base_count": self.failed_base_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxModelQualification":
        result = cls(
            model_sha256=str(payload["model_sha256"]), model_role=str(payload["model_role"]),
            base_metrics=tuple(RelaxBaseMetric.from_dict(v) for v in payload["base_metrics"]),
            policy_digest=str(payload["policy_digest"]),
        )
        if payload.get("schema") != RELAX_MODEL_QUALIFICATION_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 model qualification is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxVerifyRunRecord:
    run_plan_digest: str
    pes_verify_run_digest: str
    candidate_model_path: str
    candidate_model_sha256: str
    relaxed_artifact_path: str
    relaxed_artifact_sha256: str
    qualification: RelaxModelQualification
    serialization_schema: str = field(default=RELAX_RUN_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_RUN_RECORD_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 run schema.")
        for name in ("run_plan_digest", "pes_verify_run_digest", "candidate_model_sha256", "relaxed_artifact_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.qualification.model_role != "candidate" or self.qualification.model_sha256 != self.candidate_model_sha256:
            raise TrainingDataInputError("RELAX-VERIFY1 candidate qualification identity mismatch.")

    @property
    def passed(self) -> bool:
        return self.qualification.passed

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema, "run_plan_digest": self.run_plan_digest,
            "pes_verify_run_digest": self.pes_verify_run_digest, "candidate_model_path": self.candidate_model_path,
            "candidate_model_sha256": self.candidate_model_sha256, "relaxed_artifact_path": self.relaxed_artifact_path,
            "relaxed_artifact_sha256": self.relaxed_artifact_sha256, "qualification": self.qualification.to_dict(),
            "passed": bool(self.passed),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxVerifyRunRecord":
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]), pes_verify_run_digest=str(payload["pes_verify_run_digest"]),
            candidate_model_path=str(payload["candidate_model_path"]), candidate_model_sha256=str(payload["candidate_model_sha256"]),
            relaxed_artifact_path=str(payload["relaxed_artifact_path"]), relaxed_artifact_sha256=str(payload["relaxed_artifact_sha256"]),
            qualification=RelaxModelQualification.from_dict(payload["qualification"]),
        )
        if payload.get("schema") != RELAX_RUN_RECORD_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 run record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class RelaxVerifyCampaignRecord:
    campaign_plan_digest: str
    pes_verify_campaign_digest: str
    policy: RelaxVerifyPolicy
    base_set: RelaxBaseSet
    request_artifact: RelaxRequestArtifact
    reference_artifact: RelaxReferenceArtifact
    run_records: tuple[RelaxVerifyRunRecord, ...]
    stage_context: str
    serialization_schema: str = field(default=RELAX_CAMPAIGN_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != RELAX_CAMPAIGN_RECORD_SCHEMA:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 campaign schema.")
        for name in ("campaign_plan_digest", "pes_verify_campaign_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.base_set.policy_digest != self.policy.policy_digest or self.request_artifact.base_set_digest != self.base_set.content_digest or self.reference_artifact.base_set_digest != self.base_set.content_digest:
            raise TrainingDataInputError("RELAX-VERIFY1 campaign policy/base/reference identities disagree.")
        records = tuple(sorted(self.run_records, key=lambda v: v.run_plan_digest))
        if not records or len({v.run_plan_digest for v in records}) != len(records):
            raise TrainingDataInputError("RELAX-VERIFY1 campaign requires unique candidate run records.")
        if self.stage_context not in {"target_size_stage_c", "production"}:
            raise TrainingDataInputError("Unsupported RELAX-VERIFY1 stage context.")
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
            "pes_verify_campaign_digest": self.pes_verify_campaign_digest, "policy": self.policy.to_dict(),
            "base_set": self.base_set.to_dict(), "request_artifact": self.request_artifact.to_dict(),
            "reference_artifact": self.reference_artifact.to_dict(), "run_records": [v.to_dict() for v in self.run_records],
            "stage_context": self.stage_context, "passed_run_count": self.passed_run_count,
            "all_candidates_failed": self.all_candidates_failed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RelaxVerifyCampaignRecord":
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]), pes_verify_campaign_digest=str(payload["pes_verify_campaign_digest"]),
            policy=RelaxVerifyPolicy.from_dict(payload["policy"]), base_set=RelaxBaseSet.from_dict(payload["base_set"]),
            request_artifact=RelaxRequestArtifact.from_dict(payload["request_artifact"]),
            reference_artifact=RelaxReferenceArtifact.from_dict(payload["reference_artifact"]),
            run_records=tuple(RelaxVerifyRunRecord.from_dict(v) for v in payload["run_records"]), stage_context=str(payload["stage_context"]),
        )
        if payload.get("schema") != RELAX_CAMPAIGN_RECORD_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("RELAX-VERIFY1 campaign record is corrupt.")
        return result


def _resolve_topology_indices(material_contracts: Any | None, atoms: Any, group_ids: Sequence[str]) -> tuple[int, ...]:
    if not group_ids:
        return tuple(range(len(atoms)))
    if material_contracts is None:
        raise TrainingDataInputError("RELAX-VERIFY1 topology groups require material-profile contracts.")
    from .material_profiles import resolve_atom_group_indices
    selected: set[int] = set()
    numbers = tuple(int(v) for v in atoms.numbers)
    for group_id in group_ids:
        selected.update(resolve_atom_group_indices(material_contracts.atom_groups, numbers, str(group_id)))
    if not selected:
        raise TrainingDataInputError("RELAX-VERIFY1 preserved topology groups resolved to no atoms.")
    return tuple(sorted(selected))


def build_relax_base_set(
    pes_probe_set: Any,
    target_atoms: Sequence[Any],
    *,
    policy: RelaxVerifyPolicy | None = None,
    material_contracts: Any | None = None,
) -> tuple[RelaxBaseSet, tuple[Any, ...]]:
    """Freeze the common candidate-independent zero-K relaxation starts."""
    active = RelaxVerifyPolicy() if policy is None else policy
    target_atoms = tuple(target_atoms)
    count = min(active.maximum_base_configurations, len(pes_probe_set.base_configuration_indices))
    if count <= 0:
        raise TrainingDataInputError("RELAX-VERIFY1 requires at least one PES-VERIFY1 base structure.")
    indices = tuple(int(v) for v in pes_probe_set.base_configuration_indices[:count])
    uids = tuple(str(v) for v in pes_probe_set.base_frame_uids[:count])
    if any(i < 0 or i >= len(target_atoms) for i in indices):
        raise TrainingDataInputError("RELAX-VERIFY1 PES base index is outside the target artifact.")
    bases = tuple(_copy_without_calculator(target_atoms[i]) for i in indices)
    geoms = tuple(_geometry_digest(v) for v in bases)
    groups = tuple(_resolve_topology_indices(material_contracts, atoms, active.topology_group_ids) for atoms in bases)
    result = RelaxBaseSet(
        pes_probe_set_digest=pes_probe_set.content_digest,
        target_role_digest=pes_probe_set.target_role_digest,
        target_artifact_digest=pes_probe_set.target_artifact_digest,
        target_artifact_sha256=pes_probe_set.target_artifact_sha256,
        policy_digest=active.policy_digest,
        base_frame_uids=uids,
        base_configuration_indices=indices,
        base_geometry_digests=geoms,
        topology_atom_indices_by_base=groups,
    )
    return result, bases


def write_relax_reference_request(base_set: RelaxBaseSet, base_atoms: Sequence[Any], output_directory: str | Path) -> RelaxRequestArtifact:
    try:
        from ase.io import write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for RELAX-VERIFY1 request materialization.") from exc
    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    bases = tuple(_copy_without_calculator(v) for v in base_atoms)
    if len(bases) != len(base_set.base_frame_uids):
        raise TrainingDataInputError("RELAX-VERIFY1 request base count disagrees with base-set identity.")
    for expected, atoms in zip(base_set.base_geometry_digests, bases):
        if _geometry_digest(atoms) != expected:
            raise TrainingDataInputError("RELAX-VERIFY1 request base geometry changed after freezing.")
    extxyz = root / "relax-request.extxyz"
    write(extxyz, list(bases), format="extxyz")
    inputs = root / "dft-inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    inventory: list[tuple[str, str]] = []
    entries: list[dict[str, Any]] = []
    for index, (uid, atoms) in enumerate(zip(base_set.base_frame_uids, bases)):
        directory = inputs / f"{index:04d}-{uid[:12]}"
        directory.mkdir(parents=True, exist_ok=True)
        poscar = directory / "POSCAR"
        write(poscar, atoms, format="vasp", direct=True, vasp5=True)
        sha = _sha256_file(poscar)
        inventory.append((str(poscar.relative_to(root)), sha))
        entries.append({"request_index": index, "base_frame_uid": uid, "directory": str(directory.relative_to(root)), "poscar_sha256": sha})
    manifest = root / "relax-manifest.json"
    manifest.write_text(json.dumps({
        "schema": "mdstats.relax-verify1-request-manifest.v1",
        "base_set": base_set.to_dict(),
        "entries": entries,
        "instructions": {
            "calculation": "Run one fixed-cell zero-K ionic DFT relaxation in every listed directory using identical electronic/ionic settings.",
            "required_vasp_files_for_auto_collection": ["INCAR", "KPOINTS", "POTCAR", "vasprun.xml"],
            "cell_rule": "Keep the cell fixed (VASP ISIF=2 semantics or equivalent).",
            "force_rule": "Converge the maximum atomic force to the RELAX-VERIFY1 configured force ceiling.",
        },
    }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return RelaxRequestArtifact(
        base_set_digest=base_set.content_digest, extxyz_path=str(extxyz), extxyz_sha256=_sha256_file(extxyz),
        manifest_path=str(manifest), manifest_sha256=_sha256_file(manifest), configuration_count=len(bases),
        poscar_sha256s=tuple(inventory),
    )


def _same_fixed_cell_base(expected: Any, observed: Any, tolerance: float) -> bool:
    if tuple(int(v) for v in expected.numbers) != tuple(int(v) for v in observed.numbers):
        return False
    if tuple(bool(v) for v in expected.pbc) != tuple(bool(v) for v in observed.pbc):
        return False
    return bool(np.max(np.abs(np.asarray(expected.cell.array, dtype=float) - np.asarray(observed.cell.array, dtype=float))) <= tolerance)


def _max_force(atoms: Any) -> float:
    try:
        forces = np.asarray(atoms.get_forces(), dtype=np.float64)
    except Exception as exc:
        raise TrainingDataInputError(f"RELAX-VERIFY1 reference lacks force labels: {exc}") from exc
    if forces.shape != (len(atoms), 3) or not np.all(np.isfinite(forces)):
        raise TrainingDataInputError("RELAX-VERIFY1 reference contains invalid forces.")
    return float(np.max(np.linalg.norm(forces, axis=1))) if len(atoms) else 0.0


def load_relax_reference_extxyz(
    base_set: RelaxBaseSet,
    base_atoms: Sequence[Any],
    reference_path: str | Path,
    *,
    policy: RelaxVerifyPolicy,
    protocol_digest: str,
    protocol_source: str = "external_extxyz_assertion",
    source_file_sha256s: Sequence[tuple[str, str]] = (),
) -> tuple[RelaxReferenceArtifact, tuple[Any, ...]]:
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for RELAX-VERIFY1 reference ingestion.") from exc
    path = Path(reference_path).resolve()
    if not path.is_file():
        raise TrainingDataInputError(f"RELAX-VERIFY1 reference artifact is missing: {path}")
    values = read(path, index=":", format="extxyz")
    if not isinstance(values, list):
        values = [values]
    if len(values) != len(base_set.base_frame_uids):
        raise TrainingDataInputError("RELAX-VERIFY1 reference configuration count changed.")
    by_uid: dict[str, Any] = {}
    if all(str(v.info.get("relax_base_frame_uid", "")).strip() for v in values):
        for atoms in values:
            uid = str(atoms.info["relax_base_frame_uid"]).strip()
            if uid in by_uid:
                raise TrainingDataInputError("RELAX-VERIFY1 reference contains duplicate base UIDs.")
            by_uid[uid] = atoms
        if set(by_uid) != set(base_set.base_frame_uids):
            raise TrainingDataInputError("RELAX-VERIFY1 reference base UID membership changed.")
        ordered = tuple(by_uid[uid] for uid in base_set.base_frame_uids)
    else:
        ordered = tuple(values)
    max_forces: list[float] = []
    for expected, observed, selected in zip(base_atoms, ordered, base_set.topology_atom_indices_by_base):
        if not _same_fixed_cell_base(expected, observed, policy.reference_geometry_tolerance_angstrom):
            raise TrainingDataInputError("RELAX-VERIFY1 DFT reference changed atom identity/PBC/cell; v1 requires fixed-cell relaxation.")
        initial_edges = _edge_map(expected, selected, policy.topology_cutoff_scale)
        relaxed_edges = _edge_map(observed, selected, policy.topology_cutoff_scale)
        initial_coord = _coordination(initial_edges, selected)
        relaxed_coord = _coordination(relaxed_edges, selected)
        if set(initial_edges) != set(relaxed_edges) or initial_coord != relaxed_coord:
            raise TrainingDataInputError(
                "RELAX-VERIFY1 DFT reference changed the preserved-group topology; the common zero-K reference is not an admissible intact target structure."
            )
        fmax = _max_force(observed)
        if fmax > policy.force_convergence_ev_per_angstrom + 1.0e-12:
            raise TrainingDataInputError(
                f"RELAX-VERIFY1 DFT reference is not converged: max force {fmax:.6f} eV/A exceeds {policy.force_convergence_ev_per_angstrom:.6f}."
            )
        max_forces.append(fmax)
    artifact = RelaxReferenceArtifact(
        base_set_digest=base_set.content_digest, reference_path=str(path), reference_sha256=_sha256_file(path),
        configuration_count=len(ordered), protocol_digest=validate_digest(protocol_digest, name="protocol_digest"),
        protocol_source=str(protocol_source), max_force_ev_per_angstrom=tuple(max_forces),
        source_file_sha256s=tuple(source_file_sha256s),
    )
    return artifact, ordered


def collect_relax_reference_from_vasp(
    base_set: RelaxBaseSet,
    base_atoms: Sequence[Any],
    request_artifact: RelaxRequestArtifact,
    *,
    output_path: str | Path,
    policy: RelaxVerifyPolicy,
) -> tuple[RelaxReferenceArtifact, tuple[Any, ...]] | None:
    try:
        from ase.io import read, write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for RELAX-VERIFY1 VASP collection.") from exc
    root = Path(request_artifact.manifest_path).resolve().parent
    manifest = json.loads(Path(request_artifact.manifest_path).read_text(encoding="utf-8"))
    directories = tuple(root / str(v["directory"]) for v in manifest["entries"])
    required = ("POSCAR", "INCAR", "KPOINTS", "POTCAR", "vasprun.xml")
    if any(not all((directory / name).is_file() for name in required) for directory in directories):
        return None
    protocol_hashes: dict[str, str] = {}
    for name in ("INCAR", "KPOINTS", "POTCAR"):
        hashes = {_sha256_file(directory / name) for directory in directories}
        if len(hashes) != 1:
            raise TrainingDataInputError(f"RELAX-VERIFY1 VASP {name} bytes differ across reference relaxations.")
        protocol_hashes[name] = next(iter(hashes))
    protocol_digest = digest({"schema": "mdstats.relax-vasp-reference-protocol.v1", **protocol_hashes})
    relaxed: list[Any] = []
    source_hashes: list[tuple[str, str]] = []
    requested_poscar_sha = {str(path): sha for path, sha in request_artifact.poscar_sha256s}
    for uid, expected, directory in zip(base_set.base_frame_uids, base_atoms, directories):
        relative_poscar = str((directory / "POSCAR").relative_to(root))
        if requested_poscar_sha.get(relative_poscar) != _sha256_file(directory / "POSCAR"):
            raise TrainingDataInputError("RELAX-VERIFY1 VASP request POSCAR bytes changed after the base geometry was frozen.")
        vasprun = directory / "vasprun.xml"
        source_hashes.append((str(vasprun), _sha256_file(vasprun)))
        try:
            final = read(vasprun, index=-1)
        except Exception as exc:
            raise TrainingDataInputError(f"RELAX-VERIFY1 could not read {vasprun}: {exc}") from exc
        if not _same_fixed_cell_base(expected, final, policy.reference_geometry_tolerance_angstrom):
            raise TrainingDataInputError("RELAX-VERIFY1 VASP reference changed cell/PBC/atom identity; fixed-cell relaxation is required.")
        if _max_force(final) > policy.force_convergence_ev_per_angstrom + 1.0e-12:
            raise TrainingDataInputError("RELAX-VERIFY1 VASP reference did not converge to the configured force ceiling.")
        final.info["relax_base_frame_uid"] = uid
        relaxed.append(final)
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, relaxed, format="extxyz")
    return load_relax_reference_extxyz(
        base_set, base_atoms, output, policy=policy, protocol_digest=protocol_digest,
        protocol_source="vasp_identical_input_sha256",
        source_file_sha256s=tuple(source_hashes) + tuple((name, sha) for name, sha in sorted(protocol_hashes.items())),
    )


def _edge_map(atoms: Any, selected: Sequence[int], cutoff_scale: float) -> dict[tuple[int, int], float]:
    try:
        from ase.neighborlist import natural_cutoffs, neighbor_list
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for RELAX-VERIFY1 topology checks.") from exc
    selected_set = set(int(v) for v in selected)
    cutoffs = natural_cutoffs(atoms, mult=float(cutoff_scale))
    i_values, j_values = neighbor_list("ij", atoms, cutoffs, self_interaction=False)
    edges: dict[tuple[int, int], float] = {}
    for i, j in zip(i_values, j_values):
        i = int(i); j = int(j)
        if i == j or i not in selected_set or j not in selected_set:
            continue
        key = (i, j) if i < j else (j, i)
        distance = float(atoms.get_distance(key[0], key[1], mic=True))
        previous = edges.get(key)
        if previous is None or distance < previous:
            edges[key] = distance
    return edges


def _angle_map(atoms: Any, edges: Mapping[tuple[int, int], float]) -> dict[tuple[int, int, int], float]:
    adjacency: dict[int, set[int]] = {}
    for i, j in edges:
        adjacency.setdefault(i, set()).add(j)
        adjacency.setdefault(j, set()).add(i)
    result: dict[tuple[int, int, int], float] = {}
    for center, neighbors in adjacency.items():
        ordered = sorted(neighbors)
        for a in range(len(ordered)):
            for b in range(a + 1, len(ordered)):
                i, k = ordered[a], ordered[b]
                key = (min(i, k), center, max(i, k))
                result[key] = float(atoms.get_angle(i, center, k, mic=True))
    return result


def _coordination(edges: Mapping[tuple[int, int], float], selected: Sequence[int]) -> dict[int, int]:
    result = {int(i): 0 for i in selected}
    for i, j in edges:
        result[i] = result.get(i, 0) + 1
        result[j] = result.get(j, 0) + 1
    return result


def _periodic_displacements(reference: Any, candidate: Any, indices: Sequence[int]) -> np.ndarray:
    ref_cell = np.asarray(reference.cell.array, dtype=np.float64)
    cand_cell = np.asarray(candidate.cell.array, dtype=np.float64)
    if np.max(np.abs(ref_cell - cand_cell)) > 1.0e-8:
        # Compare Cartesian positions after the same fractional minimum-image map
        # using the reference cell; cell mismatch is separately quantified.
        pass
    ref_scaled = np.asarray(reference.get_scaled_positions(wrap=False), dtype=np.float64)
    cand_scaled = np.asarray(candidate.get_scaled_positions(wrap=False), dtype=np.float64)
    delta = cand_scaled - ref_scaled
    pbc = np.asarray(reference.pbc, dtype=bool)
    delta[:, pbc] -= np.round(delta[:, pbc])
    cart = delta @ ref_cell
    selected = np.asarray(tuple(int(v) for v in indices), dtype=int)
    chosen = cart[selected]
    # Remove a harmless rigid translation before geometry fidelity scoring.
    translation = np.mean(chosen, axis=0) if len(chosen) else np.zeros(3)
    return chosen - translation


def assess_relaxed_geometry(
    base_set: RelaxBaseSet,
    reference_relaxed: Sequence[Any],
    candidate_relaxed: Sequence[Any],
    *,
    policy: RelaxVerifyPolicy,
    optimizer_steps: Sequence[int] | None = None,
    converged: Sequence[bool] | None = None,
    energy_drop_ev_per_atom: Sequence[float | None] | None = None,
) -> tuple[RelaxBaseMetric, ...]:
    refs = tuple(reference_relaxed); candidates = tuple(candidate_relaxed)
    count = len(base_set.base_frame_uids)
    if len(refs) != count or len(candidates) != count:
        raise TrainingDataInputError("RELAX-VERIFY1 geometry assessment count mismatch.")
    steps_values = tuple(int(v) for v in (optimizer_steps or (0,) * count))
    converged_values = tuple(bool(v) for v in (converged or (True,) * count))
    energy_values = tuple(energy_drop_ev_per_atom or (None,) * count)
    metrics: list[RelaxBaseMetric] = []
    for uid, selected, ref, cand, steps, did_converge, energy_drop in zip(
        base_set.base_frame_uids, base_set.topology_atom_indices_by_base, refs, candidates, steps_values, converged_values, energy_values
    ):
        if tuple(int(v) for v in ref.numbers) != tuple(int(v) for v in cand.numbers):
            raise TrainingDataInputError("RELAX-VERIFY1 candidate atom identities changed.")
        if tuple(bool(v) for v in ref.pbc) != tuple(bool(v) for v in cand.pbc):
            raise TrainingDataInputError("RELAX-VERIFY1 candidate PBC changed.")
        ref_edges = _edge_map(ref, selected, policy.topology_cutoff_scale)
        cand_edges = _edge_map(cand, selected, policy.topology_cutoff_scale)
        ref_keys, cand_keys = set(ref_edges), set(cand_edges)
        missing = ref_keys - cand_keys
        new = cand_keys - ref_keys
        ref_coord = _coordination(ref_edges, selected); cand_coord = _coordination(cand_edges, selected)
        coordination_mismatch = sum(ref_coord.get(i, 0) != cand_coord.get(i, 0) for i in selected)
        topology_pass = not missing and not new and coordination_mismatch == 0

        disp = _periodic_displacements(ref, cand, selected)
        norms = np.linalg.norm(disp, axis=1) if len(disp) else np.zeros(0)
        rms_disp = float(np.sqrt(np.mean(norms ** 2))) if len(norms) else 0.0
        max_disp = float(np.max(norms)) if len(norms) else 0.0

        common = sorted(ref_keys & cand_keys)
        bond_err = np.asarray([cand_edges[key] - ref_edges[key] for key in common], dtype=float)
        bond_rmse = float(np.sqrt(np.mean(bond_err ** 2))) if bond_err.size else 0.0
        bond_max = float(np.max(np.abs(bond_err))) if bond_err.size else 0.0
        ref_angles = _angle_map(ref, {key: ref_edges[key] for key in common})
        cand_angles = _angle_map(cand, {key: cand_edges[key] for key in common})
        angle_keys = sorted(set(ref_angles) & set(cand_angles))
        angle_err = np.asarray([cand_angles[key] - ref_angles[key] for key in angle_keys], dtype=float)
        angle_rmse = float(np.sqrt(np.mean(angle_err ** 2))) if angle_err.size else 0.0
        angle_max = float(np.max(np.abs(angle_err))) if angle_err.size else 0.0
        ref_cell = np.asarray(ref.cell.array, dtype=float); cand_cell = np.asarray(cand.cell.array, dtype=float)
        try:
            strain = cand_cell @ np.linalg.inv(ref_cell) - np.eye(3)
            cell_strain = float(np.linalg.norm(strain))
        except np.linalg.LinAlgError:
            cell_strain = float("inf")
        final_fmax = _max_force(cand)
        reasons: list[str] = []
        if not did_converge or final_fmax > policy.force_convergence_ev_per_angstrom + 1.0e-12:
            reasons.append("relaxation_not_converged")
        if policy.require_exact_topology and not topology_pass:
            reasons.append("topology_changed")
        if rms_disp > policy.rms_displacement_tolerance_angstrom:
            reasons.append("rms_displacement_exceeded")
        if max_disp > policy.max_displacement_tolerance_angstrom:
            reasons.append("max_displacement_exceeded")
        if bond_rmse > policy.bond_rmse_tolerance_angstrom:
            reasons.append("bond_rmse_exceeded")
        if bond_max > policy.bond_max_error_tolerance_angstrom:
            reasons.append("bond_max_error_exceeded")
        if angle_rmse > policy.angle_rmse_tolerance_degrees:
            reasons.append("angle_rmse_exceeded")
        if angle_max > policy.angle_max_error_tolerance_degrees:
            reasons.append("angle_max_error_exceeded")
        if cell_strain > policy.cell_strain_tolerance:
            reasons.append("cell_changed")
        metrics.append(RelaxBaseMetric(
            base_frame_uid=uid, topology_passed=topology_pass, reference_edge_count=len(ref_edges), candidate_edge_count=len(cand_edges),
            missing_edge_count=len(missing), new_edge_count=len(new), coordination_mismatch_count=coordination_mismatch,
            rms_displacement_angstrom=rms_disp, max_displacement_angstrom=max_disp, bond_rmse_angstrom=bond_rmse,
            bond_max_error_angstrom=bond_max, angle_rmse_degrees=angle_rmse, angle_max_error_degrees=angle_max,
            cell_strain_norm=cell_strain, final_max_force_ev_per_angstrom=final_fmax, optimizer_steps=steps,
            converged=did_converge, energy_drop_ev_per_atom=None if energy_drop is None else float(energy_drop),
            passed=not reasons, failure_reasons=tuple(reasons),
        ))
    return tuple(metrics)


@mace_runtime_warning_handled("RELAX-VERIFY1 MACE zero-K relaxation")
def relax_mace_model(
    model_path: str | Path,
    base_atoms: Sequence[Any],
    *,
    policy: RelaxVerifyPolicy,
    device: str,
    model_dtype: str,
    head: str | None = None,
) -> tuple[tuple[Any, ...], tuple[int, ...], tuple[bool, ...], tuple[float | None, ...]]:
    """Relax common bases with one deployable MACE model under the frozen FIRE protocol."""
    try:
        from ase.optimize import FIRE
        from ase.calculators.singlepoint import SinglePointCalculator
        from mace.calculators import MACECalculator
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE and mace-torch are required for RELAX-VERIFY1 model relaxation.") from exc
    kwargs: dict[str, Any] = {}
    if head is not None:
        kwargs["head"] = str(head)
    calculator = MACECalculator(model_paths=str(Path(model_path).resolve()), device=str(device), default_dtype=str(model_dtype), **kwargs)
    relaxed: list[Any] = []; steps_out: list[int] = []; converged_out: list[bool] = []; drops: list[float | None] = []
    for source in base_atoms:
        atoms = source.copy(); atoms.calc = calculator
        try:
            initial_energy = float(atoms.get_potential_energy())
            optimizer = FIRE(atoms, logfile=None)
            did_converge = bool(optimizer.run(fmax=policy.force_convergence_ev_per_angstrom, steps=policy.maximum_steps))
            steps = int(getattr(optimizer, "nsteps", policy.maximum_steps))
            final_energy = float(atoms.get_potential_energy())
            final_forces = np.asarray(atoms.get_forces(), dtype=np.float64)
        except Exception as exc:
            raise TrainingDataInputError(f"RELAX-VERIFY1 MACE relaxation failed: {exc}") from exc
        if not math.isfinite(initial_energy) or not math.isfinite(final_energy) or not np.all(np.isfinite(final_forces)):
            raise TrainingDataInputError("RELAX-VERIFY1 MACE relaxation produced non-finite energy/forces.")
        output = atoms.copy()
        output.calc = SinglePointCalculator(output, energy=final_energy, forces=final_forces)
        relaxed.append(output); steps_out.append(steps); converged_out.append(did_converge)
        drops.append((final_energy - initial_energy) / max(1, len(atoms)))
    return tuple(relaxed), tuple(steps_out), tuple(converged_out), tuple(drops)


def write_relaxed_model_artifact(relaxed_atoms: Sequence[Any], output_path: str | Path, base_set: RelaxBaseSet) -> tuple[str, str]:
    try:
        from ase.io import write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for RELAX-VERIFY1 artifact writing.") from exc
    path = Path(output_path).resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    values = []
    for uid, source in zip(base_set.base_frame_uids, relaxed_atoms):
        atoms = source.copy(); atoms.info["relax_base_frame_uid"] = uid; values.append(atoms)
    write(path, values, format="extxyz")
    return str(path), _sha256_file(path)


__all__ = [
    "RELAX_VERIFY_IMPLEMENTATION_VERSION", "RelaxVerifyPolicy", "RelaxBaseSet", "RelaxRequestArtifact",
    "RelaxReferenceArtifact", "RelaxBaseMetric", "RelaxModelQualification", "RelaxVerifyRunRecord",
    "RelaxVerifyCampaignRecord", "build_relax_base_set", "write_relax_reference_request",
    "load_relax_reference_extxyz", "collect_relax_reference_from_vasp", "assess_relaxed_geometry",
    "relax_mace_model", "write_relaxed_model_artifact",
]
