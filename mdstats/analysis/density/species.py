"""Stage-11E1 periodic species-density estimation.

This module evaluates a normalized Gaussian lattice sum on one certified
registered triclinic torus.  It consumes the compact Stage-11E0b species sample
catalog, retains represented-time weighting exactly, and keeps the kernel
covariance distinct from the analysis geometry metric used to raise the density
score covector.

The estimator never substitutes a minimum-image Gaussian for the lattice sum.
Finite image enumeration is accompanied by conservative, uniform tail bounds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from ..site_samples import FrameworkAlignedIonSampleCatalog

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

PERIODIC_DENSITY_DOMAIN_SCHEMA = "mdstats.periodic-density-domain.v1"
GAUSSIAN_KERNEL_COVARIANCE_SCHEMA = "mdstats.gaussian-kernel-covariance.v1"
ANALYSIS_GEOMETRY_METRIC_SCHEMA = "mdstats.analysis-geometry-metric.v1"
GAUSSIAN_IMAGE_TRUNCATION_SCHEMA = "mdstats.gaussian-image-truncation.v1"
SPECIES_DENSITY_RESOURCE_POLICY_SCHEMA = "mdstats.species-density-resource-policy.v1"
SPECIES_DENSITY_OPTIONS_SCHEMA = "mdstats.species-density-options.v1"
SPECIES_DENSITY_INTEGRALS_SCHEMA = "mdstats.species-density-integrals.v1"
DENSITY_FIELD_ERROR_CERTIFICATE_SCHEMA = "mdstats.density-field-error-certificate.v1"
DENSITY_BLOCK_UNCERTAINTY_SCHEMA = "mdstats.density-block-uncertainty.v1"
PERIODIC_SPECIES_DENSITY_REALIZATION_SCHEMA = "mdstats.periodic-species-density-realization.v1"
PERIODIC_SPECIES_DENSITY_ESTIMATE_SCHEMA = "mdstats.periodic-species-density-estimate.v1"
PERIODIC_SPECIES_DENSITY_LADDER_SCHEMA = "mdstats.periodic-species-density-ladder.v1"
PERIODIC_SPECIES_DENSITY_STAGE = "11E1"


class PeriodicSpeciesDensityError(ValueError):
    """Base error for Stage-11E1 periodic species density."""


class PeriodicSpeciesDensityInputError(PeriodicSpeciesDensityError):
    """Raised when domain, kernel, catalog, or options disagree."""


class PeriodicSpeciesDensityResourceError(PeriodicSpeciesDensityError):
    """Raised transactionally before finite work or memory limits are exceeded."""


class PeriodicSpeciesDensitySerializationError(PeriodicSpeciesDensityError):
    """Raised when serialized data are malformed or tampered with."""


class DensityCoordinateMeasure(str, Enum):
    PHYSICAL_CARTESIAN = "physical_cartesian"
    REFERENCE_MATERIAL = "reference_material"


class SpeciesDensityBackend(str, Enum):
    DENSE = "dense"
    BLOCK_SPARSE = "block_sparse"


EvidenceChannel = Literal["position", "joint"]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None, allow_nonfinite: bool = False) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise PeriodicSpeciesDensityInputError(f"{name} must have ndim={ndim}; received {array.shape}.")
    if shape is not None and array.shape != shape:
        raise PeriodicSpeciesDensityInputError(f"{name} must have shape {shape}; received {array.shape}.")
    if (not allow_nonfinite) and np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise PeriodicSpeciesDensityInputError(f"{name} contains non-finite values.")
    array.setflags(write=False)
    return array


def _matrix3(value: Any, *, name: str, positive_definite: bool = False) -> FloatArray:
    array = _readonly(value, dtype=np.float64, ndim=2, name=name, shape=(3, 3))
    if not np.allclose(array, array.T, rtol=0.0, atol=1.0e-13) and positive_definite:
        raise PeriodicSpeciesDensityInputError(f"{name} must be symmetric.")
    if positive_definite:
        eigenvalues = np.linalg.eigvalsh(array)
        if float(eigenvalues[0]) <= 0.0:
            raise PeriodicSpeciesDensityInputError(f"{name} must be positive definite.")
    return array


def _sha(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise PeriodicSpeciesDensityInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) <= 0:
        raise PeriodicSpeciesDensityInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) < 0:
        raise PeriodicSpeciesDensityInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise PeriodicSpeciesDensityInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise PeriodicSpeciesDensityInputError(f"{name} must be finite and nonnegative.")
    return result


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise PeriodicSpeciesDensityInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(v) for v in value)
    raise PeriodicSpeciesDensityInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


@dataclass(frozen=True, slots=True)
class PeriodicDensityDomain:
    """One fixed registered periodic domain and coordinate-volume measure."""

    cell: FloatArray
    registration_signature: str
    coordinate_measure: DensityCoordinateMeasure = DensityCoordinateMeasure.REFERENCE_MATERIAL
    pbc: tuple[bool, bool, bool] = (True, True, True)
    source_cell_variation_max: float = 0.0
    fixed_cell_tolerance: float = 1.0e-10
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        cell = _readonly(self.cell, dtype=np.float64, ndim=2, name="cell", shape=(3, 3))
        determinant = float(np.linalg.det(cell))
        if not np.isfinite(determinant) or determinant <= 1.0e-12:
            raise PeriodicSpeciesDensityInputError("cell must be right-handed and nonsingular.")
        signature = _sha(self.registration_signature, name="registration_signature")
        measure = DensityCoordinateMeasure(self.coordinate_measure)
        pbc = tuple(bool(v) for v in self.pbc)
        if pbc != (True, True, True):
            raise PeriodicSpeciesDensityInputError("Stage-11E1 requires a fully periodic three-dimensional domain.")
        variation = _nonnegative_float(self.source_cell_variation_max, name="source_cell_variation_max")
        tolerance = _nonnegative_float(self.fixed_cell_tolerance, name="fixed_cell_tolerance")
        if measure is DensityCoordinateMeasure.PHYSICAL_CARTESIAN and variation > tolerance:
            raise PeriodicSpeciesDensityInputError(
                "Pooled physical Cartesian density is undefined for a varying registered cell; "
                "use reference_material or provide a fixed-cell catalog."
            )
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": PERIODIC_DENSITY_DOMAIN_SCHEMA,
            "cell_digest": _array_digest(cell),
            "registration_signature": signature,
            "coordinate_measure": measure.value,
            "pbc": list(pbc),
            "source_cell_variation_max": variation,
            "fixed_cell_tolerance": tolerance,
            "metadata": _json_value(metadata),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Periodic-density-domain signature is inconsistent.")
        object.__setattr__(self, "cell", cell)
        object.__setattr__(self, "registration_signature", signature)
        object.__setattr__(self, "coordinate_measure", measure)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "source_cell_variation_max", variation)
        object.__setattr__(self, "fixed_cell_tolerance", tolerance)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    @property
    def volume(self) -> float:
        return float(np.linalg.det(self.cell))

    @property
    def metric_covariant(self) -> FloatArray:
        result = np.asarray(self.cell @ self.cell.T, dtype=np.float64)
        result.setflags(write=False)
        return result

    @property
    def metric_contravariant(self) -> FloatArray:
        result = np.asarray(np.linalg.inv(self.metric_covariant), dtype=np.float64)
        result.setflags(write=False)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PERIODIC_DENSITY_DOMAIN_SCHEMA,
            "cell": self.cell.tolist(),
            "registration_signature": self.registration_signature,
            "coordinate_measure": self.coordinate_measure.value,
            "pbc": list(self.pbc),
            "source_cell_variation_max": self.source_cell_variation_max,
            "fixed_cell_tolerance": self.fixed_cell_tolerance,
            "metadata": _json_value(self.metadata),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicDensityDomain":
        if payload.get("schema") != PERIODIC_DENSITY_DOMAIN_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported periodic-density-domain schema.")
        return cls(
            cell=np.asarray(payload["cell"], dtype=np.float64),
            registration_signature=str(payload["registration_signature"]),
            coordinate_measure=DensityCoordinateMeasure(payload["coordinate_measure"]),
            pbc=tuple(bool(v) for v in payload["pbc"]),
            source_cell_variation_max=float(payload["source_cell_variation_max"]),
            fixed_cell_tolerance=float(payload["fixed_cell_tolerance"]),
            metadata=dict(payload.get("metadata", {})),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class AnalysisGeometryMetric:
    """Metric used for periodic distance, topology, and score index raising."""

    covariant: FloatArray
    domain_signature: str
    signature: str = ""

    def __post_init__(self) -> None:
        covariant = _matrix3(self.covariant, name="covariant", positive_definite=True)
        domain_signature = _sha(self.domain_signature, name="domain_signature")
        payload = {
            "schema": ANALYSIS_GEOMETRY_METRIC_SCHEMA,
            "covariant_digest": _array_digest(covariant),
            "domain_signature": domain_signature,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Analysis-geometry-metric signature is inconsistent.")
        object.__setattr__(self, "covariant", covariant)
        object.__setattr__(self, "domain_signature", domain_signature)
        object.__setattr__(self, "signature", expected)

    @classmethod
    def from_domain(cls, domain: PeriodicDensityDomain) -> "AnalysisGeometryMetric":
        return cls(covariant=domain.metric_covariant, domain_signature=domain.signature)

    @property
    def contravariant(self) -> FloatArray:
        result = np.asarray(np.linalg.inv(self.covariant), dtype=np.float64)
        result.setflags(write=False)
        return result

    @property
    def orthonormal_factor(self) -> FloatArray:
        """Return lower ``L`` with ``covariant = L L^T`` for ``y = q L``."""
        result = np.asarray(np.linalg.cholesky(self.covariant), dtype=np.float64)
        result.setflags(write=False)
        return result

    def covectors_in_orthonormal_chart(self, covectors: FloatArray) -> FloatArray:
        inverse_transpose = np.linalg.inv(self.orthonormal_factor).T
        result = np.asarray(np.einsum("...i,ij->...j", covectors, inverse_transpose, optimize=True), dtype=np.float64)
        result.setflags(write=False)
        return result

    def hessians_in_orthonormal_chart(self, hessians: FloatArray) -> FloatArray:
        inverse = np.linalg.inv(self.orthonormal_factor)
        result = np.asarray(np.einsum("ia,...ab,jb->...ij", inverse, hessians, inverse, optimize=True), dtype=np.float64)
        result.setflags(write=False)
        return result

    def raise_covectors(self, covectors: FloatArray) -> FloatArray:
        result = np.asarray(np.einsum("...i,ij->...j", covectors, self.contravariant, optimize=True), dtype=np.float64)
        result.setflags(write=False)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ANALYSIS_GEOMETRY_METRIC_SCHEMA,
            "covariant": self.covariant.tolist(),
            "domain_signature": self.domain_signature,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AnalysisGeometryMetric":
        if payload.get("schema") != ANALYSIS_GEOMETRY_METRIC_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported analysis-geometry-metric schema.")
        return cls(
            covariant=np.asarray(payload["covariant"], dtype=np.float64),
            domain_signature=str(payload["domain_signature"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class GaussianKernelCovariance:
    """Positive-definite Gaussian covariance expressed in fractional coordinates."""

    fractional_covariance: FloatArray
    label: str = "bandwidth-0"
    source_basis: str = "fractional"
    source_covariance: FloatArray | None = None
    domain_signature: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        covariance = _matrix3(self.fractional_covariance, name="fractional_covariance", positive_definite=True)
        label = str(self.label).strip()
        if not label:
            raise PeriodicSpeciesDensityInputError("Kernel label must be nonempty.")
        basis = str(self.source_basis)
        if basis not in {"fractional", "cartesian"}:
            raise PeriodicSpeciesDensityInputError("source_basis must be fractional or cartesian.")
        source = None
        if self.source_covariance is not None:
            source = _matrix3(self.source_covariance, name="source_covariance", positive_definite=True)
        domain_signature = self.domain_signature
        if domain_signature is not None:
            domain_signature = _sha(domain_signature, name="domain_signature")
        payload = {
            "schema": GAUSSIAN_KERNEL_COVARIANCE_SCHEMA,
            "fractional_covariance_digest": _array_digest(covariance),
            "label": label,
            "source_basis": basis,
            "source_covariance_digest": None if source is None else _array_digest(source),
            "domain_signature": domain_signature,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Gaussian-kernel-covariance signature is inconsistent.")
        object.__setattr__(self, "fractional_covariance", covariance)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "source_basis", basis)
        object.__setattr__(self, "source_covariance", source)
        object.__setattr__(self, "domain_signature", domain_signature)
        object.__setattr__(self, "signature", expected)

    @classmethod
    def isotropic_cartesian(cls, sigma: float, domain: PeriodicDensityDomain, *, label: str = "bandwidth-0") -> "GaussianKernelCovariance":
        value = _positive_float(sigma, name="sigma")
        cartesian = np.eye(3, dtype=np.float64) * value * value
        return cls.from_cartesian(cartesian, domain, label=label)

    @classmethod
    def from_cartesian(cls, covariance: FloatArray, domain: PeriodicDensityDomain, *, label: str = "bandwidth-0") -> "GaussianKernelCovariance":
        cartesian = _matrix3(covariance, name="cartesian_covariance", positive_definite=True)
        inverse_cell = np.linalg.inv(domain.cell)
        fractional = inverse_cell.T @ cartesian @ inverse_cell
        return cls(
            fractional_covariance=fractional,
            label=label,
            source_basis="cartesian",
            source_covariance=cartesian,
            domain_signature=domain.signature,
        )

    @property
    def precision(self) -> FloatArray:
        result = np.asarray(np.linalg.inv(self.fractional_covariance), dtype=np.float64)
        result.setflags(write=False)
        return result

    @property
    def normalizer(self) -> float:
        return float(1.0 / (((2.0 * math.pi) ** 1.5) * math.sqrt(float(np.linalg.det(self.fractional_covariance)))))

    def scaled(self, factor: float, *, label: str | None = None) -> "GaussianKernelCovariance":
        scale = _positive_float(factor, name="factor")
        return GaussianKernelCovariance(
            fractional_covariance=self.fractional_covariance * scale * scale,
            label=self.label if label is None else label,
            source_basis=self.source_basis,
            source_covariance=None if self.source_covariance is None else self.source_covariance * scale * scale,
            domain_signature=self.domain_signature,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": GAUSSIAN_KERNEL_COVARIANCE_SCHEMA,
            "fractional_covariance": self.fractional_covariance.tolist(),
            "label": self.label,
            "source_basis": self.source_basis,
            "source_covariance": None if self.source_covariance is None else self.source_covariance.tolist(),
            "domain_signature": self.domain_signature,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GaussianKernelCovariance":
        if payload.get("schema") != GAUSSIAN_KERNEL_COVARIANCE_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported Gaussian-kernel-covariance schema.")
        return cls(
            fractional_covariance=np.asarray(payload["fractional_covariance"], dtype=np.float64),
            label=str(payload["label"]),
            source_basis=str(payload["source_basis"]),
            source_covariance=None if payload.get("source_covariance") is None else np.asarray(payload["source_covariance"], dtype=np.float64),
            domain_signature=payload.get("domain_signature"),
            signature=str(payload.get("signature", "")),
        )


def _gaussian_tail_integrals(start: float, variance: float) -> tuple[float, float, float]:
    exponent = math.exp(-(start * start) / (2.0 * variance))
    i0 = math.sqrt(math.pi * variance / 2.0) * math.erfc(start / math.sqrt(2.0 * variance))
    i1 = variance * exponent
    i2 = variance * start * exponent + variance * i0
    return i0, i1, i2


def _one_dimensional_envelopes(variance: float, radius: int) -> tuple[float, float, float, float, float, float]:
    # For delta in (-1,1), |k+delta| >= max(|k|-1,0) and
    # |k+delta| <= |k|+1.  The resulting separable envelope is uniform in delta.
    stop = max(radius + 8, int(math.ceil(8.0 * math.sqrt(variance))) + 8)
    js = np.arange(1, stop + 1, dtype=np.float64)
    exponential = np.exp(-(js * js) / (2.0 * variance))
    a_total = 3.0 + 2.0 * float(np.sum(exponential))
    b_total = 5.0 + 2.0 * float(np.sum((js + 2.0) * exponential))
    d_total = 9.0 + 2.0 * float(np.sum((js + 2.0) ** 2 * exponential))
    start = float(stop + 1)
    i0, i1, i2 = _gaussian_tail_integrals(start, variance)
    # A decreasing-series bound f(start)+integral(start, infinity).
    first = math.exp(-(start * start) / (2.0 * variance))
    a_total += 2.0 * (first + i0)
    b_total += 2.0 * ((start + 2.0) * first + i1 + 2.0 * i0)
    d_total += 2.0 * ((start + 2.0) ** 2 * first + i2 + 4.0 * i1 + 4.0 * i0)
    if radius == 0:
        return a_total, b_total, d_total, 1.0, 1.0, 1.0
    if radius == 1:
        return a_total, b_total, d_total, 3.0, 5.0, 9.0
    local = np.arange(1, radius, dtype=np.float64)
    local_exp = np.exp(-(local * local) / (2.0 * variance))
    a_box = 3.0 + 2.0 * float(np.sum(local_exp))
    b_box = 5.0 + 2.0 * float(np.sum((local + 2.0) * local_exp))
    d_box = 9.0 + 2.0 * float(np.sum((local + 2.0) ** 2 * local_exp))
    return a_total, b_total, d_total, a_box, b_box, d_box


@dataclass(frozen=True, slots=True)
class GaussianImageTruncation:
    radius: int
    requested_relative_density_tolerance: float
    density_bound_per_unit_weight_fractional: float
    gradient_bound_per_unit_weight_fractional: float
    hessian_bound_per_unit_weight_fractional: float
    relative_peak_density_bound: float
    image_count: int
    covariance_signature: str
    signature: str = ""

    def __post_init__(self) -> None:
        radius = _nonnegative_int(self.radius, name="radius")
        tolerance = _positive_float(self.requested_relative_density_tolerance, name="requested_relative_density_tolerance")
        density = _nonnegative_float(self.density_bound_per_unit_weight_fractional, name="density_bound_per_unit_weight_fractional")
        gradient = _nonnegative_float(self.gradient_bound_per_unit_weight_fractional, name="gradient_bound_per_unit_weight_fractional")
        hessian = _nonnegative_float(self.hessian_bound_per_unit_weight_fractional, name="hessian_bound_per_unit_weight_fractional")
        relative = _nonnegative_float(self.relative_peak_density_bound, name="relative_peak_density_bound")
        count = _positive_int(self.image_count, name="image_count")
        covariance_signature = _sha(self.covariance_signature, name="covariance_signature")
        if count != (2 * radius + 1) ** 3:
            raise PeriodicSpeciesDensityInputError("image_count disagrees with radius.")
        payload = {
            "schema": GAUSSIAN_IMAGE_TRUNCATION_SCHEMA,
            "radius": radius,
            "requested_relative_density_tolerance": tolerance,
            "density_bound_per_unit_weight_fractional": density,
            "gradient_bound_per_unit_weight_fractional": gradient,
            "hessian_bound_per_unit_weight_fractional": hessian,
            "relative_peak_density_bound": relative,
            "image_count": count,
            "covariance_signature": covariance_signature,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Gaussian-image-truncation signature is inconsistent.")
        object.__setattr__(self, "radius", radius)
        object.__setattr__(self, "requested_relative_density_tolerance", tolerance)
        object.__setattr__(self, "density_bound_per_unit_weight_fractional", density)
        object.__setattr__(self, "gradient_bound_per_unit_weight_fractional", gradient)
        object.__setattr__(self, "hessian_bound_per_unit_weight_fractional", hessian)
        object.__setattr__(self, "relative_peak_density_bound", relative)
        object.__setattr__(self, "image_count", count)
        object.__setattr__(self, "covariance_signature", covariance_signature)
        object.__setattr__(self, "signature", expected)

    def image_shifts(self) -> IntArray:
        values = np.arange(-self.radius, self.radius + 1, dtype=np.int64)
        grid = np.stack(np.meshgrid(values, values, values, indexing="ij"), axis=-1).reshape(-1, 3)
        grid.setflags(write=False)
        return grid

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": GAUSSIAN_IMAGE_TRUNCATION_SCHEMA,
            "radius": self.radius,
            "requested_relative_density_tolerance": self.requested_relative_density_tolerance,
            "density_bound_per_unit_weight_fractional": self.density_bound_per_unit_weight_fractional,
            "gradient_bound_per_unit_weight_fractional": self.gradient_bound_per_unit_weight_fractional,
            "hessian_bound_per_unit_weight_fractional": self.hessian_bound_per_unit_weight_fractional,
            "relative_peak_density_bound": self.relative_peak_density_bound,
            "image_count": self.image_count,
            "covariance_signature": self.covariance_signature,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GaussianImageTruncation":
        if payload.get("schema") != GAUSSIAN_IMAGE_TRUNCATION_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported Gaussian-image-truncation schema.")
        return cls(
            radius=int(payload["radius"]),
            requested_relative_density_tolerance=float(payload["requested_relative_density_tolerance"]),
            density_bound_per_unit_weight_fractional=float(payload["density_bound_per_unit_weight_fractional"]),
            gradient_bound_per_unit_weight_fractional=float(payload["gradient_bound_per_unit_weight_fractional"]),
            hessian_bound_per_unit_weight_fractional=float(payload["hessian_bound_per_unit_weight_fractional"]),
            relative_peak_density_bound=float(payload["relative_peak_density_bound"]),
            image_count=int(payload["image_count"]),
            covariance_signature=str(payload["covariance_signature"]),
            signature=str(payload.get("signature", "")),
        )


def prepare_gaussian_image_truncation(covariance: GaussianKernelCovariance, *, relative_density_tolerance: float = 1.0e-12, max_radius: int = 12) -> GaussianImageTruncation:
    tolerance = _positive_float(relative_density_tolerance, name="relative_density_tolerance")
    limit = _nonnegative_int(max_radius, name="max_radius")
    eigenvalues = np.linalg.eigvalsh(covariance.fractional_covariance)
    largest_variance = float(eigenvalues[-1])
    precision_norm = float(np.linalg.norm(covariance.precision, ord=2))
    chosen: GaussianImageTruncation | None = None
    for radius in range(limit + 1):
        a, b, d, ar, br, dr = _one_dimensional_envelopes(largest_variance, radius)
        delta_a = max(a - ar, 0.0)
        zeroth = delta_a * (a * a + a * ar + ar * ar)
        first_axis = max((b - br) * a * a + br * delta_a * (a + ar), 0.0)
        second_axis = max((d - dr) * a * a + dr * delta_a * (a + ar), 0.0)
        first = 3.0 * first_axis
        second = 3.0 * second_axis
        density = covariance.normalizer * zeroth
        gradient = covariance.normalizer * precision_norm * first
        hessian = covariance.normalizer * (precision_norm * precision_norm * second + math.sqrt(3.0) * precision_norm * zeroth)
        relative = density / covariance.normalizer
        candidate = GaussianImageTruncation(
            radius=radius,
            requested_relative_density_tolerance=tolerance,
            density_bound_per_unit_weight_fractional=density,
            gradient_bound_per_unit_weight_fractional=gradient,
            hessian_bound_per_unit_weight_fractional=hessian,
            relative_peak_density_bound=relative,
            image_count=(2 * radius + 1) ** 3,
            covariance_signature=covariance.signature,
        )
        chosen = candidate
        if relative <= tolerance:
            return candidate
    assert chosen is not None
    raise PeriodicSpeciesDensityResourceError(
        "The requested Gaussian image-tail tolerance requires an image radius "
        f"larger than max_radius={limit}; last relative peak bound={chosen.relative_peak_density_bound:.6g}."
    )


@dataclass(frozen=True, slots=True)
class SpeciesDensityResourcePolicy:
    max_grid_nodes: int = 2_000_000
    max_samples: int = 5_000_000
    max_image_terms: int = 200_000_000
    max_workspace_bytes: int = 512 * 1024**2
    max_output_bytes: int = 1024 * 1024**2
    max_blocks: int = 500_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name=name) for name in (
            "max_grid_nodes", "max_samples", "max_image_terms", "max_workspace_bytes", "max_output_bytes", "max_blocks"
        )}
        payload = {"schema": SPECIES_DENSITY_RESOURCE_POLICY_SCHEMA, **values}
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Species-density-resource-policy signature is inconsistent.")
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SPECIES_DENSITY_RESOURCE_POLICY_SCHEMA,
            "max_grid_nodes": self.max_grid_nodes,
            "max_samples": self.max_samples,
            "max_image_terms": self.max_image_terms,
            "max_workspace_bytes": self.max_workspace_bytes,
            "max_output_bytes": self.max_output_bytes,
            "max_blocks": self.max_blocks,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesDensityResourcePolicy":
        if payload.get("schema") != SPECIES_DENSITY_RESOURCE_POLICY_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported species-density-resource-policy schema.")
        return cls(
            max_grid_nodes=int(payload["max_grid_nodes"]),
            max_samples=int(payload["max_samples"]),
            max_image_terms=int(payload["max_image_terms"]),
            max_workspace_bytes=int(payload["max_workspace_bytes"]),
            max_output_bytes=int(payload["max_output_bytes"]),
            max_blocks=int(payload["max_blocks"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class SpeciesDensityOptions:
    grid_shape: tuple[int, int, int] = (48, 48, 48)
    backend: SpeciesDensityBackend = SpeciesDensityBackend.DENSE
    block_shape: tuple[int, int, int] = (12, 12, 12)
    evidence_channel: EvidenceChannel = "position"
    relative_image_tolerance: float = 1.0e-12
    max_image_radius: int = 12
    query_batch_size: int = 1024
    sample_batch_size: int = 256
    support_tail_safety_factor: float = 8.0
    support_density_floor: float = 0.0
    minimum_effective_samples: float = 1.0
    sparse_block_density_threshold: float = 0.0
    uncertainty_blocks: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        shape = tuple(_positive_int(v, name="grid_shape") for v in self.grid_shape)
        block = tuple(_positive_int(v, name="block_shape") for v in self.block_shape)
        if len(shape) != 3 or len(block) != 3:
            raise PeriodicSpeciesDensityInputError("grid_shape and block_shape must contain three entries.")
        backend = SpeciesDensityBackend(self.backend)
        channel = str(self.evidence_channel)
        if channel not in {"position", "joint"}:
            raise PeriodicSpeciesDensityInputError("evidence_channel must be position or joint.")
        tolerance = _positive_float(self.relative_image_tolerance, name="relative_image_tolerance")
        radius = _nonnegative_int(self.max_image_radius, name="max_image_radius")
        query_batch = _positive_int(self.query_batch_size, name="query_batch_size")
        sample_batch = _positive_int(self.sample_batch_size, name="sample_batch_size")
        safety = _positive_float(self.support_tail_safety_factor, name="support_tail_safety_factor")
        floor = _nonnegative_float(self.support_density_floor, name="support_density_floor")
        neff = _positive_float(self.minimum_effective_samples, name="minimum_effective_samples")
        sparse_threshold = _nonnegative_float(self.sparse_block_density_threshold, name="sparse_block_density_threshold")
        uncertainty = _nonnegative_int(self.uncertainty_blocks, name="uncertainty_blocks")
        if uncertainty == 1:
            raise PeriodicSpeciesDensityInputError("uncertainty_blocks must be zero or at least two.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": SPECIES_DENSITY_OPTIONS_SCHEMA,
            "grid_shape": list(shape), "backend": backend.value, "block_shape": list(block),
            "evidence_channel": channel, "relative_image_tolerance": tolerance,
            "max_image_radius": radius, "query_batch_size": query_batch,
            "sample_batch_size": sample_batch, "support_tail_safety_factor": safety,
            "support_density_floor": floor, "minimum_effective_samples": neff,
            "sparse_block_density_threshold": sparse_threshold,
            "uncertainty_blocks": uncertainty, "metadata": _json_value(metadata),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Species-density-options signature is inconsistent.")
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "backend", backend)
        object.__setattr__(self, "block_shape", block)
        object.__setattr__(self, "evidence_channel", channel)
        object.__setattr__(self, "relative_image_tolerance", tolerance)
        object.__setattr__(self, "max_image_radius", radius)
        object.__setattr__(self, "query_batch_size", query_batch)
        object.__setattr__(self, "sample_batch_size", sample_batch)
        object.__setattr__(self, "support_tail_safety_factor", safety)
        object.__setattr__(self, "support_density_floor", floor)
        object.__setattr__(self, "minimum_effective_samples", neff)
        object.__setattr__(self, "sparse_block_density_threshold", sparse_threshold)
        object.__setattr__(self, "uncertainty_blocks", uncertainty)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SPECIES_DENSITY_OPTIONS_SCHEMA,
            "grid_shape": list(self.grid_shape), "backend": self.backend.value,
            "block_shape": list(self.block_shape), "evidence_channel": self.evidence_channel,
            "relative_image_tolerance": self.relative_image_tolerance,
            "max_image_radius": self.max_image_radius, "query_batch_size": self.query_batch_size,
            "sample_batch_size": self.sample_batch_size,
            "support_tail_safety_factor": self.support_tail_safety_factor,
            "support_density_floor": self.support_density_floor,
            "minimum_effective_samples": self.minimum_effective_samples,
            "sparse_block_density_threshold": self.sparse_block_density_threshold,
            "uncertainty_blocks": self.uncertainty_blocks,
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesDensityOptions":
        if payload.get("schema") != SPECIES_DENSITY_OPTIONS_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported species-density-options schema.")
        return cls(
            grid_shape=tuple(int(v) for v in payload["grid_shape"]),
            backend=SpeciesDensityBackend(payload["backend"]),
            block_shape=tuple(int(v) for v in payload["block_shape"]),
            evidence_channel=str(payload["evidence_channel"]),
            relative_image_tolerance=float(payload["relative_image_tolerance"]),
            max_image_radius=int(payload["max_image_radius"]),
            query_batch_size=int(payload["query_batch_size"]),
            sample_batch_size=int(payload["sample_batch_size"]),
            support_tail_safety_factor=float(payload["support_tail_safety_factor"]),
            support_density_floor=float(payload["support_density_floor"]),
            minimum_effective_samples=float(payload["minimum_effective_samples"]),
            sparse_block_density_threshold=float(payload["sparse_block_density_threshold"]),
            uncertainty_blocks=int(payload["uncertainty_blocks"]),
            metadata=dict(payload.get("metadata", {})),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class SpeciesDensityIntegrals:
    observation_measure: float
    observation_measure_units: str
    ion_time_integral: float
    mean_occupancy_integral: float
    probability_integral: float
    signature: str = ""

    def __post_init__(self) -> None:
        observation = _positive_float(self.observation_measure, name="observation_measure")
        units = str(self.observation_measure_units)
        if not units:
            raise PeriodicSpeciesDensityInputError("observation_measure_units must be nonempty.")
        ion_time = _positive_float(self.ion_time_integral, name="ion_time_integral")
        occupancy = _positive_float(self.mean_occupancy_integral, name="mean_occupancy_integral")
        probability = _positive_float(self.probability_integral, name="probability_integral")
        payload = {
            "schema": SPECIES_DENSITY_INTEGRALS_SCHEMA,
            "observation_measure": observation, "observation_measure_units": units,
            "ion_time_integral": ion_time, "mean_occupancy_integral": occupancy,
            "probability_integral": probability,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Species-density-integrals signature is inconsistent.")
        object.__setattr__(self, "observation_measure", observation)
        object.__setattr__(self, "observation_measure_units", units)
        object.__setattr__(self, "ion_time_integral", ion_time)
        object.__setattr__(self, "mean_occupancy_integral", occupancy)
        object.__setattr__(self, "probability_integral", probability)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SPECIES_DENSITY_INTEGRALS_SCHEMA,
            "observation_measure": self.observation_measure,
            "observation_measure_units": self.observation_measure_units,
            "ion_time_integral": self.ion_time_integral,
            "mean_occupancy_integral": self.mean_occupancy_integral,
            "probability_integral": self.probability_integral,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesDensityIntegrals":
        if payload.get("schema") != SPECIES_DENSITY_INTEGRALS_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported species-density-integrals schema.")
        return cls(
            observation_measure=float(payload["observation_measure"]),
            observation_measure_units=str(payload["observation_measure_units"]),
            ion_time_integral=float(payload["ion_time_integral"]),
            mean_occupancy_integral=float(payload["mean_occupancy_integral"]),
            probability_integral=float(payload["probability_integral"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class DensityFieldErrorCertificate:
    image_density_absolute_bound: float
    image_score_covector_norm_bound: float
    image_metric_gradient_norm_bound: float
    image_hessian_frobenius_bound: float
    discrete_number_normalization_residual: float
    discrete_probability_normalization_residual: float
    support_node_count: int
    total_node_count: int
    certified_only_on_support: bool
    truncation_signature: str
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _nonnegative_float(getattr(self, name), name=name) for name in (
            "image_density_absolute_bound", "image_score_covector_norm_bound",
            "image_metric_gradient_norm_bound", "image_hessian_frobenius_bound",
            "discrete_number_normalization_residual", "discrete_probability_normalization_residual"
        )}
        support = _nonnegative_int(self.support_node_count, name="support_node_count")
        total = _positive_int(self.total_node_count, name="total_node_count")
        if support > total:
            raise PeriodicSpeciesDensityInputError("support_node_count exceeds total_node_count.")
        truncation = _sha(self.truncation_signature, name="truncation_signature")
        payload = {
            "schema": DENSITY_FIELD_ERROR_CERTIFICATE_SCHEMA, **values,
            "support_node_count": support, "total_node_count": total,
            "certified_only_on_support": bool(self.certified_only_on_support),
            "truncation_signature": truncation,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Density-field-error-certificate signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "support_node_count", support)
        object.__setattr__(self, "total_node_count", total)
        object.__setattr__(self, "certified_only_on_support", bool(self.certified_only_on_support))
        object.__setattr__(self, "truncation_signature", truncation)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DENSITY_FIELD_ERROR_CERTIFICATE_SCHEMA,
            "image_density_absolute_bound": self.image_density_absolute_bound,
            "image_score_covector_norm_bound": self.image_score_covector_norm_bound,
            "image_metric_gradient_norm_bound": self.image_metric_gradient_norm_bound,
            "image_hessian_frobenius_bound": self.image_hessian_frobenius_bound,
            "discrete_number_normalization_residual": self.discrete_number_normalization_residual,
            "discrete_probability_normalization_residual": self.discrete_probability_normalization_residual,
            "support_node_count": self.support_node_count, "total_node_count": self.total_node_count,
            "certified_only_on_support": self.certified_only_on_support,
            "truncation_signature": self.truncation_signature, "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DensityFieldErrorCertificate":
        if payload.get("schema") != DENSITY_FIELD_ERROR_CERTIFICATE_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported density-field-error-certificate schema.")
        return cls(
            image_density_absolute_bound=float(payload["image_density_absolute_bound"]),
            image_score_covector_norm_bound=float(payload["image_score_covector_norm_bound"]),
            image_metric_gradient_norm_bound=float(payload["image_metric_gradient_norm_bound"]),
            image_hessian_frobenius_bound=float(payload["image_hessian_frobenius_bound"]),
            discrete_number_normalization_residual=float(payload["discrete_number_normalization_residual"]),
            discrete_probability_normalization_residual=float(payload["discrete_probability_normalization_residual"]),
            support_node_count=int(payload["support_node_count"]),
            total_node_count=int(payload["total_node_count"]),
            certified_only_on_support=bool(payload["certified_only_on_support"]),
            truncation_signature=str(payload["truncation_signature"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class CompleteSystemBlockUncertainty:
    block_count: int
    block_frame_ids: tuple[tuple[int, ...], ...]
    number_density_standard_error: FloatArray
    grid_shape: tuple[int, int, int]
    signature: str = ""

    def __post_init__(self) -> None:
        count = _positive_int(self.block_count, name="block_count")
        groups = tuple(tuple(int(v) for v in group) for group in self.block_frame_ids)
        if len(groups) != count or any(not group for group in groups):
            raise PeriodicSpeciesDensityInputError("block_frame_ids must contain one nonempty group per block.")
        shape = tuple(_positive_int(v, name="grid_shape") for v in self.grid_shape)
        values = _readonly(self.number_density_standard_error, dtype=np.float64, ndim=3, name="number_density_standard_error", shape=shape)
        if np.any(values < 0.0):
            raise PeriodicSpeciesDensityInputError("number_density_standard_error must be nonnegative.")
        payload = {
            "schema": DENSITY_BLOCK_UNCERTAINTY_SCHEMA, "block_count": count,
            "block_frame_ids": [list(v) for v in groups], "grid_shape": list(shape),
            "standard_error_digest": _array_digest(values),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Density-block-uncertainty signature is inconsistent.")
        object.__setattr__(self, "block_count", count)
        object.__setattr__(self, "block_frame_ids", groups)
        object.__setattr__(self, "number_density_standard_error", values)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "signature", expected)

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        payload = {
            "schema": DENSITY_BLOCK_UNCERTAINTY_SCHEMA, "block_count": self.block_count,
            "block_frame_ids": [list(v) for v in self.block_frame_ids], "grid_shape": list(self.grid_shape),
            "signature": self.signature,
        }
        if include_values: payload["number_density_standard_error"] = self.number_density_standard_error.tolist()
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompleteSystemBlockUncertainty":
        if payload.get("schema") != DENSITY_BLOCK_UNCERTAINTY_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported density-block-uncertainty schema.")
        if "number_density_standard_error" not in payload:
            raise PeriodicSpeciesDensitySerializationError("Block-uncertainty replay requires field values.")
        return cls(
            block_count=int(payload["block_count"]),
            block_frame_ids=tuple(tuple(int(v) for v in group) for group in payload["block_frame_ids"]),
            number_density_standard_error=np.asarray(payload["number_density_standard_error"], dtype=np.float64),
            grid_shape=tuple(int(v) for v in payload["grid_shape"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class PeriodicSpeciesDensityRealization:
    """Dense or block-packed canonical fields on one periodic logical-node grid."""

    backend: SpeciesDensityBackend
    grid_shape: tuple[int, int, int]
    block_shape: tuple[int, int, int]
    active_block_indices: IntArray
    number_density_values: FloatArray
    probability_density_values: FloatArray
    density_score_covector_values: FloatArray
    metric_gradient_vector_values: FloatArray
    density_hessian_covariant_values: FloatArray
    local_effective_sample_size_values: FloatArray
    support_mask_values: BoolArray
    number_density_standard_error_values: FloatArray | None
    signature: str = ""

    def __post_init__(self) -> None:
        backend = SpeciesDensityBackend(self.backend)
        shape = tuple(_positive_int(v, name="grid_shape") for v in self.grid_shape)
        block = tuple(_positive_int(v, name="block_shape") for v in self.block_shape)
        active = _readonly(self.active_block_indices, dtype=np.int64, ndim=2, name="active_block_indices")
        if active.shape[1:] != (3,):
            raise PeriodicSpeciesDensityInputError("active_block_indices must have shape (n,3).")
        if backend is SpeciesDensityBackend.DENSE:
            if active.shape[0] != 1 or not np.array_equal(active[0], np.zeros(3, dtype=np.int64)):
                raise PeriodicSpeciesDensityInputError("Dense realization uses one sentinel active block [0,0,0].")
            scalar_shape = shape
        else:
            scalar_shape = (active.shape[0],) + block
            block_counts = tuple(int(math.ceil(shape[i] / block[i])) for i in range(3))
            if np.any(active < 0) or np.any(active >= np.asarray(block_counts)):
                raise PeriodicSpeciesDensityInputError("active_block_indices lie outside the block lattice.")
            if len({tuple(int(v) for v in row) for row in active}) != active.shape[0]:
                raise PeriodicSpeciesDensityInputError("active_block_indices must be unique.")
        number = _readonly(self.number_density_values, dtype=np.float64, ndim=len(scalar_shape), name="number_density_values", shape=scalar_shape)
        probability = _readonly(self.probability_density_values, dtype=np.float64, ndim=len(scalar_shape), name="probability_density_values", shape=scalar_shape)
        neff = _readonly(self.local_effective_sample_size_values, dtype=np.float64, ndim=len(scalar_shape), name="local_effective_sample_size_values", shape=scalar_shape)
        support = _readonly(self.support_mask_values, dtype=np.bool_, ndim=len(scalar_shape), name="support_mask_values", shape=scalar_shape)
        vector_shape = scalar_shape + (3,)
        tensor_shape = scalar_shape + (3, 3)
        score = _readonly(self.density_score_covector_values, dtype=np.float64, ndim=len(vector_shape), name="density_score_covector_values", shape=vector_shape)
        gradient = _readonly(self.metric_gradient_vector_values, dtype=np.float64, ndim=len(vector_shape), name="metric_gradient_vector_values", shape=vector_shape)
        hessian = _readonly(self.density_hessian_covariant_values, dtype=np.float64, ndim=len(tensor_shape), name="density_hessian_covariant_values", shape=tensor_shape)
        stderr = None
        if self.number_density_standard_error_values is not None:
            stderr = _readonly(self.number_density_standard_error_values, dtype=np.float64, ndim=len(scalar_shape), name="number_density_standard_error_values", shape=scalar_shape)
        if np.any(number < -1.0e-14) or np.any(probability < -1.0e-14) or np.any(neff < 0.0):
            raise PeriodicSpeciesDensityInputError("Density and effective-sample fields must be nonnegative.")
        payload = {
            "schema": PERIODIC_SPECIES_DENSITY_REALIZATION_SCHEMA, "backend": backend.value,
            "grid_shape": list(shape), "block_shape": list(block), "active_blocks_digest": _array_digest(active),
            "number_digest": _array_digest(number), "probability_digest": _array_digest(probability),
            "score_digest": _array_digest(score), "metric_gradient_digest": _array_digest(gradient),
            "hessian_digest": _array_digest(hessian), "neff_digest": _array_digest(neff),
            "support_digest": _array_digest(support), "stderr_digest": None if stderr is None else _array_digest(stderr),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Periodic-species-density-realization signature is inconsistent.")
        for name, value in (("backend", backend), ("grid_shape", shape), ("block_shape", block), ("active_block_indices", active),
                            ("number_density_values", number), ("probability_density_values", probability),
                            ("density_score_covector_values", score), ("metric_gradient_vector_values", gradient),
                            ("density_hessian_covariant_values", hessian), ("local_effective_sample_size_values", neff),
                            ("support_mask_values", support), ("number_density_standard_error_values", stderr), ("signature", expected)):
            object.__setattr__(self, name, value)

    @property
    def active_block_count(self) -> int:
        return 0 if self.backend is SpeciesDensityBackend.DENSE else int(self.active_block_indices.shape[0])

    def _dense_scalar(self, values: np.ndarray, *, fill: float | bool) -> np.ndarray:
        if self.backend is SpeciesDensityBackend.DENSE:
            result = np.array(values, copy=True)
            result.setflags(write=False)
            return result
        result = np.full(self.grid_shape, fill, dtype=values.dtype)
        for block_index, block_value in zip(self.active_block_indices, values, strict=True):
            start = block_index * np.asarray(self.block_shape, dtype=np.int64)
            stop = np.minimum(start + np.asarray(self.block_shape), np.asarray(self.grid_shape))
            slices = tuple(slice(int(start[i]), int(stop[i])) for i in range(3))
            local = tuple(slice(0, int(stop[i] - start[i])) for i in range(3))
            result[slices] = block_value[local]
        result.setflags(write=False)
        return result

    def _dense_vector(self, values: np.ndarray, *, rank: int) -> np.ndarray:
        if self.backend is SpeciesDensityBackend.DENSE:
            result = np.array(values, copy=True)
            result.setflags(write=False)
            return result
        tail = (3,) if rank == 1 else (3, 3)
        result = np.zeros(self.grid_shape + tail, dtype=np.float64)
        for block_index, block_value in zip(self.active_block_indices, values, strict=True):
            start = block_index * np.asarray(self.block_shape, dtype=np.int64)
            stop = np.minimum(start + np.asarray(self.block_shape), np.asarray(self.grid_shape))
            slices = tuple(slice(int(start[i]), int(stop[i])) for i in range(3)) + (slice(None),) * rank
            local = tuple(slice(0, int(stop[i] - start[i])) for i in range(3)) + (slice(None),) * rank
            result[slices] = block_value[local]
        result.setflags(write=False)
        return result

    def number_density_dense(self) -> FloatArray:
        return self._dense_scalar(self.number_density_values, fill=0.0)  # type: ignore[return-value]

    def probability_density_dense(self) -> FloatArray:
        return self._dense_scalar(self.probability_density_values, fill=0.0)  # type: ignore[return-value]

    def density_score_covector_dense(self) -> FloatArray:
        return self._dense_vector(self.density_score_covector_values, rank=1)  # type: ignore[return-value]

    def metric_gradient_vector_dense(self) -> FloatArray:
        return self._dense_vector(self.metric_gradient_vector_values, rank=1)  # type: ignore[return-value]

    def density_hessian_covariant_dense(self) -> FloatArray:
        return self._dense_vector(self.density_hessian_covariant_values, rank=2)  # type: ignore[return-value]

    def local_effective_sample_size_dense(self) -> FloatArray:
        return self._dense_scalar(self.local_effective_sample_size_values, fill=0.0)  # type: ignore[return-value]

    def support_mask_dense(self) -> BoolArray:
        return self._dense_scalar(self.support_mask_values, fill=False)  # type: ignore[return-value]

    def number_density_standard_error_dense(self) -> FloatArray | None:
        if self.number_density_standard_error_values is None: return None
        return self._dense_scalar(self.number_density_standard_error_values, fill=0.0)  # type: ignore[return-value]

    def gather_number_density(self, logical_indices: IntArray) -> FloatArray:
        indices = np.asarray(logical_indices, dtype=np.int64)
        if indices.ndim != 2 or indices.shape[1:] != (3,):
            raise PeriodicSpeciesDensityInputError("logical_indices must have shape (n,3).")
        wrapped = np.mod(indices, np.asarray(self.grid_shape, dtype=np.int64))
        dense = self.number_density_dense()
        result = np.asarray(dense[wrapped[:, 0], wrapped[:, 1], wrapped[:, 2]], dtype=np.float64)
        result.setflags(write=False)
        return result

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": PERIODIC_SPECIES_DENSITY_REALIZATION_SCHEMA, "backend": self.backend.value,
            "grid_shape": list(self.grid_shape), "block_shape": list(self.block_shape),
            "active_block_indices": self.active_block_indices.tolist(), "signature": self.signature,
        }
        if include_values:
            payload.update({
                "number_density_values": self.number_density_values.tolist(),
                "probability_density_values": self.probability_density_values.tolist(),
                "density_score_covector_values": self.density_score_covector_values.tolist(),
                "metric_gradient_vector_values": self.metric_gradient_vector_values.tolist(),
                "density_hessian_covariant_values": self.density_hessian_covariant_values.tolist(),
                "local_effective_sample_size_values": self.local_effective_sample_size_values.tolist(),
                "support_mask_values": self.support_mask_values.tolist(),
                "number_density_standard_error_values": None if self.number_density_standard_error_values is None else self.number_density_standard_error_values.tolist(),
            })
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicSpeciesDensityRealization":
        if payload.get("schema") != PERIODIC_SPECIES_DENSITY_REALIZATION_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported density-realization schema.")
        required = ("number_density_values", "probability_density_values", "density_score_covector_values", "metric_gradient_vector_values", "density_hessian_covariant_values", "local_effective_sample_size_values", "support_mask_values")
        if any(name not in payload for name in required):
            raise PeriodicSpeciesDensitySerializationError("Density-realization replay requires field values.")
        return cls(
            backend=SpeciesDensityBackend(payload["backend"]), grid_shape=tuple(int(v) for v in payload["grid_shape"]),
            block_shape=tuple(int(v) for v in payload["block_shape"]), active_block_indices=np.asarray(payload["active_block_indices"], dtype=np.int64),
            number_density_values=np.asarray(payload["number_density_values"], dtype=np.float64),
            probability_density_values=np.asarray(payload["probability_density_values"], dtype=np.float64),
            density_score_covector_values=np.asarray(payload["density_score_covector_values"], dtype=np.float64),
            metric_gradient_vector_values=np.asarray(payload["metric_gradient_vector_values"], dtype=np.float64),
            density_hessian_covariant_values=np.asarray(payload["density_hessian_covariant_values"], dtype=np.float64),
            local_effective_sample_size_values=np.asarray(payload["local_effective_sample_size_values"], dtype=np.float64),
            support_mask_values=np.asarray(payload["support_mask_values"], dtype=np.bool_),
            number_density_standard_error_values=None if payload.get("number_density_standard_error_values") is None else np.asarray(payload["number_density_standard_error_values"], dtype=np.float64),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class PeriodicSpeciesDensityEstimate:
    species_atomic_number: int
    species_label: str
    catalog_signature: str
    domain: PeriodicDensityDomain
    kernel_covariance: GaussianKernelCovariance
    analysis_metric: AnalysisGeometryMetric
    image_truncation: GaussianImageTruncation
    integrals: SpeciesDensityIntegrals
    realization: PeriodicSpeciesDensityRealization
    error_certificate: DensityFieldErrorCertificate
    block_uncertainty: CompleteSystemBlockUncertainty | None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        atomic_number = _positive_int(self.species_atomic_number, name="species_atomic_number")
        label = str(self.species_label)
        if not label: raise PeriodicSpeciesDensityInputError("species_label must be nonempty.")
        catalog = _sha(self.catalog_signature, name="catalog_signature")
        if self.domain.registration_signature != self.metadata.get("registration_signature", self.domain.registration_signature):
            raise PeriodicSpeciesDensityInputError("Estimate metadata registration signature disagrees with domain.")
        if self.kernel_covariance.domain_signature not in {None, self.domain.signature}:
            raise PeriodicSpeciesDensityInputError("Kernel covariance is bound to a different domain.")
        if self.analysis_metric.domain_signature != self.domain.signature:
            raise PeriodicSpeciesDensityInputError("Analysis metric is bound to a different domain.")
        if self.image_truncation.covariance_signature != self.kernel_covariance.signature:
            raise PeriodicSpeciesDensityInputError("Image truncation is bound to a different covariance.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": PERIODIC_SPECIES_DENSITY_ESTIMATE_SCHEMA, "species_atomic_number": atomic_number,
            "species_label": label, "catalog_signature": catalog, "domain_signature": self.domain.signature,
            "kernel_covariance_signature": self.kernel_covariance.signature, "analysis_metric_signature": self.analysis_metric.signature,
            "image_truncation_signature": self.image_truncation.signature, "integrals_signature": self.integrals.signature,
            "realization_signature": self.realization.signature, "error_certificate_signature": self.error_certificate.signature,
            "block_uncertainty_signature": None if self.block_uncertainty is None else self.block_uncertainty.signature,
            "metadata": _json_value(metadata),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Periodic-species-density-estimate signature is inconsistent.")
        object.__setattr__(self, "species_atomic_number", atomic_number)
        object.__setattr__(self, "species_label", label)
        object.__setattr__(self, "catalog_signature", catalog)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    @property
    def voxel_volume(self) -> float:
        return self.domain.volume / float(np.prod(self.realization.grid_shape))

    @property
    def number_density_integral(self) -> float:
        return float(np.sum(self.realization.number_density_dense()) * self.voxel_volume)

    @property
    def probability_density_integral(self) -> float:
        return float(np.sum(self.realization.probability_density_dense()) * self.voxel_volume)

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        return {
            "schema": PERIODIC_SPECIES_DENSITY_ESTIMATE_SCHEMA,
            "species_atomic_number": self.species_atomic_number, "species_label": self.species_label,
            "catalog_signature": self.catalog_signature, "domain": self.domain.to_dict(),
            "kernel_covariance": self.kernel_covariance.to_dict(), "analysis_metric": self.analysis_metric.to_dict(),
            "image_truncation": self.image_truncation.to_dict(), "integrals": self.integrals.to_dict(),
            "realization": self.realization.to_dict(include_values=include_values),
            "error_certificate": self.error_certificate.to_dict(),
            "block_uncertainty": None if self.block_uncertainty is None else self.block_uncertainty.to_dict(include_values=include_values),
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicSpeciesDensityEstimate":
        if payload.get("schema") != PERIODIC_SPECIES_DENSITY_ESTIMATE_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported periodic-species-density-estimate schema.")
        return cls(
            species_atomic_number=int(payload["species_atomic_number"]),
            species_label=str(payload["species_label"]),
            catalog_signature=str(payload["catalog_signature"]),
            domain=PeriodicDensityDomain.from_dict(payload["domain"]),
            kernel_covariance=GaussianKernelCovariance.from_dict(payload["kernel_covariance"]),
            analysis_metric=AnalysisGeometryMetric.from_dict(payload["analysis_metric"]),
            image_truncation=GaussianImageTruncation.from_dict(payload["image_truncation"]),
            integrals=SpeciesDensityIntegrals.from_dict(payload["integrals"]),
            realization=PeriodicSpeciesDensityRealization.from_dict(payload["realization"]),
            error_certificate=DensityFieldErrorCertificate.from_dict(payload["error_certificate"]),
            block_uncertainty=None if payload.get("block_uncertainty") is None else CompleteSystemBlockUncertainty.from_dict(payload["block_uncertainty"]),
            metadata=dict(payload.get("metadata", {})),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class PeriodicSpeciesDensityLadder:
    catalog_signature: str
    domain_signature: str
    estimates: tuple[PeriodicSpeciesDensityEstimate, ...]
    options_signature: str
    resource_signature: str
    signature: str = ""

    def __post_init__(self) -> None:
        catalog = _sha(self.catalog_signature, name="catalog_signature")
        domain = _sha(self.domain_signature, name="domain_signature")
        options = _sha(self.options_signature, name="options_signature")
        resources = _sha(self.resource_signature, name="resource_signature")
        estimates = tuple(self.estimates)
        if not estimates:
            raise PeriodicSpeciesDensityInputError("A bandwidth ladder requires at least one estimate.")
        if len({item.kernel_covariance.signature for item in estimates}) != len(estimates):
            raise PeriodicSpeciesDensityInputError("Bandwidth ladder covariance signatures must be unique.")
        if any(item.catalog_signature != catalog or item.domain.signature != domain for item in estimates):
            raise PeriodicSpeciesDensityInputError("Bandwidth ladder estimates do not share catalog and domain identities.")
        payload = {
            "schema": PERIODIC_SPECIES_DENSITY_LADDER_SCHEMA, "catalog_signature": catalog,
            "domain_signature": domain, "estimate_signatures": [item.signature for item in estimates],
            "options_signature": options, "resource_signature": resources,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise PeriodicSpeciesDensityInputError("Periodic-species-density-ladder signature is inconsistent.")
        object.__setattr__(self, "catalog_signature", catalog)
        object.__setattr__(self, "domain_signature", domain)
        object.__setattr__(self, "estimates", estimates)
        object.__setattr__(self, "options_signature", options)
        object.__setattr__(self, "resource_signature", resources)
        object.__setattr__(self, "signature", expected)

    @property
    def bandwidth_labels(self) -> tuple[str, ...]:
        return tuple(item.kernel_covariance.label for item in self.estimates)

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        return {
            "schema": PERIODIC_SPECIES_DENSITY_LADDER_SCHEMA,
            "catalog_signature": self.catalog_signature, "domain_signature": self.domain_signature,
            "estimates": [item.to_dict(include_values=include_values) for item in self.estimates],
            "options_signature": self.options_signature, "resource_signature": self.resource_signature,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicSpeciesDensityLadder":
        if payload.get("schema") != PERIODIC_SPECIES_DENSITY_LADDER_SCHEMA:
            raise PeriodicSpeciesDensitySerializationError("Unsupported periodic-species-density-ladder schema.")
        return cls(
            catalog_signature=str(payload["catalog_signature"]),
            domain_signature=str(payload["domain_signature"]),
            estimates=tuple(PeriodicSpeciesDensityEstimate.from_dict(item) for item in payload["estimates"]),
            options_signature=str(payload["options_signature"]),
            resource_signature=str(payload["resource_signature"]),
            signature=str(payload.get("signature", "")),
        )


def _logical_grid(shape: tuple[int, int, int]) -> FloatArray:
    axes = [np.arange(size, dtype=np.float64) / float(size) for size in shape]
    result = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    result.setflags(write=False)
    return result


def _evaluate_lattice_sum(
    queries: FloatArray,
    samples: FloatArray,
    weights: FloatArray,
    covariance: GaussianKernelCovariance,
    truncation: GaussianImageTruncation,
    *,
    query_batch_size: int,
    sample_batch_size: int,
    derivatives: bool,
) -> tuple[FloatArray, FloatArray | None, FloatArray | None, FloatArray]:
    q = np.mod(np.asarray(queries, dtype=np.float64), 1.0)
    s = np.mod(np.asarray(samples, dtype=np.float64), 1.0)
    w = np.asarray(weights, dtype=np.float64)
    n_queries = q.shape[0]
    density = np.zeros(n_queries, dtype=np.float64)
    squared = np.zeros(n_queries, dtype=np.float64)
    gradient = np.zeros((n_queries, 3), dtype=np.float64) if derivatives else None
    hessian = np.zeros((n_queries, 3, 3), dtype=np.float64) if derivatives else None
    precision = covariance.precision
    normalizer = covariance.normalizer
    images = truncation.image_shifts()
    for q_start in range(0, n_queries, query_batch_size):
        q_stop = min(q_start + query_batch_size, n_queries)
        qb = q[q_start:q_stop]
        local_density = np.zeros(q_stop - q_start, dtype=np.float64)
        local_squared = np.zeros(q_stop - q_start, dtype=np.float64)
        local_gradient = np.zeros((q_stop - q_start, 3), dtype=np.float64) if derivatives else None
        local_hessian = np.zeros((q_stop - q_start, 3, 3), dtype=np.float64) if derivatives else None
        for s_start in range(0, s.shape[0], sample_batch_size):
            s_stop = min(s_start + sample_batch_size, s.shape[0])
            sb = s[s_start:s_stop]
            wb = w[s_start:s_stop]
            for shift in images:
                diff = qb[:, None, :] - sb[None, :, :] + shift[None, None, :]
                pdiff = np.einsum("bsi,ij->bsj", diff, precision, optimize=True)
                exponent = -0.5 * np.einsum("bsi,bsi->bs", diff, pdiff, optimize=True)
                kernel = normalizer * np.exp(exponent)
                weighted = kernel * wb[None, :]
                local_density += np.sum(weighted, axis=1)
                local_squared += np.sum(weighted * weighted, axis=1)
                if derivatives:
                    assert local_gradient is not None and local_hessian is not None
                    local_gradient -= np.einsum("bs,bsi->bi", weighted, pdiff, optimize=True)
                    outer = np.einsum("bsi,bsj->bsij", pdiff, pdiff, optimize=True)
                    local_hessian += np.einsum("bs,bsij->bij", weighted, outer - precision[None, None, :, :], optimize=True)
        density[q_start:q_stop] = local_density
        squared[q_start:q_stop] = local_squared
        if derivatives:
            assert gradient is not None and hessian is not None and local_gradient is not None and local_hessian is not None
            gradient[q_start:q_stop] = local_gradient
            hessian[q_start:q_stop] = local_hessian
    return density, gradient, hessian, squared


def evaluate_periodized_gaussian_oracle(
    query_fractional: FloatArray,
    sample_fractional: FloatArray,
    sample_weights: FloatArray,
    covariance: GaussianKernelCovariance,
    *,
    truncation: GaussianImageTruncation | None = None,
    relative_image_tolerance: float = 1.0e-12,
    max_image_radius: int = 12,
    derivatives: bool = True,
) -> tuple[FloatArray, FloatArray | None, FloatArray | None]:
    """Direct finite lattice-image oracle with an explicit truncation certificate."""
    queries = _readonly(query_fractional, dtype=np.float64, ndim=2, name="query_fractional")
    samples = _readonly(sample_fractional, dtype=np.float64, ndim=2, name="sample_fractional")
    if queries.shape[1:] != (3,) or samples.shape[1:] != (3,):
        raise PeriodicSpeciesDensityInputError("query_fractional and sample_fractional must have shape (n,3).")
    weights = _readonly(sample_weights, dtype=np.float64, ndim=1, name="sample_weights", shape=(samples.shape[0],))
    if np.any(weights < 0.0) or float(np.sum(weights)) <= 0.0:
        raise PeriodicSpeciesDensityInputError("sample_weights must be nonnegative with positive sum.")
    certificate = truncation or prepare_gaussian_image_truncation(covariance, relative_density_tolerance=relative_image_tolerance, max_radius=max_image_radius)
    density, gradient, hessian, _ = _evaluate_lattice_sum(
        queries, samples, weights, covariance, certificate,
        query_batch_size=max(1, min(queries.shape[0], 1024)), sample_batch_size=max(1, min(samples.shape[0], 256)), derivatives=derivatives,
    )
    for array in (density, gradient, hessian):
        if array is not None: array.setflags(write=False)
    return density, gradient, hessian


def _pack_realization(
    *,
    backend: SpeciesDensityBackend,
    grid_shape: tuple[int, int, int],
    block_shape: tuple[int, int, int],
    number: np.ndarray,
    probability: np.ndarray,
    score: np.ndarray,
    metric_gradient: np.ndarray,
    hessian: np.ndarray,
    neff: np.ndarray,
    support: np.ndarray,
    stderr: np.ndarray | None,
    sparse_threshold: float,
    resources: SpeciesDensityResourcePolicy,
) -> PeriodicSpeciesDensityRealization:
    if backend is SpeciesDensityBackend.DENSE:
        active = np.zeros((1, 3), dtype=np.int64)
        return PeriodicSpeciesDensityRealization(
            backend=backend, grid_shape=grid_shape, block_shape=grid_shape, active_block_indices=active,
            number_density_values=number, probability_density_values=probability,
            density_score_covector_values=score, metric_gradient_vector_values=metric_gradient,
            density_hessian_covariant_values=hessian, local_effective_sample_size_values=neff,
            support_mask_values=support, number_density_standard_error_values=stderr,
        )
    counts = tuple(int(math.ceil(grid_shape[i] / block_shape[i])) for i in range(3))
    active_list: list[tuple[int, int, int]] = []
    packed: dict[str, list[np.ndarray]] = {name: [] for name in ("number", "probability", "score", "gradient", "hessian", "neff", "support", "stderr")}
    for bi in np.ndindex(*counts):
        start = np.asarray(bi) * np.asarray(block_shape)
        stop = np.minimum(start + np.asarray(block_shape), np.asarray(grid_shape))
        slices = tuple(slice(int(start[i]), int(stop[i])) for i in range(3))
        local_number = number[slices]
        local_support = support[slices]
        if sparse_threshold > 0.0 and not np.any(local_support) and float(np.max(local_number)) < sparse_threshold:
            continue
        active_list.append(tuple(int(v) for v in bi))
        local_shape = tuple(int(stop[i] - start[i]) for i in range(3))
        def pad_scalar(source: np.ndarray, fill: float | bool) -> np.ndarray:
            target = np.full(block_shape, fill, dtype=source.dtype)
            local = tuple(slice(0, local_shape[i]) for i in range(3))
            target[local] = source[slices]
            return target
        def pad_vector(source: np.ndarray, rank: int) -> np.ndarray:
            tail = (3,) if rank == 1 else (3, 3)
            target = np.zeros(block_shape + tail, dtype=np.float64)
            local = tuple(slice(0, local_shape[i]) for i in range(3)) + (slice(None),) * rank
            source_slice = slices + (slice(None),) * rank
            target[local] = source[source_slice]
            return target
        packed["number"].append(pad_scalar(number, 0.0)); packed["probability"].append(pad_scalar(probability, 0.0))
        packed["score"].append(pad_vector(score, 1)); packed["gradient"].append(pad_vector(metric_gradient, 1)); packed["hessian"].append(pad_vector(hessian, 2))
        packed["neff"].append(pad_scalar(neff, 0.0)); packed["support"].append(pad_scalar(support, False))
        if stderr is not None: packed["stderr"].append(pad_scalar(stderr, 0.0))
    if len(active_list) > resources.max_blocks:
        raise PeriodicSpeciesDensityResourceError(f"Active block count {len(active_list)} exceeds max_blocks={resources.max_blocks}.")
    active = np.asarray(active_list, dtype=np.int64).reshape(-1, 3)
    def stack(name: str, shape: tuple[int, ...], dtype: Any) -> np.ndarray:
        return np.stack(packed[name], axis=0) if packed[name] else np.empty((0,) + shape, dtype=dtype)
    return PeriodicSpeciesDensityRealization(
        backend=backend, grid_shape=grid_shape, block_shape=block_shape, active_block_indices=active,
        number_density_values=stack("number", block_shape, np.float64),
        probability_density_values=stack("probability", block_shape, np.float64),
        density_score_covector_values=stack("score", block_shape + (3,), np.float64),
        metric_gradient_vector_values=stack("gradient", block_shape + (3,), np.float64),
        density_hessian_covariant_values=stack("hessian", block_shape + (3, 3), np.float64),
        local_effective_sample_size_values=stack("neff", block_shape, np.float64),
        support_mask_values=stack("support", block_shape, np.bool_),
        number_density_standard_error_values=None if stderr is None else stack("stderr", block_shape, np.float64),
    )


def _block_uncertainty(
    *,
    queries: np.ndarray,
    samples: np.ndarray,
    weights: np.ndarray,
    frame_ids: np.ndarray,
    temporal_frame_ids: np.ndarray,
    temporal_frame_weights: np.ndarray,
    block_count: int,
    covariance: GaussianKernelCovariance,
    truncation: GaussianImageTruncation,
    domain: PeriodicDensityDomain,
    options: SpeciesDensityOptions,
    target_shape: tuple[int, int, int],
) -> CompleteSystemBlockUncertainty | None:
    if block_count == 0: return None
    unique_frames = np.asarray([int(v) for v in temporal_frame_ids if np.any(frame_ids == v)], dtype=np.int64)
    if unique_frames.size < block_count:
        raise PeriodicSpeciesDensityInputError("uncertainty_blocks exceeds the number of represented frames.")
    groups = tuple(tuple(int(v) for v in group) for group in np.array_split(unique_frames, block_count))
    fields: list[np.ndarray] = []
    for group in groups:
        sample_mask = np.isin(frame_ids, np.asarray(group, dtype=np.int64))
        frame_mask = np.isin(temporal_frame_ids, np.asarray(group, dtype=np.int64))
        observation = float(np.sum(temporal_frame_weights[frame_mask]))
        if observation <= 0.0 or not np.any(sample_mask):
            raise PeriodicSpeciesDensityInputError("Every uncertainty block must contain positive represented time and samples.")
        block_weights = weights[sample_mask] / observation
        raw, _, _, _ = _evaluate_lattice_sum(
            queries, samples[sample_mask], block_weights, covariance, truncation,
            query_batch_size=options.query_batch_size, sample_batch_size=options.sample_batch_size, derivatives=False,
        )
        field = raw.reshape(target_shape) / domain.volume
        target = float(np.sum(weights[sample_mask]) / observation)
        integral = float(np.sum(field) * domain.volume / np.prod(target_shape))
        field *= target / integral
        fields.append(field)
    stacked = np.stack(fields, axis=0)
    stderr = np.std(stacked, axis=0, ddof=1) / math.sqrt(block_count)
    return CompleteSystemBlockUncertainty(block_count=block_count, block_frame_ids=groups, number_density_standard_error=stderr, grid_shape=target_shape)


def _prepare_one_estimate(
    catalog: FrameworkAlignedIonSampleCatalog,
    domain: PeriodicDensityDomain,
    covariance: GaussianKernelCovariance,
    options: SpeciesDensityOptions,
    resources: SpeciesDensityResourcePolicy,
) -> PeriodicSpeciesDensityEstimate:
    if catalog.registration_signature != domain.registration_signature:
        raise PeriodicSpeciesDensityInputError("Catalog and density domain registration signatures disagree.")
    if covariance.domain_signature not in {None, domain.signature}:
        raise PeriodicSpeciesDensityInputError("Kernel covariance is bound to a different domain.")
    view = catalog.evidence_view(options.evidence_channel)
    if view.sample_indices.size == 0 or view.total_ion_time <= 0.0:
        raise PeriodicSpeciesDensityInputError("The selected evidence channel contains no represented samples.")
    sample_fractional = catalog.registered_wrapped_fractional[view.sample_indices]
    weights = np.asarray(view.represented_time_weights, dtype=np.float64)
    accepted_frame_ids = np.unique(view.frame_ids)
    temporal = catalog.temporal_weighting
    accepted_frame_mask = temporal.temporal_mask & np.isin(temporal.frame_ids, accepted_frame_ids)
    observation = float(np.sum(temporal.represented_time_weights[accepted_frame_mask]))
    if observation <= 0.0:
        raise PeriodicSpeciesDensityInputError("The selected evidence channel has zero represented observation measure.")
    mean_occupancy = float(np.sum(weights) / observation)
    if mean_occupancy <= 0.0:
        raise PeriodicSpeciesDensityInputError("Mean occupancy must be positive.")
    shape = options.grid_shape
    node_count = int(np.prod(shape))
    if node_count > resources.max_grid_nodes:
        raise PeriodicSpeciesDensityResourceError(f"Grid node count {node_count} exceeds max_grid_nodes={resources.max_grid_nodes}.")
    if weights.size > resources.max_samples:
        raise PeriodicSpeciesDensityResourceError(f"Sample count {weights.size} exceeds max_samples={resources.max_samples}.")
    truncation = prepare_gaussian_image_truncation(covariance, relative_density_tolerance=options.relative_image_tolerance, max_radius=options.max_image_radius)
    term_count = node_count * weights.size * truncation.image_count
    if term_count > resources.max_image_terms:
        raise PeriodicSpeciesDensityResourceError(
            f"Lattice image terms {term_count} exceed max_image_terms={resources.max_image_terms}."
        )
    workspace = options.query_batch_size * min(weights.size, options.sample_batch_size) * 3 * 8 * 4
    if workspace > resources.max_workspace_bytes:
        raise PeriodicSpeciesDensityResourceError(
            f"Estimated workspace {workspace} exceeds max_workspace_bytes={resources.max_workspace_bytes}."
        )
    # Two scalar densities, two vector fields, one tensor field, n_eff, support,
    # and optional standard error.  This is a conservative dense-equivalent
    # output bound used before either dense or packed-block allocation.
    scalar_equivalents = 2 + 3 + 3 + 9 + 1 + 1 + (1 if options.uncertainty_blocks else 0)
    output_bytes = node_count * scalar_equivalents * 8
    if output_bytes > resources.max_output_bytes:
        raise PeriodicSpeciesDensityResourceError(
            f"Estimated output {output_bytes} exceeds max_output_bytes={resources.max_output_bytes}."
        )
    queries = _logical_grid(shape)
    number_weights = weights / observation
    raw, raw_gradient, raw_hessian, squared = _evaluate_lattice_sum(
        queries, sample_fractional, number_weights, covariance, truncation,
        query_batch_size=options.query_batch_size, sample_batch_size=options.sample_batch_size, derivatives=True,
    )
    assert raw_gradient is not None and raw_hessian is not None
    volume = domain.volume
    number = raw.reshape(shape) / volume
    gradient_density = raw_gradient.reshape(shape + (3,)) / volume
    hessian_density = raw_hessian.reshape(shape + (3, 3)) / volume
    voxel = volume / node_count
    raw_integral = float(np.sum(number) * voxel)
    if raw_integral <= 0.0:
        raise PeriodicSpeciesDensityInputError("The discrete Gaussian field has nonpositive integral.")
    normalization = mean_occupancy / raw_integral
    number *= normalization
    gradient_density *= normalization
    hessian_density *= normalization
    probability = number / mean_occupancy
    neff_flat = np.zeros_like(raw)
    positive_squared = squared > 0.0
    neff_flat[positive_squared] = raw[positive_squared] ** 2 / squared[positive_squared]
    neff = neff_flat.reshape(shape)
    density_tail = truncation.density_bound_per_unit_weight_fractional * mean_occupancy * normalization / volume
    gradient_tail = truncation.gradient_bound_per_unit_weight_fractional * mean_occupancy * normalization / volume
    hessian_tail = truncation.hessian_bound_per_unit_weight_fractional * mean_occupancy * normalization / volume
    lower = number - options.support_tail_safety_factor * density_tail
    support = (lower > options.support_density_floor) & (neff >= options.minimum_effective_samples)
    score = np.zeros(shape + (3,), dtype=np.float64)
    metric_gradient = np.zeros(shape + (3,), dtype=np.float64)
    hessian_supported = np.zeros(shape + (3, 3), dtype=np.float64)
    score[support] = gradient_density[support] / number[support, None]
    metric = AnalysisGeometryMetric.from_domain(domain)
    metric_gradient[support] = np.einsum("ni,ij->nj", score[support], metric.contravariant, optimize=True)
    hessian_supported[support] = hessian_density[support]
    density_lower = np.maximum(number[support] - density_tail, np.finfo(float).tiny)
    if np.any(support):
        grad_norm = np.linalg.norm(gradient_density[support], axis=1)
        score_error = gradient_tail / float(np.min(density_lower)) + float(np.max(grad_norm / (number[support] * density_lower))) * density_tail
    else:
        score_error = 0.0
    metric_error = float(np.linalg.norm(metric.contravariant, ord=2)) * score_error
    uncertainty = _block_uncertainty(
        queries=queries, samples=sample_fractional, weights=weights, frame_ids=view.frame_ids,
        temporal_frame_ids=catalog.temporal_weighting.frame_ids[catalog.temporal_weighting.temporal_mask],
        temporal_frame_weights=catalog.temporal_weighting.represented_time_weights[catalog.temporal_weighting.temporal_mask],
        block_count=options.uncertainty_blocks, covariance=covariance, truncation=truncation,
        domain=domain, options=options, target_shape=shape,
    )
    stderr = None if uncertainty is None else uncertainty.number_density_standard_error
    realization = _pack_realization(
        backend=options.backend, grid_shape=shape, block_shape=options.block_shape,
        number=number, probability=probability, score=score, metric_gradient=metric_gradient,
        hessian=hessian_supported, neff=neff, support=support, stderr=stderr,
        sparse_threshold=options.sparse_block_density_threshold, resources=resources,
    )
    number_residual = abs(float(np.sum(realization.number_density_dense()) * voxel) - mean_occupancy)
    probability_residual = abs(float(np.sum(realization.probability_density_dense()) * voxel) - 1.0)
    if options.backend is SpeciesDensityBackend.BLOCK_SPARSE and options.sparse_block_density_threshold > 0.0:
        # Sparse omission is explicit; the residual itself is the mass-loss certificate.
        pass
    certificate = DensityFieldErrorCertificate(
        image_density_absolute_bound=density_tail,
        image_score_covector_norm_bound=score_error,
        image_metric_gradient_norm_bound=metric_error,
        image_hessian_frobenius_bound=hessian_tail,
        discrete_number_normalization_residual=number_residual,
        discrete_probability_normalization_residual=probability_residual,
        support_node_count=int(np.count_nonzero(support)), total_node_count=node_count,
        certified_only_on_support=True, truncation_signature=truncation.signature,
    )
    integrals = SpeciesDensityIntegrals(
        observation_measure=observation, observation_measure_units=catalog.temporal_weighting.weight_units,
        ion_time_integral=float(np.sum(weights)), mean_occupancy_integral=mean_occupancy,
        probability_integral=1.0,
    )
    return PeriodicSpeciesDensityEstimate(
        species_atomic_number=catalog.species_atomic_number, species_label=catalog.species_label,
        catalog_signature=catalog.signature, domain=domain, kernel_covariance=covariance,
        analysis_metric=metric, image_truncation=truncation, integrals=integrals,
        realization=realization, error_certificate=certificate, block_uncertainty=uncertainty,
        metadata={
            "stage": PERIODIC_SPECIES_DENSITY_STAGE,
            "registration_signature": catalog.registration_signature,
            "coordinate_measure": domain.coordinate_measure.value,
            "kernel_operator": "normalized_triclinic_periodized_gaussian_image_sum",
            "minimum_image_gaussian_used": False,
            "evidence_channel": options.evidence_channel,
            "weight_units": catalog.temporal_weighting.weight_units,
            "local_support_claim_only": True,
            "sparse_omission_threshold": options.sparse_block_density_threshold,
        },
    )


def prepare_periodic_species_density_ladder(
    catalog: FrameworkAlignedIonSampleCatalog,
    domain: PeriodicDensityDomain,
    kernel_covariances: Sequence[GaussianKernelCovariance],
    *,
    options: SpeciesDensityOptions | None = None,
    resources: SpeciesDensityResourcePolicy | None = None,
) -> PeriodicSpeciesDensityLadder:
    """Estimate one species density at one or more explicit bandwidths."""
    if not isinstance(catalog, FrameworkAlignedIonSampleCatalog):
        raise TypeError("catalog must be FrameworkAlignedIonSampleCatalog.")
    if not isinstance(domain, PeriodicDensityDomain):
        raise TypeError("domain must be PeriodicDensityDomain.")
    kernels = tuple(kernel_covariances)
    if not kernels or any(not isinstance(item, GaussianKernelCovariance) for item in kernels):
        raise PeriodicSpeciesDensityInputError("kernel_covariances must contain GaussianKernelCovariance records.")
    resolved_options = options or SpeciesDensityOptions()
    resolved_resources = resources or SpeciesDensityResourcePolicy()
    estimates = tuple(_prepare_one_estimate(catalog, domain, kernel, resolved_options, resolved_resources) for kernel in kernels)
    return PeriodicSpeciesDensityLadder(
        catalog_signature=catalog.signature, domain_signature=domain.signature,
        estimates=estimates, options_signature=resolved_options.signature,
        resource_signature=resolved_resources.signature,
    )


def prepare_periodic_species_density(
    catalog: FrameworkAlignedIonSampleCatalog,
    domain: PeriodicDensityDomain,
    kernel_covariance: GaussianKernelCovariance,
    *,
    options: SpeciesDensityOptions | None = None,
    resources: SpeciesDensityResourcePolicy | None = None,
) -> PeriodicSpeciesDensityEstimate:
    """Estimate one bandwidth and return the single ladder member."""
    return prepare_periodic_species_density_ladder(
        catalog, domain, (kernel_covariance,), options=options, resources=resources
    ).estimates[0]


__all__ = [
    "ANALYSIS_GEOMETRY_METRIC_SCHEMA", "DENSITY_BLOCK_UNCERTAINTY_SCHEMA",
    "DENSITY_FIELD_ERROR_CERTIFICATE_SCHEMA", "GAUSSIAN_IMAGE_TRUNCATION_SCHEMA",
    "GAUSSIAN_KERNEL_COVARIANCE_SCHEMA", "PERIODIC_DENSITY_DOMAIN_SCHEMA",
    "PERIODIC_SPECIES_DENSITY_ESTIMATE_SCHEMA", "PERIODIC_SPECIES_DENSITY_LADDER_SCHEMA",
    "PERIODIC_SPECIES_DENSITY_REALIZATION_SCHEMA", "PERIODIC_SPECIES_DENSITY_STAGE",
    "SPECIES_DENSITY_INTEGRALS_SCHEMA", "SPECIES_DENSITY_OPTIONS_SCHEMA",
    "SPECIES_DENSITY_RESOURCE_POLICY_SCHEMA", "AnalysisGeometryMetric",
    "CompleteSystemBlockUncertainty", "DensityCoordinateMeasure", "DensityFieldErrorCertificate",
    "GaussianImageTruncation", "GaussianKernelCovariance", "PeriodicDensityDomain",
    "PeriodicSpeciesDensityError", "PeriodicSpeciesDensityEstimate", "PeriodicSpeciesDensityInputError",
    "PeriodicSpeciesDensityLadder", "PeriodicSpeciesDensityRealization",
    "PeriodicSpeciesDensityResourceError", "PeriodicSpeciesDensitySerializationError",
    "SpeciesDensityBackend", "SpeciesDensityIntegrals", "SpeciesDensityOptions",
    "SpeciesDensityResourcePolicy", "evaluate_periodized_gaussian_oracle",
    "prepare_gaussian_image_truncation", "prepare_periodic_species_density",
    "prepare_periodic_species_density_ladder",
]
