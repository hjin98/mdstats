"""Bounded acceptance for the owner-driven storage reset.

Every test here uses small synthetic fixtures.  Filesystem failure, archive
corruption, and publication-boundary interruption are injected *below* the real
storage owner, which itself always executes: the planner, the executor, the
control plane, the archive verifier, and the dedup owner are production code.

The assembled real-owner P1-P7 acceptance lives in
``test_mlff_storage_reset_integration.py``; nothing here substitutes for it.
"""

from __future__ import annotations

import json
import os
import stat
import tarfile
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data import campaign_cli
from mdstats.training_data.storage import (
    archive as archive_mod,
    commands as storage_commands,
)
from mdstats.training_data.storage.admission import (
    StorageAdmissionError,
    admit_storage_operation,
)
from mdstats.training_data.storage.archive import (
    BOUNDARY_AFTER_BLOB,
    BOUNDARY_AFTER_CATALOG,
    BOUNDARY_BEFORE_BLOB,
    BOUNDARY_BEFORE_RECEIPT,
    BOUNDARY_DURING_INSTALL,
    BOUNDARY_DURING_RECLAMATION,
    StorageArchiveError,
    create_cold_archive,
    list_archives,
    read_restore_journal,
    reclaim_archived_hot_members,
    restore_cold_archive,
    verify_cold_archive,
)
from mdstats.training_data.storage.control_plane import (
    StorageControlPlaneError,
    open_storage_control_plane,
)
from mdstats.training_data.storage.dedup import deduplicate
from mdstats.training_data.storage.durability import sha256_file
from mdstats.training_data.storage.inventory import (
    archive_candidates,
    build_storage_inventory,
)
from mdstats.training_data.storage.lease import (
    StorageLeaseUnavailableError,
    storage_operation_lease,
)
from mdstats.training_data.storage.plan import (
    StoragePlanStaleError,
    build_storage_plan,
    revalidate_plan,
)
from mdstats.training_data.storage.policy import (
    ACTION_ARCHIVE,
    ACTION_CLEANUP,
    ACTION_REPORT,
    StoragePolicyError,
    resolve_storage_policy,
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
    """A minimal real campaign workspace with a real CampaignStore."""

    def __init__(self, tmp_path: Path) -> None:
        self.config = _write_config(tmp_path)
        self.cfg, self.paths = cli._load_config(self.config)
        self.paths.ensure()
        self.store = cli.CampaignStore(self.paths.state_db)
        self.boundary = cli._campaign_ownership_boundary(self.cfg, self.paths, self.store)
        self.control_plane = open_storage_control_plane(self.paths)

    def close(self) -> None:
        self.store.close()

    def snapshot(self):
        return build_storage_inventory(
            self.cfg,
            self.paths,
            self.store,
            protected_inputs=self.boundary.protected_inputs,
            control_plane=self.control_plane,
        )

    def historical_bulk(self, *, generation: int = 7) -> Path:
        """A superseded P5 generation's run bulk: owner-declared cold-replaceable."""

        root = self.paths.internal / "post-selection" / f"g{generation}" / "runs"
        (root / "run-a" / "checkpoints").mkdir(parents=True, exist_ok=True)
        (root / "run-a" / "checkpoints" / "epoch-1.pt").write_bytes(b"historical" * 512)
        (root / "run-a" / "materialization.json").write_text("{}\n", encoding="utf-8")
        objects = self.paths.internal / "post-selection" / f"g{generation}" / "objects"
        objects.mkdir(parents=True, exist_ok=True)
        return root


@pytest.fixture()
def campaign(tmp_path: Path):
    instance = _Campaign(tmp_path)
    try:
        yield instance
    finally:
        instance.close()


def _policy(**kwargs):
    return resolve_storage_policy({}, **kwargs)


# ---------------------------------------------------------------------------
# R10-5 - one canonical resolved policy identity
# ---------------------------------------------------------------------------


def test_equivalent_policy_spellings_normalize_to_one_identity() -> None:
    first = resolve_storage_policy(
        {"storage": {"archive_codec": "gzip"}}, action="dedup", tier="lifecycle-safe"
    )
    second = resolve_storage_policy(
        {"storage": {"archive_codec": "TAR+GZIP"}}, action="deduplicate", tier="safe"
    )
    assert first.policy_identity == second.policy_identity
    assert first.action == second.action == "deduplicate"


def test_apply_authorization_does_not_change_the_policy_identity() -> None:
    planned = _policy(action=ACTION_CLEANUP)
    authorized = planned.for_apply(apply=True)
    assert planned.policy_identity == authorized.policy_identity


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


def test_no_environment_variable_can_widen_storage_authority(monkeypatch) -> None:
    baseline = _policy(action=ACTION_CLEANUP).policy_identity
    for name in (
        "MDSTATS_STORAGE_TIER",
        "MDSTATS_STORAGE_APPLY",
        "MDSTATS_STORAGE_SAFETY_RESERVE_BYTES",
    ):
        monkeypatch.setenv(name, "0")
    assert _policy(action=ACTION_CLEANUP).policy_identity == baseline
    import ast

    source = Path(
        cli.__file__
    ).parent.joinpath("storage", "policy.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    reads = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in {"environ", "getenv"}
    }
    assert reads == set(), reads


def test_material_policy_change_refuses_a_stale_apply(campaign) -> None:
    snapshot = campaign.snapshot()
    planned = _policy(action=ACTION_CLEANUP)
    plan = build_storage_plan(snapshot, planned, ())
    changed = resolve_storage_policy(
        {"storage": {"safety_reserve_bytes": 1}}, action=ACTION_CLEANUP, apply=True
    )
    with pytest.raises(StoragePlanStaleError, match="storage policy changed"):
        revalidate_plan(plan, snapshot, changed)


def test_presentation_only_change_does_not_invalidate_a_plan(campaign) -> None:
    snapshot = campaign.snapshot()
    policy = _policy(action=ACTION_CLEANUP)
    plan = build_storage_plan(snapshot, policy, ())
    # `--top` is presentation only and is deliberately not part of the policy.
    revalidate_plan(plan, snapshot, policy.for_apply(apply=True))


def test_dynamic_free_space_is_an_observation_not_a_scientific_invalidation(campaign) -> None:
    policy = _policy(action=ACTION_ARCHIVE)
    observation = admit_storage_operation(
        campaign.paths.workspace, policy, required_peak_bytes=1024
    )
    assert observation.admitted
    with pytest.raises(StorageAdmissionError, match="Nothing was modified"):
        admit_storage_operation(
            campaign.paths.workspace, policy, required_peak_bytes=1 << 62
        )
    # The refusal is a resource decision: campaign state is untouched.
    assert campaign.paths.state_db.is_file()


# ---------------------------------------------------------------------------
# R11-1 - archive/catalog locator containment
# ---------------------------------------------------------------------------


def _create_archive(campaign, *, reclaim_hot: bool = True, failpoint=None):
    root = campaign.historical_bulk()
    policy = _policy(action=ACTION_ARCHIVE, apply=True)
    snapshot = campaign.snapshot()
    plan = build_storage_plan(snapshot, policy, ())
    kwargs = {} if failpoint is None else {"failpoint": failpoint}
    return (
        create_cold_archive(
            workspace=campaign.paths.workspace,
            control_plane=campaign.control_plane,
            policy=policy,
            boundary=campaign.boundary,
            roots=[root],
            lineage={"current_generation": snapshot.current_generation},
            plan_identity=plan.plan_identity,
            paths=campaign.paths,
            reclaim_hot=reclaim_hot,
            **kwargs,
        ),
        policy,
        root,
    )


def _rewrite_manifest(campaign, identity: str, **fields) -> None:
    path = campaign.control_plane.manifest_path(identity)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(fields)
    body = {k: v for k, v in payload.items() if k != "manifest_content_digest"}
    from mdstats.training_data.storage.durability import canonical_digest

    body["manifest_content_digest"] = canonical_digest(body)
    path.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")


def test_valid_identity_keyed_archive_verifies_and_restores(campaign) -> None:
    result, policy, root = _create_archive(campaign)
    assert result.reclaimed_paths
    assert not (root / "run-a" / "checkpoints" / "epoch-1.pt").exists()
    verify_cold_archive(campaign.control_plane, result.archive_identity, policy)
    receipt = restore_cold_archive(
        workspace=campaign.paths.workspace,
        control_plane=campaign.control_plane,
        policy=_policy(action="restore", apply=True),
        boundary=campaign.boundary,
        archive_identity=result.archive_identity,
        paths=campaign.paths,
    )
    assert receipt.status == "complete"
    assert (root / "run-a" / "checkpoints" / "epoch-1.pt").read_bytes() == b"historical" * 512
    # Restoring bytes never promotes historical evidence to current.
    assert receipt.to_dict()["promotes_currentness"] is False


def test_absolute_archive_locator_is_rejected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    _rewrite_manifest(campaign, result.archive_identity, archive_locator="/etc/passwd")
    with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_parent_traversal_archive_locator_is_rejected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    _rewrite_manifest(
        campaign, result.archive_identity, archive_locator="../../outside.tar.gz"
    )
    with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_archive_root_symlink_escape_is_rejected(campaign, tmp_path: Path) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    outside = tmp_path / "outside"
    outside.mkdir()
    blob = campaign.control_plane.resolve_archive_blob(
        json.loads(
            campaign.control_plane.manifest_path(result.archive_identity).read_text()
        )["archive_locator"]
    )
    smuggled = outside / "smuggled.tar.gz"
    smuggled.write_bytes(blob.read_bytes())
    link = campaign.control_plane.archive_root / "escape"
    link.symlink_to(outside, target_is_directory=True)
    _rewrite_manifest(
        campaign, result.archive_identity, archive_locator="escape/smuggled.tar.gz"
    )
    # The catalog is tampered to agree, so containment is the only remaining
    # check standing between the manifest field and an out-of-root read.
    entry = dict(campaign.control_plane.read_catalog_entry(result.archive_identity))
    entry.pop("entry_digest", None)
    entry["archive_locator"] = "escape/smuggled.tar.gz"
    campaign.control_plane.publish_catalog_entry(entry)
    with pytest.raises((StorageArchiveError, StorageControlPlaneError), match="symlink|escape"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_manifest_catalog_archive_identity_mismatch_is_rejected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    _rewrite_manifest(campaign, result.archive_identity, archive_identity="0" * 32)
    with pytest.raises(StorageArchiveError, match="identity"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_a_supplied_digest_never_authorizes_reading_an_external_file(
    campaign, tmp_path: Path
) -> None:
    """A manifest field is not a licence to read an arbitrary path.

    Even when the external bytes would satisfy the recorded digest exactly, the
    locator is refused because it does not resolve inside the authorized
    storage-owned archive root.
    """

    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    manifest = json.loads(
        campaign.control_plane.manifest_path(result.archive_identity).read_text()
    )
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    external = tmp_path / "external-copy.tar.gz"
    external.write_bytes(blob.read_bytes())
    assert sha256_file(external) == manifest["archive_sha256"]
    _rewrite_manifest(campaign, result.archive_identity, archive_locator=str(external))
    with pytest.raises((StorageArchiveError, StorageControlPlaneError)):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


# ---------------------------------------------------------------------------
# R10-6 - bounded verification and extraction
# ---------------------------------------------------------------------------


def _repack(campaign, identity: str, build) -> None:
    """Replace an archive blob's contents, then re-seal the manifest digests."""

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


def _member(name: str, payload: bytes) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    return info, payload


@pytest.mark.parametrize(
    "name",
    ["/absolute/escape.bin", "../escape.bin", "./alias.bin", "dir//alias.bin"],
)
def test_unsafe_or_aliased_member_paths_are_rejected(campaign, name: str) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)

    def build(tar: tarfile.TarFile) -> None:
        info, payload = _member(name, b"x")
        tar.addfile(info, __import__("io").BytesIO(payload))

    _repack(campaign, result.archive_identity, build)
    with pytest.raises(StorageArchiveError):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_symlink_hardlink_and_special_members_are_rejected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
        def build(tar: tarfile.TarFile, kind=kind) -> None:
            info = tarfile.TarInfo("member.bin")
            info.type = kind
            info.linkname = "target.bin"
            info.size = 0
            tar.addfile(info)

        _repack(campaign, result.archive_identity, build)
        with pytest.raises(StorageArchiveError, match="rejected"):
            verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_duplicate_members_are_rejected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    manifest = json.loads(
        campaign.control_plane.manifest_path(result.archive_identity).read_text()
    )
    target = next(item for item in manifest["members"] if item["kind"] == "file")

    content = (campaign.paths.workspace / target["path"]).read_bytes()

    def build(tar: tarfile.TarFile) -> None:
        import io

        # Both copies are byte-exact, so nothing but the duplicate-name check
        # stands between the archive and two writes to one destination.
        for _ in range(2):
            info, payload = _member(target["path"], content)
            info.mode = int(target["mode"])
            tar.addfile(info, io.BytesIO(payload))

    _repack(campaign, result.archive_identity, build)
    with pytest.raises(StorageArchiveError, match="[Dd]uplicate"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_member_longer_than_its_manifest_size_is_stopped_at_the_bound(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    manifest_path = campaign.control_plane.manifest_path(result.archive_identity)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = next(item for item in manifest["members"] if item["kind"] == "file")

    def build(tar: tarfile.TarFile) -> None:
        import io

        for item in manifest["members"]:
            if item["kind"] == "directory":
                info = tarfile.TarInfo(item["path"])
                info.type = tarfile.DIRTYPE
                info.mode = int(item["mode"])
                tar.addfile(info)
                continue
            size = int(item["size_bytes"])
            if item["path"] == target["path"]:
                size += 4096
            info, payload = _member(item["path"], b"z" * size)
            info.mode = int(item["mode"])
            tar.addfile(info, io.BytesIO(payload))

    _repack(campaign, result.archive_identity, build)
    with pytest.raises(StorageArchiveError, match="longer than its manifest size"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_total_expansion_beyond_the_admitted_limit_is_refused(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign, reclaim_hot=False)
    bounded = resolve_storage_policy(
        {"storage": {"archive_expanded_bytes_limit": 16}}, action=ACTION_REPORT
    )
    with pytest.raises(StorageArchiveError, match="expanded bytes"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, bounded)


def test_decompression_amplification_is_refused_before_extraction(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign, reclaim_hot=False)
    bounded = resolve_storage_policy(
        {"storage": {"archive_expansion_ratio_limit": 1.0}}, action=ACTION_REPORT
    )
    with pytest.raises(StorageArchiveError, match="expansion ratio"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, bounded)


def test_member_count_beyond_the_admitted_limit_is_refused(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign, reclaim_hot=False)
    bounded = resolve_storage_policy(
        {"storage": {"archive_member_limit": 1}}, action=ACTION_REPORT
    )
    with pytest.raises(StorageArchiveError, match="members"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, bounded)


def test_corrupt_archive_bytes_are_detected(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    manifest = json.loads(
        campaign.control_plane.manifest_path(result.archive_identity).read_text()
    )
    blob = campaign.control_plane.resolve_archive_blob(manifest["archive_locator"])
    payload = bytearray(blob.read_bytes())
    payload[-1] ^= 0xFF
    blob.write_bytes(bytes(payload))
    with pytest.raises((StorageArchiveError, StorageControlPlaneError), match="[Dd]igest"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_restore_refuses_a_conflicting_destination(campaign) -> None:
    result, _policy_, root = _create_archive(campaign)
    victim = root / "run-a" / "checkpoints" / "epoch-1.pt"
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.write_bytes(b"different authoritative bytes")
    with pytest.raises(StorageArchiveError, match="different authoritative content"):
        restore_cold_archive(
            workspace=campaign.paths.workspace,
            control_plane=campaign.control_plane,
            policy=_policy(action="restore", apply=True),
            boundary=campaign.boundary,
            archive_identity=result.archive_identity,
            paths=campaign.paths,
        )
    assert victim.read_bytes() == b"different authoritative bytes"


# ---------------------------------------------------------------------------
# R11-2 - crash-durable publication ordering
# ---------------------------------------------------------------------------


class _Injected(RuntimeError):
    pass


def _fail_at(name: str):
    def failpoint(boundary: str) -> None:
        if boundary == name:
            raise _Injected(boundary)

    return failpoint


def test_failure_before_blob_publication_leaves_no_terminal_catalog(campaign) -> None:
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_BEFORE_BLOB))
    assert list_archives(campaign.control_plane) == ()


def test_failure_after_blob_but_before_catalog_cannot_authorize_hot_deletion(
    campaign,
) -> None:
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_AFTER_BLOB))
    assert list_archives(campaign.control_plane) == ()
    hot = (
        campaign.paths.internal
        / "post-selection"
        / "g7"
        / "runs"
        / "run-a"
        / "checkpoints"
        / "epoch-1.pt"
    )
    assert hot.is_file(), "hot bytes must survive an archive with no terminal catalog"


def test_failure_during_reclamation_is_resumable_and_truthful(campaign) -> None:
    with pytest.raises(_Injected):
        _create_archive(campaign, failpoint=_fail_at(BOUNDARY_DURING_RECLAMATION))
    entries = list_archives(campaign.control_plane)
    assert len(entries) == 1
    identity = entries[0]["archive_identity"]
    # The catalog is authenticated, so a retry may finish reclamation; it
    # re-authenticates the archive and re-authorizes each remaining hot member.
    resumed = reclaim_archived_hot_members(
        workspace=campaign.paths.workspace,
        control_plane=campaign.control_plane,
        policy=_policy(action=ACTION_ARCHIVE, apply=True),
        boundary=campaign.boundary,
        archive_identity=identity,
        paths=campaign.paths,
    )
    assert resumed.remaining_hot_paths == ()
    assert (
        campaign.control_plane.read_catalog_entry(identity)["hot_reclamation_state"]
        == "complete"
    )


def test_failure_during_restore_publication_produces_no_terminal_receipt(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign)
    with pytest.raises(_Injected):
        restore_cold_archive(
            workspace=campaign.paths.workspace,
            control_plane=campaign.control_plane,
            policy=_policy(action="restore", apply=True),
            boundary=campaign.boundary,
            archive_identity=result.archive_identity,
            paths=campaign.paths,
            failpoint=_fail_at(BOUNDARY_DURING_INSTALL),
        )
    journal = read_restore_journal(campaign.control_plane, result.archive_identity)
    assert journal is not None and journal["state"] != "terminal"


def test_the_terminal_receipt_follows_final_canonical_authentication(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign)
    with pytest.raises(_Injected):
        restore_cold_archive(
            workspace=campaign.paths.workspace,
            control_plane=campaign.control_plane,
            policy=_policy(action="restore", apply=True),
            boundary=campaign.boundary,
            archive_identity=result.archive_identity,
            paths=campaign.paths,
            failpoint=_fail_at(BOUNDARY_BEFORE_RECEIPT),
        )
    journal = read_restore_journal(campaign.control_plane, result.archive_identity)
    assert journal["state"] != "terminal"
    # A deterministic retry is idempotent for already-present identical bytes.
    receipt = restore_cold_archive(
        workspace=campaign.paths.workspace,
        control_plane=campaign.control_plane,
        policy=_policy(action="restore", apply=True),
        boundary=campaign.boundary,
        archive_identity=result.archive_identity,
        paths=campaign.paths,
    )
    assert receipt.status == "complete"
    journal = read_restore_journal(campaign.control_plane, result.archive_identity)
    assert journal["state"] == "terminal"
    assert journal["receipt"]["status"] == "complete"


def test_terminal_publication_uses_the_repository_durable_helpers() -> None:
    """Structural: terminal records go through the one durable publication owner."""

    source = Path(archive_mod.__file__).read_text(encoding="utf-8")
    # Every terminal record - blob, manifest, catalog entry, restore journal -
    # is written through the durable publication owner, never with a bare open().
    assert "durable_publish_bytes(blob" in source
    assert "durable_publish_json(manifest_path, sealed)" in source
    assert "durable_publish_json(\n                journal," in source
    assert "publish_catalog_entry" in source
    for forbidden in ("open(blob, \"wb\")", "json.dump("):
        assert forbidden not in source
    control = Path(
        archive_mod.__file__
    ).with_name("control_plane.py").read_text(encoding="utf-8")
    assert "durable_publish_json(destination, payload)" in control
    durability = Path(archive_mod.__file__).with_name("durability.py").read_text(
        encoding="utf-8"
    )
    assert "fsync_parent_directory" in durability
    # The catalog entry - the record that authorizes hot deletion - is published
    # only after the published blob has been re-authenticated.
    verify_index = source.index("_verify_published_pair(control_plane, sealed, policy)")
    catalog_index = source.index("catalog_path = control_plane.publish_catalog_entry(")
    assert verify_index < catalog_index


# ---------------------------------------------------------------------------
# R10-4 - storage control plane
# ---------------------------------------------------------------------------


def test_a_retained_archive_survives_cleanup_and_a_fresh_process(campaign, tmp_path: Path) -> None:
    result, _policy_, _root = _create_archive(campaign)
    payload = storage_commands.storage_cleanup(
        storage_commands.StorageCommandContext(
            campaign.cfg, campaign.paths, campaign.store, campaign.boundary
        ),
        SimpleNamespace(tier="cache", apply=True, dry_run=False),
    )
    assert payload["execution"]["status"] in {"complete", "partial"}
    campaign.close()

    reopened = _Campaign.__new__(_Campaign)
    reopened.config = campaign.config
    reopened.cfg, reopened.paths = cli._load_config(campaign.config)
    reopened.store = cli.CampaignStore(reopened.paths.state_db)
    reopened.boundary = cli._campaign_ownership_boundary(
        reopened.cfg, reopened.paths, reopened.store
    )
    reopened.control_plane = open_storage_control_plane(reopened.paths)
    try:
        entries = list_archives(reopened.control_plane)
        assert [item["archive_identity"] for item in entries] == [result.archive_identity]
        verify_cold_archive(
            reopened.control_plane, result.archive_identity, _policy(action=ACTION_REPORT)
        )
    finally:
        reopened.close()
    campaign.store = cli.CampaignStore(campaign.paths.state_db)


def test_audit_pruning_never_removes_catalog_state(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign)
    for index in range(20):
        campaign.control_plane.append_audit({"created_utc": str(index), "note": index})
    removed = campaign.control_plane.prune_audit(keep=5)
    assert removed > 0
    assert len(campaign.control_plane.read_audit()) == 5
    verify_cold_archive(
        campaign.control_plane, result.archive_identity, _policy(action=ACTION_REPORT)
    )


def test_control_plane_records_carry_no_scientific_currentness(campaign) -> None:
    result, _policy_, _root = _create_archive(campaign)
    entry = campaign.control_plane.read_catalog_entry(result.archive_identity)
    forbidden = {"current", "selected", "verdict", "qualified", "release", "generation_current"}
    assert not (set(entry) & forbidden)
    receipt = restore_cold_archive(
        workspace=campaign.paths.workspace,
        control_plane=campaign.control_plane,
        policy=_policy(action="restore", apply=True),
        boundary=campaign.boundary,
        archive_identity=result.archive_identity,
        paths=campaign.paths,
    ).to_dict()
    assert receipt["promotes_currentness"] is False
    assert receipt["grants_scientific_authority"] is False


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


# ---------------------------------------------------------------------------
# R10-7 - hardlink dedup metadata safety
# ---------------------------------------------------------------------------


def _dedup(campaign, *, apply: bool):
    snapshot = campaign.snapshot()
    return deduplicate(
        snapshot=snapshot,
        policy=_policy(action="deduplicate", apply=apply),
        control_plane=campaign.control_plane,
        boundary=campaign.boundary,
        paths=campaign.paths,
    )


def test_equal_bytes_with_incompatible_modes_do_not_share_an_inode(campaign) -> None:
    root = campaign.historical_bulk()
    payload = b"identical" * 1024
    first = root / "run-a" / "a.bin"
    second = root / "run-a" / "b.bin"
    first.write_bytes(payload)
    second.write_bytes(payload)
    os.chmod(first, 0o600)
    os.chmod(second, 0o644)
    result = _dedup(campaign, apply=True)
    assert first.stat().st_ino != second.stat().st_ino
    assert any("metadata" in note for note in result.excluded)


def test_equal_bytes_with_equal_metadata_are_deduplicated_exactly(campaign) -> None:
    root = campaign.historical_bulk()
    payload = b"identical" * 1024
    first = root / "run-a" / "a.bin"
    second = root / "run-a" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    result = _dedup(campaign, apply=True)
    assert result.links_replaced >= 1
    assert first.stat().st_ino == second.stat().st_ino
    assert first.read_bytes() == payload == second.read_bytes()


def test_a_deduplicated_path_survives_an_atomic_replace_of_another_alias(campaign) -> None:
    root = campaign.historical_bulk()
    payload = b"identical" * 1024
    first = root / "run-a" / "a.bin"
    second = root / "run-a" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    _dedup(campaign, apply=True)
    assert first.stat().st_ino == second.stat().st_ino
    replacement = second.parent / ".b.bin.new"
    replacement.write_bytes(b"updated" * 1024)
    os.replace(replacement, second)
    assert first.read_bytes() == payload
    assert second.read_bytes() == b"updated" * 1024


def test_dedup_only_invalidates_receipts_as_a_cache_miss(campaign) -> None:
    root = campaign.historical_bulk()
    payload = b"identical" * 1024
    first = root / "run-a" / "a.bin"
    second = root / "run-a" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    from mdstats.training_data._common import sha256_file_cached

    before = sha256_file_cached(first)
    _dedup(campaign, apply=True)
    assert sha256_file_cached(first) == before
    assert _dedup(campaign, apply=False).to_dict()["receipt_invalidation"]


def test_mutable_state_and_active_scratch_never_enter_dedup(campaign) -> None:
    """Byte equality alone never makes an artifact a dedup candidate."""

    duplicate = campaign.paths.internal / "campaign.sqlite3.copy"
    duplicate.write_bytes(campaign.paths.state_db.read_bytes())
    result = _dedup(campaign, apply=False)
    linked = {path for group in result.groups for path in group["paths"]}
    assert str(campaign.paths.state_db) not in linked
    assert str(duplicate) not in linked


# ---------------------------------------------------------------------------
# R10-3 / eligibility
# ---------------------------------------------------------------------------


def test_archive_never_removes_a_hot_path_a_current_resolver_requires(campaign) -> None:
    decisions = archive_candidates(campaign.snapshot())
    for decision in decisions:
        if decision.eligible:
            assert ".mdstats/post-selection/g" in str(decision.path) or ".mdstats/target-size/g" in str(
                decision.path
            )
    protected, why = campaign.snapshot().path_protection(campaign.paths.state_db)
    assert protected and why


def test_no_p1_p7_loader_gained_an_implicit_archive_fallback() -> None:
    """Structural: this package added no cold-read fallback under an owner."""

    training_data = Path(cli.__file__).parent
    storage_names = {"storage"}
    offenders = []
    for path in sorted(training_data.rglob("*.py")):
        if any(part in storage_names for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if "restore_cold_archive" in text or "verify_cold_archive" in text:
            offenders.append(str(path))
    assert offenders == []


def test_external_inputs_and_symlink_targets_are_never_deletable(campaign, tmp_path: Path) -> None:
    external = tmp_path / "external-payload"
    external.mkdir()
    (external / "keep.bin").write_bytes(b"keep")
    link = campaign.paths.internal / "external-link"
    link.symlink_to(external, target_is_directory=True)
    authorized, detail = campaign.boundary.destructive_authorization(external / "keep.bin")
    assert not authorized and detail
    # The link object itself is campaign-owned; its target is not traversed.
    traversal_ok, _ = campaign.boundary.traversal_authorization(link)
    assert not traversal_ok


def test_report_and_deep_audit_are_read_only_and_grant_no_authority(campaign) -> None:
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    fast = storage_commands.storage_report(context, SimpleNamespace(top=5, deep=False))
    assert fast["destructive_actions_performed"] is False
    assert fast["grants_mutation_authority"] is False
    assert fast["receipt_cache_is_separate_from_campaign_state"] is True
    deep = storage_commands.storage_report(context, SimpleNamespace(top=5, deep=True))
    assert deep["accounting_mode"] == "exact_recursive_physical"
    assert deep["grants_mutation_authority"] is False


def test_receipt_cache_is_reported_separately_from_campaign_state(campaign) -> None:
    snapshot = campaign.snapshot()
    receipts = snapshot.view("campaign_store:hash_receipts")
    state = snapshot.view("campaign_store:state")
    assert receipts.artifact_class.value == "reusable_cache_index"
    assert state.artifact_class.value == "currentness_state"
    assert receipts.cache_reconstructible and not state.cache_reconstructible


def test_safe_tier_never_evicts_the_acceleration_cache(campaign) -> None:
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    plan, _snapshot = storage_commands.build_cleanup_plan(
        context, _policy(action=ACTION_CLEANUP, tier="safe")
    )
    for action in plan.actions:
        assert action.action != "evict_cache"
        assert "hash-receipts" not in str(action.path)


def test_no_generic_is_current_then_unlink_path_exists() -> None:
    """Structural: mutation always runs inside an owner-local race barrier."""

    executor = Path(cli.__file__).parent.joinpath("storage", "executor.py").read_text(
        encoding="utf-8"
    )
    assert "with owner_mutation_barrier(self.paths, generations):" in executor
    barrier_index = executor.index("owner_mutation_barrier(self.paths, generations)")
    mutate_index = executor.index("self._execute_actions(plan, snapshot, result)")
    assert barrier_index < mutate_index
    for module in ("archive.py", "dedup.py"):
        text = Path(cli.__file__).parent.joinpath("storage", module).read_text(
            encoding="utf-8"
        )
        assert "owner_mutation_barrier" in text


def test_p5_and_p7_publishers_hold_the_same_owner_barrier() -> None:
    """Both sides of the object-before-pointer window use one barrier."""

    root = Path(cli.__file__).parent
    publication = (root / "post_selection_publication.py").read_text(encoding="utf-8")
    runtime = (root / "campaign_post_selection_runtime.py").read_text(encoding="utf-8")
    qualification = (root / "qualification" / "runtime.py").read_text(encoding="utf-8")
    assert "post_selection_publication_barrier" in publication
    assert publication.count("post_selection_publication_barrier") >= 2
    assert runtime.count("post_selection_publication_barrier") >= 3
    assert qualification.count("qualification_publication_barrier") >= 3


# ---------------------------------------------------------------------------
# Coverage carried forward from the retired STOR3/STOR4/STOR5 gates
# ---------------------------------------------------------------------------


def test_historical_derived_caches_without_an_owner_seam_are_retained(campaign) -> None:
    """No owner certifies these, so no tier evicts them."""

    for name in ("evaluation-graphs", "evaluation-predictions", "model-sweep"):
        root = campaign.paths.internal / name
        root.mkdir(parents=True, exist_ok=True)
        (root / "payload.bin").write_bytes(b"keep" * 256)
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="cache", apply=True, dry_run=False)
    )
    assert payload["execution"]["status"] == "complete"
    for name in ("evaluation-graphs", "evaluation-predictions", "model-sweep"):
        assert (campaign.paths.internal / name / "payload.bin").read_bytes() == b"keep" * 256


def test_an_orphan_record_symlink_unlinks_only_the_campaign_link(
    campaign, tmp_path: Path
) -> None:
    external = tmp_path / "external-cache"
    external.mkdir()
    important = external / "user.bin"
    important.write_bytes(b"never-delete")
    records = campaign.paths.internal / "records"
    records.mkdir(parents=True, exist_ok=True)
    link = records / "orphan-symlink"
    link.symlink_to(external, target_is_directory=True)
    old = time.time() - 24 * 3600.0
    os.utime(link, (old, old), follow_symlinks=False)

    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="safe", apply=True, dry_run=False)
    )
    assert payload["execution"]["status"] == "complete"
    assert not link.is_symlink()
    assert important.read_bytes() == b"never-delete"


