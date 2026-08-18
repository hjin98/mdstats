"""Shared contracts for dynamical analyses.

This module contains mdstats-specific infrastructure introduced by the H0
hardening stage: explicit analysis subspaces, semantic input signatures, deep
result freezing, and strict option validators.  It does not define a new
physical estimator.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
AxisLabel = Literal["x", "y", "z"]

_AXIS_INDEX: dict[str, int] = {"x": 0, "y": 1, "z": 2}
_ORTHONORMAL_RTOL = 1.0e-10
_ORTHONORMAL_ATOL = 1.0e-12


def owned_readonly_array(
    value: ArrayLike,
    *,
    dtype: np.dtype[Any] | type[Any] | None = None,
) -> NDArray[Any]:
    """Return an owned, C-contiguous, read-only NumPy array."""

    array = np.array(value, dtype=dtype, copy=True, order="C")
    array.setflags(write=False)
    return array


def freeze_nested(value: Any) -> Any:
    """Recursively freeze public metadata and diagnostic values.

    Mappings become read-only mapping proxies, sequences become tuples, sets
    become frozensets, and NumPy arrays become owned read-only arrays.  Scalar
    values and immutable dataclasses are retained.
    """

    if isinstance(value, np.ndarray):
        return owned_readonly_array(value)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: freeze_nested(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_nested(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_nested(item) for item in value)
    if isinstance(value, np.generic):
        return value.item()
    return value


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return one recursively immutable metadata mapping."""

    if value is None:
        return MappingProxyType({})
    frozen = freeze_nested(value)
    assert isinstance(frozen, Mapping)
    return frozen


def require_bool(value: object, *, name: str) -> bool:
    """Require an actual Python/NumPy boolean, rejecting integer substitutes."""

    if not isinstance(value, (bool, np.bool_)):
        raise TypeError(f"{name} must be a boolean.")
    return bool(value)


def require_positive_int(value: object, *, name: str) -> int:
    """Require a positive integer while rejecting booleans."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise TypeError(f"{name} must be an integer.")
    resolved = int(value)
    if resolved <= 0:
        raise ValueError(f"{name} must be a positive integer.")
    return resolved


def require_nonnegative_int(value: object, *, name: str) -> int:
    """Require a nonnegative integer while rejecting booleans."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, np.integer)
    ):
        raise TypeError(f"{name} must be an integer.")
    resolved = int(value)
    if resolved < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return resolved


def require_finite_real(
    value: object,
    *,
    name: str,
    positive: bool = False,
    nonnegative: bool = False,
) -> float:
    """Require a finite real scalar with an optional sign constraint."""

    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TypeError(f"{name} must be a real number.")
    resolved = float(value)
    if not np.isfinite(resolved):
        raise ValueError(f"{name} must be finite.")
    if positive and resolved <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    if nonnegative and resolved < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative.")
    return resolved


@dataclass(frozen=True, slots=True, eq=False)
class AnalysisSubspace:
    """Resolved orthonormal physical subspace for a dynamical observable."""

    projection_basis: FloatArray
    labels: tuple[AxisLabel, ...] | None
    rank: int

    def __post_init__(self) -> None:
        basis = np.asarray(self.projection_basis, dtype=np.float64)
        if basis.ndim != 2 or basis.shape[1] != 3:
            raise ValueError("projection_basis must have shape (d, 3).")
        rank = int(basis.shape[0])
        if rank not in (1, 2, 3):
            raise ValueError("projection_basis rank must be 1, 2, or 3.")
        if self.rank != rank:
            raise ValueError("rank is inconsistent with projection_basis.")
        if not np.all(np.isfinite(basis)):
            raise ValueError("projection_basis must contain only finite values.")
        gram = basis @ basis.T
        if not np.allclose(
            gram,
            np.eye(rank, dtype=np.float64),
            rtol=_ORTHONORMAL_RTOL,
            atol=_ORTHONORMAL_ATOL,
        ):
            raise ValueError("projection_basis rows must be orthonormal.")
        labels = None if self.labels is None else tuple(self.labels)
        if labels is not None:
            if len(labels) != rank:
                raise ValueError("projection labels must match the subspace rank.")
            if len(set(labels)) != len(labels) or any(
                label not in _AXIS_INDEX for label in labels
            ):
                raise ValueError("projection labels must be unique x/y/z axes.")
            expected = np.eye(3, dtype=np.float64)[
                [_AXIS_INDEX[label] for label in labels]
            ]
            if not np.allclose(
                basis,
                expected,
                rtol=0.0,
                atol=_ORTHONORMAL_ATOL,
            ):
                raise ValueError(
                    "Axis labels are inconsistent with projection_basis."
                )
        object.__setattr__(
            self,
            "projection_basis",
            owned_readonly_array(basis, dtype=np.float64),
        )
        object.__setattr__(self, "labels", labels)
        object.__setattr__(self, "rank", rank)

    @property
    def projector(self) -> FloatArray:
        """Return the read-only 3x3 orthogonal projector onto the subspace."""

        return owned_readonly_array(
            self.projection_basis.T @ self.projection_basis,
            dtype=np.float64,
        )

    @property
    def component_label(self) -> str:
        """Return the legacy result label for this subspace."""

        if self.labels is not None and len(self.labels) == 1:
            return self.labels[0]
        return "scalar"

    def same_physical_subspace(self, other: AnalysisSubspace) -> bool:
        """Compare projectors so basis rotations and sign flips remain equivalent."""

        if not isinstance(other, AnalysisSubspace) or self.rank != other.rank:
            return False
        return bool(
            np.allclose(
                self.projection_basis.T @ self.projection_basis,
                other.projection_basis.T @ other.projection_basis,
                rtol=_ORTHONORMAL_RTOL,
                atol=_ORTHONORMAL_ATOL,
            )
        )


