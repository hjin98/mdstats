#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from mdstats.analysis._cell_list import (
    _minimum_metric_norm_squared_in_box,
    _minimum_metric_norm_squared_in_boxes,
)
from mdstats.analysis.bond_angle import _batched_center_angles, _center_angles
from mdstats.plotting.density_support_atlas import _brick_coordinates_to_target_bitsets


def best_time(fn, repeats=3):
    values=[]
    result=None
    for _ in range(repeats):
        start=time.perf_counter(); result=fn(); values.append(time.perf_counter()-start)
    return min(values), result


def metric_benchmark(rng):
    n=12000
    a=rng.normal(size=(3,3)); metric=a.T@a+np.eye(3)*0.25
    center=rng.uniform(-2,2,size=(n,3)); half=rng.uniform(0.01,0.5,size=(n,3))
    lower=center-half; upper=center+half
    old_t, old=best_time(lambda: np.asarray([
        _minimum_metric_norm_squared_in_box(metric, lower[i], upper[i], tolerance=1e-12)
        for i in range(n)
    ]), repeats=1)
    new_t, new=best_time(lambda: _minimum_metric_norm_squared_in_boxes(metric, lower, upper, tolerance=1e-12))
    np.testing.assert_allclose(new, old, rtol=1e-11, atol=1e-12)
    return {'items':n,'old_seconds':old_t,'new_seconds':new_t,'speedup':old_t/new_t}


def bond_benchmark(rng):
    centers=30000; degree=4
    offsets=np.arange(0,(centers+1)*degree,degree,dtype=np.int64)
    vectors=rng.normal(size=(centers*degree,3)); vectors/=np.linalg.norm(vectors,axis=1)[:,None]
    nl=SimpleNamespace(offsets=offsets,vectors=vectors,row_slice=lambda i: slice(int(offsets[i]),int(offsets[i+1])))
    accepted=np.ones(centers,dtype=bool)
    old_t, old=best_time(lambda: np.concatenate([_center_angles(nl,nl,i,symmetric=True) for i in range(centers)]), repeats=1)
    new_t, pair=best_time(lambda: _batched_center_angles(nl,nl,accepted,symmetric=True))
    new=pair[0]
    np.testing.assert_allclose(new, old, rtol=1e-12, atol=1e-12)
    return {'centers':centers,'angles':int(old.size),'old_seconds':old_t,'new_seconds':new_t,'speedup':old_t/new_t}


def old_target_bitsets(brick_coordinates, source_block_index, routing, signed_minimum):
    block=np.asarray(routing.storage_block_shape,dtype=np.int64)
    logical=np.asarray(routing.logical_grid_shape,dtype=np.int64)
    source_start=source_block_index.astype(np.int64)*block
    global_coordinates=(source_start[None,:]+brick_coordinates+signed_minimum[None,:])%logical
    target_blocks=global_coordinates//block
    target_local=global_coordinates-target_blocks*block
    target_block_flat=np.ravel_multi_index(target_blocks.T,routing.block_grid_shape,order='C')
    target_local_flat=np.ravel_multi_index(target_local.T,tuple(block),order='C')
    grouped={}
    for b,l in zip(target_block_flat,target_local_flat,strict=True):
        grouped[int(b)]=grouped.get(int(b),0)|(1<<int(l))
    flats=np.asarray(sorted(grouped),dtype=np.int64)
    words=np.zeros((len(flats),routing.block_word_count),dtype=np.uint64)
    for row,b in enumerate(flats):
        value=grouped[int(b)]
        for word in range(routing.block_word_count):
            words[row,word]=np.uint64((value>>(64*word))&((1<<64)-1))
    return flats,words


def bitset_benchmark(rng):
    block=(16,16,16); logical=(256,256,256)
    routing=SimpleNamespace(storage_block_shape=block,logical_grid_shape=logical,block_grid_shape=(16,16,16),block_word_count=64)
    n=250000
    coords=rng.integers(-30,47,size=(n,3),dtype=np.int64)
    source=np.asarray((7,8,9),dtype=np.int32); minimum=np.asarray((-5,-5,-5),dtype=np.int64)
    old_t, old=best_time(lambda: old_target_bitsets(coords,source,routing,minimum),repeats=1)
    new_t, new=best_time(lambda: _brick_coordinates_to_target_bitsets(coords,source,routing,minimum))
    np.testing.assert_array_equal(new[0],old[0]); np.testing.assert_array_equal(new[1],old[1])
    return {'coordinates':n,'target_blocks':int(new[0].size),'old_seconds':old_t,'new_seconds':new_t,'speedup':old_t/new_t}


def mesh_reconcile_benchmark(rng):
    unique_count=60000; repeats=4; n=unique_count*repeats
    base=np.column_stack((rng.integers(0,4,size=unique_count),rng.integers(0,100000,size=(unique_count,3))))
    keys=np.repeat(base,repeats,axis=0); rng.shuffle(keys)
    def old():
        mapping={}; inverse=np.empty(n,dtype=np.int64)
        for i,row in enumerate(keys):
            key=tuple(int(x) for x in row)
            idx=mapping.get(key)
            if idx is None:
                idx=len(mapping); mapping[key]=idx
            inverse[i]=idx
        return len(mapping),inverse
    def new():
        unique, inverse=np.unique(keys,axis=0,return_inverse=True)
        return len(unique),inverse
    old_t, old_result=best_time(old,repeats=1)
    new_t, new_result=best_time(new)
    assert old_result[0]==new_result[0]
    return {'occurrences':n,'unique_vertices':unique_count,'old_seconds':old_t,'new_seconds':new_t,'speedup':old_t/new_t}


def main():
    rng=np.random.default_rng(872341)
    results={
        'schema':'mdstats.interpreter-hotpath-stage2-benchmark.v1',
        'metric_box_minimization':metric_benchmark(rng),
        'bond_angle_ragged_pairs':bond_benchmark(rng),
        'support_atlas_target_bitsets':bitset_benchmark(rng),
        'mesh_vertex_reconciliation':mesh_reconcile_benchmark(rng),
    }
    output=Path('audits/release/interpreter_hotpath_stage2_benchmarks.json')
    output.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__': main()