def test_the_execution_audit_is_append_only_and_records_pre_delete_identity(
    campaign,
) -> None:
    records = campaign.paths.internal / "records"
    records.mkdir(parents=True, exist_ok=True)
    old = time.time() - 24 * 3600.0
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    digests = []
    for name in ("orphan-1", "orphan-2"):
        child = records / name
        child.mkdir(exist_ok=True)
        (child / "payload.bin").write_bytes(name.encode())
        os.utime(child / "payload.bin", (old, old))
        os.utime(child, (old, old))
        payload = storage_commands.storage_cleanup(
            context, SimpleNamespace(tier="safe", apply=True, dry_run=False)
        )
        assert payload["execution"]["status"] == "complete"
        assert payload["execution"]["completed_actions"]
        action = payload["execution"]["completed_actions"][0]
        identity = action["filesystem_identity"]
        assert identity["schema"] == "mdstats.mlff-filesystem-identity.v1"
        assert identity["kind"] in {"directory", "file", "symlink"}
        digests.append(context.control_plane.read_audit()[-1]["event_digest"])
    assert len(set(digests)) == 2
    assert len(context.control_plane.read_audit()) >= 2


def test_the_deep_audit_classifies_the_storage_control_plane_and_receipt_cache(
    campaign,
) -> None:
    _create_archive(campaign, reclaim_hot=False)
    campaign.paths.state_db.parent.mkdir(parents=True, exist_ok=True)
    payload = storage_commands.storage_report(
        storage_commands.StorageCommandContext(
            campaign.cfg, campaign.paths, campaign.store, campaign.boundary
        ),
        SimpleNamespace(top=200, deep=True),
    )
    families = {item["family"]: item for item in payload["families"]}
    assert families["storage_control_plane"]["manual_reclamation_eligibility"] == "prohibited"
    assert (
        families["campaign_state_and_provenance"]["automatic_reclamation_eligibility"]
        == "prohibited"
    )
    assert "sha256_receipt_cache" not in families or (
        families["sha256_receipt_cache"]["retention_class"] == "reconstructable_cache"
    )