def resolve_analysis_subspace(
    *,
    axes: Sequence[AxisLabel] | None = None,
    projection_basis: ArrayLike | None = None,
) -> AnalysisSubspace:
    """Resolve one explicit orthonormal analysis subspace.

    With neither argument, the full Cartesian 3D basis is used.  Axis subsets
    preserve their user-supplied order.  General bases must have orthonormal
    rows and are represented without axis labels.
    """

    if axes is not None and projection_basis is not None:
        raise ValueError("Specify at most one of axes and projection_basis.")
    if axes is None and projection_basis is None:
        labels: tuple[AxisLabel, ...] = ("x", "y", "z")
        return AnalysisSubspace(np.eye(3, dtype=np.float64), labels, 3)
    if axes is not None:
        if isinstance(axes, str):
            raise TypeError("axes must be a sequence of axis labels, not a string.")
        labels = tuple(axes)
        if not labels:
            raise ValueError("axes must not be empty.")
        if len(labels) > 3:
            raise ValueError("axes may contain at most three labels.")
        if any(not isinstance(label, str) for label in labels):
            raise TypeError("Every axes entry must be 'x', 'y', or 'z'.")
        if any(label not in _AXIS_INDEX for label in labels):
            raise ValueError("Every axes entry must be 'x', 'y', or 'z'.")
        if len(set(labels)) != len(labels):
            raise ValueError("axes must not contain duplicates.")
        typed_labels = tuple(labels)  # type: ignore[assignment]
        basis = np.eye(3, dtype=np.float64)[
            [_AXIS_INDEX[label] for label in typed_labels]
        ]
        return AnalysisSubspace(basis, typed_labels, len(typed_labels))

    basis = np.asarray(projection_basis, dtype=np.float64)
    if basis.ndim == 1:
        basis = basis.reshape(1, -1)
    return AnalysisSubspace(basis, None, int(basis.shape[0]))


def resolve_subspace_with_legacy_options(
    *,
    axes: Sequence[AxisLabel] | None,
    projection_basis: ArrayLike | None,
    component: str,
    dimensions: object | None,
) -> AnalysisSubspace:
    """Resolve H0 subspace semantics while retaining unambiguous legacy calls."""

    if component not in ("scalar", "x", "y", "z"):
        raise ValueError("component must be 'scalar', 'x', 'y', or 'z'.")
    explicit_subspace = axes is not None or projection_basis is not None
    if explicit_subspace and component != "scalar":
        raise ValueError(
            "component cannot be combined with axes or projection_basis; use the "
            "explicit subspace alone."
        )
    if explicit_subspace:
        subspace = resolve_analysis_subspace(
            axes=axes,
            projection_basis=projection_basis,
        )
    elif component == "scalar":
        subspace = resolve_analysis_subspace()
    else:
        subspace = resolve_analysis_subspace(axes=(component,))  # type: ignore[arg-type]

    if dimensions is not None:
        if isinstance(dimensions, (bool, np.bool_)) or not isinstance(
            dimensions, (int, np.integer)
        ):
            raise TypeError("dimensions must be an integer or None.")
        legacy_dimensions = int(dimensions)
        if legacy_dimensions not in (1, 2, 3):
            raise ValueError("dimensions must be 1, 2, or 3.")
        if not explicit_subspace and component == "scalar" and legacy_dimensions != 3:
            raise ValueError(
                "dimensions=1 or 2 cannot reinterpret the full 3D scalar result; "
                "supply axes or projection_basis explicitly."
            )
        if legacy_dimensions != subspace.rank:
            raise ValueError(
                "dimensions is inconsistent with the resolved analysis subspace."
            )
    return subspace


