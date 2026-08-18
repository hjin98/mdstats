"""MVSTATE-REUSE1 integrated exact-state handoff benchmark."""
from __future__ import annotations
from dataclasses import dataclass
import json, os, resource, sys, tempfile, time
from pathlib import Path

mode=sys.argv[1]; root=Path(sys.argv[2]).resolve(); workers=int(sys.argv[3]) if len(sys.argv)>3 else 4
sys.path.insert(0,str(root)); sys.path.insert(0,str(root/'benchmarks'))
import mdstats
import benchmark_mlff_perfbase1 as pb

@dataclass
class Rung: target_size:int; frame_uids:tuple[str,...]; materializable:bool=True
@dataclass
class Dom: label_domain_id:str; content_digest:str; rungs:tuple
@dataclass
class Legacy:
    dataset_id:str; target_coverage_reference_digest:str; content_digest:str; dom:Dom
    def domain(self,label):
        if label!=self.dom.label_domain_id: raise KeyError(label)
        return self.dom

reference,role=pb._synthetic_reference(n=8192,family_count=6)
sizes=(128,256,512,1024,2048,4096)
policy=mdstats.TargetMultiViewSelectorPolicy(target_sizes=sizes)
stages=[]
def run(name,fn):
    c0=time.process_time(); t0=time.perf_counter(); obj=fn(); wall=time.perf_counter()-t0; cpu=time.process_time()-c0
    stages.append({'name':name,'wall_seconds':wall,'cpu_seconds':cpu,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    return obj

def scope(name,w=workers):
    return mdstats.StageResourceScope(stage_name=name,cpu_threads_available=max(4,workers),cpu_threads_budget=w,python_workers=w,structural_workers=1,tree_workers=1,blas_threads=1,pytorch_cpu_workers=1,ram_budget_bytes=None)

feas,neigh=run('feas_neighbor',lambda:mdstats.build_target_coverage_feasibility_artifacts(reference,role,query_workers=1,query_block_size=512,block_workers=workers,resource_scope=scope('mvstate-feas')))
idx=run('mvidx',lambda:mdstats.build_target_coverage_sparse_index(reference,role,feas,exact_neighborhood_store=neigh,query_workers=1,global_workers=workers,resource_scope=scope('mvstate-mvidx')))
cache=None
if hasattr(mdstats,'build_target_multi_view_selection_artifacts') and mode!='control':
    selection,cache=run('mvsel_state',lambda:mdstats.build_target_multi_view_selection_artifacts(reference,idx,policy=policy,execution_mode='optimized'))
else:
    selection=run('mvsel_state',lambda:mdstats.build_target_multi_view_selection_plan(reference,idx,policy=policy,execution_mode='optimized'))

repair_kwargs={'execution_mode':'optimized','proposal_workers':workers,'resource_scope':scope('mvstate-repair')}
if cache is not None: repair_kwargs['selection_state_cache']=cache
repair=run('repair',lambda:mdstats.build_target_multi_view_repair_plan(reference,idx,selection,**repair_kwargs))

d=reference.domain('target'); u=d.frame_uids
legacy=Legacy(reference.dataset_id,reference.content_digest,'4'*64,Dom('target','1'*64,tuple(Rung(s,tuple(u[:s])) for s in sizes)))
qpol=mdstats.TargetMultiViewQualificationPolicy(coverage_threshold=reference.policy.coverage_threshold,capacity_ceiling=16384)
qual=run('mvqual',lambda:mdstats.build_target_multi_view_qualification_plan(reference,idx,feas,role,legacy,repair,policy=qpol,coverage_query_workers=1,scoring_workers=workers,resource_scope=scope('mvstate-mvqual')))

persistence=None
if cache is not None:
    with tempfile.TemporaryDirectory() as td:
        rr=Path(td)/'records'; t0=time.perf_counter(); ptr=mdstats.write_target_multi_view_selection_state_native_record(cache,rr); write=time.perf_counter()-t0
        total=sum(p.stat().st_size for p in rr.rglob('*') if p.is_file())
        t0=time.perf_counter(); restored=mdstats.read_target_multi_view_selection_state_native_record(ptr,Path(td)); read=time.perf_counter()-t0
        persistence={'write_seconds':write,'read_seconds':read,'bytes':total,'restored_digest':restored.content_digest}

print(json.dumps({
 'mode':mode,'version':mdstats.__version__,'workers':workers,'stages':stages,
 'total_wall_seconds':sum(x['wall_seconds'] for x in stages),'peak_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'cache_digest':None if cache is None else cache.content_digest,'cache_persistence':persistence,
 'scientific':{'reference':reference.content_digest,'feasibility':feas.content_digest,'neighborhoods':neigh.content_digest,'mvidx':idx.content_digest,'selection':selection.content_digest,'repair':repair.content_digest,'qualification':qual.content_digest},
 'repair_swaps':repair.domain('target').total_swaps,
},sort_keys=True,indent=2))
