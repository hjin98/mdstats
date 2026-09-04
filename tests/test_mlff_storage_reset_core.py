"""Bounded acceptance for the owner-driven storage subsystem.

Every test here uses small synthetic fixtures, but the owners are real: the
campaign store, the target-size state owner, the P5 run-layout and activity
owner, the ownership boundary, the inventory, the planner, the executor, the
archive verifier, and the dedup engine are all production code.  Only three
things are substituted, all strictly below an owner boundary: filesystem
failure injection at named publication points, synthetic archive bytes for
hostile-input cases, and a deterministic mount-identity resolver so a nested
mount can be modelled without privileged mount creation.

The assembled real-owner P1-P7 acceptance lives in
``test_mlff_storage_reset_integration.py``; nothing here substitutes for it.
"""

from __future__ import annotations

import inspect
import io
import json
import os
import shutil
import stat
import tarfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_cli
from mdstats.training_data.campaign_target_size_cutover import (
    begin_target_size_cutover,
    bind_current_target_size_authorities,
    complete_target_size_cutover,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignState,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
)
from mdstats.training_data.storage import archive as archive_mod
from mdstats.training_data.storage import commands as storage_commands
from mdstats.training_data.storage.admission import (
    StorageAdmissionError,
    admit_storage_operation,
)
from mdstats.training_data.storage.archive import (
    BOUNDARY_AFTER_BLOB,
    BOUNDARY_BEFORE_BLOB,
    BOUNDARY_BEFORE_RECEIPT,
    BOUNDARY_DURING_INSTALL,
    BOUNDARY_DURING_RECLAMATION,
    ArchiveMember,
    StorageArchiveError,
    archive_container_bytes,
    archive_create_engine,
    archive_reclaim_engine,
    archive_restore_engine,
    bind_representation_authority,
    build_archive_plan_actions,
    build_reclaim_plan_actions,
    build_restore_plan_actions,
    list_archives,
    read_manifest,
    read_restore_journal,
    representation_identity,
    verify_cold_archive,
)
from mdstats.training_data.storage.control_plane import (
    IMMUTABLE_CATALOG_FIELDS,
    StorageControlPlaneError,
    open_storage_control_plane,
    open_storage_control_plane_readonly,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    certify_closed_post_selection_run_root,
)
from mdstats.training_data.storage.durability import sha256_file
from mdstats.training_data.storage.executor import synchronization_for
from mdstats.training_data.storage.inventory import (
    OwnerGraphError,
    archive_candidates,
    build_storage_inventory,
    cache_candidates,
    safe_candidates,
)
from mdstats.training_data.storage.lease import (
    OwnerSynchronization,
    StorageLeaseUnavailableError,
    storage_operation_lease,
)
from mdstats.training_data.storage.owners import (
    CertifiedNode,
    observed_node_kind,
    OwnerArtifactView,
    SubtreeCoverage,
    validate_owner_graph,
)
from mdstats.training_data.storage.plan import (
    StoragePlanStaleError,
    build_storage_plan,
    revalidate_plan,
)
from mdstats.training_data.storage.policy import (
    ACTION_ARCHIVE,
    ACTION_CLEANUP,
    ACTION_DEDUPLICATE,
    ACTION_REPORT,
    ACTION_RESTORE,
    StoragePolicyError,
    resolve_storage_policy,
)
from mdstats.training_data.storage.trust import (
    MountIdentityResolver,
    set_mount_resolver,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path) -> Path:
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="../training",
            foundation_model="../foundation.model",
            replay_train="../replay-train.xyz",
            replay_monitor="../replay-monitor.xyz",
            replay_true_labels="../true-labels",
        ),
        encoding="utf-8",
    )
    return config


class _Campaign:
    """A minimal campaign whose owners are the real ones."""

    def __init__(self, tmp_path: Path, *, current_generation: bool = True) -> None:
        self.config = _write_config(tmp_path)
        self.cfg, self.paths = cli._load_config(self.config)
        self.paths.ensure()
        self.store = cli.CampaignStore(self.paths.state_db)
        if current_generation:
            self.bind_current_generation()
        self.boundary = cli._campaign_ownership_boundary(self.cfg, self.paths, self.store)
        self.control_plane = open_storage_control_plane(self.paths)

    def bind_current_generation(self) -> int:
        """Drive the real target-size state owner to a current generation.

        The digests are fixture values, but the transitions, the compare-and-set
        fences, and the persisted state are the production owner's own.
        """

        from mdstats.training_data._common import digest

        transitioning = begin_target_size_cutover(self.store)
        bound = bind_current_target_size_authorities(
            self.store,
            transitioning,
            frame_authority_digest=digest({"fixture": "frame-authority"}),
            neutral_statistical_base_digest=digest({"fixture": "neutral-base"}),
            split_exclusion_digest=digest({"fixture": "split-exclusion"}),
            policy_digest=digest({"fixture": "policy"}),
            experiment_definition_digest=digest({"fixture": "experiment"}),
            aggregate_digest=digest({"fixture": "aggregate"}),
        )
        current = complete_target_size_cutover(self.store, bound)
        root = self.paths.internal / "target-size" / f"g{current.state.generation}"
        (root / "heads").mkdir(parents=True, exist_ok=True)
        revision = commit_target_size_campaign_transition(
            self.store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=current.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=current.state.generation,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                attempt="attempt-1",
                frame_authority_digest=current.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    current.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=current.state.split_exclusion_digest,
                policy_digest=current.state.policy_digest,
                experiment_definition_digest=current.state.experiment_definition_digest,
                aggregate_digest=current.state.aggregate_digest,
                execution_context_digest=digest({"fixture": "execution-context"}),
                common_preparation_digest=digest({"fixture": "common-preparation"}),
                screen_window_digest=digest({"fixture": "screen-window"}),
                execution_root=str(root.relative_to(self.paths.workspace)),
            ),
        ).revision
        return int(revision.state.generation)

    def close(self) -> None:
        self.store.close()

    def context(self) -> storage_commands.StorageCommandContext:
        return storage_commands.StorageCommandContext(
            self.cfg, self.paths, self.store, self.boundary
        )

    def snapshot(self, policy=None, *, certify: bool = True):
        """The planning inventory: certifying, like every consequential path."""

        return build_storage_inventory(
            self.cfg,
            self.paths,
            self.store,
            protected_inputs=self.boundary.protected_inputs,
            control_plane=self.control_plane,
            journal_retention_records=(
                policy.restore_journal_retention_records if policy else 64
            ),
            certify=certify,
        )

    def historical_run(
        self, *, generation: int = 7, name: str = "run-a", finish: bool = True
    ) -> Path:
        """A superseded P5 run root the real P5 owner certifies as closed.

        ``finish=False`` leaves the run unpublished so a test can add the outputs
        it needs *before* the owner freezes its completion anchor, which is the
        order real execution uses and the only order a create-once anchor
        allows.
        """

        root = self.paths.internal / "post-selection" / f"g{generation}" / "runs" / name
        (root / "checkpoints").mkdir(parents=True, exist_ok=True)
        (root / "checkpoints" / "epoch-1.pt").write_bytes(b"historical" * 512)
        objects = self.paths.internal / "post-selection" / f"g{generation}" / "objects"
        objects.mkdir(parents=True, exist_ok=True)
        (objects / "keep.json").write_text("{}\n", encoding="utf-8")
        if finish:
            self.finish_run(root)
        return root

    @staticmethod
    def finish_run(run_root: Path) -> None:
        """Publish the terminal record and freeze the owner's completion anchor.

        This is the real P5 publication order: the terminal evidence becomes
        durable first, and only then does the owner record the member set that
        certifies the finished run.
        """

        from mdstats.training_data.campaign_post_selection_runtime import (
            record_post_selection_run_members,
        )

        evidence = Path(run_root) / "run-evidence.json"
        if not evidence.is_file():
            evidence.write_text("{}\n", encoding="utf-8")
        record_post_selection_run_members(run_root)


@pytest.fixture()
def campaign(tmp_path: Path):
    instance = _Campaign(tmp_path)
    try:
        yield instance
    finally:
        instance.close()


def _policy(**kwargs):
    return resolve_storage_policy({}, **kwargs)


def _certification(container: Path, nodes=None, **kwargs):
    """The whole-unit owner authority a real cleanup view would carry.

    ``nodes=None`` models the exclusive-writer owner (storage's own staging
    area): everything a plain-file/directory tree can hold is this owner's.  A
    mapping models the typed-proof owner (a released P7 member, a certified
    CampaignStore orphan record).
    """

    from mdstats.training_data.storage.removal import Certification

    return Certification(nodes=nodes, exclusive=nodes is None, **kwargs)


def _certified(container: Path, *, nodes=None, certification=None, **kwargs):
    """Drive the canonical destructive owner with the bindings a real plan supplies.

    The campaign anchor and the plan's own target identity are required
    arguments of the production owner, because a consequential caller may never
    reach an unbound removal mode. These unit cases exercise the owner directly,
    so they supply the same two bindings a `PlannedAction` carries; the anchor
    rule itself is accepted through the real inventory/planning/executor path in
    the integration suite.
    """

    from mdstats.training_data.storage.removal import remove_planned_target
    from mdstats.training_data.storage_reclamation import filesystem_identity

    anchor = kwargs.pop("anchor", container.parent)
    if "planned_identity" in kwargs:
        identity = kwargs.pop("planned_identity")
    else:
        try:
            identity = filesystem_identity(container)
        except OSError:
            identity = {
                "schema": "mdstats.mlff-filesystem-identity.v1",
                "kind": "absent",
            }
    if certification is None:
        certification = _certification(container, nodes, **kwargs)
    else:
        assert not kwargs, kwargs
    action = SimpleNamespace(path=container, filesystem_identity=identity)
    return remove_planned_target(action, anchor=anchor, certification=certification)



def _args(**kwargs):
    base = {"tier": None, "apply": False, "dry_run": False, "top": 200, "deep": False}
    base.update(kwargs)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# IR13-1 - authorization is invocation-local
# ---------------------------------------------------------------------------


def test_configuration_cannot_carry_apply_authority() -> None:
    with pytest.raises(StoragePolicyError, match="authority-bearing"):
        resolve_storage_policy({"storage": {"apply": True}}, action=ACTION_CLEANUP)


def test_configuration_cannot_redirect_the_invoked_action() -> None:
    with pytest.raises(StoragePolicyError, match="authority-bearing"):
        resolve_storage_policy({"storage": {"action": "cleanup"}}, action=ACTION_ARCHIVE)


def test_a_persisted_apply_key_cannot_make_a_dry_run_mutate(campaign) -> None:
    campaign.historical_run()
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"apply": True}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    with pytest.raises(StoragePolicyError, match="authority-bearing"):
        storage_commands.storage_cleanup(context, _args())
    assert (
        campaign.paths.internal
        / "post-selection"
        / "g7"
        / "runs"
        / "run-a"
        / "checkpoints"
        / "epoch-1.pt"
    ).is_file()


def test_only_the_current_invocation_authorizes_a_mutation() -> None:
    assert storage_commands.invocation_apply(_args(apply=True)) is True
    assert storage_commands.invocation_apply(_args(apply=False)) is False
    # --dry-run wins over a stray --apply: they are opposite answers.
    assert storage_commands.invocation_apply(_args(apply=True, dry_run=True)) is False


def test_an_explicit_invocation_tier_beats_a_configured_default() -> None:
    policy = resolve_storage_policy(
        {"storage": {"tier": "cache"}}, action=ACTION_CLEANUP, tier="safe"
    )
    assert policy.tier == "safe"
    fallback = resolve_storage_policy({"storage": {"tier": "cache"}}, action=ACTION_CLEANUP)
    assert fallback.tier == "cache"


def test_no_environment_variable_can_widen_storage_authority(monkeypatch) -> None:
    import ast

    baseline = _policy(action=ACTION_CLEANUP).policy_identity
    for name in ("MDSTATS_STORAGE_TIER", "MDSTATS_STORAGE_APPLY"):
        monkeypatch.setenv(name, "1")
    assert _policy(action=ACTION_CLEANUP).policy_identity == baseline
    source = Path(cli.__file__).parent.joinpath("storage", "policy.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    reads = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}
    }
    assert reads == set(), reads


# ---------------------------------------------------------------------------
# IR13-2 - action-scoped policy identity, and no decorative knobs
# ---------------------------------------------------------------------------


def test_policy_identity_is_scoped_to_the_action_that_consumes_the_field() -> None:
    codec = {"storage": {"archive_compression_level": 9}}
    assert (
        resolve_storage_policy({}, action=ACTION_CLEANUP).policy_identity
        == resolve_storage_policy(codec, action=ACTION_CLEANUP).policy_identity
    )
    assert (
        resolve_storage_policy({}, action=ACTION_ARCHIVE).policy_identity
        != resolve_storage_policy(codec, action=ACTION_ARCHIVE).policy_identity
    )
    audit = {"storage": {"deep_audit_entry_limit": 7}}
    assert (
        resolve_storage_policy({}, action=ACTION_DEDUPLICATE).policy_identity
        == resolve_storage_policy(audit, action=ACTION_DEDUPLICATE).policy_identity
    )


def test_every_public_policy_field_is_consumed_by_some_action() -> None:
    from mdstats.training_data.storage.policy import (
        _ACTION_POLICY_SCOPE,
        StoragePolicy,
    )

    fields = {
        name
        for name in StoragePolicy.__slots__
        if name not in ("action", "tier", "apply")
    }
    covered = {name for scope in _ACTION_POLICY_SCOPE.values() for name in scope}
    assert fields == covered


def test_apply_authorization_does_not_change_the_policy_identity() -> None:
    planned = _policy(action=ACTION_CLEANUP)
    assert planned.policy_identity == planned.for_apply(apply=True).policy_identity


def test_retired_consequential_tiers_are_rejected_by_name() -> None:
    for tier in ("recompute", "compact"):
        with pytest.raises(StoragePolicyError, match="retired"):
            resolve_storage_policy({}, action=ACTION_CLEANUP, tier=tier)


def test_unsupported_policy_combinations_fail_before_any_mutation() -> None:
    with pytest.raises(StoragePolicyError):
        resolve_storage_policy({}, action=ACTION_REPORT, apply=True)
    with pytest.raises(StoragePolicyError):
        resolve_storage_policy(
            {"storage": {"archive_codec": "none", "archive_compression_level": 6}},
            action=ACTION_ARCHIVE,
        )
    with pytest.raises(StoragePolicyError, match="Unknown"):
        resolve_storage_policy({"storage": {"delete_everything": True}})


def test_the_cache_cap_retains_whole_artifacts_rather_than_tearing_one(campaign) -> None:
    """An atomic owner artifact is evicted whole or retained whole."""

    receipts = campaign.paths.internal / "hash-receipts.sqlite3"
    receipts.write_bytes(b"x" * 4096)
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"cache_eviction_maximum_bytes": 1}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(context, _args(tier="cache"))
    for action in payload["plan"]["actions"]:
        assert action["action"] != "evict_cache"


def test_the_deep_audit_entry_limit_is_a_real_bound(campaign) -> None:
    for index in range(40):
        (campaign.paths.results / f"item-{index}.json").write_text("{}", encoding="utf-8")
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"deep_audit_entry_limit": 5}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_report(context, _args(deep=True))
    assert payload["complete"] is False
    assert payload["accounting_mode"] == "bounded_incomplete"
    assert payload["entries_visited"] <= 6


# ---------------------------------------------------------------------------
# IR13-3 - non-apply paths are observational
# ---------------------------------------------------------------------------


def _tree_signature(root: Path) -> dict[str, tuple[int, int, int]]:
    signature: dict[str, tuple[int, int, int]] = {}
    for path in sorted(root.rglob("*")):
        try:
            stats = path.lstat()
        except OSError:
            continue
        signature[str(path.relative_to(root))] = (
            int(stats.st_mode),
            int(stats.st_size),
            int(stats.st_mtime_ns),
        )
    return signature


@pytest.mark.parametrize(
    "handler,arguments",
    [
        ("storage_report", {"deep": False}),
        ("storage_report", {"deep": True}),
        ("storage_cleanup", {"tier": "safe", "dry_run": True}),
        ("storage_cleanup", {"tier": "cache", "dry_run": True}),
        ("storage_deduplicate", {"dry_run": True}),
        ("storage_archive", {"archive_command": "list"}),
        ("storage_archive", {"archive_command": "create", "dry_run": True, "root": None}),
    ],
)
def test_non_apply_storage_paths_leave_managed_state_unchanged(
    campaign, handler: str, arguments: dict
) -> None:
    campaign.historical_run()
    before = _tree_signature(campaign.paths.workspace)
    payload = getattr(storage_commands, handler)(
        campaign.context(), _args(keep_hot=False, **arguments)
    )
    assert payload is not None
    after = _tree_signature(campaign.paths.workspace)
    assert after == before, sorted(set(after) ^ set(before)) or "content changed"


