#!/usr/bin/env python3
"""Reproduce the PAR-DENS6 Na-LTA end-to-end qualification.

This release tool intentionally fixes the scientific density operator while
varying only execution scale/worker policy.  It is not imported by mdstats.
"""
from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import os
import pickle
import platform
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from mdstats import (
    AtomicDensityOptions,
    AtomicDensitySelection,
    DensityKernelOptions,
    DensityStorageOptions,
    DISCRETE_PERIODIZED_OPERATOR,
    DistanceConnectivity,
    FrameworkAtomRole,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    build_framework_topology,
    compute_atomic_connectivity,
    prepare_framework_dynamics_scene,
    read_lammps_frames,
)
from mdstats.plotting.atomic_density import (
    _aggregate_sparse_cic_for_options,
    _stencil_support_for_options,
    prepare_atomic_density_fields,
)
from mdstats.plotting.density_autotune import (
    DensityAutoTunePolicy,
    density_autotune_scope,
    resolve_density_autotune_profile,
)
from mdstats.plotting.density_execution_journal import (
    density_execution_journal_scope,
    density_execution_report,
)
from mdstats.plotting.density_gpu import discover_density_gpu
from mdstats.plotting.density_scheduler import (
    DensityScheduledTask,
    DensitySceneScheduler,
    DensitySchedulerPolicy,
    DensityTaskResources,
)
from mdstats.plotting.density_sparse_mesh import prepare_sparse_density_mesh
from mdstats.plotting.density_support_atlas import (
    build_density_support_atlas,
    pack_periodic_cic_source,
)
from mdstats.plotting.density_block_routing import get_periodic_kernel_block_routing
from mdstats.plotting.density_tiled_fft import (
    DensityHybridExecutorOptions,
    DensityHybridRealizationPlan,
    plan_hybrid_tiled_realization,
)
from mdstats.plotting.density_contracts import (
    DensitySourceProvenance,
    PeriodicWeightedSamples3D,
)
from mdstats.plotting.density_sparse_optimization import estimate_periodic_cic_sparse_optimized_workspace_bytes
from mdstats.plotting.runtime_resources import (
    density_resource_budget_scope,
    probe_runtime_resources,
    resolve_runtime_resource_budget,
)

TYPE_MAP = {1: "Si", 2: "Al", 3: "O", 4: "Na"}
SPECIES = ("Na", "Si", "O")
GRID = (64, 64, 64)
SIGMA = 0.5
BLOCK = (8, 8, 8)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _release_process_memory() -> None:
    """Best-effort qualification-only reclamation between independent scenes."""

    gc.collect()
    try:
        libc = ctypes.CDLL(None)
        trim = getattr(libc, "malloc_trim", None)
        if trim is not None:
            trim(0)
    except Exception:
        pass


def _progress(message: str) -> None:
    print(f"[PAR-DENS6 qualify] {message}", flush=True)


def _current_rss_bytes() -> int:
    try:
        fields = Path("/proc/self/statm").read_text().split()
        return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))
    except Exception:
        return 0


