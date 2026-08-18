"""LD6 evidence benchmark for optional multilevel density refinement."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from mdstats.plotting import (
    DensitySourceProvenance,
    MultilevelResearchOptions,
    PeriodicScalarField3D,
    PeriodicWeightedSamples3D,
    decide_multilevel_research,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_optimized,
    profile_multilevel_field,
)

SCHEMA = "mdstats.density-multilevel-research-benchmark.v1"


def lta_cell(scale: float = 1.0) -> np.ndarray:
    return scale * np.asarray(
        [
            [3.0, 0.0, 0.0],
            [1.5, 2.598076211353316, 0.0],
            [1.5, 0.8660254037844386, 2.449489742783178],
        ],
        dtype=np.float64,
    )


def weighted_samples(
    positions: np.ndarray,
    *,
    source_kind: str,
    total_measure: float = 1.0,
    measure_kind: str = "occupancy",
    measure_units: str = "count",
    weights: np.ndarray | None = None,
) -> PeriodicWeightedSamples3D:
    positions = np.mod(np.asarray(positions, dtype=np.float64), 1.0)
    if weights is None:
        weights = np.full(positions.shape[0], total_measure / positions.shape[0])
    else:
        weights = np.asarray(weights, dtype=np.float64)
        weights = weights * (total_measure / float(np.sum(weights, dtype=np.float64)))
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(source_kind=source_kind),
        total_measure=total_measure,
        measure_kind=measure_kind,
        measure_units=measure_units,
    )


def sparse_field(
    batch: PeriodicWeightedSamples3D,
    *,
    field_key: str,
    sigma: float,
    shape: tuple[int, int, int] = (48, 48, 48),
    cell: np.ndarray | None = None,
    physical_units: str = "angstrom^-3",
):
    if cell is None:
        cell = lta_cell(5.0)
    reference = prepare_sparse_canonical_density_optimized(
        batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key=field_key,
        label=field_key,
        physical_units=physical_units,
        broadening_metric="gaussian_sigma_v1",
        max_workspace_bytes=2_000_000_000,
        cache_stencil_supports=True,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=(16, 16, 16),
        selected_atom_indices=(0,),
        max_nonzero_nodes=8_000_000,
        max_stored_block_values=8_000_000,
        max_planning_bytes=2_000_000_000,
    )


def dense_from_batch(
    batch: PeriodicWeightedSamples3D,
    *,
    field_key: str,
    sigma: float,
    shape: tuple[int, int, int] = (48, 48, 48),
    cell: np.ndarray | None = None,
):
    if cell is None:
        cell = lta_cell(5.0)
    reference = prepare_sparse_canonical_density_optimized(
        batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key=field_key,
        label=field_key,
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        max_workspace_bytes=2_000_000_000,
        cache_stencil_supports=True,
    )
    values = reference.to_dense_values(max_nodes=int(np.prod(shape)))
    return PeriodicScalarField3D(
        field_key=field_key,
        label=field_key,
        values=values,
        display_cell=cell,
        total_measure=reference.total_measure,
        selected_atom_indices=(0,),
        gaussian_bandwidth=sigma,
        source_provenance=batch.source_provenance,
        metadata={
            "physical_units": "angstrom^-3",
            "smoothing_operator": "discrete_periodized_v1",
            "broadening_metric": "gaussian_sigma_v1",
        },
    )


def cloud_samples(
    rng: np.random.Generator,
    centers: np.ndarray,
    *,
    samples_per_center: int,
    spread: float,
) -> np.ndarray:
    return np.concatenate(
        [center + spread * rng.normal(size=(samples_per_center, 3)) for center in centers],
        axis=0,
    )


def line_samples(start: np.ndarray, stop: np.ndarray, count: int) -> np.ndarray:
    parameter = (np.arange(count, dtype=np.float64) + 0.5) / count
    return start[None, :] + parameter[:, None] * (stop - start)[None, :]


def build_fields(seed: int = 20260720) -> list[Any]:
    rng = np.random.default_rng(seed)
    fields: list[Any] = []

    centers = np.asarray(
        [[0.18, 0.22, 0.26], [0.68, 0.72, 0.76], [0.20, 0.73, 0.42]],
        dtype=np.float64,
    )
    fields.append(
        sparse_field(
            weighted_samples(
                cloud_samples(rng, centers[:1], samples_per_center=120, spread=0.008),
                source_kind="atomic_occupancy",
            ),
            field_key="atomic_localized",
            sigma=0.22,
        )
    )
    fields.append(
        sparse_field(
            weighted_samples(
                cloud_samples(rng, centers, samples_per_center=60, spread=0.006),
                source_kind="framework_vertex_occupancy",
            ),
            field_key="framework_vertices_separated",
            sigma=0.21,
        )
    )
    overlapping = np.asarray(
        [[0.47, 0.49, 0.51], [0.50, 0.50, 0.50], [0.53, 0.51, 0.49]],
        dtype=np.float64,
    )
    fields.append(
        sparse_field(
            weighted_samples(
                cloud_samples(rng, overlapping, samples_per_center=70, spread=0.012),
                source_kind="atomic_occupancy",
            ),
            field_key="oxygen_clouds_overlapping",
            sigma=0.28,
        )
    )
    hopping = np.asarray(
        [[0.08, 0.45, 0.52], [0.48, 0.48, 0.50], [0.92, 0.52, 0.48]],
        dtype=np.float64,
    )
    fields.append(
        sparse_field(
            weighted_samples(
                cloud_samples(rng, hopping, samples_per_center=90, spread=0.010),
                source_kind="atomic_occupancy",
            ),
            field_key="na_multimodal_hopping",
            sigma=0.24,
        )
    )

    projected = np.concatenate(
        [
            line_samples(np.asarray([0.05, 0.25, 0.25]), np.asarray([0.45, 0.25, 0.25]), 80),
            line_samples(np.asarray([0.55, 0.75, 0.75]), np.asarray([0.95, 0.75, 0.75]), 80),
            line_samples(np.asarray([0.48, 0.05, 0.48]), np.asarray([0.48, 0.95, 0.48]), 120),
        ],
        axis=0,
    )
    fields.append(
        sparse_field(
            weighted_samples(
                projected,
                source_kind="framework_edge_projected",
                total_measure=8.5,
                measure_kind="arc_length",
                measure_units="angstrom",
            ),
            field_key="framework_edges_projected",
            sigma=0.24,
            physical_units="angstrom^-2",
        )
    )

    path = np.concatenate(
        [
            line_samples(np.asarray([0.10, 0.10, 0.10]), np.asarray([0.50, 0.45, 0.40]), 100),
            line_samples(np.asarray([0.50, 0.45, 0.40]), np.asarray([0.90, 0.85, 0.80]), 100),
        ],
        axis=0,
    )
    fields.append(
        sparse_field(
            weighted_samples(
                path,
                source_kind="framework_edge_atomic_path",
                total_measure=6.2,
                measure_kind="arc_length",
                measure_units="angstrom",
            ),
            field_key="framework_paths_atomic",
            sigma=0.23,
            physical_units="angstrom^-2",
        )
    )

    grid = np.indices((48, 48, 48), dtype=np.float64)
    broad_values = (
        1.0
        + 0.08 * np.cos(2.0 * np.pi * grid[0] / 48.0)
        + 0.05 * np.cos(2.0 * np.pi * grid[1] / 48.0)
        + 0.03 * np.cos(2.0 * np.pi * grid[2] / 48.0)
    )
    broad_values /= float(np.sum(broad_values, dtype=np.float64)) / broad_values.size
    fields.append(
        PeriodicScalarField3D(
            field_key="mobile_ion_broad",
            label="mobile_ion_broad",
            values=broad_values,
            display_cell=lta_cell(5.0),
            total_measure=float(np.sum(broad_values, dtype=np.float64))
            * abs(float(np.linalg.det(lta_cell(5.0))))
            / broad_values.size,
            selected_atom_indices=(0,),
            gaussian_bandwidth=1.6,
            source_provenance=DensitySourceProvenance(
                source_kind="atomic_occupancy"
            ),
            metadata={
                "physical_units": "angstrom^-3",
                "smoothing_operator": "discrete_periodized_v1",
                "broadening_metric": "gaussian_sigma_v1",
                "benchmark_surrogate": "smooth_delocalized_mobile_ion",
            },
        )
    )
    return fields


def run_benchmark() -> dict[str, Any]:
    options = MultilevelResearchOptions()
    profiles = []
    profile_rows = []
    for field in build_fields():
        started = time.perf_counter()
        profile = profile_multilevel_field(field, options=options)
        elapsed = time.perf_counter() - started
        profiles.append(profile)
        best = profile.best_candidate
        profile_rows.append(
            {
                "field_key": profile.field_key,
                "storage_backend": profile.storage_backend,
                "support_regime": profile.support_regime,
                "logical_node_count": profile.logical_node_count,
                "nonzero_node_count": profile.nonzero_node_count,
                "active_fraction": profile.active_fraction,
                "current_stored_value_count": profile.current_stored_value_count,
                "stored_fraction": profile.stored_fraction,
                "best_single_level_value_count": profile.best_single_level_value_count,
                "single_level_sufficient": profile.single_level_sufficient,
                "candidate_count": len(profile.candidates),
                "best_candidate_factor": None if best is None else best.coarsening_factor,
                "best_candidate_fine_mass_fraction": None if best is None else best.fine_mass_fraction,
                "best_candidate_all_phases_pass": None if best is None else best.all_phases_pass,
                "best_candidate_worst_incremental_reduction": None
                if best is None
                else best.worst_incremental_reduction_vs_single_level,
                "best_candidate_worst_relative_l1": None
                if best is None
                else best.worst_relative_l1_error,
                "best_candidate_worst_relative_linf": None
                if best is None
                else best.worst_relative_linf_error,
                "profile_seconds": elapsed,
            }
        )
    decision = decide_multilevel_research(profiles, options=options)
    return {
        "schema_version": SCHEMA,
        "options": options.to_json_dict(),
        "profiles": profile_rows,
        "decision": decision.to_json_dict(),
        "notes": [
            "The coarse/fine candidate is an optimistic research surrogate, not a production field.",
            "Every dyadic coarse-grid phase is evaluated; all phases must pass scientific tolerances.",
            "Single-level alternatives include 4^3, 8^3, and 16^3 block shapes.",
        ],
    }


def write_markdown(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LD6 multilevel research benchmark",
        "",
        f"Decision: **{result['decision']['outcome']}**",
        "",
        "| Field | Backend | Regime | Active fraction | Stored fraction | Best single-level values | Best candidate | Worst incremental reduction | Worst L1 | Time (s) |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in result["profiles"]:
        candidate = "-"
        if row["best_candidate_factor"] is not None:
            candidate = f"{row['best_candidate_factor']}x / q={row['best_candidate_fine_mass_fraction']:.2f}"
        reduction = row["best_candidate_worst_incremental_reduction"]
        l1 = row["best_candidate_worst_relative_l1"]
        lines.append(
            "| {field_key} | {storage_backend} | {support_regime} | {active_fraction:.4f} | "
            "{stored_fraction:.4f} | {best_single_level_value_count} | {candidate} | {reduction} | "
            "{l1} | {profile_seconds:.3f} |".format(
                candidate=candidate,
                reduction="-" if reduction is None else f"{reduction:.3f}x",
                l1="-" if l1 is None else f"{l1:.3e}",
                **row,
            )
        )
    lines.extend(["", "## Decision rationale", ""])
    lines.extend(f"- {item}" for item in result["decision"]["rationale"])
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in result["notes"])
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark()
    args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_markdown(result, args.markdown)


if __name__ == "__main__":
    main()