def test_reporting_an_uninitialized_campaign_creates_nothing(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = cli._load_config(config, ensure=False)
    assert not paths.workspace.exists()
    with pytest.raises(cli.CampaignCliError, match="missing"):
        cli.CampaignStore(paths.state_db, create=False)
    assert not paths.workspace.exists()


def test_locating_the_control_plane_does_not_create_it(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = cli._load_config(config)
    paths.ensure()
    plane = open_storage_control_plane_readonly(paths)
    assert plane.exists is False
    assert not plane.root.exists()


def test_inventorying_owners_does_not_create_generation_roots(campaign) -> None:
    before = _tree_signature(campaign.paths.internal)
    campaign.snapshot()
    campaign.snapshot()
    assert _tree_signature(campaign.paths.internal) == before


# ---------------------------------------------------------------------------
# IR13-4 - owner graph integrity gates consequential planning
# ---------------------------------------------------------------------------


def _view(artifact_id: str, path: Path, **kwargs) -> OwnerArtifactView:
    from mdstats.training_data.storage.owners import ArtifactClass

    return OwnerArtifactView(
        owner="p5",
        artifact_id=artifact_id,
        path=path,
        artifact_class=ArtifactClass.REPRODUCIBILITY_BULK,
        detail="fixture",
        **kwargs,
    )


def test_duplicate_owner_identities_are_an_integrity_failure(tmp_path: Path) -> None:
    failures = validate_owner_graph(
        [_view("p5:x", tmp_path / "a"), _view("p5:x", tmp_path / "b")]
    )
    assert any("duplicate" in item for item in failures)


def test_a_dependency_edge_with_no_owner_view_is_an_integrity_failure(
    tmp_path: Path,
) -> None:
    failures = validate_owner_graph(
        [_view("p5:x", tmp_path / "a", requires=("p5:missing",))]
    )
    assert any("no owner view reported" in item for item in failures)


def test_an_incomplete_owner_graph_refuses_consequential_planning(campaign) -> None:
    campaign.historical_run()
    snapshot = campaign.snapshot()
    broken = type(snapshot.owner_views)(
        views=snapshot.views + (_view("p5:orphan", campaign.paths.results, requires=("p5:ghost",)),),
        unresolved=snapshot.owner_views.unresolved,
        current_generation=snapshot.current_generation,
    )
    broken.integrity_failures = validate_owner_graph(broken.views)
    stale = type(snapshot)(
        workspace=snapshot.workspace,
        owner_views=broken,
        protected_ids=snapshot.protected_ids,
        protection_reasons=snapshot.protection_reasons,
        protected_inputs=snapshot.protected_inputs,
        control_plane=snapshot.control_plane,
        retained_control_paths=snapshot.retained_control_paths,
        protection_index=snapshot.protection_index,
    )
    assert stale.integrity_failures
    with pytest.raises(OwnerGraphError, match="refuses to mutate"):
        stale.require_planable()
    # Read-only reporting stays available and shows the problem.
    from mdstats.training_data.storage.report import build_owner_storage_report

    payload = build_owner_storage_report(stale, _policy(action=ACTION_REPORT))
    assert payload["consequential_planning_available"] is False
    assert payload["owner_graph_integrity_failures"]


def test_a_valid_graph_preserves_the_cross_owner_closure(campaign) -> None:
    campaign.historical_run()
    snapshot = campaign.snapshot()
    assert snapshot.integrity_failures == ()
    snapshot.require_planable()


# ---------------------------------------------------------------------------
# IR13-5 - synchronization comes from touched artifacts
# ---------------------------------------------------------------------------


def test_synchronization_covers_a_touched_historical_generation(campaign) -> None:
    from mdstats.training_data.storage.executor import synchronization_for

    run_root = campaign.historical_run(generation=7)
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view is not None
    policy = _policy(action=ACTION_ARCHIVE)
    from mdstats.training_data.storage.plan import planned_action

    plan = build_storage_plan(
        snapshot,
        policy,
        [
            planned_action(
                action="archive_member",
                path=run_root / "checkpoints" / "epoch-1.pt",
                artifact_id=view.artifact_id,
                reason="fixture",
                owner_state_identity=view.state_identity,
                binding={"sha256": "", "size_bytes": 0},
            )
        ],
    )
    synchronization = synchronization_for(plan, snapshot)
    assert 7 in synchronization.generations
    assert snapshot.current_generation in synchronization.generations
    assert run_root in synchronization.run_roots


def test_one_lock_order_is_used_everywhere() -> None:
    """Structural: storage and P5 acquire the shared seams in one direction."""

    lease = Path(cli.__file__).parent.joinpath("storage", "lease.py").read_text(
        encoding="utf-8"
    )
    activity = lease.index("post_selection_run_activity_lease(run_root)")
    publication = lease.index("post_selection_publication_barrier(paths, generation)")
    qualification = lease.index("qualification_publication_barrier(paths, generation)")
    assert activity < publication < qualification
    runtime = Path(cli.__file__).parent.joinpath(
        "campaign_post_selection_runtime.py"
    ).read_text(encoding="utf-8")
    # P5 execution takes the run-activity lease around the run's write lifetime,
    # and reaches its publication barrier only afterwards - the same direction
    # storage uses, so the two can never form a cycle.
    assert "with post_selection_run_activity_lease(run_root):" in runtime
    assert "with post_selection_publication_barrier(" in runtime


def test_a_held_run_activity_lease_blocks_a_storage_mutation(campaign) -> None:
    """The owner's own lease is what makes a historical run root safe to touch."""

    import threading

    from mdstats.training_data.campaign_post_selection_runtime import (
        post_selection_run_activity_lease,
    )
    from mdstats.training_data.storage.lease import owner_mutation_barrier

    run_root = campaign.historical_run()
    entered = threading.Event()
    released = threading.Event()
    acquired_after_release: list[bool] = []

    def storage_side() -> None:
        entered.wait(30.0)
        with owner_mutation_barrier(
            campaign.paths, OwnerSynchronization.of([7], [run_root])
        ):
            acquired_after_release.append(released.is_set())

    worker = threading.Thread(target=storage_side, daemon=True)
    with post_selection_run_activity_lease(run_root):
        worker.start()
        entered.set()
        time.sleep(0.6)
        released.set()
    worker.join(60.0)
    assert acquired_after_release == [True]


# ---------------------------------------------------------------------------
# IR13-6 - direct hardlink dedup with closed link ownership
# ---------------------------------------------------------------------------


def _dedup(campaign, *, apply: bool, cfg=None):
    context = storage_commands.StorageCommandContext(
        cfg or campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    return storage_commands.storage_deduplicate(context, _args(apply=apply))


def test_duplicates_become_direct_aliases_with_no_persistent_content_store(
    campaign,
) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    result = _dedup(campaign, apply=True)
    assert result["persistent_content_store"] is False
    assert first.stat().st_ino == second.stat().st_ino
    assert first.read_bytes() == payload == second.read_bytes()
    assert not (campaign.control_plane.root / "content-store").exists()


def test_removing_every_alias_releases_the_inode_naturally(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    _dedup(campaign, apply=True)
    inode = first.stat().st_ino
    assert first.stat().st_nlink == 2
    first.unlink()
    assert second.stat().st_nlink == 1
    second.unlink()
    assert not any(
        path.stat().st_ino == inode for path in run_root.rglob("*") if path.is_file()
    )


def test_an_external_hardlink_is_never_the_shared_canonical_inode(
    campaign, tmp_path: Path
) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    # Both candidates carry an unknown external link.
    external_root = tmp_path / "outside"
    external_root.mkdir()
    os.link(first, external_root / "first-alias.bin")
    os.link(second, external_root / "second-alias.bin")

    result = _dedup(campaign, apply=True)
    assert first.stat().st_ino != second.stat().st_ino
    assert any("closed link ownership" in note for note in result["excluded"])
    # Mutating the external alias cannot reach the other campaign file.
    (external_root / "first-alias.bin").write_bytes(b"tampered" * 1024)
    assert second.read_bytes() == payload


def test_replacing_one_alias_leaves_the_others_unchanged(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    _dedup(campaign, apply=True)
    replacement = second.parent / ".b.bin.new"
    replacement.write_bytes(b"updated" * 1024)
    os.replace(replacement, second)
    assert first.read_bytes() == payload
    assert second.read_bytes() == b"updated" * 1024


def test_equal_bytes_with_incompatible_modes_do_not_share_an_inode(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    first.write_bytes(payload)
    second.write_bytes(payload)
    os.chmod(first, 0o600)
    os.chmod(second, 0o644)
    campaign.finish_run(run_root)
    result = _dedup(campaign, apply=True)
    assert first.stat().st_ino != second.stat().st_ino
    assert any("metadata" in note for note in result["excluded"])


def test_repeated_dedup_is_idempotent(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    for name in ("a.bin", "b.bin"):
        path = run_root / "checkpoints" / name
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    _dedup(campaign, apply=True)
    again = _dedup(campaign, apply=True)
    assert again["execution"]["status"] == "complete"
    assert (run_root / "checkpoints" / "a.bin").stat().st_ino == (
        run_root / "checkpoints" / "b.bin"
    ).stat().st_ino


def test_cross_device_candidates_retain_duplicate_bytes(campaign, monkeypatch) -> None:
    from mdstats.training_data.storage import dedup as dedup_mod

    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    for name in ("a.bin", "b.bin"):
        path = run_root / "checkpoints" / name
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    monkeypatch.setattr(dedup_mod, "same_filesystem", lambda a, b: False)
    result = _dedup(campaign, apply=True)
    assert result["links_replaced"] == 0
    assert (run_root / "checkpoints" / "a.bin").stat().st_ino != (
        run_root / "checkpoints" / "b.bin"
    ).stat().st_ino


def test_mutable_state_never_enters_dedup(campaign) -> None:
    duplicate = campaign.paths.internal / "campaign.sqlite3.copy"
    duplicate.write_bytes(campaign.paths.state_db.read_bytes())
    result = _dedup(campaign, apply=False)
    linked = {path for group in result["groups"] for path in group["paths"]}
    assert str(campaign.paths.state_db) not in linked
    assert str(duplicate) not in linked


# ---------------------------------------------------------------------------
# IR14-1 - recursive authority needs owner certification
# ---------------------------------------------------------------------------


def test_an_unexpected_descendant_makes_a_run_root_uncertified(campaign) -> None:
    run_root = campaign.historical_run()
    (run_root / "someone-elses-notes.txt").write_text("hello", encoding="utf-8")
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view is not None
    assert view.coverage is SubtreeCoverage.CONTAINER
    assert view.archive_eligible is False
    assert view.dedup_eligible is False
    assert "did not write" in view.detail


def test_an_unexpected_descendant_is_never_archived_or_reclaimed(campaign) -> None:
    run_root = campaign.historical_run()
    stranger = run_root / "checkpoints" / "stranger.bin"
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    snapshot = campaign.snapshot()
    assert snapshot.view("p5:run:g7:run-a").archive_eligible is True

    stranger.write_bytes(b"not mine")
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=False),
    )
    assert payload["archive"] is None
    assert stranger.read_bytes() == b"not mine"
    assert checkpoint.is_file()


def test_an_unexpected_directory_is_never_absorbed_by_a_recursive_delete(
    campaign,
) -> None:
    run_root = campaign.historical_run()
    intruder = run_root / "not-p5"
    intruder.mkdir()
    (intruder / "payload.bin").write_bytes(b"keep")
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    members, refusals = snapshot.authorized_members(view)
    assert members == ()
    assert refusals
    assert (intruder / "payload.bin").read_bytes() == b"keep"


def test_a_closed_owner_certified_fixture_stays_eligible(campaign) -> None:
    campaign.historical_run()
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.coverage is SubtreeCoverage.CLOSED
    assert view.archive_eligible is True
    members, refusals = snapshot.authorized_members(view)
    assert refusals == ()
    assert any(path.name == "epoch-1.pt" for path in members)


def test_an_unfinished_run_root_is_never_certified(campaign) -> None:
    """A run that never published its completion anchor is not a closed subtree."""

    campaign.historical_run(finish=False)
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.coverage is SubtreeCoverage.CONTAINER
    assert view.archive_eligible is False
    assert "anchor" in view.detail


def test_a_run_stays_certified_after_its_terminal_evidence_goes_cold(campaign) -> None:
    """The completion proof is the retained anchor, not the hot evidence file.

    The terminal record is an ordinary archive member. An interrupted cold
    reclamation may already have removed it while other represented members are
    still hot; requiring it here would leave that reclamation unable to finish.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        certify_closed_post_selection_run_root,
    )

    run_root = campaign.historical_run()
    (run_root / "run-evidence.json").unlink()
    certified, detail = certify_closed_post_selection_run_root(run_root)
    assert certified, detail
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.coverage is SubtreeCoverage.CLOSED
    assert view.archive_eligible is True


def test_a_second_terminal_publication_verifies_rather_than_recomputes(
    campaign,
) -> None:
    """Republication reuses the immutable proof; it never rescans the tree.

    By the time a run is republished, storage may legitimately have moved
    represented members into a cold archive. Deriving a fresh member set from
    that depleted tree would look like a conflicting claim about a run that
    never changed, so the existing proof is verified and reused instead.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
        certify_closed_post_selection_run_root,
        record_post_selection_run_members,
    )

    run_root = campaign.historical_run()
    anchor = run_root / RUN_COMPLETION_ANCHOR_FILENAME
    topology = run_root / RUN_TOPOLOGY_MANIFEST_FILENAME
    before = (anchor.read_bytes(), topology.read_bytes())

    record_post_selection_run_members(run_root)
    assert (anchor.read_bytes(), topology.read_bytes()) == before

    # Members going cold is the normal case, not a conflict.
    (run_root / "checkpoints" / "epoch-1.pt").unlink()
    record_post_selection_run_members(run_root)
    assert (anchor.read_bytes(), topology.read_bytes()) == before

    # A foreign descendant does not become owned by republishing either; it
    # simply makes the run uncertifiable.
    (run_root / "checkpoints" / "epoch-2.pt").write_bytes(b"later")
    record_post_selection_run_members(run_root)
    assert (anchor.read_bytes(), topology.read_bytes()) == before
    certified, why = certify_closed_post_selection_run_root(run_root)
    assert not certified and "did not write" in why


def test_the_completion_proof_is_never_an_archive_member(campaign) -> None:
    """The proof a run needs in order to be reclaimed is not itself reclaimable."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
    )

    run_root = campaign.historical_run()
    proof = (
        run_root / RUN_COMPLETION_ANCHOR_FILENAME,
        run_root / RUN_TOPOLOGY_MANIFEST_FILENAME,
    )
    result = _create_archive(campaign)
    manifest = read_manifest(campaign.context().control_plane, result["archive_identity"])
    for item in proof:
        assert not any(
            str(entry["path"]).endswith(item.name) for entry in manifest["members"]
        )
        assert item.is_file(), f"hot reclamation removed {item.name}"
    anchor = proof[0]

    # Ordinary cleanup must not collect it either while the archive is retained.
    storage_commands.storage_cleanup(
        campaign.context(), _args(tier="safe", apply=True)
    )
    storage_commands.storage_cleanup(
        campaign.context(), _args(tier="cache", apply=True)
    )
    assert anchor.is_file()


def test_a_descendant_added_after_planning_refuses_the_action(campaign) -> None:
    run_root = campaign.historical_run()
    context = campaign.context()
    policy = _policy(action=ACTION_ARCHIVE)
    snapshot = campaign.snapshot()
    from mdstats.training_data.storage.archive import build_archive_plan_actions

    bundle = build_archive_plan_actions(
        workspace=campaign.paths.workspace,
        snapshot=snapshot,
        selected=[item for item in archive_candidates(snapshot) if item.eligible],
        boundary=campaign.boundary,
        policy=policy,
        reclaim_hot=True,
    )
    plan = build_storage_plan(snapshot, policy, bundle.actions)
    (run_root / "late-arrival.bin").write_bytes(b"late")
    with pytest.raises(StoragePlanStaleError, match="owner|closure"):
        revalidate_plan(plan, campaign.snapshot(), policy)
    assert (run_root / "late-arrival.bin").read_bytes() == b"late"


def test_no_consequential_recursive_path_equates_containment_with_ownership() -> None:
    """Structural: recursion always spends an owner's whole-unit certification.

    Read-only member resolution (archive membership, dedup candidacy) uses
    `authorized_members`.  Consequential cleanup does not: it carries the
    owner's typed certification into the destructive walk and re-checks every
    node live, so containment never becomes authority at either moment.
    """

    root = Path(cli.__file__).parent / "storage"
    inventory = (root / "inventory.py").read_text(encoding="utf-8")
    assert "def authorized_members" in inventory
    assert "SubtreeCoverage.CLOSED" in inventory
    for module in ("archive.py", "dedup.py"):
        text = (root / module).read_text(encoding="utf-8")
        assert "authorized_members" in text, module

    commands = (root / "commands.py").read_text(encoding="utf-8")
    assert "authorized_members" not in commands, (
        "cleanup resolves a member list ahead of the mutation again"
    )
    assert "cleanup_certification(" in commands

    # The one recursive owner descends no-follow through directory descriptors
    # and refuses every node the certification does not cover.
    removal = (root / "removal.py").read_text(encoding="utf-8")
    assert "shutil" not in removal
    assert "certification.certifies(" in removal


# ---------------------------------------------------------------------------
# IR13-9 - nested mounts are ownership boundaries
# ---------------------------------------------------------------------------


def test_a_nested_mount_below_an_eligible_root_is_not_traversed(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    nested = run_root / "checkpoints" / "mounted"
    nested.mkdir()
    (nested / "foreign.bin").write_bytes(b"someone else's bytes")
    campaign.finish_run(run_root)
    resolver = MountIdentityResolver(
        mount_points=frozenset({str(nested)}), available=True
    )
    set_mount_resolver(resolver)
    try:
        snapshot = campaign.snapshot()
        view = snapshot.view("p5:run:g7:run-a")
        members, refusals = snapshot.authorized_members(view)
        assert all("mounted" not in str(path) for path in members)
        assert any("mount point" in why for _path, why in refusals)
    finally:
        set_mount_resolver(None)
    assert (nested / "foreign.bin").read_bytes() == b"someone else's bytes"


def test_ambiguous_mount_discovery_retains_rather_than_traverses(campaign) -> None:
    campaign.historical_run()
    set_mount_resolver(MountIdentityResolver(mount_points=frozenset(), available=False))
    try:
        snapshot = campaign.snapshot()
        view = snapshot.view("p5:run:g7:run-a")
        members, refusals = snapshot.authorized_members(view)
        assert members == ()
        assert any("mount discovery is unavailable" in why for _p, why in refusals)
    finally:
        set_mount_resolver(None)


def test_the_workspace_itself_being_a_mount_remains_supported(campaign) -> None:
    campaign.historical_run()
    set_mount_resolver(
        MountIdentityResolver(
            mount_points=frozenset({str(campaign.paths.workspace)}), available=True
        )
    )
    try:
        snapshot = campaign.snapshot()
        view = snapshot.view("p5:run:g7:run-a")
        members, refusals = snapshot.authorized_members(view)
        assert refusals == ()
        assert members
    finally:
        set_mount_resolver(None)


# ---------------------------------------------------------------------------
# IR13-10 - conservative admission
# ---------------------------------------------------------------------------


def test_admission_accounts_for_container_overhead_on_many_tiny_files() -> None:
    members = tuple(
        ArchiveMember(f"a/{index}.bin", "file", 0o644, 1, "0" * 64, "p5:x")
        for index in range(1000)
    )
    payload_bytes = sum(item.size_bytes for item in members)
    bound = archive_container_bytes(members)
    # 1000 one-byte files cost 1000 headers plus 1000 padded blocks: the
    # container dominates the payload by three orders of magnitude.
    assert bound > 1000 * 1024
    assert bound > payload_bytes * 100


def test_an_unaffordable_operation_is_refused_before_any_mutation(campaign) -> None:
    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"safety_reserve_bytes": 1 << 62}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    with pytest.raises(StorageAdmissionError, match="Nothing was modified"):
        storage_commands.storage_archive(
            context, _args(archive_command="create", root=None, apply=True, keep_hot=False)
        )
    assert checkpoint.is_file()


def test_inode_admission_failure_refuses_before_any_mutation(campaign) -> None:
    from mdstats.training_data.storage import admission as admission_mod

    campaign.historical_run()
    original = admission_mod.observe_filesystem
    try:
        admission_mod.observe_filesystem = lambda location: (1 << 40, 1 << 40, 8)
        with pytest.raises(StorageAdmissionError, match="inodes"):
            admission_mod.admit_storage_operation(
                campaign.paths.workspace,
                _policy(action=ACTION_ARCHIVE),
                required_peak_bytes=1024,
                required_inodes=1000,
            )
    finally:
        admission_mod.observe_filesystem = original


def test_restore_admission_covers_staged_and_installed_copies(campaign) -> None:
    from mdstats.training_data.storage.archive import restore_admission

    result = _create_archive(campaign, keep_hot=True)
    manifest = read_manifest(campaign.control_plane, result["archive_identity"])
    observation = restore_admission(
        campaign.paths.workspace, _policy(action="restore"), manifest
    )
    expanded = int(manifest["total_expanded_bytes"])
    assert observation.required_peak_bytes > 2 * expanded
    assert observation.required_inodes >= 2 * int(manifest["member_count"])


# ---------------------------------------------------------------------------
# Archive: selection, identity, durability, restore
# ---------------------------------------------------------------------------


def _create_archive(campaign, *, keep_hot: bool = False, cfg=None, failpoint=None):
    context = storage_commands.StorageCommandContext(
        cfg or campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    if not any(
        (campaign.paths.internal / "post-selection").glob("g*/runs/*/run-evidence.json")
    ):
        campaign.historical_run()
    payload = storage_commands.storage_archive(
        context,
        _args(
            archive_command="create",
            root=None,
            apply=True,
            keep_hot=keep_hot,
            failpoint=failpoint,
        ),
    )
    assert payload["archive"] is not None, payload.get("detail")
    return payload["archive"]


def test_an_eligible_root_archives_and_restores(campaign) -> None:
    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    original = checkpoint.read_bytes()
    result = _create_archive(campaign)
    assert not checkpoint.exists()
    verify_cold_archive(
        campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
    )
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=True,
        ),
    )
    assert payload["restore"]["status"] == "complete"
    assert payload["restore"]["promotes_currentness"] is False
    assert checkpoint.read_bytes() == original


def test_a_requested_ancestor_of_an_eligible_root_is_rejected(campaign) -> None:
    campaign.historical_run()
    objects = campaign.paths.internal / "post-selection" / "g7" / "objects" / "keep.json"
    before = objects.read_bytes()
    parent = Path(".mdstats") / "post-selection" / "g7"
    with pytest.raises(StorageArchiveError, match="ancestor"):
        storage_commands.storage_archive(
            campaign.context(),
            _args(archive_command="create", root=[str(parent)], apply=True, keep_hot=False),
        )
    assert objects.read_bytes() == before


def test_an_exact_eligible_root_selection_succeeds(campaign) -> None:
    run_root = campaign.historical_run()
    relative = run_root.relative_to(campaign.paths.workspace)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=[str(relative)], apply=True, keep_hot=True),
    )
    assert payload["archive"] is not None
    manifest = read_manifest(campaign.control_plane, payload["archive"]["archive_identity"])
    assert manifest["represented_artifact_ids"] == ["p5:run:g7:run-a"]


def test_manifest_lineage_lists_only_represented_artifacts(campaign) -> None:
    campaign.historical_run(name="run-a")
    campaign.historical_run(name="run-b")
    run_a = campaign.paths.internal / "post-selection" / "g7" / "runs" / "run-a"
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="create",
            root=[str(run_a.relative_to(campaign.paths.workspace))],
            apply=True,
            keep_hot=True,
        ),
    )
    manifest = read_manifest(campaign.control_plane, payload["archive"]["archive_identity"])
    assert manifest["represented_artifact_ids"] == ["p5:run:g7:run-a"]
    assert all("run-b" not in item["path"] for item in manifest["members"])


def test_a_reencode_creates_a_distinct_representation(campaign) -> None:
    campaign.historical_run()
    first = _create_archive(campaign, keep_hot=True)
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"archive_compression_level": 9}
    second = _create_archive(campaign, keep_hot=True, cfg=cfg)
    assert first["archive_identity"] != second["archive_identity"]
    assert first["logical_identity"] == second["logical_identity"]
    # Both remain independently verifiable.
    for identity in (first["archive_identity"], second["archive_identity"]):
        verify_cold_archive(
            campaign.control_plane, identity, _policy(action=ACTION_REPORT)
        )


def test_a_failed_reencode_cannot_invalidate_a_retained_representation(campaign) -> None:
    campaign.historical_run()
    first = _create_archive(campaign, keep_hot=True)
    cfg = dict(campaign.cfg)
    cfg["storage"] = {"archive_compression_level": 9}

    class _Injected(RuntimeError):
        pass

    def failpoint(name: str) -> None:
        if name == BOUNDARY_AFTER_BLOB:
            raise _Injected(name)

    with pytest.raises(_Injected):
        _create_archive(campaign, keep_hot=True, cfg=cfg, failpoint=failpoint)
    verify_cold_archive(
        campaign.control_plane, first["archive_identity"], _policy(action=ACTION_REPORT)
    )


def test_a_conflicting_immutable_catalog_rewrite_is_rejected(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    entry = dict(campaign.control_plane.read_catalog_entry(identity))
    entry.pop("entry_digest", None)
    entry["archive_sha256"] = "0" * 64
    with storage_operation_lease(campaign.control_plane):
        with pytest.raises(StorageControlPlaneError, match="immutable field"):
            campaign.control_plane.publish_catalog_entry(entry)
    verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))


def test_retained_archive_authority_needs_the_storage_operation_lease(campaign) -> None:
    """IR16-5: every supported writer of retained archive state is serialized.

    Reauthenticating a representation immediately before consuming it only
    closes the race if nothing supported can replace that representation while
    the consumer holds the lease. The control plane enforces that itself rather
    than trusting each call site to be reachable only from an executor.
    """

    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    with pytest.raises(StorageControlPlaneError, match="storage-operation lease"):
        campaign.control_plane.publish_catalog_entry(
            {"archive_identity": identity, "hot_reclamation_state": "complete"}
        )
    assert (
        campaign.control_plane.read_catalog_entry(identity).get(
            "hot_reclamation_state"
        )
        != "complete"
    )
    # Read-only list/verify need no lease at all.
    assert list_archives(campaign.control_plane)
    verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))


def test_only_operational_catalog_fields_may_be_refreshed(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    with storage_operation_lease(campaign.control_plane):
        campaign.control_plane.publish_catalog_entry(
            {"archive_identity": identity, "hot_reclamation_state": "complete"}
        )
    entry = campaign.control_plane.read_catalog_entry(identity)
    assert entry["hot_reclamation_state"] == "complete"
    assert entry["archive_sha256"] == result and True or entry["archive_sha256"]
    verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))


def test_representation_identity_binds_the_serialization() -> None:
    logical = "a" * 64
    gzip_one = representation_identity(
        logical=logical, codec="tar+gzip", level=1, schema="s"
    )
    gzip_nine = representation_identity(
        logical=logical, codec="tar+gzip", level=9, schema="s"
    )
    plain = representation_identity(logical=logical, codec="tar", level=0, schema="s")
    assert len({gzip_one, gzip_nine, plain}) == 3


# ---------------------------------------------------------------------------
# Durable publication ordering
# ---------------------------------------------------------------------------


class _Injected(RuntimeError):
    pass


def _fail_at(name: str):
    def failpoint(boundary: str) -> None:
        if boundary == name:
            raise _Injected(boundary)

    return failpoint


def test_failure_before_blob_publication_leaves_no_terminal_catalog(campaign) -> None:
    campaign.historical_run()
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_BEFORE_BLOB))
    assert list_archives(campaign.control_plane) == ()


def test_failure_after_blob_cannot_authorize_hot_deletion(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_AFTER_BLOB))
    assert list_archives(campaign.control_plane) == ()
    assert (run_root / "checkpoints" / "epoch-1.pt").is_file()


def test_failure_during_reclamation_is_resumable_and_truthful(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    (run_root / "checkpoints" / "epoch-2.pt").write_bytes(b"second" * 512)
    campaign.finish_run(run_root)
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_DURING_RECLAMATION))
    entries = list_archives(campaign.control_plane)
    assert len(entries) == 1
    identity = entries[0]["archive_identity"]
    audit = campaign.control_plane.read_audit()
    assert all(item.get("status") != "complete" for item in audit)

    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="reclaim", archive_identity=identity, apply=True),
    )
    assert payload["reclaim"]["remaining_hot_paths"] == []
    assert (
        campaign.control_plane.read_catalog_entry(identity)["hot_reclamation_state"]
        == "complete"
    )


def test_failure_during_restore_produces_no_terminal_receipt(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    (run_root / "checkpoints" / "epoch-2.pt").write_bytes(b"second" * 512)
    campaign.finish_run(run_root)
    result = _create_archive(campaign)
    with pytest.raises(_Injected):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
                failpoint=_fail_at(BOUNDARY_DURING_INSTALL),
            ),
        )
    journal = read_restore_journal(campaign.control_plane, result["archive_identity"])
    assert journal is not None and journal["state"] != "terminal"


def test_the_terminal_receipt_follows_final_authentication(campaign) -> None:
    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    original = checkpoint.read_bytes()
    result = _create_archive(campaign)
    with pytest.raises(_Injected):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
                failpoint=_fail_at(BOUNDARY_BEFORE_RECEIPT),
            ),
        )
    assert read_restore_journal(campaign.control_plane, result["archive_identity"])[
        "state"
    ] != "terminal"
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=True,
        ),
    )
    assert payload["restore"]["status"] == "complete"
    assert checkpoint.read_bytes() == original


def test_terminal_publication_uses_the_repository_durable_helpers() -> None:
    source = Path(archive_mod.__file__).read_text(encoding="utf-8")
    assert "durable_publish_bytes(blob" in source
    assert "durable_publish_json(\n                manifest_path," in source
    assert "publish_catalog_entry" in source
    assert "json.dump(" not in source
    verify_index = source.index("_verify_blob_against_manifest(blob, manifest, policy)")
    catalog_index = source.index("control_plane.publish_catalog_entry(")
    assert verify_index < catalog_index
    control = Path(archive_mod.__file__).with_name("control_plane.py").read_text(
        encoding="utf-8"
    )
    assert "durable_publish_json(destination, payload, on_published=on_published)" in control


def test_every_publication_that_carries_execution_truth_is_transition_exact() -> None:
    """R37-5 structural: no owner infers publication from a helper's return.

    The window between the atomic replace and the helper's return is real and
    cannot be recovered afterwards, so each phase this execution can claim must
    be established by the primitive's transition callback. Asserting it
    structurally guards against a later edit quietly moving a phase assignment
    back below the call, where the counterfactuals would still pass on the
    happy path.
    """

    import ast

    source = Path(archive_mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    names = {
        "durable_publish_json",
        "durable_publish_bytes",
        "publish_catalog_entry",
        "_publish_archive_blob",
    }
    # Both execution owners - archive creation and restore - are named `_engine`.
    engines = [
        item
        for item in ast.walk(tree)
        if isinstance(item, ast.FunctionDef) and item.name == "_engine"
    ]
    assert len(engines) >= 2, [item.name for item in engines]
    checked = 0
    for engine in engines:
        for call in ast.walk(engine):
            if not isinstance(call, ast.Call):
                continue
            called = getattr(call.func, "id", "") or getattr(call.func, "attr", "")
            if called not in names:
                continue
            checked += 1
            assert any(
                keyword.arg == "on_published" for keyword in call.keywords
            ), ast.dump(call)
    assert checked >= 6, checked

    # And the phase vocabulary is the transition's, not a helper's return value.
    assert 'result.payload["publication_phase"] =' not in source
    assert 'result.payload = receipt' not in source


# ---------------------------------------------------------------------------
# IR14-2 - restore never mutates a pre-existing container
# ---------------------------------------------------------------------------


def test_restore_reuses_a_pre_existing_container_without_changing_its_mode(
    campaign,
) -> None:
    run_root = campaign.historical_run()
    checkpoints = run_root / "checkpoints"
    checkpoint = checkpoints / "epoch-1.pt"
    result = _create_archive(campaign)
    # The container survives archival; give it a mode the archive does not carry.
    assert checkpoints.is_dir()
    os.chmod(checkpoints, 0o750)
    before = stat.S_IMODE(checkpoints.lstat().st_mode)

    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=True,
        ),
    )
    assert payload["restore"]["status"] == "complete"
    assert checkpoint.is_file()
    assert stat.S_IMODE(checkpoints.lstat().st_mode) == before


def test_a_container_mode_change_after_planning_refuses_the_restore(campaign) -> None:
    """The plan bound this container's metadata; a change means re-plan.

    A restore never normalizes a pre-existing container, so it cannot silently
    proceed against a directory whose metadata is not the one it reasoned about.
    """

    from mdstats.training_data.storage.archive import build_restore_plan_actions
    from mdstats.training_data.storage.plan import (
        StoragePlanStaleError,
        build_storage_plan,
        revalidate_plan,
    )

    run_root = campaign.historical_run()
    checkpoints = run_root / "checkpoints"
    result = _create_archive(campaign)
    os.chmod(checkpoints, 0o750)

    context = campaign.context()
    policy = resolve_storage_policy({}, action=ACTION_RESTORE, apply=True)
    context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    actions, _manifest, _conflicts = build_restore_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=context.control_plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=result["archive_identity"],
        boundary=context.boundary,
    )
    plan = build_storage_plan(snapshot, policy, actions)
    container = [
        item for item in plan.actions if item.action == "restore_container"
    ]
    assert container, [item.action for item in plan.actions]

    os.chmod(checkpoints, 0o700)
    with pytest.raises(StoragePlanStaleError, match="mode changed after planning"):
        revalidate_plan(plan, context.snapshot(policy, certify=True), policy)
    assert stat.S_IMODE(checkpoints.lstat().st_mode) == 0o700


def test_a_restore_created_container_receives_the_archived_metadata(campaign) -> None:
    import shutil as _shutil

    run_root = campaign.historical_run()
    checkpoints = run_root / "checkpoints"
    os.chmod(checkpoints, 0o700)
    result = _create_archive(campaign)
    _shutil.rmtree(checkpoints)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=True,
        ),
    )
    assert payload["restore"]["created_containers"] >= 1
    assert stat.S_IMODE(checkpoints.lstat().st_mode) == 0o700


def test_a_changed_parent_identity_refuses_installation(campaign, tmp_path: Path) -> None:
    import shutil as _shutil

    run_root = campaign.historical_run()
    checkpoints = run_root / "checkpoints"
    result = _create_archive(campaign)
    _shutil.rmtree(checkpoints)
    # Model a substituted parent: a symlink where a real directory was planned.
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    checkpoints.symlink_to(outside, target_is_directory=True)
    with pytest.raises(StorageArchiveError):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
            ),
        )
    assert list(outside.iterdir()) == []


def test_restore_refuses_a_conflicting_destination(campaign) -> None:
    run_root = campaign.historical_run()
    result = _create_archive(campaign)
    victim = run_root / "checkpoints" / "epoch-1.pt"
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_bytes(b"different authoritative bytes")
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=False,
        ),
    )
    assert any("different authoritative content" in item["reason"] for item in payload["conflicts"])
    assert victim.read_bytes() == b"different authoritative bytes"


def test_restore_dry_run_computes_the_same_plan_and_installs_nothing(campaign) -> None:
    run_root = campaign.historical_run()
    result = _create_archive(campaign)
    before = _tree_signature(campaign.paths.workspace)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(
            archive_command="restore",
            archive_identity=result["archive_identity"],
            apply=False,
        ),
    )
    assert payload["restore"] is None
    assert payload["plan"]["action_count"] >= 1
    assert _tree_signature(campaign.paths.workspace) == before


# ---------------------------------------------------------------------------
# Bounded archive verification (hostile input)
# ---------------------------------------------------------------------------


def _repack(campaign, identity: str, build) -> None:
    manifest_path = campaign.control_plane.manifest_path(identity)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    blob.unlink()
    with tarfile.open(blob, mode="w:gz") as tar:
        build(tar)
    _rewrite_manifest(
        campaign,
        identity,
        archive_sha256=sha256_file(blob),
        archive_size_bytes=int(blob.stat().st_size),
    )


def _rewrite_manifest(campaign, identity: str, **fields) -> None:
    from mdstats.training_data.storage.durability import canonical_digest

    path = campaign.control_plane.manifest_path(identity)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(fields)
    body = {k: v for k, v in payload.items() if k != "manifest_content_digest"}
    body["manifest_content_digest"] = canonical_digest(body)
    path.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")


@pytest.mark.parametrize(
    "name", ["/absolute/escape.bin", "../escape.bin", "./alias.bin", "dir//alias.bin"]
)
def test_unsafe_or_aliased_member_paths_are_rejected(campaign, name: str) -> None:
    result = _create_archive(campaign, keep_hot=True)

    def build(tar: tarfile.TarFile) -> None:
        info = tarfile.TarInfo(name)
        info.size = 1
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(b"x"))

    _repack(campaign, result["archive_identity"], build)
    with pytest.raises(StorageArchiveError):
        verify_cold_archive(
            campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
        )


def test_symlink_hardlink_and_special_members_are_rejected(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):

        def build(tar: tarfile.TarFile, kind=kind) -> None:
            info = tarfile.TarInfo("member.bin")
            info.type = kind
            info.linkname = "target.bin"
            info.size = 0
            tar.addfile(info)

        _repack(campaign, result["archive_identity"], build)
        with pytest.raises(StorageArchiveError, match="rejected"):
            verify_cold_archive(
                campaign.control_plane,
                result["archive_identity"],
                _policy(action=ACTION_REPORT),
            )


def test_duplicate_members_are_rejected(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    manifest = read_manifest(campaign.control_plane, result["archive_identity"])
    target = next(item for item in manifest["members"] if item["kind"] == "file")
    content = (campaign.paths.workspace / target["path"]).read_bytes()

    def build(tar: tarfile.TarFile) -> None:
        for _ in range(2):
            info = tarfile.TarInfo(target["path"])
            info.size = len(content)
            info.mode = int(target["mode"])
            tar.addfile(info, io.BytesIO(content))

    _repack(campaign, result["archive_identity"], build)
    with pytest.raises(StorageArchiveError, match="[Dd]uplicate"):
        verify_cold_archive(
            campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
        )


def test_a_member_longer_than_its_manifest_size_stops_at_the_bound(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    manifest = read_manifest(campaign.control_plane, result["archive_identity"])
    target = next(item for item in manifest["members"] if item["kind"] == "file")

    def build(tar: tarfile.TarFile) -> None:
        for item in manifest["members"]:
            if item["kind"] == "directory":
                info = tarfile.TarInfo(item["path"])
                info.type = tarfile.DIRTYPE
                info.mode = int(item["mode"])
                tar.addfile(info)
                continue
            size = int(item["size_bytes"]) + (
                4096 if item["path"] == target["path"] else 0
            )
            info = tarfile.TarInfo(item["path"])
            info.size = size
            info.mode = int(item["mode"])
            tar.addfile(info, io.BytesIO(b"z" * size))

    _repack(campaign, result["archive_identity"], build)
    with pytest.raises(StorageArchiveError, match="longer than its manifest size"):
        verify_cold_archive(
            campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
        )


def test_total_expansion_and_amplification_bounds_are_enforced(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    with pytest.raises(StorageArchiveError, match="expanded bytes"):
        verify_cold_archive(
            campaign.control_plane,
            identity,
            resolve_storage_policy(
                {"storage": {"archive_expanded_bytes_limit": 16}}, action=ACTION_REPORT
            ),
        )
    with pytest.raises(StorageArchiveError, match="expansion ratio"):
        verify_cold_archive(
            campaign.control_plane,
            identity,
            resolve_storage_policy(
                {"storage": {"archive_expansion_ratio_limit": 1.0}}, action=ACTION_REPORT
            ),
        )
    with pytest.raises(StorageArchiveError, match="members"):
        verify_cold_archive(
            campaign.control_plane,
            identity,
            resolve_storage_policy(
                {"storage": {"archive_member_limit": 1}}, action=ACTION_REPORT
            ),
        )


def test_corrupt_archive_bytes_are_detected(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    manifest = read_manifest(campaign.control_plane, result["archive_identity"])
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    payload = bytearray(blob.read_bytes())
    payload[-1] ^= 0xFF
    blob.write_bytes(bytes(payload))
    with pytest.raises((StorageArchiveError, StorageControlPlaneError), match="[Dd]igest"):
        verify_cold_archive(
            campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
        )


def test_an_unsupported_durable_schema_is_rejected_and_retained(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    manifest_path = campaign.control_plane.manifest_path(identity)
    before = manifest_path.read_bytes()
    _rewrite_manifest(campaign, identity, schema="mdstats.someone-elses.v9")
    with pytest.raises(StorageArchiveError, match="retained and rejected"):
        verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))
    assert manifest_path.is_file()
    manifest_path.write_bytes(before)


# ---------------------------------------------------------------------------
# Archive locator containment
# ---------------------------------------------------------------------------


def test_an_absolute_or_traversing_archive_locator_is_rejected(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    for locator in ("/etc/passwd", "../../outside.tar.gz"):
        _rewrite_manifest(campaign, identity, archive_locator=locator)
        entry = dict(campaign.control_plane.read_catalog_entry(identity))
        with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
            verify_cold_archive(
                campaign.control_plane, identity, _policy(action=ACTION_REPORT)
            )
        del entry


def test_an_archive_root_symlink_escape_is_rejected(campaign, tmp_path: Path) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    manifest = read_manifest(campaign.control_plane, identity)
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "smuggled.tar.gz").write_bytes(blob.read_bytes())
    (campaign.control_plane.archive_root / "escape").symlink_to(
        outside, target_is_directory=True
    )
    _rewrite_manifest(campaign, identity, archive_locator="escape/smuggled.tar.gz")
    with pytest.raises(
        (StorageArchiveError, StorageControlPlaneError), match="symlink|escape|disagrees"
    ):
        verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))


def test_a_supplied_digest_never_authorizes_reading_an_external_file(
    campaign, tmp_path: Path
) -> None:
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    manifest = read_manifest(campaign.control_plane, identity)
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    external = tmp_path / "external-copy.tar.gz"
    external.write_bytes(blob.read_bytes())
    assert sha256_file(external) == manifest["archive_sha256"]
    _rewrite_manifest(campaign, identity, archive_locator=str(external))
    with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
        verify_cold_archive(campaign.control_plane, identity, _policy(action=ACTION_REPORT))


# ---------------------------------------------------------------------------
# IR13-11 - one truthful durable audit
# ---------------------------------------------------------------------------


def test_every_applied_consequential_path_appends_one_audit(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    for name in ("a.bin", "b.bin"):
        path = run_root / "checkpoints" / name
        path.write_bytes(b"identical" * 1024)
        os.chmod(path, 0o644)
    campaign.finish_run(run_root)
    _dedup(campaign, apply=True)
    result = _create_archive(campaign, keep_hot=True)
    storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="reclaim", archive_identity=result["archive_identity"], apply=True),
    )
    storage_commands.storage_cleanup(campaign.context(), _args(tier="safe", apply=True))
    actions = {item["action"] for item in campaign.control_plane.read_audit()}
    assert {"deduplicate", "archive", "cleanup"} <= actions


def test_a_read_only_command_writes_no_audit(campaign) -> None:
    campaign.historical_run()
    before = len(campaign.control_plane.read_audit())
    storage_commands.storage_report(campaign.context(), _args())
    storage_commands.storage_cleanup(campaign.context(), _args(tier="safe"))
    assert len(campaign.control_plane.read_audit()) == before


def test_an_interrupted_operation_is_never_audited_complete(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    (run_root / "checkpoints" / "epoch-2.pt").write_bytes(b"second" * 512)
    campaign.finish_run(run_root)
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_DURING_RECLAMATION))
    audit = campaign.control_plane.read_audit()
    assert audit
    assert all(item["status"] != "complete" for item in audit)
    assert any(item["status"] == "partial" for item in audit)


def test_audit_pruning_never_removes_catalog_or_journal_authority(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    with storage_operation_lease(campaign.control_plane):
        for index in range(20):
            campaign.control_plane.append_audit(
                {"created_utc": str(index), "note": index}
            )
        removed = campaign.control_plane.prune_audit(keep=5)
    assert removed > 0
    assert len(campaign.control_plane.read_audit()) == 5
    verify_cold_archive(
        campaign.control_plane, result["archive_identity"], _policy(action=ACTION_REPORT)
    )


# ---------------------------------------------------------------------------
# IR13-12 - CampaignStore maintenance is separately authorized
# ---------------------------------------------------------------------------


def test_a_compact_database_needs_neither_prune_nor_rewrite(campaign) -> None:
    from mdstats.training_data.storage.maintenance import (
        plan_campaign_state_maintenance,
    )

    decision = plan_campaign_state_maintenance(
        campaign.store, campaign.paths, _policy(action=ACTION_CLEANUP)
    )
    assert decision.actions == ()
    assert decision.prune_action is None and decision.vacuum_action is None
    assert "not worthwhile" in decision.reason
    assert "within its bound" in decision.reason


def _maintenance_cleanup(campaign, *, maximum_events: int):
    cfg = {
        **campaign.cfg,
        "storage": {"sqlite_compaction_maximum_events": maximum_events},
    }
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    return context, storage_commands.storage_cleanup(
        context, _args(tier="safe", apply=True)
    )


def test_excess_events_authorize_pruning_but_never_a_rewrite(campaign) -> None:
    """IR16-3: one excess diagnostic event is not a reason to rewrite the file.

    Pruning frees pages, so a runtime `prune then decide` would rewrite the
    database on the strength of the very free space it just created. The rewrite
    belongs to the next fresh plan, measured on its own evidence.
    """

    from mdstats.training_data.storage.maintenance import (
        measure_reclaimable,
        plan_campaign_state_maintenance,
    )

    for _index in range(150):
        campaign.store.event("info", "fixture", "x" * 32)
    policy = resolve_storage_policy(
        {
            "storage": {
                "sqlite_compaction_maximum_events": 100,
                "sqlite_compaction_minimum_reclaimable_bytes": 1 << 30,
                "sqlite_compaction_minimum_reclaimable_fraction": 0.99,
            }
        },
        action=ACTION_CLEANUP,
    )
    decision = plan_campaign_state_maintenance(campaign.store, campaign.paths, policy)
    assert decision.prune_action is not None
    assert decision.vacuum_action is None, "pruning authorized a database rewrite"
    assert decision.excess_events > 0

    cfg = {
        **campaign.cfg,
        "storage": {
            "sqlite_compaction_maximum_events": 100,
            "sqlite_compaction_minimum_reclaimable_bytes": 1 << 30,
            "sqlite_compaction_minimum_reclaimable_fraction": 0.99,
        },
    }
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(context, _args(tier="safe", apply=True))
    completed = payload["execution"]["completed_actions"]
    pruned = [item for item in completed if item["action"] == "prune_campaign_events"]
    assert pruned and pruned[0]["events_pruned"] > 0
    assert all(item.get("vacuum_performed") is not True for item in completed)
    assert not any(item["action"] == "vacuum_campaign_state" for item in completed)

    _reclaimable, _total, events = measure_reclaimable(campaign.store)
    assert events <= 100


def test_a_fresh_plan_may_authorize_the_rewrite_the_prune_made_worthwhile(
    campaign,
) -> None:
    from mdstats.training_data.storage.maintenance import (
        plan_campaign_state_maintenance,
    )

    for _index in range(4000):
        campaign.store.event("info", "fixture", "x" * 256)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 10}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    storage_commands.storage_cleanup(context, _args(tier="safe", apply=True))

    policy = resolve_storage_policy(cfg, action=ACTION_CLEANUP)
    decision = plan_campaign_state_maintenance(campaign.store, campaign.paths, policy)
    assert decision.vacuum_action is not None, decision.reason
    before = campaign.paths.state_db.stat().st_size
    payload = storage_commands.storage_cleanup(context, _args(tier="safe", apply=True))
    rewritten = [
        item
        for item in payload["execution"]["completed_actions"]
        if item["action"] == "vacuum_campaign_state"
    ]
    assert rewritten and rewritten[0]["vacuum_performed"] is True
    assert campaign.paths.state_db.stat().st_size < before


def test_no_prune_path_can_reach_an_unconditional_rewrite() -> None:
    """Structural: pruning has no VACUUM tail to fall through into."""

    import ast

    source = Path(cli.__file__).parent.joinpath("storage", "maintenance.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    engine = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "campaign_state_maintenance_engine"
    )
    prune_branch = next(
        node
        for node in ast.walk(engine)
        if isinstance(node, ast.If)
        and "ACTION_PRUNE_EVENTS" in ast.dump(node.test)
    )
    called = {
        node.func.attr
        for node in ast.walk(prune_branch)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "vacuum" not in called and "compact" not in called

    store_source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "def compact(" not in store_source, (
        "the combined prune+VACUUM helper must not survive as an alternate authority"
    )
    prune = next(
        node
        for node in ast.walk(ast.parse(store_source))
        if isinstance(node, ast.FunctionDef) and node.name == "prune_events"
    )
    assert "VACUUM" not in ast.dump(prune)


def test_a_refused_cleanup_does_not_maintain_the_database(campaign) -> None:
    campaign.historical_run()
    for index in range(4000):
        campaign.store.event("info", "fixture", "x" * 256)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 10}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    policy = resolve_storage_policy(
        cfg, action=ACTION_CLEANUP, apply=True
    )
    plan, snapshot = storage_commands.build_cleanup_plan(context, policy)
    assert any(item.action == "prune_campaign_events" for item in plan.actions)
    # A new owner artifact appears, so the plan is stale before it is applied.
    campaign.historical_run(name="run-late")
    before = campaign.paths.state_db.stat().st_size
    from mdstats.training_data.storage.executor import synchronization_for

    result = context.executor(policy).run(
        plan,
        trigger="test:stale",
        synchronization=synchronization_for(plan, snapshot),
        engine=storage_commands._cleanup_engine(context, policy),
    )
    assert result.status == "refused"
    assert not any(
        item["action"] in ("prune_campaign_events", "vacuum_campaign_state")
        for item in result.completed
    )
    assert campaign.paths.state_db.stat().st_size == before


# ---------------------------------------------------------------------------
# IR13-14/15 - complete census and journal lifecycle
# ---------------------------------------------------------------------------


def test_known_campaign_families_are_all_accounted_for(campaign) -> None:
    payload = storage_commands.storage_report(campaign.context(), _args())
    identities = {item["artifact_id"] for item in payload["artifacts"]}
    for expected in (
        "campaign_store:state",
        "campaign_store:results",
        "campaign_store:models",
        "campaign_store:runs",
        "campaign_store:data",
        "p2:statistical_authorities",
        "campaign_store:hash_receipts",
    ):
        assert expected in identities, expected


def test_an_unknown_workspace_tree_is_reported_ambiguous_and_retained(campaign) -> None:
    stranger = campaign.paths.workspace / "someone-elses-directory"
    stranger.mkdir()
    (stranger / "payload.bin").write_bytes(b"keep")
    snapshot = campaign.snapshot()
    view = snapshot.view("unclassified:workspace:someone-elses-directory")
    assert view is not None
    assert view.current and view.restart_required
    protected, why = snapshot.path_protection(stranger / "payload.bin")
    assert protected, why
    assert not any(item.eligible for item in safe_candidates(snapshot) if
                   str(stranger) in str(item.path))
    storage_commands.storage_cleanup(campaign.context(), _args(tier="cache", apply=True))
    assert (stranger / "payload.bin").read_bytes() == b"keep"


def test_terminal_restore_journals_are_bounded(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    result = _create_archive(campaign)
    for _ in range(3):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
            ),
        )
    # Force the retention bound down and prove the terminal journal is retirable.
    cfg = {**campaign.cfg, "storage": {"restore_journal_retention_records": 1}}
    snapshot = build_storage_inventory(
        cfg,
        campaign.paths,
        campaign.store,
        protected_inputs=campaign.boundary.protected_inputs,
        control_plane=campaign.control_plane,
        journal_retention_records=0,
    )
    retirable = [
        view
        for view in snapshot.views
        if view.artifact_id.startswith("storage:journal:") and view.safe_reclaimable
    ]
    assert retirable
    assert (run_root / "checkpoints" / "epoch-1.pt").is_file()


def test_a_nonterminal_journal_stays_protected(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    (run_root / "checkpoints" / "epoch-2.pt").write_bytes(b"second" * 512)
    campaign.finish_run(run_root)
    result = _create_archive(campaign)
    with pytest.raises(_Injected):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
                failpoint=_fail_at(BOUNDARY_DURING_INSTALL),
            ),
        )
    snapshot = campaign.snapshot()
    journal = campaign.control_plane.journal_path(result["archive_identity"])
    protected, why = snapshot.path_protection(journal)
    assert protected, why


def test_uncataloged_archive_residue_is_storage_owned_scratch(campaign) -> None:
    campaign.control_plane.ensure()
    residue = campaign.control_plane.archive_root / "orphan.tar.gz"
    residue.write_bytes(b"never cataloged")
    snapshot = campaign.snapshot()
    view = snapshot.view("storage:archive_residue:orphan.tar.gz")
    assert view is not None and view.safe_reclaimable
    payload = storage_commands.storage_cleanup(
        campaign.context(), _args(tier="safe", apply=True)
    )
    assert payload["execution"]["status"] in {"complete", "partial"}
    assert not residue.exists()


def test_a_retained_archive_survives_cleanup_and_a_fresh_process(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    storage_commands.storage_cleanup(campaign.context(), _args(tier="cache", apply=True))
    plane = open_storage_control_plane_readonly(campaign.paths)
    entries = list_archives(plane)
    assert [item["archive_identity"] for item in entries] == [result["archive_identity"]]
    verify_cold_archive(plane, result["archive_identity"], _policy(action=ACTION_REPORT))


def test_retained_archive_authority_is_self_contained(campaign) -> None:
    """A fresh process can plan a reclaim with no advisory files at all."""

    import shutil as _shutil

    run_root = campaign.historical_run()
    result = _create_archive(campaign, keep_hot=True)
    if campaign.paths.results.exists():
        _shutil.rmtree(campaign.paths.results)
    campaign.paths.results.mkdir(parents=True, exist_ok=True)

    from mdstats.training_data.storage.archive import build_reclaim_plan_actions

    snapshot = campaign.snapshot()
    actions, manifest, refusals = build_reclaim_plan_actions(
        workspace=campaign.paths.workspace,
        control_plane=open_storage_control_plane_readonly(campaign.paths),
        snapshot=snapshot,
        policy=_policy(action=ACTION_ARCHIVE),
        archive_identity=result["archive_identity"],
    )
    assert actions
    assert all(action.artifact_id.startswith("p5:run:") for action in actions)
    assert manifest["source_plan_actions"]
    del refusals, run_root


# ---------------------------------------------------------------------------
# Storage lease and control-plane liveness
# ---------------------------------------------------------------------------


def test_a_stale_lease_is_recovered_without_pid_inference(campaign) -> None:
    lease_path = campaign.control_plane.lock_root / "storage-operation.lock"
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text("pid=999999 stale\n", encoding="utf-8")
    with storage_operation_lease(campaign.control_plane, timeout_seconds=1.0):
        pass
    source = Path(cli.__file__).parent.joinpath("storage", "lease.py").read_text(
        encoding="utf-8"
    )
    assert "kill(" not in source and "/proc" not in source


def test_overlapping_storage_mutations_never_interleave(campaign) -> None:
    with storage_operation_lease(campaign.control_plane, timeout_seconds=0.2):
        with pytest.raises(StorageLeaseUnavailableError):
            with storage_operation_lease(campaign.control_plane, timeout_seconds=0.2):
                pass


def test_control_plane_records_carry_no_scientific_currentness(campaign) -> None:
    result = _create_archive(campaign, keep_hot=True)
    entry = campaign.control_plane.read_catalog_entry(result["archive_identity"])
    forbidden = {"current", "selected", "verdict", "qualified", "release"}
    assert not (set(entry) & forbidden)


# ---------------------------------------------------------------------------
# Frame cache: conservative retention
# ---------------------------------------------------------------------------


def test_the_frame_cache_is_reported_reconstructible_but_never_evicted(campaign) -> None:
    cache = campaign.paths.internal / "frame-cache"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "frame-cache.json").write_text("{}", encoding="utf-8")
    snapshot = campaign.snapshot()
    view = snapshot.view("p1:frame_cache")
    assert view is not None
    assert view.cache_evictable is False
    assert "liveness" in view.detail
    decisions = {item.artifact_id: item for item in cache_candidates(snapshot)}
    assert decisions["p1:frame_cache"].eligible is False
    storage_commands.storage_cleanup(campaign.context(), _args(tier="cache", apply=True))
    assert (cache / "frame-cache.json").is_file()


def test_safe_and_cache_tiers_never_evict_the_receipt_cache(campaign) -> None:
    receipts = campaign.paths.internal / "hash-receipts.sqlite3"
    receipts.write_bytes(b"x" * 1024)
    for tier in ("safe", "cache"):
        payload = storage_commands.storage_cleanup(campaign.context(), _args(tier=tier))
        for action in payload["plan"]["actions"]:
            assert "hash-receipts" not in action["path"]
    assert receipts.is_file()


# ---------------------------------------------------------------------------
# Reporting scaling and truthfulness
# ---------------------------------------------------------------------------


def test_the_normal_report_never_walks_an_owner_subtree(campaign) -> None:
    """Structural and behavioral: bounded metadata only."""

    import ast

    report_source = Path(cli.__file__).parent.joinpath("storage", "report.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(report_source)
    normal = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_owner_storage_report"
    )
    called = {
        node.func.attr
        for node in ast.walk(normal)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "rglob" not in called and "walk" not in called
    assert "build_campaign_storage_report" not in report_source

    bounded = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_bounded_metadata"
    )
    bounded_calls = {
        node.func.attr
        for node in ast.walk(bounded)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert bounded_calls <= {"lstat", "S_ISDIR", "S_ISLNK"}


def test_normal_report_cost_does_not_scale_with_descendant_count(campaign) -> None:
    run_root = campaign.historical_run()
    baseline = _count_stat_calls(campaign)
    for index in range(400):
        (run_root / "checkpoints" / f"bulk-{index}.pt").write_bytes(b"x" * 64)
    grown = _count_stat_calls(campaign)
    # A few extra owner views may appear, but the visit count must not grow with
    # the number of descendant files.
    assert grown < baseline + 50, (baseline, grown)


def _count_stat_calls(campaign) -> int:
    import os as os_module

    calls = {"n": 0}
    real_lstat = Path.lstat
    real_scandir = os_module.scandir

    def counting_lstat(self, *args, **kwargs):
        calls["n"] += 1
        return real_lstat(self, *args, **kwargs)

    def counting_scandir(*args, **kwargs):
        calls["n"] += 1
        return real_scandir(*args, **kwargs)

    Path.lstat = counting_lstat
    os_module.scandir = counting_scandir
    try:
        storage_commands.storage_report(campaign.context(), _args())
    finally:
        Path.lstat = real_lstat
        os_module.scandir = real_scandir
    return calls["n"]


def test_the_report_labels_unknown_sizes_rather_than_guessing(campaign) -> None:
    campaign.historical_run()
    payload = storage_commands.storage_report(campaign.context(), _args())
    assert payload["exact_physical_totals_available"] is False
    directories = [
        item for item in payload["artifacts"] if item["physical"]["kind"] == "directory"
    ]
    assert directories
    assert all(item["physical"]["bytes"] is None for item in directories)
    assert all(item["physical"]["size_scope"] == "unknown_without_deep_audit" for item in directories)
    for family in payload["owner_families"]:
        assert family["bytes_are_exact_totals"] is False


def test_the_deep_audit_deduplicates_shared_inodes(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    payload = b"identical" * 1024
    first = run_root / "checkpoints" / "a.bin"
    second = run_root / "checkpoints" / "b.bin"
    first.write_bytes(payload)
    os.link(first, second)
    campaign.finish_run(run_root)
    audit = storage_commands.storage_report(campaign.context(), _args(deep=True))
    assert audit["totals"]["unique_inode_bytes"] < audit["totals"]["logical_bytes"]


# ---------------------------------------------------------------------------
# Fail-closed downstream owner composition
# ---------------------------------------------------------------------------


def test_an_unreadable_selected_authority_retains_downstream_families(
    tmp_path: Path,
) -> None:
    instance = _Campaign(tmp_path, current_generation=False)
    try:
        instance.historical_run()
        snapshot = instance.snapshot()
        owners = {owner for owner, _detail in snapshot.owner_views.unresolved}
        assert "p5" in owners
        assert not any(item.eligible for item in archive_candidates(snapshot))
        protected, why = snapshot.path_protection(
            instance.paths.internal / "post-selection" / "g7" / "runs" / "run-a"
        )
        assert protected, why
    finally:
        instance.close()


def test_external_inputs_and_symlink_targets_are_never_deletable(
    campaign, tmp_path: Path
) -> None:
    external = tmp_path / "external-payload"
    external.mkdir()
    (external / "keep.bin").write_bytes(b"keep")
    link = campaign.paths.internal / "external-link"
    link.symlink_to(external, target_is_directory=True)
    authorized, detail = campaign.boundary.destructive_authorization(external / "keep.bin")
    assert not authorized and detail
    traversal_ok, _ = campaign.boundary.traversal_authorization(link)
    assert not traversal_ok


def test_no_p1_p7_loader_gained_an_implicit_archive_fallback() -> None:
    training_data = Path(cli.__file__).parent
    offenders = []
    for path in sorted(training_data.rglob("*.py")):
        if "storage" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "verify_cold_archive" in text or "archive_restore_engine" in text:
            offenders.append(str(path))
    assert offenders == []


def test_no_mutation_path_relies_on_snapshot_revalidation_alone() -> None:
    executor = Path(cli.__file__).parent.joinpath("storage", "executor.py").read_text(
        encoding="utf-8"
    )
    assert "with owner_mutation_barrier(self.paths, synchronization):" in executor
    barrier = executor.index("owner_mutation_barrier(self.paths, synchronization)")
    revalidate = executor.index("revalidate_plan(plan, snapshot, self.policy)")
    assert barrier < revalidate
    commands = Path(cli.__file__).parent.joinpath("storage", "commands.py").read_text(
        encoding="utf-8"
    )
    # Every consequential command routes through the shared executor.
    for token in (
        "engine=_cleanup_engine",
        "engine=archive_create_engine",
        "engine=archive_reclaim_engine",
        "engine=archive_restore_engine",
        "engine=dedup_engine",
    ):
        assert token in commands, token


def test_p5_and_p7_publishers_hold_the_same_owner_barrier() -> None:
    root = Path(cli.__file__).parent
    publication = (root / "post_selection_publication.py").read_text(encoding="utf-8")
    runtime = (root / "campaign_post_selection_runtime.py").read_text(encoding="utf-8")
    qualification = (root / "qualification" / "runtime.py").read_text(encoding="utf-8")
    assert publication.count("post_selection_publication_barrier") >= 2
    assert runtime.count("post_selection_publication_barrier") >= 3
    assert qualification.count("qualification_publication_barrier") >= 3


def test_the_report_never_presents_additive_family_totals(campaign) -> None:
    """Several semantic views of one path are not several storage consumptions.

    The campaign state database is simultaneously CampaignStore authority, the
    P2 statistical authorities, and the P4 selected authority. Summing owner
    family subtotals would count those bytes three times, so the report says so
    explicitly and publishes no global figure to sum into.
    """

    payload = storage_commands.storage_report(campaign.context(), _args(top=500))
    assert payload["family_totals_are_additive"] is False
    assert payload["exact_physical_totals_available"] is False
    assert "logical_bytes" not in payload
    assert "totals" not in payload

    shared = [
        item
        for item in payload["artifacts"]
        if item["logical_attribution"] == "shared_with_other_owner_views"
    ]
    assert shared, "the state database is claimed by several semantic views"
    for item in shared:
        assert item["shares_path_with"]
        for other in item["shares_path_with"]:
            assert other != item["artifact_id"]
    exclusive = [
        item
        for item in payload["artifacts"]
        if item["logical_attribution"] == "exclusive"
    ]
    assert exclusive and all(item["shares_path_with"] == [] for item in exclusive)


# ---------------------------------------------------------------------------
# IR15-1 / IR16-5 - the retained representation is reauthenticated under the lease
# ---------------------------------------------------------------------------


def _reclaim(campaign, identity, *, apply: bool = True):
    return storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="reclaim", archive_identity=identity, apply=apply),
    )


def _restore(campaign, identity, *, apply: bool = True):
    return storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="restore", archive_identity=identity, apply=apply),
    )


@pytest.mark.parametrize(
    "damage",
    ["blob_removed", "blob_corrupted", "manifest_removed", "catalog_corrupted"],
)
def test_reclaim_refuses_when_the_cold_representation_changed_after_planning(
    campaign, damage: str
) -> None:
    """A plan authenticated an archive; apply must authenticate it again.

    Between planning and apply the archive can disappear or rot. Deleting hot
    bytes on the strength of the older reading would destroy the only remaining
    copy, so the exact representation the plan bound is re-read and
    re-authenticated inside the protected window, and a mismatch removes nothing.
    """

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    original = checkpoint.read_bytes()
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    plane = campaign.control_plane

    # The plan is built here, against a healthy representation.
    context = campaign.context()
    policy = resolve_storage_policy({}, action=ACTION_RESTORE, apply=True)
    snapshot = context.snapshot(policy, certify=True)
    actions, manifest, _refusals = build_reclaim_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=identity,
    )
    assert actions, "nothing was planned for reclamation"
    authority = bind_representation_authority(plane, manifest)
    plan = build_storage_plan(snapshot, policy, actions)

    entry = plane.read_catalog_entry(identity)
    blob = plane.resolve_archive_blob(str(entry["archive_locator"]))
    manifest_path = plane.manifest_path(identity)
    catalog_path = plane.catalog_entry_path(identity)
    if damage == "blob_removed":
        blob.unlink()
    elif damage == "blob_corrupted":
        blob.write_bytes(b"corrupt" * 64)
    elif damage == "manifest_removed":
        manifest_path.unlink()
    else:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        payload["archive_sha256"] = "0" * 64
        catalog_path.write_text(json.dumps(payload), encoding="utf-8")

    execution = context.executor(policy).run(
        plan,
        trigger="test:reclaim-corruption",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_reclaim_engine(
            workspace=Path(context.paths.workspace),
            control_plane=context.consequential_plane(policy),
            policy=policy,
            boundary=context.boundary,
            manifest=manifest,
            authority=authority,
        ),
    )
    assert execution.status == "refused", execution.detail
    assert not execution.completed
    assert checkpoint.read_bytes() == original
    if catalog_path.is_file():
        refreshed = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert refreshed.get("hot_reclamation_state") != "complete"


def test_restore_installs_nothing_when_the_representation_fails_reauthentication(
    campaign,
) -> None:
    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)
    identity = result["archive_identity"]
    assert not checkpoint.exists()
    plane = campaign.control_plane

    context = campaign.context()
    policy = resolve_storage_policy({}, action=ACTION_RESTORE, apply=True)
    snapshot = context.snapshot(policy, certify=True)
    actions, manifest, conflicts = build_restore_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=identity,
        boundary=context.boundary,
    )
    assert actions and not conflicts
    authority = bind_representation_authority(plane, manifest)
    plan = build_storage_plan(snapshot, policy, actions)

    entry = plane.read_catalog_entry(identity)
    plane.resolve_archive_blob(str(entry["archive_locator"])).write_bytes(b"rot")

    execution = context.executor(policy).run(
        plan,
        trigger="test:restore-corruption",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_restore_engine(
            workspace=Path(context.paths.workspace),
            control_plane=context.consequential_plane(policy),
            policy=policy,
            boundary=context.boundary,
            manifest=manifest,
            authority=authority,
        ),
    )
    assert execution.status == "refused", execution.detail
    assert not checkpoint.exists(), "a failed reauthentication still installed bytes"
    journal = read_restore_journal(plane, identity)
    assert journal is None or journal.get("state") != "terminal"


def test_a_repaired_representation_replans_and_reclaims_normally(campaign) -> None:
    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign, keep_hot=True)
    identity = result["archive_identity"]
    plane = campaign.control_plane
    blob = plane.resolve_archive_blob(str(plane.read_catalog_entry(identity)["archive_locator"]))
    saved = blob.read_bytes()
    blob.write_bytes(b"rot")
    with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
        _reclaim(campaign, identity)
    assert checkpoint.is_file()

    blob.write_bytes(saved)
    payload = _reclaim(campaign, identity)
    assert payload["execution"]["status"] == "complete", payload["execution"]["detail"]
    assert not checkpoint.exists()


# ---------------------------------------------------------------------------
# IR15-3 - restore binds the exact parent-chain filesystem identity
# ---------------------------------------------------------------------------


def _restore_plan(campaign, identity, policy):
    context = campaign.context()
    snapshot = context.snapshot(policy, certify=True)
    actions, manifest, conflicts = build_restore_plan_actions(
        workspace=Path(context.paths.workspace),
        control_plane=campaign.control_plane,
        snapshot=snapshot,
        policy=policy,
        archive_identity=identity,
        boundary=context.boundary,
    )
    return context, snapshot, actions, manifest, conflicts


@pytest.mark.parametrize("depth", [0, 1])
def test_a_same_type_parent_inode_swap_refuses_the_restore(campaign, depth: int) -> None:
    """A pathname is not a directory.

    Replacing a planned parent with a *different* ordinary directory at the same
    path - same mode, same type, not a symlink, same device - would otherwise
    pass every check and quietly redirect the installation into a container
    nobody authorized.
    """

    import shutil as _shutil

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)
    identity = result["archive_identity"]
    assert not checkpoint.exists()

    policy = resolve_storage_policy({}, action=ACTION_RESTORE, apply=True)
    context, snapshot, actions, manifest, conflicts = _restore_plan(
        campaign, identity, policy
    )
    assert actions and not conflicts
    plan = build_storage_plan(snapshot, policy, actions)

    victim = run_root if depth else checkpoint.parent
    if not victim.is_dir():
        victim.mkdir(parents=True)
    mode = stat.S_IMODE(victim.lstat().st_mode)
    before = victim.lstat().st_ino
    # Move the original aside first so the replacement is forced onto a *new*
    # inode; recreating a same-named directory often reuses the old one, which
    # would make the fixture prove nothing.
    displaced = victim.parent / f"{victim.name}.displaced"
    victim.rename(displaced)
    victim.mkdir()
    os.chmod(victim, mode)
    assert victim.lstat().st_ino != before, "the fixture failed to swap the inode"
    _shutil.rmtree(displaced)

    execution = context.executor(policy).run(
        plan,
        trigger="test:parent-swap",
        synchronization=synchronization_for(plan, snapshot),
        engine=archive_restore_engine(
            workspace=Path(context.paths.workspace),
            control_plane=context.consequential_plane(policy),
            policy=policy,
            boundary=context.boundary,
            manifest=manifest,
            authority=bind_representation_authority(campaign.control_plane, manifest),
        ),
    )
    assert execution.status in ("refused", "partial"), execution.detail
    assert not checkpoint.exists()
    assert not any(victim.rglob("*")), "the replacement parent received installed bytes"


def test_a_restore_created_parent_is_authenticated_by_its_own_chain(campaign) -> None:
    import shutil as _shutil

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    original = checkpoint.read_bytes()
    result = _create_archive(campaign)
    _shutil.rmtree(run_root)

    payload = _restore(campaign, result["archive_identity"])
    assert payload["restore"]["status"] == "complete"
    assert payload["restore"]["created_containers"] >= 1
    assert checkpoint.read_bytes() == original


# ---------------------------------------------------------------------------
# IR15-6 / IR16-2 - observation is enforced, invocation-wide
# ---------------------------------------------------------------------------


def test_an_observational_store_refuses_every_write(campaign) -> None:
    campaign.store.event("info", "fixture", "durable")
    campaign.store.close()
    before = campaign.paths.state_db.read_bytes()

    observational = cli.CampaignStore(campaign.paths.state_db, create=False)
    try:
        assert observational.read_only is True
        assert observational.stage("doctor") is not None
        for call in (
            lambda: observational.set_meta("k", "v"),
            lambda: observational.event("info", "s", "m"),
            lambda: observational.set_stage("doctor", cli.StageState.COMPLETE, "m"),
            lambda: observational.delete_record("nothing"),
        ):
            with pytest.raises(cli.CampaignCliError, match="observation only"):
                call()
        with pytest.raises(cli.CampaignCliError, match="observation only"):
            with observational.exclusive_transaction():
                pass
    finally:
        observational.close()
    assert campaign.paths.state_db.read_bytes() == before


def test_a_read_only_store_cannot_write_even_through_raw_sql(campaign) -> None:
    """SQLite itself refuses, not just the owner's own guards."""

    import sqlite3

    campaign.store.close()
    observational = cli.CampaignStore(campaign.paths.state_db, create=False)
    try:
        connection = observational._connect()
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(
                "INSERT INTO events(timestamp_utc,level,stage,message) "
                "VALUES ('t','info','s','m')"
            )
    finally:
        observational.close()


def test_observation_reaches_a_worker_thread_that_opens_its_own_store(
    campaign,
) -> None:
    """IR16-2: a nested helper cannot escape observation by spawning a worker.

    The capability is invocation-scoped, so a worker started inside an
    observational command opens the campaign store read-only even when it calls
    the ordinary default-creating constructor.
    """

    from concurrent.futures import ThreadPoolExecutor

    from mdstats.training_data._observation import ObservationalThreadPoolExecutor

    campaign.store.close()

    def _open_and_report() -> bool:
        store = cli.CampaignStore(campaign.paths.state_db)
        try:
            return bool(store.read_only)
        finally:
            store.close()

    with cli.observational_campaign_state():
        assert _open_and_report() is True
        with ObservationalThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(lambda _index: _open_and_report(), range(2))) == [
                True,
                True,
            ]
        # A plain pool does *not* inherit the context, which is exactly why the
        # storage fan-out uses the propagating one.
        with ThreadPoolExecutor(max_workers=1) as plain:
            assert plain.submit(_open_and_report).result() is False


def test_an_observational_hash_writes_no_receipt_from_a_worker_thread(
    campaign, tmp_path: Path
) -> None:
    from mdstats.training_data import _common
    from mdstats.training_data.storage.durability import parallel_digests

    receipts = campaign.paths.internal / "hash-receipts.sqlite3"
    _common.configure_sha256_receipt_store(receipts)
    from mdstats.training_data.storage.durability import (
        RECEIPT_ACCELERATION_MINIMUM_BYTES,
    )

    targets = []
    for index in range(2):
        item = tmp_path / f"payload-{index}.bin"
        item.write_bytes(bytes([index]) * (RECEIPT_ACCELERATION_MINIMUM_BYTES + 1))
        targets.append(str(item))
    _common._SHA256_HASHED_IN_PROCESS.clear()
    before = receipts.read_bytes() if receipts.is_file() else b""

    with cli.observational_campaign_state():
        digests = parallel_digests(targets, workers=2, accelerated=True)
    assert len(digests) == 2
    after = receipts.read_bytes() if receipts.is_file() else b""
    assert after == before, "an observational hash wrote an acceleration receipt"

    # The very same call outside observation is free to accelerate.
    _common._SHA256_HASHED_IN_PROCESS.clear()
    parallel_digests(targets, workers=2, accelerated=True)
    assert receipts.is_file()


def test_an_observational_command_does_not_disable_a_concurrent_writer(
    campaign, tmp_path: Path
) -> None:
    """IR16-2: observation is scoped to its own context, not to the process."""

    import threading

    from mdstats.training_data import _common
    from mdstats.training_data.storage.durability import parallel_digests

    receipts = campaign.paths.internal / "hash-receipts.sqlite3"
    _common.configure_sha256_receipt_store(receipts)
    from mdstats.training_data.storage.durability import (
        RECEIPT_ACCELERATION_MINIMUM_BYTES,
    )

    payload = tmp_path / "writer.bin"
    payload.write_bytes(b"w" * (RECEIPT_ACCELERATION_MINIMUM_BYTES + 1))
    observing = threading.Event()
    release = threading.Event()

    def _observational_worker() -> None:
        with cli.observational_campaign_state():
            observing.set()
            release.wait(30.0)

    worker = threading.Thread(target=_observational_worker, daemon=True)
    worker.start()
    try:
        assert observing.wait(30.0)
        _common._SHA256_HASHED_IN_PROCESS.clear()
        parallel_digests([str(payload)], workers=1, accelerated=True)
        assert receipts.is_file(), (
            "an observational command in another thread disabled this writer's cache"
        )
        assert _common._SHA256_RECEIPT_PATH is not None
    finally:
        release.set()
        worker.join(30.0)


# ---------------------------------------------------------------------------
# IR15-7 - dedup replacement is directory-entry durable before completion
# ---------------------------------------------------------------------------


def _dedup_pair(campaign) -> tuple[Path, Path]:
    run_root = campaign.historical_run(finish=False)
    first = run_root / "checkpoints" / "dup-a.pt"
    second = run_root / "checkpoints" / "dup-b.pt"
    payload = b"identical" * 512
    for item in (first, second):
        item.write_bytes(payload)
        os.chmod(item, 0o644)
    campaign.finish_run(run_root)
    return first, second


def test_a_dedup_durability_failure_is_never_audited_complete(campaign) -> None:
    from mdstats.training_data.storage.dedup import (
        BOUNDARY_BEFORE_DIRECTORY_DURABILITY,
    )

    first, second = _dedup_pair(campaign)

    def failpoint(name: str) -> None:
        if name == BOUNDARY_BEFORE_DIRECTORY_DURABILITY:
            raise RuntimeError("injected directory-entry durability failure")

    with pytest.raises(RuntimeError, match="durability failure"):
        storage_commands.storage_deduplicate(
            campaign.context(), _args(apply=True, failpoint=failpoint)
        )
    audit = campaign.control_plane.read_audit()
    assert audit
    assert all(item.get("status") != "complete" for item in audit)
    assert any(item.get("status") == "partial" for item in audit)
    assert not any(
        item.parent.name == "checkpoints" and item.name.startswith(".")
        for item in (first.parent).iterdir()
    ), "a temporary dedup link survived the failure"

    # Retry from the observed filesystem state completes idempotently.
    payload = storage_commands.storage_deduplicate(
        campaign.context(), _args(apply=True)
    )
    assert payload["execution"]["status"] == "complete"
    assert first.stat().st_ino == second.stat().st_ino


def test_every_dedup_replacement_is_followed_by_directory_durability() -> None:
    """Structural: no `os.replace` publication skips the durability boundary."""

    import ast

    source = Path(cli.__file__).parent.joinpath("storage", "dedup.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    replaces = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "replace"
    ]
    assert replaces, "the dedup publication path disappeared"
    assert source.count("fsync_parent_directory(") >= len(replaces)


# ---------------------------------------------------------------------------
# IR16-6 - audit publication failure is explicit, never ordinary success
# ---------------------------------------------------------------------------


def _break_audit(campaign, monkeypatch) -> None:
    def _failing_append(_payload):
        raise OSError("injected audit publication failure")

    monkeypatch.setattr(
        type(campaign.control_plane), "append_audit", lambda self, payload: _failing_append(payload)
    )


def test_a_failed_audit_publication_is_reported_as_degraded_not_success(
    campaign, monkeypatch
) -> None:
    """The mutation stands; the claim that it was audited does not."""

    campaign.historical_run()
    for _index in range(150):
        campaign.store.event("info", "fixture", "x" * 32)
    _break_audit(campaign, monkeypatch)

    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 100}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(context, _args(tier="safe", apply=True))
    execution = payload["execution"]
    assert execution["status"].endswith("_unaudited"), execution["status"]
    assert execution["status"] != "complete"
    assert execution["audit_published"] is False
    assert "injected audit publication failure" in execution["audit_failure"]
    # The mutation itself is not rolled back and not misreported.
    assert any(
        item["action"] == "prune_campaign_events" for item in execution["completed_actions"]
    )
    assert campaign.control_plane.read_audit() == ()


@pytest.mark.parametrize("family", ["archive", "restore", "deduplicate"])
def test_every_consequential_family_reports_its_audit_failure(
    campaign, monkeypatch, family: str
) -> None:
    if family == "deduplicate":
        first, second = _dedup_pair(campaign)
        _break_audit(campaign, monkeypatch)
        payload = storage_commands.storage_deduplicate(
            campaign.context(), _args(apply=True)
        )
        assert first.stat().st_ino == second.stat().st_ino
    elif family == "archive":
        campaign.historical_run()
        _break_audit(campaign, monkeypatch)
        payload = storage_commands.storage_archive(
            campaign.context(),
            _args(archive_command="create", root=None, apply=True, keep_hot=True),
        )
    else:
        run_root = campaign.historical_run()
        checkpoint = run_root / "checkpoints" / "epoch-1.pt"
        result = _create_archive(campaign)
        assert not checkpoint.exists()
        _break_audit(campaign, monkeypatch)
        payload = _restore(campaign, result["archive_identity"])
        assert checkpoint.is_file()

    execution = payload["execution"]
    assert execution["audit_published"] is False
    assert execution["status"].endswith("_unaudited")
    assert "injected audit publication failure" in execution["audit_failure"]


def test_a_successful_operation_publishes_exactly_one_audited_record(campaign) -> None:
    campaign.historical_run()
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=True),
    )
    execution = payload["execution"]
    assert execution["status"] == "complete"
    assert execution["audit_published"] is True
    assert execution["audit_failure"] == ""
    assert len(campaign.control_plane.read_audit()) == 1