def project_trace_from_result(
    *,
    components: ArrayLike,
    tensor: ArrayLike | None,
    subspace: AnalysisSubspace,
    tensor_name: str,
) -> FloatArray:
    """Project a stored Cartesian/tensor correlation or second moment."""

    component_values = np.asarray(components, dtype=np.float64)
    if component_values.ndim < 1 or component_values.shape[-1] != 3:
        raise ValueError("components must end in a Cartesian axis of length three.")
    if subspace.labels is not None:
        indices = [_AXIS_INDEX[label] for label in subspace.labels]
        return np.asarray(np.sum(component_values[..., indices], axis=-1), dtype=np.float64)
    if tensor is None:
        raise ValueError(
            f"A rotated projection requires the full {tensor_name}; it was not stored."
        )
    tensor_values = np.asarray(tensor, dtype=np.float64)
    if tensor_values.shape[-2:] != (3, 3):
        raise ValueError(f"{tensor_name} must end in shape (3, 3).")
    projected = np.einsum(
        "ai,...ij,aj->...",
        subspace.projection_basis,
        tensor_values,
        subspace.projection_basis,
        optimize=True,
    )
    return np.asarray(projected, dtype=np.float64)


def _update_digest_with_array(
    digest: hashlib._Hash,
    label: str,
    value: ArrayLike | None,
) -> None:
    digest.update(label.encode("utf-8"))
    digest.update(b"\0")
    if value is None:
        digest.update(b"<none>")
        return
    array = np.asarray(value)
    # Canonical little-endian bytes make the identity stable across host byte
    # order while preserving the normalized dtype and exact stored values.
    canonical_dtype = array.dtype.newbyteorder("<")
    canonical = np.ascontiguousarray(array.astype(canonical_dtype, copy=False))
    digest.update(canonical.dtype.str.encode("ascii"))
    digest.update(repr(canonical.shape).encode("ascii"))
    digest.update(memoryview(canonical).cast("B"))