# ---------------------------------------------------------------------------
# Remaining S2/S3/section-5 acceptance
# ---------------------------------------------------------------------------


def test_cross_device_candidates_retain_duplicate_bytes(campaign, monkeypatch) -> None:
    """An unsupported filesystem layout keeps duplicates, never fails."""

    from mdstats.training_data.storage import dedup as dedup_mod

    root = campaign.historical_bulk()
    payload = b"identical" * 1024
    first = root / "run-a" / "a.bin"
    second = root / "run-a" / "b.bin"
    for path in (first, second):
        path.write_bytes(payload)
        os.chmod(path, 0o644)
    monkeypatch.setattr(dedup_mod, "same_filesystem", lambda a, b: False)
    result = _dedup(campaign, apply=True)
    assert result.links_replaced == 0
    assert any("cross-device" in note for note in result.excluded)
    assert first.read_bytes() == payload == second.read_bytes()
    assert first.stat().st_ino != second.stat().st_ino


def test_no_dedup_eligible_family_has_an_accepted_in_place_writer() -> None:
    """Structural: only superseded generation roots are dedup candidates.

    Every P1-P7 writer writes into the *current* generation root, so a
    superseded root has no accepted in-place content or metadata writer.
    """

    from mdstats.training_data.storage import owners as owners_mod

    source = Path(owners_mod.__file__).read_text(encoding="utf-8")
    tree = __import__("ast").parse(source)
    ast = __import__("ast")
    eligible_sites = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "dedup_eligible":
            eligible_sites += 1
            # Eligibility is never an unconditional True: it is either the
            # historical flag or a literal on a superseded-generation view.
            rendered = ast.dump(node.value)
            assert "historical" in rendered or "Constant(value=True)" in rendered
    assert eligible_sites == 2, eligible_sites
    # And a current generation never contributes: the P5 runs view ties
    # eligibility to `historical`, and the P3 view exists only for
    # non-current generations.
    assert "dedup_eligible=historical" in source
    assert "if generation is None or generation == current_generation:" in source