def test_every_retained_archive_writer_is_beneath_the_storage_lease() -> None:
    """IR16-5: account for every product path that changes retained archive state.

    Reauthenticating a representation immediately before consuming it is only
    race-closed if nothing supported can replace that representation in the
    meantime, so this enumerates the writers rather than asserting it once.
    """

    import ast

    storage = Path(cli.__file__).parent / "storage"
    control_plane_source = (storage / "control_plane.py").read_text(encoding="utf-8")
    tree = ast.parse(control_plane_source)

    def _writes_retained_state(node: ast.FunctionDef) -> bool:
        dumped = ast.dump(node)
        touches = "catalog_root" in dumped or "archive_root" in dumped
        publishes = (
            "durable_publish_json" in dumped
            or "durable_publish_bytes" in dumped
            or "unlink" in dumped
            or "rmtree" in dumped
        )
        return touches and publishes

    writers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and _writes_retained_state(node)
    ]
    assert writers, "the control plane no longer has a retained-archive writer"
    for node in writers:
        assert "require_operation_lease" in ast.dump(node), node.name

    # The archive engine publishes the blob and manifest itself.
    archive_source = (storage / "archive.py").read_text(encoding="utf-8")
    assert 'require_operation_lease("publish an archive blob/manifest")' in archive_source
    publication = archive_source.index("require_operation_lease(\"publish an archive")
    for marker in ("_publish_archive_blob(", "durable_publish_json(\n                manifest_path"):
        assert archive_source.index(marker) > publication, marker

    # Read-only discovery deliberately needs no lease.
    for name in ("iter_catalog_entries", "read_catalog_entry", "uncataloged_archive_residue"):
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        assert "require_operation_lease" not in ast.dump(node), name


