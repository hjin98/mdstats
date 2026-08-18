# Part VII - Current implementation status and frozen forward gates

## Current authority snapshot

The current campaign architecture retains the scientific contracts established by DATA1-DATA9, conventional nested CV, target/replay evaluation, MACE adapter/version locks, deployment verification, TARGET-DATA2 multi-view selection, and FINAL-GPU1 deferral. Revision 99 completes `MVQUAL-PAR1`: independent same-N domain/selector/size qualification jobs are globally scheduled under PARCORE1 while every TARGET-DATA2B report, MVIDX cross-check, hard-obligation decision, comparison order, and persisted MVQUAL record remains unchanged.

The most recent implemented performance gates are:

- **COVREF-PAR1 (`0.20.229a0`)** - TARGET-DATA2B exact reference-radius construction on one single-level global block queue with adaptive cache-sized tasks, O(1) pair/species adapters, and unchanged radius/reference authority.
- **MVKERNEL1 (`0.20.230a0`)** - exact ragged-CSR/vector telemetry kernels around the unchanged sequential MVSEL rank authority.
- **REPAIR-PAR1 (`0.20.231a0`)** - vectorized immutable repair proposals with adaptive deterministic proposal parallelism and unchanged sequential repair winner authority.
- **MVQUAL-PAR1 (`0.20.232a0`)** - global deterministic same-N scoring queue with one native numerical lane/job and canonical post-queue comparison reduction.

`PERFBASE1` (`0.20.225a0`) remains the frozen measurement authority used to judge subsequent optimization gates. `TARGET-DATA2B-FEAS1-PERF3` (`0.20.223a0`) is the direct predecessor scheduler whose successful global single-level execution pattern PARCORE1 generalizes.

The multi-view scientific gates FEAS1, MVIDX1, MVSEL1, REPAIR1, MVPERF1, MVQUAL1, SIZE-HALVE2, SIZE-FIDELITY2, and MVMIGRATE1 remain the governing target-data design. The new optimization gates below are exact-equivalence execution work layered on top of those authorities.

## Frozen campaign optimization sequence

### Gate PERFBASE1 - reproducible performance baselines - COMPLETE

**Purpose.** Freeze representative supplied-data and synthetic workloads before broad optimization.

**Implementation.** `0.20.225a0` adds the foundation-generic `PerfBase1Record`/workload/trial schemas, stage meters, deterministic benchmark harness, exact output-drift rejection, and Markdown/JSON evidence rendering. Requested and actually allocated workers are recorded separately so current serial stages are not misreported as parallel.

**Record.** The canonical MPA-0 CPU authority is stored as the PERFBASE1 JSON record and Markdown report under `benchmarks/`. It authenticates the supplied 27-file target archive, fixed representative target-family cache, unified 12,000-frame replay source, dependencies, active foundation checkpoint, and benchmark implementation manifest. It records wall/CPU time, assigned-lane occupancy, RSS, throughput, worker settings, queue telemetry where available, and exact scientific-output digests. The schema is not MPA-0-specific and can bind an MH-1 checkpoint unchanged.

**Observed baseline.** On the cgroup-limited cloud CPU (automatic budget three lanes), FEAS1 median wall time changes from about 1.78 s at one worker to 0.85 s at three workers, while current MVIDX1 changes from about 2.17 s to 2.40 s and occupancy falls from about 1.02 to 0.33. TARGET-DATA2B reference radii improve from about 0.61 s to 0.42 s. MVSEL rank authority and replay ExtXYZ ingest correctly remain single-lane baselines.

**Acceptance. PASS.** Every repeated schedule preserves the workload scientific-output digest exactly; inputs are SHA/content-addressed; repeated wall-time CV is low enough for implementation comparison on all but the sub-second three-lane radius probe, which remains usable as a coarse scaling indicator. Foundation Audit/EVAL2 model-inference baselines are explicitly unavailable on this cloud environment rather than fabricated.

**Succeeded by.** `PARCORE1` in `0.20.226a0`.

### Gate PARCORE1 - shared deterministic CPU scheduler - COMPLETE

**Purpose.** Replace repeated bespoke executors with one bounded, resource-aware, deterministic work substrate.