def test_active_p7_attempt_scratch_is_never_archive_or_dedup_eligible(campaign) -> None:
    """An in-flight attempt's dependencies are not representation-changeable."""

    from mdstats.training_data.qualification.store import (
        ATTEMPT_STATE_FILENAME,
        QUALIFICATION_ROOT_NAME,
    )

    attempt = (
        campaign.paths.internal
        / QUALIFICATION_ROOT_NAME
        / "g1"
        / "attempts"
        / ("a" * 64)
    )
    attempt.mkdir(parents=True)
    (attempt / "scratch.bin").write_bytes(b"in-flight" * 256)
    (campaign.paths.internal / QUALIFICATION_ROOT_NAME / "g1" / "objects").mkdir(
        parents=True, exist_ok=True
    )
    # No readable attempt state at all is the least safe moment to guess.
    snapshot = campaign.snapshot()
    protected, why = snapshot.path_protection(attempt / "scratch.bin")
    assert protected, why
    assert not any(item.eligible for item in archive_candidates(snapshot) if
                   str(attempt) in str(item.path))
    assert (attempt / ATTEMPT_STATE_FILENAME).exists() is False


def test_inode_admission_failure_refuses_before_any_mutation(campaign) -> None:
    from mdstats.training_data.storage import admission as admission_mod

    policy = _policy(action=ACTION_ARCHIVE)
    campaign.historical_bulk()
    original = admission_mod.observe_filesystem
    try:
        admission_mod.observe_filesystem = lambda location: (1 << 40, 1 << 40, 8)
        with pytest.raises(StorageAdmissionError, match="inodes"):
            admission_mod.admit_storage_operation(
                campaign.paths.workspace,
                policy,
                required_peak_bytes=1024,
                required_inodes=1000,
            )
    finally:
        admission_mod.observe_filesystem = original
    assert (
        campaign.paths.internal / "post-selection" / "g7" / "runs" / "run-a"
        / "checkpoints" / "epoch-1.pt"
    ).is_file()


