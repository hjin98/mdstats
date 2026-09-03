"""Operator-facing storage commands.

Two invariants shape every function here.

*Authorization is invocation-local.*  A command mutates only when the current
caller explicitly asked it to.  Configuration can tune how an action behaves; it
can never authorize one, and it can never redirect which action a command
performs.

*Non-apply is observational.*  Report, list, verify, and every dry-run leave
managed campaign state byte-for-byte unchanged.  They open the campaign store
read-only, locate the storage control plane without creating it, never
materialize an owner's generation root, and return their result rather than
writing it somewhere.  A command that had to create state in order to describe
the campaign would have already changed the thing it was describing.

Every consequential path - cleanup, dedup, archive create, hot reclaim, restore,
and campaign-state maintenance - is realized by its own engine but authorized by
one shared contract in :class:`~.executor.StorageExecutor`: owner-bound plan,
fresh under-synchronization revalidation, physical boundary, admission, and
truthful terminal audit.  The engines differ; the authorization does not.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .admission import StorageAdmissionError, admit_storage_operation
from .archive import (
    ArchivePlanBundle,
    StorageArchiveError,
    archive_admission,
    archive_create_engine,
    archive_reclaim_engine,
    archive_restore_engine,
    build_archive_plan_actions,
    bind_representation_authority,
    build_reclaim_plan_actions,
    build_restore_plan_actions,
    list_archives,
    read_restore_journal,
    restore_admission,
    select_archive_roots,
    verify_cold_archive,
)
from .control_plane import (
    StorageControlPlane,
    open_storage_control_plane,
    open_storage_control_plane_readonly,
)
from .dedup import DedupResult, build_dedup_plan, dedup_engine
from .executor import (
    STATUS_PLANNED,
    StorageAuthorizationError,
    StorageExecutionResult,
    StorageExecutor,
    record_removal,
    remove_certified_subtree,
    remove_durably_outcome,
    synchronization_for,
)
from .inventory import (
    StorageInventorySnapshot,
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
    safe_candidates,
)
from .maintenance import (
    campaign_state_maintenance_engine,
    plan_campaign_state_maintenance,
)
from .owners import P7_RELEASED_ATTEMPT_AUTHORIZER, SubtreeCoverage
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


def _format_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
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


def invocation_apply(args: Any) -> bool:
    """Whether *this* invocation explicitly authorized a mutation.

    Only an explicit ``--apply`` on the current command counts. ``--dry-run``
    and the absence of ``--apply`` are both non-mutating, and no configuration,
    environment value, stored plan, or prior audit record can substitute.
    """

    if bool(getattr(args, "dry_run", False)):
        return False
    return bool(getattr(args, "apply", False))


def _resolve(args: Any, cfg: Mapping[str, Any], *, action: str, tier: str = TIER_SAFE):
    """Normalize every configuration and CLI surface into one policy identity.

    The historical ``[cleanup]`` knobs are aliases, normalized here *before*
    policy hashing so an operator who set them keeps the behavior they
    configured and equivalent spellings still produce one identity.
    """

    overrides: dict[str, Any] = {}
    cleanup = _cleanup_section(cfg)
    storage_section = cfg.get("storage", {}) if isinstance(cfg, Mapping) else {}
    storage_section = storage_section if isinstance(storage_section, Mapping) else {}
    if (
        "maximum_event_records" in cleanup
        and "sqlite_compaction_maximum_events" not in storage_section
    ):
        # A historical alias fills in only where the current key is unset; it
        # never overrides an explicitly configured value.
        overrides["sqlite_compaction_maximum_events"] = cleanup["maximum_event_records"]
    # The campaign already owns a free-disk floor for execution. Storage does not
    # get a second, weaker one: a reserve is a floor, and the only safe
    # composition of two floors is the stricter of the two.
    execution_reserve = _execution_reserve_bytes(cfg)
    if execution_reserve is not None:
        configured = storage_section.get("safety_reserve_bytes")
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

    explicit_tier = getattr(args, "tier", None)
    policy = resolve_storage_policy(
        cfg,
        action=action,
        tier=str(explicit_tier) if explicit_tier is not None else tier,
        apply=invocation_apply(args),
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
    """Everything a storage command needs, resolved once through real owners.

    The control plane is *located*, not created. Only :meth:`consequential_plane`
    materializes it, and only an explicitly authorized invocation calls that.
    """

    def __init__(self, cfg: Mapping[str, Any], paths: Any, store: Any, boundary: Any) -> None:
        self.cfg = cfg
        self.paths = paths
        self.store = store
        self.boundary = boundary
        self.control_plane = open_storage_control_plane_readonly(paths)
        self.protected_inputs = getattr(boundary, "protected_inputs", ())

    def consequential_plane(self, policy: StoragePolicy) -> StorageControlPlane:
        """Materialize the control plane, once, for an authorized invocation.

        This happens *before* planning rather than between plan and apply: the
        control plane is itself an owner surface, so creating it after a plan
        was built would make that plan stale against state the same invocation
        had just created.
        """

        if not policy.apply:
            raise StorageAuthorizationError(
                "the storage control plane is only created by an explicitly "
                "authorized consequential invocation"
            )
        if not self.control_plane.exists:
            self.control_plane = open_storage_control_plane(self.paths)
        return self.control_plane

    def snapshot(
        self, policy: StoragePolicy | None = None, *, certify: bool = False
    ) -> StorageInventorySnapshot:
        """Inventory the owners.

        ``certify`` is on for planning and apply and off for reporting: exact
        subtree certification is what authorizes a mutation, and it is also what
        would make a report scale with campaign bulk.
        """

        return build_storage_inventory(
            self.cfg,
            self.paths,
            self.store,
            protected_inputs=self.protected_inputs,
            control_plane=self.control_plane,
            journal_retention_records=(
                policy.restore_journal_retention_records if policy is not None else 64
            ),
            certify=certify,
        )

    def executor(self, policy: StoragePolicy) -> StorageExecutor:
        return StorageExecutor(
            paths=self.paths,
            policy=policy,
            control_plane=self.consequential_plane(policy)
            if policy.apply
            else self.control_plane,
            boundary=self.boundary,
            resnapshot=lambda: self.snapshot(policy, certify=True),
        )


# ---------------------------------------------------------------------------
# report / deep audit
# ---------------------------------------------------------------------------


def storage_report(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    """Read-only owner-driven report, or an explicit deep physical audit."""

    deep = bool(getattr(args, "deep", False))
    policy = _resolve(args, context.cfg, action=ACTION_AUDIT if deep else ACTION_REPORT)
    top = int(getattr(args, "top", 20) or 20)
    if deep:
        return build_deep_storage_audit(
            Path(context.paths.workspace),
            protected_inputs=context.protected_inputs,
            top=top,
            entry_limit=policy.deep_audit_entry_limit,
        )
    return build_owner_storage_report(context.snapshot(policy), policy, top=top)


def print_storage_report(payload: Mapping[str, Any]) -> None:
    if payload.get("schema", "").startswith("mdstats.mlff-storage-deep-audit"):
        totals = payload["totals"]
        completeness = "complete" if payload["complete"] else "INCOMPLETE (entry limit reached)"
        print(f"Campaign storage deep physical audit (read-only, {completeness})", flush=True)
        print(
            "  totals: "
            f"logical={_format_bytes(int(totals['logical_bytes']))}; "
            f"allocated={_format_bytes(int(totals['allocated_physical_bytes']))}; "
            f"unique-inode={_format_bytes(int(totals['unique_inode_bytes']))}; "
            f"files={int(totals['file_count'])}; dirs={int(totals['directory_count'])}",
            flush=True,
        )
        for item in payload["refused_paths"][:5]:
            print(f"  ! not traversed: {item['path']}: {item['reason']}", flush=True)
        return
    print("Campaign storage report (owner-driven, read-only)", flush=True)
    print(f"  workspace: {payload['workspace']}", flush=True)
    print(f"  current generation: {payload['current_generation']}", flush=True)
    print(
        "  sizes below are bounded owner metadata, not exact totals; "
        "use `storage report --deep` for exact accounting",
        flush=True,
    )
    print("  owner families:", flush=True)
    for item in payload["owner_families"][:10]:
        print(
            f"    {_format_bytes(int(item['measured_bytes'])):>10}  "
            f"{item['owner']} [{item['artifact_class']}] "
            f"({item['artifact_count']} artifact(s), "
            f"{item['unmeasured_artifact_count']} unmeasured)",
            flush=True,
        )
    reclaim = payload["potential_reclaim_by_action"]
    for name in ("safe", "cache", "archive"):
        entry = reclaim[name]
        print(
            f"  potential {name}: {entry['eligible_count']} eligible "
            f"(>= {_format_bytes(int(entry['measured_eligible_bytes']))}); "
            f"{entry['refused_count']} refused by an owner",
            flush=True,
        )
    for item in payload["unresolved_owners"]:
        print(
            f"  ! owner {item['owner']} unresolved: {item['detail']} "
            "(its artifacts are retained)",
            flush=True,
        )
    for failure in payload["owner_graph_integrity_failures"]:
        print(f"  ! owner graph integrity: {failure}", flush=True)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------


def build_cleanup_plan(
    context: StorageCommandContext, policy: StoragePolicy
) -> tuple[StoragePlan, StorageInventorySnapshot]:
    """The exact cleanup intention, including planned owner maintenance."""

    snapshot = context.snapshot(policy, certify=True)
    actions = []
    refusals: list[dict[str, Any]] = []
    for decision in safe_candidates(snapshot):
        view = snapshot.view(decision.artifact_id)
        if decision.eligible:
            actions.append(
                planned_action(
                    action=ACTION_REMOVE,
                    path=decision.path,
                    artifact_id=decision.artifact_id,
                    reason=decision.reason,
                    owner_state_identity=view.state_identity if view else "",
                )
            )
        else:
            refusals.append({"path": str(decision.path), "reason": decision.reason})
    if policy.tier == TIER_CACHE:
        budget = int(policy.cache_eviction_maximum_bytes)
        spent = 0
        for decision in cache_candidates(snapshot):
            if not decision.eligible:
                refusals.append({"path": str(decision.path), "reason": decision.reason})
                continue
            view = snapshot.view(decision.artifact_id)
            action = planned_action(
                action=ACTION_EVICT_CACHE,
                path=decision.path,
                artifact_id=decision.artifact_id,
                reason=decision.reason,
                capability_cost=decision.capability_cost,
                owner_state_identity=view.state_identity if view else "",
            )
            # An owner artifact is evicted whole or retained whole: partially
            # deleting a cache tree to hit a byte cap would leave a torn cache
            # that no owner promised to be able to rebuild.
            if spent + int(action.size_bytes) > budget:
                refusals.append(
                    {
                        "path": str(decision.path),
                        "reason": (
                            "evicting this artifact would exceed the configured "
                            f"cache eviction cap of {budget} bytes; it is retained whole"
                        ),
                    }
                )
                continue
            spent += int(action.size_bytes)
            actions.append(action)

    maintenance = plan_campaign_state_maintenance(context.store, context.paths, policy)
    actions.extend(maintenance.actions)
    for reason in maintenance.reasons:
        refusals.append({"path": str(context.paths.state_db), "reason": reason})
    plan = build_storage_plan(snapshot, policy, actions, refusals=refusals)
    return plan, snapshot


def storage_cleanup(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    """Plan, show, and - only when authorized - apply safe/cache cleanup."""

    policy = _resolve(args, context.cfg, action=ACTION_CLEANUP, tier=TIER_SAFE)
    if policy.apply:
        context.consequential_plane(policy)
    plan, snapshot = build_cleanup_plan(context, policy.for_apply(apply=False))
    payload: dict[str, Any] = {"plan": plan.to_dict(), "execution": None}
    if not policy.apply:
        return payload

    apply_plan = build_storage_plan(
        snapshot,
        policy,
        plan.actions,
        refusals=plan.refusals,
        created_utc=plan.created_utc,
    )
    result = context.executor(policy).run(
        apply_plan,
        trigger=f"cli:cleanup:{policy.tier}",
        synchronization=synchronization_for(apply_plan, snapshot),
        engine=_cleanup_engine(context, policy),
    )
    payload["execution"] = result.to_dict()
    return payload


def _view_node_kind(view: Any) -> str:
    """The typed kind the P7 owner recorded for the view's own top-level node."""

    return "directory" if view.coverage is SubtreeCoverage.CLOSED else "file"


