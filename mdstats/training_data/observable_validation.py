"""MLFF-owned orchestration for analysis-owned physical observable validation.

The MLFF branch owns recipe selection, reference/candidate pairing, model and MD
lineage, and later comparison/acceptance policy. Numerical observable
calculations remain delegated to ``mdstats.analysis.observable_validation`` and
ultimately to their authoritative analysis modules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from mdstats.analysis.observable_validation import (
    ObservableAnalysisRecipe,
    ObservableExecutionResult,
    execute_observable_recipe,
    get_observable_capability,
)

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)

MLFF_OBSERVABLE_VALIDATION_PLAN_SCHEMA = "mdstats.mlff-observable-validation-plan.v4"
MLFF_OBSERVABLE_VALIDATION_EVIDENCE_SCHEMA = "mdstats.mlff-observable-validation-evidence.v4"
OBSERVABLE_COLLECTION_IDENTITY_SCHEMA = "mdstats.observable-collection-identity.v2"
TRAJECTORY_GENERATION_IDENTITY_SCHEMA = "mdstats.trajectory-generation-identity.v1"
OBSERVABLE_VALIDATION_ACTIVATION_SCHEMA = "mdstats.observable-validation-activation.v1"
MLFF_OBSERVABLE_VALIDATION_VERSION = "mdstats.mlff.observable-validation.2026-07.v4"


class ObservableRecommendationProfile(str, Enum):
    """Advisory baseline of currently executable observable calls.

    This is not the general material-profile system used for MLFF feature
    selection. It neither classifies a material nor claims to provide a complete
    physical validation protocol.
    """

    GENERIC_CONDENSED = "generic_condensed"
    CRYSTALLINE_SOLID = "crystalline_solid"
    AMORPHOUS_SOLID = "amorphous_solid"
    LIQUID = "liquid"
    INTERFACE = "interface"


_PROFILE_RECOMMENDATIONS: dict[ObservableRecommendationProfile, tuple[str, ...]] = {
    ObservableRecommendationProfile.GENERIC_CONDENSED: (
        "structure.rdf",
        "structure.coordination",
        "structure.bond_angle",
        "topology.atomic_connectivity",
        "topology.atomic_statistics",
    ),
    ObservableRecommendationProfile.CRYSTALLINE_SOLID: (
        "structure.rdf",
        "structure.coordination",
        "structure.bond_angle",
        "topology.atomic_connectivity",
        "topology.atomic_statistics",
        "dynamics.msd",
        "dynamics.vacf",
        "spectrum.vacf",
        "spectrum.vdos",
    ),
    ObservableRecommendationProfile.AMORPHOUS_SOLID: (
        "structure.rdf",
        "structure.coordination",
        "structure.bond_angle",
        "topology.atomic_connectivity",
        "topology.atomic_statistics",
        "dynamics.msd",
        "dynamics.vacf",
        "spectrum.vacf",
        "spectrum.vdos",
        "dynamics.self_van_hove",
        "dynamics.non_gaussian",
        "dynamics.self_intermediate_scattering",
    ),
    ObservableRecommendationProfile.LIQUID: (
        "structure.rdf",
        "structure.coordination",
        "structure.bond_angle",
        "topology.atomic_connectivity",
        "topology.atomic_statistics",
        "dynamics.msd",
        "dynamics.vacf",
        "transport.vacf_diffusion",
        "transport.diffusion_plateau",
        "dynamics.self_van_hove",
        "dynamics.non_gaussian",
        "dynamics.self_intermediate_scattering",
        "spectrum.velocity_welch",
        "spectrum.vdos",
    ),
    ObservableRecommendationProfile.INTERFACE: (
        "structure.rdf",
        "structure.coordination",
        "structure.bond_angle",
        "topology.atomic_connectivity",
        "topology.atomic_statistics",
        "dynamics.msd",
        "dynamics.vacf",
        "transport.vacf_diffusion",
        "transport.diffusion_plateau",
        "dynamics.self_van_hove",
        "dynamics.non_gaussian",
        "dynamics.self_intermediate_scattering",
    ),
}

_IONIC_EXTENSION: tuple[str, ...] = (
    "transport.charge_current",
    "transport.current_correlation",
    "transport.ionic_conductivity",
    "transport.conductivity_plateau",
    "transport.nernst_einstein_comparison",
)



def _array_digest(value: Any) -> str | None:
    """Return a stable digest and reject object-pointer representations."""

    if value is None:
        return None
    array = np.asarray(value)
    if array.dtype.kind == "O":
        raise TrainingDataInputError(
            "Object-dtype arrays cannot be used in immutable observable identities."
        )
    if array.dtype.kind in {"U", "S"}:
        return digest({
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "values": array.tolist(),
        })
    contiguous = np.ascontiguousarray(array)
    header = f"{contiguous.dtype.str}|{contiguous.shape}".encode("ascii")
    hasher = hashlib.sha256()
    hasher.update(header)
    hasher.update(memoryview(contiguous).cast("B"))
    return hasher.hexdigest()


def _safe_provenance_payload(provenance: Any) -> tuple[Mapping[str, Any] | None, str]:
    if provenance is None:
        return None, "absent"
    try:
        return json_value(asdict(provenance)), "verified-dataclass"
    except (TypeError, TrainingDataInputError):
        to_dict = getattr(provenance, "to_dict", None)
        if callable(to_dict):
            try:
                return json_value(to_dict()), "verified-to-dict"
            except (TypeError, TrainingDataInputError):
                pass
        return {
            "type": f"{type(provenance).__module__}.{type(provenance).__qualname__}"
        }, "opaque-type-only"


@dataclass(frozen=True, slots=True)
class ObservableCollectionIdentity:
    """Immutable scientific identity of the exact analyzed frame collection.

    Location hints such as source paths and the human label are recorded but do
    not contribute to ``content_digest``. Identical data therefore retain the
    same identity after relocation.
    """

    label: str
    frame_semantics: str
    n_frames: int
    n_atoms: int
    atomic_numbers_digest: str
    species_counts: tuple[tuple[int, int], ...]
    available_fields: tuple[str, ...]
    frame_selection_digest: str
    geometry_digest: str
    dynamics_digest: str | None
    label_fields_digest: str | None
    provenance_digest: str | None
    provenance_status: str
    atomic_numbers: tuple[int, ...] = ()
    source_content_digests: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.label.strip() or self.n_frames < 1 or self.n_atoms < 1:
            raise TrainingDataInputError("Collection identity requires a label and nonempty collection.")
        for name in ("atomic_numbers_digest", "frame_selection_digest", "geometry_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("dynamics_digest", "label_fields_digest", "provenance_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        content_digests = tuple(validate_digest(v, name="source_content_digest") for v in self.source_content_digests)
        object.__setattr__(self, "source_content_digests", tuple(sorted(content_digests)))
        object.__setattr__(self, "atomic_numbers", tuple(int(v) for v in self.atomic_numbers))
        counts = tuple(sorted((int(z), int(n)) for z, n in self.species_counts))
        if any(z <= 0 or n <= 0 for z, n in counts) or sum(n for _, n in counts) != self.n_atoms:
            raise TrainingDataInputError("species_counts must be positive and sum to n_atoms.")
        object.__setattr__(self, "species_counts", counts)
        object.__setattr__(self, "available_fields", tuple(sorted(set(self.available_fields))))
        object.__setattr__(self, "source_files", tuple(str(v) for v in self.source_files))
        if not self.provenance_status.strip():
            raise TrainingDataInputError("provenance_status must be non-empty.")

    @classmethod
    def from_collection(cls, collection: Any, *, label: str) -> "ObservableCollectionIdentity":
        numbers = np.asarray(getattr(collection, "atomic_numbers"))
        if numbers.ndim != 1 or numbers.size < 1:
            raise TrainingDataInputError("atomic_numbers must be a nonempty one-dimensional array.")
        unique, counts = np.unique(numbers.astype(np.int64), return_counts=True)
        frame_payload = {
            "frame_ids": _array_digest(getattr(collection, "frame_ids", None)),
            "steps": _array_digest(getattr(collection, "steps", None)),
            "times": _array_digest(getattr(collection, "times", None)),
        }
        geometry_payload = {
            "atomic_numbers": _array_digest(numbers),
            "masses": _array_digest(getattr(collection, "masses", None)),
            "pbc": _array_digest(getattr(collection, "pbc", None)),
            "cells": _array_digest(getattr(collection, "cells", None)),
            "origins": _array_digest(getattr(collection, "origins", None)),
            "fractional_positions": _array_digest(getattr(collection, "fractional_positions", None)),
        }
        dynamics_values = {"velocities": _array_digest(getattr(collection, "velocities", None))}
        label_values = {
            name: _array_digest(getattr(collection, name, None))
            for name in (
                "forces", "stresses", "scalar_pressures", "temperatures",
                "potential_energies", "kinetic_energies", "total_energies",
            )
        }
        available = tuple(
            name for name in (
                "times", "velocities", "forces", "stresses", "scalar_pressures",
                "temperatures", "potential_energies", "kinetic_energies", "total_energies",
            ) if getattr(collection, name, None) is not None
        )
        provenance_payload, provenance_status = _safe_provenance_payload(
            getattr(collection, "provenance", None)
        )
        provenance = getattr(collection, "provenance", None)
        source_files = () if provenance is None else tuple(getattr(provenance, "source_files", ()))
        raw_source_digests = () if provenance is None else tuple(
            str(v) for v in getattr(provenance, "source_content_digests", ())
        )
        # Store the explicit sequence only for modest systems; its digest and
        # species counts are always retained.
        explicit_numbers = tuple(int(v) for v in numbers.tolist()) if numbers.size <= 1024 else ()
        return cls(
            label=label,
            frame_semantics=str(getattr(getattr(collection, "frame_semantics", "unknown"), "value", getattr(collection, "frame_semantics", "unknown"))),
            n_frames=int(getattr(collection, "n_frames")),
            n_atoms=int(getattr(collection, "n_atoms")),
            atomic_numbers_digest=_array_digest(numbers) or "",
            species_counts=tuple((int(z), int(n)) for z, n in zip(unique, counts)),
            atomic_numbers=explicit_numbers,
            available_fields=available,
            frame_selection_digest=digest(frame_payload),
            geometry_digest=digest(geometry_payload),
            dynamics_digest=None if all(v is None for v in dynamics_values.values()) else digest(dynamics_values),
            label_fields_digest=None if all(v is None for v in label_values.values()) else digest(label_values),
            provenance_digest=None if provenance_payload is None else digest(provenance_payload),
            provenance_status=provenance_status,
            source_content_digests=raw_source_digests,
            source_files=source_files,
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_COLLECTION_IDENTITY_SCHEMA,
            "frame_semantics": self.frame_semantics,
            "n_frames": self.n_frames,
            "n_atoms": self.n_atoms,
            "atomic_numbers_digest": self.atomic_numbers_digest,
            "species_counts": [[z, n] for z, n in self.species_counts],
            "atomic_numbers": list(self.atomic_numbers),
            "available_fields": list(self.available_fields),
            "frame_selection_digest": self.frame_selection_digest,
            "geometry_digest": self.geometry_digest,
            "dynamics_digest": self.dynamics_digest,
            "label_fields_digest": self.label_fields_digest,
            "provenance_digest": self.provenance_digest,
            "provenance_status": self.provenance_status,
            "source_content_digests": list(self.source_content_digests),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "label": self.label,
            "source_files": list(self.source_files),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    def verify_collection(self, collection: Any, *, expected_label: str | None = None) -> None:
        label = self.label if expected_label is None else expected_label
        recomputed = type(self).from_collection(collection, label=label)
        if self.label != label:
            raise TrainingDataInputError(
                f"Supplied collection identity label {self.label!r} does not match {label!r}."
            )
        if self.content_digest != recomputed.content_digest:
            raise TrainingDataInputError(
                "Supplied collection identity does not match the collection actually analyzed."
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableCollectionIdentity":
        schema = payload.get("schema")
        if schema not in (OBSERVABLE_COLLECTION_IDENTITY_SCHEMA, "mdstats.observable-collection-identity.v1"):
            raise TrainingDataSerializationError("Unsupported observable collection identity schema.")
        if schema == "mdstats.observable-collection-identity.v1":
            numbers = tuple(int(v) for v in payload.get("atomic_numbers", ()))
            unique, counts = np.unique(np.asarray(numbers, dtype=np.int64), return_counts=True)
            result = cls(
                label=str(payload["label"]),
                frame_semantics=str(payload["frame_semantics"]),
                n_frames=int(payload["n_frames"]),
                n_atoms=int(payload["n_atoms"]),
                atomic_numbers_digest=_array_digest(np.asarray(numbers, dtype=np.int64)) or "",
                species_counts=tuple((int(z), int(n)) for z, n in zip(unique, counts)),
                atomic_numbers=numbers,
                available_fields=tuple(str(v) for v in payload.get("available_fields", ())),
                frame_selection_digest=str(payload["frame_selection_digest"]),
                geometry_digest=str(payload["geometry_digest"]),
                dynamics_digest=None if payload.get("dynamics_digest") is None else str(payload["dynamics_digest"]),
                label_fields_digest=None if payload.get("label_fields_digest") is None else str(payload["label_fields_digest"]),
                provenance_digest=None if payload.get("provenance_digest") is None else str(payload["provenance_digest"]),
                provenance_status="legacy-unspecified",
                source_files=tuple(str(v) for v in payload.get("source_files", ())),
            )
            return result
        result = cls(
            label=str(payload["label"]),
            frame_semantics=str(payload["frame_semantics"]),
            n_frames=int(payload["n_frames"]),
            n_atoms=int(payload["n_atoms"]),
            atomic_numbers_digest=str(payload["atomic_numbers_digest"]),
            species_counts=tuple((int(v[0]), int(v[1])) for v in payload["species_counts"]),
            atomic_numbers=tuple(int(v) for v in payload.get("atomic_numbers", ())),
            available_fields=tuple(str(v) for v in payload.get("available_fields", ())),
            frame_selection_digest=str(payload["frame_selection_digest"]),
            geometry_digest=str(payload["geometry_digest"]),
            dynamics_digest=None if payload.get("dynamics_digest") is None else str(payload["dynamics_digest"]),
            label_fields_digest=None if payload.get("label_fields_digest") is None else str(payload["label_fields_digest"]),
            provenance_digest=None if payload.get("provenance_digest") is None else str(payload["provenance_digest"]),
            provenance_status=str(payload.get("provenance_status", "unspecified")),
            source_content_digests=tuple(str(v) for v in payload.get("source_content_digests", ())),
            source_files=tuple(str(v) for v in payload.get("source_files", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable collection identity digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrajectoryGenerationIdentity:
    """Symmetric identity of the engine/protocol that generated a trajectory."""

    generator_kind: str
    generator_artifact_digest: str
    protocol_digest: str
    output_collection_digest: str
    engine_name: str
    engine_version: str
    generator_manifest_digest: str | None = None
    runtime_environment_digest: str | None = None
    initial_configuration_digest: str | None = None
    source_provenance_digest: str | None = None
    precision_policy: str = "unspecified"
    random_seed: int | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.generator_kind.strip() or not self.engine_name.strip() or not self.engine_version.strip():
            raise TrainingDataInputError("Trajectory generator and engine identifiers must be non-empty.")
        for name in ("generator_artifact_digest", "protocol_digest", "output_collection_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "generator_manifest_digest", "runtime_environment_digest",
            "initial_configuration_digest", "source_provenance_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if not self.precision_policy.strip():
            raise TrainingDataInputError("precision_policy must be non-empty.")
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAJECTORY_GENERATION_IDENTITY_SCHEMA,
            "generator_kind": self.generator_kind,
            "generator_artifact_digest": self.generator_artifact_digest,
            "generator_manifest_digest": self.generator_manifest_digest,
            "protocol_digest": self.protocol_digest,
            "output_collection_digest": self.output_collection_digest,
            "runtime_environment_digest": self.runtime_environment_digest,
            "initial_configuration_digest": self.initial_configuration_digest,
            "source_provenance_digest": self.source_provenance_digest,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "precision_policy": self.precision_policy,
            "random_seed": self.random_seed,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    def verify_output(self, identity: ObservableCollectionIdentity) -> None:
        if self.output_collection_digest != identity.content_digest:
            raise TrainingDataInputError(
                "Trajectory generation identity is not bound to the analyzed collection."
            )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrajectoryGenerationIdentity":
        if payload.get("schema") != TRAJECTORY_GENERATION_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported trajectory generation identity schema.")
        result = cls(
            generator_kind=str(payload["generator_kind"]),
            generator_artifact_digest=str(payload["generator_artifact_digest"]),
            generator_manifest_digest=None if payload.get("generator_manifest_digest") is None else str(payload["generator_manifest_digest"]),
            protocol_digest=str(payload["protocol_digest"]),
            output_collection_digest=str(payload["output_collection_digest"]),
            runtime_environment_digest=None if payload.get("runtime_environment_digest") is None else str(payload["runtime_environment_digest"]),
            initial_configuration_digest=None if payload.get("initial_configuration_digest") is None else str(payload["initial_configuration_digest"]),
            source_provenance_digest=None if payload.get("source_provenance_digest") is None else str(payload["source_provenance_digest"]),
            engine_name=str(payload["engine_name"]),
            engine_version=str(payload["engine_version"]),
            precision_policy=str(payload.get("precision_policy", "unspecified")),
            random_seed=None if payload.get("random_seed") is None else int(payload["random_seed"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Trajectory generation identity digest mismatch.")
        return result


class ObservableEvidenceRole(str, Enum):
    TRAINING_DIAGNOSTIC = "training_diagnostic"
    CHECKPOINT_MONITOR = "checkpoint_monitor"
    OUTER_VALIDATION = "outer_validation"
    CALIBRATION = "calibration"
    LOCKED_TEST = "locked_test"
    EXTERNAL_BENCHMARK = "external_benchmark"


@dataclass(frozen=True, slots=True)
class ObservableValidationActivationRecord:
    """Predeclared statistical-role and leakage-control identity."""

    role: ObservableEvidenceRole
    partition_policy_digest: str | None = None
    partition_assignment_digest: str | None = None
    comparison_policy_digest: str | None = None
    protocol_freeze_digest: str | None = None
    locked_test_activation_digest: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", ObservableEvidenceRole(self.role))
        for name in (
            "partition_policy_digest", "partition_assignment_digest",
            "comparison_policy_digest", "protocol_freeze_digest",
            "locked_test_activation_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        if self.role in {
            ObservableEvidenceRole.OUTER_VALIDATION,
            ObservableEvidenceRole.CALIBRATION,
            ObservableEvidenceRole.LOCKED_TEST,
        }:
            if self.partition_policy_digest is None or self.partition_assignment_digest is None:
                raise TrainingDataInputError(
                    f"Observable role {self.role.value!r} requires partition policy and assignment digests."
                )
        if self.role in {
            ObservableEvidenceRole.OUTER_VALIDATION,
            ObservableEvidenceRole.CALIBRATION,
            ObservableEvidenceRole.LOCKED_TEST,
            ObservableEvidenceRole.EXTERNAL_BENCHMARK,
        } and self.comparison_policy_digest is None:
            raise TrainingDataInputError(
                f"Observable role {self.role.value!r} requires a predeclared comparison policy digest."
            )
        if self.role is ObservableEvidenceRole.LOCKED_TEST:
            if self.protocol_freeze_digest is None or self.locked_test_activation_digest is None:
                raise TrainingDataInputError(
                    "Locked-test observable execution requires protocol-freeze and activation digests."
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_VALIDATION_ACTIVATION_SCHEMA,
            "role": self.role.value,
            "partition_policy_digest": self.partition_policy_digest,
            "partition_assignment_digest": self.partition_assignment_digest,
            "comparison_policy_digest": self.comparison_policy_digest,
            "protocol_freeze_digest": self.protocol_freeze_digest,
            "locked_test_activation_digest": self.locked_test_activation_digest,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableValidationActivationRecord":
        if payload.get("schema") != OBSERVABLE_VALIDATION_ACTIVATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable validation activation schema.")
        result = cls(
            role=ObservableEvidenceRole(str(payload["role"])),
            partition_policy_digest=None if payload.get("partition_policy_digest") is None else str(payload["partition_policy_digest"]),
            partition_assignment_digest=None if payload.get("partition_assignment_digest") is None else str(payload["partition_assignment_digest"]),
            comparison_policy_digest=None if payload.get("comparison_policy_digest") is None else str(payload["comparison_policy_digest"]),
            protocol_freeze_digest=None if payload.get("protocol_freeze_digest") is None else str(payload["protocol_freeze_digest"]),
            locked_test_activation_digest=None if payload.get("locked_test_activation_digest") is None else str(payload["locked_test_activation_digest"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable validation activation digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MLFFObservableValidationPlan:
    """Immutable MLFF pairing and invocation policy for one analysis recipe."""

    plan_id: str
    recommendation_profile: ObservableRecommendationProfile
    recipe: ObservableAnalysisRecipe
    material_profile_contracts_digest: str | None = None
    reference_label: str = "reference"
    candidate_label: str = "mlff"
    ionic_transport: bool = False
    require_complete_lineage: bool = True
    activation: ObservableValidationActivationRecord = ObservableValidationActivationRecord(
        ObservableEvidenceRole.CHECKPOINT_MONITOR
    )
    notes: tuple[str, ...] = ()
    bridge_version: str = MLFF_OBSERVABLE_VALIDATION_VERSION

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.reference_label.strip() or not self.candidate_label.strip():
            raise TrainingDataInputError("Validation plan identifiers must be non-empty.")
        object.__setattr__(self, "recommendation_profile", ObservableRecommendationProfile(self.recommendation_profile))
        if self.material_profile_contracts_digest is not None:
            object.__setattr__(self, "material_profile_contracts_digest", validate_digest(self.material_profile_contracts_digest, name="material_profile_contracts_digest"))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        if not self.bridge_version.strip():
            raise TrainingDataInputError("bridge_version must be non-empty.")
        ids = {call.observable_id for call in self.recipe.calls}
        for call in self.recipe.calls:
            get_observable_capability(call.observable_id)
        if self.ionic_transport and not set(_IONIC_EXTENSION).issubset(ids):
            missing = sorted(set(_IONIC_EXTENSION) - ids)
            raise TrainingDataInputError(
                "ionic_transport=True requires the complete declared ionic transport chain; "
                f"missing {missing}."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLFF_OBSERVABLE_VALIDATION_PLAN_SCHEMA,
            "bridge_version": self.bridge_version,
            "plan_id": self.plan_id,
            "observable_recommendation_profile": self.recommendation_profile.value,
            "material_profile_contracts_digest": self.material_profile_contracts_digest,
            "recipe": self.recipe.to_dict(),
            "reference_label": self.reference_label,
            "candidate_label": self.candidate_label,
            "ionic_transport": self.ionic_transport,
            "require_complete_lineage": self.require_complete_lineage,
            "activation": self.activation.to_dict(),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MLFFObservableValidationPlan":
        if payload.get("schema") != MLFF_OBSERVABLE_VALIDATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLFF observable-validation-plan schema.")
        result = cls(
            plan_id=str(payload["plan_id"]),
            recommendation_profile=ObservableRecommendationProfile(str(payload["observable_recommendation_profile"])),
            recipe=ObservableAnalysisRecipe.from_dict(payload["recipe"]),
            material_profile_contracts_digest=None if payload.get("material_profile_contracts_digest") is None else str(payload["material_profile_contracts_digest"]),
            reference_label=str(payload.get("reference_label", "reference")),
            candidate_label=str(payload.get("candidate_label", "mlff")),
            ionic_transport=bool(payload.get("ionic_transport", False)),
            require_complete_lineage=bool(payload.get("require_complete_lineage", True)),
            activation=ObservableValidationActivationRecord.from_dict(payload["activation"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
            bridge_version=str(payload.get("bridge_version", MLFF_OBSERVABLE_VALIDATION_VERSION)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLFF observable-validation-plan digest mismatch.")
        return result



@dataclass(frozen=True, slots=True)
class MLFFObservableValidationEvidenceRecord:
    """Restorable digest-verified summary without loading scientific arrays."""

    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        frozen = json_value(self.payload)
        if frozen.get("schema") != MLFF_OBSERVABLE_VALIDATION_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLFF observable-validation evidence schema.")
        claimed = frozen.get("content_digest")
        unsigned = {k: v for k, v in frozen.items() if k != "content_digest"}
        actual = digest(unsigned)
        if claimed != actual:
            raise TrainingDataSerializationError("MLFF observable-validation evidence digest mismatch.")
        object.__setattr__(self, "payload", MappingProxyType(dict(frozen)))

    @property
    def content_digest(self) -> str:
        return str(self.payload["content_digest"])

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MLFFObservableValidationEvidenceRecord":
        return cls(payload)


@dataclass(frozen=True, slots=True)
class MLFFObservableValidationEvidence:
    """Paired runtime evidence; native result objects remain analysis-owned."""

    plan: MLFFObservableValidationPlan
    reference_identity: ObservableCollectionIdentity
    candidate_identity: ObservableCollectionIdentity
    reference_generation: TrajectoryGenerationIdentity | None
    candidate_generation: TrajectoryGenerationIdentity | None
    reference_execution: ObservableExecutionResult
    candidate_execution: ObservableExecutionResult
    result_type_pairs: Mapping[str, tuple[str, str]]

    def __post_init__(self) -> None:
        if self.reference_execution.recipe.content_digest != self.plan.recipe.content_digest:
            raise TrainingDataInputError("Reference execution does not match the validation plan recipe.")
        if self.candidate_execution.recipe.content_digest != self.plan.recipe.content_digest:
            raise TrainingDataInputError("Candidate execution does not match the validation plan recipe.")
        if self.plan.require_complete_lineage and (
            self.reference_generation is None or self.candidate_generation is None
        ):
            raise TrainingDataInputError(
                "Complete observable validation lineage requires generation identities for both trajectories."
            )
        if self.reference_generation is not None:
            self.reference_generation.verify_output(self.reference_identity)
        if self.candidate_generation is not None:
            self.candidate_generation.verify_output(self.candidate_identity)
        pairs = {str(key): (str(value[0]), str(value[1])) for key, value in self.result_type_pairs.items()}
        expected = {call.call_id for call in self.plan.recipe.calls}
        if set(pairs) != expected:
            raise TrainingDataInputError("Result type pairs do not match the recipe calls.")
        object.__setattr__(self, "result_type_pairs", MappingProxyType(pairs))

    def to_evidence_dict(self) -> dict[str, Any]:
        payload = {
            "schema": MLFF_OBSERVABLE_VALIDATION_EVIDENCE_SCHEMA,
            "plan_digest": self.plan.content_digest,
            "recipe_digest": self.plan.recipe.content_digest,
            "activation": self.plan.activation.to_dict(),
            "reference_collection": self.reference_identity.to_dict(),
            "candidate_collection": self.candidate_identity.to_dict(),
            "reference_generation": None if self.reference_generation is None else self.reference_generation.to_dict(),
            "candidate_generation": None if self.candidate_generation is None else self.candidate_generation.to_dict(),
            "reference_runtime_identity": json_value(self.reference_execution.runtime_identity),
            "candidate_runtime_identity": json_value(self.candidate_execution.runtime_identity),
            "capability_digests": {
                "reference": dict(self.reference_execution.capability_digests),
                "candidate": dict(self.candidate_execution.capability_digests),
            },
            "result_identities": {
                call_id: {
                    "reference": self.reference_execution.result_identities[call_id].to_dict(),
                    "candidate": self.candidate_execution.result_identities[call_id].to_dict(),
                }
                for call_id in sorted(self.result_type_pairs)
            },
            "warnings_by_call": {
                call_id: {
                    "reference": list(self.reference_execution.warnings_by_call[call_id]),
                    "candidate": list(self.candidate_execution.warnings_by_call[call_id]),
                }
                for call_id in sorted(self.result_type_pairs)
            },
            "duration_seconds_by_call": {
                call_id: {
                    "reference": self.reference_execution.duration_seconds_by_call[call_id],
                    "candidate": self.candidate_execution.duration_seconds_by_call[call_id],
                }
                for call_id in sorted(self.result_type_pairs)
            },
            "result_type_pairs": {
                key: {"reference": value[0], "candidate": value[1]}
                for key, value in sorted(self.result_type_pairs.items())
            },
            "scientific_result_serialization": "identity-owned-by-authoritative-analysis-module",
            "comparison_and_acceptance": "predeclared-policy-identity-required-by-statistical-role",
        }
        return {**payload, "content_digest": digest(payload)}

    def to_record(self) -> MLFFObservableValidationEvidenceRecord:
        return MLFFObservableValidationEvidenceRecord.from_dict(self.to_evidence_dict())


def recommended_observable_ids(
    profile: ObservableRecommendationProfile | str,
    *,
    ionic_transport: bool = False,
) -> tuple[str, ...]:
    """Return currently executable baseline observable IDs.

    This list is advisory and intentionally incomplete. The user still supplies
    species, atom groups, cutoffs, time windows, projections, and other
    scientifically material parameters. Missing observable families remain
    owned by their respective analysis architecture plans.
    """

    resolved = ObservableRecommendationProfile(profile)
    values = list(_PROFILE_RECOMMENDATIONS[resolved])
    if ionic_transport:
        values.extend(_IONIC_EXTENSION)
    return tuple(dict.fromkeys(values))


def _verified_collection_identity(
    collection: Any,
    supplied: ObservableCollectionIdentity | None,
    *,
    label: str,
) -> ObservableCollectionIdentity:
    actual = ObservableCollectionIdentity.from_collection(collection, label=label)
    if supplied is None:
        return actual
    supplied.verify_collection(collection, expected_label=label)
    return supplied


def _coerce_generation(
    value: TrajectoryGenerationIdentity | None,
    *,
    collection_identity: ObservableCollectionIdentity,
) -> TrajectoryGenerationIdentity | None:
    if value is None:
        return None
    value.verify_output(collection_identity)
    return value


def run_mlff_observable_validation(
    reference_collection: Any,
    candidate_collection: Any,
    plan: MLFFObservableValidationPlan,
    *,
    reference_identity: ObservableCollectionIdentity | None = None,
    candidate_identity: ObservableCollectionIdentity | None = None,
    reference_generation: TrajectoryGenerationIdentity | None = None,
    candidate_generation: TrajectoryGenerationIdentity | None = None,
) -> MLFFObservableValidationEvidence:
    """Run one analysis-owned recipe on reference and MLFF trajectories."""

    reference_id = _verified_collection_identity(
        reference_collection, reference_identity, label=plan.reference_label
    )
    candidate_id = _verified_collection_identity(
        candidate_collection, candidate_identity, label=plan.candidate_label
    )
    reference_gen = _coerce_generation(
        reference_generation,
        collection_identity=reference_id,
    )
    candidate_gen = _coerce_generation(
        candidate_generation,
        collection_identity=candidate_id,
    )
    if plan.require_complete_lineage and (reference_gen is None or candidate_gen is None):
        raise TrainingDataInputError(
            "reference_generation and candidate_generation are required by the validation plan's lineage policy."
        )
    reference = execute_observable_recipe(reference_collection, plan.recipe)
    candidate = execute_observable_recipe(candidate_collection, plan.recipe)
    pairs = {
        call.call_id: (
            reference.result_types[call.call_id],
            candidate.result_types[call.call_id],
        )
        for call in plan.recipe.calls
    }
    return MLFFObservableValidationEvidence(
        plan=plan,
        reference_identity=reference_id,
        candidate_identity=candidate_id,
        reference_generation=reference_gen,
        candidate_generation=candidate_gen,
        reference_execution=reference,
        candidate_execution=candidate,
        result_type_pairs=pairs,
    )


def recommended_observable_ids_for_material_profile(
    contracts: Any,
    *,
    ionic_transport: bool = False,
) -> tuple[str, ...]:
    """Compose currently executable observable-call recommendations.

    The compositional material profile selects advisory call families only.
    Numerical algorithms and scientifically material call parameters remain
    owned by their analysis modules and explicit validation recipes.
    """

    from .phase_geometry_profiles import recommended_observable_profile_ids

    identifiers: list[str] = []
    for profile_id in recommended_observable_profile_ids(contracts):
        for observable_id in recommended_observable_ids(profile_id, ionic_transport=False):
            if observable_id not in identifiers:
                identifiers.append(observable_id)
    if ionic_transport:
        for observable_id in _IONIC_EXTENSION:
            if observable_id not in identifiers:
                identifiers.append(observable_id)
    return tuple(identifiers)