**Implementation.** `0.20.226a0` adds `DeterministicWorkQueue`, `DeterministicWorkItem`, `DeterministicWorkCompletion`, queue snapshots, task-identity errors, and `DeterministicOrderedReducer`. `StageResourceScope` now carries the stage RAM budget as well as CPU/native-thread limits. Ready, submitted/in-flight, and completed work are independently bounded; persistent memory can be reserved/released explicitly; queue and memory backpressure are counted; heartbeat snapshots expose executor state. Task locality metadata is retained for later NUMA work without activating NUMA affinity. FEAS1 is migrated from its private `ThreadPoolExecutor` coordinator to the shared queue while preserving its canonical per-profile witness reduction.

**Resource ownership.** Campaign FEAS1 passes the explicit stage scope to the queue, which applies BLAS/OpenMP quarantine once at queue scope; cKDTree remains one native worker/task while outer work can fill the budget. Direct API callers that omit a scope keep the pre-PARCORE resource-control behavior. The queue may submit up to twice the executing-lane count to hide coordinator hand-off latency, but simultaneous executing lanes remain exactly bounded by `python_workers`.

**Acceptance. PASS.** All queue contract tests pass, FEAS1 scientific output retains the exact PERFBASE1 digest (SHA-256 prefix `937214c70d1f2baa`, full value in the canonical qualification record) across worker schedules, and all three automatic-budget lanes are observed active without nested oversubscription. In the final paired same-host two-repeat comparison, PARCORE1 records a three-worker median of about 0.83 s versus about 0.94 s for the untouched `0.20.225a0` implementation; assigned-lane occupancy is about 0.66 versus 0.64. The PARCORE1 full-budget result is also consistent with the frozen PERFBASE1 median of about 0.85 s. Serial, dual, and bounded-intermediate paired medians are likewise non-regressive in the final pair. Timing is treated as execution evidence rather than scientific authority; the exact digest is the gate invariant.

**Succeeded by.** `NEIGHBOR1` in `0.20.227a0`.

### Gate NEIGHBOR1 - shared FEAS1/MVIDX exact-neighborhood engine - COMPLETE

**Purpose.** Compute exact feature-family neighborhoods once and reuse them.

**Implementation.** `0.20.227a0` adds the shared exact-neighborhood engine and content-addressed forward-neighborhood store. FEAS1 emits streamed canonical witness CSR while preserving its historical support/capacity reduction order; ragged cKDTree results are compressed at the worker boundary and discarded after canonical commit. Worker count, query-block size, and queue settings are execution-only and excluded from cache identity. Native-array persistence authenticates manifests/arrays and campaign restart validates the cache independently. The exact final CSR allocation is RAM-admitted before materialization. MVIDX1 consumes authenticated forward CSR directly; its source no longer contains cKDTree/query-ball geometry. Cache miss/staleness rebuilds once through the same global exact engine. The existing CSR-to-CSC inversion remains unchanged.

**Acceptance. PASS.** On the PERFBASE1 synthetic authority (6 families, 49,152 witnesses, 3,194,880 exact edges), FEAS1, the NEIGHBOR1 cache, and cached/rebuilt MVIDX1 remain digest-identical across worker/block settings. Their SHA-256 values begin `937214c70d1f`, `0220c89084fe`, and `e408bd25dcc9`; the complete values are frozen in the gate qualification record. A cache-hit regression test replaces the geometric query method with a fail-fast sentinel and still passes, proving zero second geometric queries. Native-array round trip/tamper tests pass. On the cgroup-limited three-lane cloud CPU, final two-repeat medians reduce FEAS1->MVIDX1 wall time from about 2.77 s in untouched `0.20.226a0` to about 1.03 s with NEIGHBOR1 (about 2.68x end-to-end); one-worker total improves from about 2.20 s to about 1.28 s. Timing is execution evidence only; digest equality is the authority.

**Succeeded by.** `MVIDX-REUSE1` in `0.20.228a0`.

### Gate MVIDX-REUSE1 - stable parallel sparse inversion - COMPLETE

**Purpose.** Reduce MVIDX to authenticated graph adoption, deterministic CSR-to-CSC inversion, and obligation metadata.

**Implementation.** `0.20.228a0` schedules independent required-family inverse builds and hard-obligation inversion through `DeterministicWorkQueue` under one `StageResourceScope`. Each individual transpose uses the deterministic compiled SciPy counting transpose with one native lane; canonical family order is restored after arbitrary task completion, so no atomics or nested sparse-kernel threads are required. The measured row-by-row sorted/unique validator is replaced by one vectorized adjacent-index comparison with CSR-boundary masking. The originally sketched Python-threaded intra-family degree/prefix/range fill was implemented experimentally and rejected because it was slower than the compiled kernel on the frozen workload.

