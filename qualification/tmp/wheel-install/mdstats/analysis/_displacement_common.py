"""Shared displacement preparation and blocked iteration.

D0 centralizes the physical input choices used by displacement observables:
atom selection, coordinate convention, reference cell, drift subtraction, and
analysis subspace.  It then exposes deterministic lag/origin/atom blocks
without defining a new statistical estimator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Mapping, Sequence
import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ..coordinates.consumer_adapters import prepare_displacement_coordinate_view
from ._dynamics_common import (
    AnalysisSubspace,
    DynamicsInputSignature,
    build_dynamics_signature,
    freeze_mapping,
    owned_readonly_array,
    require_nonnegative_int,
    require_positive_int,
    resolve_analysis_subspace,
)
from .selection import SpeciesSelection, resolve_atom_selection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
CoordinateMode = Literal["laboratory", "reference_cell"]
DriftMode = Literal["center_of_mass", "center_of_geometry"]
ReferenceCellInput = Literal["initial", "mean"] | NDArray[np.float64]

DEFAULT_DISPLACEMENT_MEMORY_TARGET_BYTES = 256 * 1024**2
# Peak workspace estimate per displacement sample: two gathered Cartesian
# endpoints (6 doubles), one Cartesian difference (3), one projected output
# (d), and the immutable owned output copy (d).
_BASE_WORKSPACE_COMPONENTS = 9


class MSDWarning(UserWarning):
    """Base warning category for MSD interpretation or sampling issues."""


class VariableCellMSDWarning(MSDWarning):
    """Laboratory-frame MSD may contain appreciable affine cell motion."""


class FixedOriginMSDWarning(MSDWarning):
    """Fixed-origin MSD should not be treated as an equilibrium estimator."""


class CollectiveMotionWarning(MSDWarning):
    """Drift subtraction may remove collective motion of measured atoms."""


class SparseOriginWarning(MSDWarning):
    """Large-lag MSD values have few independent time origins."""


class NumericalMSDWarning(MSDWarning):
    """FFT cancellation produced materially negative displacement moments."""


def _validate_uniform_time_grid(collection: AtomisticFrameCollection) -> float:
    collection.require_trajectory("Displacement analysis")
    collection.require_minimum_frames(2, "Displacement analysis")
    times = collection.require_time_axis("Displacement analysis")
    increments = np.diff(times)
    if not np.all(np.isfinite(increments)) or np.any(increments <= 0.0):
        raise ValueError("Trajectory times must be finite and strictly increasing.")
    if not np.allclose(
        increments,
        increments[0],
        rtol=1.0e-10,
        atol=1.0e-14,
    ):
        raise ValueError(
            "Displacement analysis currently requires a uniformly sampled time "
            "grid; resample or split the trajectory before analysis."
        )
    return float(increments[0])


def _validate_cell(cell: ArrayLike, *, label: str) -> FloatArray:
    array = np.asarray(cell, dtype=np.float64)
    if array.shape != (3, 3):
        raise ValueError(f"{label} must have shape (3, 3); received {array.shape}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} contains non-finite values.")
    determinant = float(np.linalg.det(array))
    if abs(determinant) <= 1.0e-12:
        raise ValueError(f"{label} is singular or nearly singular.")
    return np.array(array, dtype=np.float64, copy=True)


def _resolve_reference_cell(
    collection: AtomisticFrameCollection,
    reference_cell: ReferenceCellInput,
) -> tuple[FloatArray, str]:
    if isinstance(reference_cell, str):
        if reference_cell == "initial":
            return np.array(collection.cells[0], copy=True), "initial"
        if reference_cell == "mean":
            mean_cell = np.mean(collection.cells, axis=0)
            return _validate_cell(mean_cell, label="Mean reference cell"), "mean"
        raise ValueError(
            "reference_cell must be 'initial', 'mean', or a finite 3x3 matrix."
        )
    return _validate_cell(reference_cell, label="Explicit reference cell"), "explicit"


def _cell_variation_is_appreciable(cells: FloatArray) -> bool:
    volumes = np.abs(np.linalg.det(cells))
    mean_volume = float(np.mean(volumes))
    volume_span = 0.0 if mean_volume == 0.0 else float(np.ptp(volumes) / mean_volume)
    baseline = max(float(np.linalg.norm(cells[0])), np.finfo(np.float64).eps)
    shape_change = float(
        np.max(np.linalg.norm(cells - cells[0], axis=(1, 2))) / baseline
    )
    return volume_span > 1.0e-2 or shape_change > 1.0e-2



@dataclass(frozen=True, slots=True)
class DisplacementInputBundle:
    """Resolved immutable input shared by displacement observables."""

    positions: FloatArray
    times_ps: FloatArray
    sample_spacing_ps: float
    atom_indices: IntArray
    coordinate_mode: str
    reference_cell_mode: str | None
    reference_cell: FloatArray | None
    drift_mode: str | None
    drift_atom_indices: IntArray | None
    subspace: AnalysisSubspace
    signature: DynamicsInputSignature
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        positions = np.asarray(self.positions, dtype=np.float64)
        times = np.asarray(self.times_ps, dtype=np.float64)
        atoms = np.asarray(self.atom_indices, dtype=np.int64)
        reference = (
            None
            if self.reference_cell is None
            else np.asarray(self.reference_cell, dtype=np.float64)
        )
        drift_atoms = (
            None
            if self.drift_atom_indices is None
            else np.asarray(self.drift_atom_indices, dtype=np.int64)
        )
        if positions.ndim != 3 or positions.shape[2] != 3:
            raise ValueError("positions must have shape (T, M, 3).")
        n_frames, n_atoms, _ = positions.shape
        if n_frames < 2 or n_atoms < 1:
            raise ValueError("positions must contain at least two frames and one atom.")
        if times.shape != (n_frames,):
            raise ValueError("times_ps is inconsistent with positions.")
        if atoms.shape != (n_atoms,):
            raise ValueError("atom_indices is inconsistent with positions.")
        if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(times)):
            raise ValueError("Displacement inputs must contain only finite values.")
        if np.any(np.diff(times) <= 0.0):
            raise ValueError("times_ps must be strictly increasing.")
        spacing = float(self.sample_spacing_ps)
        if not np.isfinite(spacing) or spacing <= 0.0:
            raise ValueError("sample_spacing_ps must be finite and positive.")
        if not np.allclose(
            np.diff(times),
            spacing,
            rtol=1.0e-10,
            atol=1.0e-14,
        ):
            raise ValueError("sample_spacing_ps is inconsistent with times_ps.")
        if np.any(atoms < 0) or np.unique(atoms).size != atoms.size:
            raise ValueError("atom_indices must be unique and nonnegative.")
        if self.coordinate_mode not in ("laboratory", "reference_cell"):
            raise ValueError(
                "coordinate_mode must be 'laboratory' or 'reference_cell'."
            )
        if (self.reference_cell_mode is None) != (reference is None):
            raise ValueError(
                "reference_cell_mode and reference_cell must either both be set "
                "or both be None."
            )
        if reference is not None and reference.shape != (3, 3):
            raise ValueError("reference_cell must have shape (3, 3).")
        if (self.drift_mode is None) != (drift_atoms is None):
            raise ValueError(
                "drift_mode and drift_atom_indices must either both be set or "
                "both be None."
            )
        if self.drift_mode not in (None, "center_of_mass", "center_of_geometry"):
            raise ValueError(
                "drift_mode must be None, 'center_of_mass', or "
                "'center_of_geometry'."
            )
        if not isinstance(self.subspace, AnalysisSubspace):
            raise TypeError("subspace must be an AnalysisSubspace.")
        if not isinstance(self.signature, DynamicsInputSignature):
            raise TypeError("signature must be a DynamicsInputSignature.")
        if not np.array_equal(self.signature.atom_indices, atoms):
            raise ValueError("signature atom_indices are inconsistent with the bundle.")
        if self.signature.coordinate_mode != self.coordinate_mode:
            raise ValueError("signature coordinate_mode is inconsistent with the bundle.")
        if self.signature.reference_cell_mode != self.reference_cell_mode:
            raise ValueError(
                "signature reference_cell_mode is inconsistent with the bundle."
            )
        if self.signature.drift_mode != self.drift_mode:
            raise ValueError("signature drift_mode is inconsistent with the bundle.")
        if not np.array_equal(
            self.signature.projection_basis,
            self.subspace.projection_basis,
        ) or self.signature.projection_labels != self.subspace.labels:
            raise ValueError("signature projection basis is inconsistent with the bundle.")
        if not np.array_equal(self.signature.frame_times_ps, times):
            raise ValueError("signature frame_times_ps are inconsistent with the bundle.")
        if self.signature.sample_spacing_ps != spacing:
            raise ValueError("signature sample_spacing_ps is inconsistent with the bundle.")
        signature_reference = self.signature.reference_cell
        if signature_reference is None or reference is None:
            if signature_reference is not reference:
                raise ValueError("signature reference_cell is inconsistent with the bundle.")
        elif not np.array_equal(signature_reference, reference):
            raise ValueError("signature reference_cell is inconsistent with the bundle.")
        signature_drift = self.signature.drift_atom_indices
        if signature_drift is None or drift_atoms is None:
            if signature_drift is not drift_atoms:
                raise ValueError(
                    "signature drift_atom_indices are inconsistent with the bundle."
                )
        elif not np.array_equal(signature_drift, drift_atoms):
            raise ValueError(
                "signature drift_atom_indices are inconsistent with the bundle."
            )

        object.__setattr__(
            self,
            "positions",
            owned_readonly_array(positions, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "times_ps",
            owned_readonly_array(times, dtype=np.float64),
        )
        object.__setattr__(self, "sample_spacing_ps", spacing)
        object.__setattr__(
            self,
            "atom_indices",
            owned_readonly_array(atoms, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "reference_cell",
            None
            if reference is None
            else owned_readonly_array(reference, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "drift_atom_indices",
            None
            if drift_atoms is None
            else owned_readonly_array(drift_atoms, dtype=np.int64),
        )
        object.__setattr__(self, "metadata", freeze_mapping(self.metadata))

    @property
    def n_frames(self) -> int:
        return int(self.positions.shape[0])

    @property
    def n_atoms(self) -> int:
        return int(self.positions.shape[1])


@dataclass(frozen=True, slots=True)
class DisplacementBlockPlan:
    """Deterministic block sizes and conservative peak-work estimate."""

    atom_block_size: int
    origin_block_size: int
    bytes_per_sample: int
    estimated_peak_work_bytes: int
    memory_target_bytes: int | None

    def __post_init__(self) -> None:
        for name in (
            "atom_block_size",
            "origin_block_size",
            "bytes_per_sample",
            "estimated_peak_work_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, (bool, np.bool_)) or not isinstance(
                value, (int, np.integer)
            ):
                raise TypeError(f"{name} must be an integer.")
            if int(value) <= 0:
                raise ValueError(f"{name} must be positive.")
            object.__setattr__(self, name, int(value))
        if self.memory_target_bytes is not None:
            target = require_positive_int(
                self.memory_target_bytes,
                name="memory_target_bytes",
            )
            if self.estimated_peak_work_bytes > target:
                raise ValueError("Block plan exceeds memory_target_bytes.")
            object.__setattr__(self, "memory_target_bytes", target)


@dataclass(frozen=True, slots=True)
class DisplacementBlock:
    """One lag/origin/atom block of projected displacement samples."""

    lag_index: int
    lag_step: int
    lag_time_ps: float
    origin_indices: IntArray
    atom_indices: IntArray
    displacements: FloatArray
    n_samples: int

    def __post_init__(self) -> None:
        lag_index = require_nonnegative_int(self.lag_index, name="lag_index")
        if isinstance(self.lag_step, (bool, np.bool_)) or not isinstance(
            self.lag_step, (int, np.integer)
        ):
            raise TypeError("lag_step must be an integer.")
        lag_step = int(self.lag_step)
        if lag_step < 0:
            raise ValueError("lag_step must be nonnegative.")
        lag_time = float(self.lag_time_ps)
        if not np.isfinite(lag_time) or lag_time < 0.0:
            raise ValueError("lag_time_ps must be finite and nonnegative.")
        origins = np.asarray(self.origin_indices, dtype=np.int64)
        atoms = np.asarray(self.atom_indices, dtype=np.int64)
        displacements = np.asarray(self.displacements, dtype=np.float64)
        if origins.ndim != 1 or origins.size < 1:
            raise ValueError("origin_indices must be a nonempty one-dimensional array.")
        if atoms.ndim != 1 or atoms.size < 1:
            raise ValueError("atom_indices must be a nonempty one-dimensional array.")
        if np.any(origins < 0) or np.any(np.diff(origins) <= 0):
            raise ValueError("origin_indices must be strictly increasing and nonnegative.")
        if np.any(atoms < 0) or np.unique(atoms).size != atoms.size:
            raise ValueError("atom_indices must be unique and nonnegative.")
        if displacements.ndim != 3 or displacements.shape[:2] != (
            origins.size,
            atoms.size,
        ):
            raise ValueError(
                "displacements must have shape (len(origin_indices), "
                "len(atom_indices), d)."
            )
        if displacements.shape[2] not in (1, 2, 3):
            raise ValueError("Displacement subspace rank must be 1, 2, or 3.")
        if not np.all(np.isfinite(displacements)):
            raise ValueError("displacements must contain only finite values.")
        expected_samples = int(origins.size * atoms.size)
        if isinstance(self.n_samples, (bool, np.bool_)) or not isinstance(
            self.n_samples, (int, np.integer)
        ):
            raise TypeError("n_samples must be an integer.")
        if int(self.n_samples) != expected_samples:
            raise ValueError("n_samples is inconsistent with the block shape.")

        object.__setattr__(self, "lag_index", lag_index)
        object.__setattr__(self, "lag_step", lag_step)
        object.__setattr__(self, "lag_time_ps", lag_time)
        object.__setattr__(
            self,
            "origin_indices",
            owned_readonly_array(origins, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "atom_indices",
            owned_readonly_array(atoms, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "displacements",
            owned_readonly_array(displacements, dtype=np.float64),
        )
        object.__setattr__(self, "n_samples", expected_samples)


def prepare_displacement_inputs(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    coordinate_mode: CoordinateMode = "laboratory",
    reference_cell: ReferenceCellInput = "initial",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    axes: Sequence[Literal["x", "y", "z"]] | None = None,
    projection_basis: ArrayLike | None = None,
) -> DisplacementInputBundle:
    """Resolve displacement semantics once into an immutable input bundle."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    dt = _validate_uniform_time_grid(collection)
    if coordinate_mode not in ("laboratory", "reference_cell"):
        raise ValueError("coordinate_mode must be 'laboratory' or 'reference_cell'.")
    if drift_mode not in (None, "center_of_mass", "center_of_geometry"):
        raise ValueError(
            "drift_mode must be None, 'center_of_mass', or 'center_of_geometry'."
        )

    selected = resolve_atom_selection(
        collection.atomic_numbers,
        species=species,
        atom_indices=atom_indices,
        selection_name="measured_atom",
    )
    subspace = resolve_analysis_subspace(
        axes=axes,
        projection_basis=projection_basis,
    )

    resolved_reference_cell: FloatArray | None = None
    reference_definition: str | None = None
    variable_cell_warning = False
    if coordinate_mode == "reference_cell":
        resolved_reference_cell, reference_definition = _resolve_reference_cell(
            collection,
            reference_cell,
        )
    elif _cell_variation_is_appreciable(collection.cells):
        variable_cell_warning = True
        warnings.warn(
            "Laboratory-frame MSD includes appreciable affine cell deformation; "
            "consider coordinate_mode='reference_cell' for NPT diffusion.",
            VariableCellMSDWarning,
            stacklevel=2,
        )

    drift_indices: IntArray | None = None
    collective_motion_warning = False
    if drift_mode is None:
        if drift_species is not None or drift_atom_indices is not None:
            raise ValueError("A drift selection was supplied but drift_mode is None.")
    else:
        drift_indices = resolve_atom_selection(
            collection.atomic_numbers,
            species=drift_species,
            atom_indices=drift_atom_indices,
            selection_name="drift_atom",
        )
        if np.array_equal(np.sort(drift_indices), np.sort(selected)) and (
            selected.size < collection.n_atoms
        ):
            collective_motion_warning = True
            warnings.warn(
                "The drift reference equals the measured subset; subtracting it "
                "removes collective translation of that subset.",
                CollectiveMotionWarning,
                stacklevel=2,
            )

    consumer_view = prepare_displacement_coordinate_view(
        collection,
        coordinate_mode=coordinate_mode,
        reference_cell=resolved_reference_cell,
        reference_cell_mode=reference_definition,
        drift_mode=drift_mode,
        drift_atom_indices=drift_indices,
    )
    positions = np.asarray(
        consumer_view.positions[:, selected, :], dtype=np.float64
    )

    velocity_source = (
        None
        if collection.provenance is None
        else collection.provenance.velocity_source
    )
    signature = build_dynamics_signature(
        collection,
        atom_indices=selected,
        coordinate_mode=coordinate_mode,
        reference_cell_mode=reference_definition,
        reference_cell=resolved_reference_cell,
        drift_mode=drift_mode,
        drift_atom_indices=drift_indices,
        velocity_source=velocity_source,
        subspace=subspace,
    )
    metadata = {
        "selected_atom_indices": selected.tolist(),
        "coordinate_mode": coordinate_mode,
        "reference_cell_definition": reference_definition,
        "drift_mode": drift_mode,
        "drift_atom_indices": (
            None if drift_indices is None else drift_indices.tolist()
        ),
        "analysis_subspace_rank": subspace.rank,
        "analysis_subspace_labels": subspace.labels,
        "variable_cell_warning_emitted": variable_cell_warning,
        "collective_motion_warning_emitted": collective_motion_warning,
        "consumer_registration_signature": consumer_view.signature,
        "frame_registration_signature": consumer_view.registration.signature,
        "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
        "consumer_migration_stage": "C0B",
    }
    return DisplacementInputBundle(
        positions=positions,
        times_ps=collection.require_time_axis("Displacement analysis"),
        sample_spacing_ps=dt,
        atom_indices=selected,
        coordinate_mode=coordinate_mode,
        reference_cell_mode=reference_definition,
        reference_cell=resolved_reference_cell,
        drift_mode=drift_mode,
        drift_atom_indices=drift_indices,
        subspace=subspace,
        signature=signature,
        metadata=metadata,
    )


