"""Bounded representative measurements for the owner-driven storage reset.

This is the S4 measurement harness for the storage/I-O reset workplan. It runs
against a **real campaign** driven through the accepted P1-P5 lifecycle, so the
owner adapters, the cross-owner inventory, the plan/revalidation path, and the
archive/restore engines under measurement are the production ones. Only the
numerical trainer below the accepted P5 seam is bounded, and the historical bulk
is padded with owner-recorded members so the fixture reaches a measurable size
without waiting for real training.

It is still deliberately bounded: it establishes no production-scale, GPU, or
HPC-storage claim, and it is not a qualification run.

Measured surfaces, each named by the workplan:

1. the bounded owner report versus the explicit deep physical audit, in both
   filesystem entry visits and wall time, cold and warm;
2. how report cost responds to descendant count, which is the property that
   makes reporting usable on a large campaign at all;
3. shared SHA-256 receipt reuse across repeated storage passes;
4. I/O concurrency bounded independently of CPU worker count;
5. archive codec/level choice at a representative compressibility, and the cold
   restore that inverts it, so archival is never optimized without its inverse.

Usage::

    python benchmarks/benchmark_mlff_storage_io_reset.py --out results.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPOSITORY = Path(__file__).resolve().parent.parent
if str(_REPOSITORY) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY))


def _timed(callable_: Any) -> tuple[float, Any]:
    start = time.perf_counter()
    value = callable_()
    return time.perf_counter() - start, value


def _counted(callable_: Any) -> tuple[int, float, Any]:
    """Wall time and the number of filesystem entry visits one call performs.

    ``Path.lstat`` and ``os.scandir`` are the two primitives every storage
    traversal funnels through, so counting them measures exactly the thing the
    bounded report promises to keep small.
    """

    visits = {"n": 0}
    real_lstat = Path.lstat
    real_scandir = os.scandir

    def counting_lstat(self, *args, **kwargs):
        visits["n"] += 1
        return real_lstat(self, *args, **kwargs)

    def counting_scandir(*args, **kwargs):
        visits["n"] += 1
        return real_scandir(*args, **kwargs)

    Path.lstat = counting_lstat
    os.scandir = counting_scandir
    try:
        seconds, value = _timed(callable_)
    finally:
        Path.lstat = real_lstat
        os.scandir = real_scandir
    return visits["n"], seconds, value


def _real_campaign(tmp: Path):
    """A real campaign with a superseded generation of historical P5 bulk."""

    import tests._mlff_post_selection_fixture as p5
    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

    harness = p5.PostSelectionHarness()
    config, _workspace = p5.build_selected_campaign(tmp)
    assert p5.run_cross_validate(config, harness) == 0
    assert p5.run_train_production(config, harness) == 0
    # Supersede the selected lineage through the real P1-P4 owners, which is
    # what makes the previous generation's run trees historical bulk.
    p5.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0
    return config, p4d


def _pad_historical_bulk(
    run_root: Path, *, files: int, size_bytes: int, compressible: float, prefix: str
) -> int:
    """Add measurable bulk to a real run root and re-record its membership.

    The padding goes through the owner's own membership record, so the run root
    stays a certified closed subtree: this measures the archive path the product
    actually authorizes, not an unowned tree the product would refuse.
    """

    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
        record_post_selection_run_members,
    )

    rng = random.Random(20260901)
    destination = run_root / "checkpoints"
    destination.mkdir(parents=True, exist_ok=True)
    total = 0
    for index in range(files):
        head = int(size_bytes * compressible)
        payload = b"\0" * head + rng.randbytes(size_bytes - head)
        (destination / f"bench-{prefix}-{index}.pt").write_bytes(payload)
        total += len(payload)
    # The owner's completion proof is create-once, so a *harness* that inflates
    # a finished run has to retract the old proof and let the owner re-record the
    # run as it now stands. Production code never does this; it is how this
    # fixture stands in for a run that produced this much bulk in the first
    # place, and the proof that certifies the archive path under measurement is
    # still written by the real owner.
    (run_root / RUN_COMPLETION_ANCHOR_FILENAME).unlink(missing_ok=True)
    (run_root / RUN_TOPOLOGY_MANIFEST_FILENAME).unlink(missing_ok=True)
    record_post_selection_run_members(run_root)
    return total


def _archive_eligible_run_root(cli, cfg, paths, run_roots):
    """The first historical run root the real owners declare cold-replaceable."""

    from mdstats.training_data.storage.control_plane import (
        open_storage_control_plane_readonly,
    )
    from mdstats.training_data.storage.inventory import (
        archive_candidates,
        build_storage_inventory,
    )

    store = cli.CampaignStore(paths.state_db, create=False)
    try:
        with cli.observational_campaign_state():
            boundary = cli._campaign_ownership_boundary(cfg, paths, store)
            snapshot = build_storage_inventory(
                cfg,
                paths,
                store,
                protected_inputs=boundary.protected_inputs,
                control_plane=open_storage_control_plane_readonly(paths),
                certify=True,
            )
        eligible = {
            Path(item.path) for item in archive_candidates(snapshot) if item.eligible
        }
    finally:
        store.close()
    for root in run_roots:
        if root in eligible:
            return root
    raise AssertionError("no historical run root was owner-declared cold-replaceable")


def run(*, files: int, size_bytes: int) -> dict[str, Any]:
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data.storage import commands as storage_commands
    from mdstats.training_data.storage.archive import list_archives, read_manifest
    from mdstats.training_data.storage.control_plane import (
        open_storage_control_plane_readonly,
    )
    from mdstats.training_data.storage.durability import parallel_digests

    tmp = Path(tempfile.mkdtemp(prefix="mlff-storage-bench-"))
    try:
        config, p4d = _real_campaign(tmp)
        cfg, paths = cli._load_config(config)
        runs_root = paths.internal / "post-selection" / "g1" / "runs"
        run_roots = sorted(item for item in runs_root.iterdir() if item.is_dir())
        assert run_roots, "the real P5 owner published no historical run root"
        # Pad a run root the owners actually released, so the archive path being
        # measured is the one the product authorizes rather than one it refuses.
        target_root = _archive_eligible_run_root(cli, cfg, paths, run_roots)
        logical = _pad_historical_bulk(
            target_root,
            files=files,
            size_bytes=size_bytes,
            compressible=0.5,
            prefix="bulk",
        )

        def _context():
            store = cli.CampaignStore(paths.state_db, create=False)
            boundary = cli._campaign_ownership_boundary(cfg, paths, store)
            return store, storage_commands.StorageCommandContext(
                cfg, paths, store, boundary
            )

        def _report(deep: bool):
            store, context = _context()
            try:
                with cli.observational_campaign_state():
                    return storage_commands.storage_report(
                        context, SimpleNamespace(top=20, deep=deep)
                    )
            finally:
                store.close()

        results: dict[str, Any] = {
            "schema": "mdstats.mlff-storage-io-reset-benchmark.v2",
            "fixture": {
                "kind": "real P1-P5 campaign with one superseded generation",
                "padded_file_count": files,
                "padded_file_size_bytes": size_bytes,
                "padded_logical_bytes": logical,
                "compressible_fraction": 0.5,
                "historical_run_roots": len(run_roots),
            },
        }

        # 1. bounded owner report vs explicit deep physical audit, cold and warm
        cold_visits, cold_seconds, payload = _counted(lambda: _report(False))
        warm_visits, warm_seconds, _ = _counted(lambda: _report(False))
        deep_visits, deep_seconds, deep_payload = _counted(lambda: _report(True))
        deep_warm_visits, deep_warm_seconds, _ = _counted(lambda: _report(True))
        results["reporting"] = {
            "owner_report": {
                "cold_seconds": cold_seconds,
                "warm_seconds": warm_seconds,
                "cold_entry_visits": cold_visits,
                "warm_entry_visits": warm_visits,
                "artifact_count": len(payload["artifacts"]),
                "owner_family_count": len(payload["owner_families"]),
            },
            "deep_audit": {
                "cold_seconds": deep_seconds,
                "warm_seconds": deep_warm_seconds,
                "cold_entry_visits": deep_visits,
                "warm_entry_visits": deep_warm_visits,
                "file_count": int(deep_payload["totals"]["file_count"]),
                "complete": bool(deep_payload["complete"]),
            },
            "entry_visit_ratio_deep_over_owner": (
                deep_visits / cold_visits if cold_visits else None
            ),
            "note": (
                "the owner report visits one entry per owner-declared artifact and "
                "never walks a subtree, so its cost is set by how many artifacts the "
                "owners declare; the deep audit is the explicit opt-in whose cost is "
                "set by how much the campaign holds"
            ),
        }

        # 2. does report cost follow descendant count - and does it ever pay for
        #    the O(member-count) topology manifest?
        from mdstats.training_data.campaign_post_selection_runtime import (
            RUN_TOPOLOGY_MANIFEST_FILENAME,
        )

        manifest_path = target_root / RUN_TOPOLOGY_MANIFEST_FILENAME
        touched: list[str] = []
        real_read_text = Path.read_text

        def recording_read_text(self, *args, **kwargs):
            touched.append(str(self))
            return real_read_text(self, *args, **kwargs)

        Path.read_text = recording_read_text
        try:
            _report(False)
        finally:
            Path.read_text = real_read_text
        results["completion_authority"] = {
            "topology_manifest_bytes": int(manifest_path.stat().st_size),
            "topology_manifest_read_by_report": str(manifest_path) in touched,
            "note": (
                "the compact completion anchor is what normal reporting validates; "
                "the O(member-count) topology manifest is read only by exact "
                "closed-subtree certification"
            ),
        }


        before_visits, before_seconds, _ = _counted(lambda: _report(False))
        _pad_historical_bulk(
            target_root,
            files=files * 4,
            size_bytes=1024,
            compressible=0.5,
            prefix="scale",
        )
        after_visits, after_seconds, _ = _counted(lambda: _report(False))
        results["report_scaling"] = {
            "descendants_added": files * 4,
            "entry_visits_before": before_visits,
            "entry_visits_after": after_visits,
            "seconds_before": before_seconds,
            "seconds_after": after_seconds,
            "note": (
                "adding descendants to an owner-declared artifact must not change "
                "the bounded report's entry-visit count"
            ),
        }

        # 3. receipt reuse across repeated immutable hashing passes
        targets = sorted(str(p) for p in target_root.rglob("*") if p.is_file())
        cold_hash_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=False)
        )
        first_warm_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=True)
        )
        reuse_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=True)
        )
        results["receipt_reuse"] = {
            "file_count": len(targets),
            "uncached_seconds": cold_hash_seconds,
            "first_accelerated_seconds": first_warm_seconds,
            "reused_seconds": reuse_seconds,
            "speedup_on_reuse": (
                cold_hash_seconds / reuse_seconds if reuse_seconds else None
            ),
            "note": (
                "receipts accelerate repeated hashing of large immutable artifacts "
                "and never establish validity; below "
                "RECEIPT_ACCELERATION_MINIMUM_BYTES the direct hash is used because "
                "the receipt round-trip costs more than the read it avoids"
            ),
        }

        # 4. bounded I/O concurrency, independent of CPU worker count
        concurrency: dict[str, float] = {}
        for workers in (1, 2, 4, 8):
            from mdstats.training_data import _common

            _common._SHA256_HASHED_IN_PROCESS.clear()
            seconds, _ = _timed(
                lambda w=workers: parallel_digests(
                    targets, workers=w, accelerated=False
                )
            )
            concurrency[str(workers)] = seconds
        results["io_concurrency_seconds"] = concurrency
        results["io_concurrency_note"] = (
            "I/O workers are configured separately from CPU workers so a storage "
            "scan cannot create a metadata or hash thundering herd"
        )

        # 5. archive codec/level through the real command, and its restore
        codecs: dict[str, Any] = {}
        seen: set[str] = set()
        for codec, level in (("none", 0), ("gzip", 1), ("gzip", 6), ("gzip", 9)):
            create_seconds, rc = _timed(
                lambda c=codec, l=level: p4d._run(
                    config,
                    "storage",
                    "archive",
                    "create",
                    "--apply",
                    "--archive-codec",
                    c,
                    "--archive-compression-level",
                    str(l),
                )
            )
            if rc != 0:
                codecs[f"{codec}:{level}"] = {"skipped": "archive creation refused"}
                continue
            plane = open_storage_control_plane_readonly(paths)
            fresh = [
                entry
                for entry in list_archives(plane)
                if str(entry["archive_identity"]) not in seen
            ]
            if not fresh:
                codecs[f"{codec}:{level}"] = {"skipped": "no new representation"}
                continue
            entry = fresh[0]
            identity = str(entry["archive_identity"])
            seen.add(identity)
            blob = plane.resolve_archive_blob(str(entry["archive_locator"]))
            archive_bytes = int(blob.stat().st_size)
            manifest = read_manifest(plane, identity)
            member_bytes = int(manifest["total_expanded_bytes"])
            restore_seconds, restore_rc = _timed(
                lambda i=identity: p4d._run(
                    config, "storage", "archive", "restore", i, "--apply"
                )
            )
            codecs[f"{codec}:{level}"] = {
                "create_seconds": create_seconds,
                "restore_seconds": restore_seconds,
                "restore_exit_code": restore_rc,
                "archive_bytes": archive_bytes,
                "member_count": len(manifest["members"]),
                "member_logical_bytes": member_bytes,
                "represented_artifact_ids": list(manifest["represented_artifact_ids"]),
                "ratio": member_bytes / max(1, archive_bytes),
            }
        results["archive_codecs"] = codecs
        return results
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", type=int, default=48)
    parser.add_argument("--file-size-bytes", type=int, default=1 << 20)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    results = run(files=int(args.files), size_bytes=int(args.file_size_bytes))
    text = json.dumps(results, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
