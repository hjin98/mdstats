"""Bounded before/after evidence for post-DATA4 authority reconstruction.

The P4 repair removed a redundant full VASP frame re-read from current
target-size authority construction, made the normalized frame cache the single
payload acquisition, and restored bounded resource-aware parallelism plus
progress reporting to canonical-frame construction.

This harness measures both shapes against the same real multi-run corpus,
through the same production owners:

``before``
    fresh P1 authentication *and* a full ``read_vasp_frames`` pass per run,
    serially, exactly as ``build_vasp_canonical_frame_authority`` performs it
    -- which is what the pre-repair orchestration called;

``after``
    fresh P1 authentication with no frame payload, one authenticated
    normalized-frame acquisition, then canonical-frame construction at the
    planned worker count.

It is deliberately bounded: it establishes no production-scale claim and is
not a qualification run.  The structural result -- zero source frame reads on
a warm cache -- is the closure criterion; wall time is recorded as supporting
evidence and will vary with filesystem and cache state.

Usage::

    python benchmarks/benchmark_mlff_p4_authority_reconstruction.py --out results.json
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import mdstats
from mdstats.training_data.neutral_substrate import (
    authenticate_vasp_source_authority,
    authenticated_vasp_temperature_targets,
    build_canonical_frame_authority,
    build_source_authority_from_data2_catalog,
    build_vasp_canonical_frame_authority,
)
from mdstats.training_data.neutral_substrate.frame_authority import (
    read_authenticated_vasp_frame_data,
)
from mdstats.training_data.campaign_target_size_runtime import (
    CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR,
    _canonical_frame_worker_ceiling,
)
from mdstats.training_data.resources import detect_system_resources, resolve_worker_count


def _peak_rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class _ReadCounter:
    """Wrap the real VASP frame reader so call counts are structural evidence."""

    def __init__(self) -> None:
        import mdstats.io as io_module

        self._module = io_module
        self._real = io_module.read_vasp_frames
        self.calls: list[str] = []

    def __enter__(self) -> "_ReadCounter":
        def counting(path, *args, **kwargs):
            self.calls.append(str(path))
            return self._real(path, *args, **kwargs)

        self._module.read_vasp_frames = counting
        return self

    def __exit__(self, *exc) -> None:
        self._module.read_vasp_frames = self._real


def _corpus(root: Path, *, runs: int, frames: int) -> tuple:
    """A real multi-run VASP corpus built by the repository's own fixture writer."""

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import tests.test_mlff_neutral_scientific_substrate as fixtures

    for index in range(runs):
        fixtures._write(
            root, f"run{index}", ("Li", "O"), n_frames=frames, tebeg=650 + 50 * index
        )
    manifest = mdstats.TrainingDataManifest(
        dataset_id="p4-authority-benchmark",
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=f"run{index}",
                vasprun=f"run{index}/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            )
            for index in range(runs)
        ),
    )
    catalog = mdstats.build_training_data_source_catalog(
        manifest, base_directory=root
    )
    return manifest, catalog


