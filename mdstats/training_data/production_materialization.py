"""Restartable production DATA6--DATA8 materialization.

This module owns orchestration, immutable lineage, restart checkpoints, and
atomic promotion of DATA7/DATA8 artifacts.  Scientific feature fitting remains
owned by DATA7 and MACE artifact construction remains owned by DATA8.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from .progress_timing import format_progress_fraction
from .adaptive_stop import AdaptiveTrainingStopPolicy
from .train2_policy import (
    TrainingBudgetPolicy, LearningRateSchedulePolicy, CheckpointAdmissibilityPolicy,
    CheckpointSelectionPolicy, validate_train2_policy_set,
)
from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest, validate_serialized_digest, sha256_file_cached
from .data7_bundle import (
    MLFF_DATA7_PARSER_VERSION,
    Data7PreparationBundle,
    build_data7_preparation_bundle,
)
from .data8_bundle import Data8PreparationBundle, build_data8_preparation_bundle
from .data7_archive import (
    Data7ArchiveError, read_data7_archive, write_data7_archive,
)
from .feature_metric import FeatureFitDomain, FeatureMetricPolicyTemplate, build_feature_fit_domains
from .foundation import foundation_identity_matches_lineage
from .mace_compatibility import MaceCheckpointControlPolicy, MaceCompatibilityPolicy, MaceSourceProbe
from .mace_export import MaceExtxyzPolicy
from .mace_head_extraction import MaceSelectedHeadQualificationRecord
from .objectives import CheckpointMetricPolicy, ConfigurationWeightPolicy, TrainingObjectivePolicy
from .production_model_sweep import Data6ModelSweepArtifacts, Data6ModelSweepStatus
from .protocol import FoundationCheckpointIdentity, MaceOptimizerPolicy
from .partition import CrossValidationPlan
from .reference_fit import AtomicReferenceFitMode, AtomicReferenceFitPolicy
from .replay import ReplayMode, ReplayPreparationPlan, ReplayFileArtifact, ReplayLabelMode
from .online_monitor import OnlineMonitorPolicy
from .selection import SelectionBudgetPolicy

PRODUCTION_MATERIALIZATION_POLICY_SCHEMA = "mdstats.production-materialization-policy.v1"
PRODUCTION_MATERIALIZATION_PLAN_SCHEMA = "mdstats.production-materialization-plan.v8"
PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA = "mdstats.production-materialization-plan.v7"
PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA = "mdstats.production-materialization-plan.v6"
PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA = "mdstats.production-materialization-plan.v5"
PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA = "mdstats.production-materialization-plan.v4"
PRODUCTION_MATERIALIZATION_PLAN_V3_SCHEMA = "mdstats.production-materialization-plan.v3"
PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA = "mdstats.production-materialization-plan.v2"
PRODUCTION_DATA7_ARTIFACT_SCHEMA = "mdstats.production-data7-artifact.v1"
PRODUCTION_DATA8_ARTIFACT_SCHEMA = "mdstats.production-data8-artifact.v2"
PRODUCTION_MATERIALIZATION_CHECKPOINT_SCHEMA = "mdstats.production-materialization-checkpoint.v2"
PRODUCTION_MATERIALIZATION_RECORD_SCHEMA = "mdstats.production-materialization-record.v2"
MLFF_DATA9A9B_VERSION = "mdstats.mlff-data9a9c.production-gate-integrity.2026-07.v1"
SHARED_DATA7_ARTIFACT_SCHEMA = "mdstats.shared-data7-artifact.v2"
SHARED_DATA7_ARTIFACT_LEGACY_SCHEMA = "mdstats.shared-data7-artifact.v1"
SHARED_DATA7_RECIPE_SCHEMA = "mdstats.shared-data7-recipe.v1"


@dataclass(frozen=True, slots=True)
class _ReusableData7Artifact:
    recipe_digest: str
    domain_digest: str
    bundle_digest: str
    file_sha256: str
    path: str


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    """Atomically write compact JSON and return its SHA-256 without rereading."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    encoder = json.JSONEncoder(sort_keys=False, separators=(",", ":"), ensure_ascii=True)
    hasher = hashlib.sha256()
    try:
        with temporary.open("wb") as handle:
            for chunk in encoder.iterencode(payload):
                encoded = chunk.encode("ascii")
                handle.write(encoded)
                hasher.update(encoded)
            handle.write(b"\n")
            hasher.update(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return hasher.hexdigest()
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _read_data7_artifact(
    path: Path,
    *,
    expected_sha256: str,
) -> Data7PreparationBundle:
    """Read current compact archives and legacy monolithic JSON artifacts."""

    if path.suffix == ".zip":
        return read_data7_archive(path, expected_sha256=expected_sha256)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise TrainingDataSerializationError("DATA7 artifact checksum mismatch.")
    return Data7PreparationBundle.from_dict(json.loads(raw))


def _tree_entries(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), _sha256_file(path))
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


def _tree_digest(entries: Sequence[tuple[str, str]]) -> str:
    return digest({"files": [[str(path), validate_digest(sha, name="file_sha256")] for path, sha in entries]})


