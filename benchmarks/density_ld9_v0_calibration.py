#!/usr/bin/env python3
"""LD9-V0 hard-budget calibration from a raw stress-scene summary and browser run."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats.plotting.density_render_budget import (  # noqa: E402
    BrowserMeshBudget,
    browser_usage_from_counts,
    evaluate_browser_mesh_budget,
)

SCHEMA = "mdstats.density-ld9-v0-calibration.v1"


def _markdown(result: dict[str, Any]) -> str:
    usage = result["budget_report"]["usage"]
    limits = result["budget_report"]["budget"]
    lines = [
        "# LD9-V0 rendering calibration",
        "",
        f"- Raw density faces: {usage['final_density_face_count']:,}",
        f"- Raw density vertices: {usage['final_density_vertex_count']:,}",
        f"- Complete Plotly traces: {usage['plotly_trace_count']:,}",
        f"- Self-contained HTML: {usage['final_html_bytes'] / 1024**2:.2f} MiB",
        f"- Hard face limit: {limits['max_final_density_faces']:,}",
        f"- Hard vertex limit: {limits['max_final_density_vertices']:,}",
        f"- Hard trace limit: {limits['max_plotly_traces']:,}",
        f"- Hard HTML limit: {limits['max_final_html_bytes'] / 1024**2:.2f} MiB",
        f"- Existing artifact passes browser budget: **{result['budget_report']['passed']}**",
        "",
        "## Required reduction",
        "",
        f"- Face reduction factor: {result['required_reduction']['faces']:.3f}x",
        f"- Vertex reduction factor: {result['required_reduction']['vertices']:.3f}x",
        f"- HTML reduction factor: {result['required_reduction']['html_bytes']:.3f}x",
        "",
        "## Browser evidence",
        "",
    ]
    browser = result.get("browser_validation")
    if browser:
        metrics = browser.get("metrics", {})
        lines.extend(
            [
                f"- Status: **{browser.get('status')}**",
                f"- First complete frame: {metrics.get('first_complete_frame_seconds')} s",
                f"- Camera orbit: {metrics.get('camera_orbit_fps')} frames/s",
                f"- Trace toggle: {metrics.get('trace_toggle_seconds')} s",
                f"- WebGL context loss: {metrics.get('webgl_context_lost')}",
            ]
        )
    else:
        lines.append("- Browser validation was not supplied.")
    lines.extend(("", "## Violations", ""))
    lines.extend(f"- `{value}`" for value in result["budget_report"]["violations"])
    return "\n".join(lines) + "\n"


def calibrate(
    summary: dict[str, Any],
    *,
    browser_validation: dict[str, Any] | None = None,
    budget: BrowserMeshBudget | None = None,
) -> dict[str, Any]:
    resolved = BrowserMeshBudget() if budget is None else budget
    browser_trace_count = None
    if browser_validation is not None:
        browser_trace_count = browser_validation.get("metrics", {}).get("trace_count")
    mesh_trace_count = int(summary["mesh_trace_count"])
    non_density = (
        max(0, int(browser_trace_count) - mesh_trace_count)
        if browser_trace_count is not None
        else int(summary.get("trajectory_atom_count", 0)) + 4
    )
    usage = browser_usage_from_counts(
        face_counts=(int(summary["mesh_face_count"]),),
        vertex_counts=(int(summary["mesh_vertex_count"]),),
        trace_keys=("raw-density-scene",),
        non_density_trace_count=non_density,
        final_html_bytes=int(summary["html_bytes"]),
        metadata={
            "source_mesh_trace_count": mesh_trace_count,
            "accounting": "aggregate_raw_density_scene",
        },
    )
    report = evaluate_browser_mesh_budget(usage, budget=resolved)
    return {
        "schema": SCHEMA,
        "package_version": summary.get("package_version"),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "source_summary": summary,
        "browser_validation": browser_validation,
        "budget_report": report.to_json_dict(),
        "required_reduction": {
            "faces": usage.final_density_face_count / resolved.max_final_density_faces,
            "vertices": usage.final_density_vertex_count
            / resolved.max_final_density_vertices,
            "html_bytes": int(summary["html_bytes"]) / resolved.max_final_html_bytes,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--browser-validation", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(__file__).with_name("density_ld9_v0_calibration.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(__file__).with_name("density_ld9_v0_calibration.md"),
    )
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text())
    browser = (
        None
        if args.browser_validation is None
        else json.loads(args.browser_validation.read_text())
    )
    result = calibrate(summary, browser_validation=browser)
    args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.markdown_output.write_text(_markdown(result))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
