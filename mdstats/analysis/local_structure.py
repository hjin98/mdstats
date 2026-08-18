"""General local-structure features for atomistic selections.

This analysis-owned module provides reusable, deterministic local geometry
features.  The MLFF training-data branch may aggregate these features for data
selection, but it does not own the geometry kernels defined here.

The first implementation deliberately uses a transparent dense minimum-image
calculation.  It is intended for selection/validation subsets and is guarded by
an explicit pair-work limit.  A later implementation may route the same public
result contract through the shared cell-list/Verlet neighbor backend.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray
from ase.data import covalent_radii
from scipy.special import eval_legendre

from ..collection import AtomisticFrameCollection
from ._neighbors import minimum_image_vectors

try:  # SciPy >= 1.15
    from scipy.special import sph_harm_y as _sph_harm_y
except ImportError:  # pragma: no cover - older supported SciPy
    _sph_harm_y = None
    from scipy.special import sph_harm as _sph_harm


LOCAL_STRUCTURE_POLICY_SCHEMA = "mdstats.local-structure-feature-policy.v1"
LOCAL_STRUCTURE_RESULT_SCHEMA = "mdstats.local-structure-feature-result.v1"
LOCAL_STRUCTURE_POLICY_VERSION = "mdstats.analysis.local-structure.2026-07.v1"

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]


class LocalStructureError(RuntimeError):
    """Base error for local-structure feature construction."""


class LocalStructureComplexityError(LocalStructureError):
    """Raised when the transparent dense kernel exceeds its declared budget."""


def _finite_positive(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite.")
    return result


def _positive_orders(values: tuple[int, ...], *, name: str) -> tuple[int, ...]:
    result = tuple(sorted(set(int(value) for value in values)))
    if not result or any(value <= 0 for value in result):
        raise ValueError(f"{name} must contain positive integers.")
    return result


@dataclass(frozen=True, slots=True)
class LocalStructureFeaturePolicy:
    """Numerical policy for general local-environment features.

    ``normalized_switch_start`` and ``normalized_switch_end`` multiply the sum
    of ASE covalent radii for each atom pair.  This produces a chemistry-aware,
    smooth connectivity weight without asserting a discrete chemical bond.
    """

    normalized_switch_start: float = 1.15
    normalized_switch_end: float = 1.75
    radial_centers_angstrom: tuple[float, ...] = (
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.5,
        4.0,
        5.0,
    )
    radial_width_angstrom: float = 0.35
    density_radius_angstrom: float = 4.0
    angular_legendre_orders: tuple[int, ...] = (1, 2, 3, 4)
    orientational_orders: tuple[int, ...] = (4, 6)
    minimum_weight: float = 1.0e-8
    coincident_tolerance_angstrom: float = 1.0e-8
    fallback_covalent_radius_angstrom: float = 1.0
    maximum_dense_pair_work: int = 4_000_000
    policy_version: str = LOCAL_STRUCTURE_POLICY_VERSION

    def __post_init__(self) -> None:
        start = _finite_positive(self.normalized_switch_start, name="normalized_switch_start")
        end = _finite_positive(self.normalized_switch_end, name="normalized_switch_end")
        if start >= end:
            raise ValueError("normalized_switch_start must be smaller than normalized_switch_end.")
        centers = tuple(float(value) for value in self.radial_centers_angstrom)
        if not centers or any(not np.isfinite(value) or value <= 0.0 for value in centers):
            raise ValueError("radial_centers_angstrom must be positive and finite.")
        if any(second <= first for first, second in zip(centers, centers[1:])):
            raise ValueError("radial_centers_angstrom must be strictly increasing.")
        width = _finite_positive(self.radial_width_angstrom, name="radial_width_angstrom")
        density_radius = _finite_positive(self.density_radius_angstrom, name="density_radius_angstrom")
        minimum_weight = _finite_positive(self.minimum_weight, name="minimum_weight")
        if minimum_weight >= 1.0:
            raise ValueError("minimum_weight must be smaller than one.")
        tolerance = _finite_positive(self.coincident_tolerance_angstrom, name="coincident_tolerance_angstrom")
        fallback = _finite_positive(self.fallback_covalent_radius_angstrom, name="fallback_covalent_radius_angstrom")
        if isinstance(self.maximum_dense_pair_work, bool) or int(self.maximum_dense_pair_work) <= 0:
            raise ValueError("maximum_dense_pair_work must be a positive integer.")
        if not str(self.policy_version).strip():
            raise ValueError("policy_version must be non-empty.")
        object.__setattr__(self, "normalized_switch_start", start)
        object.__setattr__(self, "normalized_switch_end", end)
        object.__setattr__(self, "radial_centers_angstrom", centers)
        object.__setattr__(self, "radial_width_angstrom", width)
        object.__setattr__(self, "density_radius_angstrom", density_radius)
        object.__setattr__(self, "angular_legendre_orders", _positive_orders(self.angular_legendre_orders, name="angular_legendre_orders"))
        object.__setattr__(self, "orientational_orders", _positive_orders(self.orientational_orders, name="orientational_orders"))
        object.__setattr__(self, "minimum_weight", minimum_weight)
        object.__setattr__(self, "coincident_tolerance_angstrom", tolerance)
        object.__setattr__(self, "fallback_covalent_radius_angstrom", fallback)
        object.__setattr__(self, "maximum_dense_pair_work", int(self.maximum_dense_pair_work))

    @property
    def feature_names(self) -> tuple[str, ...]:
        names = [
            "nearest_neighbor_distance_angstrom",
            "weighted_neighbor_distance_mean_angstrom",
            "weighted_neighbor_distance_std_angstrom",
            "smooth_coordination",
            "hard_neighbor_count",
            "weighted_degree_l2",
            "neighbor_species_entropy",
            "local_number_density_angstrom^-3",
        ]
        names.extend(f"radial_density_r{center:.3f}_angstrom" for center in self.radial_centers_angstrom)
        names.extend(f"angular_legendre_l{order}" for order in self.angular_legendre_orders)
        names.extend(f"bond_orientational_q{order}" for order in self.orientational_orders)
        return tuple(names)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": LOCAL_STRUCTURE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "normalized_switch_start": self.normalized_switch_start,
            "normalized_switch_end": self.normalized_switch_end,
            "radial_centers_angstrom": list(self.radial_centers_angstrom),
            "radial_width_angstrom": self.radial_width_angstrom,
            "density_radius_angstrom": self.density_radius_angstrom,
            "angular_legendre_orders": list(self.angular_legendre_orders),
            "orientational_orders": list(self.orientational_orders),
            "minimum_weight": self.minimum_weight,
            "coincident_tolerance_angstrom": self.coincident_tolerance_angstrom,
            "fallback_covalent_radius_angstrom": self.fallback_covalent_radius_angstrom,
            "maximum_dense_pair_work": self.maximum_dense_pair_work,
            "feature_names": list(self.feature_names),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LocalStructureFeaturePolicy":
        if payload.get("schema") != LOCAL_STRUCTURE_POLICY_SCHEMA:
            raise ValueError("Unsupported local-structure feature-policy schema.")
        result = cls(
            normalized_switch_start=float(payload["normalized_switch_start"]),
            normalized_switch_end=float(payload["normalized_switch_end"]),
            radial_centers_angstrom=tuple(float(value) for value in payload["radial_centers_angstrom"]),
            radial_width_angstrom=float(payload["radial_width_angstrom"]),
            density_radius_angstrom=float(payload["density_radius_angstrom"]),
            angular_legendre_orders=tuple(int(value) for value in payload["angular_legendre_orders"]),
            orientational_orders=tuple(int(value) for value in payload["orientational_orders"]),
            minimum_weight=float(payload["minimum_weight"]),
            coincident_tolerance_angstrom=float(payload["coincident_tolerance_angstrom"]),
            fallback_covalent_radius_angstrom=float(payload["fallback_covalent_radius_angstrom"]),
            maximum_dense_pair_work=int(payload["maximum_dense_pair_work"]),
            policy_version=str(payload["policy_version"]),
        )
        if tuple(payload.get("feature_names", ())) not in ((), result.feature_names):
            raise ValueError("Local-structure feature ordering changed.")
        return result


@dataclass(slots=True)
class LocalStructureFeatureResult:
    """Per-atom local geometry matrix for one collection frame."""

    frame_index: int
    atom_indices: IntArray
    atomic_numbers: NDArray[np.int32]
    feature_names: tuple[str, ...]
    values: FloatArray
    missing_mask: BoolArray
    warning_codes: tuple[str, ...]
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        self.frame_index = int(self.frame_index)
        self.atom_indices = np.asarray(self.atom_indices, dtype=np.int64).copy()
        self.atomic_numbers = np.asarray(self.atomic_numbers, dtype=np.int32).copy()
        self.values = np.asarray(self.values, dtype=np.float64).copy()
        self.missing_mask = np.asarray(self.missing_mask, dtype=np.bool_).copy()
        self.feature_names = tuple(str(value) for value in self.feature_names)
        self.warning_codes = tuple(sorted(set(str(value) for value in self.warning_codes)))
        self.metadata = dict(self.metadata)
        expected = (self.atom_indices.size, len(self.feature_names))
        if self.frame_index < 0:
            raise ValueError("frame_index must be nonnegative.")
        if self.atomic_numbers.shape != self.atom_indices.shape:
            raise ValueError("atomic_numbers must align with atom_indices.")
        if self.values.shape != expected or self.missing_mask.shape != expected:
            raise ValueError("Local-structure arrays do not match atom/feature dimensions.")
        if len(set(self.feature_names)) != len(self.feature_names) or not self.feature_names:
            raise ValueError("feature_names must be non-empty and unique.")
        if np.any(~np.isfinite(self.values)):
            raise ValueError("Local-structure values must be finite; missing values use missing_mask.")
        for array in (self.atom_indices, self.atomic_numbers, self.values, self.missing_mask):
            array.setflags(write=False)

    def feature_index(self, name: str) -> int:
        try:
            return self.feature_names.index(str(name))
        except ValueError as exc:
            raise KeyError(name) from exc

    def feature(self, name: str) -> FloatArray:
        return self.values[:, self.feature_index(name)]


def _smooth_weights(normalized_distance: FloatArray, *, start: float, end: float) -> FloatArray:
    weights = np.zeros_like(normalized_distance)
    weights[normalized_distance <= start] = 1.0
    transition = (normalized_distance > start) & (normalized_distance < end)
    x = (normalized_distance[transition] - start) / (end - start)
    weights[transition] = 0.5 * (1.0 + np.cos(np.pi * x))
    return weights


def _spherical_harmonics_all_m(
    order: int, theta: FloatArray, phi: FloatArray
) -> NDArray[np.complex128]:
    """Evaluate every ``m`` for one angular order in a single ufunc call.

    The previous scalar-``m`` loop issued 9 or 13 Python/SciPy calls per atom for
    the default q4/q6 features.  Broadcasting ``m`` keeps the same equations
    while moving the hot loop into SciPy's compiled ufunc implementation.
    """

    m_values = np.arange(-order, order + 1, dtype=np.int64)[:, None]
    if _sph_harm_y is not None:
        return np.asarray(
            _sph_harm_y(order, m_values, theta[None, :], phi[None, :]),
            dtype=np.complex128,
        )
    return np.asarray(  # type: ignore[name-defined]
        _sph_harm(m_values, order, phi[None, :], theta[None, :]),
        dtype=np.complex128,
    )


def _orientational_order(vectors: FloatArray, weights: FloatArray, order: int) -> float | None:
    weight_sum = float(np.sum(weights))
    if vectors.shape[0] == 0 or weight_sum <= 0.0:
        return None
    norms = np.linalg.norm(vectors, axis=1)
    unit = vectors / norms[:, None]
    theta = np.arccos(np.clip(unit[:, 2], -1.0, 1.0))
    phi = np.arctan2(unit[:, 1], unit[:, 0])
    harmonics = _spherical_harmonics_all_m(order, theta, phi)
    q_lm = np.sum(harmonics * weights[None, :], axis=1) / weight_sum
    total = float(np.sum(np.abs(q_lm) ** 2))
    return float(np.sqrt(4.0 * np.pi * total / (2 * order + 1)))


def _angular_moments(vectors: FloatArray, weights: FloatArray, orders: tuple[int, ...]) -> tuple[float | None, ...]:
    n_neighbors = vectors.shape[0]
    if n_neighbors < 2:
        return tuple(None for _ in orders)
    unit = vectors / np.linalg.norm(vectors, axis=1)[:, None]
    first, second = _cached_upper_triangle_indices(n_neighbors)
    pair_weights = weights[first] * weights[second]
    valid = pair_weights > 0.0
    if not np.any(valid):
        return tuple(None for _ in orders)
    cosine = np.einsum("ij,ij->i", unit[first[valid]], unit[second[valid]])
    pair_weights = pair_weights[valid]
    denominator = float(np.sum(pair_weights))
    legendre = eval_legendre(
        np.asarray(orders, dtype=np.int64)[:, None], cosine[None, :]
    )
    values = np.sum(legendre * pair_weights[None, :], axis=1) / denominator
    return tuple(float(value) for value in values)


@lru_cache(maxsize=128)
def _cached_upper_triangle_indices(
    size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return immutable upper-triangle pair indices for a neighbor count.

    Local coordination counts repeat heavily across atoms and frames. Building
    the same ``np.triu_indices`` arrays millions of times was a measurable
    Python/allocation hotspot in DATA6 finalization.
    """

    first, second = np.triu_indices(int(size), k=1)
    first = np.asarray(first, dtype=np.int64)
    second = np.asarray(second, dtype=np.int64)
    first.setflags(write=False)
    second.setflags(write=False)
    return first, second


