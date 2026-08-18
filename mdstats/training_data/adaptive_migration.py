"""ADAPT-MIGRATE1 schema authority and migration-closure evidence.

This module deliberately does not replace historical freeze records.  It provides a
small schema-aware authority layer so storage/restart code can validate either the
legacy committee freeze or the adaptive deployment freeze without guessing a record
type from the generic ``protocol_freeze`` key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

PROTOCOL_FREEZE_AUTHORITY_SCHEMA = "mdstats.protocol-freeze-authority.v1"
ADAPTIVE_MIGRATION_RECORD_SCHEMA = "mdstats.adaptive-migration-record.v1"
ADAPT_MIGRATE1_VERSION = "0.20.128a0"

_AUTHORITY_KINDS = {"historical_committee", "adaptive_deployment", "mlcv_deployment"}


@dataclass(frozen=True, slots=True)
class ProtocolFreezeAuthorityRecord:
    """Schema-neutral proof that a campaign has one authoritative frozen protocol.

    ``source_record_digest`` always points at the original scientific freeze record;
    this record is only an authority adapter for generic storage/lifecycle consumers.
    It never rewrites or weakens the underlying freeze evidence.
    """

    authority_kind: str
    campaign_plan_digest: str
    production_qualification_digest: str
    source_record_schema: str
    source_record_digest: str
    protected_model_sha256: tuple[str, ...]
    frozen_at_utc: str
    model_inference_dtype: str | None = None
    scientific_analysis_dtype: str | None = None

    def __post_init__(self) -> None:
        kind = str(self.authority_kind).strip()
        if kind not in _AUTHORITY_KINDS:
            raise TrainingDataInputError(
                "Protocol-freeze authority kind must be historical_committee, adaptive_deployment, or mlcv_deployment."
            )
        object.__setattr__(self, "authority_kind", kind)
        for name in (
            "campaign_plan_digest",
            "production_qualification_digest",
            "source_record_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        schema = str(self.source_record_schema).strip()
        if not schema:
            raise TrainingDataInputError(
                "Protocol-freeze authority requires a source record schema."
            )
        object.__setattr__(self, "source_record_schema", schema)
        models = tuple(
            validate_digest(str(value), name="protected_model_sha256")
            for value in self.protected_model_sha256
        )
        if not models or len(set(models)) != len(models):
            raise TrainingDataInputError(
                "Protocol-freeze authority requires distinct protected model SHA-256 identities."
            )
        object.__setattr__(self, "protected_model_sha256", models)
        if not str(self.frozen_at_utc).strip():
            raise TrainingDataInputError(
                "Protocol-freeze authority requires the source freeze timestamp."
            )
        if kind in {"adaptive_deployment", "mlcv_deployment"}:
            dtype = str(self.model_inference_dtype).strip().lower()
            if dtype not in {"float32", "float64"}:
                raise TrainingDataInputError(
                    "Deployment protocol-freeze authority requires float32 or float64 model inference dtype."
                )
            if str(self.scientific_analysis_dtype).strip().lower() != "float64":
                raise TrainingDataInputError(
                    "Deployment protocol-freeze authority requires float64 scientific arithmetic."
                )
            object.__setattr__(self, "model_inference_dtype", dtype)
            object.__setattr__(self, "scientific_analysis_dtype", "float64")
        else:
            # Historical committee records predate the binary model-dtype contract.
            # Preserve unknown dtype rather than inventing one during migration.
            if self.model_inference_dtype not in (None, ""):
                raise TrainingDataInputError(
                    "Historical protocol-freeze authority must not invent a model dtype."
                )
            if self.scientific_analysis_dtype not in (None, ""):
                raise TrainingDataInputError(
                    "Historical protocol-freeze authority must not invent an analysis dtype."
                )
            object.__setattr__(self, "model_inference_dtype", None)
            object.__setattr__(self, "scientific_analysis_dtype", None)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PROTOCOL_FREEZE_AUTHORITY_SCHEMA,
            "authority_kind": self.authority_kind,
            "campaign_plan_digest": self.campaign_plan_digest,
            "production_qualification_digest": self.production_qualification_digest,
            "source_record_schema": self.source_record_schema,
            "source_record_digest": self.source_record_digest,
            "protected_model_sha256": list(self.protected_model_sha256),
            "frozen_at_utc": self.frozen_at_utc,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProtocolFreezeAuthorityRecord":
        if payload.get("schema") != PROTOCOL_FREEZE_AUTHORITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported protocol-freeze authority schema."
            )
        result = cls(
            authority_kind=str(payload["authority_kind"]),
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            production_qualification_digest=str(payload["production_qualification_digest"]),
            source_record_schema=str(payload["source_record_schema"]),
            source_record_digest=str(payload["source_record_digest"]),
            protected_model_sha256=tuple(
                str(value) for value in payload["protected_model_sha256"]
            ),
            frozen_at_utc=str(payload["frozen_at_utc"]),
            model_inference_dtype=(
                None
                if payload.get("model_inference_dtype") in (None, "")
                else str(payload["model_inference_dtype"])
            ),
            scientific_analysis_dtype=(
                None
                if payload.get("scientific_analysis_dtype") in (None, "")
                else str(payload["scientific_analysis_dtype"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Protocol-freeze authority digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveMigrationRecord:
    """Immutable closure receipt for one completed adaptive campaign."""

    campaign_plan_digest: str
    adaptive_full_evaluation_digest: str
    adaptive_verification_digest: str
    adaptive_deployment_model_digest: str
    adaptive_protocol_freeze_digest: str
    protocol_freeze_authority_digest: str
    model_inference_dtype: str
    scientific_analysis_dtype: str
    historical_evidence_keys: tuple[str, ...]
    migrated_at_utc: str
    migrated_legacy_protocol_freeze_alias_schema: str | None = None
    migration_version: str = ADAPT_MIGRATE1_VERSION

    def __post_init__(self) -> None:
        for name in (
            "campaign_plan_digest",
            "adaptive_full_evaluation_digest",
            "adaptive_verification_digest",
            "adaptive_deployment_model_digest",
            "adaptive_protocol_freeze_digest",
            "protocol_freeze_authority_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError(
                "Adaptive migration model dtype must be float32 or float64."
            )
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError(
                "Adaptive migration scientific arithmetic must remain float64."
            )
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")
        keys = tuple(str(value) for value in self.historical_evidence_keys)
        if tuple(sorted(set(keys))) != keys:
            raise TrainingDataInputError(
                "Adaptive migration historical evidence keys must be sorted and unique."
            )
        object.__setattr__(self, "historical_evidence_keys", keys)
        if str(self.migration_version) != ADAPT_MIGRATE1_VERSION:
            raise TrainingDataInputError(
                f"Adaptive migration version must be {ADAPT_MIGRATE1_VERSION}."
            )
        if not str(self.migrated_at_utc).strip():
            raise TrainingDataInputError("Adaptive migration requires a timestamp.")
        legacy = self.migrated_legacy_protocol_freeze_alias_schema
        if legacy is not None and not str(legacy).strip():
            raise TrainingDataInputError(
                "Migrated legacy freeze-alias schema must be nonempty when present."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_MIGRATION_RECORD_SCHEMA,
            "migration_version": self.migration_version,
            "campaign_plan_digest": self.campaign_plan_digest,
            "adaptive_full_evaluation_digest": self.adaptive_full_evaluation_digest,
            "adaptive_verification_digest": self.adaptive_verification_digest,
            "adaptive_deployment_model_digest": self.adaptive_deployment_model_digest,
            "adaptive_protocol_freeze_digest": self.adaptive_protocol_freeze_digest,
            "protocol_freeze_authority_digest": self.protocol_freeze_authority_digest,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "historical_evidence_keys": list(self.historical_evidence_keys),
            "migrated_legacy_protocol_freeze_alias_schema": self.migrated_legacy_protocol_freeze_alias_schema,
            "migrated_at_utc": self.migrated_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveMigrationRecord":
        if payload.get("schema") != ADAPTIVE_MIGRATION_RECORD_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported adaptive migration-record schema."
            )
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            adaptive_full_evaluation_digest=str(payload["adaptive_full_evaluation_digest"]),
            adaptive_verification_digest=str(payload["adaptive_verification_digest"]),
            adaptive_deployment_model_digest=str(payload["adaptive_deployment_model_digest"]),
            adaptive_protocol_freeze_digest=str(payload["adaptive_protocol_freeze_digest"]),
            protocol_freeze_authority_digest=str(payload["protocol_freeze_authority_digest"]),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
            historical_evidence_keys=tuple(
                str(value) for value in payload.get("historical_evidence_keys", ())
            ),
            migrated_at_utc=str(payload["migrated_at_utc"]),
            migrated_legacy_protocol_freeze_alias_schema=(
                None
                if payload.get("migrated_legacy_protocol_freeze_alias_schema") in (None, "")
                else str(payload["migrated_legacy_protocol_freeze_alias_schema"])
            ),
            migration_version=str(payload.get("migration_version", ADAPT_MIGRATE1_VERSION)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Adaptive migration-record digest mismatch."
            )
        return result


def protocol_freeze_authority_from_historical(freeze: Any) -> ProtocolFreezeAuthorityRecord:
    """Adapt one verified historical ``ProtocolFreezeRecord`` without mutating it."""

    return ProtocolFreezeAuthorityRecord(
        authority_kind="historical_committee",
        campaign_plan_digest=str(freeze.campaign_plan_digest),
        production_qualification_digest=str(freeze.production_qualification_digest),
        source_record_schema="mdstats.protocol-freeze-record.v1",
        source_record_digest=str(freeze.content_digest),
        protected_model_sha256=tuple(str(v) for v in freeze.committee_member_model_sha256),
        frozen_at_utc=str(freeze.frozen_at_utc),
    )


def protocol_freeze_authority_from_adaptive(freeze: Any) -> ProtocolFreezeAuthorityRecord:
    """Adapt one verified ``AdaptiveProtocolFreezeRecord`` without mutating it."""

    return ProtocolFreezeAuthorityRecord(
        authority_kind="adaptive_deployment",
        campaign_plan_digest=str(freeze.campaign_plan_digest),
        production_qualification_digest=str(freeze.production_qualification_digest),
        source_record_schema="mdstats.adaptive-protocol-freeze.v1",
        source_record_digest=str(freeze.content_digest),
        protected_model_sha256=(str(freeze.exported_model_sha256),),
        frozen_at_utc=str(freeze.frozen_at_utc),
        model_inference_dtype=str(freeze.model_inference_dtype),
        scientific_analysis_dtype=str(freeze.scientific_analysis_dtype),
    )



def protocol_freeze_authority_from_mlcv(freeze: Any) -> ProtocolFreezeAuthorityRecord:
    """Adapt one verified ``MlcvProtocolFreezeRecord`` without mutating it."""

    return ProtocolFreezeAuthorityRecord(
        authority_kind="mlcv_deployment",
        campaign_plan_digest=str(freeze.campaign_plan_digest),
        production_qualification_digest=str(freeze.production_qualification_digest),
        source_record_schema=str(getattr(freeze, "serialization_schema", "mdstats.mlcv-protocol-freeze.v1")),
        source_record_digest=str(freeze.content_digest),
        protected_model_sha256=tuple(str(v) for v in freeze.protected_model_sha256),
        frozen_at_utc=str(freeze.frozen_at_utc),
        model_inference_dtype=str(freeze.model_inference_dtype),
        scientific_analysis_dtype=str(freeze.scientific_analysis_dtype),
    )

def protocol_freeze_authority_from_payload(
    payload: Mapping[str, Any],
) -> ProtocolFreezeAuthorityRecord:
    """Read current authority, legacy committee freeze, or 0.20.127 adaptive alias."""

    schema = payload.get("schema")
    if schema == PROTOCOL_FREEZE_AUTHORITY_SCHEMA:
        return ProtocolFreezeAuthorityRecord.from_dict(payload)
    if schema == "mdstats.protocol-freeze-record.v1":
        from .campaign_execution import ProtocolFreezeRecord

        return protocol_freeze_authority_from_historical(
            ProtocolFreezeRecord.from_dict(payload)
        )
    if schema in {"mdstats.mlcv-protocol-freeze.v1", "mdstats.mlcv-protocol-freeze.v2"}:
        from .mlcv_migration import MlcvProtocolFreezeRecord

        return protocol_freeze_authority_from_mlcv(
            MlcvProtocolFreezeRecord.from_dict(payload)
        )
    if schema == "mdstats.adaptive-protocol-freeze.v1":
        from .adaptive_verification import AdaptiveProtocolFreezeRecord

        return protocol_freeze_authority_from_adaptive(
            AdaptiveProtocolFreezeRecord.from_dict(payload)
        )
    raise TrainingDataSerializationError(
        f"Unsupported protocol-freeze authority source schema: {schema!r}."
    )


__all__ = [
    "PROTOCOL_FREEZE_AUTHORITY_SCHEMA",
    "ADAPTIVE_MIGRATION_RECORD_SCHEMA",
    "ADAPT_MIGRATE1_VERSION",
    "ProtocolFreezeAuthorityRecord",
    "AdaptiveMigrationRecord",
    "protocol_freeze_authority_from_historical",
    "protocol_freeze_authority_from_adaptive",
    "protocol_freeze_authority_from_mlcv",
    "protocol_freeze_authority_from_payload",
]