def _resolve_lag_steps(bundle: DisplacementInputBundle, lag_steps: ArrayLike) -> IntArray:
    raw = np.asarray(lag_steps)
    if raw.ndim != 1 or raw.size < 1:
        raise ValueError("lag_steps must be a nonempty one-dimensional array.")
    if np.issubdtype(raw.dtype, np.bool_) or not np.issubdtype(
        raw.dtype,
        np.integer,
    ):
        raise TypeError("lag_steps must contain integers.")
    lags = raw.astype(np.int64, copy=False)
    if np.any(lags < 0):
        raise ValueError("lag_steps must be nonnegative.")
    if np.any(lags >= bundle.n_frames):
        bad = int(lags[lags >= bundle.n_frames][0])
        raise ValueError(
            f"lag step {bad} exceeds the largest available lag "
            f"{bundle.n_frames - 1}."
        )
    if lags.size > 1 and np.any(np.diff(lags) <= 0):
        raise ValueError("lag_steps must be strictly increasing and unique.")
    return np.array(lags, dtype=np.int64, copy=True)


def resolve_displacement_block_plan(
    bundle: DisplacementInputBundle,
    lag_steps: ArrayLike,
    *,
    origin_stride: int = 1,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
    memory_target_bytes: int | None = None,
) -> DisplacementBlockPlan:
    """Resolve deterministic upper bounds for displacement block dimensions."""

    if not isinstance(bundle, DisplacementInputBundle):
        raise TypeError("bundle must be a DisplacementInputBundle.")
    lags = _resolve_lag_steps(bundle, lag_steps)
    stride = require_positive_int(origin_stride, name="origin_stride")
    atom_cap = bundle.n_atoms
    if atom_block_size is not None:
        atom_cap = min(
            bundle.n_atoms,
            require_positive_int(atom_block_size, name="atom_block_size"),
        )
    max_origins = max(
        int((bundle.n_frames - 1 - int(lag)) // stride + 1)
        for lag in lags
    )
    origin_cap = max_origins
    if origin_block_size is not None:
        origin_cap = min(
            max_origins,
            require_positive_int(origin_block_size, name="origin_block_size"),
        )

    bytes_per_sample = 8 * (_BASE_WORKSPACE_COMPONENTS + 2 * bundle.subspace.rank)
    target: int | None = None
    if memory_target_bytes is not None:
        target = require_positive_int(
            memory_target_bytes,
            name="memory_target_bytes",
        )
        max_samples = target // bytes_per_sample
        if max_samples < 1:
            raise ValueError(
                "memory_target_bytes is too small for one displacement sample; "
                f"at least {bytes_per_sample} bytes are required."
            )
        # Preserve the requested/canonical atom block whenever one origin fits;
        # then reduce atom count only if even a single origin would exceed target.
        if atom_cap > max_samples:
            atom_cap = int(max_samples)
            origin_cap = 1
        else:
            origin_cap = min(origin_cap, max(1, int(max_samples // atom_cap)))

    estimated = int(atom_cap * origin_cap * bytes_per_sample)
    return DisplacementBlockPlan(
        atom_block_size=atom_cap,
        origin_block_size=origin_cap,
        bytes_per_sample=bytes_per_sample,
        estimated_peak_work_bytes=estimated,
        memory_target_bytes=target,
    )


def iter_displacement_blocks(
    bundle: DisplacementInputBundle,
    lag_steps: ArrayLike,
    *,
    origin_stride: int = 1,
    atom_block_size: int | None = None,
    origin_block_size: int | None = None,
    memory_target_bytes: int | None = None,
) -> Iterator[DisplacementBlock]:
    """Yield lag-major, origin-block-major, atom-block-major displacements."""

    if not isinstance(bundle, DisplacementInputBundle):
        raise TypeError("bundle must be a DisplacementInputBundle.")
    lags = _resolve_lag_steps(bundle, lag_steps)
    stride = require_positive_int(origin_stride, name="origin_stride")
    plan = resolve_displacement_block_plan(
        bundle,
        lags,
        origin_stride=stride,
        atom_block_size=atom_block_size,
        origin_block_size=origin_block_size,
        memory_target_bytes=memory_target_bytes,
    )
    basis = bundle.subspace.projection_basis
    for lag_index, lag_value in enumerate(lags):
        lag = int(lag_value)
        origins = np.arange(0, bundle.n_frames - lag, stride, dtype=np.int64)
        for origin_start in range(0, origins.size, plan.origin_block_size):
            origin_block = origins[
                origin_start : origin_start + plan.origin_block_size
            ]
            destination_block = origin_block + lag
            for atom_start in range(0, bundle.n_atoms, plan.atom_block_size):
                atom_stop = min(bundle.n_atoms, atom_start + plan.atom_block_size)
                delta = (
                    bundle.positions[destination_block, atom_start:atom_stop, :]
                    - bundle.positions[origin_block, atom_start:atom_stop, :]
                )
                projected = np.einsum(
                    "oaj,dj->oad",
                    delta,
                    basis,
                    optimize=True,
                )
                atoms = bundle.atom_indices[atom_start:atom_stop]
                yield DisplacementBlock(
                    lag_index=lag_index,
                    lag_step=lag,
                    lag_time_ps=float(lag * bundle.sample_spacing_ps),
                    origin_indices=origin_block,
                    atom_indices=atoms,
                    displacements=projected,
                    n_samples=int(origin_block.size * atoms.size),
                )
