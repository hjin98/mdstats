"""Bounded representative measurements for the owner-driven storage reset.

This is the S4 measurement harness for the storage/I-O reset workplan. It is
deliberately bounded: it measures the storage subsystem's own cost surfaces on a
synthetic campaign-shaped tree, not a production campaign. It establishes no
production-scale, GPU, or HPC-storage claim, and it is not a qualification run.

Measured surfaces, each named by the workplan:

1. owner-inventory fast reporting versus the explicit deep physical audit;
2. shared SHA-256 receipt reuse across repeated storage passes;
3. archive codec/level choice at a representative compressibility;
4. I/O concurrency bounded independently of CPU worker count;
5. cold restore cost, so archival is never optimized without its inverse.

Usage::

    python benchmarks/benchmark_mlff_storage_io_reset.py --out results.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any


def _build_tree(root: Path, *, files: int, size_bytes: int, compressible: float) -> int:
    """A campaign-shaped historical bulk tree with realistic compressibility."""

    rng = random.Random(20260901)
    total = 0
    for index in range(files):
        directory = root / f"run-{index % 8}" / "checkpoints"
        directory.mkdir(parents=True, exist_ok=True)
        head = int(size_bytes * compressible)
        payload = b"\0" * head + rng.randbytes(size_bytes - head)
        (directory / f"epoch-{index}.pt").write_bytes(payload)
        total += len(payload)
    return total


def _timed(callable_: Any) -> tuple[float, Any]:
    start = time.perf_counter()
    value = callable_()
    return time.perf_counter() - start, value


def _campaign(tmp: Path):
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data import campaign_cli

    config = tmp / "campaign.toml"
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
    cfg, paths = cli._load_config(config)
    paths.ensure()
    store = cli.CampaignStore(paths.state_db)
    boundary = cli._campaign_ownership_boundary(cfg, paths, store)
    return cfg, paths, store, boundary


def run(*, files: int, size_bytes: int) -> dict[str, Any]:
    from mdstats.training_data.storage import commands as storage_commands
    from mdstats.training_data.storage.archive import (
        create_cold_archive,
        restore_cold_archive,
    )
    from mdstats.training_data.storage.control_plane import open_storage_control_plane
    from mdstats.training_data.storage.durability import parallel_digests
    from mdstats.training_data.storage.inventory import build_storage_inventory
    from mdstats.training_data.storage.plan import build_storage_plan
    from mdstats.training_data.storage.policy import resolve_storage_policy

    tmp = Path(tempfile.mkdtemp(prefix="mlff-storage-bench-"))
    try:
        cfg, paths, store, boundary = _campaign(tmp)
        bulk = paths.internal / "post-selection" / "g7" / "runs"
        (paths.internal / "post-selection" / "g7" / "objects").mkdir(parents=True)
        logical = _build_tree(bulk, files=files, size_bytes=size_bytes, compressible=0.5)
        control_plane = open_storage_control_plane(paths)
        results: dict[str, Any] = {
            "schema": "mdstats.mlff-storage-io-reset-benchmark.v1",
            "fixture": {
                "file_count": files,
                "file_size_bytes": size_bytes,
                "logical_bytes": logical,
                "compressible_fraction": 0.5,
            },
        }

        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        from types import SimpleNamespace

        # 1. fast owner report vs explicit deep physical audit
        fast_seconds, _ = _timed(
            lambda: storage_commands.storage_report(
                context, SimpleNamespace(top=20, deep=False)
            )
        )
        deep_seconds, _ = _timed(
            lambda: storage_commands.storage_report(
                context, SimpleNamespace(top=20, deep=True)
            )
        )
        results["reporting"] = {
            "fast_owner_report_seconds": fast_seconds,
            "deep_physical_audit_seconds": deep_seconds,
            "ratio_deep_over_fast": (deep_seconds / fast_seconds) if fast_seconds else None,
            "note": (
                "the fast report is bounded by the owner-claimed subtrees while the "
                "deep audit is bounded by the whole workspace. This fixture makes the "
                "two coincide, so no physical speedup is claimed here: the fast "
                "report's value is that it answers ownership questions a physical "
                "walk cannot answer at all"
            ),
        }

        # 2. receipt reuse across repeated immutable hashing passes
        targets = sorted(str(p) for p in bulk.rglob("*") if p.is_file())
        cold_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=False)
        )
        warm_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=True)
        )
        reuse_seconds, _ = _timed(
            lambda: parallel_digests(targets, workers=1, accelerated=True)
        )
        results["receipt_reuse"] = {
            "uncached_seconds": cold_seconds,
            "first_accelerated_seconds": warm_seconds,
            "reused_seconds": reuse_seconds,
            "speedup_on_reuse": (cold_seconds / reuse_seconds) if reuse_seconds else None,
            "note": (
                "receipts accelerate repeated hashing of large immutable artifacts "
                "and never establish validity; below "
                "RECEIPT_ACCELERATION_MINIMUM_BYTES the direct hash is used because "
                "the receipt round-trip costs more than the read it avoids"
            ),
        }

        # 3. bounded I/O concurrency, independent of CPU worker count
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

        # 4. archive codec/level, and 5. the cold restore that inverts it
        codecs: dict[str, Any] = {}
        for codec, level in (("none", 0), ("gzip", 1), ("gzip", 6), ("gzip", 9)):
            snapshot = build_storage_inventory(
                cfg, paths, store, protected_inputs=boundary.protected_inputs,
                control_plane=control_plane,
            )
            policy = resolve_storage_policy(
                {
                    "storage": {
                        "archive_codec": codec,
                        "archive_compression_level": level,
                    }
                },
                action="archive",
                apply=True,
            )
            plan = build_storage_plan(snapshot, policy, ())
            seconds, result = _timed(
                lambda: create_cold_archive(
                    workspace=paths.workspace,
                    control_plane=control_plane,
                    policy=policy,
                    boundary=boundary,
                    roots=[bulk],
                    lineage={"benchmark": True, "codec": codec, "level": level},
                    plan_identity=plan.plan_identity,
                    paths=paths,
                    reclaim_hot=False,
                )
            )
            blob = control_plane.resolve_archive_blob(
                result.manifest["archive_locator"]
            )
            restore_seconds, _ = _timed(
                lambda: restore_cold_archive(
                    workspace=paths.workspace,
                    control_plane=control_plane,
                    policy=resolve_storage_policy({}, action="restore", apply=True),
                    boundary=boundary,
                    archive_identity=result.archive_identity,
                    paths=paths,
                )
            )
            codecs[f"{codec}:{level}"] = {
                "create_seconds": seconds,
                "restore_seconds": restore_seconds,
                "archive_bytes": int(blob.stat().st_size),
                "ratio": logical / max(1, int(blob.stat().st_size)),
            }
        results["archive_codecs"] = codecs
        store.close()
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
