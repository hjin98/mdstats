"""Velocity autocorrelation analysis for atomistic trajectories.

The module computes the positive-lag *self* velocity autocorrelation function
(VACF).  It never introduces correlations between distinct atoms.  The
canonical result stores a raw weighted correlation sum; normalization,
transport integration, and spectral transformations are intentionally left as
explicit derived operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.fft import rfft

from ..collection import AtomisticFrameCollection
from ._fft import (
    linear_fft_length,
    make_atom_fft_plan,
    positive_lag_correlation_from_spectrum,
    positive_lag_pair_counts,
)
from .selection import SpeciesSelection
from ._dynamics_common import (
    DynamicsInputSignature,
    freeze_mapping,
    owned_readonly_array,
    require_bool,
    require_nonnegative_int,
    require_positive_int,
    resolve_analysis_subspace,
)
from ._velocity_common import (
    DriftMode,
    WeightInput,
    prepare_velocity_inputs,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
ComplexArray = NDArray[np.complex128]
Backend = Literal["auto", "direct", "fft"]


class VACFWarning(UserWarning):
    """Base warning category for VACF sampling and interpretation issues."""


class FiniteDifferenceVelocityWarning(VACFWarning):
    """Finite-difference velocities can attenuate high-frequency motion."""


class SparseOriginVACFWarning(VACFWarning):
    """Large-lag VACF values have few contributing time origins."""


class CollectiveMotionVACFWarning(VACFWarning):
    """Drift subtraction may remove collective motion of measured atoms."""


@dataclass(frozen=True, slots=True)
class VACFResult:
    """Raw weighted self-VACF and reproducibility metadata.

    The stored tensor follows

    ``tensor_sum[k, alpha, beta]`` stores the origin average of
    ``sum_i w_i * v_i,alpha(t) * v_i,beta(t + lag_k)``.

    It is not symmetrized at positive lag.  ``lag_steps`` denotes saved-frame
    lag, while ``lag_times`` is the authoritative physical time in ps.
    """

    lag_steps: IntArray
    lag_times: FloatArray

    scalar_sum: FloatArray
    components_sum: FloatArray
    tensor_sum: FloatArray | None

    per_atom_scalar: FloatArray | None
    per_atom_components: FloatArray | None
    per_atom_indices: IntArray | None

    n_origins: IntArray

    atom_indices: IntArray
    atom_weights: FloatArray
    weight_sum: float

    weighting: str
    drift_mode: str | None
    backend: str

    metadata: dict[str, Any] = field(default_factory=dict)
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        """Normalize dtypes and validate result identities."""
        lag_steps = np.asarray(self.lag_steps, dtype=np.int64)
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        scalar = np.asarray(self.scalar_sum, dtype=np.float64)
        components = np.asarray(self.components_sum, dtype=np.float64)
        n_origins = np.asarray(self.n_origins, dtype=np.int64)
        atom_indices = np.asarray(self.atom_indices, dtype=np.int64)
        atom_weights = np.asarray(self.atom_weights, dtype=np.float64)
        tensor = (
            None
            if self.tensor_sum is None
            else np.asarray(self.tensor_sum, dtype=np.float64)
        )
        per_atom_scalar = (
            None
            if self.per_atom_scalar is None
            else np.asarray(self.per_atom_scalar, dtype=np.float64)
        )
        per_atom_components = (
            None
            if self.per_atom_components is None
            else np.asarray(self.per_atom_components, dtype=np.float64)
        )
        per_atom_indices = (
            None
            if self.per_atom_indices is None
            else np.asarray(self.per_atom_indices, dtype=np.int64)
        )

        n_lags = int(lag_steps.size)
        n_atoms = int(atom_indices.size)
        if lag_steps.shape != (n_lags,):
            raise ValueError("lag_steps must be one-dimensional.")
        for name, value in (
            ("lag_times", lag_times),
            ("scalar_sum", scalar),
            ("n_origins", n_origins),
        ):
            if value.shape != (n_lags,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_lags},)."
                )
        if components.shape != (n_lags, 3):
            raise ValueError(
                f"components_sum has shape {components.shape}; expected ({n_lags}, 3)."
            )
        if tensor is not None and tensor.shape != (n_lags, 3, 3):
            raise ValueError(
                f"tensor_sum has shape {tensor.shape}; expected ({n_lags}, 3, 3)."
            )
        if atom_weights.shape != (n_atoms,):
            raise ValueError(
                f"atom_weights has shape {atom_weights.shape}; expected ({n_atoms},)."
            )
        if per_atom_indices is None:
            if per_atom_scalar is not None or per_atom_components is not None:
                raise ValueError(
                    "per_atom_indices is required when per-atom correlations exist."
                )
        else:
            n_output = int(per_atom_indices.size)
            if per_atom_scalar is None or per_atom_components is None:
                raise ValueError(
                    "Both per_atom_scalar and per_atom_components are required."
                )
            if per_atom_scalar.shape != (n_lags, n_output):
                raise ValueError(
                    "per_atom_scalar has shape "
                    f"{per_atom_scalar.shape}; expected ({n_lags}, {n_output})."
                )
            if per_atom_components.shape != (n_lags, n_output, 3):
                raise ValueError(
                    "per_atom_components has shape "
                    f"{per_atom_components.shape}; expected ({n_lags}, {n_output}, 3)."
                )
            if not np.allclose(
                per_atom_scalar,
                np.sum(per_atom_components, axis=2),
                rtol=1.0e-12,
                atol=1.0e-13,
            ):
                raise ValueError(
                    "Per-atom scalar VACF must equal the sum of its components."
                )

        finite_arrays = [lag_times, scalar, components, atom_weights]
        if tensor is not None:
            finite_arrays.append(tensor)
        if per_atom_scalar is not None:
            finite_arrays.extend([per_atom_scalar, per_atom_components])
        if any(not np.all(np.isfinite(value)) for value in finite_arrays):
            raise ValueError("VACF result contains non-finite values.")
        if np.any(n_origins < 1):
            raise ValueError("Every VACF lag must contain at least one time origin.")
        if np.any(atom_weights < 0.0) or not np.any(atom_weights > 0.0):
            raise ValueError("atom_weights must be nonnegative and not all zero.")
        if not np.isfinite(self.weight_sum) or self.weight_sum <= 0.0:
            raise ValueError("weight_sum must be finite and strictly positive.")
        if not np.isclose(
            float(np.sum(atom_weights)),
            self.weight_sum,
            rtol=1.0e-13,
            atol=1.0e-14,
        ):
            raise ValueError("weight_sum is inconsistent with atom_weights.")
        if not np.allclose(
            scalar,
            np.sum(components, axis=1),
            rtol=1.0e-12,
            atol=1.0e-13,
        ):
            raise ValueError("scalar_sum must equal the sum of Cartesian components.")
        if tensor is not None and not np.allclose(
            components,
            np.diagonal(tensor, axis1=1, axis2=2),
            rtol=1.0e-12,
            atol=1.0e-13,
        ):
            raise ValueError("components_sum must equal the tensor diagonal.")

        measured = set(int(index) for index in atom_indices)
        if per_atom_indices is not None and not set(
            int(index) for index in per_atom_indices
        ).issubset(measured):
            raise ValueError("per_atom_indices must be a subset of atom_indices.")
        if per_atom_indices is not None and per_atom_indices.size == atom_indices.size:
            if set(per_atom_indices.tolist()) == set(atom_indices.tolist()):
                if not np.allclose(
                    scalar,
                    np.sum(per_atom_scalar, axis=1),
                    rtol=1.0e-12,
                    atol=1.0e-13,
                ):
                    raise ValueError(
                        "Summed per-atom correlations must reproduce scalar_sum."
                    )

        object.__setattr__(self, "lag_steps", owned_readonly_array(lag_steps, dtype=np.int64))
        object.__setattr__(self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64))
        object.__setattr__(self, "scalar_sum", owned_readonly_array(scalar, dtype=np.float64))
        object.__setattr__(self, "components_sum", owned_readonly_array(components, dtype=np.float64))
        object.__setattr__(self, "tensor_sum", None if tensor is None else owned_readonly_array(tensor, dtype=np.float64))
        object.__setattr__(self, "per_atom_scalar", None if per_atom_scalar is None else owned_readonly_array(per_atom_scalar, dtype=np.float64))
        object.__setattr__(self, "per_atom_components", None if per_atom_components is None else owned_readonly_array(per_atom_components, dtype=np.float64))
        object.__setattr__(self, "per_atom_indices", None if per_atom_indices is None else owned_readonly_array(per_atom_indices, dtype=np.int64))
        object.__setattr__(self, "n_origins", owned_readonly_array(n_origins, dtype=np.int64))
        object.__setattr__(self, "atom_indices", owned_readonly_array(atom_indices, dtype=np.int64))
        object.__setattr__(self, "atom_weights", owned_readonly_array(atom_weights, dtype=np.float64))
        object.__setattr__(self, "weight_sum", float(self.weight_sum))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not np.array_equal(self.signature.atom_indices, atom_indices):
                raise ValueError("signature atom_indices are inconsistent with VACFResult.")
            if self.signature.drift_mode != self.drift_mode:
                raise ValueError("signature drift_mode is inconsistent with VACFResult.")
            if not self.signature.subspace.same_physical_subspace(
                resolve_analysis_subspace()
            ):
                raise ValueError("A source VACFResult signature must use the full 3D subspace.")

    @property
    def scalar_mean(self) -> FloatArray:
        """Weighted-mean scalar VACF."""
        return self.scalar_sum / self.weight_sum

    @property
    def components_mean(self) -> FloatArray:
        """Weighted-mean Cartesian VACF components."""
        return self.components_sum / self.weight_sum

    @property
    def tensor_mean(self) -> FloatArray | None:
        """Weighted-mean VACF tensor, when the full tensor was retained."""
        if self.tensor_sum is None:
            return None
        return self.tensor_sum / self.weight_sum

    @staticmethod
    def _normalization_denominator(values: FloatArray, *, label: str) -> FloatArray:
        denominator = np.asarray(values[0], dtype=np.float64)
        scale = max(1.0, float(np.max(np.abs(values))))
        tolerance = 100.0 * np.finfo(np.float64).eps * scale
        if np.any(np.abs(denominator) <= tolerance):
            raise ValueError(
                f"Cannot normalize {label}: a lag-zero amplitude is zero or "
                "numerically indistinguishable from zero."
            )
        return denominator

    def normalized_scalar(self) -> FloatArray:
        """Return the scalar VACF divided by its lag-zero value."""
        denominator = self._normalization_denominator(
            self.scalar_sum, label="scalar VACF"
        )
        return self.scalar_sum / denominator

    def normalized_components(self) -> FloatArray:
        """Normalize each Cartesian component by its own lag-zero value."""
        denominator = self._normalization_denominator(
            self.components_sum, label="component VACF"
        )
        return self.components_sum / denominator

    def project_direction(
        self,
        direction: ArrayLike,
        *,
        mean: bool = False,
        normalized: bool = False,
    ) -> FloatArray:
        """Project the VACF tensor onto one Cartesian direction.

        The supplied vector is normalized internally.  The raw weighted sum is
        returned by default; ``mean=True`` divides it by ``weight_sum``.
        """
        if self.tensor_sum is None:
            raise ValueError(
                "Directional projection requires tensor_sum; recompute with "
                "compute_tensor=True."
            )
        vector = np.asarray(direction, dtype=np.float64)
        if vector.shape != (3,) or not np.all(np.isfinite(vector)):
            raise ValueError("direction must be a finite vector with shape (3,).")
        norm = float(np.linalg.norm(vector))
        if norm <= 0.0:
            raise ValueError("direction must have nonzero length.")
        unit = vector / norm
        projected = np.einsum("i,tij,j->t", unit, self.tensor_sum, unit, optimize=True)
        if mean:
            projected = projected / self.weight_sum
        if normalized:
            denominator = self._normalization_denominator(
                projected, label="direction-projected VACF"
            )
            projected = projected / denominator
        return projected


def _direct_vacf(
    velocities: FloatArray,
    weights: FloatArray,
    lags: IntArray,
    *,
    origin_stride: int,
    compute_tensor: bool,
    output_local_indices: IntArray | None,
) -> tuple[
    FloatArray,
    FloatArray | None,
    FloatArray | None,
    FloatArray | None,
    IntArray,
]:
    n_lags = int(lags.size)
    components = np.empty((n_lags, 3), dtype=np.float64)
    tensor = np.empty((n_lags, 3, 3), dtype=np.float64) if compute_tensor else None
    per_components = (
        None
        if output_local_indices is None
        else np.empty((n_lags, output_local_indices.size, 3), dtype=np.float64)
    )
    n_origins = np.empty(n_lags, dtype=np.int64)

    for out, lag_value in enumerate(lags):
        lag = int(lag_value)
        if origin_stride == 1:
            first = velocities[: velocities.shape[0] - lag]
            second = velocities[lag:]
        else:
            origins = np.arange(0, velocities.shape[0] - lag, origin_stride)
            first = velocities[origins]
            second = velocities[origins + lag]
        count = int(first.shape[0])
        n_origins[out] = count

        products = first * second
        components[out] = (
            np.einsum("oni,n->i", products, weights, optimize=True) / count
        )
        if tensor is not None:
            tensor[out] = (
                np.einsum("ona,onb,n->ab", first, second, weights, optimize=True)
                / count
            )
        if per_components is not None:
            local = output_local_indices
            per_components[out] = (
                np.mean(products[:, local, :], axis=0) * weights[local, None]
            )

    per_scalar = None if per_components is None else np.sum(per_components, axis=2)
    return components, tensor, per_scalar, per_components, n_origins


def _fft_vacf(
    all_velocities: FloatArray,
    selected_indices: IntArray,
    weights: FloatArray,
    lags: IntArray,
    *,
    compute_tensor: bool,
    output_local_indices: IntArray | None,
    atom_block_size: int | None,
    drift_velocity: FloatArray | None,
) -> tuple[
    FloatArray,
    FloatArray | None,
    FloatArray | None,
    FloatArray | None,
    IntArray,
    int,
    int,
]:
    n_frames = int(all_velocities.shape[0])
    n_atoms = int(selected_indices.size)
    max_lag = int(lags[-1])
    plan = make_atom_fft_plan(
        n_atoms,
        n_frames,
        atom_block_size=atom_block_size,
        real_series_per_atom=3,
        complex_series_per_atom=3,
        inverse_real_series_per_atom=3,
    )
    n_fft = plan.n_fft
    n_frequency = plan.n_frequency
    block_size = plan.atom_block_size

    if compute_tensor:
        accumulated: ComplexArray = np.zeros((3, 3, n_frequency), dtype=np.complex128)
    else:
        accumulated = np.zeros((3, n_frequency), dtype=np.complex128)

    per_components = (
        None
        if output_local_indices is None
        else np.empty((lags.size, output_local_indices.size, 3), dtype=np.float64)
    )
    output_map = None
    if output_local_indices is not None:
        output_map = np.full(n_atoms, -1, dtype=np.int64)
        output_map[output_local_indices] = np.arange(
            output_local_indices.size, dtype=np.int64
        )

    counts_all = positive_lag_pair_counts(n_frames, max_lag)

    for start in range(0, n_atoms, block_size):
        stop = min(start + block_size, n_atoms)
        block_weights = np.sqrt(weights[start:stop])
        canonical = selected_indices[start:stop]
        block_cartesian = all_velocities[:, canonical, :]
        if drift_velocity is not None:
            block_cartesian = block_cartesian - drift_velocity[:, None, :]
        block = np.moveaxis(block_cartesian, 0, -1)
        block = block * block_weights[:, None, None]
        transformed = rfft(block, n=n_fft, axis=-1)

        if compute_tensor:
            for alpha in range(3):
                conjugate = np.conjugate(transformed[:, alpha, :])
                for beta in range(3):
                    accumulated[alpha, beta] += np.sum(
                        conjugate * transformed[:, beta, :], axis=0
                    )
        else:
            accumulated += np.sum(np.conjugate(transformed) * transformed, axis=0)

        if per_components is not None:
            assert output_map is not None
            block_output_positions = output_map[start:stop]
            block_mask = block_output_positions >= 0
            if np.any(block_mask):
                local_fft = transformed[block_mask]
                spectra = np.conjugate(local_fft) * local_fft
                correlation = positive_lag_correlation_from_spectrum(
                    spectra, n_fft=n_fft, max_lag=max_lag
                )
                correlation = correlation / counts_all
                correlation = correlation[..., lags]
                output_positions = block_output_positions[block_mask]
                per_components[:, output_positions, :] = np.moveaxis(correlation, -1, 0)

    if compute_tensor:
        full = positive_lag_correlation_from_spectrum(
            accumulated, n_fft=n_fft, max_lag=max_lag
        )
        full = full / counts_all
        tensor = np.moveaxis(full[..., lags], -1, 0)
        components = np.diagonal(tensor, axis1=1, axis2=2).copy()
    else:
        full = positive_lag_correlation_from_spectrum(
            accumulated, n_fft=n_fft, max_lag=max_lag
        )
        full = full / counts_all
        components = np.moveaxis(full[..., lags], -1, 0)
        tensor = None

    per_scalar = None if per_components is None else np.sum(per_components, axis=2)
    n_origins = (n_frames - lags).astype(np.int64)
    return (
        components,
        tensor,
        per_scalar,
        per_components,
        n_origins,
        n_fft,
        block_size,
    )


def _select_backend(
    backend: Backend,
    *,
    n_atoms: int,
    n_frames: int,
    max_lag: int,
    n_lags: int,
    origin_stride: int,
    compute_tensor: bool,
) -> tuple[str, float, float]:
    tensor_factor = 9.0 if compute_tensor else 3.0
    mean_origins = (n_frames - max_lag / 2.0) / origin_stride
    direct_work = n_atoms * n_lags * mean_origins * tensor_factor
    n_fft = linear_fft_length(n_frames)
    fft_work = n_atoms * n_fft * np.log2(max(2, n_fft)) * tensor_factor

    if backend == "direct":
        return "direct", float(direct_work), float(fft_work)
    if backend == "fft":
        if origin_stride != 1:
            raise ValueError("backend='fft' requires origin_stride == 1.")
        return "fft", float(direct_work), float(fft_work)
    if origin_stride != 1:
        return "direct", float(direct_work), float(fft_work)
    # Direct remains preferable for small arrays because it avoids transform
    # setup and is the clearest numerical path.  The work comparison handles
    # large atom counts as well as long trajectories.
    if n_frames < 64 or direct_work <= 2.0 * fft_work:
        return "direct", float(direct_work), float(fft_work)
    return "fft", float(direct_work), float(fft_work)


def compute_vacf(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    weights: WeightInput = "uniform",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    compute_tensor: bool = True,
    per_atom: bool = False,
    per_atom_indices: ArrayLike | None = None,
    backend: Backend = "auto",
    atom_block_size: int | None = None,
) -> VACFResult:
    """Compute the positive-lag weighted self velocity autocorrelation.

    Parameters
    ----------
    collection
        Time-ordered collection with a uniform physical time grid and complete
        Cartesian velocities.
    species, atom_indices
        Mutually exclusive measured-atom selectors.  If omitted, all atoms
        are measured.
    max_lag
        Largest saved-frame lag.  Defaults to half the trajectory length.
    origin_stride
        Spacing between time origins.  Values other than one require the
        direct backend.
    lag_stride
        Spacing between returned frame lags.  Lag zero is always included.
    weights
        ``"uniform"``, ``"mass"``, or one nonnegative explicit weight per
        measured atom.
    drift_mode
        Optional framewise center-of-mass or center-of-geometry velocity
        subtraction.
    drift_species, drift_atom_indices
        Mutually exclusive drift-reference selectors.  If omitted while drift
        correction is enabled, all atoms define the drift velocity.
    compute_tensor
        Retain the full generally nonsymmetric positive-lag tensor.
    per_atom
        Return weighted per-atom component and scalar correlations for every
        measured atom.
    per_atom_indices
        Return per-atom data only for these canonical atom indices.  Supplying
        this option implicitly enables per-atom output.
    backend
        ``"direct"``, ``"fft"``, or automatic work-based selection.
    atom_block_size
        Maximum atoms transformed together by the FFT backend.  If omitted, a
        conservative memory-based block size is selected.

    Returns
    -------
    VACFResult
        Raw weighted correlation sums, derived-selection metadata, and exact
        time-origin counts.

    Notes
    -----
    The routine computes only self terms ``i == i``.  It does not calculate a
    collective current correlation.  The returned data are not windowed,
    smoothed, normalized, integrated, or Fourier transformed.
    """
    if backend not in ("auto", "direct", "fft"):
        raise ValueError("backend must be 'auto', 'direct', or 'fft'.")
    origin_stride = require_positive_int(origin_stride, name="origin_stride")
    lag_stride = require_positive_int(lag_stride, name="lag_stride")
    compute_tensor = require_bool(compute_tensor, name="compute_tensor")
    per_atom = require_bool(per_atom, name="per_atom")
    if atom_block_size is not None:
        atom_block_size = require_positive_int(atom_block_size, name="atom_block_size")

    inputs = prepare_velocity_inputs(
        collection,
        analysis_name="VACF",
        species=species,
        atom_indices=atom_indices,
        weights=weights,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
        per_atom=per_atom,
        per_atom_indices=per_atom_indices,
    )
    if inputs.drift_matches_measured_subset:
        warnings.warn(
            "The drift reference equals the measured subset; subtracting it "
            "removes collective translation of that subset.",
            CollectiveMotionVACFWarning,
            stacklevel=2,
        )

    dt = inputs.sample_spacing_ps
    all_velocities = inputs.velocities
    selected = inputs.atom_indices
    atom_weights = inputs.atom_weights
    weight_sum = inputs.weight_sum
    weighting = inputs.weighting
    weight_units = inputs.weight_units
    correlation_units = inputs.correlation_units
    drift_indices = inputs.drift_atom_indices
    resolved_drift_velocity = inputs.drift_velocity
    output_canonical = inputs.per_atom_indices
    output_local = inputs.per_atom_local_indices

    if max_lag is None:
        resolved_max_lag = collection.n_frames // 2
    else:
        resolved_max_lag = require_nonnegative_int(max_lag, name="max_lag")
    if resolved_max_lag > collection.n_frames - 1:
        raise ValueError(
            f"max_lag={resolved_max_lag} exceeds the largest available frame "
            f"lag {collection.n_frames - 1}."
        )
    lags = np.arange(0, resolved_max_lag + 1, lag_stride, dtype=np.int64)

    chosen_backend, direct_work, fft_work = _select_backend(
        backend,
        n_atoms=int(selected.size),
        n_frames=collection.n_frames,
        max_lag=resolved_max_lag,
        n_lags=int(lags.size),
        origin_stride=origin_stride,
        compute_tensor=compute_tensor,
    )

    n_fft: int | None = None
    resolved_block_size: int | None = None
    if chosen_backend == "direct":
        selected_velocities = np.asarray(
            all_velocities[:, selected, :], dtype=np.float64
        )
        if resolved_drift_velocity is not None:
            selected_velocities = (
                selected_velocities - resolved_drift_velocity[:, None, :]
            )
        components, tensor, per_scalar, per_components, n_origins = _direct_vacf(
            selected_velocities,
            atom_weights,
            lags,
            origin_stride=origin_stride,
            compute_tensor=compute_tensor,
            output_local_indices=output_local,
        )
    else:
        (
            components,
            tensor,
            per_scalar,
            per_components,
            n_origins,
            n_fft,
            resolved_block_size,
        ) = _fft_vacf(
            all_velocities,
            selected,
            atom_weights,
            lags,
            compute_tensor=compute_tensor,
            output_local_indices=output_local,
            atom_block_size=atom_block_size,
            drift_velocity=resolved_drift_velocity,
        )

    scalar = np.sum(components, axis=1)
    lag_times = lags.astype(np.float64) * dt

    if n_origins[0] >= 10 and n_origins[-1] < max(2, n_origins[0] // 10):
        warnings.warn(
            f"The largest reported lag has only {int(n_origins[-1])} time "
            f"origins compared with {int(n_origins[0])} at zero lag; the tail "
            "may be noisy.",
            SparseOriginVACFWarning,
            stacklevel=2,
        )

    velocity_source = collection.provenance.velocity_source
    if velocity_source == "finite_difference":
        warnings.warn(
            "Velocities were reconstructed by finite difference; high-frequency "
            "VACF and later velocity-spectrum amplitudes may be attenuated.",
            FiniteDifferenceVelocityWarning,
            stacklevel=2,
        )

    metadata: dict[str, Any] = {
        "selected_atom_indices": selected.tolist(),
        "per_atom_indices": (
            None if output_canonical is None else output_canonical.tolist()
        ),
        "weighting": weighting,
        "weight_units": weight_units,
        "velocity_units": "Å/ps",
        "correlation_units": correlation_units,
        "velocity_source": velocity_source,
        "drift_mode": drift_mode,
        "drift_atom_indices": (
            None if drift_indices is None else drift_indices.tolist()
        ),
        "requested_backend": backend,
        "chosen_backend": chosen_backend,
        "atom_block_size": resolved_block_size,
        "fft_length": n_fft,
        "estimated_direct_work": direct_work,
        "estimated_fft_work": fft_work,
        "origin_stride": origin_stride,
        "lag_stride": lag_stride,
        "maximum_lag": resolved_max_lag,
        "time_step_ps": dt,
        "lag_steps_semantics": "saved_frame_lag",
        "frame_count": collection.n_frames,
        "frame_id_first": int(collection.frame_ids[0]),
        "frame_id_last": int(collection.frame_ids[-1]),
        "source_format": collection.provenance.source_format,
        "source_files": list(collection.provenance.source_files),
        "time_start_ps": float(collection.times[0]),
        "time_end_ps": float(collection.times[-1]),
        "frame_ids_contiguous": bool(
            np.array_equal(
                collection.frame_ids,
                np.arange(
                    collection.frame_ids[0],
                    collection.frame_ids[0] + collection.n_frames,
                    dtype=np.int64,
                ),
            )
        ),
    }

    return VACFResult(
        lag_steps=lags,
        lag_times=lag_times,
        scalar_sum=scalar,
        components_sum=components,
        tensor_sum=tensor,
        per_atom_scalar=per_scalar,
        per_atom_components=per_components,
        per_atom_indices=output_canonical,
        n_origins=n_origins,
        atom_indices=selected,
        atom_weights=atom_weights,
        weight_sum=weight_sum,
        weighting=weighting,
        drift_mode=drift_mode,
        backend=chosen_backend,
        metadata=metadata,
        signature=inputs.signature,
    )
