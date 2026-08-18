from __future__ import annotations
import json,pickle,time,resource,sys
from mdstats import prepare_sparse_density_mesh, MeshExtractionOptions
idx=int(sys.argv[1]); q=float(sys.argv[2])
with open('/mnt/data/mdstats_0_19_53a0_TRAJECTORY4_scene.pkl','rb') as f: scene=pickle.load(f)
field=scene.atomic_density_fields[idx]
opts=MeshExtractionOptions(render_tile_shape=(32,32,32),max_crossing_cells_per_tile=200000,max_raw_faces_per_tile=1000000,max_raw_vertices_per_tile=2400000,max_transient_mesh_bytes=512*1024**2,max_total_crossing_cells=4000000,max_total_raw_faces=20000000,max_total_raw_vertices=60000000,max_planning_workspace_bytes=1024*1024**2)
t=time.perf_counter()
s=prepare_sparse_density_mesh(field,q,max_faces=2_000_000,max_candidate_cells=4_000_000,max_raw_faces=20_000_000,max_raw_vertices=60_000_000,max_workspace_bytes=2_500_000_000,max_dense_fallback_nodes=4_000_000,allow_cloud_fallback=False,extraction_method='tiled',extraction_options=opts)
elapsed=time.perf_counter()-t
m=s.mesh; assert m is not None
ex=m.metadata['tiled_extraction']; plan=m.metadata['contour_tile_plan']
print(json.dumps({'label':field.label,'mass_fraction':q,'seconds':elapsed,'candidate_cells':m.resources.candidate_cell_count,'tile_count':ex['tile_count'],'marching_cubes_calls':ex['marching_cubes_call_count'],'raw_vertices':m.resources.raw_vertex_count,'raw_faces':m.resources.raw_face_count,'indexed_vertices':m.resources.canonical_vertex_count,'indexed_faces':m.resources.canonical_face_count,'max_tile_transient_bytes':ex['maximum_tile_transient_bytes'],'estimated_peak_bytes':m.resources.estimated_peak_bytes,'planning_bytes':plan['planning_bytes'],'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
