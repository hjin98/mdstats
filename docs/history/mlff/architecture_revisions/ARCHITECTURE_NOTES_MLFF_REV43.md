# MLFF architecture revision 43 - post-major-revision performance optimization program

This architecture-only revision supersedes the shorter REV42 post-CERT optimization roadmap in the canonical `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`. Runtime behavior is unchanged until the corresponding gates are implemented. The existing DATA6-MIC1 correctness hotfix and TARGET-DATA2B-PERF1 exact-kNN performance hotfix are part of the starting baseline.

The final frozen gate order is:

1. `PERF-BASE0` - freeze exact numerical/decision/performance reference evidence before additional optimization.
2. `PERF-P0` - migrate TARGET-DATA2B to native-array/sharded/mmap authority v2; factor shared weights; consolidate exact weighted statistics; add an exact uniform-weight fixed-mass order-statistic fast path; retain cKDTree as authority unless another exact backend passes deterministic numerical qualification.
3. `PERF-P1` - create one shared exact selector/coverage engine for TARGET-DATA2C and DATA7 using immutable row norms, quota-to-FPS state continuation, preallocated/mmap selector storage, progressive nested-rung scoring, and `O(K)` persistent selected-neighbor state instead of a dense `K x K` matrix.
4. `PERF-P2` - advance TARGET-DATA2C to a lazy ladder authority v2 that stops exact rung materialization once the four smallest qualifying nested sizes are proven, with exhaustive-v1 decision-equivalence qualification.
5. `PERF-P3` - harden CPU structural/reduction execution through direct per-frame numerical kernels, topology-static caches, worker-local scratch, FoundationTargetAudit memory reduction, and unified stage-local resource scopes. Existing shared species-pair MIC work is preserved rather than redundantly reimplemented.
6. `VRAM1 + PERF-P4` - correct DATA6 capacity evidence to derivative-bearing workload-aware v2, clean/re-clamp CUDA memory, preserve explicit headroom, persist OOM-safe caps, and overlap bounded CPU graph construction, GPU inference, and CPU persistence.
7. `E3NN-BASELINE` - execute and freeze one complete optimized MACE-MH-1 / `omat_pbe` / e3nn control campaign.
8. `PERF-P5` - late TRAIN2/EVAL2 persistence/reuse hardening: streamed tensor hashing, restart-state deduplication only if exact interrupted-training restoration is proven, optional same-architecture EVAL2 model-shell hot swapping, and remaining native-array/streaming assembly. Stock MACE 0.3.16 HDF5/LMDB is explicitly not treated as a precomputed graph cache.
9. `CUEQ-DEP1` - freeze the exact accelerator runtime/dependency/GPU identity.
10. `CUEQ-PHASE1` - qualify pure-CuEq training only from the EXTRACT1-derived single-head foundation while source inference remains original MH-1/e3nn.
11. `CUEQ-PHASE2` - optional later qualification of the derived single-head CuEq realization for source-execution/DATA6 acceleration.
12. `PERF-CERT1` - certify end-to-end scientific decisions and operational performance before any generated-default policy change.

Every optimization is classified as Class E (execution-equivalent), Class S (storage/schema-equivalent), or Class A (authority-algorithm revision with proven decision equivalence). Approximate kNN/FPS, reference subsampling, reduced reference mass, sparse replacement of the existing dense structural feature definition, parity-tolerance relaxation, and stock MACE HDF5/LMDB represented as a graph cache are explicit non-goals.
