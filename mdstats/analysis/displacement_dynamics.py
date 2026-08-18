"""Displacement-distribution observables built on the D0 block iterator.

D1 implements the radial self van Hove distribution. D2 implements the
dimension-correct non-Gaussian displacement parameter. D3 implements
self-intermediate scattering in isotropic-magnitude and explicit-vector modes.
Coordinate, drift, selection, projection, and provenance semantics are delegated
to D0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import j0, spherical_jn

from ..collection import AtomisticFrameCollection
from ._displacement_common import (
    DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
    CoordinateMode,
    DisplacementBlockPlan,
    DisplacementInputBundle,
    DriftMode,
    ReferenceCellInput,
    _resolve_lag_steps,
    iter_displacement_blocks,
    prepare_displacement_inputs,
    resolve_displacement_block_plan,
)
from ._dynamics_common import (
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    require_bool,
    require_finite_real,
    require_nonnegative_int,
    require_positive_int,
)
from .selection import SpeciesSelection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
AxisLabel = Literal["x", "y", "z"]

_D1_CONTRACT_VERSION = "self-van-hove-v1"
_D2_CONTRACT_VERSION = "non-gaussian-parameter-v1"
_D3_CONTRACT_VERSION = "self-intermediate-scattering-v1"
_Q_SUBSPACE_TOLERANCE = 1.0e-10
_SCATTERING_TRANSIENT_TARGET_BYTES = 64 * 1024**2
_DEFAULT_N_BINS = 200


def _as_integer_array(value: ArrayLike, *, name: str) -> IntArray:
    raw = np.asarray(value)
    if np.issubdtype(raw.dtype, np.bool_) or not np.issubdtype(
        raw.dtype, np.integer
    ):
        raise TypeError(f"{name} must contain integers.")
    return np.asarray(raw, dtype=np.int64)


def _stable_vector_norm(values: FloatArray) -> FloatArray:
    """Return finite Euclidean norms without avoidable square overflow."""

    vectors = np.asarray(values, dtype=np.float64)
    scale = np.max(np.abs(vectors), axis=-1)
    normalized = np.zeros_like(vectors)
    np.divide(
        vectors,
        scale[..., None],
        out=normalized,
        where=scale[..., None] != 0.0,
    )
    norms = scale * np.sqrt(np.sum(normalized * normalized, axis=-1))
    if not np.all(np.isfinite(norms)):
        raise ValueError("Projected displacement radii contain non-finite values.")
    return np.asarray(norms, dtype=np.float64)


def _resolve_van_hove_lags(
    bundle: DisplacementInputBundle,
    *,
    lag_steps: ArrayLike | None,
    max_lag: int | None,
) -> IntArray:
    if lag_steps is not None and max_lag is not None:
        raise ValueError("Specify at most one of lag_steps and max_lag.")
    if lag_steps is not None:
        return _resolve_lag_steps(bundle, lag_steps)

    resolved_max = bundle.n_frames // 2 if max_lag is None else require_nonnegative_int(
        max_lag,
        name="max_lag",
    )
    if resolved_max >= bundle.n_frames:
        raise ValueError(
            f"max_lag={resolved_max} exceeds the largest available frame lag "
            f"{bundle.n_frames - 1}."
        )
    return np.arange(resolved_max + 1, dtype=np.int64)




def _resolve_regular_lags(
    bundle: DisplacementInputBundle,
    *,
    max_lag: int | None,
    lag_stride: int,
) -> IntArray:
    resolved_max = bundle.n_frames // 2 if max_lag is None else require_nonnegative_int(
        max_lag,
        name="max_lag",
    )
    if resolved_max >= bundle.n_frames:
        raise ValueError(
            f"max_lag={resolved_max} exceeds the largest available frame lag "
            f"{bundle.n_frames - 1}."
        )
    return np.arange(0, resolved_max + 1, lag_stride, dtype=np.int64)

def _validate_radial_edges(radial_edges: ArrayLike) -> FloatArray:
    raw = np.asarray(radial_edges)
    if np.issubdtype(raw.dtype, np.bool_):
        raise TypeError("radial_edges must contain real numbers, not booleans.")
    try:
        edges = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError("radial_edges must contain real numbers.") from exc
    if edges.ndim != 1 or edges.size < 2:
        raise ValueError(
            "radial_edges must be a one-dimensional array with at least two values."
        )
    if not np.all(np.isfinite(edges)):
        raise ValueError("radial_edges must contain only finite values.")
    if edges[0] != 0.0:
        raise ValueError("radial_edges must begin exactly at zero.")
    if np.any(np.diff(edges) <= 0.0):
        raise ValueError("radial_edges must be strictly increasing.")
    if edges[-1] <= 0.0:
        raise ValueError("The final radial edge must be positive.")
    return np.array(edges, dtype=np.float64, copy=True)


def _shell_measure(edges: FloatArray, rank: int) -> FloatArray:
    lower = edges[:-1]
    upper = edges[1:]
    if rank == 1:
        measure = 2.0 * (upper - lower)
    elif rank == 2:
        measure = np.pi * (upper * upper - lower * lower)
    elif rank == 3:
        measure = (4.0 * np.pi / 3.0) * (
            upper * upper * upper - lower * lower * lower
        )
    else:  # pragma: no cover - AnalysisSubspace already enforces this.
        raise ValueError("Subspace rank must be 1, 2, or 3.")
    if not np.all(np.isfinite(measure)) or np.any(measure <= 0.0):
        raise ValueError("Radial edges produce invalid shell measures.")
    return np.asarray(measure, dtype=np.float64)


def _iter_blocks_with_plan(
    bundle: DisplacementInputBundle,
    lags: IntArray,
    *,
    origin_stride: int,
    plan: DisplacementBlockPlan,
):
    return iter_displacement_blocks(
        bundle,
        lags,
        origin_stride=origin_stride,
        atom_block_size=plan.atom_block_size,
        origin_block_size=plan.origin_block_size,
        memory_target_bytes=plan.memory_target_bytes,
    )


def _automatic_radial_endpoint(
    bundle: DisplacementInputBundle,
    lags: IntArray,
    *,
    origin_stride: int,
    plan: DisplacementBlockPlan,
) -> tuple[float, float]:
    maximum = 0.0
    for block in _iter_blocks_with_plan(
        bundle,
        lags,
        origin_stride=origin_stride,
        plan=plan,
    ):
        radii = _stable_vector_norm(block.displacements)
        block_maximum = float(np.max(radii))
        if block_maximum > maximum:
            maximum = block_maximum

    if maximum > 0.0:
        endpoint = float(np.nextafter(maximum, np.inf))
        if not np.isfinite(endpoint):
            endpoint = maximum
    else:
        coordinate_scale = max(
            1.0,
            float(np.max(np.abs(bundle.positions))),
        )
        endpoint = float(np.sqrt(np.finfo(np.float64).eps) * coordinate_scale)
    if not np.isfinite(endpoint) or endpoint <= 0.0:
        raise ValueError("Automatic radial support could not be resolved.")
    return endpoint, maximum



def _validate_q_magnitudes(value: ArrayLike) -> FloatArray:
    raw = np.asarray(value)
    if np.issubdtype(raw.dtype, np.bool_):
        raise TypeError("q_magnitudes must contain real numbers, not booleans.")
    try:
        q = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError("q_magnitudes must contain real numbers.") from exc
    if q.ndim != 1 or q.size < 1:
        raise ValueError("q_magnitudes must be a nonempty one-dimensional array.")
    if not np.all(np.isfinite(q)):
        raise ValueError("q_magnitudes must contain only finite values.")
    if np.any(q < 0.0):
        raise ValueError("q_magnitudes must be nonnegative.")
    result = np.array(q, dtype=np.float64, copy=True)
    result[result == 0.0] = 0.0
    return result


def _validate_q_vectors(value: ArrayLike) -> FloatArray:
    raw = np.asarray(value)
    if np.issubdtype(raw.dtype, np.bool_):
        raise TypeError("q_vectors must contain real numbers, not booleans.")
    try:
        q = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise TypeError("q_vectors must contain real numbers.") from exc
    if q.ndim != 2 or q.shape[0] < 1 or q.shape[1] != 3:
        raise ValueError("q_vectors must have shape (Q, 3) with Q >= 1.")
    if not np.all(np.isfinite(q)):
        raise ValueError("q_vectors must contain only finite values.")
    result = np.array(q, dtype=np.float64, copy=True)
    result[result == 0.0] = 0.0
    return result


def _project_admissible_q_vectors(
    q_vectors: FloatArray,
    basis: FloatArray,
    *,
    tolerance: float = _Q_SUBSPACE_TOLERANCE,
) -> FloatArray:
    projected = np.einsum("qj,dj->qd", q_vectors, basis, optimize=True)
    reconstructed = np.einsum("qd,dj->qj", projected, basis, optimize=True)
    residual = np.linalg.norm(q_vectors - reconstructed, axis=1)
    scale = np.maximum(1.0, np.linalg.norm(q_vectors, axis=1))
    invalid = residual > tolerance * scale
    if np.any(invalid):
        first = int(np.flatnonzero(invalid)[0])
        raise ValueError(
            "q_vectors must lie in the selected analysis subspace; "
            f"vector {first} has residual {residual[first]:.6g}."
        )
    return np.asarray(projected, dtype=np.float64)


def _resolve_scattering_q_chunk_size(
    *,
    n_q: int,
    max_displacement_samples: int,
    isotropic: bool,
) -> int:
    # Isotropic chunks hold argument and kernel arrays. Explicit-vector chunks
    # hold phase plus complex phasor arrays. This private chunking bounds only
    # transient q work; the final (lag, q) result remains explicit.
    bytes_per_sample_q = 16 if isotropic else 24
    denominator = max(1, max_displacement_samples * bytes_per_sample_q)
    return min(n_q, max(1, _SCATTERING_TRANSIENT_TARGET_BYTES // denominator))


def _isotropic_scattering_kernel(arguments: FloatArray, rank: int) -> FloatArray:
    if not np.all(np.isfinite(arguments)):
        raise ValueError("q*r arguments contain non-finite values.")
    if rank == 1:
        values = np.cos(arguments)
    elif rank == 2:
        # The two-dimensional angular average is the cylindrical Bessel J0.
        # SciPy special-function evaluation: Virtanen et al., Nat. Methods 17,
        # 261-272 (2020), DOI 10.1038/s41592-019-0686-2.
        values = j0(arguments)
    elif rank == 3:
        # The three-dimensional angular average is spherical Bessel j0.
        values = spherical_jn(0, arguments)
    else:  # pragma: no cover - AnalysisSubspace enforces rank 1-3.
        raise ValueError("Subspace rank must be 1, 2, or 3.")
    if not np.all(np.isfinite(values)):
        raise ValueError("Isotropic scattering kernel contains non-finite values.")
    return np.asarray(values, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class SelfVanHoveResult:
    """Immutable radial self van Hove histogram and exact direct moment."""

    lag_steps: IntArray
    lag_times: FloatArray
    radial_edges: FloatArray
    radial_centers: FloatArray
    shell_measure: FloatArray
    shell_probability: FloatArray
    density: FloatArray
    counts: IntArray
    overflow_counts: IntArray
    overflow_probability: FloatArray
    n_samples: IntArray
    direct_second_moment: FloatArray
    atom_indices: IntArray
    projection_basis: FloatArray
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lag_steps = _as_integer_array(self.lag_steps, name="lag_steps")
        counts = _as_integer_array(self.counts, name="counts")
        overflow_counts = _as_integer_array(
            self.overflow_counts,
            name="overflow_counts",
        )
        n_samples = _as_integer_array(self.n_samples, name="n_samples")
        atom_indices = _as_integer_array(self.atom_indices, name="atom_indices")

        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        edges = _validate_radial_edges(self.radial_edges)
        centers = np.asarray(self.radial_centers, dtype=np.float64)
        shell_measure = np.asarray(self.shell_measure, dtype=np.float64)
        shell_probability = np.asarray(self.shell_probability, dtype=np.float64)
        density = np.asarray(self.density, dtype=np.float64)
        overflow_probability = np.asarray(
            self.overflow_probability,
            dtype=np.float64,
        )
        second_moment = np.asarray(self.direct_second_moment, dtype=np.float64)
        basis = np.asarray(self.projection_basis, dtype=np.float64)

        if lag_steps.ndim != 1 or lag_steps.size < 1:
            raise ValueError("lag_steps must be a nonempty one-dimensional array.")
        if np.any(lag_steps < 0) or (
            lag_steps.size > 1 and np.any(np.diff(lag_steps) <= 0)
        ):
            raise ValueError("lag_steps must be nonnegative, increasing, and unique.")
        n_lags = int(lag_steps.size)
        n_bins = int(edges.size - 1)
        if lag_times.shape != (n_lags,):
            raise ValueError("lag_times is inconsistent with lag_steps.")
        if centers.shape != (n_bins,):
            raise ValueError("radial_centers is inconsistent with radial_edges.")
        if shell_measure.shape != (n_bins,):
            raise ValueError("shell_measure is inconsistent with radial_edges.")
        for name, value in (
            ("shell_probability", shell_probability),
            ("density", density),
            ("counts", counts),
        ):
            if value.shape != (n_lags, n_bins):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_lags}, {n_bins})."
                )
        for name, value in (
            ("overflow_counts", overflow_counts),
            ("overflow_probability", overflow_probability),
            ("n_samples", n_samples),
            ("direct_second_moment", second_moment),
        ):
            if value.shape != (n_lags,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_lags},)."
                )
        if atom_indices.ndim != 1 or atom_indices.size < 1:
            raise ValueError("atom_indices must be a nonempty one-dimensional array.")
        if np.any(atom_indices < 0) or np.unique(atom_indices).size != atom_indices.size:
            raise ValueError("atom_indices must be unique and nonnegative.")
        if basis.ndim != 2 or basis.shape[1] != 3 or basis.shape[0] not in (1, 2, 3):
            raise ValueError("projection_basis must have shape (d, 3), d in {1,2,3}.")
        if not np.all(np.isfinite(basis)) or not np.allclose(
            basis @ basis.T,
            np.eye(basis.shape[0]),
            rtol=1.0e-10,
            atol=1.0e-12,
        ):
            raise ValueError("projection_basis rows must be finite and orthonormal.")

        finite_arrays = (
            lag_times,
            centers,
            shell_measure,
            shell_probability,
            density,
            overflow_probability,
            second_moment,
        )
        if any(not np.all(np.isfinite(value)) for value in finite_arrays):
            raise ValueError("Self van Hove result contains non-finite values.")
        if np.any(lag_times < 0.0):
            raise ValueError("lag_times must be nonnegative.")
        if np.any(counts < 0) or np.any(overflow_counts < 0):
            raise ValueError("Histogram counts must be nonnegative.")
        if np.any(n_samples <= 0):
            raise ValueError("n_samples must be positive at every lag.")
        if np.any(second_moment < 0.0):
            raise ValueError("direct_second_moment must be nonnegative.")

        expected_centers = 0.5 * (edges[:-1] + edges[1:])
        if not np.allclose(centers, expected_centers, rtol=0.0, atol=0.0):
            raise ValueError("radial_centers must be exact arithmetic midpoints.")
        expected_measure = _shell_measure(edges, int(basis.shape[0]))
        if not np.allclose(
            shell_measure,
            expected_measure,
            rtol=4.0e-15,
            atol=0.0,
        ):
            raise ValueError("shell_measure is inconsistent with edges and rank.")

        captured_counts = np.sum(counts, axis=1, dtype=np.int64)
        if not np.array_equal(captured_counts + overflow_counts, n_samples):
            raise ValueError("Histogram and overflow counts do not conserve samples.")
        expected_probability = counts / n_samples[:, None]
        expected_overflow = overflow_counts / n_samples
        if not np.allclose(
            shell_probability,
            expected_probability,
            rtol=2.0e-15,
            atol=2.0e-15,
        ):
            raise ValueError("shell_probability is inconsistent with counts.")
        if not np.allclose(
            overflow_probability,
            expected_overflow,
            rtol=2.0e-15,
            atol=2.0e-15,
        ):
            raise ValueError("overflow_probability is inconsistent with counts.")
        if np.any(shell_probability < 0.0) or np.any(overflow_probability < 0.0):
            raise ValueError("Probabilities must be nonnegative.")
        if not np.allclose(
            np.sum(shell_probability, axis=1) + overflow_probability,
            1.0,
            rtol=2.0e-15,
            atol=2.0e-15,
        ):
            raise ValueError("Captured and overflow probabilities must sum to one.")
        if not np.allclose(
            density * shell_measure[None, :],
            shell_probability,
            rtol=4.0e-15,
            atol=4.0e-15,
        ):
            raise ValueError("density is inconsistent with shell_probability.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, atom_indices):
            raise ValueError("signature atom_indices are inconsistent with the result.")
        if not np.array_equal(self.signature.projection_basis, basis):
            raise ValueError("signature projection basis is inconsistent with the result.")
        if self.signature.sample_spacing_ps is not None:
            expected_times = lag_steps.astype(np.float64) * float(
                self.signature.sample_spacing_ps
            )
            if not np.allclose(lag_times, expected_times, rtol=0.0, atol=1.0e-14):
                raise ValueError("lag_times are inconsistent with the signature.")

        object.__setattr__(
            self,
            "lag_steps",
            owned_readonly_array(lag_steps, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "lag_times",
            owned_readonly_array(lag_times, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "radial_edges",
            owned_readonly_array(edges, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "radial_centers",
            owned_readonly_array(centers, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "shell_measure",
            owned_readonly_array(shell_measure, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "shell_probability",
            owned_readonly_array(shell_probability, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "density",
            owned_readonly_array(density, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "counts",
            owned_readonly_array(counts, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "overflow_counts",
            owned_readonly_array(overflow_counts, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "overflow_probability",
            owned_readonly_array(overflow_probability, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "n_samples",
            owned_readonly_array(n_samples, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "direct_second_moment",
            owned_readonly_array(second_moment, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "atom_indices",
            owned_readonly_array(atom_indices, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "projection_basis",
            owned_readonly_array(basis, dtype=np.float64),
        )
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def captured_probability(self) -> FloatArray:
        """Return the read-only probability represented by finite radial bins."""

        return owned_readonly_array(
            1.0 - self.overflow_probability,
            dtype=np.float64,
        )


@dataclass(frozen=True, slots=True)
class NonGaussianResult:
    """Immutable projected second/fourth moments and non-Gaussian parameter."""

    lag_steps: IntArray
    lag_times: FloatArray
    second_moment: FloatArray
    fourth_moment: FloatArray
    alpha2: FloatArray
    undefined_mask: NDArray[np.bool_]
    n_samples: IntArray
    atom_indices: IntArray
    projection_basis: FloatArray
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lag_steps = _as_integer_array(self.lag_steps, name="lag_steps")
        n_samples = _as_integer_array(self.n_samples, name="n_samples")
        atom_indices = _as_integer_array(self.atom_indices, name="atom_indices")
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        second = np.asarray(self.second_moment, dtype=np.float64)
        fourth = np.asarray(self.fourth_moment, dtype=np.float64)
        alpha2 = np.asarray(self.alpha2, dtype=np.float64)
        raw_mask = np.asarray(self.undefined_mask)
        if raw_mask.dtype.kind != "b":
            raise TypeError("undefined_mask must contain booleans.")
        undefined = np.asarray(raw_mask, dtype=np.bool_)
        basis = np.asarray(self.projection_basis, dtype=np.float64)

        if lag_steps.ndim != 1 or lag_steps.size < 1:
            raise ValueError("lag_steps must be a nonempty one-dimensional array.")
        if np.any(lag_steps < 0) or (
            lag_steps.size > 1 and np.any(np.diff(lag_steps) <= 0)
        ):
            raise ValueError("lag_steps must be nonnegative, increasing, and unique.")
        n_lags = int(lag_steps.size)
        for name, value in (
            ("lag_times", lag_times),
            ("second_moment", second),
            ("fourth_moment", fourth),
            ("alpha2", alpha2),
            ("undefined_mask", undefined),
            ("n_samples", n_samples),
        ):
            if value.shape != (n_lags,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_lags},)."
                )
        if atom_indices.ndim != 1 or atom_indices.size < 1:
            raise ValueError("atom_indices must be a nonempty one-dimensional array.")
        if np.any(atom_indices < 0) or np.unique(atom_indices).size != atom_indices.size:
            raise ValueError("atom_indices must be unique and nonnegative.")
        if basis.ndim != 2 or basis.shape[1] != 3 or basis.shape[0] not in (1, 2, 3):
            raise ValueError("projection_basis must have shape (d, 3), d in {1,2,3}.")
        if not np.all(np.isfinite(basis)) or not np.allclose(
            basis @ basis.T,
            np.eye(basis.shape[0]),
            rtol=1.0e-10,
            atol=1.0e-12,
        ):
            raise ValueError("projection_basis rows must be finite and orthonormal.")
        if not np.all(np.isfinite(lag_times)) or np.any(lag_times < 0.0):
            raise ValueError("lag_times must be finite and nonnegative.")
        if not np.all(np.isfinite(second)) or np.any(second < 0.0):
            raise ValueError("second_moment must be finite and nonnegative.")
        if not np.all(np.isfinite(fourth)) or np.any(fourth < 0.0):
            raise ValueError("fourth_moment must be finite and nonnegative.")
        if np.any(n_samples <= 0):
            raise ValueError("n_samples must be positive at every lag.")

        expected_undefined = second == 0.0
        if not np.array_equal(undefined, expected_undefined):
            raise ValueError(
                "undefined_mask must be true exactly where second_moment is zero."
            )
        if np.any(fourth[undefined] != 0.0):
            raise ValueError(
                "fourth_moment must be exactly zero where second_moment is zero."
            )
        if np.any(~np.isnan(alpha2[undefined])):
            raise ValueError("alpha2 must be NaN at every undefined lag.")
        defined = ~undefined
        if np.any(~np.isfinite(alpha2[defined])):
            raise ValueError("alpha2 must be finite at every defined lag.")
        if np.any(defined):
            rank = int(basis.shape[0])
            second_defined = second[defined].astype(np.longdouble)
            fourth_defined = fourth[defined].astype(np.longdouble)
            expected = np.asarray(
                np.longdouble(rank / (rank + 2.0))
                * fourth_defined
                / (second_defined * second_defined)
                - 1.0,
                dtype=np.float64,
            )
            if not np.all(np.isfinite(expected)):
                raise ValueError("Moment ratio is not finite at a defined lag.")
            if not np.allclose(
                alpha2[defined],
                expected,
                rtol=2.0e-14,
                atol=2.0e-14,
            ):
                raise ValueError("alpha2 is inconsistent with stored moments and rank.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, atom_indices):
            raise ValueError("signature atom_indices are inconsistent with the result.")
        if not np.array_equal(self.signature.projection_basis, basis):
            raise ValueError("signature projection basis is inconsistent with the result.")
        if self.signature.sample_spacing_ps is not None:
            expected_times = lag_steps.astype(np.float64) * float(
                self.signature.sample_spacing_ps
            )
            if not np.allclose(lag_times, expected_times, rtol=0.0, atol=1.0e-14):
                raise ValueError("lag_times are inconsistent with the signature.")

        object.__setattr__(
            self, "lag_steps", owned_readonly_array(lag_steps, dtype=np.int64)
        )
        object.__setattr__(
            self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64)
        )
        object.__setattr__(
            self,
            "second_moment",
            owned_readonly_array(second, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "fourth_moment",
            owned_readonly_array(fourth, dtype=np.float64),
        )
        object.__setattr__(
            self, "alpha2", owned_readonly_array(alpha2, dtype=np.float64)
        )
        object.__setattr__(
            self,
            "undefined_mask",
            owned_readonly_array(undefined, dtype=np.bool_),
        )
        object.__setattr__(
            self, "n_samples", owned_readonly_array(n_samples, dtype=np.int64)
        )
        object.__setattr__(
            self,
            "atom_indices",
            owned_readonly_array(atom_indices, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "projection_basis",
            owned_readonly_array(basis, dtype=np.float64),
        )
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))



@dataclass(frozen=True, slots=True)
class SelfIntermediateScatteringResult:
    """Immutable self-intermediate scattering values on a resolved subspace."""

    lag_steps: IntArray
    lag_times: FloatArray
    values: NDArray[np.float64] | NDArray[np.complex128]
    q_magnitudes: FloatArray | None
    q_vectors: FloatArray | None
    projected_q_vectors: FloatArray | None
    n_samples: IntArray
    atom_indices: IntArray
    projection_basis: FloatArray
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lag_steps = _as_integer_array(self.lag_steps, name="lag_steps")
        n_samples = _as_integer_array(self.n_samples, name="n_samples")
        atom_indices = _as_integer_array(self.atom_indices, name="atom_indices")
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        basis = np.asarray(self.projection_basis, dtype=np.float64)

        if lag_steps.ndim != 1 or lag_steps.size < 1:
            raise ValueError("lag_steps must be a nonempty one-dimensional array.")
        if np.any(lag_steps < 0) or (
            lag_steps.size > 1 and np.any(np.diff(lag_steps) <= 0)
        ):
            raise ValueError("lag_steps must be nonnegative, increasing, and unique.")
        n_lags = int(lag_steps.size)
        if lag_times.shape != (n_lags,):
            raise ValueError("lag_times is inconsistent with lag_steps.")
        if n_samples.shape != (n_lags,):
            raise ValueError("n_samples is inconsistent with lag_steps.")
        if not np.all(np.isfinite(lag_times)) or np.any(lag_times < 0.0):
            raise ValueError("lag_times must be finite and nonnegative.")
        if np.any(n_samples <= 0):
            raise ValueError("n_samples must be positive at every lag.")
        if atom_indices.ndim != 1 or atom_indices.size < 1:
            raise ValueError("atom_indices must be a nonempty one-dimensional array.")
        if np.any(atom_indices < 0) or np.unique(atom_indices).size != atom_indices.size:
            raise ValueError("atom_indices must be unique and nonnegative.")
        if basis.ndim != 2 or basis.shape[1] != 3 or basis.shape[0] not in (1, 2, 3):
            raise ValueError("projection_basis must have shape (d, 3), d in {1,2,3}.")
        if not np.all(np.isfinite(basis)) or not np.allclose(
            basis @ basis.T,
            np.eye(basis.shape[0]),
            rtol=1.0e-10,
            atol=1.0e-12,
        ):
            raise ValueError("projection_basis rows must be finite and orthonormal.")

        isotropic = self.q_magnitudes is not None
        if isotropic == (self.q_vectors is not None):
            raise ValueError("Exactly one of q_magnitudes and q_vectors must be set.")

        if isotropic:
            q_magnitudes = _validate_q_magnitudes(self.q_magnitudes)
            if self.projected_q_vectors is not None:
                raise ValueError("projected_q_vectors must be None in isotropic mode.")
            q_vectors = None
            projected_q_vectors = None
            raw_values = np.asarray(self.values)
            if np.iscomplexobj(raw_values):
                raise TypeError("Isotropic scattering values must be real.")
            values = np.asarray(raw_values, dtype=np.float64)
            n_q = int(q_magnitudes.size)
        else:
            q_magnitudes = None
            q_vectors = _validate_q_vectors(self.q_vectors)
            projected_q_vectors = np.asarray(
                self.projected_q_vectors,
                dtype=np.float64,
            )
            expected_projected = _project_admissible_q_vectors(q_vectors, basis)
            if projected_q_vectors.shape != expected_projected.shape or not np.allclose(
                projected_q_vectors,
                expected_projected,
                rtol=0.0,
                atol=2.0e-14,
            ):
                raise ValueError(
                    "projected_q_vectors are inconsistent with q_vectors and basis."
                )
            raw_values = np.asarray(self.values)
            if raw_values.dtype.kind != "c":
                raise TypeError("Explicit-vector scattering values must be complex.")
            values = np.asarray(raw_values, dtype=np.complex128)
            n_q = int(q_vectors.shape[0])

        if values.shape != (n_lags, n_q):
            raise ValueError(
                f"values has shape {values.shape}; expected ({n_lags}, {n_q})."
            )
        if not np.all(np.isfinite(values.real)) or not np.all(np.isfinite(values.imag)):
            raise ValueError("Scattering values must contain only finite values.")

        zero_lag = np.flatnonzero(lag_steps == 0)
        if zero_lag.size and not np.allclose(
            values[zero_lag],
            1.0,
            rtol=0.0,
            atol=0.0,
        ):
            raise ValueError("Scattering values must be exactly one at lag zero.")
        if isotropic:
            zero_q = q_magnitudes == 0.0
        else:
            zero_q = np.all(q_vectors == 0.0, axis=1)
        if np.any(zero_q) and not np.allclose(
            values[:, zero_q],
            1.0,
            rtol=0.0,
            atol=0.0,
        ):
            raise ValueError("Scattering values must be exactly one at zero q.")

        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, atom_indices):
            raise ValueError("signature atom_indices are inconsistent with the result.")
        if not np.array_equal(self.signature.projection_basis, basis):
            raise ValueError("signature projection basis is inconsistent with the result.")
        if self.signature.sample_spacing_ps is not None:
            expected_times = lag_steps.astype(np.float64) * float(
                self.signature.sample_spacing_ps
            )
            if not np.allclose(lag_times, expected_times, rtol=0.0, atol=1.0e-14):
                raise ValueError("lag_times are inconsistent with the signature.")

        object.__setattr__(self, "lag_steps", owned_readonly_array(lag_steps, dtype=np.int64))
        object.__setattr__(self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64))
        object.__setattr__(
            self,
            "values",
            owned_readonly_array(
                values,
                dtype=np.float64 if isotropic else np.complex128,
            ),
        )
        object.__setattr__(
            self,
            "q_magnitudes",
            None if q_magnitudes is None else owned_readonly_array(q_magnitudes, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "q_vectors",
            None if q_vectors is None else owned_readonly_array(q_vectors, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "projected_q_vectors",
            None
            if projected_q_vectors is None
            else owned_readonly_array(projected_q_vectors, dtype=np.float64),
        )
        object.__setattr__(self, "n_samples", owned_readonly_array(n_samples, dtype=np.int64))
        object.__setattr__(self, "atom_indices", owned_readonly_array(atom_indices, dtype=np.int64))
        object.__setattr__(self, "projection_basis", owned_readonly_array(basis, dtype=np.float64))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def isotropic(self) -> bool:
        """Whether values use dimension-correct isotropic angular averaging."""

        return self.q_magnitudes is not None


def compute_self_van_hove(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    lag_steps: ArrayLike | None = None,
    max_lag: int | None = None,
    origin_stride: int = 1,
    radial_edges: ArrayLike | None = None,
    r_max: float | None = None,
    n_bins: int = _DEFAULT_N_BINS,
    require_complete_support: bool = False,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
    coordinate_mode: CoordinateMode = "laboratory",
    reference_cell: ReferenceCellInput = "initial",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
) -> SelfVanHoveResult:
    """Compute the radial self van Hove displacement distribution.

    The self space-time correlation follows Van Hove, Phys. Rev. 95, 249-262
    (1954), DOI 10.1103/PhysRev.95.249.  The projected radial reduction,
    explicit overflow accounting, direct unbinned second moment, and blocked
    D0 integration are mdstats-specific contracts.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    stride = require_positive_int(origin_stride, name="origin_stride")
    bins = require_positive_int(n_bins, name="n_bins")
    strict_support = require_bool(
        require_complete_support,
        name="require_complete_support",
    )
    if atom_block_size is not None:
        atom_block_size = require_positive_int(
            atom_block_size,
            name="atom_block_size",
        )
    if origin_block_size is not None:
        origin_block_size = require_positive_int(
            origin_block_size,
            name="origin_block_size",
        )
    if radial_edges is not None and r_max is not None:
        raise ValueError("Specify at most one of radial_edges and r_max.")

    bundle = prepare_displacement_inputs(
        collection,
        species=species,
        atom_indices=atom_indices,
        coordinate_mode=coordinate_mode,
        reference_cell=reference_cell,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
        axes=axes,
        projection_basis=projection_basis,
    )
    lags = _resolve_van_hove_lags(
        bundle,
        lag_steps=lag_steps,
        max_lag=max_lag,
    )
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        origin_stride=stride,
        atom_block_size=atom_block_size,
        origin_block_size=origin_block_size,
        memory_target_bytes=DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
    )

    observed_maximum_prepass: float | None = None
    if radial_edges is not None:
        edges = _validate_radial_edges(radial_edges)
        support_mode = "explicit_edges"
        n_bins_controls_support = False
    elif r_max is not None:
        endpoint = require_finite_real(r_max, name="r_max", positive=True)
        edges = np.linspace(0.0, endpoint, bins + 1, dtype=np.float64)
        support_mode = "user_r_max"
        n_bins_controls_support = True
    else:
        endpoint, observed_maximum_prepass = _automatic_radial_endpoint(
            bundle,
            lags,
            origin_stride=stride,
            plan=plan,
        )
        edges = np.linspace(0.0, endpoint, bins + 1, dtype=np.float64)
        support_mode = "automatic_complete"
        n_bins_controls_support = True
    edges = _validate_radial_edges(edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    measures = _shell_measure(edges, bundle.subspace.rank)

    n_lags = int(lags.size)
    n_resolved_bins = int(edges.size - 1)
    counts = np.zeros((n_lags, n_resolved_bins), dtype=np.int64)
    overflow_counts = np.zeros(n_lags, dtype=np.int64)
    n_samples = np.zeros(n_lags, dtype=np.int64)
    second_moment_sums = np.zeros(n_lags, dtype=np.float64)
    maximum_observed = 0.0
    final_edge = float(edges[-1])

    for block in _iter_blocks_with_plan(
        bundle,
        lags,
        origin_stride=stride,
        plan=plan,
    ):
        radii = _stable_vector_norm(block.displacements)
        block_maximum = float(np.max(radii))
        if block_maximum > maximum_observed:
            maximum_observed = block_maximum
        squared_sum = float(np.sum(radii * radii, dtype=np.float64))
        if not np.isfinite(squared_sum):
            raise ValueError("Projected displacement second moment overflowed.")
        lag_index = block.lag_index
        second_moment_sums[lag_index] += squared_sum
        n_samples[lag_index] += block.n_samples

        captured = radii <= final_edge
        overflow_counts[lag_index] += int(np.count_nonzero(~captured))
        if np.any(captured):
            block_counts, _ = np.histogram(radii[captured], bins=edges)
            counts[lag_index] += np.asarray(block_counts, dtype=np.int64)

    expected_samples = np.asarray(
        [
            bundle.n_atoms
            * ((bundle.n_frames - 1 - int(lag)) // stride + 1)
            for lag in lags
        ],
        dtype=np.int64,
    )
    if not np.array_equal(n_samples, expected_samples):
        raise RuntimeError("D0 block iteration produced an inconsistent sample count.")

    shell_probability = counts / n_samples[:, None]
    overflow_probability = overflow_counts / n_samples
    density = shell_probability / measures[None, :]
    direct_second_moment = second_moment_sums / n_samples

    if strict_support and np.any(overflow_counts > 0):
        total = int(np.sum(overflow_counts, dtype=np.int64))
        affected = np.flatnonzero(overflow_counts > 0).tolist()
        raise ValueError(
            "Finite radial support excluded "
            f"{total} displacement samples at lag indices {affected}; "
            "increase support or disable require_complete_support."
        )

    metadata: dict[str, Any] = {
        "estimator": "self_van_hove_radial_histogram",
        "contract_version": _D1_CONTRACT_VERSION,
        "borrowed_theory": {
            "name": "self part of the van Hove space-time correlation",
            "citation": "L. Van Hove, Physical Review 95, 249-262 (1954)",
            "doi": "10.1103/PhysRev.95.249",
        },
        "radial_support_mode": support_mode,
        "n_bins_controls_support": n_bins_controls_support,
        "n_bins": n_resolved_bins,
        "r_max_angstrom": final_edge,
        "maximum_observed_radius_angstrom": maximum_observed,
        "automatic_prepass_maximum_angstrom": observed_maximum_prepass,
        "bin_endpoint_convention": (
            "left_closed_right_open_final_bin_right_closed"
        ),
        "subspace_rank": bundle.subspace.rank,
        "density_units": f"angstrom^-{bundle.subspace.rank}",
        "shell_measure_units": f"angstrom^{bundle.subspace.rank}",
        "direct_second_moment_units": "angstrom^2",
        "origin_stride": stride,
        "atom_block_size": plan.atom_block_size,
        "origin_block_size": plan.origin_block_size,
        "bytes_per_displacement_sample": plan.bytes_per_sample,
        "estimated_peak_displacement_work_bytes": plan.estimated_peak_work_bytes,
        "displacement_memory_target_bytes": plan.memory_target_bytes,
        "total_overflow_count": int(np.sum(overflow_counts, dtype=np.int64)),
        "require_complete_support": strict_support,
        "support_complete": bool(np.all(overflow_counts == 0)),
        "input": dict(bundle.metadata),
    }
    return SelfVanHoveResult(
        lag_steps=lags,
        lag_times=lags.astype(np.float64) * bundle.sample_spacing_ps,
        radial_edges=edges,
        radial_centers=centers,
        shell_measure=measures,
        shell_probability=shell_probability,
        density=density,
        counts=counts,
        overflow_counts=overflow_counts,
        overflow_probability=overflow_probability,
        n_samples=n_samples,
        direct_second_moment=direct_second_moment,
        atom_indices=bundle.atom_indices,
        projection_basis=bundle.subspace.projection_basis,
        signature=bundle.signature,
        metadata=metadata,
    )


def compute_self_intermediate_scattering(
    collection: AtomisticFrameCollection,
    *,
    q_vectors: ArrayLike | None = None,
    q_magnitudes: ArrayLike | None = None,
    isotropic: bool = True,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
    coordinate_mode: CoordinateMode = "laboratory",
    reference_cell: ReferenceCellInput = "initial",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
) -> SelfIntermediateScatteringResult:
    """Compute the self-intermediate scattering function from D0 samples.

    The self-correlation definition follows Van Hove, Phys. Rev. 95, 249-262
    (1954), DOI 10.1103/PhysRev.95.249, and Vineyard, Phys. Rev. 110,
    999-1010 (1958), DOI 10.1103/PhysRev.110.999. Dimension-correct angular
    kernels, subspace-admissible q vectors, blocking, provenance, and immutable
    result semantics are mdstats-specific contracts.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    isotropic_mode = require_bool(isotropic, name="isotropic")
    origin_step = require_positive_int(origin_stride, name="origin_stride")
    lag_step = require_positive_int(lag_stride, name="lag_stride")
    if atom_block_size is not None:
        atom_block_size = require_positive_int(atom_block_size, name="atom_block_size")
    if origin_block_size is not None:
        origin_block_size = require_positive_int(origin_block_size, name="origin_block_size")

    if isotropic_mode:
        if q_magnitudes is None or q_vectors is not None:
            raise ValueError(
                "isotropic=True requires q_magnitudes and rejects q_vectors."
            )
        q_mags = _validate_q_magnitudes(q_magnitudes)
        q_vecs = None
    else:
        if q_vectors is None or q_magnitudes is not None:
            raise ValueError(
                "isotropic=False requires q_vectors and rejects q_magnitudes."
            )
        q_vecs = _validate_q_vectors(q_vectors)
        q_mags = None

    bundle = prepare_displacement_inputs(
        collection,
        species=species,
        atom_indices=atom_indices,
        coordinate_mode=coordinate_mode,
        reference_cell=reference_cell,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
        axes=axes,
        projection_basis=projection_basis,
    )
    lags = _resolve_regular_lags(
        bundle,
        max_lag=max_lag,
        lag_stride=lag_step,
    )
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        origin_stride=origin_step,
        atom_block_size=atom_block_size,
        origin_block_size=origin_block_size,
        memory_target_bytes=DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
    )

    if isotropic_mode:
        assert q_mags is not None
        projected_q = None
        n_q = int(q_mags.size)
        sums = np.zeros((lags.size, n_q), dtype=np.longdouble)
    else:
        assert q_vecs is not None
        projected_q = _project_admissible_q_vectors(
            q_vecs,
            bundle.subspace.projection_basis,
        )
        n_q = int(q_vecs.shape[0])
        sums = np.zeros((lags.size, n_q), dtype=np.clongdouble)

    max_block_samples = plan.atom_block_size * plan.origin_block_size
    q_chunk_size = _resolve_scattering_q_chunk_size(
        n_q=n_q,
        max_displacement_samples=max_block_samples,
        isotropic=isotropic_mode,
    )
    n_samples = np.zeros(lags.size, dtype=np.int64)

    for block in _iter_blocks_with_plan(
        bundle,
        lags,
        origin_stride=origin_step,
        plan=plan,
    ):
        samples = np.asarray(block.displacements, dtype=np.float64).reshape(
            -1,
            bundle.subspace.rank,
        )
        lag_index = block.lag_index
        if isotropic_mode:
            radii = _stable_vector_norm(samples)
            for q_start in range(0, n_q, q_chunk_size):
                q_stop = min(n_q, q_start + q_chunk_size)
                with np.errstate(over="ignore", invalid="ignore"):
                    arguments = radii[:, None] * q_mags[None, q_start:q_stop]
                kernels = _isotropic_scattering_kernel(
                    arguments,
                    bundle.subspace.rank,
                )
                sums[lag_index, q_start:q_stop] += np.sum(
                    kernels,
                    axis=0,
                    dtype=np.longdouble,
                )
        else:
            assert projected_q is not None
            for q_start in range(0, n_q, q_chunk_size):
                q_stop = min(n_q, q_start + q_chunk_size)
                with np.errstate(over="ignore", invalid="ignore"):
                    phases = samples @ projected_q[q_start:q_stop].T
                if not np.all(np.isfinite(phases)):
                    raise ValueError("q dot displacement phases contain non-finite values.")
                # Direct characteristic-function estimator from Van Hove/Vineyard.
                phasors = np.cos(phases) + 1j * np.sin(phases)
                if not np.all(np.isfinite(phasors.real)) or not np.all(
                    np.isfinite(phasors.imag)
                ):
                    raise ValueError("Explicit-vector phasors contain non-finite values.")
                sums[lag_index, q_start:q_stop] += np.sum(
                    phasors,
                    axis=0,
                    dtype=np.clongdouble,
                )
        n_samples[lag_index] += block.n_samples

    expected_samples = np.asarray(
        [
            bundle.n_atoms
            * ((bundle.n_frames - 1 - int(lag)) // origin_step + 1)
            for lag in lags
        ],
        dtype=np.int64,
    )
    if not np.array_equal(n_samples, expected_samples):
        raise RuntimeError("D0 block iteration produced an inconsistent sample count.")

    normalized = sums / n_samples[:, None].astype(np.longdouble)
    if isotropic_mode:
        values = np.asarray(normalized, dtype=np.float64)
        zero_q = q_mags == 0.0
    else:
        values = np.asarray(normalized, dtype=np.complex128)
        zero_q = np.all(q_vecs == 0.0, axis=1)
    if not np.all(np.isfinite(values.real)) or not np.all(np.isfinite(values.imag)):
        raise ValueError("Self-intermediate scattering values are not finite.")
    zero_lag = np.flatnonzero(lags == 0)
    if zero_lag.size:
        values[zero_lag, :] = 1.0
    if np.any(zero_q):
        values[:, zero_q] = 1.0

    output_bytes = int(values.nbytes + n_samples.nbytes + lags.nbytes)
    metadata: dict[str, Any] = {
        "estimator": (
            "self_intermediate_scattering_isotropic"
            if isotropic_mode
            else "self_intermediate_scattering_explicit_vector"
        ),
        "contract_version": _D3_CONTRACT_VERSION,
        "mode": "isotropic_magnitude" if isotropic_mode else "explicit_vector",
        "borrowed_theory": {
            "name": "self-intermediate scattering function",
            "citations": (
                "L. Van Hove, Physical Review 95, 249-262 (1954)",
                "G. H. Vineyard, Physical Review 110, 999-1010 (1958)",
            ),
            "dois": ("10.1103/PhysRev.95.249", "10.1103/PhysRev.110.999"),
        },
        "special_function_backend": (
            None
            if not isotropic_mode or bundle.subspace.rank == 1
            else "scipy.special"
        ),
        "subspace_rank": bundle.subspace.rank,
        "q_count": n_q,
        "q_units": "angstrom^-1",
        "lag_time_units": "ps",
        "values_units": "dimensionless",
        "q_subspace_tolerance": _Q_SUBSPACE_TOLERANCE,
        "origin_stride": origin_step,
        "lag_stride": lag_step,
        "atom_block_size": plan.atom_block_size,
        "origin_block_size": plan.origin_block_size,
        "bytes_per_displacement_sample": plan.bytes_per_sample,
        "estimated_peak_displacement_work_bytes": plan.estimated_peak_work_bytes,
        "displacement_memory_target_bytes": plan.memory_target_bytes,
        "q_chunk_size": q_chunk_size,
        "q_chunk_transient_target_bytes": _SCATTERING_TRANSIENT_TARGET_BYTES,
        "output_bytes": output_bytes,
        "accumulator_dtype": np.dtype(sums.dtype).name,
        "input": dict(bundle.metadata),
    }
    return SelfIntermediateScatteringResult(
        lag_steps=lags,
        lag_times=lags.astype(np.float64) * bundle.sample_spacing_ps,
        values=values,
        q_magnitudes=q_mags,
        q_vectors=q_vecs,
        projected_q_vectors=projected_q,
        n_samples=n_samples,
        atom_indices=bundle.atom_indices,
        projection_basis=bundle.subspace.projection_basis,
        signature=bundle.signature,
        metadata=metadata,
    )


def compute_non_gaussian_parameter(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
    coordinate_mode: CoordinateMode = "laboratory",
    reference_cell: ReferenceCellInput = "initial",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
) -> NonGaussianResult:
    """Compute the dimension-correct non-Gaussian displacement parameter.

    The displacement-cumulant form follows A. Rahman, K. S. Singwi, and
    A. Sjolander, Phys. Rev. 126, 986-996 (1962),
    DOI 10.1103/PhysRev.126.986.  Physical-subspace resolution, blocked D0
    accumulation, exact zero-moment masking, signatures, and immutable result
    semantics are mdstats-specific contracts.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    origin_step = require_positive_int(origin_stride, name="origin_stride")
    lag_step = require_positive_int(lag_stride, name="lag_stride")
    if atom_block_size is not None:
        atom_block_size = require_positive_int(
            atom_block_size,
            name="atom_block_size",
        )
    if origin_block_size is not None:
        origin_block_size = require_positive_int(
            origin_block_size,
            name="origin_block_size",
        )

    bundle = prepare_displacement_inputs(
        collection,
        species=species,
        atom_indices=atom_indices,
        coordinate_mode=coordinate_mode,
        reference_cell=reference_cell,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
        axes=axes,
        projection_basis=projection_basis,
    )
    lags = _resolve_regular_lags(
        bundle,
        max_lag=max_lag,
        lag_stride=lag_step,
    )
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        origin_stride=origin_step,
        atom_block_size=atom_block_size,
        origin_block_size=origin_block_size,
        memory_target_bytes=DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
    )

    n_lags = int(lags.size)
    second_sums = np.zeros(n_lags, dtype=np.longdouble)
    fourth_sums = np.zeros(n_lags, dtype=np.longdouble)
    n_samples = np.zeros(n_lags, dtype=np.int64)

    for block in _iter_blocks_with_plan(
        bundle,
        lags,
        origin_stride=origin_step,
        plan=plan,
    ):
        radii = _stable_vector_norm(block.displacements)
        with np.errstate(over="ignore", invalid="ignore"):
            squared = radii * radii
            fourth_power = squared * squared
        if not np.all(np.isfinite(squared)):
            raise ValueError("Projected displacement second moment overflowed.")
        if not np.all(np.isfinite(fourth_power)):
            raise ValueError("Projected displacement fourth moment overflowed.")
        lag_index = block.lag_index
        second_sums[lag_index] += np.sum(squared, dtype=np.longdouble)
        fourth_sums[lag_index] += np.sum(fourth_power, dtype=np.longdouble)
        n_samples[lag_index] += block.n_samples

    expected_samples = np.asarray(
        [
            bundle.n_atoms
            * ((bundle.n_frames - 1 - int(lag)) // origin_step + 1)
            for lag in lags
        ],
        dtype=np.int64,
    )
    if not np.array_equal(n_samples, expected_samples):
        raise RuntimeError("D0 block iteration produced an inconsistent sample count.")

    second_long = second_sums / n_samples.astype(np.longdouble)
    fourth_long = fourth_sums / n_samples.astype(np.longdouble)
    second_moment = np.asarray(second_long, dtype=np.float64)
    fourth_moment = np.asarray(fourth_long, dtype=np.float64)
    if not np.all(np.isfinite(second_moment)):
        raise ValueError("Projected displacement second moment is not finite.")
    if not np.all(np.isfinite(fourth_moment)):
        raise ValueError("Projected displacement fourth moment is not finite.")

    undefined = second_moment == 0.0
    if np.any(fourth_moment[undefined] != 0.0):
        raise RuntimeError("Zero second moment was paired with a nonzero fourth moment.")
    alpha2 = np.full(n_lags, np.nan, dtype=np.float64)
    defined = ~undefined
    if np.any(defined):
        rank = bundle.subspace.rank
        second_defined = second_moment[defined].astype(np.longdouble)
        fourth_defined = fourth_moment[defined].astype(np.longdouble)
        ratio = fourth_defined / (second_defined * second_defined)
        # Rahman-Singwi-Sjolander displacement-cumulant prefactor; the rank
        # and projected norm are resolved together by D0.
        alpha_long = np.longdouble(rank / (rank + 2.0)) * ratio - 1.0
        alpha2[defined] = np.asarray(alpha_long, dtype=np.float64)
        if not np.all(np.isfinite(alpha2[defined])):
            raise ValueError("Non-Gaussian parameter is not finite at a defined lag.")

    undefined_indices = np.flatnonzero(undefined).astype(np.int64)
    metadata: dict[str, Any] = {
        "estimator": "projected_non_gaussian_parameter",
        "contract_version": _D2_CONTRACT_VERSION,
        "borrowed_theory": {
            "name": "displacement-cumulant non-Gaussian parameter",
            "citation": (
                "A. Rahman, K. S. Singwi, and A. Sjolander, "
                "Physical Review 126, 986-996 (1962)"
            ),
            "doi": "10.1103/PhysRev.126.986",
        },
        "subspace_rank": bundle.subspace.rank,
        "alpha2_units": "dimensionless",
        "second_moment_units": "angstrom^2",
        "fourth_moment_units": "angstrom^4",
        "zero_moment_policy": "nan_where_second_moment_exactly_zero",
        "undefined_lag_indices": undefined_indices,
        "undefined_lag_count": int(undefined_indices.size),
        "origin_stride": origin_step,
        "lag_stride": lag_step,
        "atom_block_size": plan.atom_block_size,
        "origin_block_size": plan.origin_block_size,
        "bytes_per_displacement_sample": plan.bytes_per_sample,
        "estimated_peak_displacement_work_bytes": plan.estimated_peak_work_bytes,
        "displacement_memory_target_bytes": plan.memory_target_bytes,
        "accumulator_dtype": np.dtype(np.longdouble).name,
        "input": dict(bundle.metadata),
    }
    return NonGaussianResult(
        lag_steps=lags,
        lag_times=lags.astype(np.float64) * bundle.sample_spacing_ps,
        second_moment=second_moment,
        fourth_moment=fourth_moment,
        alpha2=alpha2,
        undefined_mask=undefined,
        n_samples=n_samples,
        atom_indices=bundle.atom_indices,
        projection_basis=bundle.subspace.projection_basis,
        signature=bundle.signature,
        metadata=metadata,
    )


__all__ = [
    "NonGaussianResult",
    "SelfIntermediateScatteringResult",
    "SelfVanHoveResult",
    "compute_non_gaussian_parameter",
    "compute_self_intermediate_scattering",
    "compute_self_van_hove",
]