**Acceptance. PASS.** The frozen MVIDX digest (SHA-256 prefix `e408bd25dcc9`; full value in the qualification record) is unchanged across one-, two-, and three-lane schedules, with byte-identical candidate offsets and candidate-to-witness arrays. On the same cgroup-limited cloud CPU, untouched `0.20.227a0` cached MVIDX measured about 0.59 s median, while revision 95 measured about 0.16 s at one lane, 0.12 s at two lanes, and 0.087 s at three lanes; the final paired three-lane gain is about 6.8x. Timing is execution evidence only; sparse-array/digest equality is scientific authority.

**Next gate.** `COVREF-PAR1`.

### Gate COVREF-PAR1 - TARGET-DATA2B exact CPU parallelization - COMPLETE

**Purpose.** Remove the remaining one-driver cKDTree pattern from reference-radius/coverage construction.

**Implementation.** `0.20.229a0` routes exact local-radius row blocks through the stage-wide `DeterministicWorkQueue`, with one native cKDTree worker/task and one shared read-only tree/scaled matrix per family. Execution-only adaptive row sizing caps the historical block size by an approximately 2 MiB query-temporary target and a minimum task-count rule, preventing long tails on high-core-count hosts. Pair-rule and foundation-species adapters use O(1) maps, and target-label scalar channels apply their exact historical constant-family rejection before expensive statistics/tree work. Direct API calls without an execution scope retain the historical native-tree implementation for qualification/backward compatibility.

**Acceptance. PASS.** The frozen PERFBASE1 supplied-data radius digest remains exactly `823a2c0c2f8a...6d96e52cd642e2d` across 1/2/3 outer lanes. In the final same-host four-repeat supplied-cache comparison, untouched `0.20.228a0` measures about 0.279 s median at three native cKDTree workers and `0.20.229a0` measures about 0.223 s at three outer lanes (about 1.25x faster); all three outer lanes are observed active. The frozen PERFBASE1 three-lane baseline was about 0.42 s, illustrating host-load variability and why paired controls are retained. A separate 36,408-row nonuniform equal-unit/equal-frame two-repeat stress family preserves byte-identical radii and improves from about 5.94 s to about 5.13 s (about 1.16x). One-lane queue execution is essentially neutral/slightly slower on the small cache, so the gate does not claim a serial speedup. The exact scientific/reference arrays, not wall time, are the gate authority; nested native-tree parallelism is rejected.

**Next gate.** `MVKERNEL1`.

### Gate MVKERNEL1 - sparse selector/qualification vector kernels - COMPLETE

**Purpose.** Reduce Python overhead in MVSEL/MVQUAL without altering sequential rank decisions.

**Implementation.** `0.20.230a0` adds shared exact ragged-CSR gather kernels and routes MVSEL inverse-edge updates through them. Per-family and domain-total gain arrays share one gathered edge stream, while `np.add.at` is still applied independently in canonical witness/edge order so floating-point state remains exact. Coverage and representative witness amounts are vectorized, and required hard-obligation pending count is maintained incrementally. MVIDX selected-subset coverage and obligation helpers gather candidate CSR rows once and use boolean assignment/`bincount`. MVQUAL gathers selected candidate rows once per family to derive multiplicity, covered/unique witness masks, and unique-owner candidates; DATA2A run/condition provenance codes are built once per domain. The scalar MVSEL update and scalar MVQUAL telemetry implementations are retained as qualification references.

**Acceptance. PASS.** Optimized and scalar MVSEL states agree exactly after every qualified rank and persisted selection plans remain byte-identical. The frozen 4,096-candidate/2,048-selection digest remains `d147d85acd64...b2ffaddbb978b378`; the 24,576-candidate/16,384-selection stress digest remains `aaec42fb0c1d...9a0461bcd75d608`. Same-host measurements reduce the representative selector median from about 1.404 s in untouched `0.20.229a0` to about 0.811 s, and the 16,384-selection stress path from about 6.640 s to about 5.591 s. A 16,384-candidate/8,192-selected/6-family MVQUAL telemetry fixture drops from about 0.578 s to about 0.041 s (about 14.1x), with byte-identical telemetry. Full MVQUAL plan evidence remains digest-identical to untouched `0.20.229a0`. Timing is execution evidence; exact selector state and qualification records are authority.