@dataclass
class _RSSSampler:
    baseline: int = 0
    peak: int = 0
    _stop: threading.Event | None = None
    _thread: threading.Thread | None = None

    def __enter__(self):
        self.baseline = _current_rss_bytes()
        self.peak = self.baseline
        self._stop = threading.Event()

        def sample() -> None:
            assert self._stop is not None
            while not self._stop.wait(0.01):
                self.peak = max(self.peak, _current_rss_bytes())

        self._thread = threading.Thread(target=sample, name="par-dens6-rss", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        assert self._stop is not None and self._thread is not None
        self._stop.set()
        self._thread.join()
        self.peak = max(self.peak, _current_rss_bytes())


def _payload(field) -> np.ndarray:
    for name in ("packed_values", "block_values", "values"):
        if hasattr(field, name):
            return np.array(getattr(field, name), dtype=np.float64, copy=True)
    raise TypeError(type(field))


def _field_snapshot(field) -> dict:
    return {
        "content_identity": str(field.content_identity),
        "integral": float(field.integral),
        "hdr": [float(field.threshold_for_mass_fraction(x)) for x in (0.5, 0.8, 0.95)],
        "payload": _payload(field),
    }


def _preplan_atomic_hybrid_execution(
    traj,
    *,
    idx: np.ndarray,
    weights: np.ndarray,
    display: np.ndarray,
    options: AtomicDensityOptions,
    planning_budget,
) -> dict[str, DensityHybridRealizationPlan]:
    """Freeze one scene-level direct/FFT tile partition per atomic field.

    PAR-DENS6 worker-count invariance requires executor selection to be made
    before the cooperative field leases are admitted.  The returned plans are
    execution-only: they do not enter scalar-field scientific identities.
    """

    plans: dict[str, DensityHybridRealizationPlan] = {}
    for i, species in enumerate(SPECIES):
        selection = AtomicDensitySelection(species=(species,), label=species)
        atoms = selection.resolve(traj)
        fractional = np.asarray(
            traj.fractional_positions[np.ix_(idx, atoms)], dtype=np.float64
        )
        flat = (fractional - np.floor(fractional)).reshape((-1, 3))
        sample_weights = np.repeat(weights, len(atoms))
        samples = PeriodicWeightedSamples3D(
            fractional_positions=flat,
            weights=sample_weights,
            sample_group_ids=np.tile(np.arange(len(atoms), dtype=np.int64), len(idx)),
            source_provenance=DensitySourceProvenance(
                source_kind="atomic_occupancy", atom_indices=atoms
            ),
            total_measure=float(len(atoms)),
            measure_kind="occupancy",
            measure_units="count",
        )
        cic = _aggregate_sparse_cic_for_options(
            samples,
            GRID,
            options=options,
            max_cic_contributions=200_000_000,
            max_workspace_bytes=planning_budget.max_memory_bytes,
        )
        stencil, _ = _stencil_support_for_options(
            GRID,
            display,
            SIGMA,
            options=options,
            max_candidate_contributions=1_000_000_000,
            max_workspace_bytes=planning_budget.max_memory_bytes,
        )
        source = pack_periodic_cic_source(
            cic, storage_block_shape=options.storage_options.local_block_shape
        )
        routing, _ = get_periodic_kernel_block_routing(
            stencil,
            storage_block_shape=options.storage_options.local_block_shape,
            use_cache=options.optimization_options.cache_stencil_supports,
        )
        atlas = build_density_support_atlas(
            source, routing, fft_workers=options.optimization_options.hybrid_fft_workers
        )
        hybrid_options = DensityHybridExecutorOptions(
            executor_mode="auto",
            compute_tile_shape=options.optimization_options.hybrid_compute_tile_shape,
            pair_chunk_size=options.optimization_options.sparse_pair_chunk_size,
            min_fft_source_nodes=options.optimization_options.hybrid_min_fft_source_nodes,
            fft_workers=options.optimization_options.hybrid_fft_workers,
            cache_kernel_spectra=options.optimization_options.cache_stencil_supports,
            metadata={
                "dispatch_stage": "par_dens6_scene_preplanning",
                "fft_worker_source": "runtime_thread_budget",
            },
        )
        plans[f"atomic-density-{i}"] = plan_hybrid_tiled_realization(
            source, stencil, routing, atlas, options=hybrid_options
        )
    return plans


def _run_atomic_scale(
    traj,
    *,
    nframes: int,
    budget,
    mode: str,
    planning_budget=None,
) -> tuple[dict, list[dict]]:
    idx = np.unique(np.linspace(0, traj.n_frames - 1, nframes).round().astype(int))
    weights = np.full(idx.size, 1.0 / idx.size, dtype=np.float64)
    display = np.asarray(traj.cells[int(idx[0])], dtype=np.float64)
    drift = np.zeros((idx.size, 3), dtype=np.float64)
    planning_budget = budget if planning_budget is None else planning_budget
    options = AtomicDensityOptions(
        grid_shape=GRID,
        gaussian_bandwidth=SIGMA,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(smoothing_operator=DISCRETE_PERIODIZED_OPERATOR),
        storage_options=DensityStorageOptions(grid_backend="local_sparse", local_block_shape=BLOCK),
    )
    options = replace(
        options,
        optimization_options=options.optimization_options.resolve(
            max_memory_bytes=planning_budget.max_memory_bytes
        ),
    )
    selections = tuple(AtomicDensitySelection(species=(sp,), label=sp) for sp in SPECIES)
    profile = resolve_density_autotune_profile(budget, policy=DensityAutoTunePolicy(mode=mode))
    scheduler = DensitySceneScheduler(
        budget, policy=DensitySchedulerPolicy(max_parallel_tasks=profile.max_parallel_tasks)
    )
    planning_started = time.perf_counter()
    planning_cpu_started = time.process_time()
    with (
        _RSSSampler() as planning_rss,
        density_resource_budget_scope(planning_budget),
        density_autotune_scope(resolve_density_autotune_profile(
            planning_budget, policy=DensityAutoTunePolicy(mode="auto")
        )),
        threadpool_limits(limits=planning_budget.max_threads),
    ):
        approved_hybrid_plans = _preplan_atomic_hybrid_execution(
            traj,
            idx=idx,
            weights=weights,
            display=display,
            options=options,
            planning_budget=planning_budget,
        )
    scene_preplanning_seconds = time.perf_counter() - planning_started
    planning_cpu_seconds = time.process_time() - planning_cpu_started
    tasks = []
    for i, selection in enumerate(selections):
        # Execution-faithful PAR-DENS6 declaration: the atomic field rebuilds
        # deterministic sparse CIC deposition inside realization, so its CIC
        # workspace must be visible to the global scheduler.  Species counts
        # are exact for this fixed qualification selection and the estimator is
        # the same helper used by the production Phase-B contract.
        atomic_number = {"Na": 11, "Si": 14, "O": 8}[SPECIES[i]]
        selected_atom_count = int(np.count_nonzero(traj.atomic_numbers == atomic_number))
        sample_count = int(idx.size) * selected_atom_count
        cic_workspace = estimate_periodic_cic_sparse_optimized_workspace_bytes(sample_count)
        resources = DensityTaskResources(
            task_id=f"atomic-density-{i}",
            retained_bytes=16 * 1024**2,
            transient_bytes=cic_workspace,
            minimum_workers=1,
            preferred_workers=budget.max_threads,
            construction_order=i,
            backend="local_sparse",
        )

        def prepare(_lease, *, i=i, selection=selection):
            return prepare_atomic_density_fields(
                traj,
                frame_indices=idx,
                frame_weights=weights,
                display_cell=display,
                registration_mode="material",
                framework_drift=drift,
                selections=(selection,),
                options=options,
                max_fields=1,
                max_total_voxels=2_000_000,
                max_samples=20_000_000,
                approved_hybrid_plans_by_field=approved_hybrid_plans,
                max_nonzero_nodes=2_000_000,
                max_stored_block_values=4_000_000,
                max_blocks=100_000,
                max_kernel_pairs=1_000_000_000,
                max_planning_bytes=budget.max_memory_bytes,
                max_workspace_bytes=budget.max_memory_bytes,
                max_cic_contributions=200_000_000,
                field_index_offset=i,
            )[0]

        tasks.append(DensityScheduledTask(resources, prepare))

    os.environ.setdefault("MDSTATS_DENSITY_GPU", "auto")
    started = planning_started
    cpu_started = time.process_time()
    with _RSSSampler() as rss, density_resource_budget_scope(budget), density_autotune_scope(profile), threadpool_limits(limits=budget.max_threads), density_execution_journal_scope() as journal:
        fields = scheduler.run(tuple(tasks))
    preparation = time.perf_counter() - started
    execution_cpu_seconds = time.process_time() - cpu_started
    cpu_seconds = planning_cpu_seconds + execution_cpu_seconds
    mesh_seconds = 0.0
    mesh_counts = []
    for field in fields:
        t0 = time.perf_counter()
        surface = prepare_sparse_density_mesh(
            field,
            0.80,
            max_faces=200_000,
            max_candidate_cells=200_000,
            max_raw_faces=500_000,
            max_raw_vertices=1_500_000,
            max_workspace_bytes=min(512_000_000, budget.max_memory_bytes),
            max_dense_fallback_nodes=1_000_000,
            allow_cloud_fallback=False,
        )
        mesh_seconds += time.perf_counter() - t0
        mesh_counts.append(None if surface.mesh is None else [int(surface.mesh.vertices_fractional.shape[0]), int(surface.mesh.faces.shape[0])])
    total = time.perf_counter() - started
    snapshots = [_field_snapshot(field) for field in fields]
    report = {
        "selected_frames": int(idx.size),
        "mode": mode,
        "scene_preplanning_wall_seconds": scene_preplanning_seconds,
        "preparation_wall_seconds": preparation,
        "contouring_wall_seconds": mesh_seconds,
        "total_wall_seconds": total,
        "cold_total_wall_seconds_including_calibration": total + float(profile.calibration_wall_seconds),
        "cpu_seconds": cpu_seconds,
        "normalized_cpu_utilization": cpu_seconds / max(preparation * budget.max_threads, 1.0e-30),
        "rss_baseline_bytes": min(planning_rss.baseline, rss.baseline),
        "rss_peak_bytes": max(planning_rss.peak, rss.peak),
        "rss_peak_delta_bytes": max(
            0,
            planning_rss.peak - planning_rss.baseline,
            rss.peak - rss.baseline,
        ),
        "planning_rss_peak_delta_bytes": max(0, planning_rss.peak - planning_rss.baseline),
        "realization_rss_peak_delta_bytes": max(0, rss.peak - rss.baseline),
        "autotune_profile": profile.to_json_dict(),
        "scheduler": scheduler.last_report.to_json_dict(),
        "memory_contract": "shared_sparse_cic_workspace_estimator_v1",
        "hybrid_execution_plan_authority": "scene_preplanned_before_worker_admission_v1",
        "hybrid_execution_plans": {
            sp: {
                "content_identity": approved_hybrid_plans[f"atomic-density-{i}"].content_identity,
                "direct_tile_count": approved_hybrid_plans[f"atomic-density-{i}"].direct_tile_count,
                "fft_tile_count": approved_hybrid_plans[f"atomic-density-{i}"].fft_tile_count,
                "direct_pair_count": approved_hybrid_plans[f"atomic-density-{i}"].direct_pair_count,
            }
            for i, sp in enumerate(SPECIES)
        },
        "execution_journal": density_execution_report(journal),
        "fields": {
            sp: {"content_identity": snap["content_identity"], "integral": snap["integral"], "hdr": snap["hdr"], "mesh_counts": mesh_counts[i]}
            for i, (sp, snap) in enumerate(zip(SPECIES, snapshots, strict=True))
        },
    }
    return report, snapshots


def _framework_audit(traj, *, frame_count: int, budget) -> dict:
    definition = DistanceConnectivity(cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 2.2, ("Al", "O"): 2.2}))
    state = compute_atomic_connectivity(traj, definition, frame_indices=[0]).states[0]
    mapping = FrameworkMapping.from_symbol_roles(
        {"Si": FrameworkAtomRole.VERTEX, "Al": FrameworkAtomRole.VERTEX, "O": FrameworkAtomRole.LINKER, "Na": FrameworkAtomRole.SPECTATOR},
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),),
    )
    topology = build_framework_topology(state, mapping)
    indices = np.unique(np.linspace(0, traj.n_frames - 1, frame_count).round().astype(int)).tolist()
    selections = tuple(AtomicDensitySelection(species=(sp,), label=sp) for sp in SPECIES)
    options = AtomicDensityOptions(
        grid_shape=GRID, gaussian_bandwidth=SIGMA, adaptive_smearing=False,
        kernel_options=DensityKernelOptions(smoothing_operator=DISCRETE_PERIODIZED_OPERATOR),
        storage_options=DensityStorageOptions(grid_backend="local_sparse", local_block_shape=BLOCK),
    )
    resources = FrameworkDynamicsResources(
        max_threads=budget.max_threads,
        max_memory_bytes=budget.max_memory_bytes,
        max_density_voxels=2_000_000,
    )
    scene = prepare_framework_dynamics_scene(
        traj,
        topology,
        frame_indices=indices,
        atomic_density_selections=selections,
        atomic_density_options=options,
        options=FrameworkDynamicsOptions(registration_mode=SpatialRegistrationMode.MATERIAL, display_cell="reference"),
        resources=resources,
    )
    realization = {
        item["field_key"]: item
        for item in scene.metadata["density_execution_summary"]["timings"]
        if item["stage"] == "realization"
    }
    comparison = {}
    for key, item in realization.items():
        predicted = float(item["metadata"].get("hybrid_estimated_wall_seconds", 0.0))
        observed = float(item["wall_seconds"])
        comparison[key] = {
            "predicted_wall_seconds": predicted,
            "observed_realization_wall_seconds": observed,
            "observed_over_predicted": None if predicted <= 0.0 else observed / predicted,
            "direct_tile_count": int(item["metadata"].get("hybrid_direct_tile_count", 0)),
            "fft_tile_count": int(item["metadata"].get("hybrid_fft_tile_count", 0)),
            "direct_pair_count": int(item["metadata"].get("direct_pair_count", 0)),
            "fft_padded_node_count": int(item["metadata"].get("fft_padded_node_count", 0)),
        }
    return {
        "selected_frames": len(indices),
        "topology_digest": topology.digest,
        "planning_approval_id": None if scene.planning_record is None else scene.planning_record.approval_id,
        "predicted_scene_peak_bytes": None if scene.planning_record is None else int(scene.planning_record.estimated_peak_bytes),
        "scheduler": scene.metadata["density_scheduler_summary"],
        "stage_wall_seconds": {
            "preprocessing": scene.metadata.get("trajectory_preprocessing_wall_seconds"),
            "planning": scene.metadata.get("density_planning_wall_seconds"),
            "realization": scene.metadata.get("density_realization_wall_seconds"),
            "total_preparation": scene.metadata.get("preparation_wall_seconds"),
        },
        "predicted_vs_observed": comparison,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scales", default="101,1001,10001")
    parser.add_argument(
        "--long-repeats",
        type=int,
        default=2,
        help="Independent long-scale repeats used for median speedup and timing-noise classification.",
    )
    parser.add_argument(
        "--parsed-cache",
        type=Path,
        default=None,
        help="Optional trusted local pickle cache of this exact trajectory; the original dump is still SHA-authenticated.",
    )
    args = parser.parse_args()
    scales = tuple(int(x) for x in args.scales.split(","))
    trajectory_sha = sha256(args.trajectory)
    if args.parsed_cache is not None:
        _progress(f"loading parsed trajectory cache {args.parsed_cache}")
        with args.parsed_cache.open("rb") as handle:
            traj = pickle.load(handle)
    else:
        _progress(f"reading trajectory {args.trajectory}")
        traj = read_lammps_frames(
            args.trajectory,
            units="metal",
            timestep=0.001,
            type_map=TYPE_MAP,
            reconstruct_velocities=False,
            frame_semantics="ensemble",
        )
    if traj.n_frames != 10001 or traj.n_atoms != 168:
        raise RuntimeError(
            f"Qualification trajectory shape mismatch: {traj.n_frames} frames x {traj.n_atoms} atoms."
        )
    _release_process_memory()
    snapshot = probe_runtime_resources()
    auto_budget = resolve_runtime_resource_budget(snapshot=snapshot)
    serial_budget = resolve_runtime_resource_budget(
        max_memory_bytes=auto_budget.max_memory_bytes,
        max_threads=1,
        snapshot=snapshot,
    )
    _progress(f"resolved production budget: threads={auto_budget.max_threads}, memory={auto_budget.max_memory_bytes} bytes")
    scale_reports = []
    long_auto_snapshots = None
    for scale in scales:
        _progress(f"auto benchmark: {scale} frames")
        report, snaps = _run_atomic_scale(traj, nframes=scale, budget=auto_budget, mode="auto")
        scale_reports.append(report)
        if scale == max(scales):
            long_auto_snapshots = snaps
        else:
            del snaps
        _release_process_memory()
    assert long_auto_snapshots is not None
    long_repeat_count = max(1, int(args.long_repeats))
    long_auto_reports = [scale_reports[-1]]
    for repeat_index in range(1, long_repeat_count):
        _progress(f"auto long repeat {repeat_index + 1}/{long_repeat_count}: {max(scales)} frames")
        repeat_long_report, repeat_long_snapshots = _run_atomic_scale(
            traj, nframes=max(scales), budget=auto_budget, mode="auto"
        )
        long_auto_reports.append(repeat_long_report)
        for reference, repeated in zip(long_auto_snapshots, repeat_long_snapshots, strict=True):
            if reference["content_identity"] != repeated["content_identity"] or not np.array_equal(
                reference["payload"], repeated["payload"]
            ):
                raise RuntimeError("Long auto repeat changed a scientific density field.")
        del repeat_long_snapshots
        _release_process_memory()

    serial_reports = []
    serial_snapshots = None
    for repeat_index in range(long_repeat_count):
        _progress(
            f"single-worker reference {repeat_index + 1}/{long_repeat_count}: {max(scales)} frames"
        )
        current_serial_report, current_serial_snapshots = _run_atomic_scale(
            traj,
            nframes=max(scales),
            budget=serial_budget,
            mode="off",
            planning_budget=auto_budget,
        )
        serial_reports.append(current_serial_report)
        if serial_snapshots is None:
            serial_snapshots = current_serial_snapshots
        else:
            for reference, repeated in zip(serial_snapshots, current_serial_snapshots, strict=True):
                if reference["content_identity"] != repeated["content_identity"] or not np.array_equal(
                    reference["payload"], repeated["payload"]
                ):
                    raise RuntimeError("Long serial repeat changed a scientific density field.")
            del current_serial_snapshots
        _release_process_memory()
    assert serial_snapshots is not None
    serial_report = serial_reports[0]
    max_abs = {}
    identities = {}
    for sp, auto, serial in zip(SPECIES, long_auto_snapshots, serial_snapshots, strict=True):
        max_abs[sp] = float(np.max(np.abs(auto["payload"] - serial["payload"])))
        identities[sp] = auto["content_identity"] == serial["content_identity"]
    # A second bounded repeat checks deterministic execution without retaining a
    # second 10k scene in memory.
    _progress(f"deterministic repeat: {min(scales)} frames")
    repeat_report, repeat_snapshots = _run_atomic_scale(traj, nframes=min(scales), budget=auto_budget, mode="auto")
    deterministic_repeat = {
        sp: scale_reports[0]["fields"][sp]["content_identity"] == repeat_snapshots[i]["content_identity"]
        for i, sp in enumerate(SPECIES)
    }
    _release_process_memory()
    _progress(f"full-framework Phase-B audit: {min(scales)} frames")
    framework = _framework_audit(traj, frame_count=min(scales), budget=auto_budget)
    gpu = discover_density_gpu()
    root = Path(__file__).resolve().parents[1]
    par0 = json.loads((root / "release/par_dens0_na_lta_qualification.json").read_text())
    auto_long_seconds = np.asarray(
        [float(item["total_wall_seconds"]) for item in long_auto_reports], dtype=np.float64
    )
    serial_long_seconds = np.asarray(
        [float(item["total_wall_seconds"]) for item in serial_reports], dtype=np.float64
    )
    auto_long_median = float(np.median(auto_long_seconds))
    serial_long_median = float(np.median(serial_long_seconds))
    speedup = serial_long_median / auto_long_median
    auto_relative_mad = float(
        np.median(np.abs(auto_long_seconds - auto_long_median)) / max(auto_long_median, 1.0e-30)
    )
    serial_relative_mad = float(
        np.median(np.abs(serial_long_seconds - serial_long_median)) / max(serial_long_median, 1.0e-30)
    )
    gain_fraction = speedup - 1.0
    material_gain_floor = max(0.05, 2.0 * max(auto_relative_mad, serial_relative_mad))
    material_speedup = gain_fraction >= material_gain_floor
    all_auto_reports = [*scale_reports[:-1], *long_auto_reports]
    measured_memory_ok = all(
        int(x["rss_peak_delta_bytes"]) <= int(x["scheduler"]["max_memory_bytes"])
        for x in [*all_auto_reports, *serial_reports]
    )
    declared_memory_ok = all(
        bool(x["scheduler"]["memory_budget_obeyed"])
        and int(x["scheduler"]["peak_reserved_bytes"]) <= int(x["scheduler"]["max_memory_bytes"])
        for x in [*all_auto_reports, *serial_reports]
    )
    memory_ok = bool(measured_memory_ok and declared_memory_ok)
    cpu_ok = all(
        bool(x["scheduler"]["cpu_budget_obeyed"])
        for x in [*all_auto_reports, *serial_reports]
    )
    scientific_ok = all(v == 0.0 for v in max_abs.values()) and all(identities.values()) and all(deterministic_repeat.values())

    payload = {
        "schema": "mdstats.par-dens6-na-lta-qualification.v1",
        "package_version": "0.20.145a0",
        "qualified_on": "2026-08-10",
        "input": {
            "basename": args.trajectory.name,
            "sha256": trajectory_sha,
            "bytes": args.trajectory.stat().st_size,
            "frames": traj.n_frames,
            "atoms_per_frame": traj.n_atoms,
            "type_map": {str(k): v for k, v in TYPE_MAP.items()},
            "parsed_cache_used": args.parsed_cache is not None,
        },
        "scientific_operator": {
            "selections": list(SPECIES), "grid_shape": list(GRID),
            "gaussian_bandwidth_angstrom": SIGMA, "storage_backend": "local_sparse",
            "storage_block_shape": list(BLOCK), "smoothing_operator": DISCRETE_PERIODIZED_OPERATOR,
            "resolution_changed_by_autotune": False,
            "operator_identity_changed_by_autotune": False,
        },
        "runtime_resource_authority": {
            "snapshot": snapshot.to_json_dict(),
            "auto_budget": auto_budget.to_json_dict(),
            "resolved_cpu_fraction": auto_budget.max_threads / snapshot.available_cpu_count,
            "resolved_memory_fraction": auto_budget.max_memory_bytes / snapshot.available_memory_bytes,
        },
        "basin_aware_spread_evidence": {
            "reused_evidence": "release/par_dens0_na_lta_qualification.json",
            "same_trajectory_sha256": trajectory_sha == par0["input"]["sha256"],
            "results_angstrom": par0["results_angstrom"],
            "production_convergence": par0["production_convergence"],
        },
        "three_scale_atomic_density_benchmark": scale_reports,
        "long_trajectory_auto_repeats": long_auto_reports,
        "long_trajectory_serial_repeats": serial_reports,
        "long_trajectory_serial_reference": serial_report,
        "long_trajectory_speedup_vs_single_worker": speedup,
        "long_trajectory_speedup_classification": {
            "auto_median_total_wall_seconds": auto_long_median,
            "serial_median_total_wall_seconds": serial_long_median,
            "auto_relative_mad": auto_relative_mad,
            "serial_relative_mad": serial_relative_mad,
            "gain_fraction": gain_fraction,
            "material_gain_floor": material_gain_floor,
            "criterion": "gain >= max(5%, 2*max(relative_MAD_auto, relative_MAD_serial))",
        },
        "long_trajectory_scientific_comparison": {
            "max_absolute_pointwise_difference": max_abs,
            "content_identity_equal": identities,
            "integrals_equal": scale_reports[-1]["fields"] == serial_report["fields"],
        },
        "deterministic_repeat_at_small_scale": deterministic_repeat,
        "bounded_full_framework_planner_audit": framework,
        "gpu": None if gpu is None else gpu.to_json_dict(),
        "gpu_performance_authorized_on_this_host": gpu is not None,
        "acceptance": {
            "cpu_budget_obeyed": cpu_ok,
            "declared_memory_budget_obeyed": declared_memory_ok,
            "measured_rss_budget_obeyed": measured_memory_ok,
            "memory_budget_obeyed": memory_ok,
            "pointwise_reference_equal": all(v == 0.0 for v in max_abs.values()),
            "content_identity_equal": all(identities.values()),
            "deterministic_repeat_equal": all(deterministic_repeat.values()),
            "material_long_trajectory_speedup_observed": material_speedup,
            "production_cpu_path_authorized": bool(
                cpu_ok and memory_ok and scientific_ok and material_speedup
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    _progress(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
