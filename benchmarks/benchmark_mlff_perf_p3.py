#!/usr/bin/env python3
"""Reproducible PERF-P3 CPU microbenchmarks for the current source tree."""
from __future__ import annotations
import argparse, hashlib, json, resource, time
import numpy as np
import mdstats
from mdstats.analysis.local_structure import _LocalStructureScratch, _compute_local_structure_features_arrays, _local_structure_topology_workspace


def structural(frames: int = 300, atoms: int = 168) -> dict[str, object]:
    rng=np.random.default_rng(20260815)
    cell=np.asarray([[17.363,0,0],[8.6815,15.0368,0],[8.6815,5.0123,14.1768]],dtype=np.float64)
    base=np.resize(np.asarray([13,19,3,11,8,14],dtype=np.int32),atoms)
    frac=rng.random((frames,atoms,3))
    policy=mdstats.LocalStructureFeaturePolicy(maximum_dense_pair_work=100_000_000)
    topo=_local_structure_topology_workspace(base,policy=policy); scratch=_LocalStructureScratch(); h=hashlib.sha256()
    t0=time.perf_counter(); c0=time.process_time()
    for i in range(frames):
        out=_compute_local_structure_features_arrays(atomic_numbers=base,fractional_positions=frac[i],cell=cell,pbc=(True,True,True),frame_index=0,policy=policy,topology_workspace=topo,scratch=scratch,wrap_periodic=True)
        h.update(np.ascontiguousarray(out.values).view(np.uint8))
        h.update(np.ascontiguousarray(out.missing_mask).view(np.uint8))
    wall=time.perf_counter()-t0; cpu=time.process_time()-c0
    return {'schema':'mdstats.mlff-perf-p3.current-benchmark.v1','release':mdstats.__version__,'frames':frames,'atoms':atoms,'wall_s':wall,'cpu_s':cpu,'effective_cores':cpu/wall,'maxrss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'digest':h.hexdigest()}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--frames',type=int,default=300); ap.add_argument('--atoms',type=int,default=168); ap.add_argument('--output'); ns=ap.parse_args(); out=structural(ns.frames,ns.atoms); text=json.dumps(out,indent=2,sort_keys=True); print(text); 
    if ns.output: open(ns.output,'w').write(text+'\n')