def _angular_and_orientational_moments(
    vectors: FloatArray,
    weights: FloatArray,
    angular_orders: tuple[int, ...],
    orientational_orders: tuple[int, ...],
) -> tuple[tuple[float | None, ...], tuple[float | None, ...]]:
    """Evaluate angular moments and Steinhardt ``q_l`` from one dot matrix.

    The spherical-harmonic addition theorem gives

    ``q_l^2 = sum_jk w_j w_k P_l(r_j . r_k) / (sum_j w_j)^2``.

    Reusing the same pair cosines needed by the angular moments removes the
    former per-atom complex spherical-harmonic calls while preserving the
    exact rotational invariant (up to floating-point roundoff).
    """

    n_neighbors = vectors.shape[0]
    weight_sum = float(np.sum(weights))
    if n_neighbors == 0 or weight_sum <= 0.0:
        return (
            tuple(None for _ in angular_orders),
            tuple(None for _ in orientational_orders),
        )
    unit = vectors / np.linalg.norm(vectors, axis=1)[:, None]
    first, second = _cached_upper_triangle_indices(n_neighbors)
    pair_weights = weights[first] * weights[second]
    union_orders = tuple(sorted(set((*angular_orders, *orientational_orders))))
    by_order: dict[int, np.ndarray] = {}
    if first.size:
        cosine = np.einsum("ij,ij->i", unit[first], unit[second])
        evaluated = eval_legendre(
            np.asarray(union_orders, dtype=np.int64)[:, None],
            cosine[None, :],
        )
        by_order = {
            order: np.asarray(evaluated[index], dtype=np.float64)
            for index, order in enumerate(union_orders)
        }

    pair_weight_sum = float(np.sum(pair_weights))
    angular: list[float | None] = []
    for order in angular_orders:
        if n_neighbors < 2 or pair_weight_sum <= 0.0:
            angular.append(None)
        else:
            angular.append(
                float(np.sum(by_order[order] * pair_weights) / pair_weight_sum)
            )

    self_weight = float(np.dot(weights, weights))
    orientational: list[float | None] = []
    for order in orientational_orders:
        cross = (
            0.0
            if not first.size
            else 2.0 * float(np.sum(by_order[order] * pair_weights))
        )
        q_squared = max(0.0, (self_weight + cross) / (weight_sum * weight_sum))
        orientational.append(float(np.sqrt(q_squared)))
    return tuple(angular), tuple(orientational)


