"""Stage-11E2 trajectory assignment to explicit geometric site hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._neighbors import minimum_image_geometry
from .ring_geometry import RingSideFrame
from .ring_geometry_frames import FrameRingGeometryCatalog, FrameRingGeometryStatus
from .ring_site import (
    SiteLandscapeRegime,
    SiteMicrostate,
    SiteStateKind,
    SpeciesSiteTopologyCatalog,
)
from .selection import resolve_atom_selection
from .site_kinetic_network import PeriodicSiteKineticNetwork
from .tiling_geometry_frames import FrameTilingGeometryCatalog
from .topology_statistics import (
    FrameAxis,
    StateTransitionStatistics,
    TemporalStatisticsOptions,
    build_frame_axis,
    compute_state_transition_statistics,
)
from ..collection import AtomisticFrameCollection

CANONICAL_SITE_ASSIGNMENT_SCHEMA = "mdstats.site-assignment.v1"
SITE_ASSIGNMENT_DIGEST_ALGORITHM = "sha256-canonical-json-v1"

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]


class SiteAssignmentError(ValueError):
    """Base exception for Stage-11E2 site assignment."""


class SiteAssignmentInputError(SiteAssignmentError):
    """Raised when assignment inputs violate the public contract."""


class SiteAssignmentInvariantError(SiteAssignmentError):
    """Raised when source-bound identities or generated results disagree."""


class SiteAssignmentResourceError(SiteAssignmentError):
    """Raised transactionally before declared finite-work limits are exceeded."""


class SiteAssignmentSerializationError(SiteAssignmentError):
    """Raised when canonical replay disagrees with serialized data."""


class SiteAssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    ANNULAR_ASSIGNED = "annular_assigned"
    AMBIGUOUS = "ambiguous"
    TRANSITION_REGION = "transition_region"
    UNASSIGNED = "unassigned"
    FRAME_UNRESOLVED = "frame_unresolved"


class AuxiliaryAssignmentState(str, Enum):
    AMBIGUOUS = "ambiguous"
    TRANSITION_REGION = "transition_region"
    UNASSIGNED = "unassigned"
    FRAME_UNRESOLVED = "frame_unresolved"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SiteAssignmentInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise SiteAssignmentInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive_int(value: object, *, name: str) -> int:
    result = _nonnegative_int(value, name=name)
    if result == 0:
        raise SiteAssignmentInputError(f"{name} must be positive.")
    return result


def _finite(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise SiteAssignmentInputError(f"{name} must be finite.")
    return float(value)


def _positive(value: object, *, name: str) -> float:
    result = _finite(value, name=name)
    if result <= 0:
        raise SiteAssignmentInputError(f"{name} must be positive.")
    return result


def _float3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = tuple(_finite(v, name=name) for v in value)
    if len(result) != 3:
        raise SiteAssignmentInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _shift(value: Sequence[object], *, name: str) -> tuple[int, int, int]:
    if len(value) != 3 or any(isinstance(v, bool) or not isinstance(v, Integral) for v in value):
        raise SiteAssignmentInputError(f"{name} must contain three integers.")
    return tuple(int(v) for v in value)  # type: ignore[return-value]


def _readonly_int(values: ArrayLike, *, ndim: int) -> IntArray:
    array = np.array(values, dtype=np.int64, copy=True)
    if array.ndim != ndim:
        raise SiteAssignmentInputError(f"Expected an integer array with ndim={ndim}.")
    array.setflags(write=False)
    return array


def _readonly_float(values: ArrayLike, *, ndim: int) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.ndim != ndim or np.any(~np.isfinite(array)):
        raise SiteAssignmentInputError(f"Expected a finite float array with ndim={ndim}.")
    array.setflags(write=False)
    return array


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(v) for v in value)
    if isinstance(value, np.ndarray):
        copy = np.array(value, copy=True)
        copy.setflags(write=False)
        return copy
    return value


@dataclass(frozen=True, slots=True)
class SiteAssignmentRule:
    """One explicit geometric basin rule for a selected state family."""

    rule_id: str
    normal_halfwidth: float
    in_plane_halfwidth: float
    transition_multiplier: float = 1.5
    state_key: str | None = None
    state_kind: SiteStateKind | None = None
    regime: SiteLandscapeRegime | None = None
    interface_label: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not self.rule_id.strip():
            raise SiteAssignmentInputError("rule_id must be nonempty.")
        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "normal_halfwidth", _positive(self.normal_halfwidth, name="normal_halfwidth"))
        object.__setattr__(self, "in_plane_halfwidth", _positive(self.in_plane_halfwidth, name="in_plane_halfwidth"))
        multiplier = _finite(self.transition_multiplier, name="transition_multiplier")
        if multiplier <= 1.0:
            raise SiteAssignmentInputError("transition_multiplier must exceed one.")
        object.__setattr__(self, "transition_multiplier", multiplier)
        if self.state_key is not None:
            if not isinstance(self.state_key, str) or not self.state_key:
                raise SiteAssignmentInputError("state_key must be nonempty when supplied.")
        if self.state_kind is not None:
            object.__setattr__(self, "state_kind", SiteStateKind(self.state_kind))
        if self.regime is not None:
            object.__setattr__(self, "regime", SiteLandscapeRegime(self.regime))
        if self.interface_label is not None and (not isinstance(self.interface_label, str) or not self.interface_label):
            raise SiteAssignmentInputError("interface_label must be nonempty when supplied.")
        if self.state_key is None and self.state_kind is None:
            raise SiteAssignmentInputError("A rule requires state_key or state_kind.")

    def matches(self, state: SiteMicrostate, interface_label: str | None) -> bool:
        return bool(
            (self.state_key is None or self.state_key == state.state_key)
            and (self.state_kind is None or self.state_kind is state.kind)
            and (self.regime is None or self.regime is state.regime)
            and (self.interface_label is None or self.interface_label == interface_label)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "normal_halfwidth": self.normal_halfwidth,
            "in_plane_halfwidth": self.in_plane_halfwidth,
            "transition_multiplier": self.transition_multiplier,
            "state_key": self.state_key,
            "state_kind": None if self.state_kind is None else self.state_kind.value,
            "regime": None if self.regime is None else self.regime.value,
            "interface_label": self.interface_label,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SiteAssignmentRule":
        try:
            return cls(
                rule_id=str(payload["rule_id"]),
                normal_halfwidth=float(payload["normal_halfwidth"]),
                in_plane_halfwidth=float(payload["in_plane_halfwidth"]),
                transition_multiplier=float(payload.get("transition_multiplier", 1.5)),
                state_key=payload.get("state_key"),
                state_kind=None if payload.get("state_kind") is None else SiteStateKind(payload["state_kind"]),
                regime=None if payload.get("regime") is None else SiteLandscapeRegime(payload["regime"]),
                interface_label=payload.get("interface_label"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteAssignmentSerializationError("Invalid assignment-rule payload.") from exc


@dataclass(frozen=True, slots=True)
class SiteAssignmentProfile:
    profile_id: str
    site_topology_profile_id: str
    species: str
    description: str
    rules: tuple[SiteAssignmentRule, ...]
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("profile_id", "site_topology_profile_id", "species", "description"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SiteAssignmentInputError(f"{name} must be nonempty.")
            object.__setattr__(self, name, value.strip())
        rules = tuple(self.rules)
        if not rules or any(not isinstance(v, SiteAssignmentRule) for v in rules):
            raise SiteAssignmentInputError("rules must contain SiteAssignmentRule records.")
        if len({v.rule_id for v in rules}) != len(rules):
            raise SiteAssignmentInputError("rule_id values must be unique.")
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "references", tuple(str(v) for v in self.references))

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "site_topology_profile_id": self.site_topology_profile_id,
            "species": self.species,
            "description": self.description,
            "rules": [v.to_dict() for v in self.rules],
            "references": list(self.references),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SiteAssignmentProfile":
        try:
            return cls(
                str(payload["profile_id"]),
                str(payload["site_topology_profile_id"]),
                str(payload["species"]),
                str(payload["description"]),
                tuple(SiteAssignmentRule.from_dict(v) for v in payload["rules"]),
                tuple(str(v) for v in payload.get("references", ())),
            )
        except SiteAssignmentError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteAssignmentSerializationError("Invalid assignment-profile payload.") from exc


@dataclass(frozen=True, slots=True)
class SiteAssignmentOptions:
    max_candidate_diagnostics: int = 4
    time_unit: str = "ps"

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_candidate_diagnostics", _positive_int(self.max_candidate_diagnostics, name="max_candidate_diagnostics"))
        if not isinstance(self.time_unit, str) or not self.time_unit.strip():
            raise SiteAssignmentInputError("time_unit must be nonempty.")
        object.__setattr__(self, "time_unit", self.time_unit.strip())

    def to_dict(self) -> dict[str, Any]:
        return {"max_candidate_diagnostics": self.max_candidate_diagnostics, "time_unit": self.time_unit}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SiteAssignmentOptions":
        return cls(int(payload["max_candidate_diagnostics"]), str(payload["time_unit"]))


@dataclass(frozen=True, slots=True)
class SiteAssignmentResources:
    max_frames: int = 1_000_000
    max_ions: int = 100_000
    max_states: int = 1_000_000
    max_candidate_evaluations: int = 1_000_000_000
    max_retained_diagnostics: int = 10_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SiteAssignmentResources":
        return cls(**{name: int(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class SiteCandidateDiagnostic:
    state_index: int
    state_key: str
    rule_id: str
    core: bool
    transition: bool
    score: float
    distance: float
    site_image_shift: tuple[int, int, int]
    relative_cartesian: tuple[float, float, float]
    ion_local_coordinates: tuple[float, float, float] | None
    annular_angle: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_index", _nonnegative_int(self.state_index, name="state_index"))
        if not isinstance(self.state_key, str) or not isinstance(self.rule_id, str):
            raise SiteAssignmentInputError("Candidate keys must be strings.")
        score = _finite(self.score, name="score")
        distance = _finite(self.distance, name="distance")
        if score < 0 or distance < 0:
            raise SiteAssignmentInputError("Candidate score and distance must be nonnegative.")
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "distance", distance)
        object.__setattr__(self, "site_image_shift", _shift(self.site_image_shift, name="site_image_shift"))
        object.__setattr__(self, "relative_cartesian", _float3(self.relative_cartesian, name="relative_cartesian"))
        if self.ion_local_coordinates is not None:
            object.__setattr__(self, "ion_local_coordinates", _float3(self.ion_local_coordinates, name="ion_local_coordinates"))
        if self.annular_angle is not None:
            object.__setattr__(self, "annular_angle", _finite(self.annular_angle, name="annular_angle"))
        if self.core and not self.transition:
            raise SiteAssignmentInputError("Core candidates are also transition-shell candidates.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_index": self.state_index,
            "state_key": self.state_key,
            "rule_id": self.rule_id,
            "core": self.core,
            "transition": self.transition,
            "score": self.score,
            "distance": self.distance,
            "site_image_shift": list(self.site_image_shift),
            "relative_cartesian": list(self.relative_cartesian),
            "ion_local_coordinates": None if self.ion_local_coordinates is None else list(self.ion_local_coordinates),
            "annular_angle": self.annular_angle,
        }


@dataclass(frozen=True, slots=True)
class IonFrameSiteAssignment:
    result_position: int
    collection_frame_index: int
    frame_id: int
    atom_index: int
    status: SiteAssignmentStatus
    state_index: int | None
    site_image_shift: tuple[int, int, int] | None
    relative_cartesian: tuple[float, float, float] | None
    ion_local_coordinates: tuple[float, float, float] | None
    annular_angle: float | None
    available_state_count: int
    diagnostics: tuple[SiteCandidateDiagnostic, ...]

    def __post_init__(self) -> None:
        for name in ("result_position", "collection_frame_index", "atom_index", "available_state_count"):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, Integral):
            raise SiteAssignmentInputError("frame_id must be an integer.")
        object.__setattr__(self, "frame_id", int(self.frame_id))
        status = SiteAssignmentStatus(self.status)
        object.__setattr__(self, "status", status)
        accepted = status in {SiteAssignmentStatus.ASSIGNED, SiteAssignmentStatus.ANNULAR_ASSIGNED}
        values = (self.state_index, self.site_image_shift, self.relative_cartesian)
        if accepted:
            if any(v is None for v in values):
                raise SiteAssignmentInputError("Accepted assignments require state and periodic geometry.")
            object.__setattr__(self, "state_index", _nonnegative_int(self.state_index, name="state_index"))
            object.__setattr__(self, "site_image_shift", _shift(self.site_image_shift, name="site_image_shift"))
            object.__setattr__(self, "relative_cartesian", _float3(self.relative_cartesian, name="relative_cartesian"))
            if self.ion_local_coordinates is not None:
                object.__setattr__(self, "ion_local_coordinates", _float3(self.ion_local_coordinates, name="ion_local_coordinates"))
        elif any(v is not None for v in values) or self.ion_local_coordinates is not None or self.annular_angle is not None:
            raise SiteAssignmentInputError("Nonaccepted outcomes cannot claim one authoritative state geometry.")
        if status is SiteAssignmentStatus.ANNULAR_ASSIGNED:
            object.__setattr__(self, "annular_angle", _finite(self.annular_angle, name="annular_angle"))
        elif accepted and self.annular_angle is not None:
            raise SiteAssignmentInputError("Only annular assignments carry annular_angle.")
        diagnostics = tuple(self.diagnostics)
        if any(not isinstance(v, SiteCandidateDiagnostic) for v in diagnostics):
            raise SiteAssignmentInputError("diagnostics have the wrong type.")
        object.__setattr__(self, "diagnostics", diagnostics)

    @property
    def accepted(self) -> bool:
        return self.status in {SiteAssignmentStatus.ASSIGNED, SiteAssignmentStatus.ANNULAR_ASSIGNED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_position": self.result_position,
            "collection_frame_index": self.collection_frame_index,
            "frame_id": self.frame_id,
            "atom_index": self.atom_index,
            "status": self.status.value,
            "state_index": self.state_index,
            "site_image_shift": None if self.site_image_shift is None else list(self.site_image_shift),
            "relative_cartesian": None if self.relative_cartesian is None else list(self.relative_cartesian),
            "ion_local_coordinates": None if self.ion_local_coordinates is None else list(self.ion_local_coordinates),
            "annular_angle": self.annular_angle,
            "available_state_count": self.available_state_count,
            "diagnostics": [v.to_dict() for v in self.diagnostics],
        }


@dataclass(frozen=True, slots=True)
class ObservedSiteTransition:
    event_index: int
    atom_index: int
    result_position_before: int
    result_position_after: int
    source_state_index: int
    target_state_index: int
    source_image_shift: tuple[int, int, int]
    target_image_shift: tuple[int, int, int]
    observed_translation: tuple[int, int, int]
    matching_edge_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        for name in ("event_index", "atom_index", "result_position_before", "result_position_after", "source_state_index", "target_state_index"):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        source = _shift(self.source_image_shift, name="source_image_shift")
        target = _shift(self.target_image_shift, name="target_image_shift")
        observed = _shift(self.observed_translation, name="observed_translation")
        if observed != tuple(t - s for s, t in zip(source, target, strict=True)):
            raise SiteAssignmentInputError("observed_translation disagrees with image shifts.")
        matches = tuple(_nonnegative_int(v, name="edge_index") for v in self.matching_edge_indices)
        if matches != tuple(sorted(set(matches))):
            raise SiteAssignmentInputError("matching_edge_indices must be sorted and unique.")
        object.__setattr__(self, "source_image_shift", source)
        object.__setattr__(self, "target_image_shift", target)
        object.__setattr__(self, "observed_translation", observed)
        object.__setattr__(self, "matching_edge_indices", matches)

    @property
    def on_network(self) -> bool:
        return bool(self.matching_edge_indices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_index": self.event_index,
            "atom_index": self.atom_index,
            "result_position_before": self.result_position_before,
            "result_position_after": self.result_position_after,
            "source_state_index": self.source_state_index,
            "target_state_index": self.target_state_index,
            "source_image_shift": list(self.source_image_shift),
            "target_image_shift": list(self.target_image_shift),
            "observed_translation": list(self.observed_translation),
            "matching_edge_indices": list(self.matching_edge_indices),
        }


@dataclass(frozen=True, slots=True)
class IonSiteAssignmentStatistics:
    atom_index: int
    temporal_statistics: StateTransitionStatistics
    physical_frame_counts: IntArray
    physical_occupancy_probabilities: FloatArray
    accepted_frame_count: int
    observed_transitions: tuple[ObservedSiteTransition, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "atom_index", _nonnegative_int(self.atom_index, name="atom_index"))
        if not isinstance(self.temporal_statistics, StateTransitionStatistics):
            raise SiteAssignmentInputError("temporal_statistics has the wrong type.")
        counts = _readonly_int(self.physical_frame_counts, ndim=1)
        probabilities = _readonly_float(self.physical_occupancy_probabilities, ndim=1)
        if counts.shape != probabilities.shape or np.any(counts < 0):
            raise SiteAssignmentInputError("Physical occupancy arrays are inconsistent.")
        accepted = _nonnegative_int(self.accepted_frame_count, name="accepted_frame_count")
        if int(np.sum(counts, dtype=np.int64)) != accepted:
            raise SiteAssignmentInputError("accepted_frame_count disagrees with occupancy counts.")
        expected = counts.astype(np.float64) / self.temporal_statistics.n_frames
        if not np.allclose(probabilities, expected, rtol=0.0, atol=1.0e-15):
            raise SiteAssignmentInputError("Physical occupancy probabilities are inconsistent.")
        transitions = tuple(self.observed_transitions)
        if any(not isinstance(v, ObservedSiteTransition) for v in transitions):
            raise SiteAssignmentInputError("observed_transitions have the wrong type.")
        object.__setattr__(self, "physical_frame_counts", counts)
        object.__setattr__(self, "physical_occupancy_probabilities", probabilities)
        object.__setattr__(self, "accepted_frame_count", accepted)
        object.__setattr__(self, "observed_transitions", transitions)

    @property
    def off_network_event_count(self) -> int:
        return sum(not event.on_network for event in self.observed_transitions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "temporal_statistics": self.temporal_statistics.to_dict(),
            "physical_frame_counts": self.physical_frame_counts.tolist(),
            "physical_occupancy_probabilities": self.physical_occupancy_probabilities.tolist(),
            "accepted_frame_count": self.accepted_frame_count,
            "observed_transitions": [v.to_dict() for v in self.observed_transitions],
        }


@dataclass(frozen=True, slots=True, eq=False)
class SiteAssignmentResult:
    frame_tiling_geometry_digest: str
    frame_ring_geometry_digest: str
    site_topology_digest: str
    site_network_digest: str
    collection_geometry_digest: str
    profile: SiteAssignmentProfile
    options: SiteAssignmentOptions
    resources: SiteAssignmentResources
    axis: FrameAxis
    atom_indices: IntArray
    assignments: tuple[tuple[IonFrameSiteAssignment, ...], ...]
    ion_statistics: tuple[IonSiteAssignmentStatistics, ...]
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_SITE_ASSIGNMENT_SCHEMA
    digest_algorithm: str = SITE_ASSIGNMENT_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("frame_tiling_geometry_digest", "frame_ring_geometry_digest", "site_topology_digest", "site_network_digest", "collection_geometry_digest"):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.profile, SiteAssignmentProfile) or not isinstance(self.options, SiteAssignmentOptions) or not isinstance(self.resources, SiteAssignmentResources):
            raise SiteAssignmentInputError("profile/options/resources have the wrong type.")
        if not isinstance(self.axis, FrameAxis):
            raise SiteAssignmentInputError("axis has the wrong type.")
        atoms = _readonly_int(self.atom_indices, ndim=1)
        if atoms.size == 0 or len(set(int(v) for v in atoms)) != atoms.size:
            raise SiteAssignmentInputError("atom_indices must be nonempty and unique.")
        assignments = tuple(tuple(row) for row in self.assignments)
        if len(assignments) != atoms.size or any(len(row) != self.axis.n_frames for row in assignments):
            raise SiteAssignmentInputError("assignments must have shape (n_ions, n_frames).")
        for atom, row in zip(atoms, assignments, strict=True):
            for position, assignment in enumerate(row):
                if not isinstance(assignment, IonFrameSiteAssignment):
                    raise SiteAssignmentInputError("assignments have the wrong type.")
                if assignment.atom_index != int(atom) or assignment.result_position != position:
                    raise SiteAssignmentInputError("Assignment identity/order mismatch.")
        statistics = tuple(self.ion_statistics)
        if len(statistics) != atoms.size or tuple(v.atom_index for v in statistics) != tuple(int(v) for v in atoms):
            raise SiteAssignmentInputError("ion_statistics must align with atom_indices.")
        if self.canonical_schema_version != CANONICAL_SITE_ASSIGNMENT_SCHEMA or self.digest_algorithm != SITE_ASSIGNMENT_DIGEST_ALGORITHM:
            raise SiteAssignmentInputError("Unsupported site-assignment schema or digest algorithm.")
        object.__setattr__(self, "atom_indices", atoms)
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "ion_statistics", statistics)
        object.__setattr__(self, "metadata", _deep_freeze(dict(self.metadata)))
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise SiteAssignmentInputError("Stored site-assignment digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SiteAssignmentResult) and self.digest == other.digest

    @property
    def n_physical_states(self) -> int:
        return int(self.ion_statistics[0].physical_frame_counts.size)

    @property
    def off_network_event_count(self) -> int:
        return sum(item.off_network_event_count for item in self.ion_statistics)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "frame_tiling_geometry_digest": self.frame_tiling_geometry_digest,
            "frame_ring_geometry_digest": self.frame_ring_geometry_digest,
            "site_topology_digest": self.site_topology_digest,
            "site_network_digest": self.site_network_digest,
            "collection_geometry_digest": self.collection_geometry_digest,
            "profile": self.profile.to_dict(),
            "options": self.options.to_dict(),
            "resources": self.resources.to_dict(),
            "axis": self.axis.to_dict(),
            "atom_indices": self.atom_indices.tolist(),
            "assignments": [[v.to_dict() for v in row] for row in self.assignments],
            "ion_statistics": [v.to_dict() for v in self.ion_statistics],
            "metadata": _json_mutable(self.metadata),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        collection: AtomisticFrameCollection,
        frame_tiling_geometry: FrameTilingGeometryCatalog,
        frame_ring_geometry: FrameRingGeometryCatalog,
        site_topology: SpeciesSiteTopologyCatalog,
        site_network: PeriodicSiteKineticNetwork,
    ) -> "SiteAssignmentResult":
        try:
            rebuilt = assign_trajectory_sites(
                collection,
                frame_tiling_geometry,
                frame_ring_geometry,
                site_topology,
                site_network,
                SiteAssignmentProfile.from_dict(payload["profile"]),
                atom_indices=payload["atom_indices"],
                options=SiteAssignmentOptions.from_dict(payload["options"]),
                resources=SiteAssignmentResources.from_dict(payload["resources"]),
            )
        except SiteAssignmentError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteAssignmentSerializationError("Invalid site-assignment payload.") from exc
        if rebuilt.to_dict() != dict(payload):
            raise SiteAssignmentSerializationError("Serialized site assignment is not canonical for supplied sources.")
        return rebuilt


def _json_mutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_mutable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_json_mutable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _state_interface_labels(topology: SpeciesSiteTopologyCatalog) -> tuple[str | None, ...]:
    model_by_window = {model.window_index: model for model in topology.ring_models}
    return tuple(None if state.window_index is None else model_by_window[state.window_index].interface_label for state in topology.states)


def _resolve_rules(topology: SpeciesSiteTopologyCatalog, profile: SiteAssignmentProfile) -> tuple[SiteAssignmentRule, ...]:
    interfaces = _state_interface_labels(topology)
    resolved: list[SiteAssignmentRule] = []
    for state, interface in zip(topology.states, interfaces, strict=True):
        matches = tuple(rule for rule in profile.rules if rule.matches(state, interface))
        if len(matches) != 1:
            raise SiteAssignmentInvariantError(
                f"State {state.state_key!r} matched {len(matches)} assignment rules; expected exactly one."
            )
        resolved.append(matches[0])
    return tuple(resolved)


def _ring_side_frame(state: SiteMicrostate, topology: SpeciesSiteTopologyCatalog, ring: Any) -> RingSideFrame:
    if state.anchor_indices:
        anchor = topology.anchors[state.anchor_indices[0]]
        wanted = anchor.side
        for frame in ring.side_frames:
            if frame.side == wanted:
                return frame
        raise SiteAssignmentInvariantError("Dynamic ring side frames do not contain the persistent anchor side.")
    if len(ring.side_frames) != 2:
        raise SiteAssignmentInvariantError("Mapped ring geometry must contain two side frames.")
    return ring.side_frames[0]


def _candidate_for_state(
    *,
    ion_position: np.ndarray,
    state: SiteMicrostate,
    rule: SiteAssignmentRule,
    topology: SpeciesSiteTopologyCatalog,
    tiling_frame: Any,
    ring_frame: Any,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> SiteCandidateDiagnostic | None:
    if state.kind is SiteStateKind.CAGE_INTERIOR:
        if not tiling_frame.mapped or state.tile_index is None or state.tile_index >= len(tiling_frame.tiles):
            return None
        center = np.asarray(tiling_frame.tiles[state.tile_index].cartesian_center, dtype=np.float64)
        raw = ion_position - center
        vector, distance, image = minimum_image_geometry(raw, cell=cell, pbc=pbc)
        site_shift = tuple(int(-v) for v in np.asarray(image, dtype=np.int64))
        score = float(distance) / rule.in_plane_halfwidth
        return SiteCandidateDiagnostic(
            state.state_index, state.state_key, rule.rule_id, score <= 1.0,
            score <= rule.transition_multiplier, score, float(distance), site_shift,
            tuple(float(v) for v in vector), None, None,
        )

    if state.window_index is None or state.window_index >= len(ring_frame.rings):
        return None
    ring = ring_frame.rings[state.window_index]
    if ring.status is not FrameRingGeometryStatus.MAPPED:
        return None
    frame = _ring_side_frame(state, topology, ring)
    center = np.asarray(frame.center, dtype=np.float64)
    raw = ion_position - center
    vector, _distance_center, image = minimum_image_geometry(raw, cell=cell, pbc=pbc)
    vector = np.asarray(vector, dtype=np.float64)
    site_shift = tuple(int(-v) for v in np.asarray(image, dtype=np.int64))
    normal = np.asarray(frame.inward_unit_normal, dtype=np.float64)
    axis_u = np.asarray(frame.axis_u, dtype=np.float64)
    axis_v = np.asarray(frame.axis_v, dtype=np.float64)
    z = float(np.dot(vector, normal))
    u = float(np.dot(vector, axis_u))
    v = float(np.dot(vector, axis_v))
    local = (z, u, v)

    z0, rho0, theta0 = state.local_coordinates
    if state.kind is SiteStateKind.RING_ANNULAR:
        radius = float(math.hypot(u, v))
        angle = float(math.atan2(v, u))
        dz = z - z0
        dr = radius - float(state.annular_radius)
        score = math.hypot(dz / rule.normal_halfwidth, dr / rule.in_plane_halfwidth)
        closest = z0 * normal + float(state.annular_radius) * (math.cos(angle) * axis_u + math.sin(angle) * axis_v)
        relative = vector - closest
        distance = float(np.linalg.norm(relative))
        return SiteCandidateDiagnostic(
            state.state_index, state.state_key, rule.rule_id, score <= 1.0,
            score <= rule.transition_multiplier, score, distance, site_shift,
            tuple(float(x) for x in relative), local, angle,
        )

    expected_u = rho0 * math.cos(theta0)
    expected_v = rho0 * math.sin(theta0)
    dz = z - z0
    du = u - expected_u
    dv = v - expected_v
    score = math.sqrt((dz / rule.normal_halfwidth) ** 2 + (du * du + dv * dv) / rule.in_plane_halfwidth**2)
    relative = dz * normal + du * axis_u + dv * axis_v
    distance = float(np.linalg.norm(relative))
    return SiteCandidateDiagnostic(
        state.state_index, state.state_key, rule.rule_id, score <= 1.0,
        score <= rule.transition_multiplier, score, distance, site_shift,
        tuple(float(x) for x in relative), local, None,
    )


def _status_auxiliary_id(status: SiteAssignmentStatus, n_states: int) -> int:
    mapping = {
        SiteAssignmentStatus.AMBIGUOUS: 0,
        SiteAssignmentStatus.TRANSITION_REGION: 1,
        SiteAssignmentStatus.UNASSIGNED: 2,
        SiteAssignmentStatus.FRAME_UNRESOLVED: 3,
    }
    return n_states + mapping[status]


def _frame_assignment(
    *,
    atom_index: int,
    result_position: int,
    ion_position: np.ndarray,
    topology: SpeciesSiteTopologyCatalog,
    rules: tuple[SiteAssignmentRule, ...],
    tiling_frame: Any,
    ring_frame: Any,
    cell: np.ndarray,
    pbc: np.ndarray,
    max_diagnostics: int,
) -> IonFrameSiteAssignment:
    available = 0
    candidates: list[SiteCandidateDiagnostic] = []
    for state, rule in zip(topology.states, rules, strict=True):
        candidate = _candidate_for_state(
            ion_position=ion_position, state=state, rule=rule, topology=topology,
            tiling_frame=tiling_frame, ring_frame=ring_frame, cell=cell, pbc=pbc,
        )
        if candidate is None:
            continue
        available += 1
        if candidate.transition:
            candidates.append(candidate)
    candidates.sort(key=lambda item: (not item.core, not item.transition, item.score, item.state_index, item.site_image_shift))
    core = [item for item in candidates if item.core]
    if len(core) == 1:
        chosen = core[0]
        state = topology.states[chosen.state_index]
        status = SiteAssignmentStatus.ANNULAR_ASSIGNED if state.kind is SiteStateKind.RING_ANNULAR else SiteAssignmentStatus.ASSIGNED
        return IonFrameSiteAssignment(
            result_position, tiling_frame.collection_frame_index, tiling_frame.frame_id,
            atom_index, status, chosen.state_index, chosen.site_image_shift,
            chosen.relative_cartesian, chosen.ion_local_coordinates, chosen.annular_angle,
            available, tuple(candidates[:max_diagnostics]),
        )
    if len(core) > 1:
        status = SiteAssignmentStatus.AMBIGUOUS
    elif candidates:
        status = SiteAssignmentStatus.TRANSITION_REGION
    elif available == 0:
        status = SiteAssignmentStatus.FRAME_UNRESOLVED
    else:
        status = SiteAssignmentStatus.UNASSIGNED
    return IonFrameSiteAssignment(
        result_position, tiling_frame.collection_frame_index, tiling_frame.frame_id,
        atom_index, status, None, None, None, None, None, available,
        tuple(candidates[:max_diagnostics]),
    )


def assign_trajectory_sites(
    collection: AtomisticFrameCollection,
    frame_tiling_geometry: FrameTilingGeometryCatalog,
    frame_ring_geometry: FrameRingGeometryCatalog,
    site_topology: SpeciesSiteTopologyCatalog,
    site_network: PeriodicSiteKineticNetwork,
    assignment_profile: SiteAssignmentProfile,
    *,
    species: str | int | Sequence[str | int] | None = None,
    atom_indices: ArrayLike | None = None,
    options: SiteAssignmentOptions | None = None,
    resources: SiteAssignmentResources | None = None,
) -> SiteAssignmentResult:
    """Assign selected mobile ions to explicit instantaneous geometric site basins."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise SiteAssignmentInputError("collection must be AtomisticFrameCollection.")
    collection.require_trajectory("trajectory site assignment")
    for value, expected, name in (
        (frame_tiling_geometry, FrameTilingGeometryCatalog, "frame_tiling_geometry"),
        (frame_ring_geometry, FrameRingGeometryCatalog, "frame_ring_geometry"),
        (site_topology, SpeciesSiteTopologyCatalog, "site_topology"),
        (site_network, PeriodicSiteKineticNetwork, "site_network"),
        (assignment_profile, SiteAssignmentProfile, "assignment_profile"),
    ):
        if not isinstance(value, expected):
            raise SiteAssignmentInputError(f"{name} has the wrong type.")
    if frame_ring_geometry.frame_tiling_geometry_digest != frame_tiling_geometry.digest:
        raise SiteAssignmentInvariantError("Frame ring and tiling catalogs do not share one source.")
    if site_topology.tiling_geometry_digest != frame_tiling_geometry.reference_geometry_digest:
        raise SiteAssignmentInvariantError("Site topology and frame tiling do not share one reference geometry.")
    if site_topology.ring_geometry_digest != frame_ring_geometry.reference_ring_geometry_digest:
        raise SiteAssignmentInvariantError("Site topology and frame rings do not share one reference ring catalog.")
    if site_network.site_topology_digest != site_topology.digest:
        raise SiteAssignmentInvariantError("Site network is not bound to the supplied site topology.")
    if assignment_profile.site_topology_profile_id != site_topology.profile.profile_id or assignment_profile.species != site_topology.profile.species:
        raise SiteAssignmentInvariantError("Assignment profile is not bound to the supplied species site-topology profile.")
    tiling_frames = frame_tiling_geometry.frames
    ring_frames = frame_ring_geometry.frames
    if len(tiling_frames) != len(ring_frames) or any(
        (a.result_position, a.collection_frame_index, a.frame_id) != (b.result_position, b.collection_frame_index, b.frame_id)
        for a, b in zip(tiling_frames, ring_frames, strict=True)
    ):
        raise SiteAssignmentInvariantError("Frame tiling and ring catalogs are not aligned.")

    effective_options = SiteAssignmentOptions() if options is None else options
    effective_resources = SiteAssignmentResources() if resources is None else resources
    if not isinstance(effective_options, SiteAssignmentOptions) or not isinstance(effective_resources, SiteAssignmentResources):
        raise SiteAssignmentInputError("options/resources have the wrong type.")
    selected_species = assignment_profile.species if species is None and atom_indices is None else species
    try:
        atoms = resolve_atom_selection(
            collection.atomic_numbers,
            species=selected_species,
            atom_indices=atom_indices,
            selection_name="mobile_ion",
        )
        expected_atoms = set(int(v) for v in resolve_atom_selection(collection.atomic_numbers, species=assignment_profile.species, selection_name="profile_species"))
    except (TypeError, ValueError, IndexError) as exc:
        raise SiteAssignmentInputError(str(exc)) from exc
    if any(int(v) not in expected_atoms for v in atoms):
        raise SiteAssignmentInputError("Every selected atom must match the assignment-profile species.")

    n_frames = len(tiling_frames)
    n_ions = int(atoms.size)
    n_states = len(site_topology.states)
    for count, limit, label in (
        (n_frames, effective_resources.max_frames, "max_frames"),
        (n_ions, effective_resources.max_ions, "max_ions"),
        (n_states, effective_resources.max_states, "max_states"),
    ):
        if count > limit:
            raise SiteAssignmentResourceError(f"{label} exceeded: {count}>{limit}.")
    evaluations = n_frames * n_ions * n_states
    retained = n_frames * n_ions * effective_options.max_candidate_diagnostics
    if evaluations > effective_resources.max_candidate_evaluations:
        raise SiteAssignmentResourceError("Predicted candidate evaluations exceed max_candidate_evaluations.")
    if retained > effective_resources.max_retained_diagnostics:
        raise SiteAssignmentResourceError("Predicted retained diagnostics exceed max_retained_diagnostics.")

    rules = _resolve_rules(site_topology, assignment_profile)
    frame_indices = np.asarray([frame.collection_frame_index for frame in tiling_frames], dtype=np.int64)
    if np.any(frame_indices >= collection.n_frames):
        raise SiteAssignmentInvariantError("A mapped frame index exceeds the collection.")
    axis = build_frame_axis(
        n_frames,
        frame_semantics=collection.frame_semantics,
        collection_frame_indices=frame_indices,
        frame_ids=np.asarray([frame.frame_id for frame in tiling_frames], dtype=np.int64),
        steps=None if collection.steps is None else collection.steps[frame_indices],
        times=None if collection.times is None else collection.times[frame_indices],
        time_unit=None if collection.times is None else effective_options.time_unit,
    )

    rows: list[tuple[IonFrameSiteAssignment, ...]] = []
    statistics: list[IonSiteAssignmentStatistics] = []
    edge_lookup: dict[tuple[int, int, tuple[int, int, int]], tuple[int, ...]] = {}
    for edge in site_network.edges:
        key = (edge.source_state_index, edge.target_state_index, edge.periodic_translation)
        edge_lookup[key] = tuple(sorted((*edge_lookup.get(key, ()), edge.edge_index)))

    for atom in (int(v) for v in atoms):
        row: list[IonFrameSiteAssignment] = []
        for position, (tiling_frame, ring_frame) in enumerate(zip(tiling_frames, ring_frames, strict=True)):
            frame_index = tiling_frame.collection_frame_index
            ion_position = (
                np.asarray(collection.fractional_positions[frame_index, atom], dtype=np.float64)
                @ np.asarray(collection.cells[frame_index], dtype=np.float64)
                + np.asarray(collection.origins[frame_index], dtype=np.float64)
            )
            row.append(_frame_assignment(
                atom_index=atom, result_position=position, ion_position=ion_position,
                topology=site_topology, rules=rules, tiling_frame=tiling_frame,
                ring_frame=ring_frame, cell=np.asarray(collection.cells[frame_index], dtype=np.float64),
                pbc=np.asarray(collection.pbc, dtype=np.bool_),
                max_diagnostics=effective_options.max_candidate_diagnostics,
            ))
        row_tuple = tuple(row)
        rows.append(row_tuple)
        dense_ids = np.asarray([
            assignment.state_index if assignment.accepted else _status_auxiliary_id(assignment.status, n_states)
            for assignment in row_tuple
        ], dtype=np.int64)
        temporal = compute_state_transition_statistics(
            dense_ids,
            axis,
            n_states=n_states + len(AuxiliaryAssignmentState),
            options=TemporalStatisticsOptions(),
            metadata={
                "module": "site_assignment",
                "stage": "11E2",
                "atom_index": atom,
                "physical_state_count": n_states,
                "auxiliary_state_labels": [v.value for v in AuxiliaryAssignmentState],
            },
        )
        counts = np.bincount(dense_ids[dense_ids < n_states], minlength=n_states).astype(np.int64)
        probabilities = counts.astype(np.float64) / n_frames
        events: list[ObservedSiteTransition] = []
        for before, (source, target) in enumerate(zip(row_tuple[:-1], row_tuple[1:], strict=True)):
            if not source.accepted or not target.accepted:
                continue
            assert source.state_index is not None and target.state_index is not None
            assert source.site_image_shift is not None and target.site_image_shift is not None
            translation = tuple(t - s for s, t in zip(source.site_image_shift, target.site_image_shift, strict=True))
            if source.state_index == target.state_index and translation == (0, 0, 0):
                continue
            matches = edge_lookup.get((source.state_index, target.state_index, translation), ())
            events.append(ObservedSiteTransition(
                len(events), atom, before, before + 1, source.state_index, target.state_index,
                source.site_image_shift, target.site_image_shift, translation, matches,
            ))
        statistics.append(IonSiteAssignmentStatistics(
            atom, temporal, counts, probabilities, int(np.sum(counts, dtype=np.int64)), tuple(events),
        ))

    metadata = {
        "module": "site_assignment",
        "stage": "11E2",
        "descriptive_only": True,
        "energetic_certification": False,
        "nearest_site_fallback": False,
        "candidate_evaluations": evaluations,
        "auxiliary_state_labels": [v.value for v in AuxiliaryAssignmentState],
    }
    return SiteAssignmentResult(
        frame_tiling_geometry.digest,
        frame_ring_geometry.digest,
        site_topology.digest,
        site_network.digest,
        frame_tiling_geometry.collection_geometry_digest,
        assignment_profile,
        effective_options,
        effective_resources,
        axis,
        atoms,
        tuple(rows),
        tuple(statistics),
        metadata,
    )


__all__ = [
    "AuxiliaryAssignmentState",
    "CANONICAL_SITE_ASSIGNMENT_SCHEMA",
    "IonFrameSiteAssignment",
    "IonSiteAssignmentStatistics",
    "ObservedSiteTransition",
    "SITE_ASSIGNMENT_DIGEST_ALGORITHM",
    "SiteAssignmentError",
    "SiteAssignmentInputError",
    "SiteAssignmentInvariantError",
    "SiteAssignmentOptions",
    "SiteAssignmentProfile",
    "SiteAssignmentResourceError",
    "SiteAssignmentResources",
    "SiteAssignmentResult",
    "SiteAssignmentRule",
    "SiteAssignmentSerializationError",
    "SiteAssignmentStatus",
    "SiteCandidateDiagnostic",
    "assign_trajectory_sites",
]