def test_an_unsupported_archive_schema_is_refused(campaign) -> None:
    result, policy, _root = _create_archive(campaign, reclaim_hot=False)
    _rewrite_manifest(campaign, result.archive_identity, schema="mdstats.someone-elses.v9")
    with pytest.raises(StorageArchiveError, match="schema"):
        verify_cold_archive(campaign.control_plane, result.archive_identity, policy)


def test_a_corrupt_receipt_cache_is_only_a_cache_miss(campaign) -> None:
    """Receipt corruption forces rehashing and never changes a result."""

    from mdstats.training_data.storage.durability import accelerated_sha256

    root = campaign.historical_bulk()
    target = root / "run-a" / "checkpoints" / "epoch-1.pt"
    expected = sha256_file(target)
    receipts = campaign.paths.internal / "hash-receipts.sqlite3"
    receipts.write_bytes(b"not a database at all")
    assert accelerated_sha256(target) == expected
    snapshot = campaign.snapshot()
    view = snapshot.view("campaign_store:hash_receipts")
    assert view.artifact_class.value == "reusable_cache_index"


def test_a_corrupt_owner_record_fails_toward_retention(campaign) -> None:
    """An unreadable owner retains its artifacts rather than releasing them."""

    from mdstats.training_data.qualification.store import (
        ATTEMPT_STATE_FILENAME,
        QUALIFICATION_ROOT_NAME,
    )

    attempt = (
        campaign.paths.internal
        / QUALIFICATION_ROOT_NAME
        / "g1"
        / "attempts"
        / ("b" * 64)
    )
    attempt.mkdir(parents=True)
    (attempt / ATTEMPT_STATE_FILENAME).write_text("{ not json", encoding="utf-8")
    (attempt / "scratch.bin").write_bytes(b"x" * 128)
    snapshot = campaign.snapshot()
    protected, why = snapshot.path_protection(attempt / "scratch.bin")
    assert protected, why
    assert not any(
        item.eligible and str(attempt) in str(item.path)
        for item in safe_candidates_of(snapshot)
    )


