"""Owner-driven MLFF campaign storage and I/O management.

The subsystem is organized around one flow, and every consequential mutation
goes through all of it:

``real owners -> owner views -> cross-owner inventory snapshot -> resolved
storage policy -> immutable owner-bound plan -> owner-local race barrier +
revalidation -> executor -> durable audit -> restart-equivalent product``.

Storage is never a second authority for scientific identity, target
membership, selected size, CV acceptance, representative checkpoint choice,
publication membership, qualification outcome, locked activation, or a release
verdict.  It reads what the accepted owners say and acts only inside what they
allow.

Modules:

``policy``        one canonical resolved operational policy identity
``owners``        adapters turning each current owner into uniform views
``inventory``     cross-owner protection closure and eligibility
``plan``          the immutable owner-bound plan and its revalidation
``admission``     bytes/inode/scratch admission before any mutation
``lease``         storage-operation serialization and owner race barriers
``executor``      the single consequential cleanup mutation path
``archive``       bounded, identity-keyed, crash-durable cold archive v2
``dedup``         owner-certified immutable deduplication
``control_plane`` storage's own catalog/journal/audit/lease state
``durability``    the one crash-durable publication boundary
``report``        owner-driven fast report and explicit deep physical audit
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
    ArchiveCreationResult,
    ArchiveMember,
    ArchiveRestoreResult,
    StorageArchiveError,
    collect_members,
    create_cold_archive,
    list_archives,
    reclaim_archived_hot_members,
    read_restore_journal,
    restore_cold_archive,
    verify_cold_archive,
)
from .control_plane import (
    STORAGE_CONTROL_ROOT_NAME,
    StorageControlPlane,
    StorageControlPlaneError,
    open_storage_control_plane,
    resolve_inside_root,
)
from .dedup import (
    DEDUPLICATION_REPORT_SCHEMA,
    DedupResult,
    StorageDedupError,
    deduplicate,
    prune_orphan_content_objects,
)
from .durability import (
    StorageDurabilityError,
    canonical_digest,
    durable_append_jsonl,
    durable_publish_bytes,
    durable_publish_json,
    durable_unlink,
    sha256_file,
)
from .executor import (
    STATUS_COMPLETE,
    STATUS_PARTIAL,
    STATUS_PLANNED,
    STATUS_REFUSED,
    StorageExecutionResult,
    StorageExecutor,
    operation_identity,
)
from .inventory import (
    STORAGE_INVENTORY_SCHEMA,
    EligibilityDecision,
    StorageInventorySnapshot,
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
    compute_protection_closure,
    safe_candidates,
)
from .lease import (
    StorageLeaseUnavailableError,
    owner_mutation_barrier,
    post_selection_publication_barrier,
    qualification_publication_barrier,
    storage_operation_lease,
)
from .owners import (
    ArtifactClass,
    OwnerArtifactView,
    OwnerViewSet,
    build_owner_views,
)
from .plan import (
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

__all__ = [
    "ACTION_ARCHIVE",
    "ACTION_AUDIT",
    "ACTION_CLEANUP",
    "ACTION_DEDUPLICATE",
    "ACTION_REPORT",
    "ACTION_RESTORE",
    "COLD_ARCHIVE_MANIFEST_SCHEMA",
    "COLD_ARCHIVE_RESTORE_RECEIPT_SCHEMA",
    "DEDUPLICATION_REPORT_SCHEMA",
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
    "ArchiveCreationResult",
    "ArchiveMember",
    "ArchiveRestoreResult",
    "ArtifactClass",
    "DedupResult",
    "EligibilityDecision",
    "OwnerArtifactView",
    "OwnerViewSet",
    "PlannedAction",
    "StorageAdmissionError",
    "StorageArchiveError",
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
    "admit_storage_operation",
    "archive_candidates",
    "build_deep_storage_audit",
    "build_owner_storage_report",
    "build_owner_views",
    "build_storage_inventory",
    "build_storage_plan",
    "cache_candidates",
    "canonical_digest",
    "collect_members",
    "compute_protection_closure",
    "create_cold_archive",
    "deduplicate",
    "durable_append_jsonl",
    "durable_publish_bytes",
    "durable_publish_json",
    "durable_unlink",
    "list_archives",
    "observe_filesystem",
    "open_storage_control_plane",
    "operation_identity",
    "owner_mutation_barrier",
    "planned_action",
    "post_selection_publication_barrier",
    "prune_orphan_content_objects",
    "qualification_publication_barrier",
    "read_restore_journal",
    "reclaim_archived_hot_members",
    "resolve_inside_root",
    "resolve_storage_policy",
    "restore_cold_archive",
    "revalidate_admission",
    "revalidate_plan",
    "safe_candidates",
    "sha256_file",
    "storage_operation_lease",
    "verify_cold_archive",
]
