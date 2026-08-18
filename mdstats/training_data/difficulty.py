"""Blinded foundation-model predictions and training-only residuals for DATA6."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, MutableMapping, Sequence

import numpy as np
from ase.data import chemical_symbols

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import ase_atoms_for_frame, build_frame_array_index
from .model_features import (
    AtomicModelPrediction,
    AtomicModelProvider,
    ModelCheckpointIdentity,
    ModelPredictionSummary,
    summarize_prediction,
)
from .partition import OuterRole

TRAINING_DIFFICULTY_DOMAIN_SCHEMA = "mdstats.training-difficulty-domain.v1"
SPECIES_FORCE_ERROR_SCHEMA = "mdstats.species-force-error.v1"
DIFFICULTY_FRAME_RECORD_SCHEMA = "mdstats.training-difficulty-frame.v1"
TRAINING_DIFFICULTY_CATALOG_SCHEMA = "mdstats.training-difficulty-catalog.v1"
BLINDED_PREDICTION_DOMAIN_SCHEMA = "mdstats.blinded-prediction-domain.v1"
BLINDED_PREDICTION_CATALOG_SCHEMA = "mdstats.blinded-prediction-catalog.v1"
MLFF_DATA6_DIFFICULTY_VERSION = "mdstats.mlff-data6.difficulty.2026-07.v1"


class TrainingDifficultyDomainKind(str, Enum):
    FINAL_DEVELOPMENT = "final_development"
    CROSS_VALIDATION_TRAINING = "cross_validation_training"


class BlindedPredictionDomainKind(str, Enum):
    OUTER_MONITOR = "outer_monitor"
    UNCERTAINTY_CALIBRATION = "uncertainty_calibration"
    CROSS_VALIDATION_CHECKPOINT_MONITOR = "cross_validation_checkpoint_monitor"
    CROSS_VALIDATION_EVALUATION = "cross_validation_evaluation"
    LOCKED_INTERPOLATION_TEST = "locked_interpolation_test"


class PredictionMaterializationStatus(str, Enum):
    MATERIALIZED_BLINDED = "materialized_blinded"
    SEALED_NOT_MATERIALIZED = "sealed_not_materialized"


def _normalized_digest_tuple(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(sorted(set(validate_digest(v, name=name) for v in values)))
    if not result:
        raise TrainingDataInputError(f"{name} values must be non-empty.")
    return result


def _frames_for_units(data5_bundle: Any, unit_ids: Sequence[str]) -> tuple[str, ...]:
    frames: list[str] = []
    for unit_id in unit_ids:
        frames.extend(data5_bundle.unit_catalog.unit(unit_id).frame_uids)
    result = tuple(sorted(set(frames)))
    if not result:
        raise TrainingDataInputError("Difficulty/prediction domain contains no frames.")
    return result


@dataclass(frozen=True, slots=True)
class TrainingDifficultyDomain:
    label_domain_id: str
    kind: TrainingDifficultyDomainKind
    data5_bundle_digest: str
    unit_ids: tuple[str, ...]
    frame_uids: tuple[str, ...]
    fold_index: int | None = None
    domain_version: str = MLFF_DATA6_DIFFICULTY_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip() or not self.domain_version.strip():
            raise TrainingDataInputError("Training-difficulty domain identifiers must be non-empty.")
        object.__setattr__(self, "kind", TrainingDifficultyDomainKind(self.kind))
        object.__setattr__(self, "data5_bundle_digest", validate_digest(self.data5_bundle_digest, name="data5_bundle_digest"))
        object.__setattr__(self, "unit_ids", _normalized_digest_tuple(self.unit_ids, name="unit_id"))
        object.__setattr__(self, "frame_uids", _normalized_digest_tuple(self.frame_uids, name="frame_uid"))
        if self.kind is TrainingDifficultyDomainKind.FINAL_DEVELOPMENT and self.fold_index is not None:
            raise TrainingDataInputError("Final-development domains cannot have fold_index.")
        if self.kind is TrainingDifficultyDomainKind.CROSS_VALIDATION_TRAINING:
            if self.fold_index is None or self.fold_index < 0:
                raise TrainingDataInputError("Cross-validation training domains require fold_index.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DIFFICULTY_DOMAIN_SCHEMA,
            "domain_version": self.domain_version,
            "label_domain_id": self.label_domain_id,
            "kind": self.kind.value,
            "data5_bundle_digest": self.data5_bundle_digest,
            "unit_ids": list(self.unit_ids),
            "frame_uids": list(self.frame_uids),
            "fold_index": self.fold_index,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDifficultyDomain":
        if payload.get("schema") != TRAINING_DIFFICULTY_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-difficulty domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            kind=TrainingDifficultyDomainKind(payload["kind"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            unit_ids=tuple(str(v) for v in payload["unit_ids"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            domain_version=str(payload["domain_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-difficulty domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class BlindedPredictionDomain:
    label_domain_id: str
    kind: BlindedPredictionDomainKind
    materialization_status: PredictionMaterializationStatus
    data5_bundle_digest: str
    unit_ids: tuple[str, ...]
    frame_uids: tuple[str, ...]
    fold_index: int | None = None
    domain_version: str = MLFF_DATA6_DIFFICULTY_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip() or not self.domain_version.strip():
            raise TrainingDataInputError("Blinded prediction-domain identifiers must be non-empty.")
        object.__setattr__(self, "kind", BlindedPredictionDomainKind(self.kind))
        object.__setattr__(self, "materialization_status", PredictionMaterializationStatus(self.materialization_status))
        object.__setattr__(self, "data5_bundle_digest", validate_digest(self.data5_bundle_digest, name="data5_bundle_digest"))
        object.__setattr__(self, "unit_ids", _normalized_digest_tuple(self.unit_ids, name="unit_id"))
        object.__setattr__(self, "frame_uids", _normalized_digest_tuple(self.frame_uids, name="frame_uid"))
        cv_kinds = {
            BlindedPredictionDomainKind.CROSS_VALIDATION_CHECKPOINT_MONITOR,
            BlindedPredictionDomainKind.CROSS_VALIDATION_EVALUATION,
        }
        if self.kind in cv_kinds:
            if self.fold_index is None or self.fold_index < 0:
                raise TrainingDataInputError("Cross-validation prediction domains require fold_index.")
        elif self.fold_index is not None:
            raise TrainingDataInputError("Outer prediction domains cannot have fold_index.")
        if self.kind is BlindedPredictionDomainKind.LOCKED_INTERPOLATION_TEST:
            if self.materialization_status is not PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED:
                raise TrainingDataInputError("Locked-test predictions must remain sealed in DATA6.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BLINDED_PREDICTION_DOMAIN_SCHEMA,
            "domain_version": self.domain_version,
            "label_domain_id": self.label_domain_id,
            "kind": self.kind.value,
            "materialization_status": self.materialization_status.value,
            "data5_bundle_digest": self.data5_bundle_digest,
            "unit_ids": list(self.unit_ids),
            "frame_uids": list(self.frame_uids),
            "fold_index": self.fold_index,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BlindedPredictionDomain":
        if payload.get("schema") != BLINDED_PREDICTION_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported blinded prediction-domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            kind=BlindedPredictionDomainKind(payload["kind"]),
            materialization_status=PredictionMaterializationStatus(payload["materialization_status"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            unit_ids=tuple(str(v) for v in payload["unit_ids"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            domain_version=str(payload["domain_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Blinded prediction-domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SpeciesForceError:
    atomic_number: int
    symbol: str
    atom_count: int
    component_rmse_ev_per_angstrom: float
    vector_error_mean_ev_per_angstrom: float
    vector_error_max_ev_per_angstrom: float

    def __post_init__(self) -> None:
        if self.atomic_number <= 0 or self.atom_count <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid species force-error identity.")
        for name in (
            "component_rmse_ev_per_angstrom",
            "vector_error_mean_ev_per_angstrom",
            "vector_error_max_ev_per_angstrom",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": SPECIES_FORCE_ERROR_SCHEMA,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "atom_count": self.atom_count,
            "component_rmse_ev_per_angstrom": self.component_rmse_ev_per_angstrom,
            "vector_error_mean_ev_per_angstrom": self.vector_error_mean_ev_per_angstrom,
            "vector_error_max_ev_per_angstrom": self.vector_error_max_ev_per_angstrom,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesForceError":
        if payload.get("schema") != SPECIES_FORCE_ERROR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported species force-error schema.")
        result = cls(
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            atom_count=int(payload["atom_count"]),
            component_rmse_ev_per_angstrom=float(payload["component_rmse_ev_per_angstrom"]),
            vector_error_mean_ev_per_angstrom=float(payload["vector_error_mean_ev_per_angstrom"]),
            vector_error_max_ev_per_angstrom=float(payload["vector_error_max_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Species force-error digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DifficultyFrameRecord:
    frame_uid: str
    frame_record_digest: str
    checkpoint_identity_digest: str
    signed_energy_error_ev: float
    absolute_energy_error_per_atom_ev: float
    force_component_rmse_ev_per_angstrom: float
    force_vector_error_mean_ev_per_angstrom: float
    force_vector_error_max_ev_per_angstrom: float
    stress_component_rmse_ev_per_angstrom3: float | None
    species_force_errors: tuple[SpeciesForceError, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "checkpoint_identity_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "signed_energy_error_ev",
            "absolute_energy_error_per_atom_ev",
            "force_component_rmse_ev_per_angstrom",
            "force_vector_error_mean_ev_per_angstrom",
            "force_vector_error_max_ev_per_angstrom",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or (name != "signed_energy_error_ev" and value < 0.0):
                raise TrainingDataInputError(f"{name} is invalid.")
            object.__setattr__(self, name, value)
        if self.stress_component_rmse_ev_per_angstrom3 is not None:
            stress = float(self.stress_component_rmse_ev_per_angstrom3)
            if not np.isfinite(stress) or stress < 0.0:
                raise TrainingDataInputError("Stress RMSE must be finite and nonnegative.")
            object.__setattr__(self, "stress_component_rmse_ev_per_angstrom3", stress)
        object.__setattr__(self, "species_force_errors", tuple(sorted(self.species_force_errors, key=lambda item: item.atomic_number)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DIFFICULTY_FRAME_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "checkpoint_identity_digest": self.checkpoint_identity_digest,
            "signed_energy_error_ev": self.signed_energy_error_ev,
            "absolute_energy_error_per_atom_ev": self.absolute_energy_error_per_atom_ev,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
            "force_vector_error_mean_ev_per_angstrom": self.force_vector_error_mean_ev_per_angstrom,
            "force_vector_error_max_ev_per_angstrom": self.force_vector_error_max_ev_per_angstrom,
            "stress_component_rmse_ev_per_angstrom3": self.stress_component_rmse_ev_per_angstrom3,
            "species_force_errors": [item.to_dict() for item in self.species_force_errors],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DifficultyFrameRecord":
        if payload.get("schema") != DIFFICULTY_FRAME_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported difficulty-frame schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            checkpoint_identity_digest=str(payload["checkpoint_identity_digest"]),
            signed_energy_error_ev=float(payload["signed_energy_error_ev"]),
            absolute_energy_error_per_atom_ev=float(payload["absolute_energy_error_per_atom_ev"]),
            force_component_rmse_ev_per_angstrom=float(payload["force_component_rmse_ev_per_angstrom"]),
            force_vector_error_mean_ev_per_angstrom=float(payload["force_vector_error_mean_ev_per_angstrom"]),
            force_vector_error_max_ev_per_angstrom=float(payload["force_vector_error_max_ev_per_angstrom"]),
            stress_component_rmse_ev_per_angstrom3=None if payload.get("stress_component_rmse_ev_per_angstrom3") is None else float(payload["stress_component_rmse_ev_per_angstrom3"]),
            species_force_errors=tuple(SpeciesForceError.from_dict(item) for item in payload["species_force_errors"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Difficulty-frame digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingDifficultyFeatureCatalog:
    dataset_id: str
    frame_catalog_digest: str
    domain: TrainingDifficultyDomain
    checkpoint_identity: ModelCheckpointIdentity
    records: tuple[DifficultyFrameRecord, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        records = tuple(self.records)
        uids = tuple(item.frame_uid for item in records)
        if any(left >= right for left, right in zip(uids, uids[1:])):
            records = tuple(sorted(records, key=lambda item: item.frame_uid))
        if {item.frame_uid for item in records} != set(self.domain.frame_uids):
            raise TrainingDataInputError("Difficulty records must exactly cover the authorized domain.")
        if any(item.checkpoint_identity_digest != self.checkpoint_identity.content_digest for item in records):
            raise TrainingDataInputError("Difficulty checkpoint mismatch.")
        object.__setattr__(self, "records", records)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DIFFICULTY_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "domain": self.domain.to_dict(),
            "checkpoint_identity": self.checkpoint_identity.to_dict(),
            "records": [item.to_dict() for item in self.records],
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DIFFICULTY_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "domain_digest": self.domain.content_digest,
            "checkpoint_identity_digest": self.checkpoint_identity.content_digest,
            "record_digests": [item.content_digest for item in self.records],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(self._digest_payload())
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDifficultyFeatureCatalog":
        if payload.get("schema") != TRAINING_DIFFICULTY_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-difficulty catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            domain=TrainingDifficultyDomain.from_dict(payload["domain"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            records=tuple(DifficultyFrameRecord.from_dict(item) for item in payload["records"]),
        )
        supplied = payload.get("content_digest")
        legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied not in (None, result.content_digest, legacy_digest):
            raise TrainingDataSerializationError("Training-difficulty catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class BlindedEvaluationPredictionCatalog:
    dataset_id: str
    frame_catalog_digest: str
    domain: BlindedPredictionDomain
    checkpoint_identity: ModelCheckpointIdentity
    records: tuple[ModelPredictionSummary, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        records = tuple(self.records)
        uids = tuple(item.frame_uid for item in records)
        if any(left >= right for left, right in zip(uids, uids[1:])):
            records = tuple(sorted(records, key=lambda item: item.frame_uid))
        if self.domain.materialization_status is PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED:
            if records:
                raise TrainingDataInputError("Sealed prediction domains cannot contain predictions.")
        elif {item.frame_uid for item in records} != set(self.domain.frame_uids):
            raise TrainingDataInputError("Blinded predictions must exactly cover a materialized domain.")
        if any(item.checkpoint_identity_digest != self.checkpoint_identity.content_digest for item in records):
            raise TrainingDataInputError("Blinded prediction checkpoint mismatch.")
        object.__setattr__(self, "records", records)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BLINDED_PREDICTION_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "domain": self.domain.to_dict(),
            "checkpoint_identity": self.checkpoint_identity.to_dict(),
            "records": [item.to_dict() for item in self.records],
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": BLINDED_PREDICTION_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "domain_digest": self.domain.content_digest,
            "checkpoint_identity_digest": self.checkpoint_identity.content_digest,
            "record_digests": [item.content_digest for item in self.records],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(self._digest_payload())
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BlindedEvaluationPredictionCatalog":
        if payload.get("schema") != BLINDED_PREDICTION_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported blinded-prediction catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            domain=BlindedPredictionDomain.from_dict(payload["domain"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            records=tuple(ModelPredictionSummary.from_dict(item) for item in payload["records"]),
        )
        supplied = payload.get("content_digest")
        legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied not in (None, result.content_digest, legacy_digest):
            raise TrainingDataSerializationError("Blinded-prediction catalog digest mismatch.")
        return result


def build_training_difficulty_domains(data5_bundle: Any) -> tuple[TrainingDifficultyDomain, ...]:
    domains: list[TrainingDifficultyDomain] = []
    data5_digest = data5_bundle.content_digest
    frame_cache: dict[tuple[str, ...], tuple[str, ...]] = {}

    def frames_for(unit_ids: Sequence[str]) -> tuple[str, ...]:
        key = tuple(unit_ids)
        value = frame_cache.get(key)
        if value is None:
            value = _frames_for_units(data5_bundle, key)
            frame_cache[key] = value
        return value

    for outer in data5_bundle.outer_partitions:
        unit_ids = outer.units_for(OuterRole.DEVELOPMENT)
        domains.append(
            TrainingDifficultyDomain(
                label_domain_id=outer.label_domain_id,
                kind=TrainingDifficultyDomainKind.FINAL_DEVELOPMENT,
                data5_bundle_digest=data5_digest,
                unit_ids=unit_ids,
                frame_uids=frames_for(unit_ids),
            )
        )
    for plan in data5_bundle.cross_validation_plans:
        for fold in plan.folds:
            domains.append(
                TrainingDifficultyDomain(
                    label_domain_id=plan.label_domain_id,
                    kind=TrainingDifficultyDomainKind.CROSS_VALIDATION_TRAINING,
                    data5_bundle_digest=data5_digest,
                    unit_ids=fold.training_unit_ids,
                    frame_uids=frames_for(fold.training_unit_ids),
                    fold_index=fold.fold_index,
                )
            )
    return tuple(sorted(domains, key=lambda item: (item.label_domain_id, item.kind.value, -1 if item.fold_index is None else item.fold_index)))


def build_blinded_prediction_domains(data5_bundle: Any) -> tuple[BlindedPredictionDomain, ...]:
    domains: list[BlindedPredictionDomain] = []
    data5_digest = data5_bundle.content_digest
    frame_cache: dict[tuple[str, ...], tuple[str, ...]] = {}

    def frames_for(unit_ids: Sequence[str]) -> tuple[str, ...]:
        key = tuple(unit_ids)
        value = frame_cache.get(key)
        if value is None:
            value = _frames_for_units(data5_bundle, key)
            frame_cache[key] = value
        return value

    mapping = (
        (OuterRole.OUTER_MONITOR, BlindedPredictionDomainKind.OUTER_MONITOR, PredictionMaterializationStatus.MATERIALIZED_BLINDED),
        (OuterRole.UNCERTAINTY_CALIBRATION, BlindedPredictionDomainKind.UNCERTAINTY_CALIBRATION, PredictionMaterializationStatus.MATERIALIZED_BLINDED),
        (OuterRole.LOCKED_INTERPOLATION_TEST, BlindedPredictionDomainKind.LOCKED_INTERPOLATION_TEST, PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED),
    )
    for outer in data5_bundle.outer_partitions:
        for role, kind, status in mapping:
            unit_ids = outer.units_for(role)
            if not unit_ids:
                continue
            domains.append(
                BlindedPredictionDomain(
                    label_domain_id=outer.label_domain_id,
                    kind=kind,
                    materialization_status=status,
                    data5_bundle_digest=data5_digest,
                    unit_ids=unit_ids,
                    frame_uids=frames_for(unit_ids),
                )
            )
    for plan in data5_bundle.cross_validation_plans:
        for fold in plan.folds:
            for unit_ids, kind in (
                (fold.checkpoint_monitor_unit_ids, BlindedPredictionDomainKind.CROSS_VALIDATION_CHECKPOINT_MONITOR),
                (fold.evaluation_unit_ids, BlindedPredictionDomainKind.CROSS_VALIDATION_EVALUATION),
            ):
                domains.append(
                    BlindedPredictionDomain(
                        label_domain_id=plan.label_domain_id,
                        kind=kind,
                        materialization_status=PredictionMaterializationStatus.MATERIALIZED_BLINDED,
                        data5_bundle_digest=data5_digest,
                        unit_ids=unit_ids,
                        frame_uids=frames_for(unit_ids),
                        fold_index=fold.fold_index,
                    )
                )
    return tuple(sorted(domains, key=lambda item: (item.label_domain_id, item.kind.value, -1 if item.fold_index is None else item.fold_index)))


def _prediction_for_frame(
    frame_uid: str,
    *,
    index: Mapping[str, tuple[Any, Any, int]],
    provider: AtomicModelProvider,
    prediction_cache: MutableMapping[str, AtomicModelPrediction] | None,
) -> tuple[Any, Any, int, AtomicModelPrediction]:
    record, frame_data, local_index = index[frame_uid]
    if prediction_cache is not None and frame_uid in prediction_cache:
        prediction = prediction_cache[frame_uid]
    else:
        atoms = ase_atoms_for_frame(record, frame_data, local_index)
        prediction = provider.predict(atoms)
        if prediction_cache is not None:
            prediction_cache[frame_uid] = prediction
    return record, frame_data, local_index, prediction


def _difficulty_record(
    record: Any,
    frame_data: Any,
    local_index: int,
    prediction: AtomicModelPrediction,
    checkpoint: ModelCheckpointIdentity,
) -> DifficultyFrameRecord:
    if frame_data.energies_ev is None or frame_data.forces_ev_per_angstrom is None:
        raise TrainingDataInputError("Difficulty features require DFT energy and force labels.")
    reference_energy = float(frame_data.energies_ev[local_index])
    reference_forces = np.asarray(frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64)
    predicted_forces = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
    if reference_forces.shape != predicted_forces.shape:
        raise TrainingDataInputError("Prediction/reference force shape mismatch.")
    delta = predicted_forces - reference_forces
    vector = np.linalg.norm(delta, axis=1)
    numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
    species = []
    for atomic_number in sorted(set(int(v) for v in numbers)):
        selected = delta[numbers == atomic_number]
        selected_vector = np.linalg.norm(selected, axis=1)
        species.append(
            SpeciesForceError(
                atomic_number=atomic_number,
                symbol=chemical_symbols[atomic_number],
                atom_count=int(selected.shape[0]),
                component_rmse_ev_per_angstrom=float(np.sqrt(np.mean(selected**2))),
                vector_error_mean_ev_per_angstrom=float(np.mean(selected_vector)),
                vector_error_max_ev_per_angstrom=float(np.max(selected_vector)),
            )
        )
    stress_rmse = None
    if frame_data.stresses_ev_per_angstrom3 is not None and prediction.stress_ev_per_angstrom3 is not None:
        reference_stress = np.asarray(frame_data.stresses_ev_per_angstrom3[local_index], dtype=np.float64)
        stress_rmse = float(np.sqrt(np.mean((prediction.stress_ev_per_angstrom3 - reference_stress) ** 2)))
    signed_energy_error = prediction.energy_ev - reference_energy
    return DifficultyFrameRecord(
        frame_uid=record.frame_uid,
        frame_record_digest=record.content_digest,
        checkpoint_identity_digest=checkpoint.content_digest,
        signed_energy_error_ev=signed_energy_error,
        absolute_energy_error_per_atom_ev=abs(signed_energy_error) / record.atom_count,
        force_component_rmse_ev_per_angstrom=float(np.sqrt(np.mean(delta**2))),
        force_vector_error_mean_ev_per_angstrom=float(np.mean(vector)),
        force_vector_error_max_ev_per_angstrom=float(np.max(vector)),
        stress_component_rmse_ev_per_angstrom3=stress_rmse,
        species_force_errors=tuple(species),
    )


def build_training_difficulty_feature_catalog(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    domain: TrainingDifficultyDomain,
    provider: AtomicModelProvider,
    *,
    prediction_cache: MutableMapping[str, AtomicModelPrediction] | None = None,
) -> TrainingDifficultyFeatureCatalog:
    if domain.data5_bundle_digest != data5_bundle.content_digest:
        raise TrainingDataInputError("Training-difficulty domain does not belong to DATA5 bundle.")
    valid_domains = {item.content_digest for item in build_training_difficulty_domains(data5_bundle)}
    if domain.content_digest not in valid_domains:
        raise TrainingDataInputError("Difficulty residuals require a canonical DATA5 training domain.")
    index = build_frame_array_index(frame_catalog, frame_data_by_run)
    records = []
    for frame_uid in domain.frame_uids:
        record, frame_data, local_index, prediction = _prediction_for_frame(
            frame_uid,
            index=index,
            provider=provider,
            prediction_cache=prediction_cache,
        )
        if record.label_domain_id != domain.label_domain_id:
            raise TrainingDataInputError("Difficulty domain crosses label domains.")
        records.append(_difficulty_record(record, frame_data, local_index, prediction, provider.checkpoint_identity))
    return TrainingDifficultyFeatureCatalog(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        domain=domain,
        checkpoint_identity=provider.checkpoint_identity,
        records=tuple(records),
    )


def build_blinded_evaluation_prediction_catalog(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    domain: BlindedPredictionDomain,
    provider: AtomicModelProvider,
    *,
    prediction_cache: MutableMapping[str, AtomicModelPrediction] | None = None,
) -> BlindedEvaluationPredictionCatalog:
    if domain.data5_bundle_digest != data5_bundle.content_digest:
        raise TrainingDataInputError("Blinded domain does not belong to DATA5 bundle.")
    valid_domains = {item.content_digest for item in build_blinded_prediction_domains(data5_bundle)}
    if domain.content_digest not in valid_domains:
        raise TrainingDataInputError("Prediction catalog requires a canonical DATA5 blinded domain.")
    records: list[ModelPredictionSummary] = []
    if domain.materialization_status is PredictionMaterializationStatus.MATERIALIZED_BLINDED:
        index = build_frame_array_index(frame_catalog, frame_data_by_run)
        for frame_uid in domain.frame_uids:
            record, frame_data, local_index, prediction = _prediction_for_frame(
                frame_uid,
                index=index,
                provider=provider,
                prediction_cache=prediction_cache,
            )
            if record.label_domain_id != domain.label_domain_id:
                raise TrainingDataInputError("Blinded prediction domain crosses label domains.")
            records.append(
                summarize_prediction(
                    record,
                    frame_data,
                    local_index,
                    prediction,
                    provider.checkpoint_identity,
                )
            )
    return BlindedEvaluationPredictionCatalog(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        domain=domain,
        checkpoint_identity=provider.checkpoint_identity,
        records=tuple(records),
    )


def build_model_evidence_catalogs(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    provider: AtomicModelProvider,
    *,
    build_training_difficulty: bool,
    build_blinded_predictions: bool,
    prediction_cache: MutableMapping[str, AtomicModelPrediction] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[
    tuple[TrainingDifficultyFeatureCatalog, ...],
    tuple[BlindedEvaluationPredictionCatalog, ...],
]:
    """Build all DATA6 model-evidence catalogs in one indexed frame pass.

    The historical per-domain builders intentionally remain public for focused
    use.  DATA6 orchestration, however, must not rebuild the complete frame
    index and the complete canonical-domain set for every domain.  This bulk
    path computes canonical domains once, indexes frame arrays once, reads each
    unique prediction at most once, and fans compact immutable summaries into
    the authorized catalogs.

    Complexity is ``O(N + M)`` where ``N`` is the number of unique requested
    frames and ``M`` is the total number of frame/domain memberships.  It avoids
    the former ``O(D * N + D**2)`` orchestration overhead and does not retain a
    campaign-sized collection of raw force arrays.
    """

    training_domains = (
        build_training_difficulty_domains(data5_bundle)
        if build_training_difficulty
        else ()
    )
    blinded_domains = (
        build_blinded_prediction_domains(data5_bundle)
        if build_blinded_predictions
        else ()
    )
    index = build_frame_array_index(frame_catalog, frame_data_by_run)

    training_membership: dict[str, list[int]] = {}
    for domain_index, domain in enumerate(training_domains):
        for frame_uid in domain.frame_uids:
            training_membership.setdefault(frame_uid, []).append(domain_index)

    blinded_membership: dict[str, list[int]] = {}
    for domain_index, domain in enumerate(blinded_domains):
        if domain.materialization_status is PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED:
            continue
        for frame_uid in domain.frame_uids:
            blinded_membership.setdefault(frame_uid, []).append(domain_index)

    requested = tuple(sorted(set(training_membership) | set(blinded_membership)))
    difficulty_by_frame: dict[str, DifficultyFrameRecord] = {}
    prediction_summary_by_frame: dict[str, ModelPredictionSummary] = {}
    total = len(requested)

    for completed, frame_uid in enumerate(requested, start=1):
        record, frame_data, local_index, prediction = _prediction_for_frame(
            frame_uid,
            index=index,
            provider=provider,
            prediction_cache=prediction_cache,
        )
        training_domain_indices = training_membership.get(frame_uid, ())
        blinded_domain_indices = blinded_membership.get(frame_uid, ())
        expected_labels = {
            training_domains[item].label_domain_id for item in training_domain_indices
        } | {
            blinded_domains[item].label_domain_id for item in blinded_domain_indices
        }
        if expected_labels != {record.label_domain_id}:
            raise TrainingDataInputError(
                "DATA6 model-evidence domains cross frame label-domain boundaries."
            )
        if training_domain_indices:
            difficulty_by_frame[frame_uid] = _difficulty_record(
                record,
                frame_data,
                local_index,
                prediction,
                provider.checkpoint_identity,
            )
        if blinded_domain_indices:
            prediction_summary_by_frame[frame_uid] = summarize_prediction(
                record,
                frame_data,
                local_index,
                prediction,
                provider.checkpoint_identity,
            )

        # A persistent sidecar cache verifies on read.  Retaining every force
        # array after its compact summaries have been produced only increases
        # RSS and can trigger swap-driven nonlinear slowdown.  Mapping
        # implementations may ignore deletion; the supplied persistent cache
        # releases its in-memory value while preserving its immutable record.
        if prediction_cache is not None:
            try:
                del prediction_cache[frame_uid]
            except KeyError:
                pass
        if progress_callback is not None:
            progress_callback(completed, total, frame_uid)

    difficulty_catalogs = tuple(
        TrainingDifficultyFeatureCatalog(
            dataset_id=frame_catalog.dataset_id,
            frame_catalog_digest=frame_catalog.content_digest,
            domain=domain,
            checkpoint_identity=provider.checkpoint_identity,
            records=tuple(difficulty_by_frame[uid] for uid in domain.frame_uids),
        )
        for domain in training_domains
    )
    blinded_catalogs = tuple(
        BlindedEvaluationPredictionCatalog(
            dataset_id=frame_catalog.dataset_id,
            frame_catalog_digest=frame_catalog.content_digest,
            domain=domain,
            checkpoint_identity=provider.checkpoint_identity,
            records=(
                ()
                if domain.materialization_status is PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED
                else tuple(prediction_summary_by_frame[uid] for uid in domain.frame_uids)
            ),
        )
        for domain in blinded_domains
    )
    return difficulty_catalogs, blinded_catalogs