def safe_candidates_of(snapshot):
    from mdstats.training_data.storage.inventory import safe_candidates

    return safe_candidates(snapshot)


def test_a_missing_planned_path_does_not_stall_a_removal_plan(campaign) -> None:
    """A candidate that vanished between plan and apply is simply skipped."""

    records = campaign.paths.internal / "records"
    records.mkdir(parents=True, exist_ok=True)
    old = time.time() - 24 * 3600.0
    child = records / "orphan-vanishing"
    child.mkdir()
    (child / "payload.bin").write_bytes(b"x" * 64)
    os.utime(child / "payload.bin", (old, old))
    os.utime(child, (old, old))
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    policy = _policy(action=ACTION_CLEANUP, tier="safe", apply=True)
    plan, _snapshot = storage_commands.build_cleanup_plan(context, policy)
    assert plan.actions
    import shutil as _shutil

    _shutil.rmtree(child)
    result = context.executor(policy).apply(plan, trigger="test:vanished")
    assert result.status in {"complete", "refused"}
    assert not child.exists()


def test_cleanup_enabled_false_withholds_apply_but_not_reporting(campaign) -> None:
    """The historical `[cleanup].enabled` switch keeps its documented meaning."""

    from mdstats.training_data.storage.commands import StorageDisabledError

    records = campaign.paths.internal / "records"
    records.mkdir(parents=True, exist_ok=True)
    old = time.time() - 24 * 3600.0
    child = records / "orphan-disabled"
    child.mkdir()
    (child / "payload.bin").write_bytes(b"x" * 64)
    os.utime(child / "payload.bin", (old, old))
    os.utime(child, (old, old))

    cfg = dict(campaign.cfg)
    cfg["cleanup"] = {**dict(cfg.get("cleanup", {})), "enabled": False}
    context = storage_commands.StorageCommandContext(
        cfg, campaign.paths, campaign.store, campaign.boundary
    )
    with pytest.raises(StorageDisabledError):
        storage_commands.storage_cleanup(
            context, SimpleNamespace(tier="safe", apply=True, dry_run=False)
        )
    assert child.is_dir()
    # Planning and reporting stay available.
    payload = storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="safe", apply=False, dry_run=True)
    )
    assert payload["execution"] is None
    assert payload["plan"]["action_count"] >= 1
    assert child.is_dir()


