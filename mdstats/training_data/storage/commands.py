"""Operator-facing storage commands, resolved through one canonical policy.

Every command here resolves the same :class:`~.policy.StoragePolicy`, builds
the same cross-owner inventory, and - when consequential - applies through the
same :class:`~.executor.StorageExecutor`.  There is no second destructive path
and no command that can act on a report label.

The mandatory sequence for a consequential action is plan, show, authorize:
``--dry-run`` prints and writes the plan and stops; ``--apply`` re-derives the
inventory, revalidates the plan against fresh owner state under the owning
publication barriers, and only then mutates.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .admission import StorageAdmissionError, admit_storage_operation
from .archive import (
    StorageArchiveError,
    create_cold_archive,
    list_archives,
    read_restore_journal,
    reclaim_archived_hot_members,
    restore_cold_archive,
    verify_cold_archive,
)
from .control_plane import open_storage_control_plane
from .dedup import deduplicate
from .durability import durable_publish_json
from .executor import StorageExecutor
from .inventory import (
    StorageInventorySnapshot,
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
    safe_candidates,
)
from .plan import (
    ACTION_EVICT_CACHE,
    ACTION_REMOVE,
    StoragePlan,
    build_storage_plan,
    planned_action,
)
from .policy import (
    ACTION_ARCHIVE,
    ACTION_AUDIT,
    ACTION_CLEANUP,
    ACTION_DEDUPLICATE,
    ACTION_REPORT,
    ACTION_RESTORE,
    TIER_CACHE,
    TIER_SAFE,
    StoragePolicy,
    resolve_storage_policy,
)
from .report import build_deep_storage_audit, build_owner_storage_report


def _format_bytes(value: int) -> str:
    number = float(int(value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(number) < 1024.0 or unit == "TiB":
            return f"{int(number)} B" if unit == "B" else f"{number:.1f} {unit}"
        number /= 1024.0
    return f"{int(value)} B"


class StorageDisabledError(RuntimeError):
    """`[cleanup].enabled = false` withholds consequential storage mutation."""


#: Mirrors the resolver default so the reserve composition below can compare
#: against the same value the resolver would otherwise pick.
_DEFAULT_RESERVE_BYTES = 2 * 1024**3


def _cleanup_section(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    section = cfg.get("cleanup", {}) if isinstance(cfg, Mapping) else {}
    return section if isinstance(section, Mapping) else {}


def _execution_reserve_bytes(cfg: Mapping[str, Any]) -> int | None:
    """The campaign's accepted `[execution].minimum_free_disk_gib` floor."""

    section = cfg.get("execution", {}) if isinstance(cfg, Mapping) else {}
    if not isinstance(section, Mapping) or "minimum_free_disk_gib" not in section:
        return None
    try:
        return int(float(section["minimum_free_disk_gib"]) * 1024**3)
    except (TypeError, ValueError):
        return None


def _resolve(args: Any, cfg: Mapping[str, Any], *, action: str, tier: str = TIER_SAFE):
    """Normalize every configuration and CLI surface into one policy identity.

    The historical ``[cleanup]`` knobs are aliases, normalized here *before*
    policy hashing so an operator who set them keeps the behavior they
    configured and equivalent spellings still produce one identity.
    """

    overrides: dict[str, Any] = {}
    cleanup = _cleanup_section(cfg)
    if "maximum_event_records" in cleanup:
        overrides["sqlite_compaction_maximum_events"] = cleanup["maximum_event_records"]
    # The campaign already owns a free-disk floor for execution. Storage does not
    # get a second, weaker one: a reserve is a floor, and the only safe
    # composition of two floors is the stricter of the two.
    execution_reserve = _execution_reserve_bytes(cfg)
    if execution_reserve is not None:
        storage_section = cfg.get("storage", {}) if isinstance(cfg, Mapping) else {}
        configured = (
            storage_section.get("safety_reserve_bytes")
            if isinstance(storage_section, Mapping)
            else None
        )
        floor = int(configured) if configured is not None else _DEFAULT_RESERVE_BYTES
        overrides["safety_reserve_bytes"] = max(floor, execution_reserve)
    for name in (
        "safety_reserve_bytes",
        "archive_codec",
        "archive_compression_level",
        "io_worker_limit",
    ):
        value = getattr(args, name, None)
        if value is not None:
            overrides[name] = value
    policy = resolve_storage_policy(
        cfg,
        action=action,
        tier=str(getattr(args, "tier", tier) or tier),
        apply=bool(getattr(args, "apply", False)),
        overrides=overrides,
    )
    if policy.apply and not bool(cleanup.get("enabled", True)):
        raise StorageDisabledError(
            "Consequential storage mutation is withheld by [cleanup].enabled = false. "
            "Reporting and planning remain available; set it to true to authorize "
            "an apply."
        )
    return policy


