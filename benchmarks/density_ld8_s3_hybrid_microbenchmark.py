#!/usr/bin/env python3
"""Focused LD8-S3 hybrid direct/FFT equivalence and crossover benchmark."""
from __future__ import annotations
import argparse,json,platform,time,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from mdstats.plotting.density_block_direct import realize_density_target_owned_direct
from mdstats.plotting.density_block_routing import build_periodic_kernel_block_routing
from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_kernel import build_periodic_gaussian_stencil_support
from mdstats.plotting.density_sparse_reference import SparseCICNodeMasses3D
from mdstats.plotting.density_support_atlas import build_density_support_atlas,pack_periodic_cic_source
from mdstats.plotting.density_tiled_fft import DensityHybridExecutorOptions,plan_hybrid_tiled_realization,realize_density_hybrid_tiled
SCHEMA='mdstats.density-ld8-s3-hybrid-microbenchmark.v1'

def source(shape,coords):
    coords=np.unique(np.asarray(coords,dtype=np.int64)%np.asarray(shape),axis=0)
    flat=np.ravel_multi_index(coords.T,shape,order='C');order=np.argsort(flat);flat=flat[order]
    rng=np.random.default_rng(17+len(coords));m=rng.random(len(coords));m/=m.sum()
    return SparseCICNodeMasses3D(grid_shape=shape,flat_indices=flat,node_masses=m,total_measure=1.0,source_provenance=DensitySourceProvenance(source_kind='benchmark'),metadata={'case':'ld8_s3'})

def cases(shape):
    rng=np.random.default_rng(0)
    fragmented=np.column_stack((rng.integers(0,shape[0],64),rng.integers(0,shape[1],64),rng.integers(0,shape[2],64)))
    compact=np.column_stack(np.unravel_index(np.arange(512),(8,8,8),order='C'))+np.asarray((32,32,32))
    boundary=np.concatenate((np.column_stack((np.zeros(64,dtype=int),rng.integers(0,shape[1],64),rng.integers(0,shape[2],64))),np.column_stack((np.full(64,shape[0]-1,dtype=int),rng.integers(0,shape[1],64),rng.integers(0,shape[2],64)))),axis=0)
    oxygen=np.column_stack((rng.integers(0,shape[0],2048),rng.integers(0,shape[1],2048),rng.integers(0,shape[2],2048)))
    return {'fragmented':fragmented,'compact':compact,'boundary_crossing':boundary,'oxygen_heavy':oxygen}

def run_case(name,coords,shape,stencil):
    cic=source(shape,coords);src=pack_periodic_cic_source(cic,storage_block_shape=(16,16,16));routing=build_periodic_kernel_block_routing(stencil,storage_block_shape=(16,16,16));atlas=build_density_support_atlas(src,routing)
    options=DensityHybridExecutorOptions(executor_mode='auto',compute_tile_shape=(32,32,32),min_fft_source_nodes=16)
    t=time.perf_counter();plan=plan_hybrid_tiled_realization(src,stencil,routing,atlas,options=options);plan_s=time.perf_counter()-t
    t=time.perf_counter();hybrid=realize_density_hybrid_tiled(src,stencil,routing,atlas,field_key=name,label=name,physical_units='count / angstrom^3',broadening_metric='effective_cic_stencil_rms_v1',approved_plan=plan);hybrid_s=time.perf_counter()-t
    t=time.perf_counter();direct=realize_density_target_owned_direct(src,stencil,routing,atlas,field_key=name,label=name,physical_units='count / angstrom^3',broadening_metric='effective_cic_stencil_rms_v1');direct_s=time.perf_counter()-t
    l1=float(np.sum(np.abs(hybrid.packed_values-direct.packed_values),dtype=np.float64)/np.sum(np.abs(direct.packed_values),dtype=np.float64));linf=float(np.max(np.abs(hybrid.packed_values-direct.packed_values))/np.max(np.abs(direct.packed_values)))
    return {'case':name,'source_node_count':src.occupied_node_count,'target_node_count':atlas.target_support_node_count,'stencil_offset_count':stencil.stencil_offset_count,'tile_count':plan.compute_tile_count,'direct_tile_count':plan.direct_tile_count,'fft_tile_count':plan.fft_tile_count,'planning_seconds':plan_s,'hybrid_seconds':hybrid_s,'canonical_s2_seconds':direct_s,'speedup_over_s2':direct_s/hybrid_s,'relative_l1':l1,'relative_linf':linf,'integral':hybrid.integral,'nonpositive_repairs':int(hybrid.metadata['fft_nonpositive_node_repairs'])}

def markdown(payload,path):
    lines=['# LD8-S3 hybrid microbenchmark','', '| Case | Source nodes | Target nodes | Tiles D/F | Hybrid | S2 | Speedup | Relative L1 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for x in payload['cases']:lines.append(f"| {x['case']} | {x['source_node_count']:,} | {x['target_node_count']:,} | {x['direct_tile_count']}/{x['fft_tile_count']} | {x['hybrid_seconds']:.3f} s | {x['canonical_s2_seconds']:.3f} s | {x['speedup_over_s2']:.2f}x | {x['relative_l1']:.3e} |")
    lines += ['','All cases use the same finite normalized Gaussian stencil and exact support atlas.',''];path.write_text('\n'.join(lines))

def main():
    p=argparse.ArgumentParser();p.add_argument('--output-json',type=Path,required=True);p.add_argument('--output-markdown',type=Path);p.add_argument('--shape',type=int,nargs=3,default=(96,96,96));a=p.parse_args();shape=tuple(a.shape);cell=np.diag(np.asarray(shape,dtype=float)*0.1);stencil=build_periodic_gaussian_stencil_support(shape,cell,0.2,kernel_tail_tolerance=1e-8);started=time.perf_counter();rows=[]
    for n,c in cases(shape).items():print('[S3 micro]',n,flush=True);rows.append(run_case(n,c,shape,stencil))
    payload={'schema':SCHEMA,'grid_shape':list(shape),'display_cell':cell.tolist(),'gaussian_bandwidth':0.2,'kernel_tail_tolerance':1e-8,'stencil_offset_count':stencil.stencil_offset_count,'host':{'platform':platform.platform(),'python':platform.python_version(),'numpy':np.__version__},'cases':rows,'total_seconds':time.perf_counter()-started};a.output_json.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');markdown(payload,a.output_markdown or a.output_json.with_suffix('.md'));print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':main()
