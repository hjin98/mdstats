"""Reproduce the CAMPAIGN-PERF-QUAL1 integrated target-data CPU fixture.

Usage:
    python benchmark_mlff_campaign_perf_qual1.py MODE SOURCE_ROOT [WORKERS]

MODE is an evidence label (for example ``control`` or ``current``). SOURCE_ROOT
must be the mdstats source tree to benchmark. The script writes one JSON record
to stdout and deliberately excludes model inference/GPU work.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os, resource, statistics, sys, time
from pathlib import Path

mode=sys.argv[1]
root=Path(sys.argv[2]).resolve()
workers=int(sys.argv[3]) if len(sys.argv)>3 else 4
# ensure source tree + benchmark helper
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'benchmarks'))
import mdstats
import benchmark_mlff_perfbase1 as pb

@dataclass
class Rung:
    target_size:int
    frame_uids:tuple[str,...]
    materializable:bool=True
@dataclass
class Dom:
    label_domain_id:str
    content_digest:str
    rungs:tuple
@dataclass
class Legacy:
    dataset_id:str
    target_coverage_reference_digest:str
    content_digest:str
    dom:Dom
    def domain(self,label):
        if label!=self.dom.label_domain_id: raise KeyError(label)
        return self.dom

reference, role = pb._synthetic_reference(n=8192, family_count=6)
sizes=(128,256,512,1024,2048,4096)
policy=mdstats.TargetMultiViewSelectorPolicy(target_sizes=sizes)

# Freeze reference identity separately from timed chain.
ref_digest=reference.content_digest
role_digest=role.content_digest

stages=[]
def run(name,fn):
    rss0=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    c0=time.process_time(); t0=time.perf_counter()
    obj=fn()
    wall=time.perf_counter()-t0; cpu=time.process_time()-c0
    rss1=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    stages.append({'name':name,'wall_seconds':wall,'cpu_seconds':cpu,'maxrss_kib':rss1,'rss_peak_delta_kib':max(0,rss1-rss0)})
    return obj

if hasattr(mdstats,'StageResourceScope'):
    av=max(workers,4)
    def scope(name,w=workers):
        return mdstats.StageResourceScope(stage_name=name,cpu_threads_available=av,cpu_threads_budget=w,python_workers=w,structural_workers=1,tree_workers=1,blas_threads=1,pytorch_cpu_workers=1,ram_budget_bytes=None)
else:
    scope=None

# FEAS + exact neighborhoods (current) or FEAS alone (baseline).
if hasattr(mdstats,'build_target_coverage_feasibility_artifacts'):
    def do_feas():
        return mdstats.build_target_coverage_feasibility_artifacts(reference,role,query_workers=1,query_block_size=512,block_workers=workers,resource_scope=scope('closure-feas'))
    feasibility, neighborhoods = run('feas_neighbor', do_feas)
else:
    feasibility = run('feas_neighbor', lambda: mdstats.build_target_coverage_feasibility_report(reference,role,query_workers=1,query_block_size=512,block_workers=workers))
    neighborhoods=None

# MVIDX, reusing exact graph when API supports it.
def do_mvidx():
    kwargs=dict(query_workers=1 if neighborhoods is not None else workers,query_block_size=512)
    if neighborhoods is not None:
        kwargs.update(exact_neighborhood_store=neighborhoods,global_workers=workers,resource_scope=scope('closure-mvidx'))
    return mdstats.build_target_coverage_sparse_index(reference,role,feasibility,**kwargs)
index=run('mvidx',do_mvidx)
selection=run('mvsel',lambda:mdstats.build_target_multi_view_selection_plan(reference,index,policy=policy,execution_mode='optimized'))

# Repair exact optimized path; current may parallelize immutable proposals.
def do_repair():
    kwargs={'execution_mode':'optimized'}
    if 'proposal_workers' in __import__('inspect').signature(mdstats.build_target_multi_view_repair_plan).parameters:
        kwargs.update(proposal_workers=workers,resource_scope=scope('closure-repair'))
    return mdstats.build_target_multi_view_repair_plan(reference,index,selection,**kwargs)
repair=run('repair',do_repair)

# Legacy ladder uses the same natural prefix to create the same-N comparison set.
d=reference.domain('target'); u=d.frame_uids
legacy=Legacy(reference.dataset_id,reference.content_digest,'4'*64,Dom('target','1'*64,tuple(Rung(s,tuple(u[:s])) for s in sizes)))
qpol=mdstats.TargetMultiViewQualificationPolicy(coverage_threshold=reference.policy.coverage_threshold,capacity_ceiling=16384)
def do_mvqual():
    kwargs={'policy':qpol}
    sig=__import__('inspect').signature(mdstats.build_target_multi_view_qualification_plan).parameters
    if 'scoring_workers' in sig:
        kwargs.update(coverage_query_workers=1,scoring_workers=workers,resource_scope=scope('closure-mvqual'))
    else:
        kwargs.update(coverage_query_workers=workers)
    return mdstats.build_target_multi_view_qualification_plan(reference,index,feasibility,role,legacy,repair,**kwargs)
qual=run('mvqual',do_mvqual)

scientific={
 'reference':ref_digest,
 'role':role_digest,
 'feasibility':feasibility.content_digest,
 'mvidx':index.content_digest,
 'selection':selection.content_digest,
 'repair':repair.content_digest,
 'qualification':qual.content_digest,
}
if neighborhoods is not None: scientific['neighborhoods']=neighborhoods.content_digest
payload={
 'mode':mode,'version':mdstats.__version__,'workers':workers,
 'scientific':scientific,'stages':stages,
 'total_wall_seconds':sum(x['wall_seconds'] for x in stages),
 'total_cpu_seconds':sum(x['cpu_seconds'] for x in stages),
 'peak_maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'master_order_count':len(selection.domain('target').master_order),
 'repair_swaps':repair.domain('target').total_swaps,
 'qualification_domains':len(qual.domains),
}
print(json.dumps(payload,indent=2,sort_keys=True))
