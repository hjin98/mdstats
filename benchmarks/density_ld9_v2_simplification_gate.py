#!/usr/bin/env python3
"""LD9-V2 full-resolution 50% HDR simplification evidence.

This benchmark intentionally reuses the saved LD7 scientific fields from the
original 1,500-frame stress scene.  It exercises V1 tiled extraction followed
by V2 local and global simplification.  It is not the final 12-shell browser
budget gate; scene-wide allocation belongs to LD9-V3.
"""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from typing import Any

import cloudpickle

from mdstats import MeshExtractionOptions, MeshSimplificationOptions, prepare_sparse_density_mesh

TARGETS = {
    "Na": {"target_faces": 40_000, "max_faces": 40_000, "hard_target": True},
    "Si": {"target_faces": 35_000, "max_faces": 40_000, "hard_target": False},
    "Al": {"target_faces": 38_000, "max_faces": 43_000, "hard_target": False},
    "O": {"target_faces": 110_000, "max_faces": 122_000, "hard_target": False},
}


def _plain_json(value: Any) -> Any:
    if hasattr(value, "to_json_dict"):
        return _plain_json(value.to_json_dict())
    if isinstance(value, dict) or hasattr(value, "items"):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain_json(item) for item in value]
    return value


def _rss_bytes() -> int:
    # Linux reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene_pickle", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--species", choices=("all", "Na", "Si", "Al", "O"), default="all")
    args = parser.parse_args()

    with args.scene_pickle.open("rb") as handle:
        scene = cloudpickle.load(handle)

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for field in scene.atomic_density_fields:
        species = str(field.label).split()[0]
        if args.species != "all" and species != args.species:
            continue
        policy = TARGETS[species]
        before_rss = _rss_bytes()
        t0 = time.perf_counter()
        prepared = prepare_sparse_density_mesh(
            field,
            0.50,
            max_faces=int(policy["max_faces"]),
            max_raw_faces=2_000_000,
            max_raw_vertices=4_000_000,
            max_workspace_bytes=4 * 1024**3,
            extraction_options=MeshExtractionOptions(
                render_tile_shape=(32, 32, 32),
                max_transient_mesh_bytes=768 * 1024**2,
            ),
            simplification_options=MeshSimplificationOptions(
                target_faces=int(policy["target_faces"]),
                hard_target=bool(policy["hard_target"]),
                local_presimplification=True,
                local_target_fraction=0.70,
                min_component_faces=16,
                max_samples=30_000,
                max_surface_error_p99=0.02,
                max_surface_error_max=0.08,
                max_implicit_displacement_p99=0.01,
                max_normal_degradation_degrees=8.0,
                max_relative_scalar_residual_p99=0.08,
            ),
        )
        elapsed = time.perf_counter() - t0
        mesh = prepared.mesh
        if mesh is None:
            raise RuntimeError(f"{species}: no mesh returned")
        simplification = mesh.metadata["mesh_simplification"]
        tiled = mesh.metadata["tiled_extraction"]
        fidelity = simplification["fidelity"]
        local_reports = tiled["tile_reports"]
        rows.append(
            {
                "species": species,
                "grid_shape": list(field.grid_shape),
                "hdr_fraction": 0.50,
                "scientific_level": float(mesh.scientific_hdr_threshold),
                "render_level": float(mesh.render_level),
                "elapsed_seconds": elapsed,
                "peak_rss_bytes": max(before_rss, _rss_bytes()),
                "raw_tiled_faces": int(tiled["raw_face_count"]),
                "pre_global_faces": int(simplification["input_faces"]),
                "protected_faces": int(simplification["protected_faces"]),
                "target_faces": int(simplification["target_faces"]),
                "final_faces": int(mesh.faces.shape[0]),
                "final_vertices": int(mesh.vertices_cartesian.shape[0]),
                "face_reduction_ratio": float(tiled["raw_face_count"]) / float(mesh.faces.shape[0]),
                "hard_target": bool(policy["hard_target"]),
                "local_attempted_components": sum(int(r["local_presimplification_attempted_components"]) for r in local_reports),
                "local_accepted_components": sum(int(r["local_presimplification_accepted_components"]) for r in local_reports),
                "fidelity_passed": bool(fidelity["passed"]),
                "excess_surface_distance_p99_angstrom": float(fidelity["excess_surface_distance_p99"]),
                "implicit_displacement_p99_angstrom": float(fidelity["implicit_displacement_p99"]),
                "implicit_displacement_max_angstrom": float(fidelity["implicit_displacement_max"]),
                "normal_degradation_degrees": float(fidelity["normal_degradation_degrees"]),
                "relative_scalar_residual_p99": float(fidelity["relative_scalar_residual_p99"]),
                "seam_vertex_count_reference": int(fidelity["seam_vertex_count_reference"]),
                "seam_vertex_count_candidate": int(fidelity["seam_vertex_count_candidate"]),
                "reference_topology": _plain_json(fidelity["reference_topology"]),
                "candidate_topology": _plain_json(fidelity["candidate_topology"]),
            }
        )
        print(f"{species}: {mesh.faces.shape[0]} faces in {elapsed:.3f} s", flush=True)

    evidence = {
        "schema_version": "mdstats.ld9-v2-simplification-gate.v1",
        "package_version": "0.19.60a0",
        "scene": "TRAJECTORY(4), 1,500 frames, saved full-resolution scientific fields",
        "scope": (
            "four 50% HDR shells; not the final 12-shell browser gate"
            if args.species == "all"
            else f"{args.species} 50% HDR shell; subprocess evidence row"
        ),
        "total_elapsed_seconds": time.perf_counter() - started,
        "total_raw_tiled_faces": sum(row["raw_tiled_faces"] for row in rows),
        "total_final_faces": sum(row["final_faces"] for row in rows),
        "total_final_vertices": sum(row["final_vertices"] for row in rows),
        "all_fidelity_passed": all(row["fidelity_passed"] for row in rows),
        "rows": rows,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")

    lines = [
        "# LD9-V2 full-resolution simplification gate",
        "",
        "This evidence covers the four 50% HDR shells from the saved 1,500-frame stress scene. It does not replace the LD9-V3 scene-wide 12-shell browser-budget gate.",
        "",
        "| Species | Raw faces | Final faces | Reduction | Time (s) | Fidelity |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['species']} | {row['raw_tiled_faces']:,} | {row['final_faces']:,} | {row['face_reduction_ratio']:.2f}× | {row['elapsed_seconds']:.3f} | {'pass' if row['fidelity_passed'] else 'fail'} |"
        )
    lines += [
        "",
        f"Total raw faces: **{evidence['total_raw_tiled_faces']:,}**",
        f"Total final faces: **{evidence['total_final_faces']:,}**",
        f"Aggregate reduction: **{evidence['total_raw_tiled_faces'] / evidence['total_final_faces']:.2f}×**",
        f"Total elapsed time: **{evidence['total_elapsed_seconds']:.3f} s**",
        f"All fidelity gates passed: **{evidence['all_fidelity_passed']}**",
        "",
        "The next stage must allocate and enforce one hard budget over all 12 shells after display replication.",
    ]
    args.markdown.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
