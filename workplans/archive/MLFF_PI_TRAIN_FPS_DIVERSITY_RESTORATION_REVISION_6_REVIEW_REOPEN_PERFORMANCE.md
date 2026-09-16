# Revision-6 workplan review reopen — performance capability-transfer blocker

Date: 2026-09-15
Reviewed plan: Revision-5 body + Revision-6 closure
Disposition: **NO PASS — REOPENED**

## Finding

Revision 6 closes correctness-oracle, persistence, packaging and artifact-lifecycle gaps, but it does not make the complete mature execution-performance architecture surrounding the restored selector a mandatory capability-transfer target. Its native/OpenMP language permits a conforming implementation to restore the scientific chain with only an exact serial/fallback realization, even though the exact pre-P6 lineage contained accepted production optimizations and deterministic parallel machinery whose deletion was collateral to P6.

This is a material D3/D4 workplan gap. A functionally exact but product-inadequate serial restoration would satisfy the existing wording while failing to restore the demonstrated operational capability that made the latest MVSEL2 generation production-usable.

## Historical evidence requiring transfer

The exact recovery lineage establishes the following accepted capabilities before P6 deletion:

- shared affinity/cgroup-aware CPU budget with production `cpu_fraction=0.90` and nested-parallelism control;
- `DeterministicWorkQueue` bounded/backpressured deterministic outer scheduling;
- exact parallel/optimized TargetCoverageReference/FEAS1 work under one resource scope;
- exact NEIGHBOR1/MVIDX construction with file-backed/out-of-core arrays, bounded queues/backpressure and RAM admission;
- sparse/vector exact kernels;
- one production MVSEL2 rank loop with locality-oriented Phase-A kernel;
- cached-witness, certified-lazy Phase-B kernel and memory-bounded family-major rebase;
- private bitwise-qualified native/OpenMP candidate-row reducer with real-MVIDX dynamic preflight and exact serial fallback;
- MVSTATE2 + authenticated rank-history restart without rescoring the selected prefix;
- REPAIR2 state-invariant frontier factorization, checkpoint-assisted pre-divergence continuation, and deterministic parallel proposal evaluation with serial winner/mutation authority;
- bounded/progressive sparse MVQUAL with deterministic family/rung work scheduling;
- clean native source/editable/wheel build qualification;
- progress/resource telemetry sufficient to diagnose scaling and fallback.

P6 implementation evidence explicitly records deletion of the relevant modules, including `work_queue`, `_mvsel2_native.c`, `_sparse_vector_kernels`, `_target_coverage_neighborhood`, `_target_multi_view_scoring`, MVIDX stores/views, `mvsel2_phase_a_kernel`, `mvsel2_phase_b_kernel`, `mvsel2_selection_engine`, `mvsel2_streaming_frontier`, `mvsel2_native_backend`, `mvsel2_native_preflight`, repair/checkpoint runtimes and parallel MVQUAL runtime.

## Known rejected machinery that must stay rejected

Restoration must not confuse “restore performance” with “restore every experiment.” Historical evidence rejects or supersedes:

- the failed Python fine-grained/candidate-thread MVSEL2 PAR1 path;
- eager inverse candidate-marginal propagation and MVSEL1 execution;
- aggressive mmap release/refault policies G4c/G4d that reduced residency but regressed throughput/I/O;
- MVQUAL P1 direct progressive TARGET-DATA2B reuse, which lengthened the product critical path;
- fixed 4/8/16/28 host-specific automatic worker ceilings and reuse of cKDTree worker policy as unrelated-stage CPU authority;
- independent nested pools that each claim the global CPU fraction.

## Required repair

A new Revision 7 must:

1. bind the exact performance lineage and accepted/rejected mechanisms into the historical applicability/capability-transfer map;
2. require restoration/rebinding of all current-compatible accepted optimization and parallelization capabilities, not merely permit them;
3. reuse the current surviving `SystemResourceSnapshot` / `StageResourceScope` owner and restore the deleted deterministic work-queue capability rather than add a new scheduler;
4. define exact stage-by-stage parallel boundaries for coverage/FEAS, MVIDX, MVSEL2, REPAIR2 and MVQUAL;
5. preserve exact scientific decisions under worker count/backend/chunk/queue/restart variation;
6. restore the package-wide native build/qualification route for retained compiled kernels;
7. define current representative-scale throughput/RAM/I/O/restart acceptance and matched historical/reference comparators;
8. keep final production-scale GPU qualification deferred.

Until that amendment passes independent review, Revision 6 is **NO PASS AS WORKPLAN**.