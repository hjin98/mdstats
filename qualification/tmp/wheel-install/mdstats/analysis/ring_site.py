"""Stage-11E1 species-dependent geometric site-state hypotheses.

This module deliberately separates topological ring-side anchors from physical
site hypotheses.  It does not infer energetic stability from ring order,
framework labels, or ionic radius; every hypothesis is supplied explicitly by a
species-specific profile.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from numbers import Integral, Real
import re
from typing import Any, Mapping, Sequence

import numpy as np

from .framework_semantics import FrameworkSemanticCatalog
from .ring_geometry import ReferenceRingGeometryCatalog, RingGeometryStatus, RingSideFrame
from .tiling_geometry import TileSideRef, TilingGeometryCatalog

CANONICAL_SITE_TOPOLOGY_SCHEMA = "mdstats.site-topology.v1"
SITE_TOPOLOGY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class SiteTopologyError(ValueError):
    """Base exception for Stage-11E1 site topology."""


class SiteTopologyInputError(SiteTopologyError):
    """Raised when source objects or profile values violate the contract."""


class SiteTopologyInvariantError(SiteTopologyError):
    """Raised when explicit profile rules cannot be applied consistently."""


class SiteTopologyResourceError(SiteTopologyError):
    """Raised transactionally before declared finite-work limits are exceeded."""


class SiteTopologySerializationError(SiteTopologyError):
    """Raised when canonical replay disagrees with serialized data."""


class SiteLandscapeRegime(str, Enum):
    NO_BOUND_STATE = "no_bound_state"
    ONE_SIDED = "one_sided"
    BILATERAL_DOUBLE_WELL = "bilateral_double_well"
    PLANE_CENTERED = "plane_centered"
    PLANE_OFF_CENTER_DISCRETE = "plane_off_center_discrete"
    PLANE_ANNULAR = "plane_annular"
    GENERAL_MULTIWELL = "general_multiwell"
    UNRESOLVED = "unresolved"


class SiteStateKind(str, Enum):
    RING_SIDE = "ring_side"
    RING_CENTER = "ring_center"
    RING_OFF_CENTER = "ring_off_center"
    RING_ANNULAR = "ring_annular"
    GENERAL = "general"
    CAGE_INTERIOR = "cage_interior"


class SiteSideAffinity(str, Enum):
    A = "a"
    B = "b"
    PLANE = "plane"
    CAGE = "cage"


class RingSideAnchorStatus(str, Enum):
    RESOLVED = "resolved"
    RING_GEOMETRY_UNRESOLVED = "ring_geometry_unresolved"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise SiteTopologyInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise SiteTopologyInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive_int(value: object, *, name: str) -> int:
    result = _nonnegative_int(value, name=name)
    if result == 0:
        raise SiteTopologyInputError(f"{name} must be positive.")
    return result


def _finite(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
        raise SiteTopologyInputError(f"{name} must be finite.")
    return float(value)


def _float3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = tuple(_finite(item, name=name) for item in value)
    if len(result) != 3:
        raise SiteTopologyInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


_MACHINE_LABEL = re.compile(r"^[a-z0-9][a-z0-9_.:^\-]*$")


def _machine_label(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not _MACHINE_LABEL.fullmatch(value):
        raise SiteTopologyInputError(f"{name} must be a lowercase machine label.")
    return value


def _species(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SiteTopologyInputError("species must be a nonempty string.")
    return value.strip()


def _shift(value: Sequence[object], *, name: str) -> tuple[int, int, int]:
    result = tuple(int(v) for v in value)
    if len(result) != 3 or any(isinstance(v, bool) for v in value):
        raise SiteTopologyInputError(f"{name} must contain three integers.")
    return result  # type: ignore[return-value]


def _position(frame: RingSideFrame, z: float, rho: float, theta: float) -> tuple[float, float, float]:
    center = np.asarray(frame.center, dtype=np.float64)
    normal = np.asarray(frame.inward_unit_normal, dtype=np.float64)
    axis_u = np.asarray(frame.axis_u, dtype=np.float64)
    axis_v = np.asarray(frame.axis_v, dtype=np.float64)
    point = center + z * normal + rho * (math.cos(theta) * axis_u + math.sin(theta) * axis_v)
    return tuple(float(v) for v in point)


@dataclass(frozen=True, slots=True)
class GeneralSiteTemplate:
    label: str
    side_affinity: SiteSideAffinity
    z: float
    rho: float
    theta: float
    degeneracy: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "label", _machine_label(self.label, name="label"))
        object.__setattr__(self, "side_affinity", SiteSideAffinity(self.side_affinity))
        object.__setattr__(self, "z", _finite(self.z, name="z"))
        rho = _finite(self.rho, name="rho")
        if rho < 0:
            raise SiteTopologyInputError("rho must be nonnegative.")
        object.__setattr__(self, "rho", rho)
        object.__setattr__(self, "theta", _finite(self.theta, name="theta"))
        object.__setattr__(self, "degeneracy", _positive_int(self.degeneracy, name="degeneracy"))
        if self.side_affinity is SiteSideAffinity.CAGE:
            raise SiteTopologyInputError("General ring templates cannot use cage affinity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "side_affinity": self.side_affinity.value,
            "z": self.z,
            "rho": self.rho,
            "theta": self.theta,
            "degeneracy": self.degeneracy,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeneralSiteTemplate":
        try:
            return cls(
                str(payload["label"]), SiteSideAffinity(payload["side_affinity"]),
                float(payload["z"]), float(payload["rho"]), float(payload["theta"]),
                int(payload.get("degeneracy", 1)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteTopologySerializationError("Invalid general site template payload.") from exc


@dataclass(frozen=True, slots=True)
class RingSiteRule:
    interface_label: str
    regime: SiteLandscapeRegime
    display_label: str
    active_tile_label: str | None = None
    normal_offsets: tuple[float, ...] = ()
    radial_offset: float = 0.0
    angular_count: int = 0
    angular_phase: float = 0.0
    general_templates: tuple[GeneralSiteTemplate, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "interface_label", _machine_label(self.interface_label, name="interface_label"))
        object.__setattr__(self, "regime", SiteLandscapeRegime(self.regime))
        if not isinstance(self.display_label, str) or not self.display_label.strip():
            raise SiteTopologyInputError("display_label must be nonempty.")
        object.__setattr__(self, "display_label", self.display_label.strip())
        if self.active_tile_label is not None:
            object.__setattr__(self, "active_tile_label", _machine_label(self.active_tile_label, name="active_tile_label"))
        offsets = tuple(_finite(v, name="normal_offset") for v in self.normal_offsets)
        radial = _finite(self.radial_offset, name="radial_offset")
        if radial < 0:
            raise SiteTopologyInputError("radial_offset must be nonnegative.")
        count = _nonnegative_int(self.angular_count, name="angular_count")
        phase = _finite(self.angular_phase, name="angular_phase")
        templates = tuple(self.general_templates)
        if any(not isinstance(v, GeneralSiteTemplate) for v in templates):
            raise SiteTopologyInputError("general_templates must contain GeneralSiteTemplate records.")
        object.__setattr__(self, "normal_offsets", offsets)
        object.__setattr__(self, "radial_offset", radial)
        object.__setattr__(self, "angular_count", count)
        object.__setattr__(self, "angular_phase", phase)
        object.__setattr__(self, "general_templates", templates)
        regime = self.regime
        if regime is SiteLandscapeRegime.ONE_SIDED:
            if self.active_tile_label is None or len(offsets) != 1 or offsets[0] <= 0:
                raise SiteTopologyInputError("ONE_SIDED requires active_tile_label and one positive normal offset.")
            if radial != 0 or count or phase != 0 or templates:
                raise SiteTopologyInputError("ONE_SIDED accepts only active_tile_label and normal_offsets.")
        elif regime is SiteLandscapeRegime.BILATERAL_DOUBLE_WELL:
            if len(offsets) != 2 or any(v <= 0 for v in offsets):
                raise SiteTopologyInputError("BILATERAL_DOUBLE_WELL requires two positive normal offsets.")
            if self.active_tile_label is not None or radial != 0 or count or phase != 0 or templates:
                raise SiteTopologyInputError("BILATERAL_DOUBLE_WELL accepts only normal_offsets.")
        elif regime is SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE:
            if radial <= 0 or count < 2:
                raise SiteTopologyInputError("Discrete off-center rules require radial_offset > 0 and angular_count >= 2.")
            if self.active_tile_label is not None or offsets or templates:
                raise SiteTopologyInputError("Discrete off-center rules accept only radial/angular parameters.")
        elif regime is SiteLandscapeRegime.PLANE_ANNULAR:
            if radial <= 0:
                raise SiteTopologyInputError("Annular rules require radial_offset > 0.")
            if self.active_tile_label is not None or offsets or count or phase != 0 or templates:
                raise SiteTopologyInputError("Annular rules accept only radial_offset.")
        elif regime is SiteLandscapeRegime.GENERAL_MULTIWELL:
            if not templates:
                raise SiteTopologyInputError("GENERAL_MULTIWELL requires explicit templates.")
            if self.active_tile_label is not None or offsets or radial != 0 or count or phase != 0:
                raise SiteTopologyInputError("GENERAL_MULTIWELL accepts only explicit templates.")
        elif regime in {
            SiteLandscapeRegime.NO_BOUND_STATE,
            SiteLandscapeRegime.PLANE_CENTERED,
            SiteLandscapeRegime.UNRESOLVED,
        }:
            if offsets or radial != 0 or count or phase != 0 or templates or self.active_tile_label is not None:
                raise SiteTopologyInputError(f"{regime.value} does not accept placement parameters.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface_label": self.interface_label,
            "regime": self.regime.value,
            "display_label": self.display_label,
            "active_tile_label": self.active_tile_label,
            "normal_offsets": list(self.normal_offsets),
            "radial_offset": self.radial_offset,
            "angular_count": self.angular_count,
            "angular_phase": self.angular_phase,
            "general_templates": [v.to_dict() for v in self.general_templates],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingSiteRule":
        try:
            return cls(
                str(payload["interface_label"]), SiteLandscapeRegime(payload["regime"]),
                str(payload["display_label"]), payload.get("active_tile_label"),
                tuple(float(v) for v in payload.get("normal_offsets", ())),
                float(payload.get("radial_offset", 0.0)), int(payload.get("angular_count", 0)),
                float(payload.get("angular_phase", 0.0)),
                tuple(GeneralSiteTemplate.from_dict(v) for v in payload.get("general_templates", ())),
            )
        except SiteTopologyError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteTopologySerializationError("Invalid ring site rule payload.") from exc


@dataclass(frozen=True, slots=True)
class CageInteriorRule:
    tile_label: str
    state_label: str
    display_label: str
    degeneracy: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_label", _machine_label(self.tile_label, name="tile_label"))
        object.__setattr__(self, "state_label", _machine_label(self.state_label, name="state_label"))
        if not isinstance(self.display_label, str) or not self.display_label.strip():
            raise SiteTopologyInputError("display_label must be nonempty.")
        object.__setattr__(self, "display_label", self.display_label.strip())
        object.__setattr__(self, "degeneracy", _positive_int(self.degeneracy, name="degeneracy"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_label": self.tile_label, "state_label": self.state_label,
            "display_label": self.display_label, "degeneracy": self.degeneracy,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CageInteriorRule":
        try:
            return cls(str(payload["tile_label"]), str(payload["state_label"]), str(payload["display_label"]), int(payload.get("degeneracy", 1)))
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteTopologySerializationError("Invalid cage rule payload.") from exc


@dataclass(frozen=True, slots=True)
class SpeciesSiteTopologyProfile:
    profile_id: str
    species: str
    description: str
    ring_rules: tuple[RingSiteRule, ...]
    cage_rules: tuple[CageInteriorRule, ...] = ()
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _machine_label(self.profile_id, name="profile_id"))
        object.__setattr__(self, "species", _species(self.species))
        if not isinstance(self.description, str) or not self.description.strip():
            raise SiteTopologyInputError("description must be nonempty.")
        rules = tuple(self.ring_rules)
        cages = tuple(self.cage_rules)
        if not rules or any(not isinstance(v, RingSiteRule) for v in rules):
            raise SiteTopologyInputError("ring_rules must be a nonempty tuple of RingSiteRule records.")
        if any(not isinstance(v, CageInteriorRule) for v in cages):
            raise SiteTopologyInputError("cage_rules must contain CageInteriorRule records.")
        labels = [v.interface_label for v in rules]
        if len(labels) != len(set(labels)):
            raise SiteTopologyInputError("Ring-rule interface labels must be unique.")
        tile_labels = [v.tile_label for v in cages]
        if len(tile_labels) != len(set(tile_labels)):
            raise SiteTopologyInputError("Cage-rule tile labels must be unique.")
        refs = tuple(str(v).strip() for v in self.references)
        if any(not v for v in refs):
            raise SiteTopologyInputError("references cannot contain empty strings.")
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "ring_rules", rules)
        object.__setattr__(self, "cage_rules", cages)
        object.__setattr__(self, "references", refs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id, "species": self.species, "description": self.description,
            "ring_rules": [v.to_dict() for v in self.ring_rules],
            "cage_rules": [v.to_dict() for v in self.cage_rules], "references": list(self.references),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesSiteTopologyProfile":
        try:
            return cls(
                str(payload["profile_id"]), str(payload["species"]), str(payload["description"]),
                tuple(RingSiteRule.from_dict(v) for v in payload["ring_rules"]),
                tuple(CageInteriorRule.from_dict(v) for v in payload.get("cage_rules", ())),
                tuple(str(v) for v in payload.get("references", ())),
            )
        except SiteTopologyError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteTopologySerializationError("Invalid site topology profile payload.") from exc


@dataclass(frozen=True, slots=True)
class SiteTopologyResources:
    max_rules: int = 256
    max_anchors: int = 100_000
    max_states: int = 1_000_000
    max_angular_variants: int = 1024

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class RingSideAnchor:
    anchor_index: int
    window_index: int
    side_label: str
    side: TileSideRef
    tile_label: str
    interface_label: str
    image_shift: tuple[int, int, int]
    status: RingSideAnchorStatus
    center: tuple[float, float, float] | None = None
    inward_unit_normal: tuple[float, float, float] | None = None
    axis_u: tuple[float, float, float] | None = None
    axis_v: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor_index", _nonnegative_int(self.anchor_index, name="anchor_index"))
        object.__setattr__(self, "window_index", _nonnegative_int(self.window_index, name="window_index"))
        if self.side_label not in {"a", "b"}:
            raise SiteTopologyInputError("side_label must be 'a' or 'b'.")
        if not isinstance(self.side, TileSideRef):
            raise SiteTopologyInputError("side must be TileSideRef.")
        object.__setattr__(self, "tile_label", _machine_label(self.tile_label, name="tile_label"))
        object.__setattr__(self, "interface_label", _machine_label(self.interface_label, name="interface_label"))
        object.__setattr__(self, "image_shift", _shift(self.image_shift, name="image_shift"))
        status = RingSideAnchorStatus(self.status)
        object.__setattr__(self, "status", status)
        values = (self.center, self.inward_unit_normal, self.axis_u, self.axis_v)
        if status is RingSideAnchorStatus.RESOLVED:
            if any(v is None for v in values):
                raise SiteTopologyInputError("Resolved anchors require complete frame geometry.")
            for name in ("center", "inward_unit_normal", "axis_u", "axis_v"):
                object.__setattr__(self, name, _float3(getattr(self, name), name=name))
        elif any(v is not None for v in values):
            raise SiteTopologyInputError("Unresolved anchors cannot carry geometry.")

    @property
    def resolved(self) -> bool:
        return self.status is RingSideAnchorStatus.RESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_index": self.anchor_index, "window_index": self.window_index,
            "side_label": self.side_label, "side": self.side.to_dict(), "tile_label": self.tile_label,
            "interface_label": self.interface_label, "image_shift": list(self.image_shift),
            "status": self.status.value,
            "center": None if self.center is None else list(self.center),
            "inward_unit_normal": None if self.inward_unit_normal is None else list(self.inward_unit_normal),
            "axis_u": None if self.axis_u is None else list(self.axis_u),
            "axis_v": None if self.axis_v is None else list(self.axis_v),
        }


@dataclass(frozen=True, order=True, slots=True)
class SiteTileExposure:
    tile_index: int
    image_shift: tuple[int, int, int]
    anchor_index: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_index", _nonnegative_int(self.tile_index, name="tile_index"))
        object.__setattr__(self, "image_shift", _shift(self.image_shift, name="image_shift"))
        if self.anchor_index is not None:
            object.__setattr__(self, "anchor_index", _nonnegative_int(self.anchor_index, name="anchor_index"))

    def to_dict(self) -> dict[str, Any]:
        return {"tile_index": self.tile_index, "image_shift": list(self.image_shift), "anchor_index": self.anchor_index}


@dataclass(frozen=True, slots=True)
class SiteMicrostate:
    state_index: int
    state_key: str
    species: str
    kind: SiteStateKind
    display_label: str
    regime: SiteLandscapeRegime | None
    window_index: int | None
    tile_index: int | None
    anchor_indices: tuple[int, ...]
    side_affinity: SiteSideAffinity
    reference_position: tuple[float, float, float]
    local_coordinates: tuple[float, float, float]
    annular_radius: float | None
    degeneracy: int
    exposures: tuple[SiteTileExposure, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_index", _nonnegative_int(self.state_index, name="state_index"))
        object.__setattr__(self, "state_key", _machine_label(self.state_key, name="state_key"))
        object.__setattr__(self, "species", _species(self.species))
        object.__setattr__(self, "kind", SiteStateKind(self.kind))
        if not isinstance(self.display_label, str) or not self.display_label.strip():
            raise SiteTopologyInputError("display_label must be nonempty.")
        object.__setattr__(self, "display_label", self.display_label.strip())
        if self.regime is not None:
            object.__setattr__(self, "regime", SiteLandscapeRegime(self.regime))
        for name in ("window_index", "tile_index"):
            if getattr(self, name) is not None:
                object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        anchors = tuple(_nonnegative_int(v, name="anchor_index") for v in self.anchor_indices)
        if anchors != tuple(sorted(set(anchors))):
            raise SiteTopologyInputError("anchor_indices must be sorted and unique.")
        object.__setattr__(self, "anchor_indices", anchors)
        object.__setattr__(self, "side_affinity", SiteSideAffinity(self.side_affinity))
        object.__setattr__(self, "reference_position", _float3(self.reference_position, name="reference_position"))
        object.__setattr__(self, "local_coordinates", _float3(self.local_coordinates, name="local_coordinates"))
        if self.annular_radius is not None:
            radius = _finite(self.annular_radius, name="annular_radius")
            if radius <= 0:
                raise SiteTopologyInputError("annular_radius must be positive.")
            object.__setattr__(self, "annular_radius", radius)
        object.__setattr__(self, "degeneracy", _positive_int(self.degeneracy, name="degeneracy"))
        exposures = tuple(sorted(self.exposures))
        if not exposures or len(exposures) != len(set(exposures)):
            raise SiteTopologyInputError("A state requires unique tile exposures.")
        object.__setattr__(self, "exposures", exposures)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_index": self.state_index, "state_key": self.state_key, "species": self.species,
            "kind": self.kind.value, "display_label": self.display_label,
            "regime": None if self.regime is None else self.regime.value,
            "window_index": self.window_index, "tile_index": self.tile_index,
            "anchor_indices": list(self.anchor_indices), "side_affinity": self.side_affinity.value,
            "reference_position": list(self.reference_position), "local_coordinates": list(self.local_coordinates),
            "annular_radius": self.annular_radius, "degeneracy": self.degeneracy,
            "exposures": [v.to_dict() for v in self.exposures],
        }


@dataclass(frozen=True, slots=True)
class RingSiteModel:
    window_index: int
    interface_label: str
    regime: SiteLandscapeRegime
    anchor_indices: tuple[int, int]
    state_indices: tuple[int, ...]
    resolved: bool
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_index", _nonnegative_int(self.window_index, name="window_index"))
        object.__setattr__(self, "interface_label", _machine_label(self.interface_label, name="interface_label"))
        object.__setattr__(self, "regime", SiteLandscapeRegime(self.regime))
        anchors = tuple(_nonnegative_int(v, name="anchor_index") for v in self.anchor_indices)
        if len(anchors) != 2:
            raise SiteTopologyInputError("anchor_indices must contain two values.")
        object.__setattr__(self, "anchor_indices", anchors)
        states = tuple(_nonnegative_int(v, name="state_index") for v in self.state_indices)
        object.__setattr__(self, "state_indices", states)
        if not isinstance(self.resolved, bool) or not isinstance(self.message, str):
            raise SiteTopologyInputError("resolved/message have invalid types.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index, "interface_label": self.interface_label,
            "regime": self.regime.value, "anchor_indices": list(self.anchor_indices),
            "state_indices": list(self.state_indices), "resolved": self.resolved, "message": self.message,
        }


@dataclass(frozen=True, slots=True, eq=False)
class SpeciesSiteTopologyCatalog:
    tiling_geometry_digest: str
    ring_geometry_digest: str
    framework_semantics_digest: str
    profile: SpeciesSiteTopologyProfile
    anchors: tuple[RingSideAnchor, ...]
    ring_models: tuple[RingSiteModel, ...]
    states: tuple[SiteMicrostate, ...]
    canonical_schema_version: str = CANONICAL_SITE_TOPOLOGY_SCHEMA
    digest_algorithm: str = SITE_TOPOLOGY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("tiling_geometry_digest", "ring_geometry_digest", "framework_semantics_digest"):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.profile, SpeciesSiteTopologyProfile):
            raise SiteTopologyInputError("profile must be SpeciesSiteTopologyProfile.")
        anchors = tuple(self.anchors)
        models = tuple(self.ring_models)
        states = tuple(self.states)
        if tuple(v.anchor_index for v in anchors) != tuple(range(len(anchors))):
            raise SiteTopologyInputError("Anchor IDs must be dense and ordered.")
        if tuple(v.window_index for v in models) != tuple(range(len(models))):
            raise SiteTopologyInputError("Ring model IDs must be dense and ordered by window.")
        if tuple(v.state_index for v in states) != tuple(range(len(states))):
            raise SiteTopologyInputError("State IDs must be dense and ordered.")
        if self.canonical_schema_version != CANONICAL_SITE_TOPOLOGY_SCHEMA or self.digest_algorithm != SITE_TOPOLOGY_DIGEST_ALGORITHM:
            raise SiteTopologyInputError("Unsupported site-topology schema or digest algorithm.")
        object.__setattr__(self, "anchors", anchors)
        object.__setattr__(self, "ring_models", models)
        object.__setattr__(self, "states", states)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise SiteTopologyInputError("Stored site-topology digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SpeciesSiteTopologyCatalog) and self.digest == other.digest

    @property
    def species(self) -> str:
        return self.profile.species

    def states_for_window(self, window_index: int) -> tuple[SiteMicrostate, ...]:
        index = _nonnegative_int(window_index, name="window_index")
        if index >= len(self.ring_models):
            raise SiteTopologyInputError("window_index is outside this catalog.")
        return tuple(self.states[i] for i in self.ring_models[index].state_indices)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "tiling_geometry_digest": self.tiling_geometry_digest,
            "ring_geometry_digest": self.ring_geometry_digest,
            "framework_semantics_digest": self.framework_semantics_digest,
            "profile": self.profile.to_dict(),
            "anchors": [v.to_dict() for v in self.anchors],
            "ring_models": [v.to_dict() for v in self.ring_models],
            "states": [v.to_dict() for v in self.states],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any], *, geometry: TilingGeometryCatalog,
        ring_geometry: ReferenceRingGeometryCatalog, semantics: FrameworkSemanticCatalog,
        resources: SiteTopologyResources | None = None,
    ) -> "SpeciesSiteTopologyCatalog":
        try:
            profile = SpeciesSiteTopologyProfile.from_dict(payload["profile"])
            rebuilt = build_species_site_topology(geometry, ring_geometry, semantics, profile, resources=resources)
        except SiteTopologyError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise SiteTopologySerializationError("Invalid site-topology payload.") from exc
        if rebuilt.to_dict() != dict(payload):
            raise SiteTopologySerializationError("Serialized site topology is not canonical for the supplied sources.")
        return rebuilt


def _interface_label(interface: Any) -> str:
    return interface.family_label or interface.generic_label


def _tile_label(tile: Any) -> str:
    return tile.effective_label


def build_species_site_topology(
    geometry: TilingGeometryCatalog,
    ring_geometry: ReferenceRingGeometryCatalog,
    semantics: FrameworkSemanticCatalog,
    profile: SpeciesSiteTopologyProfile,
    *,
    resources: SiteTopologyResources | None = None,
) -> SpeciesSiteTopologyCatalog:
    """Build explicit geometric site hypotheses for one species."""

    if not isinstance(geometry, TilingGeometryCatalog):
        raise SiteTopologyInputError("geometry must be TilingGeometryCatalog.")
    if not isinstance(ring_geometry, ReferenceRingGeometryCatalog):
        raise SiteTopologyInputError("ring_geometry must be ReferenceRingGeometryCatalog.")
    if not isinstance(semantics, FrameworkSemanticCatalog):
        raise SiteTopologyInputError("semantics must be FrameworkSemanticCatalog.")
    if not isinstance(profile, SpeciesSiteTopologyProfile):
        raise SiteTopologyInputError("profile must be SpeciesSiteTopologyProfile.")
    active = resources or SiteTopologyResources()
    if not isinstance(active, SiteTopologyResources):
        raise SiteTopologyInputError("resources must be SiteTopologyResources.")
    if geometry.digest != ring_geometry.tiling_geometry_digest or geometry.digest != semantics.tiling_geometry_digest:
        raise SiteTopologyInvariantError("Geometry, ring geometry, and semantics do not share one tiling source.")
    if len(profile.ring_rules) + len(profile.cage_rules) > active.max_rules:
        raise SiteTopologyResourceError("Profile rule count exceeds max_rules.")
    if 2 * len(geometry.windows) > active.max_anchors:
        raise SiteTopologyResourceError("Anchor count exceeds max_anchors.")
    if any(rule.angular_count > active.max_angular_variants for rule in profile.ring_rules):
        raise SiteTopologyResourceError("A ring rule exceeds max_angular_variants.")

    rule_by_label = {rule.interface_label: rule for rule in profile.ring_rules}
    observed_labels = {_interface_label(v) for v in semantics.interfaces}
    missing = observed_labels - set(rule_by_label)
    extra = set(rule_by_label) - observed_labels
    if missing or extra:
        raise SiteTopologyInvariantError(f"Profile interface coverage mismatch: missing={sorted(missing)}, extra={sorted(extra)}.")

    state_multiplicity = {
        SiteLandscapeRegime.NO_BOUND_STATE: lambda rule: 0,
        SiteLandscapeRegime.UNRESOLVED: lambda rule: 0,
        SiteLandscapeRegime.ONE_SIDED: lambda rule: 1,
        SiteLandscapeRegime.BILATERAL_DOUBLE_WELL: lambda rule: 2,
        SiteLandscapeRegime.PLANE_CENTERED: lambda rule: 1,
        SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE: lambda rule: rule.angular_count,
        SiteLandscapeRegime.PLANE_ANNULAR: lambda rule: 1,
        SiteLandscapeRegime.GENERAL_MULTIWELL: lambda rule: len(rule.general_templates),
    }
    predicted_ring_states = sum(
        state_multiplicity[rule_by_label[_interface_label(interface)].regime](
            rule_by_label[_interface_label(interface)]
        )
        for interface in semantics.interfaces
    )
    observed_tile_labels = {_tile_label(tile) for tile in semantics.tiles}
    unknown_cage_labels = {rule.tile_label for rule in profile.cage_rules} - observed_tile_labels
    if unknown_cage_labels:
        raise SiteTopologyInvariantError(
            f"Cage rules reference unknown tile labels: {sorted(unknown_cage_labels)}."
        )
    predicted_cage_states = sum(
        1 for tile in semantics.tiles if _tile_label(tile) in {rule.tile_label for rule in profile.cage_rules}
    )
    if predicted_ring_states + predicted_cage_states > active.max_states:
        raise SiteTopologyResourceError("Predicted state count exceeds max_states.")

    anchors: list[RingSideAnchor] = []
    for interface, ring in zip(semantics.interfaces, ring_geometry.rings, strict=True):
        label = _interface_label(interface)
        side_data = (("a", interface.side_a, interface.side_a_tile_label, (0, 0, 0)),
                     ("b", interface.side_b, interface.side_b_tile_label, interface.relative_tile_translation))
        frames = {frame.side: frame for frame in ring.side_frames}
        for side_label, side, tile_label, shift in side_data:
            frame = frames.get(side)
            resolved = ring.status is RingGeometryStatus.RESOLVED and frame is not None
            anchors.append(RingSideAnchor(
                len(anchors), interface.window_index, side_label, side, tile_label, label, shift,
                RingSideAnchorStatus.RESOLVED if resolved else RingSideAnchorStatus.RING_GEOMETRY_UNRESOLVED,
                None if not resolved else frame.center,
                None if not resolved else frame.inward_unit_normal,
                None if not resolved else frame.axis_u,
                None if not resolved else frame.axis_v,
            ))

    states: list[SiteMicrostate] = []
    models: list[RingSiteModel] = []

    def add_state(*, key_suffix: str, kind: SiteStateKind, display: str, regime: SiteLandscapeRegime | None,
                  window: int | None, tile: int | None, anchor_ids: tuple[int, ...], affinity: SiteSideAffinity,
                  position: tuple[float, float, float], local: tuple[float, float, float],
                  radius: float | None, degeneracy: int, exposures: tuple[SiteTileExposure, ...]) -> int:
        if len(states) >= active.max_states:
            raise SiteTopologyResourceError("State count exceeds max_states.")
        index = len(states)
        states.append(SiteMicrostate(
            index, f"state:{index}:{key_suffix}", profile.species, kind, display, regime, window, tile,
            tuple(sorted(anchor_ids)), affinity, position, local, radius, degeneracy, exposures,
        ))
        return index

    for interface, ring in zip(semantics.interfaces, ring_geometry.rings, strict=True):
        label = _interface_label(interface)
        rule = rule_by_label[label]
        anchor_a = anchors[2 * interface.window_index]
        anchor_b = anchors[2 * interface.window_index + 1]
        anchor_ids = (anchor_a.anchor_index, anchor_b.anchor_index)
        if rule.regime in {SiteLandscapeRegime.NO_BOUND_STATE, SiteLandscapeRegime.UNRESOLVED}:
            models.append(RingSiteModel(interface.window_index, label, rule.regime, anchor_ids, (), rule.regime is SiteLandscapeRegime.NO_BOUND_STATE, rule.display_label))
            continue
        if not anchor_a.resolved or not anchor_b.resolved or not ring.resolved:
            models.append(RingSiteModel(interface.window_index, label, rule.regime, anchor_ids, (), False, "Reference ring geometry is unresolved."))
            continue
        frames = {frame.side: frame for frame in ring.side_frames}
        frame_a = frames[interface.side_a]
        frame_b = frames[interface.side_b]
        exposure_a = SiteTileExposure(interface.side_a.tile_index, (0, 0, 0), anchor_a.anchor_index)
        exposure_b = SiteTileExposure(interface.side_b.tile_index, interface.relative_tile_translation, anchor_b.anchor_index)
        created: list[int] = []
        if rule.regime is SiteLandscapeRegime.ONE_SIDED:
            matches = [(frame_a, anchor_a, exposure_a, SiteSideAffinity.A), (frame_b, anchor_b, exposure_b, SiteSideAffinity.B)]
            matches = [v for v in matches if v[1].tile_label == rule.active_tile_label]
            if len(matches) != 1:
                raise SiteTopologyInvariantError(f"ONE_SIDED rule {label!r} requires exactly one adjacent tile labelled {rule.active_tile_label!r}.")
            frame, anchor, exposure, affinity = matches[0]
            created.append(add_state(
                key_suffix=f"w{interface.window_index}:{affinity.value}", kind=SiteStateKind.RING_SIDE,
                display=rule.display_label, regime=rule.regime, window=interface.window_index, tile=None,
                anchor_ids=(anchor.anchor_index,), affinity=affinity,
                position=_position(frame, rule.normal_offsets[0], 0.0, 0.0),
                local=(rule.normal_offsets[0], 0.0, 0.0), radius=None, degeneracy=1, exposures=(exposure,),
            ))
        elif rule.regime is SiteLandscapeRegime.BILATERAL_DOUBLE_WELL:
            for suffix, frame, anchor, exposure, affinity, offset in (
                ("a", frame_a, anchor_a, exposure_a, SiteSideAffinity.A, rule.normal_offsets[0]),
                ("b", frame_b, anchor_b, exposure_b, SiteSideAffinity.B, rule.normal_offsets[1]),
            ):
                created.append(add_state(
                    key_suffix=f"w{interface.window_index}:{suffix}", kind=SiteStateKind.RING_SIDE,
                    display=f"{rule.display_label} {suffix}", regime=rule.regime, window=interface.window_index,
                    tile=None, anchor_ids=(anchor.anchor_index,), affinity=affinity,
                    position=_position(frame, offset, 0.0, 0.0), local=(offset, 0.0, 0.0),
                    radius=None, degeneracy=1, exposures=(exposure,),
                ))
        elif rule.regime is SiteLandscapeRegime.PLANE_CENTERED:
            created.append(add_state(
                key_suffix=f"w{interface.window_index}:center", kind=SiteStateKind.RING_CENTER,
                display=rule.display_label, regime=rule.regime, window=interface.window_index, tile=None,
                anchor_ids=anchor_ids, affinity=SiteSideAffinity.PLANE, position=frame_a.center,
                local=(0.0, 0.0, 0.0), radius=None, degeneracy=1, exposures=(exposure_a, exposure_b),
            ))
        elif rule.regime is SiteLandscapeRegime.PLANE_OFF_CENTER_DISCRETE:
            for variant in range(rule.angular_count):
                theta = rule.angular_phase + 2.0 * math.pi * variant / rule.angular_count
                created.append(add_state(
                    key_suffix=f"w{interface.window_index}:angular{variant}", kind=SiteStateKind.RING_OFF_CENTER,
                    display=f"{rule.display_label} {variant}", regime=rule.regime, window=interface.window_index,
                    tile=None, anchor_ids=anchor_ids, affinity=SiteSideAffinity.PLANE,
                    position=_position(frame_a, 0.0, rule.radial_offset, theta),
                    local=(0.0, rule.radial_offset, theta), radius=None, degeneracy=1,
                    exposures=(exposure_a, exposure_b),
                ))
        elif rule.regime is SiteLandscapeRegime.PLANE_ANNULAR:
            created.append(add_state(
                key_suffix=f"w{interface.window_index}:annular", kind=SiteStateKind.RING_ANNULAR,
                display=rule.display_label, regime=rule.regime, window=interface.window_index, tile=None,
                anchor_ids=anchor_ids, affinity=SiteSideAffinity.PLANE, position=frame_a.center,
                local=(0.0, rule.radial_offset, 0.0), radius=rule.radial_offset, degeneracy=1,
                exposures=(exposure_a, exposure_b),
            ))
        elif rule.regime is SiteLandscapeRegime.GENERAL_MULTIWELL:
            for variant, template in enumerate(rule.general_templates):
                if template.side_affinity is SiteSideAffinity.A:
                    frame, anchor_set, exposures = frame_a, (anchor_a.anchor_index,), (exposure_a,)
                elif template.side_affinity is SiteSideAffinity.B:
                    frame, anchor_set, exposures = frame_b, (anchor_b.anchor_index,), (exposure_b,)
                else:
                    frame, anchor_set, exposures = frame_a, anchor_ids, (exposure_a, exposure_b)
                created.append(add_state(
                    key_suffix=f"w{interface.window_index}:{template.label}:{variant}", kind=SiteStateKind.GENERAL,
                    display=template.label, regime=rule.regime, window=interface.window_index, tile=None,
                    anchor_ids=anchor_set, affinity=template.side_affinity,
                    position=_position(frame, template.z, template.rho, template.theta),
                    local=(template.z, template.rho, template.theta), radius=None,
                    degeneracy=template.degeneracy, exposures=exposures,
                ))
        models.append(RingSiteModel(interface.window_index, label, rule.regime, anchor_ids, tuple(created), True, rule.display_label))

    cage_by_label = {rule.tile_label: rule for rule in profile.cage_rules}
    for semantic_tile, tile_geometry in zip(semantics.tiles, geometry.tiles, strict=True):
        rule = cage_by_label.get(_tile_label(semantic_tile))
        if rule is None:
            continue
        add_state(
            key_suffix=f"tile{semantic_tile.tile_index}:{rule.state_label}", kind=SiteStateKind.CAGE_INTERIOR,
            display=rule.display_label, regime=None, window=None, tile=semantic_tile.tile_index,
            anchor_ids=(), affinity=SiteSideAffinity.CAGE, position=tile_geometry.cartesian_center,
            local=(0.0, 0.0, 0.0), radius=None, degeneracy=rule.degeneracy,
            exposures=(SiteTileExposure(semantic_tile.tile_index, (0, 0, 0), None),),
        )

    return SpeciesSiteTopologyCatalog(
        geometry.digest, ring_geometry.digest, semantics.digest, profile,
        tuple(anchors), tuple(models), tuple(states),
    )


__all__ = [
    "CANONICAL_SITE_TOPOLOGY_SCHEMA", "SITE_TOPOLOGY_DIGEST_ALGORITHM",
    "CageInteriorRule", "GeneralSiteTemplate", "RingSideAnchor", "RingSideAnchorStatus",
    "RingSiteModel", "RingSiteRule", "SiteLandscapeRegime", "SiteMicrostate",
    "SiteSideAffinity", "SiteStateKind", "SiteTileExposure", "SiteTopologyError",
    "SiteTopologyInputError", "SiteTopologyInvariantError", "SiteTopologyResourceError",
    "SiteTopologyResources", "SiteTopologySerializationError", "SpeciesSiteTopologyCatalog",
    "SpeciesSiteTopologyProfile", "build_species_site_topology",
]
