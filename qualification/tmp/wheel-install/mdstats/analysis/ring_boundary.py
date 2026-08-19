"""Stage-11C3 atom-resolved structural ring boundaries and harmonics.

The ordered T/O atom coordinates supplied by :mod:`ring_geometry` and
:mod:`ring_geometry_frames` remain the authoritative structural object.  This
module adds species-independent atom chemistry, exact cyclic-index spectra,
boundary-measure angular moments, and rank-safe physical-angle harmonic fits.
It deliberately owns no mobile-ion coordination fingerprint or site label.

The discrete cyclic spectrum is the standard finite Fourier transform.  The
physical-angle fit is an explicitly weighted linear least-squares model.  The
separation between these two measures, the fail-closed identifiability policy,
the source-bound alias profile, and the persistent dihedral gauge are mdstats
architectural constructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from numbers import Integral
from typing import Any, Mapping, Sequence

import numpy as np
from ase.data import chemical_symbols

from mdstats.collection import AtomisticFrameCollection

from .ring_geometry import ReferenceRingGeometry, ReferenceRingGeometryCatalog, RingAtomRef
from .ring_geometry_frames import FrameRingGeometry, FrameRingGeometryCatalog

CANONICAL_RING_BOUNDARY_SCHEMA = "mdstats.structural-ring-boundary.v1"
RING_BOUNDARY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class RingBoundaryError(ValueError):
    """Base exception for Stage-11C3 structural ring boundaries."""


class RingBoundaryInputError(RingBoundaryError):
    """Raised when inputs or options violate the C3 contract."""


class RingBoundaryInvariantError(RingBoundaryError):
    """Raised when persistent geometry and chemistry cannot be reconciled."""


class RingBoundaryAliasError(RingBoundaryError):
    """Raised when a crystallographic alias profile fails closed."""


class RingBoundaryResourceError(RingBoundaryError):
    """Raised before a declared finite-work limit is exceeded."""


class RingBoundarySerializationError(RingBoundaryError):
    """Raised when serialized output is not canonical for supplied sources."""


class RingBoundaryStatus(str, Enum):
    RESOLVED = "resolved"
    REFERENCE_UNRESOLVED = "reference-unresolved"
    FRAME_UNRESOLVED = "frame-unresolved"


class HarmonicFitStatus(str, Enum):
    RESOLVED = "resolved"
    ANGULAR_COORDINATE_UNDEFINED = "angular-coordinate-undefined"
    RANK_DEFICIENT = "rank-deficient"
    ILL_CONDITIONED = "ill-conditioned"


class AliasValidationStatus(str, Enum):
    NOT_REQUESTED = "not-requested"
    VALIDATED = "validated"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise RingBoundaryInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise RingBoundaryInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise RingBoundaryInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise RingBoundaryInputError(f"{name} must be finite.")
    return result


def _float_tuple(values: Sequence[object], *, name: str) -> tuple[float, ...]:
    return tuple(_finite(value, name=name) for value in values)


def _float3(values: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = _float_tuple(values, name=name)
    if len(result) != 3:
        raise RingBoundaryInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _complex_record(value: complex) -> tuple[float, float]:
    return float(value.real), float(value.imag)


def _phase_delta(value: float, reference: float, mode: int) -> float:
    period = 2.0 * math.pi / mode
    return float((value - reference + 0.5 * period) % period - 0.5 * period)


def _element_symbol(atomic_number: int) -> str:
    number = int(atomic_number)
    if number <= 0 or number >= len(chemical_symbols):
        raise RingBoundaryInputError(f"Invalid atomic number {number}.")
    return str(chemical_symbols[number])


def _t_class(atomic_number: int) -> str:
    if int(atomic_number) == 14:
        return "Si"
    if int(atomic_number) == 13:
        return "Al"
    return f"Z{int(atomic_number)}"


@dataclass(frozen=True, slots=True)
class RingBoundaryOptions:
    """Numerical and semantic policy for Stage-11C3 descriptors."""

    physical_angle_modes: tuple[int, ...] = (1, 2)
    boundary_moment_modes: tuple[int, ...] = (1, 2, 3)
    angular_radius_tolerance: float = 1.0e-10
    maximum_condition_number: float = 1.0e10
    regularization: float = 0.0
    phase_amplitude_tolerance: float = 1.0e-10
    normalization_floor: float = 1.0e-12
    center_kind: str = "oxygen_area_centroid"

    def __post_init__(self) -> None:
        physical = tuple(sorted({_positive_int(v, name="physical_angle_mode") for v in self.physical_angle_modes}))
        moments = tuple(sorted({_positive_int(v, name="boundary_moment_mode") for v in self.boundary_moment_modes}))
        if not physical:
            raise RingBoundaryInputError("physical_angle_modes cannot be empty.")
        if not moments:
            raise RingBoundaryInputError("boundary_moment_modes cannot be empty.")
        object.__setattr__(self, "physical_angle_modes", physical)
        object.__setattr__(self, "boundary_moment_modes", moments)
        for name in ("angular_radius_tolerance", "maximum_condition_number", "phase_amplitude_tolerance", "normalization_floor"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise RingBoundaryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        regularization = _finite(self.regularization, name="regularization")
        if regularization < 0:
            raise RingBoundaryInputError("regularization must be nonnegative.")
        object.__setattr__(self, "regularization", regularization)
        if self.center_kind != "oxygen_area_centroid":
            raise RingBoundaryInputError(
                "Stage 11C3 currently accepts only the certified oxygen_area_centroid; alternate centers require separately named derived views."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_angle_modes": list(self.physical_angle_modes),
            "boundary_moment_modes": list(self.boundary_moment_modes),
            "angular_radius_tolerance": self.angular_radius_tolerance,
            "maximum_condition_number": self.maximum_condition_number,
            "regularization": self.regularization,
            "phase_amplitude_tolerance": self.phase_amplitude_tolerance,
            "normalization_floor": self.normalization_floor,
            "center_kind": self.center_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingBoundaryOptions":
        return cls(
            physical_angle_modes=tuple(int(v) for v in payload["physical_angle_modes"]),
            boundary_moment_modes=tuple(int(v) for v in payload["boundary_moment_modes"]),
            angular_radius_tolerance=float(payload["angular_radius_tolerance"]),
            maximum_condition_number=float(payload["maximum_condition_number"]),
            regularization=float(payload["regularization"]),
            phase_amplitude_tolerance=float(payload["phase_amplitude_tolerance"]),
            normalization_floor=float(payload["normalization_floor"]),
            center_kind=str(payload["center_kind"]),
        )


@dataclass(frozen=True, slots=True)
class RingBoundaryResources:
    max_rings: int = 100_000
    max_frames: int = 100_000
    max_atom_records: int = 20_000_000

    def __post_init__(self) -> None:
        for name in ("max_rings", "max_frames", "max_atom_records"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingBoundaryResources":
        return cls(**{name: int(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class LtaOxygenAliasProfile:
    """Exact-source LTA O(1)/O(2)/O(3) alias mapping.

    The profile is intentionally bound to one reference-ring catalog digest.
    This prevents a conventional crystallographic alias from being transferred
    silently across a different origin, ordering, chemistry, or framework.
    """

    profile_id: str
    reference_ring_geometry_digest: str
    oxygen_aliases: tuple[tuple[int, str], ...]
    require_complete: bool = True
    require_six_ring_o2_o3_alternation: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise RingBoundaryInputError("profile_id must be a nonempty string.")
        _sha(self.reference_ring_geometry_digest, name="reference_ring_geometry_digest")
        aliases = tuple(sorted((int(index), str(alias)) for index, alias in self.oxygen_aliases))
        if len({index for index, _ in aliases}) != len(aliases):
            raise RingBoundaryInputError("oxygen_aliases must have unique atom indices.")
        allowed = {"O(1)", "O(2)", "O(3)"}
        if any(index < 0 or alias not in allowed for index, alias in aliases):
            raise RingBoundaryInputError("LTA oxygen aliases must be nonnegative indices labeled O(1), O(2), or O(3).")
        object.__setattr__(self, "profile_id", self.profile_id.strip())
        object.__setattr__(self, "oxygen_aliases", aliases)
        if not isinstance(self.require_complete, bool) or not isinstance(self.require_six_ring_o2_o3_alternation, bool):
            raise RingBoundaryInputError("Alias-profile validation flags must be boolean.")

    @property
    def alias_map(self) -> dict[int, str]:
        return dict(self.oxygen_aliases)

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "framework_kind": "LTA",
            "reference_ring_geometry_digest": self.reference_ring_geometry_digest,
            "oxygen_aliases": [[index, alias] for index, alias in self.oxygen_aliases],
            "require_complete": self.require_complete,
            "require_six_ring_o2_o3_alternation": self.require_six_ring_o2_o3_alternation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaOxygenAliasProfile":
        if payload.get("framework_kind") != "LTA":
            raise RingBoundarySerializationError("Alias profile is not an LTA profile.")
        return cls(
            profile_id=str(payload["profile_id"]),
            reference_ring_geometry_digest=str(payload["reference_ring_geometry_digest"]),
            oxygen_aliases=tuple((int(v[0]), str(v[1])) for v in payload["oxygen_aliases"]),
            require_complete=bool(payload["require_complete"]),
            require_six_ring_o2_o3_alternation=bool(payload["require_six_ring_o2_o3_alternation"]),
        )


@dataclass(frozen=True, slots=True)
class HarmonicMode:
    mode: int
    coefficient_real: float
    coefficient_imag: float
    amplitude: float
    normalized_amplitude: float | None
    phase: float | None
    phase_defined: bool
    phase_uncertainty: float | None
    nyquist: bool = False
    nyquist_orientation_sign: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _nonnegative_int(self.mode, name="mode"))
        for name in ("coefficient_real", "coefficient_imag", "amplitude"):
            object.__setattr__(self, name, _finite(getattr(self, name), name=name))
        if self.amplitude < 0:
            raise RingBoundaryInputError("amplitude must be nonnegative.")
        if self.normalized_amplitude is not None:
            value = _finite(self.normalized_amplitude, name="normalized_amplitude")
            if value < 0:
                raise RingBoundaryInputError("normalized_amplitude must be nonnegative.")
            object.__setattr__(self, "normalized_amplitude", value)
        if not isinstance(self.phase_defined, bool) or not isinstance(self.nyquist, bool):
            raise RingBoundaryInputError("phase_defined and nyquist must be boolean.")
        if self.phase_defined:
            if self.phase is None:
                raise RingBoundaryInputError("A defined phase requires a value.")
            object.__setattr__(self, "phase", _finite(self.phase, name="phase"))
        elif self.phase is not None:
            raise RingBoundaryInputError("An undefined phase must be None.")
        if self.phase_uncertainty is not None:
            uncertainty = _finite(self.phase_uncertainty, name="phase_uncertainty")
            if uncertainty < 0:
                raise RingBoundaryInputError("phase_uncertainty must be nonnegative.")
            object.__setattr__(self, "phase_uncertainty", uncertainty)
        if self.nyquist:
            if self.phase_defined:
                raise RingBoundaryInputError("A cyclic Nyquist mode uses an orientation sign, not a continuous phase.")
            if self.nyquist_orientation_sign not in {-1, 0, 1}:
                raise RingBoundaryInputError("nyquist_orientation_sign must be -1, 0, or 1.")
        elif self.nyquist_orientation_sign is not None:
            raise RingBoundaryInputError("Only a Nyquist mode may carry nyquist_orientation_sign.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "coefficient_real": self.coefficient_real,
            "coefficient_imag": self.coefficient_imag,
            "amplitude": self.amplitude,
            "normalized_amplitude": self.normalized_amplitude,
            "phase": self.phase,
            "phase_defined": self.phase_defined,
            "phase_uncertainty": self.phase_uncertainty,
            "nyquist": self.nyquist,
            "nyquist_orientation_sign": self.nyquist_orientation_sign,
        }


@dataclass(frozen=True, slots=True)
class UnweightedCyclicIndexSpectrum:
    sequence_name: str
    values: tuple[float, ...]
    normalization_scale: float | None
    normalization_admissible: bool
    cyclic_origin_atom: RingAtomRef
    orientation: int
    reversal_origin_index: int
    modes: tuple[HarmonicMode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.sequence_name, str) or not self.sequence_name:
            raise RingBoundaryInputError("sequence_name must be nonempty.")
        values = _float_tuple(self.values, name="cyclic_value")
        if not values:
            raise RingBoundaryInputError("A cyclic spectrum requires values.")
        object.__setattr__(self, "values", values)
        if self.normalization_scale is not None:
            scale = _finite(self.normalization_scale, name="normalization_scale")
            if scale <= 0:
                raise RingBoundaryInputError("normalization_scale must be positive.")
            object.__setattr__(self, "normalization_scale", scale)
        if not isinstance(self.normalization_admissible, bool):
            raise RingBoundaryInputError("normalization_admissible must be boolean.")
        if not isinstance(self.cyclic_origin_atom, RingAtomRef):
            raise RingBoundaryInputError("cyclic_origin_atom must be RingAtomRef.")
        if self.orientation not in {-1, 1}:
            raise RingBoundaryInputError("orientation must be -1 or 1.")
        object.__setattr__(self, "reversal_origin_index", _nonnegative_int(self.reversal_origin_index, name="reversal_origin_index"))
        modes = tuple(self.modes)
        if tuple(mode.mode for mode in modes) != tuple(range(len(values) // 2 + 1)):
            raise RingBoundaryInputError("Cyclic modes must contain the unique real-sequence modes in order.")
        object.__setattr__(self, "modes", modes)

    def mode(self, index: int) -> HarmonicMode:
        return self.modes[_nonnegative_int(index, name="mode")]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_name": self.sequence_name,
            "measure": "equal_atom_unweighted_dft",
            "values": list(self.values),
            "normalization_scale": self.normalization_scale,
            "normalization_admissible": self.normalization_admissible,
            "cyclic_origin_atom": self.cyclic_origin_atom.to_dict(),
            "orientation": self.orientation,
            "reversal_origin_index": self.reversal_origin_index,
            "modes": [mode.to_dict() for mode in self.modes],
        }


@dataclass(frozen=True, slots=True)
class BoundaryMeasureAngularMoments:
    sequence_name: str
    values: tuple[float, ...]
    angles: tuple[float, ...]
    weights: tuple[float, ...]
    weighting_measure: str
    normalization_scale: float | None
    normalization_admissible: bool
    modes: tuple[HarmonicMode, ...]

    def __post_init__(self) -> None:
        values = _float_tuple(self.values, name="moment_value")
        angles = _float_tuple(self.angles, name="angle")
        weights = _float_tuple(self.weights, name="weight")
        if not values or len(values) != len(angles) or len(values) != len(weights):
            raise RingBoundaryInputError("Moment values, angles, and weights must be nonempty and aligned.")
        if any(weight <= 0 for weight in weights):
            raise RingBoundaryInputError("Boundary-measure weights must be positive.")
        if not isinstance(self.weighting_measure, str) or not self.weighting_measure:
            raise RingBoundaryInputError("weighting_measure must be nonempty.")
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "angles", angles)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "modes", tuple(self.modes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_name": self.sequence_name,
            "values": list(self.values),
            "angles": list(self.angles),
            "weights": list(self.weights),
            "weighting_measure": self.weighting_measure,
            "normalization_scale": self.normalization_scale,
            "normalization_admissible": self.normalization_admissible,
            "modes": [mode.to_dict() for mode in self.modes],
        }


@dataclass(frozen=True, slots=True)
class PhysicalAngleHarmonicFit:
    sequence_name: str
    values: tuple[float, ...]
    angles: tuple[float, ...]
    weights: tuple[float, ...]
    weighting_measure: str
    requested_modes: tuple[int, ...]
    status: HarmonicFitStatus
    angular_coordinate_defined: bool
    minimum_projected_radius: float
    design_rank: int
    parameter_count: int
    condition_number: float | None
    regularization: float
    residual_rms: float | None
    intercept: float | None
    normalization_scale: float | None
    normalization_admissible: bool
    modes: tuple[HarmonicMode, ...]
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", HarmonicFitStatus(self.status))
        object.__setattr__(self, "minimum_projected_radius", _finite(self.minimum_projected_radius, name="minimum_projected_radius"))
        object.__setattr__(self, "design_rank", _nonnegative_int(self.design_rank, name="design_rank"))
        object.__setattr__(self, "parameter_count", _positive_int(self.parameter_count, name="parameter_count"))
        if self.condition_number is not None:
            object.__setattr__(self, "condition_number", _finite(self.condition_number, name="condition_number"))
        if self.residual_rms is not None:
            value = _finite(self.residual_rms, name="residual_rms")
            if value < 0:
                raise RingBoundaryInputError("residual_rms must be nonnegative.")
            object.__setattr__(self, "residual_rms", value)
        if self.intercept is not None:
            object.__setattr__(self, "intercept", _finite(self.intercept, name="intercept"))
        modes = tuple(self.modes)
        if self.status is HarmonicFitStatus.RESOLVED and len(modes) != len(self.requested_modes):
            raise RingBoundaryInputError("Resolved physical-angle fits require one mode record per requested mode.")
        if self.status is not HarmonicFitStatus.RESOLVED and modes:
            raise RingBoundaryInputError("Unresolved physical-angle fits cannot carry fitted modes.")
        object.__setattr__(self, "modes", modes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_name": self.sequence_name,
            "values": list(self.values),
            "angles": list(self.angles),
            "weights": list(self.weights),
            "weighting_measure": self.weighting_measure,
            "requested_modes": list(self.requested_modes),
            "status": self.status.value,
            "angular_coordinate_defined": self.angular_coordinate_defined,
            "minimum_projected_radius": self.minimum_projected_radius,
            "design_rank": self.design_rank,
            "parameter_count": self.parameter_count,
            "condition_number": self.condition_number,
            "regularization": self.regularization,
            "residual_rms": self.residual_rms,
            "intercept": self.intercept,
            "normalization_scale": self.normalization_scale,
            "normalization_admissible": self.normalization_admissible,
            "modes": [mode.to_dict() for mode in self.modes],
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class RingBoundaryAtomRecord:
    boundary_kind: str
    cyclic_index: int
    orientation: int
    atom_ref: RingAtomRef
    atomic_number: int
    element: str
    neighboring_t_refs: tuple[RingAtomRef, ...]
    neighboring_t_atomic_numbers: tuple[int, ...]
    neighboring_t_classes: tuple[str, ...]
    oxygen_environment_signature: str | None
    crystallographic_alias: str | None
    reference_cartesian: tuple[float, float, float]
    cartesian: tuple[float, float, float]
    local_coordinates: tuple[float, float, float]
    projected_radius: float
    polar_angle: float | None
    normal_coordinate: float

    def __post_init__(self) -> None:
        if self.boundary_kind not in {"T", "O"}:
            raise RingBoundaryInputError("boundary_kind must be T or O.")
        object.__setattr__(self, "cyclic_index", _nonnegative_int(self.cyclic_index, name="cyclic_index"))
        if self.orientation not in {-1, 1}:
            raise RingBoundaryInputError("orientation must be -1 or 1.")
        object.__setattr__(self, "atomic_number", _positive_int(self.atomic_number, name="atomic_number"))
        if self.element != _element_symbol(self.atomic_number):
            raise RingBoundaryInputError("element disagrees with atomic_number.")
        object.__setattr__(self, "reference_cartesian", _float3(self.reference_cartesian, name="reference_cartesian"))
        object.__setattr__(self, "cartesian", _float3(self.cartesian, name="cartesian"))
        object.__setattr__(self, "local_coordinates", _float3(self.local_coordinates, name="local_coordinates"))
        object.__setattr__(self, "projected_radius", _finite(self.projected_radius, name="projected_radius"))
        object.__setattr__(self, "normal_coordinate", _finite(self.normal_coordinate, name="normal_coordinate"))
        if self.polar_angle is not None:
            object.__setattr__(self, "polar_angle", _finite(self.polar_angle, name="polar_angle"))
        if self.boundary_kind == "O":
            if len(self.neighboring_t_refs) != 2 or len(self.neighboring_t_atomic_numbers) != 2 or len(self.neighboring_t_classes) != 2:
                raise RingBoundaryInputError("An O boundary record requires its two ordered neighboring T atoms.")
            if self.oxygen_environment_signature is None:
                raise RingBoundaryInputError("An O boundary record requires an environment signature.")
        elif any((self.neighboring_t_refs, self.neighboring_t_atomic_numbers, self.neighboring_t_classes)) or self.oxygen_environment_signature is not None:
            raise RingBoundaryInputError("A T boundary record cannot carry an O environment.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_kind": self.boundary_kind,
            "cyclic_index": self.cyclic_index,
            "orientation": self.orientation,
            "atom_ref": self.atom_ref.to_dict(),
            "atomic_number": self.atomic_number,
            "element": self.element,
            "neighboring_t_refs": [ref.to_dict() for ref in self.neighboring_t_refs],
            "neighboring_t_atomic_numbers": list(self.neighboring_t_atomic_numbers),
            "neighboring_t_classes": list(self.neighboring_t_classes),
            "oxygen_environment_signature": self.oxygen_environment_signature,
            "crystallographic_alias": self.crystallographic_alias,
            "reference_cartesian": list(self.reference_cartesian),
            "cartesian": list(self.cartesian),
            "local_coordinates": list(self.local_coordinates),
            "projected_radius": self.projected_radius,
            "polar_angle": self.polar_angle,
            "normal_coordinate": self.normal_coordinate,
        }


@dataclass(frozen=True, slots=True)
class OxygenClassSplit:
    class_label: str
    count: int
    mean_radial_coordinate: float
    mean_normal_coordinate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_label": self.class_label,
            "count": self.count,
            "mean_radial_coordinate": self.mean_radial_coordinate,
            "mean_normal_coordinate": self.mean_normal_coordinate,
        }


@dataclass(frozen=True, slots=True)
class PhaseContinuityDiagnostic:
    sequence_name: str
    mode: int
    phase_delta: float | None
    amplitude_ratio: float | None
    resolved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_name": self.sequence_name,
            "mode": self.mode,
            "phase_delta": self.phase_delta,
            "amplitude_ratio": self.amplitude_ratio,
            "resolved": self.resolved,
        }


@dataclass(frozen=True, slots=True)
class StructuralRingBoundary:
    window_index: int
    face_index: int
    primitive_ring_id: int
    ring_size: int
    status: RingBoundaryStatus
    message: str
    center_kind: str
    center_coordinates: tuple[float, float, float] | None
    center_uncertainty: float | None
    cyclic_origin_atom: RingAtomRef | None
    orientation: int
    reversal_origin_index: int
    t_atoms: tuple[RingBoundaryAtomRecord, ...]
    o_atoms: tuple[RingBoundaryAtomRecord, ...]
    cyclic_spectra: tuple[UnweightedCyclicIndexSpectrum, ...]
    boundary_moments: tuple[BoundaryMeasureAngularMoments, ...]
    physical_angle_fits: tuple[PhysicalAngleHarmonicFit, ...]
    oxygen_class_splits: tuple[OxygenClassSplit, ...]
    maximum_oxygen_class_radial_split: float | None
    oxygen_radial_symmetry_breaking: float | None
    dominant_oxygen_radial_mode: int | None
    angular_coordinate_defined: bool
    minimum_projected_radius: float | None
    phase_continuity: tuple[PhaseContinuityDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", RingBoundaryStatus(self.status))
        object.__setattr__(self, "window_index", _nonnegative_int(self.window_index, name="window_index"))
        object.__setattr__(self, "face_index", _nonnegative_int(self.face_index, name="face_index"))
        object.__setattr__(self, "primitive_ring_id", _nonnegative_int(self.primitive_ring_id, name="primitive_ring_id"))
        object.__setattr__(self, "ring_size", _positive_int(self.ring_size, name="ring_size"))
        if self.orientation not in {-1, 1}:
            raise RingBoundaryInputError("orientation must be -1 or 1.")
        if self.status is RingBoundaryStatus.RESOLVED:
            if self.center_coordinates is None or self.center_uncertainty is None or self.cyclic_origin_atom is None:
                raise RingBoundaryInputError("Resolved boundaries require center and gauge provenance.")
            if len(self.t_atoms) != self.ring_size or len(self.o_atoms) != self.ring_size:
                raise RingBoundaryInputError("Resolved T/O atom records must match ring_size.")
            if self.minimum_projected_radius is None:
                raise RingBoundaryInputError("Resolved boundaries require a minimum projected radius.")
        else:
            if any((self.t_atoms, self.o_atoms, self.cyclic_spectra, self.boundary_moments, self.physical_angle_fits, self.oxygen_class_splits, self.phase_continuity)):
                raise RingBoundaryInputError("Unresolved boundaries cannot carry partial derived geometry.")
        object.__setattr__(self, "t_atoms", tuple(self.t_atoms))
        object.__setattr__(self, "o_atoms", tuple(self.o_atoms))
        object.__setattr__(self, "cyclic_spectra", tuple(self.cyclic_spectra))
        object.__setattr__(self, "boundary_moments", tuple(self.boundary_moments))
        object.__setattr__(self, "physical_angle_fits", tuple(self.physical_angle_fits))
        object.__setattr__(self, "oxygen_class_splits", tuple(self.oxygen_class_splits))
        object.__setattr__(self, "phase_continuity", tuple(self.phase_continuity))

    def spectrum(self, name: str) -> UnweightedCyclicIndexSpectrum:
        matches = [value for value in self.cyclic_spectra if value.sequence_name == name]
        if len(matches) != 1:
            raise RingBoundaryInputError(f"Expected one cyclic spectrum named {name!r}.")
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "primitive_ring_id": self.primitive_ring_id,
            "ring_size": self.ring_size,
            "status": self.status.value,
            "message": self.message,
            "center_kind": self.center_kind,
            "center_coordinates": None if self.center_coordinates is None else list(self.center_coordinates),
            "center_uncertainty": self.center_uncertainty,
            "cyclic_origin_atom": None if self.cyclic_origin_atom is None else self.cyclic_origin_atom.to_dict(),
            "orientation": self.orientation,
            "reversal_origin_index": self.reversal_origin_index,
            "t_atoms": [value.to_dict() for value in self.t_atoms],
            "o_atoms": [value.to_dict() for value in self.o_atoms],
            "cyclic_spectra": [value.to_dict() for value in self.cyclic_spectra],
            "boundary_moments": [value.to_dict() for value in self.boundary_moments],
            "physical_angle_fits": [value.to_dict() for value in self.physical_angle_fits],
            "oxygen_class_splits": [value.to_dict() for value in self.oxygen_class_splits],
            "maximum_oxygen_class_radial_split": self.maximum_oxygen_class_radial_split,
            "oxygen_radial_symmetry_breaking": self.oxygen_radial_symmetry_breaking,
            "dominant_oxygen_radial_mode": self.dominant_oxygen_radial_mode,
            "angular_coordinate_defined": self.angular_coordinate_defined,
            "minimum_projected_radius": self.minimum_projected_radius,
            "phase_continuity": [value.to_dict() for value in self.phase_continuity],
        }


@dataclass(frozen=True, slots=True)
class StructuralRingBoundaryFrame:
    result_position: int
    collection_frame_index: int
    frame_id: int
    boundaries: tuple[StructuralRingBoundary, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_position", _nonnegative_int(self.result_position, name="result_position"))
        object.__setattr__(self, "collection_frame_index", _nonnegative_int(self.collection_frame_index, name="collection_frame_index"))
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, Integral):
            raise RingBoundaryInputError("frame_id must be an integer.")
        boundaries = tuple(self.boundaries)
        if tuple(boundary.window_index for boundary in boundaries) != tuple(range(len(boundaries))):
            raise RingBoundaryInputError("Frame boundary window indices must be dense and ordered.")
        object.__setattr__(self, "boundaries", boundaries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_position": self.result_position,
            "collection_frame_index": self.collection_frame_index,
            "frame_id": self.frame_id,
            "boundaries": [value.to_dict() for value in self.boundaries],
        }


@dataclass(frozen=True, slots=True, eq=False)
class StructuralRingBoundaryCatalog:
    reference_ring_geometry_digest: str
    frame_ring_geometry_digest: str
    collection_chemistry_digest: str
    alias_validation_status: AliasValidationStatus
    alias_profile: LtaOxygenAliasProfile | None
    options: RingBoundaryOptions
    resources: RingBoundaryResources
    reference_boundaries: tuple[StructuralRingBoundary, ...]
    frames: tuple[StructuralRingBoundaryFrame, ...]
    canonical_schema_version: str = CANONICAL_RING_BOUNDARY_SCHEMA
    digest_algorithm: str = RING_BOUNDARY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("reference_ring_geometry_digest", "frame_ring_geometry_digest", "collection_chemistry_digest"):
            _sha(getattr(self, name), name=name)
        object.__setattr__(self, "alias_validation_status", AliasValidationStatus(self.alias_validation_status))
        references = tuple(self.reference_boundaries)
        frames = tuple(self.frames)
        if tuple(value.window_index for value in references) != tuple(range(len(references))):
            raise RingBoundaryInputError("Reference boundary indices must be dense and ordered.")
        if tuple(frame.result_position for frame in frames) != tuple(range(len(frames))):
            raise RingBoundaryInputError("Frame results must be dense and ordered.")
        if any(len(frame.boundaries) != len(references) for frame in frames):
            raise RingBoundaryInputError("Every frame must retain all persistent ring identities.")
        if self.canonical_schema_version != CANONICAL_RING_BOUNDARY_SCHEMA:
            raise RingBoundaryInputError("Unsupported structural-ring-boundary schema.")
        if self.digest_algorithm != RING_BOUNDARY_DIGEST_ALGORITHM:
            raise RingBoundaryInputError("Unsupported structural-ring-boundary digest algorithm.")
        object.__setattr__(self, "reference_boundaries", references)
        object.__setattr__(self, "frames", frames)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise RingBoundaryInputError("Stored structural-ring-boundary digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StructuralRingBoundaryCatalog) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "reference_ring_geometry_digest": self.reference_ring_geometry_digest,
            "frame_ring_geometry_digest": self.frame_ring_geometry_digest,
            "collection_chemistry_digest": self.collection_chemistry_digest,
            "alias_validation_status": self.alias_validation_status.value,
            "alias_profile": None if self.alias_profile is None else self.alias_profile.to_dict(),
            "options": self.options.to_dict(),
            "resources": self.resources.to_dict(),
            "reference_boundaries": [value.to_dict() for value in self.reference_boundaries],
            "frames": [value.to_dict() for value in self.frames],
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
        reference_geometry: ReferenceRingGeometryCatalog,
        frame_geometry: FrameRingGeometryCatalog,
        collection: AtomisticFrameCollection,
    ) -> "StructuralRingBoundaryCatalog":
        try:
            profile_payload = payload.get("alias_profile")
            rebuilt = build_structural_ring_boundary_catalog(
                reference_geometry,
                frame_geometry,
                collection,
                alias_profile=None if profile_payload is None else LtaOxygenAliasProfile.from_dict(profile_payload),
                options=RingBoundaryOptions.from_dict(payload["options"]),
                resources=RingBoundaryResources.from_dict(payload["resources"]),
            )
            if rebuilt.to_dict() != dict(payload):
                raise RingBoundarySerializationError(
                    "Serialized structural ring boundary is not canonical for supplied sources."
                )
            return rebuilt
        except RingBoundaryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise RingBoundarySerializationError("Invalid structural-ring-boundary payload.") from exc


def apply_cyclic_dihedral_gauge(
    values: Sequence[float],
    *,
    origin_shift: int = 0,
    orientation: int = 1,
) -> tuple[float, ...]:
    """Return ``y'_j = y_{j+s}`` or ``y'_j = y_{s-j}`` for a cyclic gauge change."""

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size < 2 or not np.all(np.isfinite(array)):
        raise RingBoundaryInputError("values must be a finite cyclic sequence.")
    if orientation not in {-1, 1}:
        raise RingBoundaryInputError("orientation must be -1 or 1.")
    shift = int(origin_shift) % array.size
    indices = (np.arange(array.size) + shift) % array.size if orientation == 1 else (shift - np.arange(array.size)) % array.size
    return tuple(float(value) for value in array[indices])


def transform_cyclic_coefficient(
    coefficient: complex,
    *,
    ring_size: int,
    mode: int,
    origin_shift: int = 0,
    orientation: int = 1,
) -> complex:
    """Apply the declared dihedral gauge law to one cyclic DFT coefficient."""

    size = _positive_int(ring_size, name="ring_size")
    harmonic = _nonnegative_int(mode, name="mode")
    if orientation not in {-1, 1}:
        raise RingBoundaryInputError("orientation must be -1 or 1.")
    angle = 2.0 * math.pi * harmonic * (int(origin_shift) % size) / size
    if orientation == 1:
        return complex(coefficient) * np.exp(1j * angle)
    return np.conjugate(complex(coefficient)) * np.exp(-1j * angle)


def compute_unweighted_cyclic_index_spectrum(
    values: Sequence[float],
    *,
    sequence_name: str,
    cyclic_origin_atom: RingAtomRef,
    normalization_scale: float | None = None,
    phase_amplitude_tolerance: float = 1.0e-10,
    orientation: int = 1,
    reversal_origin_index: int = 0,
) -> UnweightedCyclicIndexSpectrum:
    """Compute the exact equal-atom DFT unique to a real cyclic sequence."""

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size < 2 or not np.all(np.isfinite(array)):
        raise RingBoundaryInputError("values must be a finite one-dimensional sequence with at least two entries.")
    if orientation not in {-1, 1}:
        raise RingBoundaryInputError("orientation must be -1 or 1.")
    tolerance = _finite(phase_amplitude_tolerance, name="phase_amplitude_tolerance")
    if tolerance <= 0:
        raise RingBoundaryInputError("phase_amplitude_tolerance must be positive.")
    scale = None if normalization_scale is None else _finite(normalization_scale, name="normalization_scale")
    if scale is not None and scale <= 0:
        raise RingBoundaryInputError("normalization_scale must be positive when provided.")
    admissible = scale is not None
    coefficients = np.fft.fft(array) / array.size
    records: list[HarmonicMode] = []
    for mode in range(array.size // 2 + 1):
        coefficient = complex(coefficients[mode])
        nyquist = bool(array.size % 2 == 0 and mode == array.size // 2)
        if nyquist and abs(coefficient.imag) <= 100.0 * np.finfo(float).eps * max(1.0, abs(coefficient.real)):
            coefficient = complex(coefficient.real, 0.0)
        amplitude = abs(coefficient)
        normalized = amplitude / scale if admissible else None
        phase_defined = bool(mode > 0 and not nyquist and amplitude > tolerance * max(1.0, abs(coefficients[0])))
        phase = float(math.atan2(coefficient.imag, coefficient.real)) if phase_defined else None
        orientation_sign = None
        if nyquist:
            orientation_sign = 0 if amplitude <= tolerance * max(1.0, abs(coefficients[0])) else (1 if coefficient.real > 0 else -1)
        records.append(
            HarmonicMode(
                mode=mode,
                coefficient_real=float(coefficient.real),
                coefficient_imag=float(coefficient.imag),
                amplitude=float(amplitude),
                normalized_amplitude=None if normalized is None else float(normalized),
                phase=phase,
                phase_defined=phase_defined,
                phase_uncertainty=0.0 if phase_defined else None,
                nyquist=nyquist,
                nyquist_orientation_sign=orientation_sign,
            )
        )
    return UnweightedCyclicIndexSpectrum(
        sequence_name=sequence_name,
        values=tuple(float(v) for v in array),
        normalization_scale=scale if admissible else None,
        normalization_admissible=admissible,
        cyclic_origin_atom=cyclic_origin_atom,
        orientation=orientation,
        reversal_origin_index=reversal_origin_index,
        modes=tuple(records),
    )


def compute_boundary_measure_angular_moments(
    values: Sequence[float],
    angles: Sequence[float],
    weights: Sequence[float],
    *,
    sequence_name: str,
    modes: Sequence[int],
    normalization_scale: float | None,
    phase_amplitude_tolerance: float,
    weighting_measure: str = "arc_length_voronoi",
) -> BoundaryMeasureAngularMoments:
    array = np.asarray(values, dtype=np.float64)
    theta = np.asarray(angles, dtype=np.float64)
    weight = np.asarray(weights, dtype=np.float64)
    if array.ndim != 1 or theta.shape != array.shape or weight.shape != array.shape or array.size < 2:
        raise RingBoundaryInputError("values, angles, and weights must be aligned one-dimensional arrays.")
    if not np.all(np.isfinite(array)) or not np.all(np.isfinite(theta)) or not np.all(np.isfinite(weight)) or np.any(weight <= 0):
        raise RingBoundaryInputError("Angular-moment inputs must be finite and weights positive.")
    requested = tuple(sorted({_positive_int(mode, name="mode") for mode in modes}))
    scale = None if normalization_scale is None else _finite(normalization_scale, name="normalization_scale")
    if scale is not None and scale <= 0:
        raise RingBoundaryInputError("normalization_scale must be positive when provided.")
    admissible = scale is not None
    denominator = float(np.sum(weight))
    records: list[HarmonicMode] = []
    zero = complex(np.sum(weight * array) / denominator, 0.0)
    for mode in requested:
        coefficient = complex(np.sum(weight * array * np.exp(-1j * mode * theta)) / denominator)
        amplitude = abs(coefficient)
        phase_defined = amplitude > phase_amplitude_tolerance * max(1.0, abs(zero))
        records.append(
            HarmonicMode(
                mode=mode,
                coefficient_real=float(coefficient.real),
                coefficient_imag=float(coefficient.imag),
                amplitude=float(amplitude),
                normalized_amplitude=float(amplitude / scale) if admissible else None,
                phase=float(math.atan2(coefficient.imag, coefficient.real)) if phase_defined else None,
                phase_defined=phase_defined,
                phase_uncertainty=0.0 if phase_defined else None,
            )
        )
    return BoundaryMeasureAngularMoments(
        sequence_name=sequence_name,
        values=tuple(float(v) for v in array),
        angles=tuple(float(v) for v in theta),
        weights=tuple(float(v) for v in weight),
        weighting_measure=weighting_measure,
        normalization_scale=scale if admissible else None,
        normalization_admissible=admissible,
        modes=tuple(records),
    )


def fit_physical_angle_harmonics(
    values: Sequence[float],
    angles: Sequence[float],
    weights: Sequence[float],
    projected_radii: Sequence[float],
    *,
    sequence_name: str,
    modes: Sequence[int],
    weighting_measure: str,
    angular_radius_tolerance: float,
    maximum_condition_number: float,
    regularization: float,
    phase_amplitude_tolerance: float,
    normalization_scale: float | None,
) -> PhysicalAngleHarmonicFit:
    array = np.asarray(values, dtype=np.float64)
    theta = np.asarray(angles, dtype=np.float64)
    weight = np.asarray(weights, dtype=np.float64)
    radii = np.asarray(projected_radii, dtype=np.float64)
    if array.ndim != 1 or array.size < 2 or theta.shape != array.shape or weight.shape != array.shape or radii.shape != array.shape:
        raise RingBoundaryInputError("values, angles, weights, and projected_radii must be aligned one-dimensional arrays.")
    if not np.all(np.isfinite(array)) or not np.all(np.isfinite(theta)) or not np.all(np.isfinite(weight)) or np.any(weight <= 0):
        raise RingBoundaryInputError("Physical-angle inputs must be finite and weights positive.")
    requested = tuple(sorted({_positive_int(mode, name="mode") for mode in modes}))
    if not requested:
        raise RingBoundaryInputError("At least one physical-angle mode is required.")
    parameter_count = 1 + 2 * len(requested)
    minimum_radius = float(np.min(radii)) if radii.size else 0.0
    if normalization_scale is not None:
        normalization_scale = _finite(normalization_scale, name="normalization_scale")
        if normalization_scale <= 0:
            raise RingBoundaryInputError("normalization_scale must be positive when provided.")
    common = dict(
        sequence_name=sequence_name,
        values=tuple(float(v) for v in array),
        angles=tuple(float(v) for v in theta),
        weights=tuple(float(v) for v in weight),
        weighting_measure=weighting_measure,
        requested_modes=requested,
        minimum_projected_radius=minimum_radius,
        parameter_count=parameter_count,
        regularization=float(regularization),
        normalization_scale=normalization_scale,
        normalization_admissible=normalization_scale is not None and normalization_scale > 0,
    )
    angular_defined = bool(radii.size == array.size and radii.size > 0 and np.all(np.isfinite(radii)) and minimum_radius > angular_radius_tolerance)
    if not angular_defined:
        return PhysicalAngleHarmonicFit(
            **common,
            status=HarmonicFitStatus.ANGULAR_COORDINATE_UNDEFINED,
            angular_coordinate_defined=False,
            design_rank=0,
            condition_number=None,
            residual_rms=None,
            intercept=None,
            modes=(),
            message="At least one projected atom radius is singular or below tolerance.",
        )
    columns = [np.ones(array.size, dtype=np.float64)]
    for mode in requested:
        columns.extend((np.cos(mode * theta), np.sin(mode * theta)))
    design = np.column_stack(columns)
    weighted_design = np.sqrt(weight)[:, None] * design
    weighted_values = np.sqrt(weight) * array
    rank = int(np.linalg.matrix_rank(weighted_design))
    condition = float(np.linalg.cond(weighted_design))
    if rank < parameter_count:
        return PhysicalAngleHarmonicFit(
            **common,
            status=HarmonicFitStatus.RANK_DEFICIENT,
            angular_coordinate_defined=True,
            design_rank=rank,
            condition_number=condition,
            residual_rms=None,
            intercept=None,
            modes=(),
            message=f"Design rank {rank} is below parameter count {parameter_count}.",
        )
    if not math.isfinite(condition) or condition > maximum_condition_number:
        return PhysicalAngleHarmonicFit(
            **common,
            status=HarmonicFitStatus.ILL_CONDITIONED,
            angular_coordinate_defined=True,
            design_rank=rank,
            condition_number=condition,
            residual_rms=None,
            intercept=None,
            modes=(),
            message=f"Design condition number {condition:.6g} exceeds {maximum_condition_number:.6g}.",
        )
    normal = weighted_design.T @ weighted_design
    if regularization > 0:
        penalty = np.eye(parameter_count, dtype=np.float64) * regularization
        penalty[0, 0] = 0.0
        normal = normal + penalty
    rhs = weighted_design.T @ weighted_values
    coefficients = np.linalg.solve(normal, rhs)
    residual = array - design @ coefficients
    residual_rms = float(math.sqrt(np.sum(weight * residual**2) / np.sum(weight)))
    dof = array.size - parameter_count
    covariance = None
    if dof > 0:
        sigma2 = float(np.sum(weight * residual**2) / dof)
        covariance = sigma2 * np.linalg.inv(normal)
    scale = normalization_scale if normalization_scale is not None and normalization_scale > 0 else None
    records: list[HarmonicMode] = []
    for position, mode in enumerate(requested):
        a_index = 1 + 2 * position
        b_index = a_index + 1
        a = float(coefficients[a_index])
        b = float(coefficients[b_index])
        coefficient = complex(a, -b)
        amplitude = abs(coefficient)
        phase_defined = amplitude > phase_amplitude_tolerance * max(1.0, abs(float(coefficients[0])))
        phase_uncertainty = None
        if phase_defined and covariance is not None:
            gradient = np.asarray([b / amplitude**2, -a / amplitude**2], dtype=np.float64)
            sub = covariance[np.ix_([a_index, b_index], [a_index, b_index])]
            variance = float(gradient @ sub @ gradient)
            phase_uncertainty = math.sqrt(max(0.0, variance))
        records.append(
            HarmonicMode(
                mode=mode,
                coefficient_real=float(coefficient.real),
                coefficient_imag=float(coefficient.imag),
                amplitude=float(amplitude),
                normalized_amplitude=float(amplitude / scale) if scale is not None else None,
                phase=float(math.atan2(coefficient.imag, coefficient.real)) if phase_defined else None,
                phase_defined=phase_defined,
                phase_uncertainty=phase_uncertainty,
            )
        )
    return PhysicalAngleHarmonicFit(
        **common,
        status=HarmonicFitStatus.RESOLVED,
        angular_coordinate_defined=True,
        design_rank=rank,
        condition_number=condition,
        residual_rms=residual_rms,
        intercept=float(coefficients[0]),
        modes=tuple(records),
        message="Resolved weighted physical-angle harmonic fit.",
    )


def _chemistry_digest(collection: AtomisticFrameCollection) -> str:
    array = np.asarray(collection.atomic_numbers, dtype="<i4")
    digest = hashlib.sha256()
    digest.update(b"mdstats.ring-boundary-chemistry.v1\0")
    digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
    digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _validate_alias_profile(profile: LtaOxygenAliasProfile | None, reference: ReferenceRingGeometryCatalog, collection: AtomisticFrameCollection) -> tuple[AliasValidationStatus, dict[int, str]]:
    if profile is None:
        return AliasValidationStatus.NOT_REQUESTED, {}
    if profile.reference_ring_geometry_digest != reference.digest:
        raise RingBoundaryAliasError("The LTA alias profile is bound to a different reference-ring geometry digest.")
    oxygen_indices = {ref.atom_index for ring in reference.rings if ring.resolved for ref in ring.o_atom_refs}
    aliases = profile.alias_map
    unknown = sorted(set(aliases) - oxygen_indices)
    if unknown:
        raise RingBoundaryAliasError(f"Alias profile references atoms that are not persistent ring oxygens: {unknown[:8]}.")
    if any(int(collection.atomic_numbers[index]) != 8 for index in aliases):
        raise RingBoundaryAliasError("Alias profile assigns an O alias to a non-oxygen atom.")
    if profile.require_complete and set(aliases) != oxygen_indices:
        missing = sorted(oxygen_indices - set(aliases))
        raise RingBoundaryAliasError(f"Complete LTA alias profile is missing {len(missing)} persistent oxygen atoms.")
    if profile.require_six_ring_o2_o3_alternation:
        for ring in reference.rings:
            if not ring.resolved or ring.ring_size != 6:
                continue
            sequence = tuple(aliases.get(ref.atom_index) for ref in ring.o_atom_refs)
            if any(value not in {"O(2)", "O(3)"} for value in sequence):
                raise RingBoundaryAliasError("A validated LTA S6R alternation requires only O(2)/O(3) aliases.")
            if any(sequence[index] == sequence[(index + 1) % 6] for index in range(6)):
                raise RingBoundaryAliasError("The supplied LTA S6R O(2)/O(3) aliases do not alternate cyclically.")
    return AliasValidationStatus.VALIDATED, aliases


def _arc_length_voronoi_weights(points: np.ndarray) -> np.ndarray:
    edge = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    weights = 0.5 * (np.roll(edge, 1) + edge)
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0):
        raise RingBoundaryInvariantError("Boundary polygon does not define positive arc-length Voronoi weights.")
    return weights


def _local_components(points: np.ndarray, center: np.ndarray, axis_u: np.ndarray, axis_v: np.ndarray, normal: np.ndarray, tolerance: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    delta = points - center
    local = np.column_stack((delta @ axis_u, delta @ axis_v, delta @ normal))
    radius = np.linalg.norm(local[:, :2], axis=1)
    angles = np.full(radius.shape, np.nan, dtype=np.float64)
    valid = radius > tolerance
    angles[valid] = np.arctan2(local[valid, 1], local[valid, 0])
    return local, radius, angles, valid


def _normalization(values: np.ndarray, floor: float) -> float | None:
    scale = abs(float(np.mean(values)))
    return scale if scale > floor else None


def _build_atom_records(
    reference: ReferenceRingGeometry,
    current: ReferenceRingGeometry | FrameRingGeometry,
    collection: AtomisticFrameCollection,
    aliases: Mapping[int, str],
    tolerance: float,
) -> tuple[tuple[RingBoundaryAtomRecord, ...], tuple[RingBoundaryAtomRecord, ...], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    center = np.asarray(current.oxygen_area_centroid, dtype=np.float64)
    axis_u = np.asarray(current.side_frames[0].axis_u, dtype=np.float64)
    axis_v = np.asarray(current.side_frames[0].axis_v, dtype=np.float64)
    normal = np.asarray(current.ordered_unit_normal, dtype=np.float64)
    t_points = np.asarray(current.t_cartesian_vertices, dtype=np.float64)
    o_points = np.asarray(current.o_cartesian_vertices, dtype=np.float64)
    t_local, t_radius, t_angle, _ = _local_components(t_points, center, axis_u, axis_v, normal, tolerance)
    o_local, o_radius, o_angle, _ = _local_components(o_points, center, axis_u, axis_v, normal, tolerance)
    atomic_numbers = np.asarray(collection.atomic_numbers, dtype=np.int64)
    t_records: list[RingBoundaryAtomRecord] = []
    o_records: list[RingBoundaryAtomRecord] = []
    for index, ref in enumerate(reference.t_atom_refs):
        number = int(atomic_numbers[ref.atom_index])
        t_records.append(
            RingBoundaryAtomRecord(
                boundary_kind="T",
                cyclic_index=index,
                orientation=1,
                atom_ref=ref,
                atomic_number=number,
                element=_element_symbol(number),
                neighboring_t_refs=(),
                neighboring_t_atomic_numbers=(),
                neighboring_t_classes=(),
                oxygen_environment_signature=None,
                crystallographic_alias=None,
                reference_cartesian=reference.t_cartesian_vertices[index],
                cartesian=tuple(float(v) for v in t_points[index]),
                local_coordinates=tuple(float(v) for v in t_local[index]),
                projected_radius=float(t_radius[index]),
                polar_angle=None if not math.isfinite(float(t_angle[index])) else float(t_angle[index]),
                normal_coordinate=float(t_local[index, 2]),
            )
        )
    for index, ref in enumerate(reference.o_atom_refs):
        left_ref = reference.t_atom_refs[index]
        right_ref = reference.t_atom_refs[(index + 1) % reference.ring_size]
        left_number = int(atomic_numbers[left_ref.atom_index])
        right_number = int(atomic_numbers[right_ref.atom_index])
        classes = (_t_class(left_number), _t_class(right_number))
        signature = "--".join(sorted(classes))
        number = int(atomic_numbers[ref.atom_index])
        o_records.append(
            RingBoundaryAtomRecord(
                boundary_kind="O",
                cyclic_index=index,
                orientation=1,
                atom_ref=ref,
                atomic_number=number,
                element=_element_symbol(number),
                neighboring_t_refs=(left_ref, right_ref),
                neighboring_t_atomic_numbers=(left_number, right_number),
                neighboring_t_classes=classes,
                oxygen_environment_signature=signature,
                crystallographic_alias=aliases.get(ref.atom_index),
                reference_cartesian=reference.o_cartesian_vertices[index],
                cartesian=tuple(float(v) for v in o_points[index]),
                local_coordinates=tuple(float(v) for v in o_local[index]),
                projected_radius=float(o_radius[index]),
                polar_angle=None if not math.isfinite(float(o_angle[index])) else float(o_angle[index]),
                normal_coordinate=float(o_local[index, 2]),
            )
        )
    return tuple(t_records), tuple(o_records), t_points, o_points, t_angle, o_angle


def _sequence_payload(t_atoms: tuple[RingBoundaryAtomRecord, ...], o_atoms: tuple[RingBoundaryAtomRecord, ...]) -> dict[str, np.ndarray]:
    return {
        "t_radial": np.asarray([atom.projected_radius for atom in t_atoms], dtype=np.float64),
        "t_normal": np.asarray([atom.normal_coordinate for atom in t_atoms], dtype=np.float64),
        "t_atomic_number": np.asarray([atom.atomic_number for atom in t_atoms], dtype=np.float64),
        "oxygen_radial": np.asarray([atom.projected_radius for atom in o_atoms], dtype=np.float64),
        "oxygen_normal": np.asarray([atom.normal_coordinate for atom in o_atoms], dtype=np.float64),
        "oxygen_adjacent_al_count": np.asarray(
            [sum(number == 13 for number in atom.neighboring_t_atomic_numbers) for atom in o_atoms], dtype=np.float64
        ),
    }


def _class_splits(o_atoms: tuple[RingBoundaryAtomRecord, ...]) -> tuple[tuple[OxygenClassSplit, ...], float]:
    grouped: dict[str, list[RingBoundaryAtomRecord]] = {}
    for atom in o_atoms:
        label = atom.crystallographic_alias or str(atom.oxygen_environment_signature)
        grouped.setdefault(label, []).append(atom)
    splits = tuple(
        OxygenClassSplit(
            class_label=label,
            count=len(atoms),
            mean_radial_coordinate=float(np.mean([atom.projected_radius for atom in atoms])),
            mean_normal_coordinate=float(np.mean([atom.normal_coordinate for atom in atoms])),
        )
        for label, atoms in sorted(grouped.items())
    )
    radial = [value.mean_radial_coordinate for value in splits]
    maximum = 0.0 if len(radial) < 2 else float(max(radial) - min(radial))
    return splits, maximum


def _continuity(reference: StructuralRingBoundary, current_spectra: Sequence[UnweightedCyclicIndexSpectrum]) -> tuple[PhaseContinuityDiagnostic, ...]:
    if reference.status is not RingBoundaryStatus.RESOLVED:
        return ()
    diagnostics: list[PhaseContinuityDiagnostic] = []
    reference_by_name = {value.sequence_name: value for value in reference.cyclic_spectra}
    for spectrum in current_spectra:
        base = reference_by_name[spectrum.sequence_name]
        for now, earlier in zip(spectrum.modes[1:], base.modes[1:], strict=True):
            if now.nyquist or earlier.nyquist:
                resolved = now.nyquist_orientation_sign != 0 and earlier.nyquist_orientation_sign != 0
                diagnostics.append(
                    PhaseContinuityDiagnostic(
                        spectrum.sequence_name,
                        now.mode,
                        None,
                        None if earlier.amplitude == 0 else float(now.amplitude / earlier.amplitude),
                        resolved,
                    )
                )
            else:
                resolved = now.phase_defined and earlier.phase_defined
                diagnostics.append(
                    PhaseContinuityDiagnostic(
                        spectrum.sequence_name,
                        now.mode,
                        _phase_delta(float(now.phase), float(earlier.phase), now.mode) if resolved else None,
                        None if earlier.amplitude == 0 else float(now.amplitude / earlier.amplitude),
                        resolved,
                    )
                )
    return tuple(diagnostics)


def _build_boundary(
    reference: ReferenceRingGeometry,
    current: ReferenceRingGeometry | FrameRingGeometry,
    collection: AtomisticFrameCollection,
    aliases: Mapping[int, str],
    options: RingBoundaryOptions,
    reference_boundary: StructuralRingBoundary | None,
    unresolved_status: RingBoundaryStatus,
) -> StructuralRingBoundary:
    current_resolved = bool(getattr(current, "resolved", getattr(current, "mapped", False)))
    if not reference.resolved:
        return StructuralRingBoundary(
            window_index=reference.window_index,
            face_index=reference.face_index,
            primitive_ring_id=reference.primitive_ring_id,
            ring_size=reference.ring_size,
            status=RingBoundaryStatus.REFERENCE_UNRESOLVED,
            message=reference.message,
            center_kind=options.center_kind,
            center_coordinates=None,
            center_uncertainty=None,
            cyclic_origin_atom=None,
            orientation=1,
            reversal_origin_index=0,
            t_atoms=(), o_atoms=(), cyclic_spectra=(), boundary_moments=(), physical_angle_fits=(),
            oxygen_class_splits=(), maximum_oxygen_class_radial_split=None,
            oxygen_radial_symmetry_breaking=None, dominant_oxygen_radial_mode=None,
            angular_coordinate_defined=False, minimum_projected_radius=None,
        )
    if not current_resolved:
        return StructuralRingBoundary(
            window_index=reference.window_index,
            face_index=reference.face_index,
            primitive_ring_id=reference.primitive_ring_id,
            ring_size=reference.ring_size,
            status=unresolved_status,
            message=getattr(current, "message", "Upstream frame ring geometry is unresolved."),
            center_kind=options.center_kind,
            center_coordinates=None,
            center_uncertainty=None,
            cyclic_origin_atom=None,
            orientation=1,
            reversal_origin_index=0,
            t_atoms=(), o_atoms=(), cyclic_spectra=(), boundary_moments=(), physical_angle_fits=(),
            oxygen_class_splits=(), maximum_oxygen_class_radial_split=None,
            oxygen_radial_symmetry_breaking=None, dominant_oxygen_radial_mode=None,
            angular_coordinate_defined=False, minimum_projected_radius=None,
        )
    t_atoms, o_atoms, t_points, o_points, t_angles, o_angles = _build_atom_records(
        reference, current, collection, aliases, options.angular_radius_tolerance
    )
    sequences = _sequence_payload(t_atoms, o_atoms)
    cyclic: list[UnweightedCyclicIndexSpectrum] = []
    for name, values in sequences.items():
        atom = reference.t_atom_refs[0] if name.startswith("t_") else reference.o_atom_refs[0]
        cyclic.append(
            compute_unweighted_cyclic_index_spectrum(
                values,
                sequence_name=name,
                cyclic_origin_atom=atom,
                normalization_scale=_normalization(values, options.normalization_floor),
                phase_amplitude_tolerance=options.phase_amplitude_tolerance,
            )
        )
    o_weights = _arc_length_voronoi_weights(o_points)
    t_weights = _arc_length_voronoi_weights(t_points)
    moments: list[BoundaryMeasureAngularMoments] = []
    fits: list[PhysicalAngleHarmonicFit] = []
    for name in ("oxygen_radial", "oxygen_normal", "t_radial", "t_normal"):
        is_oxygen = name.startswith("oxygen_")
        values = sequences[name]
        angles = o_angles if is_oxygen else t_angles
        weights = o_weights if is_oxygen else t_weights
        radii = np.asarray([atom.projected_radius for atom in (o_atoms if is_oxygen else t_atoms)], dtype=np.float64)
        angular_sequence_defined = bool(np.all(np.isfinite(angles)) and np.all(radii > options.angular_radius_tolerance))
        finite_angles = np.where(np.isfinite(angles), angles, 0.0)
        scale = _normalization(values, options.normalization_floor)
        if angular_sequence_defined:
            moments.append(
                compute_boundary_measure_angular_moments(
                    values, finite_angles, weights,
                    sequence_name=name,
                    modes=options.boundary_moment_modes,
                    normalization_scale=scale,
                    phase_amplitude_tolerance=options.phase_amplitude_tolerance,
                )
            )
        fits.append(
            fit_physical_angle_harmonics(
                values, finite_angles, np.ones_like(weights), radii,
                sequence_name=name,
                modes=options.physical_angle_modes,
                weighting_measure="equal_atom",
                angular_radius_tolerance=options.angular_radius_tolerance,
                maximum_condition_number=options.maximum_condition_number,
                regularization=options.regularization,
                phase_amplitude_tolerance=options.phase_amplitude_tolerance,
                normalization_scale=scale,
            )
        )
        fits.append(
            fit_physical_angle_harmonics(
                values, finite_angles, weights, radii,
                sequence_name=name,
                modes=options.physical_angle_modes,
                weighting_measure="arc_length_voronoi",
                angular_radius_tolerance=options.angular_radius_tolerance,
                maximum_condition_number=options.maximum_condition_number,
                regularization=options.regularization,
                phase_amplitude_tolerance=options.phase_amplitude_tolerance,
                normalization_scale=scale,
            )
        )
    splits, maximum_split = _class_splits(o_atoms)
    oxygen_spectrum = next(value for value in cyclic if value.sequence_name == "oxygen_radial")
    nonzero = oxygen_spectrum.modes[1:]
    dominant_record = max(nonzero, key=lambda value: value.amplitude) if nonzero else None
    dominant = (
        dominant_record.mode
        if dominant_record is not None
        and dominant_record.amplitude > options.phase_amplitude_tolerance * max(1.0, oxygen_spectrum.modes[0].amplitude)
        else None
    )
    mean_radius = abs(float(np.mean(sequences["oxygen_radial"])))
    breaking = float(math.sqrt(sum(value.amplitude**2 for value in nonzero)) / mean_radius) if mean_radius > options.normalization_floor else None
    minimum_radius = min(atom.projected_radius for atom in (*t_atoms, *o_atoms))
    angular_defined = minimum_radius > options.angular_radius_tolerance
    continuity = () if reference_boundary is None else _continuity(reference_boundary, cyclic)
    return StructuralRingBoundary(
        window_index=reference.window_index,
        face_index=reference.face_index,
        primitive_ring_id=reference.primitive_ring_id,
        ring_size=reference.ring_size,
        status=RingBoundaryStatus.RESOLVED,
        message="Resolved atom-resolved structural ring boundary.",
        center_kind=options.center_kind,
        center_coordinates=tuple(float(v) for v in current.oxygen_area_centroid),
        center_uncertainty=0.0,
        cyclic_origin_atom=reference.o_atom_refs[0],
        orientation=1,
        reversal_origin_index=0,
        t_atoms=t_atoms,
        o_atoms=o_atoms,
        cyclic_spectra=tuple(cyclic),
        boundary_moments=tuple(moments),
        physical_angle_fits=tuple(fits),
        oxygen_class_splits=splits,
        maximum_oxygen_class_radial_split=maximum_split,
        oxygen_radial_symmetry_breaking=breaking,
        dominant_oxygen_radial_mode=dominant,
        angular_coordinate_defined=angular_defined,
        minimum_projected_radius=float(minimum_radius),
        phase_continuity=continuity,
    )


def build_structural_ring_boundary_catalog(
    reference_geometry: ReferenceRingGeometryCatalog,
    frame_geometry: FrameRingGeometryCatalog,
    collection: AtomisticFrameCollection,
    *,
    alias_profile: LtaOxygenAliasProfile | None = None,
    options: RingBoundaryOptions | None = None,
    resources: RingBoundaryResources | None = None,
) -> StructuralRingBoundaryCatalog:
    """Build the Stage-11C3 structural boundary catalog transactionally."""

    if not isinstance(reference_geometry, ReferenceRingGeometryCatalog):
        raise RingBoundaryInputError("reference_geometry has the wrong type.")
    if not isinstance(frame_geometry, FrameRingGeometryCatalog):
        raise RingBoundaryInputError("frame_geometry has the wrong type.")
    if not isinstance(collection, AtomisticFrameCollection):
        raise RingBoundaryInputError("collection has the wrong type.")
    if frame_geometry.reference_ring_geometry_digest != reference_geometry.digest:
        raise RingBoundaryInvariantError("Frame-ring geometry is not bound to the supplied reference-ring geometry.")
    active_options = RingBoundaryOptions() if options is None else options
    active_resources = RingBoundaryResources() if resources is None else resources
    if len(reference_geometry.rings) > active_resources.max_rings:
        raise RingBoundaryResourceError("Ring count exceeds max_rings before descriptor construction.")
    if len(frame_geometry.frames) > active_resources.max_frames:
        raise RingBoundaryResourceError("Frame count exceeds max_frames before descriptor construction.")
    atom_records = 2 * sum(ring.ring_size for ring in reference_geometry.rings if ring.resolved) * (1 + len(frame_geometry.frames))
    if atom_records > active_resources.max_atom_records:
        raise RingBoundaryResourceError("Predicted atom-record count exceeds max_atom_records before allocation.")
    alias_status, aliases = _validate_alias_profile(alias_profile, reference_geometry, collection)
    reference_boundaries = tuple(
        _build_boundary(
            ring, ring, collection, aliases, active_options, None, RingBoundaryStatus.REFERENCE_UNRESOLVED
        )
        for ring in reference_geometry.rings
    )
    frames: list[StructuralRingBoundaryFrame] = []
    for source_frame in frame_geometry.frames:
        boundaries = tuple(
            _build_boundary(
                reference_geometry.rings[index],
                current,
                collection,
                aliases,
                active_options,
                reference_boundaries[index],
                RingBoundaryStatus.FRAME_UNRESOLVED,
            )
            for index, current in enumerate(source_frame.rings)
        )
        frames.append(
            StructuralRingBoundaryFrame(
                result_position=source_frame.result_position,
                collection_frame_index=source_frame.collection_frame_index,
                frame_id=source_frame.frame_id,
                boundaries=boundaries,
            )
        )
    return StructuralRingBoundaryCatalog(
        reference_ring_geometry_digest=reference_geometry.digest,
        frame_ring_geometry_digest=frame_geometry.digest,
        collection_chemistry_digest=_chemistry_digest(collection),
        alias_validation_status=alias_status,
        alias_profile=alias_profile,
        options=active_options,
        resources=active_resources,
        reference_boundaries=reference_boundaries,
        frames=tuple(frames),
    )


__all__ = [
    "AliasValidationStatus",
    "BoundaryMeasureAngularMoments",
    "CANONICAL_RING_BOUNDARY_SCHEMA",
    "HarmonicFitStatus",
    "HarmonicMode",
    "LtaOxygenAliasProfile",
    "OxygenClassSplit",
    "PhaseContinuityDiagnostic",
    "PhysicalAngleHarmonicFit",
    "RING_BOUNDARY_DIGEST_ALGORITHM",
    "RingBoundaryAliasError",
    "RingBoundaryError",
    "RingBoundaryInputError",
    "RingBoundaryInvariantError",
    "RingBoundaryOptions",
    "RingBoundaryResourceError",
    "RingBoundaryResources",
    "RingBoundarySerializationError",
    "RingBoundaryStatus",
    "RingBoundaryAtomRecord",
    "StructuralRingBoundary",
    "StructuralRingBoundaryCatalog",
    "StructuralRingBoundaryFrame",
    "UnweightedCyclicIndexSpectrum",
    "apply_cyclic_dihedral_gauge",
    "build_structural_ring_boundary_catalog",
    "compute_boundary_measure_angular_moments",
    "compute_unweighted_cyclic_index_spectrum",
    "fit_physical_angle_harmonics",
    "transform_cyclic_coefficient",
]
