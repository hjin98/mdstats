"""Stage-C0A2 metric contracts and certified triclinic closest images."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Any, ClassVar, Mapping

import numpy as np

METRIC_CONTRACT_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
REGISTRATION_FIT_METRIC_SCHEMA = "mdstats.registration-fit-metric.v1"
ANALYSIS_GEOMETRY_METRIC_SCHEMA = "mdstats.analysis-geometry-metric.v1"
CLOSEST_PERIODIC_IMAGE_SCHEMA = "mdstats.closest-periodic-image.v1"


class MetricGeometryError(ValueError):
    """Base exception for Stage-C0A2 metric geometry."""


class MetricDefinitionError(MetricGeometryError):
    """Raised when a metric contract is not finite, symmetric, or positive definite."""


class ClosestImageSearchError(MetricGeometryError):
    """Raised when a certified closest-image search cannot be completed."""


class ClosestImageAmbiguityError(ClosestImageSearchError):
    """Raised when a closest-image-dependent claim requires a unique answer."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _matrix_tuple(value: object, *, name: str) -> tuple[tuple[float, float, float], ...]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3, 3) or not np.all(np.isfinite(array)):
        raise MetricDefinitionError(f"{name} must be a finite 3x3 matrix.")
    return tuple(tuple(float(item) for item in row) for row in array)


def _vector_tuple(value: object, *, name: str) -> tuple[float, float, float]:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (3,) or not np.all(np.isfinite(array)):
        raise MetricGeometryError(f"{name} must be a finite length-three vector.")
    return tuple(float(item) for item in array)


def _integer_vector_tuple(value: object, *, name: str) -> tuple[int, int, int]:
    array = np.asarray(value, dtype=np.int64)
    if array.shape != (3,):
        raise MetricGeometryError(f"{name} must be a length-three integer vector.")
    return tuple(int(item) for item in array)