def _batched_angular_and_orientational_moments(
    vectors: FloatArray,
    weights: FloatArray,
    valid_neighbors: BoolArray,
    angular_orders: tuple[int, ...],
    orientational_orders: tuple[int, ...],
) -> tuple[FloatArray, BoolArray, FloatArray, BoolArray]:
    """Evaluate invariant angular features in neighbor-count batches.

    Local coordination numbers repeat heavily in crystals and liquids.  The
    former implementation invoked Python and ``eval_legendre`` once per center
    atom.  Grouping centers with the same valid-neighbor count preserves the
    exact pair formulas while moving pair gathering, dot products, Legendre
    evaluation, and reductions into compiled NumPy/SciPy kernels.
    """

    center_count = int(vectors.shape[0])
    angular = np.zeros((center_count, len(angular_orders)), dtype=np.float64)
    orientational = np.zeros(
        (center_count, len(orientational_orders)), dtype=np.float64
    )
    angular_missing = np.ones_like(angular, dtype=np.bool_)
    orientational_missing = np.ones_like(orientational, dtype=np.bool_)
    neighbor_counts = np.count_nonzero(valid_neighbors, axis=1)
    union_orders = tuple(sorted(set((*angular_orders, *orientational_orders))))
    order_index = {order: index for index, order in enumerate(union_orders)}

    for neighbor_count in np.unique(neighbor_counts):
        count = int(neighbor_count)
        if count <= 0:
            continue
        rows = np.flatnonzero(neighbor_counts == count)
        nonzero_rows, columns = np.nonzero(valid_neighbors[rows])
        if columns.size != rows.size * count:
            raise RuntimeError("Batched local-neighbor grouping is inconsistent.")
        # np.nonzero traverses C-order, so equal-count row memberships reshape
        # directly into one index row per center.
        columns = columns.reshape(rows.size, count)
        selected_vectors = vectors[rows[:, None], columns]
        selected_weights = weights[rows[:, None], columns]
        norms = np.linalg.norm(selected_vectors, axis=2)
        unit = selected_vectors / norms[:, :, None]
        weight_sum = np.sum(selected_weights, axis=1)
        self_weight = np.sum(selected_weights * selected_weights, axis=1)

        first, second = _cached_upper_triangle_indices(count)
        if first.size:
            # The contraction is tiny and repeated once per coordination
            # group.  ``optimize=True`` recomputes an einsum path for every
            # group even though this two-operand contraction has no alternate
            # contraction order.  The direct c_einsum path is numerically
            # identical and avoids that Python planning overhead.
            cosines = np.einsum(
                "gpi,gpi->gp",
                unit[:, first, :],
                unit[:, second, :],
                optimize=False,
            )
            pair_weights = (
                selected_weights[:, first] * selected_weights[:, second]
            )
            evaluated = eval_legendre(
                np.asarray(union_orders, dtype=np.int64)[:, None, None],
                cosines[None, :, :],
            )
            weighted_legendre = np.sum(
                evaluated * pair_weights[None, :, :], axis=2
            )
            pair_weight_sum = np.sum(pair_weights, axis=1)
        else:
            weighted_legendre = np.zeros(
                (len(union_orders), rows.size), dtype=np.float64
            )
            pair_weight_sum = np.zeros(rows.size, dtype=np.float64)

        if count >= 2:
            valid_pair_rows = pair_weight_sum > 0.0
            for output_column, order in enumerate(angular_orders):
                values = np.divide(
                    weighted_legendre[order_index[order]],
                    pair_weight_sum,
                    out=np.zeros(rows.size, dtype=np.float64),
                    where=valid_pair_rows,
                )
                angular[rows, output_column] = values
                angular_missing[rows, output_column] = ~valid_pair_rows

        valid_weight_rows = weight_sum > 0.0
        for output_column, order in enumerate(orientational_orders):
            cross = 2.0 * weighted_legendre[order_index[order]]
            q_squared = np.divide(
                self_weight + cross,
                weight_sum * weight_sum,
                out=np.zeros(rows.size, dtype=np.float64),
                where=valid_weight_rows,
            )
            orientational[rows, output_column] = np.sqrt(
                np.maximum(q_squared, 0.0)
            )
            orientational_missing[rows, output_column] = ~valid_weight_rows

    return angular, angular_missing, orientational, orientational_missing