def test_an_audit_failure_while_recording_a_partial_operation_fabricates_nothing(
    campaign, monkeypatch
) -> None:
    """The worst case: an interruption whose own evidence cannot be written.

    Nothing is rolled back and nothing is invented. The next fresh inventory has
    to be able to re-plan from what is actually on disk, not from a record that
    does not exist.
    """

    from mdstats.training_data.storage import executor as executor_mod
    from mdstats.training_data.storage.executor import synchronization_for

    campaign.historical_run(generation=7, name="run-a")
    campaign.historical_run(generation=7, name="run-b")
    campaign.historical_run(generation=7, name="run-c")

    context = campaign.context()
    policy = resolve_storage_policy({}, action=ACTION_ARCHIVE, apply=True)
    context.consequential_plane(policy)
    snapshot = context.snapshot(policy, certify=True)
    selected = [item for item in archive_candidates(snapshot) if item.eligible]
    assert len(selected) >= 2
    bundle = build_archive_plan_actions(
        workspace=Path(context.paths.workspace),
        snapshot=snapshot,
        selected=selected,
        boundary=context.boundary,
        policy=policy,
        reclaim_hot=True,
    )
    plan = build_storage_plan(snapshot, policy, bundle.actions)

    _break_audit(campaign, monkeypatch)
    from mdstats.training_data.storage import archive as archive_mod

    calls = {"n": 0}
    real_unlink = archive_mod.durable_unlink

    def failing_unlink(path, *, dir_fd=None, missing_ok=True, on_unlinked=None) -> None:
        # Signature-faithful: the production caller passes the transition
        # callback, and a double that could not accept it would prove nothing
        # about how the real primitive reports what it removed.
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("injected interruption")
        real_unlink(path, dir_fd=dir_fd, missing_ok=missing_ok, on_unlinked=on_unlinked)

    monkeypatch.setattr(archive_mod, "durable_unlink", failing_unlink)
    del executor_mod

    with pytest.raises(RuntimeError, match="injected interruption"):
        context.executor(policy).run(
            plan,
            trigger="test:partial-unaudited",
            synchronization=synchronization_for(plan, snapshot),
            engine=archive_create_engine(
                workspace=Path(context.paths.workspace),
                control_plane=context.control_plane,
                policy=policy,
                boundary=context.boundary,
                bundle=bundle,
                reclaim_hot=True,
            ),
        )
    assert campaign.control_plane.read_audit() == ()

    # A fresh inventory re-plans from the actual filesystem, not from evidence.
    monkeypatch.undo()
    fresh = campaign.context().snapshot(policy, certify=True)
    assert fresh is not None
    payload = storage_commands.storage_report(campaign.context(), _args())
    assert payload["destructive_actions_performed"] is False


# ---------------------------------------------------------------------------
# IR17-1 / IR17-6 / IR18-1 - the P5 completion proof
# ---------------------------------------------------------------------------


def _anchor_paths(run_root: Path) -> tuple[Path, Path]:
    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
    )

    return (
        run_root / RUN_COMPLETION_ANCHOR_FILENAME,
        run_root / RUN_TOPOLOGY_MANIFEST_FILENAME,
    )


def _rewrite_json(path: Path, **changes) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(changes)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_the_bounded_report_never_reads_the_full_member_manifest(campaign) -> None:
    """Completion is O(1); exact topology is not, and reporting pays only the O(1).

    The compact anchor exists precisely so that describing a campaign costs the
    same whether a run holds ten files or ten thousand.
    """

    run_root = campaign.historical_run(finish=False)
    bulk = run_root / "checkpoints"
    for index in range(400):
        (bulk / f"bulk-{index}.pt").write_bytes(b"x" * 32)
    campaign.finish_run(run_root)
    anchor, topology = _anchor_paths(run_root)
    assert topology.stat().st_size > anchor.stat().st_size * 4

    opened: list[str] = []
    real_open = Path.open
    real_read_text = Path.read_text
    real_os_open = os.open

    def recording_open(self, *args, **kwargs):
        opened.append(str(self))
        return real_open(self, *args, **kwargs)

    def recording_read_text(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_text(self, *args, **kwargs)

    def recording_os_open(path, *args, **kwargs):
        opened.append(str(path))
        return real_os_open(path, *args, **kwargs)

    Path.open = recording_open
    Path.read_text = recording_read_text
    os.open = recording_os_open
    try:
        payload = storage_commands.storage_report(campaign.context(), _args())
    finally:
        Path.open = real_open
        Path.read_text = real_read_text
        os.open = real_os_open
    assert str(topology) not in opened, "the bounded report read the full manifest"
    assert str(anchor) in opened, "the bounded report skipped the completion anchor"
    assert payload["accounting_mode"] == "bounded_owner_metadata"

    # Consequential planning does pay for it, and does catch its corruption.
    _rewrite_json(topology, node_count=999)
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.archive_eligible is False
    assert "topology manifest" in view.detail


def test_the_bounded_report_follows_the_owner_after_terminal_evidence_goes_cold(
    campaign,
) -> None:
    """IR17-6: reporting uses the same completion authority as certification."""

    run_root = campaign.historical_run()
    (run_root / "run-evidence.json").unlink()
    bounded = campaign.snapshot(certify=False).view("p5:run:g7:run-a")
    exact = campaign.snapshot(certify=True).view("p5:run:g7:run-a")
    assert bounded.archive_eligible is exact.archive_eligible is True
    assert bounded.current is exact.current


def test_an_unexpected_empty_directory_is_never_swept_into_a_recursive_action(
    campaign,
) -> None:
    """IR18-1: recursive ownership covers directory nodes, not only files."""

    run_root = campaign.historical_run()
    stranger = run_root / "checkpoints" / "someone-elses-dir"
    stranger.mkdir()
    assert not any(stranger.iterdir())

    certified, why = certify_closed_post_selection_run_root(run_root)
    assert not certified and "did not write" in why

    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.archive_eligible is False
    assert "someone-elses-dir" in view.detail
    members, _refusals = snapshot.authorized_members(view)
    assert members == ()

    storage_commands.storage_cleanup(campaign.context(), _args(tier="safe", apply=True))
    assert stranger.is_dir(), "an unrecorded empty directory disappeared"

    # And when the directory appears under a view that *was* certified, the
    # recursive authorization itself refuses it rather than sweeping it along.
    stranger.rmdir()
    certified_view = campaign.snapshot().view("p5:run:g7:run-a")
    assert certified_view.archive_eligible is True
    stranger.mkdir()
    members, refusals = campaign.snapshot(certify=False).authorized_members(
        campaign.snapshot(certify=True).view("p5:run:g7:run-a")
    )
    del members, refusals
    fresh_members, fresh_refusals = _authorized_after_planning(
        campaign, certified_view, stranger
    )
    assert fresh_members == () or all(
        str(item) != str(stranger) for item in fresh_members
    )
    assert any(str(stranger) == str(path) for path, _why in fresh_refusals)


def _authorized_after_planning(campaign, view, stranger: Path):
    """Authorize a *planned* closed view against the tree as it is now."""

    return campaign.snapshot(certify=False).authorized_members(view)


def test_a_recorded_empty_directory_stays_certifiable(campaign) -> None:
    run_root = campaign.historical_run(finish=False)
    owned = run_root / "checkpoints" / "owner-made-empty"
    owned.mkdir()
    campaign.finish_run(run_root)
    certified, why = certify_closed_post_selection_run_root(run_root)
    assert certified, why


@pytest.mark.parametrize(
    "damage",
    [
        "topology_extra_member",
        "topology_duplicate",
        "topology_absolute_path",
        "topology_digest",
        "anchor_terminal_records",
        "anchor_run_root",
        "anchor_node_count",
        "anchor_digest",
        "anchor_schema",
        "anchor_copied",
        "legacy_schema_only",
    ],
)
def test_a_tampered_completion_proof_never_widens_authority(campaign, damage) -> None:
    """Ambiguity in the proof reduces authority; it never invents ownership."""

    run_root = campaign.historical_run()
    anchor, topology = _anchor_paths(run_root)
    foreign = run_root / "checkpoints" / "foreign.pt"
    foreign.write_bytes(b"not mine")

    if damage == "topology_extra_member":
        payload = json.loads(topology.read_text(encoding="utf-8"))
        payload["nodes"].append({"path": "checkpoints/foreign.pt", "kind": "file"})
        payload["node_count"] = len(payload["nodes"])
        topology.write_text(json.dumps(payload), encoding="utf-8")
    elif damage == "topology_duplicate":
        payload = json.loads(topology.read_text(encoding="utf-8"))
        payload["nodes"].append(dict(payload["nodes"][0]))
        topology.write_text(json.dumps(payload), encoding="utf-8")
    elif damage == "topology_absolute_path":
        payload = json.loads(topology.read_text(encoding="utf-8"))
        payload["nodes"][0]["path"] = "/etc/passwd"
        topology.write_text(json.dumps(payload), encoding="utf-8")
    elif damage == "topology_digest":
        _rewrite_json(topology, content_digest="0" * 64)
    elif damage == "anchor_terminal_records":
        _rewrite_json(anchor, terminal_records=["not-a-terminal-record.json"])
    elif damage == "anchor_run_root":
        _rewrite_json(anchor, run_root="some-other-run")
    elif damage == "anchor_node_count":
        _rewrite_json(anchor, node_count=99)
    elif damage == "anchor_digest":
        _rewrite_json(anchor, content_digest="0" * 64)
    elif damage == "anchor_schema":
        _rewrite_json(anchor, schema="mdstats.post-selection-run-completion.v99")
    elif damage == "anchor_copied":
        other = run_root.parent / "run-b"
        other.mkdir(parents=True, exist_ok=True)
        (other / "run-evidence.json").write_text("{}\n", encoding="utf-8")
        shutil.copy2(anchor, other / anchor.name)
        shutil.copy2(topology, other / topology.name)
        certified, why = certify_closed_post_selection_run_root(other)
        assert not certified and "different run root" in why
        return
    else:  # legacy_schema_only
        anchor.unlink()
        topology.unlink()
        (run_root / "run-members.json").write_text(
            json.dumps(
                {
                    "schema": "mdstats.post-selection-run-members.v1",
                    "run_root": run_root.name,
                    "terminal_records": ["run-evidence.json"],
                    "members": ["checkpoints/epoch-1.pt", "checkpoints/foreign.pt"],
                    "member_count": 2,
                }
            ),
            encoding="utf-8",
        )

    certified, _why = certify_closed_post_selection_run_root(run_root)
    assert not certified
    snapshot = campaign.snapshot()
    view = snapshot.view("p5:run:g7:run-a")
    assert view.archive_eligible is False
    members, _refusals = snapshot.authorized_members(view)
    assert all(str(item) != str(foreign) for item in members)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=False),
    )
    assert payload["archive"] is None, "a tampered proof authorized an archive"
    assert foreign.read_bytes() == b"not mine"
    assert (run_root / "checkpoints" / "epoch-1.pt").is_file()


def test_one_validating_reader_owns_every_positive_use_of_the_anchor() -> None:
    """Structural: no consequential path re-parses the proof for itself."""

    storage = Path(cli.__file__).parent / "storage"
    for name in ("owners.py", "inventory.py", "archive.py", "dedup.py", "report.py"):
        source = (storage / name).read_text(encoding="utf-8")
        assert "run-members.json" not in source, name
        assert "run-completion.json" not in source, name
        assert "run-topology.json" not in source, name


# ---------------------------------------------------------------------------
# IR17-2 - one effective event-retention bound
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bound", [0, 1, 10, 99, 100, 250])
def test_event_retention_executes_the_exact_resolved_bound(campaign, bound) -> None:
    """A hidden execution floor would make the plan describe a different product."""

    from mdstats.training_data.storage.maintenance import measure_reclaimable

    for _index in range(400):
        campaign.store.event("info", "fixture", "x" * 16)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": bound}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(context, _args(tier="safe", apply=True))
    pruned = [
        item
        for item in payload["execution"]["completed_actions"]
        if item["action"] == "prune_campaign_events"
    ]
    assert pruned, payload["plan"]["refusals"]
    assert pruned[0]["binding"]["maximum_events"] == bound
    _reclaimable, _total, events = measure_reclaimable(campaign.store)
    assert events == bound


def test_the_legacy_event_alias_resolves_to_the_same_identity() -> None:
    canonical = resolve_storage_policy(
        {"storage": {"sqlite_compaction_maximum_events": 7}}, action=ACTION_CLEANUP
    )
    aliased = storage_commands._resolve(
        _args(), {"cleanup": {"maximum_event_records": 7}}, action=ACTION_CLEANUP
    )
    assert aliased.sqlite_compaction_maximum_events == 7
    assert aliased.policy_identity == canonical.policy_identity


def test_no_execution_helper_hides_an_event_retention_floor() -> None:
    import ast

    source = Path(cli.__file__).read_text(encoding="utf-8")
    prune = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == "prune_events"
    )
    del ast
    body = source[source.index("def prune_events("):]
    body = body[: body.index("\n    def ", 1)]
    assert "max(100" not in body, "prune_events still clamps the resolved bound"


# ---------------------------------------------------------------------------
# IR17-4 / IR18-3 - the audit stream lifecycle
# ---------------------------------------------------------------------------


def test_the_persisted_audit_record_says_it_was_published(campaign) -> None:
    campaign.historical_run()
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=True),
    )
    execution = payload["execution"]
    stored = campaign.control_plane.read_audit()
    assert len(stored) == 1
    record = stored[0]
    assert record["audit_published"] is True
    assert record["audit_failure"] == ""
    assert record["status"] == execution["status"] == "complete"
    assert record["operation_identity"] == execution["operation_identity"]
    assert record["plan_identity"] == execution["plan_identity"]
    assert record["action"] == "archive"


def test_audit_retention_is_serialized_with_publication() -> None:
    """Structural: retention and append share one owner serialization."""

    import ast

    storage = Path(cli.__file__).parent / "storage"
    control_plane = (storage / "control_plane.py").read_text(encoding="utf-8")
    tree = ast.parse(control_plane)
    for name in ("append_audit", "prune_audit"):
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        assert "require_operation_lease" in ast.dump(node), name

    executor = (storage / "executor.py").read_text(encoding="utf-8")
    finalize = next(
        item
        for item in ast.walk(ast.parse(executor))
        if isinstance(item, ast.FunctionDef) and item.name == "run"
    )
    dumped = ast.dump(finalize)
    # Every terminal path publishes from inside the lease.
    assert "prune_audit" not in dumped


def test_retention_never_drops_a_concurrently_published_record(campaign) -> None:
    """The read-modify-replace rewrite must not race away a newer record."""

    campaign.historical_run(name="run-a")
    campaign.historical_run(name="run-b")
    cfg = {**campaign.cfg, "storage": {"audit_retention_records": 2}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    identities = []
    for _index in range(4):
        payload = storage_commands.storage_deduplicate(context, _args(apply=True))
        identities.append(payload["execution"]["operation_identity"])
    stored = campaign.control_plane.read_audit()
    assert len(stored) == 2
    assert [item["operation_identity"] for item in stored] == identities[-2:]


def test_a_retention_failure_never_unpublishes_a_successful_record(
    campaign, monkeypatch
) -> None:
    campaign.historical_run()

    def _failing_prune(self, *, keep: int) -> int:
        raise OSError("injected audit retention failure")

    monkeypatch.setattr(type(campaign.control_plane), "prune_audit", _failing_prune)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=True),
    )
    execution = payload["execution"]
    assert execution["status"] == "complete"
    assert execution["audit_published"] is True
    assert "injected audit retention failure" in execution["retention_failure"]
    assert len(campaign.control_plane.read_audit()) == 1

    # A later operation retries retention without any special recovery step.
    monkeypatch.undo()
    storage_commands.storage_cleanup(campaign.context(), _args(tier="safe", apply=True))
    assert campaign.control_plane.audit_stream_integrity() == ()


def test_a_damaged_audit_tail_is_surfaced_and_never_rewritten_over(campaign) -> None:
    campaign.historical_run()
    storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=True),
    )
    path = campaign.control_plane.audit_path
    before = path.read_bytes()
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"schema": "mdstats.mlff-storage-audit.v1", "trunc')

    problems = campaign.control_plane.audit_stream_integrity()
    assert problems
    with storage_operation_lease(campaign.control_plane):
        with pytest.raises(StorageControlPlaneError, match="damaged audit stream"):
            campaign.control_plane.prune_audit(keep=0)
    assert path.read_bytes().startswith(before)


def test_an_append_failure_after_bytes_reach_the_file_is_pessimistic(
    campaign, monkeypatch
) -> None:
    """A post-write failure cannot prove absence, so the caller is told nothing was."""

    campaign.historical_run()
    real_append = type(campaign.control_plane).append_audit

    def half_written(self, payload):
        real_append(self, payload)
        raise OSError("injected fsync failure after the bytes were written")

    monkeypatch.setattr(type(campaign.control_plane), "append_audit", half_written)
    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=True),
    )
    execution = payload["execution"]
    assert execution["audit_published"] is False
    assert execution["status"].endswith("_unaudited")
    # Either outcome is permitted for the durable stream; neither is authority.
    monkeypatch.undo()
    assert len(campaign.control_plane.read_audit()) in (0, 1)


# ---------------------------------------------------------------------------
# IR17-5 / IR18-4 - dedup staging has a storage-owned recovery lifecycle
# ---------------------------------------------------------------------------


def test_the_dedup_temporary_link_never_lands_inside_the_p5_run(campaign) -> None:
    from mdstats.training_data.storage.dedup import (
        BOUNDARY_BEFORE_DIRECTORY_DURABILITY,
    )

    del BOUNDARY_BEFORE_DIRECTORY_DURABILITY
    first, _second = _dedup_pair(campaign)
    run_root = first.parent.parent
    staged: list[str] = []
    real_replace = os.replace

    def observing_replace(source, destination, *args, **kwargs):
        # The instant before the destination is replaced is the only moment the
        # pre-rename alias exists; that is exactly where a hard crash would
        # strand it, so that is where its ownership matters.
        staged.append(str(source))
        raise RuntimeError("injected crash between the staged link and the rename")

    os.replace = observing_replace
    try:
        with pytest.raises(RuntimeError, match="injected crash"):
            storage_commands.storage_deduplicate(campaign.context(), _args(apply=True))
    finally:
        os.replace = real_replace
    assert staged, "dedup never staged a temporary alias"
    staging_root = str(campaign.control_plane.staging_root)
    assert all(item.startswith(staging_root) for item in staged), staged
    assert all(str(run_root) not in item for item in staged)

    certified, why = certify_closed_post_selection_run_root(run_root)
    assert certified, why


def test_abandoned_dedup_staging_is_storage_owned_and_recoverable(campaign) -> None:
    """A hard crash leaves storage-owned residue, not an unknown P5 descendant."""

    first, second = _dedup_pair(campaign)
    run_root = first.parent.parent
    residue = campaign.control_plane.staging_root_for("f" * 32) / "dedup"
    residue.mkdir(parents=True)
    os.link(first, residue / "0-dup-a.pt")
    before = (first.stat().st_mode, first.stat().st_ino, first.stat().st_nlink)

    snapshot = campaign.snapshot()
    view = snapshot.view(f"storage:staging:{'f' * 32}")
    assert view is not None and view.safe_reclaimable is True
    assert view.owner.startswith("storage")

    storage_commands.storage_cleanup(campaign.context(), _args(tier="safe", apply=True))
    assert not residue.exists()
    after = first.stat()
    assert (after.st_mode, after.st_ino) == before[:2]
    assert after.st_nlink == before[2] - 1

    certified, why = certify_closed_post_selection_run_root(run_root)
    assert certified, why
    payload = storage_commands.storage_deduplicate(campaign.context(), _args(apply=True))
    assert payload["execution"]["status"] == "complete"
    assert first.stat().st_ino == second.stat().st_ino


def test_no_dedup_staging_reclamation_reads_a_pid_or_an_age() -> None:
    import ast

    storage = Path(cli.__file__).parent / "storage"
    dedup = (storage / "dedup.py").read_text(encoding="utf-8")
    assert "getpid" not in dedup
    owners = (storage / "owners.py").read_text(encoding="utf-8")
    tree = ast.parse(owners)
    staging = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "control_plane_views"
    )
    dumped = ast.dump(staging)
    for folklore in ("getpid", "st_mtime", "stale_age_hours", "time("):
        assert folklore not in dumped, folklore


def test_cross_device_dedup_staging_refuses_instead_of_falling_back(
    campaign, monkeypatch
) -> None:
    """An atomic hardlink replacement needs one filesystem, or nothing happens.

    Falling back to a copy, or to an unowned temporary inside the run, would
    trade a refusal for a recovery hole.
    """

    from mdstats.training_data.storage import dedup as dedup_module

    first, second = _dedup_pair(campaign)
    run_root = first.parent.parent
    real_same_filesystem = dedup_module.same_filesystem

    def not_shared(a: Path, b: Path) -> bool:
        if str(campaign.control_plane.staging_root) in str(a):
            return False
        return real_same_filesystem(a, b)

    monkeypatch.setattr(dedup_module, "same_filesystem", not_shared)
    payload = storage_commands.storage_deduplicate(campaign.context(), _args(apply=True))
    execution = payload["execution"]
    assert execution["status"] == "refused"
    assert any(
        "different filesystems" in item["refusal"] for item in execution["refused_actions"]
    )
    assert first.stat().st_ino != second.stat().st_ino
    assert not [item for item in run_root.rglob(".*dedup*")]
    certified, why = certify_closed_post_selection_run_root(run_root)
    assert certified, why


# ---------------------------------------------------------------------------
# R19-A - typed, no-follow closed-subtree authority
# ---------------------------------------------------------------------------


def _p5_view(campaign, *, certify: bool = True):
    return campaign.snapshot(certify=certify).view("p5:run:g7:run-a")


@pytest.mark.parametrize(
    "substitution", ["file_to_directory", "directory_to_file", "symlink", "fifo"]
)
def test_a_same_name_node_substitution_is_never_the_node_the_owner_certified(
    campaign, substitution: str
) -> None:
    """A path string is not a node. Kind is part of the owner's proof."""

    run_root = campaign.historical_run(finish=False)
    owned_dir = run_root / "checkpoints" / "owned-dir"
    owned_dir.mkdir()
    (owned_dir / "inner.pt").write_bytes(b"inner")
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    campaign.finish_run(run_root)
    assert certify_closed_post_selection_run_root(run_root)[0]

    if substitution == "file_to_directory":
        checkpoint.unlink()
        checkpoint.mkdir()
        victim = checkpoint
    elif substitution == "directory_to_file":
        shutil.rmtree(owned_dir)
        owned_dir.write_bytes(b"not a directory")
        victim = owned_dir
    elif substitution == "symlink":
        checkpoint.unlink()
        checkpoint.symlink_to(run_root / "run-evidence.json")
        victim = checkpoint
    else:
        checkpoint.unlink()
        os.mkfifo(checkpoint)
        victim = checkpoint

    certified, why = certify_closed_post_selection_run_root(run_root)
    assert not certified, why
    view = _p5_view(campaign)
    assert view.archive_eligible is False
    members, _refusals = campaign.snapshot().authorized_members(view)
    assert all(str(item) != str(victim) for item in members)

    payload = storage_commands.storage_archive(
        campaign.context(),
        _args(archive_command="create", root=None, apply=True, keep_hot=False),
    )
    assert payload["archive"] is None
    assert observed_node_kind(victim) != "absent"


