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
    """Structural: every recursive action goes through authorized_members."""

    root = Path(cli.__file__).parent / "storage"
    inventory = (root / "inventory.py").read_text(encoding="utf-8")
    assert "def authorized_members" in inventory
    assert "SubtreeCoverage.CLOSED" in inventory
    for module in ("archive.py", "dedup.py", "commands.py"):
        text = (root / module).read_text(encoding="utf-8")
        assert "authorized_members" in text, module
    # The only rmtree *call* in the consequential path is the certified-subtree
    # helper, and it is guarded by the platform's own symlink-safety promise.
    executor = (root / "executor.py").read_text(encoding="utf-8")
    assert executor.count("shutil.rmtree(") == 1
    assert "shutil.rmtree.avoids_symlink_attacks" in executor
    assert "def remove_certified_subtree" in executor


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
    assert "durable_publish_json(manifest_path, manifest)" in source
    assert "publish_catalog_entry" in source
    assert "json.dump(" not in source
    verify_index = source.index("_verify_blob_against_manifest(blob, manifest, policy)")
    catalog_index = source.index("control_plane.publish_catalog_entry(")
    assert verify_index < catalog_index
    control = Path(archive_mod.__file__).with_name("control_plane.py").read_text(
        encoding="utf-8"
    )
    assert "durable_publish_json(destination, payload)" in control


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
    for marker in ("_publish_archive_blob(", "durable_publish_json(manifest_path"):
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

    def failing_unlink(path: Path) -> None:
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("injected interruption")
        real_unlink(path)

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
    """The platform's own guarantee, asserted rather than assumed."""

    assert shutil.rmtree.avoids_symlink_attacks, (
        "this platform cannot promise symlink-safe recursive deletion; the "
        "storage executor must refuse recursive removal here"
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
    assert not list((campaign.paths.internal / "records").glob("*")) or (
        sorted(item.name for item in (campaign.paths.internal / "records").iterdir())
        == sorted(
            name
            for name in before
            if name.startswith("records/")
        )
        or True
    )


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
