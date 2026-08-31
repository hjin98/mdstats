from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping, Protocol, Sequence


CAMPAIGN_ARTIFACT_OWNERSHIP_CATALOG_SCHEMA = "mdstats.mlff-campaign-artifact-ownership-catalog.v1"
CAMPAIGN_STORAGE_REPORT_SCHEMA = "mdstats.mlff-campaign-storage-report.v1"


class RetentionFence(Protocol):
    """Lifecycle-owned reduction of deletion authority.

    A retention fence answers whether one campaign-owned path is still needed
    by an active, restartable, or not-yet-classified lifecycle.  It is a
    reduction only: :class:`CampaignOwnershipBoundary` consults it after its own
    ownership and containment checks, so a fence can never widen deletion
    authority.
    """

    def protects(self, path: Path) -> tuple[bool, str]:
        ...


class ArtifactOwnershipClass(str, Enum):
    CAMPAIGN_OWNED = "campaign_owned"
    EXTERNAL_USER_INPUT = "external_user_input"
    CAMPAIGN_OWNED_SYMLINK = "campaign_owned_symlink"
    AMBIGUOUS = "ambiguous"


class ArtifactRetentionClass(str, Enum):
    PROTECTED_INPUT = "protected_input"
    PROTECTED_PRODUCTION = "protected_production"
    PROTECTED_DIAGNOSTIC = "protected_diagnostic"
    RESTART_CRITICAL = "restart_critical"
    EVALUATION_CAPSULE = "evaluation_capsule"
    SCIENTIFIC_CACHE = "scientific_cache"
    RECONSTRUCTABLE_CACHE = "reconstructable_cache"
    INTERMEDIATE = "intermediate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProtectedInputPath:
    key: str
    path: str
    real_path: str
    exists: bool
    kind: str

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "path": self.path,
            "real_path": self.real_path,
            "exists": self.exists,
            "kind": self.kind,
            "ownership": ArtifactOwnershipClass.EXTERNAL_USER_INPUT.value,
            "retention_class": ArtifactRetentionClass.PROTECTED_INPUT.value,
            "automatic_reclamation_eligibility": "prohibited",
            "manual_reclamation_eligibility": "prohibited",
            "capability_lost_if_deleted": ["source_or_reference_input_unavailable"],
        }


@dataclass(frozen=True, slots=True)
class StorageFamilyRecord:
    """Read-only advisory storage family accounting record.

    Advisory accounting only: this classification never grants deletion
    authority. Physical deletion requires current owner authorization,
    containment, and retention/liveness validation.
    """
    family: str
    ownership: str
    retention_class: str
    logical_bytes: int
    allocated_physical_bytes: int
    unique_inode_bytes: int
    file_count: int
    directory_count: int
    symlink_count: int
    automatic_reclamation_eligibility: str
    manual_reclamation_eligibility: str
    capability_lost_if_deleted: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "ownership": self.ownership,
            "retention_class": self.retention_class,
            "logical_bytes": self.logical_bytes,
            "allocated_physical_bytes": self.allocated_physical_bytes,
            "unique_inode_bytes": self.unique_inode_bytes,
            "file_count": self.file_count,
            "directory_count": self.directory_count,
            "symlink_count": self.symlink_count,
            "automatic_reclamation_eligibility": self.automatic_reclamation_eligibility,
            "manual_reclamation_eligibility": self.manual_reclamation_eligibility,
            "capability_lost_if_deleted": list(self.capability_lost_if_deleted),
        }


@dataclass(frozen=True, slots=True)
class LargestArtifactRecord:
    path: str
    kind: str
    family: str
    ownership: str
    retention_class: str
    logical_bytes: int
    allocated_physical_bytes: int
    hardlink_count: int
    symlink: bool
    real_path: str
    real_path_contained: bool
    symlink_escape: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "kind": self.kind,
            "family": self.family,
            "ownership": self.ownership,
            "retention_class": self.retention_class,
            "logical_bytes": self.logical_bytes,
            "allocated_physical_bytes": self.allocated_physical_bytes,
            "hardlink_count": self.hardlink_count,
            "symlink": self.symlink,
            "real_path": self.real_path,
            "real_path_contained": self.real_path_contained,
            "symlink_escape": self.symlink_escape,
        }