@dataclass(frozen=True, slots=True)
class _MetricContract:
    """Immutable positive-definite row-vector metric."""

    matrix: tuple[tuple[float, float, float], ...]
    units: str = "dimensionless"
    coordinate_frame: str = "registered_cartesian"
    transformation_provenance: str = "declared_in_coordinate_frame"
    digest: str = ""

    SCHEMA: ClassVar[str] = ""

    def __post_init__(self) -> None:
        matrix = np.asarray(_matrix_tuple(self.matrix, name="matrix"), dtype=np.float64)
        symmetric = 0.5 * (matrix + matrix.T)
        scale = max(float(np.linalg.norm(matrix)), 1.0)
        if float(np.linalg.norm(matrix - matrix.T)) > 1.0e-12 * scale:
            raise MetricDefinitionError("Metric matrix must be symmetric.")
        eigenvalues = np.linalg.eigvalsh(symmetric)
        if eigenvalues[0] <= 0.0 or not np.all(np.isfinite(eigenvalues)):
            raise MetricDefinitionError("Metric matrix must be positive definite.")
        units = str(self.units).strip()
        coordinate_frame = str(self.coordinate_frame).strip()
        provenance = str(self.transformation_provenance).strip()
        if not units or not coordinate_frame or not provenance:
            raise MetricDefinitionError(
                "Metric units, coordinate_frame, and transformation_provenance are required."
            )
        matrix_tuple = tuple(tuple(float(item) for item in row) for row in symmetric)
        payload = {
            "schema": self.SCHEMA,
            "digest_algorithm": METRIC_CONTRACT_DIGEST_ALGORITHM,
            "matrix": [list(row) for row in matrix_tuple],
            "units": units,
            "coordinate_frame": coordinate_frame,
            "transformation_provenance": provenance,
        }
        expected = _digest(payload)
        if self.digest and self.digest != expected:
            raise MetricDefinitionError("Metric digest is inconsistent.")
        object.__setattr__(self, "matrix", matrix_tuple)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "coordinate_frame", coordinate_frame)
        object.__setattr__(self, "transformation_provenance", provenance)
        object.__setattr__(self, "digest", expected)

    @classmethod
    def euclidean(
        cls,
        *,
        units: str = "dimensionless",
        coordinate_frame: str = "registered_cartesian",
    ) -> "_MetricContract":
        return cls(
            matrix=_matrix_tuple(np.eye(3), name="matrix"),
            units=units,
            coordinate_frame=coordinate_frame,
            transformation_provenance="euclidean_in_declared_coordinate_frame",
        )

    def as_array(self) -> np.ndarray:
        return np.asarray(self.matrix, dtype=np.float64)

    def squared_norm(self, displacement: object) -> float:
        vector = np.asarray(_vector_tuple(displacement, name="displacement"))
        return float(vector @ self.as_array() @ vector)

    def norm(self, displacement: object) -> float:
        return float(np.sqrt(max(self.squared_norm(displacement), 0.0)))

    def transformed(
        self,
        coordinate_map: object,
        *,
        coordinate_frame: str,
        transformation_provenance: str | None = None,
    ) -> "_MetricContract":
        transform = np.asarray(
            _matrix_tuple(coordinate_map, name="coordinate_map"), dtype=np.float64
        )
        determinant = float(np.linalg.det(transform))
        if not np.isfinite(determinant) or abs(determinant) <= 1.0e-15:
            raise MetricDefinitionError("coordinate_map must be invertible.")
        inverse = np.linalg.inv(transform)
        transformed = inverse @ self.as_array() @ inverse.T
        provenance = transformation_provenance or (
            f"row_coordinate_transform_from:{self.digest}"
        )
        return type(self)(
            matrix=_matrix_tuple(transformed, name="matrix"),
            units=self.units,
            coordinate_frame=coordinate_frame,
            transformation_provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.SCHEMA,
            "digest_algorithm": METRIC_CONTRACT_DIGEST_ALGORITHM,
            "matrix": [list(row) for row in self.matrix],
            "units": self.units,
            "coordinate_frame": self.coordinate_frame,
            "transformation_provenance": self.transformation_provenance,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "_MetricContract":
        if payload.get("schema") != cls.SCHEMA:
            raise MetricDefinitionError(f"Unsupported {cls.__name__} schema.")
        return cls(
            matrix=_matrix_tuple(payload["matrix"], name="matrix"),
            units=str(payload["units"]),
            coordinate_frame=str(payload["coordinate_frame"]),
            transformation_provenance=str(payload["transformation_provenance"]),
            digest=str(payload.get("digest", "")),
        )


@dataclass(frozen=True, slots=True)
class RegistrationFitMetric(_MetricContract):
    """Metric used only for reference-group registration residuals."""

    SCHEMA: ClassVar[str] = REGISTRATION_FIT_METRIC_SCHEMA


@dataclass(frozen=True, slots=True)
class AnalysisGeometryMetric(_MetricContract):
    """Metric reserved for downstream periodic analysis geometry."""

    SCHEMA: ClassVar[str] = ANALYSIS_GEOMETRY_METRIC_SCHEMA


@dataclass(frozen=True, slots=True)
class ClosestImageOptions:
    absolute_tie_tolerance: float = 1.0e-12
    relative_tie_tolerance: float = 1.0e-10
    singular_value_tolerance: float = 1.0e-14
    maximum_candidates: int = 2_000_000

    def __post_init__(self) -> None:
        for name in (
            "absolute_tie_tolerance",
            "relative_tie_tolerance",
            "singular_value_tolerance",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ClosestImageSearchError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if isinstance(self.maximum_candidates, bool) or int(self.maximum_candidates) < 1:
            raise ClosestImageSearchError("maximum_candidates must be a positive integer.")
        object.__setattr__(self, "maximum_candidates", int(self.maximum_candidates))

    def to_dict(self) -> dict[str, Any]:
        return {
            "absolute_tie_tolerance": self.absolute_tie_tolerance,
            "relative_tie_tolerance": self.relative_tie_tolerance,
            "singular_value_tolerance": self.singular_value_tolerance,
            "maximum_candidates": self.maximum_candidates,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ClosestImageOptions":
        return cls(
            absolute_tie_tolerance=float(payload["absolute_tie_tolerance"]),
            relative_tie_tolerance=float(payload["relative_tie_tolerance"]),
            singular_value_tolerance=float(payload["singular_value_tolerance"]),
            maximum_candidates=int(payload["maximum_candidates"]),
        )


@dataclass(frozen=True, slots=True)
class ClosestPeriodicImage:
    displacement: tuple[float, float, float]
    image_shift: tuple[int, int, int]
    vector: tuple[float, float, float]
    distance: float
    second_distance: float | None
    branch_separation: float | None
    ambiguous: bool
    candidates_examined: int
    certified: bool
    metric_digest: str
    options: ClosestImageOptions

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "displacement", _vector_tuple(self.displacement, name="displacement")
        )
        object.__setattr__(
            self, "image_shift", _integer_vector_tuple(self.image_shift, name="image_shift")
        )
        object.__setattr__(self, "vector", _vector_tuple(self.vector, name="vector"))
        if self.distance < 0.0 or not np.isfinite(self.distance):
            raise ClosestImageSearchError("distance must be finite and nonnegative.")
        if self.second_distance is not None:
            if self.second_distance < self.distance or not np.isfinite(self.second_distance):
                raise ClosestImageSearchError("second_distance is inconsistent.")
        if self.branch_separation is not None and self.branch_separation < 0.0:
            raise ClosestImageSearchError("branch_separation must be nonnegative.")
        if len(self.metric_digest) != 64:
            raise ClosestImageSearchError("metric_digest must be SHA-256.")
        if not self.certified:
            raise ClosestImageSearchError("Uncertified closest-image results are forbidden.")

    def require_unique(self, claim: str) -> None:
        if self.ambiguous:
            raise ClosestImageAmbiguityError(
                f"{claim} requires a unique periodic closest image."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CLOSEST_PERIODIC_IMAGE_SCHEMA,
            "displacement": list(self.displacement),
            "image_shift": list(self.image_shift),
            "vector": list(self.vector),
            "distance": self.distance,
            "second_distance": self.second_distance,
            "branch_separation": self.branch_separation,
            "ambiguous": self.ambiguous,
            "candidates_examined": self.candidates_examined,
            "certified": self.certified,
            "metric_digest": self.metric_digest,
            "options": self.options.to_dict(),
        }


def closest_periodic_image(
    displacement: object,
    *,
    cell: object,
    metric: RegistrationFitMetric | AnalysisGeometryMetric,
    options: ClosestImageOptions | None = None,
) -> ClosestPeriodicImage:
    """Return the certified closest lattice image under a declared metric.

    The finite enumeration box follows directly from the lower singular-value
    bound in ``metric_geometry_spec.md``. Fractional rounding supplies only the
    initial upper bound.
    """

    active = options or ClosestImageOptions()
    delta = np.asarray(_vector_tuple(displacement, name="displacement"), dtype=np.float64)
    lattice = np.asarray(_matrix_tuple(cell, name="cell"), dtype=np.float64)
    determinant = float(np.linalg.det(lattice))
    if not np.isfinite(determinant) or abs(determinant) <= 1.0e-15:
        raise ClosestImageSearchError("cell must be finite and full rank.")
    metric_array = metric.as_array()
    factor = np.linalg.cholesky(metric_array)
    transformed_lattice = lattice @ factor
    singular_values = np.linalg.svd(transformed_lattice, compute_uv=False)
    sigma_min = float(singular_values[-1])
    if not np.isfinite(sigma_min) or sigma_min <= active.singular_value_tolerance:
        raise ClosestImageSearchError(
            "Metric-transformed lattice is singular within closest-image tolerance."
        )

    fractional = delta @ np.linalg.inv(lattice)
    seed = np.rint(fractional).astype(np.int64)
    seed_vector = delta - seed @ lattice
    seed_distance = metric.norm(seed_vector)
    # A certified second-best upper bound is obtained from the six adjacent
    # integer lattice points. Enumerating every candidate whose lower bound can
    # beat that upper bound certifies both the nearest and runner-up branches.
    adjacent_distances: list[float] = []
    for axis in range(3):
        for direction in (-1, 1):
            neighbor = seed.copy()
            neighbor[axis] += direction
            adjacent_distances.append(metric.norm(delta - neighbor @ lattice))
    second_upper_bound = min(adjacent_distances)
    radius = max(seed_distance, second_upper_bound) / sigma_min
    padding = 8.0 * np.finfo(np.float64).eps * max(float(np.linalg.norm(fractional)), 1.0)
    lower = np.floor(fractional - radius - padding).astype(np.int64)
    upper = np.ceil(fractional + radius + padding).astype(np.int64)
    widths = upper - lower + 1
    candidate_count = int(np.prod(widths, dtype=np.int64))
    if candidate_count > active.maximum_candidates:
        raise ClosestImageSearchError(
            "Certified closest-image enumeration exceeds maximum_candidates: "
            f"{candidate_count}>{active.maximum_candidates}."
        )

    ranked: list[tuple[float, tuple[int, int, int], np.ndarray]] = []
    ranges = [range(int(lower[k]), int(upper[k]) + 1) for k in range(3)]
    for candidate_tuple in itertools.product(*ranges):
        candidate = np.asarray(candidate_tuple, dtype=np.int64)
        vector = delta - candidate @ lattice
        distance_squared = float(vector @ metric_array @ vector)
        if distance_squared < 0.0 and abs(distance_squared) <= 1.0e-13:
            distance_squared = 0.0
        if distance_squared < 0.0 or not np.isfinite(distance_squared):
            raise ClosestImageSearchError("Encountered an invalid metric distance.")
        ranked.append((distance_squared, candidate_tuple, vector))

    ranked.sort(key=lambda item: (item[0], item[1]))
    best_squared, best_shift, best_vector = ranked[0]
    second_squared = ranked[1][0] if len(ranked) > 1 else None
    best_distance = float(np.sqrt(best_squared))
    second_distance = None if second_squared is None else float(np.sqrt(second_squared))
    separation = (
        None if second_distance is None else max(0.0, second_distance - best_distance)
    )
    tie_threshold = active.absolute_tie_tolerance + active.relative_tie_tolerance * max(
        best_distance,
        1.0,
    )
    ambiguous = second_distance is not None and separation <= tie_threshold
    return ClosestPeriodicImage(
        displacement=_vector_tuple(delta, name="displacement"),
        image_shift=_integer_vector_tuple(best_shift, name="image_shift"),
        vector=_vector_tuple(best_vector, name="vector"),
        distance=best_distance,
        second_distance=second_distance,
        branch_separation=separation,
        ambiguous=bool(ambiguous),
        candidates_examined=candidate_count,
        certified=True,
        metric_digest=metric.digest,
        options=active,
    )
