"""Analysis-owned registration, periodic-mean, spread, and grid diagnostics.

This module implements architecture gate LD0-R2.  It contains no density
estimator and no rendering dependency.  Periodic means use a deterministic
multi-start flat-torus Fréchet/Karcher iteration.  The mathematical construction
follows Fréchet (1948) and Karcher (1977); the start policy, ambiguity test,
chunked weighted-medoid search, reciprocal-grid diagnostic, and registration
validation are project-specific policies.  LD7 temporal spread subsampling adapts standard stratified random sampling (Cochran, 1977) to ordered weighted trajectory frames; the deterministic strata, seed policy, and weight transfer are project-specific.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from .._neighbors import minimum_image_geometry
from .numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalResourceError,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

CELL_EQUIVALENCE_ABSOLUTE_TOLERANCE = 1.0e-10
CELL_EQUIVALENCE_RELATIVE_TOLERANCE = 1.0e-10
SPREAD_QUANTILE_METHOD = "linear"
PERIODIC_MEAN_DIAGNOSTIC_SCHEMA = "mdstats.periodic-mean-diagnostic.v1"
PERIODIC_SPREAD_DIAGNOSTIC_SCHEMA = "mdstats.periodic-spread-diagnostic.v3"
BASIN_SPREAD_DIAGNOSTIC_SCHEMA = "mdstats.basin-spread-diagnostic.v1"
SPREAD_CONVERGENCE_DIAGNOSTIC_SCHEMA = "mdstats.spread-convergence-diagnostic.v1"
RECIPROCAL_RESOLUTION_SCHEMA = "mdstats.reciprocal-resolution.v1"
CELL_EQUIVALENCE_SCHEMA = "mdstats.cell-equivalence.v1"


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise DensityNumericalInputError(
            f"{name} must be {ndim}-dimensional; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise DensityNumericalInputError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _validated_cell(cell: Any) -> FloatArray:
    matrix = np.asarray(cell, dtype=np.float64)
    if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
        raise DensityNumericalInputError("cell must be a finite 3x3 matrix.")
    if abs(float(np.linalg.det(matrix))) <= 1.0e-12:
        raise DensityNumericalInputError("cell must be nonsingular.")
    return matrix


def _validated_weights(weights: Any, n_samples: int) -> FloatArray:
    values = np.asarray(weights, dtype=np.float64)
    if values.shape != (n_samples,) or np.any(~np.isfinite(values)):
        raise DensityNumericalInputError("weights must be finite and align with samples.")
    if np.any(values < 0.0):
        raise DensityNumericalInputError("weights must be nonnegative.")
    total = float(np.sum(values))
    if total <= 0.0:
        raise DensityNumericalInputError("weights must have positive total measure.")
    normalized = np.asarray(values / total, dtype=np.float64)
    normalized.setflags(write=False)
    return normalized


def _reference_length(cell: FloatArray) -> float:
    return max(1.0, float(np.max(np.linalg.norm(cell, axis=1))))


@dataclass(frozen=True, slots=True)
class PeriodicMeanPolicy:
    """Deterministic numerical policy for one periodic Fréchet mean."""

    max_iterations: int = 128
    update_tolerance_scale: float = 1.0e-12
    objective_relative_tolerance: float = 1.0e-12
    mean_separation_tolerance_scale: float = 1.0e-8
    medoid_block_size: int = 64
    certified_fast_path: bool = False
    minimum_valid_reference_fraction: float = 0.50
    minimum_valid_reference_count: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.max_iterations, bool) or int(self.max_iterations) < 1:
            raise DensityNumericalInputError("max_iterations must be a positive integer.")
        if isinstance(self.medoid_block_size, bool) or int(self.medoid_block_size) < 1:
            raise DensityNumericalInputError("medoid_block_size must be a positive integer.")
        if not isinstance(self.certified_fast_path, (bool, np.bool_)):
            raise DensityNumericalInputError("certified_fast_path must be boolean.")
        object.__setattr__(self, "certified_fast_path", bool(self.certified_fast_path))
        for name in (
            "update_tolerance_scale",
            "objective_relative_tolerance",
            "mean_separation_tolerance_scale",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise DensityNumericalInputError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        fraction = float(self.minimum_valid_reference_fraction)
        if not np.isfinite(fraction) or not 0.0 <= fraction <= 1.0:
            raise DensityNumericalInputError(
                "minimum_valid_reference_fraction must lie in [0, 1]."
            )
        count = self.minimum_valid_reference_count
        if isinstance(count, bool) or int(count) < 0:
            raise DensityNumericalInputError(
                "minimum_valid_reference_count must be a nonnegative integer."
            )
        object.__setattr__(self, "max_iterations", int(self.max_iterations))
        object.__setattr__(self, "medoid_block_size", int(self.medoid_block_size))
        object.__setattr__(self, "minimum_valid_reference_fraction", fraction)
        object.__setattr__(self, "minimum_valid_reference_count", int(count))


@dataclass(frozen=True, slots=True)
class CellEquivalenceReport:
    """Frobenius-norm equivalence report for source and display cells."""

    equivalent: bool
    tolerance: float
    maximum_mismatch: float
    maximum_mismatch_frame_position: int
    mismatch_by_frame: FloatArray
    schema_version: str = CELL_EQUIVALENCE_SCHEMA

    def __post_init__(self) -> None:
        mismatch = _readonly(
            self.mismatch_by_frame,
            np.float64,
            ndim=1,
            name="mismatch_by_frame",
        )
        if mismatch.size < 1:
            raise DensityNumericalInputError("mismatch_by_frame must be nonempty.")
        position = int(self.maximum_mismatch_frame_position)
        if position < 0 or position >= mismatch.size:
            raise DensityNumericalInputError("maximum_mismatch_frame_position is invalid.")
        object.__setattr__(self, "mismatch_by_frame", mismatch)
        object.__setattr__(self, "tolerance", float(self.tolerance))
        object.__setattr__(self, "maximum_mismatch", float(self.maximum_mismatch))
        object.__setattr__(self, "maximum_mismatch_frame_position", position)

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "cell_equivalence_schema": self.schema_version,
            "cell_equivalence_tolerance": self.tolerance,
            "cell_equivalence_maximum_mismatch": self.maximum_mismatch,
            "cell_equivalence_maximum_mismatch_frame_position": (
                self.maximum_mismatch_frame_position
            ),
            "cell_equivalent": self.equivalent,
        }


def evaluate_cell_equivalence(
    source_cells: Any,
    display_cell: Any,
    *,
    absolute_tolerance: float = CELL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    relative_tolerance: float = CELL_EQUIVALENCE_RELATIVE_TOLERANCE,
) -> CellEquivalenceReport:
    """Return the exact architecture-standard laboratory-cell comparison."""

    cells = np.asarray(source_cells, dtype=np.float64)
    display = _validated_cell(display_cell)
    if cells.ndim == 2:
        cells = cells[None, :, :]
    if cells.ndim != 3 or cells.shape[1:] != (3, 3):
        raise DensityNumericalInputError("source_cells must have shape (n_frames, 3, 3).")
    if cells.shape[0] < 1 or np.any(~np.isfinite(cells)):
        raise DensityNumericalInputError("source_cells must be nonempty and finite.")
    atol = float(absolute_tolerance)
    rtol = float(relative_tolerance)
    if not np.isfinite(atol) or atol < 0.0 or not np.isfinite(rtol) or rtol < 0.0:
        raise DensityNumericalInputError("Cell-equivalence tolerances must be finite and nonnegative.")
    tolerance = atol + rtol * float(np.linalg.norm(display, ord="fro"))
    mismatch = np.linalg.norm(cells - display[None, :, :], axis=(1, 2))
    position = int(np.argmax(mismatch))
    maximum = float(mismatch[position])
    return CellEquivalenceReport(
        equivalent=bool(maximum <= tolerance),
        tolerance=tolerance,
        maximum_mismatch=maximum,
        maximum_mismatch_frame_position=position,
        mismatch_by_frame=mismatch,
    )


def require_equivalent_laboratory_density_cells(
    source_cells: Any,
    display_cell: Any,
    *,
    field_context: str,
) -> CellEquivalenceReport:
    """Validate the periodic cell identification used by laboratory density."""

    report = evaluate_cell_equivalence(source_cells, display_cell)
    if not report.equivalent:
        raise DensityNumericalInputError(
            "Periodic laboratory-frame density requires every selected source cell "
            "to equal the display cell within the architecture-standard Frobenius "
            f"tolerance. {field_context}: maximum mismatch="
            f"{report.maximum_mismatch:.6g} A, tolerance={report.tolerance:.6g} A, "
            f"frame position={report.maximum_mismatch_frame_position}. Laboratory "
            "trajectories remain supported; use material/framework_registered "
            "density or a constant display-equivalent cell."
        )
    return report


@dataclass(frozen=True, slots=True)
class ReciprocalResolutionDiagnostic:
    """Shortest reciprocal sampling-lattice vector and derived interval."""

    reciprocal_interval: float
    shortest_vector_norm: float
    integer_vector: IntArray
    cartesian_vector: FloatArray
    enumeration_bound: int
    schema_version: str = RECIPROCAL_RESOLUTION_SCHEMA

    def __post_init__(self) -> None:
        integer = _readonly(
            self.integer_vector,
            np.int64,
            ndim=1,
            name="integer_vector",
        )
        cartesian = _readonly(
            self.cartesian_vector,
            np.float64,
            ndim=1,
            name="cartesian_vector",
        )
        if integer.shape != (3,) or cartesian.shape != (3,):
            raise DensityNumericalInputError("Reciprocal vectors must have shape (3,).")
        if not np.any(integer):
            raise DensityNumericalInputError("integer_vector must be nonzero.")
        if self.reciprocal_interval <= 0.0 or self.shortest_vector_norm <= 0.0:
            raise DensityNumericalInputError("Reciprocal diagnostic values must be positive.")
        object.__setattr__(self, "integer_vector", integer)
        object.__setattr__(self, "cartesian_vector", cartesian)
        object.__setattr__(self, "enumeration_bound", int(self.enumeration_bound))

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "reciprocal_resolution_schema": self.schema_version,
            "h_reciprocal": self.reciprocal_interval,
            "shortest_reciprocal_sampling_vector_norm": self.shortest_vector_norm,
            "shortest_reciprocal_sampling_integer_vector": tuple(
                int(v) for v in self.integer_vector
            ),
            "shortest_reciprocal_sampling_cartesian_vector": tuple(
                float(v) for v in self.cartesian_vector
            ),
            "reciprocal_enumeration_bound": self.enumeration_bound,
        }


def reciprocal_resolution_diagnostic(
    cell: Any,
    grid_shape: tuple[int, int, int],
    *,
    maximum_enumeration_bound: int = 4096,
) -> ReciprocalResolutionDiagnostic:
    """Return a certified shortest-vector diagnostic for the sampling lattice.

    With row-vector convention, the real-space sampling basis is
    ``diag(1/N) @ H`` and its angular reciprocal basis is
    ``2*pi*diag(N) @ H**(-T)``.  A singular-value lower bound gives a finite
    cube containing every integer vector that can improve the shortest basis
    vector.  Exhaustive lexicographic enumeration inside that cube is therefore
    exact.  This bounded-enumeration proof is project-specific.
    """

    matrix = _validated_cell(cell)
    if len(grid_shape) != 3:
        raise DensityNumericalInputError("grid_shape must contain three entries.")
    shape_values: list[int] = []
    for value in grid_shape:
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
            raise DensityNumericalInputError("grid_shape entries must be positive integers.")
        result = int(value)
        if result <= 0:
            raise DensityNumericalInputError("grid_shape entries must be positive integers.")
        shape_values.append(result)
    shape = np.asarray(shape_values, dtype=np.float64)
    basis = 2.0 * np.pi * (np.diag(shape) @ np.linalg.inv(matrix).T)
    row_norms = np.linalg.norm(basis, axis=1)
    upper = float(np.min(row_norms))
    singular_min = float(np.min(np.linalg.svd(basis, compute_uv=False)))
    if singular_min <= 0.0 or not np.isfinite(singular_min):
        raise DensityNumericalInputError("Could not certify the reciprocal sampling lattice.")
    bound = max(1, int(np.floor(upper / singular_min)) + 1)
    if bound > int(maximum_enumeration_bound):
        raise DensityNumericalResourceError(
            "The certified reciprocal-vector enumeration bound "
            f"{bound} exceeds maximum_enumeration_bound={maximum_enumeration_bound}."
        )

    best_norm = float("inf")
    best_integer: tuple[int, int, int] | None = None
    best_cartesian: FloatArray | None = None
    tolerance = 5.0e-15 * max(1.0, upper)
    for i in range(-bound, bound + 1):
        for j in range(-bound, bound + 1):
            for k in range(-bound, bound + 1):
                integer = (i, j, k)
                if integer == (0, 0, 0):
                    continue
                first_nonzero = next(value for value in integer if value != 0)
                if first_nonzero < 0:
                    continue
                cartesian = np.asarray(integer, dtype=np.float64) @ basis
                norm = float(np.linalg.norm(cartesian))
                if norm < best_norm - tolerance:
                    best_norm = norm
                    best_integer = integer
                    best_cartesian = np.asarray(cartesian, dtype=np.float64)
                elif abs(norm - best_norm) <= tolerance and (
                    best_integer is None or integer < best_integer
                ):
                    best_norm = norm
                    best_integer = integer
                    best_cartesian = np.asarray(cartesian, dtype=np.float64)
    assert best_integer is not None and best_cartesian is not None
    return ReciprocalResolutionDiagnostic(
        reciprocal_interval=2.0 * np.pi / best_norm,
        shortest_vector_norm=best_norm,
        integer_vector=np.asarray(best_integer, dtype=np.int64),
        cartesian_vector=best_cartesian,
        enumeration_bound=bound,
    )


@dataclass(frozen=True, slots=True)
class PeriodicMeanDiagnostic:
    """Selected periodic mean and deterministic multi-start diagnostics."""

    mean_cartesian: FloatArray
    mean_fractional: FloatArray
    mean_converged: bool
    iteration_count: int
    final_update_norm: float
    objective_value: float
    mean_ambiguity_detected: bool
    candidate_solution_count: int
    start_count: int
    schema_version: str = PERIODIC_MEAN_DIAGNOSTIC_SCHEMA

    def __post_init__(self) -> None:
        cartesian = _readonly(
            self.mean_cartesian,
            np.float64,
            ndim=1,
            name="mean_cartesian",
        )
        fractional = _readonly(
            self.mean_fractional,
            np.float64,
            ndim=1,
            name="mean_fractional",
        )
        if cartesian.shape != (3,) or fractional.shape != (3,):
            raise DensityNumericalInputError("Periodic mean coordinates must have shape (3,).")
        if not np.isfinite(self.final_update_norm) or self.final_update_norm < 0.0:
            raise DensityNumericalInputError("final_update_norm must be finite and nonnegative.")
        if not np.isfinite(self.objective_value) or self.objective_value < 0.0:
            raise DensityNumericalInputError("objective_value must be finite and nonnegative.")
        object.__setattr__(self, "mean_cartesian", cartesian)
        object.__setattr__(self, "mean_fractional", fractional)
        object.__setattr__(self, "iteration_count", int(self.iteration_count))
        object.__setattr__(self, "candidate_solution_count", int(self.candidate_solution_count))
        object.__setattr__(self, "start_count", int(self.start_count))

    @property
    def valid_for_reference(self) -> bool:
        return bool(self.mean_converged and not self.mean_ambiguity_detected)

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "mean_converged": self.mean_converged,
            "iteration_count": self.iteration_count,
            "final_update_norm": self.final_update_norm,
            "objective_value": self.objective_value,
            "mean_ambiguity_detected": self.mean_ambiguity_detected,
            "candidate_solution_count": self.candidate_solution_count,
            "start_count": self.start_count,
        }


@dataclass(frozen=True, slots=True)
class _MeanIterationResult:
    cartesian: FloatArray
    fractional: FloatArray
    converged: bool
    iterations: int
    final_update_norm: float
    objective: float
    start_index: int


def _fold_fractional(samples: FloatArray, pbc: BoolArray) -> FloatArray:
    folded = np.array(samples, dtype=np.float64, copy=True)
    for axis, periodic in enumerate(pbc):
        if periodic:
            folded[..., axis] -= np.floor(folded[..., axis])
    return folded


def _objective(
    point_cartesian: FloatArray,
    sample_cartesian: FloatArray,
    weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
) -> float:
    vectors, distances, _ = minimum_image_geometry(
        sample_cartesian - point_cartesian,
        cell=cell,
        pbc=pbc,
    )
    del vectors
    return float(np.sum(weights * distances * distances))


def _weighted_medoid_index(
    sample_cartesian: FloatArray,
    weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
    block_size: int,
) -> int:
    n_samples = sample_cartesian.shape[0]
    best_index = 0
    best_objective = float("inf")
    tolerance = 5.0e-15 * max(1.0, _reference_length(cell) ** 2)
    for start in range(0, n_samples, block_size):
        stop = min(n_samples, start + block_size)
        candidates = sample_cartesian[start:stop]
        raw = sample_cartesian[None, :, :] - candidates[:, None, :]
        _vectors, distances, _shifts = minimum_image_geometry(
            raw,
            cell=cell,
            pbc=pbc,
        )
        objectives = np.sum(distances * distances * weights[None, :], axis=1)
        for local, value in enumerate(objectives):
            index = start + local
            objective = float(value)
            if objective < best_objective - tolerance:
                best_index = index
                best_objective = objective
    return best_index


def _circular_start(
    folded: FloatArray,
    weights: FloatArray,
    pbc: BoolArray,
) -> FloatArray:
    result = np.empty(3, dtype=np.float64)
    for axis, periodic in enumerate(pbc):
        if periodic:
            phase = np.sum(weights * np.exp(2j * np.pi * folded[:, axis]))
            result[axis] = float(np.mod(np.angle(phase) / (2.0 * np.pi), 1.0))
        else:
            result[axis] = float(np.sum(weights * folded[:, axis]))
    return result


def _iterate_mean(
    start_fractional: FloatArray,
    sample_cartesian: FloatArray,
    weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
    update_tolerance: float,
    max_iterations: int,
    start_index: int,
) -> _MeanIterationResult:
    inverse = np.linalg.inv(cell)
    fractional = _fold_fractional(np.asarray(start_fractional)[None, :], pbc)[0]
    point = fractional @ cell
    converged = False
    final_norm = 0.0
    iterations = 0
    for iteration in range(1, max_iterations + 1):
        vectors, _distances, _shifts = minimum_image_geometry(
            sample_cartesian - point,
            cell=cell,
            pbc=pbc,
        )
        delta = np.sum(weights[:, None] * vectors, axis=0)
        final_norm = float(np.linalg.norm(delta))
        point = point + delta
        fractional = point @ inverse
        fractional = _fold_fractional(fractional[None, :], pbc)[0]
        point = fractional @ cell
        iterations = iteration
        if final_norm <= update_tolerance:
            converged = True
            break
    objective = _objective(
        point,
        sample_cartesian,
        weights,
        cell=cell,
        pbc=pbc,
    )
    return _MeanIterationResult(
        cartesian=np.asarray(point, dtype=np.float64),
        fractional=np.asarray(fractional, dtype=np.float64),
        converged=converged,
        iterations=iterations,
        final_update_norm=final_norm,
        objective=objective,
        start_index=start_index,
    )


def _certified_single_start_periodic_mean(
    folded: FloatArray,
    sample_cartesian: FloatArray,
    normalized_weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
    policy: PeriodicMeanPolicy,
) -> PeriodicMeanDiagnostic | None:
    """Return a proven-unique mean without the O(N^2) medoid search when safe.

    A flat torus has injectivity radius half the shortest nonzero periodic
    lattice translation.  If every sample lies strictly inside a ball of radius
    one half of that injectivity radius around a converged circular-start mean,
    the data occupy one strongly convex Euclidean chart.  The Fréchet objective
    is then uniquely minimized by that converged solution, so the expensive
    exact weighted-medoid start and ambiguity multi-start search cannot change
    the answer.  Ambiguous/mobile distributions fall back to the authoritative
    multi-start algorithm unchanged.
    """

    if not bool(policy.certified_fast_path):
        return None
    start = _circular_start(folded, normalized_weights, pbc)
    length = _reference_length(cell)
    update_tolerance = policy.update_tolerance_scale * length
    result = _iterate_mean(
        start,
        sample_cartesian,
        normalized_weights,
        cell=cell,
        pbc=pbc,
        update_tolerance=update_tolerance,
        max_iterations=policy.max_iterations,
        start_index=0,
    )
    if not result.converged:
        return None

    # Minkowski reduction exposes a shortest periodic lattice basis vector for
    # the active periodic subspace.  The conservative quarter-shortest-vector
    # radius is half the torus injectivity radius and therefore a strong-convexity
    # certificate rather than a heuristic spread threshold.
    from ase.geometry import minkowski_reduce
    from ase.geometry.geometry import complete_cell

    reduced, _operation = minkowski_reduce(complete_cell(cell), pbc=pbc)
    reduced = np.asarray(reduced, dtype=np.float64)
    periodic_norms = np.linalg.norm(reduced[np.asarray(pbc, dtype=bool)], axis=1)
    if periodic_norms.size == 0:
        shortest_translation = float("inf")
    else:
        shortest_translation = float(np.min(periodic_norms))
    _vectors, distances, _shifts = minimum_image_geometry(
        sample_cartesian - result.cartesian, cell=cell, pbc=pbc
    )
    maximum_distance = float(np.max(distances)) if distances.size else 0.0
    certificate_radius = 0.25 * shortest_translation
    margin = 64.0 * np.finfo(np.float64).eps * max(1.0, shortest_translation)
    if not maximum_distance < certificate_radius - margin:
        return None
    return PeriodicMeanDiagnostic(
        mean_cartesian=result.cartesian,
        mean_fractional=result.fractional,
        mean_converged=True,
        iteration_count=result.iterations,
        final_update_norm=result.final_update_norm,
        objective_value=result.objective,
        mean_ambiguity_detected=False,
        candidate_solution_count=1,
        start_count=1,
    )


def periodic_frechet_mean_diagnostic(
    fractional_samples: Any,
    *,
    weights: Any,
    cell: Any,
    pbc: Any,
    policy: PeriodicMeanPolicy | None = None,
) -> PeriodicMeanDiagnostic:
    """Return a deterministic multi-start flat-torus mean and diagnostics."""

    samples = np.asarray(fractional_samples, dtype=np.float64)
    matrix = _validated_cell(cell)
    periodic = np.asarray(pbc, dtype=bool)
    if samples.ndim != 2 or samples.shape[1:] != (3,) or samples.shape[0] < 1:
        raise DensityNumericalInputError("fractional_samples must have shape (n_samples, 3).")
    if periodic.shape != (3,):
        raise DensityNumericalInputError("pbc must have shape (3,).")
    normalized_weights = _validated_weights(weights, samples.shape[0])
    active_policy = PeriodicMeanPolicy() if policy is None else policy
    if not isinstance(active_policy, PeriodicMeanPolicy):
        raise TypeError("policy must be PeriodicMeanPolicy or None.")

    folded = _fold_fractional(samples, periodic)
    sample_cartesian = folded @ matrix
    certified = _certified_single_start_periodic_mean(
        folded,
        sample_cartesian,
        normalized_weights,
        cell=matrix,
        pbc=periodic,
        policy=active_policy,
    )
    if certified is not None:
        return certified
    medoid_index = _weighted_medoid_index(
        sample_cartesian,
        normalized_weights,
        cell=matrix,
        pbc=periodic,
        block_size=active_policy.medoid_block_size,
    )
    _vectors, distances_from_medoid, _shifts = minimum_image_geometry(
        sample_cartesian - sample_cartesian[medoid_index],
        cell=matrix,
        pbc=periodic,
    )
    farthest_index = int(np.argmax(distances_from_medoid))
    starts = [
        _circular_start(folded, normalized_weights, periodic),
        folded[medoid_index],
        folded[0],
        folded[farthest_index],
    ]

    length = _reference_length(matrix)
    update_tolerance = active_policy.update_tolerance_scale * length
    separation_tolerance = active_policy.mean_separation_tolerance_scale * length
    unique_starts: list[FloatArray] = []
    for start in starts:
        point = np.asarray(start, dtype=np.float64)
        duplicate = False
        for existing in unique_starts:
            raw = (point - existing) @ matrix
            _mic, distance, _shift = minimum_image_geometry(
                raw[None, :],
                cell=matrix,
                pbc=periodic,
            )
            if float(distance[0]) <= update_tolerance:
                duplicate = True
                break
        if not duplicate:
            unique_starts.append(point)

    iterations = [
        _iterate_mean(
            start,
            sample_cartesian,
            normalized_weights,
            cell=matrix,
            pbc=periodic,
            update_tolerance=update_tolerance,
            max_iterations=active_policy.max_iterations,
            start_index=index,
        )
        for index, start in enumerate(unique_starts)
    ]
    converged = [result for result in iterations if result.converged]
    selection_pool = converged if converged else iterations
    selected = min(selection_pool, key=lambda result: (result.objective, result.start_index))

    unique_solutions: list[_MeanIterationResult] = []
    for result in converged:
        duplicate = False
        for existing in unique_solutions:
            raw = result.cartesian - existing.cartesian
            _mic, distance, _shift = minimum_image_geometry(
                raw[None, :],
                cell=matrix,
                pbc=periodic,
            )
            if float(distance[0]) <= separation_tolerance:
                duplicate = True
                break
        if not duplicate:
            unique_solutions.append(result)

    ambiguity = False
    if len(unique_solutions) > 1:
        best_objective = min(result.objective for result in unique_solutions)
        objective_scale = max(1.0, abs(best_objective))
        near_best = [
            result
            for result in unique_solutions
            if abs(result.objective - best_objective)
            <= active_policy.objective_relative_tolerance * objective_scale
        ]
        ambiguity = len(near_best) > 1

    return PeriodicMeanDiagnostic(
        mean_cartesian=selected.cartesian,
        mean_fractional=selected.fractional,
        mean_converged=selected.converged,
        iteration_count=selected.iterations,
        final_update_norm=selected.final_update_norm,
        objective_value=selected.objective,
        mean_ambiguity_detected=ambiguity,
        candidate_solution_count=len(unique_solutions),
        start_count=len(unique_starts),
    )


@dataclass(frozen=True, slots=True)
class BasinSpreadDiagnostic:
    """One qualified basin contribution to a basin-aware item spread."""

    item_index: int
    basin_id: int
    mean_cartesian: FloatArray
    standard_deviation: float
    mean_square_radius: float
    represented_weight: float
    source_sample_count: int
    sampled_count: int
    replicate_count: int
    compact_fast_path_count: int
    fallback_mean_count: int
    schema_version: str = BASIN_SPREAD_DIAGNOSTIC_SCHEMA

    def __post_init__(self) -> None:
        mean = _readonly(self.mean_cartesian, np.float64, ndim=1, name="mean_cartesian")
        if mean.shape != (3,):
            raise DensityNumericalInputError("Basin mean_cartesian must have shape (3,).")
        for name in ("item_index", "basin_id", "source_sample_count", "sampled_count",
                     "replicate_count", "compact_fast_path_count", "fallback_mean_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) < 0:
                raise DensityNumericalInputError(f"{name} must be a nonnegative integer.")
            object.__setattr__(self, name, int(value))
        for name in ("standard_deviation", "mean_square_radius", "represented_weight"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise DensityNumericalInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "mean_cartesian", mean)

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema_version,
            "item_index": self.item_index,
            "basin_id": self.basin_id,
            "mean_cartesian": tuple(float(v) for v in self.mean_cartesian),
            "standard_deviation": self.standard_deviation,
            "mean_square_radius": self.mean_square_radius,
            "represented_weight": self.represented_weight,
            "source_sample_count": self.source_sample_count,
            "sampled_count": self.sampled_count,
            "replicate_count": self.replicate_count,
            "compact_fast_path_count": self.compact_fast_path_count,
            "fallback_mean_count": self.fallback_mean_count,
        }


@dataclass(frozen=True, slots=True)
class SpreadConvergenceDiagnostic:
    """Replicate dispersion and progressive convergence for one spread reference."""

    replicate_reference_standard_deviations: FloatArray
    progressive_reference_standard_deviations: FloatArray
    reference_standard_error: float | None
    confidence_level: float
    confidence_interval_low: float | None
    confidence_interval_high: float | None
    relative_confidence_half_width: float | None
    requested_replicate_count: int
    realized_replicate_count: int
    max_replicate_count: int
    effective_sample_count: int
    escalation_occurred: bool
    convergence_relative_change: float | None
    converged: bool
    schema_version: str = SPREAD_CONVERGENCE_DIAGNOSTIC_SCHEMA

    def __post_init__(self) -> None:
        replicate = np.array(
            self.replicate_reference_standard_deviations, dtype=np.float64, copy=True
        )
        progressive = np.array(
            self.progressive_reference_standard_deviations, dtype=np.float64, copy=True
        )
        if replicate.ndim != 1 or progressive.ndim != 1:
            raise DensityNumericalInputError(
                "Spread convergence reference arrays must be one-dimensional."
            )
        if np.any(np.isinf(replicate)) or np.any(np.isinf(progressive)):
            raise DensityNumericalInputError(
                "Spread convergence reference arrays cannot contain infinities."
            )
        replicate.setflags(write=False); progressive.setflags(write=False)
        # Random-replicate uncertainty samples and deterministic progressive
        # convergence anchors intentionally have different cardinalities.  The
        # former estimate sampling dispersion; the latter establish the point
        # estimate at increasing represented-time coverage.
        for name in ("requested_replicate_count", "realized_replicate_count",
                     "max_replicate_count", "effective_sample_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) < 0:
                raise DensityNumericalInputError(f"{name} must be a nonnegative integer.")
            object.__setattr__(self, name, int(value))
        if self.realized_replicate_count != replicate.size:
            raise DensityNumericalInputError(
                "realized_replicate_count must match replicate diagnostics."
            )
        level = float(self.confidence_level)
        if not np.isfinite(level) or not 0.0 < level < 1.0:
            raise DensityNumericalInputError("confidence_level must lie in (0, 1).")
        object.__setattr__(self, "confidence_level", level)
        for name in (
            "reference_standard_error", "confidence_interval_low",
            "confidence_interval_high", "relative_confidence_half_width",
            "convergence_relative_change",
        ):
            value = getattr(self, name)
            if value is not None:
                number = float(value)
                if not np.isfinite(number) or number < 0.0:
                    raise DensityNumericalInputError(
                        f"{name} must be finite and nonnegative or None."
                    )
                object.__setattr__(self, name, number)
        object.__setattr__(self, "replicate_reference_standard_deviations", replicate)
        object.__setattr__(self, "progressive_reference_standard_deviations", progressive)
        object.__setattr__(self, "escalation_occurred", bool(self.escalation_occurred))
        object.__setattr__(self, "converged", bool(self.converged))

    def metadata_dict(self) -> dict[str, Any]:
        # NaN is an internal sentinel for a replicate/anchor with no finite
        # reference.  JSON/provenance metadata must remain canonical, so expose
        # those unavailable diagnostics as None rather than non-finite floats.
        def json_optional(value: float) -> float | None:
            number = float(value)
            return number if np.isfinite(number) else None

        return {
            "schema": self.schema_version,
            "replicate_reference_standard_deviations": tuple(
                json_optional(v) for v in self.replicate_reference_standard_deviations
            ),
            "progressive_reference_standard_deviations": tuple(
                json_optional(v) for v in self.progressive_reference_standard_deviations
            ),
            "reference_standard_error": self.reference_standard_error,
            "confidence_level": self.confidence_level,
            "confidence_interval_low": self.confidence_interval_low,
            "confidence_interval_high": self.confidence_interval_high,
            "relative_confidence_half_width": self.relative_confidence_half_width,
            "requested_replicate_count": self.requested_replicate_count,
            "realized_replicate_count": self.realized_replicate_count,
            "max_replicate_count": self.max_replicate_count,
            "effective_sample_count": self.effective_sample_count,
            "escalation_occurred": self.escalation_occurred,
            "convergence_relative_change": self.convergence_relative_change,
            "converged": self.converged,
        }


@dataclass(frozen=True, slots=True)
class PeriodicSpreadDiagnostics:
    """Per-item basin-aware periodic spread and automatic-reference diagnostics."""

    standard_deviations: FloatArray
    valid_reference_mask: BoolArray
    means_cartesian: FloatArray
    mean_diagnostics: tuple[PeriodicMeanDiagnostic, ...]
    reference_standard_deviation: float | None
    quantile: float
    quantile_method: str
    valid_reference_count: int
    required_reference_count: int
    adaptive_target_defined: bool
    source_frame_count: int
    sampled_frame_indices: IntArray
    sampling_strategy: str
    sampling_seed: int
    basin_source: str = "global"
    basin_counts_by_item: IntArray | None = None
    accepted_source_sample_counts_by_item: IntArray | None = None
    excluded_source_sample_counts_by_item: IntArray | None = None
    basin_diagnostics: tuple[BasinSpreadDiagnostic, ...] = ()
    convergence: SpreadConvergenceDiagnostic | None = None
    item_mean_semantics: str = "single_periodic_mean"
    schema_version: str = PERIODIC_SPREAD_DIAGNOSTIC_SCHEMA

    def __post_init__(self) -> None:
        deviations = _readonly(
            self.standard_deviations, np.float64, ndim=1, name="standard_deviations"
        )
        mask = _readonly(
            self.valid_reference_mask, np.bool_, ndim=1, name="valid_reference_mask"
        )
        means = _readonly(self.means_cartesian, np.float64, ndim=2, name="means_cartesian")
        if mask.shape != deviations.shape or means.shape != (deviations.size, 3):
            raise DensityNumericalInputError("Periodic spread diagnostics are misaligned.")
        if len(self.mean_diagnostics) != deviations.size:
            raise DensityNumericalInputError("mean_diagnostics must align with items.")
        sampled = _readonly(
            self.sampled_frame_indices, np.int64, ndim=1, name="sampled_frame_indices"
        )
        source_count = int(self.source_frame_count)
        if source_count < 1:
            raise DensityNumericalInputError("source_frame_count must be positive.")
        if sampled.size < 1 or np.any(sampled < 0) or np.any(sampled >= source_count):
            raise DensityNumericalInputError(
                "sampled_frame_indices are outside the source frames."
            )
        if np.any(np.diff(sampled) <= 0):
            raise DensityNumericalInputError(
                "sampled_frame_indices must be strictly increasing."
            )
        n_items = deviations.size
        basin_counts = (
            np.ones(n_items, dtype=np.int64)
            if self.basin_counts_by_item is None
            else _readonly(self.basin_counts_by_item, np.int64, ndim=1, name="basin_counts_by_item")
        )
        accepted = (
            np.full(n_items, source_count, dtype=np.int64)
            if self.accepted_source_sample_counts_by_item is None
            else _readonly(
                self.accepted_source_sample_counts_by_item,
                np.int64,
                ndim=1,
                name="accepted_source_sample_counts_by_item",
            )
        )
        excluded = (
            np.zeros(n_items, dtype=np.int64)
            if self.excluded_source_sample_counts_by_item is None
            else _readonly(
                self.excluded_source_sample_counts_by_item,
                np.int64,
                ndim=1,
                name="excluded_source_sample_counts_by_item",
            )
        )
        if basin_counts.shape != (n_items,) or accepted.shape != (n_items,) or excluded.shape != (n_items,):
            raise DensityNumericalInputError("Basin-aware spread count arrays must align with items.")
        if np.any(basin_counts < 0) or np.any(accepted < 0) or np.any(excluded < 0):
            raise DensityNumericalInputError("Basin-aware spread counts must be nonnegative.")
        if np.any(accepted + excluded != source_count):
            raise DensityNumericalInputError(
                "Accepted and excluded source counts must partition every item trajectory."
            )
        basin_rows = tuple(self.basin_diagnostics)
        if any(not isinstance(row, BasinSpreadDiagnostic) for row in basin_rows):
            raise TypeError("basin_diagnostics must contain BasinSpreadDiagnostic values.")
        if self.convergence is not None and not isinstance(
            self.convergence, SpreadConvergenceDiagnostic
        ):
            raise TypeError("convergence must be SpreadConvergenceDiagnostic or None.")
        object.__setattr__(self, "standard_deviations", deviations)
        object.__setattr__(self, "valid_reference_mask", mask)
        object.__setattr__(self, "means_cartesian", means)
        object.__setattr__(self, "valid_reference_count", int(self.valid_reference_count))
        object.__setattr__(self, "required_reference_count", int(self.required_reference_count))
        object.__setattr__(self, "source_frame_count", source_count)
        object.__setattr__(self, "sampled_frame_indices", sampled)
        object.__setattr__(self, "sampling_strategy", str(self.sampling_strategy))
        object.__setattr__(self, "sampling_seed", int(self.sampling_seed))
        object.__setattr__(self, "basin_source", str(self.basin_source))
        object.__setattr__(self, "basin_counts_by_item", basin_counts)
        object.__setattr__(self, "accepted_source_sample_counts_by_item", accepted)
        object.__setattr__(self, "excluded_source_sample_counts_by_item", excluded)
        object.__setattr__(self, "basin_diagnostics", basin_rows)
        object.__setattr__(self, "item_mean_semantics", str(self.item_mean_semantics))

    @property
    def total_item_count(self) -> int:
        return int(self.standard_deviations.size)

    @property
    def insufficient_valid_reference(self) -> bool:
        return self.valid_reference_count < self.required_reference_count

    def metadata_dict(self) -> dict[str, Any]:
        deviations = self.standard_deviations
        converged = tuple(bool(value.mean_converged) for value in self.mean_diagnostics)
        ambiguous = tuple(bool(value.mean_ambiguity_detected) for value in self.mean_diagnostics)
        payload = {
            "periodic_spread_schema": self.schema_version,
            "sample_sd_definition": "sqrt(pooled_within_basin_trace(periodic_covariance)/3)",
            "sample_sd_quantile": self.quantile,
            "sample_sd_quantile_method": self.quantile_method,
            "sample_sd_reference": self.reference_standard_deviation,
            "sample_sd_min": None if deviations.size == 0 else float(np.min(deviations)),
            "sample_sd_median": None if deviations.size == 0 else float(np.median(deviations)),
            "sample_sd_max": None if deviations.size == 0 else float(np.max(deviations)),
            "sample_standard_deviations": tuple(float(value) for value in deviations),
            "periodic_mean_converged": converged,
            "periodic_mean_ambiguous": ambiguous,
            "periodic_mean_iteration_counts": tuple(int(value.iteration_count) for value in self.mean_diagnostics),
            "periodic_mean_final_update_norms": tuple(float(value.final_update_norm) for value in self.mean_diagnostics),
            "periodic_mean_objective_values": tuple(float(value.objective_value) for value in self.mean_diagnostics),
            "periodic_mean_candidate_solution_counts": tuple(int(value.candidate_solution_count) for value in self.mean_diagnostics),
            "valid_reference_mask": tuple(bool(value) for value in self.valid_reference_mask),
            "valid_reference_count": self.valid_reference_count,
            "required_reference_count": self.required_reference_count,
            "adaptive_target_defined": self.adaptive_target_defined,
            "spread_source_frame_count": self.source_frame_count,
            "spread_sampled_frame_count": int(self.sampled_frame_indices.size),
            "spread_sample_fraction": float(self.sampled_frame_indices.size) / float(self.source_frame_count),
            "spread_sampled_frame_indices": tuple(int(value) for value in self.sampled_frame_indices),
            "spread_sampling_strategy": self.sampling_strategy,
            "spread_sampling_seed": self.sampling_seed,
            "spread_basin_source": self.basin_source,
            "spread_item_mean_semantics": self.item_mean_semantics,
            "spread_basin_counts_by_item": tuple(int(v) for v in self.basin_counts_by_item),
            "spread_accepted_source_sample_counts_by_item": tuple(
                int(v) for v in self.accepted_source_sample_counts_by_item
            ),
            "spread_excluded_source_sample_counts_by_item": tuple(
                int(v) for v in self.excluded_source_sample_counts_by_item
            ),
            "spread_basin_diagnostics": tuple(row.metadata_dict() for row in self.basin_diagnostics),
        }
        if self.convergence is not None:
            payload["spread_convergence"] = self.convergence.metadata_dict()
        return payload


@dataclass(frozen=True, slots=True)
class _BasinMoment:
    item_index: int
    basin_id: int
    mean_diagnostic: PeriodicMeanDiagnostic
    mean_square_radius: float
    represented_weight: float
    source_sample_count: int
    sampled_count: int
    compact_fast_path: bool


@dataclass(frozen=True, slots=True)
class _ReplicateEstimate:
    basin_moments: tuple[_BasinMoment, ...]
    sampled_indices: IntArray
    item_standard_deviations: FloatArray
    valid_item_mask: BoolArray
    reference_standard_deviation: float | None


def _compact_periodic_mean_diagnostic(
    fractional_samples: FloatArray,
    weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
    policy: PeriodicMeanPolicy,
) -> tuple[PeriodicMeanDiagnostic, bool]:
    """Use an O(N) compact-basin mean when a conservative uniqueness test passes."""

    folded = _fold_fractional(fractional_samples, pbc)
    sample_cartesian = folded @ cell
    if not np.any(pbc):
        mean = np.sum(weights[:, None] * sample_cartesian, axis=0)
        fractional = mean @ np.linalg.inv(cell)
        vectors = sample_cartesian - mean
        objective = float(np.sum(weights * np.einsum("ij,ij->i", vectors, vectors, optimize=True)))
        return (
            PeriodicMeanDiagnostic(
                mean_cartesian=mean,
                mean_fractional=fractional,
                mean_converged=True,
                iteration_count=1,
                final_update_norm=0.0,
                objective_value=objective,
                mean_ambiguity_detected=False,
                candidate_solution_count=1,
                start_count=1,
            ),
            True,
        )

    length = _reference_length(cell)
    result = _iterate_mean(
        _circular_start(folded, weights, pbc),
        sample_cartesian,
        weights,
        cell=cell,
        pbc=pbc,
        update_tolerance=policy.update_tolerance_scale * length,
        max_iterations=policy.max_iterations,
        start_index=0,
    )
    _vectors, distances, _shifts = minimum_image_geometry(
        sample_cartesian - result.cartesian,
        cell=cell,
        pbc=pbc,
    )
    # sigma_min(cell) is a rigorous lower bound on every nonzero lattice
    # translation length.  A radius below one quarter of that bound is a
    # conservative strongly-localized certificate for this flat-torus use.
    singular_min = float(np.min(np.linalg.svd(cell, compute_uv=False)))
    compact_radius = 0.25 * singular_min
    if result.converged and float(np.max(distances)) < compact_radius:
        return (
            PeriodicMeanDiagnostic(
                mean_cartesian=result.cartesian,
                mean_fractional=result.fractional,
                mean_converged=True,
                iteration_count=result.iterations,
                final_update_norm=result.final_update_norm,
                objective_value=result.objective,
                mean_ambiguity_detected=False,
                candidate_solution_count=1,
                start_count=1,
            ),
            True,
        )
    return (
        periodic_frechet_mean_diagnostic(
            folded, weights=weights, cell=cell, pbc=pbc, policy=policy
        ),
        False,
    )


def _weighted_running_mean(values: FloatArray, window: int) -> FloatArray:
    """Centered unweighted running mean used only by the provisional prepass."""

    n = values.shape[0]
    if n < 3:
        return np.array(values, copy=True)
    width = min(int(window), n if n % 2 else n - 1)
    width = max(3, width)
    if width % 2 == 0:
        width -= 1
    pad = width // 2
    padded = np.pad(values, ((pad, pad), (0, 0)), mode="edge")
    kernel = np.ones(width, dtype=np.float64) / float(width)
    return np.column_stack(
        [np.convolve(padded[:, axis], kernel, mode="valid") for axis in range(3)]
    )


def _provisional_basin_labels(
    samples: FloatArray,
    normalized_weights: FloatArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
) -> tuple[IntArray, str]:
    """Return conservative density-independent persistent-basin labels.

    This prepass is intentionally conservative: it uses complete-linkage
    clustering of coarse temporal block centers, then merges population
    centroids that are not separated by more than a vibration-informed
    threshold.  Only persistent clusters are retained, and blocks adjacent to
    a persistent state change are excluded as transition material.  If the
    evidence is too fragmented, the estimator falls back to one global basin
    rather than artificially shrinking the spread by over-segmentation.
    """

    n_frames, n_items, _ = samples.shape
    labels = np.zeros((n_frames, n_items), dtype=np.int64)
    if n_frames < 32 or n_items == 0:
        labels.setflags(write=False)
        return labels, "provisional_compact_residence_v1"

    # PAR-DENS6: do not unwrap every item in one giant MIC batch.  The generic
    # triclinic minimum-image routine may materialize candidate-image workspaces
    # proportional to ``n_frames * n_items``; for long trajectories this dwarfs
    # the density field itself.  Basin detection is item-separable, so unwrap
    # bounded item blocks.  This preserves the exact per-step MIC result and
    # downstream clustering semantics while bounding transient memory by
    # O(n_frames * bounded_items), not O(n_frames * n_items * image_candidates).

    block_count = min(128, max(16, n_frames // 64))
    edges = np.linspace(0, n_frames, block_count + 1, dtype=np.int64)
    typical_block = max(1, n_frames // block_count)
    smooth_window = min(21, max(5, 2 * max(2, typical_block // 8) + 1))
    reference_length = _reference_length(cell)
    geometric_floor = min(0.50, 0.025 * reference_length)

    try:
        from scipy.cluster.hierarchy import fcluster, linkage
    except Exception as exc:  # pragma: no cover - scipy is a core dependency
        raise DensityNumericalResourceError(
            "Provisional basin detection requires scipy.cluster.hierarchy."
        ) from exc

    def iter_unwrapped_items():
        # Bound the generic triclinic MIC candidate workspace while still
        # amortizing setup across many independent items.  About 20k step
        # vectors keeps candidate-image temporaries comfortably bounded on the
        # qualified host; the batching changes only execution shape, not the
        # vectorwise minimum-image result.
        step_count = max(1, n_frames - 1)
        items_per_block = max(1, min(n_items, 20_000 // step_count))
        for item_start in range(0, n_items, items_per_block):
            item_stop = min(n_items, item_start + items_per_block)
            folded_block = _fold_fractional(samples[:, item_start:item_stop, :], pbc)
            cartesian_block = folded_block @ cell
            raw_steps = cartesian_block[1:] - cartesian_block[:-1]
            mic_steps, _distances, _shifts = minimum_image_geometry(
                raw_steps, cell=cell, pbc=pbc
            )
            unwrapped_block = np.empty_like(cartesian_block)
            unwrapped_block[0] = cartesian_block[0]
            unwrapped_block[1:] = (
                cartesian_block[0][None, :, :] + np.cumsum(mic_steps, axis=0)
            )
            for local_item, item in enumerate(range(item_start, item_stop)):
                yield item, unwrapped_block[:, local_item, :]

    for item, trajectory in iter_unwrapped_items():
        smooth = _weighted_running_mean(trajectory, smooth_window)
        pad = smooth_window // 2
        core = slice(pad, n_frames - pad if n_frames - pad > pad else n_frames)
        residual = trajectory[core] - smooth[core]
        coordinate_r2 = np.sum(residual * residual, axis=1) / 3.0
        if coordinate_r2.size:
            q90 = float(np.quantile(coordinate_r2, 0.90, method="linear"))
            trimmed = coordinate_r2[coordinate_r2 <= q90]
            local_sigma = float(np.sqrt(np.mean(trimmed if trimmed.size else coordinate_r2)))
        else:
            local_sigma = 0.0
        separation = max(5.0 * local_sigma, geometric_floor)

        centers = np.empty((block_count, 3), dtype=np.float64)
        block_weights = np.empty(block_count, dtype=np.float64)
        for block in range(block_count):
            start = int(edges[block]); stop = int(edges[block + 1])
            local_weights = normalized_weights[start:stop]
            total = float(np.sum(local_weights, dtype=np.float64))
            block_weights[block] = total
            if total > 0.0:
                centers[block] = np.sum(
                    local_weights[:, None] * trajectory[start:stop], axis=0
                ) / total
            else:
                centers[block] = np.mean(trajectory[start:stop], axis=0)

        if block_count <= 1 or np.allclose(centers, centers[0], rtol=0.0, atol=1.0e-14):
            continue
        raw_labels = fcluster(
            linkage(centers, method="complete", metric="euclidean"),
            t=separation,
            criterion="distance",
        ).astype(np.int64) - 1

        unique = [int(v) for v in np.unique(raw_labels)]
        parent = {value: value for value in unique}

        def find(value: int) -> int:
            while parent[value] != value:
                parent[value] = parent[parent[value]]
                value = parent[value]
            return value

        def union(left: int, right: int) -> None:
            a, b = find(left), find(right)
            if a != b:
                parent[max(a, b)] = min(a, b)

        population_centers = {
            value: np.average(
                centers[raw_labels == value],
                axis=0,
                weights=np.maximum(block_weights[raw_labels == value], 1.0e-300),
            )
            for value in unique
        }
        for position, left in enumerate(unique):
            for right in unique[position + 1 :]:
                if float(np.linalg.norm(population_centers[left] - population_centers[right])) < separation:
                    union(left, right)
        roots = sorted({find(value) for value in unique})
        remap = {root: position for position, root in enumerate(roots)}
        merged = np.asarray([remap[find(int(v))] for v in raw_labels], dtype=np.int64)

        qualified: list[int] = []
        minimum_blocks = max(2, int(np.ceil(0.03 * block_count)))
        for basin in np.unique(merged):
            block_ids = np.flatnonzero(merged == basin)
            runs = np.split(block_ids, np.flatnonzero(np.diff(block_ids) > 1) + 1)
            longest = max(len(run) for run in runs)
            represented = float(np.sum(block_weights[block_ids], dtype=np.float64))
            if len(block_ids) >= minimum_blocks and longest >= 2 and represented >= 0.03:
                qualified.append(int(basin))

        # A strongly fragmented path is not a trustworthy residence decomposition.
        # Preserve the global spread rather than manufacture small pseudo-basins.
        if len(qualified) <= 1:
            if len(qualified) == 1:
                keep = qualified[0]
                labels[:, item] = -1
                for block in np.flatnonzero(merged == keep):
                    start = int(edges[block]); stop = int(edges[block + 1])
                    labels[start:stop, item] = 0
            continue
        if len(qualified) > 8:
            labels[:, item] = 0
            continue

        labels[:, item] = -1
        qualified_remap = {basin: position for position, basin in enumerate(sorted(qualified))}
        transition_blocks: set[int] = set()
        for block in range(block_count - 1):
            left = int(merged[block]); right = int(merged[block + 1])
            if left != right and left in qualified_remap and right in qualified_remap:
                transition_blocks.update((block, block + 1))
        for block in range(block_count):
            basin = int(merged[block])
            if basin not in qualified_remap or block in transition_blocks:
                continue
            start = int(edges[block]); stop = int(edges[block + 1])
            labels[start:stop, item] = qualified_remap[basin]

        accepted = labels[:, item] >= 0
        if np.count_nonzero(accepted) < max(4, int(0.10 * n_frames)):
            labels[:, item] = 0

    labels[normalized_weights <= 0.0, :] = -1
    labels.setflags(write=False)
    return labels, "provisional_compact_residence_v1"


def spread_basin_labels_from_site_assignment(
    assignment_result: Any,
    *,
    source_frame_indices: Any | None = None,
    atom_indices: Any | None = None,
) -> IntArray:
    """Translate geometry-based site assignment into basin labels for spread use.

    Accepted ``ASSIGNED``/``ANNULAR_ASSIGNED`` samples carry their physical
    state index. Transition-region, ambiguous, unassigned, and unresolved
    samples are emitted as ``-1`` and therefore cannot contribute vibrational
    variance.
    """

    from ..site_assignment import SiteAssignmentResult

    if not isinstance(assignment_result, SiteAssignmentResult):
        raise TypeError("assignment_result must be SiteAssignmentResult.")
    frames = np.asarray(
        assignment_result.axis.collection_frame_indices
        if source_frame_indices is None else source_frame_indices,
        dtype=np.int64,
    )
    atoms = np.asarray(
        assignment_result.atom_indices if atom_indices is None else atom_indices,
        dtype=np.int64,
    )
    if frames.ndim != 1 or atoms.ndim != 1 or frames.size == 0 or atoms.size == 0:
        raise DensityNumericalInputError("source_frame_indices and atom_indices must be nonempty 1-D arrays.")
    frame_position = {int(frame): i for i, frame in enumerate(frames)}
    source_atom_position = {
        int(atom): i for i, atom in enumerate(np.asarray(assignment_result.atom_indices, dtype=np.int64))
    }
    labels = np.full((frames.size, atoms.size), -1, dtype=np.int64)
    for output_item, atom in enumerate(atoms):
        source_item = source_atom_position.get(int(atom))
        if source_item is None:
            raise DensityNumericalInputError(f"Atom {int(atom)} is absent from site assignment.")
        for assignment in assignment_result.assignments[source_item]:
            output_frame = frame_position.get(int(assignment.collection_frame_index))
            if output_frame is not None and assignment.accepted:
                assert assignment.state_index is not None
                labels[output_frame, output_item] = int(assignment.state_index)
    labels.setflags(write=False)
    return labels


def spread_basin_labels_from_final_segmentation(
    sample_catalog: Any,
    final_segmentation: Any,
    *,
    source_frame_indices: Any | None = None,
    atom_indices: Any | None = None,
) -> IntArray:
    """Translate Stage-11E6 final membership/residence lineage into spread labels."""

    from ..site_samples import FrameworkAlignedIonSampleCatalog
    from .final_segmentation import (
        FinalHystereticSegmentationCatalog,
        FinalMembershipClass,
    )

    if not isinstance(sample_catalog, FrameworkAlignedIonSampleCatalog):
        raise TypeError("sample_catalog must be FrameworkAlignedIonSampleCatalog.")
    if not isinstance(final_segmentation, FinalHystereticSegmentationCatalog):
        raise TypeError(
            "final_segmentation must be FinalHystereticSegmentationCatalog."
        )
    if final_segmentation.membership.n_samples != sample_catalog.frame_indices.size:
        raise DensityNumericalInputError("Final segmentation and sample catalog do not align.")
    frames = np.asarray(
        sample_catalog.temporal_weighting.frame_indices
        if source_frame_indices is None else source_frame_indices,
        dtype=np.int64,
    )
    atoms = np.asarray(
        sample_catalog.selected_atom_indices if atom_indices is None else atom_indices,
        dtype=np.int64,
    )
    frame_position = {int(frame): i for i, frame in enumerate(frames)}
    atom_position = {int(atom): i for i, atom in enumerate(atoms)}
    labels = np.full((frames.size, atoms.size), -1, dtype=np.int64)
    residence_member = np.zeros(sample_catalog.frame_indices.size, dtype=bool)
    for residence in final_segmentation.residences:
        residence_member[np.asarray(residence.sample_indices, dtype=np.int64)] = True
    membership = final_segmentation.membership
    accepted_codes = {int(FinalMembershipClass.CORE), int(FinalMembershipClass.BASIN)}
    for sample in range(sample_catalog.frame_indices.size):
        if not residence_member[sample] or bool(membership.conflict_mask[sample]):
            continue
        if int(membership.membership_class[sample]) not in accepted_codes:
            continue
        state = int(membership.state_ids[sample])
        if state < 0:
            continue
        frame = frame_position.get(int(sample_catalog.frame_indices[sample]))
        item = atom_position.get(int(sample_catalog.atom_indices[sample]))
        if frame is not None and item is not None:
            labels[frame, item] = state
    labels.setflags(write=False)
    return labels


# Reference for the sampling principle: W. G. Cochran, *Sampling Techniques*,
# 3rd ed., Wiley, 1977. Weighted temporal strata and deterministic seed/weight
# transfer are mdstats-specific.
def _spread_frame_subsample(
    samples: FloatArray,
    normalized_weights: FloatArray,
    *,
    sample_size: int,
    sample_seed: int,
    sampling_strategy: Literal["all", "stratified_random"],
) -> tuple[FloatArray, FloatArray, IntArray, str]:
    """Backward-compatible whole-frame stratified sampler."""

    n_frames = int(samples.shape[0])
    if sampling_strategy == "all" or n_frames <= sample_size:
        indices = np.arange(n_frames, dtype=np.int64)
        return samples, normalized_weights, indices, "all"
    if sampling_strategy != "stratified_random":
        raise DensityNumericalInputError("sampling_strategy must be all or stratified_random.")
    if sample_size < 2:
        raise DensityNumericalInputError("sample_size must be at least 2.")
    rng = np.random.default_rng(int(sample_seed))
    edges = np.linspace(0, n_frames, sample_size + 1, dtype=np.int64)
    indices = np.empty(sample_size, dtype=np.int64)
    sampled_weights = np.empty(sample_size, dtype=np.float64)
    for stratum in range(sample_size):
        start = int(edges[stratum]); stop = int(edges[stratum + 1])
        if stop <= start:
            stop = min(n_frames, start + 1)
        local = normalized_weights[start:stop]
        stratum_weight = float(np.sum(local, dtype=np.float64))
        if stratum_weight > 0.0:
            offset = int(rng.choice(stop - start, p=local / stratum_weight))
        else:
            offset = int(rng.integers(0, stop - start))
        indices[stratum] = start + offset
        sampled_weights[stratum] = stratum_weight
    sampled_weights /= float(np.sum(sampled_weights, dtype=np.float64))
    indices.setflags(write=False); sampled_weights.setflags(write=False)
    return samples[indices], sampled_weights, indices, "stratified_random"


def _coalesce_samples(indices: IntArray, weights: FloatArray) -> tuple[IntArray, FloatArray]:
    order = np.argsort(indices, kind="stable")
    sorted_indices = np.asarray(indices[order], dtype=np.int64)
    sorted_weights = np.asarray(weights[order], dtype=np.float64)
    unique, starts = np.unique(sorted_indices, return_index=True)
    summed = np.add.reduceat(sorted_weights, starts)
    unique = np.asarray(unique, dtype=np.int64); summed = np.asarray(summed, dtype=np.float64)
    unique.setflags(write=False); summed.setflags(write=False)
    return unique, summed


def _weighted_temporal_sample(
    frame_indices: IntArray,
    source_weights: FloatArray,
    *,
    sample_size: int,
    sample_seed: int,
    sampling_strategy: Literal["all", "stratified_random", "stratified_midpoint"],
    replicate_index: int = 0,
    replicate_count: int = 1,
) -> tuple[IntArray, FloatArray]:
    """Sample ordered qualified frames using equal represented-weight strata."""

    frames = np.asarray(frame_indices, dtype=np.int64)
    weights = np.asarray(source_weights, dtype=np.float64)
    positive = weights > 0.0
    frames = frames[positive]; weights = weights[positive]
    if frames.size == 0:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.float64)
    total = float(np.sum(weights, dtype=np.float64))
    if sampling_strategy == "all" or frames.size <= sample_size:
        return _coalesce_samples(frames, weights)
    if sampling_strategy not in {"stratified_random", "stratified_midpoint"}:
        raise DensityNumericalInputError(
            "sampling_strategy must be all, stratified_random, or stratified_midpoint."
        )
    count = max(1, int(sample_size))
    replicate_index = int(replicate_index); replicate_count = int(replicate_count)
    if replicate_count < 1 or replicate_index < 0 or replicate_index >= replicate_count:
        raise DensityNumericalInputError("Invalid replicated stratified-sampling index/count.")
    rng = np.random.default_rng(int(sample_seed) + 15485863 * replicate_index)
    # Preserve the historical disjoint temporal-stratum sampler exactly for
    # uniformly weighted contiguous trajectories. Besides backward compatibility,
    # this guarantees one distinct frame per stratum in the common MD case.
    if (
        frames.size >= count
        and np.all(np.diff(frames) == 1)
        and np.allclose(weights, weights[0], rtol=1.0e-13, atol=0.0)
    ):
        edges_i = np.linspace(0, frames.size, count + 1, dtype=np.int64)
        selected_i = np.empty(count, dtype=np.int64)
        represented_i = np.empty(count, dtype=np.float64)
        for stratum in range(count):
            left_i = int(edges_i[stratum]); right_i = int(edges_i[stratum + 1])
            if right_i <= left_i:
                right_i = min(frames.size, left_i + 1)
            if sampling_strategy == "stratified_midpoint":
                offset = (left_i + right_i - 1) // 2
            else:
                draw_left, draw_right = left_i, right_i
                if replicate_count > 1 and right_i - left_i >= replicate_count:
                    sub_edges = np.linspace(left_i, right_i, replicate_count + 1, dtype=np.int64)
                    perm_rng = np.random.default_rng(int(sample_seed) + 104729 * stratum)
                    slot = int(perm_rng.permutation(replicate_count)[replicate_index])
                    draw_left = int(sub_edges[slot]); draw_right = int(sub_edges[slot + 1])
                    if draw_right <= draw_left:
                        draw_right = min(right_i, draw_left + 1)
                offset = int(rng.integers(draw_left, draw_right))
            selected_i[stratum] = frames[offset]
            # One sampled point represents the complete original stratum, not
            # only its Latinized sub-stratum. Each replicate is therefore a
            # complete estimator while the replicate ensemble has better coverage.
            represented_i[stratum] = float(np.sum(weights[left_i:right_i], dtype=np.float64))
        return _coalesce_samples(selected_i, represented_i)
    cumulative = np.concatenate(([0.0], np.cumsum(weights, dtype=np.float64)))
    edges = np.linspace(0.0, total, count + 1)
    selected = np.empty(count, dtype=np.int64)
    represented = np.empty(count, dtype=np.float64)
    for stratum in range(count):
        lower = float(edges[stratum]); upper = float(edges[stratum + 1])
        if sampling_strategy == "stratified_midpoint":
            target = 0.5 * (lower + upper)
            chosen = min(
                frames.size - 1,
                max(0, int(np.searchsorted(cumulative, target, side="right") - 1)),
            )
        else:
            draw_lower, draw_upper = lower, upper
            if replicate_count > 1:
                sub_edges = np.linspace(lower, upper, replicate_count + 1)
                perm_rng = np.random.default_rng(int(sample_seed) + 104729 * stratum)
                slot = int(perm_rng.permutation(replicate_count)[replicate_index])
                draw_lower = float(sub_edges[slot]); draw_upper = float(sub_edges[slot + 1])
            left = max(0, int(np.searchsorted(cumulative, draw_lower, side="right") - 1))
            right = min(frames.size, int(np.searchsorted(cumulative, draw_upper, side="left") + 1))
            candidates = np.arange(left, max(left + 1, right), dtype=np.int64)
            overlaps = np.minimum(cumulative[candidates + 1], draw_upper) - np.maximum(cumulative[candidates], draw_lower)
            overlaps = np.maximum(overlaps, 0.0)
            overlap_total = float(np.sum(overlaps, dtype=np.float64))
            if overlap_total <= 0.0:
                chosen = min(frames.size - 1, left)
            else:
                chosen = int(rng.choice(candidates, p=overlaps / overlap_total))
        selected[stratum] = frames[chosen]
        represented[stratum] = upper - lower
    return _coalesce_samples(selected, represented)


def _allocate_basin_sample_counts(
    labels: IntArray,
    weights: FloatArray,
    sample_size: int,
) -> dict[int, int]:
    basins = [int(v) for v in np.unique(labels[labels >= 0])]
    if not basins:
        return {}
    basin_weights = np.asarray(
        [float(np.sum(weights[labels == basin], dtype=np.float64)) for basin in basins],
        dtype=np.float64,
    )
    total = float(np.sum(basin_weights))
    target = max(int(sample_size), sum(2 if np.count_nonzero(labels == basin) >= 2 else 1 for basin in basins))
    ideal = target * basin_weights / total
    counts = np.floor(ideal).astype(np.int64)
    minimum = np.asarray([2 if np.count_nonzero(labels == basin) >= 2 else 1 for basin in basins], dtype=np.int64)
    counts = np.maximum(counts, minimum)
    while int(np.sum(counts)) < target:
        remainder = ideal - counts
        counts[int(np.argmax(remainder))] += 1
    while int(np.sum(counts)) > target:
        removable = np.flatnonzero(counts > minimum)
        if removable.size == 0:
            break
        excess = counts[removable] - ideal[removable]
        counts[int(removable[int(np.argmax(excess))])] -= 1
    return {basin: int(count) for basin, count in zip(basins, counts, strict=True)}


def _one_replicate(
    samples: FloatArray,
    normalized_weights: FloatArray,
    basin_labels: IntArray,
    *,
    cell: FloatArray,
    pbc: BoolArray,
    quantile: float,
    policy: PeriodicMeanPolicy,
    sample_size: int,
    sample_seed: int,
    sampling_strategy: Literal["all", "stratified_random"],
    replicate_index: int = 0,
    replicate_count: int = 1,
) -> _ReplicateEstimate:
    n_frames, n_items, _ = samples.shape
    moments: list[_BasinMoment] = []
    sampled_all: list[IntArray] = []
    item_sds = np.full(n_items, np.nan, dtype=np.float64)
    valid = np.zeros(n_items, dtype=bool)
    zero_tolerance = 1.0e-12 * _reference_length(cell)
    for item in range(n_items):
        item_labels = basin_labels[:, item]
        allocations = _allocate_basin_sample_counts(item_labels, normalized_weights, sample_size)
        if not allocations:
            continue
        item_msr = 0.0; item_weight = 0.0; item_valid = True
        for basin, count in allocations.items():
            eligible = np.flatnonzero(item_labels == basin).astype(np.int64)
            source_weight = float(np.sum(normalized_weights[eligible], dtype=np.float64))
            if source_weight <= 0.0:
                item_valid = False; continue
            indices, represented = _weighted_temporal_sample(
                eligible,
                normalized_weights[eligible],
                sample_size=count,
                sample_seed=(int(sample_seed) + 1009 * basin) & 0x7FFFFFFF,
                sampling_strategy=sampling_strategy,
                replicate_index=replicate_index,
                replicate_count=replicate_count,
            )
            if indices.size == 0:
                item_valid = False; continue
            sampled_all.append(indices)
            basin_weights = np.asarray(represented / np.sum(represented), dtype=np.float64)
            diagnostic, compact = _compact_periodic_mean_diagnostic(
                samples[indices, item, :],
                basin_weights,
                cell=cell,
                pbc=pbc,
                policy=policy,
            )
            if not diagnostic.valid_for_reference:
                item_valid = False
            sample_cartesian = _fold_fractional(samples[indices, item, :], pbc) @ cell
            vectors, _distances, _shifts = minimum_image_geometry(
                sample_cartesian - diagnostic.mean_cartesian,
                cell=cell,
                pbc=pbc,
            )
            msr = float(np.sum(basin_weights * np.einsum("ij,ij->i", vectors, vectors, optimize=True)))
            moments.append(
                _BasinMoment(
                    item_index=item,
                    basin_id=basin,
                    mean_diagnostic=diagnostic,
                    mean_square_radius=msr,
                    represented_weight=source_weight,
                    source_sample_count=int(eligible.size),
                    sampled_count=int(indices.size),
                    compact_fast_path=compact,
                )
            )
            item_msr += source_weight * msr
            item_weight += source_weight
        if item_valid and item_weight > 0.0:
            deviation = float(np.sqrt(max(0.0, item_msr / item_weight / 3.0)))
            item_sds[item] = 0.0 if deviation <= zero_tolerance else deviation
            valid[item] = True
    required = max(
        policy.minimum_valid_reference_count,
        int(np.ceil(policy.minimum_valid_reference_fraction * n_items)),
    )
    reference = None
    if int(np.count_nonzero(valid)) >= required:
        reference = float(np.quantile(item_sds[valid], quantile, method=SPREAD_QUANTILE_METHOD))
    sampled = (
        np.unique(np.concatenate(sampled_all)).astype(np.int64)
        if sampled_all else np.asarray([0], dtype=np.int64)
    )
    sampled.setflags(write=False); item_sds.setflags(write=False); valid.setflags(write=False)
    return _ReplicateEstimate(tuple(moments), sampled, item_sds, valid, reference)


def _combine_replicates(
    replicates: list[_ReplicateEstimate],
    *,
    n_items: int,
    cell: FloatArray,
    pbc: BoolArray,
    quantile: float,
    policy: PeriodicMeanPolicy,
    basin_labels: IntArray,
    normalized_weights: FloatArray,
) -> tuple[FloatArray, BoolArray, FloatArray, tuple[PeriodicMeanDiagnostic, ...], tuple[BasinSpreadDiagnostic, ...], float | None]:
    by_key: dict[tuple[int, int], list[_BasinMoment]] = {}
    for replicate in replicates:
        for moment in replicate.basin_moments:
            by_key.setdefault((moment.item_index, moment.basin_id), []).append(moment)

    basin_rows: list[BasinSpreadDiagnostic] = []
    combined_by_item: dict[int, list[tuple[float, float, PeriodicMeanDiagnostic, bool]]] = {}
    for (item, basin), moments in sorted(by_key.items()):
        if len(moments) != len(replicates):
            continue
        means_fractional = np.asarray(
            [m.mean_diagnostic.mean_fractional for m in moments], dtype=np.float64
        )
        mean_weights = np.full(len(moments), 1.0 / len(moments), dtype=np.float64)
        if len(moments) == 1:
            combined_mean = moments[0].mean_diagnostic
        else:
            combined_mean, _compact = _compact_periodic_mean_diagnostic(
                means_fractional, mean_weights, cell=cell, pbc=pbc, policy=policy
            )
        rep_means_cart = np.asarray([m.mean_diagnostic.mean_cartesian for m in moments], dtype=np.float64)
        between_vectors, _distances, _shifts = minimum_image_geometry(
            rep_means_cart - combined_mean.mean_cartesian,
            cell=cell,
            pbc=pbc,
        )
        pooled_msr = float(np.mean([
            m.mean_square_radius + float(np.dot(vec, vec))
            for m, vec in zip(moments, between_vectors, strict=True)
        ]))
        represented = float(moments[0].represented_weight)
        source_count = int(np.count_nonzero(basin_labels[:, item] == basin))
        sampled_count = int(sum(m.sampled_count for m in moments))
        deviation = float(np.sqrt(max(0.0, pooled_msr / 3.0)))
        basin_valid = all(m.mean_diagnostic.valid_for_reference for m in moments)
        basin_rows.append(
            BasinSpreadDiagnostic(
                item_index=item,
                basin_id=basin,
                mean_cartesian=combined_mean.mean_cartesian,
                standard_deviation=deviation,
                mean_square_radius=pooled_msr,
                represented_weight=represented,
                source_sample_count=source_count,
                sampled_count=sampled_count,
                replicate_count=len(moments),
                compact_fast_path_count=sum(int(m.compact_fast_path) for m in moments),
                fallback_mean_count=sum(int(not m.compact_fast_path) for m in moments),
            )
        )
        combined_by_item.setdefault(item, []).append((represented, pooled_msr, combined_mean, basin_valid))

    deviations = np.full(n_items, np.nan, dtype=np.float64)
    valid = np.zeros(n_items, dtype=bool)
    means = np.zeros((n_items, 3), dtype=np.float64)
    diagnostics: list[PeriodicMeanDiagnostic] = []
    zero_tolerance = 1.0e-12 * _reference_length(cell)
    for item in range(n_items):
        rows = combined_by_item.get(item, [])
        expected_basins = [int(v) for v in np.unique(basin_labels[:, item][basin_labels[:, item] >= 0])]
        if not rows or len(rows) != len(expected_basins):
            # A deterministic placeholder keeps legacy metadata aligned while the
            # validity mask prevents this item from defining the reference.
            fallback = periodic_frechet_mean_diagnostic(
                np.asarray([[0.0, 0.0, 0.0]]),
                weights=np.asarray([1.0]), cell=cell, pbc=pbc, policy=policy,
            )
            diagnostics.append(fallback); means[item] = fallback.mean_cartesian
            continue
        total_weight = float(sum(row[0] for row in rows))
        msr = float(sum(weight * value for weight, value, _diag, _valid in rows) / total_weight)
        deviation = float(np.sqrt(max(0.0, msr / 3.0)))
        deviations[item] = 0.0 if deviation <= zero_tolerance else deviation
        valid[item] = all(row[3] for row in rows)
        dominant = max(rows, key=lambda row: row[0])[2]
        diagnostics.append(dominant); means[item] = dominant.mean_cartesian

    required = max(
        policy.minimum_valid_reference_count,
        int(np.ceil(policy.minimum_valid_reference_fraction * n_items)),
    )
    reference = None
    if int(np.count_nonzero(valid)) >= required:
        reference = float(np.quantile(deviations[valid], quantile, method=SPREAD_QUANTILE_METHOD))
    deviations.setflags(write=False); valid.setflags(write=False); means.setflags(write=False)
    return deviations, valid, means, tuple(diagnostics), tuple(basin_rows), reference


def _placeholder_mean(cell: FloatArray, pbc: BoolArray, policy: PeriodicMeanPolicy) -> PeriodicMeanDiagnostic:
    return periodic_frechet_mean_diagnostic(
        np.asarray([[0.0, 0.0, 0.0]]),
        weights=np.asarray([1.0]),
        cell=cell,
        pbc=pbc,
        policy=policy,
    )


def periodic_item_spread_diagnostics(
    fractional_by_frame: Any,
    *,
    weights: Any,
    cell: Any,
    pbc: Any,
    quantile: float,
    policy: PeriodicMeanPolicy | None = None,
    sample_size: int = 128,
    sample_seed: int = 0,
    sampling_strategy: Literal["all", "stratified_random"] = "stratified_random",
    replicate_count: int = 1,
    max_replicate_count: int | None = None,
    convergence_relative_tolerance: float = 0.01,
    confidence_level: float = 0.95,
    basin_mode: Literal["auto", "global"] = "global",
    basin_labels_by_frame: Any | None = None,
    basin_label_source: str | None = None,
) -> PeriodicSpreadDiagnostics:
    """Return basin-aware periodic item spreads and a converged quantile reference.

    ``basin_labels_by_frame`` is the authoritative route: nonnegative integers
    identify qualified basin/core membership and negative values are excluded
    from vibrational variance.  Without labels, ``basin_mode='auto'`` runs the
    conservative density-independent provisional residence prepass.  ``global``
    preserves the historical one-basin interpretation explicitly.

    ``sample_size`` is the target number of represented-time strata *per
    replicate*.  Production density options use four independent 128-stratum
    replicates, while this low-level API keeps ``replicate_count=1`` for backward
    compatibility. Compact basins use an O(N) Karcher fast path, so ``all`` or
    larger sample coverage does not normally trigger the old quadratic medoid.
    """

    samples = np.asarray(fractional_by_frame, dtype=np.float64)
    matrix = _validated_cell(cell)
    periodic = np.asarray(pbc, dtype=bool)
    if samples.ndim != 3 or samples.shape[2:] != (3,):
        raise DensityNumericalInputError(
            "fractional_by_frame must have shape (n_frames, n_items, 3)."
        )
    if samples.shape[0] < 1:
        raise DensityNumericalInputError("fractional_by_frame must contain at least one frame.")
    if periodic.shape != (3,):
        raise DensityNumericalInputError("pbc must have shape (3,).")
    normalized_weights = _validated_weights(weights, samples.shape[0])
    q = float(quantile)
    if not np.isfinite(q) or not 0.0 <= q <= 1.0:
        raise DensityNumericalInputError("quantile must lie in [0, 1].")
    active_policy = PeriodicMeanPolicy() if policy is None else policy
    if not isinstance(active_policy, PeriodicMeanPolicy):
        raise TypeError("policy must be PeriodicMeanPolicy or None.")
    if isinstance(sample_size, bool) or int(sample_size) < 2:
        raise DensityNumericalInputError("sample_size must be an integer of at least 2.")
    if isinstance(sample_seed, bool) or not isinstance(sample_seed, (int, np.integer)):
        raise DensityNumericalInputError("sample_seed must be an integer.")
    if sampling_strategy not in {"all", "stratified_random"}:
        raise DensityNumericalInputError("sampling_strategy must be all or stratified_random.")
    if basin_mode not in {"auto", "global"}:
        raise DensityNumericalInputError("basin_mode must be auto or global.")
    if isinstance(replicate_count, bool) or int(replicate_count) < 1:
        raise DensityNumericalInputError("replicate_count must be a positive integer.")
    requested_replicates = int(replicate_count)
    maximum_replicates = requested_replicates if max_replicate_count is None else int(max_replicate_count)
    if maximum_replicates < requested_replicates:
        raise DensityNumericalInputError("max_replicate_count cannot be smaller than replicate_count.")
    tolerance = float(convergence_relative_tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise DensityNumericalInputError("convergence_relative_tolerance must be finite and positive.")
    level = float(confidence_level)
    if not np.isfinite(level) or not 0.0 < level < 1.0:
        raise DensityNumericalInputError("confidence_level must lie in (0, 1).")

    source_frame_count, n_items, _ = samples.shape
    if basin_labels_by_frame is not None:
        labels = np.asarray(basin_labels_by_frame, dtype=np.int64)
        if labels.shape != (source_frame_count, n_items):
            raise DensityNumericalInputError(
                "basin_labels_by_frame must have shape (n_frames, n_items)."
            )
        labels = np.array(labels, copy=True)
        labels[normalized_weights <= 0.0, :] = -1
        basin_source = "provided" if basin_label_source is None else str(basin_label_source)
    elif basin_mode == "global":
        labels = np.zeros((source_frame_count, n_items), dtype=np.int64)
        labels[normalized_weights <= 0.0, :] = -1
        basin_source = "global"
    else:
        labels, basin_source = _provisional_basin_labels(
            samples, normalized_weights, cell=matrix, pbc=periodic
        )
        labels = np.asarray(labels, dtype=np.int64)
    labels.setflags(write=False)

    basin_counts = np.asarray(
        [np.unique(labels[:, item][labels[:, item] >= 0]).size for item in range(n_items)],
        dtype=np.int64,
    )
    accepted_counts = np.asarray(
        [np.count_nonzero(labels[:, item] >= 0) for item in range(n_items)], dtype=np.int64
    )
    excluded_counts = source_frame_count - accepted_counts

    # Random replicated solves quantify sampling dispersion, while deterministic
    # represented-time midpoint anchors establish the production point estimate.
    # Separating those roles avoids a seed-sensitive point estimate without
    # pretending deterministic convergence removes finite-trajectory uncertainty.
    target_initial = 1 if sampling_strategy == "all" else requested_replicates
    target_maximum = 1 if sampling_strategy == "all" else maximum_replicates
    uncertainty_replicates: list[_ReplicateEstimate] = []
    anchor_estimates: list[_ReplicateEstimate] = []
    progressive: list[float] = []
    realized_replicates = target_initial
    escalation_occurred = False

    if sampling_strategy == "all":
        exact = _one_replicate(
            samples, normalized_weights, labels, cell=matrix, pbc=periodic,
            quantile=q, policy=active_policy, sample_size=int(sample_size),
            sample_seed=int(sample_seed), sampling_strategy="all",
        )
        uncertainty_replicates.append(exact)
        anchor_estimates.append(exact)
        combined_cache = _combine_replicates(
            [exact], n_items=n_items, cell=matrix, pbc=periodic, quantile=q,
            policy=active_policy, basin_labels=labels,
            normalized_weights=normalized_weights,
        )
        progressive.append(np.nan if combined_cache[-1] is None else float(combined_cache[-1]))
        relative_change = None
        converged = combined_cache[-1] is not None
        sampling_label = "all"
    elif requested_replicates == 1:
        # Preserve the historical low-level one-replicate point-estimate semantics.
        estimate = _one_replicate(
            samples, normalized_weights, labels, cell=matrix, pbc=periodic,
            quantile=q, policy=active_policy, sample_size=int(sample_size),
            sample_seed=int(sample_seed), sampling_strategy="stratified_random",
        )
        uncertainty_replicates.append(estimate)
        anchor_estimates.append(estimate)
        combined_cache = _combine_replicates(
            [estimate], n_items=n_items, cell=matrix, pbc=periodic, quantile=q,
            policy=active_policy, basin_labels=labels,
            normalized_weights=normalized_weights,
        )
        progressive.append(np.nan if combined_cache[-1] is None else float(combined_cache[-1]))
        relative_change = None
        converged = combined_cache[-1] is not None
        sampling_label = "stratified_random"
    else:
        def add_uncertainty_replicates(first: int, stop: int) -> None:
            for replicate in range(first, stop):
                uncertainty_replicates.append(
                    _one_replicate(
                        samples, normalized_weights, labels, cell=matrix, pbc=periodic,
                        quantile=q, policy=active_policy, sample_size=int(sample_size),
                        sample_seed=int(sample_seed) + 7919 * replicate,
                        sampling_strategy="stratified_random",
                    )
                )

        def midpoint_anchor(coverage: int) -> tuple[_ReplicateEstimate, tuple[Any, ...]]:
            estimate = _one_replicate(
                samples, normalized_weights, labels, cell=matrix, pbc=periodic,
                quantile=q, policy=active_policy, sample_size=max(2, int(coverage)),
                sample_seed=int(sample_seed), sampling_strategy="stratified_midpoint",
            )
            combined = _combine_replicates(
                [estimate], n_items=n_items, cell=matrix, pbc=periodic, quantile=q,
                policy=active_policy, basin_labels=labels,
                normalized_weights=normalized_weights,
            )
            return estimate, combined

        add_uncertainty_replicates(0, target_initial)
        realized_replicates = target_initial
        lower_coverage = max(int(sample_size), int(sample_size) * max(1, realized_replicates // 2))
        upper_coverage = int(sample_size) * realized_replicates
        lower_anchor, lower_combined = midpoint_anchor(lower_coverage)
        upper_anchor, combined_cache = midpoint_anchor(upper_coverage)
        anchor_estimates.extend((lower_anchor, upper_anchor))
        progressive.extend((
            np.nan if lower_combined[-1] is None else float(lower_combined[-1]),
            np.nan if combined_cache[-1] is None else float(combined_cache[-1]),
        ))

        def current_relative_change() -> float | None:
            finite = np.asarray([v for v in progressive if np.isfinite(v)], dtype=np.float64)
            if finite.size < 2 or finite[-1] <= 0.0:
                return None
            return float(abs(finite[-1] - finite[-2]) / finite[-1])

        relative_change = current_relative_change()
        while (
            (relative_change is None or relative_change > tolerance)
            and realized_replicates < target_maximum
        ):
            previous = realized_replicates
            realized_replicates = min(target_maximum, realized_replicates + target_initial)
            add_uncertainty_replicates(previous, realized_replicates)
            escalation_occurred = True
            upper_coverage = int(sample_size) * realized_replicates
            upper_anchor, combined_cache = midpoint_anchor(upper_coverage)
            anchor_estimates.append(upper_anchor)
            progressive.append(
                np.nan if combined_cache[-1] is None else float(combined_cache[-1])
            )
            relative_change = current_relative_change()
        converged = bool(
            combined_cache[-1] is not None
            and relative_change is not None
            and relative_change <= tolerance
        )
        sampling_label = "convergence_qualified_stratified"

    deviations, valid, means, diagnostics, basin_rows, reference = combined_cache
    required = max(
        active_policy.minimum_valid_reference_count,
        int(np.ceil(active_policy.minimum_valid_reference_fraction * n_items)),
    )
    valid_count = int(np.count_nonzero(valid))
    if valid_count < required:
        reference = None
    target_defined = bool(reference is not None and reference > 0.0)

    replicate_refs = np.asarray(
        [
            np.nan if rep.reference_standard_deviation is None
            else rep.reference_standard_deviation
            for rep in uncertainty_replicates
        ],
        dtype=np.float64,
    )
    finite_refs = replicate_refs[np.isfinite(replicate_refs)]
    standard_error: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    relative_half: float | None = None
    if finite_refs.size >= 2 and reference is not None:
        sample_sd = float(np.std(finite_refs, ddof=1))
        standard_error = sample_sd / np.sqrt(float(finite_refs.size))
        try:
            from scipy.stats import t as student_t
            multiplier = float(
                student_t.ppf(0.5 + level / 2.0, df=finite_refs.size - 1)
            )
        except Exception:  # pragma: no cover
            multiplier = 1.96
        half = multiplier * standard_error
        ci_low = max(0.0, float(reference - half))
        ci_high = float(reference + half)
        if reference > 0.0:
            relative_half = half / reference

    # For exact/all and the backward-compatible one-replicate mode, lack of a
    # progressive pair is intentional rather than a convergence failure.
    if sampling_strategy == "all" or requested_replicates == 1:
        relative_change = None
        converged = bool(reference is not None)
    effective_sample_count = int(
        sum(row.sampled_count for row in basin_rows) / max(1, n_items)
    )
    convergence = SpreadConvergenceDiagnostic(
        replicate_reference_standard_deviations=replicate_refs,
        progressive_reference_standard_deviations=np.asarray(progressive, dtype=np.float64),
        reference_standard_error=standard_error,
        confidence_level=level,
        confidence_interval_low=ci_low,
        confidence_interval_high=ci_high,
        relative_confidence_half_width=relative_half,
        requested_replicate_count=target_initial,
        realized_replicate_count=len(uncertainty_replicates),
        max_replicate_count=target_maximum,
        effective_sample_count=effective_sample_count,
        escalation_occurred=escalation_occurred,
        convergence_relative_change=relative_change,
        converged=converged,
    )
    sampled_parts = [rep.sampled_indices for rep in uncertainty_replicates]
    sampled_parts.extend(anchor.sampled_indices for anchor in anchor_estimates)
    sampled_union = np.unique(np.concatenate(sampled_parts)).astype(np.int64)
    sampled_union.setflags(write=False)
    return PeriodicSpreadDiagnostics(
        standard_deviations=deviations,
        valid_reference_mask=valid,
        means_cartesian=means,
        mean_diagnostics=diagnostics,
        reference_standard_deviation=reference,
        quantile=q,
        quantile_method=SPREAD_QUANTILE_METHOD,
        valid_reference_count=valid_count,
        required_reference_count=required,
        adaptive_target_defined=target_defined,
        source_frame_count=source_frame_count,
        sampled_frame_indices=sampled_union,
        sampling_strategy=sampling_label,
        sampling_seed=int(sample_seed),
        basin_source=basin_source,
        basin_counts_by_item=basin_counts,
        accepted_source_sample_counts_by_item=accepted_counts,
        excluded_source_sample_counts_by_item=excluded_counts,
        basin_diagnostics=basin_rows,
        convergence=convergence,
        item_mean_semantics=("dominant_basin_mean" if np.any(basin_counts > 1) else "single_periodic_mean"),
    )

