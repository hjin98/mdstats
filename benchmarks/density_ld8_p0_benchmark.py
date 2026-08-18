#!/usr/bin/env python3
"""LD8-P0 production-cutoff evidence and executor-spike benchmark.

The benchmark consumes a saved :class:`FrameworkDynamicsScene` so the costly
trajectory registration step is not repeated.  It reconstructs the all-frame atomic
samples, resolves the canonical effective CIC-plus-stencil broadening policy at the
retained ``1e-8`` tail cutoff, records source/block occupancy for 8^3, 16^3, and
32^3 storage blocks, and optionally executes the existing LD7 sparse path as the
production baseline.  A bounded dense-tile convolution spike compares direct and FFT
linear convolution without changing any public backend.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cloudpickle
import numpy as np
import psutil
from scipy.signal import convolve, fftconvolve

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats.plotting.atomic_density import (  # noqa: E402
    AtomicDensityOptions,
    resolve_density_numerics,
)
from mdstats.plotting.density_block_sparse import pack_sparse_reference_blocks  # noqa: E402
from mdstats.plotting.density_contracts import (  # noqa: E402
    DISCRETE_PERIODIZED_OPERATOR,
    EFFECTIVE_CIC_STENCIL_BROADENING,
    LOCAL_SPARSE_BACKEND,
    DensityKernelOptions,
    DensityOptimizationOptions,
    DensityResolutionOptions,
    DensitySourceProvenance,
    DensityStorageOptions,
    PeriodicWeightedSamples3D,
)
from mdstats.plotting.density_sparse_optimization import (  # noqa: E402
    aggregate_periodic_cic_sparse_optimized,
    clear_density_optimization_caches,
    get_periodic_gaussian_stencil_support,
    prepare_sparse_canonical_density_optimized,
)

SCHEMA = "mdstats.density-ld8-p0-benchmark.v1"
DEFAULT_BLOCK_SHAPES = (8, 16, 32)


@dataclass
class PeakRSSMonitor:
    interval_seconds: float = 0.02

    def __post_init__(self) -> None:
        self._process = psutil.Process()
        self._peak = self._process.memory_info().rss
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "PeakRSSMonitor":
        def sample() -> None:
            while not self._stop.wait(self.interval_seconds):
                self._peak = max(self._peak, self._process.memory_info().rss)

        self._thread = threading.Thread(target=sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # type: ignore[no-untyped-def]
        self._peak = max(self._peak, self._process.memory_info().rss)
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    @property
    def peak_bytes(self) -> int:
        return int(self._peak)


def _block_profile(
    flat_indices: np.ndarray,
    grid_shape: tuple[int, int, int],
    block_edge: int,
) -> dict[str, Any]:
    coordinates = np.column_stack(np.unravel_index(flat_indices, grid_shape, order="C"))
    block_shape = np.asarray((block_edge, block_edge, block_edge), dtype=np.int64)
    block_grid = tuple(
        (grid_shape[axis] + block_edge - 1) // block_edge for axis in range(3)
    )
    block_coordinates = coordinates // block_shape[None, :]
    block_flat = (
        (block_coordinates[:, 0] * block_grid[1] + block_coordinates[:, 1])
        * block_grid[2]
        + block_coordinates[:, 2]
    )
    unique, counts = np.unique(block_flat, return_counts=True)
    fixed_slots = int(unique.size * block_edge**3)
    bitset_bytes = int(unique.size * ((block_edge**3 + 7) // 8))
    packed_bytes = int(flat_indices.size * 8 + bitset_bytes + unique.size * 3 * 4)
    fixed_bytes = int(fixed_slots * 8 + unique.size * 3 * 8)
    return {
        "block_shape": [block_edge, block_edge, block_edge],
        "block_grid_shape": list(block_grid),
        "occupied_block_count": int(unique.size),
        "occupied_node_count": int(flat_indices.size),
        "mean_nodes_per_occupied_block": float(np.mean(counts)),
        "max_nodes_per_occupied_block": int(np.max(counts, initial=0)),
        "occupied_fraction_within_stored_blocks": (
            float(flat_indices.size / fixed_slots) if fixed_slots else 0.0
        ),
        "fixed_block_value_slots": fixed_slots,
        "estimated_fixed_block_bytes": fixed_bytes,
        "estimated_packed_positive_bytes": packed_bytes,
    }


def _connected_block_components(
    flat_indices: np.ndarray,
    grid_shape: tuple[int, int, int],
    block_edge: int,
) -> dict[str, Any]:
    coordinates = np.column_stack(np.unravel_index(flat_indices, grid_shape, order="C"))
    block_grid = tuple(
        (grid_shape[axis] + block_edge - 1) // block_edge for axis in range(3)
    )
    block_coordinates = np.unique(coordinates // block_edge, axis=0)
    blocks = {tuple(int(value) for value in row) for row in block_coordinates}
    sizes: list[int] = []
    while blocks:
        seed = blocks.pop()
        stack = [seed]
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for axis in range(3):
                for step in (-1, 1):
                    candidate = list(current)
                    candidate[axis] = (candidate[axis] + step) % block_grid[axis]
                    key = tuple(candidate)
                    if key in blocks:
                        blocks.remove(key)
                        stack.append(key)
        sizes.append(size)
    sizes.sort(reverse=True)
    return {
        "component_count": len(sizes),
        "largest_component_blocks": sizes[0] if sizes else 0,
        "component_block_sizes": sizes,
    }


def _scene_field_samples(scene: Any, field: Any, max_frames: int | None) -> tuple[np.ndarray, PeriodicWeightedSamples3D]:
    path_set = scene.trajectory_paths
    frame_count = path_set.n_frames if max_frames is None else min(path_set.n_frames, max_frames)
    frame_indices = np.arange(frame_count, dtype=np.int64)
    atom_lookup = {int(atom): index for index, atom in enumerate(path_set.atom_indices)}
    selected_atoms = tuple(int(atom) for atom in field.selected_atom_indices)
    path_indices = np.asarray([atom_lookup[atom] for atom in selected_atoms], dtype=np.int64)
    cartesian_by_atom = np.asarray(
        path_set.display_positions[path_indices, :frame_count], dtype=np.float64
    )
    fractional_by_frame = np.transpose(cartesian_by_atom, (1, 0, 2)) @ np.linalg.inv(
        scene.display_cell
    )
    fractional_by_frame -= np.floor(fractional_by_frame)
    frame_weights = np.full(frame_count, 1.0 / frame_count, dtype=np.float64)
    flat = fractional_by_frame.reshape((-1, 3))
    weights = np.repeat(frame_weights, len(selected_atoms))
    groups = np.tile(np.arange(len(selected_atoms), dtype=np.int64), frame_count)
    samples = PeriodicWeightedSamples3D(
        fractional_positions=flat,
        weights=weights,
        sample_group_ids=groups,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=selected_atoms
        ),
        total_measure=float(len(selected_atoms)),
        measure_kind="occupancy",
        measure_units="count",
        metadata={
            "frame_count": frame_count,
            "source": "saved_framework_dynamics_scene",
        },
    )
    return fractional_by_frame, samples


def _resolution_options(tolerance: float) -> AtomicDensityOptions:
    return AtomicDensityOptions(
        resolution_options=DensityResolutionOptions(
            grid_interval=0.20,
            gaussian_to_grid_ratio=2.0,
            adaptive_smearing=True,
            max_smearing_to_sample_sd_ratio=0.50,
            sample_sd_quantile=0.10,
            spread_sample_size=128,
            spread_sample_seed=0,
            spread_sampling_strategy="stratified_random",
            broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
        ),
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR,
            kernel_tail_tolerance=tolerance,
        ),
        storage_options=DensityStorageOptions(
            grid_backend=LOCAL_SPARSE_BACKEND,
            local_block_shape=(16, 16, 16),
        ),
        optimization_options=DensityOptimizationOptions(
            sparse_evaluation_mode="optimized",
            cache_stencil_supports=True,
            sparse_pair_chunk_size=262_144,
            sparse_group_batch_size=8,
        ),
    )


def _executor_spike(stencil: Any, *, tile_edge: int, fill_fraction: float, seed: int) -> dict[str, Any]:
    shape = np.asarray(stencil.grid_shape, dtype=np.int64)
    offsets = np.column_stack(
        np.unravel_index(stencil.active_flat_indices, stencil.grid_shape, order="C")
    ).astype(np.int64, copy=False)
    offsets = offsets.copy()
    for axis in range(3):
        wrapped = offsets[:, axis] > shape[axis] // 2
        offsets[wrapped, axis] -= shape[axis]
    weights = np.asarray(stencil.active_weights, dtype=np.float64)
    minimum = np.min(offsets, axis=0)
    maximum = np.max(offsets, axis=0)
    kernel_shape = tuple((maximum - minimum + 1).tolist())
    kernel = np.zeros(kernel_shape, dtype=np.float64)
    shifted = offsets - minimum[None, :]
    kernel[shifted[:, 0], shifted[:, 1], shifted[:, 2]] = weights
    rng = np.random.default_rng(seed)
    source = np.zeros((tile_edge, tile_edge, tile_edge), dtype=np.float64)
    occupied = max(1, int(round(source.size * fill_fraction)))
    chosen = rng.choice(source.size, size=occupied, replace=False)
    source.flat[chosen] = rng.random(occupied)

    started = time.perf_counter()
    direct = convolve(source, kernel, mode="full", method="direct")
    direct_seconds = time.perf_counter() - started
    started = time.perf_counter()
    fft = fftconvolve(source, kernel, mode="full")
    fft_seconds = time.perf_counter() - started
    absolute = float(np.max(np.abs(direct - fft), initial=0.0))
    relative_l1 = float(
        np.sum(np.abs(direct - fft), dtype=np.float64)
        / max(np.sum(np.abs(direct), dtype=np.float64), np.finfo(np.float64).tiny)
    )
    return {
        "tile_shape": [tile_edge, tile_edge, tile_edge],
        "source_fill_fraction": float(occupied / source.size),
        "occupied_source_nodes": occupied,
        "kernel_shape": list(kernel_shape),
        "kernel_nonzero_count": int(weights.size),
        "direct_seconds": direct_seconds,
        "fft_seconds": fft_seconds,
        "direct_to_fft_speed_ratio": direct_seconds / max(fft_seconds, 1.0e-12),
        "max_absolute_difference": absolute,
        "relative_l1_difference": relative_l1,
    }


def benchmark_field(
    scene: Any,
    field: Any,
    *,
    tolerance: float,
    max_frames: int | None,
    execute_ld7: bool,
    block_shapes: tuple[int, ...],
    spike_tile_edge: int,
) -> dict[str, Any]:
    fractional_by_frame, samples = _scene_field_samples(scene, field, max_frames)
    frame_count = fractional_by_frame.shape[0]
    frame_weights = np.full(frame_count, 1.0 / frame_count, dtype=np.float64)
    options = _resolution_options(tolerance)

    started = time.perf_counter()
    numerics = resolve_density_numerics(
        np.asarray(scene.display_cell, dtype=np.float64),
        options=options,
        fractional_by_frame=fractional_by_frame,
        frame_weights=frame_weights,
        pbc=np.ones(3, dtype=bool),
        max_voxels=int(np.iinfo(np.int64).max),
        field_label=field.label,
    )
    resolution_seconds = time.perf_counter() - started

    started = time.perf_counter()
    cic = aggregate_periodic_cic_sparse_optimized(
        samples,
        numerics.grid_shape,
        max_cic_contributions=100_000_000,
        max_workspace_bytes=8_000_000_000,
    )
    cic_seconds = time.perf_counter() - started

    started = time.perf_counter()
    stencil, cache_hit = get_periodic_gaussian_stencil_support(
        numerics.grid_shape,
        np.asarray(scene.display_cell, dtype=np.float64),
        numerics.gaussian_bandwidth,
        kernel_tail_tolerance=tolerance,
        max_candidate_contributions=2_000_000_000,
        max_workspace_bytes=8_000_000_000,
        use_cache=True,
    )
    stencil_seconds = time.perf_counter() - started

    block_profiles = {
        str(edge): _block_profile(cic.flat_indices, numerics.grid_shape, edge)
        for edge in block_shapes
    }
    fragmentation = _connected_block_components(cic.flat_indices, numerics.grid_shape, 16)
    spike = _executor_spike(
        stencil,
        tile_edge=spike_tile_edge,
        fill_fraction=min(0.25, max(0.02, cic.occupied_node_count / max(1, 16**3))),
        seed=0,
    )

    result: dict[str, Any] = {
        "label": field.label,
        "frame_count": frame_count,
        "selected_atom_count": len(field.selected_atom_indices),
        "sample_count": int(samples.fractional_positions.shape[0]),
        "grid_shape": list(numerics.grid_shape),
        "logical_node_count": int(np.prod(numerics.grid_shape, dtype=object)),
        "gaussian_bandwidth_angstrom": numerics.gaussian_bandwidth,
        "effective_rms_angstrom": (
            None
            if numerics.broadening_diagnostic is None
            else numerics.broadening_diagnostic.effective_rms
        ),
        "sample_sd_reference_angstrom": numerics.spread_diagnostics.reference_standard_deviation,
        "kernel_tail_tolerance": tolerance,
        "kernel_cutoff_radius_angstrom": stencil.cutoff_radius,
        "kernel_stencil_offset_count": stencil.stencil_offset_count,
        "occupied_cic_node_count": cic.occupied_node_count,
        "estimated_kernel_pair_count": int(
            cic.occupied_node_count * stencil.stencil_offset_count
        ),
        "resolution_seconds": resolution_seconds,
        "cic_seconds": cic_seconds,
        "stencil_seconds": stencil_seconds,
        "stencil_cache_hit": cache_hit,
        "source_block_profiles": block_profiles,
        "source_block_fragmentation_16": fragmentation,
        "executor_spike": spike,
    }

    if execute_ld7:
        clear_density_optimization_caches()
        monitor = PeakRSSMonitor()
        baseline_started = time.perf_counter()
        try:
            with monitor:
                started = time.perf_counter()
                reference = prepare_sparse_canonical_density_optimized(
                    samples,
                    grid_shape=numerics.grid_shape,
                    display_cell=np.asarray(scene.display_cell, dtype=np.float64),
                    gaussian_bandwidth=numerics.gaussian_bandwidth,
                    field_key=field.field_key,
                    label=field.label,
                    physical_units=field.physical_units,
                    broadening_metric=EFFECTIVE_CIC_STENCIL_BROADENING,
                    kernel_tail_tolerance=tolerance,
                    pair_chunk_size=262_144,
                    block_shape=(16, 16, 16),
                    group_batch_size=8,
                    cache_stencil_supports=True,
                    max_cic_contributions=100_000_000,
                    max_stencil_candidate_contributions=2_000_000_000,
                    max_kernel_pairs=20_000_000_000,
                    max_workspace_bytes=8_000_000_000,
                )
                ld7_seconds = time.perf_counter() - started
                started = time.perf_counter()
                packed = pack_sparse_reference_blocks(
                    reference,
                    block_shape=(16, 16, 16),
                    max_nonzero_nodes=100_000_000,
                    max_stored_block_values=100_000_000,
                    max_blocks=1_000_000,
                    max_planning_bytes=8_000_000_000,
                )
                packing_seconds = time.perf_counter() - started
                started = time.perf_counter()
                hdr = [
                    packed.hdr_details(fraction).to_json_dict()
                    for fraction in (0.5, 0.8, 0.95)
                ]
                hdr_seconds = time.perf_counter() - started
            result["ld7_baseline"] = {
                "status": "completed",
                "scientific_seconds": ld7_seconds,
                "packing_seconds": packing_seconds,
                "hdr_seconds": hdr_seconds,
                "process_peak_rss_bytes": monitor.peak_bytes,
                "integral": packed.integral,
                "storage_summary": packed.storage_summary().to_json_dict(),
                "metadata": reference.metadata.to_json_dict(),
                "hdr": hdr,
            }
        except Exception as error:  # preserve benchmark failure evidence
            result["ld7_baseline"] = {
                "status": "failed",
                "elapsed_seconds": time.perf_counter() - baseline_started,
                "process_peak_rss_bytes": monitor.peak_bytes,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            }
    return result


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# LD8-P0 production-cutoff benchmark",
        "",
        f"- Scene: `{result['scene_pickle']}`",
        f"- Tail tolerance: `{result['kernel_tail_tolerance']:.1e}`",
        f"- Existing LD7 execution enabled: **{result['execute_ld7']}**",
        f"- Total wall time: {result['total_seconds']:.3f} s",
        "",
        "| Field | Grid | CIC nodes | Stencil offsets | Estimated pairs | LD7 seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for field in result["fields"]:
        baseline = field.get("ld7_baseline", {})
        lines.append(
            "| {label} | {grid} | {nodes:,} | {offsets:,} | {pairs:,} | {seconds} |".format(
                label=field["label"],
                grid="x".join(str(value) for value in field["grid_shape"]),
                nodes=field["occupied_cic_node_count"],
                offsets=field["kernel_stencil_offset_count"],
                pairs=field["estimated_kernel_pair_count"],
                seconds=(
                    f"{baseline['scientific_seconds']:.3f}"
                    if baseline.get("status") == "completed"
                    else (
                        f"failed: {baseline.get('error_type', 'unknown')}"
                        if baseline
                        else "not executed"
                    )
                ),
            )
        )
    lines.extend(
        (
            "",
            "The direct/FFT spike is a bounded evidence kernel only. It does not change the production backend or public API.",
        )
    )
    return "\n".join(lines) + "\n"


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    with args.scene_pickle.open("rb") as handle:
        scene = cloudpickle.load(handle)
    fields = [
        field
        for field in scene.atomic_density_fields
        if not args.species
        or field.label.split()[0] in args.species
    ]
    clear_density_optimization_caches()
    results = []
    for field in fields:
        print(f"[LD8-P0] starting {field.label}", flush=True)
        field_result = benchmark_field(
            scene,
            field,
            tolerance=args.kernel_tail_tolerance,
            max_frames=args.max_frames,
            execute_ld7=args.execute_ld7,
            block_shapes=tuple(args.block_shapes),
            spike_tile_edge=args.spike_tile_edge,
        )
        results.append(field_result)
        baseline = field_result.get("ld7_baseline")
        if baseline is None:
            print(
                f"[LD8-P0] planned {field.label}: "
                f"{field_result['estimated_kernel_pair_count']:,} pairs",
                flush=True,
            )
        elif baseline.get("status") == "completed":
            print(
                f"[LD8-P0] completed {field.label}: "
                f"{baseline['scientific_seconds']:.3f} s",
                flush=True,
            )
        else:
            print(
                f"[LD8-P0] failed {field.label}: "
                f"{baseline.get('error_type', 'unknown')}: "
                f"{baseline.get('error', '')}",
                flush=True,
            )
    return {
        "schema": SCHEMA,
        "scene_pickle": str(args.scene_pickle.resolve()),
        "kernel_tail_tolerance": args.kernel_tail_tolerance,
        "max_frames": args.max_frames,
        "execute_ld7": args.execute_ld7,
        "block_shapes": args.block_shapes,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "cpu_count": psutil.cpu_count(logical=True),
            "total_memory_bytes": psutil.virtual_memory().total,
        },
        "fields": results,
        "total_seconds": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_pickle", type=Path)
    parser.add_argument("--species", nargs="*", default=[])
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--kernel-tail-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--block-shapes", nargs="*", type=int, default=list(DEFAULT_BLOCK_SHAPES))
    parser.add_argument("--spike-tile-edge", type=int, default=8)
    parser.add_argument("--execute-ld7", action="store_true")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(__file__).with_name("density_ld8_p0_benchmark.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(__file__).with_name("density_ld8_p0_benchmark.md"),
    )
    args = parser.parse_args()
    result = run_benchmark(args)
    args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.markdown_output.write_text(_markdown(result))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