**Next gate.** `REPAIR-PAR1`.

### Gate REPAIR-PAR1 - deterministic parallel repair proposals - COMPLETE

**Purpose.** Reduce REPAIR1 proposal cost without changing the sequential repair iteration, swap objective, tie hierarchy, accepted/rejected trace, or winner application.

**Implementation.** `0.20.231a0` fuses removal unique-coverage and representative-loss scans, scores complete replacement frontiers with shared ragged-CSR gathers, and replaces repeated set intersections with thread-private epoch/stamp witness membership. A candidate-to-rank inverse map makes future displacement lookup O(1). Immutable removal proposals may run through the PARCORE1 deterministic queue; each task owns private stamp scratch, native numerical layers remain single-threaded, and results are canonically reduced in the historical removal-shortlist order. Parallel dispatch is adaptive: proposal batches below an execution-only sparse-edge threshold remain serial because qualification showed that blindly threading the historical Python loops is slower. The winning pair's representative contribution is recomputed with the historical scalar/stamp arithmetic before the swap is persisted. `execution_mode="reference"` retains the historical scalar proposal oracle.

**Acceptance. PASS.** The complete serialized repair plan/trace on the frozen REPAIR1 fixture is identical for the scalar reference and optimized 1/2/4-worker realizations, digest `5dcb048b02ae...b265a52615b9545b`. A 2,048-candidate proposal fixture preserves result digest `1a09e7745aa5...244421e4b859a9b1` and improves from about 3.176 s in untouched `0.20.230a0` to about 0.119 s (about 26.6x); adaptive execution correctly keeps it serial. An 8,192-candidate sparse fixture preserves result digest `9fda146806fc...10c468b41994` and improves from about 3.130 s to about 0.830/0.611/0.461 s at 1/2/4 lanes: about 3.77x from vectorization alone, 6.79x end-to-end at four lanes, and 1.80x additional 1-to-4-lane scaling. Timing is execution evidence; the complete repair trace and terminal order are scientific authority.

**Next gate.** `MVQUAL-PAR1`.

### Gate MVQUAL-PAR1 - global same-N scoring queue - COMPLETE

**Purpose.** Execute independent domain/selector/size rescoring concurrently without changing any same-N qualification authority.

**Implementation.** `0.20.232a0` freezes one execution-only job for every materializable `(domain, selector, target size)` score. A job performs the existing immutable TARGET-DATA2B rescore, MVKERNEL1 batched sparse telemetry, hard-obligation state, and MVIDX covered-mass cross-check. Large job sets execute through the PARCORE1 `DeterministicWorkQueue`; completion order is arbitrary, but comparisons and progress messages are reconstructed afterward in the historical domain/size order. Campaign jobs force cKDTree and BLAS/OpenMP to one native lane each, preventing nested oversubscription. Per-job temporary-memory estimates participate in queue admission. Automatic campaign mode is capped at four outer score lanes because qualification shows these jobs become memory-bandwidth limited; an explicit larger override remains available for qualified high-bandwidth hosts. Direct API calls without an explicit `StageResourceScope` deliberately do not alter the process native-thread environment. This preserves historical direct-API behavior while campaign execution retains its pre-gate BLAS=1 scientific authority; qualification caught that changing only BLAS thread count can shift the Wasserstein diagnostic by about 1e-16 and therefore change a cryptographic report digest.

**Acceptance. PASS.** Scalar/direct and 1/2/4-worker realizations preserve complete qualification-plan dictionaries under their respective historical native-thread contract. Under the production BLAS=1 contract, untouched `0.20.231a0` and MVQUAL-PAR1 preserve the same plan digest `2ebd7f5dc2b5...befda74059fc90b` on a 16,000-reference, six-size, 12-job same-N fixture. Same-host warm medians are about 0.866 s for the old serial driver with four native cKDTree workers and about 0.409 s for four outer MVQUAL lanes with one native tree worker/job (about 2.12x faster). The new path measures about 0.828/0.451/0.458 s at 1/2/4 outer lanes; all four lanes are observed active and all 12 jobs complete without queue or memory backpressure on the fixture. Timing is execution evidence; exact qualification records and digests remain scientific authority.

**Next gate.** `AUDIT-EVAL-PERF1`.

### Gate AUDIT-EVAL-PERF1 - Foundation Audit and EVAL2 CPU hardening - COMPLETE