class StorageCommandContext:
    """Everything a storage command needs, resolved once through real owners."""

    def __init__(self, cfg: Mapping[str, Any], paths: Any, store: Any, boundary: Any) -> None:
        self.cfg = cfg
        self.paths = paths
        self.store = store
        self.boundary = boundary
        self.control_plane = open_storage_control_plane(paths)
        self.protected_inputs = getattr(boundary, "protected_inputs", ())

    def snapshot(self) -> StorageInventorySnapshot:
        return build_storage_inventory(
            self.cfg,
            self.paths,
            self.store,
            protected_inputs=self.protected_inputs,
            control_plane=self.control_plane,
        )

    def executor(self, policy: StoragePolicy) -> StorageExecutor:
        return StorageExecutor(
            paths=self.paths,
            policy=policy,
            control_plane=self.control_plane,
            boundary=self.boundary,
            resnapshot=self.snapshot,
        )

    def generations(self, snapshot: StorageInventorySnapshot) -> tuple[int, ...]:
        current = snapshot.current_generation
        return () if current is None else (int(current),)

    def write_result(self, name: str, payload: Mapping[str, Any]) -> Path | None:
        destination = Path(self.paths.results) / name
        authorized, _detail = self.boundary.destructive_authorization(destination)
        if not authorized:
            return None
        destination.parent.mkdir(parents=True, exist_ok=True)
        durable_publish_json(destination, dict(payload))
        return destination


# ---------------------------------------------------------------------------
# report / deep audit
# ---------------------------------------------------------------------------