@lru_cache(maxsize=128)
def _cached_species_geometry(
    atomic_numbers: tuple[int, ...],
    fallback_radius: float,
) -> tuple[np.ndarray, tuple[int, ...], np.ndarray]:
    """Cache chemistry-only arrays shared by every frame of a trajectory."""

    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    radii = np.empty(numbers.size, dtype=np.float64)
    fallback_numbers: list[int] = []
    for index, atomic_number in enumerate(numbers):
        radius = (
            float(covalent_radii[int(atomic_number)])
            if int(atomic_number) < len(covalent_radii)
            else 0.0
        )
        if not np.isfinite(radius) or radius <= 0.0:
            radius = float(fallback_radius)
            fallback_numbers.append(int(atomic_number))
        radii[index] = radius
    _, inverse_species = np.unique(numbers, return_inverse=True)
    species_indicator = np.eye(
        int(np.max(inverse_species)) + 1, dtype=np.float64
    )[inverse_species]
    radii.setflags(write=False)
    species_indicator.setflags(write=False)
    return radii, tuple(sorted(set(fallback_numbers))), species_indicator


@dataclass(frozen=True, slots=True)
class _LocalStructureTopologyWorkspace:
    """Execution-only chemistry/topology arrays shared by fixed-topology frames."""

    atomic_numbers: NDArray[np.int32]
    radii: FloatArray
    species_indicator: FloatArray
    pair_radii: FloatArray
    all_centers: IntArray
    upper_first: IntArray
    upper_second: IntArray
    fallback_atomic_numbers: tuple[int, ...]