def test_the_cleanup_event_bound_normalizes_into_the_policy_identity(campaign) -> None:
    """A historical `[cleanup]` knob is an alias, normalized before hashing."""

    from mdstats.training_data.storage import commands as commands_mod

    args = SimpleNamespace(tier="safe", apply=False, dry_run=True)
    default = commands_mod._resolve(args, {}, action=ACTION_CLEANUP)
    aliased = commands_mod._resolve(
        args, {"cleanup": {"maximum_event_records": 25}}, action=ACTION_CLEANUP
    )
    explicit = commands_mod._resolve(
        args,
        {"storage": {"sqlite_compaction_maximum_events": 25}},
        action=ACTION_CLEANUP,
    )
    assert aliased.policy_identity == explicit.policy_identity
    assert aliased.policy_identity != default.policy_identity


def test_the_written_plan_is_advisory_and_authorizes_nothing(campaign) -> None:
    import json as _json

    records = campaign.paths.internal / "records"
    records.mkdir(parents=True, exist_ok=True)
    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="safe", apply=False, dry_run=True)
    )
    written = _json.loads(
        (campaign.paths.results / "storage-cleanup-plan-safe.json").read_text(
            encoding="utf-8"
        )
    )
    assert written["advisory_copy"] is True
    assert written["authorizes_apply"] is False
    assert written["grants_scientific_authority"] is False