def _cleanup_engine(context: StorageCommandContext, policy: StoragePolicy):
    """Cleanup removals plus the separately planned owner maintenance."""

    maintenance = campaign_state_maintenance_engine(context.store, policy)

    def _engine(
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        from ..qualification.store import (
            open_released_attempt_session,
            remove_released_attempt_member,
        )

        executor = context.executor(policy)
        # One live authority per released attempt, not per member. The session
        # certifies state, proof, root binding and typed topology on the open
        # attempt descriptor and then every member of that attempt is mutated
        # through it, so the authority is verified once and never lapses between
        # verification and use.
        sessions: dict[str, Any] = {}
        try:
            for action in plan.actions:
                if action.action not in (ACTION_REMOVE, ACTION_EVICT_CACHE):
                    maintenance(action, snapshot, result)
                    continue
                authorized, detail = executor.authorize_path(action.path, snapshot)
                if not authorized:
                    result.refused.append({**action.to_dict(), "refusal": detail})
                    continue
                view = snapshot.view(action.artifact_id)
                if (
                    view is not None
                    and view.exact_authorizer == P7_RELEASED_ATTEMPT_AUTHORIZER
                ):
                    _apply_released_member(
                        result,
                        action,
                        view,
                        snapshot,
                        sessions,
                        open_released_attempt_session,
                        remove_released_attempt_member,
                    )
                    continue
                if view is not None and view.path == action.path and action.path.is_dir():
                    members, refusals = snapshot.authorized_members(view)
                    _record_or_reraise(
                        result,
                        action,
                        lambda members=members, refusals=refusals, view=view, action=action: (
                            remove_certified_subtree(
                                action.path,
                                members=members,
                                refusals=refusals,
                                root_identity=view.path_identity,
                                authority_identity=view.root_identity,
                            )
                        ),
                    )
                    continue
                _record_or_reraise(
                    result,
                    action,
                    lambda action=action: remove_durably_outcome(action.path),
                )
        finally:
            for session, _why in sessions.values():
                if session is not None:
                    session.close()

    return _engine


def _record_or_reraise(result, action, run) -> Any:
    """Record what one action did, even when it ends by raising.

    A helper that unlinked and then failed on durability knows something the
    executor's outer interruption handling never will: which action mutated and
    how many bytes are already gone. That evidence is recorded here, at the
    action boundary, before the failure is allowed to continue upward - so the
    partial audit describes the tree that now exists rather than reporting only
    that something went wrong.
    """

    from .outcome import PartialMutationError

    try:
        outcome = run()
    except PartialMutationError as exc:
        record_removal(result, action, exc.outcome)
        raise (exc.cause or exc) from exc
    record_removal(result, action, outcome)
    return outcome


def _apply_released_member(
    result,
    action,
    view,
    snapshot,
    sessions: dict[str, Any],
    open_session,
    remove_member,
) -> None:
    """One released-attempt action, under the attempt's live capability.

    A contradiction found at any member's mutation boundary is evidence about
    the whole attempt, not just that member: the session's certification is no
    longer a sufficient premise. So the capability is withdrawn and the rest of
    that attempt's planned members inherit an explicit no-change refusal without
    reaching the filesystem. Other attempts are unaffected - their authority was
    never in question.
    """

    from .outcome import PartialMutationError, refused_no_change

    attempt_root = view.path.parent
    key = str(attempt_root)
    if key not in sessions:
        sessions[key] = open_session(
            snapshot.campaign_paths,
            attempt_root,
            expected_root_identity=view.root_identity,
            expected_release_authority=view.state_identity,
        )
    session, why = sessions[key]
    if session is None:
        # A failed acquisition is the attempt's answer for this execution; it is
        # not re-attempted per member.
        record_removal(result, action, why)
        return
    if not session.live:
        record_removal(
            result,
            action,
            refused_no_change(
                "an earlier member of this attempt contradicted the authority this "
                f"action shares, so it was withheld: {session.invalidation_reason}"
            ),
        )
        return

    try:
        outcome = remove_member(
            session,
            view.path.name,
            expected_kind=_view_node_kind(view),
            planned_identity=action.filesystem_identity,
        )
    except PartialMutationError as exc:
        record_removal(result, action, exc.outcome)
        session.invalidate(exc.outcome.detail)
        sessions[key] = (session, exc.outcome)
        raise (exc.cause or exc) from exc
    record_removal(result, action, outcome)
    if outcome.refused:
        session.invalidate(outcome.detail)
        sessions[key] = (session, outcome)


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
            f"[{action['capability_cost']}] {action['action']} {action['path']}",
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
    print_audit_outcome(execution)


def print_audit_outcome(execution: Mapping[str, Any] | None) -> None:
    """Say plainly when a mutation stands but its durable evidence does not.

    The audit is diagnostic evidence, so its loss neither rolls back the
    operation nor invalidates any science - but an operator must not read an
    ordinary success line and conclude a durable record exists.
    """

    if not execution or execution.get("audit_published", True):
        return
    print(
        "[WARN] the operation itself is truthful, but its durable storage audit "
        f"record could not be published: {execution.get('audit_failure', 'unknown')}",
        flush=True,
    )
    print(
        "       this outcome is reported as "
        f"{execution['status']!r} rather than as a fully audited success",
        flush=True,
    )


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
        return _storage_restore(context, args)
    if subcommand == "reclaim":
        return _storage_reclaim(context, args)
    if subcommand != "create":
        raise StorageArchiveError(f"Unknown storage archive subcommand {subcommand!r}.")
    return _storage_archive_create(context, args)


def _storage_archive_create(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    policy = _resolve(args, context.cfg, action=ACTION_ARCHIVE)
    if policy.apply:
        context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    snapshot.require_planable()
    decisions = archive_candidates(snapshot)
    refused = [item for item in decisions if not item.eligible]
    selected, _ = select_archive_roots(snapshot, getattr(args, "root", None))
    reclaim_hot = not bool(getattr(args, "keep_hot", False))

    payload: dict[str, Any] = {
        "eligible": [
            {"artifact_id": item.artifact_id, "path": str(item.path), "reason": item.reason}
            for item in decisions
            if item.eligible
        ],
        "refused": [
            {"artifact_id": item.artifact_id, "path": str(item.path), "reason": item.reason}
            for item in refused
        ],
        "selected_roots": [str(item.path) for item in selected],
        "policy": policy.to_dict(),
        "resolved_policy_summary": policy.describe(),
        "archive": None,
        "execution": None,
    }
    if not selected:
        payload["detail"] = (
            "no owner declared any artifact cold-replaceable; nothing was archived"
        )
        return payload

    bundle = build_archive_plan_actions(
        workspace=Path(context.paths.workspace),
        snapshot=snapshot,
        selected=selected,
        boundary=context.boundary,
        policy=policy,
        reclaim_hot=reclaim_hot,
    )
    bundle.admission = archive_admission(
        Path(context.paths.internal), policy, bundle.members
    )
    plan = build_storage_plan(
        snapshot,
        policy,
        bundle.actions,
        refusals=bundle.refusals,
        admission=bundle.admission,
    )
    payload["plan"] = plan.to_dict()
    if not policy.apply:
        payload["detail"] = "dry-run: no archive was created and no hot byte was removed"
        return payload

    control_plane = context.consequential_plane(policy)
    result = context.executor(policy).run(
        plan,
        trigger="cli:archive:create",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_create_engine(
            workspace=Path(context.paths.workspace),
            control_plane=control_plane,
            policy=policy,
            boundary=context.boundary,
            bundle=bundle,
            reclaim_hot=reclaim_hot,
            failpoint=getattr(args, "failpoint", None) or (lambda _name: None),
        ),
    )
    payload["execution"] = result.to_dict()
    payload["archive"] = result.payload or None
    return payload


def _storage_reclaim(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    policy = _resolve(args, context.cfg, action=ACTION_ARCHIVE)
    if policy.apply:
        context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    snapshot.require_planable()
    actions, manifest, refusals = build_reclaim_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=context.control_plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=str(args.archive_identity),
    )
    plan = build_storage_plan(snapshot, policy, actions, refusals=refusals)
    payload: dict[str, Any] = {
        "reclaim": None,
        "plan": plan.to_dict(),
        "manifest_identity": str(manifest["archive_identity"]),
        "execution": None,
    }
    if not policy.apply:
        payload["detail"] = (
            "dry-run: the archive was authenticated and a current reclamation plan "
            "was computed; no hot byte was removed"
        )
        return payload
    control_plane = context.consequential_plane(policy)
    result = context.executor(policy).run(
        plan,
        trigger="cli:archive:reclaim",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_reclaim_engine(
            workspace=Path(context.paths.workspace),
            control_plane=control_plane,
            policy=policy,
            boundary=context.boundary,
            manifest=manifest,
            authority=bind_representation_authority(context.control_plane, manifest),
            failpoint=getattr(args, "failpoint", None) or (lambda _name: None),
        ),
    )
    payload["execution"] = result.to_dict()
    payload["reclaim"] = result.payload or None
    return payload


def _storage_restore(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    policy = _resolve(args, context.cfg, action=ACTION_RESTORE)
    if policy.apply:
        context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    snapshot.require_planable()
    actions, manifest, conflicts = build_restore_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=context.control_plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=str(args.archive_identity),
        boundary=context.boundary,
    )
    admission = restore_admission(Path(context.paths.workspace), policy, manifest)
    plan = build_storage_plan(
        snapshot, policy, actions, refusals=conflicts, admission=admission
    )
    journal = read_restore_journal(context.control_plane, str(args.archive_identity))
    payload: dict[str, Any] = {
        "restore": None,
        "plan": plan.to_dict(),
        "journal": journal,
        "conflicts": conflicts,
        "execution": None,
    }
    if conflicts:
        payload["detail"] = (
            "the restore plan reports destination conflicts; nothing was installed"
        )
        if not policy.apply:
            return payload
        raise StorageArchiveError(
            "restore refuses to install while destination conflicts remain: "
            + "; ".join(f"{item['path']}: {item['reason']}" for item in conflicts[:3])
        )
    if not policy.apply:
        payload["detail"] = (
            "dry-run: the archive was authenticated and the exact restore plan was "
            "computed; nothing was staged or installed"
        )
        return payload
    control_plane = context.consequential_plane(policy)
    result = context.executor(policy).run(
        plan,
        trigger="cli:archive:restore",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_restore_engine(
            workspace=Path(context.paths.workspace),
            control_plane=control_plane,
            policy=policy,
            boundary=context.boundary,
            manifest=manifest,
            authority=bind_representation_authority(context.control_plane, manifest),
            failpoint=getattr(args, "failpoint", None) or (lambda _name: None),
        ),
    )
    payload["execution"] = result.to_dict()
    payload["restore"] = result.payload or None
    return payload


def print_archive(payload: Mapping[str, Any]) -> None:
    print_audit_outcome(payload.get("execution"))
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
        _print_plan_summary(payload)
        receipt = payload["restore"]
        if receipt is None:
            print(f"  {payload.get('detail', 'nothing was installed')}", flush=True)
            for item in payload.get("conflicts", [])[:5]:
                print(f"  conflict: {item['path']}: {item['reason']}", flush=True)
            return
        print(
            f"  restored {receipt['restored_files']} file(s), reused "
            f"{receipt['already_present_files']}, created "
            f"{receipt['created_containers']} container(s); restored evidence "
            "remains historical",
            flush=True,
        )
        return
    if "reclaim" in payload:
        _print_plan_summary(payload)
        result = payload["reclaim"]
        if result is None:
            print(f"  {payload.get('detail', 'nothing was reclaimed')}", flush=True)
            return
        print(
            f"  reclaimed {len(result['reclaimed_hot_paths'])} hot file(s); "
            f"{len(result['remaining_hot_paths'])} still hot",
            flush=True,
        )
        return
    print("Cold archive creation", flush=True)
    for item in payload["eligible"]:
        print(f"  eligible: {item['path']}", flush=True)
    for item in payload["refused"][:5]:
        print(f"  retained hot: {item['path']}: {item['reason']}", flush=True)
    _print_plan_summary(payload)
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


def _print_plan_summary(payload: Mapping[str, Any]) -> None:
    plan = payload.get("plan")
    if not plan:
        return
    print(
        f"  plan: {plan['policy_summary']}; actions={plan['action_count']}; "
        f"refusals={len(plan['refusals'])}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# deduplicate
# ---------------------------------------------------------------------------


def storage_deduplicate(context: StorageCommandContext, args: Any) -> dict[str, Any]:
    policy = _resolve(args, context.cfg, action=ACTION_DEDUPLICATE)
    if policy.apply:
        context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    if policy.apply:
        snapshot.require_planable()
    actions, groups, excluded = build_dedup_plan(snapshot, policy)
    plan = build_storage_plan(
        snapshot,
        policy,
        actions,
        refusals=[{"path": "", "reason": note} for note in excluded],
    )
    payload: dict[str, Any] = {
        **DedupResult(
            applied=False,
            groups=groups,
            excluded=excluded,
            realization=policy.dedup_realization,
        ).to_dict(),
        "plan": plan.to_dict(),
        "execution": None,
    }
    if not policy.apply:
        return payload
    result = context.executor(policy).run(
        plan,
        trigger="cli:deduplicate",
        synchronization=synchronization_for(plan, snapshot),
        engine=dedup_engine(
            boundary=context.boundary,
            control_plane=context.consequential_plane(policy),
            groups=groups,
            excluded=excluded,
            failpoint=getattr(args, "failpoint", None) or (lambda _name: None),
        ),
    )
    payload["execution"] = result.to_dict()
    if result.payload:
        payload.update(result.payload)
    return payload


def print_dedup(payload: Mapping[str, Any]) -> None:
    print_audit_outcome(payload.get("execution"))
    print(
        f"Immutable deduplication ({payload['realization']}, no persistent content "
        f"store): {payload['group_count']} group(s)",
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
    "invocation_apply",
    "print_archive",
    "print_audit_outcome",
    "print_cleanup",
    "print_dedup",
    "print_storage_report",
    "storage_archive",
    "storage_cleanup",
    "storage_deduplicate",
    "storage_report",
]