def _measure(label: str, function) -> dict:
    started = time.monotonic()
    with _ReadCounter() as counter:
        result = function()
    elapsed = time.monotonic() - started
    return {
        "phase": label,
        "seconds": round(elapsed, 4),
        "source_frame_reads": len(counter.calls),
        "peak_rss_mib": round(_peak_rss_mib(), 1),
        "digest": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument(
        "--frames",
        type=int,
        nargs="+",
        default=(96, 1024),
        help="Frames per run; several values sweep the parallel break-even.",
    )
    args = parser.parse_args()

    cases: list[dict] = []
    for frames_per_run in args.frames:
        records = []
        root = Path(tempfile.mkdtemp(prefix="p4-authority-benchmark-"))
        manifest, catalog = _corpus(root, runs=args.runs, frames=frames_per_run)
        authority = build_source_authority_from_data2_catalog(catalog, manifest=manifest)

        records: list[dict] = []

        # --- before: authentication plus a full serial source frame rebuild ------
        records.append(
            _measure(
                "before/direct-vasp-rebuild-serial",
                lambda: build_vasp_canonical_frame_authority(
                    authority, base_directory=root
                ).content_digest,
            )
        )

        # Publish the normalized frame cache the repaired path reuses.
        frame_data, _targets = mdstats.load_vasp_frame_data_by_run(
            catalog, base_directory=root
        )
        cache_root = root / "frame-cache"
        mdstats.write_frame_data_cache(catalog, frame_data, cache_root)
        del frame_data

        resources = detect_system_resources(
            cpu_fraction=0.9, ram_fraction=0.8, gpu_memory_fraction=0.9, device="cpu"
        )
        atom_frames = sum(
            int(data.n_frames) * int(data.n_atoms)
            for data in mdstats.load_frame_data_cache(catalog, cache_root).values()
        )
        workers = resolve_worker_count(
            task_count=args.runs,
            resources=resources,
            requested=0,
            estimated_bytes_per_worker=384 * 1024**2,
            reserved_bytes=args.runs * frames_per_run * 8192,
            maximum_workers=_canonical_frame_worker_ceiling(atom_frames),
        )
        # The unbounded plan is recorded too, because the floor below which
        # one-shot worker startup does not repay itself is what motivates it.
        unbounded_workers = resolve_worker_count(
            task_count=args.runs,
            resources=resources,
            requested=0,
            estimated_bytes_per_worker=384 * 1024**2,
            reserved_bytes=args.runs * frames_per_run * 8192,
        )

        def repaired(active_workers: int):
            def run() -> str:
                authenticated = authenticate_vasp_source_authority(
                    authority, base_directory=root
                )
                cached = mdstats.load_frame_data_cache(catalog, cache_root)
                return build_canonical_frame_authority(
                    authority,
                    dict(cached),
                    temperature_targets_by_run=authenticated_vasp_temperature_targets(
                        authenticated
                    ),
                    parallel_workers=active_workers,
                ).content_digest

            return run

        # Serial warm cache isolates the removed redundant I/O from the parallelism.
        serial = _measure("after/warm-cache-serial", repaired(1))
        serial["canonical_workers"] = 1
        records.append(serial)

        after = _measure("after/warm-cache-planned", repaired(workers))
        after["canonical_workers"] = workers
        records.append(after)

        if unbounded_workers != workers:
            unbounded = _measure(
                "after/warm-cache-unbounded-workers", repaired(unbounded_workers)
            )
            unbounded["canonical_workers"] = unbounded_workers
            records.append(unbounded)

        # --- after, cache miss: one source read per run, payload reused ---------
        def rebuilt() -> str:
            authenticated = authenticate_vasp_source_authority(
                authority, base_directory=root
            )
            loaded = read_authenticated_vasp_frame_data(authenticated)
            return build_canonical_frame_authority(
                authority,
                loaded,
                temperature_targets_by_run=authenticated_vasp_temperature_targets(
                    authenticated
                ),
                parallel_workers=workers,
            ).content_digest

        miss = _measure("after/cache-rebuild-planned", rebuilt)
        miss["canonical_workers"] = workers
        records.append(miss)

        cases.append(
            {
                "frames_per_run": frames_per_run,
                "atom_frames": atom_frames,
                "scientific_identity_preserved": (
                    len({record["digest"] for record in records}) == 1
                ),
                "canonical_frame_authority_digest": sorted(
                    {record["digest"] for record in records}
                ),
                "measurements": records,
            }
        )

    resources = detect_system_resources(
        cpu_fraction=0.9, ram_fraction=0.8, gpu_memory_fraction=0.9, device="cpu"
    )
    payload = {
        "schema": "mdstats.benchmark.p4-authority-reconstruction.v1",
        "runs": args.runs,
        "resources": resources.summary(),
        "parallel_atom_frame_floor": CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR,
        "scientific_identity_preserved": all(
            case["scientific_identity_preserved"] for case in cases
        ),
        "cases": cases,
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if args.out is not None:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0 if payload["scientific_identity_preserved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
