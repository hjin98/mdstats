"""PES-VERIFY1 finite-displacement local-PES qualification for TRAIN2 candidates.

The gate is intentionally independent of checkpoint ranking.  It freezes one
candidate-independent probe geometry set from the already authorized EVAL2
physical target role, requests matched DFT single-point labels for symmetric
perturbations, and compares foundation/candidate local restoring behavior to
that same DFT evidence.

PES-VERIFY1 does not relax structures and does not run MD.  Those authorities
belong to RELAX-VERIFY1 and DYN-VERIFY2 respectively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math

import numpy as np

from .foundation import FoundationPotentialIdentity, FoundationInferenceIdentity

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

PES_VERIFY_POLICY_SCHEMA = "mdstats.pes-verify-policy.v1"
PES_PROBE_MODE_SCHEMA = "mdstats.pes-probe-mode.v1"
PES_PROBE_GEOMETRY_SCHEMA = "mdstats.pes-probe-geometry.v1"
PES_PROBE_SET_SCHEMA = "mdstats.pes-probe-set.v1"
PES_PROBE_REQUEST_SCHEMA = "mdstats.pes-probe-request.v1"
PES_REFERENCE_ARTIFACT_SCHEMA = "mdstats.pes-reference-artifact.v1"
PES_MODE_METRIC_SCHEMA = "mdstats.pes-mode-metric.v1"
PES_MODEL_QUALIFICATION_SCHEMA = "mdstats.pes-model-qualification.v1"
PES_RUN_RECORD_SCHEMA = "mdstats.pes-verify-run.v1"
PES_CAMPAIGN_RECORD_SCHEMA = "mdstats.pes-verify-campaign.v2"
PES_CAMPAIGN_RECORD_V1_SCHEMA = "mdstats.pes-verify-campaign.v1"
PES_VERIFY_IMPLEMENTATION_VERSION = "mdstats.pes-verify1.2026-08.v1"


def _sha256_file(path: str | Path) -> str:
    target = Path(path)
    hasher = hashlib.sha256()
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and non-negative.")
    return result


def _geometry_digest(atoms: Any) -> str:
    """Tolerance-stable geometry identity for request/reference matching."""

    numbers = tuple(int(v) for v in np.asarray(atoms.numbers, dtype=int).tolist())
    cell = np.round(np.asarray(atoms.cell.array, dtype=np.float64), 8)
    scaled = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=np.float64)
    scaled = np.mod(scaled, 1.0)
    scaled = np.round(scaled, 8)
    return digest(
        {
            "schema": "mdstats.pes-probe-geometry-identity.v1",
            "atomic_numbers": list(numbers),
            "cell_angstrom": cell.tolist(),
            "scaled_positions": scaled.tolist(),
            "pbc": [bool(v) for v in atoms.pbc],
        }
    )


def _copy_without_calculator(atoms: Any) -> Any:
    result = atoms.copy()
    result.calc = None
    return result


def _stress_matrix(atoms: Any) -> np.ndarray | None:
    try:
        stress = np.asarray(atoms.get_stress(voigt=False), dtype=np.float64)
    except Exception:
        return None
    if stress.shape != (3, 3) or not np.all(np.isfinite(stress)):
        return None
    return stress


@dataclass(frozen=True, slots=True)
class PESVerifyPolicy:
    maximum_base_configurations: int = 4
    maximum_modes_per_base: int = 4
    displacement_amplitude_angstrom: float = 0.04
    strain_amplitude: float = 0.01
    neighbor_cutoff_scale: float = 1.20
    include_strain_modes: bool = True
    projected_force_atol_ev_per_angstrom: float = 0.05
    projected_force_rtol: float = 0.25
    force_stiffness_atol_ev_per_angstrom2: float = 0.50
    force_stiffness_rtol: float = 0.30
    energy_curvature_atol_ev_per_angstrom2: float = 0.50
    energy_curvature_rtol: float = 0.30
    restoring_force_resolution_floor_ev_per_angstrom: float = 0.02
    stiffness_sign_resolution_floor_ev_per_angstrom2: float = 0.25
    strain_stress_atol_ev_per_angstrom3: float = 0.01
    strain_stress_rtol: float = 0.30
    strain_energy_curvature_atol_ev_per_atom: float = 1.0
    strain_energy_curvature_rtol: float = 0.30
    strain_stress_resolution_floor_ev_per_angstrom3: float = 0.002
    geometry_match_tolerance_angstrom: float = 1.0e-6
    require_all_modes: bool = True
    implementation_version: str = PES_VERIFY_IMPLEMENTATION_VERSION
    serialization_schema: str = field(default=PES_VERIFY_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_VERIFY_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 policy schema.")
        for name in ("maximum_base_configurations", "maximum_modes_per_base"):
            value = int(getattr(self, name))
            if value <= 0:
                raise TrainingDataInputError(f"PES-VERIFY1 {name} must be positive.")
            object.__setattr__(self, name, value)
        for name in (
            "displacement_amplitude_angstrom",
            "strain_amplitude",
            "neighbor_cutoff_scale",
            "geometry_match_tolerance_angstrom",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"PES-VERIFY1 {name} must be finite and positive.")
            object.__setattr__(self, name, value)
        for name in (
            "projected_force_atol_ev_per_angstrom",
            "projected_force_rtol",
            "force_stiffness_atol_ev_per_angstrom2",
            "force_stiffness_rtol",
            "energy_curvature_atol_ev_per_angstrom2",
            "energy_curvature_rtol",
            "restoring_force_resolution_floor_ev_per_angstrom",
            "stiffness_sign_resolution_floor_ev_per_angstrom2",
            "strain_stress_atol_ev_per_angstrom3",
            "strain_stress_rtol",
            "strain_energy_curvature_atol_ev_per_atom",
            "strain_energy_curvature_rtol",
            "strain_stress_resolution_floor_ev_per_angstrom3",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        if not bool(self.require_all_modes):
            raise TrainingDataInputError(
                "PES-VERIFY1 v1 requires all generated modes to pass; partial-mode qualification is not supported."
            )
        if not self.implementation_version.strip():
            raise TrainingDataInputError("PES-VERIFY1 implementation version is empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "maximum_base_configurations": self.maximum_base_configurations,
            "maximum_modes_per_base": self.maximum_modes_per_base,
            "displacement_amplitude_angstrom": self.displacement_amplitude_angstrom,
            "strain_amplitude": self.strain_amplitude,
            "neighbor_cutoff_scale": self.neighbor_cutoff_scale,
            "include_strain_modes": bool(self.include_strain_modes),
            "projected_force_atol_ev_per_angstrom": self.projected_force_atol_ev_per_angstrom,
            "projected_force_rtol": self.projected_force_rtol,
            "force_stiffness_atol_ev_per_angstrom2": self.force_stiffness_atol_ev_per_angstrom2,
            "force_stiffness_rtol": self.force_stiffness_rtol,
            "energy_curvature_atol_ev_per_angstrom2": self.energy_curvature_atol_ev_per_angstrom2,
            "energy_curvature_rtol": self.energy_curvature_rtol,
            "restoring_force_resolution_floor_ev_per_angstrom": self.restoring_force_resolution_floor_ev_per_angstrom,
            "stiffness_sign_resolution_floor_ev_per_angstrom2": self.stiffness_sign_resolution_floor_ev_per_angstrom2,
            "strain_stress_atol_ev_per_angstrom3": self.strain_stress_atol_ev_per_angstrom3,
            "strain_stress_rtol": self.strain_stress_rtol,
            "strain_energy_curvature_atol_ev_per_atom": self.strain_energy_curvature_atol_ev_per_atom,
            "strain_energy_curvature_rtol": self.strain_energy_curvature_rtol,
            "strain_stress_resolution_floor_ev_per_angstrom3": self.strain_stress_resolution_floor_ev_per_angstrom3,
            "geometry_match_tolerance_angstrom": self.geometry_match_tolerance_angstrom,
            "require_all_modes": bool(self.require_all_modes),
            "implementation_version": self.implementation_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESVerifyPolicy":
        if payload.get("schema") != PES_VERIFY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PES-VERIFY1 policy schema.")
        kwargs = {name: payload[name] for name in cls.__dataclass_fields__ if name not in {"serialization_schema"} and name in payload}
        result = cls(**kwargs)
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PESProbeMode:
    mode_id: str
    base_frame_uid: str
    base_configuration_index: int
    mode_type: str
    motif_key: str
    coordinate_kind: str
    atom_indices: tuple[int, ...]
    direction: tuple[tuple[float, float, float], ...] = ()
    strain_tensor: tuple[tuple[float, float, float], ...] = ()
    amplitude: float = 0.04
    serialization_schema: str = field(default=PES_PROBE_MODE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_PROBE_MODE_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 mode schema.")
        object.__setattr__(self, "mode_id", validate_digest(self.mode_id, name="mode_id"))
        object.__setattr__(self, "base_frame_uid", validate_digest(self.base_frame_uid, name="base_frame_uid"))
        if int(self.base_configuration_index) < 0:
            raise TrainingDataInputError("PES-VERIFY1 base configuration index cannot be negative.")
        object.__setattr__(self, "base_configuration_index", int(self.base_configuration_index))
        if self.mode_type not in {"bond_stretch", "angle_bend", "coordination_breathing", "strain"}:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 mode type.")
        if self.coordinate_kind not in {"atomic_displacement_angstrom", "strain"}:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 coordinate kind.")
        if not self.motif_key.strip():
            raise TrainingDataInputError("PES-VERIFY1 motif key cannot be empty.")
        amplitude = float(self.amplitude)
        if not math.isfinite(amplitude) or amplitude <= 0.0:
            raise TrainingDataInputError("PES-VERIFY1 mode amplitude must be positive.")
        object.__setattr__(self, "amplitude", amplitude)
        indices = tuple(int(v) for v in self.atom_indices)
        if any(v < 0 for v in indices) or len(set(indices)) != len(indices):
            raise TrainingDataInputError("PES-VERIFY1 mode atom indices are invalid.")
        object.__setattr__(self, "atom_indices", indices)
        direction = tuple(tuple(float(x) for x in row) for row in self.direction)
        strain = tuple(tuple(float(x) for x in row) for row in self.strain_tensor)
        if self.coordinate_kind == "atomic_displacement_angstrom":
            if not direction or strain:
                raise TrainingDataInputError("Atomic PES modes require a direction and no strain tensor.")
            array = np.asarray(direction, dtype=np.float64)
            if array.ndim != 2 or array.shape[1] != 3 or not np.all(np.isfinite(array)):
                raise TrainingDataInputError("PES-VERIFY1 displacement direction is invalid.")
            norm = float(np.linalg.norm(array))
            if abs(norm - 1.0) > 1.0e-10:
                raise TrainingDataInputError("PES-VERIFY1 displacement directions must have unit Frobenius norm.")
        else:
            if direction or len(strain) != 3 or any(len(row) != 3 for row in strain):
                raise TrainingDataInputError("Strain PES modes require a 3x3 strain tensor and no atomic direction.")
            array = np.asarray(strain, dtype=np.float64)
            if not np.all(np.isfinite(array)) or abs(float(np.linalg.norm(array)) - 1.0) > 1.0e-10:
                raise TrainingDataInputError("PES-VERIFY1 strain tensors must have unit Frobenius norm.")
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "strain_tensor", strain)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "mode_id": self.mode_id,
            "base_frame_uid": self.base_frame_uid,
            "base_configuration_index": self.base_configuration_index,
            "mode_type": self.mode_type,
            "motif_key": self.motif_key,
            "coordinate_kind": self.coordinate_kind,
            "atom_indices": list(self.atom_indices),
            "direction": [list(v) for v in self.direction],
            "strain_tensor": [list(v) for v in self.strain_tensor],
            "amplitude": self.amplitude,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESProbeMode":
        if payload.get("schema") != PES_PROBE_MODE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PES-VERIFY1 mode schema.")
        result = cls(
            mode_id=str(payload["mode_id"]),
            base_frame_uid=str(payload["base_frame_uid"]),
            base_configuration_index=int(payload["base_configuration_index"]),
            mode_type=str(payload["mode_type"]),
            motif_key=str(payload["motif_key"]),
            coordinate_kind=str(payload["coordinate_kind"]),
            atom_indices=tuple(int(v) for v in payload.get("atom_indices", ())),
            direction=tuple(tuple(float(x) for x in row) for row in payload.get("direction", ())),
            strain_tensor=tuple(tuple(float(x) for x in row) for row in payload.get("strain_tensor", ())),
            amplitude=float(payload["amplitude"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 mode digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PESProbeGeometry:
    probe_uid: str
    base_frame_uid: str
    mode_id: str | None
    side: int
    request_index: int
    geometry_digest: str
    serialization_schema: str = field(default=PES_PROBE_GEOMETRY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_PROBE_GEOMETRY_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 probe-geometry schema.")
        object.__setattr__(self, "probe_uid", validate_digest(self.probe_uid, name="probe_uid"))
        object.__setattr__(self, "base_frame_uid", validate_digest(self.base_frame_uid, name="base_frame_uid"))
        if self.mode_id is not None:
            object.__setattr__(self, "mode_id", validate_digest(self.mode_id, name="mode_id"))
        if int(self.side) not in {-1, 0, 1}:
            raise TrainingDataInputError("PES-VERIFY1 probe side must be -1, 0, or +1.")
        object.__setattr__(self, "side", int(self.side))
        if int(self.request_index) < 0:
            raise TrainingDataInputError("PES-VERIFY1 request index cannot be negative.")
        object.__setattr__(self, "request_index", int(self.request_index))
        object.__setattr__(self, "geometry_digest", validate_digest(self.geometry_digest, name="geometry_digest"))
        if self.side == 0 and self.mode_id is not None:
            raise TrainingDataInputError("PES-VERIFY1 base probes must not carry a mode ID.")
        if self.side != 0 and self.mode_id is None:
            raise TrainingDataInputError("PES-VERIFY1 displaced probes require a mode ID.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "probe_uid": self.probe_uid,
            "base_frame_uid": self.base_frame_uid,
            "mode_id": self.mode_id,
            "side": self.side,
            "request_index": self.request_index,
            "geometry_digest": self.geometry_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESProbeGeometry":
        result = cls(
            probe_uid=str(payload["probe_uid"]),
            base_frame_uid=str(payload["base_frame_uid"]),
            mode_id=None if payload.get("mode_id") is None else str(payload["mode_id"]),
            side=int(payload["side"]),
            request_index=int(payload["request_index"]),
            geometry_digest=str(payload["geometry_digest"]),
        )
        if payload.get("schema") != PES_PROBE_GEOMETRY_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 probe geometry is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class PESProbeSet:
    deploy_probe_set_digest: str
    target_role_digest: str
    target_artifact_digest: str
    target_artifact_sha256: str
    policy_digest: str
    base_frame_uids: tuple[str, ...]
    base_configuration_indices: tuple[int, ...]
    modes: tuple[PESProbeMode, ...]
    probes: tuple[PESProbeGeometry, ...]
    selection_method: str = "deploy_block_round_robin_bases_plus_generic_local_modes_v1"
    serialization_schema: str = field(default=PES_PROBE_SET_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_PROBE_SET_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 probe-set schema.")
        for name in ("deploy_probe_set_digest", "target_role_digest", "target_artifact_digest", "target_artifact_sha256", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(validate_digest(v, name="base_frame_uid") for v in self.base_frame_uids)
        indices = tuple(int(v) for v in self.base_configuration_indices)
        if not frames or len(frames) != len(indices) or len(set(frames)) != len(frames) or len(set(indices)) != len(indices):
            raise TrainingDataInputError("PES-VERIFY1 base membership is invalid.")
        modes = tuple(self.modes)
        probes = tuple(sorted(self.probes, key=lambda v: v.request_index))
        if not modes or not probes:
            raise TrainingDataInputError("PES-VERIFY1 requires finite-displacement modes and probes.")
        if len({v.mode_id for v in modes}) != len(modes) or len({v.probe_uid for v in probes}) != len(probes):
            raise TrainingDataInputError("PES-VERIFY1 probe/mode identities must be unique.")
        if tuple(v.request_index for v in probes) != tuple(range(len(probes))):
            raise TrainingDataInputError("PES-VERIFY1 probe request indices must be contiguous.")
        mode_ids = {v.mode_id for v in modes}
        base_set = set(frames)
        for probe in probes:
            if probe.base_frame_uid not in base_set or (probe.mode_id is not None and probe.mode_id not in mode_ids):
                raise TrainingDataInputError("PES-VERIFY1 probe lineage is inconsistent.")
        for frame in frames:
            if sum(v.base_frame_uid == frame and v.side == 0 for v in probes) != 1:
                raise TrainingDataInputError("PES-VERIFY1 requires exactly one q=0 probe per base frame.")
        for mode in modes:
            sides = sorted(v.side for v in probes if v.mode_id == mode.mode_id)
            if sides != [-1, 1]:
                raise TrainingDataInputError("PES-VERIFY1 every mode requires symmetric +/- probes.")
        object.__setattr__(self, "base_frame_uids", frames)
        object.__setattr__(self, "base_configuration_indices", indices)
        object.__setattr__(self, "modes", modes)
        object.__setattr__(self, "probes", probes)
        if not self.selection_method.strip():
            raise TrainingDataInputError("PES-VERIFY1 selection method is empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "deploy_probe_set_digest": self.deploy_probe_set_digest,
            "target_role_digest": self.target_role_digest,
            "target_artifact_digest": self.target_artifact_digest,
            "target_artifact_sha256": self.target_artifact_sha256,
            "policy_digest": self.policy_digest,
            "base_frame_uids": list(self.base_frame_uids),
            "base_configuration_indices": list(self.base_configuration_indices),
            "modes": [v.to_dict() for v in self.modes],
            "probes": [v.to_dict() for v in self.probes],
            "selection_method": self.selection_method,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESProbeSet":
        if payload.get("schema") != PES_PROBE_SET_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PES-VERIFY1 probe-set schema.")
        result = cls(
            deploy_probe_set_digest=str(payload["deploy_probe_set_digest"]),
            target_role_digest=str(payload["target_role_digest"]),
            target_artifact_digest=str(payload["target_artifact_digest"]),
            target_artifact_sha256=str(payload["target_artifact_sha256"]),
            policy_digest=str(payload["policy_digest"]),
            base_frame_uids=tuple(str(v) for v in payload["base_frame_uids"]),
            base_configuration_indices=tuple(int(v) for v in payload["base_configuration_indices"]),
            modes=tuple(PESProbeMode.from_dict(v) for v in payload["modes"]),
            probes=tuple(PESProbeGeometry.from_dict(v) for v in payload["probes"]),
            selection_method=str(payload.get("selection_method", "deploy_block_round_robin_bases_plus_generic_local_modes_v1")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 probe-set digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PESProbeRequestArtifact:
    probe_set_digest: str
    extxyz_path: str
    extxyz_sha256: str
    manifest_path: str
    manifest_sha256: str
    configuration_count: int
    poscar_sha256s: tuple[tuple[str, str], ...]
    serialization_schema: str = field(default=PES_PROBE_REQUEST_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_PROBE_REQUEST_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 request schema.")
        for name in ("probe_set_digest", "extxyz_sha256", "manifest_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("PES-VERIFY1 request must contain configurations.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        values = tuple((str(path), validate_digest(sha, name="poscar_sha256")) for path, sha in self.poscar_sha256s)
        if len(values) != self.configuration_count or len({p for p, _ in values}) != len(values):
            raise TrainingDataInputError("PES-VERIFY1 POSCAR request inventory is inconsistent.")
        object.__setattr__(self, "poscar_sha256s", values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "probe_set_digest": self.probe_set_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESProbeRequestArtifact":
        result = cls(
            probe_set_digest=str(payload["probe_set_digest"]),
            extxyz_path=str(payload["extxyz_path"]),
            extxyz_sha256=str(payload["extxyz_sha256"]),
            manifest_path=str(payload["manifest_path"]),
            manifest_sha256=str(payload["manifest_sha256"]),
            configuration_count=int(payload["configuration_count"]),
            poscar_sha256s=tuple((str(v["path"]), str(v["sha256"])) for v in payload["poscar_sha256s"]),
        )
        if payload.get("schema") != PES_PROBE_REQUEST_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 request artifact is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class PESReferenceArtifact:
    probe_set_digest: str
    reference_path: str
    reference_sha256: str
    configuration_count: int
    prediction_digest: str
    protocol_digest: str
    protocol_source: str
    source_file_sha256s: tuple[tuple[str, str], ...] = ()
    serialization_schema: str = field(default=PES_REFERENCE_ARTIFACT_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_REFERENCE_ARTIFACT_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 reference schema.")
        for name in ("probe_set_digest", "reference_sha256", "prediction_digest", "protocol_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.configuration_count) <= 0 or not self.reference_path.strip() or not self.protocol_source.strip():
            raise TrainingDataInputError("PES-VERIFY1 reference artifact identity is incomplete.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        values = tuple((str(path), validate_digest(sha, name="source_file_sha256")) for path, sha in self.source_file_sha256s)
        object.__setattr__(self, "source_file_sha256s", values)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "probe_set_digest": self.probe_set_digest,
            "reference_path": self.reference_path,
            "reference_sha256": self.reference_sha256,
            "configuration_count": self.configuration_count,
            "prediction_digest": self.prediction_digest,
            "protocol_digest": self.protocol_digest,
            "protocol_source": self.protocol_source,
            "source_file_sha256s": [{"path": p, "sha256": s} for p, s in self.source_file_sha256s],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESReferenceArtifact":
        result = cls(
            probe_set_digest=str(payload["probe_set_digest"]),
            reference_path=str(payload["reference_path"]),
            reference_sha256=str(payload["reference_sha256"]),
            configuration_count=int(payload["configuration_count"]),
            prediction_digest=str(payload["prediction_digest"]),
            protocol_digest=str(payload["protocol_digest"]),
            protocol_source=str(payload["protocol_source"]),
            source_file_sha256s=tuple((str(v["path"]), str(v["sha256"])) for v in payload.get("source_file_sha256s", ())),
        )
        if payload.get("schema") != PES_REFERENCE_ARTIFACT_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 reference artifact is corrupt.")
        return result


def _normalize_direction(direction: np.ndarray) -> np.ndarray:
    array = np.asarray(direction, dtype=np.float64)
    norm = float(np.linalg.norm(array))
    if not math.isfinite(norm) or norm <= 1.0e-14:
        raise TrainingDataInputError("PES-VERIFY1 discovered a degenerate displacement mode.")
    return array / norm


def _neighbor_geometry(atoms: Any, cutoff_scale: float) -> tuple[list[tuple[int, int, float, np.ndarray]], dict[int, list[tuple[int, float, np.ndarray]]]]:
    try:
        from ase.neighborlist import natural_cutoffs, neighbor_list
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for PES-VERIFY1.") from exc
    cutoffs = natural_cutoffs(atoms, mult=float(cutoff_scale))
    i_values, j_values, d_values, vectors = neighbor_list("ijdD", atoms, cutoffs)
    unique: dict[tuple[int, int], tuple[int, int, float, np.ndarray]] = {}
    adjacency: dict[int, list[tuple[int, float, np.ndarray]]] = {i: [] for i in range(len(atoms))}
    for i, j, distance, vector in zip(i_values, j_values, d_values, vectors):
        i = int(i); j = int(j)
        if i == j:
            continue
        vector = np.asarray(vector, dtype=np.float64)
        distance = float(distance)
        adjacency[i].append((j, distance, vector))
        key = (min(i, j), max(i, j))
        if key not in unique or distance < unique[key][2]:
            if i <= j:
                unique[key] = (i, j, distance, vector)
            else:
                unique[key] = (j, i, distance, -vector)
    bonds = sorted(unique.values(), key=lambda v: (v[2], int(atoms.numbers[v[0]]), int(atoms.numbers[v[1]]), v[0], v[1]))
    for center in adjacency:
        adjacency[center].sort(key=lambda v: (v[1], int(atoms.numbers[v[0]]), v[0]))
    return bonds, adjacency


def _mode_identity(*, base_frame_uid: str, mode_type: str, motif_key: str, coordinate_payload: Mapping[str, Any]) -> str:
    return digest(
        {
            "schema": "mdstats.pes-mode-identity.v1",
            "base_frame_uid": base_frame_uid,
            "mode_type": mode_type,
            "motif_key": motif_key,
            "coordinate": coordinate_payload,
        }
    )


def _build_atomic_mode(
    *,
    base_frame_uid: str,
    base_configuration_index: int,
    mode_type: str,
    motif_key: str,
    atom_indices: Sequence[int],
    direction: np.ndarray,
    amplitude: float,
) -> PESProbeMode:
    direction = _normalize_direction(direction)
    direction_tuple = tuple(tuple(float(x) for x in row) for row in direction)
    mode_id = _mode_identity(
        base_frame_uid=base_frame_uid,
        mode_type=mode_type,
        motif_key=motif_key,
        coordinate_payload={"direction": [list(v) for v in direction_tuple], "amplitude": float(amplitude)},
    )
    return PESProbeMode(
        mode_id=mode_id,
        base_frame_uid=base_frame_uid,
        base_configuration_index=base_configuration_index,
        mode_type=mode_type,
        motif_key=motif_key,
        coordinate_kind="atomic_displacement_angstrom",
        atom_indices=tuple(int(v) for v in atom_indices),
        direction=direction_tuple,
        amplitude=float(amplitude),
    )


def _build_strain_mode(
    *,
    base_frame_uid: str,
    base_configuration_index: int,
    motif_key: str,
    strain_tensor: np.ndarray,
    amplitude: float,
) -> PESProbeMode:
    tensor = np.asarray(strain_tensor, dtype=np.float64)
    tensor = tensor / float(np.linalg.norm(tensor))
    tensor_tuple = tuple(tuple(float(x) for x in row) for row in tensor)
    mode_id = _mode_identity(
        base_frame_uid=base_frame_uid,
        mode_type="strain",
        motif_key=motif_key,
        coordinate_payload={"strain_tensor": [list(v) for v in tensor_tuple], "amplitude": float(amplitude)},
    )
    return PESProbeMode(
        mode_id=mode_id,
        base_frame_uid=base_frame_uid,
        base_configuration_index=base_configuration_index,
        mode_type="strain",
        motif_key=motif_key,
        coordinate_kind="strain",
        atom_indices=(),
        strain_tensor=tensor_tuple,
        amplitude=float(amplitude),
    )


def _focus_indices(material_contracts: Any | None, atoms: Any) -> set[int]:
    if material_contracts is None:
        return set()
    try:
        from .material_profiles import focus_atom_group_ids, resolve_atom_group_indices
        groups = focus_atom_group_ids(material_contracts)
        result: set[int] = set()
        for group in groups:
            try:
                result.update(resolve_atom_group_indices(material_contracts.atom_groups, tuple(int(v) for v in atoms.numbers), group))
            except Exception:
                continue
        return result
    except Exception:
        return set()


def discover_pes_probe_modes(
    atoms: Any,
    *,
    base_frame_uid: str,
    base_configuration_index: int,
    policy: PESVerifyPolicy,
    material_contracts: Any | None = None,
    strain_variant_index: int = 0,
) -> tuple[PESProbeMode, ...]:
    """Discover a small deterministic, material-generic local-mode suite."""

    n_atoms = len(atoms)
    if n_atoms < 2:
        raise TrainingDataInputError("PES-VERIFY1 requires at least two atoms per base configuration.")
    bonds, adjacency = _neighbor_geometry(atoms, policy.neighbor_cutoff_scale)
    numbers = np.asarray(atoms.numbers, dtype=int)
    candidates: list[tuple[int, tuple[Any, ...], PESProbeMode]] = []

    # Bond-stretch candidates: shortest bonded motifs first.  Symmetric motion
    # keeps the mode translationally neutral and gives a unit Cartesian path.
    for i, j, distance, vector in bonds:
        if distance <= 1.0e-12:
            continue
        unit = vector / distance
        direction = np.zeros((n_atoms, 3), dtype=np.float64)
        direction[i] = -unit
        direction[j] = unit
        motif = f"Z{min(numbers[i],numbers[j])}-Z{max(numbers[i],numbers[j])}:bond"
        mode = _build_atomic_mode(
            base_frame_uid=base_frame_uid,
            base_configuration_index=base_configuration_index,
            mode_type="bond_stretch",
            motif_key=motif,
            atom_indices=(i, j),
            direction=direction,
            amplitude=policy.displacement_amplitude_angstrom,
        )
        candidates.append((0, (distance, motif, i, j), mode))

    # Angle mode follows the exact angle gradient for two nearest neighbors.
    for center, neighbors in adjacency.items():
        if len(neighbors) < 2:
            continue
        first = neighbors[: min(4, len(neighbors))]
        for a in range(len(first)):
            for b in range(a + 1, len(first)):
                i, r1_len, r1 = first[a]
                k, r2_len, r2 = first[b]
                if r1_len <= 1.0e-12 or r2_len <= 1.0e-12:
                    continue
                e1 = r1 / r1_len
                e2 = r2 / r2_len
                cosine = float(np.clip(np.dot(e1, e2), -1.0, 1.0))
                sine = math.sqrt(max(0.0, 1.0 - cosine * cosine))
                if sine < 0.15:  # nearly collinear gradients are ill conditioned
                    continue
                grad_i = (cosine * e1 - e2) / (r1_len * sine)
                grad_k = (cosine * e2 - e1) / (r2_len * sine)
                grad_c = -(grad_i + grad_k)
                direction = np.zeros((n_atoms, 3), dtype=np.float64)
                direction[i] = grad_i
                direction[k] = grad_k
                direction[center] = grad_c
                neighbor_pair = tuple(sorted((int(numbers[i]), int(numbers[k]))))
                motif = f"Z{neighbor_pair[0]}-Z{int(numbers[center])}-Z{neighbor_pair[1]}:angle"
                mode = _build_atomic_mode(
                    base_frame_uid=base_frame_uid,
                    base_configuration_index=base_configuration_index,
                    mode_type="angle_bend",
                    motif_key=motif,
                    atom_indices=(i, center, k),
                    direction=direction,
                    amplitude=policy.displacement_amplitude_angstrom,
                )
                candidates.append((1, (-len(neighbors), r1_len + r2_len, motif, center, i, k), mode))

    # Coordination breathing deliberately prioritizes explicit profile focus
    # groups when available, while remaining generic when no profile exists.
    focus = _focus_indices(material_contracts, atoms)
    for center, neighbors in adjacency.items():
        if len(neighbors) < 2:
            continue
        direction = np.zeros((n_atoms, 3), dtype=np.float64)
        used: list[int] = []
        for neighbor, distance, vector in neighbors:
            if distance <= 1.0e-12:
                continue
            direction[neighbor] += vector / distance
            used.append(neighbor)
        if len(used) < 2:
            continue
        direction[center] = -np.sum(direction[used], axis=0)
        shell = tuple(sorted(int(numbers[v]) for v in used))
        motif = f"Z{int(numbers[center])}:coord:{','.join('Z'+str(v) for v in shell[:8])}:n{len(used)}"
        mode = _build_atomic_mode(
            base_frame_uid=base_frame_uid,
            base_configuration_index=base_configuration_index,
            mode_type="coordination_breathing",
            motif_key=motif,
            atom_indices=(center, *used),
            direction=direction,
            amplitude=policy.displacement_amplitude_angstrom,
        )
        candidates.append((2, (0 if center in focus else 1, -len(used), motif, center), mode))

    # One small affine strain mode per base, rotating among hydrostatic,
    # volume-preserving orthorhombic, and shear directions to keep DFT cost bounded.
    if policy.include_strain_modes and bool(np.all(atoms.pbc)) and float(abs(atoms.get_volume())) > 1.0e-12:
        strain_modes = (
            ("hydrostatic", np.eye(3, dtype=np.float64)),
            ("orthorhombic", np.diag([1.0, -1.0, 0.0])),
            ("shear_xy", np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64)),
        )
        label, tensor = strain_modes[int(strain_variant_index) % len(strain_modes)]
        mode = _build_strain_mode(
            base_frame_uid=base_frame_uid,
            base_configuration_index=base_configuration_index,
            motif_key=f"cell:{label}",
            strain_tensor=tensor,
            amplitude=policy.strain_amplitude,
        )
        candidates.append((3, (label,), mode))

    if not candidates:
        raise TrainingDataInputError("PES-VERIFY1 could not discover any stable finite-displacement modes.")

    # First purchase one representative of each available semantic mode family,
    # then fill from the deterministic residual ranking.  This avoids four nearly
    # identical shortest bonds crowding out angle/coordination/strain evidence.
    candidates.sort(key=lambda item: (item[0], item[1], item[2].mode_id))
    selected: list[PESProbeMode] = []
    seen_types: set[str] = set()
    for _, _, mode in candidates:
        if mode.mode_type not in seen_types:
            selected.append(mode)
            seen_types.add(mode.mode_type)
            if len(selected) >= policy.maximum_modes_per_base:
                break
    if len(selected) < policy.maximum_modes_per_base:
        chosen = {v.mode_id for v in selected}
        seen_motifs = {v.motif_key for v in selected}
        for _, _, mode in candidates:
            if mode.mode_id in chosen:
                continue
            # Prefer novel motif identities; allow duplicates only after all
            # novel candidates have been exhausted.
            if mode.motif_key in seen_motifs:
                continue
            selected.append(mode); chosen.add(mode.mode_id); seen_motifs.add(mode.motif_key)
            if len(selected) >= policy.maximum_modes_per_base:
                break
        if len(selected) < policy.maximum_modes_per_base:
            for _, _, mode in candidates:
                if mode.mode_id in chosen:
                    continue
                selected.append(mode); chosen.add(mode.mode_id)
                if len(selected) >= policy.maximum_modes_per_base:
                    break
    return tuple(selected)


def _apply_mode(base_atoms: Any, mode: PESProbeMode, side: int) -> Any:
    if side not in {-1, 1}:
        raise TrainingDataInputError("PES-VERIFY1 displacement side must be +/-1.")
    atoms = _copy_without_calculator(base_atoms)
    q = float(side) * mode.amplitude
    if mode.coordinate_kind == "atomic_displacement_angstrom":
        direction = np.asarray(mode.direction, dtype=np.float64)
        if direction.shape != (len(atoms), 3):
            raise TrainingDataInputError("PES-VERIFY1 atomic mode size does not match its base structure.")
        atoms.positions = np.asarray(atoms.positions, dtype=np.float64) + q * direction
    else:
        strain = np.asarray(mode.strain_tensor, dtype=np.float64)
        deformation = np.eye(3, dtype=np.float64) + q * strain
        cell = np.asarray(atoms.cell.array, dtype=np.float64)
        new_cell = cell @ deformation.T
        if float(np.linalg.det(new_cell)) <= 0.0:
            raise TrainingDataInputError("PES-VERIFY1 strain mode produced a non-positive cell volume.")
        atoms.set_cell(new_cell, scale_atoms=True)
    return atoms


def build_pes_probe_set(
    deploy_probe_set: Any,
    target_atoms: Sequence[Any],
    *,
    policy: PESVerifyPolicy | None = None,
    material_contracts: Any | None = None,
) -> tuple[PESProbeSet, tuple[Any, ...]]:
    """Build one candidate-independent finite-displacement request.

    ``target_atoms`` must be the complete target artifact indexed by the
    deployment probe-set configuration indices.  Base frames are the first
    correlation-block-round-robin deployment probes, so candidate ranking never
    influences membership.
    """

    active = PESVerifyPolicy() if policy is None else policy
    if getattr(deploy_probe_set, "selection_method", "") != "correlation_block_round_robin_v1":
        raise TrainingDataInputError("PES-VERIFY1 requires the authenticated DEPLOY-VERIFY1 block-balanced probe authority.")
    target_atoms = tuple(target_atoms)
    if not target_atoms:
        raise TrainingDataInputError("PES-VERIFY1 target artifact is empty.")
    count = min(active.maximum_base_configurations, len(deploy_probe_set.configuration_indices))
    base_frame_uids = tuple(deploy_probe_set.frame_uids[:count])
    base_indices = tuple(int(v) for v in deploy_probe_set.configuration_indices[:count])
    if any(index >= len(target_atoms) for index in base_indices):
        raise TrainingDataInputError("PES-VERIFY1 deployment probe index exceeds the target artifact.")

    modes: list[PESProbeMode] = []
    request_atoms: list[Any] = []
    probes: list[PESProbeGeometry] = []
    request_index = 0
    for base_ordinal, (frame_uid, configuration_index) in enumerate(zip(base_frame_uids, base_indices)):
        base = _copy_without_calculator(target_atoms[configuration_index])
        base_probe_uid = digest({"schema": "mdstats.pes-probe-uid.v1", "base_frame_uid": frame_uid, "side": 0})
        base.info.update(
            {
                "pes_probe_uid": base_probe_uid,
                "pes_base_frame_uid": frame_uid,
                "pes_side": 0,
                "pes_mode_id": "base",
            }
        )
        probes.append(PESProbeGeometry(
            probe_uid=base_probe_uid,
            base_frame_uid=frame_uid,
            mode_id=None,
            side=0,
            request_index=request_index,
            geometry_digest=_geometry_digest(base),
        ))
        request_atoms.append(base)
        request_index += 1
        discovered = discover_pes_probe_modes(
            base,
            base_frame_uid=frame_uid,
            base_configuration_index=configuration_index,
            policy=active,
            material_contracts=material_contracts,
            strain_variant_index=base_ordinal,
        )
        modes.extend(discovered)
        for mode in discovered:
            for side in (-1, 1):
                displaced = _apply_mode(base, mode, side)
                probe_uid = digest(
                    {
                        "schema": "mdstats.pes-probe-uid.v1",
                        "base_frame_uid": frame_uid,
                        "mode_id": mode.mode_id,
                        "side": side,
                        "amplitude": mode.amplitude,
                    }
                )
                displaced.info.update(
                    {
                        "pes_probe_uid": probe_uid,
                        "pes_base_frame_uid": frame_uid,
                        "pes_side": int(side),
                        "pes_mode_id": mode.mode_id,
                        "pes_mode_type": mode.mode_type,
                        "pes_motif_key": mode.motif_key,
                    }
                )
                probes.append(PESProbeGeometry(
                    probe_uid=probe_uid,
                    base_frame_uid=frame_uid,
                    mode_id=mode.mode_id,
                    side=side,
                    request_index=request_index,
                    geometry_digest=_geometry_digest(displaced),
                ))
                request_atoms.append(displaced)
                request_index += 1

    probe_set = PESProbeSet(
        deploy_probe_set_digest=deploy_probe_set.content_digest,
        target_role_digest=deploy_probe_set.target_role_digest,
        target_artifact_digest=deploy_probe_set.target_artifact_digest,
        target_artifact_sha256=deploy_probe_set.target_artifact_sha256,
        policy_digest=active.policy_digest,
        base_frame_uids=base_frame_uids,
        base_configuration_indices=base_indices,
        modes=tuple(modes),
        probes=tuple(probes),
    )
    return probe_set, tuple(request_atoms)


def write_pes_probe_request(
    probe_set: PESProbeSet,
    request_atoms: Sequence[Any],
    output_directory: str | Path,
) -> PESProbeRequestArtifact:
    """Write a common ExtXYZ request plus one POSCAR directory per DFT point."""

    try:
        from ase.io import write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for PES-VERIFY1 request materialization.") from exc
    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    atoms_values = tuple(_copy_without_calculator(v) for v in request_atoms)
    if len(atoms_values) != len(probe_set.probes):
        raise TrainingDataInputError("PES-VERIFY1 request atom count disagrees with probe-set identity.")
    extxyz = root / "probe-request.extxyz"
    write(extxyz, list(atoms_values), format="extxyz")
    inputs_root = root / "dft-inputs"
    inputs_root.mkdir(parents=True, exist_ok=True)
    poscar_inventory: list[tuple[str, str]] = []
    manifest_entries: list[dict[str, Any]] = []
    for probe, atoms in zip(probe_set.probes, atoms_values):
        directory = inputs_root / f"{probe.request_index:04d}-{probe.probe_uid[:12]}"
        directory.mkdir(parents=True, exist_ok=True)
        poscar = directory / "POSCAR"
        write(poscar, atoms, format="vasp", direct=True, vasp5=True)
        poscar_inventory.append((str(poscar.relative_to(root)), _sha256_file(poscar)))
        manifest_entries.append(
            {
                "request_index": probe.request_index,
                "probe_uid": probe.probe_uid,
                "base_frame_uid": probe.base_frame_uid,
                "mode_id": probe.mode_id,
                "side": probe.side,
                "geometry_digest": probe.geometry_digest,
                "directory": str(directory.relative_to(root)),
                "poscar_sha256": _sha256_file(poscar),
            }
        )
    manifest = root / "probe-manifest.json"
    manifest_payload = {
        "schema": "mdstats.pes-probe-request-manifest.v1",
        "probe_set": probe_set.to_dict(),
        "entries": manifest_entries,
        "instructions": {
            "calculation": "Run one fixed-geometry DFT single-point calculation in every listed directory using identical electronic-structure settings.",
            "required_vasp_files_for_auto_collection": ["INCAR", "KPOINTS", "POTCAR", "vasprun.xml"],
            "geometry_rule": "Do not relax ionic positions or cell; PES-VERIFY1 rejects changed probe geometry.",
        },
    }
    manifest.write_text(json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return PESProbeRequestArtifact(
        probe_set_digest=probe_set.content_digest,
        extxyz_path=str(extxyz),
        extxyz_sha256=_sha256_file(extxyz),
        manifest_path=str(manifest),
        manifest_sha256=_sha256_file(manifest),
        configuration_count=len(atoms_values),
        poscar_sha256s=tuple(poscar_inventory),
    )


def _geometry_matches(expected: Any, observed: Any, tolerance: float) -> bool:
    if tuple(int(v) for v in expected.numbers) != tuple(int(v) for v in observed.numbers):
        return False
    if tuple(bool(v) for v in expected.pbc) != tuple(bool(v) for v in observed.pbc):
        return False
    if np.max(np.abs(np.asarray(expected.cell.array) - np.asarray(observed.cell.array))) > tolerance:
        return False
    try:
        # Fractional modulo comparison handles harmless periodic wrapping.
        a = np.asarray(expected.get_scaled_positions(wrap=True), dtype=np.float64)
        b = np.asarray(observed.get_scaled_positions(wrap=True), dtype=np.float64)
        delta = a - b
        delta -= np.round(delta)
        cart = delta @ np.asarray(expected.cell.array, dtype=np.float64)
        return bool(np.max(np.linalg.norm(cart, axis=1)) <= tolerance)
    except Exception:
        return bool(np.max(np.linalg.norm(np.asarray(expected.positions) - np.asarray(observed.positions), axis=1)) <= tolerance)


def _prediction_payload_from_labeled_atoms(atoms_values: Sequence[Any]) -> dict[str, Any]:
    energies: list[float] = []
    forces: list[np.ndarray] = []
    stresses: list[np.ndarray | None] = []
    for atoms in atoms_values:
        try:
            energy = float(atoms.get_potential_energy())
            force = np.asarray(atoms.get_forces(), dtype=np.float64)
        except Exception as exc:
            raise TrainingDataInputError(f"PES-VERIFY1 reference lacks energy/force labels: {exc}") from exc
        if not math.isfinite(energy) or force.shape != (len(atoms), 3) or not np.all(np.isfinite(force)):
            raise TrainingDataInputError("PES-VERIFY1 reference contains invalid energy/force labels.")
        energies.append(energy); forces.append(force); stresses.append(_stress_matrix(atoms))
    stress_available = all(v is not None for v in stresses)
    payload: dict[str, Any] = {
        "energy": np.asarray(energies, dtype=np.float64),
        "forces_by_configuration": tuple(forces),
        "stress": None if not stress_available else np.stack([np.asarray(v) for v in stresses], axis=0),
    }
    return payload


def _prediction_digest(payload: Mapping[str, Any]) -> str:
    return digest(
        {
            "schema": "mdstats.pes-prediction-view.v1",
            "energy": np.asarray(payload["energy"], dtype=np.float64).tolist(),
            "forces": [np.asarray(v, dtype=np.float64).tolist() for v in payload["forces_by_configuration"]],
            "stress": None if payload.get("stress") is None else np.asarray(payload["stress"], dtype=np.float64).tolist(),
        }
    )


def load_pes_reference_extxyz(
    probe_set: PESProbeSet,
    request_atoms: Sequence[Any],
    reference_path: str | Path,
    *,
    policy: PESVerifyPolicy,
    protocol_digest: str,
    protocol_source: str = "external_extxyz_assertion",
    source_file_sha256s: Sequence[tuple[str, str]] = (),
) -> tuple[PESReferenceArtifact, tuple[Any, ...], dict[str, Any]]:
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for PES-VERIFY1 reference ingestion.") from exc
    target = Path(reference_path).resolve()
    if not target.is_file():
        raise TrainingDataInputError(f"PES-VERIFY1 reference artifact is missing: {target}")
    values = read(target, index=":", format="extxyz")
    if not isinstance(values, list):
        values = [values]
    if len(values) != len(probe_set.probes) or len(values) != len(request_atoms):
        raise TrainingDataInputError("PES-VERIFY1 reference configuration count changed.")
    by_uid: dict[str, Any] = {}
    if all(str(atoms.info.get("pes_probe_uid", "")).strip() for atoms in values):
        for atoms in values:
            uid = str(atoms.info["pes_probe_uid"]).strip()
            if uid in by_uid:
                raise TrainingDataInputError("PES-VERIFY1 reference contains duplicate probe UIDs.")
            by_uid[uid] = atoms
        if set(by_uid) != {v.probe_uid for v in probe_set.probes}:
            raise TrainingDataInputError("PES-VERIFY1 reference probe UID membership changed.")
        ordered = tuple(by_uid[v.probe_uid] for v in probe_set.probes)
    else:
        ordered = tuple(values)
    for expected, observed in zip(request_atoms, ordered):
        if not _geometry_matches(expected, observed, policy.geometry_match_tolerance_angstrom):
            raise TrainingDataInputError("PES-VERIFY1 DFT reference geometry changed; fixed-geometry single points are required.")
    predictions = _prediction_payload_from_labeled_atoms(ordered)
    if any(mode.coordinate_kind == "strain" for mode in probe_set.modes) and predictions["stress"] is None:
        raise TrainingDataInputError("PES-VERIFY1 strain probes require stress labels on every DFT reference configuration.")
    artifact = PESReferenceArtifact(
        probe_set_digest=probe_set.content_digest,
        reference_path=str(target),
        reference_sha256=_sha256_file(target),
        configuration_count=len(ordered),
        prediction_digest=_prediction_digest(predictions),
        protocol_digest=validate_digest(protocol_digest, name="protocol_digest"),
        protocol_source=str(protocol_source),
        source_file_sha256s=tuple(source_file_sha256s),
    )
    return artifact, ordered, predictions


def collect_pes_reference_from_vasp(
    probe_set: PESProbeSet,
    request_atoms: Sequence[Any],
    request_artifact: PESProbeRequestArtifact,
    *,
    output_path: str | Path,
    policy: PESVerifyPolicy,
) -> tuple[PESReferenceArtifact, tuple[Any, ...], dict[str, Any]] | None:
    """Auto-collect fixed-geometry VASP single points when every request dir is complete.

    The collector requires identical INCAR/KPOINTS/POTCAR bytes for every probe.
    It never copies POTCAR into campaign artifacts; only SHA-256 identities are
    persisted.
    """

    try:
        from ase.io import read, write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for PES-VERIFY1 VASP collection.") from exc
    manifest_path = Path(request_artifact.manifest_path).resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = list(manifest.get("entries", ()))
    if len(entries) != len(probe_set.probes):
        raise TrainingDataInputError("PES-VERIFY1 request manifest is inconsistent.")
    required = ("INCAR", "KPOINTS", "POTCAR", "vasprun.xml")
    directories = [(root / str(entry["directory"])).resolve() for entry in entries]
    if not all(all((directory / name).is_file() for name in required) for directory in directories):
        return None
    protocol_names = ("INCAR", "KPOINTS", "POTCAR")
    protocol_hashes: dict[str, str] = {}
    for name in protocol_names:
        hashes = {_sha256_file(directory / name) for directory in directories}
        if len(hashes) != 1:
            raise TrainingDataInputError(f"PES-VERIFY1 VASP {name} bytes differ across probe calculations.")
        protocol_hashes[name] = next(iter(hashes))
    protocol_digest = digest({"schema": "mdstats.pes-vasp-reference-protocol.v1", **protocol_hashes})
    labeled: list[Any] = []
    source_hashes: list[tuple[str, str]] = []
    for probe, expected, directory in zip(probe_set.probes, request_atoms, directories):
        vasprun = directory / "vasprun.xml"
        source_hashes.append((str(vasprun), _sha256_file(vasprun)))
        try:
            atoms = read(vasprun, index=-1)
        except Exception as exc:
            raise TrainingDataInputError(f"PES-VERIFY1 could not read {vasprun}: {exc}") from exc
        if not _geometry_matches(expected, atoms, policy.geometry_match_tolerance_angstrom):
            raise TrainingDataInputError(f"PES-VERIFY1 VASP output geometry changed for probe {probe.request_index}.")
        atoms.info.update(
            {
                "pes_probe_uid": probe.probe_uid,
                "pes_base_frame_uid": probe.base_frame_uid,
                "pes_side": probe.side,
                "pes_mode_id": "base" if probe.mode_id is None else probe.mode_id,
            }
        )
        labeled.append(atoms)
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, labeled, format="extxyz")
    return load_pes_reference_extxyz(
        probe_set,
        request_atoms,
        output,
        policy=policy,
        protocol_digest=protocol_digest,
        protocol_source="vasp_identical_input_sha256",
        source_file_sha256s=tuple(source_hashes) + tuple((name, sha) for name, sha in sorted(protocol_hashes.items())),
    )


def prediction_payload_from_mace_view(predictions: Mapping[str, np.ndarray], probe_atoms: Sequence[Any]) -> dict[str, Any]:
    energy = np.asarray(predictions["energy"], dtype=np.float64)
    if energy.shape != (len(probe_atoms),):
        raise TrainingDataInputError("PES-VERIFY1 model energy prediction shape is invalid.")
    flat = np.asarray(predictions["forces"], dtype=np.float64).reshape(-1)
    forces: list[np.ndarray] = []
    offset = 0
    for atoms in probe_atoms:
        size = len(atoms) * 3
        if offset + size > len(flat):
            raise TrainingDataInputError("PES-VERIFY1 model force prediction length is invalid.")
        forces.append(flat[offset:offset + size].reshape(len(atoms), 3))
        offset += size
    if offset != len(flat):
        raise TrainingDataInputError("PES-VERIFY1 model force prediction has trailing values.")
    stress = None
    if "stress" in predictions:
        stress = np.asarray(predictions["stress"], dtype=np.float64)
        if stress.shape != (len(probe_atoms), 3, 3):
            raise TrainingDataInputError("PES-VERIFY1 model stress prediction shape is invalid.")
    if not np.all(np.isfinite(energy)) or any(not np.all(np.isfinite(v)) for v in forces) or (stress is not None and not np.all(np.isfinite(stress))):
        raise TrainingDataInputError("PES-VERIFY1 model prediction contains non-finite values.")
    return {"energy": energy, "forces_by_configuration": tuple(forces), "stress": stress}


def _mixed_close(observed: float, reference: float, *, atol: float, rtol: float) -> bool:
    return bool(abs(observed - reference) <= atol + rtol * abs(reference))


def _sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def _base_and_sides(probe_set: PESProbeSet) -> tuple[dict[str, int], dict[str, dict[int, int]]]:
    base: dict[str, int] = {}
    sides: dict[str, dict[int, int]] = {}
    for probe in probe_set.probes:
        if probe.side == 0:
            base[probe.base_frame_uid] = probe.request_index
        else:
            assert probe.mode_id is not None
            sides.setdefault(probe.mode_id, {})[probe.side] = probe.request_index
    return base, sides


@dataclass(frozen=True, slots=True)
class PESModeMetric:
    mode_id: str
    mode_type: str
    motif_key: str
    coordinate_kind: str
    reference_energy_curvature: float
    observed_energy_curvature: float
    reference_force_or_stress_stiffness: float
    observed_force_or_stress_stiffness: float
    resolved_sign_checks: int
    sign_mismatches: int
    maximum_side_projection_error: float
    passed: bool
    rejection_reasons: tuple[str, ...]
    serialization_schema: str = field(default=PES_MODE_METRIC_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_MODE_METRIC_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 mode-metric schema.")
        object.__setattr__(self, "mode_id", validate_digest(self.mode_id, name="mode_id"))
        for name in (
            "reference_energy_curvature", "observed_energy_curvature",
            "reference_force_or_stress_stiffness", "observed_force_or_stress_stiffness",
            "maximum_side_projection_error",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value):
                raise TrainingDataInputError("PES-VERIFY1 mode metrics must be finite.")
            object.__setattr__(self, name, value)
        for name in ("resolved_sign_checks", "sign_mismatches"):
            value = int(getattr(self, name))
            if value < 0:
                raise TrainingDataInputError("PES-VERIFY1 sign counts cannot be negative.")
            object.__setattr__(self, name, value)
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        object.__setattr__(self, "rejection_reasons", reasons)
        if bool(self.passed) != (len(reasons) == 0):
            raise TrainingDataInputError("PES-VERIFY1 mode pass flag disagrees with rejection reasons.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "mode_id": self.mode_id,
            "mode_type": self.mode_type,
            "motif_key": self.motif_key,
            "coordinate_kind": self.coordinate_kind,
            "reference_energy_curvature": self.reference_energy_curvature,
            "observed_energy_curvature": self.observed_energy_curvature,
            "reference_force_or_stress_stiffness": self.reference_force_or_stress_stiffness,
            "observed_force_or_stress_stiffness": self.observed_force_or_stress_stiffness,
            "resolved_sign_checks": self.resolved_sign_checks,
            "sign_mismatches": self.sign_mismatches,
            "maximum_side_projection_error": self.maximum_side_projection_error,
            "passed": bool(self.passed),
            "rejection_reasons": list(self.rejection_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESModeMetric":
        result = cls(
            mode_id=str(payload["mode_id"]), mode_type=str(payload["mode_type"]), motif_key=str(payload["motif_key"]), coordinate_kind=str(payload["coordinate_kind"]),
            reference_energy_curvature=float(payload["reference_energy_curvature"]), observed_energy_curvature=float(payload["observed_energy_curvature"]),
            reference_force_or_stress_stiffness=float(payload["reference_force_or_stress_stiffness"]), observed_force_or_stress_stiffness=float(payload["observed_force_or_stress_stiffness"]),
            resolved_sign_checks=int(payload["resolved_sign_checks"]), sign_mismatches=int(payload["sign_mismatches"]),
            maximum_side_projection_error=float(payload["maximum_side_projection_error"]), passed=bool(payload["passed"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
        )
        if payload.get("schema") != PES_MODE_METRIC_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 mode metric is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class PESModelQualification:
    model_role: str
    model_sha256: str
    prediction_digest: str
    mode_metrics: tuple[PESModeMetric, ...]
    passed: bool
    failed_mode_count: int
    restoring_sign_mismatch_count: int
    serialization_schema: str = field(default=PES_MODEL_QUALIFICATION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_MODEL_QUALIFICATION_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 model qualification schema.")
        if self.model_role not in {"foundation", "candidate"}:
            raise TrainingDataInputError("PES-VERIFY1 model role is invalid.")
        object.__setattr__(self, "model_sha256", validate_digest(self.model_sha256, name="model_sha256"))
        object.__setattr__(self, "prediction_digest", validate_digest(self.prediction_digest, name="prediction_digest"))
        metrics = tuple(self.mode_metrics)
        if not metrics or len({v.mode_id for v in metrics}) != len(metrics):
            raise TrainingDataInputError("PES-VERIFY1 model qualification requires unique mode metrics.")
        object.__setattr__(self, "mode_metrics", metrics)
        failed = sum(not v.passed for v in metrics)
        signs = sum(v.sign_mismatches for v in metrics)
        if int(self.failed_mode_count) != failed or int(self.restoring_sign_mismatch_count) != signs:
            raise TrainingDataInputError("PES-VERIFY1 model summary counts are inconsistent.")
        if bool(self.passed) != (failed == 0):
            raise TrainingDataInputError("PES-VERIFY1 model pass flag disagrees with mode evidence.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "model_role": self.model_role,
            "model_sha256": self.model_sha256,
            "prediction_digest": self.prediction_digest,
            "mode_metrics": [v.to_dict() for v in self.mode_metrics],
            "passed": bool(self.passed),
            "failed_mode_count": self.failed_mode_count,
            "restoring_sign_mismatch_count": self.restoring_sign_mismatch_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESModelQualification":
        result = cls(
            model_role=str(payload["model_role"]), model_sha256=str(payload["model_sha256"]), prediction_digest=str(payload["prediction_digest"]),
            mode_metrics=tuple(PESModeMetric.from_dict(v) for v in payload["mode_metrics"]), passed=bool(payload["passed"]),
            failed_mode_count=int(payload["failed_mode_count"]), restoring_sign_mismatch_count=int(payload["restoring_sign_mismatch_count"]),
        )
        if payload.get("schema") != PES_MODEL_QUALIFICATION_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 model qualification is corrupt.")
        return result


def assess_pes_model(
    probe_set: PESProbeSet,
    reference: Mapping[str, Any],
    observed: Mapping[str, Any],
    *,
    policy: PESVerifyPolicy,
    model_role: str,
    model_sha256: str,
) -> PESModelQualification:
    """Compare one model against the matched DFT local-PES probe evidence."""

    base_index, side_index = _base_and_sides(probe_set)
    ref_e = np.asarray(reference["energy"], dtype=np.float64)
    obs_e = np.asarray(observed["energy"], dtype=np.float64)
    ref_f = tuple(np.asarray(v, dtype=np.float64) for v in reference["forces_by_configuration"])
    obs_f = tuple(np.asarray(v, dtype=np.float64) for v in observed["forces_by_configuration"])
    ref_s = None if reference.get("stress") is None else np.asarray(reference["stress"], dtype=np.float64)
    obs_s = None if observed.get("stress") is None else np.asarray(observed["stress"], dtype=np.float64)
    if ref_e.shape != obs_e.shape or len(ref_f) != len(obs_f) or len(ref_e) != len(probe_set.probes):
        raise TrainingDataInputError("PES-VERIFY1 model/reference prediction membership changed.")

    metrics: list[PESModeMetric] = []
    for mode in probe_set.modes:
        i0 = base_index[mode.base_frame_uid]
        im = side_index[mode.mode_id][-1]
        ip = side_index[mode.mode_id][1]
        q = float(mode.amplitude)
        reasons: list[str] = []
        resolved_sign_checks = 0
        sign_mismatches = 0
        side_errors: list[float] = []
        if mode.coordinate_kind == "atomic_displacement_angstrom":
            direction = np.asarray(mode.direction, dtype=np.float64)
            ref_proj = [float(np.sum(ref_f[idx] * direction)) for idx in (im, i0, ip)]
            obs_proj = [float(np.sum(obs_f[idx] * direction)) for idx in (im, i0, ip)]
            ref_delta = (ref_proj[0] - ref_proj[1], ref_proj[2] - ref_proj[1])
            obs_delta = (obs_proj[0] - obs_proj[1], obs_proj[2] - obs_proj[1])
            for side_name, r, o in (("minus", ref_delta[0], obs_delta[0]), ("plus", ref_delta[1], obs_delta[1])):
                side_errors.append(abs(o - r))
                if not _mixed_close(o, r, atol=policy.projected_force_atol_ev_per_angstrom, rtol=policy.projected_force_rtol):
                    reasons.append(f"projected_force_{side_name}_mismatch")
                if abs(r) >= policy.restoring_force_resolution_floor_ev_per_angstrom:
                    resolved_sign_checks += 1
                    if _sign(o) != _sign(r):
                        sign_mismatches += 1
                        reasons.append(f"projected_force_{side_name}_direction_mismatch")
            ref_stiff = -(ref_proj[2] - ref_proj[0]) / (2.0 * q)
            obs_stiff = -(obs_proj[2] - obs_proj[0]) / (2.0 * q)
            if not _mixed_close(obs_stiff, ref_stiff, atol=policy.force_stiffness_atol_ev_per_angstrom2, rtol=policy.force_stiffness_rtol):
                reasons.append("force_stiffness_mismatch")
            if abs(ref_stiff) >= policy.stiffness_sign_resolution_floor_ev_per_angstrom2 and _sign(obs_stiff) != _sign(ref_stiff):
                reasons.append("force_stiffness_direction_mismatch")
            ref_ec = float((ref_e[ip] + ref_e[im] - 2.0 * ref_e[i0]) / (q * q))
            obs_ec = float((obs_e[ip] + obs_e[im] - 2.0 * obs_e[i0]) / (q * q))
            if not _mixed_close(obs_ec, ref_ec, atol=policy.energy_curvature_atol_ev_per_angstrom2, rtol=policy.energy_curvature_rtol):
                reasons.append("energy_curvature_mismatch")
            if abs(ref_ec) >= policy.stiffness_sign_resolution_floor_ev_per_angstrom2 and _sign(obs_ec) != _sign(ref_ec):
                reasons.append("energy_curvature_direction_mismatch")
        else:
            if ref_s is None or obs_s is None:
                reasons.append("strain_stress_unavailable")
                ref_stiff = obs_stiff = 0.0
                ref_ec = obs_ec = 0.0
                side_errors = [float("inf")]
            else:
                tensor = np.asarray(mode.strain_tensor, dtype=np.float64)
                ref_proj = [float(np.sum(ref_s[idx] * tensor)) for idx in (im, i0, ip)]
                obs_proj = [float(np.sum(obs_s[idx] * tensor)) for idx in (im, i0, ip)]
                ref_delta = (ref_proj[0] - ref_proj[1], ref_proj[2] - ref_proj[1])
                obs_delta = (obs_proj[0] - obs_proj[1], obs_proj[2] - obs_proj[1])
                for side_name, r, o in (("minus", ref_delta[0], obs_delta[0]), ("plus", ref_delta[1], obs_delta[1])):
                    side_errors.append(abs(o - r))
                    if not _mixed_close(o, r, atol=policy.strain_stress_atol_ev_per_angstrom3, rtol=policy.strain_stress_rtol):
                        reasons.append(f"strain_stress_{side_name}_mismatch")
                    if abs(r) >= policy.strain_stress_resolution_floor_ev_per_angstrom3:
                        resolved_sign_checks += 1
                        if _sign(o) != _sign(r):
                            sign_mismatches += 1
                            reasons.append(f"strain_stress_{side_name}_direction_mismatch")
                ref_stiff = float((ref_proj[2] - ref_proj[0]) / (2.0 * q))
                obs_stiff = float((obs_proj[2] - obs_proj[0]) / (2.0 * q))
                # Stress slope shares stress units per unit strain. Reuse the
                # side tolerance scaled by 1/q only for an aggregate curvature check.
                stress_slope_atol = policy.strain_stress_atol_ev_per_angstrom3 / max(q, 1.0e-12)
                if not _mixed_close(obs_stiff, ref_stiff, atol=stress_slope_atol, rtol=policy.strain_stress_rtol):
                    reasons.append("strain_stress_stiffness_mismatch")
                natoms = len(ref_f[i0])
                ref_ec = float((ref_e[ip] + ref_e[im] - 2.0 * ref_e[i0]) / (q * q * natoms))
                obs_ec = float((obs_e[ip] + obs_e[im] - 2.0 * obs_e[i0]) / (q * q * natoms))
                if not _mixed_close(obs_ec, ref_ec, atol=policy.strain_energy_curvature_atol_ev_per_atom, rtol=policy.strain_energy_curvature_rtol):
                    reasons.append("strain_energy_curvature_mismatch")
        metrics.append(PESModeMetric(
            mode_id=mode.mode_id,
            mode_type=mode.mode_type,
            motif_key=mode.motif_key,
            coordinate_kind=mode.coordinate_kind,
            reference_energy_curvature=ref_ec,
            observed_energy_curvature=obs_ec,
            reference_force_or_stress_stiffness=ref_stiff,
            observed_force_or_stress_stiffness=obs_stiff,
            resolved_sign_checks=resolved_sign_checks,
            sign_mismatches=sign_mismatches,
            maximum_side_projection_error=max(side_errors) if side_errors and all(math.isfinite(v) for v in side_errors) else 1.0e300,
            passed=(len(reasons) == 0),
            rejection_reasons=tuple(reasons),
        ))
    failed = sum(not v.passed for v in metrics)
    # PES-VERIFY1 v1 is an all-mode hard qualification gate.
    passed = failed == 0
    return PESModelQualification(
        model_role=model_role,
        model_sha256=validate_digest(model_sha256, name="model_sha256"),
        prediction_digest=_prediction_digest(observed),
        mode_metrics=tuple(metrics),
        passed=passed,
        failed_mode_count=failed,
        restoring_sign_mismatch_count=sum(v.sign_mismatches for v in metrics),
    )


@dataclass(frozen=True, slots=True)
class PESVerifyRunRecord:
    run_plan_digest: str
    deploy_verify_run_digest: str
    candidate_model_path: str
    candidate_model_sha256: str
    candidate_qualification: PESModelQualification
    serialization_schema: str = field(default=PES_RUN_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != PES_RUN_RECORD_SCHEMA:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 run schema.")
        object.__setattr__(self, "run_plan_digest", validate_digest(self.run_plan_digest, name="run_plan_digest"))
        object.__setattr__(self, "deploy_verify_run_digest", validate_digest(self.deploy_verify_run_digest, name="deploy_verify_run_digest"))
        object.__setattr__(self, "candidate_model_sha256", validate_digest(self.candidate_model_sha256, name="candidate_model_sha256"))
        if self.candidate_qualification.model_role != "candidate" or self.candidate_qualification.model_sha256 != self.candidate_model_sha256:
            raise TrainingDataInputError("PES-VERIFY1 candidate qualification identity mismatch.")

    @property
    def passed(self) -> bool:
        return self.candidate_qualification.passed

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "deploy_verify_run_digest": self.deploy_verify_run_digest,
            "candidate_model_path": self.candidate_model_path,
            "candidate_model_sha256": self.candidate_model_sha256,
            "candidate_qualification": self.candidate_qualification.to_dict(),
            "passed": bool(self.passed),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESVerifyRunRecord":
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]), deploy_verify_run_digest=str(payload["deploy_verify_run_digest"]),
            candidate_model_path=str(payload["candidate_model_path"]), candidate_model_sha256=str(payload["candidate_model_sha256"]),
            candidate_qualification=PESModelQualification.from_dict(payload["candidate_qualification"]),
        )
        if payload.get("schema") != PES_RUN_RECORD_SCHEMA or payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 run record is corrupt.")
        return result


@dataclass(frozen=True, slots=True)
class PESVerifyCampaignRecord:
    campaign_plan_digest: str
    deploy_verify_campaign_digest: str
    foundation_audit_digest: str
    foundation_model_sha256: str
    policy: PESVerifyPolicy
    probe_set: PESProbeSet
    probe_request: PESProbeRequestArtifact
    reference_artifact: PESReferenceArtifact
    foundation_qualification: PESModelQualification
    run_records: tuple[PESVerifyRunRecord, ...]
    stage_context: str
    foundation_head_name: str | None = None
    foundation_potential_identity: FoundationPotentialIdentity | None = None
    foundation_inference_identity: FoundationInferenceIdentity | None = None
    serialization_schema: str = field(default=PES_CAMPAIGN_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {PES_CAMPAIGN_RECORD_SCHEMA, PES_CAMPAIGN_RECORD_V1_SCHEMA}:
            raise TrainingDataInputError("Unsupported PES-VERIFY1 campaign schema.")
        if (self.foundation_potential_identity is None) != (self.foundation_inference_identity is None):
            raise TrainingDataInputError("PES-VERIFY1 foundation potential/inference identities must be both present or both absent.")
        if self.foundation_potential_identity is None and self.serialization_schema == PES_CAMPAIGN_RECORD_SCHEMA:
            object.__setattr__(self, "serialization_schema", PES_CAMPAIGN_RECORD_V1_SCHEMA)
        if self.foundation_potential_identity is not None:
            if self.serialization_schema != PES_CAMPAIGN_RECORD_SCHEMA:
                raise TrainingDataInputError("Canonical PES foundation identities require the v2 campaign schema.")
            if self.foundation_inference_identity.foundation_potential_digest != self.foundation_potential_identity.canonical_content_digest:
                raise TrainingDataInputError("PES foundation inference/potential identities disagree.")
            if self.foundation_model_sha256 != self.foundation_potential_identity.sha256:
                raise TrainingDataInputError("PES foundation SHA disagrees with canonical potential identity.")
            if self.foundation_head_name not in (None, "", self.foundation_potential_identity.foundation_head):
                raise TrainingDataInputError("PES legacy foundation-head mirror conflicts with canonical potential identity.")
            object.__setattr__(self, "foundation_head_name", self.foundation_potential_identity.foundation_head)
        for name in ("campaign_plan_digest", "deploy_verify_campaign_digest", "foundation_audit_digest", "foundation_model_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.probe_set.policy_digest != self.policy.policy_digest or self.probe_request.probe_set_digest != self.probe_set.content_digest or self.reference_artifact.probe_set_digest != self.probe_set.content_digest:
            raise TrainingDataInputError("PES-VERIFY1 campaign probe/policy identities disagree.")
        if self.foundation_qualification.model_role != "foundation" or self.foundation_qualification.model_sha256 != self.foundation_model_sha256:
            raise TrainingDataInputError("PES-VERIFY1 foundation qualification identity mismatch.")
        if self.foundation_potential_identity is None:
            head = None if self.foundation_head_name is None else str(self.foundation_head_name).strip()
            object.__setattr__(self, "foundation_head_name", head or None)
        records = tuple(sorted(self.run_records, key=lambda v: v.run_plan_digest))
        if not records or len({v.run_plan_digest for v in records}) != len(records):
            raise TrainingDataInputError("PES-VERIFY1 campaign requires unique candidate run evidence.")
        if self.stage_context != "production":
            raise TrainingDataInputError("PES-VERIFY1 is post-selection production verification only.")
        object.__setattr__(self, "run_records", records)

    @property
    def passed_run_count(self) -> int:
        return sum(v.passed for v in self.run_records)

    @property
    def all_candidates_failed(self) -> bool:
        return self.passed_run_count == 0

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "deploy_verify_campaign_digest": self.deploy_verify_campaign_digest,
            "foundation_audit_digest": self.foundation_audit_digest,
            "foundation_model_sha256": self.foundation_model_sha256,
            "policy": self.policy.to_dict(),
            "probe_set": self.probe_set.to_dict(),
            "probe_request": self.probe_request.to_dict(),
            "reference_artifact": self.reference_artifact.to_dict(),
            "foundation_qualification": self.foundation_qualification.to_dict(),
            "run_records": [v.to_dict() for v in self.run_records],
            "stage_context": self.stage_context,
            "foundation_head_name": self.foundation_head_name,
            **(
                {
                    "foundation_potential_identity": self.foundation_potential_identity.to_dict(),
                    "foundation_inference_identity": self.foundation_inference_identity.to_dict(),
                }
                if self.serialization_schema == PES_CAMPAIGN_RECORD_SCHEMA
                else {}
            ),
            "passed_run_count": self.passed_run_count,
            "all_candidates_failed": self.all_candidates_failed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PESVerifyCampaignRecord":
        if payload.get("schema") not in {PES_CAMPAIGN_RECORD_SCHEMA, PES_CAMPAIGN_RECORD_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported PES-VERIFY1 campaign schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            deploy_verify_campaign_digest=str(payload["deploy_verify_campaign_digest"]),
            foundation_audit_digest=str(payload["foundation_audit_digest"]),
            foundation_model_sha256=str(payload["foundation_model_sha256"]),
            policy=PESVerifyPolicy.from_dict(payload["policy"]),
            probe_set=PESProbeSet.from_dict(payload["probe_set"]),
            probe_request=PESProbeRequestArtifact.from_dict(payload["probe_request"]),
            reference_artifact=PESReferenceArtifact.from_dict(payload["reference_artifact"]),
            foundation_qualification=PESModelQualification.from_dict(payload["foundation_qualification"]),
            run_records=tuple(PESVerifyRunRecord.from_dict(v) for v in payload["run_records"]),
            stage_context=str(payload["stage_context"]),
            foundation_head_name=(None if payload.get("foundation_head_name") in (None, "") else str(payload.get("foundation_head_name"))),
            foundation_potential_identity=(None if payload.get("foundation_potential_identity") is None else FoundationPotentialIdentity.from_dict(payload["foundation_potential_identity"])),
            foundation_inference_identity=(None if payload.get("foundation_inference_identity") is None else FoundationInferenceIdentity.from_dict(payload["foundation_inference_identity"])),
            serialization_schema=str(payload["schema"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PES-VERIFY1 campaign digest mismatch.")
        return result


__all__ = [
    "PES_VERIFY_IMPLEMENTATION_VERSION",
    "PESVerifyPolicy",
    "PESProbeMode",
    "PESProbeGeometry",
    "PESProbeSet",
    "PESProbeRequestArtifact",
    "PESReferenceArtifact",
    "PESModeMetric",
    "PESModelQualification",
    "PESVerifyRunRecord",
    "PESVerifyCampaignRecord",
    "discover_pes_probe_modes",
    "build_pes_probe_set",
    "write_pes_probe_request",
    "load_pes_reference_extxyz",
    "collect_pes_reference_from_vasp",
    "prediction_payload_from_mace_view",
    "assess_pes_model",
]
