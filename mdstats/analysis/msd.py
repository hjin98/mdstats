"""Mean-square displacement analysis for atomistic trajectories.

The module supports two physically distinct estimators:

* a stationary, multiple-time-origin MSD with direct and blocked-FFT
  backends; and
* a fixed-origin cumulative displacement diagnostic for nonstationary
  processes such as melting.

The direct estimator remains the numerical reference.  The FFT estimator uses
position autocorrelations plus cumulative squared-coordinate sums and never
changes the mathematical definition of the result.
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
from ._displacement_common import (
    DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
    CollectiveMotionWarning,
    CoordinateMode,
    DisplacementBlockPlan,
    DisplacementInputBundle,
    DriftMode,
    FixedOriginMSDWarning,
    MSDWarning,
    NumericalMSDWarning,
    ReferenceCellInput,
    SparseOriginWarning,
    VariableCellMSDWarning,
    iter_displacement_blocks,
    prepare_displacement_inputs,
    resolve_displacement_block_plan,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
ComplexArray = NDArray[np.complex128]
MSDMode = Literal["time_averaged", "fixed_origin"]
Backend = Literal["auto", "direct", "fft"]


@dataclass(frozen=True, slots=True)
class MSDResult:
    """Mean-square displacement result and reproducibility metadata.

    ``lag_steps`` contains saved-frame lags, not source integration-step
    labels.  ``lag_times`` is the authoritative physical separation in ps.
    """

    lag_steps: IntArray
    lag_times: FloatArray

    msd: FloatArray
    components: FloatArray
    tensor: FloatArray | None

    per_atom_msd: FloatArray | None
    n_origins: IntArray

    atom_indices: IntArray
    n_atoms: int

    mode: str
    coordinate_mode: str
    drift_mode: str | None
    reference_cell: FloatArray | None

    metadata: dict[str, Any] = field(default_factory=dict)
    signature: DynamicsInputSignature | None = None

    def __post_init__(self) -> None:
        """Normalize result dtypes and verify internal shape identities."""
        lag_steps = np.asarray(self.lag_steps, dtype=np.int64)
        lag_times = np.asarray(self.lag_times, dtype=np.float64)
        msd = np.asarray(self.msd, dtype=np.float64)
        components = np.asarray(self.components, dtype=np.float64)
        n_origins = np.asarray(self.n_origins, dtype=np.int64)
        atom_indices = np.asarray(self.atom_indices, dtype=np.int64)
        tensor = (
            None if self.tensor is None else np.asarray(self.tensor, dtype=np.float64)
        )
        per_atom = (
            None
            if self.per_atom_msd is None
            else np.asarray(self.per_atom_msd, dtype=np.float64)
        )
        reference_cell = (
            None
            if self.reference_cell is None
            else np.asarray(self.reference_cell, dtype=np.float64)
        )

        n_lags = int(lag_steps.size)
        if lag_steps.shape != (n_lags,):
            raise ValueError("lag_steps must be one-dimensional.")
        for name, value in (
            ("lag_times", lag_times),
            ("msd", msd),
            ("n_origins", n_origins),
        ):
            if value.shape != (n_lags,):
                raise ValueError(
                    f"{name} has shape {value.shape}; expected ({n_lags},)."
                )
        if components.shape != (n_lags, 3):
            raise ValueError(
                f"components has shape {components.shape}; expected ({n_lags}, 3)."
            )
        if tensor is not None and tensor.shape != (n_lags, 3, 3):
            raise ValueError(
                f"tensor has shape {tensor.shape}; expected ({n_lags}, 3, 3)."
            )
        if atom_indices.shape != (self.n_atoms,):
            raise ValueError(
                f"atom_indices has shape {atom_indices.shape}; "
                f"expected ({self.n_atoms},)."
            )
        if per_atom is not None and per_atom.shape != (n_lags, self.n_atoms):
            raise ValueError(
                f"per_atom_msd has shape {per_atom.shape}; "
                f"expected ({n_lags}, {self.n_atoms})."
            )
        if reference_cell is not None and reference_cell.shape != (3, 3):
            raise ValueError("reference_cell must have shape (3, 3).")
        finite_arrays = [lag_times, msd, components]
        if tensor is not None:
            finite_arrays.append(tensor)
        if per_atom is not None:
            finite_arrays.append(per_atom)
        if any(not np.all(np.isfinite(value)) for value in finite_arrays):
            raise ValueError("MSD result contains non-finite values.")
        if np.any(n_origins < 1):
            raise ValueError("Every MSD lag must contain at least one time origin.")
        if not np.allclose(msd, np.sum(components, axis=1), rtol=1e-12, atol=1e-14):
            raise ValueError("Scalar MSD must equal the sum of Cartesian components.")
        if tensor is not None:
            if not np.allclose(
                tensor,
                np.swapaxes(tensor, 1, 2),
                rtol=1e-12,
                atol=1e-14,
            ):
                raise ValueError("MSD second-moment tensors must be symmetric.")
            if not np.allclose(
                components,
                np.diagonal(tensor, axis1=1, axis2=2),
                rtol=1e-12,
                atol=1e-14,
            ):
                raise ValueError("MSD components must equal the tensor diagonal.")

        object.__setattr__(self, "lag_steps", owned_readonly_array(lag_steps, dtype=np.int64))
        object.__setattr__(self, "lag_times", owned_readonly_array(lag_times, dtype=np.float64))
        object.__setattr__(self, "msd", owned_readonly_array(msd, dtype=np.float64))
        object.__setattr__(self, "components", owned_readonly_array(components, dtype=np.float64))
        object.__setattr__(self, "tensor", None if tensor is None else owned_readonly_array(tensor, dtype=np.float64))
        object.__setattr__(self, "per_atom_msd", None if per_atom is None else owned_readonly_array(per_atom, dtype=np.float64))
        object.__setattr__(self, "n_origins", owned_readonly_array(n_origins, dtype=np.int64))
        object.__setattr__(self, "atom_indices", owned_readonly_array(atom_indices, dtype=np.int64))
        object.__setattr__(self, "reference_cell", None if reference_cell is None else owned_readonly_array(reference_cell, dtype=np.float64))
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))
        if self.signature is not None:
            if not isinstance(self.signature, DynamicsInputSignature):
                raise TypeError("signature must be a DynamicsInputSignature or None.")
            if not np.array_equal(self.signature.atom_indices, atom_indices):
                raise ValueError("signature atom_indices are inconsistent with MSDResult.")
            if self.signature.coordinate_mode != self.coordinate_mode:
                raise ValueError("signature coordinate_mode is inconsistent with MSDResult.")
            if self.signature.drift_mode != self.drift_mode:
                raise ValueError("signature drift_mode is inconsistent with MSDResult.")
            signature_cell = self.signature.reference_cell
            if signature_cell is None or reference_cell is None:
                if signature_cell is not reference_cell:
                    raise ValueError("signature reference_cell is inconsistent with MSDResult.")
            elif not np.array_equal(signature_cell, reference_cell):
                raise ValueError("signature reference_cell is inconsistent with MSDResult.")
            if not self.signature.subspace.same_physical_subspace(
                resolve_analysis_subspace()
            ):
                raise ValueError("A source MSDResult signature must use the full 3D subspace.")


def _direct_time_averaged_msd(
    bundle: DisplacementInputBundle,
    lags: IntArray,
    *,
    origin_stride: int,
    compute_tensor: bool,
    per_atom: bool,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
    memory_target_bytes: int | None = DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES,
) -> tuple[
    FloatArray,
    FloatArray,
    FloatArray | None,
    FloatArray | None,
    IntArray,
    DisplacementBlockPlan,
]:
    """Reference estimator accumulated from deterministic D0 blocks."""

    if bundle.subspace.labels != ("x", "y", "z"):
        raise ValueError(
            "The MSDResult source estimator requires the canonical full Cartesian "
            "subspace."
        )
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        origin_stride=origin_stride,
        atom_block_size=atom_block_size,
        origin_block_size=origin_block_size,
        memory_target_bytes=memory_target_bytes,
    )
    n_lags = int(lags.size)
    n_atoms = bundle.n_atoms
    component_sums = np.zeros((n_lags, 3), dtype=np.float64)
    tensor_sums = (
        np.zeros((n_lags, 3, 3), dtype=np.float64) if compute_tensor else None
    )
    per_atom_sums = (
        np.zeros((n_lags, n_atoms), dtype=np.float64) if per_atom else None
    )
    local_index = {int(atom): index for index, atom in enumerate(bundle.atom_indices)}

    for block in iter_displacement_blocks(
        bundle,
        lags,
        origin_stride=origin_stride,
        atom_block_size=plan.atom_block_size,
        origin_block_size=plan.origin_block_size,
        memory_target_bytes=plan.memory_target_bytes,
    ):
        delta = block.displacements
        squared = delta * delta
        component_sums[block.lag_index] += np.sum(squared, axis=(0, 1))
        if tensor_sums is not None:
            tensor_sums[block.lag_index] += np.einsum(
                "oai,oaj->ij",
                delta,
                delta,
                optimize=True,
            )
        if per_atom_sums is not None:
            block_local = np.fromiter(
                (local_index[int(atom)] for atom in block.atom_indices),
                dtype=np.int64,
                count=block.atom_indices.size,
            )
            per_atom_sums[block.lag_index, block_local] += np.sum(
                np.sum(squared, axis=2),
                axis=0,
            )

    n_origins = np.asarray(
        [
            (bundle.n_frames - 1 - int(lag)) // origin_stride + 1
            for lag in lags
        ],
        dtype=np.int64,
    )
    denominators = n_origins.astype(np.float64) * float(n_atoms)
    components = component_sums / denominators[:, None]
    tensor = (
        None
        if tensor_sums is None
        else tensor_sums / denominators[:, None, None]
    )
    per_atom_msd = (
        None
        if per_atom_sums is None
        else per_atom_sums / n_origins.astype(np.float64)[:, None]
    )
    msd = np.sum(components, axis=1)
    return msd, components, tensor, per_atom_msd, n_origins, plan


def _prefix_sums(values: FloatArray) -> FloatArray:
    """Return cumulative sums with a leading zero along the final axis."""
    prefix = np.zeros(values.shape[:-1] + (values.shape[-1] + 1,), dtype=np.float64)
    np.cumsum(values, axis=-1, out=prefix[..., 1:])
    return prefix


def _clamp_roundoff_negative(
    values: FloatArray,
    *,
    label: str,
    warn: bool = True,
) -> FloatArray:
    """Clamp only scale-consistent negative roundoff in nonnegative moments."""
    array = np.asarray(values, dtype=np.float64)
    scale = max(1.0, float(np.max(np.abs(array))))
    tolerance = 2048.0 * np.finfo(np.float64).eps * scale
    tiny = (array < 0.0) & (array >= -tolerance)
    if np.any(tiny):
        array[tiny] = 0.0
    materially_negative = array < -tolerance
    if warn and np.any(materially_negative):
        minimum = float(np.min(array))
        warnings.warn(
            f"{label} contains a materially negative value ({minimum:.6g}); "
            "this can indicate severe FFT cancellation or malformed coordinates.",
            NumericalMSDWarning,
            stacklevel=3,
        )
    return array


def _fft_time_averaged_msd(
    positions: FloatArray,
    lags: IntArray,
    *,
    compute_tensor: bool,
    per_atom: bool,
    atom_block_size: int | None,
) -> tuple[
    FloatArray,
    FloatArray,
    FloatArray | None,
    FloatArray | None,
    IntArray,
    int,
    int,
]:
    """Compute the all-origin MSD from position auto/cross-correlations.

    A constant per-atom origin is removed before the FFT.  This leaves every
    displacement unchanged while reducing cancellation from large unwrapped
    coordinate offsets.
    """
    n_frames, n_atoms, _ = positions.shape
    max_lag = int(lags[-1])
    plan = make_atom_fft_plan(
        n_atoms,
        n_frames,
        atom_block_size=atom_block_size,
        real_series_per_atom=3,
        complex_series_per_atom=3,
        inverse_real_series_per_atom=3,
    )
    counts_all = positive_lag_pair_counts(n_frames, max_lag)
    counts = counts_all[lags]

    if compute_tensor:
        accumulated_spectra: ComplexArray = np.zeros(
            (3, 3, plan.n_frequency), dtype=np.complex128
        )
        coordinate_products = np.zeros((3, 3, n_frames), dtype=np.float64)
    else:
        accumulated_spectra = np.zeros((3, plan.n_frequency), dtype=np.complex128)
        coordinate_products = np.zeros((3, n_frames), dtype=np.float64)

    per_atom_msd = (
        np.empty((lags.size, n_atoms), dtype=np.float64) if per_atom else None
    )

    for start in range(0, n_atoms, plan.atom_block_size):
        stop = min(start + plan.atom_block_size, n_atoms)
        # (block atom, Cartesian component, time)
        block = np.moveaxis(positions[:, start:stop, :], 0, -1)
        block = np.asarray(block - block[..., :1], dtype=np.float64)
        transformed = rfft(block, n=plan.n_fft, axis=-1)

        if compute_tensor:
            coordinate_products += np.einsum(
                "iat,ibt->abt", block, block, optimize=True
            )
            for alpha in range(3):
                conjugate = np.conjugate(transformed[:, alpha, :])
                for beta in range(3):
                    accumulated_spectra[alpha, beta] += np.sum(
                        conjugate * transformed[:, beta, :], axis=0
                    )
        else:
            coordinate_products += np.sum(block * block, axis=0)
            accumulated_spectra += np.sum(
                np.conjugate(transformed) * transformed, axis=0
            )

        if per_atom_msd is not None:
            auto_spectra = np.conjugate(transformed) * transformed
            autocorrelation = positive_lag_correlation_from_spectrum(
                auto_spectra,
                n_fft=plan.n_fft,
                max_lag=max_lag,
            )[..., lags]
            square_prefix = _prefix_sums(block * block)
            early = square_prefix[..., n_frames - lags]
            late = square_prefix[..., -1, None] - square_prefix[..., lags]
            per_components = (early + late - 2.0 * autocorrelation) / counts
            block_scalar = np.sum(per_components, axis=1).T
            per_atom_msd[:, start:stop] = _clamp_roundoff_negative(
                block_scalar,
                label="Per-atom FFT MSD",
            )

    correlation = positive_lag_correlation_from_spectrum(
        accumulated_spectra,
        n_fft=plan.n_fft,
        max_lag=max_lag,
    )[..., lags]
    product_prefix = _prefix_sums(coordinate_products)
    early = product_prefix[..., n_frames - lags]
    late = product_prefix[..., -1, None] - product_prefix[..., lags]
    denominator = counts * n_atoms

    tensor: FloatArray | None
    if compute_tensor:
        tensor = np.empty((lags.size, 3, 3), dtype=np.float64)
        for alpha in range(3):
            for beta in range(alpha, 3):
                value = (
                    early[alpha, beta]
                    + late[alpha, beta]
                    - correlation[alpha, beta]
                    - correlation[beta, alpha]
                ) / denominator
                # The estimator itself is symmetric.  Assigning one computed
                # value to both entries preserves that formula exactly rather
                # than repairing an incomplete tensor afterward.
                tensor[:, alpha, beta] = value
                tensor[:, beta, alpha] = value
        components = np.diagonal(tensor, axis1=1, axis2=2).copy()
        components = _clamp_roundoff_negative(
            components,
            label="FFT MSD Cartesian components",
        )
        for axis in range(3):
            tensor[:, axis, axis] = components[:, axis]
    else:
        component_by_axis = (early + late - 2.0 * correlation) / denominator
        components = _clamp_roundoff_negative(
            component_by_axis.T,
            label="FFT MSD Cartesian components",
        )
        tensor = None

    msd = _clamp_roundoff_negative(
        np.sum(components, axis=1),
        label="FFT scalar MSD",
    )
    n_origins = (n_frames - lags).astype(np.int64)
    return (
        msd,
        components,
        tensor,
        per_atom_msd,
        n_origins,
        plan.n_fft,
        plan.atom_block_size,
    )


def _compute_fixed_origin(
    positions: FloatArray,
    *,
    origin_frame: int,
    lags: IntArray,
    compute_tensor: bool,
    per_atom: bool,
) -> tuple[FloatArray, FloatArray, FloatArray | None, FloatArray | None, IntArray]:
    frames = origin_frame + lags
    delta = positions[frames] - positions[origin_frame]
    squared = delta * delta
    components = np.mean(squared, axis=1)
    msd = np.sum(components, axis=1)

    tensor = None
    if compute_tensor:
        tensor = (
            np.einsum(
                "tai,taj->tij",
                delta,
                delta,
                optimize=True,
            )
            / delta.shape[1]
        )

    per_atom_msd = np.sum(squared, axis=2) if per_atom else None
    n_origins = np.ones(lags.size, dtype=np.int64)
    return msd, components, tensor, per_atom_msd, n_origins


def _select_backend(
    backend: Backend,
    *,
    mode: MSDMode,
    n_atoms: int,
    n_frames: int,
    max_lag: int,
    n_lags: int,
    origin_stride: int,
    compute_tensor: bool,
) -> tuple[str, float, float]:
    """Resolve the numerical backend from semantics and estimated work."""
    if backend not in ("auto", "direct", "fft"):
        raise ValueError("backend must be 'auto', 'direct', or 'fft'.")

    tensor_factor = 9.0 if compute_tensor else 3.0
    mean_origins = (n_frames - max_lag / 2.0) / max(1, origin_stride)
    direct_work = n_atoms * n_lags * mean_origins * tensor_factor
    n_fft = linear_fft_length(n_frames)
    # MSD requires both correlations and squared-coordinate endpoint sums.
    fft_work = n_atoms * n_fft * np.log2(max(2, n_fft)) * tensor_factor * 1.25

    if mode == "fixed_origin":
        if backend == "fft":
            raise ValueError("backend='fft' is not applicable to fixed-origin MSD.")
        return "direct", float(direct_work), float(fft_work)
    if backend == "direct":
        return "direct", float(direct_work), float(fft_work)
    if backend == "fft":
        if origin_stride != 1:
            raise ValueError("backend='fft' requires origin_stride == 1.")
        return "fft", float(direct_work), float(fft_work)
    if origin_stride != 1:
        return "direct", float(direct_work), float(fft_work)
    if n_frames < 64 or direct_work <= 2.0 * fft_work:
        return "direct", float(direct_work), float(fft_work)
    return "fft", float(direct_work), float(fft_work)


def compute_msd(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    mode: MSDMode = "time_averaged",
    origin_frame: int = 0,
    max_lag: int | None = None,
    origin_stride: int = 1,
    lag_stride: int = 1,
    coordinate_mode: CoordinateMode = "laboratory",
    reference_cell: ReferenceCellInput = "mean",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    compute_tensor: bool = True,
    per_atom: bool = False,
    backend: Backend = "auto",
    atom_block_size: int | None = None,
) -> MSDResult:
    """Compute fixed-origin or time-origin-averaged mean-square displacement.

    Parameters
    ----------
    collection
        Time-ordered frame collection with persistent atom order and
        continuous fractional coordinates.
    species, atom_indices
        Mutually exclusive measured-atom selectors.  If omitted, all atoms
        are selected.
    mode
        ``"time_averaged"`` for a stationary many-origin estimator or
        ``"fixed_origin"`` for cumulative displacement from ``origin_frame``.
    origin_frame
        Reference frame in fixed-origin mode.  Ignored in time-averaged mode.
    max_lag
        Maximum saved-frame lag.  Defaults to half the trajectory for time
        averaging and the final available frame for fixed-origin mode.
    origin_stride
        Frame spacing between time origins.  Values other than one require the
        direct time-averaged backend.
    lag_stride
        Frame spacing between reported lag values.
    coordinate_mode
        ``"laboratory"`` uses each instantaneous cell.  ``"reference_cell"``
        maps all continuous fractional coordinates into one fixed cell.
    reference_cell
        ``"initial"``, ``"mean"``, or an explicit 3x3 row-vector cell matrix.
        Used only in reference-cell mode.
    drift_mode
        Optional center-of-mass or center-of-geometry translation removal.
    drift_species, drift_atom_indices
        Mutually exclusive drift-reference selectors.  If omitted while drift
        removal is enabled, all atoms define the drift trajectory.
    compute_tensor
        Return the complete displacement second-moment tensor.
    per_atom
        Return one scalar MSD curve per measured atom.
    backend
        ``"direct"``, ``"fft"``, or work-based automatic selection.  The FFT
        backend applies only to all-origin time-averaged MSD.
    atom_block_size
        Maximum atoms transformed together by the FFT backend.  If omitted, a
        conservative memory-based value is selected.

    Returns
    -------
    MSDResult
        Scalar, Cartesian, tensor, and optional per-atom displacement moments.

    Notes
    -----
    The routine requires a uniform physical time grid.  ``lag_steps`` denotes
    saved-frame lag; use ``lag_times`` for physical time.  The FFT backend
    computes the same estimator as the direct implementation and retains the
    latter as its numerical reference.
    """
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    collection.require_trajectory("MSD")
    if mode not in ("time_averaged", "fixed_origin"):
        raise ValueError("mode must be 'time_averaged' or 'fixed_origin'.")
    origin_stride = require_positive_int(origin_stride, name="origin_stride")
    lag_stride = require_positive_int(lag_stride, name="lag_stride")
    compute_tensor = require_bool(compute_tensor, name="compute_tensor")
    per_atom = require_bool(per_atom, name="per_atom")
    if atom_block_size is not None:
        atom_block_size = require_positive_int(atom_block_size, name="atom_block_size")
    if max_lag is not None:
        max_lag = require_nonnegative_int(max_lag, name="max_lag")

    bundle = prepare_displacement_inputs(
        collection,
        species=species,
        atom_indices=atom_indices,
        coordinate_mode=coordinate_mode,
        reference_cell=reference_cell,
        drift_mode=drift_mode,
        drift_species=drift_species,
        drift_atom_indices=drift_atom_indices,
    )
    dt = bundle.sample_spacing_ps
    selected = bundle.atom_indices
    positions = bundle.positions
    resolved_reference_cell = bundle.reference_cell
    reference_definition = bundle.reference_cell_mode
    drift_indices = bundle.drift_atom_indices

    n_fft: int | None = None
    resolved_block_size: int | None = None
    displacement_plan: DisplacementBlockPlan | None = None
    if mode == "time_averaged":
        maximum_available = collection.n_frames - 1
        resolved_max_lag = collection.n_frames // 2 if max_lag is None else max_lag
        if resolved_max_lag > maximum_available:
            raise ValueError(
                f"max_lag={resolved_max_lag} exceeds the largest available frame "
                f"lag {maximum_available}."
            )
        lags = np.arange(0, resolved_max_lag + 1, lag_stride, dtype=np.int64)
        chosen_backend, direct_work, fft_work = _select_backend(
            backend,
            mode=mode,
            n_atoms=int(selected.size),
            n_frames=collection.n_frames,
            max_lag=resolved_max_lag,
            n_lags=int(lags.size),
            origin_stride=origin_stride,
            compute_tensor=compute_tensor,
        )
        if chosen_backend == "direct":
            (
                msd,
                components,
                tensor,
                per_atom_msd,
                n_origins,
                displacement_plan,
            ) = _direct_time_averaged_msd(
                bundle,
                lags,
                origin_stride=origin_stride,
                compute_tensor=compute_tensor,
                per_atom=per_atom,
            )
        else:
            (
                msd,
                components,
                tensor,
                per_atom_msd,
                n_origins,
                n_fft,
                resolved_block_size,
            ) = _fft_time_averaged_msd(
                positions,
                lags,
                compute_tensor=compute_tensor,
                per_atom=per_atom,
                atom_block_size=atom_block_size,
            )
        lag_times = lags.astype(np.float64) * dt
        origin_metadata: dict[str, Any] = {
            "origin_frame": None,
            "origin_step": None,
            "origin_time_ps": None,
        }
        if n_origins[0] >= 10 and n_origins[-1] < max(2, n_origins[0] // 10):
            warnings.warn(
                f"The largest reported lag has only {int(n_origins[-1])} time "
                "origins compared with "
                f"{int(n_origins[0])} at zero lag; long-lag statistics may be noisy.",
                SparseOriginWarning,
                stacklevel=2,
            )
    else:
        origin_frame = require_nonnegative_int(origin_frame, name="origin_frame")
        if origin_frame < 0 or origin_frame >= collection.n_frames:
            raise IndexError(
                f"origin_frame={origin_frame} is outside 0..{collection.n_frames - 1}."
            )
        maximum_available = collection.n_frames - 1 - origin_frame
        resolved_max_lag = maximum_available if max_lag is None else max_lag
        if resolved_max_lag > maximum_available:
            raise ValueError(
                f"max_lag={resolved_max_lag} exceeds the {maximum_available} "
                "frames available after origin_frame."
            )
        lags = np.arange(0, resolved_max_lag + 1, lag_stride, dtype=np.int64)
        chosen_backend, direct_work, fft_work = _select_backend(
            backend,
            mode=mode,
            n_atoms=int(selected.size),
            n_frames=collection.n_frames,
            max_lag=resolved_max_lag,
            n_lags=int(lags.size),
            origin_stride=origin_stride,
            compute_tensor=compute_tensor,
        )
        msd, components, tensor, per_atom_msd, n_origins = _compute_fixed_origin(
            positions,
            origin_frame=origin_frame,
            lags=lags,
            compute_tensor=compute_tensor,
            per_atom=per_atom,
        )
        frames = origin_frame + lags
        times = collection.require_time_axis("MSD")
        lag_times = times[frames] - times[origin_frame]
        origin_metadata = {
            "origin_frame": origin_frame,
            "origin_step": (
                None
                if collection.steps is None
                else int(collection.steps[origin_frame])
            ),
            "origin_time_ps": float(times[origin_frame]),
        }
        warnings.warn(
            "Fixed-origin MSD is a nonstationary trajectory diagnostic; use a "
            "time-origin-averaged MSD on a stationary segment for equilibrium "
            "diffusion fitting.",
            FixedOriginMSDWarning,
            stacklevel=2,
        )

    # Enforce exact zero at zero lag and eliminate signed roundoff zeros.
    zero_index = np.flatnonzero(lags == 0)
    if zero_index.size:
        idx = int(zero_index[0])
        msd[idx] = 0.0
        components[idx] = 0.0
        if tensor is not None:
            tensor[idx] = 0.0
        if per_atom_msd is not None:
            per_atom_msd[idx] = 0.0

    metadata: dict[str, Any] = {
        "mode": mode,
        **origin_metadata,
        "selected_atom_indices": selected.tolist(),
        "coordinate_mode": coordinate_mode,
        "reference_cell_definition": reference_definition,
        "requested_backend": backend,
        "chosen_backend": chosen_backend,
        "atom_block_size": resolved_block_size,
        "displacement_common_stage": "D0",
        "displacement_atom_block_size": (
            None if displacement_plan is None else displacement_plan.atom_block_size
        ),
        "displacement_origin_block_size": (
            None if displacement_plan is None else displacement_plan.origin_block_size
        ),
        "displacement_memory_target_bytes": (
            None if displacement_plan is None else displacement_plan.memory_target_bytes
        ),
        "displacement_estimated_peak_work_bytes": (
            None
            if displacement_plan is None
            else displacement_plan.estimated_peak_work_bytes
        ),
        "fft_length": n_fft,
        "fft_coordinate_centering": (
            "subtract_first_position_per_atom" if chosen_backend == "fft" else None
        ),
        "estimated_direct_work": direct_work,
        "estimated_fft_work": fft_work,
        "origin_stride": origin_stride,
        "lag_stride": lag_stride,
        "maximum_lag": resolved_max_lag,
        "time_step_ps": dt,
        "lag_steps_semantics": "saved_frame_lag",
        "drift_mode": drift_mode,
        "drift_atom_indices": None if drift_indices is None else drift_indices.tolist(),
        "frame_count": collection.n_frames,
        "source_format": (
            None if collection.provenance is None else collection.provenance.source_format
        ),
        "source_files": (
            [] if collection.provenance is None else list(collection.provenance.source_files)
        ),
    }

    signature = bundle.signature

    return MSDResult(
        lag_steps=lags,
        lag_times=lag_times,
        msd=msd,
        components=components,
        tensor=tensor,
        per_atom_msd=per_atom_msd,
        n_origins=n_origins,
        atom_indices=selected,
        n_atoms=int(selected.size),
        mode=mode,
        coordinate_mode=coordinate_mode,
        drift_mode=drift_mode,
        reference_cell=resolved_reference_cell,
        metadata=metadata,
        signature=signature,
    )
