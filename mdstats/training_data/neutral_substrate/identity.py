"""Canonical numerical-label and frame identity without compatibility domains.

Canonical label identity binds the training payload and the semantic/unit/
convention information required to interpret it. Advisory compatibility-group
assignment is not hashed into the payload or labeled-configuration identity.
Precise electronic-structure provenance is referenced separately. Non-finite
numerical labels (NaN, +inf, -inf) are rejected.
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
from ..eligibility import (
    FrameEligibilityPolicy,
    StressRequirement,
    evaluate_required_label_contract,
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

CANONICAL_TRAINING_LABEL_PAYLOAD_SCHEMA = "mdstats.canonical-training-label-payload.v1"
CANONICAL_FRAME_IDENTITY_SCHEMA = "mdstats.canonical-frame-identity.v1"


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
    if energy_ev is not None:
        val = float(energy_ev)
        if not np.isfinite(val):
            raise TrainingDataInputError("energy_ev must be finite.")
        energy_quantized = _quantize_label(
            np.asarray([val]),
            active.energy_tolerance_ev,
        )[0]
    else:
        energy_quantized = None

    payload: dict[str, Any] = {
        "schema": CANONICAL_TRAINING_LABEL_PAYLOAD_SCHEMA,
        "policy_digest": active.policy_digest,
        "selected_energy_channel": str(selected_energy_channel),
        "energy_semantic_role": str(energy_semantic_role),
        "energy_units": str(energy_units),
        "energy_normalization": str(energy_normalization),
        "entropy_convention": str(entropy_convention),
        "derivative_convention_digest": convention,
        "energy_quantized": energy_quantized,
        "forces_quantized": None,
        "stress_quantized": None,
    }
    if forces_ev_per_angstrom is not None:
        forces = np.asarray(forces_ev_per_angstrom, dtype=np.float64)
        if forces.ndim != 2 or forces.shape[1] != 3:
            raise TrainingDataInputError("forces must have shape (n_atoms, 3).")
        if not np.all(np.isfinite(forces)):
            raise TrainingDataInputError("forces must contain only finite values.")
        payload["forces_quantized"] = _quantize_label(
            forces, active.force_tolerance_ev_per_angstrom
        )
    if stress_ev_per_angstrom3 is not None:
        stress = np.asarray(stress_ev_per_angstrom3, dtype=np.float64)
        if stress.shape != (3, 3):
            raise TrainingDataInputError("stress must have shape (3, 3).")
        if not np.all(np.isfinite(stress)):
            raise TrainingDataInputError("stress must contain only finite values.")
        payload["stress_quantized"] = _quantize_label(
            stress, active.stress_tolerance_ev_per_angstrom3
        )
    return digest(payload)


from ..eligibility import FrameEligibilityPolicy, StressRequirement


@dataclass(frozen=True, slots=True)
class CanonicalFrameIdentity:
    """Occurrence, geometry, canonical labels, and separate provenance reference."""

    frame_uid: str
    run_id: str
    source_frame_index: int
    geometry_fingerprint: str
    canonical_label_payload_digest: str | None = None
    labeled_configuration_fingerprint: str | None = None
    electronic_structure_fingerprint_digest: str = ""

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise TrainingDataInputError("run_id must be non-empty.")
        if isinstance(self.source_frame_index, bool) or int(self.source_frame_index) < 0:
            raise TrainingDataInputError("source_frame_index must be nonnegative.")
        object.__setattr__(self, "source_frame_index", int(self.source_frame_index))
        for name in (
            "frame_uid",
            "geometry_fingerprint",
            "electronic_structure_fingerprint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "canonical_label_payload_digest",
            "labeled_configuration_fingerprint",
        ):
            val = getattr(self, name)
            if val is not None:
                object.__setattr__(self, name, validate_digest(val, name=name))

        if (self.canonical_label_payload_digest is None) != (self.labeled_configuration_fingerprint is None):
            raise TrainingDataInputError(
                "canonical_label_payload_digest and labeled_configuration_fingerprint must be either both present or both None."
            )
        if self.canonical_label_payload_digest is not None:
            expected_fingerprint = labeled_configuration_fingerprint(
                self.geometry_fingerprint, self.canonical_label_payload_digest
            )
            if self.labeled_configuration_fingerprint != expected_fingerprint:
                raise TrainingDataInputError(
                    f"labeled_configuration_fingerprint mismatch: expected {expected_fingerprint}, got {self.labeled_configuration_fingerprint}"
                )

    @property
    def has_authoritative_label(self) -> bool:
        return self.canonical_label_payload_digest is not None

    @property
    def label_payload_digest(self) -> str | None:
        """Alias used by geometry/labeled duplicate grouping."""

        return self.canonical_label_payload_digest

    def as_duplicate_frame_identity(self) -> FrameIdentity:
        if self.canonical_label_payload_digest is None or self.labeled_configuration_fingerprint is None:
            raise TrainingDataInputError("Cannot construct FrameIdentity without authoritative label identity.")
        return FrameIdentity(
            frame_uid=self.frame_uid,
            geometry_fingerprint=self.geometry_fingerprint,
            label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CANONICAL_FRAME_IDENTITY_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalFrameIdentity":
        if payload.get("schema") != CANONICAL_FRAME_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported canonical frame-identity schema.")
        label_digest = (
            None
            if payload.get("canonical_label_payload_digest") is None
            else str(payload["canonical_label_payload_digest"])
        )
        labeled_fingerprint = (
            None
            if payload.get("labeled_configuration_fingerprint") is None
            else str(payload["labeled_configuration_fingerprint"])
        )
        geom_fingerprint = str(payload["geometry_fingerprint"])
        if (label_digest is None) != (labeled_fingerprint is None):
            raise TrainingDataSerializationError(
                "canonical_label_payload_digest and labeled_configuration_fingerprint must be either both present or both None."
            )
        if label_digest is not None:
            expected = labeled_configuration_fingerprint(geom_fingerprint, label_digest)
            if labeled_fingerprint != expected:
                raise TrainingDataSerializationError(
                    f"labeled_configuration_fingerprint mismatch: expected {expected}, got {labeled_fingerprint}"
                )

        result = cls(
            frame_uid=str(payload["frame_uid"]),
            run_id=str(payload["run_id"]),
            source_frame_index=int(payload["source_frame_index"]),
            geometry_fingerprint=geom_fingerprint,
            canonical_label_payload_digest=label_digest,
            labeled_configuration_fingerprint=labeled_fingerprint,
            electronic_structure_fingerprint_digest=str(
                payload["electronic_structure_fingerprint_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Canonical frame-identity digest mismatch.")
        return result


def build_canonical_frame_identity(
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
    eligibility_policy: FrameEligibilityPolicy | None = None,
) -> CanonicalFrameIdentity:
    eligibility_active = (
        FrameEligibilityPolicy() if eligibility_policy is None else eligibility_policy
    )
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

    n_atoms = len(np.asarray(atomic_numbers))
    label_eval = evaluate_required_label_contract(
        atom_count=n_atoms,
        energy_ev=energy_ev,
        forces_ev_per_angstrom=forces_ev_per_angstrom,
        stress_ev_per_angstrom3=stress_ev_per_angstrom3,
        policy=eligibility_active,
    )

    if label_eval.is_satisfied:
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
        labeled_fingerprint = labeled_configuration_fingerprint(geometry, labels)
    else:
        labels = None
        labeled_fingerprint = None

    return CanonicalFrameIdentity(
        frame_uid=uid,
        run_id=run_id,
        source_frame_index=int(source_frame_index),
        geometry_fingerprint=geometry,
        canonical_label_payload_digest=labels,
        labeled_configuration_fingerprint=labeled_fingerprint,
        electronic_structure_fingerprint_digest=validate_digest(
            electronic_structure_fingerprint_digest,
            name="electronic_structure_fingerprint_digest",
        ),
    )
