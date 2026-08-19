"""Source-independent atomistic frame-collection data model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .exceptions import (
    InsufficientFramesError,
    MissingTimeAxisError,
    MissingVelocityError,
    TrajectoryRequiredError,
)
from .provenance import FrameCollectionProvenance
from .semantics import FrameSemantics, coerce_frame_semantics

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]
FrameSelection = int | slice | NDArray[np.integer] | list[int]


@dataclass(slots=True)
class AtomisticFrameCollection:
    """Fixed-population collection of atomistic configurations.

    A collection has explicit frame semantics:

    - ``trajectory``: frames form a physically ordered time series;
    - ``ensemble``: frames are independent samples and carry no temporal
      continuity assumption.

    The same structural analyses may operate on both forms. Temporal analyses
    must call :meth:`require_trajectory` and, when needed,
    :meth:`require_time_axis` or :meth:`require_velocities`.

    Coordinates use ASE's row-vector cell convention::

        cartesian = fractional @ cell

    For trajectories, ``fractional_positions`` are continuous (unwrapped)
    across time. For ensembles they are wrapped independently into each
    periodic cell.
    """

    frame_semantics: FrameSemantics | str
    frame_ids: IntArray

    # Constant atom metadata.
    atomic_numbers: Int32Array
    masses: FloatArray
    pbc: BoolArray

    # Optional source trajectory labels. They do not imply temporal semantics
    # when frame_semantics == ENSEMBLE.
    steps: IntArray | None
    times: FloatArray | None

    # Frame-dependent geometry.
    cells: FloatArray
    origins: FloatArray
    fractional_positions: FloatArray

    # Cartesian per-atom fields.
    velocities: FloatArray | None = None
    forces: FloatArray | None = None

    # Optional frame-level thermodynamics.
    stresses: FloatArray | None = None
    scalar_pressures: FloatArray | None = None
    temperatures: FloatArray | None = None
    potential_energies: FloatArray | None = None
    kinetic_energies: FloatArray | None = None
    total_energies: FloatArray | None = None

    provenance: FrameCollectionProvenance | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize dtypes and validate collection invariants."""
        self.frame_semantics = coerce_frame_semantics(self.frame_semantics)
        self.frame_ids = np.asarray(self.frame_ids, dtype=np.int64)
        self.atomic_numbers = np.asarray(self.atomic_numbers, dtype=np.int32)
        self.masses = np.asarray(self.masses, dtype=np.float64)
        self.pbc = np.asarray(self.pbc, dtype=np.bool_)
        self.steps = (
            None if self.steps is None else np.asarray(self.steps, dtype=np.int64)
        )
        self.times = (
            None if self.times is None else np.asarray(self.times, dtype=np.float64)
        )
        self.cells = np.asarray(self.cells, dtype=np.float64)
        self.origins = np.asarray(self.origins, dtype=np.float64)
        self.fractional_positions = np.asarray(
            self.fractional_positions, dtype=np.float64
        )
        if self.velocities is not None:
            self.velocities = np.asarray(self.velocities, dtype=np.float64)

        for name in (
            "forces",
            "stresses",
            "scalar_pressures",
            "temperatures",
            "potential_energies",
            "kinetic_energies",
            "total_energies",
        ):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, np.asarray(value, dtype=np.float64))

        self.metadata = dict(self.metadata)
        self.metadata["single_frame"] = self.frame_ids.shape[0] == 1
        self.metadata["frame_semantics"] = self.frame_semantics.value

        from .preprocess.validate import validate_frame_collection

        validate_frame_collection(self)

    @property
    def n_frames(self) -> int:
        """Number of stored configurations."""
        return int(self.frame_ids.shape[0])

    @property
    def n_atoms(self) -> int:
        """Number of atoms in every frame."""
        return int(self.atomic_numbers.shape[0])

    @property
    def is_single_frame(self) -> bool:
        """Whether the collection contains exactly one configuration."""
        return self.n_frames == 1

    @property
    def is_trajectory(self) -> bool:
        """Whether frames form a physically ordered time series."""
        return self.frame_semantics is FrameSemantics.TRAJECTORY

    @property
    def is_ensemble(self) -> bool:
        """Whether frames are independent samples."""
        return self.frame_semantics is FrameSemantics.ENSEMBLE

    @property
    def has_time_axis(self) -> bool:
        """Whether a physical time axis is valid for temporal analysis."""
        return self.is_trajectory and self.times is not None

    @property
    def has_velocities(self) -> bool:
        """Whether a complete Cartesian velocity field is available."""
        return self.velocities is not None

    @property
    def has_forces(self) -> bool:
        """Whether a complete Cartesian force field is available."""
        return self.forces is not None

    @property
    def coordinates_are_time_unwrapped(self) -> bool:
        """Whether fractional coordinates are continuous across frame time."""
        return self.is_trajectory

    def require_minimum_frames(self, minimum: int, analysis_name: str) -> None:
        """Raise if an analysis requires more frames than are stored."""
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise ValueError("minimum must be a positive integer.")
        if self.n_frames < minimum:
            raise InsufficientFramesError(
                f"{analysis_name} requires at least {minimum} frames; "
                f"received {self.n_frames}."
            )

    def require_trajectory(self, analysis_name: str) -> None:
        """Raise unless frames have explicit time-ordered semantics."""
        if not self.is_trajectory:
            raise TrajectoryRequiredError(
                f"{analysis_name} requires a time-ordered trajectory, but the "
                "input is an independent frame ensemble."
            )

    def require_time_axis(self, analysis_name: str) -> FloatArray:
        """Return physical times or raise a descriptive requirement error."""
        self.require_trajectory(analysis_name)
        if self.times is None:
            raise MissingTimeAxisError(
                f"{analysis_name} requires physical frame times, but none are stored."
            )
        return self.times

    def require_velocities(self, analysis_name: str) -> FloatArray:
        """Return velocities or raise a descriptive requirement error."""
        if self.velocities is None:
            raise MissingVelocityError(
                f"{analysis_name} requires atomic velocities, but this "
                "AtomisticFrameCollection has no velocity field."
            )
        return self.velocities

    @property
    def volumes(self) -> FloatArray:
        """Instantaneous cell volumes in Å³."""
        return np.abs(np.linalg.det(self.cells))

    @property
    def is_uniform_time_grid(self) -> bool:
        """Whether a trajectory has uniformly spaced physical frame times."""
        if not self.has_time_axis:
            return False
        assert self.times is not None
        if self.n_frames < 3:
            return True
        dt = np.diff(self.times)
        return bool(np.allclose(dt, dt[0], rtol=1.0e-10, atol=1.0e-14))

    @property
    def pressures(self) -> FloatArray | None:
        """Pressure in eV/Å³, preferring the full normalized stress tensor."""
        if self.stresses is not None:
            return -np.trace(self.stresses, axis1=1, axis2=2) / 3.0
        return self.scalar_pressures

    def get_positions(self, frames: FrameSelection = slice(None)) -> FloatArray:
        """Return Cartesian positions in Å.

        Trajectory coordinates are unwrapped laboratory-frame positions.
        Ensemble coordinates are independent per-frame Cartesian positions.
        """
        scaled = self.fractional_positions[frames]
        cells = self.cells[frames]
        if scaled.ndim == 2:
            return np.asarray(scaled @ cells, dtype=np.float64)
        return np.einsum("tni,tij->tnj", scaled, cells, optimize=True)

    def get_wrapped_fractional_positions(
        self, frames: FrameSelection = slice(None)
    ) -> FloatArray:
        """Return fractional coordinates wrapped only along periodic axes."""
        scaled = np.array(self.fractional_positions[frames], copy=True)
        for axis, periodic in enumerate(self.pbc):
            if periodic:
                scaled[..., axis] -= np.floor(scaled[..., axis])
        return scaled

    def get_wrapped_positions(self, frames: FrameSelection = slice(None)) -> FloatArray:
        """Return Cartesian positions wrapped into each instantaneous cell."""
        scaled = self.get_wrapped_fractional_positions(frames)
        cells = self.cells[frames]
        if scaled.ndim == 2:
            return np.asarray(scaled @ cells, dtype=np.float64)
        return np.einsum("tni,tij->tnj", scaled, cells, optimize=True)

    def select_frames(
        self,
        frames: FrameSelection,
        *,
        frame_semantics: FrameSemantics | str | None = None,
    ) -> AtomisticFrameCollection:
        """Return a frame subset with optional semantic reinterpretation.

        Use ``frame_semantics='ensemble'`` when extracting random or clustered
        frames from an MD trajectory. Velocity data are deliberately discarded
        for ensemble outputs.
        """
        index = np.arange(self.n_frames, dtype=np.int64)[frames]
        index = np.atleast_1d(index).astype(np.int64, copy=False)
        if index.size == 0:
            raise ValueError("Frame selection is empty.")
        semantics = (
            self.frame_semantics
            if frame_semantics is None
            else coerce_frame_semantics(frame_semantics)
        )
        if self.is_ensemble and semantics is FrameSemantics.TRAJECTORY:
            raise ValueError(
                "An independent ensemble cannot be reinterpreted as a trajectory; "
                "temporal continuity and velocities have already been discarded."
            )

        def take_optional(value: FloatArray | IntArray | None):
            return None if value is None else np.array(value[index], copy=True)

        selected_fractional = np.array(self.fractional_positions[index], copy=True)
        velocities = take_optional(self.velocities)
        provenance = self.provenance
        if semantics is FrameSemantics.ENSEMBLE:
            for axis, periodic in enumerate(self.pbc):
                if periodic:
                    selected_fractional[..., axis] -= np.floor(
                        selected_fractional[..., axis]
                    )
            velocities = None
            if provenance is not None:
                provenance = replace(
                    provenance,
                    velocity_source=(
                        "discarded_for_ensemble"
                        if self.velocities is not None
                        else "unavailable"
                    ),
                    coordinate_normalization="independent_frame_wrapping",
                )

        metadata = dict(self.metadata)
        if semantics is FrameSemantics.ENSEMBLE:
            source_field_semantics = dict(metadata.get("source_field_semantics", {}))
            if source_field_semantics:
                source_field_semantics["velocity_frame"] = "unavailable"
                metadata["source_field_semantics"] = source_field_semantics
        metadata["parent_frame_ids"] = self.frame_ids[index].tolist()
        metadata["selection_from_semantics"] = self.frame_semantics.value

        return AtomisticFrameCollection(
            frame_semantics=semantics,
            frame_ids=np.arange(index.size, dtype=np.int64),
            atomic_numbers=self.atomic_numbers.copy(),
            masses=self.masses.copy(),
            pbc=self.pbc.copy(),
            steps=take_optional(self.steps),
            times=take_optional(self.times),
            cells=np.array(self.cells[index], copy=True),
            origins=np.array(self.origins[index], copy=True),
            fractional_positions=selected_fractional,
            velocities=velocities,
            forces=take_optional(self.forces),
            stresses=take_optional(self.stresses),
            scalar_pressures=take_optional(self.scalar_pressures),
            temperatures=take_optional(self.temperatures),
            potential_energies=take_optional(self.potential_energies),
            kinetic_energies=take_optional(self.kinetic_energies),
            total_energies=take_optional(self.total_energies),
            provenance=provenance,
            metadata=metadata,
        )

    def as_ensemble(self) -> AtomisticFrameCollection:
        """Return the same frames as independent samples without velocities."""
        return self.select_frames(slice(None), frame_semantics=FrameSemantics.ENSEMBLE)
