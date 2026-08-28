"""V7 canonical numerical-label and frame identity (unreachable scaffolding).

Canonical label identity binds the training payload and the semantic/unit/
convention information required to interpret it. Advisory compatibility-group
assignment is not hashed into the payload or labeled-configuration identity.
Precise electronic-structure provenance is referenced separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..identity import (
    DuplicateDetectionCatalog,
    FrameIdentity,
    GeometryFingerprintPolicy,
    LabelFingerprintPolicy,
    _quantize_label,
    build_duplicate_detection_catalog,
    frame_uid,
    geometry_fingerprint,
    labeled_configuration_fingerprint,
    source_occurrence_signature,
)

CANONICAL_TRAINING_LABEL_PAYLOAD_SCHEMA = "mdstats.v7-canonical-training-label-payload.v1"
V7_FRAME_IDENTITY_SCHEMA = "mdstats.v7-frame-identity.v1"
V7_FRAME_IDENTITY_CATALOG_SCHEMA = "mdstats.v7-frame-identity-catalog.v1"


def canonical_training_label_payload_digest(
    *,
    selected_energy_channel: str,
    energy_semantic_role: str,
    energy_units: str,
    energy_normalization: str,
    entropy_convention: str,
    energy_ev: float | None,
    forces_ev_per_angstrom: ArrayLike | None,
    stress_ev_per_angstrom3: ArrayLike | None,
    derivative_convention_digest: str,
    policy: LabelFingerprintPolicy | None = None,
) -> str:
    """Digest canonical numerical labels plus interpretation, without grouping."""

    active = LabelFingerprintPolicy() if policy is None else policy
    for name, value in (
        ("selected_energy_channel", selected_energy_channel),
        ("energy_semantic_role", energy_semantic_role),
        ("energy_units", energy_units),
        ("energy_normalization", energy_normalization),
        ("entropy_convention", entropy_convention),
    ):
        if not str(value).strip():
            raise TrainingDataInputError(
                f"{name} is required to canonicalize numerical training labels."
            )
    convention = validate_digest(
        derivative_convention_digest, name="derivative_convention_digest"
    )
    payload: dict[str, Any] = {
        "schema": CANONICAL_TRAINING_LABEL_PAYLOAD_SCHEMA,
        "policy_digest": active.policy_digest,
        "selected_energy_channel": str(selected_energy_channel),
        "energy_semantic_role": str(energy_semantic_role),
        "energy_units": str(energy_units),
        "energy_normalization": str(energy_normalization),
        "entropy_convention": str(entropy_convention),
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


@dataclass(frozen=True, slots=True)
class V7FrameIdentity:
    """Occurrence, geometry, canonical labels, and separate provenance reference."""

    frame_uid: str
    run_id: str
    source_frame_index: int
    geometry_fingerprint: str
    canonical_label_payload_digest: str
    labeled_configuration_fingerprint: str
    electronic_structure_fingerprint_digest: str

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise TrainingDataInputError("run_id must be non-empty.")
        if isinstance(self.source_frame_index, bool) or int(self.source_frame_index) < 0:
            raise TrainingDataInputError("source_frame_index must be nonnegative.")
        object.__setattr__(self, "source_frame_index", int(self.source_frame_index))
        for name in (
            "frame_uid",
            "geometry_fingerprint",
            "canonical_label_payload_digest",
            "labeled_configuration_fingerprint",
            "electronic_structure_fingerprint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))

    @property
    def label_payload_digest(self) -> str:
        """Alias used by geometry/labeled duplicate grouping."""

        return self.canonical_label_payload_digest

    def as_duplicate_frame_identity(self) -> FrameIdentity:
        return FrameIdentity(
            frame_uid=self.frame_uid,
            geometry_fingerprint=self.geometry_fingerprint,
            label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_FRAME_IDENTITY_SCHEMA,
            "frame_uid": self.frame_uid,
            "run_id": self.run_id,
            "source_frame_index": self.source_frame_index,
            "geometry_fingerprint": self.geometry_fingerprint,
            "canonical_label_payload_digest": self.canonical_label_payload_digest,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
            "electronic_structure_fingerprint_digest": self.electronic_structure_fingerprint_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7FrameIdentity":
        if payload.get("schema") != V7_FRAME_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 frame-identity schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            run_id=str(payload["run_id"]),
            source_frame_index=int(payload["source_frame_index"]),
            geometry_fingerprint=str(payload["geometry_fingerprint"]),
            canonical_label_payload_digest=str(payload["canonical_label_payload_digest"]),
            labeled_configuration_fingerprint=str(
                payload["labeled_configuration_fingerprint"]
            ),
            electronic_structure_fingerprint_digest=str(
                payload["electronic_structure_fingerprint_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 frame-identity digest mismatch.")
        return result


def build_v7_frame_identity(
    *,
    run_id: str,
    source_locator: str,
    source_identity_signature: str,
    source_frame_index: int,
    atomic_numbers: ArrayLike,
    pbc: ArrayLike,
    cell: ArrayLike,
    fractional_positions: ArrayLike,
    selected_energy_channel: str,
    energy_semantic_role: str,
    energy_units: str,
    energy_normalization: str,
    entropy_convention: str,
    energy_ev: float | None,
    forces_ev_per_angstrom: ArrayLike | None,
    stress_ev_per_angstrom3: ArrayLike | None,
    derivative_convention_digest: str,
    electronic_structure_fingerprint_digest: str,
    geometry_policy: GeometryFingerprintPolicy | None = None,
    label_policy: LabelFingerprintPolicy | None = None,
) -> V7FrameIdentity:
    occurrence = source_occurrence_signature(
        run_id=run_id,
        source_locator=source_locator,
        source_identity_signature=source_identity_signature,
    )
    uid = frame_uid(occurrence, source_frame_index)
    geometry = geometry_fingerprint(
        atomic_numbers,
        pbc,
        cell,
        fractional_positions,
        policy=geometry_policy,
    )
    labels = canonical_training_label_payload_digest(
        selected_energy_channel=selected_energy_channel,
        energy_semantic_role=energy_semantic_role,
        energy_units=energy_units,
        energy_normalization=energy_normalization,
        entropy_convention=entropy_convention,
        energy_ev=energy_ev,
        forces_ev_per_angstrom=forces_ev_per_angstrom,
        stress_ev_per_angstrom3=stress_ev_per_angstrom3,
        derivative_convention_digest=derivative_convention_digest,
        policy=label_policy,
    )
    return V7FrameIdentity(
        frame_uid=uid,
        run_id=run_id,
        source_frame_index=int(source_frame_index),
        geometry_fingerprint=geometry,
        canonical_label_payload_digest=labels,
        labeled_configuration_fingerprint=labeled_configuration_fingerprint(
            geometry, labels
        ),
        electronic_structure_fingerprint_digest=validate_digest(
            electronic_structure_fingerprint_digest,
            name="electronic_structure_fingerprint_digest",
        ),
    )


@dataclass(frozen=True, slots=True)
class V7FrameIdentityCatalog:
    identities: tuple[V7FrameIdentity, ...]
    duplicates: DuplicateDetectionCatalog

    def __post_init__(self) -> None:
        ordered = tuple(
            sorted(self.identities, key=lambda item: (item.run_id, item.source_frame_index))
        )
        if len({item.frame_uid for item in ordered}) != len(ordered):
            raise TrainingDataInputError("V7 frame identities require unique frame UIDs.")
        object.__setattr__(self, "identities", ordered)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_FRAME_IDENTITY_CATALOG_SCHEMA,
            "identities": [item.to_dict() for item in self.identities],
            "duplicates": self.duplicates.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7FrameIdentityCatalog":
        if payload.get("schema") != V7_FRAME_IDENTITY_CATALOG_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported V7 frame-identity-catalog schema."
            )
        result = cls(
            identities=tuple(V7FrameIdentity.from_dict(item) for item in payload["identities"]),
            duplicates=DuplicateDetectionCatalog.from_dict(payload["duplicates"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "V7 frame-identity-catalog digest mismatch."
            )
        return result


def build_v7_frame_identity_catalog(
    identities: Sequence[V7FrameIdentity],
    *,
    source_frame_counts: Mapping[str, int],
) -> V7FrameIdentityCatalog:
    records = tuple(identities)
    duplicates = build_duplicate_detection_catalog(
        records, source_frame_counts=source_frame_counts
    )
    return V7FrameIdentityCatalog(identities=records, duplicates=duplicates)
