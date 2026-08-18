from __future__ import annotations
import gc,json,pickle,time,resource
from pathlib import Path
from mdstats import prepare_sparse_density_mesh, MeshExtractionOptions

scene_path=Path('/mnt/data/mdstats_0_19_53a0_TRAJECTORY4_scene.pkl')
out_path=Path('/mnt/data/mdstats_ld9v1_work/mdstats_ld8s4_work/benchmarks/ld9_v1_stress_mesh.json')
with scene_path.open('rb') as f: scene=pickle.load(f)
options=MeshExtractionOptions(
    render_tile_shape=(32,32,32),
    max_crossing_cells_per_tile=200_000,
    max_raw_faces_per_tile=1_000_000,
    max_raw_vertices_per_tile=2_400_000,
    max_transient_mesh_bytes=512*1024**2,
    max_total_crossing_cells=4_000_000,
    max_total_raw_faces=20_000_000,
    max_total_raw_vertices=60_000_000,
    max_planning_workspace_bytes=1024*1024**2,
)
rows=[]
start_all=time.perf_counter()
for field in scene.atomic_density_fields:
    for fraction in (0.5,0.8,0.95):
        t=time.perf_counter()
        surface=prepare_sparse_density_mesh(
            field,fraction,
            max_faces=2_000_000,
            max_candidate_cells=4_000_000,
            max_raw_faces=20_000_000,
            max_raw_vertices=60_000_000,
            max_workspace_bytes=2_500_000_000,
            max_dense_fallback_nodes=4_000_000,
            allow_cloud_fallback=False,
            extraction_method='tiled',
            extraction_options=options,
        )
        elapsed=time.perf_counter()-t
        mesh=surface.mesh
        assert mesh is not None
        ex=mesh.metadata['tiled_extraction']
        plan=mesh.metadata['contour_tile_plan']
        row={
            'label':field.label,
            'mass_fraction':fraction,
            'seconds':elapsed,
            'candidate_cells':mesh.resources.candidate_cell_count,
            'tile_count':ex['tile_count'],
            'marching_cubes_calls':ex['marching_cubes_call_count'],
            'raw_vertices':mesh.resources.raw_vertex_count,
            'raw_faces':mesh.resources.raw_face_count,
            'indexed_vertices':mesh.resources.canonical_vertex_count,
            'indexed_faces':mesh.resources.canonical_face_count,
            'max_tile_transient_bytes':ex['maximum_tile_transient_bytes'],
            'estimated_peak_bytes':mesh.resources.estimated_peak_bytes,
            'planning_bytes':plan['planning_bytes'],
            'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
        rows.append(row)
        print(json.dumps(row),flush=True)
        del surface,mesh
        gc.collect()
result={
    'schema_version':'mdstats.ld9-v1-stress-mesh-benchmark.v1',
    'source_scene':str(scene_path),
    'render_tile_shape':[32,32,32],
    'rows':rows,
    'total_seconds':time.perf_counter()-start_all,
    'total_faces':sum(r['indexed_faces'] for r in rows),
    'total_vertices':sum(r['indexed_vertices'] for r in rows),
    'total_marching_cubes_calls':sum(r['marching_cubes_calls'] for r in rows),
    'legacy_render_seconds':729.132034452,
    'legacy_total_faces':3184902,
    'legacy_total_vertices':1599109,
}
out_path.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
