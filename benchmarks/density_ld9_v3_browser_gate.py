#!/usr/bin/env python3
"""LD9-V3 complete twelve-shell browser-scene gate."""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

import cloudpickle

from mdstats import (
    AtomicDensity3DRenderOptions,
    BrowserMeshBudget,
    DensitySceneAllocationOptions,
    Trajectory3DRenderOptions,
    plot_framework_dynamics_3d,
)


def rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_pickle", type=Path)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    with args.scene_pickle.open("rb") as handle:
        scene = cloudpickle.load(handle)

    started = time.perf_counter()
    result = plot_framework_dynamics_3d(
        scene,
        trajectory_options=Trajectory3DRenderOptions(
            group_by_species=True,
            enable_hover=False,
            show_start_end=True,
            line_width=2.0,
            opacity=0.60,
        ),
        density_options=AtomicDensity3DRenderOptions(
            mass_fractions=(0.50, 0.80, 0.95),
            max_mesh_faces=250_000,
            show_samples=False,
        ),
        browser_budget=BrowserMeshBudget(),
        scene_allocation_options=DensitySceneAllocationOptions(
            min_canonical_faces_per_shell=4_000,
            reserve_face_fraction=0.15,
        ),
        isolate_large_sparse_meshes=True,
    )
    render_seconds = time.perf_counter() - started
    serialize_started = time.perf_counter()
    result.write_html(args.html, include_plotlyjs=True)
    serialize_seconds = time.perf_counter() - serialize_started
    report = result.browser_budget_report
    usage = result.browser_usage
    assert report is not None and usage is not None
    evidence = {
        "schema_version": "mdstats.ld9-v3-browser-gate.v1",
        "package_version": "0.19.61a0",
        "scene": "TRAJECTORY(4), 1,500 frames, four species, 12 HDR shells",
        "render_seconds": render_seconds,
        "serialization_seconds": serialize_seconds,
        "peak_rss_bytes": rss_bytes(),
        "html_path": str(args.html),
        "html_bytes": args.html.stat().st_size,
        "budget_report": report.to_json_dict(),
        "render_metadata": dict(result.render_metadata),
        "figure_trace_count": len(result.figure.data),
        "trajectory_unique_trace_count": len(
            {ids[0] for ids in result.trajectory_trace_indices.values()}
        ),
    }
    args.json.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    lines = [
        "# LD9-V3 twelve-shell browser gate",
        "",
        f"- Render time: **{render_seconds:.3f} s**",
        f"- Serialization time: **{serialize_seconds:.3f} s**",
        f"- Density faces: **{usage.final_density_face_count:,}**",
        f"- Density vertices: **{usage.final_density_vertex_count:,}**",
        f"- Plotly traces: **{usage.plotly_trace_count}**",
        f"- HTML bytes: **{usage.final_html_bytes:,}**",
        f"- Peak RSS: **{rss_bytes() / 1024**3:.3f} GiB**",
        f"- Budget passed: **{report.passed}**",
        "",
        "| Trace | Faces | Vertices | Replication |",
        "|---|---:|---:|---:|",
    ]
    for trace in usage.density_traces:
        lines.append(
            f"| {trace.trace_key} | {trace.serialized_face_count:,} | "
            f"{trace.serialized_vertex_count:,} | {trace.display_replication} |"
        )
    args.markdown.write_text("\n".join(lines) + "\n")
    print(json.dumps({
        "faces": usage.final_density_face_count,
        "vertices": usage.final_density_vertex_count,
        "traces": usage.plotly_trace_count,
        "html_bytes": usage.final_html_bytes,
        "render_seconds": render_seconds,
        "passed": report.passed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
