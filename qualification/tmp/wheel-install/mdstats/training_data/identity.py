"""Frame-occurrence, geometry, and label identities for MLFF-DATA3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

GEOMETRY_FINGERPRINT_POLICY_SCHEMA = "mdstats.geometry-fingerprint-policy.v1"
LABEL_FINGERPRINT_POLICY_SCHEMA = "mdstats.label-fingerprint-policy.v1"
FRAME_IDENTITY_SCHEMA = "mdstats.training-frame-identity.v1"
DUPLICATE_GEOMETRY_GROUP_SCHEMA = "mdstats.duplicate-geometry-group.v1"
DUPLICATE_LABELED_GROUP_SCHEMA = "mdstats.duplicate-labeled-group.v1"
DUPLICATE_DETECTION_CATALOG_SCHEMA = "mdstats.duplicate-detection-catalog.v1"

GEOMETRY_FINGERPRINT_POLICY_VERSION = "mdstats.mlff-data3.geometry-fingerprint.2026-07.v1"
LABEL_FINGERPRINT_POLICY_VERSION = "mdstats.mlff-data3.label-fingerprint.2026-07.v1"

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def _positive_tolerance(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TrainingDataInputError(f"{name} must be finite and positive.")
    return result


def _quantize(array: ArrayLike, tolerance: float, *, name: str) -> list[Any]:
    values = np.asarray(array, dtype=np.float64)
    if np.any(~np.isfinite(values)):
        raise TrainingDataInputError(f"{name} contains non-finite values.")
    scaled = np.rint(values / tolerance)
    limit = np.iinfo(np.int64).max
    if np.any(np.abs(scaled) > limit):
        raise TrainingDataInputError(
            f"{name} cannot be quantized safely with tolerance {tolerance:g}."
        )
    return scaled.astype(np.int64).tolist()


def _quantize_label(array: ArrayLike, tolerance: float) -> Any:
    values = np.asarray(array, dtype=np.float64)
    result = np.empty(values.shape, dtype=object)
    finite = np.isfinite(values)
    scaled = np.rint(values[finite] / tolerance)
    limit = np.iinfo(np.int64).max
    if np.any(np.abs(scaled) > limit):
        raise TrainingDataInputError("Label cannot be quantized safely.")
    result[finite] = scaled.astype(np.int64)
    result[np.isnan(values)] = "nan"
    result[np.isposinf(values)] = "+inf"
    result[np.isneginf(values)] = "-inf"
    return result.tolist()




def source_occurrence_signature(
    *,
    run_id: str,
    source_locator: str,
    source_identity_signature: str,
) -> str:
    """Bind a content-derived source identity to one manifest occurrence."""

    if not run_id.strip() or not source_locator.strip():
        raise TrainingDataInputError("run_id and source_locator must be non-empty.")
    return digest(
        {
            "schema": "mdstats.source-occurrence-signature.v1",
            "run_id": run_id,
            "source_locator": source_locator,
            "source_identity_signature": validate_digest(
                source_identity_signature, name="source_identity_signature"
            ),
        }
    )

def frame_uid(source_occurrence_signature: str, source_frame_index: int) -> str:
    """Return the stable occurrence identity for one source frame."""

    source = validate_digest(
        source_occurrence_signature, name="source_occurrence_signature"
    )
    if isinstance(source_frame_index, bool) or int(source_frame_index) < 0:
        raise TrainingDataInputError("source_frame_index must be nonnegative.")
    return digest(
        {
            "schema": "mdstats.frame-uid.v1",
            "source_occurrence_signature": source,
            "source_frame_index": int(source_frame_index),
        }
    )


@dataclass(frozen=True, slots=True)
class GeometryFingerprintPolicy:
    cell_tolerance_angstrom: float = 1.0e-8
    fractional_tolerance: float = 1.0e-8
    wrap_tolerance: float = 1.0e-10
    preserve_atom_order: bool = True
    preserve_cell_basis: bool = True
    policy_version: str = GEOMETRY_FINGERPRINT_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cell_tolerance_angstrom",
            _positive_tolerance(
                self.cell_tolerance_angstrom, name="cell_tolerance_angstrom"
            ),
        )
        object.__setattr__(
            self,
            "fractional_tolerance",
            _positive_tolerance(
                self.fractional_tolerance, name="fractional_tolerance"
            ),
        )
        wrap = float(self.wrap_tolerance)
        if not np.isfinite(wrap) or wrap < 0.0 or wrap >= 0.5:
            raise TrainingDataInputError("wrap_tolerance must lie in [0, 0.5).")
        object.__setattr__(self, "wrap_tolerance", wrap)
        if not self.preserve_atom_order or not self.preserve_cell_basis:
            raise TrainingDataInputError(
                "DATA3 exact fingerprints preserve atom order and cell basis."
            )
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": GEOMETRY_FINGERPRINT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "cell_tolerance_angstrom": self.cell_tolerance_angstrom,
            "fractional_tolerance": self.fractional_tolerance,
            "wrap_tolerance": self.wrap_tolerance,
            "preserve_atom_order": self.preserve_atom_order,
            "preserve_cell_basis": self.preserve_cell_basis,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryFingerprintPolicy":
        if payload.get("schema") != GEOMETRY_FINGERPRINT_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported geometry-fingerprint policy schema."
            )
        result = cls(
            cell_tolerance_angstrom=float(payload["cell_tolerance_angstrom"]),
            fractional_tolerance=float(payload["fractional_tolerance"]),
            wrap_tolerance=float(payload["wrap_tolerance"]),
            preserve_atom_order=bool(payload["preserve_atom_order"]),
            preserve_cell_basis=bool(payload["preserve_cell_basis"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError(
                "Geometry-fingerprint policy digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class LabelFingerprintPolicy:
    energy_tolerance_ev: float = 1.0e-10
    force_tolerance_ev_per_angstrom: float = 1.0e-10
    stress_tolerance_ev_per_angstrom3: float = 1.0e-12
    policy_version: str = LABEL_FINGERPRINT_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "energy_tolerance_ev",
            "force_tolerance_ev_per_angstrom",
            "stress_tolerance_ev_per_angstrom3",
        ):
            object.__setattr__(
                self, name, _positive_tolerance(getattr(self, name), name=name)
            )
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LABEL_FINGERPRINT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "energy_tolerance_ev": self.energy_tolerance_ev,
            "force_tolerance_ev_per_angstrom": self.force_tolerance_ev_per_angstrom,
            "stress_tolerance_ev_per_angstrom3": self.stress_tolerance_ev_per_angstrom3,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LabelFingerprintPolicy":
        if payload.get("schema") != LABEL_FINGERPRINT_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported label-fingerprint policy schema."
            )
        result = cls(
            energy_tolerance_ev=float(payload["energy_tolerance_ev"]),
            force_tolerance_ev_per_angstrom=float(
                payload["force_tolerance_ev_per_angstrom"]
            ),
            stress_tolerance_ev_per_angstrom3=float(
                payload["stress_tolerance_ev_per_angstrom3"]
            ),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError(
                "Label-fingerprint policy digest mismatch."
            )
        return result


def canonical_wrapped_fractional_positions(
    fractional_positions: ArrayLike,
    pbc: ArrayLike,
    *,
    wrap_tolerance: float,
) -> FloatArray:
    fractional = np.asarray(fractional_positions, dtype=np.float64)
    periodic = np.asarray(pbc, dtype=np.bool_)
    if fractional.ndim != 2 or fractional.shape[1] != 3:
        raise TrainingDataInputError(
            "fractional_positions must have shape (n_atoms, 3)."
        )
    if periodic.shape != (3,):
        raise TrainingDataInputError("pbc must have shape (3,).")
    if np.any(~np.isfinite(fractional)):
        raise TrainingDataInputError(
            "fractional_positions contains non-finite values."
        )
    result = np.array(fractional, copy=True)
    for axis, is_periodic in enumerate(periodic):
        if not is_periodic:
            continue
        result[:, axis] -= np.floor(result[:, axis])
        near_upper = result[:, axis] >= 1.0 - wrap_tolerance
        near_lower = np.abs(result[:, axis]) <= wrap_tolerance
        result[near_upper | near_lower, axis] = 0.0
    result[result == 0.0] = 0.0
    result.setflags(write=False)
    return result


def geometry_fingerprint(
    atomic_numbers: ArrayLike,
    pbc: ArrayLike,
    cell: ArrayLike,
    fractional_positions: ArrayLike,
    *,
    policy: GeometryFingerprintPolicy | None = None,
) -> str:
    """Return the first-release exact geometry fingerprint."""

    active = GeometryFingerprintPolicy() if policy is None else policy
    numbers = np.asarray(atomic_numbers, dtype=np.int64)
    periodic = np.asarray(pbc, dtype=np.bool_)
    cell_array = np.asarray(cell, dtype=np.float64)
    if numbers.ndim != 1 or numbers.size == 0 or np.any(numbers <= 0):
        raise TrainingDataInputError(
            "atomic_numbers must be a non-empty positive integer vector."
        )
    if periodic.shape != (3,):
        raise TrainingDataInputError("pbc must have shape (3,).")
    if cell_array.shape != (3, 3) or np.any(~np.isfinite(cell_array)):
        raise TrainingDataInputError("cell must be a finite 3 x 3 matrix.")
    wrapped = canonical_wrapped_fractional_positions(
        fractional_positions, periodic, wrap_tolerance=active.wrap_tolerance
    )
    if wrapped.shape[0] != numbers.size:
        raise TrainingDataInputError(
            "Atomic-number and fractional-position counts do not match."
        )
    payload = {
        "schema": "mdstats.geometry-fingerprint.v1",
        "policy_digest": active.policy_digest,
        "atomic_numbers": numbers.tolist(),
        "pbc": periodic.astype(np.int8).tolist(),
        "cell_quantized": _quantize(
            cell_array, active.cell_tolerance_angstrom, name="cell"
        ),
        "fractional_quantized": _quantize(
            wrapped, active.fractional_tolerance, name="fractional_positions"
        ),
    }
    return digest(payload)


def label_payload_digest(
    *,
    label_domain_id: str,
    selected_energy_channel: str,
    energy_ev: float | None,
    forces_ev_per_angstrom: ArrayLike | None,
    stress_ev_per_angstrom3: ArrayLike | None,
    derivative_convention_digest: str,
    policy: LabelFingerprintPolicy | None = None,
) -> str:
    active = LabelFingerprintPolicy() if policy is None else policy
    if not label_domain_id.strip() or not selected_energy_channel.strip():
        raise TrainingDataInputError(
            "label_domain_id and selected_energy_channel must be non-empty."
        )
    convention = validate_digest(
        derivative_convention_digest, name="derivative_convention_digest"
    )
    payload: dict[str, Any] = {
        "schema": "mdstats.label-payload-digest.v1",
        "policy_digest": active.policy_digest,
        "label_domain_id": label_domain_id,
        "selected_energy_channel": selected_energy_channel,
        "derivative_convention_digest": convention,
        "energy_quantized": (
            None
            if energy_ev is None
            else _quantize_label(
                np.asarray([float(energy_ev)]),
                active.energy_tolerance_ev,
            )[0]
        ),
        "forces_quantized": None,
        "stress_quantized": None,
    }
    if forces_ev_per_angstrom is not None:
        forces = np.asarray(forces_ev_per_angstrom, dtype=np.float64)
        if forces.ndim != 2 or forces.shape[1] != 3:
            raise TrainingDataInputError("forces must have shape (n_atoms, 3).")
        payload["forces_quantized"] = _quantize_label(
            forces, active.force_tolerance_ev_per_angstrom
        )
    if stress_ev_per_angstrom3 is not None:
        stress = np.asarray(stress_ev_per_angstrom3, dtype=np.float64)
        if stress.shape != (3, 3):
            raise TrainingDataInputError("stress must have shape (3, 3).")
        payload["stress_quantized"] = _quantize_label(
            stress, active.stress_tolerance_ev_per_angstrom3
        )
    return digest(payload)


def labeled_configuration_fingerprint(
    geometry_digest: str, label_digest: str
) -> str:
    return digest(
        {
            "schema": "mdstats.labeled-configuration-fingerprint.v1",
            "geometry_fingerprint": validate_digest(
                geometry_digest, name="geometry_fingerprint"
            ),
            "label_payload_digest": validate_digest(
                label_digest, name="label_payload_digest"
            ),
        }
    )


@dataclass(frozen=True, slots=True)
class FrameIdentity:
    frame_uid: str
    geometry_fingerprint: str
    label_payload_digest: str
    labeled_configuration_fingerprint: str

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "geometry_fingerprint",
            "label_payload_digest",
            "labeled_configuration_fingerprint",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_IDENTITY_SCHEMA,
            "frame_uid": self.frame_uid,
            "geometry_fingerprint": self.geometry_fingerprint,
            "label_payload_digest": self.label_payload_digest,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameIdentity":
        if payload.get("schema") != FRAME_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-identity schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            geometry_fingerprint=str(payload["geometry_fingerprint"]),
            label_payload_digest=str(payload["label_payload_digest"]),
            labeled_configuration_fingerprint=str(
                payload["labeled_configuration_fingerprint"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Frame-identity digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DuplicateGeometryGroup:
    geometry_fingerprint: str
    frame_uids: tuple[str, ...]
    run_ids: tuple[str, ...]
    cross_source: bool
    restart_boundary_pattern: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "geometry_fingerprint",
            validate_digest(
                self.geometry_fingerprint, name="geometry_fingerprint"
            ),
        )
        uids = tuple(sorted(validate_digest(v, name="frame_uid") for v in self.frame_uids))
        if len(uids) < 2 or len(set(uids)) != len(uids):
            raise TrainingDataInputError(
                "Duplicate geometry groups require at least two unique frame UIDs."
            )
        object.__setattr__(self, "frame_uids", uids)
        runs = tuple(sorted(str(v) for v in self.run_ids))
        object.__setattr__(self, "run_ids", runs)
        if self.cross_source != (len(set(runs)) > 1):
            raise TrainingDataInputError("cross_source is inconsistent with run_ids.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DUPLICATE_GEOMETRY_GROUP_SCHEMA,
            "geometry_fingerprint": self.geometry_fingerprint,
            "frame_uids": list(self.frame_uids),
            "run_ids": list(self.run_ids),
            "cross_source": self.cross_source,
            "restart_boundary_pattern": self.restart_boundary_pattern,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DuplicateGeometryGroup":
        if payload.get("schema") != DUPLICATE_GEOMETRY_GROUP_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported duplicate-geometry-group schema."
            )
        result = cls(
            geometry_fingerprint=str(payload["geometry_fingerprint"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            run_ids=tuple(str(v) for v in payload["run_ids"]),
            cross_source=bool(payload["cross_source"]),
            restart_boundary_pattern=bool(payload["restart_boundary_pattern"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Duplicate-geometry-group digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class DuplicateLabeledGroup:
    labeled_configuration_fingerprint: str
    frame_uids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "labeled_configuration_fingerprint",
            validate_digest(
                self.labeled_configuration_fingerprint,
                name="labeled_configuration_fingerprint",
            ),
        )
        uids = tuple(sorted(validate_digest(v, name="frame_uid") for v in self.frame_uids))
        if len(uids) < 2 or len(set(uids)) != len(uids):
            raise TrainingDataInputError(
                "Duplicate labeled groups require at least two unique frame UIDs."
            )
        object.__setattr__(self, "frame_uids", uids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DUPLICATE_LABELED_GROUP_SCHEMA,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
            "frame_uids": list(self.frame_uids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DuplicateLabeledGroup":
        if payload.get("schema") != DUPLICATE_LABELED_GROUP_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported duplicate-labeled-group schema."
            )
        result = cls(
            labeled_configuration_fingerprint=str(
                payload["labeled_configuration_fingerprint"]
            ),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Duplicate-labeled-group digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class DuplicateDetectionCatalog:
    geometry_groups: tuple[DuplicateGeometryGroup, ...]
    labeled_groups: tuple[DuplicateLabeledGroup, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "geometry_groups",
            tuple(sorted(self.geometry_groups, key=lambda item: item.geometry_fingerprint)),
        )
        object.__setattr__(
            self,
            "labeled_groups",
            tuple(
                sorted(
                    self.labeled_groups,
                    key=lambda item: item.labeled_configuration_fingerprint,
                )
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DUPLICATE_DETECTION_CATALOG_SCHEMA,
            "geometry_groups": [item.to_dict() for item in self.geometry_groups],
            "labeled_groups": [item.to_dict() for item in self.labeled_groups],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DuplicateDetectionCatalog":
        if payload.get("schema") != DUPLICATE_DETECTION_CATALOG_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported duplicate-detection-catalog schema."
            )
        result = cls(
            geometry_groups=tuple(
                DuplicateGeometryGroup.from_dict(item)
                for item in payload.get("geometry_groups", ())
            ),
            labeled_groups=tuple(
                DuplicateLabeledGroup.from_dict(item)
                for item in payload.get("labeled_groups", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Duplicate-detection-catalog digest mismatch."
            )
        return result


def build_duplicate_detection_catalog(
    records: Sequence[Any], *, source_frame_counts: Mapping[str, int]
) -> DuplicateDetectionCatalog:
    """Group exact geometry and labeled-configuration duplicates.

    Records must expose ``frame_uid``, ``run_id``, ``source_frame_index``,
    ``geometry_fingerprint``, and ``labeled_configuration_fingerprint``.
    """

    geometry: dict[str, list[Any]] = {}
    labeled: dict[str, list[Any]] = {}
    for record in records:
        geometry.setdefault(record.geometry_fingerprint, []).append(record)
        labeled.setdefault(record.labeled_configuration_fingerprint, []).append(record)

    geometry_groups: list[DuplicateGeometryGroup] = []
    for fingerprint, group in geometry.items():
        if len(group) < 2:
            continue
        runs = tuple(sorted({item.run_id for item in group}))
        first_runs = {
            item.run_id for item in group if int(item.source_frame_index) == 0
        }
        final_runs = {
            item.run_id
            for item in group
            if int(item.source_frame_index)
            == int(source_frame_counts[item.run_id]) - 1
        }
        # A restart boundary exists when both endpoint sets are populated and
        # they are not the same singleton run.  The former Cartesian-product
        # predicate was O(R**2) for a large duplicate group.
        restart = bool(
            first_runs
            and final_runs
            and len(first_runs | final_runs) > 1
        )
        geometry_groups.append(
            DuplicateGeometryGroup(
                geometry_fingerprint=fingerprint,
                frame_uids=tuple(item.frame_uid for item in group),
                run_ids=runs,
                cross_source=len(set(runs)) > 1,
                restart_boundary_pattern=restart,
            )
        )

    labeled_groups = [
        DuplicateLabeledGroup(
            labeled_configuration_fingerprint=fingerprint,
            frame_uids=tuple(item.frame_uid for item in group),
        )
        for fingerprint, group in labeled.items()
        if len(group) >= 2
    ]
    return DuplicateDetectionCatalog(
        geometry_groups=tuple(geometry_groups), labeled_groups=tuple(labeled_groups)
    )
