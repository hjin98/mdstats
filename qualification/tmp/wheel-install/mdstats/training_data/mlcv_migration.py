"""MLCV-MIGRATE1 lifecycle identity, freeze authority, and migration closure.

The conventional-CV path is a scientific authority distinct from the historical
``adaptive_topk`` evaluator.  This module gives new MLCV campaigns an immutable
lifecycle identity at campaign construction, then freezes the complete ROLE1 ->
VERIFY1 evidence graph after production publication without rewriting older
adaptive or committee campaigns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest

MLCV_LIFECYCLE_AUTHORITY_SCHEMA = "mdstats.mlcv-lifecycle-authority.v2"
MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA = "mdstats.mlcv-lifecycle-authority.v1"
MLCV_LIFECYCLE_AUTHORITY_VERSION = "mdstats.mlcv-nested-cv-replay-degradation.2026-08.v2"
MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION = "mdstats.mlcv-nested-cv.2026-08.v1"
MLCV_PROTOCOL_FREEZE_SCHEMA = "mdstats.mlcv-protocol-freeze.v2"
MLCV_PROTOCOL_FREEZE_LEGACY_SCHEMA = "mdstats.mlcv-protocol-freeze.v1"
MLCV_MIGRATION_RECORD_SCHEMA = "mdstats.mlcv-migration-record.v2"
MLCV_MIGRATION_RECORD_LEGACY_SCHEMA = "mdstats.mlcv-migration-record.v1"
MLCV_MIGRATE1_VERSION = "0.20.140a0"
MLCV_MIGRATE1_LEGACY_VERSION = "0.20.139a0"
MLCV_CHECKPOINT_STRATEGY = "mlcv_nested_cv"
MLCV_TRANSITIONAL_STRATEGY_ALIAS = "adaptive_topk"


def _digests(values: Sequence[str], *, name: str, require_nonempty: bool = True) -> tuple[str, ...]:
    result = tuple(validate_digest(str(v), name=name) for v in values)
    if require_nonempty and not result:
        raise TrainingDataInputError(f"{name} requires at least one digest.")
    if len(set(result)) != len(result):
        raise TrainingDataInputError(f"{name} digests must be unique.")
    return result


@dataclass(frozen=True, slots=True)
class MlcvLifecycleAuthorityRecord:
    """Immutable evaluator-family identity for a conventional-CV campaign."""

    campaign_plan_digest: str
    role_catalog_digests: tuple[str, ...]
    monitor_catalog_digests: tuple[str, ...]
    source_checkpoint_strategy: str = MLCV_CHECKPOINT_STRATEGY
    checkpoint_strategy: str = MLCV_CHECKPOINT_STRATEGY
    candidate_limit_per_run: int = 5
    authority_version: str = MLCV_LIFECYCLE_AUTHORITY_VERSION
    serialization_schema: str = field(default=MLCV_LIFECYCLE_AUTHORITY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "campaign_plan_digest", validate_digest(self.campaign_plan_digest, name="campaign_plan_digest"))
        object.__setattr__(self, "role_catalog_digests", _digests(self.role_catalog_digests, name="role_catalog_digest"))
        object.__setattr__(self, "monitor_catalog_digests", _digests(self.monitor_catalog_digests, name="monitor_catalog_digest"))
        if self.checkpoint_strategy != MLCV_CHECKPOINT_STRATEGY:
            raise TrainingDataInputError(f"MLCV lifecycle checkpoint strategy must be {MLCV_CHECKPOINT_STRATEGY!r}.")
        source = str(self.source_checkpoint_strategy).strip().lower()
        if source not in {MLCV_CHECKPOINT_STRATEGY, MLCV_TRANSITIONAL_STRATEGY_ALIAS}:
            raise TrainingDataInputError("MLCV lifecycle source strategy is unsupported.")
        object.__setattr__(self, "source_checkpoint_strategy", source)
        if int(self.candidate_limit_per_run) != 5:
            raise TrainingDataInputError("MLCV lifecycle v1 requires run-local top-five candidate retention.")
        object.__setattr__(self, "candidate_limit_per_run", 5)
        expected_version = (MLCV_LIFECYCLE_AUTHORITY_VERSION if self.serialization_schema == MLCV_LIFECYCLE_AUTHORITY_SCHEMA else MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION)
        if self.serialization_schema not in {MLCV_LIFECYCLE_AUTHORITY_SCHEMA, MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA}:
            raise TrainingDataInputError("Unsupported MLCV lifecycle-authority schema.")
        if self.authority_version != expected_version:
            raise TrainingDataInputError("Unsupported MLCV lifecycle authority version.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "authority_version": self.authority_version,
            "campaign_plan_digest": self.campaign_plan_digest,
            "checkpoint_strategy": self.checkpoint_strategy,
            "source_checkpoint_strategy": self.source_checkpoint_strategy,
            "candidate_limit_per_run": self.candidate_limit_per_run,
            "role_catalog_digests": list(self.role_catalog_digests),
            "monitor_catalog_digests": list(self.monitor_catalog_digests),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvLifecycleAuthorityRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_LIFECYCLE_AUTHORITY_SCHEMA, MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MLCV lifecycle-authority schema.")
        default_version = MLCV_LIFECYCLE_AUTHORITY_VERSION if schema == MLCV_LIFECYCLE_AUTHORITY_SCHEMA else MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            role_catalog_digests=tuple(str(v) for v in payload["role_catalog_digests"]),
            monitor_catalog_digests=tuple(str(v) for v in payload["monitor_catalog_digests"]),
            source_checkpoint_strategy=str(payload.get("source_checkpoint_strategy", MLCV_CHECKPOINT_STRATEGY)),
            checkpoint_strategy=str(payload.get("checkpoint_strategy", MLCV_CHECKPOINT_STRATEGY)),
            candidate_limit_per_run=int(payload.get("candidate_limit_per_run", 5)),
            authority_version=str(payload.get("authority_version", default_version)),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV lifecycle-authority digest mismatch.")
        return result

    def permits_config_strategy(self, value: str) -> bool:
        strategy = str(value).strip().lower()
        return strategy == self.checkpoint_strategy or (
            self.source_checkpoint_strategy == MLCV_TRANSITIONAL_STRATEGY_ALIAS
            and strategy == MLCV_TRANSITIONAL_STRATEGY_ALIAS
        )


def build_mlcv_lifecycle_authority(
    campaign: Any,
    data8_bundles: Sequence[Any],
    *,
    source_checkpoint_strategy: str = MLCV_CHECKPOINT_STRATEGY,
) -> MlcvLifecycleAuthorityRecord | None:
    bundles = tuple(data8_bundles)
    flags = tuple(
        getattr(v, "mlcv_role_catalog", None) is not None
        and getattr(v, "mlcv_monitor_catalog", None) is not None
        for v in bundles
    )
    if not bundles or not any(flags):
        return None
    if not all(flags):
        raise TrainingDataInputError("Campaign mixes MLCV and pre-MLCV DATA8 authorities.")
    roles = tuple(sorted({v.mlcv_role_catalog.content_digest for v in bundles}))
    monitors = tuple(sorted({v.mlcv_monitor_catalog.content_digest for v in bundles}))
    return MlcvLifecycleAuthorityRecord(
        campaign_plan_digest=campaign.content_digest,
        role_catalog_digests=roles,
        monitor_catalog_digests=monitors,
        source_checkpoint_strategy=source_checkpoint_strategy,
    )


@dataclass(frozen=True, slots=True)
class MlcvProtocolFreezeRecord:
    """Scientific freeze of the complete conventional-CV production evidence graph."""

    production_qualification_digest: str
    campaign_plan_digest: str
    lifecycle_authority_digest: str
    lightweight_ranking_record_digests: tuple[str, ...]
    run_selection_record_digests: tuple[str, ...]
    campaign_cv_aggregate_digest: str
    final_selection_record_digest: str
    final_committee_record_digest: str
    verification_record_digest: str
    locked_test_record_digest: str
    production_model_record_digest: str
    protected_checkpoint_sha256: tuple[str, ...]
    protected_model_sha256: tuple[str, ...]
    model_inference_dtype: str
    scientific_analysis_dtype: str
    frozen_at_utc: str
    evaluation_authority: str = MLCV_LIFECYCLE_AUTHORITY_VERSION
    serialization_schema: str = field(default=MLCV_PROTOCOL_FREEZE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "production_qualification_digest", "campaign_plan_digest", "lifecycle_authority_digest",
            "campaign_cv_aggregate_digest", "final_selection_record_digest", "final_committee_record_digest",
            "verification_record_digest", "locked_test_record_digest", "production_model_record_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "lightweight_ranking_record_digests", _digests(self.lightweight_ranking_record_digests, name="lightweight_ranking_record_digest"))
        object.__setattr__(self, "run_selection_record_digests", _digests(self.run_selection_record_digests, name="run_selection_record_digest"))
        object.__setattr__(self, "protected_checkpoint_sha256", tuple(sorted(_digests(self.protected_checkpoint_sha256, name="protected_checkpoint_sha256"))))
        object.__setattr__(self, "protected_model_sha256", tuple(sorted(_digests(self.protected_model_sha256, name="protected_model_sha256"))))
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("MLCV freeze model dtype must be float32 or float64.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("MLCV freeze scientific arithmetic must remain float64.")
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")
        if self.serialization_schema not in {MLCV_PROTOCOL_FREEZE_SCHEMA, MLCV_PROTOCOL_FREEZE_LEGACY_SCHEMA}:
            raise TrainingDataInputError("Unsupported MLCV protocol-freeze schema.")
        expected_authority = (MLCV_LIFECYCLE_AUTHORITY_VERSION if self.serialization_schema == MLCV_PROTOCOL_FREEZE_SCHEMA else MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION)
        if self.evaluation_authority != expected_authority:
            raise TrainingDataInputError("MLCV protocol freeze has the wrong evaluation authority.")
        if not str(self.frozen_at_utc).strip():
            raise TrainingDataInputError("MLCV protocol freeze requires a timestamp.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "evaluation_authority": self.evaluation_authority,
            "production_qualification_digest": self.production_qualification_digest,
            "campaign_plan_digest": self.campaign_plan_digest,
            "lifecycle_authority_digest": self.lifecycle_authority_digest,
            "lightweight_ranking_record_digests": list(self.lightweight_ranking_record_digests),
            "run_selection_record_digests": list(self.run_selection_record_digests),
            "campaign_cv_aggregate_digest": self.campaign_cv_aggregate_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "final_committee_record_digest": self.final_committee_record_digest,
            "verification_record_digest": self.verification_record_digest,
            "locked_test_record_digest": self.locked_test_record_digest,
            "production_model_record_digest": self.production_model_record_digest,
            "protected_checkpoint_sha256": list(self.protected_checkpoint_sha256),
            "protected_model_sha256": list(self.protected_model_sha256),
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "frozen_at_utc": self.frozen_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvProtocolFreezeRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_PROTOCOL_FREEZE_SCHEMA, MLCV_PROTOCOL_FREEZE_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MLCV protocol-freeze schema.")
        default_authority = MLCV_LIFECYCLE_AUTHORITY_VERSION if schema == MLCV_PROTOCOL_FREEZE_SCHEMA else MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION
        result = cls(
            production_qualification_digest=str(payload["production_qualification_digest"]),
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            lifecycle_authority_digest=str(payload["lifecycle_authority_digest"]),
            lightweight_ranking_record_digests=tuple(str(v) for v in payload["lightweight_ranking_record_digests"]),
            run_selection_record_digests=tuple(str(v) for v in payload["run_selection_record_digests"]),
            campaign_cv_aggregate_digest=str(payload["campaign_cv_aggregate_digest"]),
            final_selection_record_digest=str(payload["final_selection_record_digest"]),
            final_committee_record_digest=str(payload["final_committee_record_digest"]),
            verification_record_digest=str(payload["verification_record_digest"]),
            locked_test_record_digest=str(payload["locked_test_record_digest"]),
            production_model_record_digest=str(payload["production_model_record_digest"]),
            protected_checkpoint_sha256=tuple(str(v) for v in payload["protected_checkpoint_sha256"]),
            protected_model_sha256=tuple(str(v) for v in payload["protected_model_sha256"]),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
            frozen_at_utc=str(payload["frozen_at_utc"]),
            evaluation_authority=str(payload.get("evaluation_authority", default_authority)),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV protocol-freeze digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvMigrationRecord:
    campaign_plan_digest: str
    lifecycle_authority_digest: str
    mlcv_protocol_freeze_digest: str
    protocol_freeze_authority_digest: str
    historical_evidence_keys: tuple[str, ...]
    migrated_at_utc: str
    migration_version: str = MLCV_MIGRATE1_VERSION
    serialization_schema: str = field(default=MLCV_MIGRATION_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "lifecycle_authority_digest", "mlcv_protocol_freeze_digest", "protocol_freeze_authority_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        keys = tuple(sorted(set(str(v) for v in self.historical_evidence_keys)))
        object.__setattr__(self, "historical_evidence_keys", keys)
        if self.serialization_schema not in {MLCV_MIGRATION_RECORD_SCHEMA, MLCV_MIGRATION_RECORD_LEGACY_SCHEMA}:
            raise TrainingDataInputError("Unsupported MLCV migration-record schema.")
        expected_version = MLCV_MIGRATE1_VERSION if self.serialization_schema == MLCV_MIGRATION_RECORD_SCHEMA else MLCV_MIGRATE1_LEGACY_VERSION
        if self.migration_version != expected_version:
            raise TrainingDataInputError(f"MLCV migration version must be {expected_version}.")
        if not str(self.migrated_at_utc).strip():
            raise TrainingDataInputError("MLCV migration requires a timestamp.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "migration_version": self.migration_version,
            "campaign_plan_digest": self.campaign_plan_digest,
            "lifecycle_authority_digest": self.lifecycle_authority_digest,
            "mlcv_protocol_freeze_digest": self.mlcv_protocol_freeze_digest,
            "protocol_freeze_authority_digest": self.protocol_freeze_authority_digest,
            "historical_evidence_keys": list(self.historical_evidence_keys),
            "migrated_at_utc": self.migrated_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvMigrationRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_MIGRATION_RECORD_SCHEMA, MLCV_MIGRATION_RECORD_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MLCV migration-record schema.")
        default_version = MLCV_MIGRATE1_VERSION if schema == MLCV_MIGRATION_RECORD_SCHEMA else MLCV_MIGRATE1_LEGACY_VERSION
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            lifecycle_authority_digest=str(payload["lifecycle_authority_digest"]),
            mlcv_protocol_freeze_digest=str(payload["mlcv_protocol_freeze_digest"]),
            protocol_freeze_authority_digest=str(payload["protocol_freeze_authority_digest"]),
            historical_evidence_keys=tuple(str(v) for v in payload.get("historical_evidence_keys", ())),
            migrated_at_utc=str(payload["migrated_at_utc"]),
            migration_version=str(payload.get("migration_version", default_version)),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV migration-record digest mismatch.")
        return result


def mlcv_replay_semantics_stale_boundary(evidence: Mapping[str, Any]) -> str | None:
    """Return the earliest replay-dependent gate that must be regenerated.

    Transitional MLCV evidence from 0.20.131a0--0.20.139a0 used absolute replay
    RMSE for STOP1/RANK1/SELECT1/AGG1/FINAL1.  It remains readable, but is not
    authoritative for a replay-degradation campaign.
    """
    schema = str(evidence.get("schema", ""))
    if schema in {
        "mdstats.adaptive-training-stop-state.v1", "mdstats.adaptive-training-stop-state.v2",
        "mdstats.adaptive-training-stop-policy.v1", "mdstats.adaptive-training-stop-policy.v2",
    }:
        return "MLCV-STOP1"
    if schema in {"mdstats.lightweight-checkpoint-score.v1", "mdstats.lightweight-run-champion.v1", "mdstats.lightweight-run-champion.v2"}:
        return "MLCV-RANK1"
    if schema in {"mdstats.mlcv-run-selection-policy.v1", "mdstats.mlcv-full-selection-candidate.v1", "mdstats.mlcv-run-selection-record.v1"}:
        return "MLCV-SELECT1"
    if schema in {"mdstats.mlcv-cross-validation-policy.v1", "mdstats.mlcv-outer-fold-evaluation.v1", "mdstats.mlcv-seed-cv-aggregate.v1", "mdstats.mlcv-campaign-cv-aggregate.v1"}:
        return "MLCV-AGG1"
    if schema in {"mdstats.mlcv-final-seed-candidate.v1", "mdstats.mlcv-final-selection-record.v1", "mdstats.mlcv-final-committee-member.v1", "mdstats.mlcv-final-committee.v1"}:
        return "MLCV-FINAL1"
    return None


__all__ = [
    "MLCV_LIFECYCLE_AUTHORITY_SCHEMA", "MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA", "MLCV_LIFECYCLE_AUTHORITY_VERSION", "MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION",
    "MLCV_PROTOCOL_FREEZE_SCHEMA", "MLCV_PROTOCOL_FREEZE_LEGACY_SCHEMA", "MLCV_MIGRATION_RECORD_SCHEMA", "MLCV_MIGRATION_RECORD_LEGACY_SCHEMA", "MLCV_MIGRATE1_VERSION", "MLCV_MIGRATE1_LEGACY_VERSION",
    "MLCV_CHECKPOINT_STRATEGY", "MLCV_TRANSITIONAL_STRATEGY_ALIAS",
    "MlcvLifecycleAuthorityRecord", "MlcvProtocolFreezeRecord", "MlcvMigrationRecord",
    "build_mlcv_lifecycle_authority", "mlcv_replay_semantics_stale_boundary",
]
