"""Shared velocity-input preparation for trajectory analyses.

This private module centralizes the selection, weighting, drift-removal, and
uniform-time-grid semantics used by VACF, direct Welch velocity spectra, and
collective charge-current construction. It introduces no new physical estimator:
the helpers are an mdstats refactor of the validated velocity-input contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ..coordinates.consumer_adapters import prepare_velocity_translation_view
from .selection import SpeciesSelection, resolve_atom_selection
from ._dynamics_common import (
    DynamicsInputSignature,
    build_dynamics_signature,
    owned_readonly_array,
    require_bool,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
DriftMode = Literal["center_of_mass", "center_of_geometry"]
WeightInput = Literal["uniform", "mass"] | ArrayLike


@dataclass(frozen=True, slots=True)
class VelocityInputBundle:
    """Resolved velocity-analysis inputs without copying the full trajectory.

    ``velocities`` retains the collection's canonical ``(T, N, 3)`` array.
    Selection and weighting arrays are small owned arrays.  ``drift_velocity``
    is either ``None`` or a framewise ``(T, 3)`` correction.  Per-atom output
    indices are stored both in canonical atom numbering and in local measured-
    selection numbering so downstream estimators need no duplicate lookup.
    """

    sample_spacing_ps: float
    velocities: FloatArray

    atom_indices: IntArray
    atom_weights: FloatArray
    weight_sum: float
    weighting: str
    weight_units: str
    correlation_units: str

    drift_mode: str | None
    drift_atom_indices: IntArray | None
    drift_velocity: FloatArray | None
    drift_matches_measured_subset: bool

    per_atom_indices: IntArray | None
    per_atom_local_indices: IntArray | None
    signature: DynamicsInputSignature
    translation_policy_signature: str
    consumer_registration_signature: str
    scientific_drift_owner: str


def validate_uniform_time_grid(
    collection: AtomisticFrameCollection,
    *,
    analysis_name: str,
) -> float:
    """Validate trajectory semantics and return the uniform sample spacing."""

    collection.require_trajectory(analysis_name)
    collection.require_minimum_frames(2, analysis_name)
    times = collection.require_time_axis(analysis_name)
    dt = np.diff(times)
    if not np.all(np.isfinite(dt)) or np.any(dt <= 0.0):
        raise ValueError("Trajectory times must be finite and strictly increasing.")
    if not np.allclose(dt, dt[0], rtol=1.0e-10, atol=1.0e-14):
        raise ValueError(
            f"{analysis_name} currently requires a uniformly sampled time grid; "
            "resample or split the trajectory before analysis."
        )
    return float(dt[0])


def resolve_velocity_weights(
    collection: AtomisticFrameCollection,
    selected: IntArray,
    weights: WeightInput,
) -> tuple[FloatArray, str, str, str]:
    """Resolve one nonnegative atom weight per measured atom."""

    if isinstance(weights, str):
        if weights == "uniform":
            values = np.ones(selected.size, dtype=np.float64)
            return values, "uniform", "dimensionless", "Å^2/ps^2"
        if weights == "mass":
            values = np.asarray(collection.masses[selected], dtype=np.float64)
            return (
                np.array(values, dtype=np.float64, copy=True),
                "mass",
                "amu",
                "amu*Å^2/ps^2",
            )
        raise ValueError("weights must be 'uniform', 'mass', or an explicit array.")

    values = np.asarray(weights, dtype=np.float64)
    if values.shape != (selected.size,):
        raise ValueError(
            f"Explicit weights have shape {values.shape}; expected ({selected.size},)."
        )
    if not np.all(np.isfinite(values)):
        raise ValueError("Explicit weights must contain only finite values.")
    if np.any(values < 0.0):
        raise ValueError("Explicit weights must be nonnegative.")
    if not np.any(values > 0.0):
        raise ValueError("Explicit weights must not all be zero.")
    return np.array(values, copy=True), "explicit", "dimensionless", "Å^2/ps^2"


def compute_drift_velocity(
    collection: AtomisticFrameCollection,
    velocities: FloatArray,
    drift_indices: IntArray,
    *,
    drift_mode: DriftMode,
) -> FloatArray:
    """Return a framewise center-of-geometry or center-of-mass velocity."""

    view = prepare_velocity_translation_view(
        collection,
        velocities=velocities,
        drift_mode=drift_mode,
        drift_atom_indices=drift_indices,
    )
    assert view.drift_velocity is not None
    return np.asarray(view.drift_velocity, dtype=np.float64)


def resolve_per_atom_output(
    selected: IntArray,
    per_atom: bool,
    per_atom_indices: ArrayLike | None,
    n_atoms: int,
) -> tuple[IntArray | None, IntArray | None]:
    """Resolve requested per-atom outputs in canonical and local numbering."""

    per_atom = require_bool(per_atom, name="per_atom")
    if per_atom_indices is None and not per_atom:
        return None, None
    if per_atom_indices is None:
        canonical = np.array(selected, dtype=np.int64, copy=True)
    else:
        raw = np.asarray(per_atom_indices)
        if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
            raise TypeError("per_atom_indices must be a one-dimensional integer array.")
        canonical = raw.astype(np.int64, copy=False)
        if canonical.size == 0:
            raise ValueError("per_atom_indices must not be empty.")
        if np.any(canonical < 0) or np.any(canonical >= n_atoms):
            bad = int(canonical[(canonical < 0) | (canonical >= n_atoms)][0])
            raise IndexError(
                f"per_atom index {bad} is outside the valid range 0..{n_atoms - 1}."
            )
        if np.unique(canonical).size != canonical.size:
            raise ValueError("per_atom_indices contains duplicate entries.")
        measured = set(int(index) for index in selected)
        missing = [int(index) for index in canonical if int(index) not in measured]
        if missing:
            raise ValueError(
                "per_atom_indices must be a subset of the measured atom selection; "
                f"invalid indices: {missing}."
            )
        canonical = np.array(canonical, dtype=np.int64, copy=True)

    lookup = {int(atom): local for local, atom in enumerate(selected)}
    local = np.asarray([lookup[int(atom)] for atom in canonical], dtype=np.int64)
    return canonical, local


def prepare_velocity_inputs(
    collection: AtomisticFrameCollection,
    *,
    analysis_name: str,
    species: SpeciesSelection = None,
    atom_indices: ArrayLike | None = None,
    weights: WeightInput = "uniform",
    drift_mode: DriftMode | None = None,
    drift_species: SpeciesSelection = None,
    drift_atom_indices: ArrayLike | None = None,
    per_atom: bool = False,
    per_atom_indices: ArrayLike | None = None,
) -> VelocityInputBundle:
    """Resolve the common input contract for velocity-based self analyses.

    This function performs no VACF, spectrum, or transport calculation.  It
    prepares canonical selections and framewise drift data so those estimators
    share exactly the same physical input semantics.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    if not isinstance(analysis_name, str) or not analysis_name.strip():
        raise ValueError("analysis_name must be a nonempty string.")

    name = analysis_name.strip()
    sample_spacing_ps = validate_uniform_time_grid(collection, analysis_name=name)
    velocities = np.asarray(collection.require_velocities(name), dtype=np.float64)

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

    resolved_drift_indices: IntArray | None = None
    drift_velocity: FloatArray | None = None
    drift_matches_measured_subset = False
    velocity_translation = None
    if drift_mode is None:
        if drift_species is not None or drift_atom_indices is not None:
            raise ValueError("A drift selection was supplied but drift_mode is None.")
    else:
        resolved_drift_indices = resolve_atom_selection(
            collection.atomic_numbers,
            species=drift_species,
            atom_indices=drift_atom_indices,
            selection_name="drift_atom",
        )
        drift_matches_measured_subset = bool(
            selected.size < collection.n_atoms
            and np.array_equal(
                np.sort(resolved_drift_indices), np.sort(selected)
            )
        )
        velocity_translation = prepare_velocity_translation_view(
            collection,
            velocities=velocities,
            drift_mode=drift_mode,
            drift_atom_indices=resolved_drift_indices,
        )
        drift_velocity = np.asarray(velocity_translation.drift_velocity, dtype=np.float64)

    if velocity_translation is None:
        velocity_translation = prepare_velocity_translation_view(
            collection,
            velocities=velocities,
            drift_mode=None,
            drift_atom_indices=None,
        )

    atom_weights, weighting, weight_units, correlation_units = (
        resolve_velocity_weights(collection, selected, weights)
    )
    weight_sum = float(np.sum(atom_weights))
    output_canonical, output_local = resolve_per_atom_output(
        selected,
        per_atom,
        per_atom_indices,
        collection.n_atoms,
    )

    signature = build_dynamics_signature(
        collection,
        atom_indices=selected,
        coordinate_mode="laboratory",
        reference_cell_mode=None,
        reference_cell=None,
        drift_mode=drift_mode,
        drift_atom_indices=resolved_drift_indices,
        velocity_source=(
            None if collection.provenance is None else collection.provenance.velocity_source
        ),
    )

    return VelocityInputBundle(
        sample_spacing_ps=sample_spacing_ps,
        velocities=velocities,
        atom_indices=owned_readonly_array(selected, dtype=np.int64),
        atom_weights=owned_readonly_array(atom_weights, dtype=np.float64),
        weight_sum=weight_sum,
        weighting=weighting,
        weight_units=weight_units,
        correlation_units=correlation_units,
        drift_mode=drift_mode,
        drift_atom_indices=(
            None
            if resolved_drift_indices is None
            else owned_readonly_array(resolved_drift_indices, dtype=np.int64)
        ),
        drift_velocity=(
            None
            if drift_velocity is None
            else owned_readonly_array(drift_velocity, dtype=np.float64)
        ),
        drift_matches_measured_subset=drift_matches_measured_subset,
        per_atom_indices=(
            None
            if output_canonical is None
            else owned_readonly_array(output_canonical, dtype=np.int64)
        ),
        per_atom_local_indices=(
            None if output_local is None else owned_readonly_array(output_local, dtype=np.int64)
        ),
        signature=signature,
        translation_policy_signature=velocity_translation.policy.signature,
        consumer_registration_signature=velocity_translation.signature,
        scientific_drift_owner="mdstats.coordinates.consumer_adapters",
    )