@dataclass(slots=True)
class _LocalStructureScratch:
    """Bounded worker-local scratch for direct structural frame execution.

    The current qualified scratch retains only wrapped fractional coordinates.
    Larger dense pair/radial scratch buffers were benchmarked during PERF-P3
    and rejected because they increased resident memory and reduced throughput
    on the bounded LTA-like workload.
    """

    wrapped_fractional: FloatArray | None = None

    def wrapped(self, fractional: FloatArray, pbc: BoolArray) -> FloatArray:
        shape = tuple(int(value) for value in fractional.shape)
        if self.wrapped_fractional is None or self.wrapped_fractional.shape != shape:
            self.wrapped_fractional = np.empty(shape, dtype=np.float64)
        np.copyto(self.wrapped_fractional, fractional)
        for axis in range(3):
            if bool(pbc[axis]):
                self.wrapped_fractional[:, axis] %= 1.0
        return self.wrapped_fractional


@lru_cache(maxsize=128)
def _cached_local_structure_topology(
    atomic_numbers: tuple[int, ...],
    fallback_radius: float,
) -> _LocalStructureTopologyWorkspace:
    """Cache immutable topology-only arrays for direct frame kernels."""

    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    radii, fallback_numbers, species_indicator = _cached_species_geometry(
        atomic_numbers, fallback_radius
    )
    pair_radii = np.asarray(radii[:, None] + radii[None, :], dtype=np.float64)
    centers = np.arange(numbers.size, dtype=np.int64)
    upper_first, upper_second = _cached_upper_triangle_indices(numbers.size)
    for array in (numbers, pair_radii, centers):
        array.setflags(write=False)
    return _LocalStructureTopologyWorkspace(
        atomic_numbers=numbers,
        radii=radii,
        species_indicator=species_indicator,
        pair_radii=pair_radii,
        all_centers=centers,
        upper_first=upper_first,
        upper_second=upper_second,
        fallback_atomic_numbers=fallback_numbers,
    )


