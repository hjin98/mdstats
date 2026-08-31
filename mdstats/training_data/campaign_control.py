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

    return inventory_checkpoint_files(
        root_directory,
        run_plan_digest=run_plan.content_digest,
        run_id=run_plan.run_id,
        pattern=pattern,
        epoch_pattern=epoch_pattern,
    )


def inventory_checkpoint_files(
    root_directory: str | Path,
    *,
    run_plan_digest: str,
    run_id: str,
    pattern: str = "*.pt",
    epoch_pattern: str = r"(?:epoch[-_]?)(\d+)",
) -> CandidateCheckpointCatalog:
    """Inventory checkpoint bytes for any run identity.

    Checkpoint inventory is a property of the bytes on disk and the owning run,
    not of any particular run-plan schema, so this owner takes the run identity
    directly.  That lets target-size screening and post-selection runs share one
    inventory implementation instead of maintaining two.
    """

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
                run_plan_digest=run_plan_digest,
                candidate_id=f"{run_id}:epoch-{epoch}",
                epoch=epoch,
                relative_path=relative.as_posix(),
                sha256=sha,
                size_bytes=path.stat().st_size,
            )
        )
    return CandidateCheckpointCatalog(
        run_plan_digest=run_plan_digest,
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
