#!/usr/bin/env python3
"""Benchmark the LD8-S3 hybrid tiled direct/FFT executor on saved fields."""
from __future__ import annotations
import argparse
import json
import pickle
import platform
import resource
import sys
import time
from pathlib import Path

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from density_ld8_p0_benchmark import _resolution_options,_scene_field_samples
from mdstats.plotting.atomic_density import resolve_density_numerics
from mdstats.plotting.density_block_routing import get_periodic_kernel_block_routing
from mdstats.plotting.density_sparse_optimization import aggregate_periodic_cic_sparse_optimized,get_periodic_gaussian_stencil_support
from mdstats.plotting.density_support_atlas import pack_periodic_cic_source,build_density_support_atlas
from mdstats.plotting.density_tiled_fft import DensityHybridExecutorOptions,plan_hybrid_tiled_realization,realize_density_hybrid_tiled
SCHEMA='mdstats.density-ld8-s3-hybrid-benchmark.v1'
def _baseline(path:Path|None):
    if path is None:return {}
    p=json.loads(path.read_text());return {x['label']:x for x in p.get('fields',[])}
def _md(payload,path):
    lines=['# LD8-S3 hybrid tiled executor benchmark','',f"- Total elapsed: `{payload['total_seconds']:.3f} s`",'', '| Field | Grid | Tiles (D/F) | Atlas | S3 realize | LD7 realize | Speedup | Peak RSS | Rel. L1 gate |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in payload['fields']:
        lines.append('| {label} | {grid} | {tiles} ({d}/{f}) | {atlas:.3f} s | {real:.3f} s | {ld7:.3f} s | {speed:.2f}x | {rss:.3f} GiB | tests |'.format(label=x['label'],grid='x'.join(map(str,x['grid_shape'])),tiles=x['compute_tile_count'],d=x['direct_tile_count'],f=x['fft_tile_count'],atlas=x['atlas_seconds'],real=x['hybrid_realization_seconds'],ld7=x.get('ld7_scientific_seconds',float('nan')),speed=x.get('realization_speedup_over_ld7',float('nan')),rss=x['process_peak_rss_bytes']/2**30))
    lines += ['','Scientific equivalence is enforced by the focused S2 comparison suite; the production benchmark measures execution and support counts without repeating the full LD7 field.','']
    path.write_text('\n'.join(lines))
def run(a):
    started=time.perf_counter()
    with a.scene.open('rb') as h: scene=pickle.load(h)
    base=_baseline(a.ld7_baseline); fields=list(scene.atomic_density_fields)
    if a.labels: fields=[f for f in fields if f.label in set(a.labels)]
    out=[]
    for field in fields:
        print(f'[S3] {field.label}: prepare',flush=True); field_start=time.perf_counter()
        frac,samples=_scene_field_samples(scene,field,None); fw=np.full(frac.shape[0],1/frac.shape[0])
        t=time.perf_counter(); res=resolve_density_numerics(scene.display_cell,options=_resolution_options(a.kernel_tail_tolerance),fractional_by_frame=frac,frame_weights=fw,pbc=np.ones(3,bool),max_voxels=np.iinfo(np.int64).max,field_label=field.label); resolution=time.perf_counter()-t
        t=time.perf_counter(); cic=aggregate_periodic_cic_sparse_optimized(samples,res.grid_shape); cic_s=time.perf_counter()-t
        t=time.perf_counter(); st,_=get_periodic_gaussian_stencil_support(res.grid_shape,scene.display_cell,res.gaussian_bandwidth,kernel_tail_tolerance=a.kernel_tail_tolerance); stencil_s=time.perf_counter()-t
        t=time.perf_counter(); src=pack_periodic_cic_source(cic,storage_block_shape=tuple(a.block_shape)); source_s=time.perf_counter()-t
        t=time.perf_counter(); rt,_=get_periodic_kernel_block_routing(st,storage_block_shape=tuple(a.block_shape)); routing_s=time.perf_counter()-t
        t=time.perf_counter(); at=build_density_support_atlas(src,rt); atlas_s=time.perf_counter()-t
        opt=DensityHybridExecutorOptions(executor_mode=a.executor_mode,compute_tile_shape=tuple(a.tile_shape),min_fft_source_nodes=a.min_fft_source_nodes,fft_workers=a.fft_workers)
        t=time.perf_counter(); plan=plan_hybrid_tiled_realization(src,st,rt,at,options=opt); plan_s=time.perf_counter()-t
        t=time.perf_counter(); result=realize_density_hybrid_tiled(src,st,rt,at,field_key=field.field_key,label=field.label,physical_units=field.physical_units,broadening_metric='effective_cic_stencil_rms_v1',approved_plan=plan); realize_s=time.perf_counter()-t
        b=base.get(field.label,{}).get('ld7_baseline',{}); ld7=float(b.get('scientific_seconds',float('nan')))
        row={'label':field.label,'grid_shape':list(res.grid_shape),'source_node_count':src.occupied_node_count,'target_support_node_count':at.target_support_node_count,'stencil_offset_count':st.stencil_offset_count,'compute_tile_count':plan.compute_tile_count,'direct_tile_count':plan.direct_tile_count,'fft_tile_count':plan.fft_tile_count,'predicted_peak_bytes':plan.predicted_peak_bytes,'resolution_seconds':resolution,'cic_seconds':cic_s,'stencil_seconds':stencil_s,'source_packing_seconds':source_s,'routing_seconds':routing_s,'atlas_seconds':atlas_s,'hybrid_planning_seconds':plan_s,'hybrid_realization_seconds':realize_s,'field_total_seconds':time.perf_counter()-field_start,'process_peak_rss_bytes':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,'integral':result.integral,'nonpositive_node_repairs':int(result.metadata['fft_nonpositive_node_repairs']),'fft_kernel_transform_count':int(result.metadata['fft_kernel_transform_count']),'ld7_scientific_seconds':ld7,'realization_speedup_over_ld7':ld7/realize_s if np.isfinite(ld7) else None}
        print(f"[S3] {field.label}: realize {realize_s:.3f}s, tiles {plan.direct_tile_count}/{plan.fft_tile_count}, integral {result.integral:.12g}",flush=True);out.append(row)
    return {'schema':SCHEMA,'scene_pickle':str(a.scene),'kernel_tail_tolerance':a.kernel_tail_tolerance,'storage_block_shape':list(a.block_shape),'compute_tile_shape':list(a.tile_shape),'executor_mode':a.executor_mode,'min_fft_source_nodes':a.min_fft_source_nodes,'fft_workers':a.fft_workers,'host':{'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__},'fields':out,'aggregate_hybrid_realization_seconds':sum(x['hybrid_realization_seconds'] for x in out),'aggregate_atlas_seconds':sum(x['atlas_seconds'] for x in out),'total_seconds':time.perf_counter()-started}
def main():
    p=argparse.ArgumentParser();p.add_argument('scene',type=Path);p.add_argument('--ld7-baseline',type=Path);p.add_argument('--output-json',type=Path,required=True);p.add_argument('--output-markdown',type=Path);p.add_argument('--kernel-tail-tolerance',type=float,default=1e-8);p.add_argument('--block-shape',type=int,nargs=3,default=(16,16,16));p.add_argument('--tile-shape',type=int,nargs=3,default=(32,32,32));p.add_argument('--executor-mode',choices=('auto','direct','fft'),default='auto');p.add_argument('--min-fft-source-nodes',type=int,default=16);p.add_argument('--fft-workers',type=int,default=1);p.add_argument('--label',dest='labels',action='append');a=p.parse_args(); payload=run(a);a.output_json.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');_md(payload,a.output_markdown or a.output_json.with_suffix('.md'));print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':main()
