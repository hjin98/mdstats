"""Source-independent frame-collection normalization pipeline."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from ..collection import AtomisticFrameCollection
from ..exceptions import (
    AtomIdentityError,
    IncompleteFieldError,
    MissingTimeError,
    SpeciesConsistencyError,
)
from ..io.common import RawFrameCollection
from ..provenance import FrameCollectionProvenance, SourceFormat
from ..semantics import FrameSemantics, coerce_frame_semantics
from .unwrap import (
    construct_independent_fractional_positions,
    construct_unwrapped_fractional_positions,
)
from .velocity import VelocityReconstructionWarning, reconstruct_velocities


def _reorder_atom_scalar(values: NDArray, order: NDArray[np.int64]) -> NDArray:
    return np.take_along_axis(values, order, axis=1)


def _reorder_atom_vector(values: NDArray, order: NDArray[np.int64]) -> NDArray:
    return np.take_along_axis(values, order[..., None], axis=1)


def _canonicalize_atom_order(raw: RawFrameCollection) -> RawFrameCollection:
    """Sort persistent IDs and verify fixed atom identity/species."""
    n_frames, n_atoms = raw.atomic_numbers.shape
    if raw.source_ids is None:
        order = np.broadcast_to(np.arange(n_atoms, dtype=np.int64), (n_frames, n_atoms))
    else:
        ids = np.asarray(raw.source_ids, dtype=np.int64)
        if ids.shape != (n_frames, n_atoms):
            raise AtomIdentityError(
                f"source_ids has shape {ids.shape}; expected {(n_frames, n_atoms)}."
            )
        order = np.argsort(ids, axis=1, kind="stable")
        sorted_ids = _reorder_atom_scalar(ids, order)
        if np.any(np.diff(sorted_ids, axis=1) == 0):
            frame = int(np.argwhere(np.diff(sorted_ids, axis=1) == 0)[0, 0])
            raise AtomIdentityError(f"Duplicate source atom ID in frame {frame}.")
        reference = sorted_ids[0]
        mismatch = np.any(sorted_ids != reference[None, :], axis=1)
        if np.any(mismatch):
            frame = int(np.flatnonzero(mismatch)[0])
            raise AtomIdentityError(
                f"Sorted atom IDs in frame {frame} differ from the first frame; "
                "atoms may have been inserted, deleted, or omitted."
            )

    raw.atomic_numbers = _reorder_atom_scalar(raw.atomic_numbers, order)
    raw.masses = _reorder_atom_scalar(raw.masses, order)
    raw.coordinates = _reorder_atom_vector(raw.coordinates, order)

    if raw.source_type_ids is not None:
        raw.source_type_ids = _reorder_atom_scalar(raw.source_type_ids, order)
    if raw.image_flags is not None:
        raw.image_flags = _reorder_atom_vector(raw.image_flags, order)
    if raw.velocities is not None:
        raw.velocities = _reorder_atom_vector(raw.velocities, order)
    if raw.forces is not None:
        raw.forces = _reorder_atom_vector(raw.forces, order)

    if np.any(raw.atomic_numbers != raw.atomic_numbers[0][None, :]):
        frame, atom = np.argwhere(raw.atomic_numbers != raw.atomic_numbers[0][None, :])[
            0
        ]
        raise SpeciesConsistencyError(
            f"Atomic species changed at canonical atom index {atom}, frame {frame}."
        )
    if not np.allclose(raw.masses, raw.masses[0][None, :], rtol=0.0, atol=1e-10):
        frame, atom = np.argwhere(
            ~np.isclose(raw.masses, raw.masses[0][None, :], rtol=0.0, atol=1e-10)
        )[0]
        raise SpeciesConsistencyError(
            f"Atomic mass changed at canonical atom index {atom}, frame {frame}."
        )
    if raw.source_type_ids is not None and np.any(
        raw.source_type_ids != raw.source_type_ids[0][None, :]
    ):
        frame, atom = np.argwhere(
            raw.source_type_ids != raw.source_type_ids[0][None, :]
        )[0]
        raise SpeciesConsistencyError(
            f"Source atom type changed at canonical atom index {atom}, frame {frame}."
        )

    raw.source_ids = None
    return raw


def normalize_raw_frame_collection(
    raw: RawFrameCollection,
    *,
    frame_semantics: FrameSemantics | str,
    source_format: SourceFormat,
    source_files: tuple[str | Path, ...],
    units_source: str,
    stress_source: str | None,
    reconstruct_missing_velocities: bool = True,
    unwrapping_warning_threshold: float = 0.45,
) -> AtomisticFrameCollection:
    """Normalize source data into :class:`AtomisticFrameCollection`."""
    semantics = coerce_frame_semantics(frame_semantics)
    raw = _canonicalize_atom_order(raw)

    if semantics is FrameSemantics.TRAJECTORY:
        if raw.times is None:
            raise MissingTimeError(
                "A time-ordered trajectory requires physical frame times."
            )
        scaled, coordinate_method = construct_unwrapped_fractional_positions(
            coordinate_kind=raw.coordinate_kind,
            coordinates=raw.coordinates,
            cells=raw.cells,
            origins=raw.origins,
            pbc=raw.pbc,
            image_flags=raw.image_flags,
            warning_threshold=unwrapping_warning_threshold,
        )

        if raw.velocities is not None:
            if raw.velocities.shape != raw.coordinates.shape or not np.all(
                np.isfinite(raw.velocities)
            ):
                raise IncompleteFieldError(
                    "Native velocities are present but incomplete or non-finite."
                )
            velocities = np.asarray(raw.velocities, dtype=np.float64)
            velocity_source = "native"
        elif raw.frame_ids.shape[0] == 1:
            velocities = None
            velocity_source = "unavailable"
        else:
            if not reconstruct_missing_velocities:
                raise IncompleteFieldError(
                    "The source contains no complete velocity trajectory and "
                    "velocity reconstruction was disabled."
                )
            cartesian = np.einsum("tni,tij->tnj", scaled, raw.cells, optimize=True)
            velocities = reconstruct_velocities(cartesian, raw.times)
            velocity_source = "finite_difference"
            warnings.warn(
                "Velocities were reconstructed from unwrapped Cartesian positions. "
                "High-frequency velocity spectra may be distorted.",
                VelocityReconstructionWarning,
                stacklevel=2,
            )
    else:
        scaled, coordinate_method = construct_independent_fractional_positions(
            coordinate_kind=raw.coordinate_kind,
            coordinates=raw.coordinates,
            cells=raw.cells,
            origins=raw.origins,
            pbc=raw.pbc,
        )
        velocities = None
        velocity_source = (
            "discarded_for_ensemble" if raw.velocities is not None else "unavailable"
        )

    provenance = FrameCollectionProvenance(
        source_format=source_format,
        source_files=tuple(str(Path(path)) for path in source_files),
        velocity_source=velocity_source,
        coordinate_normalization=coordinate_method,  # type: ignore[arg-type]
        stress_source=stress_source,
        units_source=units_source,
    )

    source_field_semantics = {
        "schema": "mdstats.source-field-semantics.v1",
        "position_frame": "cell_origin_relative_cartesian",
        "velocity_frame": (
            "unavailable"
            if velocities is None
            else (
                "finite_difference_normalized_cartesian"
                if velocity_source == "finite_difference"
                else "normalized_cartesian"
            )
        ),
        "force_frame": (
            "normalized_cartesian_covector"
            if raw.forces is not None
            else "unavailable"
        ),
        "box_origin_frame": (
            "zero_origin_convention"
            if np.allclose(raw.origins, 0.0, rtol=0.0, atol=0.0)
            else "laboratory_cartesian"
        ),
    }
    metadata = {
        **dict(raw.metadata),
        "single_frame": raw.frame_ids.shape[0] == 1,
        "frame_semantics": semantics.value,
        "source_field_semantics": source_field_semantics,
    }
    if semantics is FrameSemantics.ENSEMBLE and raw.velocities is not None:
        metadata["native_velocities_discarded"] = True

    return AtomisticFrameCollection(
        frame_semantics=semantics,
        frame_ids=np.asarray(raw.frame_ids, dtype=np.int64),
        atomic_numbers=np.asarray(raw.atomic_numbers[0], dtype=np.int32),
        masses=np.asarray(raw.masses[0], dtype=np.float64),
        pbc=np.asarray(raw.pbc, dtype=np.bool_),
        steps=None if raw.steps is None else np.asarray(raw.steps, dtype=np.int64),
        times=None if raw.times is None else np.asarray(raw.times, dtype=np.float64),
        cells=np.asarray(raw.cells, dtype=np.float64),
        origins=np.asarray(raw.origins, dtype=np.float64),
        fractional_positions=scaled,
        velocities=velocities,
        forces=raw.forces,
        stresses=raw.stresses,
        scalar_pressures=raw.scalar_pressures,
        temperatures=raw.temperatures,
        potential_energies=raw.potential_energies,
        kinetic_energies=raw.kinetic_energies,
        total_energies=raw.total_energies,
        provenance=provenance,
        metadata=metadata,
    )