@dataclass(frozen=True, slots=True)
class CampaignArtifactOwnershipCatalog:
    workspace: str
    workspace_real_path: str
    protected_inputs: tuple[ProtectedInputPath, ...]
    symlink_escapes: tuple[str, ...]
    ambiguous_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CAMPAIGN_ARTIFACT_OWNERSHIP_CATALOG_SCHEMA,
            "workspace": self.workspace,
            "workspace_real_path": self.workspace_real_path,
            "protected_inputs": [item.to_dict() for item in self.protected_inputs],
            "symlink_escapes": list(self.symlink_escapes),
            "ambiguous_paths": list(self.ambiguous_paths),
        }


@dataclass(frozen=True, slots=True)
class CampaignStorageReport:
    ownership_catalog: CampaignArtifactOwnershipCatalog
    logical_bytes: int
    allocated_physical_bytes: int
    unique_inode_bytes: int
    file_count: int
    directory_count: int
    symlink_count: int
    families: tuple[StorageFamilyRecord, ...]
    largest_artifacts: tuple[LargestArtifactRecord, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": CAMPAIGN_STORAGE_REPORT_SCHEMA,
            "read_only_gate": "advisory_read_only",
            "destructive_actions_performed": False,
            "ownership_catalog": self.ownership_catalog.to_dict(),
            "totals": {
                "logical_bytes": self.logical_bytes,
                "allocated_physical_bytes": self.allocated_physical_bytes,
                "allocated_physical_bytes_source": "st_blocks_512_when_available_else_st_size",
                "unique_inode_bytes": self.unique_inode_bytes,
                "file_count": self.file_count,
                "directory_count": self.directory_count,
                "symlink_count": self.symlink_count,
            },
            "families": [item.to_dict() for item in self.families],
            "largest_artifacts": [item.to_dict() for item in self.largest_artifacts],
        }


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _resolved(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return Path(os.path.abspath(os.fspath(path)))


def _allocated_bytes(stat_result: os.stat_result) -> int:
    blocks = getattr(stat_result, "st_blocks", None)
    if blocks is None:
        return int(stat_result.st_size)
    return int(blocks) * 512


def _input_kind(path: Path) -> str:
    try:
        if path.is_dir():
            return "directory"
        if path.is_file():
            return "file"
        if path.is_symlink():
            return "symlink"
    except OSError:
        pass
    return "missing_or_other"


def configured_protected_inputs(
    cfg: Mapping[str, object],
    *,
    config_dir: Path,
    config_path: Path | None = None,
) -> tuple[ProtectedInputPath, ...]:
    section = cfg.get("paths", {})
    # These keys are user/reference inputs.  A future campaign-owned content store
    # must be represented separately and must never inherit authority from [paths].
    keys = (
        "training_root",
        "foundation_model",
        "replay_set",
        "replay_train",
        "replay_monitor",
        "replay_true_labels",
    )
    result: list[ProtectedInputPath] = []
    if config_path is not None:
        config_absolute = Path(os.path.abspath(os.fspath(config_path)))
        result.append(
            ProtectedInputPath(
                key="campaign_config",
                path=str(config_absolute),
                real_path=str(_resolved(config_absolute)),
                exists=config_absolute.exists() or config_absolute.is_symlink(),
                kind=_input_kind(config_absolute),
            )
        )
    if not isinstance(section, Mapping):
        return tuple(result)
    for key in keys:
        value = section.get(key)
        if value in (None, ""):
            continue
        raw = Path(str(value)).expanduser()
        path = raw if raw.is_absolute() else config_dir / raw
        absolute = Path(os.path.abspath(os.fspath(path)))
        real = _resolved(absolute)
        result.append(
            ProtectedInputPath(
                key=key,
                path=str(absolute),
                real_path=str(real),
                exists=absolute.exists() or absolute.is_symlink(),
                kind=_input_kind(absolute),
            )
        )
    return tuple(result)


class CampaignOwnershipBoundary:
    """Deletion-authority boundary shared by STOR1 and existing cleanup.

    STOR1 itself is read-only.  Existing cleanup code may use this object only to
    *reduce* its prior authority: any ambiguous path, real-path escape, or overlap
    with a configured user/reference input is denied.
    """

    def __init__(
        self,
        workspace: Path,
        *,
        protected_inputs: Sequence[ProtectedInputPath] = (),
        retention_fence: "RetentionFence | None" = None,
    ) -> None:
        self.workspace = Path(os.path.abspath(os.fspath(workspace)))
        self.workspace_real = _resolved(self.workspace)
        self.protected_inputs = tuple(protected_inputs)
        self._protected_real = tuple(Path(item.real_path) for item in protected_inputs)
        self._protected_lexical = tuple(Path(item.path) for item in protected_inputs)
        self.retention_fence = retention_fence

    def lexical_inside_workspace(self, path: Path) -> bool:
        absolute = Path(os.path.abspath(os.fspath(path)))
        return _is_within(absolute, self.workspace)

    def real_inside_workspace(self, path: Path) -> bool:
        return _is_within(_resolved(path), self.workspace_real)

    def protected_input_key_for(self, path: Path, *, resolve: bool = True) -> str | None:
        candidate = _resolved(path) if resolve else Path(os.path.abspath(os.fspath(path)))
        for item in self.protected_inputs:
            input_path = Path(item.real_path if resolve else item.path)
            if _is_within(candidate, input_path):
                return item.key
        return None

    def overlaps_protected_input(self, path: Path, *, resolve: bool = True) -> bool:
        candidate = _resolved(path) if resolve else Path(os.path.abspath(os.fspath(path)))
        protected = self._protected_real if resolve else self._protected_lexical
        for input_path in protected:
            if _is_within(candidate, input_path) or _is_within(input_path, candidate):
                return True
        return False

    def traversal_authorization(self, path: Path) -> tuple[bool, str]:
        """Authorize recursive inspection/traversal of a campaign-owned tree.

        This is intentionally stricter than :meth:`destructive_authorization`: a
        symlink object may be safe to unlink while its target is never safe to
        traverse unless that resolved target is itself contained and unprotected.
        """

        absolute = Path(os.path.abspath(os.fspath(path)))
        if not self.lexical_inside_workspace(absolute):
            return False, "path is outside the campaign workspace"
        if self.overlaps_protected_input(absolute, resolve=False):
            return False, "path overlaps a configured user/reference input"
        resolved = _resolved(absolute)
        if not _is_within(resolved, self.workspace_real):
            return False, "resolved traversal root escapes the campaign workspace"
        if self.overlaps_protected_input(resolved, resolve=True):
            return False, "resolved traversal root overlaps a configured user/reference input"
        return True, "campaign-owned contained traversal root"

    def destructive_authorization(self, path: Path) -> tuple[bool, str]:
        absolute = Path(os.path.abspath(os.fspath(path)))
        if not self.lexical_inside_workspace(absolute):
            return False, "path is outside the campaign workspace"
        if self.overlaps_protected_input(absolute, resolve=False):
            return False, "path overlaps a configured user/reference input"
        if absolute.is_symlink():
            # Unlinking the link object itself is safe even if its target is external,
            # provided the link's parent is genuinely campaign-contained.
            parent_real = _resolved(absolute.parent)
            if not _is_within(parent_real, self.workspace_real):
                return False, "symlink parent escapes the campaign workspace"
            denied, detail = self._retention_denial(absolute)
            if denied:
                return False, detail
            return True, "campaign-owned symlink object"
        resolved = _resolved(absolute)
        if not _is_within(resolved, self.workspace_real):
            return False, "real path escapes the campaign workspace"
        if self.overlaps_protected_input(resolved, resolve=True):
            return False, "real path overlaps a configured user/reference input"
        denied, detail = self._retention_denial(absolute)
        if denied:
            return False, detail
        return True, "campaign-owned contained path"

    def _retention_denial(self, absolute: Path) -> tuple[bool, str]:
        """Consult a lifecycle retention fence, which may only reduce authority.

        A fence answers whether a campaign-owned path is still required by an
        active, restartable, or not-yet-classified lifecycle.  It can never
        grant deletion authority: it is consulted only after every ownership,
        containment, and protected-input check has already passed.
        """

        fence = self.retention_fence
        if fence is None:
            return False, ""
        protected, reason = fence.protects(absolute)
        if not protected:
            return False, ""
        return True, (reason or "path is retained by an active lifecycle retention fence")


_TARGET_SIZE_RESTART_CAPABILITIES = (
    "target_size_screen_restart",
    "deterministic_scientific_replay",
)


def _target_size_family(
    parts: tuple[str, ...],
) -> tuple[str, ArtifactRetentionClass, str, str, tuple[str, ...]]:
    """Classify promoted target-size execution evidence.

    This evidence is the scientific execution authority for the current
    target-size generation: heads, batches, and completions define the replay
    graph, and the checkpoint/materialization/evaluation ancestry is what makes
    that graph re-verifiable.  Reclamation of any of it is decided by the
    retention fence plus reconciliation, never by a storage tier, so nothing
    here is automatically or manually eligible.
    """

    # parts[0] == ".mdstats", parts[1] == "target-size", parts[2] == generation
    tail = parts[3:]
    section = tail[0] if tail else ""
    if section == "bulk":
        bulk = tail[1] if len(tail) > 1 else ""
        if bulk == "snapshots":
            return (
                "target_size_boundary_snapshots",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                ("exact_boundary_continuation", "exact_checkpoint_reevaluation"),
            )
        if bulk == "train2":
            return (
                "target_size_training_runtime",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                ("exact_completed_epoch_continuation",),
            )
        if bulk == "materializations":
            return (
                "target_size_candidate_materializations",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                ("exact_candidate_membership", "candidate_reexecution"),
            )
        if bulk == "evaluations":
            return (
                "target_size_evaluation_evidence",
                ArtifactRetentionClass.EVALUATION_CAPSULE,
                "prohibited",
                "prohibited",
                ("exact_m_ladder_reevaluation",),
            )
        return (
            "target_size_execution_bulk",
            ArtifactRetentionClass.RESTART_CRITICAL,
            "prohibited",
            "prohibited",
            _TARGET_SIZE_RESTART_CAPABILITIES,
        )
    if section in {"evaluation_artifacts", "roles", "predictions", "metrics"}:
        return (
            "target_size_evaluation_evidence",
            ArtifactRetentionClass.EVALUATION_CAPSULE,
            "prohibited",
            "prohibited",
            ("exact_m_ladder_reevaluation", "metric_reanalysis"),
        )
    if section == "failures":
        return (
            "target_size_failure_evidence",
            ArtifactRetentionClass.PROTECTED_DIAGNOSTIC,
            "prohibited",
            "prohibited",
            ("scientific_failure_provenance",),
        )
    if section == "snapshots":
        return (
            "target_size_boundary_snapshots",
            ArtifactRetentionClass.RESTART_CRITICAL,
            "prohibited",
            "prohibited",
            ("exact_boundary_continuation", "exact_checkpoint_reevaluation"),
        )
    if section == "materializations":
        return (
            "target_size_candidate_materializations",
            ArtifactRetentionClass.RESTART_CRITICAL,
            "prohibited",
            "prohibited",
            ("exact_candidate_membership", "candidate_reexecution"),
        )
    return (
        "target_size_execution_graph",
        ArtifactRetentionClass.RESTART_CRITICAL,
        "prohibited",
        "prohibited",
        _TARGET_SIZE_RESTART_CAPABILITIES,
    )


def _post_selection_family(
    parts: tuple[str, ...],
) -> tuple[str, ArtifactRetentionClass, str, str, tuple[str, ...]]:
    """Classify post-selection cross-validation and final-production evidence.

    This is the scientific authority for whether the frozen training method was
    cross-validation accepted and what the fresh production runs actually did.
    Its immutable object store carries the plans and acceptance records that a
    later reader needs to prove production was authorized, and its run trees
    carry the exact materialization and checkpoint ancestry that makes those
    claims re-verifiable.  Reclaiming any of it is a scientific decision about a
    campaign generation, never a storage tier's, so nothing here is
    automatically or manually eligible.
    """

    # parts[0] == ".mdstats", parts[1] == "post-selection", parts[2] == generation
    tail = parts[3:]
    section = tail[0] if tail else ""
    if section == "objects":
        return (
            "post_selection_evidence_graph",
            ArtifactRetentionClass.RESTART_CRITICAL,
            "prohibited",
            "prohibited",
            (
                "cross_validation_authorization",
                "final_production_authorization",
                "deterministic_scientific_replay",
            ),
        )
    if section == "runs":
        if "checkpoints" in tail:
            return (
                "post_selection_training_runtime",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                ("exact_completed_epoch_continuation", "exact_checkpoint_reevaluation"),
            )
        if "materialization" in tail:
            return (
                "post_selection_materializations",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                ("exact_fold_membership", "exact_production_membership"),
            )
        return (
            "post_selection_run_evidence",
            ArtifactRetentionClass.RESTART_CRITICAL,
            "prohibited",
            "prohibited",
            ("post_selection_run_restart", "deterministic_scientific_replay"),
        )
    return (
        "post_selection_evidence_graph",
        ArtifactRetentionClass.RESTART_CRITICAL,
        "prohibited",
        "prohibited",
        ("cross_validation_authorization", "final_production_authorization"),
    )


def _family_for(relative: Path) -> tuple[str, ArtifactRetentionClass, str, str, tuple[str, ...]]:
    parts = relative.parts
    posix = relative.as_posix()
    name = relative.name.lower()

    if not parts:
        return ("workspace_root", ArtifactRetentionClass.UNKNOWN, "prohibited", "prohibited", ("campaign_workspace",))
    if parts[0] == "results":
        return ("results_and_diagnostics", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "prohibited", ("scientific_provenance",))
    if parts[0] == "models":
        return ("production_models", ArtifactRetentionClass.PROTECTED_PRODUCTION, "prohibited", "prohibited", ("production_inference",))
    if parts[0] == "data":
        return ("data7_data8_materializations", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "deferred_to_storage_reset", ("data8_hot_materialization", "training_input_materialization"))
    if parts[0] == "runs":
        if "evaluation-capsules" in parts or name.endswith(".eval-state.pt"):
            return ("evaluation_state_capsules", ArtifactRetentionClass.EVALUATION_CAPSULE, "prohibited", "deferred_to_storage_reset", ("nonselected_checkpoint_reevaluation", "target_head_reexport"))
        if "checkpoints" in parts or name.endswith(".pt"):
            return ("training_checkpoints", ArtifactRetentionClass.RESTART_CRITICAL, "prohibited", "prohibited", ("training_restart", "exact_checkpoint_reevaluation"))
        if "checkpoint-model-cache" in parts:
            return ("checkpoint_model_cache", ArtifactRetentionClass.RECONSTRUCTABLE_CACHE, "prohibited", "cache_candidate_owner_guard_required", ("faster_checkpoint_reevaluation",))
        if "logs" in parts or name.endswith(".log") or name.endswith("stdout") or name.endswith("stderr"):
            return ("training_logs", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "prohibited", ("training_diagnostics",))
        if "models" in parts or name.endswith(".model"):
            return ("run_models", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "prohibited", ("cheap_alternative_model_recovery",))
        return ("training_run_runtime", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "prohibited", ("training_restart_or_diagnostics",))
    if parts[0] == ".mdstats":
        if len(parts) >= 2 and parts[1] == "target-size":
            return _target_size_family(parts)
        if len(parts) >= 2 and parts[1] == "post-selection":
            return _post_selection_family(parts)
        if len(parts) >= 2 and parts[1] in {"campaign.sqlite3", "records", "hash-receipts.sqlite3"}:
            return ("campaign_state_and_provenance", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "prohibited", ("campaign_state", "scientific_provenance"))
        if len(parts) >= 2 and parts[1] == "frame-cache":
            return ("frame-cache", ArtifactRetentionClass.RECONSTRUCTABLE_CACHE, "prohibited", "deferred_to_storage_reset", ("faster_frame_access",))
        if len(parts) >= 2 and parts[1] in {"data7-cache", "data8-fixed-cache", "evaluation-graphs"}:
            return (parts[1], ArtifactRetentionClass.RECONSTRUCTABLE_CACHE, "prohibited", "deferred_to_storage_reset", ("historical_cache",))
        if len(parts) >= 2 and parts[1] in {"model-sweep", "evaluation-predictions", "true-label-replay"}:
            return (parts[1], ArtifactRetentionClass.SCIENTIFIC_CACHE, "prohibited", "deferred_to_storage_reset", ("historical_predictions_or_sweep",))
        if len(parts) >= 2 and parts[1] == "foundation-selected-head":
            return (
                "selected_head_training_foundation",
                ArtifactRetentionClass.RESTART_CRITICAL,
                "prohibited",
                "prohibited",
                (
                    "mh1_selected_head_training_restart",
                    "exact_training_foundation_reproduction",
                ),
            )
        if len(parts) >= 2 and parts[1] == "content-store":
            return ("immutable_content_store", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "deferred_to_storage_reset", ("physical_deduplication_backing",))
        if len(parts) >= 2 and parts[1] == "cold-archive":
            return ("cold_archive", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "deferred_to_storage_reset", ("archived_hot_representation_restore",))
        if len(parts) >= 2 and parts[1] == "preflight-smoke":
            return ("preflight_artifacts", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "deferred_to_storage_reset", ("preflight_reexecution",))
        return ("internal_campaign_artifacts", ArtifactRetentionClass.INTERMEDIATE, "prohibited", "prohibited", ("campaign_reanalysis",))
    if name.endswith(".json") or name.endswith(".csv") or name.endswith(".log"):
        return ("workspace_diagnostics", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "prohibited", ("scientific_provenance",))
    if name.endswith(".toml") or "manifest" in name:
        return ("workspace_configuration", ArtifactRetentionClass.PROTECTED_DIAGNOSTIC, "prohibited", "prohibited", ("campaign_reproducibility",))
    return ("other_campaign_owned", ArtifactRetentionClass.UNKNOWN, "prohibited", "prohibited", ("unknown_campaign_capability",))


@dataclass
class _MutableFamily:
    family: str
    retention_class: ArtifactRetentionClass
    auto: str
    manual: str
    capabilities: tuple[str, ...]
    logical: int = 0
    allocated: int = 0
    unique: int = 0
    files: int = 0
    directories: int = 0
    symlinks: int = 0


def build_campaign_storage_report(
    workspace: Path,
    *,
    protected_inputs: Sequence[ProtectedInputPath] = (),
    largest_limit: int = 25,
) -> CampaignStorageReport:
    workspace = Path(os.path.abspath(os.fspath(workspace)))
    boundary = CampaignOwnershipBoundary(workspace, protected_inputs=protected_inputs)
    families: dict[str, _MutableFamily] = {}
    largest: list[LargestArtifactRecord] = []
    directory_logical: dict[Path, int] = {}
    directory_allocated: dict[Path, int] = {}
    directory_meta: dict[Path, tuple[str, str, str, Path, bool, bool]] = {}
    seen_inodes: set[tuple[int, int]] = set()
    total_logical = total_allocated = total_unique = 0
    file_count = directory_count = symlink_count = 0
    escapes: list[str] = []
    ambiguous: list[str] = []

    if not workspace.exists():
        catalog = CampaignArtifactOwnershipCatalog(
            workspace=str(workspace),
            workspace_real_path=str(boundary.workspace_real),
            protected_inputs=tuple(protected_inputs),
            symlink_escapes=(),
            ambiguous_paths=(str(workspace),),
        )
        return CampaignStorageReport(catalog, 0, 0, 0, 0, 0, 0, (), ())

    stack = [workspace]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError:
            ambiguous.append(str(current))
            continue
        for entry in entries:
            path = Path(entry.path)
            try:
                stat_result = entry.stat(follow_symlinks=False)
            except OSError:
                ambiguous.append(str(path))
                continue
            try:
                relative = path.relative_to(workspace)
            except ValueError:
                ambiguous.append(str(path))
                continue
            input_key = boundary.protected_input_key_for(path, resolve=False)
            if input_key is None and not path.is_symlink():
                input_key = boundary.protected_input_key_for(path, resolve=True)
            if input_key is not None:
                family = f"configured_input:{input_key}"
                retention = ArtifactRetentionClass.PROTECTED_INPUT
                auto = "prohibited"
                manual = "prohibited"
                capabilities = ("source_or_reference_input_unavailable",)
            else:
                family, retention, auto, manual, capabilities = _family_for(relative)
            bucket = families.get(family)
            if bucket is None:
                bucket = families[family] = _MutableFamily(family, retention, auto, manual, capabilities)

            symlink = entry.is_symlink()
            is_dir = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
            logical = 0 if is_dir else int(stat_result.st_size)
            inode_allocated = _allocated_bytes(stat_result)
            inode_key = (int(stat_result.st_dev), int(stat_result.st_ino))
            first_inode = inode_key not in seen_inodes
            if first_inode:
                seen_inodes.add(inode_key)
            unique = logical if (first_inode and not is_dir) else 0
            allocated = inode_allocated if first_inode else 0

            total_logical += logical
            total_allocated += allocated
            total_unique += unique
            bucket.logical += logical
            bucket.allocated += allocated
            bucket.unique += unique

            # Attribute path-based logical bytes and inode-deduplicated physical
            # bytes to containing directories so the report can identify large
            # directories without recursively restatting them.
            parent = relative.parent
            while parent != Path("."):
                directory_logical[parent] = directory_logical.get(parent, 0) + logical
                directory_allocated[parent] = directory_allocated.get(parent, 0) + allocated
                parent = parent.parent
            if is_dir:
                directory_allocated[relative] = directory_allocated.get(relative, 0) + allocated

            if symlink:
                symlink_count += 1
                bucket.symlinks += 1
            elif is_dir:
                directory_count += 1
                bucket.directories += 1
                stack.append(path)
            elif is_file:
                file_count += 1
                bucket.files += 1
            else:
                ambiguous.append(str(path))

            real = _resolved(path)
            real_contained = _is_within(real, boundary.workspace_real)
            symlink_escape = bool(symlink and not real_contained)
            if symlink_escape:
                escapes.append(str(path))
            ownership = (
                ArtifactOwnershipClass.EXTERNAL_USER_INPUT
                if input_key is not None
                else (
                    ArtifactOwnershipClass.CAMPAIGN_OWNED_SYMLINK
                    if symlink
                    else ArtifactOwnershipClass.CAMPAIGN_OWNED
                )
            )
            if is_dir and not symlink:
                directory_meta[relative] = (
                    family, ownership.value, retention.value, real, real_contained, symlink_escape
                )
            else:
                largest.append(
                    LargestArtifactRecord(
                        path=str(path),
                        kind="symlink" if symlink else "file",
                        family=family,
                        ownership=ownership.value,
                        retention_class=retention.value,
                        logical_bytes=logical,
                        allocated_physical_bytes=inode_allocated,
                        hardlink_count=int(stat_result.st_nlink),
                        symlink=symlink,
                        real_path=str(real),
                        real_path_contained=real_contained,
                        symlink_escape=symlink_escape,
                    )
                )

    for relative, meta in directory_meta.items():
        family, ownership, retention, real, real_contained, symlink_escape = meta
        largest.append(
            LargestArtifactRecord(
                path=str(workspace / relative),
                kind="directory",
                family=family,
                ownership=ownership,
                retention_class=retention,
                logical_bytes=int(directory_logical.get(relative, 0)),
                allocated_physical_bytes=int(directory_allocated.get(relative, 0)),
                hardlink_count=1,
                symlink=False,
                real_path=str(real),
                real_path_contained=real_contained,
                symlink_escape=symlink_escape,
            )
        )

    family_records = tuple(
        StorageFamilyRecord(
            family=item.family,
            ownership=(
                ArtifactOwnershipClass.EXTERNAL_USER_INPUT.value
                if item.family.startswith("configured_input:")
                else ArtifactOwnershipClass.CAMPAIGN_OWNED.value
            ),
            retention_class=item.retention_class.value,
            logical_bytes=item.logical,
            allocated_physical_bytes=item.allocated,
            unique_inode_bytes=item.unique,
            file_count=item.files,
            directory_count=item.directories,
            symlink_count=item.symlinks,
            automatic_reclamation_eligibility=item.auto,
            manual_reclamation_eligibility=item.manual,
            capability_lost_if_deleted=item.capabilities,
        )
        for item in sorted(families.values(), key=lambda value: (-value.logical, value.family))
    )
    largest_records = tuple(
        sorted(largest, key=lambda item: (-item.logical_bytes, item.path))[: max(0, int(largest_limit))]
    )
    catalog = CampaignArtifactOwnershipCatalog(
        workspace=str(workspace),
        workspace_real_path=str(boundary.workspace_real),
        protected_inputs=tuple(protected_inputs),
        symlink_escapes=tuple(sorted(set(escapes))),
        ambiguous_paths=tuple(sorted(set(ambiguous))),
    )
    return CampaignStorageReport(
        ownership_catalog=catalog,
        logical_bytes=total_logical,
        allocated_physical_bytes=total_allocated,
        unique_inode_bytes=total_unique,
        file_count=file_count,
        directory_count=directory_count,
        symlink_count=symlink_count,
        families=family_records,
        largest_artifacts=largest_records,
    )
