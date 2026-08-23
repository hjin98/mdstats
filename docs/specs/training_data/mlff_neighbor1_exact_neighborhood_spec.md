# MLFF NEIGHBOR1 exact-neighborhood reuse specification

**Release:** `mdstats 0.20.227a0`  
**Architecture revision:** 94  
**Gate:** `NEIGHBOR1`  
**Authority:** execution optimization only; scientific authority unchanged

## 1. Scope

NEIGHBOR1 defines one exact TARGET-DATA2B/C neighborhood implementation and a reconstructible forward-CSR execution cache shared by FEAS1 and MVIDX1. It MUST NOT change feature values/scales, local radii, coverage threshold, candidate ordering, scaled-Euclidean tolerance, FEAS1 FP64 reduction order, MVIDX sparse graph semantics, target selection, model authority, training/evaluation policy, or GPU authority. The active qualification uses MACE-MPA-0 medium; the engine/cache contain no foundation-model-specific behavior and SHALL apply unchanged to MACE-MH-1 campaigns.

## 2. Exact geometry contract

`ExactNeighborhoodEngine` SHALL be the common geometric implementation. A witness block SHALL use the frozen TARGET-DATA2B scaled-Euclidean `cKDTree.query_ball_point` radius/tolerance semantics and SHALL deduplicate row neighbors to unique candidate-frame indices in canonical row-major/candidate-major order. Under outer parallelism, each cKDTree task SHALL use one native worker.

## 3. FEAS1 streaming contract

FEAS1 SHALL reduce support/capacity evidence in the same historical canonical witness-block order. At that same commit boundary it SHALL append the exact witness->candidate relation to a disk-backed CSR stream and release the ragged temporary neighbor object. The final cache SHALL use `uint64` witness offsets and `uint32` candidate indices. Final forward-CSR arrays SHALL remain file-backed for campaign execution; aggregate completed CSR payload bytes are storage, not anonymous execution RAM. Only bounded finalization/copy scratch is admitted against the stage RAM budget. When that bounded scratch is temporarily unavailable, finalization SHALL backpressure while already admitted work drains rather than fail merely because other live work occupies the budget.

## 4. Cache identity and persistence

The cache is reconstructible execution state, not scientific authority. Family identity SHALL bind label-domain identity, frame-domain/candidate ordering digest, TARGET-DATA2B family digest, candidate/witness cardinality, frozen metric/tolerance semantics, and cache-format version. Worker count, tree-worker count, query-block size, queue depth, timing, progress cadence, and host topology MUST NOT enter cache identity.

Native persistence SHALL authenticate a manifest and every NumPy array by checksum and scientific array reference. Campaign storage SHALL retain the cache as its own content-addressed record. A stale, corrupt, or missing cache SHALL be rejected/rebuilt rather than trusted.

## 5. MVIDX adoption contract

On an authenticated cache hit, MVIDX1 SHALL adopt the forward witness CSR without any geometric cKDTree/query-ball call. It SHALL then perform only its existing CSR-to-CSC inversion and hard-obligation/metadata construction. A cache miss SHALL rebuild forward CSR once through the same global NEIGHBOR1 engine and persist it. The pre-NEIGHBOR1 duplicate geometry implementation MUST NOT remain as an alternate path. CSR-to-CSC inversion is deliberately unchanged until `MVIDX-REUSE1`.

## 6. Exact-equivalence qualification

NEIGHBOR1 passes only if:

1. FEAS1 report/digest is invariant across worker/block settings and matches PERFBASE1;
2. FEAS1-emitted and independently rebuilt neighborhood stores are byte/scientific-digest identical;
3. cached and rebuilt MVIDX1 outputs are identical;
4. a cache-hit test can disable the geometric query method entirely without affecting MVIDX construction;
5. native persistence round trip and tamper rejection pass;
6. bounded scheduling, finalization-scratch RAM admission/backpressure, file-backed aggregate CSR larger than the stage RAM budget, and native mmap persistence are exercised; and
7. same-host end-to-end FEAS1->MVIDX1 timing shows a material improvement versus untouched 0.20.226a0 without changing scientific digests.

The revision-94 PERFBASE1 workload digests are:

- FEAS1: `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613`;
- NEIGHBOR1 forward CSR: `0220c89084fe957e85eb1e1c87a581eaa44869f11cb98bee7f7bd8cdafd3d74e`;
- MVIDX1: `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c`.

`MVIDX-REUSE1` is the next gate.
