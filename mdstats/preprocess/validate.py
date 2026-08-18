"""Validation for normalized atomistic frame collections."""

from __future__ import annotations

import numpy as np

from ..exceptions import FrameCollectionError, InvalidCellError
from ..semantics import FrameSemantics


def _require_shape(name: str, value: np.ndarray, shape: tuple[int, ...]) -> None:
    if value.shape != shape:
        raise FrameCollectionError(f"{name} has shape {value.shape}; expected {shape}.")


def _require_finite(name: str, value: np.ndarray) -> None:
    if not np.all(np.isfinite(value)):
        index = tuple(np.argwhere(~np.isfinite(value))[0])
        raise FrameCollectionError(
            f"{name} contains a non-finite value at index {index}."
        )


def validate_frame_collection(
    collection: object, *, cell_tolerance: float = 1.0e-12
) -> None:
    """Raise a descriptive exception if any collection invariant is violated."""
    n_atoms = int(collection.atomic_numbers.shape[0])
    n_frames = int(collection.frame_ids.shape[0])
    if n_atoms < 1:
        raise FrameCollectionError("A collection must contain at least one atom.")
    if n_frames < 1:
        raise FrameCollectionError("A collection must contain at least one frame.")

    _require_shape("frame_ids", collection.frame_ids, (n_frames,))
    _require_shape("atomic_numbers", collection.atomic_numbers, (n_atoms,))
    _require_shape("masses", collection.masses, (n_atoms,))
    _require_shape("pbc", collection.pbc, (3,))
    if collection.steps is not None:
        _require_shape("steps", collection.steps, (n_frames,))
    if collection.times is not None:
        _require_shape("times", collection.times, (n_frames,))
    _require_shape("cells", collection.cells, (n_frames, 3, 3))
    _require_shape("origins", collection.origins, (n_frames, 3))
    _require_shape(
        "fractional_positions",
        collection.fractional_positions,
        (n_frames, n_atoms, 3),
    )
    if collection.velocities is not None:
        _require_shape("velocities", collection.velocities, (n_frames, n_atoms, 3))

    optional_shapes = {
        "forces": (n_frames, n_atoms, 3),
        "stresses": (n_frames, 3, 3),
        "scalar_pressures": (n_frames,),
        "temperatures": (n_frames,),
        "potential_energies": (n_frames,),
        "kinetic_energies": (n_frames,),
        "total_energies": (n_frames,),
    }
    for name, shape in optional_shapes.items():
        value = getattr(collection, name)
        if value is not None:
            _require_shape(name, value, shape)
            _require_finite(name, value)

    for name in (
        "masses",
        "cells",
        "origins",
        "fractional_positions",
    ):
        _require_finite(name, getattr(collection, name))
    if collection.times is not None:
        _require_finite("times", collection.times)
    if collection.velocities is not None:
        _require_finite("velocities", collection.velocities)

    if np.unique(collection.frame_ids).size != n_frames:
        raise FrameCollectionError("frame_ids must be unique within a collection.")
    if np.any(collection.atomic_numbers <= 0):
        raise FrameCollectionError("Atomic numbers must be positive integers.")
    if np.any(collection.masses <= 0.0):
        raise FrameCollectionError("Atomic masses must be strictly positive.")

    if collection.frame_semantics is FrameSemantics.TRAJECTORY:
        if collection.times is None:
            raise FrameCollectionError(
                "A time-ordered trajectory requires a physical times array."
            )
        if n_frames > 1 and not np.all(np.diff(collection.times) > 0.0):
            raise FrameCollectionError(
                "Trajectory frame times must be strictly increasing."
            )
        if collection.steps is not None and n_frames > 1:
            if not np.all(np.diff(collection.steps) > 0):
                raise FrameCollectionError(
                    "Trajectory source timesteps must be strictly increasing."
                )
        if n_frames > 1 and collection.velocities is None:
            raise FrameCollectionError(
                "A multi-frame trajectory requires a complete velocity field."
            )
    elif collection.frame_semantics is FrameSemantics.ENSEMBLE:
        if collection.velocities is not None:
            raise FrameCollectionError(
                "Independent ensembles must not store velocities. Convert or "
                "discard them before construction."
            )

    determinants = np.linalg.det(collection.cells)
    if np.any(np.abs(determinants) <= cell_tolerance):
        frame = int(np.argwhere(np.abs(determinants) <= cell_tolerance)[0, 0])
        raise InvalidCellError(
            f"Cell at frame {frame} is singular or nearly singular: "
            f"det(H)={determinants[frame]:.6g}."
        )

    if collection.stresses is not None and not np.allclose(
        collection.stresses,
        np.swapaxes(collection.stresses, 1, 2),
        rtol=1.0e-9,
        atol=1.0e-12,
    ):
        raise FrameCollectionError("Stress tensors must be symmetric.")

    if collection.provenance is None:
        raise FrameCollectionError("Frame-collection provenance is required.")
    if collection.provenance.stress_convention != "tensile_positive":
        raise FrameCollectionError(
            "Only the tensile-positive normalized stress convention is accepted."
        )

    expected_single_frame = n_frames == 1
    if collection.metadata.get("single_frame") is not expected_single_frame:
        raise FrameCollectionError(
            "metadata['single_frame'] is inconsistent with the stored frame count."
        )
    if collection.metadata.get("frame_semantics") != collection.frame_semantics.value:
        raise FrameCollectionError(
            "metadata['frame_semantics'] is inconsistent with frame_semantics."
        )
    if collection.velocities is None and collection.provenance.velocity_source not in {
        "unavailable",
        "discarded_for_ensemble",
    }:
        raise FrameCollectionError(
            "Velocity provenance is inconsistent with an absent velocity field."
        )
    if collection.velocities is not None and collection.provenance.velocity_source in {
        "unavailable",
        "discarded_for_ensemble",
    }:
        raise FrameCollectionError(
            "Velocity provenance is inconsistent with a present velocity field."
        )
