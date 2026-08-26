"""Protocol-matched campaign and checkpoint control for MLFF-DATA9B1.

This module deliberately does not launch MACE.  It freezes the exact DATA8 job
matrix, inventories immutable checkpoint files, applies the already-declared
checkpoint metric policy, and performs deterministic fail-closed selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .data8_bundle import Data8PreparationBundle
from .objectives import CheckpointMetricPolicy
from .production_qualification import (
    ProductionCorpusQualificationRecord,
    ProductionGateStatus,
)
from .protocol import MaceJobArtifact, MaceJobKind, TrainingMode
from .replay import ReplayLabelMode

TRAINING_CAMPAIGN_POLICY_SCHEMA = "mdstats.training-campaign-policy.v3"
TRAINING_CAMPAIGN_POLICY_V2_SCHEMA = "mdstats.training-campaign-policy.v2"
TRAINING_CAMPAIGN_POLICY_LEGACY_SCHEMA = "mdstats.training-campaign-policy.v1"
TRAINING_CAMPAIGN_RUN_PLAN_SCHEMA = "mdstats.training-campaign-run-plan.v1"
TRAINING_CAMPAIGN_PLAN_SCHEMA = "mdstats.training-campaign-plan.v1"
CHECKPOINT_FILE_RECORD_SCHEMA = "mdstats.checkpoint-file-record.v1"
CANDIDATE_CHECKPOINT_CATALOG_SCHEMA = "mdstats.candidate-checkpoint-catalog.v1"
CHECKPOINT_METRIC_RECORD_SCHEMA = "mdstats.checkpoint-metric-record.v2"
CHECKPOINT_METRIC_RECORD_LEGACY_SCHEMA = "mdstats.checkpoint-metric-record.v1"
PSEUDOLABEL_FOUNDATION_SELF_RMSE_TOLERANCE_EV_PER_ANGSTROM = 1.0e-3
CHECKPOINT_ADMISSIBILITY_DECISION_SCHEMA = "mdstats.checkpoint-admissibility-decision.v1"
CHECKPOINT_SELECTION_RECORD_SCHEMA = "mdstats.checkpoint-selection-record.v1"
MLFF_DATA9B1_VERSION = "0.20.56a0"


class CheckpointAdmissibilityOutcome(str, Enum):
    ADMISSIBLE = "admissible"
    REJECTED = "rejected"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _finite_nonnegative(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative when present.")
    return result


def _optimizer_family_payload(job: MaceJobArtifact) -> dict[str, Any]:
    payload = dict(job.protocol.optimizer_policy.to_dict())
    payload.pop("policy_digest", None)
    payload.pop("seed", None)
    return payload


def _protocol_family_payload(job: MaceJobArtifact) -> dict[str, Any]:
    protocol = job.protocol
    return {
        "schema": "mdstats.training-protocol-family.v1",
        "training_mode": protocol.training_mode.value,
        "foundation_checkpoint_digest": protocol.foundation_checkpoint.content_digest,
        "compatibility_probe_digest": protocol.compatibility_probe_digest,
        "replay_plan_digest": protocol.replay_plan_digest,
        "training_objective_policy_digest": protocol.training_objective_policy_digest,
        "configuration_weight_policy_digest": protocol.configuration_weight_policy_digest,
        "checkpoint_metric_policy_digest": protocol.checkpoint_metric_policy_digest,
        "checkpoint_control_policy_digest": protocol.checkpoint_control_policy.policy_digest,
        "optimizer_policy_without_seed": _optimizer_family_payload(job),
        "selection_size": protocol.selection_size,
        "exposure_backend": protocol.exposure_backend.value,
        "real_pt_data_ratio_threshold": protocol.real_pt_data_ratio_threshold,
    }


def protocol_family_digest(job: MaceJobArtifact) -> str:
    """Return the fold-local-data- and seed-independent protocol family digest."""

    return digest(_protocol_family_payload(job))


def protocol_variant_digest(job: MaceJobArtifact) -> str:
    """Return the protocol family plus scalar-seed identity."""

    return digest(
        {
            "schema": "mdstats.training-protocol-variant.v1",
            "family_digest": protocol_family_digest(job),
            "seed": job.protocol.optimizer_policy.seed,
        }
    )


@dataclass(frozen=True, slots=True)
class TrainingCampaignPolicy:
    required_seeds: tuple[int, ...] = (1,)
    required_training_modes: tuple[TrainingMode, ...] = (TrainingMode.MULTIHEAD_REPLAY,)
    required_selection_sizes: tuple[int, ...] = (512,)
    required_variants: tuple[tuple[TrainingMode, int, int, int], ...] = ()
    require_final_development: bool = True
    require_cross_validation: bool = True
    require_save_all_checkpoints: bool = True
    require_external_checkpoint_audit: bool = True
    required_execution_wrapper: str = "mdstats-mace-train"
    allow_additional_variants: bool = False
    acceleration_probe_digest: str | None = None

    def __post_init__(self) -> None:
        seeds = tuple(sorted(set(int(v) for v in self.required_seeds)))
        modes = tuple(sorted({TrainingMode(v) for v in self.required_training_modes}, key=lambda v: v.value))
        sizes = tuple(sorted(set(int(v) for v in self.required_selection_sizes)))
        variants = tuple(
            sorted(
                {
                    (TrainingMode(mode), int(size), int(seed), int(folds))
                    for mode, size, seed, folds in self.required_variants
                },
                key=lambda item: (item[0].value, item[1], item[2], item[3]),
            )
        )
        if not seeds or any(v < 0 for v in seeds):
            raise TrainingDataInputError("Training campaign requires nonnegative seeds.")
        if not modes:
            raise TrainingDataInputError("Training campaign requires at least one training mode.")
        if not sizes or any(v <= 0 for v in sizes):
            raise TrainingDataInputError("Training campaign selection sizes must be positive.")
        if variants and any(
            size <= 0 or seed < 0 or folds < 0 or folds == 1
            for _, size, seed, folds in variants
        ):
            raise TrainingDataInputError(
                "Training campaign variant requirements require positive sizes, nonnegative seeds, "
                "and either zero or at least two cross-validation folds."
            )
        if not self.required_execution_wrapper.strip():
            raise TrainingDataInputError("Training campaign execution wrapper must be non-empty.")
        if self.required_execution_wrapper == "mace_run_train":
            raise TrainingDataInputError("Production DATA9B must use the mdstats precision-aware MACE wrapper.")
        if self.acceleration_probe_digest is not None:
            object.__setattr__(
                self,
                "acceleration_probe_digest",
                validate_digest(self.acceleration_probe_digest, name="acceleration_probe_digest"),
            )
        object.__setattr__(self, "required_seeds", seeds)
        object.__setattr__(self, "required_training_modes", modes)
        object.__setattr__(self, "required_selection_sizes", sizes)
        object.__setattr__(self, "required_variants", variants)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_CAMPAIGN_POLICY_SCHEMA,
            "required_seeds": list(self.required_seeds),
            "required_training_modes": [v.value for v in self.required_training_modes],
            "required_selection_sizes": list(self.required_selection_sizes),
            "required_variants": [
                {
                    "training_mode": mode.value,
                    "selection_size": size,
                    "seed": seed,
                    "cross_validation_folds": folds,
                }
                for mode, size, seed, folds in self.required_variants
            ],
            "require_final_development": self.require_final_development,
            "require_cross_validation": self.require_cross_validation,
            "require_save_all_checkpoints": self.require_save_all_checkpoints,
            "require_external_checkpoint_audit": self.require_external_checkpoint_audit,
            "required_execution_wrapper": self.required_execution_wrapper,
            "allow_additional_variants": self.allow_additional_variants,
            "acceleration_probe_digest": self.acceleration_probe_digest,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingCampaignPolicy":
        if payload.get("schema") not in {
            TRAINING_CAMPAIGN_POLICY_SCHEMA,
            TRAINING_CAMPAIGN_POLICY_V2_SCHEMA,
            TRAINING_CAMPAIGN_POLICY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported training-campaign policy schema.")
        result = cls(
            required_seeds=tuple(int(v) for v in payload["required_seeds"]),
            required_training_modes=tuple(TrainingMode(v) for v in payload["required_training_modes"]),
            required_selection_sizes=tuple(int(v) for v in payload["required_selection_sizes"]),
            required_variants=tuple(
                (
                    TrainingMode(item["training_mode"]),
                    int(item["selection_size"]),
                    int(item["seed"]),
                    int(item["cross_validation_folds"]),
                )
                for item in payload.get("required_variants", ())
            ),
            require_final_development=bool(payload["require_final_development"]),
            require_cross_validation=bool(payload["require_cross_validation"]),
            require_save_all_checkpoints=bool(payload["require_save_all_checkpoints"]),
            require_external_checkpoint_audit=bool(payload["require_external_checkpoint_audit"]),
            required_execution_wrapper=str(payload["required_execution_wrapper"]),
            allow_additional_variants=bool(payload.get("allow_additional_variants", False)),
            acceleration_probe_digest=(
                None
                if payload.get("acceleration_probe_digest") is None
                else str(payload["acceleration_probe_digest"])
            ),
        )
        expected_digest = result.policy_digest
        if payload.get("schema") in {
            TRAINING_CAMPAIGN_POLICY_V2_SCHEMA,
            TRAINING_CAMPAIGN_POLICY_LEGACY_SCHEMA,
        }:
            legacy_payload = result._payload()
            legacy_payload["schema"] = payload.get("schema")
            legacy_payload.pop("required_variants", None)
            legacy_payload.pop("acceleration_probe_digest", None)
            if payload.get("schema") == TRAINING_CAMPAIGN_POLICY_V2_SCHEMA:
                legacy_payload["acceleration_probe_digest"] = result.acceleration_probe_digest
            expected_digest = digest(legacy_payload)
        if payload.get("policy_digest") not in (None, expected_digest):
            raise TrainingDataSerializationError("Training-campaign policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingCampaignRunPlan:
    run_id: str
    data8_bundle_digest: str
    mace_job_artifact_digest: str
    job_id: str
    kind: MaceJobKind
    fold_index: int | None
    training_mode: TrainingMode
    selection_size: int
    seed: int
    protocol_family_digest: str
    protocol_variant_digest: str
    protocol_digest: str
    checkpoint_metric_policy_digest: str
    target_monitor_artifact_digest: str
    replay_monitor_artifact_digest: str | None
    relative_output_directory: str
    execution_wrapper: str = "mdstats-mace-train"

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.job_id.strip() or not self.relative_output_directory.strip():
            raise TrainingDataInputError("Campaign run identifiers and output directory must be non-empty.")
        object.__setattr__(self, "kind", MaceJobKind(self.kind))
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        for name in (
            "data8_bundle_digest",
            "mace_job_artifact_digest",
            "protocol_family_digest",
            "protocol_variant_digest",
            "protocol_digest",
            "checkpoint_metric_policy_digest",
            "target_monitor_artifact_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.replay_monitor_artifact_digest is not None:
            object.__setattr__(
                self,
                "replay_monitor_artifact_digest",
                validate_digest(self.replay_monitor_artifact_digest, name="replay_monitor_artifact_digest"),
            )
        if self.kind is MaceJobKind.CROSS_VALIDATION_FOLD and self.fold_index is None:
            raise TrainingDataInputError("Cross-validation campaign runs require a fold index.")
        if self.kind is MaceJobKind.FINAL_DEVELOPMENT and self.fold_index is not None:
            raise TrainingDataInputError("Final-development campaign runs cannot carry a fold index.")
        if self.selection_size <= 0 or self.seed < 0:
            raise TrainingDataInputError("Campaign run selection size and seed are invalid.")
        if self.training_mode is TrainingMode.MULTIHEAD_REPLAY and self.replay_monitor_artifact_digest is None:
            raise TrainingDataInputError("Replay campaign runs require replay-monitor artifact lineage.")
        if self.training_mode is TrainingMode.NAIVE_FINE_TUNING and self.replay_monitor_artifact_digest is not None:
            raise TrainingDataInputError("Naive campaign runs cannot carry replay-monitor artifact lineage.")
        if self.execution_wrapper == "mace_run_train" or not self.execution_wrapper.strip():
            raise TrainingDataInputError("Campaign runs must use a non-raw mdstats MACE wrapper.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_CAMPAIGN_RUN_PLAN_SCHEMA,
            "run_id": self.run_id,
            "data8_bundle_digest": self.data8_bundle_digest,
            "mace_job_artifact_digest": self.mace_job_artifact_digest,
            "job_id": self.job_id,
            "kind": self.kind.value,
            "fold_index": self.fold_index,
            "training_mode": self.training_mode.value,
            "selection_size": self.selection_size,
            "seed": self.seed,
            "protocol_family_digest": self.protocol_family_digest,
            "protocol_variant_digest": self.protocol_variant_digest,
            "protocol_digest": self.protocol_digest,
            "checkpoint_metric_policy_digest": self.checkpoint_metric_policy_digest,
            "target_monitor_artifact_digest": self.target_monitor_artifact_digest,
            "replay_monitor_artifact_digest": self.replay_monitor_artifact_digest,
            "relative_output_directory": self.relative_output_directory,
            "execution_wrapper": self.execution_wrapper,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingCampaignRunPlan":
        if payload.get("schema") != TRAINING_CAMPAIGN_RUN_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-campaign run schema.")
        result = cls(
            run_id=str(payload["run_id"]),
            data8_bundle_digest=str(payload["data8_bundle_digest"]),
            mace_job_artifact_digest=str(payload["mace_job_artifact_digest"]),
            job_id=str(payload["job_id"]),
            kind=MaceJobKind(payload["kind"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            training_mode=TrainingMode(payload["training_mode"]),
            selection_size=int(payload["selection_size"]),
            seed=int(payload["seed"]),
            protocol_family_digest=str(payload["protocol_family_digest"]),
            protocol_variant_digest=str(payload["protocol_variant_digest"]),
            protocol_digest=str(payload["protocol_digest"]),
            checkpoint_metric_policy_digest=str(payload["checkpoint_metric_policy_digest"]),
            target_monitor_artifact_digest=str(payload["target_monitor_artifact_digest"]),
            replay_monitor_artifact_digest=None if payload.get("replay_monitor_artifact_digest") is None else str(payload["replay_monitor_artifact_digest"]),
            relative_output_directory=str(payload["relative_output_directory"]),
            execution_wrapper=str(payload["execution_wrapper"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-campaign run digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingCampaignPlan:
    campaign_id: str
    dataset_id: str
    production_qualification_digest: str
    production_plan_digest: str
    qualified_anchor_data8_bundle_digest: str
    policy: TrainingCampaignPolicy
    expected_cross_validation_fold_count: int
    runs: tuple[TrainingCampaignRunPlan, ...]
    data8_bundle_digests: tuple[str, ...]
    _run_by_id: dict[str, TrainingCampaignRunPlan] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _runs_by_variant: dict[
        tuple[TrainingMode, int, int], tuple[TrainingCampaignRunPlan, ...]
    ] = field(default_factory=dict, init=False, repr=False, compare=False)
    _runs_by_protocol_variant_digest: dict[
        str, tuple[TrainingCampaignRunPlan, ...]
    ] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.campaign_id.strip() or not self.dataset_id.strip():
            raise TrainingDataInputError("Training campaign identifiers must be non-empty.")
        for name in (
            "production_qualification_digest",
            "production_plan_digest",
            "qualified_anchor_data8_bundle_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        bundles = tuple(sorted(set(validate_digest(v, name="data8_bundle_digest") for v in self.data8_bundle_digests)))
        if self.qualified_anchor_data8_bundle_digest not in bundles:
            raise TrainingDataInputError("Campaign does not contain the DATA9A-qualified anchor DATA8 bundle.")
        if self.expected_cross_validation_fold_count < 0:
            raise TrainingDataInputError("Expected cross-validation fold count cannot be negative.")
        runs = tuple(sorted(self.runs, key=lambda v: (v.training_mode.value, v.selection_size, v.seed, v.kind.value, -1 if v.fold_index is None else v.fold_index)))
        if not runs:
            raise TrainingDataInputError("Training campaign requires at least one run.")
        if len({v.run_id for v in runs}) != len(runs):
            collisions: dict[str, list[TrainingCampaignRunPlan]] = {}
            for item in runs:
                collisions.setdefault(item.run_id, []).append(item)
            detail = "; ".join(
                f"{run_id} ({len(items)} jobs; bundles="
                + ",".join(sorted({item.data8_bundle_digest[:12] for item in items}))
                + ")"
                for run_id, items in sorted(collisions.items())
                if len(items) > 1
            )
            raise TrainingDataInputError(
                "Training campaign run IDs must be unique. Collisions: " + detail
            )
        if len({v.mace_job_artifact_digest for v in runs}) != len(runs):
            raise TrainingDataInputError("Training campaign DATA8 job identities must be unique.")
        if any(v.data8_bundle_digest not in bundles for v in runs):
            raise TrainingDataInputError("Training campaign run references an undeclared DATA8 bundle.")
        if any(v.execution_wrapper != self.policy.required_execution_wrapper for v in runs):
            raise TrainingDataInputError("Training campaign execution-wrapper mismatch.")

        grouped_runs: dict[
            tuple[TrainingMode, int, int], list[TrainingCampaignRunPlan]
        ] = {}
        for run in runs:
            grouped_runs.setdefault(
                (run.training_mode, run.selection_size, run.seed), []
            ).append(run)
        observed_combinations = set(grouped_runs)
        if self.policy.required_variants:
            required_combinations = {
                (mode, size, seed)
                for mode, size, seed, _ in self.policy.required_variants
            }
            expected_fold_count_by_combination = {
                (mode, size, seed): folds
                for mode, size, seed, folds in self.policy.required_variants
            }
        else:
            required_combinations = {
                (mode, size, seed)
                for mode in self.policy.required_training_modes
                for size in self.policy.required_selection_sizes
                for seed in self.policy.required_seeds
            }
            expected_fold_count_by_combination = {
                combination: self.expected_cross_validation_fold_count
                for combination in required_combinations
            }
        if self.policy.allow_additional_variants:
            if not required_combinations.issubset(observed_combinations):
                raise TrainingDataInputError("Training campaign is missing required mode/size/seed variants.")
        elif observed_combinations != required_combinations:
            raise TrainingDataInputError("Training campaign mode/size/seed matrix does not match policy exactly.")

        for combination in sorted(observed_combinations, key=lambda v: (v[0].value, v[1], v[2])):
            subset = tuple(grouped_runs[combination])
            family_digests = {v.protocol_family_digest for v in subset}
            variant_digests = {v.protocol_variant_digest for v in subset}
            if len(family_digests) != 1 or len(variant_digests) != 1:
                raise TrainingDataInputError("Fold/final jobs in a campaign variant are not protocol-matched.")
            finals = tuple(v for v in subset if v.kind is MaceJobKind.FINAL_DEVELOPMENT)
            folds = tuple(v for v in subset if v.kind is MaceJobKind.CROSS_VALIDATION_FOLD)
            if self.policy.require_final_development and len(finals) != 1:
                raise TrainingDataInputError("Each campaign variant requires exactly one final-development job.")
            if not self.policy.require_final_development and finals:
                raise TrainingDataInputError("Campaign policy forbids final-development jobs.")
            expected_fold_count = expected_fold_count_by_combination.get(
                combination, self.expected_cross_validation_fold_count
            )
            expected_folds = set(range(expected_fold_count)) if self.policy.require_cross_validation else set()
            observed_folds = {int(v.fold_index) for v in folds if v.fold_index is not None}
            if observed_folds != expected_folds:
                raise TrainingDataInputError("Campaign cross-validation fold coverage is incomplete or unexpected.")

        object.__setattr__(self, "runs", runs)
        object.__setattr__(self, "data8_bundle_digests", bundles)
        object.__setattr__(self, "_run_by_id", {item.run_id: item for item in runs})
        object.__setattr__(
            self,
            "_runs_by_variant",
            {key: tuple(value) for key, value in grouped_runs.items()},
        )
        by_protocol_variant: dict[str, list[TrainingCampaignRunPlan]] = {}
        for run in runs:
            by_protocol_variant.setdefault(run.protocol_variant_digest, []).append(run)
        object.__setattr__(
            self,
            "_runs_by_protocol_variant_digest",
            {key: tuple(value) for key, value in by_protocol_variant.items()},
        )

    def run(self, run_id: str) -> TrainingCampaignRunPlan:
        try:
            return self._run_by_id[run_id]
        except KeyError:
            raise TrainingDataInputError(f"Unknown campaign run ID {run_id!r}.") from None

    def runs_for_variant(
        self, training_mode: TrainingMode | str, selection_size: int, seed: int
    ) -> tuple[TrainingCampaignRunPlan, ...]:
        return self._runs_by_variant.get(
            (TrainingMode(training_mode), int(selection_size), int(seed)), ()
        )

    def runs_for_protocol_variant_digest(
        self, protocol_variant_digest: str
    ) -> tuple[TrainingCampaignRunPlan, ...]:
        key = validate_digest(
            protocol_variant_digest, name="protocol_variant_digest"
        )
        return self._runs_by_protocol_variant_digest.get(key, ())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_CAMPAIGN_PLAN_SCHEMA,
            "parser_version": MLFF_DATA9B1_VERSION,
            "campaign_id": self.campaign_id,
            "dataset_id": self.dataset_id,
            "production_qualification_digest": self.production_qualification_digest,
            "production_plan_digest": self.production_plan_digest,
            "qualified_anchor_data8_bundle_digest": self.qualified_anchor_data8_bundle_digest,
            "policy": self.policy.to_dict(),
            "expected_cross_validation_fold_count": self.expected_cross_validation_fold_count,
            "runs": [v.to_dict() for v in self.runs],
            "data8_bundle_digests": list(self.data8_bundle_digests),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingCampaignPlan":
        if payload.get("schema") != TRAINING_CAMPAIGN_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-campaign plan schema.")
        if payload.get("parser_version") not in (None, MLFF_DATA9B1_VERSION):
            raise TrainingDataSerializationError("Unsupported DATA9B1 parser version.")
        result = cls(
            campaign_id=str(payload["campaign_id"]),
            dataset_id=str(payload["dataset_id"]),
            production_qualification_digest=str(payload["production_qualification_digest"]),
            production_plan_digest=str(payload["production_plan_digest"]),
            qualified_anchor_data8_bundle_digest=str(payload["qualified_anchor_data8_bundle_digest"]),
            policy=TrainingCampaignPolicy.from_dict(payload["policy"]),
            expected_cross_validation_fold_count=int(payload["expected_cross_validation_fold_count"]),
            runs=tuple(TrainingCampaignRunPlan.from_dict(v) for v in payload["runs"]),
            data8_bundle_digests=tuple(str(v) for v in payload["data8_bundle_digests"]),
        )
        stored_digest = payload.get("content_digest")
        if stored_digest is not None:
            # ``TrainingCampaignPolicy`` is intentionally migrated while loading
            # older campaign records (for example v2 -> v3 when method-specific
            # seed/fold controls were added).  Re-serializing that migrated policy
            # changes the *current* plan digest even though the original record is
            # byte-for-byte intact and every nested policy/run digest has already
            # been verified.  Accept either the current canonical digest or the
            # canonical digest of the exact serialized legacy payload.  The latter
            # is still fail-closed: changing any stored field without updating its
            # recorded digest is rejected, and nested records retain their own
            # independent digest checks.
            serialized_payload = dict(payload)
            serialized_payload.pop("content_digest", None)
            serialized_digest = digest(serialized_payload)
            if stored_digest not in (result.content_digest, serialized_digest):
                raise TrainingDataSerializationError(
                    "Training-campaign plan digest mismatch."
                )
        return result


def build_training_campaign_plan(
    qualification: ProductionCorpusQualificationRecord,
    data8_bundles: Sequence[Data8PreparationBundle],
    *,
    campaign_id: str,
    policy: TrainingCampaignPolicy,
    run_namespace: str = "",
) -> TrainingCampaignPlan:
    """Build a fail-closed protocol-matched DATA9B campaign plan."""

    if qualification.status is not ProductionGateStatus.PASSED or not qualification.full_data9a_passed:
        raise TrainingDataInputError("DATA9B campaign planning requires a passed full DATA9A qualification record.")
    if qualification.data8_bundle_digest is None:
        raise TrainingDataInputError("Passed DATA9A qualification lacks a DATA8 bundle digest.")
    bundles = tuple(data8_bundles)
    if not bundles:
        raise TrainingDataInputError("DATA9B campaign planning requires DATA8 bundles.")
    if qualification.data8_bundle_digest not in {v.content_digest for v in bundles}:
        raise TrainingDataInputError("DATA9B campaign does not contain the qualified anchor DATA8 bundle.")

    anchor = next(v for v in bundles if v.content_digest == qualification.data8_bundle_digest)
    for bundle in bundles:
        if bundle.dataset_id != qualification.dataset_id:
            raise TrainingDataInputError("DATA8 campaign bundle dataset mismatch.")
        if bundle.source_catalog_digest != qualification.source_catalog_digest:
            raise TrainingDataInputError("DATA8 campaign bundle source-catalog mismatch.")
        if bundle.frame_catalog_digest != qualification.frame_catalog_digest:
            raise TrainingDataInputError("DATA8 campaign bundle frame-catalog mismatch.")
        if qualification.data5_bundle_digest is not None and bundle.data5_bundle_digest != qualification.data5_bundle_digest:
            raise TrainingDataInputError("DATA8 campaign bundle DATA5 lineage mismatch.")
        if bundle.compatibility_probe.content_digest != anchor.compatibility_probe.content_digest:
            raise TrainingDataInputError("DATA8 campaign bundles use different MACE compatibility probes.")

    namespace = str(run_namespace).strip()
    if namespace and any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in namespace):
        raise TrainingDataInputError("Training campaign run namespace must be lowercase filesystem-safe text.")
    prefix = "" if not namespace else f"{namespace}-"
    run_plans: list[TrainingCampaignRunPlan] = []
    for bundle in bundles:
        for job in bundle.jobs:
            checkpoint_control = job.protocol.checkpoint_control_policy
            if policy.require_save_all_checkpoints and not checkpoint_control.save_all_checkpoints:
                raise TrainingDataInputError("Campaign requires save-all checkpoint control.")
            if policy.require_external_checkpoint_audit and not checkpoint_control.require_external_checkpoint_audit:
                raise TrainingDataInputError("Campaign requires external checkpoint audit.")
            seed = job.protocol.optimizer_policy.seed
            mode = job.protocol.training_mode
            size = job.protocol.selection_size
            fold_label = "final" if job.fold_index is None else f"fold-{job.fold_index:02d}"
            run_id = f"{prefix}{mode.value}-n{size}-seed{seed}-{fold_label}"
            run_plans.append(
                TrainingCampaignRunPlan(
                    run_id=run_id,
                    data8_bundle_digest=bundle.content_digest,
                    mace_job_artifact_digest=job.content_digest,
                    job_id=job.job_id,
                    kind=job.kind,
                    fold_index=job.fold_index,
                    training_mode=mode,
                    selection_size=size,
                    seed=seed,
                    protocol_family_digest=protocol_family_digest(job),
                    protocol_variant_digest=protocol_variant_digest(job),
                    protocol_digest=job.protocol.content_digest,
                    checkpoint_metric_policy_digest=job.protocol.checkpoint_metric_policy_digest,
                    target_monitor_artifact_digest=job.target_valid_artifact_digest,
                    replay_monitor_artifact_digest=(None if bundle.replay_plan.monitor_artifact is None else bundle.replay_plan.monitor_artifact.content_digest),
                    relative_output_directory=job.relative_directory,
                    execution_wrapper=policy.required_execution_wrapper,
                )
            )

    return TrainingCampaignPlan(
        campaign_id=campaign_id,
        dataset_id=qualification.dataset_id,
        production_qualification_digest=qualification.content_digest,
        production_plan_digest=qualification.production_plan_digest,
        qualified_anchor_data8_bundle_digest=qualification.data8_bundle_digest,
        policy=policy,
        expected_cross_validation_fold_count=qualification.cross_validation_fold_count,
        runs=tuple(run_plans),
        data8_bundle_digests=tuple(v.content_digest for v in bundles),
    )


@dataclass(frozen=True, slots=True)
class CheckpointFileRecord:
    run_plan_digest: str
    candidate_id: str
    epoch: int
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_plan_digest", validate_digest(self.run_plan_digest, name="run_plan_digest"))
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        if not self.candidate_id.strip() or not self.relative_path.strip():
            raise TrainingDataInputError("Checkpoint candidate ID and relative path must be non-empty.")
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise TrainingDataInputError("Checkpoint path must be contained and relative.")
        if self.epoch < 0 or self.size_bytes <= 0:
            raise TrainingDataInputError("Checkpoint epoch and byte size are invalid.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_FILE_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "candidate_id": self.candidate_id,
            "epoch": self.epoch,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointFileRecord":
        if payload.get("schema") != CHECKPOINT_FILE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-file schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            candidate_id=str(payload["candidate_id"]),
            epoch=int(payload["epoch"]),
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            size_bytes=int(payload["size_bytes"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Checkpoint-file digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CandidateCheckpointCatalog:
    run_plan_digest: str
    root_directory: str
    checkpoints: tuple[CheckpointFileRecord, ...]
    pattern: str
    _by_sha256: dict[str, CheckpointFileRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_plan_digest", validate_digest(self.run_plan_digest, name="run_plan_digest"))
        if not self.root_directory.strip() or not self.pattern.strip():
            raise TrainingDataInputError("Checkpoint catalog root and pattern must be non-empty.")
        checkpoints = tuple(sorted(self.checkpoints, key=lambda v: (v.epoch, v.sha256)))
        if not checkpoints:
            raise TrainingDataInputError("Checkpoint catalog cannot be empty.")
        if any(v.run_plan_digest != self.run_plan_digest for v in checkpoints):
            raise TrainingDataInputError("Checkpoint catalog run-plan lineage mismatch.")
        if len({v.epoch for v in checkpoints}) != len(checkpoints):
            raise TrainingDataInputError("Checkpoint catalog contains duplicate epochs.")
        if len({v.relative_path for v in checkpoints}) != len(checkpoints):
            raise TrainingDataInputError("Checkpoint catalog contains duplicate paths.")
        if len({v.sha256 for v in checkpoints}) != len(checkpoints):
            raise TrainingDataInputError("Checkpoint catalog contains duplicate file content.")
        object.__setattr__(self, "checkpoints", checkpoints)
        object.__setattr__(self, "_by_sha256", {item.sha256: item for item in checkpoints})

    def checkpoint_by_sha256(self, sha256: str) -> CheckpointFileRecord:
        key = validate_digest(sha256, name="checkpoint_sha256")
        try:
            return self._by_sha256[key]
        except KeyError:
            raise TrainingDataInputError(
                "Checkpoint is not present in the candidate catalog."
            ) from None

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": CANDIDATE_CHECKPOINT_CATALOG_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoints": [v.to_dict() for v in self.checkpoints],
            "pattern": self.pattern,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "root_directory": self.root_directory,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CandidateCheckpointCatalog":
        if payload.get("schema") != CANDIDATE_CHECKPOINT_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-catalog schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            root_directory=str(payload["root_directory"]),
            checkpoints=tuple(CheckpointFileRecord.from_dict(v) for v in payload["checkpoints"]),
            pattern=str(payload["pattern"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Checkpoint-catalog digest mismatch.")
        return result


def inventory_mace_checkpoints(
    run_plan: TrainingCampaignRunPlan,
    root_directory: str | Path,
    *,
    pattern: str = "*.pt",
    epoch_pattern: str = r"(?:epoch[-_]?)(\d+)",
) -> CandidateCheckpointCatalog:
    """Inventory checkpoint bytes without importing or trusting MACE metadata."""

    root = Path(root_directory).resolve()
    if not root.is_dir():
        raise TrainingDataInputError(f"Checkpoint root does not exist: {root!s}.")
    regex = re.compile(epoch_pattern)
    records: list[CheckpointFileRecord] = []
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:  # pragma: no cover - rglob containment is defensive
            raise TrainingDataInputError("Checkpoint file escaped the declared output root.") from exc
        match = regex.search(path.name)
        if match is None:
            raise TrainingDataInputError(f"Cannot determine checkpoint epoch from {path.name!r}.")
        epoch = int(match.group(1))
        sha = _sha256_file(path)
        records.append(
            CheckpointFileRecord(
                run_plan_digest=run_plan.content_digest,
                candidate_id=f"{run_plan.run_id}:epoch-{epoch}",
                epoch=epoch,
                relative_path=relative.as_posix(),
                sha256=sha,
                size_bytes=path.stat().st_size,
            )
        )
    return CandidateCheckpointCatalog(
        run_plan_digest=run_plan.content_digest,
        root_directory=str(root),
        checkpoints=tuple(records),
        pattern=pattern,
    )


@dataclass(frozen=True, slots=True)
class CheckpointMetricRecord:
    run_plan_digest: str
    checkpoint_sha256: str
    target_monitor_artifact_digest: str
    energy_mae_ev_per_atom: float | None
    force_component_rmse_ev_per_angstrom: float | None
    focus_force_rmse_ev_per_angstrom: tuple[tuple[str, float], ...] = ()
    stress_rmse_ev_per_angstrom3: float | None = None
    worst_condition_force_rmse_ev_per_angstrom: float | None = None
    target_combined_loss: float | None = None
    replay_monitor_artifact_digest: str | None = None
    replay_baseline_metric: float | None = None
    replay_candidate_metric: float | None = None
    replay_degradation_fraction: float | None = None
    replay_label_mode: ReplayLabelMode | None = None
    evaluation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_plan_digest", validate_digest(self.run_plan_digest, name="run_plan_digest"))
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        object.__setattr__(self, "target_monitor_artifact_digest", validate_digest(self.target_monitor_artifact_digest, name="target_monitor_artifact_digest"))
        if self.replay_monitor_artifact_digest is not None:
            object.__setattr__(self, "replay_monitor_artifact_digest", validate_digest(self.replay_monitor_artifact_digest, name="replay_monitor_artifact_digest"))
        for name in (
            "energy_mae_ev_per_atom",
            "force_component_rmse_ev_per_angstrom",
            "stress_rmse_ev_per_angstrom3",
            "worst_condition_force_rmse_ev_per_angstrom",
            "target_combined_loss",
            "replay_baseline_metric",
            "replay_candidate_metric",
            "replay_degradation_fraction",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        focus = tuple(sorted((str(key).strip(), _finite_nonnegative(value, name=f"focus_force_rmse[{key}]") or 0.0) for key, value in self.focus_force_rmse_ev_per_angstrom))
        if any(not key for key, _ in focus) or len({key for key, _ in focus}) != len(focus):
            raise TrainingDataInputError("Focus-force metric IDs must be unique and non-empty.")
        object.__setattr__(self, "focus_force_rmse_ev_per_angstrom", focus)
        object.__setattr__(self, "evaluation_notes", tuple(str(v) for v in self.evaluation_notes))
        if self.replay_label_mode is not None:
            object.__setattr__(self, "replay_label_mode", ReplayLabelMode(self.replay_label_mode))
        replay_core = (
            self.replay_monitor_artifact_digest,
            self.replay_baseline_metric,
            self.replay_candidate_metric,
        )
        if any(v is not None for v in replay_core) and not all(v is not None for v in replay_core):
            raise TrainingDataInputError("Replay metric evidence must be complete and include monitor, baseline, and candidate values together.")
        if all(v is None for v in replay_core):
            if self.replay_degradation_fraction is not None or self.replay_label_mode is not None:
                raise TrainingDataInputError("Replay provenance or degradation cannot be present without replay metrics.")
        elif self.replay_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
            # A foundation model compared with its own pseudo-labels has a near-zero
            # denominator.  Relative degradation is mathematically ill-conditioned
            # and is intentionally omitted; candidate disagreement remains diagnostic.
            if self.replay_degradation_fraction is not None:
                raise TrainingDataInputError(
                    "Foundation-pseudolabel replay must not carry a relative degradation fraction."
                )
        elif self.replay_degradation_fraction is None:
            raise TrainingDataInputError(
                "True-label or legacy replay metrics require a relative degradation fraction."
            )

    @property
    def maximum_focus_force_rmse(self) -> float | None:
        if not self.focus_force_rmse_ev_per_angstrom:
            return None
        return max(value for _, value in self.focus_force_rmse_ev_per_angstrom)

    def primary_metric_value(self, policy: CheckpointMetricPolicy) -> float | None:
        if policy.primary_metric == "target_force_component_rmse":
            return self.force_component_rmse_ev_per_angstrom
        if policy.primary_metric == "target_energy_mae_per_atom":
            return self.energy_mae_ev_per_atom
        if policy.primary_metric == "target_combined_loss":
            return self.target_combined_loss
        raise TrainingDataInputError("Unsupported checkpoint primary metric.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_METRIC_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "target_monitor_artifact_digest": self.target_monitor_artifact_digest,
            "energy_mae_ev_per_atom": self.energy_mae_ev_per_atom,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
            "focus_force_rmse_ev_per_angstrom": dict(self.focus_force_rmse_ev_per_angstrom),
            "stress_rmse_ev_per_angstrom3": self.stress_rmse_ev_per_angstrom3,
            "worst_condition_force_rmse_ev_per_angstrom": self.worst_condition_force_rmse_ev_per_angstrom,
            "target_combined_loss": self.target_combined_loss,
            "replay_monitor_artifact_digest": self.replay_monitor_artifact_digest,
            "replay_baseline_metric": self.replay_baseline_metric,
            "replay_candidate_metric": self.replay_candidate_metric,
            "replay_degradation_fraction": self.replay_degradation_fraction,
            "replay_label_mode": None if self.replay_label_mode is None else self.replay_label_mode.value,
            "evaluation_notes": list(self.evaluation_notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointMetricRecord":
        schema = payload.get("schema")
        if schema not in (CHECKPOINT_METRIC_RECORD_SCHEMA, CHECKPOINT_METRIC_RECORD_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported checkpoint-metric-record schema.")
        replay_label_mode = (
            None
            if payload.get("replay_label_mode") is None
            else ReplayLabelMode(payload["replay_label_mode"])
        )
        degradation = None if payload.get("replay_degradation_fraction") is None else float(payload["replay_degradation_fraction"])
        # Legacy v1 records did not store replay-label provenance.  Preserve the
        # legacy fraction until the caller binds the immutable ReplayFileArtifact.
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            target_monitor_artifact_digest=str(payload["target_monitor_artifact_digest"]),
            energy_mae_ev_per_atom=None if payload.get("energy_mae_ev_per_atom") is None else float(payload["energy_mae_ev_per_atom"]),
            force_component_rmse_ev_per_angstrom=None if payload.get("force_component_rmse_ev_per_angstrom") is None else float(payload["force_component_rmse_ev_per_angstrom"]),
            focus_force_rmse_ev_per_angstrom=tuple((str(k), float(v)) for k, v in payload.get("focus_force_rmse_ev_per_angstrom", {}).items()),
            stress_rmse_ev_per_angstrom3=None if payload.get("stress_rmse_ev_per_angstrom3") is None else float(payload["stress_rmse_ev_per_angstrom3"]),
            worst_condition_force_rmse_ev_per_angstrom=None if payload.get("worst_condition_force_rmse_ev_per_angstrom") is None else float(payload["worst_condition_force_rmse_ev_per_angstrom"]),
            target_combined_loss=None if payload.get("target_combined_loss") is None else float(payload["target_combined_loss"]),
            replay_monitor_artifact_digest=None if payload.get("replay_monitor_artifact_digest") is None else str(payload["replay_monitor_artifact_digest"]),
            replay_baseline_metric=None if payload.get("replay_baseline_metric") is None else float(payload["replay_baseline_metric"]),
            replay_candidate_metric=None if payload.get("replay_candidate_metric") is None else float(payload["replay_candidate_metric"]),
            replay_degradation_fraction=degradation,
            replay_label_mode=replay_label_mode,
            evaluation_notes=tuple(str(v) for v in payload.get("evaluation_notes", ())),
        )
        if schema == CHECKPOINT_METRIC_RECORD_LEGACY_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("content_digest", None)
            expected = digest(legacy_payload)
        else:
            expected = result.content_digest
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Checkpoint metric-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CheckpointAdmissibilityDecision:
    run_plan_digest: str
    checkpoint_sha256: str
    checkpoint_metric_record_digest: str
    checkpoint_metric_policy_digest: str
    outcome: CheckpointAdmissibilityOutcome
    primary_metric_name: str
    primary_metric_value: float | None
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "checkpoint_sha256",
            "checkpoint_metric_record_digest",
            "checkpoint_metric_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "outcome", CheckpointAdmissibilityOutcome(self.outcome))
        object.__setattr__(self, "primary_metric_value", _finite_nonnegative(self.primary_metric_value, name="primary_metric_value"))
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.outcome is CheckpointAdmissibilityOutcome.ADMISSIBLE and reasons:
            raise TrainingDataInputError("Admissible checkpoint cannot carry rejection reasons.")
        if self.outcome is CheckpointAdmissibilityOutcome.REJECTED and not reasons:
            raise TrainingDataInputError("Rejected checkpoint requires reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_ADMISSIBILITY_DECISION_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_metric_record_digest": self.checkpoint_metric_record_digest,
            "checkpoint_metric_policy_digest": self.checkpoint_metric_policy_digest,
            "outcome": self.outcome.value,
            "primary_metric_name": self.primary_metric_name,
            "primary_metric_value": self.primary_metric_value,
            "rejection_reasons": list(self.rejection_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointAdmissibilityDecision":
        if payload.get("schema") != CHECKPOINT_ADMISSIBILITY_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-admissibility schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_metric_record_digest=str(payload["checkpoint_metric_record_digest"]),
            checkpoint_metric_policy_digest=str(payload["checkpoint_metric_policy_digest"]),
            outcome=CheckpointAdmissibilityOutcome(payload["outcome"]),
            primary_metric_name=str(payload["primary_metric_name"]),
            primary_metric_value=None if payload.get("primary_metric_value") is None else float(payload["primary_metric_value"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Checkpoint-admissibility digest mismatch.")
        return result


def assess_checkpoint_admissibility(
    run_plan: TrainingCampaignRunPlan,
    checkpoint: CheckpointFileRecord,
    metrics: CheckpointMetricRecord,
    policy: CheckpointMetricPolicy,
) -> CheckpointAdmissibilityDecision:
    """Apply the frozen checkpoint metric policy without discretionary ranking."""

    if checkpoint.run_plan_digest != run_plan.content_digest or metrics.run_plan_digest != run_plan.content_digest:
        raise TrainingDataInputError("Checkpoint, metrics, and campaign run lineage do not match.")
    if checkpoint.sha256 != metrics.checkpoint_sha256:
        raise TrainingDataInputError("Checkpoint metric record refers to different checkpoint bytes.")
    if policy.policy_digest != run_plan.checkpoint_metric_policy_digest:
        raise TrainingDataInputError("Checkpoint metric policy does not match the DATA8 protocol.")
    if metrics.target_monitor_artifact_digest != run_plan.target_monitor_artifact_digest:
        raise TrainingDataInputError("Target monitor artifact lineage mismatch.")

    reasons: list[str] = []
    primary = metrics.primary_metric_value(policy)
    if primary is None:
        reasons.append("missing_primary_metric")
    if policy.maximum_energy_mae_ev_per_atom is not None:
        if metrics.energy_mae_ev_per_atom is None:
            reasons.append("missing_energy_mae")
        elif metrics.energy_mae_ev_per_atom > policy.maximum_energy_mae_ev_per_atom:
            reasons.append("energy_mae_threshold_exceeded")
    if policy.maximum_focus_force_rmse_ev_per_angstrom is not None:
        focus = metrics.maximum_focus_force_rmse
        if focus is None:
            reasons.append("missing_focus_force_rmse")
        elif focus > policy.maximum_focus_force_rmse_ev_per_angstrom:
            reasons.append("focus_force_rmse_threshold_exceeded")
    if policy.maximum_stress_rmse_ev_per_angstrom3 is not None:
        if metrics.stress_rmse_ev_per_angstrom3 is None:
            reasons.append("missing_stress_rmse")
        elif metrics.stress_rmse_ev_per_angstrom3 > policy.maximum_stress_rmse_ev_per_angstrom3:
            reasons.append("stress_rmse_threshold_exceeded")
    if policy.maximum_worst_condition_force_rmse_ev_per_angstrom is not None:
        if metrics.worst_condition_force_rmse_ev_per_angstrom is None:
            reasons.append("missing_worst_condition_force_rmse")
        elif metrics.worst_condition_force_rmse_ev_per_angstrom > policy.maximum_worst_condition_force_rmse_ev_per_angstrom:
            reasons.append("worst_condition_force_rmse_threshold_exceeded")

    replay_required = run_plan.training_mode is TrainingMode.MULTIHEAD_REPLAY
    if replay_required:
        if (
            metrics.replay_monitor_artifact_digest is None
            or metrics.replay_baseline_metric is None
            or metrics.replay_candidate_metric is None
        ):
            reasons.append("missing_replay_retention_metrics")
        else:
            if metrics.replay_monitor_artifact_digest != run_plan.replay_monitor_artifact_digest:
                raise TrainingDataInputError("Replay monitor artifact lineage mismatch.")
            label_mode = metrics.replay_label_mode
            if label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
                # Pseudo-replay is a regularizer.  Candidate-vs-foundation
                # disagreement is reported, but it is not an accuracy verdict.
                # The only hard check here is provenance integrity: the exact
                # foundation must reproduce its own pseudo-labels numerically.
                if (
                    metrics.replay_baseline_metric
                    > PSEUDOLABEL_FOUNDATION_SELF_RMSE_TOLERANCE_EV_PER_ANGSTROM
                ):
                    reasons.append("pseudolabel_foundation_self_mismatch")
            else:
                # TRUE_DFT replay is genuine held-out accuracy evidence.  Legacy
                # records with unspecified provenance retain the historical
                # conservative relative-degradation behavior.
                if metrics.replay_degradation_fraction is None:
                    reasons.append("missing_replay_retention_metrics")
                elif (
                    policy.maximum_replay_degradation_fraction is not None
                    and metrics.replay_degradation_fraction > policy.maximum_replay_degradation_fraction
                ):
                    reasons.append("replay_retention_threshold_exceeded")
    elif metrics.replay_monitor_artifact_digest is not None:
        reasons.append("unexpected_replay_metrics_for_naive_protocol")

    outcome = (
        CheckpointAdmissibilityOutcome.ADMISSIBLE
        if not reasons
        else CheckpointAdmissibilityOutcome.REJECTED
    )
    return CheckpointAdmissibilityDecision(
        run_plan_digest=run_plan.content_digest,
        checkpoint_sha256=checkpoint.sha256,
        checkpoint_metric_record_digest=metrics.content_digest,
        checkpoint_metric_policy_digest=policy.policy_digest,
        outcome=outcome,
        primary_metric_name=policy.primary_metric,
        primary_metric_value=primary,
        rejection_reasons=tuple(reasons),
    )


@dataclass(frozen=True, slots=True)
class CheckpointSelectionRecord:
    run_plan_digest: str
    checkpoint_catalog_digest: str
    checkpoint_metric_policy_digest: str
    decisions: tuple[CheckpointAdmissibilityDecision, ...]
    selected_checkpoint_sha256: str
    selected_checkpoint_epoch: int
    selected_primary_metric_value: float
    ranking_order: tuple[str, ...] = (
        "primary_metric",
        "true_label_replay_degradation_if_available",
        "epoch",
        "checkpoint_sha256",
    )

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "checkpoint_catalog_digest",
            "checkpoint_metric_policy_digest",
            "selected_checkpoint_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        decisions = tuple(sorted(self.decisions, key=lambda v: v.checkpoint_sha256))
        if not decisions or any(v.run_plan_digest != self.run_plan_digest for v in decisions):
            raise TrainingDataInputError("Checkpoint selection decisions are empty or have wrong lineage.")
        if len({v.checkpoint_sha256 for v in decisions}) != len(decisions):
            raise TrainingDataInputError("Checkpoint selection has duplicate decisions.")
        selected = [v for v in decisions if v.checkpoint_sha256 == self.selected_checkpoint_sha256]
        if len(selected) != 1 or selected[0].outcome is not CheckpointAdmissibilityOutcome.ADMISSIBLE:
            raise TrainingDataInputError("Selected checkpoint is absent or inadmissible.")
        value = _finite_nonnegative(self.selected_primary_metric_value, name="selected_primary_metric_value")
        if value is None or selected[0].primary_metric_value != value:
            raise TrainingDataInputError("Selected checkpoint metric does not match its decision.")
        if self.selected_checkpoint_epoch < 0:
            raise TrainingDataInputError("Selected checkpoint epoch is invalid.")
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(self, "selected_primary_metric_value", value)
        object.__setattr__(self, "ranking_order", tuple(str(v) for v in self.ranking_order))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_SELECTION_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoint_catalog_digest": self.checkpoint_catalog_digest,
            "checkpoint_metric_policy_digest": self.checkpoint_metric_policy_digest,
            "decisions": [v.to_dict() for v in self.decisions],
            "selected_checkpoint_sha256": self.selected_checkpoint_sha256,
            "selected_checkpoint_epoch": self.selected_checkpoint_epoch,
            "selected_primary_metric_value": self.selected_primary_metric_value,
            "ranking_order": list(self.ranking_order),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointSelectionRecord":
        if payload.get("schema") != CHECKPOINT_SELECTION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported checkpoint-selection schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            checkpoint_catalog_digest=str(payload["checkpoint_catalog_digest"]),
            checkpoint_metric_policy_digest=str(payload["checkpoint_metric_policy_digest"]),
            decisions=tuple(CheckpointAdmissibilityDecision.from_dict(v) for v in payload["decisions"]),
            selected_checkpoint_sha256=str(payload["selected_checkpoint_sha256"]),
            selected_checkpoint_epoch=int(payload["selected_checkpoint_epoch"]),
            selected_primary_metric_value=float(payload["selected_primary_metric_value"]),
            ranking_order=tuple(str(v) for v in payload.get("ranking_order", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Checkpoint-selection digest mismatch.")
        return result


def select_checkpoint(
    run_plan: TrainingCampaignRunPlan,
    catalog: CandidateCheckpointCatalog,
    metrics: Sequence[CheckpointMetricRecord],
    policy: CheckpointMetricPolicy,
) -> CheckpointSelectionRecord:
    """Evaluate every candidate and select the deterministic constrained optimum."""

    if catalog.run_plan_digest != run_plan.content_digest:
        raise TrainingDataInputError("Checkpoint catalog does not belong to the campaign run.")
    metric_by_sha = {v.checkpoint_sha256: v for v in metrics}
    if len(metric_by_sha) != len(tuple(metrics)):
        raise TrainingDataInputError("Duplicate checkpoint metric records were supplied.")
    checkpoint_shas = {v.sha256 for v in catalog.checkpoints}
    if set(metric_by_sha) != checkpoint_shas:
        missing = sorted(checkpoint_shas - set(metric_by_sha))
        extra = sorted(set(metric_by_sha) - checkpoint_shas)
        raise TrainingDataInputError(
            f"Checkpoint metric coverage is incomplete or contains extras; missing={missing}, extra={extra}."
        )

    decisions: list[CheckpointAdmissibilityDecision] = []
    metric_lookup: dict[str, CheckpointMetricRecord] = {}
    checkpoint_lookup = {v.sha256: v for v in catalog.checkpoints}
    for checkpoint in catalog.checkpoints:
        metric = metric_by_sha[checkpoint.sha256]
        metric_lookup[checkpoint.sha256] = metric
        decisions.append(assess_checkpoint_admissibility(run_plan, checkpoint, metric, policy))
    admissible = [v for v in decisions if v.outcome is CheckpointAdmissibilityOutcome.ADMISSIBLE]
    if not admissible:
        reason_counts: dict[str, int] = {}
        for decision in decisions:
            for reason in decision.rejection_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        summary = ", ".join(
            f"{name}={count}" for name, count in sorted(reason_counts.items())
        ) or "unspecified_constraint_failure"
        raise TrainingDataInputError(
            "No candidate checkpoint satisfies all mandatory constraints; "
            f"rejection summary: {summary}."
        )

    def ranking_key(decision: CheckpointAdmissibilityDecision) -> tuple[float, float, int, str]:
        metric = metric_lookup[decision.checkpoint_sha256]
        primary = decision.primary_metric_value
        if primary is None:  # pragma: no cover - admissibility forbids this
            primary = float("inf")
        replay = metric.replay_degradation_fraction
        replay_key = (
            0.0
            if metric.replay_label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
            else (float("inf") if replay is None else float(replay))
        )
        checkpoint = checkpoint_lookup[decision.checkpoint_sha256]
        return float(primary), replay_key, checkpoint.epoch, checkpoint.sha256

    selected = min(admissible, key=ranking_key)
    checkpoint = checkpoint_lookup[selected.checkpoint_sha256]
    if selected.primary_metric_value is None:  # pragma: no cover
        raise TrainingDataInputError("Selected checkpoint has no primary metric.")
    return CheckpointSelectionRecord(
        run_plan_digest=run_plan.content_digest,
        checkpoint_catalog_digest=catalog.content_digest,
        checkpoint_metric_policy_digest=policy.policy_digest,
        decisions=tuple(decisions),
        selected_checkpoint_sha256=checkpoint.sha256,
        selected_checkpoint_epoch=checkpoint.epoch,
        selected_primary_metric_value=selected.primary_metric_value,
    )