def _remove_data8_pointer(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.exists():
        shutil.rmtree(path)


def _promote_data8_tree(root: Path, staging: Path, tree_digest: str) -> Path:
    """Promote a verified DATA8 tree through an atomic symlink switch."""

    generations = root / ".data8-generations"
    generations.mkdir(parents=True, exist_ok=True)
    generation = generations / tree_digest
    if generation.exists():
        if _tree_digest(_tree_entries(generation)) == tree_digest:
            shutil.rmtree(staging, ignore_errors=True)
        else:
            corrupt = generations / f".{tree_digest}.corrupt-{uuid.uuid4().hex}"
            os.replace(generation, corrupt)
            os.replace(staging, generation)
            shutil.rmtree(corrupt, ignore_errors=True)
    else:
        os.replace(staging, generation)
    final = root / "data8"
    if final.exists() and not final.is_symlink():
        legacy = root / f".data8-legacy-{uuid.uuid4().hex}"
        os.replace(final, legacy)
        shutil.rmtree(legacy, ignore_errors=True)
    temporary_link = root / f".data8-link-{uuid.uuid4().hex}"
    relative_target = os.path.relpath(generation, root)
    os.symlink(relative_target, temporary_link, target_is_directory=True)
    os.replace(temporary_link, final)
    return final



def _replay_semantically_matches(source: ReplayPreparationPlan, staged: ReplayPreparationPlan) -> bool:
    if source.mode is not staged.mode:
        return False
    if source.mode is ReplayMode.NONE:
        return True
    for left, right in ((source.train_artifact, staged.train_artifact), (source.monitor_artifact, staged.monitor_artifact)):
        if left is None or right is None:
            return False
        if (
            left.configuration_count != right.configuration_count
            or left.atomic_numbers != right.atomic_numbers
            or left.geometry_identities != right.geometry_identities
            or left.label_payload_digest != right.label_payload_digest
            or left.energy_key != right.energy_key
            or left.forces_key != right.forces_key
            or left.stress_key != right.stress_key
            or left.stress_present_count != right.stress_present_count
            or left.label_mode is not right.label_mode
            or left.foundation_lineage_digest != right.foundation_lineage_digest
        ):
            return False
    return (
        source.requested_train_count == staged.requested_train_count
        and source.filtering_type == staged.filtering_type
        and source.subselect == staged.subselect
        and source.seed == staged.seed
        and source.head_weight == staged.head_weight
        and source.target_weight == staged.target_weight
        and source.retention_policy == staged.retention_policy
    )

class ProductionMaterializationStatus(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProductionMaterializationExecutionPolicy:
    max_new_data7_domains: int | None = None
    materialize_data8: bool = True
    verify_existing: bool = True
    recompute_invalid: bool = True

    def __post_init__(self) -> None:
        if self.max_new_data7_domains is not None and self.max_new_data7_domains < 1:
            raise TrainingDataInputError("max_new_data7_domains must be positive when present.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRODUCTION_MATERIALIZATION_POLICY_SCHEMA,
            "max_new_data7_domains": self.max_new_data7_domains,
            "materialize_data8": self.materialize_data8,
            "verify_existing": self.verify_existing,
            "recompute_invalid": self.recompute_invalid,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionMaterializationExecutionPolicy":
        if payload.get("schema") != PRODUCTION_MATERIALIZATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production materialization policy schema.")
        result = cls(
            max_new_data7_domains=None if payload.get("max_new_data7_domains") is None else int(payload["max_new_data7_domains"]),
            materialize_data8=bool(payload["materialize_data8"]),
            verify_existing=bool(payload["verify_existing"]),
            recompute_invalid=bool(payload["recompute_invalid"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production materialization policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionMaterializationPlan:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    data5_bundle_digest: str
    data6_bundle_digest: str
    data6_model_sweep_checkpoint_digest: str
    data6_descriptor_manifest_digest: str | None
    data6_prediction_manifest_digest: str | None
    domains: tuple[FeatureFitDomain, ...]
    feature_metric_policy: FeatureMetricPolicyTemplate
    atomic_reference_policy: AtomicReferenceFitPolicy
    objective_policy: TrainingObjectivePolicy
    configuration_weight_policy: ConfigurationWeightPolicy
    checkpoint_metric_policy: CheckpointMetricPolicy
    selection_budget_policy: SelectionBudgetPolicy
    foundation_checkpoint: FoundationCheckpointIdentity
    foundation_reference_energies: tuple[tuple[int, float], ...]
    compatibility_policy: MaceCompatibilityPolicy
    compatibility_probe: MaceSourceProbe
    replay_plan: ReplayPreparationPlan
    optimizer_policy: MaceOptimizerPolicy
    checkpoint_control_policy: MaceCheckpointControlPolicy
    extxyz_policy: MaceExtxyzPolicy
    selected_head_qualification: MaceSelectedHeadQualificationRecord | None = None
    online_monitor_policy: OnlineMonitorPolicy | None = None
    true_replay_monitor_artifact: ReplayFileArtifact | None = None
    adaptive_stop_policy: AdaptiveTrainingStopPolicy | None = None
    training_budget_policy: TrainingBudgetPolicy | None = None
    learning_rate_schedule_policy: LearningRateSchedulePolicy | None = None
    checkpoint_admissibility_policy: CheckpointAdmissibilityPolicy | None = None
    checkpoint_selection_policy: CheckpointSelectionPolicy | None = None
    cross_validation_plans: tuple[CrossValidationPlan, ...] = ()
    plan_schema: str = PRODUCTION_MATERIALIZATION_PLAN_SCHEMA
    real_pt_data_ratio_threshold: float = 0.0
    selection_size: int | None = None
    require_foundation_residual_e0: bool = True
    require_replay: bool = True
    plan_version: str = MLFF_DATA9A9B_VERSION

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.plan_version.strip():
            raise TrainingDataInputError("Production materialization identifiers must be non-empty.")
        for name in (
            "source_catalog_digest", "frame_catalog_digest", "data4_bundle_digest", "data5_bundle_digest",
            "data6_bundle_digest", "data6_model_sweep_checkpoint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("data6_descriptor_manifest_digest", "data6_prediction_manifest_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        domains = tuple(sorted(self.domains, key=lambda item: (item.label_domain_id, item.kind.value, -1 if item.fold_index is None else item.fold_index)))
        if not domains or len({item.content_digest for item in domains}) != len(domains):
            raise TrainingDataInputError("Production materialization requires unique canonical DATA7 domains.")
        if any(item.data5_bundle_digest != self.data5_bundle_digest for item in domains):
            raise TrainingDataInputError("Production DATA7 domain/DATA5 lineage mismatch.")
        object.__setattr__(self, "domains", domains)
        if self.plan_schema not in {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V3_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA,
        }:
            raise TrainingDataInputError("Unsupported production materialization plan schema.")
        plans = tuple(
            sorted(self.cross_validation_plans, key=lambda item: item.label_domain_id)
        )
        if self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA and plans:
            raise TrainingDataInputError(
                "Legacy production materialization plans cannot carry method-specific cross-validation plans."
            )
        if plans and len({item.label_domain_id for item in plans}) != len(plans):
            raise TrainingDataInputError(
                "Production materialization requires one cross-validation plan per label domain."
            )
        plan_fold_pairs = {
            (item.label_domain_id, fold.fold_index)
            for item in plans
            for fold in item.folds
        }
        domain_fold_pairs = {
            (item.label_domain_id, item.fold_index)
            for item in domains
            if item.fold_index is not None
        }
        if plans and domain_fold_pairs != plan_fold_pairs:
            raise TrainingDataInputError(
                "Production DATA7 domains do not match the configured cross-validation plans."
            )
        object.__setattr__(self, "cross_validation_plans", plans)
        refs = tuple(sorted((int(z), float(value)) for z, value in self.foundation_reference_energies))
        if len({z for z, _ in refs}) != len(refs):
            raise TrainingDataInputError("Foundation reference-energy atomic numbers must be unique.")
        object.__setattr__(self, "foundation_reference_energies", refs)
        if self.selected_head_qualification is not None:
            extraction = self.selected_head_qualification.extraction
            canonical = self.foundation_checkpoint.canonicalized()
            if extraction.source_potential_digest != canonical.canonical_content_digest:
                raise TrainingDataInputError("Selected-head qualification belongs to a different production foundation/head.")
            if extraction.source_checkpoint_sha256 != canonical.sha256 or extraction.source_head != canonical.foundation_head:
                raise TrainingDataInputError("Selected-head qualification source identity disagrees with the production foundation.")
            if self.plan_schema != PRODUCTION_MATERIALIZATION_PLAN_SCHEMA:
                raise TrainingDataInputError("Selected-head training qualification requires production materialization v8.")
        elif self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_SCHEMA:
            raise TrainingDataInputError("Production materialization v8 requires selected-head training qualification.")
        if (
            self.foundation_checkpoint.inspection_state == "inspected"
            and len(self.foundation_checkpoint.available_heads) > 1
            and self.selected_head_qualification is None
        ):
            raise TrainingDataInputError("Inspected multi-head production foundations require selected-head training qualification.")
        if self.compatibility_probe.policy_digest != self.compatibility_policy.policy_digest:
            raise TrainingDataInputError("Production compatibility policy/probe mismatch.")
        if not self.compatibility_probe.fixed_file_adapter_supported:
            raise TrainingDataInputError("Production materialization requires a passing MACE compatibility probe.")
        if self.require_replay and self.replay_plan.mode is ReplayMode.NONE:
            raise TrainingDataInputError("Production materialization requires an exact replay corpus.")
        if self.replay_plan.mode is not ReplayMode.NONE and not self.replay_plan.ready_for_fixed_file_training:
            raise TrainingDataInputError("Production replay plan must be resolved to local fixed files.")
        if self.online_monitor_policy is not None:
            if self.true_replay_monitor_artifact is None:
                raise TrainingDataInputError("ADAPT-MON1 plans require an independent true-label replay monitor artifact.")
            if self.true_replay_monitor_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
                raise TrainingDataInputError("ADAPT-MON1 replay monitor source must carry true DFT labels.")
        elif self.true_replay_monitor_artifact is not None:
            raise TrainingDataInputError("True replay monitor evidence requires an online-monitor policy.")
        if self.adaptive_stop_policy is not None:
            if self.online_monitor_policy is None:
                raise TrainingDataInputError("ADAPT-STOP1 requires ADAPT-MON1 monitor evidence.")
            if self.optimizer_policy.eval_interval != 1:
                raise TrainingDataInputError("ADAPT-STOP1 requires eval_interval=1.")
            if self.adaptive_stop_policy.max_num_epochs != self.optimizer_policy.max_num_epochs:
                raise TrainingDataInputError("ADAPT-STOP1 epoch ceiling disagrees with optimizer policy.")
            if bool(self.adaptive_stop_policy.replay_enabled) != bool(self.require_replay):
                raise TrainingDataInputError("ADAPT-STOP1 replay_enabled disagrees with the materialization training mode.")
        train2_active = validate_train2_policy_set(
            budget=self.training_budget_policy,
            learning_rate=self.learning_rate_schedule_policy,
            admissibility=self.checkpoint_admissibility_policy,
            selection=self.checkpoint_selection_policy,
        )
        if train2_active and self.adaptive_stop_policy is not None:
            raise TrainingDataInputError(
                "TRAIN2 policy authority and historical AdaptiveTrainingStopPolicy are mutually exclusive."
            )
        if train2_active:
            if self.online_monitor_policy is None:
                raise TrainingDataInputError("TRAIN2 materialization requires authenticated monitor evidence.")
            if self.training_budget_policy.planned_epochs != self.optimizer_policy.max_num_epochs:
                raise TrainingDataInputError("TRAIN2 epoch budget disagrees with optimizer policy.")
            if abs(self.learning_rate_schedule_policy.base_learning_rate - self.optimizer_policy.learning_rate) > 1e-18:
                raise TrainingDataInputError("TRAIN2 base LR disagrees with optimizer policy.")
            if bool(self.checkpoint_admissibility_policy.replay_enabled) != bool(self.require_replay):
                raise TrainingDataInputError("TRAIN2 replay admissibility disagrees with the materialization mode.")
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA} and not train2_active:
            raise TrainingDataInputError("Production materialization v6/v7/v8 requires complete TRAIN2 authority.")
        if self.plan_schema not in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA} and train2_active:
            raise TrainingDataInputError("TRAIN2 authority requires production materialization v6, v7, or v8.")
        if self.real_pt_data_ratio_threshold < 0.0:
            raise TrainingDataInputError("real_pt_data_ratio_threshold must be nonnegative.")
        if self.selection_size is not None and self.selection_size < 1:
            raise TrainingDataInputError("selection_size must be positive when present.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.plan_schema,
            "plan_version": self.plan_version,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "data6_model_sweep_checkpoint_digest": self.data6_model_sweep_checkpoint_digest,
            "data6_descriptor_manifest_digest": self.data6_descriptor_manifest_digest,
            "data6_prediction_manifest_digest": self.data6_prediction_manifest_digest,
            "domains": [item.to_dict() for item in self.domains],
            "feature_metric_policy": self.feature_metric_policy.to_dict(),
            "atomic_reference_policy": self.atomic_reference_policy.to_dict(),
            "objective_policy": self.objective_policy.to_dict(),
            "configuration_weight_policy": self.configuration_weight_policy.to_dict(),
            "checkpoint_metric_policy": self.checkpoint_metric_policy.to_dict(),
            "selection_budget_policy": self.selection_budget_policy.to_dict(),
            "foundation_checkpoint": self.foundation_checkpoint.to_dict(),
            "foundation_reference_energies": [[z, value] for z, value in self.foundation_reference_energies],
            "compatibility_policy": self.compatibility_policy.to_dict(),
            "compatibility_probe": self.compatibility_probe.to_dict(),
            "replay_plan": self.replay_plan.to_dict(),
            "optimizer_policy": self.optimizer_policy.to_dict(),
            "checkpoint_control_policy": self.checkpoint_control_policy.to_dict(),
            "extxyz_policy": self.extxyz_policy.to_dict(),
            "real_pt_data_ratio_threshold": self.real_pt_data_ratio_threshold,
            "selection_size": self.selection_size,
            "require_foundation_residual_e0": self.require_foundation_residual_e0,
            "require_replay": self.require_replay,
        }
        if self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_SCHEMA:
            payload["selected_head_qualification"] = self.selected_head_qualification.to_dict()
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V3_SCHEMA}:
            payload["cross_validation_plans"] = [
                item.to_dict() for item in self.cross_validation_plans
            ]
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA}:
            payload["online_monitor_policy"] = None if self.online_monitor_policy is None else self.online_monitor_policy.to_dict()
            payload["true_replay_monitor_artifact"] = None if self.true_replay_monitor_artifact is None else self.true_replay_monitor_artifact.to_dict()
        if self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA:
            payload["adaptive_stop_policy"] = None if self.adaptive_stop_policy is None else self.adaptive_stop_policy.to_dict()
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA}:
            payload.update({
                "training_budget_policy": None if self.training_budget_policy is None else self.training_budget_policy.to_dict(),
                "learning_rate_schedule_policy": None if self.learning_rate_schedule_policy is None else self.learning_rate_schedule_policy.to_dict(),
                "checkpoint_admissibility_policy": None if self.checkpoint_admissibility_policy is None else self.checkpoint_admissibility_policy.to_dict(),
                "checkpoint_selection_policy": None if self.checkpoint_selection_policy is None else self.checkpoint_selection_policy.to_dict(),
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionMaterializationPlan":
        schema = payload.get("schema")
        if schema not in {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V3_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported production materialization plan schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            data6_bundle_digest=str(payload["data6_bundle_digest"]),
            data6_model_sweep_checkpoint_digest=str(payload["data6_model_sweep_checkpoint_digest"]),
            data6_descriptor_manifest_digest=None if payload.get("data6_descriptor_manifest_digest") is None else str(payload["data6_descriptor_manifest_digest"]),
            data6_prediction_manifest_digest=None if payload.get("data6_prediction_manifest_digest") is None else str(payload["data6_prediction_manifest_digest"]),
            domains=tuple(FeatureFitDomain.from_dict(item) for item in payload["domains"]),
            feature_metric_policy=FeatureMetricPolicyTemplate.from_dict(payload["feature_metric_policy"]),
            atomic_reference_policy=AtomicReferenceFitPolicy.from_dict(payload["atomic_reference_policy"]),
            objective_policy=TrainingObjectivePolicy.from_dict(payload["objective_policy"]),
            configuration_weight_policy=ConfigurationWeightPolicy.from_dict(payload["configuration_weight_policy"]),
            checkpoint_metric_policy=CheckpointMetricPolicy.from_dict(payload["checkpoint_metric_policy"]),
            selection_budget_policy=SelectionBudgetPolicy.from_dict(payload["selection_budget_policy"]),
            foundation_checkpoint=FoundationCheckpointIdentity.from_dict(payload["foundation_checkpoint"]),
            foundation_reference_energies=tuple((int(item[0]), float(item[1])) for item in payload.get("foundation_reference_energies", ())),
            selected_head_qualification=(
                None if payload.get("selected_head_qualification") is None
                else MaceSelectedHeadQualificationRecord.from_dict(payload["selected_head_qualification"])
            ),
            compatibility_policy=MaceCompatibilityPolicy.from_dict(payload["compatibility_policy"]),
            compatibility_probe=MaceSourceProbe.from_dict(payload["compatibility_probe"]),
            replay_plan=ReplayPreparationPlan.from_dict(payload["replay_plan"]),
            optimizer_policy=MaceOptimizerPolicy.from_dict(payload["optimizer_policy"]),
            checkpoint_control_policy=MaceCheckpointControlPolicy.from_dict(payload["checkpoint_control_policy"]),
            extxyz_policy=MaceExtxyzPolicy.from_dict(payload["extxyz_policy"]),
            online_monitor_policy=None if payload.get("online_monitor_policy") is None else OnlineMonitorPolicy.from_dict(payload["online_monitor_policy"]),
            true_replay_monitor_artifact=None if payload.get("true_replay_monitor_artifact") is None else ReplayFileArtifact.from_dict(payload["true_replay_monitor_artifact"]),
            adaptive_stop_policy=None if payload.get("adaptive_stop_policy") is None else AdaptiveTrainingStopPolicy.from_dict(payload["adaptive_stop_policy"]),
            training_budget_policy=None if payload.get("training_budget_policy") is None else TrainingBudgetPolicy.from_dict(payload["training_budget_policy"]),
            learning_rate_schedule_policy=None if payload.get("learning_rate_schedule_policy") is None else LearningRateSchedulePolicy.from_dict(payload["learning_rate_schedule_policy"]),
            checkpoint_admissibility_policy=None if payload.get("checkpoint_admissibility_policy") is None else CheckpointAdmissibilityPolicy.from_dict(payload["checkpoint_admissibility_policy"]),
            checkpoint_selection_policy=None if payload.get("checkpoint_selection_policy") is None else CheckpointSelectionPolicy.from_dict(payload["checkpoint_selection_policy"]),
            cross_validation_plans=tuple(
                CrossValidationPlan.from_dict(item)
                for item in payload.get("cross_validation_plans", ())
            ),
            plan_schema=str(schema),
            real_pt_data_ratio_threshold=float(payload["real_pt_data_ratio_threshold"]),
            selection_size=None if payload.get("selection_size") is None else int(payload["selection_size"]),
            require_foundation_residual_e0=bool(payload["require_foundation_residual_e0"]),
            require_replay=bool(payload["require_replay"]),
            plan_version=str(payload["plan_version"]),
        )
        validate_serialized_digest(
            payload,
            digest_field="content_digest",
            current_digest=result.content_digest,
            error_message="Production materialization plan digest mismatch.",
        )
        return result


@dataclass(frozen=True, slots=True)
class ProductionData7ArtifactRecord:
    domain_digest: str
    relative_path: str
    bundle_digest: str
    file_sha256: str

    def __post_init__(self) -> None:
        for name in ("domain_digest", "bundle_digest", "file_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        path = Path(self.relative_path)
        if not self.relative_path.strip() or path.is_absolute() or ".." in path.parts:
            raise TrainingDataInputError("DATA7 artifact path must be safe and relative.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_DATA7_ARTIFACT_SCHEMA, "domain_digest": self.domain_digest, "relative_path": self.relative_path, "bundle_digest": self.bundle_digest, "file_sha256": self.file_sha256}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionData7ArtifactRecord":
        if payload.get("schema") != PRODUCTION_DATA7_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production DATA7 artifact schema.")
        result = cls(domain_digest=str(payload["domain_digest"]), relative_path=str(payload["relative_path"]), bundle_digest=str(payload["bundle_digest"]), file_sha256=str(payload["file_sha256"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production DATA7 artifact digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionData8ArtifactRecord:
    relative_directory: str
    bundle_relative_path: str
    bundle_digest: str
    tree_entries: tuple[tuple[str, str], ...]
    tree_digest: str

    def __post_init__(self) -> None:
        directory = Path(self.relative_directory)
        bundle_path = Path(self.bundle_relative_path)
        if not self.relative_directory.strip() or directory.is_absolute() or ".." in directory.parts:
            raise TrainingDataInputError("DATA8 artifact directory must be safe and relative.")
        if not self.bundle_relative_path.strip() or bundle_path.is_absolute() or ".." in bundle_path.parts:
            raise TrainingDataInputError("DATA8 bundle path must be safe and relative.")
        object.__setattr__(self, "bundle_digest", validate_digest(self.bundle_digest, name="bundle_digest"))
        entries = tuple(sorted((str(path), validate_digest(sha, name="file_sha256")) for path, sha in self.tree_entries))
        if not entries or len({path for path, _ in entries}) != len(entries):
            raise TrainingDataInputError("DATA8 tree entries must be non-empty and unique.")
        if any(Path(path).is_absolute() or ".." in Path(path).parts for path, _ in entries):
            raise TrainingDataInputError("DATA8 tree entries must use safe relative paths.")
        object.__setattr__(self, "tree_entries", entries)
        object.__setattr__(self, "tree_digest", validate_digest(self.tree_digest, name="tree_digest"))
        if _tree_digest(entries) != self.tree_digest:
            raise TrainingDataInputError("DATA8 tree digest does not match its entries.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_DATA8_ARTIFACT_SCHEMA, "relative_directory": self.relative_directory, "bundle_relative_path": self.bundle_relative_path, "bundle_digest": self.bundle_digest, "tree_entries": [[path, sha] for path, sha in self.tree_entries], "tree_digest": self.tree_digest}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionData8ArtifactRecord":
        if payload.get("schema") != PRODUCTION_DATA8_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production DATA8 artifact schema.")
        result = cls(relative_directory=str(payload["relative_directory"]), bundle_relative_path=str(payload["bundle_relative_path"]), bundle_digest=str(payload["bundle_digest"]), tree_entries=tuple((str(v[0]), str(v[1])) for v in payload["tree_entries"]), tree_digest=str(payload["tree_digest"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production DATA8 artifact digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionMaterializationCheckpoint:
    plan: ProductionMaterializationPlan
    data7_artifacts: tuple[ProductionData7ArtifactRecord, ...] = ()
    data8_artifact: ProductionData8ArtifactRecord | None = None
    status: ProductionMaterializationStatus = ProductionMaterializationStatus.INCOMPLETE
    failure_type: str | None = None
    failure_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ProductionMaterializationStatus(self.status))
        records = tuple(sorted(self.data7_artifacts, key=lambda item: item.domain_digest))
        if len({item.domain_digest for item in records}) != len(records):
            raise TrainingDataInputError("Production checkpoint contains duplicate DATA7 domains.")
        if not set(item.domain_digest for item in records).issubset({item.content_digest for item in self.plan.domains}):
            raise TrainingDataInputError("Production checkpoint contains foreign DATA7 domains.")
        object.__setattr__(self, "data7_artifacts", records)
        complete_data7 = len(records) == len(self.plan.domains)
        if self.data8_artifact is not None and not complete_data7:
            raise TrainingDataInputError("DATA8 cannot be recorded before all DATA7 domains are complete.")
        if self.status is ProductionMaterializationStatus.COMPLETE and (not complete_data7 or self.data8_artifact is None):
            raise TrainingDataInputError("Complete production checkpoint requires all DATA7 and DATA8 artifacts.")
        if self.status is ProductionMaterializationStatus.FAILED:
            if not self.failure_type or self.failure_message is None:
                raise TrainingDataInputError("Failed production checkpoint requires failure evidence.")
        elif self.failure_type is not None or self.failure_message is not None:
            raise TrainingDataInputError("Non-failed production checkpoint cannot carry failure evidence.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_MATERIALIZATION_CHECKPOINT_SCHEMA, "plan": self.plan.to_dict(), "data7_artifacts": [item.to_dict() for item in self.data7_artifacts], "data8_artifact": None if self.data8_artifact is None else self.data8_artifact.to_dict(), "status": self.status.value, "failure_type": self.failure_type, "failure_message": self.failure_message}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionMaterializationCheckpoint":
        if payload.get("schema") != PRODUCTION_MATERIALIZATION_CHECKPOINT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production materialization checkpoint schema.")
        result = cls(plan=ProductionMaterializationPlan.from_dict(payload["plan"]), data7_artifacts=tuple(ProductionData7ArtifactRecord.from_dict(item) for item in payload.get("data7_artifacts", ())), data8_artifact=None if payload.get("data8_artifact") is None else ProductionData8ArtifactRecord.from_dict(payload["data8_artifact"]), status=ProductionMaterializationStatus(payload["status"]), failure_type=None if payload.get("failure_type") is None else str(payload["failure_type"]), failure_message=None if payload.get("failure_message") is None else str(payload["failure_message"]))
        validate_serialized_digest(
            payload,
            digest_field="content_digest",
            current_digest=result.content_digest,
            error_message="Production materialization checkpoint digest mismatch.",
        )
        return result


@dataclass(frozen=True, slots=True)
class ProductionMaterializationRecord:
    root_directory: str
    checkpoint: ProductionMaterializationCheckpoint

    @property
    def complete(self) -> bool:
        return self.checkpoint.status is ProductionMaterializationStatus.COMPLETE

    @property
    def data7_bundle_digests(self) -> tuple[str, ...]:
        return tuple(item.bundle_digest for item in self.checkpoint.data7_artifacts)

    @property
    def data8_bundle_digest(self) -> str | None:
        return None if self.checkpoint.data8_artifact is None else self.checkpoint.data8_artifact.bundle_digest

    @property
    def data8_runtime_directory(self) -> str | None:
        """Return the promoted live DATA8 root, not its deleted staging root."""

        artifact = self.checkpoint.data8_artifact
        if artifact is None:
            return None
        return str((Path(self.root_directory) / artifact.relative_directory).resolve())

    def load_data7_bundles(self) -> tuple[Data7PreparationBundle, ...]:
        root = Path(self.root_directory)
        indexed = {item.domain_digest: item for item in self.checkpoint.data7_artifacts}
        for record in indexed.values():
            if not _data7_record_valid(record, root, self.checkpoint.plan):
                raise TrainingDataSerializationError("Production DATA7 artifact failed verification before loading.")
        return tuple(
            _read_data7_artifact(
                root / indexed[domain.content_digest].relative_path,
                expected_sha256=indexed[domain.content_digest].file_sha256,
            )
            for domain in self.checkpoint.plan.domains
            if domain.content_digest in indexed
        )

    def load_data8_bundle(self) -> Data8PreparationBundle:
        if self.checkpoint.data8_artifact is None:
            raise TrainingDataInputError("Production materialization has no DATA8 artifact.")
        root = Path(self.root_directory)
        if not _data8_record_valid(self.checkpoint.data8_artifact, root, self.checkpoint.plan):
            raise TrainingDataSerializationError("Production DATA8 artifact failed verification before loading.")
        path = root / self.checkpoint.data8_artifact.bundle_relative_path
        return Data8PreparationBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _identity_payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_MATERIALIZATION_RECORD_SCHEMA, "checkpoint": self.checkpoint.to_dict()}

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "root_directory": self.root_directory, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionMaterializationRecord":
        if payload.get("schema") != PRODUCTION_MATERIALIZATION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production materialization record schema.")
        result = cls(root_directory=str(payload["root_directory"]), checkpoint=ProductionMaterializationCheckpoint.from_dict(payload["checkpoint"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production materialization record digest mismatch.")
        return result


def build_production_materialization_plan(
    source_catalog: Any,
    frame_catalog: Any,
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    model_sweep_artifacts: Data6ModelSweepArtifacts,
    *,
    foundation_checkpoint: FoundationCheckpointIdentity,
    selected_head_qualification: MaceSelectedHeadQualificationRecord | None = None,
    compatibility_probe: MaceSourceProbe,
    replay_plan: ReplayPreparationPlan,
    cross_validation_plans: Sequence[CrossValidationPlan] | None = None,
    online_monitor_policy: OnlineMonitorPolicy | None = None,
    true_replay_monitor_artifact: ReplayFileArtifact | None = None,
    adaptive_stop_policy: AdaptiveTrainingStopPolicy | None = None,
    training_budget_policy: TrainingBudgetPolicy | None = None,
    learning_rate_schedule_policy: LearningRateSchedulePolicy | None = None,
    checkpoint_admissibility_policy: CheckpointAdmissibilityPolicy | None = None,
    checkpoint_selection_policy: CheckpointSelectionPolicy | None = None,
    feature_metric_policy: FeatureMetricPolicyTemplate | None = None,
    atomic_reference_policy: AtomicReferenceFitPolicy | None = None,
    objective_policy: TrainingObjectivePolicy | None = None,
    configuration_weight_policy: ConfigurationWeightPolicy | None = None,
    checkpoint_metric_policy: CheckpointMetricPolicy | None = None,
    selection_budget_policy: SelectionBudgetPolicy,
    compatibility_policy: MaceCompatibilityPolicy | None = None,
    optimizer_policy: MaceOptimizerPolicy | None = None,
    checkpoint_control_policy: MaceCheckpointControlPolicy | None = None,
    extxyz_policy: MaceExtxyzPolicy | None = None,
    foundation_reference_energies: Mapping[int, float] | None = None,
    real_pt_data_ratio_threshold: float = 0.0,
    selection_size: int | None = None,
    require_foundation_residual_e0: bool = True,
    require_replay: bool = True,
) -> ProductionMaterializationPlan:
    if not model_sweep_artifacts.complete or model_sweep_artifacts.checkpoint.status is not Data6ModelSweepStatus.COMPLETE:
        raise TrainingDataInputError("DATA9A9b requires a completed DATA6 model sweep.")
    if data6_bundle.model_sweep_checkpoint_digest != model_sweep_artifacts.checkpoint.content_digest:
        raise TrainingDataInputError("DATA6 bundle/model-sweep checkpoint mismatch.")
    expected_descriptor = None if model_sweep_artifacts.descriptor_manifest is None else model_sweep_artifacts.descriptor_manifest.content_digest
    observed_descriptor = None if data6_bundle.mace_descriptor_manifest is None else data6_bundle.mace_descriptor_manifest.content_digest
    expected_prediction = None if model_sweep_artifacts.prediction_manifest is None else model_sweep_artifacts.prediction_manifest.content_digest
    observed_prediction = None if data6_bundle.prediction_manifest is None else data6_bundle.prediction_manifest.content_digest
    if observed_descriptor != expected_descriptor or observed_prediction != expected_prediction:
        raise TrainingDataInputError("DATA6 bundle does not bind the completed sweep manifests exactly.")
    if source_catalog.content_digest != data6_bundle.source_catalog_digest or frame_catalog.content_digest != data6_bundle.frame_catalog_digest:
        raise TrainingDataInputError("DATA9A9b source/frame lineage mismatch.")
    if data4_bundle.content_digest != data6_bundle.data4_bundle_digest or data5_bundle.content_digest != data6_bundle.data5_bundle_digest:
        raise TrainingDataInputError("DATA9A9b DATA4/DATA5/DATA6 lineage mismatch.")
    sweep_identity = model_sweep_artifacts.checkpoint.plan.checkpoint_identity
    if not foundation_identity_matches_lineage(
        foundation_checkpoint,
        foundation_identity_digest=sweep_identity.foundation_potential_digest,
        legacy_checkpoint_digest=(None if sweep_identity.foundation_potential_digest is not None else sweep_identity.checkpoint_sha256),
    ):
        raise TrainingDataInputError("DATA8 foundation potential/head differs from the completed DATA6 sweep identity.")
    active_compat = MaceCompatibilityPolicy() if compatibility_policy is None else compatibility_policy
    # ``require_replay`` selects the scientific training mode.  Prior releases
    # retained the resolved replay corpus even when ``require_replay=False``;
    # DATA8 therefore inferred MULTIHEAD_REPLAY for nominally naive variants.
    # Bind an explicit replay-free plan so the DATA8 protocol identity, files,
    # and generated MACE heads agree with the requested mode.
    active_replay = (
        replay_plan
        if require_replay
        else ReplayPreparationPlan(mode=ReplayMode.NONE)
    )
    active_cv_plans = (
        tuple(data5_bundle.cross_validation_plans)
        if cross_validation_plans is None
        else tuple(cross_validation_plans)
    )
    return ProductionMaterializationPlan(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest,
        data6_model_sweep_checkpoint_digest=model_sweep_artifacts.checkpoint.content_digest,
        data6_descriptor_manifest_digest=None if model_sweep_artifacts.descriptor_manifest is None else model_sweep_artifacts.descriptor_manifest.content_digest,
        data6_prediction_manifest_digest=None if model_sweep_artifacts.prediction_manifest is None else model_sweep_artifacts.prediction_manifest.content_digest,
        domains=build_feature_fit_domains(
            data5_bundle,
            cross_validation_plans=active_cv_plans,
        ),
        cross_validation_plans=active_cv_plans,
        feature_metric_policy=FeatureMetricPolicyTemplate() if feature_metric_policy is None else feature_metric_policy,
        atomic_reference_policy=(AtomicReferenceFitPolicy(fit_mode=AtomicReferenceFitMode.FOUNDATION_RESIDUAL) if atomic_reference_policy is None and require_foundation_residual_e0 else AtomicReferenceFitPolicy() if atomic_reference_policy is None else atomic_reference_policy),
        objective_policy=TrainingObjectivePolicy() if objective_policy is None else objective_policy,
        configuration_weight_policy=ConfigurationWeightPolicy() if configuration_weight_policy is None else configuration_weight_policy,
        checkpoint_metric_policy=CheckpointMetricPolicy() if checkpoint_metric_policy is None else checkpoint_metric_policy,
        selection_budget_policy=selection_budget_policy,
        foundation_checkpoint=foundation_checkpoint,
        foundation_reference_energies=tuple((int(z), float(value)) for z, value in (foundation_reference_energies or {}).items()),
        selected_head_qualification=selected_head_qualification,
        compatibility_policy=active_compat,
        compatibility_probe=compatibility_probe,
        replay_plan=active_replay,
        optimizer_policy=MaceOptimizerPolicy() if optimizer_policy is None else optimizer_policy,
        checkpoint_control_policy=MaceCheckpointControlPolicy() if checkpoint_control_policy is None else checkpoint_control_policy,
        extxyz_policy=MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy,
        online_monitor_policy=online_monitor_policy,
        true_replay_monitor_artifact=true_replay_monitor_artifact,
        adaptive_stop_policy=adaptive_stop_policy,
        training_budget_policy=training_budget_policy,
        learning_rate_schedule_policy=learning_rate_schedule_policy,
        checkpoint_admissibility_policy=checkpoint_admissibility_policy,
        checkpoint_selection_policy=checkpoint_selection_policy,
        plan_schema=(
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA
            if training_budget_policy is not None and selected_head_qualification is not None
            else PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA
            if training_budget_policy is not None
            else PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA
        ),
        real_pt_data_ratio_threshold=real_pt_data_ratio_threshold,
        selection_size=selection_size,
        require_foundation_residual_e0=require_foundation_residual_e0,
        require_replay=require_replay,
    )


def _data7_recipe_digest(
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> str:
    """Identity of every input that can change a DATA7 scientific artifact.

    Optimizer seed, replay mode, output layout, and other DATA8-only controls are
    deliberately excluded, allowing exact DATA7 reuse across training variants.
    """

    return digest({
        "schema": SHARED_DATA7_RECIPE_SCHEMA,
        "data7_parser_version": MLFF_DATA7_PARSER_VERSION,
        "dataset_id": plan.dataset_id,
        "source_catalog_digest": plan.source_catalog_digest,
        "frame_catalog_digest": plan.frame_catalog_digest,
        "data4_bundle_digest": plan.data4_bundle_digest,
        "data5_bundle_digest": plan.data5_bundle_digest,
        "data6_bundle_digest": plan.data6_bundle_digest,
        "data6_model_sweep_checkpoint_digest": plan.data6_model_sweep_checkpoint_digest,
        "data6_descriptor_manifest_digest": plan.data6_descriptor_manifest_digest,
        "data6_prediction_manifest_digest": plan.data6_prediction_manifest_digest,
        "domain": domain.to_dict(),
        "feature_metric_policy": plan.feature_metric_policy.to_dict(),
        "atomic_reference_policy": plan.atomic_reference_policy.to_dict(),
        "objective_policy": plan.objective_policy.to_dict(),
        "configuration_weight_policy": plan.configuration_weight_policy.to_dict(),
        "checkpoint_metric_policy": plan.checkpoint_metric_policy.to_dict(),
        "selection_budget_policy": plan.selection_budget_policy.to_dict(),
        "foundation_checkpoint_sha256": plan.foundation_checkpoint.sha256,
        "foundation_identity_digest": plan.foundation_checkpoint.canonical_content_digest,
        "foundation_reference_energies": {
            str(z): value for z, value in plan.foundation_reference_energies
        },
    })


def _data7_bundle_matches_plan(
    bundle: Data7PreparationBundle,
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> bool:
    requires_foundation = plan.atomic_reference_policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
    return (
        bundle.dataset_id == plan.dataset_id
        and bundle.source_catalog_digest == plan.source_catalog_digest
        and bundle.frame_catalog_digest == plan.frame_catalog_digest
        and bundle.data4_bundle_digest == plan.data4_bundle_digest
        and bundle.data5_bundle_digest == plan.data5_bundle_digest
        and bundle.data6_bundle_digest == plan.data6_bundle_digest
        and bundle.domain.content_digest == domain.content_digest
        and bundle.fitted_metric.policy.policy_digest == plan.feature_metric_policy.policy_digest
        and bundle.atomic_reference_fit.policy.policy_digest == plan.atomic_reference_policy.policy_digest
        and (
            (not requires_foundation and bundle.atomic_reference_fit.foundation_lineage_digest is None)
            or (requires_foundation and foundation_identity_matches_lineage(
                plan.foundation_checkpoint,
                foundation_identity_digest=bundle.atomic_reference_fit.foundation_identity_digest,
                legacy_checkpoint_digest=bundle.atomic_reference_fit.foundation_checkpoint_digest,
            ))
        )
        and bundle.atomic_reference_fit.foundation_reference_energies_ev
        == plan.foundation_reference_energies
        and bundle.training_weights.objective_policy.policy_digest
        == plan.objective_policy.policy_digest
        and bundle.training_weights.configuration_policy.policy_digest
        == plan.configuration_weight_policy.policy_digest
        and bundle.checkpoint_metric_policy.policy_digest
        == plan.checkpoint_metric_policy.policy_digest
        and bundle.selection_plan.policy.policy_digest
        == plan.selection_budget_policy.policy_digest
    )


def _atomic_link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        try:
            os.link(source, temporary)
        except OSError:
            with source.open("rb") as read_handle, temporary.open("wb") as write_handle:
                shutil.copyfileobj(read_handle, write_handle, length=1024 * 1024)
                write_handle.flush()
                os.fsync(write_handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _load_reusable_data7_artifact(
    cache_root: Path,
    recipe_digest: str,
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
) -> tuple[_ReusableData7Artifact, Data7PreparationBundle] | None:
    manifest_path = cache_root / f"{recipe_digest}.manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            metadata.get("schema") not in {
                SHARED_DATA7_ARTIFACT_SCHEMA,
                SHARED_DATA7_ARTIFACT_LEGACY_SCHEMA,
            }
            or metadata.get("recipe_digest") != recipe_digest
            or metadata.get("domain_digest") != domain.content_digest
        ):
            return None
        artifact_name = metadata.get("artifact_name")
        if artifact_name is None:
            artifact_path = cache_root / f"{recipe_digest}.json"
        else:
            candidate = Path(str(artifact_name))
            if candidate.is_absolute() or ".." in candidate.parts:
                return None
            artifact_path = cache_root / candidate
        if not artifact_path.is_file():
            return None
        file_sha256 = str(metadata.get("file_sha256", ""))
        bundle = _read_data7_artifact(
            artifact_path, expected_sha256=file_sha256
        )
        if (
            bundle.content_digest != metadata.get("bundle_digest")
            or not _data7_bundle_matches_plan(bundle, plan, domain)
        ):
            return None
        return (
            _ReusableData7Artifact(
                recipe_digest=recipe_digest,
                domain_digest=domain.content_digest,
                bundle_digest=bundle.content_digest,
                file_sha256=file_sha256,
                path=str(artifact_path),
            ),
            bundle,
        )
    except Exception:
        return None


def _write_reusable_data7_artifact(
    cache_root: Path,
    recipe_digest: str,
    domain: FeatureFitDomain,
    bundle: Data7PreparationBundle,
) -> _ReusableData7Artifact:
    cache_root.mkdir(parents=True, exist_ok=True)
    artifact_path = cache_root / f"{recipe_digest}.data7.zip"
    file_sha256 = write_data7_archive(bundle, artifact_path)
    _atomic_json(
        cache_root / f"{recipe_digest}.manifest.json",
        {
            "schema": SHARED_DATA7_ARTIFACT_SCHEMA,
            "recipe_digest": recipe_digest,
            "domain_digest": domain.content_digest,
            "bundle_digest": bundle.content_digest,
            "artifact_name": artifact_path.name,
            "file_sha256": file_sha256,
        },
    )
    return _ReusableData7Artifact(
        recipe_digest=recipe_digest,
        domain_digest=domain.content_digest,
        bundle_digest=bundle.content_digest,
        file_sha256=file_sha256,
        path=str(artifact_path),
    )


def _load_valid_data7_record(
    record: ProductionData7ArtifactRecord,
    root: Path,
    plan: ProductionMaterializationPlan,
) -> Data7PreparationBundle | None:
    path = root / record.relative_path
    if not path.is_file():
        return None
    try:
        bundle = _read_data7_artifact(
            path, expected_sha256=record.file_sha256
        )
    except Exception:
        return None
    if (
        bundle.content_digest != record.bundle_digest
        or bundle.domain.content_digest != record.domain_digest
        or bundle.data6_bundle_digest != plan.data6_bundle_digest
    ):
        return None
    return bundle


def _data7_record_valid(record: ProductionData7ArtifactRecord, root: Path, plan: ProductionMaterializationPlan) -> bool:
    return _load_valid_data7_record(record, root, plan) is not None


def register_reusable_data7_artifacts(
    record: ProductionMaterializationRecord,
    shared_data7_artifacts: MutableMapping[str, _ReusableData7Artifact],
) -> int:
    """Register verified promoted DATA7 artifacts for exact in-process reuse.

    A completed campaign may have cleaned its transient shared DATA7 cache while
    retaining the authoritative promoted per-variant DATA7 archives.  Seed
    extension therefore repopulates the in-process recipe map directly from
    those immutable promoted artifacts.  Recipe identity deliberately excludes
    optimizer seed, so a newly appended optimizer-only seed can hard-link/copy
    the exact same fold-local DATA7 artifacts without refitting them.

    Invalid or missing promoted artifacts are skipped rather than trusted.  A
    later materialization will rebuild such a recipe through the normal DATA7
    path.  Conflicting valid artifacts for the same recipe fail closed.
    """

    plan = record.checkpoint.plan
    root = Path(record.root_directory).resolve()
    domains = {domain.content_digest: domain for domain in plan.domains}
    registered = 0
    for item in record.checkpoint.data7_artifacts:
        domain = domains.get(item.domain_digest)
        if domain is None:
            continue
        bundle = _load_valid_data7_record(item, root, plan)
        if bundle is None or not _data7_bundle_matches_plan(bundle, plan, domain):
            continue
        recipe_digest = _data7_recipe_digest(plan, domain)
        source = (root / item.relative_path).resolve()
        artifact = _ReusableData7Artifact(
            recipe_digest=recipe_digest,
            domain_digest=domain.content_digest,
            bundle_digest=bundle.content_digest,
            file_sha256=item.file_sha256,
            path=str(source),
        )
        previous = shared_data7_artifacts.get(recipe_digest)
        if previous is not None:
            if (
                previous.domain_digest != artifact.domain_digest
                or previous.bundle_digest != artifact.bundle_digest
                or previous.file_sha256 != artifact.file_sha256
            ):
                raise TrainingDataSerializationError(
                    "Conflicting promoted DATA7 artifacts share one scientific recipe."
                )
            continue
        shared_data7_artifacts[recipe_digest] = artifact
        registered += 1
    return registered


def _data8_record_valid(record: ProductionData8ArtifactRecord, root: Path, plan: ProductionMaterializationPlan) -> bool:
    directory = root / record.relative_directory
    bundle_path = root / record.bundle_relative_path
    if not directory.is_dir() or not bundle_path.is_file():
        return False
    entries = _tree_entries(directory)
    if entries != record.tree_entries or _tree_digest(entries) != record.tree_digest:
        return False
    try:
        bundle = Data8PreparationBundle.from_dict(json.loads(bundle_path.read_text(encoding="utf-8")))
    except Exception:
        return False
    return bundle.content_digest == record.bundle_digest and bundle.data5_bundle_digest == plan.data5_bundle_digest and _replay_semantically_matches(plan.replay_plan, bundle.replay_plan)


def _verify_live_inputs(
    source_catalog: Any, frame_catalog: Any, data4_bundle: Any, data5_bundle: Any,
    data6_bundle: Any, model_sweep_artifacts: Data6ModelSweepArtifacts,
    plan: ProductionMaterializationPlan,
) -> None:
    observed = (
        source_catalog.content_digest, frame_catalog.content_digest, data4_bundle.content_digest,
        data5_bundle.content_digest, data6_bundle.content_digest, model_sweep_artifacts.checkpoint.content_digest,
    )
    expected = (
        plan.source_catalog_digest, plan.frame_catalog_digest, plan.data4_bundle_digest,
        plan.data5_bundle_digest, plan.data6_bundle_digest, plan.data6_model_sweep_checkpoint_digest,
    )
    if observed != expected:
        raise TrainingDataInputError("Production materialization live inputs do not match the frozen plan.")
    if not model_sweep_artifacts.complete:
        raise TrainingDataInputError("Production materialization requires a completed model sweep.")
    descriptor = None if model_sweep_artifacts.descriptor_manifest is None else model_sweep_artifacts.descriptor_manifest.content_digest
    prediction = None if model_sweep_artifacts.prediction_manifest is None else model_sweep_artifacts.prediction_manifest.content_digest
    if descriptor != plan.data6_descriptor_manifest_digest or prediction != plan.data6_prediction_manifest_digest:
        raise TrainingDataInputError("Production materialization sweep manifests do not match the frozen plan.")


def run_restartable_production_materialization(
    source_catalog: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    model_sweep_artifacts: Data6ModelSweepArtifacts,
    plan: ProductionMaterializationPlan,
    output_directory: str | Path,
    *,
    mace_descriptor_root: str | Path | None = None,
    foundation_prediction_energy_by_frame: Mapping[str, float] | None = None,
    shared_data7_cache_directory: str | Path | None = None,
    shared_data7_artifacts: MutableMapping[str, _ReusableData7Artifact] | None = None,
    shared_data8_fixed_file_cache_directory: str | Path | None = None,
    shared_frame_array_index_cache: MutableMapping[str, Mapping[str, tuple[Any, Any, int]]] | None = None,
    execution_policy: ProductionMaterializationExecutionPolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> ProductionMaterializationRecord:
    active = ProductionMaterializationExecutionPolicy() if execution_policy is None else execution_policy
    _verify_live_inputs(source_catalog, frame_catalog, data4_bundle, data5_bundle, data6_bundle, model_sweep_artifacts, plan)
    root = Path(output_directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    shared_cache_root = (
        None
        if shared_data7_cache_directory is None
        else Path(shared_data7_cache_directory).resolve()
    )
    shared_memory = shared_data7_artifacts
    checkpoint_path = root / "production_materialization_checkpoint.json"
    records: dict[str, ProductionData7ArtifactRecord] = {}
    resolved_bundles: dict[str, Data7PreparationBundle] = {}
    data8_record: ProductionData8ArtifactRecord | None = None
    if checkpoint_path.is_file():
        try:
            restored = ProductionMaterializationCheckpoint.from_dict(json.loads(checkpoint_path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise TrainingDataSerializationError("Cannot restore production materialization checkpoint.") from exc
        if restored.plan.content_digest != plan.content_digest:
            raise TrainingDataInputError("Existing production materialization checkpoint belongs to another plan.")
        records = {item.domain_digest: item for item in restored.data7_artifacts}
        data8_record = restored.data8_artifact
    if active.verify_existing:
        # Validate DATA8 first so we know whether parsed DATA7 bundles should be
        # retained for immediate DATA8 reconstruction.  The former order parsed
        # every large DATA7 JSON for validation, discarded it, and then parsed
        # the same files again when DATA8 was absent or invalid.
        if data8_record is not None and not _data8_record_valid(data8_record, root, plan):
            if not active.recompute_invalid:
                raise TrainingDataSerializationError("Invalid existing DATA8 artifact.")
            _remove_data8_pointer(root / data8_record.relative_directory)
            data8_record = None
        retain_verified_data7 = active.materialize_data8 and data8_record is None
        for domain_digest, record in tuple(records.items()):
            restored_bundle = _load_valid_data7_record(record, root, plan)
            if restored_bundle is not None:
                if retain_verified_data7:
                    resolved_bundles[domain_digest] = restored_bundle
                continue
            if not active.recompute_invalid:
                raise TrainingDataSerializationError(f"Invalid existing DATA7 artifact for domain {domain_digest}.")
            del records[domain_digest]
            if data8_record is not None:
                _remove_data8_pointer(root / data8_record.relative_directory)
            data8_record = None

    prediction_energy: Mapping[str, float] | None = foundation_prediction_energy_by_frame
    if prediction_energy is None and model_sweep_artifacts.prediction_manifest is not None:
        if progress_callback is not None:
            progress_callback("status=phase; phase=reading-authenticated-foundation-energies")
        cache = model_sweep_artifacts.prediction_cache()
        prediction_energy = {
            item.frame_uid: cache.energy_for_frame(item.frame_uid)
            for item in model_sweep_artifacts.prediction_manifest.records
        }
    new_domains = 0
    canonical_domain_digests = frozenset(item.content_digest for item in plan.domains)
    frame_record_by_uid = {item.frame_uid: item for item in frame_catalog.frames}
    event_anchor_frame_uids = frozenset(
        event.anchor_frame_uid for event in data4_bundle.events.events
    )
    protected_event_frame_uids = frozenset(data4_bundle.events.protected_frame_uids)
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = (
        None
        if shared_frame_array_index_cache is None
        else shared_frame_array_index_cache.get(frame_catalog.content_digest)
    )
    mace_summary_cache: dict[
        tuple[str, tuple[int, ...]], tuple[Any, Any]
    ] = {}
    composition_count_cache: dict[str, Mapping[int, int]] = {}
    try:
        for domain in plan.domains:
            if domain.content_digest in records:
                continue
            if active.max_new_data7_domains is not None and new_domains >= active.max_new_data7_domains:
                break
            recipe_digest = _data7_recipe_digest(plan, domain)
            domain_label = (
                f"DATA7 kind={domain.kind.value} fold={domain.fold_index}"
            )

            def domain_progress(message: str, *, _label: str = domain_label) -> None:
                if progress_callback is not None:
                    progress_callback(f"{_label}: {message}")

            artifact = None if shared_memory is None else shared_memory.get(recipe_digest)
            bundle: Data7PreparationBundle | None = None
            if artifact is not None and Path(artifact.path).is_file():
                if progress_callback is not None:
                    progress_callback(
                        f"DATA7 domain; progress={format_progress_fraction(new_domains + 1, len(plan.domains))}; status=reuse-in-process; "
                        f"kind={domain.kind.value} fold={domain.fold_index}"
                    )
            elif shared_cache_root is not None:
                restored_shared = _load_reusable_data7_artifact(
                    shared_cache_root, recipe_digest, domain, plan
                )
                if restored_shared is not None:
                    artifact, bundle = restored_shared
                    resolved_bundles[domain.content_digest] = bundle
                    if shared_memory is not None:
                        shared_memory[recipe_digest] = artifact
                    if progress_callback is not None:
                        progress_callback(
                            f"DATA7 domain; progress={format_progress_fraction(new_domains + 1, len(plan.domains))}; status=reuse-verified; "
                            f"kind={domain.kind.value} fold={domain.fold_index}"
                        )
            if artifact is None:
                if progress_callback is not None:
                    progress_callback(
                        f"DATA7 domain; progress={format_progress_fraction(new_domains + 1, len(plan.domains))}; status=building; "
                        f"kind={domain.kind.value} fold={domain.fold_index}"
                    )
                if frame_array_index is None:
                    if progress_callback is not None:
                        progress_callback("status=phase; phase=building-shared-frame-array-index; consumer=DATA7")
                    from ._frame_access import build_frame_array_index

                    frame_array_index = build_frame_array_index(
                        frame_catalog, frame_data_by_run
                    )
                    if shared_frame_array_index_cache is not None:
                        shared_frame_array_index_cache[frame_catalog.content_digest] = frame_array_index
                bundle = build_data7_preparation_bundle(
                    source_catalog, frame_catalog, frame_data_by_run, data4_bundle, data5_bundle, data6_bundle, domain,
                    feature_metric_policy=plan.feature_metric_policy,
                    atomic_reference_policy=plan.atomic_reference_policy,
                    objective_policy=plan.objective_policy,
                    configuration_weight_policy=plan.configuration_weight_policy,
                    checkpoint_metric_policy=plan.checkpoint_metric_policy,
                    selection_budget_policy=plan.selection_budget_policy,
                    mace_descriptor_root=model_sweep_artifacts.root_directory if mace_descriptor_root is None else mace_descriptor_root,
                    foundation_prediction_energy_by_frame=(prediction_energy if plan.atomic_reference_policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL else None),
                    foundation_reference_energies=(dict(plan.foundation_reference_energies) or None) if plan.atomic_reference_policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL else None,
                    foundation_checkpoint_digest=None,
                    foundation_identity_digest=(plan.foundation_checkpoint.canonical_content_digest if plan.atomic_reference_policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL else None),
                    frame_array_index=frame_array_index,
                    mace_summary_cache=mace_summary_cache,
                    composition_count_cache=composition_count_cache,
                    canonical_domain_digests=canonical_domain_digests,
                    frame_record_by_uid=frame_record_by_uid,
                    event_anchor_frame_uids=event_anchor_frame_uids,
                    protected_event_frame_uids=protected_event_frame_uids,
                    progress_callback=domain_progress,
                )
                resolved_bundles[domain.content_digest] = bundle
                if not _data7_bundle_matches_plan(bundle, plan, domain):
                    raise TrainingDataSerializationError(
                        "New DATA7 artifact does not match its scientific recipe."
                    )
                if shared_cache_root is not None:
                    artifact = _write_reusable_data7_artifact(
                        shared_cache_root, recipe_digest, domain, bundle
                    )
                    if shared_memory is not None:
                        shared_memory[recipe_digest] = artifact
            relative = Path("data7") / f"{domain.content_digest}.data7.zip"
            path = root / relative
            if artifact is not None:
                _atomic_link_or_copy(Path(artifact.path), path)
                bundle_digest = artifact.bundle_digest
                file_sha256 = artifact.file_sha256
            else:
                assert bundle is not None
                file_sha256 = write_data7_archive(bundle, path)
                bundle_digest = bundle.content_digest
            if bundle is not None:
                resolved_bundles[domain.content_digest] = bundle
            records[domain.content_digest] = ProductionData7ArtifactRecord(
                domain_digest=domain.content_digest,
                relative_path=relative.as_posix(),
                bundle_digest=bundle_digest,
                file_sha256=file_sha256,
            )
            new_domains += 1
            checkpoint = ProductionMaterializationCheckpoint(plan=plan, data7_artifacts=tuple(records.values()), status=ProductionMaterializationStatus.INCOMPLETE)
            _atomic_json(checkpoint_path, checkpoint.to_dict())

        all_data7 = len(records) == len(plan.domains)
        if all_data7 and active.materialize_data8 and data8_record is None:
            # Descriptor summaries are a cross-domain extraction cache only;
            # DATA8 consumes the compact DATA7 bundles, not these raw summary
            # arrays. Release them before loading/assembling all DATA7 domains
            # together to avoid avoidable peak memory and swap-induced stalls.
            mace_summary_cache.clear()
            if progress_callback is not None:
                progress_callback("status=phase; phase=assembling-DATA8-fixed-files")
            bundles_list: list[Data7PreparationBundle] = []
            for domain_number, domain in enumerate(plan.domains, start=1):
                bundle = resolved_bundles.get(domain.content_digest)
                if bundle is None:
                    if progress_callback is not None:
                        progress_callback(
                            f"DATA7 domain; progress={format_progress_fraction(domain_number, len(plan.domains))}; status=loading; "
                            "for DATA8 assembly"
                        )
                    bundle = _load_valid_data7_record(
                        records[domain.content_digest], root, plan
                    )
                    if bundle is None:
                        raise TrainingDataSerializationError(
                            "DATA7 artifact became invalid before DATA8 assembly."
                        )
                    resolved_bundles[domain.content_digest] = bundle
                bundles_list.append(bundle)
            bundles = tuple(bundles_list)
            if frame_array_index is None:
                if progress_callback is not None:
                    progress_callback("status=phase; phase=building-shared-frame-array-index; consumer=DATA8")
                from ._frame_access import build_frame_array_index
                frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)
                if shared_frame_array_index_cache is not None:
                    shared_frame_array_index_cache[frame_catalog.content_digest] = frame_array_index
            staging = root / f".data8-staging-{os.getpid()}-{uuid.uuid4().hex}"
            shutil.rmtree(staging, ignore_errors=True)
            bundle8 = build_data8_preparation_bundle(
                source_catalog, frame_catalog, frame_data_by_run, data5_bundle, bundles,
                output_directory=staging,
                foundation_checkpoint=plan.foundation_checkpoint,
                selected_head_qualification=plan.selected_head_qualification,
                compatibility_probe=plan.compatibility_probe,
                compatibility_policy=plan.compatibility_policy,
                replay_plan=plan.replay_plan,
                online_monitor_policy=plan.online_monitor_policy,
                true_replay_monitor_artifact=plan.true_replay_monitor_artifact,
                adaptive_stop_policy=plan.adaptive_stop_policy,
                training_budget_policy=plan.training_budget_policy,
                learning_rate_schedule_policy=plan.learning_rate_schedule_policy,
                checkpoint_admissibility_policy=plan.checkpoint_admissibility_policy,
                checkpoint_selection_policy=plan.checkpoint_selection_policy,
                optimizer_policy=plan.optimizer_policy,
                checkpoint_control_policy=plan.checkpoint_control_policy,
                extxyz_policy=plan.extxyz_policy,
                real_pt_data_ratio_threshold=plan.real_pt_data_ratio_threshold,
                selection_size=plan.selection_size,
                require_foundation_residual_e0=plan.require_foundation_residual_e0,
                cross_validation_plans=(
                    None
                    if plan.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA
                    else plan.cross_validation_plans
                ),
                frame_array_index=frame_array_index,
                shared_fixed_file_cache_directory=shared_data8_fixed_file_cache_directory,
            )
            _atomic_json(staging / "data8_preparation_bundle.json", bundle8.to_dict())
            entries = _tree_entries(staging)
            tree_digest = _tree_digest(entries)
            final_dir = _promote_data8_tree(root, staging, tree_digest)
            data8_record = ProductionData8ArtifactRecord(relative_directory="data8", bundle_relative_path="data8/data8_preparation_bundle.json", bundle_digest=bundle8.content_digest, tree_entries=entries, tree_digest=tree_digest)
            # The staging tree was hashed immediately before an atomic rename,
            # and ``_promote_data8_tree`` validates an already-existing content-
            # addressed generation before reuse.  Rehashing the entire promoted
            # tree here duplicates all DATA8 I/O; retain only a pointer sanity
            # check. Full verification remains mandatory when restoring later.
            if not final_dir.is_dir() or not (final_dir / "data8_preparation_bundle.json").is_file():
                raise TrainingDataSerializationError("Promoted DATA8 artifact pointer is invalid.")

        complete = all_data7 and data8_record is not None
        checkpoint = ProductionMaterializationCheckpoint(plan=plan, data7_artifacts=tuple(records.values()), data8_artifact=data8_record, status=ProductionMaterializationStatus.COMPLETE if complete else ProductionMaterializationStatus.INCOMPLETE)
        _atomic_json(checkpoint_path, checkpoint.to_dict())
        return ProductionMaterializationRecord(root_directory=str(root), checkpoint=checkpoint)
    except Exception as exc:
        for staging in root.glob(".data8-staging-*"):
            shutil.rmtree(staging, ignore_errors=True)
        failed = ProductionMaterializationCheckpoint(plan=plan, data7_artifacts=tuple(records.values()), data8_artifact=data8_record, status=ProductionMaterializationStatus.FAILED, failure_type=type(exc).__name__, failure_message=str(exc))
        _atomic_json(checkpoint_path, failed.to_dict())
        raise


def load_production_materialization(output_directory: str | Path) -> ProductionMaterializationRecord:
    root = Path(output_directory).resolve()
    path = root / "production_materialization_checkpoint.json"
    if not path.is_file():
        raise TrainingDataInputError("Production materialization checkpoint is absent.")
    checkpoint = ProductionMaterializationCheckpoint.from_dict(json.loads(path.read_text(encoding="utf-8")))
    for record in checkpoint.data7_artifacts:
        if not _data7_record_valid(record, root, checkpoint.plan):
            raise TrainingDataSerializationError("Restored production DATA7 artifact failed verification.")
    if checkpoint.data8_artifact is not None and not _data8_record_valid(checkpoint.data8_artifact, root, checkpoint.plan):
        raise TrainingDataSerializationError("Restored production DATA8 artifact failed verification.")
    return ProductionMaterializationRecord(root_directory=str(root), checkpoint=checkpoint)