def _local_structure_topology_workspace(
    atomic_numbers: ArrayLike,
    *,
    policy: LocalStructureFeaturePolicy,
) -> _LocalStructureTopologyWorkspace:
    """Return the execution-only cached workspace for one fixed topology."""

    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    if numbers.ndim != 1 or numbers.size == 0:
        raise ValueError("atomic_numbers must be a non-empty one-dimensional array.")
    return _cached_local_structure_topology(
        tuple(int(value) for value in numbers),
        policy.fallback_covalent_radius_angstrom,
    )


def _compute_local_structure_features_arrays(
    *,
    atomic_numbers: ArrayLike,
    fractional_positions: ArrayLike,
    cell: ArrayLike,
    pbc: ArrayLike,
    frame_index: int = 0,
    atom_indices: ArrayLike | None = None,
    policy: LocalStructureFeaturePolicy | None = None,
    topology_workspace: _LocalStructureTopologyWorkspace | None = None,
    scratch: _LocalStructureScratch | None = None,
    wrap_periodic: bool = False,
    origin: ArrayLike | None = None,
) -> LocalStructureFeatureResult:
    """Internal direct numerical frame kernel used by high-throughput DATA6.

    ``topology_workspace`` and ``scratch`` are execution-only accelerators. They
    never enter result metadata or scientific identity.
    """

    active = LocalStructureFeaturePolicy() if policy is None else policy
    if not isinstance(active, LocalStructureFeaturePolicy):
        raise TypeError("policy must be a LocalStructureFeaturePolicy.")
    frame_index = int(frame_index)
    if frame_index < 0:
        raise IndexError("frame_index must be nonnegative.")
    numbers = np.asarray(atomic_numbers, dtype=np.int32)
    fractional = np.asarray(fractional_positions, dtype=np.float64)
    cell = np.asarray(cell, dtype=np.float64)
    pbc_array = np.asarray(pbc, dtype=np.bool_)
    if numbers.ndim != 1 or numbers.size == 0:
        raise ValueError("atomic_numbers must be a non-empty one-dimensional array.")
    if fractional.shape != (numbers.size, 3):
        raise ValueError("fractional_positions must have shape (n_atoms, 3).")
    if cell.shape != (3, 3) or pbc_array.shape != (3,):
        raise ValueError("cell and pbc must have shapes (3, 3) and (3,).")
    topology = (
        _local_structure_topology_workspace(numbers, policy=active)
        if topology_workspace is None
        else topology_workspace
    )
    if not np.array_equal(numbers, topology.atomic_numbers):
        raise ValueError("topology_workspace atomic numbers do not match the frame.")
    if atom_indices is None:
        centers = topology.all_centers
    else:
        centers = np.asarray(atom_indices, dtype=np.int64)
        if centers.ndim != 1 or centers.size == 0:
            raise ValueError("atom_indices must be a non-empty one-dimensional selection.")
        if (
            np.any(centers < 0)
            or np.any(centers >= numbers.size)
            or len(set(int(v) for v in centers)) != centers.size
        ):
            raise ValueError("atom_indices contain invalid or duplicate indices.")
        centers = np.sort(centers)
    pair_work = int(centers.size) * int(numbers.size)
    if pair_work > active.maximum_dense_pair_work:
        raise LocalStructureComplexityError(
            f"Dense local-structure pair work {pair_work} exceeds the declared limit "
            f"{active.maximum_dense_pair_work}."
        )

    if wrap_periodic:
        if scratch is None:
            fractional = np.array(fractional, copy=True)
            for axis in range(3):
                if pbc_array[axis]:
                    fractional[:, axis] %= 1.0
        else:
            fractional = scratch.wrapped(fractional, pbc_array)
    origin_array = (
        np.zeros(3, dtype=np.float64)
        if origin is None
        else np.asarray(origin, dtype=np.float64)
    )
    if origin_array.shape != (3,):
        raise ValueError("origin must have shape (3,).")
    cartesian = fractional @ cell + origin_array
    all_atoms = centers.size == numbers.size and np.array_equal(centers, topology.all_centers)
    if all_atoms:
        first, second = topology.upper_first, topology.upper_second
        pair_vectors, pair_distances = minimum_image_vectors(
            cartesian[second] - cartesian[first],
            cell=cell,
            pbc=pbc_array,
        )
        vectors = np.zeros((numbers.size, numbers.size, 3), dtype=np.float64)
        distances = np.full((numbers.size, numbers.size), np.inf, dtype=np.float64)
        vectors[first, second] = pair_vectors
        vectors[second, first] = -pair_vectors
        distances[first, second] = pair_distances
        distances[second, first] = pair_distances
    else:
        raw = cartesian[None, :, :] - cartesian[centers, None, :]
        vectors, distances = minimum_image_vectors(raw, cell=cell, pbc=pbc_array)
        vectors = np.asarray(vectors, dtype=np.float64)
        distances = np.asarray(distances, dtype=np.float64)
        center_rows = np.arange(centers.size, dtype=np.int64)
        distances[center_rows, centers] = np.inf
        vectors[center_rows, centers] = 0.0

    warnings: set[str] = set()
    finite_distances = distances[np.isfinite(distances)]
    if finite_distances.size and float(np.min(finite_distances)) <= active.coincident_tolerance_angstrom:
        warnings.add("near_coincident_distinct_atoms")

    numbers = topology.atomic_numbers
    fallback_numbers = topology.fallback_atomic_numbers
    species_indicator = topology.species_indicator
    if fallback_numbers:
        warnings.add("fallback_covalent_radius_used")

    pair_radii = (
        topology.pair_radii
        if all_atoms
        else topology.radii[centers, None] + topology.radii[None, :]
    )
    normalized = distances / pair_radii
    weights = _smooth_weights(
        normalized,
        start=active.normalized_switch_start,
        end=active.normalized_switch_end,
    )
    weights[~np.isfinite(distances)] = 0.0

    names = active.feature_names
    values = np.zeros((centers.size, len(names)), dtype=np.float64)
    missing = np.zeros_like(values, dtype=np.bool_)
    density_volume = 4.0 * np.pi * active.density_radius_angstrom**3 / 3.0
    radial_centers = np.asarray(active.radial_centers_angstrom, dtype=np.float64)
    radial_width = active.radial_width_angstrom

    # All scalar/radial features are dense reductions over the same pair
    # matrices.  Evaluate them once in vectorized form instead of repeating
    # Python reductions for every center atom.
    finite = np.isfinite(distances)
    safe_distances = np.where(finite, distances, 0.0)
    retained = weights > active.minimum_weight
    finite_count = np.count_nonzero(finite, axis=1)
    total_weight = np.sum(weights, axis=1)
    weighted_distance_sum = np.sum(weights * safe_distances, axis=1)
    weighted_mean = np.divide(
        weighted_distance_sum,
        total_weight,
        out=np.zeros_like(total_weight),
        where=total_weight > 0.0,
    )
    centered = np.where(finite, distances - weighted_mean[:, None], 0.0)
    weighted_variance = np.divide(
        np.sum(weights * centered * centered, axis=1),
        total_weight,
        out=np.zeros_like(total_weight),
        where=total_weight > 0.0,
    )

    values[:, 0] = np.min(distances, axis=1)
    missing[:, 0] = finite_count == 0
    values[missing[:, 0], 0] = 0.0
    values[:, 1] = weighted_mean
    values[:, 2] = np.sqrt(np.maximum(weighted_variance, 0.0))
    missing[:, 1:3] = (total_weight <= 0.0)[:, None]
    values[missing[:, 1], 1] = 0.0
    values[missing[:, 2], 2] = 0.0
    values[:, 3] = total_weight
    retained_count = np.count_nonzero(retained, axis=1)
    values[:, 4] = retained_count
    values[:, 5] = np.sqrt(np.sum(weights * weights, axis=1))

    species_weight = weights @ species_indicator
    probabilities = np.divide(
        species_weight,
        total_weight[:, None],
        out=np.zeros_like(species_weight),
        where=total_weight[:, None] > 0.0,
    )
    log_probabilities = np.zeros_like(probabilities)
    positive_probabilities = probabilities > 0.0
    log_probabilities[positive_probabilities] = np.log(
        probabilities[positive_probabilities]
    )
    values[:, 6] = -np.sum(probabilities * log_probabilities, axis=1)
    missing[:, 6] = total_weight <= 0.0
    values[missing[:, 6], 6] = 0.0

    gaussian_density = np.exp(
        -((np.where(finite, distances, np.inf) / active.density_radius_angstrom) ** 2)
    )
    values[:, 7] = np.sum(gaussian_density, axis=1) / density_volume
    radial = np.exp(
        -0.5
        * (
            (
                np.where(finite, distances, np.inf)[:, :, None]
                - radial_centers[None, None, :]
            )
            / radial_width
        )
        ** 2
    )
    radial_start = 8
    radial_end = radial_start + radial_centers.size
    values[:, radial_start:radial_end] = np.sum(radial, axis=1)

    angular_start = radial_end
    orientational_start = angular_start + len(active.angular_legendre_orders)
    valid_angular_neighbors = retained & (
        distances > active.coincident_tolerance_angstrom
    )
    (
        angular_values,
        angular_missing,
        orientational_values,
        orientational_missing,
    ) = _batched_angular_and_orientational_moments(
        vectors,
        weights,
        valid_angular_neighbors,
        active.angular_legendre_orders,
        active.orientational_orders,
    )
    values[
        :, angular_start:orientational_start
    ] = angular_values
    missing[
        :, angular_start:orientational_start
    ] = angular_missing
    orientational_end = orientational_start + len(active.orientational_orders)
    values[
        :, orientational_start:orientational_end
    ] = orientational_values
    missing[
        :, orientational_start:orientational_end
    ] = orientational_missing

    if np.any(retained_count == 0):
        warnings.add("atom_without_smooth_neighbors")
    if np.any((retained_count > 0) & (retained_count < 2)):
        warnings.add("atom_without_angular_neighbor_pair")

    return LocalStructureFeatureResult(
        frame_index=frame_index,
        atom_indices=centers,
        atomic_numbers=numbers[centers],
        feature_names=names,
        values=values,
        missing_mask=missing,
        warning_codes=tuple(warnings),
        metadata={
            "schema": LOCAL_STRUCTURE_RESULT_SCHEMA,
            "policy": active.to_dict(),
            "pair_work": pair_work,
            "fallback_covalent_radius_atomic_numbers": sorted(set(fallback_numbers)),
            "connectivity_semantics": "smooth chemistry-scaled covalent-radius weight; not a discrete chemical bond",
            "density_semantics": "Gaussian local number density divided by the declared spherical support volume",
        },
    )


def compute_local_structure_features(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    atom_indices: ArrayLike | None = None,
    policy: LocalStructureFeaturePolicy | None = None,
) -> LocalStructureFeatureResult:
    """Compute general per-atom local geometry features for one frame.

    Neighbors are drawn from the complete collection population. ``atom_indices``
    selects centers only. Periodicity and triclinic minimum-image geometry are
    inherited from :class:`AtomisticFrameCollection`.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    index = int(frame_index)
    if index < 0 or index >= collection.n_frames:
        raise IndexError("frame_index is outside the collection.")
    return _compute_local_structure_features_arrays(
        atomic_numbers=collection.atomic_numbers,
        fractional_positions=collection.fractional_positions[index],
        cell=collection.cells[index],
        pbc=collection.pbc,
        frame_index=index,
        atom_indices=atom_indices,
        policy=policy,
        origin=collection.origins[index],
    )
