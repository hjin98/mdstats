"""Stage-C0B compatibility adapters for analysis and plotting consumers.

This module owns the translation from legacy consumer options into the shared
Stage-C0 coordinate-registration foundation.  It intentionally does not define
new estimators.  Compatibility corrections are explicit, immutable, and
source-bound so scientific drift removal is no longer implemented inside
plotting or duplicated across dynamical analyses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from ..collection import AtomisticFrameCollection
from .contracts import ReferenceCellDefinition
from .periodic_gauge import (
    LatticeBasisContinuityError,
    LatticeGaugeOptions,
    prepare_source_coordinate_contract,
)
from .registration import (
    FrameRegistrationPolicy,
    FrameRegistrationResult,
    ReferenceWeighting,
    RegistrationSpatialPolicy,
    TranslationMode,
    prepare_frame_registration,
)

CONSUMER_COORDINATE_VIEW_SCHEMA = "mdstats.consumer-coordinate-view.v1"
VELOCITY_TRANSLATION_VIEW_SCHEMA = "mdstats.velocity-translation-view.v1"
CONSUMER_ADAPTER_DIGEST_ALGORITHM = "sha256-canonical-json-and-array-bytes-v1"


class ConsumerRegistrationError(ValueError):
    """Raised when a legacy consumer cannot be mapped to a shared registration."""


class ConsumerSpatialMode(str, Enum):
    """Legacy plotting spatial modes admitted by the C0B adapter."""

    MATERIAL = "material"
    FRAMEWORK_REGISTERED = "framework_registered"
    LABORATORY = "laboratory"


class ConsumerTranslationConvention(str, Enum):
    """Explicit compatibility translation applied after the C0 affine map."""

    NONE = "none"
    ZERO_CENTER = "zero_center"
    REFERENCE_CENTER_DELTA = "reference_center_delta"
    VELOCITY_CENTER = "velocity_center"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _readonly(
    value: object,
    *,
    dtype: Any,
    shape_suffix: tuple[int, ...],
    name: str,
) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if shape_suffix and (
        array.ndim < len(shape_suffix)
        or tuple(array.shape[-len(shape_suffix):]) != shape_suffix
    ):
        raise ConsumerRegistrationError(
            f"{name} must end with shape {shape_suffix}; received {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and not np.all(np.isfinite(array)):
        raise ConsumerRegistrationError(f"{name} contains non-finite values.")
    array.setflags(write=False)
    return array


def _indices(
    value: Sequence[int] | np.ndarray,
    *,
    n_atoms: int,
    name: str,
) -> tuple[int, ...]:
    result = tuple(int(item) for item in value)
    if not result:
        raise ConsumerRegistrationError(f"{name} must not be empty.")
    if len(set(result)) != len(result) or min(result) < 0 or max(result) >= n_atoms:
        raise ConsumerRegistrationError(
            f"{name} must contain unique atom indices inside the collection."
        )
    return result


def _weights(
    collection: AtomisticFrameCollection,
    atom_indices: tuple[int, ...],
    *,
    mode: str,
) -> tuple[np.ndarray, ReferenceWeighting]:
    if mode == "center_of_geometry":
        values = np.ones(len(atom_indices), dtype=np.float64)
        return values, ReferenceWeighting.CENTER_OF_GEOMETRY
    if mode == "center_of_mass":
        values = np.asarray(collection.masses[list(atom_indices)], dtype=np.float64)
        if not np.all(np.isfinite(values)) or float(np.sum(values)) <= 0.0:
            raise ConsumerRegistrationError(
                "The center-of-mass reference has invalid total mass."
            )
        return values, ReferenceWeighting.CENTER_OF_MASS
    raise ConsumerRegistrationError(
        "translation mode must be center_of_geometry or center_of_mass."
    )


def _consumer_source_contract(
    collection: AtomisticFrameCollection,
    *,
    reference_cell: ReferenceCellDefinition | None,
):
    """Build a source contract while preserving legacy continuous-cell support.

    C0A1's conservative default continuity threshold remains authoritative for
    new scientific APIs.  Legacy MSD/plotting consumers historically admitted
    larger smooth cell deformations, so C0B retries only non-integer-like cell
    changes with an explicit data-derived continuity envelope.  Certifiable
    unimodular relabelings are never hidden by this compatibility path.
    """

    try:
        return prepare_source_coordinate_contract(
            collection, reference_cell=reference_cell
        )
    except LatticeBasisContinuityError:
        cells = np.asarray(collection.cells, dtype=np.float64)
        comparisons = [
            index - 1 if collection.is_trajectory else 0
            for index in range(1, collection.n_frames)
        ]
        direct_changes: list[float] = []
        for frame_index, comparison_index in enumerate(comparisons, start=1):
            previous = cells[comparison_index]
            current = cells[frame_index]
            scale = max(float(np.linalg.norm(previous)), np.finfo(np.float64).tiny)
            direct_changes.append(float(np.linalg.norm(current - previous) / scale))
            candidate_real = previous @ np.linalg.inv(current)
            candidate = np.rint(candidate_real).astype(np.int64)
            candidate_scale = max(float(np.linalg.norm(candidate_real)), 1.0)
            integer_residual = float(
                np.linalg.norm(candidate_real - candidate) / candidate_scale
            )
            determinant = int(round(float(np.linalg.det(candidate))))
            reconciled = candidate @ current
            reconciled_change = float(np.linalg.norm(reconciled - previous) / scale)
            if (
                abs(determinant) == 1
                and integer_residual <= 5.0e-2
                and reconciled_change <= 5.0e-2
            ):
                raise
        tolerance = max(0.25, max(direct_changes, default=0.25) * (1.0 + 1.0e-10))
        return prepare_source_coordinate_contract(
            collection,
            reference_cell=reference_cell,
            lattice_options=LatticeGaugeOptions(
                continuity_relative_tolerance=tolerance,
            ),
        )

def _weighted_centers(positions: np.ndarray, weights: np.ndarray) -> np.ndarray:
    total = float(np.sum(weights))
    return np.einsum("tni,n->ti", positions, weights, optimize=True) / total


def _consumer_round_trip_tolerance(
    collection: AtomisticFrameCollection,
) -> float:
    """Return an absolute validation tolerance that resolves source-coordinate ULPs.

    Legacy displacement tests intentionally admit very large absolute unwrapped
    positions with small increments.  Reconstructing such positions from wrapped
    fractions cannot be certified below their floating-point spacing.  The C0B
    policy therefore records a conservative eight-ULP absolute floor while
    retaining C0A2's 1e-10 default for ordinary coordinates.
    """

    positions = np.asarray(collection.get_positions(), dtype=np.float64)
    scale = float(np.max(np.abs(positions))) if positions.size else 0.0
    ulp = float(np.spacing(scale)) if scale > 0.0 else 0.0
    return max(1.0e-10, 8.0 * ulp)


@dataclass(frozen=True, slots=True)
class ConsumerCoordinateView:
    """One immutable consumer coordinate product backed by C0A2 registration.

    ``registration`` owns the affine source-to-target map.  The separate
    ``translation_corrections`` array records the exact legacy-compatible
    translation convention.  This separation is deliberate: translations do
    not alter pair vectors, while their ownership and provenance remain
    explicit and inspectable.
    """

    registration: FrameRegistrationResult
    frame_indices: np.ndarray
    translation_corrections: np.ndarray
    positions: np.ndarray
    display_cell: np.ndarray | None
    spatial_mode: str
    translation_convention: ConsumerTranslationConvention
    reference_atom_indices: tuple[int, ...]
    reference_weighting: str | None
    metadata: Mapping[str, Any]
    signature: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.registration, FrameRegistrationResult):
            raise TypeError("registration must be a FrameRegistrationResult.")
        frames = _readonly(
            self.frame_indices, dtype=np.int64, shape_suffix=(), name="frame_indices"
        )
        if frames.ndim != 1 or frames.size < 1:
            raise ConsumerRegistrationError("frame_indices must be a nonempty vector.")
        if np.any(frames < 0) or np.any(frames >= self.registration.registered_cells.shape[0]):
            raise ConsumerRegistrationError("frame_indices are outside the registration.")
        if np.unique(frames).size != frames.size:
            raise ConsumerRegistrationError("frame_indices must be unique.")
        corrections = _readonly(
            self.translation_corrections,
            dtype=np.float64,
            shape_suffix=(3,),
            name="translation_corrections",
        )
        positions = _readonly(
            self.positions, dtype=np.float64, shape_suffix=(3,), name="positions"
        )
        if corrections.shape != (frames.size, 3):
            raise ConsumerRegistrationError(
                "translation_corrections must have shape (selected_frames, 3)."
            )
        if positions.shape != (
            frames.size,
            self.registration.registered_unwrapped_cartesian.shape[1],
            3,
        ):
            raise ConsumerRegistrationError(
                "positions are inconsistent with selected frames and source atoms."
            )
        expected = None
        if (
            str(self.spatial_mode) == ConsumerSpatialMode.LABORATORY.value
            or self.registration.policy.spatial_policy
            is RegistrationSpatialPolicy.REFERENCE_MATERIAL
        ):
            expected = (
                self.registration.registered_unwrapped_cartesian[frames]
                + corrections[:, None, :]
            )
        if expected is not None and not np.array_equal(positions, expected) and not np.allclose(
            positions, expected, rtol=0.0, atol=2.0e-12
        ):
            raise ConsumerRegistrationError(
                "positions are inconsistent with registration plus translation correction."
            )
        cell = None
        if self.display_cell is not None:
            cell = _readonly(
                self.display_cell,
                dtype=np.float64,
                shape_suffix=(3, 3),
                name="display_cell",
            )
            if (
                cell.shape != (3, 3)
                or abs(float(np.linalg.det(cell))) <= 1.0e-12
            ):
                raise ConsumerRegistrationError(
                    "display_cell must be a nonsingular 3x3 matrix."
                )
        try:
            convention = ConsumerTranslationConvention(self.translation_convention)
        except ValueError as exc:
            raise ConsumerRegistrationError("Unsupported translation convention.") from exc
        refs = tuple(int(item) for item in self.reference_atom_indices)
        if refs and (
            min(refs) < 0
            or max(refs) >= positions.shape[1]
            or len(set(refs)) != len(refs)
        ):
            raise ConsumerRegistrationError("reference_atom_indices are invalid.")
        metadata = dict(self.metadata)
        payload = {
            "schema": CONSUMER_COORDINATE_VIEW_SCHEMA,
            "digest_algorithm": CONSUMER_ADAPTER_DIGEST_ALGORITHM,
            "registration_signature": self.registration.signature,
            "frame_indices_digest": _array_digest(frames),
            "translation_corrections_digest": _array_digest(corrections),
            "positions_digest": _array_digest(positions),
            "display_cell_digest": None if cell is None else _array_digest(cell),
            "spatial_mode": str(self.spatial_mode),
            "translation_convention": convention.value,
            "reference_atom_indices": list(refs),
            "reference_weighting": self.reference_weighting,
            "metadata": metadata,
        }
        expected_signature = _digest(payload)
        if self.signature and self.signature != expected_signature:
            raise ConsumerRegistrationError(
                "Consumer-coordinate signature is inconsistent."
            )
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "translation_corrections", corrections)
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "display_cell", cell)
        object.__setattr__(self, "translation_convention", convention)
        object.__setattr__(self, "reference_atom_indices", refs)
        object.__setattr__(self, "metadata", MappingProxyType(metadata))
        object.__setattr__(self, "signature", expected_signature)

    def _local_frame_positions(self, frame_indices: Sequence[int]) -> np.ndarray:
        lookup = {int(frame): local for local, frame in enumerate(self.frame_indices)}
        try:
            local = np.asarray(
                [lookup[int(frame)] for frame in frame_indices], dtype=np.int64
            )
        except KeyError as exc:
            raise ConsumerRegistrationError(
                "Requested frame is outside this consumer coordinate view."
            ) from exc
        return local

    def atom_positions(
        self,
        *,
        frame_indices: Sequence[int] | None = None,
        atom_indices: Sequence[int] | None = None,
    ) -> np.ndarray:
        frames = (
            tuple(int(v) for v in self.frame_indices)
            if frame_indices is None
            else tuple(int(v) for v in frame_indices)
        )
        local = self._local_frame_positions(frames)
        if atom_indices is None:
            atoms = np.arange(self.positions.shape[1], dtype=np.int64)
        else:
            atoms = np.asarray(tuple(int(v) for v in atom_indices), dtype=np.int64)
            if (
                atoms.ndim != 1
                or np.any(atoms < 0)
                or np.any(atoms >= self.positions.shape[1])
            ):
                raise ConsumerRegistrationError(
                    "atom_indices are outside the source collection."
                )
        return np.asarray(self.positions[np.ix_(local, atoms)], dtype=np.float64)

    def display_fractional(
        self,
        *,
        frame_indices: Sequence[int] | None = None,
        atom_indices: Sequence[int] | None = None,
    ) -> np.ndarray:
        if self.display_cell is None:
            raise ConsumerRegistrationError("This view has no display-cell contract.")
        return self.atom_positions(
            frame_indices=frame_indices, atom_indices=atom_indices
        ) @ np.linalg.inv(self.display_cell)

    def transform_fractional(
        self,
        fractional_by_frame: object,
        *,
        frame_indices: Sequence[int],
        output: str = "cartesian",
    ) -> np.ndarray:
        values = np.asarray(fractional_by_frame, dtype=np.float64)
        frames = tuple(int(v) for v in frame_indices)
        if (
            values.ndim != 3
            or values.shape[0] != len(frames)
            or values.shape[2] != 3
        ):
            raise ConsumerRegistrationError(
                "fractional_by_frame must have shape (selected_frames, items, 3)."
            )
        local = self._local_frame_positions(frames)
        if str(self.spatial_mode) in {
            ConsumerSpatialMode.MATERIAL.value,
            ConsumerSpatialMode.FRAMEWORK_REGISTERED.value,
        }:
            if self.display_cell is None:
                raise ConsumerRegistrationError("Material views require a display cell.")
            transformed = values @ self.display_cell
        else:
            # Recover source Cartesian coordinates from G = H M, then apply
            # the authoritative C0 affine map.
            selected_frames = np.asarray(frames, dtype=np.int64)
            affine = self.registration.affine_matrices[selected_frames]
            registered_cells = self.registration.registered_cells[selected_frames]
            source_cell = np.einsum(
                "tij,tjk->tik", registered_cells, np.linalg.inv(affine), optimize=True
            )
            source_cartesian = np.einsum(
                "tni,tij->tnj", values, source_cell, optimize=True
            )
            transformed = np.einsum(
                "tni,tij->tnj", source_cartesian, affine, optimize=True
            )
            transformed += self.registration.affine_translations[
                selected_frames, None, :
            ]
        transformed += self.translation_corrections[local, None, :]
        if output == "cartesian":
            return transformed
        if output == "display_fractional":
            if self.display_cell is None:
                raise ConsumerRegistrationError("This view has no display-cell contract.")
            return transformed @ np.linalg.inv(self.display_cell)
        raise ConsumerRegistrationError("output must be cartesian or display_fractional.")

    def transform_lattice_shifts(
        self,
        shifts: object,
        *,
        frame_indices: Sequence[int],
    ) -> np.ndarray:
        if self.display_cell is None:
            raise ConsumerRegistrationError("This view has no display-cell contract.")
        values = np.asarray(shifts, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != 3:
            raise ConsumerRegistrationError("shifts must have shape (items, 3).")
        frames = np.asarray(tuple(int(v) for v in frame_indices), dtype=np.int64)
        self._local_frame_positions(frames)
        if str(self.spatial_mode) in {
            ConsumerSpatialMode.MATERIAL.value,
            ConsumerSpatialMode.FRAMEWORK_REGISTERED.value,
        }:
            return np.broadcast_to(
                values[None, :, :], (len(frames), values.shape[0], 3)
            ).copy()
        affine = self.registration.affine_matrices[frames]
        registered_cells = self.registration.registered_cells[frames]
        source_cell = np.einsum(
            "tij,tjk->tik", registered_cells, np.linalg.inv(affine), optimize=True
        )
        source_vectors = np.einsum("ei,tij->tej", values, source_cell, optimize=True)
        transformed = np.einsum("tei,tij->tej", source_vectors, affine, optimize=True)
        return transformed @ np.linalg.inv(self.display_cell)


@dataclass(frozen=True, slots=True)
class VelocityTranslationView:
    """Translation-only velocity correction preserving legacy VACF semantics."""

    policy: FrameRegistrationPolicy
    atom_indices: tuple[int, ...]
    drift_mode: str | None
    drift_velocity: np.ndarray | None
    correction_velocity: np.ndarray
    signature: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.policy, FrameRegistrationPolicy):
            raise TypeError("policy must be a FrameRegistrationPolicy.")
        atoms = tuple(int(v) for v in self.atom_indices)
        correction = _readonly(
            self.correction_velocity,
            dtype=np.float64,
            shape_suffix=(3,),
            name="correction_velocity",
        )
        drift = None
        if self.drift_velocity is not None:
            drift = _readonly(
                self.drift_velocity,
                dtype=np.float64,
                shape_suffix=(3,),
                name="drift_velocity",
            )
            if drift.shape != correction.shape:
                raise ConsumerRegistrationError(
                    "drift_velocity and correction_velocity shapes disagree."
                )
            if not np.allclose(correction, -drift, rtol=0.0, atol=0.0):
                raise ConsumerRegistrationError(
                    "Velocity correction must be the negative drift velocity."
                )
        elif np.any(correction != 0.0):
            raise ConsumerRegistrationError(
                "A view without drift_velocity must have zero correction."
            )
        payload = {
            "schema": VELOCITY_TRANSLATION_VIEW_SCHEMA,
            "digest_algorithm": CONSUMER_ADAPTER_DIGEST_ALGORITHM,
            "policy_signature": self.policy.signature,
            "atom_indices": list(atoms),
            "drift_mode": self.drift_mode,
            "drift_velocity_digest": None if drift is None else _array_digest(drift),
            "correction_velocity_digest": _array_digest(correction),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ConsumerRegistrationError("Velocity-translation signature is inconsistent.")
        object.__setattr__(self, "atom_indices", atoms)
        object.__setattr__(self, "drift_velocity", drift)
        object.__setattr__(self, "correction_velocity", correction)
        object.__setattr__(self, "signature", expected)


def prepare_displacement_coordinate_view(
    collection: AtomisticFrameCollection,
    *,
    coordinate_mode: str,
    reference_cell: np.ndarray | None,
    reference_cell_mode: str | None,
    drift_mode: str | None,
    drift_atom_indices: Sequence[int] | np.ndarray | None,
) -> ConsumerCoordinateView:
    """Map legacy MSD coordinate options into one shared coordinate view."""

    if coordinate_mode not in {"laboratory", "reference_cell"}:
        raise ConsumerRegistrationError(
            "coordinate_mode must be laboratory or reference_cell."
        )
    reference_definition = None
    spatial = RegistrationSpatialPolicy.PHYSICAL
    if coordinate_mode == "reference_cell":
        if reference_cell is None or reference_cell_mode is None:
            raise ConsumerRegistrationError(
                "reference_cell coordinates require a resolved reference cell."
            )
        reference_definition = ReferenceCellDefinition.explicit_matrix(
            reference_cell, periodic_axes=collection.pbc
        )
        spatial = RegistrationSpatialPolicy.REFERENCE_MATERIAL
    elif reference_cell is not None or reference_cell_mode is not None:
        raise ConsumerRegistrationError(
            "laboratory coordinates must not carry a reference cell."
        )

    policy = FrameRegistrationPolicy(
        spatial_policy=spatial,
        translation_mode=TranslationMode.NONE,
        round_trip_tolerance=_consumer_round_trip_tolerance(collection),
    )
    source_contract = _consumer_source_contract(
        collection, reference_cell=reference_definition
    )
    registration = prepare_frame_registration(
        collection,
        policy=policy,
        source_contract=source_contract,
    )
    corrections = np.zeros((collection.n_frames, 3), dtype=np.float64)
    refs: tuple[int, ...] = ()
    weighting_name: str | None = None
    convention = ConsumerTranslationConvention.NONE
    if drift_mode is not None:
        if drift_atom_indices is None:
            raise ConsumerRegistrationError(
                "drift_atom_indices are required when drift_mode is set."
            )
        refs = _indices(
            drift_atom_indices, n_atoms=collection.n_atoms, name="drift_atom_indices"
        )
        values, _weighting = _weights(collection, refs, mode=drift_mode)
        centers = _weighted_centers(
            registration.registered_unwrapped_cartesian[:, list(refs), :], values
        )
        corrections = -centers
        weighting_name = drift_mode
        convention = ConsumerTranslationConvention.ZERO_CENTER
    positions = registration.registered_unwrapped_cartesian + corrections[:, None, :]
    return ConsumerCoordinateView(
        registration=registration,
        frame_indices=np.arange(collection.n_frames, dtype=np.int64),
        translation_corrections=corrections,
        positions=positions,
        display_cell=None,
        spatial_mode=coordinate_mode,
        translation_convention=convention,
        reference_atom_indices=refs,
        reference_weighting=weighting_name,
        metadata={
            "consumer": "displacement",
            "coordinate_mode": coordinate_mode,
            "reference_cell_mode": reference_cell_mode,
            "legacy_regression_contract": "exact_coordinate_preparation_v1",
            "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
        },
    )


def prepare_plotting_coordinate_view(
    collection: AtomisticFrameCollection,
    *,
    frame_indices: Sequence[int],
    display_cell: object,
    spatial_mode: ConsumerSpatialMode | str,
    framework_atom_indices: Sequence[int],
    framework_fractional_by_frame: object,
) -> ConsumerCoordinateView:
    """Prepare the shared scientific coordinate view used by plotting consumers."""

    try:
        mode = ConsumerSpatialMode(spatial_mode)
    except ValueError as exc:
        raise ConsumerRegistrationError(
            "spatial_mode must be material, framework_registered, or laboratory."
        ) from exc
    frames = tuple(int(v) for v in frame_indices)
    if not frames or len(set(frames)) != len(frames):
        raise ConsumerRegistrationError("frame_indices must be nonempty and unique.")
    if min(frames) < 0 or max(frames) >= collection.n_frames:
        raise ConsumerRegistrationError("frame_indices are outside the collection.")
    cell = np.asarray(display_cell, dtype=np.float64)
    if (
        cell.shape != (3, 3)
        or not np.all(np.isfinite(cell))
        or abs(float(np.linalg.det(cell))) <= 1.0e-12
    ):
        raise ConsumerRegistrationError(
            "display_cell must be a finite nonsingular 3x3 matrix."
        )

    full_periodicity = bool(np.all(collection.pbc))
    if mode is ConsumerSpatialMode.LABORATORY or not full_periodicity:
        spatial = RegistrationSpatialPolicy.PHYSICAL
        reference_definition = None
    else:
        spatial = RegistrationSpatialPolicy.REFERENCE_MATERIAL
        reference_definition = ReferenceCellDefinition.explicit_matrix(
            cell, periodic_axes=collection.pbc
        )
    source_contract = _consumer_source_contract(
        collection, reference_cell=reference_definition
    )
    registration = prepare_frame_registration(
        collection,
        policy=FrameRegistrationPolicy(
            spatial_policy=spatial,
            translation_mode=TranslationMode.NONE,
            round_trip_tolerance=_consumer_round_trip_tolerance(collection),
        ),
        source_contract=source_contract,
    )
    corrections = np.zeros((len(frames), 3), dtype=np.float64)
    refs: tuple[int, ...] = ()
    convention = ConsumerTranslationConvention.NONE
    if mode is ConsumerSpatialMode.FRAMEWORK_REGISTERED:
        refs = _indices(
            framework_atom_indices,
            n_atoms=collection.n_atoms,
            name="framework_atom_indices",
        )
        fractional = np.asarray(framework_fractional_by_frame, dtype=np.float64)
        if fractional.shape != (len(frames), len(refs), 3):
            raise ConsumerRegistrationError(
                "framework_fractional_by_frame must match frames and framework atoms."
            )
        centroids = np.mean(fractional, axis=1)
        fractional_correction = -(centroids - centroids[0])
        corrections = fractional_correction @ cell
        convention = ConsumerTranslationConvention.REFERENCE_CENTER_DELTA

    if mode is ConsumerSpatialMode.LABORATORY:
        selected_base = registration.registered_unwrapped_cartesian[
            np.asarray(frames, dtype=np.int64)
        ]
    else:
        selected_fractional = np.asarray(
            collection.fractional_positions[np.asarray(frames, dtype=np.int64)],
            dtype=np.float64,
        )
        selected_base = selected_fractional @ cell
    positions = selected_base + corrections[:, None, :]
    return ConsumerCoordinateView(
        registration=registration,
        frame_indices=np.asarray(frames, dtype=np.int64),
        translation_corrections=corrections,
        positions=positions,
        display_cell=cell,
        spatial_mode=mode.value,
        translation_convention=convention,
        reference_atom_indices=refs,
        reference_weighting=(
            "center_of_geometry" if refs else None
        ),
        metadata={
            "consumer": "plotting",
            "legacy_regression_contract": "framework_dynamics_v1",
            "scientific_drift_owner": "mdstats.coordinates.consumer_adapters",
            "pair_geometry_policy": "physical",
        },
    )


def prepare_velocity_translation_view(
    collection: AtomisticFrameCollection,
    *,
    velocities: object,
    drift_mode: str | None,
    drift_atom_indices: Sequence[int] | np.ndarray | None,
) -> VelocityTranslationView:
    """Prepare an exact translation-only correction for velocity consumers."""

    values = np.asarray(velocities, dtype=np.float64)
    if values.shape != (collection.n_frames, collection.n_atoms, 3):
        raise ConsumerRegistrationError(
            "velocities must match the collection's (frames, atoms, 3) shape."
        )
    if not np.all(np.isfinite(values)):
        raise ConsumerRegistrationError("velocities contain non-finite values.")
    if drift_mode is None:
        if drift_atom_indices is not None:
            raise ConsumerRegistrationError(
                "drift_atom_indices require a drift_mode."
            )
        policy = FrameRegistrationPolicy()
        return VelocityTranslationView(
            policy=policy,
            atom_indices=(),
            drift_mode=None,
            drift_velocity=None,
            correction_velocity=np.zeros((collection.n_frames, 3), dtype=np.float64),
        )
    if drift_atom_indices is None:
        raise ConsumerRegistrationError(
            "drift_atom_indices are required when drift_mode is set."
        )
    refs = _indices(
        drift_atom_indices, n_atoms=collection.n_atoms, name="drift_atom_indices"
    )
    weights, weighting = _weights(collection, refs, mode=drift_mode)
    drift = _weighted_centers(values[:, list(refs), :], weights)
    policy = FrameRegistrationPolicy(
        spatial_policy=RegistrationSpatialPolicy.PHYSICAL,
        translation_mode=TranslationMode.MATCHED_REFERENCE,
        reference_atom_indices=refs,
        reference_weighting=weighting,
    )
    return VelocityTranslationView(
        policy=policy,
        atom_indices=refs,
        drift_mode=drift_mode,
        drift_velocity=drift,
        correction_velocity=-drift,
    )


__all__ = [
    "CONSUMER_ADAPTER_DIGEST_ALGORITHM",
    "CONSUMER_COORDINATE_VIEW_SCHEMA",
    "VELOCITY_TRANSLATION_VIEW_SCHEMA",
    "ConsumerCoordinateView",
    "ConsumerRegistrationError",
    "ConsumerSpatialMode",
    "ConsumerTranslationConvention",
    "VelocityTranslationView",
    "prepare_displacement_coordinate_view",
    "prepare_plotting_coordinate_view",
    "prepare_velocity_translation_view",
]
