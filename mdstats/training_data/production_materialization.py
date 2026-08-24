"""Restartable production DATA6--DATA8 materialization.

This module owns orchestration, immutable lineage, restart checkpoints, and
atomic promotion of DATA7/DATA8 artifacts.  Scientific feature fitting remains
owned by DATA7 and MACE artifact construction remains owned by DATA8.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import uuid

import numpy as np

from threading import Lock
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
    validate_data7_fitted_component_reuse,
)
from .data8_bundle import Data8PreparationBundle, build_data8_preparation_bundle
from .data7_archive import (
    Data7ArchiveError, read_data7_archive, write_data7_archive,
)
from .feature_metric import FeatureFitDomain, FeatureFitDomainKind, FeatureMetricPolicyTemplate, build_feature_fit_domains
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
from .resources import (
    SystemResourceSnapshot,
    build_stage_resource_scope,
    detect_system_resources,
)
from .work_queue import DeterministicOrderedReducer, DeterministicWorkQueue

PRODUCTION_MATERIALIZATION_POLICY_SCHEMA = "mdstats.production-materialization-policy.v1"
PRODUCTION_MATERIALIZATION_PLAN_SCHEMA = "mdstats.production-materialization-plan.v10"
PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA = "mdstats.production-materialization-plan.v9"
PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA = "mdstats.production-materialization-plan.v8"
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
SHARED_DATA7_ARTIFACT_SCHEMA = "mdstats.shared-data7-artifact.v3"
SHARED_DATA7_ARTIFACT_V2_SCHEMA = "mdstats.shared-data7-artifact.v2"
SHARED_DATA7_ARTIFACT_LEGACY_SCHEMA = "mdstats.shared-data7-artifact.v1"
SHARED_DATA7_RECIPE_SCHEMA = "mdstats.shared-data7-recipe.v2"
SHARED_DATA7_RECIPE_V1_SCHEMA = "mdstats.shared-data7-recipe.v1"
SHARED_DATA7_FIT_CORE_SCHEMA = "mdstats.shared-data7-fit-core.v1"
SHARED_DATA7_FIT_CORE_INDEX_SCHEMA = "mdstats.shared-data7-fit-core-index.v2"
SHARED_DATA7_FIT_CORE_INDEX_V1_SCHEMA = "mdstats.shared-data7-fit-core-index.v1"
DATA7_FIT_CORE_REUSE_MIN_DOMAIN_FRAMES = 128


@dataclass(frozen=True, slots=True)
class _ReusableData7Artifact:
    recipe_digest: str
    domain_digest: str
    bundle_digest: str
    file_sha256: str
    path: str


@dataclass(frozen=True, slots=True)
class _Data7ArtifactReceipt:
    recipe_digest: str
    domain_digest: str
    bundle_digest: str
    file_sha256: str
    path: str
    source: str
    wall_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class _ReusableData7FitCore:
    fit_core_digest: str
    fitted_result_digest: str
    carrier_recipe_digest: str
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


def _publish_json_create_once(path: Path, payload: Mapping[str, Any]) -> bool:
    """Publish a complete JSON file only if no concurrent publisher won first."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    )
    encoded = (
        json.dumps(payload, sort_keys=False, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    try:
        with temporary.open("xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
    finally:
        temporary.unlink(missing_ok=True)


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
    selection_authority_role: str = "standard"
    target_size_study_digest: str | None = None
    prescribed_final_development_prefixes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    prescribed_training_domain_prefixes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    prescribed_target_size_evaluation_frames: tuple[tuple[str, tuple[str, ...]], ...] = ()
    require_foundation_residual_e0: bool = True
    require_replay: bool = True
    plan_version: str = MLFF_DATA9A9B_VERSION
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

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
        topology_keys = tuple(
            (item.label_domain_id, item.kind.value, item.fold_index) for item in domains
        )
        if len(set(topology_keys)) != len(topology_keys):
            raise TrainingDataInputError(
                "Production materialization requires unique DATA7 domain topology keys."
            )
        source_labels = {item.label_domain_id for item in domains}
        final_counts = {
            label: sum(
                item.label_domain_id == label
                and item.kind is FeatureFitDomainKind.FINAL_DEVELOPMENT
                for item in domains
            )
            for label in source_labels
        }
        if any(count != 1 for count in final_counts.values()):
            raise TrainingDataInputError(
                "Production materialization requires exactly one final-development domain per source label."
            )
        if any(item.data5_bundle_digest != self.data5_bundle_digest for item in domains):
            raise TrainingDataInputError("Production DATA7 domain/DATA5 lineage mismatch.")
        object.__setattr__(self, "domains", domains)
        if self.plan_schema not in {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA,
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
        domain_fold_sequence = tuple(
            (item.label_domain_id, item.fold_index)
            for item in domains
            if item.kind is FeatureFitDomainKind.CROSS_VALIDATION_TRAINING
        )
        domain_fold_pairs = set(domain_fold_sequence)
        if len(domain_fold_sequence) != len(domain_fold_pairs):
            raise TrainingDataInputError(
                "Production DATA7 domains contain duplicate cross-validation topology keys."
            )
        if self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_SCHEMA and domain_fold_pairs and not plans:
            raise TrainingDataInputError(
                "Current production DATA7 plans with cross-validation domains require configured cross-validation plans."
            )
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
            if self.plan_schema not in {
                PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
                PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
            }:
                raise TrainingDataInputError(
                    "Selected-head training qualification requires production materialization v9 or newer."
                )
        elif self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA:
            raise TrainingDataInputError(
                "Legacy production materialization v9 requires selected-head training qualification."
            )
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
        train2_schemas = {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA,
        }
        if self.plan_schema in train2_schemas and not train2_active:
            raise TrainingDataInputError(
                "Production materialization v6/v7/v8/v9/v10 requires complete TRAIN2 authority."
            )
        if self.plan_schema not in train2_schemas and train2_active:
            raise TrainingDataInputError(
                "TRAIN2 authority requires production materialization v6, v7, v8, v9, or v10."
            )
        if self.real_pt_data_ratio_threshold < 0.0:
            raise TrainingDataInputError("real_pt_data_ratio_threshold must be nonnegative.")
        if self.selection_size is not None and self.selection_size < 1:
            raise TrainingDataInputError("selection_size must be positive when present.")
        role = str(self.selection_authority_role)
        allowed_roles = {"standard", "target_size_candidate", "selected_production_prefix"}
        if role not in allowed_roles:
            raise TrainingDataInputError("Unsupported production selection authority role.")
        legacy_prefixes = tuple(
            sorted(
                (str(label), tuple(str(uid) for uid in uids))
                for label, uids in self.prescribed_final_development_prefixes
            )
        )
        prefixes = tuple(
            sorted(
                (str(domain_digest), tuple(str(uid) for uid in uids))
                for domain_digest, uids in self.prescribed_training_domain_prefixes
            )
        )
        evaluation_frames = tuple(
            sorted(
                (str(label), tuple(str(uid) for uid in uids))
                for label, uids in self.prescribed_target_size_evaluation_frames
            )
        )
        if len({label for label, _ in legacy_prefixes}) != len(legacy_prefixes):
            raise TrainingDataInputError("Legacy prescribed final-development prefixes require unique label domains.")
        if len({domain_digest for domain_digest, _ in prefixes}) != len(prefixes):
            raise TrainingDataInputError("Prescribed target training prefixes require unique DATA7 domain identities.")
        if legacy_prefixes and prefixes:
            raise TrainingDataInputError("Target membership cannot have both legacy label-prefix and training-domain-prefix authorities.")
        domain_by_digest = {item.content_digest: item for item in self.domains}
        frame_uid_set_by_domain_digest = {
            item.content_digest: frozenset(item.frame_uids) for item in self.domains
        }
        final_domains = {
            item.label_domain_id: item
            for item in self.domains
            if item.kind is FeatureFitDomainKind.FINAL_DEVELOPMENT
        }
        final_frame_uid_set_by_label = {
            label: frame_uid_set_by_domain_digest[domain.content_digest]
            for label, domain in final_domains.items()
        }
        if legacy_prefixes:
            if any(item.kind is not FeatureFitDomainKind.FINAL_DEVELOPMENT for item in self.domains):
                raise TrainingDataInputError(
                    "Legacy label-domain prefixes cannot authorize target-size materialization with CV training domains."
                )
            if set(label for label, _ in legacy_prefixes) != set(final_domains):
                raise TrainingDataInputError(
                    "Legacy target-size prefix materialization must bind every final-development label domain exactly once."
                )
            prefixes = tuple(sorted(
                (final_domains[label].content_digest, uids)
                for label, uids in legacy_prefixes
            ))
            legacy_prefixes = ()
        if role == "standard":
            if prefixes or evaluation_frames or self.target_size_study_digest is not None:
                raise TrainingDataInputError("Standard DATA7 selection cannot claim target-size prefix authority.")
        else:
            if self.plan_schema not in {
                PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
                PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
            }:
                raise TrainingDataInputError("Target-size prefix materialization requires current production plan authority.")
            if self.target_size_study_digest is None:
                raise TrainingDataInputError("Target-size prefix materialization requires the target-size study digest.")
            object.__setattr__(
                self, "target_size_study_digest",
                validate_digest(self.target_size_study_digest, name="target_size_study_digest"),
            )
            if self.selection_size is None or not prefixes:
                raise TrainingDataInputError("Target-size prefix materialization requires a selected size and domain prefixes.")
            if set(domain_digest for domain_digest, _ in prefixes) != set(domain_by_digest):
                raise TrainingDataInputError(
                    "Target-size prefix materialization must bind every final/CV gradient-training DATA7 domain exactly once."
                )
            for domain_digest, uids in prefixes:
                domain = domain_by_digest[domain_digest]
                if len(uids) != self.selection_size or len(set(uids)) != len(uids):
                    raise TrainingDataInputError("Each prescribed target-size prefix must equal selection_size with unique frames.")
                if not set(uids).issubset(frame_uid_set_by_domain_digest[domain_digest]):
                    raise TrainingDataInputError(
                        "Prescribed target-size prefix contains frames outside its gradient-training domain."
                    )
            if role == "target_size_candidate":
                if set(label for label, _ in evaluation_frames) != set(final_domains):
                    raise TrainingDataInputError("Candidate target-size materialization requires one development-complement evaluation cohort per label domain.")
                prefix_by_label = {
                    domain_by_digest[domain_digest].label_domain_id: uids
                    for domain_digest, uids in prefixes
                    if domain_by_digest[domain_digest].kind is FeatureFitDomainKind.FINAL_DEVELOPMENT
                }
                for label, uids in evaluation_frames:
                    if not uids or len(uids) != len(set(uids)):
                        raise TrainingDataInputError("Candidate target-size evaluation cohorts must be non-empty and unique.")
                    if not set(uids).issubset(final_frame_uid_set_by_label[label]):
                        raise TrainingDataInputError("Candidate target-size evaluation cohort lies outside its development domain.")
                    if set(uids) & set(prefix_by_label[label]):
                        raise TrainingDataInputError("Candidate target-size evaluation cohort overlaps target training membership.")
            elif evaluation_frames:
                raise TrainingDataInputError("Only target_size_candidate materializations may bind the pre-selection development evaluation cohort.")
        object.__setattr__(self, "selection_authority_role", role)
        object.__setattr__(self, "prescribed_final_development_prefixes", legacy_prefixes)
        object.__setattr__(self, "prescribed_training_domain_prefixes", prefixes)
        object.__setattr__(self, "prescribed_target_size_evaluation_frames", evaluation_frames)

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
            "selection_authority_role": self.selection_authority_role,
            "target_size_study_digest": self.target_size_study_digest,
            "prescribed_final_development_prefixes": [
                [label, list(uids)] for label, uids in self.prescribed_final_development_prefixes
            ],
            "prescribed_target_size_evaluation_frames": [
                [label, list(uids)] for label, uids in self.prescribed_target_size_evaluation_frames
            ],
            "require_foundation_residual_e0": self.require_foundation_residual_e0,
            "require_replay": self.require_replay,
        }
        # This field is an optional current-v9 extension.  Omitting the empty
        # value preserves digest compatibility for unrelated standard v9 plans,
        # while target-size-controlled plans authenticate the new final/CV
        # training-domain prefix authority explicitly.
        if self.prescribed_training_domain_prefixes:
            payload["prescribed_training_domain_prefixes"] = [
                [domain_digest, list(uids)]
                for domain_digest, uids in self.prescribed_training_domain_prefixes
            ]
        if self.plan_schema in {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
        }:
            payload["selected_head_qualification"] = (
                None
                if self.selected_head_qualification is None
                else self.selected_head_qualification.to_dict()
            )
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V3_SCHEMA}:
            payload["cross_validation_plans"] = [
                item.to_dict() for item in self.cross_validation_plans
            ]
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V4_SCHEMA}:
            payload["online_monitor_policy"] = None if self.online_monitor_policy is None else self.online_monitor_policy.to_dict()
            payload["true_replay_monitor_artifact"] = None if self.true_replay_monitor_artifact is None else self.true_replay_monitor_artifact.to_dict()
        if self.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA:
            payload["adaptive_stop_policy"] = None if self.adaptive_stop_policy is None else self.adaptive_stop_policy.to_dict()
        if self.plan_schema in {PRODUCTION_MATERIALIZATION_PLAN_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA, PRODUCTION_MATERIALIZATION_PLAN_V6_SCHEMA}:
            payload.update({
                "training_budget_policy": None if self.training_budget_policy is None else self.training_budget_policy.to_dict(),
                "learning_rate_schedule_policy": None if self.learning_rate_schedule_policy is None else self.learning_rate_schedule_policy.to_dict(),
                "checkpoint_admissibility_policy": None if self.checkpoint_admissibility_policy is None else self.checkpoint_admissibility_policy.to_dict(),
                "checkpoint_selection_policy": None if self.checkpoint_selection_policy is None else self.checkpoint_selection_policy.to_dict(),
            })
        return payload

    @property
    def content_digest(self) -> str:
        return self._content_digest_for_payload()

    def _content_digest_for_payload(self, payload: Mapping[str, Any] | None = None) -> str:
        cached = self._content_digest_cache
        if cached:
            return cached
        value = digest(self._payload() if payload is None else payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return value

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": self._content_digest_for_payload(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionMaterializationPlan":
        schema = payload.get("schema")
        if schema not in {
            PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA,
            PRODUCTION_MATERIALIZATION_PLAN_V8_SCHEMA,
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
            selection_authority_role=str(payload.get("selection_authority_role", "standard")),
            target_size_study_digest=(None if payload.get("target_size_study_digest") is None else str(payload["target_size_study_digest"])),
            prescribed_final_development_prefixes=tuple(
                (str(item[0]), tuple(str(uid) for uid in item[1]))
                for item in payload.get("prescribed_final_development_prefixes", ())
            ),
            prescribed_training_domain_prefixes=tuple(
                (str(item[0]), tuple(str(uid) for uid in item[1]))
                for item in payload.get("prescribed_training_domain_prefixes", ())
            ),
            prescribed_target_size_evaluation_frames=tuple(
                (str(item[0]), tuple(str(uid) for uid in item[1]))
                for item in payload.get("prescribed_target_size_evaluation_frames", ())
            ),
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
        plan_order = {
            domain.content_digest: index for index, domain in enumerate(self.plan.domains)
        }
        records = tuple(self.data7_artifacts)
        if len({item.domain_digest for item in records}) != len(records):
            raise TrainingDataInputError("Production checkpoint contains duplicate DATA7 domains.")
        if not set(item.domain_digest for item in records).issubset(plan_order):
            raise TrainingDataInputError("Production checkpoint contains foreign DATA7 domains.")
        records = tuple(sorted(records, key=lambda item: plan_order[item.domain_digest]))
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
        parsed_records = tuple(
            ProductionData7ArtifactRecord.from_dict(item)
            for item in payload.get("data7_artifacts", ())
        )
        result = cls(
            plan=ProductionMaterializationPlan.from_dict(payload["plan"]),
            data7_artifacts=parsed_records,
            data8_artifact=(
                None if payload.get("data8_artifact") is None
                else ProductionData8ArtifactRecord.from_dict(payload["data8_artifact"])
            ),
            status=ProductionMaterializationStatus(payload["status"]),
            failure_type=None if payload.get("failure_type") is None else str(payload["failure_type"]),
            failure_message=None if payload.get("failure_message") is None else str(payload["failure_message"]),
        )
        serialized_digest = payload.get("content_digest")
        if serialized_digest not in (None, result.content_digest):
            # DATA78-PAR1 serialized DATA7 artifact records in lexical digest
            # order.  CLOSEOUT1 changes the canonical order to ``plan.domains``
            # while retaining read compatibility with those already-written
            # checkpoints.  New writes always use plan order.
            legacy_records = tuple(sorted(parsed_records, key=lambda item: item.domain_digest))
            legacy_payload = {
                "schema": PRODUCTION_MATERIALIZATION_CHECKPOINT_SCHEMA,
                "plan": result.plan.to_dict(),
                "data7_artifacts": [item.to_dict() for item in legacy_records],
                "data8_artifact": (
                    None if result.data8_artifact is None else result.data8_artifact.to_dict()
                ),
                "status": result.status.value,
                "failure_type": result.failure_type,
                "failure_message": result.failure_message,
            }
            if serialized_digest != digest(legacy_payload):
                raise TrainingDataSerializationError(
                    "Production materialization checkpoint digest mismatch."
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
        bundles: list[Data7PreparationBundle] = []
        for domain in self.checkpoint.plan.domains:
            record = indexed.get(domain.content_digest)
            if record is None:
                continue
            bundle = _load_valid_data7_record(record, root, self.checkpoint.plan)
            if bundle is None:
                raise TrainingDataSerializationError(
                    "Production DATA7 artifact failed verification before loading."
                )
            bundles.append(bundle)
        return tuple(bundles)

    def load_data8_bundle(self) -> Data8PreparationBundle:
        if self.checkpoint.data8_artifact is None:
            raise TrainingDataInputError("Production materialization has no DATA8 artifact.")
        root = Path(self.root_directory)
        bundle = _load_valid_data8_record(
            self.checkpoint.data8_artifact, root, self.checkpoint.plan
        )
        if bundle is None:
            raise TrainingDataSerializationError("Production DATA8 artifact failed verification before loading.")
        return bundle

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
    selection_authority_role: str = "standard",
    target_size_study_digest: str | None = None,
    prescribed_final_development_prefixes: Mapping[str, Sequence[str]] | None = None,
    prescribed_training_domain_prefixes: Mapping[str, Sequence[str]] | None = None,
    prescribed_target_size_evaluation_frames: Mapping[str, Sequence[str]] | None = None,
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
    active_feature_domains = build_feature_fit_domains(
        data5_bundle,
        cross_validation_plans=active_cv_plans,
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
        domains=active_feature_domains,
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
            if (
                training_budget_policy is not None
                and selection_authority_role != "standard"
                and selected_head_qualification is None
            )
            else PRODUCTION_MATERIALIZATION_PLAN_V9_SCHEMA
            if training_budget_policy is not None and selected_head_qualification is not None
            else PRODUCTION_MATERIALIZATION_PLAN_V7_SCHEMA
            if training_budget_policy is not None
            else PRODUCTION_MATERIALIZATION_PLAN_V5_SCHEMA
        ),
        real_pt_data_ratio_threshold=real_pt_data_ratio_threshold,
        selection_size=selection_size,
        selection_authority_role=selection_authority_role,
        target_size_study_digest=target_size_study_digest,
        prescribed_final_development_prefixes=tuple(
            (str(label), tuple(str(uid) for uid in uids))
            for label, uids in (prescribed_final_development_prefixes or {}).items()
        ),
        prescribed_training_domain_prefixes=tuple(
            (str(domain_digest), tuple(str(uid) for uid in uids))
            for domain_digest, uids in (prescribed_training_domain_prefixes or {}).items()
        ),
        prescribed_target_size_evaluation_frames=tuple(
            (str(label), tuple(str(uid) for uid in uids))
            for label, uids in (prescribed_target_size_evaluation_frames or {}).items()
        ),
        require_foundation_residual_e0=require_foundation_residual_e0,
        require_replay=require_replay,
    )


def _data7_recipe_payload(
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> dict[str, Any]:
    """Identity of every input that can change a DATA7 scientific artifact.

    Optimizer seed, replay mode, output layout, and other DATA8-only controls are
    deliberately excluded, allowing exact DATA7 reuse across training variants.
    """

    return {
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
        "selection_authority_role": plan.selection_authority_role,
        "prescribed_training_domain_prefix": (
            None
            if plan.selection_authority_role == "standard"
            else list(dict(plan.prescribed_training_domain_prefixes).get(domain.content_digest, ()))
        ),
        "foundation_checkpoint_sha256": plan.foundation_checkpoint.sha256,
        "foundation_identity_digest": plan.foundation_checkpoint.canonical_content_digest,
        "foundation_reference_energies": {
            str(z): value for z, value in plan.foundation_reference_energies
        },
    }


def _data7_recipe_digest(
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> str:
    return digest(_data7_recipe_payload(plan, domain))


def _data7_recipe_digest_v1(
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> str:
    payload = _data7_recipe_payload(plan, domain)
    payload["schema"] = SHARED_DATA7_RECIPE_V1_SCHEMA
    payload["target_size_study_digest"] = plan.target_size_study_digest
    payload["prescribed_target_size_evaluation_frames"] = (
        None
        if domain.kind is not FeatureFitDomainKind.FINAL_DEVELOPMENT
        else list(
            dict(plan.prescribed_target_size_evaluation_frames).get(
                domain.label_domain_id, ()
            )
        )
    )
    return digest(payload)


def _data7_fit_core_digest(
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> str:
    """Execution identity of selection-invariant DATA7 fitted products."""

    return digest({
        "schema": SHARED_DATA7_FIT_CORE_SCHEMA,
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
        "foundation_checkpoint_sha256": plan.foundation_checkpoint.sha256,
        "foundation_identity_digest": plan.foundation_checkpoint.canonical_content_digest,
        "foundation_reference_energies": {
            str(z): value for z, value in plan.foundation_reference_energies
        },
    })


def _data7_fitted_result_digest(bundle: Data7PreparationBundle) -> str:
    """Authenticate the selection-invariant fitted products carried by DATA7."""

    return digest({
        "schema": "mdstats.shared-data7-fitted-result.v1",
        "fitted_metric_digest": bundle.fitted_metric.content_digest,
        "atomic_reference_fit_digest": bundle.atomic_reference_fit.content_digest,
        "training_weights_digest": bundle.training_weights.content_digest,
        "checkpoint_metric_policy_digest": bundle.checkpoint_metric_policy.policy_digest,
    })


def _register_reusable_data7_fit_core(
    registry: MutableMapping[str, _ReusableData7FitCore],
    carrier: _ReusableData7FitCore,
) -> None:
    previous = registry.get(carrier.fit_core_digest)
    if previous is not None:
        if (
            previous.fitted_result_digest != carrier.fitted_result_digest
            or previous.domain_digest != carrier.domain_digest
        ):
            raise TrainingDataSerializationError(
                "Conflicting DATA7 fitted-core results share one execution recipe: "
                f"fit_core={carrier.fit_core_digest}; "
                f"existing_result={previous.fitted_result_digest}; "
                f"candidate_result={carrier.fitted_result_digest}; "
                f"existing_carrier={previous.carrier_recipe_digest}; "
                f"candidate_carrier={carrier.carrier_recipe_digest}."
            )
        return
    registry[carrier.fit_core_digest] = carrier



def _data7_fitted_core_matches_plan(
    bundle: Data7PreparationBundle,
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> bool:
    requires_foundation = (
        plan.atomic_reference_policy.fit_mode
        is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
    )
    plan_reference_energies = dict(plan.foundation_reference_energies)
    element_order = tuple(int(z) for z in bundle.atomic_reference_fit.element_order)
    expected_domain_references = (
        tuple((z, plan_reference_energies[z]) for z in element_order)
        if requires_foundation
        and all(z in plan_reference_energies for z in element_order)
        else (() if not requires_foundation else None)
    )
    return (
        bundle.dataset_id == plan.dataset_id
        and bundle.source_catalog_digest == plan.source_catalog_digest
        and bundle.frame_catalog_digest == plan.frame_catalog_digest
        and bundle.data4_bundle_digest == plan.data4_bundle_digest
        and bundle.data5_bundle_digest == plan.data5_bundle_digest
        and bundle.data6_bundle_digest == plan.data6_bundle_digest
        and bundle.domain.content_digest == domain.content_digest
        and bundle.fitted_metric.policy.policy_digest
        == plan.feature_metric_policy.policy_digest
        and bundle.atomic_reference_fit.policy.policy_digest
        == plan.atomic_reference_policy.policy_digest
        and (
            (not requires_foundation and bundle.atomic_reference_fit.foundation_lineage_digest is None)
            or (
                requires_foundation
                and foundation_identity_matches_lineage(
                    plan.foundation_checkpoint,
                    foundation_identity_digest=bundle.atomic_reference_fit.foundation_identity_digest,
                    legacy_checkpoint_digest=bundle.atomic_reference_fit.foundation_checkpoint_digest,
                )
            )
        )
        and bundle.atomic_reference_fit.foundation_reference_energies_ev
        == expected_domain_references
        and bundle.training_weights.objective_policy.policy_digest
        == plan.objective_policy.policy_digest
        and bundle.training_weights.configuration_policy.policy_digest
        == plan.configuration_weight_policy.policy_digest
        and bundle.checkpoint_metric_policy.policy_digest
        == plan.checkpoint_metric_policy.policy_digest
    )


def _data7_bundle_matches_plan(
    bundle: Data7PreparationBundle,
    plan: ProductionMaterializationPlan,
    domain: FeatureFitDomain,
) -> bool:
    expected_prefix = dict(plan.prescribed_training_domain_prefixes).get(
        domain.content_digest
    )
    actual_prefix = tuple(item.frame_uid for item in bundle.selection_plan.master_order)
    return (
        _data7_fitted_core_matches_plan(bundle, plan, domain)
        and bundle.selection_plan.policy.policy_digest
        == plan.selection_budget_policy.policy_digest
        and (
            plan.selection_authority_role == "standard"
            or actual_prefix == tuple(expected_prefix or ())
        )
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


def _load_reusable_data7_artifact_from_paths(
    *,
    manifest_path: Path,
    artifact_root: Path,
    recipe_digest: str,
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
) -> tuple[_ReusableData7Artifact, Data7PreparationBundle] | None:
    if not manifest_path.is_file():
        return None
    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            metadata.get("schema") not in {
                SHARED_DATA7_ARTIFACT_SCHEMA,
                SHARED_DATA7_ARTIFACT_V2_SCHEMA,
                SHARED_DATA7_ARTIFACT_LEGACY_SCHEMA,
            }
            or metadata.get("recipe_digest") != recipe_digest
            or metadata.get("domain_digest") != domain.content_digest
        ):
            return None
        artifact_name = metadata.get("artifact_name")
        if artifact_name is None:
            artifact_path = artifact_root / f"{recipe_digest}.json"
        else:
            candidate = Path(str(artifact_name))
            if candidate.is_absolute() or ".." in candidate.parts:
                return None
            artifact_path = artifact_root / candidate
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


def _load_reusable_data7_artifact(
    cache_root: Path,
    recipe_digest: str,
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
) -> tuple[_ReusableData7Artifact, Data7PreparationBundle] | None:
    # Current cache generations are installed atomically as one directory.
    generation = cache_root / recipe_digest[:2] / recipe_digest
    current = _load_reusable_data7_artifact_from_paths(
        manifest_path=generation / "cache.json",
        artifact_root=generation,
        recipe_digest=recipe_digest,
        domain=domain,
        plan=plan,
    )
    if current is not None:
        return current
    # Read-only compatibility for pre-PAR1 flat cache generations.
    return _load_reusable_data7_artifact_from_paths(
        manifest_path=cache_root / f"{recipe_digest}.manifest.json",
        artifact_root=cache_root,
        recipe_digest=recipe_digest,
        domain=domain,
        plan=plan,
    )


def _load_data7_carrier_by_recipe(
    cache_root: Path,
    carrier_recipe_digest: str,
) -> tuple[_ReusableData7Artifact, Data7PreparationBundle] | None:
    locations = (
        (
            cache_root / carrier_recipe_digest[:2] / carrier_recipe_digest / "cache.json",
            cache_root / carrier_recipe_digest[:2] / carrier_recipe_digest,
        ),
        (
            cache_root / f"{carrier_recipe_digest}.manifest.json",
            cache_root,
        ),
    )
    for manifest_path, artifact_root in locations:
        if not manifest_path.is_file():
            continue
        try:
            metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                metadata.get("schema") not in {
                    SHARED_DATA7_ARTIFACT_SCHEMA,
                    SHARED_DATA7_ARTIFACT_V2_SCHEMA,
                    SHARED_DATA7_ARTIFACT_LEGACY_SCHEMA,
                }
                or metadata.get("recipe_digest") != carrier_recipe_digest
            ):
                continue
            artifact_name = metadata.get("artifact_name")
            if artifact_name is None:
                artifact_path = artifact_root / f"{carrier_recipe_digest}.json"
            else:
                candidate = Path(str(artifact_name))
                if candidate.is_absolute() or ".." in candidate.parts:
                    continue
                artifact_path = artifact_root / candidate
            if not artifact_path.is_file():
                continue
            file_sha256 = str(metadata.get("file_sha256", ""))
            bundle = _read_data7_artifact(
                artifact_path, expected_sha256=file_sha256
            )
            if bundle.content_digest != metadata.get("bundle_digest"):
                continue
            return (
                _ReusableData7Artifact(
                    recipe_digest=carrier_recipe_digest,
                    domain_digest=str(metadata.get("domain_digest", "")),
                    bundle_digest=bundle.content_digest,
                    file_sha256=file_sha256,
                    path=str(artifact_path),
                ),
                bundle,
            )
        except Exception:
            continue
    return None


def _fit_core_index_path(cache_root: Path, fit_core_digest: str) -> Path:
    return cache_root / "fit-cores" / fit_core_digest[:2] / f"{fit_core_digest}.json"


def _load_reusable_data7_fit_core(
    cache_root: Path,
    fit_core_digest: str,
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
    *,
    reuse_validator: Callable[[Data7PreparationBundle], bool] | None = None,
    invalidate_invalid: bool = False,
) -> tuple[_ReusableData7FitCore, Data7PreparationBundle] | None:
    path = _fit_core_index_path(cache_root, fit_core_digest)
    if not path.is_file():
        return None

    def invalid() -> None:
        if invalidate_invalid:
            path.unlink(missing_ok=True)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            payload.get("schema") != SHARED_DATA7_FIT_CORE_INDEX_SCHEMA
            or payload.get("fit_core_digest") != fit_core_digest
            or payload.get("domain_digest") != domain.content_digest
        ):
            invalid()
            return None
        fitted_result_digest = validate_digest(
            str(payload.get("fitted_result_digest", "")),
            name="fitted_result_digest",
        )
        carrier_recipe_digest = validate_digest(
            str(payload.get("carrier_recipe_digest", "")),
            name="carrier_recipe_digest",
        )
        loaded = _load_data7_carrier_by_recipe(
            cache_root, carrier_recipe_digest
        )
        if loaded is None:
            invalid()
            return None
        artifact, bundle = loaded
        observed_result_digest = _data7_fitted_result_digest(bundle)
        if (
            artifact.domain_digest != domain.content_digest
            or artifact.bundle_digest != payload.get("bundle_digest")
            or artifact.file_sha256 != payload.get("file_sha256")
            or observed_result_digest != fitted_result_digest
            or not _data7_fitted_core_matches_plan(bundle, plan, domain)
            or (reuse_validator is not None and not reuse_validator(bundle))
        ):
            invalid()
            return None
        return (
            _ReusableData7FitCore(
                fit_core_digest=fit_core_digest,
                fitted_result_digest=fitted_result_digest,
                carrier_recipe_digest=carrier_recipe_digest,
                domain_digest=domain.content_digest,
                bundle_digest=artifact.bundle_digest,
                file_sha256=artifact.file_sha256,
                path=artifact.path,
            ),
            bundle,
        )
    except Exception:
        invalid()
        return None


def _write_data7_fit_core_index(
    cache_root: Path,
    fit_core_digest: str,
    artifact: _ReusableData7Artifact,
    bundle: Data7PreparationBundle,
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
) -> _ReusableData7FitCore:
    if (
        artifact.domain_digest != domain.content_digest
        or artifact.bundle_digest != bundle.content_digest
        or not _data7_fitted_core_matches_plan(bundle, plan, domain)
    ):
        raise TrainingDataSerializationError(
            "DATA7 fitted-core publication carrier does not match its recipe."
        )
    local_result_digest = _data7_fitted_result_digest(bundle)
    existing = _load_reusable_data7_fit_core(
        cache_root,
        fit_core_digest,
        domain,
        plan,
        invalidate_invalid=True,
    )
    if existing is not None:
        winner = existing[0]
        if winner.fitted_result_digest != local_result_digest:
            raise TrainingDataSerializationError(
                "Divergent DATA7 fitted-core results share one execution recipe: "
                f"fit_core={fit_core_digest}; "
                f"winner_result={winner.fitted_result_digest}; "
                f"local_result={local_result_digest}; "
                f"winner_carrier={winner.carrier_recipe_digest}; "
                f"local_carrier={artifact.recipe_digest}."
            )
        return winner

    path = _fit_core_index_path(cache_root, fit_core_digest)
    _publish_json_create_once(
        path,
        {
            "schema": SHARED_DATA7_FIT_CORE_INDEX_SCHEMA,
            "fit_core_digest": fit_core_digest,
            "fitted_result_digest": local_result_digest,
            "carrier_recipe_digest": artifact.recipe_digest,
            "domain_digest": domain.content_digest,
            "bundle_digest": artifact.bundle_digest,
            "file_sha256": artifact.file_sha256,
        },
    )
    winner = _load_reusable_data7_fit_core(
        cache_root, fit_core_digest, domain, plan
    )
    if winner is None:
        raise TrainingDataSerializationError(
            "DATA7 fitted-core index publication did not yield a valid carrier."
        )
    winner_carrier = winner[0]
    if winner_carrier.fitted_result_digest != local_result_digest:
        raise TrainingDataSerializationError(
            "Concurrent DATA7 fitted-core publishers produced divergent results: "
            f"fit_core={fit_core_digest}; "
            f"winner_result={winner_carrier.fitted_result_digest}; "
            f"local_result={local_result_digest}; "
            f"winner_carrier={winner_carrier.carrier_recipe_digest}; "
            f"local_carrier={artifact.recipe_digest}."
        )
    return winner_carrier


def _write_reusable_data7_artifact(
    cache_root: Path,
    recipe_digest: str,
    domain: FeatureFitDomain,
    bundle: Data7PreparationBundle,
    plan: ProductionMaterializationPlan,
) -> _ReusableData7Artifact:
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_directory = cache_root / recipe_digest[:2] / recipe_digest
    cache_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = cache_directory.parent / (
        f".{recipe_digest}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    )
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging / "artifact.data7.zip"
        local_file_sha256 = write_data7_archive(bundle, artifact_path)
        local_bundle_digest = bundle.content_digest

        existing = _load_reusable_data7_artifact(
            cache_root, recipe_digest, domain, plan
        )
        if existing is not None:
            winner = existing[0]
            if (
                winner.bundle_digest != local_bundle_digest
                or winner.file_sha256 != local_file_sha256
            ):
                raise TrainingDataSerializationError(
                    "Divergent DATA7 results share one scientific recipe: "
                    f"recipe={recipe_digest}; "
                    f"winner_bundle={winner.bundle_digest}; "
                    f"local_bundle={local_bundle_digest}; "
                    f"winner_file_sha256={winner.file_sha256}; "
                    f"local_file_sha256={local_file_sha256}."
                )
            return winner

        _atomic_json(
            staging / "cache.json",
            {
                "schema": SHARED_DATA7_ARTIFACT_SCHEMA,
                "recipe_digest": recipe_digest,
                "domain_digest": domain.content_digest,
                "bundle_digest": local_bundle_digest,
                "artifact_name": artifact_path.name,
                "file_sha256": local_file_sha256,
            },
        )
        try:
            os.rename(staging, cache_directory)
        except OSError:
            # Another producer won. Authenticate the complete generation below
            # and require its deterministic scientific/archive result to match.
            shutil.rmtree(staging, ignore_errors=True)
        winner = _load_reusable_data7_artifact(
            cache_root, recipe_digest, domain, plan
        )
        if winner is None:
            raise TrainingDataSerializationError(
                "Concurrent DATA7 cache publication did not yield a valid generation."
            )
        winner_artifact = winner[0]
        if (
            winner_artifact.bundle_digest != local_bundle_digest
            or winner_artifact.file_sha256 != local_file_sha256
        ):
            raise TrainingDataSerializationError(
                "Concurrent DATA7 publishers produced divergent results: "
                f"recipe={recipe_digest}; "
                f"winner_bundle={winner_artifact.bundle_digest}; "
                f"local_bundle={local_bundle_digest}; "
                f"winner_file_sha256={winner_artifact.file_sha256}; "
                f"local_file_sha256={local_file_sha256}."
            )
        return winner_artifact
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _estimate_data7_domain_peak_bytes(
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
    data6_bundle: Any,
    frame_data_by_run: Mapping[str, Any],
) -> int:
    """Conservative incremental peak-RSS estimate for one DATA7 fit.

    DATA7 extracts one raw block at a time but retains transformed block outputs
    until the final combined matrix is assembled.  The estimate intentionally
    overstates unknown low-dimensional blocks so queue admission fails safe.
    """

    rows = max(1, len(domain.frame_uids))
    species = {
        int(number)
        for frame_data in frame_data_by_run.values()
        for number in np.asarray(frame_data.atomic_numbers, dtype=np.int32).reshape(-1)
    }
    species_count = max(1, len(species))
    structural_dimension = 0
    domain_set = frozenset(domain.frame_uids)
    for catalog in getattr(data6_bundle, "universal_structural_features", ()):
        table = catalog.frame_descriptor_table
        if domain_set.issubset(table.frame_uid_set):
            structural_dimension = max(structural_dimension, len(table.feature_names))

    descriptor_dimension = 0
    manifest = getattr(data6_bundle, "mace_descriptor_manifest", None)
    if manifest is not None:
        signature = getattr(manifest, "signature", None)
        if signature is not None:
            descriptor_dimension = int(signature.returned_per_atom_dimension)
        elif getattr(manifest, "records", ()):
            descriptor_dimension = max(int(item.shape[1]) for item in manifest.records)
    mace_summary_dimension = (
        2 * descriptor_dimension + species_count * (descriptor_dimension + 1)
        if descriptor_dimension > 0
        else 0
    )

    raw_physical_dimension = 20 + 3 * species_count
    difficulty_dimension = 5 + 3 * species_count
    profile_dimension = 0
    profile_extensions = tuple(
        getattr(data6_bundle, "profile_selection_features", ())
    )
    if not profile_extensions and getattr(
        data6_bundle, "lta_selection_features", None
    ) is not None:
        # The compatibility wrapper is deterministic and does not materialize
        # frame matrices; use it only to learn the actual extension width.
        from .profile_extensions import wrap_lta_selection_features

        profile_extensions = (
            wrap_lta_selection_features(
                data6_bundle.lta_selection_features,
                data4_bundle_digest=data6_bundle.data4_bundle_digest,
            ),
        )
    if profile_extensions and domain.frame_uids:
        sample_uid = domain.frame_uids[0]
        for extension in profile_extensions:
            try:
                names, _, _ = extension.frame_feature_vector(sample_uid)
            except (KeyError, TrainingDataInputError):
                continue
            profile_dimension += len(names)

    # Unknown future blocks fail conservatively without making today's
    # low-dimensional raw/difficulty blocks look thousands of columns wide.
    conservative_unknown_dimension = 4096
    input_dimensions: list[int] = []
    output_dimensions: list[int] = []
    for block in plan.feature_metric_policy.blocks:
        if block.name == "universal_structural" and structural_dimension > 0:
            width = structural_dimension
        elif block.name == "mace_summary" and mace_summary_dimension > 0:
            width = mace_summary_dimension
        elif block.name == "raw_physical":
            width = raw_physical_dimension
        elif block.name == "difficulty":
            width = difficulty_dimension
        elif block.name in {"profile_extensions", "lta_frame"} and profile_dimension > 0:
            width = profile_dimension
        else:
            width = conservative_unknown_dimension
        logical = width * (2 if block.include_missing_indicators else 1)
        output = (
            min(logical, int(block.pca_components))
            if block.pca_components is not None
            else logical
        )
        input_dimensions.append(width)
        output_dimensions.append(max(1, output))

    maximum_input = max(input_dimensions, default=conservative_unknown_dimension)
    retained_output = sum(output_dimensions)
    # Per raw value: input float64 + missing bool + standardized/work matrices
    # and conservative PCA/quantile scratch. Retained outputs are counted twice
    # to cover block outputs plus the final combined table during assembly.
    block_workspace = rows * maximum_input * 40
    retained_workspace = rows * retained_output * 16
    fixed_overhead = 256 * 1024**2
    estimate = int((block_workspace + retained_workspace + fixed_overhead) * 1.20)
    return max(64 * 1024**2, estimate)


def _estimate_data7_reuse_peak_bytes(
    domain: FeatureFitDomain,
    plan: ProductionMaterializationPlan,
    carrier: _ReusableData7FitCore,
) -> int:
    """Conservative peak-RSS estimate for selection-only fitted-core reuse."""

    try:
        archive_bytes = max(0, Path(carrier.path).stat().st_size)
    except OSError:
        archive_bytes = 0
    rows = max(1, len(domain.frame_uids))
    selected_rows = max(
        1,
        int(plan.selection_size or 0),
        max((len(uids) for _, uids in plan.prescribed_training_domain_prefixes), default=0),
    )
    # Archive inflation/load, selection bookkeeping, coverage realization, and
    # deterministic archive output.  Keep a substantial floor while remaining
    # materially below the feature-fit workspace for normal domains.
    estimate = (
        archive_bytes * 8
        + rows * 4096
        + selected_rows * 2048
        + 32 * 1024**2
    )
    return max(64 * 1024**2, int(estimate * 1.20))



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
    shared_data7_fit_cores: MutableMapping[str, _ReusableData7FitCore] | None = None,
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
        if shared_data7_fit_cores is not None:
            fit_core_digest = _data7_fit_core_digest(plan, domain)
            _register_reusable_data7_fit_core(
                shared_data7_fit_cores,
                _ReusableData7FitCore(
                    fit_core_digest=fit_core_digest,
                    fitted_result_digest=_data7_fitted_result_digest(bundle),
                    carrier_recipe_digest=recipe_digest,
                    domain_digest=domain.content_digest,
                    bundle_digest=bundle.content_digest,
                    file_sha256=item.file_sha256,
                    path=str(source),
                ),
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


def _load_valid_data8_record(
    record: ProductionData8ArtifactRecord,
    root: Path,
    plan: ProductionMaterializationPlan,
) -> Data8PreparationBundle | None:
    directory = root / record.relative_directory
    bundle_path = root / record.bundle_relative_path
    if not directory.is_dir() or not bundle_path.is_file():
        return None
    entries = _tree_entries(directory)
    if entries != record.tree_entries or _tree_digest(entries) != record.tree_digest:
        return None
    try:
        bundle = Data8PreparationBundle.from_dict(json.loads(bundle_path.read_text(encoding="utf-8")))
    except Exception:
        return None
    if (
        bundle.content_digest != record.bundle_digest
        or bundle.data5_bundle_digest != plan.data5_bundle_digest
        or not _replay_semantically_matches(plan.replay_plan, bundle.replay_plan)
    ):
        return None
    return bundle


def _data8_record_valid(record: ProductionData8ArtifactRecord, root: Path, plan: ProductionMaterializationPlan) -> bool:
    return _load_valid_data8_record(record, root, plan) is not None


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
    shared_data7_fit_cores: MutableMapping[str, _ReusableData7FitCore] | None = None,
    shared_data8_fixed_file_cache_directory: str | Path | None = None,
    shared_frame_array_index_cache: MutableMapping[str, Mapping[str, tuple[Any, Any, int]]] | None = None,
    execution_resources: SystemResourceSnapshot | None = None,
    minimum_free_disk_bytes: int = 0,
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
    shared_fit_memory = shared_data7_fit_cores
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
    progress_lock = Lock()
    resources = (
        detect_system_resources(device="cpu")
        if execution_resources is None
        else execution_resources
    )

    def exact_fit_core_bundle_matches(
        bundle: Data7PreparationBundle, domain: FeatureFitDomain
    ) -> bool:
        try:
            validate_data7_fitted_component_reuse(
                bundle,
                source_catalog,
                frame_catalog,
                data4_bundle,
                data5_bundle,
                data6_bundle,
                domain,
                feature_metric_policy=plan.feature_metric_policy,
                atomic_reference_policy=plan.atomic_reference_policy,
                objective_policy=plan.objective_policy,
                configuration_weight_policy=plan.configuration_weight_policy,
                checkpoint_metric_policy=plan.checkpoint_metric_policy,
                foundation_prediction_energy_by_frame=(
                    prediction_energy
                    if plan.atomic_reference_policy.fit_mode
                    is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
                    else None
                ),
                foundation_reference_energies=(
                    dict(plan.foundation_reference_energies) or None
                    if plan.atomic_reference_policy.fit_mode
                    is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
                    else None
                ),
                foundation_checkpoint_digest=None,
                foundation_identity_digest=(
                    plan.foundation_checkpoint.canonical_content_digest
                    if plan.atomic_reference_policy.fit_mode
                    is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
                    else None
                ),
            )
        except TrainingDataInputError:
            return False
        return True

    def in_memory_fit_core_matches(
        carrier: _ReusableData7FitCore, domain: FeatureFitDomain
    ) -> bool:
        try:
            bundle = _read_data7_artifact(
                Path(carrier.path), expected_sha256=carrier.file_sha256
            )
        except Exception:
            return False
        return (
            carrier.domain_digest == domain.content_digest
            and carrier.bundle_digest == bundle.content_digest
            and carrier.fitted_result_digest == _data7_fitted_result_digest(bundle)
            and _data7_fitted_core_matches_plan(bundle, plan, domain)
            and exact_fit_core_bundle_matches(bundle, domain)
        )

    def emit_progress(message: str) -> None:
        if progress_callback is None:
            return
        with progress_lock:
            progress_callback(message)

    def build_receipt(
        domain: FeatureFitDomain,
        recipe_digest: str,
        fit_core_digest: str,
        fit_core_carrier: _ReusableData7FitCore | None,
    ) -> _Data7ArtifactReceipt:
        started = time.monotonic()
        label = f"DATA7 kind={domain.kind.value} fold={domain.fold_index}"

        def domain_progress(message: str) -> None:
            emit_progress(f"{label}: {message}")

        reuse_bundle: Data7PreparationBundle | None = None
        if fit_core_carrier is not None:
            try:
                candidate = _read_data7_artifact(
                    Path(fit_core_carrier.path),
                    expected_sha256=fit_core_carrier.file_sha256,
                )
                if (
                    fit_core_carrier.bundle_digest == candidate.content_digest
                    and fit_core_carrier.fitted_result_digest
                    == _data7_fitted_result_digest(candidate)
                    and _data7_fitted_core_matches_plan(candidate, plan, domain)
                    and exact_fit_core_bundle_matches(candidate, domain)
                ):
                    reuse_bundle = candidate
                    domain_progress(
                        "status=reusing; phase=domain-fitted-core; "
                        f"carrier={fit_core_carrier.bundle_digest[:12]}"
                    )
            except Exception:
                reuse_bundle = None
        if fit_core_carrier is not None and reuse_bundle is None:
            if shared_fit_memory is not None:
                current = shared_fit_memory.get(fit_core_digest)
                if current == fit_core_carrier:
                    shared_fit_memory.pop(fit_core_digest, None)
            domain_progress(
                "status=invalidated; phase=domain-fitted-core; action=fresh-fit"
            )
        domain_progress(
            "status=building; phase="
            + ("selection-realization" if reuse_bundle is not None else "domain-fit")
        )
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
            mace_summary_cache={},
            composition_count_cache={},
            canonical_domain_digests=canonical_domain_digests,
            frame_record_by_uid=frame_record_by_uid,
            event_anchor_frame_uids=event_anchor_frame_uids,
            protected_event_frame_uids=protected_event_frame_uids,
            prescribed_selection_frame_uids=(
                None
                if plan.selection_authority_role == "standard"
                else dict(plan.prescribed_training_domain_prefixes).get(domain.content_digest)
            ),
            prescribed_selection_role=(
                None if plan.selection_authority_role == "standard" else plan.selection_authority_role
            ),
            reuse_fitted_components_from=reuse_bundle,
            progress_callback=domain_progress,
        )
        if not _data7_bundle_matches_plan(bundle, plan, domain):
            raise TrainingDataSerializationError(
                "New DATA7 artifact does not match its scientific recipe."
            )
        fit_core_enabled = (
            len(domain.frame_uids) >= DATA7_FIT_CORE_REUSE_MIN_DOMAIN_FRAMES
        )
        if shared_cache_root is not None:
            artifact = _write_reusable_data7_artifact(
                shared_cache_root, recipe_digest, domain, bundle, plan
            )
            fit_core_artifact = (
                _write_data7_fit_core_index(
                    shared_cache_root, fit_core_digest, artifact, bundle, domain, plan
                )
                if fit_core_enabled
                else None
            )
            path = artifact.path
            bundle_digest = artifact.bundle_digest
            file_sha256 = artifact.file_sha256
            source = "built-shared-cache"
        else:
            relative = Path("data7") / f"{domain.content_digest}.data7.zip"
            path_obj = root / relative
            file_sha256 = write_data7_archive(bundle, path_obj)
            path = str(path_obj)
            bundle_digest = bundle.content_digest
            source = "built-production"
            fit_core_artifact = (
                _ReusableData7FitCore(
                    fit_core_digest=fit_core_digest,
                    fitted_result_digest=_data7_fitted_result_digest(bundle),
                    carrier_recipe_digest=recipe_digest,
                    domain_digest=domain.content_digest,
                    bundle_digest=bundle.content_digest,
                    file_sha256=file_sha256,
                    path=path,
                )
                if fit_core_enabled
                else None
            )
        if shared_fit_memory is not None and fit_core_artifact is not None:
            _register_reusable_data7_fit_core(shared_fit_memory, fit_core_artifact)
        if reuse_bundle is not None:
            source = "built-from-fit-core"
        wall = max(0.0, time.monotonic() - started)
        domain_progress(
            f"status=complete; phase=domain-fit; elapsed_seconds={wall:.3f}"
        )
        return _Data7ArtifactReceipt(
            recipe_digest=recipe_digest,
            domain_digest=domain.content_digest,
            bundle_digest=bundle_digest,
            file_sha256=file_sha256,
            path=path,
            source=source,
            wall_seconds=wall,
        )

    try:
        missing_domains = [
            domain for domain in plan.domains if domain.content_digest not in records
        ]
        if active.max_new_data7_domains is not None:
            missing_domains = missing_domains[: active.max_new_data7_domains]

        immediate: list[tuple[FeatureFitDomain, _Data7ArtifactReceipt]] = []
        builds: list[
            tuple[
                int,
                FeatureFitDomain,
                str,
                str,
                _ReusableData7FitCore | None,
                int,
            ]
        ] = []
        for canonical_index, domain in enumerate(missing_domains):
            recipe_digest = _data7_recipe_digest(plan, domain)
            legacy_recipe_digest = _data7_recipe_digest_v1(plan, domain)
            fit_core_digest = _data7_fit_core_digest(plan, domain)
            fit_core_enabled = (
                len(domain.frame_uids) >= DATA7_FIT_CORE_REUSE_MIN_DOMAIN_FRAMES
            )
            artifact = None if shared_memory is None else shared_memory.get(recipe_digest)
            if artifact is not None and Path(artifact.path).is_file():
                immediate.append((
                    domain,
                    _Data7ArtifactReceipt(
                        recipe_digest=recipe_digest,
                        domain_digest=domain.content_digest,
                        bundle_digest=artifact.bundle_digest,
                        file_sha256=artifact.file_sha256,
                        path=artifact.path,
                        source="reuse-in-process",
                    ),
                ))
                continue
            if shared_cache_root is not None:
                restored_shared = _load_reusable_data7_artifact(
                    shared_cache_root, recipe_digest, domain, plan
                )
                if restored_shared is None:
                    restored_shared = _load_reusable_data7_artifact(
                        shared_cache_root, legacy_recipe_digest, domain, plan
                    )
                if restored_shared is not None:
                    artifact, restored_bundle = restored_shared
                    if fit_core_enabled:
                        fit_core_artifact = _write_data7_fit_core_index(
                            shared_cache_root,
                            fit_core_digest,
                            artifact,
                            restored_bundle,
                            domain,
                            plan,
                        )
                        if shared_fit_memory is not None:
                            _register_reusable_data7_fit_core(
                                shared_fit_memory, fit_core_artifact
                            )
                    del restored_bundle
                    if shared_memory is not None:
                        shared_memory[recipe_digest] = artifact
                    immediate.append((
                        domain,
                        _Data7ArtifactReceipt(
                            recipe_digest=recipe_digest,
                            domain_digest=domain.content_digest,
                            bundle_digest=artifact.bundle_digest,
                            file_sha256=artifact.file_sha256,
                            path=artifact.path,
                            source="reuse-verified",
                        ),
                    ))
                    continue
            fit_core_carrier = (
                None
                if shared_fit_memory is None or not fit_core_enabled
                else shared_fit_memory.get(fit_core_digest)
            )
            if fit_core_carrier is not None and not in_memory_fit_core_matches(
                fit_core_carrier, domain
            ):
                if shared_fit_memory is not None:
                    current = shared_fit_memory.get(fit_core_digest)
                    if current == fit_core_carrier:
                        shared_fit_memory.pop(fit_core_digest, None)
                fit_core_carrier = None
            if fit_core_carrier is None and shared_cache_root is not None:
                restored_core = (
                    _load_reusable_data7_fit_core(
                        shared_cache_root,
                        fit_core_digest,
                        domain,
                        plan,
                        reuse_validator=lambda bundle, domain=domain: exact_fit_core_bundle_matches(
                            bundle, domain
                        ),
                        invalidate_invalid=True,
                    )
                    if fit_core_enabled
                    else None
                )
                if restored_core is not None:
                    fit_core_carrier, restored_core_bundle = restored_core
                    del restored_core_bundle
                    if shared_fit_memory is not None:
                        _register_reusable_data7_fit_core(
                            shared_fit_memory, fit_core_carrier
                        )
            estimate = (
                _estimate_data7_reuse_peak_bytes(domain, plan, fit_core_carrier)
                if fit_core_carrier is not None
                else _estimate_data7_domain_peak_bytes(
                    domain, plan, data6_bundle, frame_data_by_run
                )
            )
            builds.append((
                canonical_index,
                domain,
                recipe_digest,
                fit_core_digest,
                fit_core_carrier,
                estimate,
            ))

        if builds and frame_array_index is None:
            emit_progress(
                "status=phase; phase=building-shared-frame-array-index; consumer=DATA7"
            )
            from ._frame_access import build_frame_array_index

            frame_array_index = build_frame_array_index(
                frame_catalog, frame_data_by_run
            )
            if shared_frame_array_index_cache is not None:
                shared_frame_array_index_cache[frame_catalog.content_digest] = frame_array_index

        selected_by_digest = {domain.content_digest: domain for domain in missing_domains}

        def commit_receipt(domain_digest: str, receipt: _Data7ArtifactReceipt) -> None:
            nonlocal new_domains
            domain = selected_by_digest[domain_digest]
            relative = Path("data7") / f"{domain.content_digest}.data7.zip"
            destination = root / relative
            source_path = Path(receipt.path)
            if source_path.resolve() != destination.resolve():
                _atomic_link_or_copy(source_path, destination)
            records[domain.content_digest] = ProductionData7ArtifactRecord(
                domain_digest=domain.content_digest,
                relative_path=relative.as_posix(),
                bundle_digest=receipt.bundle_digest,
                file_sha256=receipt.file_sha256,
            )
            if shared_memory is not None:
                shared_memory[receipt.recipe_digest] = _ReusableData7Artifact(
                    recipe_digest=receipt.recipe_digest,
                    domain_digest=receipt.domain_digest,
                    bundle_digest=receipt.bundle_digest,
                    file_sha256=receipt.file_sha256,
                    path=str(source_path),
                )
            new_domains += 1
            checkpoint = ProductionMaterializationCheckpoint(
                plan=plan,
                data7_artifacts=tuple(records.values()),
                status=ProductionMaterializationStatus.INCOMPLETE,
            )
            _atomic_json(checkpoint_path, checkpoint.to_dict())
            emit_progress(
                f"DATA7 domain; progress={format_progress_fraction(new_domains, len(plan.domains))}; "
                f"status=committed; kind={domain.kind.value} fold={domain.fold_index}; "
                f"source={receipt.source}; elapsed_seconds={receipt.wall_seconds:.3f}"
            )

        reducer = DeterministicOrderedReducer(
            [domain.content_digest for domain in missing_domains],
            commit=commit_receipt,
        )
        for domain, receipt in immediate:
            reducer.push(domain.content_digest, receipt)

        if builds:
            workers = max(1, min(len(builds), int(resources.cpu_threads_budget)))
            scope = build_stage_resource_scope(
                resources,
                stage_name="DATA7-domain-materialization",
                python_workers=workers,
                structural_workers=1,
                tree_workers=1,
                blas_threads=1,
                native_openmp_threads=1,
                pytorch_cpu_workers=1,
                gpu_jobs=0,
                ram_budget_bytes=resources.ram_budget_bytes,
            )
            emit_progress(
                f"status=phase; phase=DATA7-parallel-domains; workers={workers}; "
                f"cpu_budget={resources.cpu_threads_budget}; "
                f"ram_budget_bytes={scope.ram_budget_bytes}"
            )

            def queue_telemetry(snapshot: Any) -> None:
                emit_progress(
                    "DATA7 queue; "
                    f"busy={snapshot.busy_workers}/{snapshot.allocated_workers}; "
                    f"finished={snapshot.finished_tasks}/{snapshot.submitted_tasks}; "
                    f"accounted_ram_bytes={snapshot.accounted_memory_bytes}; "
                    f"ram_budget_bytes={snapshot.memory_budget_bytes}; "
                    f"memory_backpressure={snapshot.memory_backpressure_events}"
                )

            with DeterministicWorkQueue(
                scope,
                max_ready_tasks=max(1, len(builds)),
                max_inflight_tasks=workers,
                max_completed_tasks=max(1, len(builds)),
                heartbeat_interval_seconds=15.0,
                telemetry_callback=queue_telemetry,
                thread_name_prefix="mdstats-data7",
            ) as queue:
                for (
                    canonical_index,
                    domain,
                    recipe_digest,
                    fit_core_digest,
                    fit_core_carrier,
                    estimate,
                ) in builds:
                    queue.submit(
                        task_id=domain.content_digest,
                        canonical_order=(canonical_index,),
                        function=build_receipt,
                        args=(
                            domain,
                            recipe_digest,
                            fit_core_digest,
                            fit_core_carrier,
                        ),
                        task_kind="DATA7-domain",
                        estimated_memory_bytes=estimate,
                        locality_key=domain.label_domain_id,
                    )
                while not reducer.complete:
                    queue.wait_for_completion()
                    for completion in queue.drain_completed():
                        reducer.push(completion.task_id, completion.value)

        all_data7 = len(records) == len(plan.domains)
        if all_data7 and active.materialize_data8 and data8_record is None:
            # Descriptor summaries are a cross-domain extraction cache only;
            # DATA8 consumes the compact DATA7 bundles, not these raw summary
            # arrays. Release them before loading/assembling all DATA7 domains
            # together to avoid avoidable peak memory and swap-induced stalls.
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
                target_size_evaluation_frame_uids=(
                    None
                    if plan.selection_authority_role != "target_size_candidate"
                    else dict(plan.prescribed_target_size_evaluation_frames).get(
                        bundles[0].domain.label_domain_id
                    )
                ),
                require_foundation_residual_e0=plan.require_foundation_residual_e0,
                cross_validation_plans=(
                    None
                    if plan.plan_schema == PRODUCTION_MATERIALIZATION_PLAN_V2_SCHEMA
                    else plan.cross_validation_plans
                ),
                frame_array_index=frame_array_index,
                shared_fixed_file_cache_directory=shared_data8_fixed_file_cache_directory,
                execution_resources=resources,
                minimum_free_disk_bytes=max(0, int(minimum_free_disk_bytes)),
                progress_callback=progress_callback,
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