def storage_report(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    """Read-only owner-driven report, or an explicit deep physical audit."""

    deep = bool(getattr(args, "deep", False))
    policy = _resolve(args, context.cfg, action=ACTION_AUDIT if deep else ACTION_REPORT)
    top = int(getattr(args, "top", 20) or 20)
    if deep:
        payload = build_deep_storage_audit(
            Path(context.paths.workspace),
            protected_inputs=context.protected_inputs,
            top=top,
        )
        context.write_result("storage-deep-audit.json", payload)
        return payload
    snapshot = context.snapshot()
    payload = build_owner_storage_report(snapshot, policy, top=top)
    context.write_result("storage-report.json", payload)
    return payload


def print_storage_report(payload: Mapping[str, Any]) -> None:
    if payload.get("schema", "").endswith("deep-audit.v1"):
        totals = payload["totals"]
        print("Campaign storage deep physical audit (read-only)", flush=True)
        print(
            "  totals: "
            f"logical={_format_bytes(int(totals['logical_bytes']))}; "
            f"allocated={_format_bytes(int(totals['allocated_physical_bytes']))}; "
            f"unique-inode={_format_bytes(int(totals['unique_inode_bytes']))}; "
            f"files={int(totals['file_count'])}; dirs={int(totals['directory_count'])}",
            flush=True,
        )
        return
    print("Campaign storage report (owner-driven, read-only)", flush=True)
    print(f"  workspace: {payload['workspace']}", flush=True)
    print(f"  current generation: {payload['current_generation']}", flush=True)
    print("  owner families:", flush=True)
    for item in payload["owner_families"][:10]:
        print(
            f"    {_format_bytes(int(item['logical_bytes'])):>10}  "
            f"{item['owner']} [{item['artifact_class']}]",
            flush=True,
        )
    reclaim = payload["potential_reclaim_by_action"]
    for name in ("safe", "cache", "archive"):
        entry = reclaim[name]
        print(
            f"  potential {name}: {entry['eligible_count']} eligible "
            f"({_format_bytes(int(entry['eligible_bytes']))}); "
            f"{entry['refused_count']} refused by an owner",
            flush=True,
        )
    for item in payload["unresolved_owners"]:
        print(
            f"  ! owner {item['owner']} unresolved: {item['detail']} "
            "(its artifacts are retained)",
            flush=True,
        )


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------


def build_cleanup_plan(
    context: StorageCommandContext, policy: StoragePolicy
) -> tuple[StoragePlan, StorageInventorySnapshot]:
    snapshot = context.snapshot()
    actions = []
    refusals: list[dict[str, Any]] = []
    for decision in safe_candidates(snapshot):
        if decision.eligible:
            actions.append(
                planned_action(
                    action=ACTION_REMOVE,
                    path=decision.path,
                    artifact_id=decision.artifact_id,
                    reason=decision.reason,
                )
            )
        else:
            refusals.append({"path": str(decision.path), "reason": decision.reason})
    if policy.tier == TIER_CACHE:
        for decision in cache_candidates(snapshot):
            if decision.eligible:
                actions.append(
                    planned_action(
                        action=ACTION_EVICT_CACHE,
                        path=decision.path,
                        artifact_id=decision.artifact_id,
                        reason=decision.reason,
                        capability_cost=decision.capability_cost,
                    )
                )
            else:
                refusals.append({"path": str(decision.path), "reason": decision.reason})
    plan = build_storage_plan(snapshot, policy, actions, refusals=refusals)
    return plan, snapshot


def storage_cleanup(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    """Plan, show, and - only when authorized - apply safe/cache cleanup."""

    policy = _resolve(args, context.cfg, action=ACTION_CLEANUP, tier=TIER_SAFE)
    plan, _snapshot = build_cleanup_plan(context, policy.for_apply(apply=False))
    payload: dict[str, Any] = {"plan": plan.to_dict()}
    # The written plan is an operator-facing advisory copy. Apply always
    # re-derives the inventory and revalidates in-process; nothing is ever
    # authorized by reading this file back.
    context.write_result(
        f"storage-cleanup-plan-{policy.tier}.json",
        {**plan.to_dict(), "advisory_copy": True, "authorizes_apply": False},
    )
    if not policy.apply:
        payload["execution"] = None
        return payload
    # The applied plan carries the apply flag; its policy identity is unchanged,
    # which is exactly why a plan can be authorized without a re-plan while a
    # material policy change still refuses.
    apply_plan = build_storage_plan(
        _snapshot,
        policy,
        plan.actions,
        refusals=plan.refusals,
        created_utc=plan.created_utc,
    )
    result = context.executor(policy).apply(apply_plan, trigger=f"cli:cleanup:{policy.tier}")
    payload["execution"] = result.to_dict()
    context.write_result(f"storage-cleanup-{policy.tier}.json", result.to_dict())
    _compact_campaign_state(context, policy, payload)
    return payload


def _compact_campaign_state(
    context: StorageCommandContext, policy: StoragePolicy, payload: dict[str, Any]
) -> None:
    """Bounded diagnostic-event housekeeping on the authoritative store.

    Compaction is a store-owner maintenance operation, not a deletion of
    scientific state: it bounds diagnostic event retention, which is separate
    from scientific records and from the receipt cache.

    ``VACUUM`` rewrites the database into a temporary copy, so it is admitted
    against the same safety reserve as any other storage operation. Running it
    without that admission is exactly how a maintenance step turns into an
    out-of-space failure on the authoritative state.
    """

    state_db = Path(context.paths.state_db)
    authorized, detail = context.boundary.destructive_authorization(state_db)
    if not authorized:
        payload["state_compaction"] = {"performed": False, "detail": detail}
        return
    try:
        size = int(state_db.stat().st_size) if state_db.is_file() else 0
        admission = admit_storage_operation(
            state_db.parent,
            policy,
            # VACUUM's peak is the original plus its rewritten copy.
            required_peak_bytes=2 * size,
            required_inodes=1,
        )
        context.store.compact(maximum_events=int(policy.sqlite_compaction_maximum_events))
        payload["state_compaction"] = {
            "performed": True,
            "detail": "diagnostic events bounded and the database rewritten",
            "admission": admission.to_dict(),
        }
    except StorageAdmissionError as exc:
        payload["state_compaction"] = {
            "performed": False,
            "detail": f"compaction was not admitted and was skipped: {exc}",
        }
    except Exception as exc:
        payload["state_compaction"] = {"performed": False, "detail": str(exc)}


def print_cleanup(payload: Mapping[str, Any]) -> None:
    plan = payload["plan"]
    print(f"Storage cleanup plan: {plan['policy_summary']}", flush=True)
    print(
        f"  candidates={plan['action_count']}; "
        f"potential reclaim={_format_bytes(int(plan['planned_bytes']))}",
        flush=True,
    )
    for action in plan["actions"][:10]:
        print(
            f"    {_format_bytes(int(action['size_bytes'])):>10}  "
            f"[{action['capability_cost']}] {action['path']}",
            flush=True,
        )
    for refusal in plan["refusals"][:5]:
        print(f"    retained: {refusal['path']}: {refusal['reason']}", flush=True)
    execution = payload.get("execution")
    if execution is None:
        print("  dry-run: nothing was modified", flush=True)
        return
    print(
        f"  execution status={execution['status']}; "
        f"reclaimed={_format_bytes(int(execution['reclaimed_bytes']))}; "
        f"refused={len(execution['refused_actions'])}",
        flush=True,
    )
    if execution["status"] != "complete":
        print(f"  detail: {execution['detail']}", flush=True)


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------


def storage_archive(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    """Create, list, verify, restore, or resume reclamation for a cold archive."""

    subcommand = str(getattr(args, "archive_command", "list") or "list")
    if subcommand == "list":
        policy = _resolve(args, context.cfg, action=ACTION_REPORT)
        entries = list_archives(context.control_plane)
        return {"archives": [dict(item) for item in entries], "policy": policy.to_dict()}
    if subcommand == "verify":
        policy = _resolve(args, context.cfg, action=ACTION_REPORT)
        manifest = verify_cold_archive(
            context.control_plane, str(args.archive_identity), policy
        )
        return {"verified": True, "manifest": manifest}
    if subcommand == "restore":
        policy = _resolve(args, context.cfg, action=ACTION_RESTORE)
        journal = read_restore_journal(context.control_plane, str(args.archive_identity))
        if not policy.apply:
            manifest = verify_cold_archive(
                context.control_plane, str(args.archive_identity), policy
            )
            return {
                "restore": None,
                "journal": journal,
                "manifest": manifest,
                "detail": "dry-run: the archive was authenticated; nothing was installed",
            }
        snapshot = context.snapshot()
        receipt = restore_cold_archive(
            workspace=Path(context.paths.workspace),
            control_plane=context.control_plane,
            policy=policy,
            boundary=context.boundary,
            archive_identity=str(args.archive_identity),
            paths=context.paths,
            generations=context.generations(snapshot),
        )
        payload = {"restore": receipt.to_dict()}
        context.write_result("storage-restore-receipt.json", receipt.to_dict())
        return payload
    if subcommand == "reclaim":
        policy = _resolve(args, context.cfg, action=ACTION_ARCHIVE)
        if not policy.apply:
            return {
                "reclaim": None,
                "detail": "dry-run: hot reclamation was not resumed",
            }
        snapshot = context.snapshot()
        result = reclaim_archived_hot_members(
            workspace=Path(context.paths.workspace),
            control_plane=context.control_plane,
            policy=policy,
            boundary=context.boundary,
            archive_identity=str(args.archive_identity),
            paths=context.paths,
            generations=context.generations(snapshot),
        )
        return {"reclaim": result.to_dict()}
    if subcommand != "create":
        raise StorageArchiveError(f"Unknown storage archive subcommand {subcommand!r}.")

    policy = _resolve(args, context.cfg, action=ACTION_ARCHIVE)
    snapshot = context.snapshot()
    decisions = archive_candidates(snapshot)
    eligible = [item for item in decisions if item.eligible]
    refused = [item for item in decisions if not item.eligible]
    requested = _requested_roots(args, snapshot, eligible)
    payload: dict[str, Any] = {
        "eligible": [
            {"artifact_id": item.artifact_id, "path": str(item.path), "reason": item.reason}
            for item in eligible
        ],
        "refused": [
            {"artifact_id": item.artifact_id, "path": str(item.path), "reason": item.reason}
            for item in refused
        ],
        "selected_roots": [str(item) for item in requested],
        "policy": policy.to_dict(),
    }
    if not requested:
        payload["archive"] = None
        payload["detail"] = (
            "no owner declared any artifact cold-replaceable; nothing was archived"
        )
        return payload
    plan = build_storage_plan(snapshot, policy, ())
    if not policy.apply:
        payload["archive"] = None
        payload["detail"] = "dry-run: no archive was created and no hot byte was removed"
        return payload
    result = create_cold_archive(
        workspace=Path(context.paths.workspace),
        control_plane=context.control_plane,
        policy=policy,
        boundary=context.boundary,
        roots=requested,
        lineage={
            "current_generation": snapshot.current_generation,
            "owner_binding": dict(plan.owner_binding),
            "artifact_ids": sorted(item.artifact_id for item in eligible),
        },
        plan_identity=plan.plan_identity,
        paths=context.paths,
        generations=context.generations(snapshot),
        reclaim_hot=not bool(getattr(args, "keep_hot", False)),
    )
    payload["archive"] = result.to_dict()
    payload["resolved_policy_summary"] = policy.describe()
    context.write_result("storage-archive-receipt.json", result.to_dict())
    return payload


def _requested_roots(
    args: Any, snapshot: StorageInventorySnapshot, eligible: Sequence[Any]
) -> tuple[Path, ...]:
    """Resolve operator-selected roots, restricted to owner-eligible artifacts."""

    selected = [Path(item.path) for item in eligible]
    requested = list(getattr(args, "root", None) or ())
    if not requested:
        return tuple(selected)
    chosen: list[Path] = []
    for value in requested:
        candidate = Path(os.path.abspath(os.fspath(Path(snapshot.workspace) / value)))
        match = next(
            (
                item
                for item in selected
                if item == candidate or _within(item, candidate) or _within(candidate, item)
            ),
            None,
        )
        if match is None:
            raise StorageArchiveError(
                f"{candidate} is not owner-declared cold-replaceable; archive never "
                "removes hot bytes an owner still requires."
            )
        chosen.append(candidate)
    return tuple(chosen)


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def print_archive(payload: Mapping[str, Any]) -> None:
    if "archives" in payload:
        entries = payload["archives"]
        print(f"Cold archive catalog: {len(entries)} retained representation(s)", flush=True)
        for entry in entries:
            print(
                f"  {entry['archive_identity']}  "
                f"{_format_bytes(int(entry['archive_size_bytes']))}  "
                f"members={entry['member_count']}  "
                f"hot={entry.get('hot_reclamation_state', 'unknown')}",
                flush=True,
            )
        return
    if payload.get("verified"):
        manifest = payload["manifest"]
        print(
            f"Cold archive {manifest['archive_identity']} verified: "
            f"{manifest['member_count']} member(s), "
            f"{_format_bytes(int(manifest['total_expanded_bytes']))} expanded",
            flush=True,
        )
        return
    if "restore" in payload:
        receipt = payload["restore"]
        if receipt is None:
            print(f"  {payload['detail']}", flush=True)
            return
        print(
            f"Restored archive {receipt['archive_identity']}: "
            f"{receipt['restored_files']} file(s) installed, "
            f"{receipt['already_present_files']} already present; "
            "restored evidence remains historical",
            flush=True,
        )
        return
    if "reclaim" in payload:
        result = payload["reclaim"]
        if result is None:
            print(f"  {payload['detail']}", flush=True)
            return
        print(
            f"Resumed hot reclamation for {result['archive_identity']}: "
            f"{len(result['reclaimed_hot_paths'])} reclaimed, "
            f"{len(result['remaining_hot_paths'])} still hot",
            flush=True,
        )
        return
    print("Cold archive creation", flush=True)
    for item in payload["eligible"]:
        print(f"  eligible: {item['path']}", flush=True)
    for item in payload["refused"][:5]:
        print(f"  retained hot: {item['path']}: {item['reason']}", flush=True)
    result = payload.get("archive")
    if result is None:
        print(f"  {payload.get('detail', 'nothing was archived')}", flush=True)
        return
    print(
        f"  archive {result['archive_identity']}: {result['member_count']} member(s); "
        f"reclaimed {len(result['reclaimed_hot_paths'])} hot file(s); "
        f"{len(result['remaining_hot_paths'])} remain hot",
        flush=True,
    )


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


def storage_deduplicate(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    policy = _resolve(args, context.cfg, action=ACTION_DEDUPLICATE)
    snapshot = context.snapshot()
    result = deduplicate(
        snapshot=snapshot,
        policy=policy,
        control_plane=context.control_plane,
        boundary=context.boundary,
        paths=context.paths,
        generations=context.generations(snapshot),
    )
    payload = result.to_dict()
    context.write_result("storage-deduplication.json", payload)
    return payload


def print_dedup(payload: Mapping[str, Any]) -> None:
    print(
        f"Immutable deduplication ({payload['realization']}): "
        f"{payload['group_count']} group(s)",
        flush=True,
    )
    if payload["applied"]:
        print(
            f"  linked={payload['links_replaced']}; "
            f"reclaimed={_format_bytes(int(payload['reclaimed_bytes']))}",
            flush=True,
        )
    else:
        print("  dry-run: no inode was replaced", flush=True)
    for note in payload["excluded"][:5]:
        print(f"  excluded: {note}", flush=True)


__all__ = [
    "StorageCommandContext",
    "StorageDisabledError",
    "build_cleanup_plan",
    "print_archive",
    "print_cleanup",
    "print_dedup",
    "print_storage_report",
    "storage_archive",
    "storage_cleanup",
    "storage_deduplicate",
    "storage_report",
]
