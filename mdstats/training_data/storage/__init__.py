"""Owner-driven MLFF campaign storage and I/O management.

Every consequential storage mutation - cleanup, deduplication, archive
creation, hot reclamation, restore, and campaign-state maintenance - is
realized by its own engine and authorized by one shared contract:

``real owners -> owner views -> cross-owner inventory snapshot -> action-scoped
resolved policy -> immutable owner-bound plan -> storage lease + every touched
owner's activity and publication seam -> fresh revalidation -> admission ->
narrow mutation -> truthful durable audit``

Specialized engines exist because writing a tar is not relinking an inode. The
authorization above them is identical, and nothing mutates outside it.

Storage is never a second authority for scientific identity, target membership,
selected size, CV acceptance, representative checkpoint choice, publication
membership, qualification outcome, locked activation, or a release verdict. It
reads what the accepted owners say and acts only inside what they allow.

Modules:

``policy``        action-scoped resolved policy; authorization stays invocation-local
``owners``        adapters turning each current owner into uniform views
``inventory``     cross-owner protection closure, graph integrity, member authorization
``plan``          the immutable owner-bound plan and its revalidation
``admission``     conservative peak byte/inode admission before any mutation
``lease``         storage serialization plus owner activity/publication seams
``executor``      the one authorization contract every engine runs inside
``archive``       bounded, immutable, owner-bound cold archive v2
``dedup``         direct owner-certified hardlink aliasing, no persistent store
``maintenance``   benefit-gated CampaignStore maintenance as its own action
``control_plane`` storage's own catalog/journal/audit/lease state
``durability``    the one crash-durable publication boundary
``trust``         mount boundaries as ownership boundaries
``report``        bounded owner report and explicit bounded deep audit
"""

from __future__ import annotations

from .admission import (
    AdmissionObservation,
    StorageAdmissionError,
    admit_storage_operation,
    observe_filesystem,
    revalidate_admission,
)
from .archive import (
    COLD_ARCHIVE_MANIFEST_SCHEMA,
    COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA,
    ArchiveMember,
    ArchivePlanBundle,
    StorageArchiveError,
    archive_admission,
    archive_container_bytes,
    archive_create_engine,
    archive_reclaim_engine,
    archive_restore_engine,
    build_archive_plan_actions,
    build_reclaim_plan_actions,
    build_restore_plan_actions,
    collect_members,
    list_archives,
    logical_identity,
    read_manifest,
    read_restore_journal,
    representation_identity,
    restore_admission,
    select_archive_roots,
    verify_cold_archive,
)
from .control_plane import (
    IMMUTABLE_CATALOG_FIELDS,
    STORAGE_CONTROL_ROOT_NAME,
    StorageControlPlane,
    StorageControlPlaneError,
    open_storage_control_plane,
    open_storage_control_plane_readonly,
    resolve_inside_root,
)
from .dedup import (
    DEDUPLICATION_REPORT_SCHEMA,
    DedupResult,
    StorageDedupError,
    build_dedup_plan,
    dedup_engine,
    same_filesystem,
)
from .durability import (
    StorageDurabilityError,
    canonical_digest,
    durable_append_jsonl,
    durable_publish_bytes,
    durable_publish_json,
    durable_unlink,
    parallel_digests,
    sha256_file,
)
from .executor import (
    STATUS_COMPLETE,
    STATUS_PARTIAL,
    STATUS_PLANNED,
    STATUS_REFUSED,
    StorageAuthorizationError,
    StorageExecutionResult,
    StorageExecutor,
    operation_identity,
    remove_certified_subtree,
    remove_durably,
    synchronization_for,
)
from .inventory import (
    STORAGE_INVENTORY_SCHEMA,
    EligibilityDecision,
    OwnerGraphError,
    StorageInventorySnapshot,
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
    compute_protection_closure,
    safe_candidates,
)
from .lease import (
    OwnerSynchronization,
    StorageLeaseUnavailableError,
    owner_mutation_barrier,
    post_selection_publication_barrier,
    qualification_publication_barrier,
    storage_operation_lease,
)
from .maintenance import (
    MaintenanceDecision,
    campaign_state_maintenance_engine,
    measure_reclaimable,
    plan_campaign_state_maintenance,
)
from .owners import (
    ArtifactClass,
    OwnerArtifactView,
    OwnerViewSet,
    SubtreeCoverage,
    build_owner_views,
    validate_owner_graph,
)
from .plan import (
    ACTION_ARCHIVE_MEMBER,
    ACTION_DEDUP_LINK,
    ACTION_EVICT_CACHE,
    ACTION_MAINTAIN_STATE,
    ACTION_RECLAIM_MEMBER,
    ACTION_REMOVE,
    ACTION_RESTORE_CONTAINER,
    ACTION_RESTORE_MEMBER,
    STORAGE_PLAN_SCHEMA,
    PlannedAction,
    StoragePlan,
    StoragePlanStaleError,
    build_storage_plan,
    planned_action,
    revalidate_plan,
)
from .policy import (
    ACTION_ARCHIVE,
    ACTION_AUDIT,
    ACTION_CLEANUP,
    ACTION_DEDUPLICATE,
    ACTION_REPORT,
    ACTION_RESTORE,
    FORBIDDEN_AUTHORITY_KEYS,
    TIER_ARCHIVE,
    TIER_CACHE,
    TIER_SAFE,
    StoragePolicy,
    StoragePolicyError,
    resolve_storage_policy,
)
from .report import (
    STORAGE_DEEP_AUDIT_SCHEMA,
    STORAGE_OWNER_REPORT_SCHEMA,
    build_deep_storage_audit,
    build_owner_storage_report,
)
from .trust import (
    MountIdentityResolver,
    crosses_mount_boundary,
    mount_resolver,
    set_mount_resolver,
    walk_contained,
)

