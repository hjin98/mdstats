"""One canonical resolved storage policy identity.

A plan that was inspected under one reserve/codec/threshold/concurrency policy
must not execute later under silently different defaults.  Every CLI, config,
and API entry point resolves through :func:`resolve_storage_policy`, which
normalizes aliases *before* hashing so equivalent spellings produce one
identity, and rejects unsupported combinations before any mutation.

Dynamic measurements - free bytes, inode headroom, observed saturation - are
execution observations recorded on the plan, never policy defaults, so a
changed disk does not invalidate a scientific identity and a changed policy
does invalidate an unapplied plan.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from .durability import canonical_digest

STORAGE_POLICY_SCHEMA = "mdstats.mlff-storage-policy.v1"

#: The consequential actions this package implements.  ``report`` and
#: ``audit`` are read-only; the rest are consequential and require an explicit
#: apply authorization.
ACTION_REPORT = "report"
ACTION_AUDIT = "audit"
ACTION_CLEANUP = "cleanup"
ACTION_DEDUPLICATE = "deduplicate"
ACTION_ARCHIVE = "archive"
ACTION_RESTORE = "restore"
ACTIONS = (
    ACTION_REPORT,
    ACTION_AUDIT,
    ACTION_CLEANUP,
    ACTION_DEDUPLICATE,
    ACTION_ARCHIVE,
    ACTION_RESTORE,
)
READ_ONLY_ACTIONS = frozenset({ACTION_REPORT, ACTION_AUDIT})

TIER_SAFE = "safe"
TIER_CACHE = "cache"
TIER_ARCHIVE = "archive"
TIERS = (TIER_SAFE, TIER_CACHE, TIER_ARCHIVE)

#: Retired consequential-loss tiers.  They are not current product authority
#: and are rejected by name rather than silently mapped onto a safer tier.
RETIRED_TIERS = ("recompute", "compact")

_TIER_ALIASES = {
    "safe": TIER_SAFE,
    "lifecycle-safe": TIER_SAFE,
    "lifecycle_safe": TIER_SAFE,
    "cache": TIER_CACHE,
    "caches": TIER_CACHE,
    "archive": TIER_ARCHIVE,
    "cold-archive": TIER_ARCHIVE,
    "cold_archive": TIER_ARCHIVE,
}

_ACTION_ALIASES = {
    "report": ACTION_REPORT,
    "status": ACTION_REPORT,
    "audit": ACTION_AUDIT,
    "deep-audit": ACTION_AUDIT,
    "deep_audit": ACTION_AUDIT,
    "cleanup": ACTION_CLEANUP,
    "clean": ACTION_CLEANUP,
    "deduplicate": ACTION_DEDUPLICATE,
    "dedup": ACTION_DEDUPLICATE,
    "dedupe": ACTION_DEDUPLICATE,
    "archive": ACTION_ARCHIVE,
    "restore": ACTION_RESTORE,
}

CODEC_GZIP = "tar+gzip"
CODEC_STORE = "tar"
CODECS = (CODEC_GZIP, CODEC_STORE)
_CODEC_ALIASES = {
    "gzip": CODEC_GZIP,
    "gz": CODEC_GZIP,
    "tar+gzip": CODEC_GZIP,
    "tar.gz": CODEC_GZIP,
    "none": CODEC_STORE,
    "store": CODEC_STORE,
    "tar": CODEC_STORE,
}

DEDUP_HARDLINK = "same-filesystem-content-addressed-hardlink"
DEDUP_DISABLED = "disabled"
DEDUP_REALIZATIONS = (DEDUP_HARDLINK, DEDUP_DISABLED)
_DEDUP_ALIASES = {
    "hardlink": DEDUP_HARDLINK,
    "hardlinks": DEDUP_HARDLINK,
    DEDUP_HARDLINK: DEDUP_HARDLINK,
    "disabled": DEDUP_DISABLED,
    "off": DEDUP_DISABLED,
    "none": DEDUP_DISABLED,
}


class StoragePolicyError(ValueError):
    """A requested storage policy is unsupported or internally inconsistent."""


def _normalize(value: Any, aliases: Mapping[str, str], *, name: str) -> str:
    token = str(value).strip().lower().replace(" ", "-")
    normalized = aliases.get(token) or aliases.get(token.replace("-", "_"))
    if normalized is None:
        raise StoragePolicyError(
            f"Unsupported storage {name} {value!r}; choose one of "
            f"{sorted(set(aliases.values()))}."
        )
    return normalized


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise StoragePolicyError(f"Storage policy {name} must be an integer.") from exc
    if number < minimum:
        raise StoragePolicyError(f"Storage policy {name} must be >= {minimum}.")
    return number


def _nonnegative_float(value: Any, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StoragePolicyError(f"Storage policy {name} must be a number.") from exc
    if number < 0.0 or number != number:
        raise StoragePolicyError(f"Storage policy {name} must be a nonnegative number.")
    return number


@dataclass(frozen=True, slots=True)
class StoragePolicy:
    """The one resolved operational policy a storage plan binds.

    Every field materially affects candidate selection, admission, or the
    physical realization of a mutation.  Presentation-only concerns (report
    width, JSON formatting, how many largest artifacts are printed) are
    deliberately absent: changing them must not invalidate an unapplied plan.
    """

    action: str
    tier: str
    apply: bool
    safety_reserve_bytes: int
    safety_reserve_fraction: float
    minimum_free_inodes: int
    cache_eviction_maximum_bytes: int
    sqlite_compaction_maximum_events: int
    archive_codec: str
    archive_compression_level: int
    archive_member_limit: int
    archive_expanded_bytes_limit: int
    archive_expansion_ratio_limit: float
    dedup_realization: str
    dedup_minimum_file_bytes: int
    io_worker_limit: int
    deep_audit_entry_limit: int
    operation_lease_timeout_seconds: float
    audit_retention_records: int

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise StoragePolicyError(f"Unsupported storage action {self.action!r}.")
        if self.tier not in TIERS:
            raise StoragePolicyError(f"Unsupported storage tier {self.tier!r}.")
        if self.archive_codec not in CODECS:
            raise StoragePolicyError(f"Unsupported archive codec {self.archive_codec!r}.")
        if self.dedup_realization not in DEDUP_REALIZATIONS:
            raise StoragePolicyError(
                f"Unsupported dedup realization {self.dedup_realization!r}."
            )
        if self.apply and self.action in READ_ONLY_ACTIONS:
            raise StoragePolicyError(
                f"Storage action {self.action!r} is read-only and cannot be applied."
            )
        if self.action == ACTION_DEDUPLICATE and self.dedup_realization == DEDUP_DISABLED:
            raise StoragePolicyError(
                "Deduplication was requested while the dedup realization is disabled."
            )
        if self.tier == TIER_ARCHIVE and self.action not in (ACTION_ARCHIVE, ACTION_REPORT):
            raise StoragePolicyError(
                "The archive tier belongs to the archive action; safe/cache cleanup "
                "never performs archive representation changes."
            )
        if not 0.0 <= self.safety_reserve_fraction < 1.0:
            raise StoragePolicyError(
                "Storage policy safety_reserve_fraction must be within [0, 1)."
            )
        if self.archive_codec == CODEC_STORE and self.archive_compression_level != 0:
            raise StoragePolicyError(
                "An uncompressed archive codec cannot carry a nonzero compression level."
            )
        if self.archive_codec == CODEC_GZIP and not 1 <= self.archive_compression_level <= 9:
            raise StoragePolicyError("gzip compression level must be within [1, 9].")
        if self.archive_expansion_ratio_limit < 1.0:
            raise StoragePolicyError(
                "The archive expansion-ratio limit must be at least 1.0."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_POLICY_SCHEMA,
            "action": self.action,
            "tier": self.tier,
            "apply": bool(self.apply),
            "safety_reserve_bytes": int(self.safety_reserve_bytes),
            "safety_reserve_fraction": float(self.safety_reserve_fraction),
            "minimum_free_inodes": int(self.minimum_free_inodes),
            "cache_eviction_maximum_bytes": int(self.cache_eviction_maximum_bytes),
            "sqlite_compaction_maximum_events": int(self.sqlite_compaction_maximum_events),
            "archive_codec": self.archive_codec,
            "archive_compression_level": int(self.archive_compression_level),
            "archive_member_limit": int(self.archive_member_limit),
            "archive_expanded_bytes_limit": int(self.archive_expanded_bytes_limit),
            "archive_expansion_ratio_limit": float(self.archive_expansion_ratio_limit),
            "dedup_realization": self.dedup_realization,
            "dedup_minimum_file_bytes": int(self.dedup_minimum_file_bytes),
            "io_worker_limit": int(self.io_worker_limit),
            "deep_audit_entry_limit": int(self.deep_audit_entry_limit),
            "operation_lease_timeout_seconds": float(self.operation_lease_timeout_seconds),
            "audit_retention_records": int(self.audit_retention_records),
        }

    @property
    def policy_identity(self) -> str:
        """Digest of the resolved consequential policy.

        ``apply`` is excluded: a dry-run plan and its authorized application are
        the same policy, and requiring a re-plan between them would make the
        mandatory plan/authorize sequence impossible.
        """

        payload = {k: v for k, v in self._payload().items() if k != "apply"}
        return canonical_digest(payload)

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_identity": self.policy_identity}

    def for_apply(self, *, apply: bool) -> "StoragePolicy":
        return replace(self, apply=bool(apply))

    def describe(self) -> str:
        """One operator-facing line naming the consequential resolved choices.

        Nothing here is a secret or a machine credential: only the action, the
        tier, and the material automatic choices are reported.
        """

        consequential = "apply" if self.apply else "dry-run"
        return (
            f"action={self.action} tier={self.tier} {consequential} "
            f"codec={self.archive_codec}:{self.archive_compression_level} "
            f"dedup={self.dedup_realization} io_workers={self.io_worker_limit} "
            f"reserve={self.safety_reserve_bytes}B+{self.safety_reserve_fraction:.3f} "
            f"identity={self.policy_identity[:12]}"
        )


def _section(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = cfg.get(name, {}) if isinstance(cfg, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def resolve_storage_policy(
    cfg: Mapping[str, Any] | None = None,
    *,
    action: str = ACTION_REPORT,
    tier: str = TIER_SAFE,
    apply: bool = False,
    overrides: Mapping[str, Any] | None = None,
) -> StoragePolicy:
    """Resolve one canonical storage policy from config plus explicit overrides.

    Only the ``[storage]`` configuration section participates.  No environment
    variable may widen deletion or archive authority: this resolver reads none,
    so a deployment cannot silently expand what a storage action is allowed to
    remove.
    """

    config = _section(cfg or {}, "storage")
    merged: dict[str, Any] = dict(config)
    for key, value in dict(overrides or {}).items():
        if value is not None:
            merged[key] = value

    requested_tier = merged.pop("tier", tier)
    if str(requested_tier).strip().lower() in RETIRED_TIERS:
        raise StoragePolicyError(
            f"Storage tier {requested_tier!r} is a retired consequential-loss tier and "
            "is not current product authority; intentionally lossy history pruning "
            "requires an explicit future product decision."
        )

    policy = StoragePolicy(
        action=_normalize(merged.pop("action", action), _ACTION_ALIASES, name="action"),
        tier=_normalize(requested_tier, _TIER_ALIASES, name="tier"),
        apply=bool(merged.pop("apply", apply)),
        safety_reserve_bytes=_positive_int(
            merged.pop("safety_reserve_bytes", 2 * 1024**3),
            name="safety_reserve_bytes",
            minimum=0,
        ),
        safety_reserve_fraction=_nonnegative_float(
            merged.pop("safety_reserve_fraction", 0.02),
            name="safety_reserve_fraction",
        ),
        minimum_free_inodes=_positive_int(
            merged.pop("minimum_free_inodes", 4096), name="minimum_free_inodes", minimum=0
        ),
        cache_eviction_maximum_bytes=_positive_int(
            merged.pop("cache_eviction_maximum_bytes", 64 * 1024**3),
            name="cache_eviction_maximum_bytes",
            minimum=0,
        ),
        sqlite_compaction_maximum_events=_positive_int(
            merged.pop("sqlite_compaction_maximum_events", 10_000),
            name="sqlite_compaction_maximum_events",
            minimum=0,
        ),
        archive_codec=_normalize(
            merged.pop("archive_codec", CODEC_GZIP), _CODEC_ALIASES, name="archive codec"
        ),
        # Level 1 is the measured default: on representative campaign bulk it
        # reaches the same compression ratio as levels 6 and 9 while costing
        # ~20% less to create and ~20% less to restore.
        archive_compression_level=_positive_int(
            merged.pop("archive_compression_level", 1),
            name="archive_compression_level",
            minimum=0,
        ),
        archive_member_limit=_positive_int(
            merged.pop("archive_member_limit", 1_000_000), name="archive_member_limit"
        ),
        archive_expanded_bytes_limit=_positive_int(
            merged.pop("archive_expanded_bytes_limit", 2 * 1024**4),
            name="archive_expanded_bytes_limit",
        ),
        archive_expansion_ratio_limit=_nonnegative_float(
            merged.pop("archive_expansion_ratio_limit", 200.0),
            name="archive_expansion_ratio_limit",
        ),
        dedup_realization=_normalize(
            merged.pop("dedup_realization", DEDUP_HARDLINK),
            _DEDUP_ALIASES,
            name="dedup realization",
        ),
        dedup_minimum_file_bytes=_positive_int(
            merged.pop("dedup_minimum_file_bytes", 4096),
            name="dedup_minimum_file_bytes",
            minimum=1,
        ),
        io_worker_limit=_positive_int(merged.pop("io_worker_limit", 4), name="io_worker_limit"),
        deep_audit_entry_limit=_positive_int(
            merged.pop("deep_audit_entry_limit", 200_000), name="deep_audit_entry_limit"
        ),
        operation_lease_timeout_seconds=_nonnegative_float(
            merged.pop("operation_lease_timeout_seconds", 30.0),
            name="operation_lease_timeout_seconds",
        ),
        audit_retention_records=_positive_int(
            merged.pop("audit_retention_records", 5000),
            name="audit_retention_records",
            minimum=1,
        ),
    )
    unknown = sorted(key for key in merged if not str(key).startswith("_"))
    if unknown:
        raise StoragePolicyError(
            f"Unknown [storage] policy key(s): {unknown}. An unrecognized key is "
            "rejected rather than ignored, so a typo can never silently widen or "
            "narrow storage authority."
        )
    return policy


def storage_reserve_bytes(policy: StoragePolicy, total_bytes: int) -> int:
    """The absolute safety reserve for one filesystem under this policy."""

    fractional = int(float(total_bytes) * float(policy.safety_reserve_fraction))
    return max(int(policy.safety_reserve_bytes), fractional)


def default_policy_for(action: str, **kwargs: Any) -> StoragePolicy:
    """Convenience resolver for API callers with no campaign configuration."""

    return resolve_storage_policy({}, action=action, **kwargs)


def workspace_policy_path(workspace: str | Path) -> Path:
    """Where a resolved policy is echoed for operator diagnostics."""

    return Path(workspace) / ".mdstats" / "storage" / "resolved-policy.json"


__all__ = [
    "ACTIONS",
    "ACTION_ARCHIVE",
    "ACTION_AUDIT",
    "ACTION_CLEANUP",
    "ACTION_DEDUPLICATE",
    "ACTION_REPORT",
    "ACTION_RESTORE",
    "CODECS",
    "CODEC_GZIP",
    "CODEC_STORE",
    "DEDUP_DISABLED",
    "DEDUP_HARDLINK",
    "READ_ONLY_ACTIONS",
    "RETIRED_TIERS",
    "STORAGE_POLICY_SCHEMA",
    "TIERS",
    "TIER_ARCHIVE",
    "TIER_CACHE",
    "TIER_SAFE",
    "StoragePolicy",
    "StoragePolicyError",
    "default_policy_for",
    "resolve_storage_policy",
    "storage_reserve_bytes",
    "workspace_policy_path",
]