**Purpose.** Remove repeated Python frame/species/statistics loops surrounding already optimized model inference without changing any prediction, checkpoint-selection, or GPU numerical authority.

**Implementation.** `0.20.233a0` adds an execution-only EVAL2 static-reduction cache keyed by the immutable evaluation-view object and ordered correlation-block IDs. It precomputes composition keys, per-frame species membership, focus masks, and compact block codes once, then reuses them across checkpoint reductions. Force-tail vector storage is preallocated rather than accumulated as ragged per-frame arrays and concatenated. Paired block bootstrap preserves the exact seeded NumPy RNG stream but draws in bounded vector batches sized from a 32 MiB temporary target, eliminating the 2,000-replicate Python loop without unbounded allocation. FOUNDATION-AUDIT1 now builds the DATA3 frame-array index once for the whole audit, shares immutable per-run species membership across audit domains, reuses `delta*delta` work for total/species reductions, and evaluates all configured force-tail quantiles in one call. Prediction-manifest authentication and conditioned-feature semantics are unchanged; no new model inference is introduced.

**Acceptance. PASS.** On a 4,096-frame / 294,912-atom repeated EVAL2 fixture, untouched `0.20.232a0` and `0.20.233a0` preserve exact metric digest `d9dd9db2c2d4...9d3f15762d434658`; same-host median reduction time improves from about 0.862 s to 0.449 s (about 1.92x). On a 768-block, 2,000-replicate paired bootstrap, the exact comparison digest `9664354fd2d8...14acb729590397e` is preserved while median time improves from about 0.0512 s to 0.0152 s (about 3.36x). The available no-inference FOUNDATION-AUDIT1 fixture preserves audit digest `39b8b207c741...61ba87b0e8c94e5`, keeps model-provider descriptor/prediction call counts fixed at 44/44, and improves median audit reduction from about 0.0580 s to 0.0545 s (about 1.06x). Timing is execution evidence; persisted metric/audit/bootstrap records remain scientific authority.

**Next gate.** `REPLAY-PERF1`.

### Gate REPLAY-PERF1 - replay index/cache and chunk materialization - COMPLETE

**Purpose.** Avoid repeated serial parsing of the immutable replay corpus without changing REPLAY-UNIFY1 source, label, split, prediction, or retention authority.

**Implementation.** `0.20.234a0` adds `ReplaySourceIndex`, a reconstructible execution artifact bound to the exact source SHA-256, source-artifact digest, source-order geometry digest, byte size, frame offsets/lengths, and atom counts. The cache is stored beneath the campaign replay-internal tree, is independently authenticated on reuse, relocates without scientific change when identical source bytes move, and is rebuilt automatically on source mutation or receipt corruption. Indexed readers seek only requested source indices; contiguous requested frames are parsed in bounded chunks, while sparse monitor reconstruction does not scan unrelated frames. True-label materialization, pseudo-label materialization, and foundation-prediction cache construction reuse the authenticated source-order geometry identity instead of recomputing canonical geometry hashes after parsing. ExtXYZ parsing itself remains single-threaded: measured Python-threaded ASE parsing was slower, so REPLAY-PERF1 does not introduce a misleading parser thread pool.

**Acceptance. PASS.** On the supplied 12,000-frame replay corpus (`187eed42...98403c`), the persisted index has content digest `ce6c678a...c0c5e1`; first byte-index construction is about 0.45 s and an authenticated restart hit about 0.07 s on the qualification host. Monitor-only true-label reconstruction preserves logical digest `633aae8a...bf1114` and exact ExtXYZ SHA-256 `cc0f9b30...eab2cf` while improving median wall time from about 9.14 s to 3.01 s (~3.03x). A complete parse/geometry-identity pass preserves the ordered-identity digest while improving from about 7.64 s to 6.42 s (~1.19x). Full train+monitor materialization preserves byte-identical train and monitor files and improves more modestly from about 15.68 s to 14.35 s (~1.09x), as expected because every frame must still be parsed and written. Cache corruption and source mutation are fail-safe reconstruction events, and chunk size does not enter scientific identity.

**Next gate.** `CAMPAIGN-PERF-QUAL1`.

### Gate CAMPAIGN-PERF-QUAL1 - end-to-end optimization closure - COMPLETE

**Purpose.** Reprofile the accumulated CPU optimization program as an integrated campaign rather than summing isolated microbenchmarks, while preserving all scientific and GPU numerical authority.

