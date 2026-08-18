#!/usr/bin/env python3
"""Benchmark the LD8-S1 exact packed periodic support atlas.

This benchmark keeps the scientific estimator unchanged. It resolves the full
adaptive grid at the production 1e-8 Gaussian tail tolerance, aggregates one
global periodic CIC source per field, and constructs the exact modular support
atlas with source-block padded-bitset dilation. It never allocates the complete
source-node by stencil-offset pair array.
"""

from __future__ import annotations

import argparse
import json
import pickle
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np

from density_ld8_p0_benchmark import _resolution_options, _scene_field_samples
from mdstats.plotting.atomic_density import resolve_density_numerics
from mdstats.plotting.density_block_routing import (
    clear_density_routing_cache,
    get_periodic_kernel_block_routing,
)
from mdstats.plotting.density_scene_planning import DensitySupportPlanningLimits
from mdstats.plotting.density_sparse_optimization import (
    aggregate_periodic_cic_sparse_optimized,
    get_periodic_gaussian_stencil_support,
)
from mdstats.plotting.density_support_atlas import (
    build_density_support_atlas,
    pack_periodic_cic_source,
)

SCHEMA = "mdstats.density-ld8-s1-support-atlas-benchmark.v1"


def _timer() -> float:
    return time.perf_counter()


