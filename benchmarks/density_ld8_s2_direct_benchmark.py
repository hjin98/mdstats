#!/usr/bin/env python3
"""Bounded LD8-S2 target-owned direct-realization benchmark.

This benchmark is intentionally smaller than the full production trajectory.
LD8-S2 is the canonical exact migration oracle; full-field production execution
remains LD7 until LD8-S3 introduces and validates the hybrid executor.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np

from mdstats.plotting.density_block_direct import (
    DensityDirectRealizationLimits,
    plan_target_owned_direct_realization,
    realize_density_target_owned_direct,
)
from mdstats.plotting.density_block_routing import build_periodic_kernel_block_routing
from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_kernel import build_periodic_gaussian_stencil_support
from mdstats.plotting.density_sparse_reference import (
    SparseCICNodeMasses3D,
    scatter_periodic_stencil_sparse,
)
from mdstats.plotting.density_support_atlas import (
    build_density_support_atlas,
    pack_periodic_cic_source,
)

SCHEMA = "mdstats.density-ld8-s2-direct-benchmark.v1"


def _timer() -> float:
    return time.perf_counter()


def _flat_packed(field) -> tuple[np.ndarray, np.ndarray]:
    parts = list(field.iter_stored_nodes())
    coordinates = np.concatenate([part[0] for part in parts])
    values = np.concatenate([part[1] for part in parts])
    flat = np.ravel_multi_index(
        (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]),
        field.logical_grid_shape,
        order="C",
    )
    order = np.argsort(flat)
    return flat[order], values[order]


def _case(source_nodes: int, *, seed: int) -> dict[str, Any]:
    shape = (96, 96, 96)
    cell = np.diag(np.asarray((17.0, 17.0, 17.0), dtype=np.float64))
    spacing = 17.0 / 96.0
    sigma = 2.0 * spacing
    rng = np.random.default_rng(seed)
    coordinates = np.unique(
        rng.integers(0, np.asarray(shape), size=(source_nodes, 3)), axis=0
    )
    while coordinates.shape[0] < source_nodes:
        extra = rng.integers(
            0,
            np.asarray(shape),
            size=(source_nodes - coordinates.shape[0], 3),
        )
        coordinates = np.unique(np.vstack((coordinates, extra)), axis=0)
    coordinates = coordinates[:source_nodes]
    flat = np.ravel_multi_index(coordinates.T, shape, order="C")
    flat.sort()
    masses = np.full(source_nodes, 1.0 / source_nodes, dtype=np.float64)
    cic = SparseCICNodeMasses3D(
        grid_shape=shape,
        flat_indices=flat,
        node_masses=masses,
        total_measure=1.0,
        source_provenance=DensitySourceProvenance(source_kind="ld8_s2_benchmark"),
        metadata={"seed": seed},
    )

    t0 = _timer()
    stencil = build_periodic_gaussian_stencil_support(
        shape,
        cell,
        sigma,
        kernel_tail_tolerance=1.0e-8,
    )
    stencil_seconds = _timer() - t0

    t0 = _timer()
    source = pack_periodic_cic_source(cic, storage_block_shape=(16, 16, 16))
    routing = build_periodic_kernel_block_routing(
        stencil, storage_block_shape=(16, 16, 16)
    )
    atlas = build_density_support_atlas(source, routing)
    support_seconds = _timer() - t0

    limits = DensityDirectRealizationLimits(
        max_candidate_pairs=100_000_000,
        max_exact_contributions=20_000_000,
        max_transient_bytes=1_000_000_000,
        max_retained_bytes=1_000_000_000,
    )
    t0 = _timer()
    plan = plan_target_owned_direct_realization(
        source, stencil, routing, atlas, limits=limits
    )
    planning_seconds = _timer() - t0

    t0 = _timer()
    field = realize_density_target_owned_direct(
        source,
        stencil,
        routing,
        atlas,
        field_key=f"sources_{source_nodes}",
        label=f"{source_nodes} source nodes",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        approved_plan=plan,
    )
    s2_seconds = _timer() - t0

    t0 = _timer()
    reference = scatter_periodic_stencil_sparse(
        cic,
        stencil,
        field_key=f"sources_{source_nodes}",
        label=f"{source_nodes} source nodes",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        max_kernel_pairs=20_000_000,
        max_workspace_bytes=2_000_000_000,
    )
    ld1_seconds = _timer() - t0

    flat_s2, values_s2 = _flat_packed(field)
    if not np.array_equal(flat_s2, reference.active_flat_indices):
        raise RuntimeError("S2 and LD1-A active-node identities differ.")
    relative_l1 = float(
        np.sum(np.abs(values_s2 - reference.active_values), dtype=np.float64)
        / np.sum(np.abs(reference.active_values), dtype=np.float64)
    )
    if relative_l1 > 5.0e-12:
        raise RuntimeError(f"S2 relative L1 error {relative_l1} exceeds tolerance.")

    ld1_retained_bytes = int(
        reference.active_flat_indices.nbytes + reference.active_values.nbytes
    )
    return {
        "source_node_count": source_nodes,
        "grid_shape": list(shape),
        "grid_spacing_angstrom": spacing,
        "gaussian_bandwidth_angstrom": sigma,
        "kernel_tail_tolerance": 1.0e-8,
        "stencil_offset_count": stencil.stencil_offset_count,
        "source_block_count": source.source_block_count,
        "target_block_count": atlas.target_block_count,
        "target_support_node_count": atlas.target_support_node_count,
        "source_target_edge_count": atlas.source_target_edge_count,
        "exact_contribution_count": plan.exact_contribution_count,
        "conservative_candidate_pair_count": plan.conservative_candidate_pair_count,
        "candidate_to_exact_ratio": (
            plan.conservative_candidate_pair_count / plan.exact_contribution_count
        ),
        "stencil_seconds": stencil_seconds,
        "support_seconds": support_seconds,
        "planning_seconds": planning_seconds,
        "s2_realization_seconds": s2_seconds,
        "ld1a_reference_seconds": ld1_seconds,
        "s2_to_ld1a_time_ratio": s2_seconds / ld1_seconds,
        "relative_l1_error": relative_l1,
        "s2_integral": field.integral,
        "s2_retained_bytes": field.retained_array_bytes,
        "ld1a_retained_bytes": ld1_retained_bytes,
        "ld1a_workspace_upper_bound_bytes": int(
            reference.metadata["workspace_upper_bound_bytes"]
        ),
        "s2_predicted_peak_bytes": plan.predicted_peak_bytes,
        "s2_observed_peak_pair_workspace_bytes": int(
            field.metadata["peak_pair_workspace_bytes"]
        ),
        "s2_peak_chunk_pair_count": int(field.metadata["peak_chunk_pair_count"]),
        "s2_vectorized_chunk_count": int(field.metadata["vectorized_chunk_count"]),
        "complete_fine_pair_array_allocated": bool(
            field.metadata["complete_fine_pair_array_allocated"]
        ),
        "global_target_coordinate_array_allocated": bool(
            field.metadata["global_target_coordinate_array_allocated"]
        ),
    }


def _write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LD8-S2 canonical direct-realization benchmark",
        "",
        "This bounded benchmark validates the S2 migration oracle. It is not a",
        "claim that S2 replaces the production LD7 executor before LD8-S3.",
        "",
        "| Source nodes | Stencil offsets | Exact pairs | Candidate pairs | Target nodes | S2 time | LD1-A time | S2/LD1-A | Relative L1 | Packed field |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in payload["cases"]:
        lines.append(
            "| {source_node_count:,} | {stencil_offset_count:,} | "
            "{exact_contribution_count:,} | {conservative_candidate_pair_count:,} | "
            "{target_support_node_count:,} | {s2_realization_seconds:.3f} s | "
            "{ld1a_reference_seconds:.3f} s | {s2_to_ld1a_time_ratio:.2f}x | "
            "{relative_l1_error:.3e} | {packed_mib:.2f} MiB |".format(
                packed_mib=item["s2_retained_bytes"] / 2**20,
                **item,
            )
        )
    lines.extend(
        [
            "",
            "S2 is exact and bounded, but the current NumPy target-owned oracle is",
            "slower than LD1-A on these small-to-medium cases. This is expected and",
            "supports retaining LD7 for production until the LD8-S3 hybrid executor",
            "passes its crossover and full-field performance gates.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(source_counts: list[int]) -> dict[str, Any]:
    started = _timer()
    cases = []
    for index, count in enumerate(source_counts):
        print(f"[LD8-S2] source nodes={count}", flush=True)
        cases.append(_case(count, seed=20260721 + index))
    return {
        "schema": SCHEMA,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "cases": cases,
        "total_seconds": _timer() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-counts",
        type=int,
        nargs="+",
        default=[64, 128, 512],
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=Path("benchmarks/density_ld8_s2_direct_benchmark.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("benchmarks/density_ld8_s2_direct_benchmark.md"),
    )
    args = parser.parse_args()
    payload = run(args.source_counts)
    args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_markdown(payload, args.markdown)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
