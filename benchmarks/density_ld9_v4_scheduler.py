from __future__ import annotations
import argparse
import json, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    DensitySourceProvenance,
    MeshExtractionOptions,
    MeshSimplificationOptions,
    PeriodicWeightedSamples3D,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_reference,
)
from mdstats.plotting.density_mesh_execution import DensityMeshExecutionOptions, DensityMeshExecutionReport
from mdstats.plotting.framework_dynamics import _prepare_sparse_density_mesh_isolated_timed

parser = argparse.ArgumentParser(description="Run the LD9-V4 bounded real-mesh shell scheduler benchmark.")
parser.add_argument("--json-output", type=Path, default=Path("benchmarks/density_ld9_v4_scheduler.json"))
parser.add_argument("--markdown-output", type=Path, default=Path("benchmarks/density_ld9_v4_scheduler.md"))
args = parser.parse_args()
OUT = args.json_output
MD = args.markdown_output
OUT.parent.mkdir(parents=True, exist_ok=True)
MD.parent.mkdir(parents=True, exist_ok=True)

cell = np.asarray([[12.0,0,0],[1.7,10.8,0],[0.9,1.2,9.9]], dtype=np.float64)
positions = np.asarray([
    [0.18,0.22,0.28],[0.31,0.36,0.43],[0.51,0.48,0.55],
    [0.68,0.64,0.61],[0.82,0.77,0.72],[0.97,0.50,0.48],
], dtype=np.float64)
samples = PeriodicWeightedSamples3D(
    fractional_positions=positions,
    weights=np.full(len(positions), 1.0/len(positions)),
    source_provenance=DensitySourceProvenance(source_kind='atomic_occupancy', atom_indices=tuple(range(len(positions)))),
    total_measure=1.0,
    measure_kind='occupancy',
    measure_units='count',
)
reference = prepare_sparse_canonical_density_reference(
    samples,
    grid_shape=(88,80,72),
    display_cell=cell,
    gaussian_bandwidth=0.26,
    field_key='ld9-v4-scheduler-benchmark',
    label='density',
    physical_units='angstrom^-3',
    broadening_metric=GAUSSIAN_SIGMA_BROADENING,
    max_workspace_bytes=1_000_000_000,
)
field = pack_sparse_reference_blocks(
    reference,
    block_shape=(8,8,8),
    max_stored_block_values=20_000_000,
    max_planning_bytes=1_000_000_000,
)
fractions = (0.50,0.80,0.95)
policies = {
    0.50: MeshSimplificationOptions(target_faces=10000, hard_target=False, max_samples=5000, max_surface_error_p99=0.15, max_surface_error_max=0.35, max_implicit_displacement_p99=0.035, max_normal_degradation_degrees=18, max_relative_scalar_residual_p99=0.25, projection_max_step=0.04),
    0.80: MeshSimplificationOptions(target_faces=14000, hard_target=False, max_samples=5000, max_surface_error_p99=0.15, max_surface_error_max=0.35, max_implicit_displacement_p99=0.035, max_normal_degradation_degrees=18, max_relative_scalar_residual_p99=0.25, projection_max_step=0.04),
    0.95: MeshSimplificationOptions(target_faces=18000, hard_target=False, max_samples=5000, max_surface_error_p99=0.18, max_surface_error_max=0.40, max_implicit_displacement_p99=0.04, max_normal_degradation_degrees=20, max_relative_scalar_residual_p99=0.30, projection_max_step=0.05),
}
common = dict(
    max_faces=500_000,
    max_candidate_cells=4_000_000,
    max_raw_faces=2_000_000,
    max_raw_vertices=4_000_000,
    max_workspace_bytes=1_000_000_000,
    max_dense_fallback_nodes=4_000_000,
    allow_cloud_fallback=False,
    cloud_max_points=100_000,
    extraction_options=MeshExtractionOptions(render_tile_shape=(24,24,24)),
)

def run(workers:int):
    options = DensityMeshExecutionOptions(max_parallel_shell_workers=workers, worker_native_threads=1, worker_timeout_seconds=300.0)
    start=time.perf_counter()
    results=[]
    if workers == 1:
        for f in fractions:
            surface, seconds = _prepare_sparse_density_mesh_isolated_timed(field, f, execution_options=options, simplification_options=policies[f], **common)
            results.append((f,surface,seconds))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures=[ex.submit(_prepare_sparse_density_mesh_isolated_timed, field, f, execution_options=options, simplification_options=policies[f], **common) for f in fractions]
            for f, fut in zip(fractions,futures,strict=True):
                surface,seconds=fut.result()
                results.append((f,surface,seconds))
    wall=time.perf_counter()-start
    shells=[]
    for f,surface,seconds in results:
        mesh=surface.mesh
        shells.append({'mass_fraction':f,'seconds':seconds,'faces':int(mesh.faces.shape[0]),'vertices':int(mesh.vertices_cartesian.shape[0]),'render_kind':surface.render_kind})
    report=DensityMeshExecutionReport(
        isolated_shell_count=len(results),parallel_worker_count=workers,wall_seconds=wall,
        sum_shell_seconds=sum(x['seconds'] for x in shells),maximum_shell_seconds=max(x['seconds'] for x in shells),
        metadata={'benchmark':'bounded_real_mesh_shells_v1'}
    )
    return {'report':report.to_json_dict(),'shells':shells}

serial=run(1)
parallel=run(3)
serial_key={(x['mass_fraction'],x['faces'],x['vertices']) for x in serial['shells']}
parallel_key={(x['mass_fraction'],x['faces'],x['vertices']) for x in parallel['shells']}
if serial_key != parallel_key:
    raise RuntimeError('serial/parallel geometry counts differ')
speedup=serial['report']['wall_seconds']/parallel['report']['wall_seconds']
payload={'schema':'mdstats.ld9-v4-scheduler-benchmark.v1','field':{'grid_shape':[88,80,72],'nonzero_nodes':field.storage_summary().nonzero_node_count},'serial':serial,'parallel':parallel,'wall_speedup':speedup,'deterministic_geometry_counts':True}
OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
lines=['# LD9-V4 bounded shell scheduler benchmark','',f"- Grid: `88 x 80 x 72`",f"- Positive scientific nodes: **{payload['field']['nonzero_nodes']:,}**",f"- Serial wall time: **{serial['report']['wall_seconds']:.3f} s**",f"- Three-worker wall time: **{parallel['report']['wall_seconds']:.3f} s**",f"- Wall speedup: **{speedup:.3f}x**",f"- Geometry counts deterministic: **yes**",'', '| HDR | Faces | Vertices | Serial shell s | Parallel shell s |','|---:|---:|---:|---:|---:|']
ps={x['mass_fraction']:x for x in parallel['shells']}
for x in serial['shells']:
    y=ps[x['mass_fraction']]
    lines.append(f"| {x['mass_fraction']:.2f} | {x['faces']:,} | {x['vertices']:,} | {x['seconds']:.3f} | {y['seconds']:.3f} |")
MD.write_text('\n'.join(lines)+'\n')
print(json.dumps(payload,indent=2))