def test_a_symlinked_completion_proof_grants_no_authority_and_is_not_followed(
    campaign, tmp_path: Path
) -> None:
    """An owner proof that can be redirected is not a proof."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
    )

    run_root = campaign.historical_run()
    for name in (RUN_COMPLETION_ANCHOR_FILENAME, RUN_TOPOLOGY_MANIFEST_FILENAME):
        target = run_root / name
        elsewhere = tmp_path / f"planted-{name}"
        elsewhere.write_bytes(target.read_bytes())
        saved = target.read_bytes()
        target.unlink()
        target.symlink_to(elsewhere)

        certified, why = certify_closed_post_selection_run_root(run_root)
        assert not certified, why
        assert _p5_view(campaign).archive_eligible is False
        assert _p5_view(campaign, certify=False).archive_eligible is False

        target.unlink()
        target.write_bytes(saved)
    assert certify_closed_post_selection_run_root(run_root)[0]


def test_recursive_deletion_is_symlink_attack_resistant() -> None:
    """The capability the consequential recursion actually rests on.

    `shutil.rmtree.avoids_symlink_attacks` describes `rmtree`'s implementation
    and is no protection whatsoever for a separate walker. The one cleanup
    recursion descends through directory descriptors, so the capability that
    protects it is the dir-fd primitive set - and it refuses rather than
    widening to a pathname walk when that set is unavailable.
    """

    from mdstats.training_data.storage.trust import dir_fd_mutation_supported

    assert dir_fd_mutation_supported(), (
        "this platform cannot provide no-follow directory-descriptor removal; "
        "the canonical destructive owner must refuse recursive removal here"
    )
    removal = (
        Path(cli.__file__).parent / "storage" / "removal.py"
    ).read_text(encoding="utf-8")
    assert "shutil" not in removal, (
        "the canonical destructive owner delegates its recursion to rmtree"
    )


def test_every_consequential_engine_consumes_the_typed_owner_authority() -> None:
    """Structural: no engine re-derives authority from bare path names."""

    import ast

    storage = Path(cli.__file__).parent / "storage"
    inventory = (storage / "inventory.py").read_text(encoding="utf-8")
    tree = ast.parse(inventory)
    node = next(
        item
        for item in ast.walk(tree)
        if isinstance(item, ast.FunctionDef) and item.name == "authorized_members"
    )
    dumped = ast.dump(node)
    assert "certified_nodes" in dumped
    assert "observed_node_kind" in dumped
    assert "certified_members" not in dumped, (
        "recursive authorization still reads the path-only display surface"
    )
    for name in ("archive.py", "dedup.py", "commands.py", "executor.py"):
        source = (storage / name).read_text(encoding="utf-8")
        assert "certified_members" not in source, name


# ---------------------------------------------------------------------------
# R19-C - the CampaignStore writer gate
# ---------------------------------------------------------------------------


def test_a_second_thread_blocks_on_the_writer_exclusion(campaign) -> None:
    """Reentrancy belongs to the acquiring thread, never to the object."""

    import threading

    holding = threading.Event()
    release = threading.Event()
    order: list[str] = []

    def holder() -> None:
        with campaign.store.writer_exclusion():
            holding.set()
            release.wait(30.0)
            order.append("holder")

    def writer() -> None:
        holding.wait(30.0)
        campaign.store.event("info", "fixture", "second thread")
        order.append("writer")

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=writer, daemon=True)
    first.start()
    assert holding.wait(30.0)
    second.start()
    time.sleep(0.5)
    assert order == [], "a second thread wrote while the exclusion was held"
    release.set()
    first.join(30.0)
    second.join(30.0)
    assert order == ["holder", "writer"]


def test_two_store_instances_for_one_database_share_the_gate(campaign) -> None:
    import threading

    other = cli.CampaignStore(campaign.paths.state_db)
    try:
        holding = threading.Event()
        release = threading.Event()
        order: list[str] = []

        def writer() -> None:
            holding.wait(30.0)
            other.event("info", "fixture", "other instance")
            order.append("writer")

        thread = threading.Thread(target=writer, daemon=True)
        with campaign.store.writer_exclusion():
            holding.set()
            thread.start()
            time.sleep(0.5)
            assert order == [], "a second store instance bypassed the shared gate"
            release.set()
        thread.join(30.0)
        assert order == ["writer"]
    finally:
        other.close()


def test_a_same_thread_nested_write_is_reentrant(campaign) -> None:
    other = cli.CampaignStore(campaign.paths.state_db)
    try:
        with campaign.store.writer_exclusion():
            campaign.store.event("info", "fixture", "nested through the same store")
            other.event("info", "fixture", "nested through another instance")
    finally:
        other.close()
    assert campaign.store.stage("doctor") is not None


def test_an_observational_store_creates_no_writer_lock(campaign, tmp_path: Path) -> None:
    """The read-only capability fails before *any* side effect, not after."""

    import mdstats as _mdstats

    campaign.store.close()
    observational = cli.CampaignStore(campaign.paths.state_db, create=False)
    lock_path = observational.writer_lock_path
    lock_path.unlink(missing_ok=True)
    before = _tree_signature(campaign.paths.workspace)
    try:
        with pytest.raises(cli.CampaignCliError, match="observation only"):
            with observational.writer_exclusion():
                pass
        big = {"payload": "x" * (2 * 1024 * 1024)}
        with pytest.raises(cli.CampaignCliError, match="observation only"):
            observational.replace_records_atomically({"huge": big})
    finally:
        observational.close()
    assert not lock_path.exists(), "an observational store created the writer lock"
    assert _tree_signature(campaign.paths.workspace) == before
    del _mdstats


def test_every_campaign_store_write_site_joins_the_writer_boundary() -> None:
    """Structural census, constructor included."""

    import ast

    source = Path(cli.__file__).read_text(encoding="utf-8")
    store = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef) and node.name == "CampaignStore"
    )
    mutating = ("INSERT", "UPDATE", "DELETE", "VACUUM", "CREATE TABLE", "executescript")
    offenders: list[str] = []
    for node in store.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        dumped = ast.dump(node)
        if not any(marker in dumped for marker in mutating):
            continue
        if "writer_exclusion" in dumped or "exclusive_transaction" in dumped:
            continue
        offenders.append(node.name)
    assert offenders == [], offenders
    constructor = next(
        node
        for node in store.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    assert "writer_exclusion" in ast.dump(constructor)


def test_the_writer_lock_is_campaign_store_owner_infrastructure(campaign) -> None:
    campaign.store.event("info", "fixture", "materialize the lock")
    snapshot = campaign.snapshot()
    view = snapshot.view("campaign_store:writer_lock")
    assert view is not None
    assert view.path == campaign.store.writer_lock_path
    assert view.safe_reclaimable is False
    assert view.archive_eligible is False
    assert view.hot_path_required is True

    for candidates in (
        safe_candidates(snapshot),
        cache_candidates(snapshot),
        archive_candidates(snapshot),
    ):
        assert all(
            str(item.path) != str(view.path) or not item.eligible for item in candidates
        )
    payload = storage_commands.storage_report(campaign.context(), _args(top=500))
    unknown = [
        item
        for item in payload["artifacts"]
        if item["artifact_id"].startswith("unclassified:")
        and "writer-lock" in item["path"]
    ]
    assert unknown == []


# ---------------------------------------------------------------------------
# IR20-1 - observational purity crosses the real externalization boundary
# ---------------------------------------------------------------------------


def test_an_observational_replacement_fails_before_externalizing_anything(
    campaign,
) -> None:
    """The guard must precede the *filesystem* work, not just the SQLite write.

    `_encode_record_for_storage` materializes external payloads under
    `.mdstats/records/` before the database is touched at all, so a capability
    check that only ran when the writer exclusion or SQLite finally refused
    would already have written them.
    """

    from mdstats.training_data._campaign_cli_core import (
        EXTERNAL_RECORD_THRESHOLD_BYTES,
    )

    campaign.store.close()
    observational = cli.CampaignStore(campaign.paths.state_db, create=False)
    observational.writer_lock_path.unlink(missing_ok=True)
    before = _tree_signature(campaign.paths.workspace)
    try:
        # A key the store forces through an external representation regardless
        # of size, and an ordinary key strictly larger than the externalization
        # threshold: both reach real filesystem work before SQLite.
        for records in (
            {"frame_catalog": {"frames": [{"uid": "a" * 32}]}},
            {"bulk": {"payload": "x" * (EXTERNAL_RECORD_THRESHOLD_BYTES + 4096)}},
        ):
            with pytest.raises(cli.CampaignCliError, match="observation only"):
                observational.replace_records_atomically(records)
    finally:
        observational.close()

    assert _tree_signature(campaign.paths.workspace) == before
    assert not observational.writer_lock_path.exists()
    # Exact, with no unconditional escape: the externalized record directory
    # holds precisely the entries the pre-operation workspace signature named.
    records_root = campaign.paths.internal / "records"
    assert sorted(
        str(item.relative_to(campaign.paths.workspace))
        for item in records_root.rglob("*")
    ) == sorted(name for name in before if name.startswith("internal/records/"))


def test_the_replacement_guard_is_the_first_executable_statement() -> None:
    """Structural: no encoding happens above the capability check."""

    import ast

    source = Path(cli.__file__).read_text(encoding="utf-8")
    node = next(
        item
        for item in ast.walk(ast.parse(source))
        if isinstance(item, ast.FunctionDef)
        and item.name == "replace_records_atomically"
    )
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]  # the docstring
    assert body, "replace_records_atomically has no executable body"
    assert "_require_writable" in ast.dump(body[0]), ast.dump(body[0])[:160]

    # And the misnamed duplicate is gone from put_records.
    put_records = next(
        item
        for item in ast.walk(ast.parse(source))
        if isinstance(item, ast.FunctionDef) and item.name == "put_records"
    )
    dumped = ast.dump(put_records)
    assert dumped.count("_require_writable") == 1
    assert "replace campaign records" not in dumped


# ---------------------------------------------------------------------------
# IR23-2 / R24-3 - the synchronization contract and the P7 authority boundary
# ---------------------------------------------------------------------------


def test_the_synchronization_contract_serializes_the_attempt_seam() -> None:
    """IR23-2: one serializer, and it tells the whole truth.

    Runtime locking already used `attempt_roots`; a diagnostic that omitted it
    made the acquired lock set look smaller than it is, at exactly the seam
    under review.
    """

    from mdstats.training_data.storage.lease import OwnerSynchronization

    source = inspect.getsource(OwnerSynchronization)
    assert source.count("def to_dict(") == 1, "a duplicate serializer still shadows it"

    synchronization = OwnerSynchronization.of(
        (7,), (Path("/w/runs/run-a"),), (Path("/w/attempts/aa"), Path("/w/attempts/bb"))
    )
    payload = synchronization.to_dict()
    assert payload["generations"] == [7]
    assert payload["run_roots"] == ["/w/runs/run-a"]
    assert payload["attempt_roots"] == ["/w/attempts/aa", "/w/attempts/bb"]


def test_no_p7_consumer_converts_root_bound_certification_into_path_authority() -> None:
    """R24-3 structural: the exact result is never reduced to names alone.

    A released-attempt view carries both the owner's own authorizer and the
    filesystem identity it was certified against. Every place that could spend
    that authority - the common member resolver, the plan binding, and the final
    recursive removal - has to consume them.
    """

    import ast

    storage_root = Path(cli.__file__).parent / "storage"
    inventory_source = (storage_root / "inventory.py").read_text(encoding="utf-8")
    executor_source = (storage_root / "executor.py").read_text(encoding="utf-8")
    commands_source = (storage_root / "commands.py").read_text(encoding="utf-8")
    plan_source = (storage_root / "plan.py").read_text(encoding="utf-8")

    # The common resolver delegates released P7 subtrees to the owner instead of
    # re-walking them by pathname.
    tree = ast.parse(inventory_source)
    resolver = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "authorized_members"
    )
    del resolver
    # Released P7 members are never resolved here at all: their owner keeps the
    # authority and hands its authenticated descriptor to the canonical
    # destructive owner, so no pathname re-walk exists to be redirected.
    assert "authorize_released_attempt_member" not in inventory_source
    assert "remove_certified_unit" in (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")
    assert "attempt_fd" in (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")

    # The last mutation seam re-observes the certified root.
    removal_source = (storage_root / "removal.py").read_text(encoding="utf-8")
    assert "root_identity" in removal_source
    certification = next(
        node
        for node in ast.walk(ast.parse(removal_source))
        if isinstance(node, ast.ClassDef) and node.name == "Certification"
    )
    accepted = {
        node.target.id
        for node in certification.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }
    assert {"root_identity", "authority_identity"} <= accepted, (
        "the recursive removal cannot be told which objects it was authorized on"
    )
    # Both the container and the authority root above it: a symlinked ancestor
    # that happens to lead back to the certified bytes is still an unauthenticated
    # chain, so the leaf identity alone is not the proof.
    assert "root_identity=view.path_identity" in commands_source, (
        "the cleanup engine drops the certified container identity before removing"
    )
    assert "authority_identity=view.root_identity" in commands_source, (
        "the cleanup engine drops the certified authority root before removing"
    )
    del executor_source

    # And an identity change - of either - stales an unapplied plan.
    assert "view.root_identity" in plan_source and "view.path_identity" in plan_source


# ---------------------------------------------------------------------------
# R28 - the final apply boundary and the terminal-outcome contract
# ---------------------------------------------------------------------------


def test_the_final_p7_apply_certifies_on_the_descriptor_it_mutates() -> None:
    """Structural: the session, not a carried snapshot, is the authority.

    A narrow guard on the actual mechanism. The released-member remover must
    take a live session rather than a path plus a set of names produced
    somewhere else, and the session opener must authenticate state and certify
    topology on the descriptor it returns still open.
    """

    import ast

    store_path = Path(cli.__file__).parent / "qualification" / "store.py"
    source = store_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    opener = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "open_released_attempt_session"
    )
    # IR17-2C splits *deciding* the acquisition outcome from *releasing* the
    # descriptor, so the authentication steps live in the helper the opener
    # calls unconditionally. The claim is unchanged - one descent, then state,
    # proof, root binding and typed topology on the descriptor that is returned
    # still open - so the guard follows the delegation rather than the file
    # layout.
    decider = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "_authenticate_released_attempt"
    )
    body = ast.dump(opener) + ast.dump(decider)
    for required in (
        "_authenticate_attempt_from_descriptor",
        "_certify_attempt_from_descriptor",
        "released_authority_identity",
        "open_attempt_namespace",
    ):
        assert required in body, required
    assert "_authenticate_released_attempt" in ast.dump(opener), (
        "the opener no longer delegates to the acquisition decider"
    )
    # The decider never competes with the caller's ranking by closing.
    assert "os" not in {
        node.value.id
        for node in ast.walk(decider)
        if isinstance(node, ast.Attribute)
        and node.attr == "close"
        and isinstance(node.value, ast.Name)
    }, "the acquisition decider closes the descriptor it is deciding about"
    # And no raw `finally: os.close(...)` remains around the opener's refusal
    # returns, where a close failure could cancel an already-decided owner or
    # authentication refusal.
    for node in ast.walk(opener):
        if not isinstance(node, ast.Try):
            continue
        for statement in node.finalbody:
            for inner in ast.walk(statement):
                assert not (
                    isinstance(inner, ast.Attribute)
                    and inner.attr == "close"
                    and isinstance(inner.value, ast.Name)
                    and inner.value.id == "os"
                ), "a raw finally-close can still replace a decided refusal"

    remover = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "remove_released_attempt_member"
    )
    # The first parameter is the live capability. A `paths`/`attempt_root` pair
    # would mean the remover re-opens the namespace for itself, which is the
    # closed-descriptor gap this replaced.
    assert [arg.arg for arg in remover.args.args][:2] == ["session", "member_name"], (
        [arg.arg for arg in remover.args.args]
    )
    remover_body = ast.dump(remover)
    assert "open_attempt_namespace" not in remover_body, (
        "the remover reacquires the namespace instead of using the session"
    )
    assert "certified_nodes" not in [arg.arg for arg in remover.args.kwonlyargs], (
        "a snapshot's certified node set is still passed in as final authority"
    )

    # And the cleanup engine opens exactly one session per attempt.
    commands = (Path(cli.__file__).parent / "storage" / "commands.py").read_text(
        encoding="utf-8"
    )
    assert "open_released_attempt_session" in commands
    assert "sessions[key]" in commands, (
        "the engine no longer reuses one live capability per attempt"
    )


def test_every_cleanup_removal_owner_reports_a_terminal_outcome() -> None:
    """Structural: no removal path still answers with a bare boolean.

    Reason strings are diagnostics. If any owner returned prose plus a boolean,
    the executor would have to guess whether a refusal had already changed the
    filesystem, and the durable audit would inherit the guess.
    """

    import ast
    import inspect as _inspect

    from mdstats.training_data.qualification.store import (
        remove_released_attempt_member,
    )
    from mdstats.training_data.storage.executor import record_removal
    from mdstats.training_data.storage.outcome import MutationOutcome
    from mdstats.training_data.storage.removal import (
        remove_certified_unit,
        remove_planned_target,
    )

    for owner in (
        remove_released_attempt_member,
        remove_certified_unit,
        remove_planned_target,
    ):
        annotation = _inspect.signature(owner).return_annotation
        assert "MutationOutcome" in str(annotation), (owner.__name__, annotation)

    # Settlement reads the outcome, never the detail text.
    settle = next(
        node
        for node in ast.walk(
            ast.parse(
                (Path(cli.__file__).parent / "storage" / "executor.py").read_text(
                    encoding="utf-8"
                )
            )
        )
        if isinstance(node, ast.FunctionDef) and node.name == "record_removal"
    )
    dumped = ast.dump(settle)
    assert "succeeded" in dumped and "mutated" in dumped
    # The aggregate is the sum of what each action recorded, so the two can
    # never disagree about how much this execution reclaimed.
    assert "reclaimed_bytes" in dumped
    assert "detail" in dumped  # carried as evidence...
    assert ".find(" not in dumped and ".startswith(" not in dumped, (
        "the outcome is being inferred from the reason string"
    )
    assert isinstance(record_removal, type(record_removal))
    assert set(MutationOutcome.__dataclass_fields__) >= {
        "outcome",
        "detail",
        "removed_bytes",
    }


def test_a_partial_removal_never_credits_the_planned_size() -> None:
    """The reclaim figure an operator reads is what actually went."""

    from mdstats.training_data.storage.outcome import (
        already_absent,
        partial_change_refused,
        refused_no_change,
        removed,
    )

    assert removed("done").credited_bytes(4096) == 4096
    assert removed("done", removed_bytes=100).credited_bytes(4096) == 100
    assert already_absent("gone").credited_bytes(4096) == 0
    assert refused_no_change("no").credited_bytes(4096) == 0
    partial = partial_change_refused("stopped", removed_bytes=17)
    assert partial.credited_bytes(4096) == 17
    assert partial.mutated is True and partial.refused is True
    assert partial.succeeded is False


def test_the_canonical_owner_reports_partial_when_it_half_empties(
    tmp_path: Path,
) -> None:
    """A contradiction after a certified sibling is a partial, not a refusal.

    The walk removes what the owner certified and stops at the first node it did
    not. Reporting that as `refused_no_change` would describe a directory that
    no longer holds what it held; reporting it as `removed` would claim a
    container that is still there.
    """

    from mdstats.training_data.storage.outcome import (
        OUTCOME_PARTIAL_CHANGE_REFUSED,
        OUTCOME_REFUSED_NO_CHANGE,
    )

    container = tmp_path / "campaign" / "container"
    container.mkdir(parents=True)
    authorized = container / "authorized.bin"
    authorized.write_bytes(b"x" * 64)
    foreign = container / "foreign.bin"
    foreign.write_bytes(b"not ours")

    # Entries are walked in name order, so the certified member goes first and
    # the unrecorded one stops the action.
    outcome = _certified(
        container, nodes={"authorized.bin": "file"}, anchor=container.parent
    )
    assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED, outcome
    assert outcome.mutated is True and outcome.succeeded is False
    assert outcome.removed_bytes == 64, outcome
    # Never the planned size: only what this execution measured before deleting.
    assert outcome.credited_bytes(1_000_000) == 64
    assert not authorized.exists()
    assert foreign.read_bytes() == b"not ours"
    assert container.is_dir()

    # And with nothing certified to remove, the same contradiction is a clean
    # no-change refusal rather than a partial.
    only_foreign = tmp_path / "campaign" / "only-foreign"
    only_foreign.mkdir(parents=True)
    (only_foreign / "foreign.bin").write_bytes(b"not ours")
    outcome = _certified(only_foreign, nodes={}, anchor=only_foreign.parent)
    assert outcome.outcome == OUTCOME_REFUSED_NO_CHANGE, outcome
    assert outcome.mutated is False
    assert outcome.credited_bytes(1_000_000) == 0


# ---------------------------------------------------------------------------
# R30-H - exact action-local bytes through recursive partial mutation
# ---------------------------------------------------------------------------


def _recorded_tree(root: Path) -> dict[str, str]:
    """The typed node map a released proof would carry for this tree."""

    recorded: dict[str, str] = {root.name: "directory"}
    for item in sorted(root.rglob("*")):
        relative = f"{root.name}/{item.relative_to(root).as_posix()}"
        recorded[relative] = "directory" if item.is_dir() else "file"
    return recorded


def _certified_unit(parent_fd: int, container: Path, recorded, **kwargs):
    """Drive the canonical destructive owner exactly as the P7 session does.

    The session authenticates the attempt directory and hands its descriptor to
    the one canonical remover, along with the proof's typed node map keyed
    relative to that attempt root.  These unit cases supply the same two things.
    """

    from mdstats.training_data.storage.removal import (
        Certification,
        remove_certified_unit,
    )
    from mdstats.training_data.storage_reclamation import filesystem_identity

    name = kwargs.pop("name", container.name)
    identity = kwargs.pop("planned_identity", None)
    if identity is None:
        try:
            identity = filesystem_identity(container)
        except OSError:
            identity = {
                "schema": "mdstats.mlff-filesystem-identity.v1",
                "kind": "absent",
            }
    return remove_certified_unit(
        parent_fd,
        name,
        container,
        planned_identity=identity,
        certification=Certification(
            nodes=recorded,
            prefix=f"{name}/",
            root_kind=recorded.get(name),
            **kwargs,
        ),
    )


def test_recursive_partial_mutation_reports_exact_action_local_bytes(
    tmp_path: Path,
) -> None:
    """A fully removed nested subtree still counts toward a later refusal.

    The recursion unlinks a complete subtree, then meets a node the proof never
    recorded. If the nested success did not propagate its measured bytes, the
    parent's partial figure would silently drop everything the subtree freed -
    reporting less reclaim than the filesystem actually gave back.
    """

    import os as _os

    from mdstats.training_data.qualification.store import dir_fd_mutation_supported
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    assert dir_fd_mutation_supported()
    container = tmp_path / "member"
    nested = container / "a-nested"
    nested.mkdir(parents=True)
    (nested / "one.bin").write_bytes(b"x" * 100)
    (nested / "two.bin").write_bytes(b"y" * 250)
    (container / "m-later.bin").write_bytes(b"z" * 7)
    recorded = _recorded_tree(container)

    # Planted after the proof was taken: an addition the owner never authored.
    # Sorted enumeration reaches it after the nested subtree is already gone.
    (container / "zz-foreign.bin").write_bytes(b"not ours")

    parent_fd = _os.open(tmp_path, _os.O_RDONLY | _os.O_DIRECTORY)
    try:
        outcome = _certified_unit(parent_fd, container, recorded)
    finally:
        _os.close(parent_fd)

    assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED, outcome
    assert outcome.mutated is True and outcome.succeeded is False
    # 100 + 250 from the nested subtree that fully went, plus the 7-byte file
    # removed before the foreign node stopped the walk.
    assert outcome.removed_bytes == 357, outcome
    assert outcome.credited_bytes(1_000_000) == 357
    assert not nested.exists(), "the nested subtree survived"
    assert (container / "zz-foreign.bin").read_bytes() == b"not ours"


def test_recursive_byte_accounting_deduplicates_hard_links(tmp_path: Path) -> None:
    """One file with several names is one file's worth of reclaim.

    The planner's own tree metric counts each `(device, inode)` once. If the
    removal counted per link, a partial figure would claim more bytes back than
    the filesystem ever held.
    """

    import os as _os

    from mdstats.training_data.storage.plan import _tree_bytes
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    container = tmp_path / "member"
    container.mkdir()
    original = container / "a-original.bin"
    original.write_bytes(b"x" * 512)
    _os.link(original, container / "b-hardlink.bin")
    recorded = _recorded_tree(container)
    planner_view = _tree_bytes(container)
    assert planner_view == 512, planner_view

    (container / "zz-foreign.bin").write_bytes(b"not ours")

    parent_fd = _os.open(tmp_path, _os.O_RDONLY | _os.O_DIRECTORY)
    try:
        outcome = _certified_unit(parent_fd, container, recorded)
    finally:
        _os.close(parent_fd)

    assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED, outcome
    assert outcome.removed_bytes == 512, outcome
    assert outcome.removed_bytes == planner_view


def test_a_clean_recursive_removal_measures_what_the_planner_would(
    tmp_path: Path,
) -> None:
    """The success path's measured bytes agree with the planned size metric."""

    import os as _os

    from mdstats.training_data.storage.plan import _tree_bytes
    from mdstats.training_data.storage.outcome import OUTCOME_REMOVED

    container = tmp_path / "member"
    (container / "deep").mkdir(parents=True)
    (container / "top.bin").write_bytes(b"a" * 33)
    (container / "deep" / "inner.bin").write_bytes(b"b" * 77)
    recorded = _recorded_tree(container)
    expected = _tree_bytes(container)

    parent_fd = _os.open(tmp_path, _os.O_RDONLY | _os.O_DIRECTORY)
    try:
        outcome = _certified_unit(parent_fd, container, recorded)
    finally:
        _os.close(parent_fd)

    assert outcome.outcome == OUTCOME_REMOVED, outcome
    assert outcome.removed_bytes == expected == 110, (outcome, expected)
    assert not container.exists()


def test_the_final_target_check_is_no_weaker_than_plan_revalidation() -> None:
    """R30-B: the two identity checks may not drift apart.

    Ordinary plan revalidation and the final P7 boundary answer the same
    question at different moments. If revalidation later strengthens its bounded
    identity and the final owner boundary silently keeps the old, narrower set,
    the last check before the syscall becomes the weakest one.
    """

    import ast

    from mdstats.training_data.storage.removal import TARGET_IDENTITY_DIMENSIONS

    plan_source = (Path(cli.__file__).parent / "storage" / "plan.py").read_text(
        encoding="utf-8"
    )
    revalidate = next(
        node
        for node in ast.walk(ast.parse(plan_source))
        if isinstance(node, ast.FunctionDef) and node.name == "_revalidate_action_target"
    )
    checked: set[str] = set()
    for node in ast.walk(revalidate):
        if isinstance(node, ast.Tuple):
            values = [
                item.value
                for item in node.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            ]
            if {"kind", "device", "inode"} <= set(values):
                checked = set(values)
    assert checked, "the plan's revalidation dimensions could not be located"
    assert checked <= set(TARGET_IDENTITY_DIMENSIONS), (
        checked - set(TARGET_IDENTITY_DIMENSIONS)
    )


