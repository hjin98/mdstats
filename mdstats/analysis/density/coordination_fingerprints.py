"""Stage-11E5a species-dependent coordination fingerprints and classification.

The authoritative record is the exact state-conditioned physical M--O/M--T
sample matrix in the persistent structural gauge.  Fourier coefficients,
actual-angle fits, locking scores, and structural classes are derived and
inspectable diagnostics; none replaces the exact distances or direct local ion
coordinates.

The equal-index DFT, weighted angular moments, least-squares trigonometric fit,
and circular resultant are standard background.  The source binding,
centered-reference residual, geometry-forward check, occupancy-mixture status,
and conservative classification lattice are mdstats-specific constructions.
"""

from __future__ import annotations

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

from ...collection import AtomisticFrameCollection
from .._neighbors import minimum_image_geometry
from ..registered_structural_view import (
    RegisteredRingViewStatus,
    RegisteredStructuralGeometryView,
)
from ..site_samples import FrameworkAlignedIonSampleCatalog
from .evidence_validation import (
    StructuralAssociationStatus,
    StructuralObjectKind,
    ValidatedFrozenCatalog,
)
from .temporal_assignment import (
    ProvisionalTemporalAssignmentCatalog,
    RawMembershipClass,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

COORDINATION_FINGERPRINT_STAGE = "11E5a"
COORDINATION_FINGERPRINT_OPTIONS_SCHEMA = "mdstats.coordination-fingerprint-options.v1"
COORDINATION_FINGERPRINT_RESOURCES_SCHEMA = "mdstats.coordination-fingerprint-resources.v1"
COORDINATION_HARMONIC_SCHEMA = "mdstats.coordination-harmonic.v1"
COORDINATION_SPECTRUM_SCHEMA = "mdstats.coordination-spectrum.v1"
OCCUPANCY_CONTEXT_FINGERPRINT_SCHEMA = "mdstats.occupancy-context-fingerprint.v1"
COORDINATION_CLASSIFICATION_EVIDENCE_SCHEMA = "mdstats.coordination-classification-evidence.v1"
STATE_COORDINATION_FINGERPRINT_SCHEMA = "mdstats.state-coordination-fingerprint.v1"
COORDINATION_FINGERPRINT_CATALOG_SCHEMA = "mdstats.coordination-fingerprint-catalog.v1"


class CoordinationFingerprintError(ValueError):
    """Base Stage-11E5a error."""


class CoordinationFingerprintInputError(CoordinationFingerprintError):
    """Raised when source contracts or sample geometry are inconsistent."""


class CoordinationFingerprintResourceError(CoordinationFingerprintError):
    """Raised before declared E5a resource limits are exceeded."""


class CoordinationFingerprintSerializationError(CoordinationFingerprintError):
    """Raised for malformed or tampered serialized records."""


class CoordinationFingerprintStatus(str, Enum):
    RESOLVED = "resolved"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    STRUCTURAL_ASSOCIATION_UNRESOLVED = "structural_association_unresolved"
    STRUCTURAL_OBJECT_UNSUPPORTED = "structural_object_unsupported"
    FRAME_GEOMETRY_UNRESOLVED = "frame_geometry_unresolved"


class CoordinationStructuralClass(str, Enum):
    POINT = "point"
    BILATERAL = "bilateral"
    DISCRETE_OFF_CENTER = "discrete_off_center"
    SMOOTH_ANNULAR = "smooth_annular"
    CORRUGATED_ANNULAR = "corrugated_annular"
    CAGE = "cage"
    GENERAL = "general"
    AMBIGUOUS = "classification_ambiguous"


class OccupancyMixtureStatus(str, Enum):
    NOT_PROVIDED = "not_provided"
    INSUFFICIENT = "insufficient"
    CONSISTENT = "consistent"
    RESOLVED_MIXTURE = "resolved_mixture"


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
    text = str(value)
    if len(text) != 64:
        raise CoordinationFingerprintInputError(f"{name} must be a SHA-256 digest.")
    return text


def _positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise CoordinationFingerprintInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise CoordinationFingerprintInputError(f"{name} must be finite and nonnegative.")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise CoordinationFingerprintInputError(f"{name} must be a positive integer.")
    return int(value)


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise CoordinationFingerprintInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise CoordinationFingerprintInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise CoordinationFingerprintInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise CoordinationFingerprintInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _wrap_angle(value: float) -> float:
    return float((value + math.pi) % (2.0 * math.pi) - math.pi)


def _circular_resultant(angles: np.ndarray, weights: np.ndarray) -> tuple[float | None, float]:
    if angles.size == 0 or float(np.sum(weights)) <= 0.0:
        return None, 0.0
    z = np.sum(weights * np.exp(1j * angles)) / np.sum(weights)
    return float(math.atan2(z.imag, z.real)), float(abs(z))


def _arc_voronoi_weights(points: np.ndarray) -> np.ndarray:
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 2:
        raise CoordinationFingerprintInputError("Boundary points must have shape (k, 3), k>=2.")
    edges = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    if np.any(edges <= np.finfo(float).eps):
        raise CoordinationFingerprintInputError("Coincident ordered boundary atoms are not admissible.")
    return 0.5 * (np.roll(edges, 1) + edges)


def _collection_binding_digest(collection: AtomisticFrameCollection) -> str:
    payload = {
        "frame_semantics": collection.frame_semantics.value,
        "frame_ids": _array_digest(collection.frame_ids),
        "atomic_numbers": _array_digest(collection.atomic_numbers),
        "pbc": _array_digest(collection.pbc),
        "cells": _array_digest(collection.cells),
        "origins": _array_digest(collection.origins),
        "fractional_positions": _array_digest(collection.fractional_positions),
    }
    return _digest(payload)


@dataclass(frozen=True, slots=True)
class CoordinationFingerprintOptions:
    minimum_samples: int = 4
    maximum_harmonic_mode: int = 4
    phase_amplitude_tolerance: float = 1.0e-8
    angular_radius_tolerance: float = 1.0e-8
    maximum_condition_number: float = 1.0e10
    regularization: float = 0.0
    centered_offcenter_threshold: float = 0.15
    phase_stability_threshold: float = 0.65
    annularity_threshold: float = 0.55
    corrugation_threshold: float = 0.20
    bilateral_balance_threshold: float = 0.55
    occupancy_minimum_samples: int = 3
    occupancy_center_shift_threshold: float = 0.15
    occupancy_phase_shift_threshold: float = math.pi / 3.0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        minimum = _positive_int(self.minimum_samples, "minimum_samples")
        maximum_mode = _positive_int(self.maximum_harmonic_mode, "maximum_harmonic_mode")
        occupancy_minimum = _positive_int(self.occupancy_minimum_samples, "occupancy_minimum_samples")
        values = {
            "phase_amplitude_tolerance": _positive(self.phase_amplitude_tolerance, "phase_amplitude_tolerance"),
            "angular_radius_tolerance": _positive(self.angular_radius_tolerance, "angular_radius_tolerance"),
            "maximum_condition_number": _positive(self.maximum_condition_number, "maximum_condition_number"),
            "regularization": _nonnegative(self.regularization, "regularization"),
            "centered_offcenter_threshold": _positive(self.centered_offcenter_threshold, "centered_offcenter_threshold"),
            "phase_stability_threshold": _nonnegative(self.phase_stability_threshold, "phase_stability_threshold"),
            "annularity_threshold": _nonnegative(self.annularity_threshold, "annularity_threshold"),
            "corrugation_threshold": _nonnegative(self.corrugation_threshold, "corrugation_threshold"),
            "bilateral_balance_threshold": _nonnegative(self.bilateral_balance_threshold, "bilateral_balance_threshold"),
            "occupancy_center_shift_threshold": _positive(self.occupancy_center_shift_threshold, "occupancy_center_shift_threshold"),
            "occupancy_phase_shift_threshold": _positive(self.occupancy_phase_shift_threshold, "occupancy_phase_shift_threshold"),
        }
        for name in ("phase_stability_threshold", "annularity_threshold", "corrugation_threshold", "bilateral_balance_threshold"):
            if values[name] > 1.0:
                raise CoordinationFingerprintInputError(f"{name} must not exceed one.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": COORDINATION_FINGERPRINT_OPTIONS_SCHEMA, "minimum_samples": minimum,
                   "maximum_harmonic_mode": maximum_mode, "occupancy_minimum_samples": occupancy_minimum,
                   **values, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise CoordinationFingerprintInputError("Coordination options signature is inconsistent.")
        object.__setattr__(self, "minimum_samples", minimum)
        object.__setattr__(self, "maximum_harmonic_mode", maximum_mode)
        object.__setattr__(self, "occupancy_minimum_samples", occupancy_minimum)
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", metadata); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_FINGERPRINT_OPTIONS_SCHEMA,
                **{name: getattr(self, name) for name in (
                    "minimum_samples", "maximum_harmonic_mode", "phase_amplitude_tolerance",
                    "angular_radius_tolerance", "maximum_condition_number", "regularization",
                    "centered_offcenter_threshold", "phase_stability_threshold", "annularity_threshold",
                    "corrugation_threshold", "bilateral_balance_threshold", "occupancy_minimum_samples",
                    "occupancy_center_shift_threshold", "occupancy_phase_shift_threshold")},
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationFingerprintOptions":
        if p.get("schema") != COORDINATION_FINGERPRINT_OPTIONS_SCHEMA:
            raise CoordinationFingerprintSerializationError("Unsupported coordination-options schema.")
        keys = ("minimum_samples", "maximum_harmonic_mode", "phase_amplitude_tolerance", "angular_radius_tolerance",
                "maximum_condition_number", "regularization", "centered_offcenter_threshold", "phase_stability_threshold",
                "annularity_threshold", "corrugation_threshold", "bilateral_balance_threshold", "occupancy_minimum_samples",
                "occupancy_center_shift_threshold", "occupancy_phase_shift_threshold")
        return cls(**{k: p[k] for k in keys}, metadata=p.get("metadata", {}), signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CoordinationFingerprintResourcePolicy:
    max_states: int = 100_000
    max_associations: int = 1_000_000
    max_sample_distance_values: int = 100_000_000
    max_occupancy_groups: int = 1_000_000
    max_serialized_records: int = 20_000_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_states", "max_associations", "max_sample_distance_values", "max_occupancy_groups", "max_serialized_records")}
        expected = _digest({"schema": COORDINATION_FINGERPRINT_RESOURCES_SCHEMA, **values})
        if self.signature and self.signature != expected:
            raise CoordinationFingerprintInputError("Coordination resources signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_FINGERPRINT_RESOURCES_SCHEMA,
                **{name: getattr(self, name) for name in ("max_states", "max_associations", "max_sample_distance_values", "max_occupancy_groups", "max_serialized_records")},
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationFingerprintResourcePolicy":
        if p.get("schema") != COORDINATION_FINGERPRINT_RESOURCES_SCHEMA:
            raise CoordinationFingerprintSerializationError("Unsupported coordination-resources schema.")
        return cls(**{name: int(p[name]) for name in ("max_states", "max_associations", "max_sample_distance_values", "max_occupancy_groups", "max_serialized_records")}, signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CoordinationHarmonic:
    mode: int
    coefficient_real: float
    coefficient_imag: float
    amplitude: float
    normalized_amplitude: float | None
    phase: float | None
    phase_defined: bool
    signature: str = ""

    def __post_init__(self) -> None:
        mode = int(self.mode)
        if mode < 0: raise CoordinationFingerprintInputError("mode must be nonnegative.")
        real = float(self.coefficient_real); imag = float(self.coefficient_imag); amplitude = _nonnegative(self.amplitude, "amplitude")
        if not np.isfinite(real) or not np.isfinite(imag): raise CoordinationFingerprintInputError("Harmonic coefficient is non-finite.")
        normalized = None if self.normalized_amplitude is None else _nonnegative(self.normalized_amplitude, "normalized_amplitude")
        phase = None if self.phase is None else float(self.phase)
        if self.phase_defined and (phase is None or not np.isfinite(phase)):
            raise CoordinationFingerprintInputError("Resolved phase requires a finite value.")
        if not self.phase_defined and phase is not None:
            raise CoordinationFingerprintInputError("Undefined phase must be None.")
        payload = {"schema": COORDINATION_HARMONIC_SCHEMA, "mode": mode, "coefficient_real": real,
                   "coefficient_imag": imag, "amplitude": amplitude, "normalized_amplitude": normalized,
                   "phase": phase, "phase_defined": bool(self.phase_defined)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("Harmonic signature is inconsistent.")
        for name, value in (("mode", mode), ("coefficient_real", real), ("coefficient_imag", imag), ("amplitude", amplitude),
                            ("normalized_amplitude", normalized), ("phase", phase), ("phase_defined", bool(self.phase_defined)), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_HARMONIC_SCHEMA, "mode": self.mode, "coefficient_real": self.coefficient_real,
                "coefficient_imag": self.coefficient_imag, "amplitude": self.amplitude,
                "normalized_amplitude": self.normalized_amplitude, "phase": self.phase,
                "phase_defined": self.phase_defined, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationHarmonic":
        if p.get("schema") != COORDINATION_HARMONIC_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported harmonic schema.")
        return cls(int(p["mode"]), float(p["coefficient_real"]), float(p["coefficient_imag"]), float(p["amplitude"]),
                   p.get("normalized_amplitude"), p.get("phase"), bool(p["phase_defined"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CoordinationSpectrum:
    sequence_name: str
    measure: str
    values: tuple[float, ...]
    angles: tuple[float, ...]
    weights: tuple[float, ...]
    harmonics: tuple[CoordinationHarmonic, ...]
    fit_rank: int | None = None
    parameter_count: int | None = None
    condition_number: float | None = None
    residual_rms: float | None = None
    diagnostic_only: bool = True
    signature: str = ""

    def __post_init__(self) -> None:
        name = str(self.sequence_name); measure = str(self.measure)
        values = tuple(float(v) for v in self.values); angles = tuple(float(v) for v in self.angles); weights = tuple(float(v) for v in self.weights)
        if not name or not measure or not values or any(not np.isfinite(v) for v in values):
            raise CoordinationFingerprintInputError("Invalid coordination spectrum identity or values.")
        if angles and len(angles) != len(values): raise CoordinationFingerprintInputError("Spectrum angles must align with values.")
        if weights and (len(weights) != len(values) or any(v <= 0 or not np.isfinite(v) for v in weights)):
            raise CoordinationFingerprintInputError("Spectrum weights must be positive and aligned.")
        harmonics = tuple(self.harmonics)
        if tuple(v.mode for v in harmonics) != tuple(sorted(v.mode for v in harmonics)):
            raise CoordinationFingerprintInputError("Spectrum harmonics must be mode ordered.")
        rank = None if self.fit_rank is None else int(self.fit_rank); count = None if self.parameter_count is None else int(self.parameter_count)
        condition = None if self.condition_number is None else _nonnegative(self.condition_number, "condition_number")
        residual = None if self.residual_rms is None else _nonnegative(self.residual_rms, "residual_rms")
        payload = {"schema": COORDINATION_SPECTRUM_SCHEMA, "sequence_name": name, "measure": measure,
                   "values": list(values), "angles": list(angles), "weights": list(weights),
                   "harmonic_signatures": [v.signature for v in harmonics], "fit_rank": rank,
                   "parameter_count": count, "condition_number": condition, "residual_rms": residual,
                   "diagnostic_only": bool(self.diagnostic_only)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("Spectrum signature is inconsistent.")
        for n, v in (("sequence_name", name), ("measure", measure), ("values", values), ("angles", angles), ("weights", weights),
                     ("harmonics", harmonics), ("fit_rank", rank), ("parameter_count", count), ("condition_number", condition),
                     ("residual_rms", residual), ("diagnostic_only", bool(self.diagnostic_only)), ("signature", expected)):
            object.__setattr__(self, n, v)

    def mode(self, mode: int) -> CoordinationHarmonic:
        matches = [v for v in self.harmonics if v.mode == int(mode)]
        if len(matches) != 1: raise CoordinationFingerprintInputError(f"Spectrum has no unique mode {mode}.")
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_SPECTRUM_SCHEMA, "sequence_name": self.sequence_name, "measure": self.measure,
                "values": list(self.values), "angles": list(self.angles), "weights": list(self.weights),
                "harmonics": [v.to_dict() for v in self.harmonics], "fit_rank": self.fit_rank,
                "parameter_count": self.parameter_count, "condition_number": self.condition_number,
                "residual_rms": self.residual_rms, "diagnostic_only": self.diagnostic_only, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationSpectrum":
        if p.get("schema") != COORDINATION_SPECTRUM_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported spectrum schema.")
        return cls(str(p["sequence_name"]), str(p["measure"]), tuple(p["values"]), tuple(p.get("angles", ())),
                   tuple(p.get("weights", ())), tuple(CoordinationHarmonic.from_dict(v) for v in p["harmonics"]),
                   p.get("fit_rank"), p.get("parameter_count"), p.get("condition_number"), p.get("residual_rms"),
                   bool(p.get("diagnostic_only", True)), str(p.get("signature", "")))


def _dft_spectrum(values: np.ndarray, name: str, tolerance: float) -> CoordinationSpectrum:
    coeff = np.fft.fft(values) / values.size
    scale = max(abs(float(coeff[0].real)), np.finfo(float).eps)
    modes = []
    for mode in range(values.size // 2 + 1):
        c = complex(coeff[mode]); amp = abs(c)
        nyquist = values.size % 2 == 0 and mode == values.size // 2
        defined = bool(mode > 0 and not nyquist and amp > tolerance * max(1.0, abs(coeff[0])))
        modes.append(CoordinationHarmonic(mode, float(c.real), float(c.imag), float(amp), float(amp / scale),
                                          float(math.atan2(c.imag, c.real)) if defined else None, defined))
    return CoordinationSpectrum(name, "equal_atom_unweighted_dft", tuple(float(v) for v in values), (), (), tuple(modes))


def _angular_spectrum(values: np.ndarray, angles: np.ndarray, weights: np.ndarray, name: str, maximum_mode: int,
                      tolerance: float, maximum_condition_number: float, regularization: float) -> tuple[CoordinationSpectrum, CoordinationSpectrum]:
    scale = max(abs(float(np.sum(weights * values) / np.sum(weights))), np.finfo(float).eps)
    modes: list[CoordinationHarmonic] = []
    for mode in range(1, maximum_mode + 1):
        c = complex(np.sum(weights * values * np.exp(-1j * mode * angles)) / np.sum(weights)); amp = abs(c)
        defined = bool(amp > tolerance * max(1.0, scale))
        modes.append(CoordinationHarmonic(mode, float(c.real), float(c.imag), float(amp), float(amp / scale),
                                          float(math.atan2(c.imag, c.real)) if defined else None, defined))
    moments = CoordinationSpectrum(name, "boundary_measure_angular_moment", tuple(float(v) for v in values),
                                   tuple(float(v) for v in angles), tuple(float(v) for v in weights), tuple(modes))
    columns = [np.ones_like(angles)]
    for mode in range(1, maximum_mode + 1):
        columns.extend((np.cos(mode * angles), np.sin(mode * angles)))
    design = np.column_stack(columns); root = np.sqrt(weights / np.sum(weights)); a = design * root[:, None]; y = values * root
    if regularization > 0.0:
        reg = math.sqrt(regularization) * np.eye(design.shape[1]); reg[0, 0] = 0.0
        a_fit = np.vstack((a, reg)); y_fit = np.concatenate((y, np.zeros(design.shape[1])))
    else:
        a_fit, y_fit = a, y
    rank = int(np.linalg.matrix_rank(a)); singular = np.linalg.svd(a, compute_uv=False)
    condition = math.inf if singular[-1] <= np.finfo(float).eps else float(singular[0] / singular[-1])
    fit_modes: list[CoordinationHarmonic] = []; residual = None
    if rank == design.shape[1] and condition <= maximum_condition_number:
        beta, *_ = np.linalg.lstsq(a_fit, y_fit, rcond=None); predicted = design @ beta
        residual = float(np.sqrt(np.sum(weights * (values - predicted) ** 2) / np.sum(weights)))
        for mode in range(1, maximum_mode + 1):
            cos_c = float(beta[2 * mode - 1]); sin_c = float(beta[2 * mode]); c = complex(cos_c, -sin_c); amp = abs(c)
            defined = bool(amp > tolerance * max(1.0, abs(float(beta[0]))))
            fit_modes.append(CoordinationHarmonic(mode, float(c.real), float(c.imag), float(amp), float(amp / scale),
                                                  float(math.atan2(c.imag, c.real)) if defined else None, defined))
    fit = CoordinationSpectrum(name, "rank_safe_actual_angle_least_squares", tuple(float(v) for v in values),
                               tuple(float(v) for v in angles), tuple(float(v) for v in weights), tuple(fit_modes),
                               rank, int(design.shape[1]), None if not np.isfinite(condition) else condition, residual)
    return moments, fit


@dataclass(frozen=True, slots=True)
class OccupancyContextFingerprint:
    label: str
    sample_count: int
    represented_time: float
    mean_local_coordinates: tuple[float, float, float]
    covariance_trace: float
    mean_radial_offset: float
    circular_phase: float | None
    phase_resultant: float
    signature: str = ""

    def __post_init__(self) -> None:
        label = str(self.label); count = _positive_int(self.sample_count, "sample_count"); time = _positive(self.represented_time, "represented_time")
        local = tuple(float(v) for v in self.mean_local_coordinates)
        if len(local) != 3 or any(not np.isfinite(v) for v in local): raise CoordinationFingerprintInputError("Invalid context mean coordinates.")
        covariance = _nonnegative(self.covariance_trace, "covariance_trace"); radial = _nonnegative(self.mean_radial_offset, "mean_radial_offset")
        phase = None if self.circular_phase is None else float(self.circular_phase); resultant = _nonnegative(self.phase_resultant, "phase_resultant")
        if resultant > 1.0 + 1e-12 or (phase is not None and not np.isfinite(phase)): raise CoordinationFingerprintInputError("Invalid context circular statistic.")
        payload = {"schema": OCCUPANCY_CONTEXT_FINGERPRINT_SCHEMA, "label": label, "sample_count": count,
                   "represented_time": time, "mean_local_coordinates": list(local), "covariance_trace": covariance,
                   "mean_radial_offset": radial, "circular_phase": phase, "phase_resultant": resultant}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("Context fingerprint signature is inconsistent.")
        for n, v in (("label", label), ("sample_count", count), ("represented_time", time), ("mean_local_coordinates", local),
                     ("covariance_trace", covariance), ("mean_radial_offset", radial), ("circular_phase", phase),
                     ("phase_resultant", resultant), ("signature", expected)): object.__setattr__(self, n, v)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": OCCUPANCY_CONTEXT_FINGERPRINT_SCHEMA, "label": self.label, "sample_count": self.sample_count,
                "represented_time": self.represented_time, "mean_local_coordinates": list(self.mean_local_coordinates),
                "covariance_trace": self.covariance_trace, "mean_radial_offset": self.mean_radial_offset,
                "circular_phase": self.circular_phase, "phase_resultant": self.phase_resultant, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "OccupancyContextFingerprint":
        if p.get("schema") != OCCUPANCY_CONTEXT_FINGERPRINT_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported occupancy-context schema.")
        return cls(str(p["label"]), int(p["sample_count"]), float(p["represented_time"]), tuple(p["mean_local_coordinates"]),
                   float(p["covariance_trace"]), float(p["mean_radial_offset"]), p.get("circular_phase"),
                   float(p["phase_resultant"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CoordinationClassificationEvidence:
    structural_class: CoordinationStructuralClass
    direct_mean_radial_offset: float
    direct_mean_normal_offset: float
    direct_radial_std: float
    phase_resultant: float
    phase_resolved: bool
    oxygen_locking_score: float
    gap_locking_score: float
    sector_locking_score: float
    opposite_side_partner_score: float
    annularity_score: float
    corrugation_score: float
    geometry_explained_fraction: float
    forward_model_residual_rms: float
    occupancy_mixture_status: OccupancyMixtureStatus
    diagnostics: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        cls = CoordinationStructuralClass(self.structural_class); mixture = OccupancyMixtureStatus(self.occupancy_mixture_status)
        nonneg = {name: _nonnegative(getattr(self, name), name) for name in (
            "direct_mean_radial_offset", "direct_radial_std", "phase_resultant", "oxygen_locking_score", "gap_locking_score",
            "sector_locking_score", "opposite_side_partner_score", "annularity_score", "corrugation_score",
            "geometry_explained_fraction", "forward_model_residual_rms")}
        normal = float(self.direct_mean_normal_offset)
        if not np.isfinite(normal): raise CoordinationFingerprintInputError("direct_mean_normal_offset is non-finite.")
        for name in ("phase_resultant", "oxygen_locking_score", "gap_locking_score", "sector_locking_score",
                     "opposite_side_partner_score", "annularity_score", "corrugation_score", "geometry_explained_fraction"):
            if nonneg[name] > 1.0 + 1e-12: raise CoordinationFingerprintInputError(f"{name} must not exceed one.")
        diagnostics = tuple(str(v) for v in self.diagnostics)
        payload = {"schema": COORDINATION_CLASSIFICATION_EVIDENCE_SCHEMA, "structural_class": cls.value,
                   **nonneg, "direct_mean_normal_offset": normal, "phase_resolved": bool(self.phase_resolved),
                   "occupancy_mixture_status": mixture.value, "diagnostics": list(diagnostics)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("Classification signature is inconsistent.")
        object.__setattr__(self, "structural_class", cls); object.__setattr__(self, "occupancy_mixture_status", mixture)
        object.__setattr__(self, "direct_mean_normal_offset", normal); object.__setattr__(self, "phase_resolved", bool(self.phase_resolved))
        for n, v in nonneg.items(): object.__setattr__(self, n, min(1.0, v) if n not in {"direct_mean_radial_offset", "direct_radial_std", "forward_model_residual_rms"} else v)
        object.__setattr__(self, "diagnostics", diagnostics); object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_CLASSIFICATION_EVIDENCE_SCHEMA, "structural_class": self.structural_class.value,
                **{name: getattr(self, name) for name in ("direct_mean_radial_offset", "direct_mean_normal_offset",
                    "direct_radial_std", "phase_resultant", "phase_resolved", "oxygen_locking_score", "gap_locking_score",
                    "sector_locking_score", "opposite_side_partner_score", "annularity_score", "corrugation_score",
                    "geometry_explained_fraction", "forward_model_residual_rms")},
                "occupancy_mixture_status": self.occupancy_mixture_status.value, "diagnostics": list(self.diagnostics), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationClassificationEvidence":
        if p.get("schema") != COORDINATION_CLASSIFICATION_EVIDENCE_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported classification schema.")
        return cls(CoordinationStructuralClass(p["structural_class"]), float(p["direct_mean_radial_offset"]),
                   float(p["direct_mean_normal_offset"]), float(p["direct_radial_std"]), float(p["phase_resultant"]),
                   bool(p["phase_resolved"]), float(p["oxygen_locking_score"]), float(p["gap_locking_score"]),
                   float(p["sector_locking_score"]), float(p["opposite_side_partner_score"]), float(p["annularity_score"]),
                   float(p["corrugation_score"]), float(p["geometry_explained_fraction"]), float(p["forward_model_residual_rms"]),
                   OccupancyMixtureStatus(p["occupancy_mixture_status"]), tuple(p.get("diagnostics", ())), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StateCoordinationFingerprint:
    state_id: int
    candidate_index: int
    status: CoordinationFingerprintStatus
    structural_object_kind: StructuralObjectKind
    persistent_identity: str
    sample_indices: IntArray
    frame_indices: IntArray
    ion_atom_indices: IntArray
    represented_time_weights: FloatArray
    local_coordinates: FloatArray
    mo_distances: FloatArray
    mt_distances: FloatArray
    centered_reference_mo_distances: FloatArray
    geometry_predicted_mo_distances: FloatArray
    oxygen_atom_indices: tuple[int, ...]
    oxygen_image_shifts: tuple[tuple[int, int, int], ...]
    oxygen_environment_signatures: tuple[str | None, ...]
    oxygen_aliases: tuple[str | None, ...]
    t_atom_indices: tuple[int, ...]
    t_image_shifts: tuple[tuple[int, int, int], ...]
    spectra: tuple[CoordinationSpectrum, ...]
    occupancy_contexts: tuple[OccupancyContextFingerprint, ...]
    classification: CoordinationClassificationEvidence | None
    message: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        sid = int(self.state_id); candidate = int(self.candidate_index)
        if min(sid, candidate) < 0: raise CoordinationFingerprintInputError("State and candidate indices must be nonnegative.")
        status = CoordinationFingerprintStatus(self.status); kind = StructuralObjectKind(self.structural_object_kind); identity = str(self.persistent_identity)
        if not identity: raise CoordinationFingerprintInputError("persistent_identity must be nonempty.")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        n = samples.size
        frames = _readonly(self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices", shape=(n,))
        ions = _readonly(self.ion_atom_indices, dtype=np.int64, ndim=1, name="ion_atom_indices", shape=(n,))
        weights = _readonly(self.represented_time_weights, dtype=np.float64, ndim=1, name="represented_time_weights", shape=(n,))
        local = _readonly(self.local_coordinates, dtype=np.float64, ndim=2, name="local_coordinates", shape=(n, 3))
        mo = _readonly(self.mo_distances, dtype=np.float64, ndim=2, name="mo_distances")
        mt = _readonly(self.mt_distances, dtype=np.float64, ndim=2, name="mt_distances")
        centered = _readonly(self.centered_reference_mo_distances, dtype=np.float64, ndim=2, name="centered_reference_mo_distances", shape=mo.shape)
        predicted = _readonly(self.geometry_predicted_mo_distances, dtype=np.float64, ndim=2, name="geometry_predicted_mo_distances", shape=mo.shape)
        if mo.shape[0] != n or mt.shape[0] != n or np.any(mo <= 0) or np.any(mt <= 0) or np.any(centered <= 0) or np.any(predicted <= 0):
            raise CoordinationFingerprintInputError("Distance matrices must be positive and sample aligned.")
        o_indices = tuple(int(v) for v in self.oxygen_atom_indices); t_indices = tuple(int(v) for v in self.t_atom_indices)
        o_shifts = tuple(tuple(int(x) for x in v) for v in self.oxygen_image_shifts); t_shifts = tuple(tuple(int(x) for x in v) for v in self.t_image_shifts)
        o_env = tuple(None if v is None else str(v) for v in self.oxygen_environment_signatures); aliases = tuple(None if v is None else str(v) for v in self.oxygen_aliases)
        if mo.shape[1] != len(o_indices) or mt.shape[1] != len(t_indices) or len(o_shifts) != len(o_indices) or len(o_env) != len(o_indices) or len(aliases) != len(o_indices) or len(t_shifts) != len(t_indices):
            raise CoordinationFingerprintInputError("Persistent structural identities do not align with distance matrices.")
        spectra = tuple(self.spectra); contexts = tuple(self.occupancy_contexts)
        if status is CoordinationFingerprintStatus.RESOLVED:
            if n == 0 or self.classification is None: raise CoordinationFingerprintInputError("Resolved fingerprints require samples and classification.")
        elif self.classification is not None:
            raise CoordinationFingerprintInputError("Unresolved fingerprints cannot carry a classification.")
        payload = {"schema": STATE_COORDINATION_FINGERPRINT_SCHEMA, "state_id": sid, "candidate_index": candidate,
                   "status": status.value, "structural_object_kind": kind.value, "persistent_identity": identity,
                   "sample_indices": _array_digest(samples), "frame_indices": _array_digest(frames), "ion_atom_indices": _array_digest(ions),
                   "weights": _array_digest(weights), "local_coordinates": _array_digest(local), "mo_distances": _array_digest(mo),
                   "mt_distances": _array_digest(mt), "centered_mo": _array_digest(centered), "predicted_mo": _array_digest(predicted),
                   "oxygen_atom_indices": list(o_indices), "oxygen_image_shifts": [list(v) for v in o_shifts],
                   "oxygen_environment_signatures": list(o_env), "oxygen_aliases": list(aliases),
                   "t_atom_indices": list(t_indices), "t_image_shifts": [list(v) for v in t_shifts],
                   "spectrum_signatures": [v.signature for v in spectra], "context_signatures": [v.signature for v in contexts],
                   "classification_signature": None if self.classification is None else self.classification.signature, "message": str(self.message)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("State fingerprint signature is inconsistent.")
        for name, value in (("state_id", sid), ("candidate_index", candidate), ("status", status), ("structural_object_kind", kind),
                            ("persistent_identity", identity), ("sample_indices", samples), ("frame_indices", frames), ("ion_atom_indices", ions),
                            ("represented_time_weights", weights), ("local_coordinates", local), ("mo_distances", mo), ("mt_distances", mt),
                            ("centered_reference_mo_distances", centered), ("geometry_predicted_mo_distances", predicted),
                            ("oxygen_atom_indices", o_indices), ("oxygen_image_shifts", o_shifts), ("oxygen_environment_signatures", o_env),
                            ("oxygen_aliases", aliases), ("t_atom_indices", t_indices), ("t_image_shifts", t_shifts), ("spectra", spectra),
                            ("occupancy_contexts", contexts), ("message", str(self.message)), ("signature", expected)):
            object.__setattr__(self, name, value)

    def spectrum(self, name: str, measure: str = "equal_atom_unweighted_dft") -> CoordinationSpectrum:
        matches = [v for v in self.spectra if v.sequence_name == name and v.measure == measure]
        if len(matches) != 1: raise CoordinationFingerprintInputError(f"Expected one spectrum {name!r}/{measure!r}.")
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STATE_COORDINATION_FINGERPRINT_SCHEMA, "state_id": self.state_id, "candidate_index": self.candidate_index,
                "status": self.status.value, "structural_object_kind": self.structural_object_kind.value,
                "persistent_identity": self.persistent_identity, "sample_indices": self.sample_indices.tolist(),
                "frame_indices": self.frame_indices.tolist(), "ion_atom_indices": self.ion_atom_indices.tolist(),
                "represented_time_weights": self.represented_time_weights.tolist(), "local_coordinates": self.local_coordinates.tolist(),
                "mo_distances": self.mo_distances.tolist(), "mt_distances": self.mt_distances.tolist(),
                "centered_reference_mo_distances": self.centered_reference_mo_distances.tolist(),
                "geometry_predicted_mo_distances": self.geometry_predicted_mo_distances.tolist(),
                "oxygen_atom_indices": list(self.oxygen_atom_indices), "oxygen_image_shifts": [list(v) for v in self.oxygen_image_shifts],
                "oxygen_environment_signatures": list(self.oxygen_environment_signatures), "oxygen_aliases": list(self.oxygen_aliases),
                "t_atom_indices": list(self.t_atom_indices), "t_image_shifts": [list(v) for v in self.t_image_shifts],
                "spectra": [v.to_dict() for v in self.spectra], "occupancy_contexts": [v.to_dict() for v in self.occupancy_contexts],
                "classification": None if self.classification is None else self.classification.to_dict(), "message": self.message,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StateCoordinationFingerprint":
        if p.get("schema") != STATE_COORDINATION_FINGERPRINT_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported state-fingerprint schema.")
        return cls(int(p["state_id"]), int(p["candidate_index"]), CoordinationFingerprintStatus(p["status"]),
                   StructuralObjectKind(p["structural_object_kind"]), str(p["persistent_identity"]), np.asarray(p["sample_indices"]),
                   np.asarray(p["frame_indices"]), np.asarray(p["ion_atom_indices"]), np.asarray(p["represented_time_weights"]),
                   np.asarray(p["local_coordinates"]), np.asarray(p["mo_distances"]), np.asarray(p["mt_distances"]),
                   np.asarray(p["centered_reference_mo_distances"]), np.asarray(p["geometry_predicted_mo_distances"]),
                   tuple(p["oxygen_atom_indices"]), tuple(tuple(v) for v in p["oxygen_image_shifts"]),
                   tuple(p["oxygen_environment_signatures"]), tuple(p["oxygen_aliases"]), tuple(p["t_atom_indices"]),
                   tuple(tuple(v) for v in p["t_image_shifts"]), tuple(CoordinationSpectrum.from_dict(v) for v in p["spectra"]),
                   tuple(OccupancyContextFingerprint.from_dict(v) for v in p["occupancy_contexts"]),
                   None if p.get("classification") is None else CoordinationClassificationEvidence.from_dict(p["classification"]),
                   str(p.get("message", "")), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class CoordinationFingerprintCatalog:
    collection_binding_digest: str
    sample_catalog_signature: str
    temporal_assignment_signature: str
    validated_frozen_catalog_signature: str
    registered_structural_view_digest: str
    registration_signature: str
    options: CoordinationFingerprintOptions
    resources: CoordinationFingerprintResourcePolicy
    fingerprints: tuple[StateCoordinationFingerprint, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        digests = {name: _sha(getattr(self, name), name) for name in ("collection_binding_digest", "sample_catalog_signature",
                   "temporal_assignment_signature", "validated_frozen_catalog_signature", "registered_structural_view_digest", "registration_signature")}
        fingerprints = tuple(self.fingerprints)
        keys = [(v.state_id, v.candidate_index) for v in fingerprints]
        if keys != sorted(keys) or len(set(keys)) != len(keys): raise CoordinationFingerprintInputError("Fingerprints must be uniquely ordered by state/candidate.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": COORDINATION_FINGERPRINT_CATALOG_SCHEMA, **digests, "options_signature": self.options.signature,
                   "resources_signature": self.resources.signature, "fingerprint_signatures": [v.signature for v in fingerprints],
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise CoordinationFingerprintInputError("Coordination catalog signature is inconsistent.")
        for n, v in digests.items(): object.__setattr__(self, n, v)
        object.__setattr__(self, "fingerprints", fingerprints); object.__setattr__(self, "metadata", metadata); object.__setattr__(self, "signature", expected)

    def for_state(self, state_id: int) -> tuple[StateCoordinationFingerprint, ...]:
        return tuple(v for v in self.fingerprints if v.state_id == int(state_id))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": COORDINATION_FINGERPRINT_CATALOG_SCHEMA,
                **{name: getattr(self, name) for name in ("collection_binding_digest", "sample_catalog_signature",
                    "temporal_assignment_signature", "validated_frozen_catalog_signature", "registered_structural_view_digest", "registration_signature")},
                "options": self.options.to_dict(), "resources": self.resources.to_dict(),
                "fingerprints": [v.to_dict() for v in self.fingerprints], "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoordinationFingerprintCatalog":
        if p.get("schema") != COORDINATION_FINGERPRINT_CATALOG_SCHEMA: raise CoordinationFingerprintSerializationError("Unsupported coordination-catalog schema.")
        return cls(*(str(p[name]) for name in ("collection_binding_digest", "sample_catalog_signature", "temporal_assignment_signature",
                   "validated_frozen_catalog_signature", "registered_structural_view_digest", "registration_signature")),
                   CoordinationFingerprintOptions.from_dict(p["options"]), CoordinationFingerprintResourcePolicy.from_dict(p["resources"]),
                   tuple(StateCoordinationFingerprint.from_dict(v) for v in p["fingerprints"]), dict(p.get("metadata", {})), str(p.get("signature", "")))


def _context_summaries(local: np.ndarray, weights: np.ndarray, labels: np.ndarray | None,
                       options: CoordinationFingerprintOptions) -> tuple[tuple[OccupancyContextFingerprint, ...], OccupancyMixtureStatus]:
    if labels is None: return (), OccupancyMixtureStatus.NOT_PROVIDED
    records: list[OccupancyContextFingerprint] = []
    for label in sorted(set(str(v) for v in labels)):
        mask = np.asarray([str(v) == label for v in labels], dtype=bool)
        if int(np.sum(mask)) < options.occupancy_minimum_samples: continue
        w = weights[mask]; pts = local[mask]; mean = np.average(pts, axis=0, weights=w); centered = pts - mean
        covariance = float(np.sum(w[:, None] * centered**2) / np.sum(w)); radial = np.linalg.norm(pts[:, :2], axis=1)
        phase_mask = radial > options.centered_offcenter_threshold
        phase, resultant = _circular_resultant(np.arctan2(pts[phase_mask, 1], pts[phase_mask, 0]), w[phase_mask])
        records.append(OccupancyContextFingerprint(label, int(np.sum(mask)), float(np.sum(w)), tuple(float(v) for v in mean),
                                                    covariance, float(np.average(radial, weights=w)), phase, resultant))
    if len(records) < 2: return tuple(records), OccupancyMixtureStatus.INSUFFICIENT
    mixture = False
    for i, left in enumerate(records):
        for right in records[i + 1:]:
            if np.linalg.norm(np.asarray(left.mean_local_coordinates) - np.asarray(right.mean_local_coordinates)) > options.occupancy_center_shift_threshold:
                mixture = True
            if left.circular_phase is not None and right.circular_phase is not None and min(left.phase_resultant, right.phase_resultant) >= options.phase_stability_threshold:
                if abs(_wrap_angle(left.circular_phase - right.circular_phase)) > options.occupancy_phase_shift_threshold: mixture = True
    return tuple(records), OccupancyMixtureStatus.RESOLVED_MIXTURE if mixture else OccupancyMixtureStatus.CONSISTENT


def analyze_coordination_fingerprint_samples(
    *,
    state_id: int,
    candidate_index: int,
    persistent_identity: str,
    structural_object_kind: StructuralObjectKind,
    sample_indices: Sequence[int],
    frame_indices: Sequence[int],
    ion_atom_indices: Sequence[int],
    represented_time_weights: Sequence[float],
    local_coordinates: Sequence[Sequence[float]],
    mo_distances: Sequence[Sequence[float]],
    mt_distances: Sequence[Sequence[float]],
    centered_reference_mo_distances: Sequence[Sequence[float]],
    geometry_predicted_mo_distances: Sequence[Sequence[float]],
    oxygen_atom_indices: Sequence[int],
    oxygen_image_shifts: Sequence[Sequence[int]],
    oxygen_environment_signatures: Sequence[str | None],
    oxygen_aliases: Sequence[str | None],
    t_atom_indices: Sequence[int],
    t_image_shifts: Sequence[Sequence[int]],
    mean_oxygen_angles: Sequence[float],
    mean_oxygen_arc_weights: Sequence[float],
    occupancy_labels: Sequence[Any] | None = None,
    options: CoordinationFingerprintOptions | None = None,
) -> StateCoordinationFingerprint:
    """Analyze one exact, already matched state/structural-association sample block."""
    options = options or CoordinationFingerprintOptions()
    samples = np.asarray(sample_indices, dtype=np.int64); frames = np.asarray(frame_indices, dtype=np.int64); ions = np.asarray(ion_atom_indices, dtype=np.int64)
    weights = np.asarray(represented_time_weights, dtype=float); local = np.asarray(local_coordinates, dtype=float)
    mo = np.asarray(mo_distances, dtype=float); mt = np.asarray(mt_distances, dtype=float); centered = np.asarray(centered_reference_mo_distances, dtype=float); predicted = np.asarray(geometry_predicted_mo_distances, dtype=float)
    n = samples.size
    if n < options.minimum_samples:
        empty_o = np.empty((0, len(tuple(oxygen_atom_indices))), dtype=float); empty_t = np.empty((0, len(tuple(t_atom_indices))), dtype=float)
        return StateCoordinationFingerprint(state_id, candidate_index, CoordinationFingerprintStatus.INSUFFICIENT_SAMPLES,
            structural_object_kind, persistent_identity, np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64),
            np.empty(0), np.empty((0, 3)), empty_o, empty_t, empty_o, empty_o, tuple(oxygen_atom_indices),
            tuple(tuple(v) for v in oxygen_image_shifts), tuple(oxygen_environment_signatures), tuple(oxygen_aliases), tuple(t_atom_indices),
            tuple(tuple(v) for v in t_image_shifts), (), (), None, "insufficient_state_conditioned_samples")
    if any(arr.shape[0] != n for arr in (frames, ions, weights, local, mo, mt, centered, predicted)) or local.shape != (n, 3) or centered.shape != mo.shape or predicted.shape != mo.shape:
        raise CoordinationFingerprintInputError("State-conditioned sample arrays are not aligned.")
    if np.any(weights <= 0) or np.any(~np.isfinite(weights)): raise CoordinationFingerprintInputError("Represented-time weights must be finite and positive.")
    angles = np.asarray(mean_oxygen_angles, dtype=float); arc = np.asarray(mean_oxygen_arc_weights, dtype=float)
    if angles.shape != (mo.shape[1],) or arc.shape != angles.shape: raise CoordinationFingerprintInputError("Mean oxygen angle/arc arrays do not align with M--O distances.")
    total = float(np.sum(weights)); wn = weights / total
    mean_mo = np.sum(wn[:, None] * mo, axis=0); mean_mt = np.sum(wn[:, None] * mt, axis=0)
    mean_centered = np.sum(wn[:, None] * centered, axis=0); mean_predicted = np.sum(wn[:, None] * predicted, axis=0)
    mean_residual = mean_mo - mean_centered; scale = max(float(np.mean(mean_mo)), np.finfo(float).eps)
    maximum_mode = min(options.maximum_harmonic_mode, max(1, mo.shape[1] // 2))
    spectra: list[CoordinationSpectrum] = [
        _dft_spectrum(mean_mo, "M-O mean distance", options.phase_amplitude_tolerance),
        _dft_spectrum(mean_mt, "M-T mean distance", options.phase_amplitude_tolerance),
        _dft_spectrum(mean_residual, "M-O centered-reference residual", options.phase_amplitude_tolerance),
    ]
    for values, name in ((mean_mo, "M-O mean distance"), (mean_residual, "M-O centered-reference residual")):
        moment, fit = _angular_spectrum(values, angles, arc, name, maximum_mode, options.phase_amplitude_tolerance,
                                        options.maximum_condition_number, options.regularization)
        spectra.extend((moment, fit))
    mean_local = np.sum(wn[:, None] * local, axis=0); radial = np.linalg.norm(local[:, :2], axis=1)
    phase_mask = radial > options.centered_offcenter_threshold
    phase, resultant = _circular_resultant(np.arctan2(local[phase_mask, 1], local[phase_mask, 0]), weights[phase_mask])
    phase_resolved = bool(phase is not None and resultant >= options.phase_stability_threshold)
    if phase is None:
        oxygen_lock = gap_lock = sector_lock = 0.0
    else:
        oxygen_delta = min(abs(_wrap_angle(phase - theta)) for theta in angles)
        ordered = np.sort(np.mod(angles, 2.0 * math.pi)); extended = np.concatenate((ordered, ordered[:1] + 2.0 * math.pi))
        gaps = np.mod(0.5 * (extended[:-1] + extended[1:]), 2.0 * math.pi)
        gap_delta = min(abs(_wrap_angle(phase - theta)) for theta in gaps)
        oxygen_lock = float(0.5 * (1.0 + math.cos(oxygen_delta))); gap_lock = float(0.5 * (1.0 + math.cos(gap_delta)))
        sector_lock = float(max(oxygen_lock, gap_lock) * resultant)
    positive = float(np.sum(weights[local[:, 2] > options.centered_offcenter_threshold])); negative = float(np.sum(weights[local[:, 2] < -options.centered_offcenter_threshold]))
    bilateral = 0.0 if positive + negative <= 0 else float(2.0 * min(positive, negative) / (positive + negative))
    phase_bins = max(6, 2 * mo.shape[1]); occupied = 0
    if phase_mask.any():
        hist, _ = np.histogram(np.mod(np.arctan2(local[phase_mask, 1], local[phase_mask, 0]), 2.0 * math.pi), bins=phase_bins, range=(0.0, 2.0 * math.pi), weights=weights[phase_mask])
        occupied = int(np.sum(hist > 0)); c = np.fft.rfft(hist / max(np.sum(hist), np.finfo(float).eps))
        corrugation = float(min(1.0, 2.0 * np.max(np.abs(c[1:])) if c.size > 1 else 0.0))
    else:
        corrugation = 0.0
    mean_radial = float(np.average(radial, weights=weights)); radial_std = float(np.sqrt(np.average((radial - mean_radial) ** 2, weights=weights)))
    annularity = float((occupied / phase_bins) * math.exp(-radial_std / max(mean_radial, options.centered_offcenter_threshold)))
    delta = mean_mo - mean_centered; pred_delta = mean_predicted - mean_centered
    residual_rms = float(np.sqrt(np.mean((mean_mo - mean_predicted) ** 2)))
    explained = float(np.clip(1.0 - np.linalg.norm(delta - pred_delta) / max(np.linalg.norm(delta), options.phase_amplitude_tolerance * scale), 0.0, 1.0))
    contexts, mixture = _context_summaries(local, weights, None if occupancy_labels is None else np.asarray(occupancy_labels, dtype=object), options)
    diagnostics = ["residual_spectra_are_diagnostic_not_exact_component_separation"]
    if mixture is OccupancyMixtureStatus.RESOLVED_MIXTURE: diagnostics.append("occupancy_conditioned_fingerprint_mixture_retained")
    kind = StructuralObjectKind(structural_object_kind)
    if kind is StructuralObjectKind.TILE_CAGE:
        cls = CoordinationStructuralClass.CAGE
    elif annularity >= options.annularity_threshold:
        cls = CoordinationStructuralClass.CORRUGATED_ANNULAR if corrugation >= options.corrugation_threshold else CoordinationStructuralClass.SMOOTH_ANNULAR
    elif bilateral >= options.bilateral_balance_threshold:
        cls = CoordinationStructuralClass.BILATERAL
    elif mean_radial > options.centered_offcenter_threshold and phase_resolved and explained >= 0.5:
        cls = CoordinationStructuralClass.DISCRETE_OFF_CENTER
    elif mean_radial <= options.centered_offcenter_threshold:
        cls = CoordinationStructuralClass.POINT
    elif mixture is OccupancyMixtureStatus.RESOLVED_MIXTURE or (mean_radial > options.centered_offcenter_threshold and not phase_resolved):
        cls = CoordinationStructuralClass.AMBIGUOUS
    else:
        cls = CoordinationStructuralClass.GENERAL
    evidence = CoordinationClassificationEvidence(cls, mean_radial, float(mean_local[2]), radial_std, resultant, phase_resolved,
        oxygen_lock, gap_lock, sector_lock, bilateral, annularity, corrugation, explained, residual_rms, mixture, tuple(diagnostics))
    return StateCoordinationFingerprint(state_id, candidate_index, CoordinationFingerprintStatus.RESOLVED, kind, persistent_identity,
        samples, frames, ions, weights, local, mo, mt, centered, predicted, tuple(oxygen_atom_indices), tuple(tuple(v) for v in oxygen_image_shifts),
        tuple(oxygen_environment_signatures), tuple(oxygen_aliases), tuple(t_atom_indices), tuple(tuple(v) for v in t_image_shifts), tuple(spectra), contexts, evidence)


def _unresolved_record(state_id: int, candidate_index: int, kind: StructuralObjectKind, identity: str,
                       status: CoordinationFingerprintStatus, message: str) -> StateCoordinationFingerprint:
    return StateCoordinationFingerprint(state_id, candidate_index, status, kind, identity,
        np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64), np.empty(0), np.empty((0, 3)),
        np.empty((0, 0)), np.empty((0, 0)), np.empty((0, 0)), np.empty((0, 0)), (), (), (), (), (), (), (), (), None, message)


def prepare_coordination_fingerprint_catalog(
    collection: AtomisticFrameCollection,
    sample_catalog: FrameworkAlignedIonSampleCatalog,
    temporal_assignment: ProvisionalTemporalAssignmentCatalog,
    validated_catalog: ValidatedFrozenCatalog,
    registered_structural_view: RegisteredStructuralGeometryView,
    *,
    occupancy_context_labels: Sequence[Any] | None = None,
    options: CoordinationFingerprintOptions | None = None,
    resources: CoordinationFingerprintResourcePolicy | None = None,
) -> CoordinationFingerprintCatalog:
    """Build exact physical coordination fingerprints for all retained E5 associations."""
    options = options or CoordinationFingerprintOptions(); resources = resources or CoordinationFingerprintResourcePolicy()
    if not isinstance(collection, AtomisticFrameCollection): raise TypeError("collection must be AtomisticFrameCollection.")
    if validated_catalog.sample_catalog_signature != sample_catalog.signature or validated_catalog.temporal_assignment_signature != temporal_assignment.signature:
        raise CoordinationFingerprintInputError("E5 catalog does not belong to the supplied E0b/E4 sources.")
    if validated_catalog.registered_structural_view_digest != registered_structural_view.digest:
        raise CoordinationFingerprintInputError("E5 catalog and structural view disagree.")
    if sample_catalog.registration_signature != registered_structural_view.registration_signature:
        raise CoordinationFingerprintInputError("Sample and structural registrations disagree.")
    binding = _collection_binding_digest(collection)
    if binding != registered_structural_view.collection_binding_digest:
        raise CoordinationFingerprintInputError("Collection and registered structural view disagree.")
    if len(validated_catalog.states) > resources.max_states: raise CoordinationFingerprintResourceError("states exceed max_states")
    labels = None if occupancy_context_labels is None else np.asarray(occupancy_context_labels, dtype=object)
    if labels is not None and labels.shape != (sample_catalog.n_samples,): raise CoordinationFingerprintInputError("occupancy_context_labels must match compact samples.")
    membership = temporal_assignment.membership
    fingerprints: list[StateCoordinationFingerprint] = []
    work = 0; context_groups = 0
    for state in validated_catalog.states:
        associations = state.structural_association.candidates
        if len(fingerprints) + len(associations) > resources.max_associations: raise CoordinationFingerprintResourceError("associations exceed max_associations")
        if not associations:
            fingerprints.append(_unresolved_record(state.state_id, 0, StructuralObjectKind.RING, f"state:{state.state_id}",
                CoordinationFingerprintStatus.STRUCTURAL_ASSOCIATION_UNRESOLVED, "no_retained_structural_association"))
            continue
        sample_mask = np.asarray(sample_catalog.evidence_masks.position_mask, dtype=bool) & np.isin(membership.raw_classification, [int(RawMembershipClass.CORE), int(RawMembershipClass.BASIN)]) & (membership.basin_membership == state.source_attractor_id)
        state_samples = np.flatnonzero(sample_mask)
        for association in associations:
            if association.kind is not StructuralObjectKind.RING:
                fingerprints.append(_unresolved_record(state.state_id, association.candidate_index, association.kind, association.persistent_identity,
                    CoordinationFingerprintStatus.STRUCTURAL_OBJECT_UNSUPPORTED, "exact cyclic M-O/M-T fingerprint currently requires a ring association"))
                continue
            window_index = int(association.physical_geometry_reference.get("window_index", association.object_index))
            rows = []; first_ring = None
            for sample_index in state_samples:
                frame_index = int(sample_catalog.frame_indices[sample_index]); atom_index = int(sample_catalog.atom_indices[sample_index])
                frame = registered_structural_view.frame_for_collection_index(frame_index)
                if window_index >= len(frame.rings): continue
                ring = frame.rings[window_index]
                if ring.status is not RegisteredRingViewStatus.RESOLVED or ring.physical is None or ring.registered is None: continue
                if first_ring is None: first_ring = ring
                elif tuple(a.atom_ref for a in ring.registered.o_atoms) != tuple(a.atom_ref for a in first_ring.registered.o_atoms):
                    raise CoordinationFingerprintInputError("Persistent oxygen identities changed across frames.")
                cell = collection.cells[frame_index]; origin = collection.origins[frame_index]
                ion = collection.fractional_positions[frame_index, atom_index] @ cell + origin
                center = np.asarray(ring.physical.center); raw = ion - center
                mic, _, _ = minimum_image_geometry(raw[None, :], cell=cell, pbc=collection.pbc)
                ion_matched = center + mic[0]
                u = np.asarray(ring.physical.axis_u); v = np.asarray(ring.physical.axis_v); normal = np.asarray(ring.physical.ordered_unit_normal)
                delta = ion_matched - center; local = np.asarray([delta @ u, delta @ v, delta @ normal])
                o = np.asarray(ring.physical.o_cartesian_vertices); t = np.asarray(ring.physical.t_cartesian_vertices)
                mo = np.linalg.norm(o - ion_matched, axis=1); mt = np.linalg.norm(t - ion_matched, axis=1)
                centered_point = center + local[2] * normal; centered = np.linalg.norm(o - centered_point, axis=1)
                o_local = np.column_stack(((o - center) @ u, (o - center) @ v, (o - center) @ normal))
                angles = np.arctan2(o_local[:, 1], o_local[:, 0]); arc = _arc_voronoi_weights(o)
                rows.append((int(sample_index), frame_index, atom_index, float(sample_catalog.represented_time_weights[sample_index]), local, mo, mt, centered, center, u, v, normal, o, angles, arc))
            if len(rows) < options.minimum_samples or first_ring is None:
                fingerprints.append(_unresolved_record(state.state_id, association.candidate_index, association.kind, association.persistent_identity,
                    CoordinationFingerprintStatus.FRAME_GEOMETRY_UNRESOLVED, "insufficient_resolved_state_conditioned_ring_frames"))
                continue
            weights = np.asarray([r[3] for r in rows]); local = np.asarray([r[4] for r in rows]); mean_local = np.average(local, axis=0, weights=weights)
            predicted = []
            for row in rows:
                point = row[8] + mean_local[0] * row[9] + mean_local[1] * row[10] + mean_local[2] * row[11]
                predicted.append(np.linalg.norm(row[12] - point, axis=1))
            work += len(rows) * (2 * first_ring.ring_size)
            if work > resources.max_sample_distance_values: raise CoordinationFingerprintResourceError("sample distance work exceeds max_sample_distance_values")
            context = None if labels is None else labels[[r[0] for r in rows]]
            if context is not None: context_groups += len(set(str(v) for v in context))
            if context_groups > resources.max_occupancy_groups: raise CoordinationFingerprintResourceError("occupancy groups exceed max_occupancy_groups")
            o_atoms = first_ring.registered.o_atoms; t_atoms = first_ring.registered.t_atoms
            result = analyze_coordination_fingerprint_samples(
                state_id=state.state_id, candidate_index=association.candidate_index, persistent_identity=association.persistent_identity,
                structural_object_kind=association.kind, sample_indices=[r[0] for r in rows], frame_indices=[r[1] for r in rows],
                ion_atom_indices=[r[2] for r in rows], represented_time_weights=weights, local_coordinates=local,
                mo_distances=[r[5] for r in rows], mt_distances=[r[6] for r in rows], centered_reference_mo_distances=[r[7] for r in rows],
                geometry_predicted_mo_distances=predicted, oxygen_atom_indices=[a.atom_ref.atom_index for a in o_atoms],
                oxygen_image_shifts=[a.atom_ref.image_shift for a in o_atoms], oxygen_environment_signatures=[a.oxygen_environment_signature for a in o_atoms],
                oxygen_aliases=[a.crystallographic_alias for a in o_atoms], t_atom_indices=[a.atom_ref.atom_index for a in t_atoms],
                t_image_shifts=[a.atom_ref.image_shift for a in t_atoms],
                mean_oxygen_angles=np.angle(np.average(np.exp(1j * np.asarray([r[13] for r in rows])), axis=0, weights=weights)),
                mean_oxygen_arc_weights=np.average(np.asarray([r[14] for r in rows]), axis=0, weights=weights),
                occupancy_labels=context, options=options)
            fingerprints.append(result)
    records = len(fingerprints) + sum(len(v.spectra) + len(v.occupancy_contexts) for v in fingerprints)
    if records > resources.max_serialized_records: raise CoordinationFingerprintResourceError("serialized records exceed max_serialized_records")
    metadata = {
        "exact_physical_distance_vectors_authoritative": True,
        "residual_spectra_diagnostic_not_exact_separation": True,
        "phase_labels_require_resolved_amplitude_and_stable_circular_phase": True,
        "multiple_structural_associations_retained": True,
        "occupancy_conditioning_pooled_only_when_consistent": True,
        "site_labels_finalized": False,
        "method_background": (
            "finite cyclic DFT and least-squares trigonometric regression",
            "circular mean resultant for phase stability",
        ),
    }
    return CoordinationFingerprintCatalog(binding, sample_catalog.signature, temporal_assignment.signature, validated_catalog.signature,
        registered_structural_view.digest, sample_catalog.registration_signature, options, resources, tuple(fingerprints), metadata)


__all__ = [
    "COORDINATION_CLASSIFICATION_EVIDENCE_SCHEMA", "COORDINATION_FINGERPRINT_CATALOG_SCHEMA",
    "COORDINATION_FINGERPRINT_OPTIONS_SCHEMA", "COORDINATION_FINGERPRINT_RESOURCES_SCHEMA",
    "COORDINATION_FINGERPRINT_STAGE", "COORDINATION_HARMONIC_SCHEMA", "COORDINATION_SPECTRUM_SCHEMA",
    "OCCUPANCY_CONTEXT_FINGERPRINT_SCHEMA", "STATE_COORDINATION_FINGERPRINT_SCHEMA",
    "CoordinationClassificationEvidence", "CoordinationFingerprintCatalog", "CoordinationFingerprintError",
    "CoordinationFingerprintInputError", "CoordinationFingerprintOptions", "CoordinationFingerprintResourceError",
    "CoordinationFingerprintResourcePolicy", "CoordinationFingerprintSerializationError", "CoordinationFingerprintStatus",
    "CoordinationHarmonic", "CoordinationSpectrum", "CoordinationStructuralClass", "OccupancyContextFingerprint",
    "OccupancyMixtureStatus", "StateCoordinationFingerprint", "analyze_coordination_fingerprint_samples",
    "prepare_coordination_fingerprint_catalog",
]
