"""Stage-11E5 joint evidence validation and structural association.

This module freezes a selected Stage-11E2 state catalog and combines orthogonal
spatial, temporal, force, stationarity, geometry, curvature, and transfer
evidence without collapsing disagreements into one optimistic score.  It also
associates statistical states with persistent Stage-C0A3 structural objects in
the registered density domain while retaining physical-geometry references for
downstream coordination work.

Discovery/selection/final-validation separation, metastable-state validation,
and symmetry exchangeability are established statistical background.  The exact
source binding, no-nearest-object fallback, orthogonal status lattice,
selection-conditioned outcome, and frozen-versus-refit catalog distinction are
mdstats-specific constructions.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ...coordinates.metric_geometry import (
    AnalysisGeometryMetric as CoordinateAnalysisGeometryMetric,
    ClosestImageOptions,
    closest_periodic_image,
)
from ..registered_structural_view import (
    RegisteredRingViewStatus,
    RegisteredStructuralGeometryView,
)
from ..site_samples import (
    EquilibriumStatus,
    FrameworkAlignedIonSampleCatalog,
    StationarityStatus,
)
from .attractors import (
    AttractorGeometry,
    DensityAttractorCatalog,
    TopologyStabilityStatus,
)
from .force_refinement import (
    CurvatureClass,
    ForceEvidenceStatus,
    ForceRefinementCatalog,
)
from .species import PeriodicSpeciesDensityEstimate
from .temporal_assignment import (
    ProvisionalTemporalAssignmentCatalog,
    RawMembershipClass,
    TemporalSupportStatus,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

JOINT_EVIDENCE_STAGE = "11E5"
JOINT_EVIDENCE_OPTIONS_SCHEMA = "mdstats.joint-evidence-options.v1"
JOINT_EVIDENCE_RESOURCES_SCHEMA = "mdstats.joint-evidence-resources.v1"
EVIDENCE_BLOCK_PLAN_SCHEMA = "mdstats.evidence-block-plan.v1"
BLOCK_EVIDENCE_SUMMARY_SCHEMA = "mdstats.block-evidence-summary.v1"
STRUCTURAL_ASSOCIATION_CANDIDATE_SCHEMA = "mdstats.structural-association-candidate.v1"
STRUCTURAL_ASSOCIATION_SET_SCHEMA = "mdstats.structural-association-set.v1"
SITE_EVIDENCE_STATUS_SCHEMA = "mdstats.site-evidence-status.v1"
VALIDATED_STATISTICAL_STATE_SCHEMA = "mdstats.validated-statistical-state.v1"
STRUCTURAL_SITE_COMPLEX_SCHEMA = "mdstats.structural-site-complex.v1"
SYMMETRY_ORBIT_CANDIDATE_SCHEMA = "mdstats.symmetry-orbit-candidate.v1"
STRUCTURAL_SYMMETRY_ORBIT_SCHEMA = "mdstats.structural-symmetry-orbit.v1"
VALIDATED_FROZEN_CATALOG_SCHEMA = "mdstats.validated-frozen-catalog.v1"
FINAL_REFIT_CATALOG_SCHEMA = "mdstats.final-refit-catalog.v1"


class JointEvidenceError(ValueError):
    """Base Stage-11E5 error."""


class JointEvidenceInputError(JointEvidenceError):
    """Raised when E0b--E4 or C0A3 sources cannot be reconciled."""


class JointEvidenceResourceError(JointEvidenceError):
    """Raised transactionally before declared E5 work limits are exceeded."""


class JointEvidenceSerializationError(JointEvidenceError):
    """Raised when serialized E5 data are malformed or tampered with."""


class EvidenceChannelStatus(str, Enum):
    RESOLVED = "resolved"
    SUPPORTED = "supported"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT = "insufficient"
    AMBIGUOUS = "ambiguous"
    DISAGREEMENT = "disagreement"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class OverallCertificationStatus(str, Enum):
    SPATIAL_CANDIDATE = "spatial_candidate"
    SPATIAL_TEMPORAL_VALIDATED = "spatial_temporal_validated"
    FORCE_VALIDATED = "force_validated"
    FULLY_VALIDATED = "fully_validated"
    EVIDENCE_DISAGREEMENT = "evidence_disagreement"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class ValidationIndependenceStatus(str, Enum):
    INDEPENDENT_SELECTION_AND_VALIDATION = "independent_selection_and_validation"
    SELECTION_CONDITIONED_VALIDATION = "selection_conditioned_validation"
    INDEPENDENT_VALIDATION_UNAVAILABLE = "independent_validation_unavailable"


class FinalValidationStatus(str, Enum):
    INDEPENDENT_VALIDATION_SUPPORTED = "independent_validation_supported"
    INDEPENDENT_VALIDATION_DISAGREEMENT = "independent_validation_disagreement"
    SELECTION_CONDITIONED = "selection_conditioned_validation"
    INDEPENDENT_VALIDATION_UNAVAILABLE = "independent_validation_unavailable"
    INSUFFICIENT_TRANSFER_SUPPORT = "insufficient_transfer_support"


class StructuralAssociationStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    STRUCTURAL_VIEW_UNAVAILABLE = "structural_view_unavailable"


class StructuralObjectKind(str, Enum):
    RING = "ring"
    TILE_CAGE = "tile_cage"
    WINDOW = "window"


class ExchangeabilityStatus(str, Enum):
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class EvidenceBlockRole(str, Enum):
    DISCOVERY = "discovery"
    SELECTION = "selection"
    FINAL_VALIDATION = "final_validation"
    OPTIONAL_REFIT = "optional_refit"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii")); h.update(str(arr.shape).encode("ascii")); h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise JointEvidenceInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise JointEvidenceInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise JointEvidenceInputError(f"{name} must be finite and nonnegative.")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise JointEvidenceInputError(f"{name} must be a positive integer.")
    return int(value)


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise JointEvidenceInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise JointEvidenceInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise JointEvidenceInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise JointEvidenceInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _canonical_indices(values: Sequence[int], name: str) -> tuple[int, ...]:
    result = tuple(sorted({int(v) for v in values}))
    if result and result[0] < 0:
        raise JointEvidenceInputError(f"{name} must contain nonnegative frame indices.")
    return result


@dataclass(frozen=True, slots=True)
class JointEvidenceOptions:
    maximum_association_distance: float = 3.5
    association_ambiguity_distance: float = 0.25
    force_score_residual_tolerance: float = 0.5
    minimum_block_samples: int = 4
    maximum_transfer_fraction_shift: float = 0.35
    exchangeability_probability_tolerance: float = 0.25
    exchangeability_occupancy_tolerance: float = 0.35
    exchangeability_persistence_tolerance: float = 0.5
    closest_image_options: ClosestImageOptions = ClosestImageOptions()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        max_distance = _positive(self.maximum_association_distance, "maximum_association_distance")
        ambiguity = _nonnegative(self.association_ambiguity_distance, "association_ambiguity_distance")
        if ambiguity >= max_distance:
            raise JointEvidenceInputError("association_ambiguity_distance must be smaller than maximum_association_distance.")
        force_tol = _nonnegative(self.force_score_residual_tolerance, "force_score_residual_tolerance")
        minimum = _positive_int(self.minimum_block_samples, "minimum_block_samples")
        transfer = _nonnegative(self.maximum_transfer_fraction_shift, "maximum_transfer_fraction_shift")
        probability = _nonnegative(self.exchangeability_probability_tolerance, "exchangeability_probability_tolerance")
        occupancy = _nonnegative(self.exchangeability_occupancy_tolerance, "exchangeability_occupancy_tolerance")
        persistence = _nonnegative(self.exchangeability_persistence_tolerance, "exchangeability_persistence_tolerance")
        for name, value in (("maximum_transfer_fraction_shift", transfer), ("exchangeability_probability_tolerance", probability),
                            ("exchangeability_occupancy_tolerance", occupancy), ("exchangeability_persistence_tolerance", persistence)):
            if value > 1.0:
                raise JointEvidenceInputError(f"{name} must not exceed one.")
        if not isinstance(self.closest_image_options, ClosestImageOptions):
            raise JointEvidenceInputError("closest_image_options has the wrong type.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": JOINT_EVIDENCE_OPTIONS_SCHEMA, "maximum_association_distance": max_distance,
                   "association_ambiguity_distance": ambiguity, "force_score_residual_tolerance": force_tol,
                   "minimum_block_samples": minimum, "maximum_transfer_fraction_shift": transfer,
                   "exchangeability_probability_tolerance": probability,
                   "exchangeability_occupancy_tolerance": occupancy,
                   "exchangeability_persistence_tolerance": persistence,
                   "closest_image_options": self.closest_image_options.to_dict(), "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Joint-evidence options signature is inconsistent.")
        for name, value in (("maximum_association_distance", max_distance), ("association_ambiguity_distance", ambiguity),
                            ("force_score_residual_tolerance", force_tol), ("minimum_block_samples", minimum),
                            ("maximum_transfer_fraction_shift", transfer), ("exchangeability_probability_tolerance", probability),
                            ("exchangeability_occupancy_tolerance", occupancy),
                            ("exchangeability_persistence_tolerance", persistence), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": JOINT_EVIDENCE_OPTIONS_SCHEMA, "maximum_association_distance": self.maximum_association_distance,
                "association_ambiguity_distance": self.association_ambiguity_distance,
                "force_score_residual_tolerance": self.force_score_residual_tolerance,
                "minimum_block_samples": self.minimum_block_samples,
                "maximum_transfer_fraction_shift": self.maximum_transfer_fraction_shift,
                "exchangeability_probability_tolerance": self.exchangeability_probability_tolerance,
                "exchangeability_occupancy_tolerance": self.exchangeability_occupancy_tolerance,
                "exchangeability_persistence_tolerance": self.exchangeability_persistence_tolerance,
                "closest_image_options": self.closest_image_options.to_dict(), "metadata": _json_value(self.metadata),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "JointEvidenceOptions":
        if p.get("schema") != JOINT_EVIDENCE_OPTIONS_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported joint-evidence options schema.")
        return cls(maximum_association_distance=float(p["maximum_association_distance"]),
                   association_ambiguity_distance=float(p["association_ambiguity_distance"]),
                   force_score_residual_tolerance=float(p["force_score_residual_tolerance"]),
                   minimum_block_samples=int(p["minimum_block_samples"]),
                   maximum_transfer_fraction_shift=float(p["maximum_transfer_fraction_shift"]),
                   exchangeability_probability_tolerance=float(p["exchangeability_probability_tolerance"]),
                   exchangeability_occupancy_tolerance=float(p["exchangeability_occupancy_tolerance"]),
                   exchangeability_persistence_tolerance=float(p["exchangeability_persistence_tolerance"]),
                   closest_image_options=ClosestImageOptions.from_dict(p["closest_image_options"]),
                   metadata=p.get("metadata", {}), signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class JointEvidenceResourcePolicy:
    max_states: int = 100_000
    max_structural_candidates: int = 10_000_000
    max_block_memberships: int = 100_000_000
    max_orbit_pairs: int = 10_000_000
    max_serialized_records: int = 20_000_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_states", "max_structural_candidates", "max_block_memberships", "max_orbit_pairs", "max_serialized_records")}
        expected = _digest({"schema": JOINT_EVIDENCE_RESOURCES_SCHEMA, **values})
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Joint-evidence resource signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": JOINT_EVIDENCE_RESOURCES_SCHEMA, **{name: getattr(self, name) for name in (
            "max_states", "max_structural_candidates", "max_block_memberships", "max_orbit_pairs", "max_serialized_records")},
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "JointEvidenceResourcePolicy":
        if p.get("schema") != JOINT_EVIDENCE_RESOURCES_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported joint-evidence resources schema.")
        return cls(**{name: int(p[name]) for name in (
            "max_states", "max_structural_candidates", "max_block_memberships", "max_orbit_pairs", "max_serialized_records")},
                   signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class EvidenceBlockPlan:
    discovery_frame_indices: tuple[int, ...]
    selection_frame_indices: tuple[int, ...] = ()
    final_validation_frame_indices: tuple[int, ...] = ()
    optional_refit_frame_indices: tuple[int, ...] = ()
    independence_status: ValidationIndependenceStatus | None = None
    notes: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        discovery = _canonical_indices(self.discovery_frame_indices, "discovery_frame_indices")
        selection = _canonical_indices(self.selection_frame_indices, "selection_frame_indices")
        validation = _canonical_indices(self.final_validation_frame_indices, "final_validation_frame_indices")
        refit = _canonical_indices(self.optional_refit_frame_indices, "optional_refit_frame_indices")
        if not discovery:
            raise JointEvidenceInputError("At least one discovery frame is required.")
        d, s, v = set(discovery), set(selection), set(validation)
        if not validation:
            derived = ValidationIndependenceStatus.INDEPENDENT_VALIDATION_UNAVAILABLE
        elif (d & v) or (s & v) or not selection:
            derived = ValidationIndependenceStatus.SELECTION_CONDITIONED_VALIDATION
        elif d & s:
            derived = ValidationIndependenceStatus.SELECTION_CONDITIONED_VALIDATION
        else:
            derived = ValidationIndependenceStatus.INDEPENDENT_SELECTION_AND_VALIDATION
        status = derived if self.independence_status is None else ValidationIndependenceStatus(self.independence_status)
        if status is not derived:
            raise JointEvidenceInputError("Declared block independence status disagrees with frame partitions.")
        notes = tuple(str(v) for v in self.notes)
        payload = {"schema": EVIDENCE_BLOCK_PLAN_SCHEMA, "discovery": list(discovery), "selection": list(selection),
                   "final_validation": list(validation), "optional_refit": list(refit),
                   "independence_status": status.value, "notes": list(notes)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Evidence-block-plan signature is inconsistent.")
        for name, value in (("discovery_frame_indices", discovery), ("selection_frame_indices", selection),
                            ("final_validation_frame_indices", validation), ("optional_refit_frame_indices", refit),
                            ("independence_status", status), ("notes", notes), ("signature", expected)):
            object.__setattr__(self, name, value)

    @classmethod
    def discovery_only(cls, frame_indices: Sequence[int]) -> "EvidenceBlockPlan":
        return cls(discovery_frame_indices=tuple(int(v) for v in frame_indices))

    def frames_for(self, role: EvidenceBlockRole) -> tuple[int, ...]:
        return {EvidenceBlockRole.DISCOVERY: self.discovery_frame_indices,
                EvidenceBlockRole.SELECTION: self.selection_frame_indices,
                EvidenceBlockRole.FINAL_VALIDATION: self.final_validation_frame_indices,
                EvidenceBlockRole.OPTIONAL_REFIT: self.optional_refit_frame_indices}[EvidenceBlockRole(role)]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": EVIDENCE_BLOCK_PLAN_SCHEMA, "discovery_frame_indices": list(self.discovery_frame_indices),
                "selection_frame_indices": list(self.selection_frame_indices),
                "final_validation_frame_indices": list(self.final_validation_frame_indices),
                "optional_refit_frame_indices": list(self.optional_refit_frame_indices),
                "independence_status": self.independence_status.value, "notes": list(self.notes), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "EvidenceBlockPlan":
        if p.get("schema") != EVIDENCE_BLOCK_PLAN_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported evidence-block-plan schema.")
        return cls(tuple(p["discovery_frame_indices"]), tuple(p.get("selection_frame_indices", ())),
                   tuple(p.get("final_validation_frame_indices", ())), tuple(p.get("optional_refit_frame_indices", ())),
                   ValidationIndependenceStatus(p["independence_status"]), tuple(p.get("notes", ())),
                   str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class BlockEvidenceSummary:
    state_id: int
    role: EvidenceBlockRole
    sample_count: int
    core_sample_count: int
    basin_sample_count: int
    represented_time: float
    block_ion_time_fraction: float | None
    mean_frame_occupancy: float | None
    signature: str = ""

    def __post_init__(self) -> None:
        sid = int(self.state_id); count = int(self.sample_count); core = int(self.core_sample_count); basin = int(self.basin_sample_count)
        if sid < 0 or min(count, core, basin) < 0 or core + basin > count:
            raise JointEvidenceInputError("Invalid block-evidence counters.")
        role = EvidenceBlockRole(self.role)
        represented = _nonnegative(self.represented_time, "represented_time")
        fraction = None if self.block_ion_time_fraction is None else _nonnegative(self.block_ion_time_fraction, "block_ion_time_fraction")
        occupancy = None if self.mean_frame_occupancy is None else _nonnegative(self.mean_frame_occupancy, "mean_frame_occupancy")
        if fraction is not None and fraction > 1.0 + 1e-12:
            raise JointEvidenceInputError("block_ion_time_fraction must not exceed one.")
        payload = {"schema": BLOCK_EVIDENCE_SUMMARY_SCHEMA, "state_id": sid, "role": role.value,
                   "sample_count": count, "core_sample_count": core, "basin_sample_count": basin,
                   "represented_time": represented, "block_ion_time_fraction": fraction,
                   "mean_frame_occupancy": occupancy}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Block-evidence signature is inconsistent.")
        for name, value in (("state_id", sid), ("role", role), ("sample_count", count), ("core_sample_count", core),
                            ("basin_sample_count", basin), ("represented_time", represented),
                            ("block_ion_time_fraction", fraction), ("mean_frame_occupancy", occupancy), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": BLOCK_EVIDENCE_SUMMARY_SCHEMA, "state_id": self.state_id, "role": self.role.value,
                "sample_count": self.sample_count, "core_sample_count": self.core_sample_count,
                "basin_sample_count": self.basin_sample_count, "represented_time": self.represented_time,
                "block_ion_time_fraction": self.block_ion_time_fraction, "mean_frame_occupancy": self.mean_frame_occupancy,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "BlockEvidenceSummary":
        if p.get("schema") != BLOCK_EVIDENCE_SUMMARY_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported block-evidence schema.")
        return cls(int(p["state_id"]), EvidenceBlockRole(p["role"]), int(p["sample_count"]),
                   int(p["core_sample_count"]), int(p["basin_sample_count"]), float(p["represented_time"]),
                   p.get("block_ion_time_fraction"), p.get("mean_frame_occupancy"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralAssociationCandidate:
    candidate_index: int
    kind: StructuralObjectKind
    object_index: int
    persistent_identity: str
    mean_registered_distance: float
    maximum_registered_distance: float
    geometric_score: float
    chemical_score: float | None
    frame_support_count: int
    physical_geometry_reference: Mapping[str, Any]
    chemical_signature: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        index = int(self.candidate_index); object_index = int(self.object_index); support = int(self.frame_support_count)
        if min(index, object_index) < 0 or support <= 0:
            raise JointEvidenceInputError("Invalid structural-association candidate counters.")
        kind = StructuralObjectKind(self.kind)
        identity = str(self.persistent_identity)
        if not identity:
            raise JointEvidenceInputError("persistent_identity must be nonempty.")
        mean = _nonnegative(self.mean_registered_distance, "mean_registered_distance")
        maximum = _nonnegative(self.maximum_registered_distance, "maximum_registered_distance")
        score = _nonnegative(self.geometric_score, "geometric_score")
        chemical = None if self.chemical_score is None else _nonnegative(self.chemical_score, "chemical_score")
        if score > 1.0 + 1e-12 or (chemical is not None and chemical > 1.0 + 1e-12) or maximum + 1e-12 < mean:
            raise JointEvidenceInputError("Invalid structural-association score or distance.")
        chemistry = None if self.chemical_signature is None else _sha(self.chemical_signature, "chemical_signature")
        physical = _freeze(dict(self.physical_geometry_reference))
        payload = {"schema": STRUCTURAL_ASSOCIATION_CANDIDATE_SCHEMA, "candidate_index": index, "kind": kind.value,
                   "object_index": object_index, "persistent_identity": identity, "mean_registered_distance": mean,
                   "maximum_registered_distance": maximum, "geometric_score": score, "chemical_score": chemical,
                   "frame_support_count": support, "physical_geometry_reference": _json_value(physical),
                   "chemical_signature": chemistry}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Structural-association-candidate signature is inconsistent.")
        for name, value in (("candidate_index", index), ("kind", kind), ("object_index", object_index),
                            ("persistent_identity", identity), ("mean_registered_distance", mean),
                            ("maximum_registered_distance", maximum), ("geometric_score", score),
                            ("chemical_score", chemical), ("frame_support_count", support),
                            ("physical_geometry_reference", physical), ("chemical_signature", chemistry), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_ASSOCIATION_CANDIDATE_SCHEMA, "candidate_index": self.candidate_index,
                "kind": self.kind.value, "object_index": self.object_index, "persistent_identity": self.persistent_identity,
                "mean_registered_distance": self.mean_registered_distance,
                "maximum_registered_distance": self.maximum_registered_distance, "geometric_score": self.geometric_score,
                "chemical_score": self.chemical_score, "frame_support_count": self.frame_support_count,
                "physical_geometry_reference": _json_value(self.physical_geometry_reference),
                "chemical_signature": self.chemical_signature, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StructuralAssociationCandidate":
        if p.get("schema") != STRUCTURAL_ASSOCIATION_CANDIDATE_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported structural-association-candidate schema.")
        return cls(int(p["candidate_index"]), StructuralObjectKind(p["kind"]), int(p["object_index"]),
                   str(p["persistent_identity"]), float(p["mean_registered_distance"]),
                   float(p["maximum_registered_distance"]), float(p["geometric_score"]), p.get("chemical_score"),
                   int(p["frame_support_count"]), dict(p.get("physical_geometry_reference", {})),
                   p.get("chemical_signature"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralAssociationSet:
    state_id: int
    status: StructuralAssociationStatus
    candidates: tuple[StructuralAssociationCandidate, ...]
    primary_candidate_index: int | None
    ambiguity_distance: float | None
    registered_structural_view_digest: str
    physical_geometry_retained: bool = True
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        sid = int(self.state_id)
        if sid < 0: raise JointEvidenceInputError("state_id must be nonnegative.")
        status = StructuralAssociationStatus(self.status); candidates = tuple(self.candidates)
        if tuple(v.candidate_index for v in candidates) != tuple(range(len(candidates))):
            raise JointEvidenceInputError("Association candidate indices must be canonical.")
        primary = None if self.primary_candidate_index is None else int(self.primary_candidate_index)
        if status is StructuralAssociationStatus.RESOLVED:
            if primary is None or primary < 0 or primary >= len(candidates):
                raise JointEvidenceInputError("Resolved association requires a valid primary candidate.")
        elif primary is not None:
            raise JointEvidenceInputError("Only resolved associations may identify a primary candidate.")
        ambiguity = None if self.ambiguity_distance is None else _nonnegative(self.ambiguity_distance, "ambiguity_distance")
        view = _sha(self.registered_structural_view_digest, "registered_structural_view_digest")
        payload = {"schema": STRUCTURAL_ASSOCIATION_SET_SCHEMA, "state_id": sid, "status": status.value,
                   "candidate_signatures": [v.signature for v in candidates], "primary_candidate_index": primary,
                   "ambiguity_distance": ambiguity, "registered_structural_view_digest": view,
                   "physical_geometry_retained": bool(self.physical_geometry_retained), "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Structural-association-set signature is inconsistent.")
        for name, value in (("state_id", sid), ("status", status), ("candidates", candidates),
                            ("primary_candidate_index", primary), ("ambiguity_distance", ambiguity),
                            ("registered_structural_view_digest", view),
                            ("physical_geometry_retained", bool(self.physical_geometry_retained)), ("signature", expected)):
            object.__setattr__(self, name, value)

    @property
    def primary(self) -> StructuralAssociationCandidate | None:
        return None if self.primary_candidate_index is None else self.candidates[self.primary_candidate_index]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_ASSOCIATION_SET_SCHEMA, "state_id": self.state_id, "status": self.status.value,
                "candidates": [v.to_dict() for v in self.candidates], "primary_candidate_index": self.primary_candidate_index,
                "ambiguity_distance": self.ambiguity_distance,
                "registered_structural_view_digest": self.registered_structural_view_digest,
                "physical_geometry_retained": self.physical_geometry_retained, "diagnostic": self.diagnostic,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StructuralAssociationSet":
        if p.get("schema") != STRUCTURAL_ASSOCIATION_SET_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported structural-association-set schema.")
        return cls(int(p["state_id"]), StructuralAssociationStatus(p["status"]),
                   tuple(StructuralAssociationCandidate.from_dict(v) for v in p["candidates"]),
                   p.get("primary_candidate_index"), p.get("ambiguity_distance"),
                   str(p["registered_structural_view_digest"]), bool(p.get("physical_geometry_retained", True)),
                   p.get("diagnostic"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SiteEvidenceStatus:
    spatial: EvidenceChannelStatus
    temporal: EvidenceChannelStatus
    force: EvidenceChannelStatus
    force_score_consistency: EvidenceChannelStatus
    stationarity: EvidenceChannelStatus
    geometry: EvidenceChannelStatus
    curvature: EvidenceChannelStatus
    overall: OverallCertificationStatus
    final_validation: FinalValidationStatus
    diagnostics: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: EvidenceChannelStatus(getattr(self, name)) for name in (
            "spatial", "temporal", "force", "force_score_consistency", "stationarity", "geometry", "curvature")}
        overall = OverallCertificationStatus(self.overall); final = FinalValidationStatus(self.final_validation)
        diagnostics = tuple(str(v) for v in self.diagnostics)
        payload = {"schema": SITE_EVIDENCE_STATUS_SCHEMA, **{k: v.value for k, v in values.items()},
                   "overall": overall.value, "final_validation": final.value, "diagnostics": list(diagnostics)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Site-evidence-status signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "overall", overall); object.__setattr__(self, "final_validation", final)
        object.__setattr__(self, "diagnostics", diagnostics); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SITE_EVIDENCE_STATUS_SCHEMA, **{name: getattr(self, name).value for name in (
            "spatial", "temporal", "force", "force_score_consistency", "stationarity", "geometry", "curvature")},
                "overall": self.overall.value, "final_validation": self.final_validation.value,
                "diagnostics": list(self.diagnostics), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "SiteEvidenceStatus":
        if p.get("schema") != SITE_EVIDENCE_STATUS_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported site-evidence-status schema.")
        return cls(*(EvidenceChannelStatus(p[name]) for name in (
            "spatial", "temporal", "force", "force_score_consistency", "stationarity", "geometry", "curvature")),
                   OverallCertificationStatus(p["overall"]), FinalValidationStatus(p["final_validation"]),
                   tuple(p.get("diagnostics", ())), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ValidatedStatisticalState:
    state_id: int
    source_attractor_id: int
    source_attractor_signature: str
    anchor_fractional: FloatArray
    geometry: AttractorGeometry
    basin_probability: float
    ion_time_fraction: float
    mean_occupancy: float
    evidence: SiteEvidenceStatus
    structural_association: StructuralAssociationSet
    block_summaries: tuple[BlockEvidenceSummary, ...]
    signature: str = ""

    def __post_init__(self) -> None:
        sid = int(self.state_id); aid = int(self.source_attractor_id)
        if min(sid, aid) < 0: raise JointEvidenceInputError("State and attractor ids must be nonnegative.")
        source = _sha(self.source_attractor_signature, "source_attractor_signature")
        anchor = _readonly(self.anchor_fractional, dtype=np.float64, ndim=1, name="anchor_fractional", shape=(3,))
        anchor = np.mod(anchor, 1.0); anchor.setflags(write=False)
        geometry = AttractorGeometry(self.geometry); basin = _nonnegative(self.basin_probability, "basin_probability")
        ion_time = _nonnegative(self.ion_time_fraction, "ion_time_fraction"); occupancy = _nonnegative(self.mean_occupancy, "mean_occupancy")
        if basin > 1.0 + 1e-12 or ion_time > 1.0 + 1e-12:
            raise JointEvidenceInputError("State probabilities must not exceed one.")
        if self.structural_association.state_id != sid:
            raise JointEvidenceInputError("Structural association belongs to another state.")
        blocks = tuple(self.block_summaries)
        if any(v.state_id != sid for v in blocks) or tuple(v.role for v in blocks) != tuple(EvidenceBlockRole):
            raise JointEvidenceInputError("Each state requires canonical summaries for all block roles.")
        payload = {"schema": VALIDATED_STATISTICAL_STATE_SCHEMA, "state_id": sid, "source_attractor_id": aid,
                   "source_attractor_signature": source, "anchor": _array_digest(anchor), "geometry": geometry.value,
                   "basin_probability": basin, "ion_time_fraction": ion_time, "mean_occupancy": occupancy,
                   "evidence_signature": self.evidence.signature,
                   "association_signature": self.structural_association.signature,
                   "block_signatures": [v.signature for v in blocks]}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Validated-state signature is inconsistent.")
        for name, value in (("state_id", sid), ("source_attractor_id", aid), ("source_attractor_signature", source),
                            ("anchor_fractional", anchor), ("geometry", geometry), ("basin_probability", basin),
                            ("ion_time_fraction", ion_time), ("mean_occupancy", occupancy),
                            ("block_summaries", blocks), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": VALIDATED_STATISTICAL_STATE_SCHEMA, "state_id": self.state_id,
                "source_attractor_id": self.source_attractor_id,
                "source_attractor_signature": self.source_attractor_signature,
                "anchor_fractional": self.anchor_fractional.tolist(), "geometry": self.geometry.value,
                "basin_probability": self.basin_probability, "ion_time_fraction": self.ion_time_fraction,
                "mean_occupancy": self.mean_occupancy, "evidence": self.evidence.to_dict(),
                "structural_association": self.structural_association.to_dict(),
                "block_summaries": [v.to_dict() for v in self.block_summaries], "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ValidatedStatisticalState":
        if p.get("schema") != VALIDATED_STATISTICAL_STATE_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported validated-state schema.")
        return cls(int(p["state_id"]), int(p["source_attractor_id"]), str(p["source_attractor_signature"]),
                   np.asarray(p["anchor_fractional"], dtype=float), AttractorGeometry(p["geometry"]),
                   float(p["basin_probability"]), float(p["ion_time_fraction"]), float(p["mean_occupancy"]),
                   SiteEvidenceStatus.from_dict(p["evidence"]), StructuralAssociationSet.from_dict(p["structural_association"]),
                   tuple(BlockEvidenceSummary.from_dict(v) for v in p["block_summaries"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralSiteComplex:
    complex_id: int
    kind: StructuralObjectKind
    persistent_identity: str
    member_state_ids: tuple[int, ...]
    preliminary: bool = True
    signature: str = ""

    def __post_init__(self) -> None:
        cid = int(self.complex_id)
        if cid < 0: raise JointEvidenceInputError("complex_id must be nonnegative.")
        kind = StructuralObjectKind(self.kind); identity = str(self.persistent_identity)
        members = tuple(sorted({int(v) for v in self.member_state_ids}))
        if not identity or not members or members[0] < 0:
            raise JointEvidenceInputError("Structural-site complex requires an identity and members.")
        payload = {"schema": STRUCTURAL_SITE_COMPLEX_SCHEMA, "complex_id": cid, "kind": kind.value,
                   "persistent_identity": identity, "member_state_ids": list(members), "preliminary": bool(self.preliminary)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Structural-site-complex signature is inconsistent.")
        for name, value in (("complex_id", cid), ("kind", kind), ("persistent_identity", identity),
                            ("member_state_ids", members), ("preliminary", bool(self.preliminary)), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_SITE_COMPLEX_SCHEMA, "complex_id": self.complex_id, "kind": self.kind.value,
                "persistent_identity": self.persistent_identity, "member_state_ids": list(self.member_state_ids),
                "preliminary": self.preliminary, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StructuralSiteComplex":
        if p.get("schema") != STRUCTURAL_SITE_COMPLEX_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported structural-site-complex schema.")
        return cls(int(p["complex_id"]), StructuralObjectKind(p["kind"]), str(p["persistent_identity"]),
                   tuple(p["member_state_ids"]), bool(p.get("preliminary", True)), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SymmetryOrbitCandidate:
    label: str
    member_state_ids: tuple[int, ...]
    ideal_multiplicity: int
    provenance: str
    signature: str = ""

    def __post_init__(self) -> None:
        label = str(self.label).strip(); provenance = str(self.provenance).strip()
        members = tuple(sorted({int(v) for v in self.member_state_ids})); ideal = _positive_int(self.ideal_multiplicity, "ideal_multiplicity")
        if not label or not provenance or len(members) < 2 or members[0] < 0 or ideal < len(members):
            raise JointEvidenceInputError("Invalid symmetry-orbit candidate.")
        payload = {"schema": SYMMETRY_ORBIT_CANDIDATE_SCHEMA, "label": label, "member_state_ids": list(members),
                   "ideal_multiplicity": ideal, "provenance": provenance}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Symmetry-orbit-candidate signature is inconsistent.")
        for name, value in (("label", label), ("member_state_ids", members), ("ideal_multiplicity", ideal),
                            ("provenance", provenance), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SYMMETRY_ORBIT_CANDIDATE_SCHEMA, "label": self.label,
                "member_state_ids": list(self.member_state_ids), "ideal_multiplicity": self.ideal_multiplicity,
                "provenance": self.provenance, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "SymmetryOrbitCandidate":
        if p.get("schema") != SYMMETRY_ORBIT_CANDIDATE_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported symmetry-orbit-candidate schema.")
        return cls(str(p["label"]), tuple(p["member_state_ids"]), int(p["ideal_multiplicity"]),
                   str(p["provenance"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StructuralSymmetryOrbit:
    orbit_id: int
    candidate: SymmetryOrbitCandidate
    status: ExchangeabilityStatus
    observed_multiplicity: int
    resolved_channels: tuple[str, ...]
    reasons: tuple[str, ...]
    augmentation_performed: bool = False
    signature: str = ""

    def __post_init__(self) -> None:
        oid = int(self.orbit_id); observed = int(self.observed_multiplicity)
        if oid < 0 or observed != len(self.candidate.member_state_ids):
            raise JointEvidenceInputError("Invalid symmetry-orbit counters.")
        status = ExchangeabilityStatus(self.status); channels = tuple(sorted({str(v) for v in self.resolved_channels}))
        reasons = tuple(str(v) for v in self.reasons)
        if self.augmentation_performed:
            raise JointEvidenceInputError("Stage 11E5 forbids default symmetry augmentation.")
        payload = {"schema": STRUCTURAL_SYMMETRY_ORBIT_SCHEMA, "orbit_id": oid,
                   "candidate_signature": self.candidate.signature, "status": status.value,
                   "observed_multiplicity": observed, "resolved_channels": list(channels), "reasons": list(reasons),
                   "augmentation_performed": False}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Structural-symmetry-orbit signature is inconsistent.")
        for name, value in (("orbit_id", oid), ("status", status), ("observed_multiplicity", observed),
                            ("resolved_channels", channels), ("reasons", reasons),
                            ("augmentation_performed", False), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRUCTURAL_SYMMETRY_ORBIT_SCHEMA, "orbit_id": self.orbit_id,
                "candidate": self.candidate.to_dict(), "status": self.status.value,
                "observed_multiplicity": self.observed_multiplicity, "resolved_channels": list(self.resolved_channels),
                "reasons": list(self.reasons), "augmentation_performed": self.augmentation_performed,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StructuralSymmetryOrbit":
        if p.get("schema") != STRUCTURAL_SYMMETRY_ORBIT_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported structural-symmetry-orbit schema.")
        return cls(int(p["orbit_id"]), SymmetryOrbitCandidate.from_dict(p["candidate"]),
                   ExchangeabilityStatus(p["status"]), int(p["observed_multiplicity"]),
                   tuple(p.get("resolved_channels", ())), tuple(p.get("reasons", ())),
                   bool(p.get("augmentation_performed", False)), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ValidatedFrozenCatalog:
    sample_catalog_signature: str
    density_estimate_signature: str
    attractor_catalog_signature: str
    temporal_assignment_signature: str
    force_refinement_signature: str | None
    registered_structural_view_digest: str
    options: JointEvidenceOptions
    resources: JointEvidenceResourcePolicy
    block_plan: EvidenceBlockPlan
    states: tuple[ValidatedStatisticalState, ...]
    structural_complexes: tuple[StructuralSiteComplex, ...]
    symmetry_orbits: tuple[StructuralSymmetryOrbit, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sample = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        density = _sha(self.density_estimate_signature, "density_estimate_signature")
        attractor = _sha(self.attractor_catalog_signature, "attractor_catalog_signature")
        temporal = _sha(self.temporal_assignment_signature, "temporal_assignment_signature")
        force = None if self.force_refinement_signature is None else _sha(self.force_refinement_signature, "force_refinement_signature")
        view = _sha(self.registered_structural_view_digest, "registered_structural_view_digest")
        states = tuple(self.states); complexes = tuple(self.structural_complexes); orbits = tuple(self.symmetry_orbits)
        if tuple(v.state_id for v in states) != tuple(range(len(states))):
            raise JointEvidenceInputError("Validated states must be densely ordered.")
        if tuple(v.complex_id for v in complexes) != tuple(range(len(complexes))):
            raise JointEvidenceInputError("Structural complexes must be densely ordered.")
        if tuple(v.orbit_id for v in orbits) != tuple(range(len(orbits))):
            raise JointEvidenceInputError("Symmetry orbits must be densely ordered.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": VALIDATED_FROZEN_CATALOG_SCHEMA, "sample_catalog_signature": sample,
                   "density_estimate_signature": density, "attractor_catalog_signature": attractor,
                   "temporal_assignment_signature": temporal, "force_refinement_signature": force,
                   "registered_structural_view_digest": view, "options_signature": self.options.signature,
                   "resources_signature": self.resources.signature, "block_plan_signature": self.block_plan.signature,
                   "state_signatures": [v.signature for v in states], "complex_signatures": [v.signature for v in complexes],
                   "orbit_signatures": [v.signature for v in orbits], "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Validated-frozen-catalog signature is inconsistent.")
        for name, value in (("sample_catalog_signature", sample), ("density_estimate_signature", density),
                            ("attractor_catalog_signature", attractor), ("temporal_assignment_signature", temporal),
                            ("force_refinement_signature", force), ("registered_structural_view_digest", view),
                            ("states", states), ("structural_complexes", complexes), ("symmetry_orbits", orbits),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": VALIDATED_FROZEN_CATALOG_SCHEMA, "sample_catalog_signature": self.sample_catalog_signature,
                "density_estimate_signature": self.density_estimate_signature,
                "attractor_catalog_signature": self.attractor_catalog_signature,
                "temporal_assignment_signature": self.temporal_assignment_signature,
                "force_refinement_signature": self.force_refinement_signature,
                "registered_structural_view_digest": self.registered_structural_view_digest,
                "options": self.options.to_dict(), "resources": self.resources.to_dict(), "block_plan": self.block_plan.to_dict(),
                "states": [v.to_dict() for v in self.states],
                "structural_complexes": [v.to_dict() for v in self.structural_complexes],
                "symmetry_orbits": [v.to_dict() for v in self.symmetry_orbits],
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ValidatedFrozenCatalog":
        if p.get("schema") != VALIDATED_FROZEN_CATALOG_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported validated-frozen-catalog schema.")
        return cls(str(p["sample_catalog_signature"]), str(p["density_estimate_signature"]),
                   str(p["attractor_catalog_signature"]), str(p["temporal_assignment_signature"]),
                   p.get("force_refinement_signature"), str(p["registered_structural_view_digest"]),
                   JointEvidenceOptions.from_dict(p["options"]), JointEvidenceResourcePolicy.from_dict(p["resources"]),
                   EvidenceBlockPlan.from_dict(p["block_plan"]),
                   tuple(ValidatedStatisticalState.from_dict(v) for v in p["states"]),
                   tuple(StructuralSiteComplex.from_dict(v) for v in p["structural_complexes"]),
                   tuple(StructuralSymmetryOrbit.from_dict(v) for v in p["symmetry_orbits"]),
                   dict(p.get("metadata", {})), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FinalRefitCatalog:
    validated_frozen_catalog_signature: str
    refit_attractor_catalog_signature: str
    refit_force_refinement_signature: str | None
    state_count: int
    decision_inherited: bool = True
    parameter_validation_inherited: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        frozen = _sha(self.validated_frozen_catalog_signature, "validated_frozen_catalog_signature")
        attractor = _sha(self.refit_attractor_catalog_signature, "refit_attractor_catalog_signature")
        force = None if self.refit_force_refinement_signature is None else _sha(self.refit_force_refinement_signature, "refit_force_refinement_signature")
        count = _positive_int(self.state_count, "state_count")
        if not self.decision_inherited or self.parameter_validation_inherited:
            raise JointEvidenceInputError("A final refit inherits the decision but never parameter-validation evidence.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": FINAL_REFIT_CATALOG_SCHEMA, "validated_frozen_catalog_signature": frozen,
                   "refit_attractor_catalog_signature": attractor, "refit_force_refinement_signature": force,
                   "state_count": count, "decision_inherited": True, "parameter_validation_inherited": False,
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise JointEvidenceInputError("Final-refit-catalog signature is inconsistent.")
        for name, value in (("validated_frozen_catalog_signature", frozen), ("refit_attractor_catalog_signature", attractor),
                            ("refit_force_refinement_signature", force), ("state_count", count),
                            ("decision_inherited", True), ("parameter_validation_inherited", False),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FINAL_REFIT_CATALOG_SCHEMA,
                "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature,
                "refit_attractor_catalog_signature": self.refit_attractor_catalog_signature,
                "refit_force_refinement_signature": self.refit_force_refinement_signature,
                "state_count": self.state_count, "decision_inherited": self.decision_inherited,
                "parameter_validation_inherited": self.parameter_validation_inherited,
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "FinalRefitCatalog":
        if p.get("schema") != FINAL_REFIT_CATALOG_SCHEMA:
            raise JointEvidenceSerializationError("Unsupported final-refit-catalog schema.")
        return cls(str(p["validated_frozen_catalog_signature"]), str(p["refit_attractor_catalog_signature"]),
                   p.get("refit_force_refinement_signature"), int(p["state_count"]),
                   bool(p.get("decision_inherited", True)), bool(p.get("parameter_validation_inherited", False)),
                   dict(p.get("metadata", {})), str(p.get("signature", "")))


def _source_checks(catalog: FrameworkAlignedIonSampleCatalog, density: PeriodicSpeciesDensityEstimate,
                   attractors: DensityAttractorCatalog, temporal: ProvisionalTemporalAssignmentCatalog,
                   force: ForceRefinementCatalog | None, structural: RegisteredStructuralGeometryView) -> None:
    if density.catalog_signature != catalog.signature:
        raise JointEvidenceInputError("Density estimate belongs to another sample catalog.")
    if attractors.density_estimate_signature != density.signature:
        raise JointEvidenceInputError("Attractor catalog belongs to another density estimate.")
    if temporal.sample_catalog_signature != catalog.signature or temporal.density_estimate_signature != density.signature or temporal.attractor_catalog_signature != attractors.signature:
        raise JointEvidenceInputError("Temporal assignment source signatures disagree.")
    if force is not None and (force.sample_catalog_signature != catalog.signature or force.density_estimate_signature != density.signature or force.attractor_catalog_signature != attractors.signature):
        raise JointEvidenceInputError("Force-refinement source signatures disagree.")
    if structural.registration_signature != catalog.registration_signature:
        raise JointEvidenceInputError("Registered structural view and sample catalog use different registrations.")
    if density.domain.registration_signature != catalog.registration_signature:
        raise JointEvidenceInputError("Density domain and sample catalog use different registrations.")
    n = len(attractors.attractors)
    if len(temporal.attractor_diagnostics) != n or (force is not None and len(force.refinements) != n):
        raise JointEvidenceInputError("E2/E3/E4 state counts disagree.")


def _validate_block_plan(plan: EvidenceBlockPlan, catalog: FrameworkAlignedIonSampleCatalog) -> None:
    available = set(int(v) for v in np.unique(catalog.frame_indices))
    requested = set(plan.discovery_frame_indices) | set(plan.selection_frame_indices) | set(plan.final_validation_frame_indices) | set(plan.optional_refit_frame_indices)
    missing = sorted(requested - available)
    if missing:
        raise JointEvidenceInputError(f"Evidence block plan references unavailable frames: {missing[:8]}.")


def _coordinate_metric(density: PeriodicSpeciesDensityEstimate) -> CoordinateAnalysisGeometryMetric:
    return CoordinateAnalysisGeometryMetric(
        matrix=tuple(tuple(float(v) for v in row) for row in density.analysis_metric.covariant),
        units="registered_length_squared",
        coordinate_frame="registered_fractional",
        transformation_provenance=f"stage11e1-analysis-metric:{density.analysis_metric.signature}",
    )


def _periodic_distance(a: np.ndarray, b: np.ndarray, metric: CoordinateAnalysisGeometryMetric,
                       options: ClosestImageOptions) -> tuple[float, bool]:
    result = closest_periodic_image(a - b, cell=np.eye(3), metric=metric, options=options)
    return result.distance, result.ambiguous


def _ring_chemical_signature(ring: Any) -> str | None:
    if ring.status is not RegisteredRingViewStatus.RESOLVED or ring.registered is None:
        return None
    payload = {
        "t": [(a.atomic_number, a.element) for a in ring.registered.t_atoms],
        "o": [(a.atomic_number, a.element, a.oxygen_environment_signature, a.crystallographic_alias) for a in ring.registered.o_atoms],
    }
    return _digest(payload)


def _structural_objects(structural: RegisteredStructuralGeometryView) -> dict[tuple[StructuralObjectKind, int, str], dict[str, Any]]:
    objects: dict[tuple[StructuralObjectKind, int, str], dict[str, Any]] = {}
    for frame in structural.frames:
        for ring in frame.rings:
            if ring.status is not RegisteredRingViewStatus.RESOLVED or ring.registered is None or ring.physical is None:
                continue
            identity = f"ring:window={ring.window_index}:primitive={ring.primitive_ring_id}:face={ring.face_index}"
            key = (StructuralObjectKind.RING, ring.window_index, identity)
            record = objects.setdefault(key, {"centers": [], "chemical": [], "physical": {
                "window_index": ring.window_index, "primitive_ring_id": ring.primitive_ring_id,
                "face_index": ring.face_index, "ring_size": ring.ring_size,
                "physical_center_aperture_radius": ring.physical.center_aperture_radius,
                "physical_projected_area": ring.physical.projected_area}})
            record["centers"].append(np.asarray(ring.registered.center_fractional_wrapped, dtype=float))
            record["chemical"].append(_ring_chemical_signature(ring))
        for tile in frame.tiles:
            identity = f"tile_cage:{tile.tile_index}"
            key = (StructuralObjectKind.TILE_CAGE, tile.tile_index, identity)
            record = objects.setdefault(key, {"centers": [], "chemical": [], "physical": {
                "tile_index": tile.tile_index, "physical_volume": tile.physical_volume,
                "physical_surface_area": tile.physical_surface_area,
                "physical_diameter": tile.physical_diameter}})
            record["centers"].append(np.asarray(tile.registered_fractional_wrapped, dtype=float)); record["chemical"].append(None)
        for window in frame.windows:
            identity = f"window:{window.window_index}"
            key = (StructuralObjectKind.WINDOW, window.window_index, identity)
            record = objects.setdefault(key, {"centers": [], "chemical": [], "physical": {
                "window_index": window.window_index, "physical_area": window.physical_area,
                "physical_projected_aperture_radius": window.physical_projected_aperture_radius,
                "physical_planarity_rms": window.physical_planarity_rms}})
            record["centers"].append(np.asarray(window.registered_fractional_wrapped, dtype=float)); record["chemical"].append(None)
    return objects


def _association(state_id: int, anchor: np.ndarray, structural: RegisteredStructuralGeometryView,
                 density: PeriodicSpeciesDensityEstimate, options: JointEvidenceOptions,
                 object_records: Mapping[tuple[StructuralObjectKind, int, str], Mapping[str, Any]]) -> StructuralAssociationSet:
    metric = _coordinate_metric(density); raw: list[tuple[float, StructuralObjectKind, int, str, list[float], float, Mapping[str, Any], str | None, float | None]] = []
    for (kind, index, identity), record in object_records.items():
        distances: list[float] = []
        ambiguous_branch = False
        for center in record["centers"]:
            distance, ambiguous = _periodic_distance(anchor, np.asarray(center), metric, options.closest_image_options)
            distances.append(distance); ambiguous_branch |= ambiguous
        if not distances:
            continue
        mean = float(np.mean(distances)); maximum = float(np.max(distances))
        if mean > options.maximum_association_distance:
            continue
        chemistry_values = tuple(v for v in record["chemical"] if v is not None)
        chemical_signature = chemistry_values[0] if chemistry_values and len(set(chemistry_values)) == 1 else None
        chemical_score = 1.0 if chemical_signature is not None else (0.0 if chemistry_values else None)
        scale = max(options.maximum_association_distance / 2.0, np.finfo(float).eps)
        score = float(math.exp(-0.5 * (mean / scale) ** 2))
        if ambiguous_branch:
            score *= 0.5
        raw.append((mean, kind, index, identity, distances, score, record["physical"], chemical_signature, chemical_score))
    raw.sort(key=lambda v: (v[0], v[1].value, v[2], v[3]))
    candidates = tuple(StructuralAssociationCandidate(i, kind, index, identity, mean, max(distances),
                    score, chemical_score, len(distances), physical, chemical_signature)
                    for i, (mean, kind, index, identity, distances, score, physical, chemical_signature, chemical_score) in enumerate(raw))
    if not candidates:
        return StructuralAssociationSet(state_id, StructuralAssociationStatus.UNRESOLVED, (), None, None, structural.digest,
                                        diagnostic="no_structural_object_within_declared_association_distance")
    ambiguity = None if len(candidates) < 2 else candidates[1].mean_registered_distance - candidates[0].mean_registered_distance
    if ambiguity is not None and ambiguity <= options.association_ambiguity_distance:
        return StructuralAssociationSet(state_id, StructuralAssociationStatus.AMBIGUOUS, candidates, None, ambiguity,
                                        structural.digest, diagnostic="multiple_structural_objects_remain_geometrically_plausible")
    return StructuralAssociationSet(state_id, StructuralAssociationStatus.RESOLVED, candidates, 0, ambiguity, structural.digest)


def _block_summary(state_id: int, role: EvidenceBlockRole, frames: tuple[int, ...], catalog: FrameworkAlignedIonSampleCatalog,
                   temporal: ProvisionalTemporalAssignmentCatalog) -> BlockEvidenceSummary:
    if not frames:
        return BlockEvidenceSummary(state_id, role, 0, 0, 0, 0.0, None, None)
    block_mask = np.isin(catalog.frame_indices, np.asarray(frames, dtype=np.int64)) & temporal.membership.position_evidence_mask
    state_core = temporal.membership.core_membership == state_id
    state_basin = temporal.membership.basin_membership == state_id
    state_mask = block_mask & (state_core | state_basin)
    count = int(np.count_nonzero(state_mask)); core = int(np.count_nonzero(block_mask & state_core)); basin = int(np.count_nonzero(block_mask & state_basin & ~state_core))
    represented = float(np.sum(catalog.represented_time_weights[state_mask]))
    total = float(np.sum(catalog.represented_time_weights[block_mask]))
    fraction = None if total <= 0.0 else represented / total
    frame_occupancies: list[int] = []
    for frame in frames:
        frame_occupancies.append(int(np.count_nonzero(state_mask & (catalog.frame_indices == frame))))
    occupancy = None if not frame_occupancies else float(np.mean(frame_occupancies))
    return BlockEvidenceSummary(state_id, role, count, core, basin, represented, fraction, occupancy)


def _global_state_statistics(state_id: int, catalog: FrameworkAlignedIonSampleCatalog,
                             temporal: ProvisionalTemporalAssignmentCatalog) -> tuple[float, float]:
    evidence = temporal.membership.position_evidence_mask
    assigned = evidence & ((temporal.membership.core_membership == state_id) | (temporal.membership.basin_membership == state_id))
    total = float(np.sum(catalog.represented_time_weights[evidence])); represented = float(np.sum(catalog.represented_time_weights[assigned]))
    ion_time = 0.0 if total <= 0.0 else represented / total
    frame_values = [int(np.count_nonzero(assigned & (catalog.frame_indices == frame))) for frame in np.unique(catalog.frame_indices)]
    occupancy = 0.0 if not frame_values else float(np.mean(frame_values))
    return ion_time, occupancy


def _spatial_status(attractors: DensityAttractorCatalog, state_id: int) -> EvidenceChannelStatus:
    attractor = attractors.attractors[state_id]
    if attractor.geometry is AttractorGeometry.FLAT_UNRESOLVED_COMPONENT:
        return EvidenceChannelStatus.UNRESOLVED
    certificate = attractors.topology_certificate
    if certificate is None or certificate.status is TopologyStabilityStatus.UNASSESSED:
        return EvidenceChannelStatus.SUPPORTED
    if certificate.status is TopologyStabilityStatus.STABLE:
        return EvidenceChannelStatus.RESOLVED
    if certificate.status is TopologyStabilityStatus.UNSTABLE:
        return EvidenceChannelStatus.DISAGREEMENT
    return EvidenceChannelStatus.UNRESOLVED


def _temporal_status(temporal: ProvisionalTemporalAssignmentCatalog, state_id: int) -> EvidenceChannelStatus:
    status = temporal.attractor_diagnostics[state_id].support_status
    return {TemporalSupportStatus.PERSISTENT: EvidenceChannelStatus.RESOLVED,
            TemporalSupportStatus.NONPERSISTENT: EvidenceChannelStatus.REJECTED,
            TemporalSupportStatus.STRIDE_SENSITIVE: EvidenceChannelStatus.AMBIGUOUS,
            TemporalSupportStatus.INSUFFICIENT: EvidenceChannelStatus.INSUFFICIENT,
            TemporalSupportStatus.UNAVAILABLE: EvidenceChannelStatus.UNAVAILABLE}[status]


def _force_status(force: ForceRefinementCatalog | None, state_id: int) -> EvidenceChannelStatus:
    if force is None: return EvidenceChannelStatus.UNAVAILABLE
    status = force.refinements[state_id].evidence_status
    if status is ForceEvidenceStatus.RESOLVED: return EvidenceChannelStatus.RESOLVED
    if status is ForceEvidenceStatus.FORCE_UNAVAILABLE: return EvidenceChannelStatus.UNAVAILABLE
    if status is ForceEvidenceStatus.PMF_PROVENANCE_REJECTED: return EvidenceChannelStatus.REJECTED
    if status in {ForceEvidenceStatus.INSUFFICIENT_LOCAL_SUPPORT, ForceEvidenceStatus.RANK_DEFICIENT, ForceEvidenceStatus.ILL_CONDITIONED}:
        return EvidenceChannelStatus.INSUFFICIENT
    return EvidenceChannelStatus.UNRESOLVED


def _force_score_status(force: ForceRefinementCatalog | None, state_id: int, options: JointEvidenceOptions) -> EvidenceChannelStatus:
    if force is None: return EvidenceChannelStatus.UNAVAILABLE
    ref = force.refinements[state_id]
    if ref.evidence_status is not ForceEvidenceStatus.RESOLVED or ref.density_force_residual_norm is None:
        return EvidenceChannelStatus.INSUFFICIENT if ref.evidence_status is not ForceEvidenceStatus.FORCE_UNAVAILABLE else EvidenceChannelStatus.UNAVAILABLE
    return EvidenceChannelStatus.RESOLVED if ref.density_force_residual_norm <= options.force_score_residual_tolerance else EvidenceChannelStatus.DISAGREEMENT


def _stationarity_status(catalog: FrameworkAlignedIonSampleCatalog) -> EvidenceChannelStatus:
    state = catalog.sampling_state
    if state.equilibrium_status is EquilibriumStatus.DECLARED_NONEQUILIBRIUM or state.stationarity_status is StationarityStatus.NONSTATIONARY:
        return EvidenceChannelStatus.REJECTED
    if state.equilibrium_status is EquilibriumStatus.DECLARED_EQUILIBRIUM and state.stationarity_status is StationarityStatus.TESTED_STATIONARY:
        return EvidenceChannelStatus.RESOLVED
    if state.equilibrium_status is EquilibriumStatus.DECLARED_EQUILIBRIUM and state.stationarity_status is StationarityStatus.ASSUMED_STATIONARY:
        return EvidenceChannelStatus.SUPPORTED
    return EvidenceChannelStatus.UNAVAILABLE


def _geometry_status(association: StructuralAssociationSet) -> EvidenceChannelStatus:
    return {StructuralAssociationStatus.RESOLVED: EvidenceChannelStatus.RESOLVED,
            StructuralAssociationStatus.AMBIGUOUS: EvidenceChannelStatus.AMBIGUOUS,
            StructuralAssociationStatus.UNRESOLVED: EvidenceChannelStatus.UNRESOLVED,
            StructuralAssociationStatus.STRUCTURAL_VIEW_UNAVAILABLE: EvidenceChannelStatus.UNAVAILABLE}[association.status]


def _curvature_status(force: ForceRefinementCatalog | None, state_id: int) -> EvidenceChannelStatus:
    if force is None: return EvidenceChannelStatus.UNAVAILABLE
    ref = force.refinements[state_id]
    if ref.evidence_status is not ForceEvidenceStatus.RESOLVED:
        return EvidenceChannelStatus.UNAVAILABLE if ref.evidence_status is ForceEvidenceStatus.FORCE_UNAVAILABLE else EvidenceChannelStatus.INSUFFICIENT
    if ref.curvature_class in {CurvatureClass.STABLE_POINT, CurvatureClass.SOFT_MANIFOLD}:
        return EvidenceChannelStatus.RESOLVED
    if ref.curvature_class is CurvatureClass.SADDLE_OR_UNSTABLE:
        return EvidenceChannelStatus.DISAGREEMENT
    return EvidenceChannelStatus.UNRESOLVED


def _final_validation(blocks: tuple[BlockEvidenceSummary, ...], plan: EvidenceBlockPlan,
                      options: JointEvidenceOptions) -> FinalValidationStatus:
    selection = blocks[1]
    validation = blocks[2]
    if plan.independence_status is ValidationIndependenceStatus.INDEPENDENT_VALIDATION_UNAVAILABLE:
        return FinalValidationStatus.INDEPENDENT_VALIDATION_UNAVAILABLE
    if plan.independence_status is ValidationIndependenceStatus.SELECTION_CONDITIONED_VALIDATION:
        return FinalValidationStatus.SELECTION_CONDITIONED
    if selection.sample_count < options.minimum_block_samples or validation.sample_count < options.minimum_block_samples:
        return FinalValidationStatus.INSUFFICIENT_TRANSFER_SUPPORT
    if selection.block_ion_time_fraction is None or validation.block_ion_time_fraction is None:
        return FinalValidationStatus.INSUFFICIENT_TRANSFER_SUPPORT
    if abs(selection.block_ion_time_fraction - validation.block_ion_time_fraction) > options.maximum_transfer_fraction_shift:
        return FinalValidationStatus.INDEPENDENT_VALIDATION_DISAGREEMENT
    return FinalValidationStatus.INDEPENDENT_VALIDATION_SUPPORTED


def _overall(spatial: EvidenceChannelStatus, temporal: EvidenceChannelStatus, force: EvidenceChannelStatus,
             force_score: EvidenceChannelStatus, stationarity: EvidenceChannelStatus, geometry: EvidenceChannelStatus,
             curvature: EvidenceChannelStatus, final: FinalValidationStatus) -> OverallCertificationStatus:
    if spatial is EvidenceChannelStatus.REJECTED or temporal is EvidenceChannelStatus.REJECTED:
        return OverallCertificationStatus.REJECTED
    if spatial is EvidenceChannelStatus.UNRESOLVED:
        return OverallCertificationStatus.UNRESOLVED
    if EvidenceChannelStatus.DISAGREEMENT in {spatial, force_score, curvature} or final is FinalValidationStatus.INDEPENDENT_VALIDATION_DISAGREEMENT:
        return OverallCertificationStatus.EVIDENCE_DISAGREEMENT
    spatial_ok = spatial in {EvidenceChannelStatus.RESOLVED, EvidenceChannelStatus.SUPPORTED}
    temporal_ok = temporal is EvidenceChannelStatus.RESOLVED
    force_ok = force is EvidenceChannelStatus.RESOLVED and force_score is EvidenceChannelStatus.RESOLVED and curvature is EvidenceChannelStatus.RESOLVED
    if spatial_ok and temporal_ok and force_ok:
        if stationarity in {EvidenceChannelStatus.RESOLVED, EvidenceChannelStatus.SUPPORTED} and geometry is EvidenceChannelStatus.RESOLVED and final is FinalValidationStatus.INDEPENDENT_VALIDATION_SUPPORTED:
            return OverallCertificationStatus.FULLY_VALIDATED
        return OverallCertificationStatus.FORCE_VALIDATED
    if spatial_ok and temporal_ok:
        return OverallCertificationStatus.SPATIAL_TEMPORAL_VALIDATED
    return OverallCertificationStatus.SPATIAL_CANDIDATE


def _structural_complexes(states: Sequence[ValidatedStatisticalState]) -> tuple[StructuralSiteComplex, ...]:
    groups: dict[tuple[StructuralObjectKind, str], list[int]] = defaultdict(list)
    for state in states:
        primary = state.structural_association.primary
        if primary is not None:
            groups[(primary.kind, primary.persistent_identity)].append(state.state_id)
    return tuple(StructuralSiteComplex(i, kind, identity, tuple(members)) for i, ((kind, identity), members) in enumerate(sorted(groups.items(), key=lambda p: (p[0][0].value, p[0][1]))))


def _relative_spread(values: Sequence[float]) -> float:
    if not values: return math.inf
    mean = float(np.mean(values))
    return float((max(values) - min(values)) / max(abs(mean), np.finfo(float).eps))


def _exchangeability(candidate: SymmetryOrbitCandidate, states: Sequence[ValidatedStatisticalState],
                     temporal: ProvisionalTemporalAssignmentCatalog, force: ForceRefinementCatalog | None,
                     options: JointEvidenceOptions, orbit_id: int) -> StructuralSymmetryOrbit:
    if any(v >= len(states) for v in candidate.member_state_ids):
        raise JointEvidenceInputError("Symmetry-orbit candidate references an unknown state.")
    members = [states[v] for v in candidate.member_state_ids]; reasons: list[str] = []; channels: list[str] = []; rejected = False
    if _relative_spread([v.basin_probability for v in members]) <= options.exchangeability_probability_tolerance:
        channels.append("ion_time_probability")
    else:
        rejected = True; reasons.append("ion_time_probability_not_exchangeable")
    if _relative_spread([v.mean_occupancy for v in members]) <= options.exchangeability_occupancy_tolerance:
        channels.append("mean_occupancy")
    else:
        rejected = True; reasons.append("mean_occupancy_not_exchangeable")
    kinds = [None if v.structural_association.primary is None else v.structural_association.primary.kind for v in members]
    chem = [None if v.structural_association.primary is None else v.structural_association.primary.chemical_signature for v in members]
    if all(k is not None for k in kinds) and len(set(kinds)) == 1 and len(set(chem)) <= 1:
        channels.append("structural_geometry_and_chemistry")
    elif any(k is None for k in kinds):
        reasons.append("structural_association_unresolved")
    else:
        rejected = True; reasons.append("structural_geometry_or_chemistry_breaks_exchangeability")
    temporal_statuses = [temporal.attractor_diagnostics[v.state_id].support_status for v in members]
    persistence = [temporal.attractor_diagnostics[v.state_id].persistence_ratio for v in members]
    if all(s is TemporalSupportStatus.PERSISTENT for s in temporal_statuses) and all(p is not None for p in persistence):
        if _relative_spread([float(p) for p in persistence if p is not None]) <= options.exchangeability_persistence_tolerance:
            channels.append("temporal_persistence")
        else:
            rejected = True; reasons.append("temporal_persistence_not_exchangeable")
    else:
        reasons.append("temporal_exchangeability_insufficient")
    jump_counts = []
    for state in members:
        jump_counts.append(sum(1 for p in temporal.passages if p.source_attractor_id == state.state_id and p.target_attractor_id is not None))
    if sum(jump_counts) > 0:
        if max(jump_counts) - min(jump_counts) <= 1:
            channels.append("transition_counts")
        else:
            rejected = True; reasons.append("transition_counts_not_exchangeable")
    else:
        reasons.append("transition_exchangeability_insufficient")
    if force is not None:
        force_status = [force.refinements[v.state_id].evidence_status for v in members]
        curvature = [force.refinements[v.state_id].curvature_class for v in members]
        if all(s is ForceEvidenceStatus.RESOLVED for s in force_status) and len(set(curvature)) == 1:
            channels.append("force_and_curvature")
        elif any(s is ForceEvidenceStatus.RESOLVED for s in force_status):
            rejected = True; reasons.append("force_or_curvature_not_exchangeable")
        else:
            reasons.append("force_exchangeability_insufficient")
    else:
        reasons.append("force_exchangeability_unavailable")
    if rejected:
        status = ExchangeabilityStatus.REJECTED
    elif {"ion_time_probability", "mean_occupancy", "structural_geometry_and_chemistry", "temporal_persistence", "transition_counts", "force_and_curvature"}.issubset(channels):
        status = ExchangeabilityStatus.SUPPORTED
    else:
        status = ExchangeabilityStatus.INSUFFICIENT
    return StructuralSymmetryOrbit(orbit_id, candidate, status, len(candidate.member_state_ids), tuple(channels), tuple(reasons), False)


def prepare_validated_frozen_catalog(
    catalog: FrameworkAlignedIonSampleCatalog,
    density_estimate: PeriodicSpeciesDensityEstimate,
    attractor_catalog: DensityAttractorCatalog,
    temporal_assignment: ProvisionalTemporalAssignmentCatalog,
    registered_structural_view: RegisteredStructuralGeometryView,
    *,
    force_refinement: ForceRefinementCatalog | None = None,
    block_plan: EvidenceBlockPlan | None = None,
    symmetry_orbit_candidates: Sequence[SymmetryOrbitCandidate] = (),
    options: JointEvidenceOptions | None = None,
    resources: JointEvidenceResourcePolicy | None = None,
) -> ValidatedFrozenCatalog:
    """Freeze and validate one selected E2 catalog without relocating states."""

    options = options or JointEvidenceOptions(); resources = resources or JointEvidenceResourcePolicy()
    _source_checks(catalog, density_estimate, attractor_catalog, temporal_assignment, force_refinement, registered_structural_view)
    frame_indices = tuple(int(v) for v in np.unique(catalog.frame_indices))
    plan = block_plan or EvidenceBlockPlan.discovery_only(frame_indices)
    _validate_block_plan(plan, catalog)
    n_states = len(attractor_catalog.attractors)
    if n_states > resources.max_states:
        raise JointEvidenceResourceError(f"states {n_states}>{resources.max_states}")
    object_records = _structural_objects(registered_structural_view)
    if n_states * max(len(object_records), 1) > resources.max_structural_candidates:
        raise JointEvidenceResourceError("Structural association candidate work exceeds max_structural_candidates.")
    if catalog.n_samples * 4 > resources.max_block_memberships:
        raise JointEvidenceResourceError("Block membership work exceeds max_block_memberships.")
    orbit_pairs = sum(len(v.member_state_ids) * (len(v.member_state_ids) - 1) // 2 for v in symmetry_orbit_candidates)
    if orbit_pairs > resources.max_orbit_pairs:
        raise JointEvidenceResourceError("Symmetry exchangeability work exceeds max_orbit_pairs.")
    states: list[ValidatedStatisticalState] = []
    for sid, attractor in enumerate(attractor_catalog.attractors):
        association = _association(sid, attractor.anchor_fractional, registered_structural_view, density_estimate, options, object_records)
        blocks = tuple(_block_summary(sid, role, plan.frames_for(role), catalog, temporal_assignment) for role in EvidenceBlockRole)
        final = _final_validation(blocks, plan, options)
        spatial = _spatial_status(attractor_catalog, sid); temporal = _temporal_status(temporal_assignment, sid)
        force = _force_status(force_refinement, sid); force_score = _force_score_status(force_refinement, sid, options)
        stationarity = _stationarity_status(catalog); geometry = _geometry_status(association); curvature = _curvature_status(force_refinement, sid)
        overall = _overall(spatial, temporal, force, force_score, stationarity, geometry, curvature, final)
        diagnostics: list[str] = []
        if force_score is EvidenceChannelStatus.DISAGREEMENT: diagnostics.append("matched_force_disagrees_with_density_score_covector")
        if final is FinalValidationStatus.INDEPENDENT_VALIDATION_UNAVAILABLE: diagnostics.append("independent_final_validation_unavailable")
        if association.status is StructuralAssociationStatus.AMBIGUOUS: diagnostics.append("structural_association_ambiguity_retained")
        evidence = SiteEvidenceStatus(spatial, temporal, force, force_score, stationarity, geometry, curvature, overall, final, tuple(diagnostics))
        ion_time, occupancy = _global_state_statistics(sid, catalog, temporal_assignment)
        states.append(ValidatedStatisticalState(sid, sid, attractor.signature, attractor.anchor_fractional,
                      attractor.geometry, attractor.basin_probability, ion_time, occupancy, evidence, association, blocks))
    complexes = _structural_complexes(states)
    orbits = tuple(_exchangeability(candidate, states, temporal_assignment, force_refinement, options, i)
                   for i, candidate in enumerate(symmetry_orbit_candidates))
    records = len(states) + sum(len(v.structural_association.candidates) for v in states) + len(complexes) + len(orbits)
    if records > resources.max_serialized_records:
        raise JointEvidenceResourceError("Output records exceed max_serialized_records.")
    metadata = {
        "selected_catalog_frozen_before_final_validation": True,
        "state_relocation_performed": False,
        "nearest_structural_object_fallback_performed": False,
        "symmetry_sample_augmentation_performed": False,
        "force_compared_to_density_score_covector": True,
        "force_compared_to_unqualified_gradient": False,
        "coordination_fingerprints_computed": False,
        "final_events_published": False,
        "validation_independence_status": plan.independence_status.value,
        "method_background": (
            "Sarich-Noe-Schuette core-set validation DOI 10.1137/090764049",
            "Prinz et al. Markov-model validation DOI 10.1063/1.3565032",
        ),
    }
    return ValidatedFrozenCatalog(catalog.signature, density_estimate.signature, attractor_catalog.signature,
                                  temporal_assignment.signature, None if force_refinement is None else force_refinement.signature,
                                  registered_structural_view.digest, options, resources, plan, tuple(states), complexes, orbits, metadata)


def prepare_final_refit_catalog(validated: ValidatedFrozenCatalog, refit_attractor_catalog: DensityAttractorCatalog,
                                *, refit_force_refinement: ForceRefinementCatalog | None = None,
                                metadata: Mapping[str, Any] | None = None) -> FinalRefitCatalog:
    """Record an optional all-data refit without inheriting parameter validation."""
    if len(refit_attractor_catalog.attractors) != len(validated.states):
        raise JointEvidenceInputError("Final refit must preserve the validated state count and decision identity.")
    if refit_force_refinement is not None and refit_force_refinement.attractor_catalog_signature != refit_attractor_catalog.signature:
        raise JointEvidenceInputError("Final-refit force catalog belongs to another attractor catalog.")
    return FinalRefitCatalog(validated.signature, refit_attractor_catalog.signature,
                             None if refit_force_refinement is None else refit_force_refinement.signature,
                             len(validated.states), True, False,
                             {"validated_parameter_evidence_not_inherited": True, **dict(metadata or {})})


__all__ = [
    "BLOCK_EVIDENCE_SUMMARY_SCHEMA", "EVIDENCE_BLOCK_PLAN_SCHEMA", "FINAL_REFIT_CATALOG_SCHEMA",
    "JOINT_EVIDENCE_OPTIONS_SCHEMA", "JOINT_EVIDENCE_RESOURCES_SCHEMA", "JOINT_EVIDENCE_STAGE",
    "SITE_EVIDENCE_STATUS_SCHEMA", "STRUCTURAL_ASSOCIATION_CANDIDATE_SCHEMA", "STRUCTURAL_ASSOCIATION_SET_SCHEMA",
    "STRUCTURAL_SITE_COMPLEX_SCHEMA", "STRUCTURAL_SYMMETRY_ORBIT_SCHEMA", "SYMMETRY_ORBIT_CANDIDATE_SCHEMA",
    "VALIDATED_FROZEN_CATALOG_SCHEMA", "VALIDATED_STATISTICAL_STATE_SCHEMA", "BlockEvidenceSummary",
    "EvidenceBlockPlan", "EvidenceBlockRole", "EvidenceChannelStatus", "ExchangeabilityStatus", "FinalRefitCatalog",
    "FinalValidationStatus", "JointEvidenceError", "JointEvidenceInputError", "JointEvidenceOptions",
    "JointEvidenceResourceError", "JointEvidenceResourcePolicy", "JointEvidenceSerializationError",
    "OverallCertificationStatus", "SiteEvidenceStatus", "StructuralAssociationCandidate", "StructuralAssociationSet",
    "StructuralAssociationStatus", "StructuralObjectKind", "StructuralSiteComplex", "StructuralSymmetryOrbit",
    "SymmetryOrbitCandidate", "ValidatedFrozenCatalog", "ValidatedStatisticalState", "ValidationIndependenceStatus",
    "prepare_final_refit_catalog", "prepare_validated_frozen_catalog",
]