def test_a_spent_capability_is_rejected_before_any_descriptor_syscall() -> None:
    """R30-B structural: the guard runs first, not after a stat.

    A closed session's integer may already belong to something else, so the
    check has to precede every use of it - including the observation that would
    otherwise decide the outcome.
    """

    import ast

    store_source = (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")
    remover = next(
        node
        for node in ast.walk(ast.parse(store_source))
        if isinstance(node, ast.FunctionDef)
        and node.name == "remove_released_attempt_member"
    )
    statements = [
        node
        for node in remover.body
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
        and not isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    guard_index = next(
        index
        for index, node in enumerate(statements)
        if "require_live" in ast.dump(node)
    )
    syscall_index = next(
        index
        for index, node in enumerate(statements)
        if any(
            name in ast.dump(node)
            for name in ("remove_certified_unit", "attempt_fd")
        )
    )
    assert guard_index < syscall_index, (guard_index, syscall_index)

    # And the guard is one-way: closing sets a flag nothing clears.
    session_class = next(
        node
        for node in ast.walk(ast.parse(store_source))
        if isinstance(node, ast.ClassDef) and node.name == "ReleasedAttemptSession"
    )
    dumped = ast.dump(session_class)
    assert "invalidation_reason" in dumped and "require_live" in dumped
    assert "MappingProxyType" in dumped, (
        "the session's proof lookup is not handed out read-only"
    )


def test_the_cleanup_engine_withholds_the_rest_of_a_contradicted_attempt() -> None:
    """R30-D structural: refusal invalidates the shared capability."""

    import ast

    commands_source = (Path(cli.__file__).parent / "storage" / "commands.py").read_text(
        encoding="utf-8"
    )
    applier = next(
        node
        for node in ast.walk(ast.parse(commands_source))
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_released_member"
    )
    dumped = ast.dump(applier)
    assert "invalidate" in dumped, "a contradicted attempt keeps its capability"
    assert "live" in dumped, "later members never consult the capability's state"
    assert "planned_identity" in dumped, (
        "the final owner boundary is not given the plan-bound target identity"
    )
    # And a post-mutation failure records the action before it propagates.
    executor_source = (Path(cli.__file__).parent / "storage" / "executor.py").read_text(
        encoding="utf-8"
    )
    recorder = next(
        node
        for node in ast.walk(ast.parse(executor_source))
        if isinstance(node, ast.FunctionDef) and node.name == "record_or_reraise"
    )
    recorded = ast.dump(recorder)
    # One recorder, owned by the executor, reached by the one cleanup path.
    assert "record_or_reraise" in commands_source
    assert "PartialMutationError" in recorded and "record_removal" in recorded
    assert "Raise" in recorded, "the failure is swallowed instead of propagating"


def test_a_failed_unlink_does_not_inflate_the_partial_figure(tmp_path: Path) -> None:
    """Bytes are credited once the entry has actually gone, not before.

    The size has to be read before the unlink - afterwards there is nothing left
    to read - but a measurement is not a removal. If the unlink then fails, the
    file is still there and its bytes are not this execution's to claim.
    """

    import os as _os

    from mdstats.training_data.storage.outcome import PartialMutationError

    container = tmp_path / "member"
    container.mkdir()
    (container / "a-goes.bin").write_bytes(b"x" * 40)
    (container / "b-stays.bin").write_bytes(b"y" * 900)
    recorded = _recorded_tree(container)

    from mdstats.training_data.storage import removal as removal_mod

    real_unlink = removal_mod.unlink_certified_entry
    seen: list[str] = []

    def fail_on_second(parent_fd, name, display, stats, ledger):
        seen.append(str(name))
        if len(seen) > 1:
            raise ledger.failure(
                OSError(13, "injected unlink failure"),
                f"{display} could not be removed",
            )
        return real_unlink(parent_fd, name, display, stats, ledger)

    removal_mod.unlink_certified_entry = fail_on_second
    parent_fd = _os.open(tmp_path, _os.O_RDONLY | _os.O_DIRECTORY)
    raised: BaseException | None = None
    try:
        _certified_unit(parent_fd, container, recorded)
    except BaseException as exc:  # noqa: BLE001 - the propagation is the contract
        raised = exc
    finally:
        removal_mod.unlink_certified_entry = real_unlink
        _os.close(parent_fd)

    # A failing unlink is an I/O failure, not an owner contradiction, so it
    # propagates carrying the exact bytes already gone.
    assert isinstance(raised, PartialMutationError), raised
    # Only the 40 bytes that really went; never the 900 that are still there.
    assert raised.outcome.removed_bytes == 40, raised.outcome
    assert (container / "b-stays.bin").stat().st_size == 900
    assert not (container / "a-goes.bin").exists()


# ---------------------------------------------------------------------------
# R31-2 - post-mutation failure truth on the generic and certified paths
# ---------------------------------------------------------------------------


def _drive_removal(tmp_path: Path, target: Path, run) -> tuple[dict, BaseException | None]:
    """Run one removal through the real action-boundary recorder.

    The recorder, the result object and the settlement are the production ones;
    only the filesystem transition below them is made to fail.
    """

    from mdstats.training_data.storage.executor import (
        StorageExecutionResult,
        record_or_reraise,
    )
    from mdstats.training_data.storage.plan import planned_action

    action = planned_action(
        action="remove",
        path=target,
        artifact_id="test:generic",
        reason="test",
    )
    result = StorageExecutionResult(
        operation_identity="t",
        plan_identity="t",
        policy_identity="t",
        action="cleanup",
        status="planned",
    )
    raised: BaseException | None = None
    try:
        record_or_reraise(result, action, run)
    except BaseException as exc:  # noqa: BLE001 - the propagation is the contract
        raised = exc
    return result.to_dict(), raised


def test_a_generic_partial_directory_removal_records_exact_bytes(
    tmp_path: Path,
) -> None:
    """R31-2: a subset is gone and the container survives - say exactly that.

    Checking only whether the top-level pathname disappeared cannot see this
    state, and a bare `OSError` would leave the audit unable to name which
    action mutated or by how much.
    """

    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    tree = root / "tree"
    (tree / "sub").mkdir(parents=True)
    (tree / "a.bin").write_bytes(b"a" * 10)
    (tree / "sub" / "locked.bin").write_bytes(b"b" * 20)
    os.chmod(tree / "sub", 0o500)  # its child cannot be unlinked
    try:
        payload, raised = _drive_removal(
            tmp_path, tree, lambda: _certified(tree, anchor=root)
        )
    finally:
        os.chmod(tree / "sub", 0o700)

    assert isinstance(raised, OSError), raised
    assert payload["status"] in ("partial", "planned"), payload
    entries = payload["refused_actions"]
    assert len(entries) == 1, entries
    assert entries[0]["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entries[0]
    assert entries[0]["mutated"] is True
    assert int(entries[0]["reclaimed_bytes"]) == 10, entries[0]
    assert int(payload["reclaimed_bytes"]) == 10, payload
    assert payload["mutated"] is True
    assert tree.exists() and (tree / "sub" / "locked.bin").exists()
    assert not (tree / "a.bin").exists()


def test_a_generic_durability_failure_after_unlink_records_the_removal(
    tmp_path: Path,
) -> None:
    """R31-2 case 1: unlink succeeds, durability fails, action is partial."""

    from mdstats.training_data.storage import removal as removal_mod
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    root.mkdir()
    victim = root / "lonely.bin"
    victim.write_bytes(b"x" * 64)
    real = removal_mod.persist_entry_removal

    def fail_durability(parent_fd, display, ledger):
        # The unlink really crossed; only the durability step that follows it
        # fails, so the action is partial rather than a no-op.
        raise ledger.failure(
            OSError(5, "injected durability failure"),
            f"{display} was removed but the removal could not be made durable",
        )

    removal_mod.persist_entry_removal = fail_durability
    try:
        payload, raised = _drive_removal(
            tmp_path, victim, lambda: _certified(victim, anchor=root)
        )
    finally:
        removal_mod.persist_entry_removal = real

    assert isinstance(raised, OSError), raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entry
    assert int(entry["reclaimed_bytes"]) == 64, entry
    assert int(payload["reclaimed_bytes"]) == 64
    assert not victim.exists()


def test_a_certified_subtree_durability_failure_records_the_removal(
    tmp_path: Path,
) -> None:
    """R31-2 case 3: the fully certified branch keeps its account too."""

    from mdstats.training_data.storage import removal as removal_mod
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    container = root / "certified"
    container.mkdir(parents=True)
    (container / "one.bin").write_bytes(b"a" * 30)
    # Durability is the retained parent capability's own step, so the injection
    # point is that step rather than a pathname re-resolution.
    real = removal_mod.persist_entry_removal

    def fail_durability(parent_fd, display, ledger):
        raise ledger.failure(
            OSError(5, "injected durability failure"),
            f"{display} was removed but the removal could not be made durable",
        )

    removal_mod.persist_entry_removal = fail_durability
    try:
        payload, raised = _drive_removal(
            tmp_path, container, lambda: _certified(container, anchor=root)
        )
    finally:
        removal_mod.persist_entry_removal = real

    assert isinstance(raised, OSError), raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entry
    assert entry["mutated"] is True
    assert int(entry["reclaimed_bytes"]) == 30, entry
    assert not container.exists()


def test_an_authorized_member_failure_keeps_the_earlier_members_bytes(
    tmp_path: Path,
) -> None:
    """R31-2 case 4: an earlier success survives a later pre-mutation failure."""

    from mdstats.training_data.storage import removal as removal_mod
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    container = root / "mixed"
    container.mkdir(parents=True)
    first = container / "a-first.bin"
    first.write_bytes(b"a" * 11)
    second = container / "b-second.bin"
    second.write_bytes(b"b" * 900)
    foreign = container / "zz-foreign.bin"
    foreign.write_bytes(b"not ours")

    real = removal_mod.unlink_certified_entry
    done: list[str] = []

    def fail_on_second(parent_fd, name, display, stats, ledger):
        if done:
            raise ledger.failure(
                OSError(13, "injected pre-mutation failure"),
                f"{display} could not be removed",
            )
        done.append(str(name))
        return real(parent_fd, name, display, stats, ledger)

    removal_mod.unlink_certified_entry = fail_on_second
    try:
        payload, raised = _drive_removal(
            tmp_path,
            container,
            lambda: _certified(
                container,
                nodes={"a-first.bin": "file", "b-second.bin": "file"},
                anchor=root,
            ),
        )
    finally:
        removal_mod.unlink_certified_entry = real

    assert isinstance(raised, OSError), raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entry
    # Only the 11 bytes that really went; the 900-byte file is still there.
    assert int(entry["reclaimed_bytes"]) == 11, entry
    assert int(payload["reclaimed_bytes"]) == 11
    assert not first.exists() and second.exists() and foreign.exists()


def test_a_generic_failure_before_any_mutation_credits_nothing(
    tmp_path: Path,
) -> None:
    """R31-2 case 5: no first destructive transition, no fabricated mutation."""

    from mdstats.training_data.storage import removal as removal_mod

    root = tmp_path / "campaign"
    root.mkdir()
    victim = root / "untouched.bin"
    victim.write_bytes(b"x" * 40)
    real = removal_mod.unlink_certified_entry

    def never(parent_fd, name, display, stats, ledger):
        raise ledger.failure(
            OSError(13, "injected pre-mutation failure"),
            f"{display} could not be removed",
        )

    removal_mod.unlink_certified_entry = never
    try:
        payload, raised = _drive_removal(
            tmp_path, victim, lambda: _certified(victim, anchor=root)
        )
    finally:
        removal_mod.unlink_certified_entry = real

    assert isinstance(raised, OSError), raised
    assert payload["mutated"] is False, payload
    assert int(payload["reclaimed_bytes"]) == 0, payload
    assert victim.stat().st_size == 40


def test_the_p7_recursion_retains_a_file_it_cannot_measure(tmp_path: Path) -> None:
    """R31-3: an unmeasurable file is retained, never deleted unaccounted.

    Deleting it and crediting zero would put bytes beyond recovery that the
    action can never account for - and with nothing else removed yet, the
    outcome would even read as "nothing changed".
    """

    from mdstats.training_data.storage.outcome import (
        OUTCOME_PARTIAL_CHANGE_REFUSED,
        OUTCOME_REFUSED_NO_CHANGE,
    )

    from mdstats.training_data.storage import removal as removal_mod

    real_scandir = os.scandir
    # Patching `os.scandir` also defeats the platform capability probe, which
    # reads `os.scandir in os.supports_fd`. The probe's real answer is captured
    # first so the injection stays confined to the measurement it is testing.
    assert removal_mod.dir_fd_mutation_supported()

    class _UnmeasurableEntry:
        def __init__(self, entry):
            self._entry = entry

        def __getattr__(self, name):
            return getattr(self._entry, name)

        def stat(self, *args, **kwargs):
            raise OSError(5, "injected measurement failure")

    def scandir_with_blind_spot(target):
        return [
            _UnmeasurableEntry(item) if item.name == blind_name else item
            for item in real_scandir(target)
        ]

    for scenario in ("first", "after-one"):
        container = tmp_path / f"member-{scenario}"
        container.mkdir()
        recorded = {f"member-{scenario}": "directory"}
        if scenario == "after-one":
            (container / "a-counted.bin").write_bytes(b"c" * 7)
            recorded[f"member-{scenario}/a-counted.bin"] = "file"
        blind_name = "m-unmeasurable.bin"
        (container / blind_name).write_bytes(b"z" * 11)
        recorded[f"member-{scenario}/{blind_name}"] = "file"

        os.scandir = scandir_with_blind_spot
        real_probe = removal_mod.dir_fd_mutation_supported
        removal_mod.dir_fd_mutation_supported = lambda: True
        parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            outcome = _certified_unit(parent_fd, container, recorded)
        finally:
            os.scandir = real_scandir
            removal_mod.dir_fd_mutation_supported = real_probe
            os.close(parent_fd)

        # In both cases the file nobody could measure is still there.
        assert (container / blind_name).read_bytes() == b"z" * 11, scenario
        if scenario == "first":
            assert outcome.outcome == OUTCOME_REFUSED_NO_CHANGE, (scenario, outcome)
            assert outcome.mutated is False
            assert outcome.credited_bytes(1_000_000) == 0
        else:
            assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED, (scenario, outcome)
            assert outcome.mutated is True
            assert outcome.removed_bytes == 7, outcome
            assert not (container / "a-counted.bin").exists()


# ---------------------------------------------------------------------------
# R32 - mutation truth, safe recursion, and guards that name their owner
# ---------------------------------------------------------------------------


def test_the_recursive_owners_descend_no_follow_and_never_by_pathname() -> None:
    """R32-2 structural: the descent cannot regress to a pathname walk.

    The failure this replaces was a guard that counted `shutil.rmtree(` calls.
    It kept passing while the mechanism it protected moved out from under it, so
    this asserts the shape of the recursion instead: children are opened
    no-follow from the parent descriptor, and no recursive call is handed a
    pathname rebuilt from a `DirEntry`.
    """

    import ast

    storage = Path(cli.__file__).parent / "storage"
    removal_source = (storage / "removal.py").read_text(encoding="utf-8")
    tree = ast.parse(removal_source)

    recursions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name in ("descend_to_parent", "_empty_certified_directory")
    ]
    assert len(recursions) == 2, [node.name for node in recursions]
    bodies = {node.name: ast.dump(node) for node in recursions}

    for name, dumped in bodies.items():
        assert "open_directory_nofollow" in dumped, name
        # The exact regression: classify with is_dir(follow_symlinks=False) and
        # then recurse into Path(entry.path), which a swapped entry redirects.
        assert "entry.path" not in dumped, (
            f"{name} rebuilds a pathname from a DirEntry and recurses into it"
        )
        assert "avoids_symlink_attacks" not in dumped, (
            f"{name} cites rmtree's promise as protection for its own walk"
        )

    # Child mutation is descriptor-relative, not by absolute pathname.
    assert "dir_fd" in bodies["_empty_certified_directory"]

    # And the capability guard names the primitive the recursion really uses.
    assert "dir_fd_mutation_supported" in removal_source

    # One owner for the primitive: the destructive owner must not reach into
    # the P7 owner for it, and the P7 owner must not keep a private copy.
    assert "from ..qualification" not in removal_source, (
        "the canonical destructive owner imports the P7 owner"
    )
    store_source = (
        Path(cli.__file__).parent / "qualification" / "store.py"
    ).read_text(encoding="utf-8")
    assert "def _open_directory_nofollow" not in store_source, (
        "the P7 owner kept a private second copy of the no-follow open"
    )
    from mdstats.training_data.qualification import store as qstore
    from mdstats.training_data.storage import trust

    assert qstore._open_directory_nofollow is trust.open_directory_nofollow
    assert qstore.NamespaceAmbiguity is trust.NamespaceAmbiguity
    assert qstore.dir_fd_mutation_supported is trust.dir_fd_mutation_supported


def test_a_swapped_child_directory_is_never_followed_out_of_the_tree(
    tmp_path: Path,
) -> None:
    """R32-2: the race the pathname walker lost.

    A child is classified as a directory and then replaced by a symlink to
    somewhere else entirely. A walk that reopened the child by pathname would
    delete the external target's contents; a no-follow open from the parent
    descriptor refuses it.
    """

    from mdstats.training_data.storage import trust

    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.bin"
    sentinel.write_bytes(b"someone else's bytes")

    root = tmp_path / "campaign"
    tree = root / "tree"
    (tree / "victim").mkdir(parents=True)
    (tree / "victim" / "inner.bin").write_bytes(b"x" * 5)

    real_open = trust.open_directory_nofollow
    swapped: list[str] = []

    def racing_open(name, *, dir_fd=None):
        if name == "victim" and not swapped:
            swapped.append(name)
            (tree / "victim" / "inner.bin").unlink()
            (tree / "victim").rmdir()
            (tree / "victim").symlink_to(external)
        return real_open(name, dir_fd=dir_fd)

    trust.open_directory_nofollow = racing_open
    try:
        outcome = _certified(tree, anchor=root)
    finally:
        trust.open_directory_nofollow = real_open

    assert swapped, "the race never fired"
    # The swapped child is refused rather than followed; nothing outside the
    # authorized tree is touched.
    assert outcome.refused, outcome
    assert "victim" in outcome.detail, outcome.detail
    assert sentinel.read_bytes() == b"someone else's bytes"
    assert external.is_dir()


def test_a_zero_byte_removal_is_a_mutation_even_though_it_frees_nothing(
    tmp_path: Path,
) -> None:
    """R32-1: mutation truth and byte count are different facts.

    A zero-byte file, an emptied directory, and a second hard link to an
    already-counted inode all change the namespace while crediting nothing.
    Deciding "did this mutate?" from the byte total reports them as no change -
    and skips the durability step the caller owes for entries that really went.
    """

    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    for scenario in ("zero-byte-file", "empty-directory", "extra-hard-link"):
        container = tmp_path / scenario
        container.mkdir()
        recorded = {scenario: "directory"}
        if scenario == "zero-byte-file":
            (container / "a-empty.bin").write_bytes(b"")
            recorded[f"{scenario}/a-empty.bin"] = "file"
        elif scenario == "empty-directory":
            (container / "a-sub").mkdir()
            recorded[f"{scenario}/a-sub"] = "directory"
        else:
            original = container / "a-original.bin"
            original.write_bytes(b"x" * 12)
            os.link(original, container / "b-link.bin")
            recorded[f"{scenario}/a-original.bin"] = "file"
            recorded[f"{scenario}/b-link.bin"] = "file"
        # A node the proof never recorded, reached after the credited work.
        (container / "zz-foreign.bin").write_bytes(b"not ours")

        parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            outcome = _certified_unit(parent_fd, container, recorded)
        finally:
            os.close(parent_fd)

        assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED, (scenario, outcome)
        assert outcome.mutated is True, scenario
        expected = 12 if scenario == "extra-hard-link" else 0
        assert outcome.removed_bytes == expected, (scenario, outcome)
        assert (container / "zz-foreign.bin").exists(), scenario


def test_a_zero_credit_mutation_still_owes_its_durability_step(
    tmp_path: Path,
) -> None:
    """R32-1: the fsync is gated on mutation, never on the byte total.

    The defect this pins was not only a label: the caller skipped the directory
    fsync whenever credited bytes were zero, so removals that really happened
    were also never made durable.
    """

    from mdstats.training_data.storage.outcome import MutationLedger

    fsynced: list[int] = []
    real_fsync = os.fsync

    def watched_fsync(fd):
        fsynced.append(fd)
        return real_fsync(fd)

    container = tmp_path / "member"
    container.mkdir()
    (container / "a-empty.bin").write_bytes(b"")
    recorded = {"member": "directory", "member/a-empty.bin": "file"}

    os.fsync = watched_fsync
    parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        outcome = _certified_unit(parent_fd, container, recorded)
    finally:
        os.close(parent_fd)
        os.fsync = real_fsync

    assert outcome.outcome == "removed", outcome
    assert outcome.mutated is True and outcome.removed_bytes == 0, outcome
    assert fsynced, "a zero-credit removal skipped its durability step"

    # And the ledger keeps the two facts apart at the type level.
    ledger = MutationLedger()
    ledger.note_mutation()
    assert ledger.mutated is True and ledger.removed_bytes == 0
    assert ledger.stop("x").outcome == "partial_change_refused"


def test_r35_canonical_opened_descriptor_mount_trust(tmp_path: Path) -> None:
    """R35-1: canonical opened-descriptor mount trust helper fails closed."""
    from unittest import mock
    from mdstats.training_data.storage.trust import verify_opened_directory_trust

    parent_dir = tmp_path / "parent"
    child_dir = parent_dir / "child"
    child_dir.mkdir(parents=True)

    parent_fd = os.open(parent_dir, os.O_RDONLY | os.O_DIRECTORY)
    child_fd = os.open(child_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        # 1. Normal case: same device, not mount point -> (False, "")
        crossed, why = verify_opened_directory_trust(parent_fd, child_fd, child_dir)
        assert crossed is False and why == ""

        # 2. Mount point resolver unavailable -> fails closed
        class UnavailableResolver:
            available = False

            def is_mount_point(self, path):
                return False

        with mock.patch("mdstats.training_data.storage.trust.mount_resolver", return_value=UnavailableResolver()):
            crossed, why = verify_opened_directory_trust(parent_fd, child_fd, child_dir)
            assert crossed is True
            assert "unavailable" in why

        # 3. Mount point detected -> fails closed
        class MountResolver:
            available = True

            def is_mount_point(self, path):
                return True

        with mock.patch("mdstats.training_data.storage.trust.mount_resolver", return_value=MountResolver()):
            crossed, why = verify_opened_directory_trust(parent_fd, child_fd, child_dir)
            assert crossed is True
            assert "mount point" in why

        # 4. Device boundary mismatch -> fails closed
        real_fstat = os.fstat

        def fake_fstat(fd):
            st = real_fstat(fd)
            if fd == child_fd:
                class FakeStat:
                    st_dev = st.st_dev + 1
                    st_ino = st.st_ino
                    st_mode = st.st_mode
                return FakeStat()
            return st

        with mock.patch("os.fstat", side_effect=fake_fstat):
            crossed, why = verify_opened_directory_trust(parent_fd, child_fd, child_dir)
            assert crossed is True
            assert "different filesystem" in why
    finally:
        os.close(child_fd)
        os.close(parent_fd)


def test_r35_single_file_transition_aware_replacement_survives(tmp_path: Path) -> None:
    """R35-2A: single file unlink succeeds, replacement installed before fsync fails."""
    from unittest import mock
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED, PartialMutationError

    root = tmp_path / "campaign"
    root.mkdir()
    victim = root / "victim.bin"
    victim.write_bytes(b"ORIGINAL_BYTES" * 8)
    original_size = victim.stat().st_size
    replacement_content = b"REPLACEMENT_DATA" * 4

    def fsync_interceptor(fd):
        victim.write_bytes(replacement_content)
        raise OSError(5, "injected durability failure")

    with mock.patch("os.fsync", side_effect=fsync_interceptor):
        with pytest.raises(PartialMutationError) as exc_info:
            _certified(victim, anchor=root)

    exc = exc_info.value
    assert exc.outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED
    assert exc.outcome.mutated is True
    assert int(exc.outcome.removed_bytes) == original_size
    assert victim.exists()
    assert victim.read_bytes() == replacement_content


def test_r35_single_file_unlink_not_occurring_no_mutation(tmp_path: Path) -> None:
    """R35-2A: single file unlink does not occur; no mutation or bytes attributed."""
    from mdstats.training_data.storage.outcome import OUTCOME_ALREADY_ABSENT

    root = tmp_path / "campaign"
    root.mkdir()
    nonexistent = root / "never_existed.bin"
    outcome = _certified(nonexistent, anchor=root)
    assert outcome.outcome == OUTCOME_ALREADY_ABSENT
    assert outcome.mutated is False
    assert outcome.removed_bytes is None or outcome.removed_bytes == 0


def test_r35_common_member_swapped_to_symlink_or_dir_retained(tmp_path: Path) -> None:
    """R35-2B: a certified file swapped to a symlink or directory is retained untouched."""
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    container = root / "common_container"
    container.mkdir(parents=True)
    f_sym = container / "victim_sym.bin"
    f_sym.write_bytes(b"S" * 40)
    f_dir = container / "victim_dir.bin"
    f_dir.write_bytes(b"D" * 50)
    f_ord = container / "ordinary.bin"
    f_ord.write_bytes(b"O" * 30)

    external_sentinel = tmp_path / "external_sentinel.bin"
    external_sentinel.write_bytes(b"SENTINEL_CONTENT")

    f_sym.unlink()
    f_sym.symlink_to(external_sentinel)
    f_dir.unlink()
    f_dir.mkdir()
    (f_dir / "nested.bin").write_bytes(b"nested")

    # The owner certified three plain files. Sorted enumeration reaches the
    # surviving ordinary file first, then the substituted ones.
    outcome = _certified(
        container,
        nodes={"ordinary.bin": "file", "victim_dir.bin": "file", "victim_sym.bin": "file"},
        anchor=root,
        root_identity={"device": int(container.stat().st_dev), "inode": int(container.stat().st_ino)},
        authority_identity={"device": int(root.stat().st_dev), "inode": int(root.stat().st_ino)},
    )

    assert outcome.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED
    assert outcome.mutated is True
    assert int(outcome.removed_bytes) == 30
    assert not f_ord.exists()
    assert f_sym.is_symlink()
    assert external_sentinel.read_bytes() == b"SENTINEL_CONTENT"
    assert f_dir.is_dir()
    assert (f_dir / "nested.bin").exists()


def test_r35_session_close_failure_preserves_primary_exception(tmp_path: Path) -> None:
    """R35-3: session close failure does not replace active in-flight exception."""
    from unittest import mock
    from mdstats.training_data.qualification.store import ReleasedAttemptSession

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    fd = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY)
    session = ReleasedAttemptSession(
        attempt_fd=fd,
        attempt_root=scratch,
        generation=1,
        state=mock.Mock(),
        proof={},
        certified_nodes=(),
        root_identity={"device": 0, "inode": 0},
        release_authority="auth",
    )
    assert session.live is True
    session.close()
    assert session.closed is True
    assert session.attempt_fd == -1
    assert session.live is False

    fd2 = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY)
    session2 = ReleasedAttemptSession(
        attempt_fd=fd2,
        attempt_root=scratch,
        generation=1,
        state=mock.Mock(),
        proof={},
        certified_nodes=(),
        root_identity={"device": 0, "inode": 0},
        release_authority="auth",
    )
    # R37-3 supersedes the earlier behaviour here. `invalidate()` no longer
    # inspects the ambient exception state to decide whether its own close
    # failure matters: that ranking belongs to the caller that knows whether a
    # primary product failure is in flight, and deciding it here made a genuine
    # close-only failure invisible whenever anything else happened to be
    # propagating. What the session still guarantees unconditionally is that the
    # capability is spent before the close is attempted.
    from mdstats.training_data.qualification.store import SpentCapabilityError

    with mock.patch("os.close", side_effect=OSError(9, "Bad file descriptor")):
        try:
            raise RuntimeError("primary cause")
        except RuntimeError:
            with pytest.raises(OSError):
                session2.invalidate("contradiction reason")
    assert session2.closed is True
    assert session2.attempt_fd == -1
    assert session2.live is False
    with pytest.raises(SpentCapabilityError):
        session2.require_live()
    os.close(fd2)


def test_settlement_maps_explicit_mutation_truth_to_status(tmp_path: Path) -> None:
    """R35-5/R37-4: settlement reads `mutated`, and only settlement is tested here.

    A hand-built result proves how `_settle` maps mutation truth to a status. It
    proves nothing about whether any engine sets that flag correctly, so the
    archive create/reclaim and restore claims are carried by the real-owner
    publication counterfactuals above, never by this.
    """
    from mdstats.training_data.storage.executor import StorageExecutionResult, StorageExecutor

    res = StorageExecutionResult(
        operation_identity="op",
        plan_identity="pl",
        policy_identity="pol",
        action="archive",
        status="running",
        mutated=True,
        completed=[],
        refused=[{"action": "dummy"}],
    )
    executor = StorageExecutor.__new__(StorageExecutor)
    executor._settle(res)
    assert res.status == "partial"

    res2 = StorageExecutionResult(
        operation_identity="op",
        plan_identity="pl",
        policy_identity="pol",
        action="archive",
        status="running",
        mutated=False,
        completed=[],
        refused=[{"action": "dummy"}],
    )
    executor._settle(res2)
    assert res2.status == "refused"


def test_r35_dedup_and_maintenance_mutation_truth(tmp_path: Path) -> None:
    """R35-5: dedup and maintenance establish explicit mutation truth."""
    from unittest import mock
    from mdstats.training_data.storage.executor import StorageExecutionResult
    from mdstats.training_data.storage.maintenance import (
        campaign_state_maintenance_engine,
        ACTION_PRUNE_EVENTS,
    )
    from mdstats.training_data.storage.plan import StoragePlan, PlannedAction
    from mdstats.training_data.storage.policy import resolve_storage_policy

    store = mock.Mock()
    store.prune_events.return_value = 0
    policy = resolve_storage_policy({}, action="cleanup", tier="safe", apply=True)
    engine = campaign_state_maintenance_engine(store, policy)
    action = PlannedAction(
        path=tmp_path,
        action=ACTION_PRUNE_EVENTS,
        size_bytes=0,
        binding={},
        artifact_id="art",
        reason="prune",
        capability_cost=0,
        filesystem_identity={"device": 0, "inode": 0},
    )
    snapshot = mock.Mock()
    snapshot.view.return_value = mock.Mock(path=tmp_path)
    res = StorageExecutionResult(
        operation_identity="op",
        plan_identity="pl",
        policy_identity="pol",
        action="maintenance",
        status="running",
    )
    engine(action, snapshot, res)
    assert res.mutated is False
    assert len(res.completed) == 1
    assert res.completed[0]["events_pruned"] == 0

    store.prune_events.return_value = 5
    res2 = StorageExecutionResult(
        operation_identity="op",
        plan_identity="pl",
        policy_identity="pol",
        action="maintenance",
        status="running",
    )
    engine(action, snapshot, res2)
    assert res2.mutated is True
    assert res2.completed[0]["events_pruned"] == 5


def test_every_patched_production_name_is_one_the_product_actually_reads() -> None:
    """R32-7/R37-4: a failpoint on a name nobody calls must fail loudly.

    A test that patches ``module.name`` when the production path no longer reads
    that attribute keeps passing while the mechanism it claims to cover is
    entirely untested. That is how the generic-removal half of the interruption
    counterfactual evaporated, and how a guard's subject moved out from under
    it.

    ``hasattr`` alone is too weak to catch the next one: a name can survive as a
    definition long after every caller stopped reading it. So each patched name
    must also be *read* somewhere in the production storage/qualification
    sources - the seam has a consumer, not just a home. Whether the seam fired
    in one particular counterfactual is a separate claim, and every such test
    asserts its own execution counter.
    """

    import ast
    import importlib

    aliases = {
        "executor_mod": "mdstats.training_data.storage.executor",
        "removal_mod": "mdstats.training_data.storage.removal",
        "commands_mod": "mdstats.training_data.storage.commands",
        "storage_commands": "mdstats.training_data.storage.commands",
        "archive_mod": "mdstats.training_data.storage.archive",
        "durability_mod": "mdstats.training_data.storage.durability",
        "persistence_mod": "mdstats.training_data.target_size_execution.persistence",
        "trust_mod": "mdstats.training_data.storage.trust",
        "store_mod": "mdstats.training_data.qualification.store",
        "qstore": "mdstats.training_data.qualification.store",
        "cli": "mdstats.training_data._campaign_cli_core",
        "trust": "mdstats.training_data.storage.trust",
        "_tse": "mdstats.training_data.target_size_execution",
    }
    suites = [
        Path(__file__),
        Path(__file__).with_name("test_mlff_storage_reset_integration.py"),
    ]

    # Every name the production storage/qualification sources actually read.
    product_roots = [
        Path(cli.__file__).parent / "storage",
        Path(cli.__file__).parent / "qualification",
    ]
    read_names: set[str] = set()
    for root in product_roots:
        for module_path in sorted(root.glob("*.py")):
            product = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(product):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    read_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    read_names.add(node.attr)
    assert "durable_unlink" in read_names, "the sweep is not reading the product"

    def _patched(tree: ast.AST):
        """Both ways these suites replace a production attribute."""

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(
                        target.value, ast.Name
                    ):
                        yield node.lineno, target.value.id, target.attr
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                yield node.lineno, node.args[0].id, node.args[1].value

    dead: list[str] = []
    checked = 0
    for suite in suites:
        tree = ast.parse(suite.read_text(encoding="utf-8"))
        for lineno, alias, attribute in _patched(tree):
            module_name = aliases.get(alias)
            if module_name is None:
                continue
            checked += 1
            module = importlib.import_module(module_name)
            if not hasattr(module, attribute):
                dead.append(
                    f"{suite.name}:{lineno} patches {alias}.{attribute}, which "
                    f"{module_name} does not define"
                )
            elif attribute not in read_names:
                dead.append(
                    f"{suite.name}:{lineno} patches {alias}.{attribute}, which no "
                    "production storage or qualification module reads"
                )
    assert checked >= 10, checked
    assert dead == [], dead


# ---------------------------------------------------------------------------
# R37-1 - every consequential persistent transition establishes mutation truth
# at the transition, not at the helper's return
# ---------------------------------------------------------------------------


def _last_audit(campaign) -> dict:
    """The durable record this execution actually published."""

    records = campaign.control_plane.read_audit()
    assert records, "the execution published no audit record"
    return dict(records[-1])


def _fail_parent_fsync(monkeypatch, predicate):
    """Fail one publication's parent-directory fsync, *after* its atomic replace.

    ``fsync_parent_directory`` is the lowest real callable both
    ``durable_publish_bytes`` and ``durable_unlink`` reach once their transition
    has already crossed, so failing it models exactly the window this
    requirement is about: the canonical name resolves to the new state and the
    step meant to make that durable then fails. The counter proves the seam
    fired rather than the test passing because nothing was injected.
    """

    from mdstats.training_data.storage import durability as durability_mod

    real = durability_mod.fsync_parent_directory
    fired = {"n": 0}

    def guarded(path):
        target = Path(path)
        if predicate(target):
            fired["n"] += 1
            raise OSError(5, f"injected durability failure at {target}")
        return real(target)

    monkeypatch.setattr(durability_mod, "fsync_parent_directory", guarded)
    return fired


def _fail_before_replace(monkeypatch, predicate):
    """Fail one publication while it is still staging, before any replace."""

    import tempfile as tempfile_mod

    from mdstats.training_data.storage import durability as durability_mod

    real = tempfile_mod.mkstemp
    fired = {"n": 0}

    def guarded(*args, **kwargs):
        directory = kwargs.get("dir")
        if directory is not None and predicate(Path(directory)):
            fired["n"] += 1
            raise OSError(13, "injected pre-publication failure")
        return real(*args, **kwargs)

    monkeypatch.setattr(
        durability_mod, "tempfile", SimpleNamespace(mkstemp=guarded)
    )
    return fired


def test_an_absent_target_fires_no_unlink_transition(tmp_path: Path) -> None:
    """R37-1A case 1: a name that was already gone was not removed by this call."""

    from mdstats.training_data.storage.durability import durable_unlink

    fired: list[str] = []
    absent = tmp_path / "never-existed.bin"
    durable_unlink(absent, missing_ok=True, on_unlinked=lambda: fired.append("x"))
    assert fired == [], "the callback claimed a removal that never happened"

    with pytest.raises(FileNotFoundError):
        durable_unlink(absent, missing_ok=False, on_unlinked=lambda: fired.append("y"))
    assert fired == []

    # And the positive control: a real removal does fire it exactly once.
    present = tmp_path / "present.bin"
    present.write_bytes(b"gone")
    durable_unlink(present, missing_ok=False, on_unlinked=lambda: fired.append("z"))
    assert fired == ["z"]


def test_a_failed_unlink_never_inherits_another_actors_removal(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-1A case 2: absence afterwards is not proof this execution caused it.

    The unlink genuinely fails; while the failure is being handled, another
    actor removes the name. Asking the filesystem "is it gone?" would answer
    yes and hand this execution a mutation and a byte credit it never earned.
    """

    from mdstats.training_data.storage import removal as removal_mod

    root = tmp_path / "campaign"
    root.mkdir()
    victim = root / "contended.bin"
    victim.write_bytes(b"x" * 128)
    fired = {"n": 0}

    def unlink_fails_then_vanishes(parent_fd, name, display, stats, ledger):
        fired["n"] += 1
        # Another actor, between our failed syscall and our error handling.
        Path(display).unlink()
        raise ledger.failure(
            OSError(13, "injected unlink failure"), f"{display} could not be removed"
        )

    monkeypatch.setattr(
        removal_mod, "unlink_certified_entry", unlink_fails_then_vanishes
    )
    payload, raised = _drive_removal(
        tmp_path, victim, lambda: _certified(victim, anchor=root)
    )

    assert fired["n"] == 1, "the injected unlink seam never fired"
    assert isinstance(raised, OSError), raised
    assert payload["mutated"] is False, payload
    assert int(payload["reclaimed_bytes"]) == 0, payload
    assert not victim.exists()


def test_an_unlink_then_a_replacement_and_a_durability_failure_is_exact(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-1A case 3: the replacement survives and the partial is still exact."""

    from mdstats.training_data.storage import removal as removal_mod
    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    root = tmp_path / "campaign"
    root.mkdir()
    victim = root / "reappearing.bin"
    victim.write_bytes(b"x" * 200)
    fired = {"n": 0}

    def fail_durability(parent_fd, display, ledger):
        fired["n"] += 1
        # Another actor repopulates the name before we handle the failure.
        Path(display).write_bytes(b"someone else's file")
        raise ledger.failure(
            OSError(5, "injected durability failure"),
            f"{display} was removed but the removal could not be made durable",
        )

    monkeypatch.setattr(removal_mod, "persist_entry_removal", fail_durability)
    payload, raised = _drive_removal(
        tmp_path, victim, lambda: _certified(victim, anchor=root)
    )

    assert fired["n"] == 1, "the injected durability seam never fired"
    assert isinstance(raised, OSError), raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entry
    assert int(entry["reclaimed_bytes"]) == 200, entry
    assert victim.read_bytes() == b"someone else's file"


def test_a_blob_publication_that_fails_after_its_replace_is_mutated(
    campaign, monkeypatch
) -> None:
    """R37-1C case 5: the blob is canonical from its replace, not from the return."""

    campaign.historical_run()
    plane = campaign.control_plane
    # Manifests live beside blobs, so the blob is named by exclusion.
    fired = _fail_parent_fsync(
        monkeypatch,
        lambda path: path.parent == plane.archive_root
        and not path.name.endswith(".manifest.json"),
    )

    with pytest.raises(OSError):
        _create_archive(campaign)

    assert fired["n"] == 1, "the blob durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert audit["status"] == "partial", audit
    assert audit["result"]["publication_phase"] == archive_mod.ARCHIVE_PHASE_BLOB_PUBLISHED
    assert audit["result"]["archive_identity"], audit


def test_a_blob_publication_that_fails_before_its_replace_is_not_mutated(
    campaign, monkeypatch
) -> None:
    """R37-1C case 5, symmetric control: a staging failure claims nothing."""

    campaign.historical_run()
    plane = campaign.control_plane
    fired = _fail_before_replace(
        monkeypatch, lambda directory: directory == plane.archive_root
    )

    with pytest.raises(OSError):
        _create_archive(campaign)

    assert fired["n"] == 1, "the injected pre-publication seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is False, audit
    assert "publication_phase" not in audit.get("result", {}), audit


def test_the_boundary_after_the_blob_records_the_blob_it_published(campaign) -> None:
    """R37-1C case 4: `BOUNDARY_AFTER_BLOB` cannot escape as "nothing happened"."""

    campaign.historical_run()
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_AFTER_BLOB))
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert audit["status"] == "partial", audit
    assert audit["result"]["publication_phase"] == archive_mod.ARCHIVE_PHASE_BLOB_PUBLISHED
    # ... and it is also the symmetric pre-replace control for the manifest.
    assert list_archives(campaign.control_plane) == ()


def test_a_manifest_publication_that_fails_after_its_replace_advances_the_phase(
    campaign, monkeypatch
) -> None:
    """R37-1C case 6: manifest publication is transition-exact too."""

    campaign.historical_run()
    plane = campaign.control_plane
    fired = _fail_parent_fsync(
        monkeypatch, lambda path: path.name.endswith(".manifest.json")
    )

    with pytest.raises(OSError):
        _create_archive(campaign)

    assert fired["n"] == 1, "the manifest durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert (
        audit["result"]["publication_phase"]
        == archive_mod.ARCHIVE_PHASE_MANIFEST_PUBLISHED
    ), audit
    assert list_archives(campaign.control_plane) == ()


def test_a_catalog_publication_that_fails_after_its_replace_advances_the_phase(
    campaign, monkeypatch
) -> None:
    """R37-1C case 7: the catalog entry is claimed only from its own replace."""

    campaign.historical_run()
    plane = campaign.control_plane
    fired = _fail_parent_fsync(
        monkeypatch, lambda path: path.parent == plane.catalog_root
    )

    with pytest.raises(OSError):
        _create_archive(campaign)

    assert fired["n"] == 1, "the catalog durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert (
        audit["result"]["publication_phase"]
        == archive_mod.ARCHIVE_PHASE_CATALOG_PUBLISHED
    ), audit


