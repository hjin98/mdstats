"""Stage-11E8a-S3 structural mapping and temporal-support preparation.

The stage maps the source-bound central Na-density attractors onto the packaged
persistent Na-LTA primitive-ring topology without replacing the actual
serrated oxygen polygons by circles or ellipses.  It then transfers the signed
spatial partition from the represented-time quadrature catalog to the exact
full-weight coordinate-identical sample catalog and executes the Stage-11E4
provisional temporal assignment.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
from importlib.resources import files as resource_files
import json
from pathlib import Path
from time import perf_counter
from types import MappingProxyType
from typing import Any

import numpy as np

from ...collection import AtomisticFrameCollection
from ..framework_topology import FrameworkTopology
from ..primitive_ring import PrimitiveRingCatalog, expand_primitive_ring_atomic_walk
from .attractors import DensityAttractorCatalog
from ._pilot_common import (
    array_digest as _array_digest,
    array_payload_bytes as _array_payload_bytes,
    canonical_json as _canonical_json,
    digest as _digest,
    freeze as _freeze,
    json_value as _json_value,
    nonnegative as _nonnegative,
    positive as _positive,
    positive_int as _positive_int,
    readonly_array as _readonly,
    replace_evidence as _replace_evidence,
)

from .pilot_audit import (
    NaLta300KPilotReport,
    PilotAuditInputError,
    PilotAuditResourcePolicy,
    PilotEvidenceRecord,
    PilotEvidenceStatus,
    PilotPMFStatus,
    PilotRateStatus,
    PilotResourceUsage,
    PilotScientificOutcome,
    prepare_na_lta_300k_pilot_report,
)
from .pilot_density_attractors import NaLta300KDensityAttractorPilotOptions
from .pilot_refinement_lineage import (
    NaLta300KRefinementLineageOptions,
    NaLta300KRefinementLineagePilot,
    prepare_na_lta_300k_refinement_lineage_pilot,
)
from .species import SpeciesDensityResourcePolicy
from .attractors import DensityAttractorOptions, DensityAttractorResourcePolicy
from .temporal_assignment import (
    ProvisionalTemporalAssignmentCatalog,
    RawMembershipClass,
    TemporalAssignmentOptions,
    TemporalAssignmentResourcePolicy,
    TemporalSupportStatus,
    prepare_provisional_temporal_assignment,
)

PILOT_STRUCTURAL_TEMPORAL_STAGE = "11E8a-S3"
PILOT_STRUCTURAL_TEMPORAL_OPTIONS_SCHEMA = "mdstats.na-lta-300k-structural-temporal-options.v1"
RING_GEOMETRY_SCHEMA = "mdstats.na-lta-ring-geometry-snapshot.v1"
ATTRACTOR_RING_CANDIDATE_SCHEMA = "mdstats.na-lta-attractor-ring-candidate.v1"
ATTRACTOR_STRUCTURAL_MAPPING_SCHEMA = "mdstats.na-lta-attractor-structural-mapping.v1"
STRUCTURAL_MAPPING_CATALOG_SCHEMA = "mdstats.na-lta-structural-mapping-catalog.v1"
























class StructuralMappingStatus(str, Enum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    OUTSIDE_LIMIT = "outside_limit"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class NaLta300KStructuralTemporalOptions:
    maximum_ring_association_distance_angstrom: float = 2.75
    minimum_unique_margin_angstrom: float = 0.12
    candidate_count: int = 3
    maximum_ring_planarity_rms_angstrom: float = 0.50
    minimum_framework_bond_angstrom: float = 1.20
    maximum_framework_bond_angstrom: float = 2.20
    temporal_options: TemporalAssignmentOptions = field(default_factory=TemporalAssignmentOptions)
    signature: str = ""

    def __post_init__(self) -> None:
        maximum = _positive(self.maximum_ring_association_distance_angstrom, "maximum_ring_association_distance_angstrom")
        margin = _nonnegative(self.minimum_unique_margin_angstrom, "minimum_unique_margin_angstrom")
        count = _positive_int(self.candidate_count, "candidate_count")
        planarity = _positive(self.maximum_ring_planarity_rms_angstrom, "maximum_ring_planarity_rms_angstrom")
        minimum_bond = _positive(self.minimum_framework_bond_angstrom, "minimum_framework_bond_angstrom")
        maximum_bond = _positive(self.maximum_framework_bond_angstrom, "maximum_framework_bond_angstrom")
        if minimum_bond >= maximum_bond:
            raise PilotAuditInputError("minimum_framework_bond_angstrom must be smaller than maximum_framework_bond_angstrom.")
        if not isinstance(self.temporal_options, TemporalAssignmentOptions):
            raise PilotAuditInputError("temporal_options must be TemporalAssignmentOptions.")
        payload = {
            "schema": PILOT_STRUCTURAL_TEMPORAL_OPTIONS_SCHEMA,
            "maximum_ring_association_distance_angstrom": maximum,
            "minimum_unique_margin_angstrom": margin,
            "candidate_count": count,
            "maximum_ring_planarity_rms_angstrom": planarity,
            "minimum_framework_bond_angstrom": minimum_bond,
            "maximum_framework_bond_angstrom": maximum_bond,
            "temporal_options_signature": self.temporal_options.signature,
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("S3 options signature is inconsistent.")
        object.__setattr__(self, "maximum_ring_association_distance_angstrom", maximum)
        object.__setattr__(self, "minimum_unique_margin_angstrom", margin)
        object.__setattr__(self, "candidate_count", count)
        object.__setattr__(self, "maximum_ring_planarity_rms_angstrom", planarity)
        object.__setattr__(self, "minimum_framework_bond_angstrom", minimum_bond)
        object.__setattr__(self, "maximum_framework_bond_angstrom", maximum_bond)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PILOT_STRUCTURAL_TEMPORAL_OPTIONS_SCHEMA,
            "maximum_ring_association_distance_angstrom": self.maximum_ring_association_distance_angstrom,
            "minimum_unique_margin_angstrom": self.minimum_unique_margin_angstrom,
            "candidate_count": self.candidate_count,
            "maximum_ring_planarity_rms_angstrom": self.maximum_ring_planarity_rms_angstrom,
            "minimum_framework_bond_angstrom": self.minimum_framework_bond_angstrom,
            "maximum_framework_bond_angstrom": self.maximum_framework_bond_angstrom,
            "temporal_options": self.temporal_options.to_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaLta300KStructuralTemporalOptions":
        if payload.get("schema") != PILOT_STRUCTURAL_TEMPORAL_OPTIONS_SCHEMA:
            raise PilotAuditInputError("Unsupported S3 options schema.")
        return cls(
            maximum_ring_association_distance_angstrom=float(payload["maximum_ring_association_distance_angstrom"]),
            minimum_unique_margin_angstrom=float(payload["minimum_unique_margin_angstrom"]),
            candidate_count=int(payload["candidate_count"]),
            maximum_ring_planarity_rms_angstrom=float(payload["maximum_ring_planarity_rms_angstrom"]),
            minimum_framework_bond_angstrom=float(payload["minimum_framework_bond_angstrom"]),
            maximum_framework_bond_angstrom=float(payload["maximum_framework_bond_angstrom"]),
            temporal_options=TemporalAssignmentOptions.from_dict(payload["temporal_options"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class RingGeometrySnapshot:
    ring_id: int
    ring_size: int
    oxygen_atom_indices: tuple[int, ...]
    center_fractional: np.ndarray
    center_cartesian: np.ndarray
    normal_cartesian: np.ndarray
    basis_u_cartesian: np.ndarray
    basis_v_cartesian: np.ndarray
    oxygen_polygon_xy: np.ndarray
    mean_oxygen_radius_angstrom: float
    minimum_oxygen_radius_angstrom: float
    maximum_oxygen_radius_angstrom: float
    planarity_rms_angstrom: float
    signature: str = ""

    def __post_init__(self) -> None:
        identifier = int(self.ring_id); size = int(self.ring_size)
        oxygen = tuple(int(v) for v in self.oxygen_atom_indices)
        if identifier < 0 or size < 3 or len(oxygen) != size:
            raise PilotAuditInputError("Ring geometry identifiers are inconsistent.")
        arrays = {
            "center_fractional": _readonly(self.center_fractional, dtype=float, ndim=1, name="center_fractional", shape=(3,)),
            "center_cartesian": _readonly(self.center_cartesian, dtype=float, ndim=1, name="center_cartesian", shape=(3,)),
            "normal_cartesian": _readonly(self.normal_cartesian, dtype=float, ndim=1, name="normal_cartesian", shape=(3,)),
            "basis_u_cartesian": _readonly(self.basis_u_cartesian, dtype=float, ndim=1, name="basis_u_cartesian", shape=(3,)),
            "basis_v_cartesian": _readonly(self.basis_v_cartesian, dtype=float, ndim=1, name="basis_v_cartesian", shape=(3,)),
            "oxygen_polygon_xy": _readonly(self.oxygen_polygon_xy, dtype=float, ndim=2, name="oxygen_polygon_xy", shape=(size, 2)),
        }
        radii = {
            "mean_oxygen_radius_angstrom": _positive(self.mean_oxygen_radius_angstrom, "mean_oxygen_radius_angstrom"),
            "minimum_oxygen_radius_angstrom": _positive(self.minimum_oxygen_radius_angstrom, "minimum_oxygen_radius_angstrom"),
            "maximum_oxygen_radius_angstrom": _positive(self.maximum_oxygen_radius_angstrom, "maximum_oxygen_radius_angstrom"),
            "planarity_rms_angstrom": _nonnegative(self.planarity_rms_angstrom, "planarity_rms_angstrom"),
        }
        payload = {"schema": RING_GEOMETRY_SCHEMA, "ring_id": identifier, "ring_size": size, "oxygen_atom_indices": list(oxygen),
                   **{f"{k}_digest": _array_digest(v) for k, v in arrays.items()}, **radii}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise PilotAuditInputError("Ring geometry signature is inconsistent.")
        object.__setattr__(self, "ring_id", identifier); object.__setattr__(self, "ring_size", size); object.__setattr__(self, "oxygen_atom_indices", oxygen)
        for name, value in arrays.items(): object.__setattr__(self, name, value)
        for name, value in radii.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": RING_GEOMETRY_SCHEMA, "ring_id": self.ring_id, "ring_size": self.ring_size,
                "oxygen_atom_indices": list(self.oxygen_atom_indices), "center_fractional": self.center_fractional.tolist(),
                "center_cartesian": self.center_cartesian.tolist(), "normal_cartesian": self.normal_cartesian.tolist(),
                "basis_u_cartesian": self.basis_u_cartesian.tolist(), "basis_v_cartesian": self.basis_v_cartesian.tolist(),
                "oxygen_polygon_xy": self.oxygen_polygon_xy.tolist(), "mean_oxygen_radius_angstrom": self.mean_oxygen_radius_angstrom,
                "minimum_oxygen_radius_angstrom": self.minimum_oxygen_radius_angstrom, "maximum_oxygen_radius_angstrom": self.maximum_oxygen_radius_angstrom,
                "planarity_rms_angstrom": self.planarity_rms_angstrom, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingGeometrySnapshot":
        if payload.get("schema") != RING_GEOMETRY_SCHEMA: raise PilotAuditInputError("Unsupported ring geometry schema.")
        return cls(ring_id=int(payload["ring_id"]), ring_size=int(payload["ring_size"]), oxygen_atom_indices=tuple(payload["oxygen_atom_indices"]),
                   center_fractional=np.asarray(payload["center_fractional"]), center_cartesian=np.asarray(payload["center_cartesian"]),
                   normal_cartesian=np.asarray(payload["normal_cartesian"]), basis_u_cartesian=np.asarray(payload["basis_u_cartesian"]),
                   basis_v_cartesian=np.asarray(payload["basis_v_cartesian"]), oxygen_polygon_xy=np.asarray(payload["oxygen_polygon_xy"]),
                   mean_oxygen_radius_angstrom=float(payload["mean_oxygen_radius_angstrom"]), minimum_oxygen_radius_angstrom=float(payload["minimum_oxygen_radius_angstrom"]),
                   maximum_oxygen_radius_angstrom=float(payload["maximum_oxygen_radius_angstrom"]), planarity_rms_angstrom=float(payload["planarity_rms_angstrom"]),
                   signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class AttractorRingCandidate:
    ring_id: int
    ring_size: int
    association_distance_angstrom: float
    center_distance_angstrom: float
    signed_plane_distance_angstrom: float
    polygon_clearance_angstrom: float
    radial_fraction_of_serrated_boundary: float
    inside_projected_polygon: bool
    side_sign: int
    signature: str = ""

    def __post_init__(self) -> None:
        ring_id = int(self.ring_id); ring_size = int(self.ring_size); side = int(self.side_sign)
        if ring_id < 0 or ring_size < 3 or side not in {-1, 0, 1}: raise PilotAuditInputError("Invalid ring candidate identifiers.")
        values = {
            "association_distance_angstrom": _nonnegative(self.association_distance_angstrom, "association_distance_angstrom"),
            "center_distance_angstrom": _nonnegative(self.center_distance_angstrom, "center_distance_angstrom"),
            "signed_plane_distance_angstrom": float(self.signed_plane_distance_angstrom),
            "polygon_clearance_angstrom": float(self.polygon_clearance_angstrom),
            "radial_fraction_of_serrated_boundary": _nonnegative(self.radial_fraction_of_serrated_boundary, "radial_fraction_of_serrated_boundary"),
        }
        if any(not np.isfinite(v) for v in values.values()): raise PilotAuditInputError("Ring candidate contains non-finite values.")
        payload = {"schema": ATTRACTOR_RING_CANDIDATE_SCHEMA, "ring_id": ring_id, "ring_size": ring_size, **values,
                   "inside_projected_polygon": bool(self.inside_projected_polygon), "side_sign": side}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise PilotAuditInputError("Ring candidate signature is inconsistent.")
        object.__setattr__(self, "ring_id", ring_id); object.__setattr__(self, "ring_size", ring_size); object.__setattr__(self, "side_sign", side)
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "inside_projected_polygon", bool(self.inside_projected_polygon)); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ATTRACTOR_RING_CANDIDATE_SCHEMA, **{f.name: getattr(self, f.name) for f in fields(self)}}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AttractorRingCandidate":
        if payload.get("schema") != ATTRACTOR_RING_CANDIDATE_SCHEMA: raise PilotAuditInputError("Unsupported ring candidate schema.")
        return cls(**{k: v for k, v in payload.items() if k != "schema"})


@dataclass(frozen=True, slots=True)
class AttractorStructuralMapping:
    attractor_id: int
    status: StructuralMappingStatus
    candidates: tuple[AttractorRingCandidate, ...]
    unique_margin_angstrom: float | None
    signature: str = ""

    def __post_init__(self) -> None:
        identifier = int(self.attractor_id); status = StructuralMappingStatus(self.status); candidates = tuple(self.candidates)
        if identifier < 0 or not candidates: raise PilotAuditInputError("Attractor mapping requires candidates.")
        margin = None if self.unique_margin_angstrom is None else _nonnegative(self.unique_margin_angstrom, "unique_margin_angstrom")
        payload = {"schema": ATTRACTOR_STRUCTURAL_MAPPING_SCHEMA, "attractor_id": identifier, "status": status.value,
                   "candidate_signatures": [item.signature for item in candidates], "unique_margin_angstrom": margin}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise PilotAuditInputError("Attractor mapping signature is inconsistent.")
        object.__setattr__(self, "attractor_id", identifier); object.__setattr__(self, "status", status); object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "unique_margin_angstrom", margin); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ATTRACTOR_STRUCTURAL_MAPPING_SCHEMA, "attractor_id": self.attractor_id, "status": self.status.value,
                "candidates": [item.to_dict() for item in self.candidates], "unique_margin_angstrom": self.unique_margin_angstrom,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AttractorStructuralMapping":
        if payload.get("schema") != ATTRACTOR_STRUCTURAL_MAPPING_SCHEMA: raise PilotAuditInputError("Unsupported attractor mapping schema.")
        return cls(attractor_id=int(payload["attractor_id"]), status=StructuralMappingStatus(payload["status"]),
                   candidates=tuple(AttractorRingCandidate.from_dict(v) for v in payload["candidates"]),
                   unique_margin_angstrom=payload.get("unique_margin_angstrom"), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralMappingCatalog:
    trajectory_digest: str
    registration_signature: str
    attractor_catalog_signature: str
    topology_digest: str
    ring_catalog_digest: str
    options_signature: str
    ring_geometries: tuple[RingGeometrySnapshot, ...]
    mappings: tuple[AttractorStructuralMapping, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        for name in ("trajectory_digest", "registration_signature", "attractor_catalog_signature", "topology_digest", "ring_catalog_digest", "options_signature"):
            value = str(getattr(self, name))
            if len(value) != 64: raise PilotAuditInputError(f"{name} must be SHA-256.")
        rings = tuple(self.ring_geometries); mappings = tuple(self.mappings)
        if tuple(v.ring_id for v in rings) != tuple(sorted(v.ring_id for v in rings)): raise PilotAuditInputError("Ring geometries must be canonical.")
        if tuple(v.attractor_id for v in mappings) != tuple(range(len(mappings))): raise PilotAuditInputError("Attractor mappings must be canonical.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": STRUCTURAL_MAPPING_CATALOG_SCHEMA, "trajectory_digest": self.trajectory_digest,
                   "registration_signature": self.registration_signature, "attractor_catalog_signature": self.attractor_catalog_signature,
                   "topology_digest": self.topology_digest, "ring_catalog_digest": self.ring_catalog_digest,
                   "options_signature": self.options_signature, "ring_geometry_signatures": [v.signature for v in rings],
                   "mapping_signatures": [v.signature for v in mappings], "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise PilotAuditInputError("Structural mapping catalog signature is inconsistent.")
        object.__setattr__(self, "ring_geometries", rings); object.__setattr__(self, "mappings", mappings); object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    @property
    def unique_count(self) -> int:
        return sum(v.status is StructuralMappingStatus.UNIQUE for v in self.mappings)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_MAPPING_CATALOG_SCHEMA, "trajectory_digest": self.trajectory_digest,
                "registration_signature": self.registration_signature, "attractor_catalog_signature": self.attractor_catalog_signature,
                "topology_digest": self.topology_digest, "ring_catalog_digest": self.ring_catalog_digest,
                "options_signature": self.options_signature, "ring_geometries": [v.to_dict() for v in self.ring_geometries],
                "mappings": [v.to_dict() for v in self.mappings], "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StructuralMappingCatalog":
        if payload.get("schema") != STRUCTURAL_MAPPING_CATALOG_SCHEMA: raise PilotAuditInputError("Unsupported structural mapping catalog schema.")
        return cls(trajectory_digest=str(payload["trajectory_digest"]), registration_signature=str(payload["registration_signature"]),
                   attractor_catalog_signature=str(payload["attractor_catalog_signature"]), topology_digest=str(payload["topology_digest"]),
                   ring_catalog_digest=str(payload["ring_catalog_digest"]), options_signature=str(payload["options_signature"]),
                   ring_geometries=tuple(RingGeometrySnapshot.from_dict(v) for v in payload["ring_geometries"]),
                   mappings=tuple(AttractorStructuralMapping.from_dict(v) for v in payload["mappings"]),
                   metadata=dict(payload.get("metadata", {})), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class NaLta300KStructuralTemporalPilot:
    report: NaLta300KPilotReport
    s2_pilot: NaLta300KRefinementLineagePilot
    structural_mapping: StructuralMappingCatalog
    temporal_assignment: ProvisionalTemporalAssignmentCatalog
    wall_seconds: float

    def __post_init__(self) -> None:
        central_index = self.s2_pilot.options.bandwidth_sigmas_angstrom.index(
            self.s2_pilot.options.central_bandwidth_sigma_angstrom
        )
        if self.structural_mapping.attractor_catalog_signature != self.s2_pilot.lineage_catalogs[central_index].signature:
            raise PilotAuditInputError("S3 structural mapping is not bound to the central S2 attractor catalog.")
        if self.temporal_assignment.attractor_catalog_signature != self.s2_pilot.lineage_catalogs[central_index].signature:
            raise PilotAuditInputError("S3 temporal assignment is not bound to the central S2 attractor catalog.")
        if self.temporal_assignment.sample_catalog_signature != self.s2_pilot.s1_pilot.source_bootstrap.na_samples.signature:
            raise PilotAuditInputError("S3 temporal assignment is not bound to the full source sample catalog.")


def _load_packaged_topology() -> tuple[FrameworkTopology, PrimitiveRingCatalog]:
    root = resource_files("mdstats").joinpath("data")
    topology = FrameworkTopology.from_dict(json.loads(root.joinpath("na_lta_framework_topology.json").read_text()))
    rings = PrimitiveRingCatalog.from_dict(json.loads(root.joinpath("na_lta_primitive_ring_catalog.json").read_text()))
    if rings.topology_digest != topology.digest or rings.topology_graph_digest != topology.graph_digest:
        raise PilotAuditInputError("Packaged Na-LTA topology and primitive-ring catalog disagree.")
    return topology, rings


def _mean_registered_fractional(registration: Any) -> np.ndarray:
    wrapped = np.asarray(registration.registered_wrapped_fractional, dtype=float)
    reference = wrapped[0]
    displacement = wrapped - reference[None, :, :]
    displacement -= np.rint(displacement)
    return reference + np.mean(displacement, axis=0)


def _validate_framework_topology_geometry(
    registration: Any,
    topology: FrameworkTopology,
    options: NaLta300KStructuralTemporalOptions,
) -> tuple[float, float, float]:
    cell = np.asarray(registration.registered_cells[0], dtype=float)
    mean_fractional = _mean_registered_fractional(registration)
    distances: list[float] = []
    for edge in topology.edges:
        for source, target in zip(
            edge.atomic_path_indices[:-1],
            edge.atomic_path_indices[1:],
            strict=True,
        ):
            delta = np.asarray(mean_fractional[int(target)] - mean_fractional[int(source)], dtype=float)
            delta -= np.rint(delta)
            distances.append(float(np.linalg.norm(delta @ cell)))
    if not distances:
        raise PilotAuditInputError("Packaged Na-LTA topology contains no framework bonds.")
    minimum = min(distances)
    maximum = max(distances)
    mean = float(np.mean(distances))
    if minimum < options.minimum_framework_bond_angstrom or maximum > options.maximum_framework_bond_angstrom:
        raise PilotAuditInputError(
            "Collection geometry does not replay the packaged Na-LTA T-O-T topology "
            f"within [{options.minimum_framework_bond_angstrom}, "
            f"{options.maximum_framework_bond_angstrom}] Angstrom; observed "
            f"[{minimum}, {maximum}]."
        )
    return minimum, maximum, mean


def _polygon_centroid(points: np.ndarray) -> tuple[np.ndarray, float]:
    x = points[:, 0]; y = points[:, 1]; x2 = np.roll(x, -1); y2 = np.roll(y, -1)
    cross = x * y2 - x2 * y; area2 = float(np.sum(cross))
    if abs(area2) <= 1.0e-14:
        return np.mean(points, axis=0), 0.0
    centroid = np.array([np.sum((x + x2) * cross), np.sum((y + y2) * cross)]) / (3.0 * area2)
    return centroid, 0.5 * area2


def _ring_geometry(collection: AtomisticFrameCollection, registration: Any, topology: FrameworkTopology, rings: PrimitiveRingCatalog) -> tuple[RingGeometrySnapshot, ...]:
    cell = np.asarray(registration.registered_cells[0], dtype=float); inv = np.linalg.inv(cell)
    mean_fractional = _mean_registered_fractional(registration)
    result: list[RingGeometrySnapshot] = []
    for ring in rings.rings:
        if tuple(ring.winding) != (0, 0, 0):
            continue
        walk = expand_primitive_ring_atomic_walk(topology, ring)
        oxygen_refs = [ref for ref in walk if int(collection.atomic_numbers[ref.atom_index]) == 8]
        if len(oxygen_refs) != ring.size:
            raise PilotAuditInputError(f"Ring {ring.ring_id} does not contain one oxygen per edge.")
        oxygen_indices = [ref.atom_index for ref in oxygen_refs]
        local_fractional = [np.asarray(mean_fractional[oxygen_indices[0]], dtype=float)]
        for previous, current in zip(oxygen_indices[:-1], oxygen_indices[1:], strict=True):
            delta = np.asarray(mean_fractional[current] - mean_fractional[previous], dtype=float)
            delta -= np.rint(delta)
            local_fractional.append(local_fractional[-1] + delta)
        coords = np.asarray(local_fractional) @ cell
        origin = np.mean(coords, axis=0); centered = coords - origin
        _, _, vh = np.linalg.svd(centered, full_matrices=False); normal = vh[-1]
        area_vector = np.sum(np.cross(centered, np.roll(centered, -1, axis=0)), axis=0)
        if np.dot(normal, area_vector) < 0.0: normal = -normal
        first = centered[0] - np.dot(centered[0], normal) * normal
        if np.linalg.norm(first) <= 1.0e-12: first = vh[0]
        u = first / np.linalg.norm(first); v = np.cross(normal, u); v /= np.linalg.norm(v)
        xy0 = np.column_stack((centered @ u, centered @ v)); centroid2, signed_area = _polygon_centroid(xy0)
        if signed_area < 0.0:
            v = -v; xy0[:, 1] *= -1.0; centroid2, _ = _polygon_centroid(xy0)
        center = origin + centroid2[0] * u + centroid2[1] * v
        xy = np.column_stack(((coords - center) @ u, (coords - center) @ v))
        radii = np.linalg.norm(xy, axis=1); planarity = float(np.sqrt(np.mean(((coords - center) @ normal) ** 2)))
        frac = np.mod(center @ inv, 1.0)
        result.append(RingGeometrySnapshot(ring.ring_id, ring.size, tuple(ref.atom_index for ref in oxygen_refs), frac, center, normal, u, v, xy,
                                           float(np.mean(radii)), float(np.min(radii)), float(np.max(radii)), planarity))
    return tuple(sorted(result, key=lambda item: item.ring_id))


def _point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    x, y = point; inside = False
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0), strict=True):
        if (a[1] > y) != (b[1] > y):
            x_cross = (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
            if x < x_cross: inside = not inside
    return inside


def _segment_distance(point: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    delta = b - a; denom = float(np.dot(delta, delta))
    t = 0.0 if denom <= 1.0e-30 else float(np.clip(np.dot(point - a, delta) / denom, 0.0, 1.0))
    return float(np.linalg.norm(point - (a + t * delta)))


def _cross2(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _serrated_boundary_radius(point: np.ndarray, polygon: np.ndarray) -> float:
    radius = float(np.linalg.norm(point))
    if radius <= 1.0e-14: return float(np.min(np.linalg.norm(polygon, axis=1)))
    direction = point / radius; hits: list[float] = []
    for a, b in zip(polygon, np.roll(polygon, -1, axis=0), strict=True):
        edge = b - a; denom = _cross2(direction, edge)
        if abs(denom) <= 1.0e-14: continue
        t = _cross2(a, edge) / denom; s = _cross2(a, direction) / denom
        if t >= 0.0 and -1.0e-12 <= s <= 1.0 + 1.0e-12: hits.append(float(t))
    return min((v for v in hits if v > 1.0e-12), default=float(np.max(np.linalg.norm(polygon, axis=1))))


def _map_attractors(attractors: DensityAttractorCatalog, cell: np.ndarray, rings: tuple[RingGeometrySnapshot, ...], options: NaLta300KStructuralTemporalOptions) -> tuple[AttractorStructuralMapping, ...]:
    inv = np.linalg.inv(cell); result: list[AttractorStructuralMapping] = []
    for attractor in attractors.attractors:
        anchor0 = np.asarray(attractor.anchor_fractional) @ cell; candidates: list[AttractorRingCandidate] = []
        for ring in rings:
            delta_frac = (anchor0 - ring.center_cartesian) @ inv; delta_frac -= np.rint(delta_frac); delta = delta_frac @ cell
            plane = float(np.dot(delta, ring.normal_cartesian)); point = np.array([np.dot(delta, ring.basis_u_cartesian), np.dot(delta, ring.basis_v_cartesian)])
            inside = _point_in_polygon(point, ring.oxygen_polygon_xy)
            edge_distance = min(_segment_distance(point, a, b) for a, b in zip(ring.oxygen_polygon_xy, np.roll(ring.oxygen_polygon_xy, -1, axis=0), strict=True))
            clearance = edge_distance if inside else -edge_distance
            association = float(np.hypot(plane, max(0.0, -clearance)))
            center_distance = float(np.linalg.norm(delta)); boundary = _serrated_boundary_radius(point, ring.oxygen_polygon_xy)
            radial_fraction = float(np.linalg.norm(point) / max(boundary, np.finfo(float).tiny))
            side = 0 if abs(plane) <= 1.0e-12 else (1 if plane > 0.0 else -1)
            candidates.append(AttractorRingCandidate(ring.ring_id, ring.ring_size, association, center_distance, plane, clearance, radial_fraction, inside, side))
        candidates.sort(key=lambda item: (item.association_distance_angstrom, item.center_distance_angstrom, item.ring_id))
        retained = tuple(candidates[: options.candidate_count]); best = retained[0]
        margin = None if len(retained) < 2 else retained[1].association_distance_angstrom - best.association_distance_angstrom
        if best.association_distance_angstrom > options.maximum_ring_association_distance_angstrom:
            status = StructuralMappingStatus.OUTSIDE_LIMIT
        elif margin is None or margin >= options.minimum_unique_margin_angstrom:
            status = StructuralMappingStatus.UNIQUE
        else:
            status = StructuralMappingStatus.AMBIGUOUS
        result.append(AttractorStructuralMapping(attractor.attractor_id, status, retained, margin))
    return tuple(result)


def _structural_mapping(collection: AtomisticFrameCollection, s2: NaLta300KRefinementLineagePilot, options: NaLta300KStructuralTemporalOptions) -> StructuralMappingCatalog:
    topology, primitive_rings = _load_packaged_topology()
    if tuple(int(v) for v in topology.vertex_atom_indices) != tuple(range(48)):
        raise PilotAuditInputError("Packaged Na-LTA topology does not match the required T-atom indexing.")
    if not np.array_equal(collection.atomic_numbers[:48], np.asarray([14] * 24 + [13] * 24)) or not np.all(collection.atomic_numbers[48:144] == 8):
        raise PilotAuditInputError("Collection framework indexing is incompatible with the packaged Na-LTA topology.")
    minimum_bond, maximum_bond, mean_bond = _validate_framework_topology_geometry(
        s2.s1_pilot.source_bootstrap.registration,
        topology,
        options,
    )
    central_index = s2.options.bandwidth_sigmas_angstrom.index(s2.options.central_bandwidth_sigma_angstrom)
    attractors = s2.lineage_catalogs[central_index]
    geometries = _ring_geometry(collection, s2.s1_pilot.source_bootstrap.registration, topology, primitive_rings)
    if not geometries or max(item.planarity_rms_angstrom for item in geometries) > options.maximum_ring_planarity_rms_angstrom:
        raise PilotAuditInputError("Mean registered ring geometry exceeds the declared planarity gate.")
    mappings = _map_attractors(attractors, np.asarray(s2.s1_pilot.source_bootstrap.registration.registered_cells[0]), geometries, options)
    return StructuralMappingCatalog(s2.s1_pilot.source_bootstrap.trajectory_sha256, s2.s1_pilot.source_bootstrap.registration.signature,
                                    attractors.signature, topology.digest, primitive_rings.digest, options.signature, geometries, mappings,
                                    metadata={"serrated_polygon_mapping": True, "circle_or_ellipse_substitution": False,
                                              "ring_size_counts": {str(size): sum(g.ring_size == size for g in geometries) for size in (4, 6, 8)},
                                              "minimum_framework_bond_angstrom": minimum_bond,
                                              "maximum_framework_bond_angstrom": maximum_bond,
                                              "mean_framework_bond_angstrom": mean_bond})


def prepare_na_lta_300k_structural_temporal_pilot(
    collection: AtomisticFrameCollection,
    trajectory_path: str | Path,
    *,
    options: NaLta300KStructuralTemporalOptions | None = None,
    s2_options: NaLta300KRefinementLineageOptions | None = None,
    s1_options: NaLta300KDensityAttractorPilotOptions | None = None,
    density_resources: SpeciesDensityResourcePolicy | None = None,
    attractor_options: DensityAttractorOptions | None = None,
    attractor_resources: DensityAttractorResourcePolicy | None = None,
    temporal_resources: TemporalAssignmentResourcePolicy | None = None,
    audit_policy: PilotAuditResourcePolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> NaLta300KStructuralTemporalPilot:
    """Execute Stage 11E8a-S3 on the source-bound Na-LTA trajectory."""
    active = options or NaLta300KStructuralTemporalOptions(); started = perf_counter()
    s2 = prepare_na_lta_300k_refinement_lineage_pilot(collection, trajectory_path, options=s2_options, s1_options=s1_options,
                                                     density_resources=density_resources, attractor_options=attractor_options,
                                                     attractor_resources=attractor_resources, audit_policy=audit_policy,
                                                     metadata={"requested_by_stage": PILOT_STRUCTURAL_TEMPORAL_STAGE})
    structural = _structural_mapping(collection, s2, active)
    central_index = s2.options.bandwidth_sigmas_angstrom.index(s2.options.central_bandwidth_sigma_angstrom)
    central_density = s2.density_ladder.estimates[central_index]; central_attractors = s2.lineage_catalogs[central_index]
    temporal = prepare_provisional_temporal_assignment(
        s2.s1_pilot.source_bootstrap.na_samples,
        central_density,
        central_attractors,
        discovery_catalog=s2.s1_pilot.pilot_samples,
        options=active.temporal_options,
        resources=temporal_resources,
    )
    elapsed = perf_counter() - started; source_digest = s2.s1_pilot.source_bootstrap.trajectory_sha256
    unique = structural.unique_count; total = len(structural.mappings); unique_fraction = unique / max(1, total)
    temporal_spatial_authoritative = (
        s2.scale_consensus.status.value == "resolved"
        and s2.grid_refinement.certificate.status.value == "stable"
    )
    mapping_status = (
        PilotEvidenceStatus.RESOLVED
        if unique == total and temporal_spatial_authoritative
        else PilotEvidenceStatus.PARTIAL
    )
    raw = temporal.membership.raw_classification
    class_counts = {item.name.lower(): int(np.sum(raw == int(item))) for item in RawMembershipClass}
    core_fraction = class_counts.get("core", 0) / max(1, raw.size)
    temporal_status = PilotEvidenceStatus.RESOLVED if temporal_spatial_authoritative and temporal.temporal_support_status is TemporalSupportStatus.PERSISTENT else PilotEvidenceStatus.PARTIAL
    replacements = {
        "structural_mapping": PilotEvidenceRecord("structural_mapping", PILOT_STRUCTURAL_TEMPORAL_STAGE, mapping_status, source_digest=source_digest,
            accepted_fraction=unique_fraction, unresolved_fraction=1.0 - unique_fraction,
            metrics={"catalog_signature": structural.signature, "topology_digest": structural.topology_digest, "ring_catalog_digest": structural.ring_catalog_digest,
                     "ring_count": len(structural.ring_geometries), "ring_size_counts": dict(structural.metadata["ring_size_counts"]),
                     "unique_mapping_count": unique, "ambiguous_mapping_count": sum(v.status is StructuralMappingStatus.AMBIGUOUS for v in structural.mappings),
                     "outside_limit_count": sum(v.status is StructuralMappingStatus.OUTSIDE_LIMIT for v in structural.mappings),
                     "serrated_polygon_mapping": True,
                     "spatial_hypothesis_authoritative": temporal_spatial_authoritative,
                     "minimum_framework_bond_angstrom": structural.metadata["minimum_framework_bond_angstrom"],
                     "maximum_framework_bond_angstrom": structural.metadata["maximum_framework_bond_angstrom"]},
            messages=(
                ()
                if mapping_status is PilotEvidenceStatus.RESOLVED
                else (
                    ("Some attractors retain multiple or out-of-limit ring candidates.",)
                    if unique < total
                    else ("All attractor-to-ring associations are unique, but the upstream S2 spatial scale/topology is not yet authoritative.",)
                )
            ),
        ),
        "temporal_support": PilotEvidenceRecord("temporal_support", "11E4/S3", temporal_status, source_digest=source_digest,
            accepted_fraction=core_fraction, unresolved_fraction=1.0 - core_fraction,
            metrics={"temporal_assignment_signature": temporal.signature, "support_status": temporal.temporal_support_status.value,
                     "evidence_pattern": temporal.evidence_pattern.value, "partition_transfer_performed": temporal.metadata["partition_transfer_performed"],
                     "full_sample_count": temporal.membership.raw_classification.size, "core_visit_count": len(temporal.core_visits),
                     "residence_count": len(temporal.residences), "passage_count": len(temporal.passages), "membership_class_counts": class_counts,
                     "stride_sensitive": temporal.stride_diagnostic.sensitive, "spatial_hypothesis_authoritative": temporal_spatial_authoritative},
            messages=(() if temporal_status is PilotEvidenceStatus.RESOLVED else ("Temporal diagnostics are provisional because the S2 spatial scale/topology remains unresolved or persistence is not established.",))),
    }
    resident_bytes = _array_payload_bytes(collection, s2, structural, temporal)
    replacements["cost"] = PilotEvidenceRecord("cost", PILOT_STRUCTURAL_TEMPORAL_STAGE, PilotEvidenceStatus.RESOLVED, source_digest=source_digest,
        accepted_fraction=1.0, unresolved_fraction=0.0, metrics={"s3_total_wall_seconds": elapsed, "ring_count": len(structural.ring_geometries), "sample_count": temporal.membership.raw_classification.size})
    replacements["memory"] = PilotEvidenceRecord("memory", PILOT_STRUCTURAL_TEMPORAL_STAGE, PilotEvidenceStatus.RESOLVED, source_digest=source_digest,
        accepted_fraction=1.0, unresolved_fraction=0.0, metrics={"resident_numerical_payload_bytes": resident_bytes, "measurement_kind": "deduplicated recursive ndarray payload estimate"})
    evidence = _replace_evidence(s2.report.evidence, replacements)
    jumps = sum(item.outcome.value == "jump" for item in temporal.passages)
    report = prepare_na_lta_300k_pilot_report(
        s2.report.dataset, evidence, artifacts=s2.report.artifacts,
        resources=PilotResourceUsage(wall_seconds=elapsed, peak_memory_bytes=resident_bytes, worker_count=1,
                                     output_bytes=sum(item.byte_count for item in s2.report.artifacts),
                                     metadata={"scope": "S0-S3 structural mapping and provisional temporal support"}),
        outcome=PilotScientificOutcome(site_center_count=unique, supported_basin_count=len(central_attractors.attractors), observed_connection_count=jumps,
                                       transition_path_ensemble_count=None, undersampled_path_ensemble_count=None, rate_status=PilotRateStatus.NOT_EVALUATED,
                                       global_pmf_status=s2.report.outcome.global_pmf_status,
                                       conclusions=(f"S3 mapped {unique}/{total} attractors uniquely to persistent serrated ring polygons.",
                                                    f"Provisional temporal support is {temporal.temporal_support_status.value} with pattern {temporal.evidence_pattern.value}.",
                                                    "The temporal result remains tied to the exploratory central S2 spatial hypothesis.",
                                                    "Force-density agreement and observed transition-path reconstruction remain unresolved.")),
        metadata={**dict(metadata or {}), "audit_kind": "real_structural_temporal_pilot", "s1_complete": True, "s2_complete": True, "s3_complete": True,
                  "options_signature": active.signature, "structural_mapping_signature": structural.signature,
                  "temporal_assignment_signature": temporal.signature, "next_execution_boundary": "11E8a-S4 force-density agreement and transition-path preparation"},
        policy=audit_policy,
    )
    return NaLta300KStructuralTemporalPilot(report, s2, structural, temporal, elapsed)


__all__ = [
    "PILOT_STRUCTURAL_TEMPORAL_STAGE", "PILOT_STRUCTURAL_TEMPORAL_OPTIONS_SCHEMA", "RING_GEOMETRY_SCHEMA",
    "ATTRACTOR_RING_CANDIDATE_SCHEMA", "ATTRACTOR_STRUCTURAL_MAPPING_SCHEMA", "STRUCTURAL_MAPPING_CATALOG_SCHEMA",
    "StructuralMappingStatus", "NaLta300KStructuralTemporalOptions", "RingGeometrySnapshot", "AttractorRingCandidate",
    "AttractorStructuralMapping", "StructuralMappingCatalog", "NaLta300KStructuralTemporalPilot",
    "prepare_na_lta_300k_structural_temporal_pilot",
]