__all__ = [
    "ACTION_ARCHIVE",
    "ACTION_ARCHIVE_MEMBER",
    "ACTION_AUDIT",
    "ACTION_CLEANUP",
    "ACTION_DEDUPLICATE",
    "ACTION_DEDUP_LINK",
    "ACTION_EVICT_CACHE",
    "ACTION_MAINTAIN_STATE",
    "ACTION_RECLAIM_MEMBER",
    "ACTION_REMOVE",
    "ACTION_REPORT",
    "ACTION_RESTORE",
    "ACTION_RESTORE_CONTAINER",
    "ACTION_RESTORE_MEMBER",
    "COLD_ARCHIVE_MANIFEST_SCHEMA",
    "COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA",
    "DEDUPLICATION_REPORT_SCHEMA",
    "FORBIDDEN_AUTHORITY_KEYS",
    "IMMUTABLE_CATALOG_FIELDS",
    "STATUS_COMPLETE",
    "STATUS_PARTIAL",
    "STATUS_PLANNED",
    "STATUS_REFUSED",
    "STORAGE_CONTROL_ROOT_NAME",
    "STORAGE_DEEP_AUDIT_SCHEMA",
    "STORAGE_INVENTORY_SCHEMA",
    "STORAGE_OWNER_REPORT_SCHEMA",
    "STORAGE_PLAN_SCHEMA",
    "TIER_ARCHIVE",
    "TIER_CACHE",
    "TIER_SAFE",
    "AdmissionObservation",
    "ArchiveMember",
    "ArchivePlanBundle",
    "ArtifactClass",
    "DedupResult",
    "EligibilityDecision",
    "MaintenanceDecision",
    "MountIdentityResolver",
    "OwnerArtifactView",
    "OwnerGraphError",
    "OwnerSynchronization",
    "OwnerViewSet",
    "PlannedAction",
    "StorageAdmissionError",
    "StorageArchiveError",
    "StorageAuthorizationError",
    "StorageControlPlane",
    "StorageControlPlaneError",
    "StorageDedupError",
    "StorageDurabilityError",
    "StorageExecutionResult",
    "StorageExecutor",
    "StorageInventorySnapshot",
    "StorageLeaseUnavailableError",
    "StoragePlan",
    "StoragePlanStaleError",
    "StoragePolicy",
    "StoragePolicyError",
    "SubtreeCoverage",
    "admit_storage_operation",
    "archive_admission",
    "archive_candidates",
    "archive_container_bytes",
    "archive_create_engine",
    "archive_reclaim_engine",
    "archive_restore_engine",
    "build_archive_plan_actions",
    "build_dedup_plan",
    "build_deep_storage_audit",
    "build_owner_storage_report",
    "build_owner_views",
    "build_reclaim_plan_actions",
    "build_restore_plan_actions",
    "build_storage_inventory",
    "build_storage_plan",
    "cache_candidates",
    "campaign_state_maintenance_engine",
    "canonical_digest",
    "collect_members",
    "compute_protection_closure",
    "crosses_mount_boundary",
    "dedup_engine",
    "durable_append_jsonl",
    "durable_publish_bytes",
    "durable_publish_json",
    "durable_unlink",
    "list_archives",
    "logical_identity",
    "measure_reclaimable",
    "mount_resolver",
    "observe_filesystem",
    "open_storage_control_plane",
    "open_storage_control_plane_readonly",
    "operation_identity",
    "owner_mutation_barrier",
    "parallel_digests",
    "plan_campaign_state_maintenance",
    "planned_action",
    "post_selection_publication_barrier",
    "qualification_publication_barrier",
    "read_manifest",
    "read_restore_journal",
    "remove_certified_subtree",
    "remove_durably",
    "representation_identity",
    "resolve_inside_root",
    "resolve_storage_policy",
    "restore_admission",
    "revalidate_admission",
    "revalidate_plan",
    "safe_candidates",
    "same_filesystem",
    "select_archive_roots",
    "set_mount_resolver",
    "sha256_file",
    "storage_operation_lease",
    "synchronization_for",
    "validate_owner_graph",
    "verify_cold_archive",
    "walk_contained",
]