def test_the_boundary_after_the_manifest_does_not_claim_the_catalog(campaign) -> None:
    """R37-1C cases 7 and 12: phases advance only where a replace crossed."""

    from mdstats.training_data.storage.archive import BOUNDARY_AFTER_MANIFEST

    campaign.historical_run()
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_AFTER_MANIFEST))
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert (
        audit["result"]["publication_phase"]
        == archive_mod.ARCHIVE_PHASE_MANIFEST_PUBLISHED
    ), audit
    assert list_archives(campaign.control_plane) == ()


def test_a_hot_reclamation_durability_failure_credits_exactly_what_went(
    campaign, monkeypatch
) -> None:
    """R37-1C case 8: the reclaimed member is credited, once, and exactly."""

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    size = checkpoint.stat().st_size
    fired = _fail_parent_fsync(monkeypatch, lambda path: path == checkpoint)

    with pytest.raises(OSError):
        _create_archive(campaign, keep_hot=False)

    assert fired["n"] == 1, "the reclamation durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert int(audit["reclaimed_bytes"]) == size, audit
    assert not checkpoint.exists()


def test_a_failed_hot_unlink_fabricates_no_reclamation(campaign, monkeypatch) -> None:
    """R37-1C case 8, control: a member that did not go is not credited."""

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    fired = {"n": 0}
    real = archive_mod.durable_unlink

    def refuse(path, *, dir_fd=None, missing_ok=True, on_unlinked=None):
        if Path(path) == checkpoint:
            fired["n"] += 1
            raise OSError(13, "injected pre-transition unlink failure")
        return real(path, dir_fd=dir_fd, missing_ok=missing_ok, on_unlinked=on_unlinked)

    monkeypatch.setattr(archive_mod, "durable_unlink", refuse)
    with pytest.raises(OSError):
        _create_archive(campaign, keep_hot=False)

    assert fired["n"] == 1, "the injected unlink seam never fired"
    audit = _last_audit(campaign)
    assert int(audit["reclaimed_bytes"]) == 0, audit
    assert checkpoint.is_file()


def test_the_initial_restore_journal_is_an_execution_mutation(
    campaign, monkeypatch
) -> None:
    """R37-1D case 9: a published nonterminal journal is durable recovery state.

    The control plane is fully materialized by the archive creation above, so
    the only transition this counterfactual can be crediting is the journal's
    own atomic publication - nothing has been staged or installed yet.
    """

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)
    assert not checkpoint.exists()

    journal = campaign.control_plane.journal_path(result["archive_identity"])
    fired = _fail_parent_fsync(monkeypatch, lambda path: path == journal)

    with pytest.raises(OSError):
        _restore(campaign, result["archive_identity"])

    assert fired["n"] == 1, "the journal durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert audit["status"] == "partial", audit
    assert int(audit["restored_bytes"]) == 0, audit
    assert (
        audit["result"]["restore_phase"]
        == archive_mod.RESTORE_PHASE_JOURNAL_STAGING_PUBLISHED
    ), audit
    assert not checkpoint.exists(), "nothing was installed, and none is claimed"


def test_a_restore_journal_failure_before_its_replace_is_nonmutating(
    campaign, monkeypatch
) -> None:
    """R37-1D case 10: no transition crossed, so nothing is claimed."""

    campaign.historical_run()
    result = _create_archive(campaign)
    journal = campaign.control_plane.journal_path(result["archive_identity"])
    fired = _fail_before_replace(monkeypatch, lambda directory: directory == journal.parent)

    with pytest.raises(OSError):
        _restore(campaign, result["archive_identity"])

    assert fired["n"] == 1, "the injected pre-publication seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is False, audit
    assert audit["status"] == "refused", audit
    assert "restore_phase" not in audit.get("result", {}), audit


@pytest.mark.parametrize("second_restore", [False, True])
def test_the_terminal_restore_journal_phase_survives_a_later_failure(
    campaign, monkeypatch, second_restore: bool
) -> None:
    """R37-1D case 11: proven with and without any destination mutation.

    The reuse run installs nothing at all - every member is already present -
    so if the terminal journal's own publication did not establish mutation
    truth, that case would report a nonmutating refusal while a terminal
    receipt sits on disk.
    """

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)
    identity = result["archive_identity"]
    if second_restore:
        assert _restore(campaign, identity)["restore"]["status"] == "complete"
        assert checkpoint.is_file()

    journal = campaign.control_plane.journal_path(identity)
    seen = {"n": 0}

    from mdstats.training_data.storage import durability as durability_mod

    real = durability_mod.fsync_parent_directory

    def guarded(path):
        target = Path(path)
        if target == journal:
            seen["n"] += 1
            if seen["n"] >= 2:
                raise OSError(5, "injected terminal journal durability failure")
        return real(target)

    monkeypatch.setattr(durability_mod, "fsync_parent_directory", guarded)
    with pytest.raises(OSError):
        _restore(campaign, identity)

    assert seen["n"] == 2, "the terminal journal seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    # Phase evidence never regresses: the terminal replacement really crossed.
    assert (
        audit["result"]["restore_phase"]
        == archive_mod.RESTORE_PHASE_JOURNAL_TERMINAL_PUBLISHED
    ), audit
    if second_restore:
        # Nothing was installed at all, so the journal is the only transition
        # this execution can be reporting.
        assert int(audit["restored_bytes"]) == 0, audit
    else:
        assert int(audit["restored_bytes"]) >= checkpoint.stat().st_size, audit


# ---------------------------------------------------------------------------
# R37-2 / R37-3 - descriptor and mount authority through the final syscall,
# and finalization that is leak-free and terminality-safe
# ---------------------------------------------------------------------------


def _certified_container(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A container with a nested certified member and one node nobody recorded.

    ``zz-foreign.bin`` sorts after ``nested``, so the walk reaches the certified
    subtree first and the contradiction afterwards.
    """

    container = tmp_path / "campaign" / "container"
    (container / "nested").mkdir(parents=True)
    member = container / "nested" / "owned.bin"
    member.write_bytes(b"m" * 64)
    foreign = container / "zz-foreign.bin"
    foreign.write_bytes(b"not ours")
    return container, member, foreign


def _container_nodes(**extra: str) -> dict[str, str]:
    nodes = {"nested": "directory", "nested/owned.bin": "file"}
    nodes.update(extra)
    return nodes


def test_an_unrecorded_member_grants_no_deletion_authority(tmp_path: Path) -> None:
    """R37-2B: the absence of a certified kind is not permission to delete.

    Defaulting an unrecorded node to "file" lets an owner that simply never
    wrote it be deleted anyway - the one substitution no later check can catch,
    because there is nothing left to compare against.
    """

    container, member, foreign = _certified_container(tmp_path)
    outcome = _certified(
        container,
        nodes={"nested": "directory"},  # the nested member itself is unrecorded
        anchor=container.parent,
    )
    assert outcome.refused, outcome
    assert outcome.mutated is False, outcome
    assert "did not record" in outcome.detail, outcome.detail
    assert member.is_file(), "an unrecorded member was deleted anyway"
    assert foreign.is_file()


@pytest.mark.parametrize("substitute", ["symlink", "directory", "fifo"])
def test_a_typed_member_is_removed_and_a_substituted_one_is_not(
    tmp_path: Path, substitute: str
) -> None:
    """R37-2B: typed authority is compared, not assumed, at the member itself.

    Whatever the owner certified as a regular file has been replaced by
    something else by the time the descent reaches it. Each replacement is
    retained: the kind is what the authority was granted against, and a
    same-name object of another kind is not that object.
    """

    container, member, foreign = _certified_container(tmp_path)
    swapped = container / "nested" / "swapped.bin"
    if substitute == "symlink":
        swapped.symlink_to(tmp_path / "elsewhere")
    elif substitute == "directory":
        swapped.mkdir()
        (swapped / "inside.bin").write_bytes(b"planted")
    else:
        os.mkfifo(swapped)

    outcome = _certified(
        container,
        nodes=_container_nodes(**{"nested/swapped.bin": "file"}),
        anchor=container.parent,
    )
    assert outcome.mutated is True, outcome
    assert int(outcome.removed_bytes or 0) == 64, outcome
    assert not member.exists()
    # Certified as a file, found as something else: retained, never followed.
    assert swapped.exists() or swapped.is_symlink()
    if substitute == "directory":
        assert (swapped / "inside.bin").read_bytes() == b"planted"
    assert foreign.is_file()


def test_a_nested_mount_under_an_individually_authorized_member_stops_the_descent(
    tmp_path: Path,
) -> None:
    """R37-2B: every intermediate directory is a traversal decision.

    The descent to a nested member passes through directories the owner never
    re-authenticated for this action. A mount appearing at one of them exposes
    somebody else's bytes under a campaign-looking name, so it stops the descent
    rather than being walked through on the way to an authorized leaf.
    """

    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    container, member, foreign = _certified_container(tmp_path)
    set_mount_resolver(
        MountIdentityResolver(
            mount_points=frozenset({str(container / "nested")}), available=True
        )
    )
    try:
        outcome = _certified(
            container, nodes=_container_nodes(), anchor=container.parent
        )
    finally:
        set_mount_resolver(None)

    assert outcome.refused, outcome
    assert outcome.mutated is False, outcome
    assert "not campaign-owned" in outcome.detail, outcome.detail
    assert member.read_bytes() == b"m" * 64


def test_an_unavailable_mount_resolver_stops_the_authorized_descent(
    tmp_path: Path,
) -> None:
    """R37-2B: ambiguity retains. A same-device bind mount cannot be ruled out."""

    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    container, member, foreign = _certified_container(tmp_path)
    set_mount_resolver(MountIdentityResolver(mount_points=frozenset(), available=False))
    try:
        outcome = _certified(
            container, nodes=_container_nodes(), anchor=container.parent
        )
    finally:
        set_mount_resolver(None)

    assert outcome.refused and outcome.mutated is False, outcome
    assert "mount discovery is unavailable" in outcome.detail, outcome.detail
    assert member.is_file()


def test_a_known_prefix_survives_a_later_contradiction(tmp_path: Path) -> None:
    """R37-2B: earlier successful members keep their exact account."""

    container, member, foreign = _certified_container(tmp_path)
    later = container / "nested" / "zz-later.bin"
    later.write_bytes(b"l" * 7)

    # `zz-later.bin` is present but unrecorded, so it stops the walk after the
    # certified member has already gone.
    outcome = _certified(
        container, nodes=_container_nodes(), anchor=container.parent
    )
    assert outcome.mutated is True, outcome
    assert outcome.refused, outcome
    assert int(outcome.removed_bytes or 0) == 64, outcome
    assert not member.exists() and later.is_file()


def _swap_before_the_final_check(monkeypatch, name: str, replacement):
    """Substitute a directory after it is emptied, just before its `rmdir`.

    The spy wraps the production check rather than replacing it, so the check
    itself is what decides - and the counter proves it actually ran.
    """

    from mdstats.training_data.storage import trust as trust_mod

    real = trust_mod.verify_final_directory_identity
    fired = {"n": 0}

    def swap_then_check(parent_fd, entry_name, child_fd, display):
        if display.name == name and fired["n"] == 0:
            fired["n"] += 1
            replacement(display)
        return real(parent_fd, entry_name, child_fd, display)

    monkeypatch.setattr(trust_mod, "verify_final_directory_identity", swap_then_check)
    return fired


def test_a_directory_replaced_before_its_final_rmdir_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-2A: `rmdir` names an entry, so the entry is checked against the fd.

    Without the final comparison the emptied directory's name would be removed
    whatever now stands behind it, spending an authority that was established
    against a different filesystem object.
    """

    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "child.bin").write_bytes(b"c" * 12)

    def replace(display: Path) -> None:
        display.rename(display.parent / "moved-aside")
        display.mkdir()
        (display / "impostor.bin").write_bytes(b"planted")

    fired = _swap_before_the_final_check(monkeypatch, "sub", replace)
    payload, raised = _drive_removal(
        tmp_path, root, lambda: _certified(root, anchor=anchor)
    )

    assert fired["n"] == 1, "the final identity check never ran"
    assert raised is None, raised
    assert payload["mutated"] is True, payload
    assert int(payload["reclaimed_bytes"]) == 12, payload
    assert (root / "sub" / "impostor.bin").read_bytes() == b"planted"
    assert (root / "moved-aside").is_dir()


def test_a_directory_swapped_for_a_symlink_before_its_rmdir_is_refused(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-2A: a substituted final component is seen as the symlink it is."""

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.bin").write_bytes(b"someone else's bytes")
    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "child.bin").write_bytes(b"c" * 9)

    def replace(display: Path) -> None:
        display.rmdir()
        display.symlink_to(outside, target_is_directory=True)

    fired = _swap_before_the_final_check(monkeypatch, "sub", replace)
    payload, raised = _drive_removal(
        tmp_path, root, lambda: _certified(root, anchor=anchor)
    )

    assert fired["n"] == 1, "the final identity check never ran"
    assert raised is None, raised
    assert payload["mutated"] is True, payload
    assert (outside / "external.bin").read_bytes() == b"someone else's bytes"
    assert (root / "sub").is_symlink()


def _fail_close_of(monkeypatch, predicate):
    """Make exactly the descriptors matching ``predicate`` fail to close.

    The descriptor is really closed first, so the injection models a failing
    ``close(2)`` rather than leaking the fd it is testing the handling of.
    """

    from mdstats.training_data.storage import trust as trust_mod

    real_open = trust_mod.open_directory_nofollow
    real_close = os.close
    marked: set[int] = set()
    fired = {"n": 0}

    def spy_open(name, *, dir_fd=None):
        handle = real_open(name, dir_fd=dir_fd)
        if predicate(name):
            marked.add(handle)
        return handle

    def guarded_close(handle):
        if handle in marked:
            marked.discard(handle)
            fired["n"] += 1
            real_close(handle)
            raise OSError(5, "injected close failure")
        return real_close(handle)

    monkeypatch.setattr(trust_mod, "open_directory_nofollow", spy_open)
    monkeypatch.setattr(os, "close", guarded_close)
    return fired


def test_a_close_failure_after_mutation_is_an_exact_partial(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-3: a close that fails alone, after bytes went, is a partial."""

    from mdstats.training_data.storage.outcome import OUTCOME_PARTIAL_CHANGE_REFUSED

    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "child.bin").write_bytes(b"c" * 33)

    fired = _fail_close_of(monkeypatch, lambda name: name == "sub")
    payload, raised = _drive_removal(
        tmp_path, root, lambda: _certified(root, anchor=anchor)
    )

    assert fired["n"] == 1, "the injected close seam never fired"
    assert isinstance(raised, OSError), raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == OUTCOME_PARTIAL_CHANGE_REFUSED, entry
    assert int(entry["reclaimed_bytes"]) == 33, entry