**Implementation.** `0.20.235a0` is a measurement/documentation release: runtime scientific algorithms are unchanged from `0.20.234a0`. The closure runs a common 8,192-candidate/six-family FEAS1 -> NEIGHBOR1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVQUAL1 chain against an untouched `0.20.225a0` PERFBASE1-era control, rechecks the supplied 12,000-frame replay restart path, and reproduces EVAL2/bootstrap and Foundation Audit CPU records. Exact output digests, restart/cache identities, worker scaling, process CPU, and peak RSS are recorded in `benchmarks/mlff_campaign_perf_qual1_cloud_cpu_mpa0_2026-08-17.json`.

**Acceptance. PASS, FOLLOW-UP REQUIRED.** The integrated target-data chain improves from about 27.26 s to a four-lane median of about 11.95 s (~2.28x) with exact FEAS1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 scientific digests. The current one/two/four-lane chain is about 12.91/12.07/11.95 s, showing that the remaining tail is no longer parallel-starved. Peak RSS rises from about 306 MiB to about 343 MiB because authenticated sparse execution state is retained, but remains far below the campaign memory ceiling with no observed backpressure. Replay monitor reconstruction reproduces exact bytes with an authenticated index hit near 0.07 s; EVAL2 and paired-bootstrap closure reruns reproduce their frozen digests. Reprofiling shows MVSEL exact sparse state mutation consumes most selector time, while REPAIR performs approximately 4,098 additional `_select_and_update` calls to reconstruct the already-computed selected-order state and spends several seconds on that replay before/around proposal scoring. This is duplicated reconstructible execution work, so total CPU optimization closure is deferred one targeted gate.

**Next gate.** `MVSTATE-REUSE1`.

### Gate MVSTATE-REUSE1 - selector-to-repair sparse-state reuse - COMPLETE

**Purpose.** Remove duplicated selector-state reconstruction inside REPAIR while preserving every selector rank, target rung, repair objective/tie decision, swap, terminal order, and MVQUAL record.

**Implementation.** `0.20.236a0` adds authenticated exact MVSEL state checkpoints at each materializable rung and a native bundled-array store. REPAIR restores a checkpoint only before its first accepted repair swap; after repair diverges, it carries the historical mutable state forward. Pure checkpoint reconciliation after divergence was measured and rejected because it changed FP64 representative-gain entries at roughly `1e-17`--`1e-16`. Bounded post-divergence CSR gather batching changes preparation only; all state mutations remain candidate-major in the historical arithmetic order. Fresh campaign execution passes the just-built cache directly from MVSEL to REPAIR while persisting it for restart. Invalid cache state fails safely to exact replay.

**Acceptance. PASS; CPU OPTIMIZATION CLOSED.** On the common 8,192-candidate/six-family fixture, the untouched 0.20.235a0 chain median is about 12.00 s. MVSTATE-REUSE1 is about 11.02 s excluding persistence and about 11.19 s including the one-time cache write (~1.07x fresh-chain speedup); REPAIR improves about 5.37 s -> 4.27 s (~1.26x). All FEAS1/NEIGHBOR1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 digests remain exact, cache restart/tamper/stale-lineage behavior is qualified, and peak RSS remains within budget. Relative to the PERFBASE1-era 27.26 s chain, the fresh accumulated CPU realization is about 2.44x faster. The residual tail is exact sequential sparse-state arithmetic rather than another material duplicate execution artifact.


`0.20.238a0` hardens the already-complete MVIDX-REUSE1 execution path for production caches containing billions of exact NEIGHBOR1 edges. Large inversions are now file-backed and chunked under explicit RAM admission, with exact byte-equivalence to the in-memory transpose. This is an execution/storage maintenance adaptation under revision 103 and does not reopen the CPU optimization gate sequence.

**Next gate.** `FINAL-GPU1` workstation qualification.

## Explicit non-goals

The optimization program does not authorize approximate neighborhood search, approximate coverage, learned subset selectors, GPU graph authority, relaxed 0.95 coverage, larger-than-16,384 rescue, altered CV leakage boundaries, or new locked-test tuning. GPU qualification remains consolidated at the final release boundary.

## Documentation and lineage rule

Current scientific/execution contracts belong in this manual or module specifications. Revision comments and release deltas belong only in `docs/history/mlff/`. A historical note may explain why a decision changed, but it may not override the current manual. Every future architecture revision SHALL update the history index and this manual's current-state section rather than prepending another revision block to the document.