def test_the_report_names_p2_as_an_explicit_owner_surface(campaign) -> None:
    """P2 statistical authority is reported through its owner, not a path family."""

    payload = storage_commands.storage_report(
        storage_commands.StorageCommandContext(
            campaign.cfg, campaign.paths, campaign.store, campaign.boundary
        ),
        SimpleNamespace(top=200, deep=False),
    )
    owners = {item["owner"] for item in payload["owner_families"]}
    assert "p2" in owners
    p2 = campaign.snapshot().view("p2:statistical_authorities")
    assert p2 is not None and p2.current and p2.hot_path_required
    assert "reducer" in p2.detail
    assert payload["resolved_policy_summary"]


def test_sqlite_compaction_is_admitted_against_the_safety_reserve(campaign) -> None:
    """VACUUM's temporary amplification is admitted like any other operation."""

    context = storage_commands.StorageCommandContext(
        campaign.cfg, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(
        context, SimpleNamespace(tier="safe", apply=True, dry_run=False)
    )
    compaction = payload["state_compaction"]
    assert compaction["performed"] is True
    assert compaction["admission"]["required_peak_bytes"] >= 0
    assert campaign.paths.state_db.is_file()

    # An unsatisfiable reserve skips compaction instead of risking the state db.
    huge = dict(campaign.cfg)
    huge["storage"] = {"safety_reserve_bytes": 1 << 62}
    starved = storage_commands.StorageCommandContext(
        huge, campaign.paths, campaign.store, campaign.boundary
    )
    payload = storage_commands.storage_cleanup(
        starved, SimpleNamespace(tier="safe", apply=True, dry_run=False)
    )
    assert payload["state_compaction"]["performed"] is False
    assert "not admitted" in payload["state_compaction"]["detail"]
    assert campaign.paths.state_db.is_file()


def test_the_storage_reserve_never_undercuts_the_campaign_execution_floor() -> None:
    """Two reserves compose as the stricter floor, not as a weaker second one."""

    from mdstats.training_data.storage import commands as commands_mod

    args = SimpleNamespace(tier="safe", apply=False, dry_run=True)
    policy = commands_mod._resolve(
        args, {"execution": {"minimum_free_disk_gib": 20.0}}, action=ACTION_CLEANUP
    )
    assert policy.safety_reserve_bytes == 20 * 1024**3
    # An explicitly larger storage reserve still wins.
    stricter = commands_mod._resolve(
        args,
        {
            "execution": {"minimum_free_disk_gib": 20.0},
            "storage": {"safety_reserve_bytes": 64 * 1024**3},
        },
        action=ACTION_CLEANUP,
    )
    assert stricter.safety_reserve_bytes == 64 * 1024**3