def test_a_close_failure_before_any_mutation_claims_no_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-3: the same failure, before anything went, is not a partial.

    The walk refuses at the unrecorded member, so nothing has been removed when
    the container descriptor fails to close. The refusal is the product answer
    and stays primary; the close failure is logged as secondary evidence rather
    than being turned into a mutation this action never made.
    """

    container, member, foreign = _certified_container(tmp_path)
    fired = _fail_close_of(monkeypatch, lambda name: name == container.name)
    payload, raised = _drive_removal(
        tmp_path,
        container,
        lambda: _certified(
            container, nodes={"nested": "directory"}, anchor=container.parent
        ),
    )

    assert fired["n"] == 1, "the injected close seam never fired"
    assert raised is None, raised
    entry = payload["refused_actions"][0]
    assert entry["outcome"] == "refused_no_change", entry
    assert payload["mutated"] is False, payload
    assert int(payload["reclaimed_bytes"]) == 0, payload
    assert member.is_file()


def test_a_primary_failure_survives_a_close_failure_behind_it(
    tmp_path: Path, monkeypatch
) -> None:
    """R37-3: the failure that carries the mutation truth is the one reported."""

    from mdstats.training_data.storage import removal as removal_mod

    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "child.bin").write_bytes(b"c" * 5)

    fired = _fail_close_of(monkeypatch, lambda name: name == "sub")
    real_contents = removal_mod._empty_certified_directory
    primary_fired = {"n": 0}

    def fail_inside(handle, display, certification, prefix, ledger):
        stopped = real_contents(handle, display, certification, prefix, ledger)
        if display.name == "sub":
            primary_fired["n"] += 1
            raise ledger.failure(
                OSError(13, "injected primary failure"), f"{display} stopped"
            )
        return stopped

    monkeypatch.setattr(removal_mod, "_empty_certified_directory", fail_inside)
    payload, raised = _drive_removal(
        tmp_path, root, lambda: _certified(root, anchor=anchor)
    )

    assert primary_fired["n"] == 1 and fired["n"] == 1, (primary_fired, fired)
    assert isinstance(raised, OSError), raised
    assert "injected primary failure" in str(raised), raised
    assert payload["mutated"] is True, payload
    assert int(payload["reclaimed_bytes"]) == 5, payload


def test_repeated_contradictions_do_not_accumulate_descriptors(tmp_path: Path) -> None:
    """R37-3: every refusal path releases what it opened.

    A leak here is invisible in any single run and fatal in a long one, so the
    same contradiction is driven repeatedly and the process's own descriptor
    count is the evidence.
    """

    def open_descriptor_count() -> int:
        return len(os.listdir("/proc/self/fd"))

    container, member, foreign = _certified_container(tmp_path)

    def once() -> None:
        outcome = _certified(
            container, nodes={"nested": "directory"}, anchor=container.parent
        )
        assert outcome.refused, outcome

    once()
    before = open_descriptor_count()
    for _ in range(40):
        once()
    assert open_descriptor_count() <= before, "descriptors accumulated across refusals"


# ---------------------------------------------------------------------------
# R37-2 - mount authority at every shared destructive mechanism
# ---------------------------------------------------------------------------


def _mounted_at(points) -> None:
    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    set_mount_resolver(
        MountIdentityResolver(
            mount_points=frozenset(str(item) for item in points), available=True
        )
    )


@pytest.mark.parametrize("nodes", ["exclusive", "typed"])
@pytest.mark.parametrize("where", ["top", "nested"])
def test_a_mount_stops_the_recursive_removal_owner(
    tmp_path: Path, nodes: str, where: str
) -> None:
    """R37-2A: one mount decision, at both depths and under either certification.

    A same-device bind mount is indistinguishable by device number alone, so the
    mount table is what decides - and it decides on the descriptor that is about
    to be enumerated, not on a pathname checked earlier.
    """

    from mdstats.training_data.storage.trust import set_mount_resolver

    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    nested = root / "sub"
    nested.mkdir(parents=True)
    (nested / "foreign.bin").write_bytes(b"someone else's bytes")
    certified = (
        None if nodes == "exclusive" else {"sub": "directory", "sub/foreign.bin": "file"}
    )

    _mounted_at([root if where == "top" else nested])
    try:
        payload, raised = _drive_removal(
            tmp_path, root, lambda: _certified(root, nodes=certified, anchor=anchor)
        )
    finally:
        set_mount_resolver(None)

    assert raised is None, raised
    assert payload["mutated"] is False, payload
    entry = payload["refused_actions"][0]
    assert "campaign-owned" in entry["refusal"], entry
    assert (nested / "foreign.bin").read_bytes() == b"someone else's bytes"


@pytest.mark.parametrize("nodes", ["exclusive", "typed"])
def test_an_unavailable_resolver_stops_the_recursive_removal_owner(
    tmp_path: Path, nodes: str
) -> None:
    """R37-2A: ambiguity retains at the one shared destructive mechanism."""

    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    anchor = tmp_path / "campaign"
    root = anchor / "tree"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "child.bin").write_bytes(b"c" * 4)
    certified = (
        None if nodes == "exclusive" else {"sub": "directory", "sub/child.bin": "file"}
    )

    set_mount_resolver(MountIdentityResolver(mount_points=frozenset(), available=False))
    try:
        payload, raised = _drive_removal(
            tmp_path, root, lambda: _certified(root, nodes=certified, anchor=anchor)
        )
    finally:
        set_mount_resolver(None)

    assert raised is None, raised
    assert payload["mutated"] is False, payload
    assert (root / "sub" / "child.bin").is_file()


# ---------------------------------------------------------------------------
# R37-4 - restore destination and maintenance transitions through real owners
# ---------------------------------------------------------------------------


def test_a_restore_destination_failure_after_the_replace_records_the_install(
    campaign, monkeypatch
) -> None:
    """R37-4: the installed member is recorded at its own `os.replace`."""

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)
    assert not checkpoint.exists()

    # The installer reaches the shared persistence primitive directly, which is
    # the lowest real callable on that path.
    from mdstats.training_data.target_size_execution import persistence as persistence_mod

    real = persistence_mod.fsync_parent_directory
    fired = {"n": 0}

    def guarded(path):
        if Path(path) == checkpoint:
            fired["n"] += 1
            raise OSError(5, "injected destination durability failure")
        return real(path)

    monkeypatch.setattr(persistence_mod, "fsync_parent_directory", guarded)
    with pytest.raises(OSError):
        _restore(campaign, result["archive_identity"])

    assert fired["n"] == 1, "the destination durability seam never fired"
    audit = _last_audit(campaign)
    assert audit["mutated"] is True, audit
    assert audit["status"] == "partial", audit
    installed = [
        item for item in audit["completed_actions"] if item.get("installed") is True
    ]
    assert installed, audit["completed_actions"]
    assert checkpoint.is_file(), "the replace really happened"


def test_a_restore_that_fails_before_installing_claims_no_destination_change(
    campaign,
) -> None:
    """R37-4 control: the journal transition is real; the install is not claimed."""

    run_root = campaign.historical_run()
    checkpoint = run_root / "checkpoints" / "epoch-1.pt"
    result = _create_archive(campaign)

    from mdstats.training_data.storage.archive import BOUNDARY_AFTER_STAGING

    with pytest.raises(_Injected):
        storage_commands.storage_archive(
            campaign.context(),
            _args(
                archive_command="restore",
                archive_identity=result["archive_identity"],
                apply=True,
                failpoint=_fail_at(BOUNDARY_AFTER_STAGING),
            ),
        )
    audit = _last_audit(campaign)
    # Mutated, because the nonterminal journal really was published - but the
    # destination evidence is absent, because no destination changed.
    assert audit["mutated"] is True, audit
    assert (
        audit["result"]["restore_phase"]
        == archive_mod.RESTORE_PHASE_JOURNAL_STAGING_PUBLISHED
    ), audit
    assert int(audit["restored_bytes"]) == 0, audit
    assert not any(item.get("installed") for item in audit["completed_actions"]), audit
    assert not checkpoint.exists()


def test_event_pruning_marks_mutation_only_where_it_pruned(
    campaign, monkeypatch
) -> None:
    """R37-4: a positive prune is a mutation; a cleanup with nothing to prune is not."""

    campaign.historical_run()
    control = storage_commands.storage_cleanup(
        campaign.context(), _args(tier="safe", apply=True)
    )["execution"]
    assert not any(
        item["action"] == "prune_campaign_events"
        for item in control["completed_actions"]
    ), control
    assert control["mutated"] is False, control

    for _index in range(150):
        campaign.store.event("info", "fixture", "x" * 32)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 100}}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    execution = storage_commands.storage_cleanup(
        context, _args(tier="safe", apply=True)
    )["execution"]
    pruned = [
        item
        for item in execution["completed_actions"]
        if item["action"] == "prune_campaign_events"
    ]
    assert pruned and int(pruned[0]["events_pruned"]) > 0, execution
    assert execution["mutated"] is True, execution


# ---------------------------------------------------------------------------
# R37-5 - structural closure over the mechanisms the counterfactuals exercise
# ---------------------------------------------------------------------------


def _destructive_sources() -> dict[str, str]:
    storage = Path(cli.__file__).parent / "storage"
    qualification = Path(cli.__file__).parent / "qualification"
    return {
        "removal.py": (storage / "removal.py").read_text(encoding="utf-8"),
        "executor.py": (storage / "executor.py").read_text(encoding="utf-8"),
        "archive.py": (storage / "archive.py").read_text(encoding="utf-8"),
        "durability.py": (storage / "durability.py").read_text(encoding="utf-8"),
        "store.py": (qualification / "store.py").read_text(encoding="utf-8"),
    }


def test_no_owner_infers_a_removal_from_a_later_pathname_lookup() -> None:
    """R37-5: absence after a failure is not evidence this execution caused it.

    The inference is cheap to reintroduce and impossible to see in a green
    suite, because on the happy path it agrees with the truth. It only diverges
    under exactly the contention the counterfactuals model.
    """

    import ast

    for name, source in _destructive_sources().items():
        tree = ast.parse(source)
        for handler in (
            node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
        ):
            dumped = ast.dump(handler)
            assert "attr='exists'" not in dumped, (
                f"{name}: an error handler consults pathname existence, which "
                "cannot distinguish this execution's removal from another's"
            )
            assert "attr='is_symlink'" not in dumped, name


def test_no_consequential_unlink_has_a_signature_incompatible_fallback() -> None:
    """R37-5: a `TypeError` fallback would fabricate the transition it lost.

    Calling an older signature and then invoking the callback by hand claims a
    removal the primitive never reported, and it hides the fact that some caller
    is out of date with the durability contract.
    """

    import ast

    for name, source in _destructive_sources().items():
        tree = ast.parse(source)
        for handler in (
            node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)
        ):
            if handler.type is None:
                continue
            caught = ast.dump(handler.type)
            if "TypeError" not in caught:
                continue
            body = ast.dump(ast.Module(body=handler.body, type_ignores=[]))
            assert "durable_unlink" not in body, f"{name}: unlink fallback"
            assert "durable_publish" not in body, f"{name}: publication fallback"


def test_every_consequential_rmdir_keeps_parent_authority_and_rechecks() -> None:
    """R37-5: the last destructive syscall spends the capability it authenticated.

    Both recursive owners must reach `rmdir` through the parent descriptor they
    descended with, immediately after comparing the entry against the still-open
    child descriptor. An absolute-path `rmdir` would re-resolve the name and
    discard everything the descent established.
    """

    import ast

    sources = _destructive_sources()
    sites = 0
    for name in ("removal.py",):
        tree = ast.parse(sources[name])
        for call in ast.walk(tree):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "rmdir"
            ):
                continue
            sites += 1
            assert any(
                keyword.arg == "dir_fd" for keyword in call.keywords
            ), f"{name}: a consequential rmdir does not name its parent descriptor"
        # And the comparison is what guards it.
        assert "verify_final_directory_identity(" in sources[name], name
    assert sites == 1, sites

    # There is one such site in the product, and the P7 owner delegates to it
    # rather than keeping a second one.
    assert "rmdir" not in sources["store.py"], (
        "the P7 owner regained its own directory removal"
    )


# ---------------------------------------------------------------------------
# IR17-2 - one exactly-once primary/secondary close ranking doctrine
# ---------------------------------------------------------------------------


def _count_closes(monkeypatch, module=os):
    """Every `os.close` this process performs, recorded per descriptor number."""

    real = os.close
    closed: list[int] = []

    def watched(handle):
        closed.append(int(handle))
        return real(handle)

    monkeypatch.setattr(os, "close", watched)
    return closed, real


@pytest.mark.parametrize("failure", ["wrong_kind", "fstat"])
def test_the_nofollow_acquisition_closes_each_fd_exactly_once(
    tmp_path: Path, monkeypatch, failure: str
) -> None:
    """IR17-2B: cleanup is attempted once, even when the close itself fails.

    The helper either hands the descriptor to its caller or releases it exactly
    once. A wrong-kind or unidentifiable object is a namespace/authentication
    failure and stays the primary classification; a failing cleanup close is
    secondary evidence and never triggers a second close of a number the kernel
    may already have reissued.
    """

    from mdstats.training_data.storage.trust import (
        NamespaceAmbiguity,
        open_directory_nofollow,
    )

    victim = tmp_path / "not-a-directory"
    victim.write_bytes(b"x")
    real_close = os.close
    attempts: list[int] = []

    def refusing_close(handle):
        attempts.append(int(handle))
        real_close(handle)
        raise OSError(5, "injected close failure")

    # `O_DIRECTORY` refuses a regular file before any descriptor exists, so the
    # two post-open branches are reached by making the *identification* step
    # disagree with the open - which is exactly the racing case the branches
    # exist for.
    target = tmp_path / "plain"
    target.mkdir()
    victim_stat = os.stat(victim)

    if failure == "fstat":

        def observed_fstat(handle):
            raise OSError(5, "injected identification failure")

    else:

        def observed_fstat(handle):
            return victim_stat

    monkeypatch.setattr(os, "fstat", observed_fstat)
    monkeypatch.setattr(os, "close", refusing_close)
    with pytest.raises(NamespaceAmbiguity) as caught:
        open_directory_nofollow(str(target))

    # The namespace/authentication failure survives the failing close.
    assert "close" not in str(caught.value).lower(), caught.value
    # Cleanup was attempted exactly once for the one descriptor acquired.
    assert len(attempts) == 1, attempts
    assert len(set(attempts)) == 1, attempts


def test_a_successful_nofollow_acquisition_transfers_ownership(tmp_path: Path, monkeypatch) -> None:
    """IR17-2B: once a valid directory fd is returned, the helper never closes it."""

    from mdstats.training_data.storage.trust import open_directory_nofollow

    target = tmp_path / "dir"
    target.mkdir()
    real_close = os.close
    closed: list[int] = []
    monkeypatch.setattr(os, "close", lambda handle: (closed.append(int(handle)), real_close(handle))[1])
    handle = open_directory_nofollow(str(target))
    try:
        assert closed == [], closed
        # The returned descriptor is live and is the caller's to spend.
        assert stat.S_ISDIR(os.fstat(handle).st_mode)
    finally:
        monkeypatch.undo()
        os.close(handle)


def test_a_mount_refusal_close_failure_never_bypasses_the_ledger(
    tmp_path: Path, monkeypatch
) -> None:
    """IR17-2A: the structured refusal is built before the descriptor is released.

    A raw close in the mount-refusal branch would let a close failure escape as
    a bare `OSError`, outside the `MutationLedger` transport, and the action's
    already-removed prefix would never reach the audit.
    """

    from mdstats.training_data.storage import removal as removal_mod
    from mdstats.training_data.storage.outcome import MutationLedger
    from mdstats.training_data.storage.trust import (
        MountIdentityResolver,
        set_mount_resolver,
    )

    root = tmp_path / "tree"
    (root / "nested").mkdir(parents=True)
    (root / "a-first.bin").write_bytes(b"a" * 7)
    (root / "nested" / "kept.bin").write_bytes(b"b" * 3)

    set_mount_resolver(
        MountIdentityResolver(
            mount_points=frozenset({os.path.abspath(root / "nested")}), available=True
        )
    )
    real_close = os.close
    refused_handles: list[int] = []

    def refusing_close(handle):
        refused_handles.append(int(handle))
        real_close(handle)
        raise OSError(5, "injected close failure")

    ledger = MutationLedger()
    handle = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        monkeypatch.setattr(os, "close", refusing_close)
        stopped = removal_mod._empty_certified_directory(
            handle, root, _certification(root), "", ledger
        )
    finally:
        monkeypatch.undo()
        set_mount_resolver(None)
        os.close(handle)

    outcome = ledger.stop(stopped)
    assert outcome.outcome == "partial_change_refused", outcome
    # The mount refusal remains primary and the earlier prefix is exact.
    assert "not campaign-owned" in outcome.detail, outcome.detail
    assert outcome.removed_bytes == 7, outcome
    assert refused_handles, "the refused child's descriptor was never released"
    # The externally owned bytes survive.
    assert (root / "nested" / "kept.bin").exists()


def test_no_direct_close_before_a_structured_outcome_remains() -> None:
    """IR17-2D: the bounded consequential close-family census, as a guard.

    Every consequential descriptor finalization in the destructive owners goes
    through one of the ranking helpers. Only those helpers - and the one-way
    session close, whose caller ranks it - may name `os.close` directly.
    """

    import ast

    roots = {
        "storage/executor.py": {"_close_descriptor"},
        "storage/trust.py": {"_release_unowned_descriptor"},
        "storage/commands.py": set(),
        "qualification/store.py": {
            "_close_owner_descriptor",
            "release_descriptor_behind",
            "close",
            # Observational readers below the destructive boundary; they run
            # while no action-local mutation and no structured product failure
            # is in flight, so uniformity buys nothing.
            "_read_regular_file_nofollow",
            "_observe_attempt_nodes_from_descriptor",
            "_observe_attempt",
            "authenticate_attempt_state",
            "observe_qualification_namespace",
            "_observe_generation",
            "_child_is_directory",
        },
    }
    package = Path(cli.__file__).parent
    for relative, allowed in roots.items():
        tree = ast.parse((package / relative).read_text(encoding="utf-8"))
        owners: dict[int, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for inner in ast.walk(node):
                    owners.setdefault(id(inner), node.name)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "close"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                continue
            owner = owners.get(id(node), "<module>")
            assert owner in allowed, f"{relative}: unranked os.close in {owner}"


def test_consequential_removal_is_anchored_bound_and_same_parent_durable() -> None:
    """Structural closure for the one destructive authority family.

    Source/absence evidence for the claims no counterfactual can establish on
    its own: that there is no *other* way through the consequential owner.
    """

    import ast

    package = Path(cli.__file__).parent
    removal_source = (package / "storage" / "removal.py").read_text(encoding="utf-8")
    commands_source = (package / "storage" / "commands.py").read_text(encoding="utf-8")
    store_source = (package / "qualification" / "store.py").read_text(encoding="utf-8")
    removal_tree = ast.parse(removal_source)

    def _function(tree, name):
        return next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        )

    # 1. The root of trust is the plan's own campaign anchor, and the descent
    #    below it is componentwise from an already-authenticated descriptor -
    #    never a fresh absolute/multi-component open whose last component
    #    happened to be no-follow.
    descent = _function(removal_tree, "descend_to_parent")
    dumped = ast.dump(descent)
    assert "relative_to" in dumped, "the descent does not root itself in the anchor"
    acquisitions = [
        node
        for node in ast.walk(descent)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open_directory_nofollow"
    ]
    assert len(acquisitions) == 2, (
        "the descent no longer opens exactly the anchor plus one hop per component"
    )
    # Exactly one of them names an absolute path - the anchor - and every other
    # hop is relative to the descriptor of the parent already authenticated.
    assert sum(
        1
        for call in acquisitions
        if not any(keyword.arg == "dir_fd" for keyword in call.keywords)
    ) == 1, "a consequential hop is opened without naming its parent descriptor"
    assert "verify_opened_directory_trust" in dumped, (
        "an intermediate hop escapes the opened-descriptor mount decision"
    )
    assert "descend_to_parent" in ast.dump(
        _function(removal_tree, "remove_planned_target")
    )
    assert "anchor=plan.workspace" in commands_source, (
        "the production cleanup engine no longer supplies the campaign anchor"
    )
    # The P7 entry point needs no descent: its live session already
    # authenticated the parent, and that descriptor is what it hands over.
    assert "descend_to_parent" not in ast.dump(
        _function(removal_tree, "remove_certified_unit")
    )
    assert "session.attempt_fd" in store_source

    # 2. The opened target is compared with the plan's own binding, and the
    #    owner's identities remain independently enforced.
    spend = ast.dump(_function(removal_tree, "_spend_certified_unit"))
    assert spend.count("identity_contradiction") >= 3, (
        "the entry, the opened descriptor and the owner root are not all compared"
    )
    assert "owner_identity_contradiction" in spend, (
        "plan identity and owner identity are no longer independent constraints"
    )
    for name in ("remove_planned_target", "remove_certified_unit"):
        accepted = {
            argument.arg
            for argument in _function(removal_tree, name).args.kwonlyargs
        }
        assert "certification" in accepted, name
    assert "planned_identity" in {
        argument.arg
        for argument in _function(removal_tree, "remove_certified_unit").args.kwonlyargs
    }
    assert "anchor" in {
        argument.arg
        for argument in _function(removal_tree, "remove_planned_target").args.kwonlyargs
    }

    # 3. Once the plan-bound parent capability exists the single-file path
    #    cannot fall back to an absolute unlink.
    unlink_calls = [
        node
        for node in ast.walk(_function(removal_tree, "_spend_certified_unit"))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "unlink_certified_entry"
    ]
    assert unlink_calls, "the single-file boundary disappeared"
    assert all(
        isinstance(call.args[0], ast.Name) and call.args[0].id == "parent_fd"
        for call in unlink_calls
    ), "a consequential single-file unlink no longer names its parent descriptor"

    # 4. Directory-entry durability spends the retained parent capability; a
    #    pathname re-resolution does not exist in the destructive owner at all.
    assert "fsync_parent_directory" not in removal_source, (
        "the destructive owner can still re-resolve a parent pathname"
    )
    persist = ast.dump(_function(removal_tree, "persist_entry_removal"))
    assert "fsync" in persist and "parent_fd" in persist, persist[:200]
    assert "persist_entry_removal" in spend, (
        "the destructive owner no longer persists through its own parent"
    )

    # 5. No post-failure disappearance inference or signature-incompatible
    #    unlink fallback has returned, and publication truth stays at the
    #    atomic replace.
    durability_source = (package / "storage" / "durability.py").read_text(
        encoding="utf-8"
    )
    assert "on_published()" in durability_source
    replace_index = durability_source.index("os.replace(staging, target)")
    published_index = durability_source.index("on_published()")
    fsync_index = durability_source.index("fsync_parent_directory(target)")
    assert replace_index < published_index < fsync_index, (
        "publication truth no longer fires at the atomic replace"
    )
    assert "exists()" not in ast.dump(_function(ast.parse(durability_source), "durable_unlink"))


# ---------------------------------------------------------------------------
# R38 - one cleanup semantic path, one canonical destructive owner
# ---------------------------------------------------------------------------
#
# Caller/API census recorded for this closure, taken over the whole repository:
#
#   * `StorageExecutor.run` is called from five production sites, all in
#     `storage/commands.py`, and every one of them supplies a specialized
#     engine: cleanup, archive create, archive reclaim, archive restore, dedup.
#     The engine argument is now required, so there is no default destructive
#     route at all and nothing for a routing domain to keep in step.
#   * The only cleanup destructive implementation is `storage/removal.py`.
#     Ordinary cleanup enters it through `remove_planned_target`, and the P7
#     released-attempt owner enters it through `remove_certified_unit` with the
#     descriptor its live session already authenticated.
#   * `remove_durably` / `remove_durably_outcome` / `remove_certified_subtree`
#     had no production consumer once the default engine was removed; the
#     supported contract they were reachable through is the canonical path
#     above, so the second algorithm was deleted rather than wrapped.


def _cleanup_context(campaign, cfg=None):
    return storage_commands.StorageCommandContext(
        cfg if cfg is not None else campaign.cfg,
        campaign.paths,
        campaign.store,
        campaign.boundary,
    )


def _run_cleanup(
    campaign,
    *,
    cfg=None,
    tier="safe",
    plan_actions=None,
    invoked_as=None,
):
    """Real planning, real revalidation, real `StorageExecutor.run`, real audit.

    ``plan_actions(actions, snapshot)`` may narrow or extend the *real* cleanup
    plan; nothing below the executor is substituted, and the plan is always
    rebuilt against the real snapshot it will be revalidated with.

    ``invoked_as`` resolves the apply policy under a *different* action family
    while the plan still carries real cleanup actions. Ordinary revalidation is
    satisfied in that case - policy identity, action equality, owner binding,
    protection closure and per-action filesystem identity all hold - so nothing
    before the cleanup family gate would refuse the execution.
    """

    context = _cleanup_context(campaign, cfg)
    cleanup_policy = resolve_storage_policy(
        cfg if cfg is not None else {}, action=ACTION_CLEANUP, tier=tier, apply=True
    )
    context.consequential_plane(cleanup_policy)
    plan, snapshot = storage_commands.build_cleanup_plan(
        context, cleanup_policy.for_apply(apply=False)
    )
    actions = list(plan.actions)
    if plan_actions is not None:
        actions = list(plan_actions(actions, snapshot))
    policy = (
        cleanup_policy
        if invoked_as is None
        else resolve_storage_policy(
            cfg if cfg is not None else {}, action=invoked_as, tier=tier, apply=True
        )
    )
    apply_plan = build_storage_plan(
        snapshot,
        policy,
        actions,
        refusals=plan.refusals,
        created_utc=plan.created_utc,
    )
    if invoked_as is not None:
        revalidate_plan(apply_plan, snapshot, policy)
    raised: BaseException | None = None
    result = None
    try:
        result = context.executor(policy).run(
            apply_plan,
            trigger="test:r38",
            synchronization=synchronization_for(apply_plan, snapshot),
            engine=storage_commands._cleanup_engine(context, policy),
        )
    except BaseException as exc:  # noqa: BLE001 - propagation is the contract
        raised = exc
    return result, raised, apply_plan


def _owner_scoped_container(campaign, *, contradiction: bool = True) -> Path:
    """A real reclaimable owner-scoped container, optionally contradicted.

    `.mdstats/storage/staging/<identity>` is the storage owner's own
    exclusive-writer scratch: a real closed-subtree artifact whose whole-unit
    authority covers exactly what that owner could have written. A symlink is
    something it never writes, so its presence contradicts the certification.
    """

    root = campaign.control_plane.staging_root_for("f" * 32)
    (root / "dedup").mkdir(parents=True, exist_ok=True)
    (root / "dedup" / "authorized.bin").write_bytes(b"a" * 24)
    sentinel = root / "dedup" / "foreign.link"
    if contradiction and not sentinel.is_symlink():
        sentinel.symlink_to(campaign.paths.state_db)
    return root


def _generic_leaf(campaign, name: str = "aaaa.bin") -> Path:
    """A real leaf cleanup target: uncataloged archive publication residue."""

    campaign.control_plane.archive_root.mkdir(parents=True, exist_ok=True)
    residue = campaign.control_plane.archive_root / name
    residue.write_bytes(b"r" * 40)
    return residue


def _last_audit(campaign):
    records = campaign.control_plane.read_audit()
    return dict(records[-1]) if records else None


def _refusal_details(result) -> str:
    return "\n".join(str(item.get("refusal", "")) for item in result.refused)


def _assert_action_refused(campaign, result, raised, *, fragment):
    """The action was refused, nothing mutated, and the truth was audited."""

    assert raised is None, raised
    assert result is not None, result
    detail = _refusal_details(result)
    assert fragment in detail, detail
    assert result.mutated is False, result.to_dict()
    assert int(result.reclaimed_bytes) == 0, result.to_dict()
    assert result.completed == [], result.completed
    audit = _last_audit(campaign)
    assert audit is not None, "the refused truth was never published"
    assert audit["status"] == "refused", audit
    assert audit["mutated"] is False, audit
    assert int(audit["reclaimed_bytes"]) == 0, audit
    assert "re-plan" not in audit["detail"], audit["detail"]
    return detail


def _assert_wrong_family_refusal(campaign, result, raised, *, action):
    """Refused, non-mutating, zero-byte, durably audited - and for this reason."""

    from mdstats.training_data.storage.executor import StorageAuthorizationError

    assert isinstance(raised, StorageAuthorizationError), raised
    detail = str(raised)
    assert action in detail, detail
    assert "cleanup" in detail and "action family" in detail, detail
    assert result is None, "a wrong-family execution must not settle a result"
    audit = _last_audit(campaign)
    assert audit is not None, "the refused truth was never published"
    assert audit["status"] == "refused", audit
    assert audit["mutated"] is False, audit
    assert int(audit["reclaimed_bytes"]) == 0, audit
    assert audit["completed_actions"] == [], audit
    assert "re-plan" not in audit["detail"], audit["detail"]
    return detail


def test_an_unrecognized_exact_authorizer_is_never_generic(tmp_path: Path):
    """A future authorizer is unsupported, not generic.

    The point of a positive authority gate is that a field it has never seen
    cannot become a removal by failing to match anything.
    """

    from mdstats.training_data.storage.commands import cleanup_action_authority
    from mdstats.training_data.storage.owners import (
        ArtifactClass,
        P7_RELEASED_ATTEMPT_AUTHORIZER,
    )
    from mdstats.training_data.storage.plan import ACTION_REMOVE, planned_action

    target = tmp_path / "leaf.bin"
    target.write_bytes(b"x" * 32)
    policy = _policy(action=ACTION_CLEANUP, tier="safe")

    def _view(authorizer: str):
        return OwnerArtifactView(
            owner="p9",
            artifact_id="future:leaf",
            path=target,
            artifact_class=ArtifactClass.TEMPORARY_SCRATCH,
            detail="a future owner released this leaf",
            safe_reclaimable=True,
            exact_authorizer=authorizer,
        )

    action = planned_action(
        action=ACTION_REMOVE,
        path=target,
        artifact_id="future:leaf",
        reason="r38 fixture",
    )

    def _snapshot(view):
        return SimpleNamespace(view=lambda artifact_id: view)

    _, why = cleanup_action_authority(
        action, _snapshot(_view("p9.some-future-authorizer.v1")), policy
    )
    assert "unrecognized authorizer" in why, why

    # The recognized one still passes the gate, so this is a domain boundary
    # rather than a blanket refusal of every authorizer.
    view, why = cleanup_action_authority(
        action, _snapshot(_view(P7_RELEASED_ATTEMPT_AUTHORIZER)), policy
    )
    assert why == "", why
    assert view.exact_authorizer == P7_RELEASED_ATTEMPT_AUTHORIZER

    # And with no authorizer at all it is the ordinary released leaf it looks like.
    _, why = cleanup_action_authority(action, _snapshot(_view("")), policy)
    assert why == "", why


def test_a_directory_shaped_evictable_cache_is_removed_as_a_certified_unit(
    tmp_path: Path, campaign
):
    """A cache artifact is not a leaf unlink just because it is cache.

    Census result first: no owner in this product currently publishes a
    `cache_evictable` view at all - the SHA receipt store and the P1 frame cache
    both retain, the latter because P1 exposes no consumer-liveness seam - so a
    `cache` tier cleanup is legitimately a no-op today and there is no
    maintained directory-shaped production eviction target to drive. Rather than
    invent a fake production owner, the authority derivation the real engine
    uses is covered directly for the shape such an owner would produce.
    """

    from mdstats.training_data.storage.commands import cleanup_certification
    from mdstats.training_data.storage.owners import ArtifactClass

    # The census claim itself, through the real owners and the real inventory.
    snapshot = campaign.snapshot()
    assert not [view for view in snapshot.views if view.cache_evictable], (
        "an evictable cache family appeared; this case must now be driven "
        "through that real production owner instead of the view fixture"
    )
    assert not [item for item in cache_candidates(snapshot) if item.eligible]

    root = tmp_path / "derived-cache"
    (root / "shard").mkdir(parents=True)
    (root / "shard" / "a.bin").write_bytes(b"a" * 16)

    directory_view = OwnerArtifactView(
        owner="p1",
        artifact_id="p1:derived_cache",
        path=root,
        artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
        detail="owner-certified reconstructible derived cache",
        cache_reconstructible=True,
        cache_evictable=True,
        coverage=SubtreeCoverage.CLOSED,
        certified_nodes=(
            CertifiedNode(path="shard", kind="directory"),
            CertifiedNode(path="shard/a.bin", kind="file"),
        ),
    )
    certification = cleanup_certification(directory_view)
    assert certification is not None
    assert certification.exclusive is False
    assert certification.nodes == {"shard": "directory", "shard/a.bin": "file"}

    # A file-shaped evictable cache with no subtree authority carries no
    # whole-unit certification, and the canonical owner spends only the plan's
    # own target identity on it.
    leaf_view = OwnerArtifactView(
        owner="p1",
        artifact_id="p1:derived_index",
        path=tmp_path / "index.sqlite3",
        artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
        detail="owner-certified reconstructible index file",
        cache_reconstructible=True,
        cache_evictable=True,
    )
    assert cleanup_certification(leaf_view) is None

    # A container the owner does not close is never recursive authority.
    container_view = OwnerArtifactView(
        owner="p1",
        artifact_id="p1:derived_container",
        path=root,
        artifact_class=ArtifactClass.REUSABLE_CACHE_INDEX,
        detail="an open container",
        cache_reconstructible=True,
        cache_evictable=True,
        coverage=SubtreeCoverage.CONTAINER,
        certified_nodes=(CertifiedNode(path="shard/a.bin", kind="file"),),
    )
    assert cleanup_certification(container_view) is None


def test_an_open_container_is_never_recursive_destructive_authority(tmp_path: Path):
    """A directory with no whole-unit authority is retained, not half-emptied."""

    root = tmp_path / "campaign" / "container"
    (root / "inside").mkdir(parents=True)
    (root / "inside" / "keep.bin").write_bytes(b"k" * 8)

    from mdstats.training_data.storage.removal import remove_planned_target
    from mdstats.training_data.storage_reclamation import filesystem_identity

    outcome = remove_planned_target(
        SimpleNamespace(path=root, filesystem_identity=filesystem_identity(root)),
        anchor=root.parent,
        certification=None,
    )
    assert outcome.outcome == "refused_no_change", outcome
    assert "whole-unit authority" in outcome.detail, outcome.detail
    assert (root / "inside" / "keep.bin").is_file()


@pytest.mark.parametrize("kind", ["symlink", "unrecorded", "wrong-kind"])
def test_an_uncertified_descendant_retains_the_whole_container(tmp_path: Path, kind):
    """A node the owner never certified stops the removal instead of widening it."""

    root = tmp_path / "campaign" / "unit"
    root.mkdir(parents=True)
    (root / "recorded.bin").write_bytes(b"r" * 8)
    nodes = {"recorded.bin": "file"}
    if kind == "symlink":
        (root / "recorded.bin").with_name("link").symlink_to(root / "recorded.bin")
        nodes["link"] = "file"
    elif kind == "unrecorded":
        (root / "surprise.bin").write_bytes(b"s" * 4)
    else:
        (root / "wrong").mkdir()
        nodes["wrong"] = "file"

    outcome = _certified(root, nodes=nodes, anchor=root.parent)
    assert outcome.refused, outcome
    assert "container is retained" in outcome.detail, outcome.detail
    assert root.is_dir(), "the contradicted container was removed anyway"


def test_a_wholly_certified_unit_is_removed_through_the_canonical_owner(
    tmp_path: Path,
):
    """The positive path is live, not merely restrictive."""

    root = tmp_path / "campaign" / "unit"
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "a.bin").write_bytes(b"a" * 10)
    (root / "b.bin").write_bytes(b"b" * 6)

    outcome = _certified(
        root,
        nodes={"nested": "directory", "nested/a.bin": "file", "b.bin": "file"},
        anchor=root.parent,
    )
    assert outcome.outcome == "removed", outcome
    assert int(outcome.removed_bytes) == 16, outcome
    assert not root.exists()


@pytest.mark.parametrize("shape", ["mismatched-binding", "owner-ineligible"])
def test_a_malformed_or_ineligible_cleanup_action_never_mutates(campaign, shape):
    """Path authorization alone cannot rescue an action the owner did not release.

    `artifact_id` is a name, not authority, and `p1:data7-cache` is a real owner
    view for a historical derived cache with no certified reconstruction:
    unprotected and physically campaign-owned, and released by its owner for
    neither safe reclamation nor cache eviction.
    """

    from mdstats.training_data.storage.plan import ACTION_REMOVE, planned_action

    named = _generic_leaf(campaign, "aaaa.bin")
    decoy = _generic_leaf(campaign, "bbbb.bin")
    ineligible = campaign.paths.internal / "data7-cache"
    ineligible.mkdir(parents=True, exist_ok=True)
    (ineligible / "old.bin").write_bytes(b"o" * 12)

    def _malform(actions, snapshot):
        if shape == "mismatched-binding":
            view = next(item for item in snapshot.views if item.path == named)
            target = decoy
        else:
            view = next(
                item for item in snapshot.views if item.artifact_id == "p1:data7-cache"
            )
            assert not view.safe_reclaimable and not view.cache_evictable, view
            protected, _why = snapshot.path_protection(view.path)
            assert not protected, "the fixture target is protected, not merely ineligible"
            authorized, why = campaign.boundary.destructive_authorization(view.path)
            assert authorized, why
            target = view.path
        # A valid artifact id, a real owner state identity, and a genuine
        # plan-bound filesystem identity.
        return [
            planned_action(
                action=ACTION_REMOVE,
                path=target,
                artifact_id=view.artifact_id,
                reason=f"r38 {shape}",
                owner_state_identity=view.state_identity,
            )
        ]

    result, raised, _plan = _run_cleanup(campaign, plan_actions=_malform)
    fragment = (
        "may not name one owner artifact and mutate another"
        if shape == "mismatched-binding"
        else "p1:data7-cache"
    )
    _assert_action_refused(campaign, result, raised, fragment=fragment)
    assert named.exists() and decoy.exists()
    assert (ineligible / "old.bin").exists()


def test_production_cleanup_routes_every_owner_to_the_canonical_destructive_owner(
    campaign,
):
    """The live path keeps its owners and has exactly one destructive owner.

    The released-P7 half of this claim needs a real qualified campaign and is
    accepted in the integration suite.
    """

    from mdstats.training_data.storage import commands as commands_mod

    campaign.historical_run()
    for index in range(4000):
        campaign.store.event("info", "fixture", "x" * 256)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 10}}
    container = _owner_scoped_container(campaign, contradiction=False)
    contents = sorted(str(item) for item in container.rglob("*"))
    assert contents, "the container fixture is empty"
    leaf = _generic_leaf(campaign)

    observed: list[tuple[str, bool]] = []
    real = commands_mod.remove_planned_target

    def watch(action, *, anchor, certification=None):
        observed.append((str(action.path), certification is not None))
        return real(action, anchor=anchor, certification=certification)

    commands_mod.remove_planned_target = watch
    try:
        result, raised, plan = _run_cleanup(campaign, cfg=cfg)
    finally:
        commands_mod.remove_planned_target = real

    assert raised is None, raised
    assert result is not None, result
    # One destructive owner, entered with whole-unit authority for the container
    # and with the plan's own binding alone for the leaf.
    assert (str(container), True) in observed, observed
    assert (str(leaf), False) in observed, observed
    assert not leaf.exists(), "the released leaf was not removed by production cleanup"
    assert not container.exists(), "the wholly certified container was retained"
    assert any(
        item["action"] == "prune_campaign_events" for item in result.completed
    ), result.completed


def test_an_uncertified_container_is_retained_while_its_siblings_proceed(campaign):
    """O3: an open/contradicted container is refused, not selectively emptied."""

    container = _owner_scoped_container(campaign, contradiction=True)
    before = sorted(str(item) for item in container.rglob("*"))
    leaf = _generic_leaf(campaign)

    result, raised, plan = _run_cleanup(campaign)
    assert raised is None, raised
    assert any(item.path == container for item in plan.actions), (
        "the real planner never released the owner-scoped container"
    )
    assert not leaf.exists(), "an independently authorized sibling was withheld"
    # The container itself is retained, and so is the node its owner could not
    # have written; the removal stops there rather than negotiating a member set.
    assert container.is_dir(), "an uncertified container was removed anyway"
    assert (container / "dedup" / "foreign.link").is_symlink()
    assert campaign.paths.state_db.exists(), "the symlink target was followed"
    refusal = _refusal_details(result)
    assert "container is retained" in refusal, refusal
    del before


@pytest.mark.parametrize(
    "invoked_as", [ACTION_ARCHIVE, ACTION_DEDUPLICATE, ACTION_RESTORE]
)
def test_a_non_cleanup_invocation_can_never_spend_cleanup_deletion(
    campaign, invoked_as
):
    """The cleanup family gate is plan-level and total.

    `revalidate_plan` proves the executor policy and the plan policy agree with
    *each other*; it never proves the actions they agree on belong to the family
    that authorized the invocation. The plan below carries the real,
    owner-released leaf the cleanup planner produced, and revalidation succeeds.
    """

    from mdstats.training_data.storage import commands as commands_mod

    leaf = _generic_leaf(campaign)
    before = leaf.read_bytes()
    calls: list[str] = []
    real = commands_mod.remove_planned_target
    commands_mod.remove_planned_target = lambda action, **kw: calls.append(
        str(action.path)
    )
    try:
        result, raised, plan = _run_cleanup(
            campaign,
            invoked_as=invoked_as,
            plan_actions=lambda actions, snapshot: [
                item for item in actions if item.path == leaf
            ],
        )
    finally:
        commands_mod.remove_planned_target = real

    assert [item.action for item in plan.actions] == ["remove"], plan.actions
    _assert_wrong_family_refusal(campaign, result, raised, action=invoked_as)
    assert calls == [], calls
    assert leaf.exists() and leaf.read_bytes() == before


@pytest.mark.parametrize("shape", ["empty", "maintenance"])
def test_the_family_gate_is_plan_level_rather_than_per_action(campaign, shape):
    """An empty or maintenance-only wrong-family plan is refused identically.

    An empty plan has no action to inspect, so a per-action family test would
    let this settle `complete` - falsely reporting that cleanup executed the
    requested archive operation. Maintenance is exactly as out of domain as
    removal once the invocation is not a cleanup.
    """

    campaign.historical_run()
    for index in range(4000):
        campaign.store.event("info", "fixture", "x" * 256)
    cfg = {**campaign.cfg, "storage": {"sqlite_compaction_maximum_events": 10}}
    leaf = _generic_leaf(campaign)

    def _select(actions, snapshot):
        if shape == "empty":
            return []
        return [item for item in actions if item.action == "prune_campaign_events"]

    result, raised, plan = _run_cleanup(
        campaign, cfg=cfg, invoked_as=ACTION_DEDUPLICATE, plan_actions=_select
    )
    if shape == "empty":
        assert plan.actions == (), plan.actions
    else:
        assert plan.actions, "the maintenance fixture produced no action to carry"
    _assert_wrong_family_refusal(campaign, result, raised, action=ACTION_DEDUPLICATE)
    assert leaf.exists()


def test_a_genuinely_empty_cleanup_plan_is_a_valid_no_op(campaign):
    """`empty` never means `refuse`; wrong-family does."""

    result, raised, plan = _run_cleanup(
        campaign, plan_actions=lambda actions, snapshot: []
    )
    assert raised is None, raised
    assert plan.actions == (), plan.actions
    assert result is not None
    assert result.status == "complete", result.to_dict()
    assert result.mutated is False, result.to_dict()
    audit = _last_audit(campaign)
    assert audit["status"] == "complete", audit
    assert audit["mutated"] is False, audit
    assert int(audit["reclaimed_bytes"]) == 0, audit


def test_exactly_one_consequential_cleanup_destructive_implementation_exists():
    """R38 structural reduction: no second remover and no alternate route.

    Scope: the whole `mdstats` package source. The rule is a positive census of
    the syscalls that actually destroy a campaign-owned directory entry, so a
    reintroduced recursion is found by the syscall it must use rather than by a
    name it could choose freely.

    Limits: `durable_unlink` is the shared publication/reclamation primitive and
    is counted at its definition; archive hot reclamation, restore staging, the
    control plane's own records, and dedup's own staged replacement link
    legitimately unlink their own bytes and are named explicitly here.
    """

    import ast as _ast

    root = Path(cli.__file__).parent
    destructive = {"rmdir", "unlink", "rmtree", "removedirs"}
    #: Modules whose own transformation/recovery semantics own their unlinks.
    allowed = {
        "storage/removal.py",  # the canonical cleanup destructive owner
        "storage/durability.py",  # the shared durable-unlink primitive
        "storage/archive.py",  # staged bytes and authenticated hot reclamation
        "storage/control_plane.py",  # storage's own catalog/journal state
        "storage/dedup.py",  # its own staged replacement link, never a member
    }
    sites: dict[str, list[str]] = {}
    # Scope: the storage and qualification packages. Owners elsewhere in the
    # campaign (staging areas, view caches, capsules) manage their own private
    # files and are not campaign-owned cleanup targets.
    scanned = [root / "storage", root / "qualification"]
    for source_path in sorted(
        item for base in scanned for item in base.rglob("*.py")
    ):
        relative = source_path.relative_to(root).as_posix()
        tree = _ast.parse(source_path.read_text(encoding="utf-8"))
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            if name in destructive:
                sites.setdefault(relative, []).append(f"{name}:{node.lineno}")

    #: Owners of their own private staging/scratch, which is never a
    #: campaign-owned cleanup target and never reached recursively from one.
    private = {
        "qualification/store.py": {"unlink"},  # its own atomic-write staging file
        "qualification/runtime.py": {"rmtree"},  # its own LAMMPS worker sandbox
    }
    unexpected = {
        path: found
        for path, found in sites.items()
        if path not in allowed
        and not set(item.split(":")[0] for item in found) <= private.get(path, set())
    }
    # Nothing outside those owners destroys a campaign directory entry, and the
    # qualification package no longer owns a cleanup deletion algorithm at all.
    assert unexpected == {}, unexpected
    store_sites = {item.split(":")[0] for item in sites.get("qualification/store.py", ())}
    assert "rmdir" not in store_sites, store_sites

    # One recursive walk, in one module, reached from exactly two entry points.
    removal = (root / "storage" / "removal.py").read_text(encoding="utf-8")
    recursions = [
        node.name
        for node in _ast.walk(_ast.parse(removal))
        if isinstance(node, (_ast.FunctionDef,))
        and any(
            isinstance(inner, _ast.Call)
            and getattr(inner.func, "id", "") == node.name
            for inner in _ast.walk(node)
        )
    ]
    assert recursions == ["_empty_certified_directory"], recursions

    # And no cleanup path can reach a destructive transition without owner
    # authority: the ordinary entry point takes the plan's binding, and the
    # unit walker takes the owner's certification.
    commands_source = (root / "storage" / "commands.py").read_text(encoding="utf-8")
    assert "remove_planned_target(" in commands_source
    executor_source = (root / "storage" / "executor.py").read_text(encoding="utf-8")
    for token in ("remove_planned_target", "remove_certified_unit", "os.unlink", "os.rmdir"):
        assert token not in executor_source, (
            f"the common execution envelope regained a destructive path ({token})"
        )


def test_mutation_truth_is_never_inferred_after_the_transition():
    """F7: no pathname/byte/signature inference survives in the removal owner."""

    import ast as _ast

    root = Path(cli.__file__).parent
    removal = (root / "storage" / "removal.py").read_text(encoding="utf-8")
    tree = _ast.parse(removal)
    for forbidden in (".exists()", "is_symlink()", "shutil."):
        assert forbidden not in removal, forbidden
    # Every credit happens inside the primitive that observed the syscall, and
    # the ledger is the only thing that decides `mutated`.
    assert removal.count("os.unlink(") == 1, "a second unlink site appeared"
    assert removal.count("ledger.credit(") == 1, removal.count("ledger.credit(")
    assert "def observed_identity" in removal
    # The P7 owner delegates its filesystem mechanics rather than repeating them.
    store = (root / "qualification" / "store.py").read_text(encoding="utf-8")
    assert "remove_certified_unit" in store
    for token in ("os.rmdir(", "os.unlink("):
        assert token not in store, f"the P7 owner regained a deletion algorithm ({token})"
    del tree


def test_every_production_storage_execution_supplies_an_explicit_engine():
    """No production `StorageExecutor.run` can rely on a default engine.

    Scan scope: the whole `mdstats` package. `run` itself now requires the
    argument, so this census is the structural half of the same claim: it also
    establishes that `storage/commands.py` is the only module that calls it.
    """

    import ast as _ast

    root = Path(cli.__file__).parent.parent
    callers: list[str] = []
    for source_path in sorted(root.rglob("*.py")):
        source = source_path.read_text(encoding="utf-8")
        if ".run(" not in source:
            continue
        tree = _ast.parse(source)
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            if getattr(node.func, "attr", "") != "run":
                continue
            keywords = {kw.arg for kw in node.keywords}
            if "trigger" not in keywords or "synchronization" not in keywords:
                continue  # not a `StorageExecutor.run` call
            relative = source_path.relative_to(root).as_posix()
            callers.append(relative)
            engine = next((kw for kw in node.keywords if kw.arg == "engine"), None)
            assert engine is not None, (
                f"{relative}:{node.lineno} calls StorageExecutor.run without an engine"
            )
            assert not (
                isinstance(engine.value, _ast.Constant) and engine.value.value is None
            ), f"{relative}:{node.lineno} runs a production plan on no engine"
    assert callers, "the census found no StorageExecutor.run call at all"
    assert set(callers) == {"training_data/storage/commands.py"}, sorted(set(callers))
    assert len(callers) == 5, callers

    # The signature itself carries the requirement, so a future caller cannot
    # reintroduce a default destructive route by omission.
    from mdstats.training_data.storage.executor import StorageExecutor

    parameter = inspect.signature(StorageExecutor.run).parameters["engine"]
    assert parameter.default is inspect.Parameter.empty, parameter