def trajectory_fingerprint(collection: AtomisticFrameCollection) -> str:
    """Digest the analyzed frame sequence and identity-bearing trajectory data."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    digest = hashlib.sha256()
    digest.update(b"mdstats.dynamics.trajectory.v2\0")
    _update_digest_with_array(digest, "frame_ids", collection.frame_ids)
    _update_digest_with_array(digest, "steps", collection.steps)
    _update_digest_with_array(digest, "times", collection.times)
    _update_digest_with_array(digest, "atomic_numbers", collection.atomic_numbers)
    _update_digest_with_array(digest, "masses", collection.masses)
    _update_digest_with_array(digest, "pbc", collection.pbc)
    _update_digest_with_array(digest, "cells", collection.cells)
    _update_digest_with_array(digest, "origins", collection.origins)
    _update_digest_with_array(
        digest,
        "fractional_positions",
        collection.fractional_positions,
    )
    _update_digest_with_array(digest, "velocities", collection.velocities)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class DynamicsInputSignature:
    """Deeply immutable physical-input identity shared by dynamics results."""

    source_format: str | None
    source_files: tuple[str, ...]
    trajectory_fingerprint: str

    frame_indices: tuple[int, ...] | None
    frame_times_ps: FloatArray
    n_frames: int
    sample_spacing_ps: float | None

    atom_indices: IntArray
    coordinate_mode: str
    reference_cell_mode: str | None
    reference_cell: FloatArray | None

    drift_mode: str | None
    drift_atom_indices: IntArray | None
    velocity_source: str | None

    projection_basis: FloatArray
    projection_labels: tuple[AxisLabel, ...] | None

    def __post_init__(self) -> None:
        if self.source_format is not None and (
            not isinstance(self.source_format, str) or not self.source_format
        ):
            raise ValueError("source_format must be a nonempty string or None.")
        if isinstance(self.source_files, (str, bytes)):
            raise TypeError("source_files must be a sequence of path strings.")
        source_files = tuple(self.source_files)
        if any(not isinstance(value, str) or not value for value in source_files):
            raise ValueError("source_files entries must be nonempty strings.")
        if not isinstance(self.trajectory_fingerprint, str) or not self.trajectory_fingerprint:
            raise ValueError("trajectory_fingerprint must be a nonempty string.")
        if isinstance(self.n_frames, (bool, np.bool_)) or not isinstance(
            self.n_frames, (int, np.integer)
        ):
            raise TypeError("n_frames must be an integer.")
        n_frames = int(self.n_frames)
        if n_frames < 1:
            raise ValueError("n_frames must be positive.")
        for name in ("coordinate_mode",):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a nonempty string.")
        for name in ("reference_cell_mode", "drift_mode", "velocity_source"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ValueError(f"{name} must be a nonempty string or None.")
        times = np.asarray(self.frame_times_ps, dtype=np.float64)
        atoms = np.asarray(self.atom_indices, dtype=np.int64)
        basis = np.asarray(self.projection_basis, dtype=np.float64)
        if times.shape != (n_frames,):
            raise ValueError("frame_times_ps is inconsistent with n_frames.")
        if not np.all(np.isfinite(times)):
            raise ValueError("frame_times_ps must contain only finite values.")
        if n_frames > 1 and np.any(np.diff(times) <= 0.0):
            raise ValueError("frame_times_ps must be strictly increasing.")
        if atoms.ndim != 1 or atoms.size < 1:
            raise ValueError("atom_indices must be a nonempty one-dimensional array.")
        if np.any(atoms < 0):
            raise ValueError("atom_indices must be nonnegative.")
        if np.unique(atoms).size != atoms.size:
            raise ValueError("atom_indices must not contain duplicates.")
        subspace = AnalysisSubspace(
            basis,
            None if self.projection_labels is None else tuple(self.projection_labels),
            int(basis.shape[0]),
        )
        if self.frame_indices is not None:
            raw_indices = tuple(self.frame_indices)
            if any(
                isinstance(value, (bool, np.bool_))
                or not isinstance(value, (int, np.integer))
                for value in raw_indices
            ):
                raise TypeError("frame_indices entries must be integers.")
            indices = tuple(int(value) for value in raw_indices)
            if len(indices) != n_frames:
                raise ValueError("frame_indices is inconsistent with n_frames.")
            if any(value < 0 for value in indices):
                raise ValueError("frame_indices must be nonnegative.")
        else:
            indices = None
        spacing = None if self.sample_spacing_ps is None else float(self.sample_spacing_ps)
        if spacing is not None and (not np.isfinite(spacing) or spacing <= 0.0):
            raise ValueError("sample_spacing_ps must be finite and positive or None.")
        if n_frames == 1 and spacing is not None:
            raise ValueError("sample_spacing_ps must be None for one frame.")
        if n_frames > 1 and spacing is not None:
            increments = np.diff(times)
            if not np.allclose(increments, spacing, rtol=1.0e-10, atol=1.0e-14):
                raise ValueError("sample_spacing_ps is inconsistent with frame_times_ps.")
        reference = (
            None
            if self.reference_cell is None
            else np.asarray(self.reference_cell, dtype=np.float64)
        )
        if reference is not None:
            if reference.shape != (3, 3) or not np.all(np.isfinite(reference)):
                raise ValueError("reference_cell must be a finite 3x3 matrix or None.")
        drift_atoms = (
            None
            if self.drift_atom_indices is None
            else np.asarray(self.drift_atom_indices, dtype=np.int64)
        )
        if drift_atoms is not None:
            if drift_atoms.ndim != 1 or drift_atoms.size < 1:
                raise ValueError(
                    "drift_atom_indices must be a nonempty one-dimensional array or None."
                )
            if np.any(drift_atoms < 0) or np.unique(drift_atoms).size != drift_atoms.size:
                raise ValueError("drift_atom_indices must be unique and nonnegative.")
        if (self.drift_mode is None) != (drift_atoms is None):
            raise ValueError(
                "drift_mode and drift_atom_indices must either both be set or both be None."
            )
        if (self.reference_cell_mode is None) != (reference is None):
            raise ValueError(
                "reference_cell_mode and reference_cell must either both be set or both be None."
            )

        object.__setattr__(self, "source_files", source_files)
        object.__setattr__(self, "frame_indices", indices)
        object.__setattr__(self, "frame_times_ps", owned_readonly_array(times, dtype=np.float64))
        object.__setattr__(self, "n_frames", n_frames)
        object.__setattr__(self, "sample_spacing_ps", spacing)
        object.__setattr__(self, "atom_indices", owned_readonly_array(atoms, dtype=np.int64))
        object.__setattr__(
            self,
            "reference_cell",
            None if reference is None else owned_readonly_array(reference, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "drift_atom_indices",
            None if drift_atoms is None else owned_readonly_array(drift_atoms, dtype=np.int64),
        )
        object.__setattr__(
            self,
            "projection_basis",
            subspace.projection_basis,
        )
        object.__setattr__(self, "projection_labels", subspace.labels)

    @property
    def subspace(self) -> AnalysisSubspace:
        return AnalysisSubspace(
            self.projection_basis,
            self.projection_labels,
            int(self.projection_basis.shape[0]),
        )

    def with_subspace(self, subspace: AnalysisSubspace) -> DynamicsInputSignature:
        """Return the same source identity under a resolved observable subspace."""

        return DynamicsInputSignature(
            source_format=self.source_format,
            source_files=self.source_files,
            trajectory_fingerprint=self.trajectory_fingerprint,
            frame_indices=self.frame_indices,
            frame_times_ps=self.frame_times_ps,
            n_frames=self.n_frames,
            sample_spacing_ps=self.sample_spacing_ps,
            atom_indices=self.atom_indices,
            coordinate_mode=self.coordinate_mode,
            reference_cell_mode=self.reference_cell_mode,
            reference_cell=self.reference_cell,
            drift_mode=self.drift_mode,
            drift_atom_indices=self.drift_atom_indices,
            velocity_source=self.velocity_source,
            projection_basis=subspace.projection_basis,
            projection_labels=subspace.labels,
        )

    def mismatch_fields(self, other: DynamicsInputSignature) -> tuple[str, ...]:
        """Return semantic fields that differ, comparing physical projectors."""

        if not isinstance(other, DynamicsInputSignature):
            return ("signature_type",)
        mismatches: list[str] = []
        scalar_fields = (
            "source_format",
            "source_files",
            "trajectory_fingerprint",
            "frame_indices",
            "n_frames",
            "sample_spacing_ps",
            "coordinate_mode",
            "reference_cell_mode",
            "drift_mode",
            "velocity_source",
        )
        for name in scalar_fields:
            if getattr(self, name) != getattr(other, name):
                mismatches.append(name)
        array_fields = (
            "frame_times_ps",
            "atom_indices",
            "reference_cell",
            "drift_atom_indices",
        )
        for name in array_fields:
            left = getattr(self, name)
            right = getattr(other, name)
            if left is None or right is None:
                if left is not right:
                    mismatches.append(name)
            elif not np.array_equal(left, right):
                mismatches.append(name)
        if not self.subspace.same_physical_subspace(other.subspace):
            mismatches.append("projection_subspace")
        return tuple(mismatches)

    def is_compatible_with(self, other: DynamicsInputSignature) -> bool:
        return not self.mismatch_fields(other)


def build_dynamics_signature(
    collection: AtomisticFrameCollection,
    *,
    atom_indices: ArrayLike,
    coordinate_mode: str,
    reference_cell_mode: str | None,
    reference_cell: ArrayLike | None,
    drift_mode: str | None,
    drift_atom_indices: ArrayLike | None,
    velocity_source: str | None,
    subspace: AnalysisSubspace | None = None,
) -> DynamicsInputSignature:
    """Construct one complete signature from a normalized frame collection."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection instance.")
    resolved_subspace = resolve_analysis_subspace() if subspace is None else subspace
    provenance = collection.provenance
    times = collection.require_time_axis("Dynamics input signature")
    spacing: float | None
    if times.size < 2:
        spacing = None
    else:
        increments = np.diff(times)
        spacing = (
            float(increments[0])
            if np.allclose(increments, increments[0], rtol=1.0e-10, atol=1.0e-14)
            else None
        )
    return DynamicsInputSignature(
        source_format=None if provenance is None else provenance.source_format,
        source_files=() if provenance is None else tuple(provenance.source_files),
        trajectory_fingerprint=trajectory_fingerprint(collection),
        frame_indices=tuple(int(value) for value in collection.frame_ids),
        frame_times_ps=times,
        n_frames=collection.n_frames,
        sample_spacing_ps=spacing,
        atom_indices=np.asarray(atom_indices, dtype=np.int64),
        coordinate_mode=str(coordinate_mode),
        reference_cell_mode=reference_cell_mode,
        reference_cell=reference_cell,
        drift_mode=drift_mode,
        drift_atom_indices=drift_atom_indices,
        velocity_source=velocity_source,
        projection_basis=resolved_subspace.projection_basis,
        projection_labels=resolved_subspace.labels,
    )