def _baseline_by_label(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["label"]): item for item in payload.get("fields", [])}


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LD8-S1 exact support-atlas benchmark",
        "",
        f"- Schema: `{payload['schema']}`",
        f"- Kernel tail tolerance: `{payload['kernel_tail_tolerance']:.1e}`",
        f"- Total benchmark time: `{payload['total_seconds']:.3f} s`",
        "",
        "| Field | Grid | Source nodes | Source blocks | Target blocks | Target nodes | Atlas time | Pair/shift reduction | LD7 count match |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["fields"]:
        match = item.get("ld7_active_node_count_match")
        match_text = "n/a" if match is None else ("yes" if match else "no")
        lines.append(
            "| {label} | {grid} | {source_nodes:,} | {source_blocks:,} | "
            "{target_blocks:,} | {target_nodes:,} | {atlas_seconds:.3f} s | "
            "{reduction:.1f}x | {match} |".format(
                label=item["label"],
                grid="x".join(str(v) for v in item["grid_shape"]),
                source_nodes=item["source_node_count"],
                source_blocks=item["source_block_count"],
                target_blocks=item["target_block_count"],
                target_nodes=item["target_support_node_count"],
                atlas_seconds=item["atlas_seconds"],
                reduction=item["fine_pair_to_bitset_shift_ratio"],
                match=match_text,
            )
        )
    lines.extend(
        [
            "",
            "The reduction ratio compares the complete fine interaction count",
            "`occupied CIC nodes x stencil offsets` with the exact S1 count",
            "`occupied source blocks x stencil offsets`. It is an operation-count",
            "reference, not a claim of equal cost per operation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = _timer()
    with args.scene.open("rb") as handle:
        scene = pickle.load(handle)
    baseline = _baseline_by_label(args.ld7_baseline)
    fields = list(scene.atomic_density_fields)
    if args.labels:
        wanted = set(args.labels)
        fields = [field for field in fields if field.label in wanted]
    if not fields:
        raise ValueError("No atomic density fields matched the requested labels.")

    clear_density_routing_cache()
    results: list[dict[str, Any]] = []
    for field in fields:
        field_started = _timer()
        print(f"[LD8-S1] {field.label}: resolving and planning", flush=True)
        fractional_by_frame, samples = _scene_field_samples(scene, field, None)
        frame_weights = np.full(
            fractional_by_frame.shape[0],
            1.0 / fractional_by_frame.shape[0],
            dtype=np.float64,
        )
        options = _resolution_options(args.kernel_tail_tolerance)

        t0 = _timer()
        resolved = resolve_density_numerics(
            scene.display_cell,
            options=options,
            fractional_by_frame=fractional_by_frame,
            frame_weights=frame_weights,
            pbc=np.ones(3, dtype=bool),
            max_voxels=int(np.iinfo(np.int64).max),
            field_label=field.label,
        )
        resolution_seconds = _timer() - t0
        print(f"[LD8-S1] {field.label}: resolution {resolution_seconds:.3f} s", flush=True)

        t0 = _timer()
        sparse_source = aggregate_periodic_cic_sparse_optimized(
            samples, resolved.grid_shape
        )
        cic_seconds = _timer() - t0
        print(f"[LD8-S1] {field.label}: CIC {cic_seconds:.3f} s", flush=True)

        t0 = _timer()
        stencil, stencil_cache_hit = get_periodic_gaussian_stencil_support(
            resolved.grid_shape,
            scene.display_cell,
            resolved.gaussian_bandwidth,
            kernel_tail_tolerance=args.kernel_tail_tolerance,
        )
        stencil_seconds = _timer() - t0
        print(f"[LD8-S1] {field.label}: stencil {stencil_seconds:.3f} s", flush=True)

        t0 = _timer()
        packed_source = pack_periodic_cic_source(
            sparse_source, storage_block_shape=tuple(args.block_shape)
        )
        source_packing_seconds = _timer() - t0
        print(f"[LD8-S1] {field.label}: source pack {source_packing_seconds:.3f} s", flush=True)

        t0 = _timer()
        routing, routing_cache_hit = get_periodic_kernel_block_routing(
            stencil, storage_block_shape=tuple(args.block_shape)
        )
        routing_seconds = _timer() - t0
        print(f"[LD8-S1] {field.label}: routing {routing_seconds:.3f} s", flush=True)

        t0 = _timer()
        atlas = build_density_support_atlas(
            packed_source,
            routing,
            planning_limits=DensitySupportPlanningLimits(),
            compute_connected_components=args.connected_components,
        )
        atlas_seconds = _timer() - t0

        complete_pairs = (
            packed_source.occupied_node_count * routing.stencil_offset_count
        )
        shift_count = (
            packed_source.source_block_count * routing.stencil_offset_count
        )
        baseline_item = baseline.get(field.label)
        baseline_active_nodes = None
        baseline_match = None
        if baseline_item is not None:
            baseline_active_nodes = int(
                baseline_item["ld7_baseline"]["metadata"]["active_node_count"]
            )
            baseline_match = baseline_active_nodes == atlas.target_support_node_count
            if not baseline_match:
                raise RuntimeError(
                    f"{field.label}: atlas target-node count "
                    f"{atlas.target_support_node_count} differs from LD7 "
                    f"{baseline_active_nodes}."
                )

        print(
            f"[LD8-S1] {field.label}: {atlas.target_support_node_count:,} nodes, "
            f"{atlas.target_block_count:,} blocks, atlas {atlas_seconds:.3f} s",
            flush=True,
        )
        results.append(
            {
                "label": field.label,
                "frame_count": int(fractional_by_frame.shape[0]),
                "grid_shape": list(resolved.grid_shape),
                "gaussian_bandwidth_angstrom": resolved.gaussian_bandwidth,
                "kernel_tail_tolerance": args.kernel_tail_tolerance,
                "stencil_offset_count": routing.stencil_offset_count,
                "source_node_count": packed_source.occupied_node_count,
                "source_block_count": packed_source.source_block_count,
                "target_block_count": atlas.target_block_count,
                "target_support_node_count": atlas.target_support_node_count,
                "source_target_edge_count": atlas.source_target_edge_count,
                "component_count": atlas.component_count,
                "complete_fine_pair_count_reference": complete_pairs,
                "bitset_shift_operation_count": shift_count,
                "fine_pair_to_bitset_shift_ratio": complete_pairs / shift_count,
                "source_retained_bytes": packed_source.retained_array_bytes,
                "routing_retained_bytes": routing.retained_array_bytes,
                "atlas_retained_bytes": atlas.retained_array_bytes,
                "predicted_peak_bytes": atlas.planning.predicted_peak_bytes,
                "maximum_lifted_brick_nodes": atlas.planning.maximum_lifted_brick_nodes,
                "maximum_lifted_transient_bytes": atlas.planning.maximum_lifted_transient_bytes,
                "realized_maximum_lifted_transient_bytes": int(
                    atlas.metadata["maximum_lifted_transient_bytes"]
                ),
                "resolution_seconds": resolution_seconds,
                "cic_seconds": cic_seconds,
                "stencil_seconds": stencil_seconds,
                "source_packing_seconds": source_packing_seconds,
                "routing_seconds": routing_seconds,
                "atlas_seconds": atlas_seconds,
                "field_total_seconds": _timer() - field_started,
                "stencil_cache_hit": stencil_cache_hit,
                "routing_cache_hit": routing_cache_hit,
                "ld7_active_node_count": baseline_active_nodes,
                "ld7_active_node_count_match": baseline_match,
                "algorithm": atlas.metadata["algorithm"],
                "complete_fine_pair_array_allocated": atlas.metadata[
                    "complete_fine_pair_array_allocated"
                ],
                "source_specific_global_cache_used": atlas.metadata[
                    "source_specific_global_cache_used"
                ],
            }
        )

    return {
        "schema": SCHEMA,
        "scene_pickle": str(args.scene),
        "ld7_baseline": None if args.ld7_baseline is None else str(args.ld7_baseline),
        "kernel_tail_tolerance": args.kernel_tail_tolerance,
        "storage_block_shape": list(args.block_shape),
        "connected_components": args.connected_components,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "fields": results,
        "total_seconds": _timer() - started,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=Path)
    parser.add_argument("--ld7-baseline", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path)
    parser.add_argument("--kernel-tail-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--block-shape", type=int, nargs=3, default=(16, 16, 16))
    parser.add_argument("--label", dest="labels", action="append")
    parser.add_argument("--connected-components", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown = args.output_markdown or args.output_json.with_suffix(".md")
    _write_markdown(payload, markdown)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
