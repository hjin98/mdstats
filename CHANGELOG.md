## 0.20.240a0 - 2026-08-18

- Fix MVIDX-REUSE1 producer-side PARCORE1 backpressure for domains whose required-family count exceeds the bounded ready queue (production incident: 165 families with 56 ready slots at 28 inverse workers).
- Replace eager family submission with deterministic submit/drain/refill scheduling; bounded queue sizes, RAM admission, canonical completion reduction, out-of-core inverse storage, and all scientific digests remain unchanged.
- Add a forced one-slot ready-queue regression over a production-style 17-family TARGET-DATA2B reference, which would fail under the previous eager-submission loop and now reproduces the exact MVIDX digest.
- Retain the 0.20.239a0 Python-3.11 syntax hotfix and 0.20.238a0 multi-billion-edge out-of-core MVIDX hardening. Architecture revision 103 / schema 83 remain unchanged; `FINAL-GPU1` remains next.

## 0.20.239a0 - 2026-08-17

- Correct a Python 3.11 syntax incompatibility introduced in the DATA6 progress-format line: a multiline function call was embedded directly inside an f-string expression.
- Precompute the canonical timing-field string before interpolation; progress output and scientific behavior are unchanged.
- Add whole-tree Python 3.11 grammar qualification for MLFF campaign sources so a package cannot be released with syntax accepted only by Python 3.12+ f-string grammar.
- Keep architecture revision 103 and dependency schema 83 unchanged; MVIDX out-of-core hardening from 0.20.238a0 is retained and FINAL-GPU1 remains next.

## 0.20.238a0 - 2026-08-17

- Harden TARGET-DATA2C MVIDX for multi-billion-edge NEIGHBOR1 caches with an exact out-of-core CSR-to-CSC inversion path. Large inverse edge arrays are written directly as NPY memmaps with bounded chunk scratch instead of requiring the complete inverse plus SciPy transpose workspace in anonymous RAM.
- Make MVIDX queue admission account for bounded out-of-core scratch rather than full-family edge payload when file-backed inversion is active; explicit campaign RAM ceilings remain fail-closed.
- Hard-link whole mmap-backed NPY arrays into the authenticated MVIDX native store when source and destination share a filesystem, avoiding duplicate tens-of-GiB copies.
- Add a disk-space preflight for the inverse payload and periodic canonical MVIDX progress heartbeats with HH:MM:SS elapsed/ETA.
- Preserve the exact TARGET-DATA2C scientific authority: in-memory and out-of-core inverse arrays are byte-identical and all prior TARGET-DATA2 scientific tests remain unchanged.

## 0.20.237a0 - 2026-08-17

- Standardize MLFF progress and heartbeat presentation across campaign stages without changing scientific or execution authority.
- Use fixed-width `HH:MM:SS` for every elapsed/ETA field; unresolved ETA is always `--:--:--`.
- Normalize periodic messages to the common field order `status`, `progress`, `elapsed`, `eta`, rates, then stage-specific telemetry, with semicolon-delimited fields.
- Normalize frame/witness/task counters, phase messages, DATA6 model-sweep reporting, TARGET-DATA2B/FEAS1/NEIGHBOR1/MVIDX/MVSEL/REPAIR/MVQUAL callbacks, adaptive inference/evaluation schedulers, and TRAIN heartbeats.
- Keep MLFF architecture revision 103 and dependency schema 83 unchanged; this is presentation-only maintenance and `FINAL-GPU1` remains the next release gate.

## 0.20.236a0 - 2026-08-17

- Complete MVSTATE-REUSE1 / architecture revision 103 and close the exact-equivalence CPU optimization program.
- Persist authenticated exact MVSEL rung-state checkpoints and pass them directly to REPAIR on fresh campaign execution while retaining exact replay as the fallback/oracle.
- Reject post-divergence checkpoint reconciliation because it perturbs FP64 representative-gain state; carry historical repair state after the first accepted swap.
- Bundle the ~7 MiB state artifact in one authenticated NPZ, reducing observed write cost from the exploratory per-array realization to about 0.18 s median.
- On the common 8,192-candidate closure fixture, reduce REPAIR from about 5.37 s to 4.27 s and fresh integrated target-chain time from about 12.00 s to 11.19 s including cache persistence, with exact scientific digests.
- Close CPU optimization at about 2.44x cumulative fresh-chain speedup versus PERFBASE1-era 0.20.225a0; next gate is FINAL-GPU1.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving MACE-MH-1 compatibility.

## 0.20.235a0 - 2026-08-17

- Complete CAMPAIGN-PERF-QUAL1 / architecture revision 102 as the integrated exact-equivalence CPU optimization closure review; runtime scientific algorithms remain unchanged from 0.20.234a0.
- On a common 8,192-candidate/six-family target-data chain, preserve exact FEAS1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 authority while reducing wall time from about 27.26 s in the PERFBASE1-era 0.20.225a0 control to about 11.95 s at four lanes (~2.28x).
- Requalify replay indexed restart, EVAL2/bootstrap, Foundation Audit, worker scaling, and representative memory behavior.
- Reprofile the shifted target-data tail and identify duplicated MVSEL sparse-state reconstruction inside REPAIR as the dominant exact-reuse opportunity.
- Keep the CPU optimization program open for MVSTATE-REUSE1 rather than falsely declaring total closure; final GPU qualification remains deferred.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic MACE-MH-1 compatibility.

## 0.20.234a0 - 2026-08-17

- Implement REPLAY-PERF1 / architecture revision 101 as exact replay-source indexing and indexed materialization over the unified immutable replay corpus.
- Add the source-SHA-bound `ReplaySourceIndex` byte-offset/natoms cache with authenticated reuse, relocation-safe locator rebinding, corruption rebuild, and explicit invalidation on source mutation.
- Route true-label views, pseudo-label views, and foundation-prediction source iteration through deterministic indexed parsing; sparse role reconstruction seeks only requested frames and all indexed paths reuse authenticated source-order geometry identities.
- Keep ASE ExtXYZ parsing serial after direct qualification showed threaded parser chunks regress wall time on this host.
- On the supplied 12,000-frame replay source, reduce monitor-only true-label reconstruction from about 9.14 s to 3.01 s (~3.03x) with byte-identical output; full-source parse/identity improves ~1.19x and full train+monitor materialization ~1.09x.
- Preserve the REPLAY-UNIFY1 5:1 split, true-label/pseudo-label authority, cached foundation predictions, active MACE-MPA-0 qualification, and model-generic MACE-MH-1 compatibility; next gate is CAMPAIGN-PERF-QUAL1.

## 0.20.233a0 - 2026-08-17

- Implement AUDIT-EVAL-PERF1 / architecture revision 100 as exact CPU hardening around already materialized Foundation Audit and EVAL2 predictions.
- Cache immutable EVAL2 composition/species/focus/block reduction metadata, preallocate force-tail storage, and batch paired bootstrap draws under a 32 MiB temporary target while preserving the exact seeded RNG stream.
- Share FOUNDATION-AUDIT1 frame/species indexing across domains, reuse force-square work, and batch configured tail quantiles without adding model inference.
- Preserve exact qualification metric digest `d9dd9db2c2d47e2d6f034e0b58f094c04c516d5a0dc4f0089d3f15762d434658`, bootstrap digest `9664354fd2d871e67113ff5b9ef28118c9414a59f29a5fd4114acb729590397e`, and foundation-audit digest `39b8b207c741798f5a8555b41ceb0c746948935612d84d45961ba87b0e8c94e5`.
- Same-host medians improve from about 0.862 to 0.449 s for repeated EVAL2 target reduction (~1.92x), 0.0512 to 0.0152 s for the paired bootstrap (~3.36x), and 0.0580 to 0.0545 s for the available no-inference Foundation Audit fixture (~1.06x).
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic MACE-MH-1 compatibility; next optimization gate is REPLAY-PERF1.

## 0.20.232a0 - 2026-08-17

- Implement MVQUAL-PAR1 / architecture revision 99 as a global deterministic queue over independent domain/selector/target-size same-N qualification jobs.
- Preserve TARGET-DATA2B independent rescoring, MVIDX mass cross-checks, hard-obligation authority, canonical domain/size reduction, and every persisted MVQUAL scientific record exactly.
- Constrain nested cKDTree/BLAS work to one native lane per outer campaign job; preserve legacy direct-API native-thread semantics when no explicit resource scope is supplied.
- Add RAM-admitted per-job temporary estimates and an automatic four-lane ceiling for memory-bandwidth-heavy MVQUAL scoring, with explicit higher overrides allowed on qualified high-bandwidth hosts.
- On a 16,000-reference / six-size / 12-job same-N fixture, reduce same-host median wall time from about 0.866 s in untouched 0.20.231a0 to about 0.409 s at four outer lanes (~2.12x), while preserving plan digest `2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b`.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic MACE-MH-1 compatibility; next optimization gate is AUDIT-EVAL-PERF1.

## 0.20.231a0 - 2026-08-17

- Implement REPAIR-PAR1 / architecture revision 98 while preserving sequential repair iteration, objective/tie authority, accepted/rejected trace, terminal order, and winner application.
- Fuse removal sparse metrics, vectorize replacement-frontier CSR scoring, add thread-private epoch/stamp membership, and replace repeated future-rank searches with an O(1) inverse rank map.
- Use PARCORE1 only for sufficiently large immutable proposal batches; canonical reduction follows historical removal-shortlist order and the winning representative contribution is recomputed with historical scalar arithmetic before persistence.
- Preserve complete repair-plan digest `5dcb048b02ae2670d48d15f3f610b5814b611b2339df4ec4b265a52615b9545b` across scalar reference and optimized 1/2/4-worker schedules.
- On same-host proposal fixtures, reduce the medium scalar scorer from about 3.176 s to 0.119 s (~26.6x) and the large scorer from about 3.130 s to 0.830/0.611/0.461 s at 1/2/4 lanes (~6.79x end-to-end at four lanes).
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic MACE-MH-1 compatibility; next optimization gate is MVQUAL-PAR1.

## 0.20.230a0 - 2026-08-17

- Implement MVKERNEL1 / architecture revision 97 as exact sparse-vector hardening around the frozen sequential MVSEL rank authority and independent MVQUAL scientific scorer.
- Add shared vectorized ragged-CSR gathers, fuse identical family/domain scatter streams, vectorize witness-weight arithmetic, and maintain hard-obligation pending count incrementally without changing selector decisions.
- Vectorize MVIDX selected-subset coverage and obligation telemetry with canonical CSR gathers and `bincount`; MVQUAL provenance coding is built once per domain and telemetry remains byte-equivalent to the scalar reference.
- Preserve the 4,096/2,048 selector digest `d147d85acd64dd386dcd9b64e1bd534001e1b1a9e1736522b2ffaddbb978b378` and the 24,576/16,384 scale digest `aaec42fb0c1df6a62ce2286ec5f5b8897bc089d6d31726da89a0461bcd75d608`.
- On the cloud CPU, reduce the representative selector fixture from about 1.404 s to about 0.811 s and the 16,384-selection stress path from about 6.640 s to about 5.591 s; reduce 8,192-frame/6-family MVQUAL telemetry from about 0.578 s to about 0.041 s while preserving the exact telemetry authority.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic compatibility with MACE-MH-1; next optimization gate is REPAIR-PAR1.

## 0.20.229a0 - 2026-08-17

- Implement COVREF-PAR1 / architecture revision 96: exact TARGET-DATA2B reference-radius block parallelism on the shared deterministic scheduler with one native cKDTree worker per task.
- Add adaptive cache-sized radius blocks, O(1) pair/species adapters, and exact pre-tree scalar constant-family rejection while preserving TARGET-DATA2B scientific authority.
- Preserve PERFBASE1 supplied-family radius digest `823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d`; next gate is MVKERNEL1.

## 0.20.228a0 - 2026-08-17

- Implement MVIDX-REUSE1 / architecture revision 95 as an exact-equivalence optimization of TARGET-DATA2C sparse-index inversion after NEIGHBOR1 removes the duplicate geometry sweep.
- Keep NEIGHBOR1 forward CSR and all MVIDX scientific semantics fixed while parallelizing independent required-family inversions and hard-obligation construction through the PARCORE1 deterministic work queue.
- Retain the deterministic compiled SciPy counting transpose as the per-component CSR-to-CSC kernel; reject an exact Python-threaded intra-family range-fill prototype because qualification hardware showed it slower than the compiled kernel.
- Replace row-by-row Python canonical-CSR validation with an equivalent vectorized boundary-aware monotonicity check, removing tens of thousands of tiny validation calls on large sparse graphs.
- Preserve exact MVIDX1 digest `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c` for 1/2/3-worker schedules and byte-identical inverse arrays.
- On the same-host frozen synthetic authority, reduce cached MVIDX median wall time from about 0.590 s in untouched 0.20.227a0 to about 0.156/0.118/0.087 s at 1/2/3 lanes, about 6.8x faster at the available three-lane budget.
- Preserve 111/111 TARGET-DATA2 functional tests with the same 18 expected warnings; keep active qualification on supplied MACE-MPA-0 medium while preserving the same runtime contract for MACE-MH-1.
- Next optimization gate is COVREF-PAR1.

## 0.20.227a0 - 2026-08-17

- Implement NEIGHBOR1 / architecture revision 94 as an exact-equivalence shared neighborhood engine for TARGET-DATA2B FEAS1 and TARGET-DATA2C MVIDX1.
- Add `ExactNeighborhoodEngine` and canonical streamed witness->candidate CSR production on the PARCORE1 global queue; ragged cKDTree results are compressed at the worker boundary and released after canonical reduction.
- Make FEAS1 emit its unchanged feasibility authority together with a content-addressed, worker/block-invariant forward-CSR execution cache.
- Add authenticated native-array persistence and campaign restart/rebuild behavior for the NEIGHBOR1 cache; final CSR bytes are admitted against `StageResourceScope` before RAM materialization.
- Make MVIDX1 adopt authenticated forward CSR and skip its former second geometric cKDTree sweep on cache hit; cache miss rebuilds once through the same global exact engine. The existing CSR->CSC inversion remains unchanged for MVIDX-REUSE1.
- Preserve frozen FEAS1 digest `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613` and MVIDX1 digest `e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c` on the PERFBASE1 synthetic authority.
- On the cgroup-limited three-lane cloud CPU, paired final medians reduce FEAS1->MVIDX1 wall time from about 2.77 s in untouched 0.20.226a0 to about 1.03 s with NEIGHBOR1 (about 2.68x end-to-end speedup); timing remains execution evidence only.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving model-generic support for MACE-MH-1; no model inference/training/GPU authority changes.
- Advance dependency-graph schema to 76; next optimization gate is MVIDX-REUSE1.

## 0.20.226a0 - 2026-08-17

- Implement PARCORE1 / architecture revision 93 as the shared deterministic CPU scheduling substrate under exact scientific equivalence.
- Add `DeterministicWorkQueue`, bounded ready/in-flight/completed work, work-conserving dispatch, ordered reducers, task-identity failures, RAM admission/backpressure and reservations, heartbeat telemetry, and NUMA-ready locality metadata.
- Extend `StageResourceScope` with the execution-only stage RAM budget and centralize campaign-owned BLAS/OpenMP quarantine at queue scope.
- Migrate FEAS1 from its bespoke executor coordinator to PARCORE1 while preserving exact cKDTree neighborhoods, one-native-worker-per-task outer scheduling, and canonical FP64 witness-block reduction.
- Preserve FEAS1 scientific digest `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613`; same-host full-budget throughput and assigned-lane occupancy are indistinguishable from the untouched 0.20.225a0 control within observed timing noise.
- Keep the active qualification on supplied MACE-MPA-0 medium while retaining the same scheduler/record contracts for MACE-MH-1.
- Advance dependency-graph schema to 75; next optimization gate is NEIGHBOR1.

## 0.20.225a0 - 2026-08-17

- Implement PERFBASE1 / architecture revision 92 as the measurement-only first gate of the frozen campaign optimization program.
- Add foundation-generic `PerfBase1Trial`, `PerfBase1Workload`, and `PerfBase1Record` authorities with exact scientific-output digests separated from timing/RSS/occupancy/queue telemetry.
- Add a deterministic CPU benchmark harness spanning supplied TARGET-DATA2B/replay data and synthetic FEAS1/MVIDX1/MVSEL1 workloads across 1, 2, bounded-intermediate, and automatic worker schedules.
- Bind the current qualification to the supplied MACE-MPA-0 medium checkpoint while preserving the same record/harness contract for MACE-MH-1.
- Freeze cloud CPU evidence showing useful FEAS1 scaling and no current MVIDX1 native-worker scaling; do not change any scientific/runtime optimization authority in this release.
- Mark Foundation Audit/EVAL2 model-inference timing unavailable on the cloud measurement host rather than synthesizing performance evidence.
- Advance dependency-graph schema to 74; next optimization gate is PARCORE1.

## 0.20.224a0 - 2026-08-17

- DOC-ARCH1 / architecture revision 91: restructured the MLFF architecture manual into indexed chapter sources plus one assembled canonical Markdown/PDF authority.
- Moved architecture revision notes and release notes out of the repository root into `docs/history/mlff/` with lineage indexes; canonical specs, runbooks, reports, and qualification evidence now live under their existing docs/release trees.
- Froze the campaign-wide exact-equivalence performance roadmap: PARCORE1 shared scheduling, FEAS1/MVIDX neighborhood reuse, stable sparse transpose, TARGET-DATA2B parallelization, MV sparse/vector kernels, REPAIR/MVQUAL parallelism, audit/evaluation vectorization, replay indexing, and end-to-end requalification.
- No scientific dataset, coverage, training, evaluation, or GPU authority changed in this documentation-only gate.

## 0.20.223a0 - 2026-08-17

- Implement TARGET-DATA2B-FEAS1-PERF3 after workstation evidence showed PERF2 profile-local block threading still underutilized the CPU and its progress output omitted the total profile count.
- Replace nested block-thread/native-cKDTree factorization with one campaign-wide single-level FEAS1 work queue: automatic mode allocates one executor lane per configured CPU-budget thread and every parallel cKDTree block uses `workers=1`.
- Feed profile preparation and witness blocks from every domain/profile into the same bounded queue so completed/profile-tail work immediately yields its lane to another profile rather than stranding CPU capacity.
- Preserve deterministic per-profile witness-order reduction, exact row-major/candidate-major FP64 accumulation, all FEAS1 scientific schemas/digests, the 16,384 ceiling, and downstream TARGET-DATA2C semantics.
- Upgrade FEAS1 progress to campaign-wide totals: profiles completed/total, profiles prepared, active profiles, blocks, witnesses, executor busy lanes, pending/queued tasks, throughput, elapsed time, and global ETA.
- Add `[performance].target_coverage_feasibility_global_workers`; automatic `0` uses the full CPU budget (normally 90% of logical threads). PERF2/PERF1 block/family controls remain compatibility aliases.
- On the 8-lane qualification workload (8 x 25,033-witness profiles), global single-level scheduling reduced FEAS1 evaluation wall time from 7.793 s to 3.811 s while averaging 7.66 CPU cores, about 95.7% of the assigned worker lanes.
- Advance MLFF architecture to revision 90 and dependency-graph schema 72.

## 0.20.222a0 - 2026-08-17

- Implement TARGET-DATA2B-FEAS1-PERF2 after workstation evidence still showed only about 200-500% CPU utilization during long FEAS1 execution.
- Replace PERF1 family-level scheduling with bounded shared-cKDTree witness-block threading so query and NumPy neighborhood-compression phases overlap even for a single expensive family.
- Factor `StageResourceScope` across `target_coverage_feasibility_block_workers * target_coverage_workers`, with automatic block/tree balancing and exact witness-order parent reduction.
- Reject the evaluated fork/process block backend as the default because ragged-neighborhood IPC was substantially slower on qualification hardware.
- Add FEAS1 interval heartbeats plus block/witness elapsed-rate-ETA reporting; add matching block-level elapsed-rate-ETA-edge progress to MVIDX1.
- Preserve exact FEAS1/MVIDX1 scientific schemas, FP64 accumulation order, coverage neighborhoods, 16,384 ceiling, downstream selector behavior, and GPU authority unchanged.
- Advance MLFF architecture to revision 89 and dependency-graph schema 71.

## 0.20.221a0 - 2026-08-17

- Implement TARGET-DATA2B-FEAS1-PERF1 exact-equivalence CPU hardening after low-utilization workstation evidence.
- Replace the serialized FEAS1 per-witness neighborhood reduction with canonical vectorized `(witness,candidate)` compression, vectorized support-degree evaluation, and historical-order FP64 accumulation.
- Add bounded concurrent feature-family execution that partitions the existing CPU budget between family workers and cKDTree workers; expose `target_coverage_feasibility_family_workers` as an execution-only override.
- Reuse the same canonical row-compression kernel in TARGET-DATA2C-MVIDX1 so sparse row construction no longer loops in Python over every witness.
- Preserve FEAS1/MVIDX1 scientific schemas, coverage neighborhoods, candidate ceiling, report/graph digests, TARGET-DATA2C selector semantics, and all GPU/FINAL-GPU1 authority unchanged.
- Advance MLFF architecture to revision 88 and dependency-graph schema 70.

## 0.20.220a0 - 2026-08-17

- Implement WARN-DOMAIN1: one campaign-wide MACE/PyTorch warning domain at the MLFF CLI boundary.
- Capture and condense Python warnings emitted anywhere in the campaign command, including setup/recovery code that lies outside operation-local MACE decorators.
- Capture MACE/PyTorch `logging.WARNING` records (including root-logger dtype-conversion warnings) through the same domain and suppress their raw logger output.
- Make the campaign warning owner process-wide/thread-aware so warning scopes entered by worker threads merge into the same command summary instead of emitting independent compatibility warnings.
- Emit one normalized `[WARN]` campaign summary while preserving unrelated warning/logging behavior; retain local warning scopes for non-campaign API use.
- Preserve CUEQ-REPEAT1-PARITY1 scientific authority unchanged; this release changes warning transport/observability only.

## 0.20.219a0 - 2026-08-16

- Implement CUEQ-REPEAT1-PARITY1, replacing stochastic one-shot TRAIN2 FP32 force allclose with an authorizing warm-up/all-pairs self-noise-normalized parity gate.
- Restore stable TRAIN2/source energy/stress/descriptor FP32 authority to the tight `1e-5/1e-6` policy.
- Freeze 1 discarded warm-up + 10 post-warm-up samples/backend, 45/45/100 self/cross comparisons, p99 force-distribution ratio ceiling 1.25, Fmax self-envelope factor 1.5, and absolute catastrophic ceiling `1e-4 eV/A`.
- Retain DIAG3 repeatability arrays as audit evidence, remove deterministic-control execution from routine doctor authorization, and keep the deterministic worker as an optional diagnostic.
- Advance FINAL-GPU1 preflight to v10 and bind both stable-channel and noise-normalized TRAIN2 parity-policy digests.

## 0.20.218a0 - 2026-08-16

- Refine the non-authorizing TRAIN2 FP32 repeatability diagnostic to CUEQ-REPEAT1-DIAG3.
- Discard one explicit warm-up evaluation per backend before collecting evidence.
- Retain ten post-warm-up outputs per backend and compute 45 e3nn-self, 45 CuEq-self, and 100 e3nn/CuEq all-pairs comparisons offline.
- Report min/median/p90/p99/max force distributions plus E/S/D maxima, exceedance counts, and selection identity.
- Preserve historical repeatability-diagnostic v1 records while emitting v2 all-pairs records.
- Keep TRAIN2 FP32 parity policy unchanged at rtol=1e-5, atol=1e-5; DIAG3 remains non-authorizing.

## 0.20.217a0 - 2026-08-16

- Refine CUEQ-REPEAT1-DIAG with complete e3nn-self and CuEq-self force RMSE/p99/p99.9/exceedance distributions in terminal output and serialized evidence.
- Add an isolated non-authorizing deterministic-control subprocess with `CUBLAS_WORKSPACE_CONFIG=:4096:8`, deterministic PyTorch algorithms/debug mode, and deterministic cuDNN settings; unsupported deterministic kernels are reported explicitly rather than silently falling back.
- Preserve the active TRAIN2 FP32 parity authority at `rtol=1e-5, atol=1e-5`; the refined diagnostic remains measurement-only pending workstation interpretation.
- Advance MLFF architecture to revision 84 and dependency-graph schema 66; revision-82 FINAL-GPU1/HF2 remains archival.

## 0.20.216a0 - 2026-08-16

- Add CUEQ-REPEAT1-DIAG: non-authorizing 10-repeat TRAIN2 FP32 e3nn/CuEq repeatability diagnostics with printed force-tail statistics and deterministic-runtime observations.
- Keep all parity and scientific convergence tolerances unchanged pending workstation evidence.
- Advance MLFF architecture to revision 83 and dependency-graph schema 65; hold the revision-82 FINAL-GPU1 HF2 handoff archival until the diagnostic is reviewed.

- Apply CUEQ-DEFAULT1-HF2: raise only the TRAIN2 FP32 CuEq/e3nn absolute backend-parity ceiling from `2e-6` to `1e-5` while retaining `rtol=1e-5`.
- Keep generic source/DATA6 FP32 parity unchanged at `rtol=1e-5, atol=1e-6` and keep FP64 parity unchanged at `rtol=1e-10, atol=1e-12`.
- Freeze MPA-0/default evidence (`Emax=2.384e-7`, `Fmax=8.911e-6`, `Smax=1.660e-7`, `Dmax=2.883e-7`, identical selection) as motivation for a fixed FP32 backend-equivalence envelope, not a scientific convergence tolerance.
- Add explicit regression that `8.911e-6` passes TRAIN2-only while `1.0001e-5` against zero fails; no adaptive tolerance widening or silent fallback is introduced.
- Advance FINAL-GPU1 preflight to v9 and bind the exact TRAIN2 parity-policy payload/digest into the immutable handoff.
- Advance MLFF architecture to revision 82 and dependency-graph schema 64.

## 0.20.214a0 - REPLAY-UNIFY1E

The single-source replay migration is complete. The executable invalidation planner freezes minimal cache invalidation, identical-byte relocation avoids source reparse, and FINAL-GPU1 v3 adds a release-blocking replay pseudo-label GPU execution gate. Positive GPU qualification remains pending the regenerated workstation bundle.

## 0.20.213a0 - 2026-08-16

- Implement REPLAY-UNIFY1D and switch new campaign configuration to one `[paths].replay_set` external replay authority with default deterministic 5:1 splitting.
- Integrate Gate-A/B/C source, true-label, prediction, qualification, split, and lazy materialization records into doctor/prepare/restart authority while preserving downstream TRAIN2/DATA8 scientific contracts through internal transport adapters.
- Generate pseudo-label train/monitor and independent true-label monitor views from the exact same split; source truth remains separate and missing required retention truth fails closed.
- Hide deprecated init split-file flags while retaining legacy parser/config readability and forbid mixed new/legacy replay inputs.
- Add authenticated source-inspection and transport-artifact receipts so process-style restarts avoid 12k ExtXYZ rescans; protect `replay_set` in storage accounting.
- Qualify the supplied 12,000-frame true-label campaign integration as exactly 10,000 train / 2,000 monitor with ~0.60 s receipt-backed restart; defer real MACE/CUDA/CuEq execution to regenerated FINAL-GPU1 after REPLAY-UNIFY1E.
- Advance MLFF architecture to revision 80 and dependency-graph schema 62; next gate is REPLAY-UNIFY1E.

## 0.20.212a0 - 2026-08-16

- Implement REPLAY-UNIFY1C as an additive foundation-prediction, audit, qualification, and lazy pseudo-label materialization layer over the single replay source.
- Reuse `MaceCalculatorProvider.predict_batch()` with frozen foundation model/head/inference/kernel identity; strip source truth from inference copies and keep batch/shard tuning outside scientific cache identity.
- Add order-independent logical prediction-cache identity, bounded ragged prediction shards, and a compact authenticated audit sidecar so threshold-only reclassification performs zero model calls and avoids force/stress payload I/O.
- Add qualification-bound lazy pseudo-label train/monitor transport views with authenticated cache hits and reinference-free reconstruction of deleted views.
- Qualify the control plane on the supplied 12,000-frame LTA source as 10,000 train / 2,000 monitor; retain real MACE/CUDA/CuEq qualification for the regenerated FINAL-GPU1 bundle after REPLAY-UNIFY1E.
- Advance MLFF architecture to revision 79 and dependency-graph schema 61; next gate is REPLAY-UNIFY1D.

## 0.20.211a0 - 2026-08-16

- Implement REPLAY-UNIFY1B source-true-label cache authority and lazy train/monitor materialization from the single replay source and immutable split manifest.
- Preserve exact source truth independently of pseudo-label transport fields; reject missing requested truth and same-geometry/different-label cache masquerading.
- Generate missing train+monitor true-label views in one bounded-memory source pass and return authenticated cache hits without reopening the source.
- Qualify the supplied 12,000-frame source as 10,000 train / 2,000 monitor and remove an accidental quadratic per-frame whole-corpus digest path.
- Advance MLFF architecture to revision 78 and dependency-graph schema 60; next gate is REPLAY-UNIFY1C.

## 0.20.210a0 - 2026-08-16

- Freeze REPLAY-UNIFY1 as a five-gate migration from external replay train/monitor files to one selected replay-set authority.
- Implement REPLAY-UNIFY1A source/config/split schemas, canonical 1e-8 Angstrom geometry identity, streamed source-label inventory, and deterministic 5:1 seeded split manifests.
- Prove the default 12,000-frame replay authority maps exactly to 10,000 training and 2,000 monitor configurations with disjoint complete membership.
- Keep historical ReplayFileArtifact/ReplayPreparationPlan and live DATA8/TRAIN2 behavior unchanged until REPLAY-UNIFY1D.
- Mark the 0.20.209a0 FINAL-GPU1 workstation bundle archival and defer one-shot bundle regeneration until REPLAY-UNIFY1E closes.
- Advance MLFF architecture to revision 77 and dependency-graph schema 59; next gate is REPLAY-UNIFY1B.

## 0.20.209a0 - 2026-08-16

- Upgrade FINAL-GPU1 to the v2 immutable 17-item workstation matrix with typed SIZE-FIDELITY2 and MVMIGRATE1 learning-control must-pass evidence.
- Add final GPU evidence assemblers and exact digest/dataset binding in the reducer.
- Implement fail-closed dry-run plus single-transaction TARGET-DATA2C v5 / TARGET-DATA2D v3 activation while preserving historical v4 authority.
- Make prepare restart receipts generation-aware and invalidate stale production-decision aliases at activation.
- Advance MLFF architecture to revision 76 and dependency-graph schema 58; positive GPU execution remains pending the user's final workstation run.

## 0.20.208a0 - 2026-08-16

- Implement TARGET-DATA2C-MVMIGRATE1 as an atomic, fail-closed generated-policy migration latch over the completed FEAS1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVPERF1 -> MVQUAL1 -> SIZE-HALVE2 -> SIZE-FIDELITY2 chain.
- Add TARGET-DATA2C v5 candidate authority using the exact REPAIR1 master order, the fixed eight sizes `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`, independently reconstructed TARGET-DATA2B coverage/DATA2A hard obligations, minimum four hard qualifiers, and no dynamic rescue.
- Reserve and implement generation-separated TARGET-DATA2D v3 / TARGET-DATA2E v3 schemas so historical v4/v2/v2 authorities cannot masquerade as migrated v5/v3/v3 records.
- Persist `target_multi_view_migration_plan` and an authenticated `target_data_ladder_mv_candidate` without replacing the live revision-64 v4 ladder; candidate invalidation is content-addressed to only the migration/MV lineage.
- Require positive FINAL-GPU1 legacy-vs-MV learning controls and SIZE-FIDELITY2 GPU qualification before the migration latch can authorize atomic activation. No CPU-only or deferred report can activate generated defaults.
- Preserve current generated v4/v2/v2 execution, DATA8 membership, e3nn source/DATA6 policy, and CuEq TRAIN2 policy until the final consolidated GPU evidence passes.
- Advance canonical MLFF architecture to revision 75 and dependency-graph schema 57; the next release action is FINAL-GPU1 qualification followed by atomic v5/v3/v3 activation if all gates pass.

## 0.20.207a0 - 2026-08-16

- Implement SIZE-FIDELITY2 as the pre-migration survivor-fidelity requalification control plane for the MV fixed-eight target-size funnel.
- Reuse one exhaustive seed x hard-qualified-size 30-epoch trajectory matrix to reconstruct every scientifically available admission width q=4..8; do not retrain per q.
- Require exact uninterrupted 3/10/30 checkpoint ancestry, 100% retention of the eventual two 30-epoch finalists through epochs 3 and 10, and fail on material fixed-16,384 boundary nonconvergence.
- Derive 128/256/512/1024 coarse-monitor views from the same authorized epoch-3 full prediction product, adding zero extra model-inference passes; recommend the smallest monitor with exact promotion equivalence.
- Integrate `size_fidelity2_execution_plan` into campaign prepare/restart receipts while keeping positive GPU execution deferred to FINAL-GPU1 and leaving revision-64 TARGET-DATA2C v4/TARGET-DATA2D v2 unchanged.
- Advance canonical MLFF architecture to revision 74 and dependency-graph schema 56; next gate is TARGET-DATA2C-MVMIGRATE1.

## 0.20.206a0 - 2026-08-16

- Implement SIZE-HALVE2 as a separate pre-migration fixed-eight target-size funnel authority over the independently qualified MV-selected ladder.
- Freeze exactly `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`, require at least four independently hard-qualified sizes, and forbid coverage-failing sizes from purchasing TRAIN2.
- Implement exact `q -> min(q,4) -> 2 -> 1` 3/10/30 evidence transitions with boundary tie protection, exact checkpoint/optimizer/RNG ancestry, and final fixed-ceiling nonconvergence diagnosis.
- Reuse PERF-P2R execution geometry so promoted candidates continue 0->3->10->30 without repaying completed epochs.
- Integrate `size_halve2_plan` into campaign prepare/restart receipts without replacing revision-64 TARGET-DATA2C v4 or TARGET-DATA2D v2 production authority.
- Advance canonical MLFF architecture to revision 73 and dependency-graph schema 55; next gate is SIZE-FIDELITY2.

## 0.20.205a0 - 2026-08-16

- Implement TARGET-DATA2C-MVQUAL1 as independent same-N legacy-vs-MV scientific qualification evidence.
- Re-score both selectors through immutable TARGET-DATA2B, bind DATA2A/MVIDX hard obligations, and record D_max/D_sum/N95 plus uncovered/unique/provenance telemetry.
- Fail qualification on same-N hard-predicate regression, worse worst-view deficit, or increased common-size N95; independently rescore all MV rungs for bounded-capacity diagnosis.
- Freeze one or two common hard-qualified legacy-vs-MV learning-control sizes while deferring positive TRAIN2/GPU execution to the final consolidated GPU qualification.
- Integrate `target_multi_view_qualification` into campaign prepare/restart receipts without changing revision-64 TARGET-DATA2C v4, DATA8 membership, TARGET-DATA2D, or CuEq policy.
- Advance canonical MLFF architecture to revision 72 and dependency-graph schema 54; next gate is SIZE-HALVE2.

## 0.20.204a0 - 2026-08-16

- Implement TARGET-DATA2C-MVPERF1 exact-equivalence sparse execution hardening for MVIDX1/MVSEL1/REPAIR1.
- Add bounded witness-order scatter updates, reference/optimized execution equivalence, consolidated REPAIR1 shell scans, and MVSEL1/REPAIR1 StageResourceScope execution.
- Record ~2.7x representative selector speedup and successful full 16,384-selection cardinality stress execution with unchanged scientific policies.
- Advance canonical MLFF architecture to revision 71 and dependency-graph schema 53; next gate is TARGET-DATA2C-MVQUAL1.

## 0.20.203a0 - 2026-08-16

- Implement TARGET-DATA2C-REPAIR1 exact active-shell repair as diagnostic/pre-migration evidence on top of MVSEL1/MVIDX1.
- Add exact coverage-multiplicity unique-contribution accounting, hard-obligation-safe removals, deficit-directed replacements, strict lexicographic improvement, replacement-rank inheritance, and frozen lower-prefix protection.
- Keep exact required-obligation multiplicities in the MVSEL1 reconstructible state so removal safety is evaluated without rescanning or changing any MVSEL1 selection decision.
- Integrate `target_multi_view_repair` into campaign prepare/restart receipts while retaining revision-64 TARGET-DATA2C v4 as the active production selector.
- Advance canonical MLFF architecture to revision 70 and dependency-graph schema 52; next gate is TARGET-DATA2C-MVPERF1.

## 0.20.202a0 - 2026-08-16

- Implement TARGET-DATA2C-MVSEL1 deterministic progressive multi-view selection as pre-migration evidence.
- Add hard-obligation-first and worst-view-first Phase-A selection with exact incremental MVIDX1 gain updates.
- Add density-aware harmonic witness-multiplicity Phase-B filling, deterministic provenance/diversity tie-breaking, nested rung evidence, exact replay validation, CampaignStore/restart integration, and public APIs.
- Keep revision-64 TARGET-DATA2C v4 as the active production selector pending REPAIR1/MVPERF1/MVQUAL1/SIZE-HALVE2/SIZE-FIDELITY2/MVMIGRATE1.

## 0.20.201a0 - 2026-08-16

- Implement TARGET-DATA2C-MVIDX1 exact sparse bidirectional required-family coverage adjacency and first-class extent/stratum/correlation obligation indexing.
- Persist MVIDX1 scientific arrays as authenticated content-addressed NPY sidecars; selector caches remain reconstructible and outside scientific identity.
- Integrate `target_coverage_sparse_index` into `prepare` and receipts without changing revision-64 TARGET-DATA2C v4 selection/default behavior.
- Advance architecture revision to 68 and dependency-graph schema to 50; next gate is TARGET-DATA2C-MVSEL1.

## 0.20.200a0 - 2026-08-16

- Implement TARGET-DATA2B-FEAS1 as the first executable gate of the optimized multi-view target-data roadmap.
- Add deterministic cross-support fragility diagnostics and conservative 16,384-cap cardinality lower bounds.
- Integrate authenticated FEAS1 evidence into campaign prepare/restart receipts without changing TARGET-DATA2C v4 selection.
- Advance canonical MLFF architecture to revision 67 and dependency-graph schema 49.

## 0.20.199a0 - 2026-08-16

- Harden TARGET-DATA2-MVPLAN1 into TARGET-DATA2-MVPLAN2 as a plan-only architecture revision; executable revision-64 TARGET-DATA2C v4 remains unchanged until MVMIGRATE1.
- Replace tautological full-pool FEAS1 semantics with self-consistency, cross-support fragility, cardinality lower-bound, and provable 16,384-capacity diagnostics.
- Freeze MVIDX1 as an exact sparse bidirectional candidate<->witness graph with hard extent/stratum obligations, content-addressed binary sidecars, and authoritative-versus-reconstructible cache separation.
- Freeze MVSEL1 as deterministic two-phase selection: hard obligations/worst-view coverage first, then density-aware representative filling; FP64 gain accumulation and stable frame-UID tie breaking are normative.
- Freeze REPAIR1 as exact coverage-multiplicity unique-contribution analysis plus deficit-directed shell-local exchanges; literal leave-one-out rescoring and full all-pairs swap search are forbidden.
- Carry PERF-P2/P2R/P3/P4/P5 constraints into MVPERF1: incremental updates, lazy exact rescoring, one StageResourceScope, bounded memmap/CSR storage, streamed hashing, and scaling telemetry.
- Strengthen MVQUAL1 with same-N deficit dominance, N95, redundancy/cost telemetry, and limited legacy-vs-MV learning controls.
- Revise SIZE-HALVE2 so coverage-failing sizes are never trained: q qualified candidates enter the 3-epoch stage and reduce q -> min(q,4) -> 2 -> 1; q=8 gives the intended 8 -> 4 -> 2 -> 1 funnel.
- Add deterministic rung invariants, saturation diagnostics, shell-rank inheritance, and explicit non-goals (no active data acquisition, ANN, learned selector, or GPU graph authority in this gate sequence).
- Advance canonical MLFF architecture to revision 66 and dependency-graph schema 48.

## 0.20.198a0 - 2026-08-16

- Freeze TARGET-DATA2-MVPLAN1 as a plan-only architecture revision for deterministic multi-view target-data coverage optimization; executable revision-64 selection remains unchanged until migration.
- Set the planned generated target-size ceiling to 16,384, yielding eight fixed power-of-two candidate sizes from 128 through 16,384.
- Add full-development-pool feasibility/support-mismatch diagnosis before subset optimization and preserve the independent 0.95 hard-coverage authority.
- Freeze robust worst-view-first selection, exact nested prefixes, unique-contribution redundancy, deficit-directed shell repair, independent audit, and exact-equivalence performance hardening.
- Clarify successive fidelity as candidate-count reduction 8 -> 4 -> 2 -> 1 at 3 -> 10 -> 30 epochs; coverage-failing candidates cannot survive and at least four hard qualifiers are required before the 10-epoch stage.
- Break implementation into nine ordered gates ending in TARGET-DATA2C-MVMIGRATE1; revision-64 dynamic rescue is retired only after qualification.
- Preserve the e3nn source/DATA6 and CuEq TRAIN2 policy unchanged.
- Advance canonical MLFF architecture to revision 65 and dependency-graph schema 47.

## 0.20.197a0 - 2026-08-16

- Correct TARGET-DATA2C fixed-ceiling under-qualification exposed by the full production DATA6-derived coverage families: preserve the base 128..8192 ladder and activate a deterministic bounded upper-ladder rescue only when fewer than the required hard-coverage qualifiers survive.
- Generate rescue candidates at aligned 3/8, 4/8, 5/8, 6/8, and 7/8 fractions of the smallest authorized development pool; the 7/8 ceiling preserves at least a 1/8 leakage-safe EVAL2 development complement.
- Keep TARGET-DATA2B hard coverage unchanged (`coverage_threshold = 0.95` by default); the correction expands candidate density rather than relaxing coverage, extent, stratum, or mandatory-reservation predicates.
- Bind rescue activation/candidates/minimum-qualifier requirement into TARGET-DATA2C v4 serialization and restart validation; pre-v4 ladder authorities rebuild fail-closed.
- Improve TARGET-DATA2D failure diagnostics with rescue state and largest-rung family/extent/stratum/mandatory failure details.
- Preserve the phase-separated e3nn source/DATA6 and CuEq TRAIN2 policy unchanged.
- Advance canonical MLFF architecture to revision 64 and dependency-graph schema 46.

## 0.20.196a0 - 2026-08-16

- Fix FOUNDATION-AUDIT1 prepare crash `NameError: name 'cfg' is not defined` by making the campaign configuration an explicit keyword-only input to `_ensure_foundation_target_audit()` and passing it from materialization.
- Add a branch-level regression that invokes the helper with a non-default `performance.foundation_audit_temporary_ram_mib` value and verifies the exact byte threshold reaching `build_foundation_target_audit()`.
- Sweep top-level `campaign_cli.py` helpers for any remaining unbound `cfg` references; none remain after the repair.
- Preserve DATA6, foundation-audit scientific definitions, e3nn source execution, CuEq TRAIN2 policy, and restart identities; only orchestration configuration plumbing changes.
- Advance canonical MLFF architecture to revision 63 and dependency-graph schema 45.

## 0.20.195a0 - 2026-08-16

- Fix DATA6 verified model-sweep recovery crash `NameError: name 'np' is not defined` by restoring the required module-level NumPy import in `campaign_cli.py`.
- Add a regression that forces absent/nonreusable DATA6 checkpoint recovery with more requested frames than the calibration stress cap, guaranteeing execution of the `np.linspace` sampling branch.
- Preserve DATA6 scientific/materialization identity, source/TRAIN2 acceleration policy, deterministic selections, and restart compatibility; the MACE/PyTorch TorchScript deprecation output remains warning-only.
- Advance canonical MLFF architecture to revision 62 and dependency-graph schema 44.

## 0.20.194a0 - 2026-08-16

- Fix revision-60 doctor foundation-contract reporting after the source/TRAIN2 backend split (`backend` -> `source_backend` + `training_backend`).
- Add a separately frozen selected-head TRAIN2 FP32 CuEq parity policy with `rtol=1e-5, atol=2e-6`; the generic ACCEL1 source/DATA6 authority remains unchanged at `rtol=1e-5, atol=1e-6`.
- Record the TRAIN2 parity-policy identity alongside the TRAIN2 realization/parity evidence so the numerical authority is explicit and content-addressed.
- Add regression coverage for the workstation roundoff envelope that motivated PHASE1 and for the phase-separated foundation configuration contract.
- Advance canonical MLFF architecture to revision 61 and dependency-graph schema 43.

## 0.20.193a0 - 2026-08-16

- Make pure CuEq the generated TRAIN2 backend while retaining e3nn for source inference, DATA6, pseudolabel generation, evaluation, and verification.
- Add phase-separated source/training acceleration configuration with exact legacy unified-backend compatibility.
- Add a dedicated content-addressed TRAIN2 acceleration realization and independent doctor qualification so training acceleration cannot grant source-execution authority.
- Bind DATA8/preflight training to the TRAIN2 backend and keep exported checkpoints portable through `only_cueq=false`.
- Preserve fail-closed runtime/parity behavior; this explicit policy migration does not manufacture or reinterpret pending FINAL-GPU1 evidence.
- Advance canonical MLFF architecture to revision 60 and dependency-graph schema 42.

## 0.20.192a0 - 2026-08-15

- Implement FINAL-GPU1 release-handoff evidence/reduction authority and advance preflight to v6 with exact release-archive binding.
- Separate release-blocking accelerator qualification from measure-only optimization probes and optional PHASE2/deployment capabilities.
- Require one locked CUEQ-DEP1 runtime identity across registered accelerator evidence and reject cross-release/cross-runtime contamination.
- Add resumable `init`, immutable `record`, `status`, explicit `verify`, and `reduce` handoff operations while preserving the legacy preflight invocation.
- Harden workstation handoff CLIs for direct source-tree execution; require content-addressed terminal evidence, explicit CUEQ runtime binding where applicable, and pre-reduction re-hashing of release/model/evidence bytes.
- Require locked foundation identities at handoff initialization and fail closed if the serialized FINAL-GPU1 policy or exact ordered matrix structure is altered.
- Keep generated-default mutation outside FINAL-GPU1; a positive PERF-CERT1 recommendation requires a later explicit policy revision.
- Advance canonical MLFF architecture to revision 59 and dependency-graph schema 41; positive CUDA/CuEq execution is pending on the final workstation package.

## 0.20.191a0 - 2026-08-15

- Implement PERF-CERT1 end-to-end scientific/performance certification and profile recommendation.
- Preserve the optimized MH-1/`omat_pbe` e3nn path as authoritative baseline; require exact hard-decision and deterministic target/DATA6/DATA7 selection identity.
- Keep CUEQ-PHASE1 training and optional CUEQ-PHASE2 source/DATA6 authorizations independent; PHASE2 failure does not block a passing PHASE1 profile.
- Record production-workload preparation, DATA2B/2C, DATA6, TRAIN2, EVAL2, VRAM, OOM/backoff, metric, checkpoint/head, runtime, dependency, and verification evidence.
- Require a strict positive total end-to-end speedup for recommendation while allowing different final checkpoint bytes when scientific decisions remain unchanged.
- Reject locked-test tuning and keep generated-default mutation outside PERF-CERT1 authority.
- Add `tools/qualify_mlff_perf_cert1.py`; advance FINAL-GPU1 preflight to v5 with independent PERF-CERT1 deferred state.
- Advance canonical MLFF architecture to revision 58 and dependency-graph schema 40. Positive accelerator execution remains deferred to FINAL-GPU1.

## 0.20.190a0 - 2026-08-15

- Implement CUEQ-PHASE2 as an optional selected-head pure-CuEq source-execution/DATA6 qualification authority while preserving original six-head MH-1/`omat_pbe` as the scientific source identity.
- Freeze the exact MH-1 source checkpoint, source-potential digest, EXTRACT1 selected-head checkpoint, and EXTRACT1 qualification digest in `CueqPhase2Policy.v1`.
- Add deterministic stratified development-corpus evidence with an explicit hard guard against locked-test tuning.
- Reuse the existing `MaceAccelerationParityRecord` for energy/force/stress/descriptor numerical acceptance; add foundation-difficulty, frozen-transform PCA/FPS, and exact DATA6/DATA7 selection parity without relaxing any tolerance.
- Content-address the selected-head/CuEq execution realization and require explicit scientific-source plus execution-realization lineage for caches and optional pseudolabel/E0 generation.
- Make pseudolabel authorization conditional on explicit value/E0 parity evidence; a source/DATA6 pass alone does not authorize pseudolabel execution.
- Keep direct six-head CuEq execution and generated-default changes permanently unauthorized at this gate.
- Add `tools/qualify_mlff_cueq_phase2.py` and advance FINAL-GPU1 preflight to v4 with independent CUEQ-PHASE1 and CUEQ-PHASE2 deferred states.
- Advance canonical MLFF architecture to revision 57 and dependency-graph schema 39. Positive accelerator evidence remains deferred to FINAL-GPU1; PERF-CERT1 is the next implementation gate.


## 0.20.189a0 - 2026-08-15

- Implement CUEQ-PHASE1 as a dedicated training-only paired-qualification authority while keeping source inference, DATA6, pseudolabel generation, and source evaluation on original MH-1/`omat_pbe`/e3nn.
- Add content-addressed phase-1 policy, trajectory, paired-assessment, and qualification records that freeze the EXTRACT1 selected-head starting checkpoint, DATA8, seed/order/splits, precision, objective/LR/stopping/replay policy, validation/EVAL2 authority, and common CUEQ-DEP1 runtime.
- Require a 5-10 epoch short e3nn/CuEq pair (default 8) plus at least one representative full pair; short-only success is explicitly non-authorizing.
- Preserve existing scientific authority rather than requiring bit-identical final weights: replay retention, finiteness, checkpoint admissibility, target-head extraction, EVAL2, and available physical verification must pass without hard-decision disagreement.
- Record paired target/replay metric deltas, wall time, update throughput, and peak/reserved VRAM as diagnostics only; no tolerance is added or relaxed.
- Add `tools/qualify_mlff_cueq_phase1.py` and advance FINAL-GPU1 preflight to v3 with embedded phase-1 deferred state/schema.
- Advance the canonical architecture to revision 56 and dependency-graph schema 38. Positive CuEq training evidence remains deferred to FINAL-GPU1; CUEQ-PHASE2 is the next optional implementation gate.

## 0.20.188a0 - 2026-08-15

- Implement CUEQ-DEP1 as a dedicated content-addressed accelerator-runtime authority with separate implementation and final-GPU qualification state.
- Require CuEq core, `cuequivariance_torch`, and `cuequivariance_ops_torch`; extend ops-distribution discovery through CUDA 13/12/11 and generic packages.
- Freeze installed distribution metadata/RECORD/WHEEL identities, imported module bytes, CUDA device/driver/toolkit, cuDNN, PyTorch deterministic/TF32/matmul settings, and relevant environment variables.
- Keep OpenEquivariance optional for phase-1 pure-CuEq training and preserve fail-closed no-fallback behavior.
- Upgrade FINAL-GPU1 preflight to v2 so the final workstation handoff embeds the full CUEQ-DEP1 runtime record and cannot omit the CUDA-ops layer.
- Advance the canonical architecture to revision 55 and dependency-graph schema 37. Positive CUEQ-DEP1 accelerator evidence remains deferred to FINAL-GPU1.

## 0.20.187a0 - 2026-08-15

- Complete PERF-P5 CPU/control-plane hardening for late TRAIN2/EVAL2 persistence and reuse. TRAIN2 and STOR2 tensor-state SHA-256 paths stream canonical contiguous CPU buffers through Python's buffer protocol in bounded chunks, preserving the exact historical digest contract while eliminating the extra full-payload `bytes` allocation.
- Add execution-only TRAIN2 persistence telemetry covering state cloning, tensor hashing, raw-checkpoint hashing, continuation-companion writing, summary writing, total persistence time, and payload sizes without weakening the continuation capsule.
- Add an opt-in fail-closed EVAL2 compatible-model state reload path. It requires exact model class, state-key, tensor-shape, tensor-dtype, device/head compatibility, and strict state loading. The normal reconstruction path remains the default.
- On the CPU development host, a 256 MB FP32 state reduces median TRAIN2 digest time 46.05% and STOR2 capsule-digest time 40.82%; incremental peak RSS falls from about 245 MiB to below 1 MiB in both cases. Supplied MH-1 shell reload is prediction-exact but 6.49% slower than fresh construction, so shell reuse is not promoted as a CPU default.
- Retain MACE HDF5/LMDB as dataset-storage formats rather than treating them as authenticated graph caches. Existing DATA8 fixed-file and DATA6/EVAL2 graph-cache authorities remain unchanged.
- Advance the canonical architecture to revision 54 and dependency-graph schema 36. Accelerator-side PERF-P5 performance qualification remains deferred to FINAL-GPU1.

## 0.20.186a0 - 2026-08-15

- Implement VRAM1 `MaceBatchCapacityCalibration.v2` with explicit descriptor/prediction/combined workload modes, deterministic stress-oriented calibration structures, allocator and driver-visible CUDA memory telemetry, throughput-aware safe-batch selection, one-time post-calibration cleanup, and a mandatory fresh live-VRAM re-clamp before DATA6. Historical v1 remains readable with descriptor-only semantics.
- Persist OOM-derived DATA6 safe-batch caps under an identity binding checkpoint, descriptor policy, device/dtype, workload mode, and calibration evidence. Matching restarts reuse the learned cap; changed identity invalidates it.
- Implement PERF-P4 bounded execution with CPU graph prefetch for native MACE batches and asynchronous descriptor/prediction shard persistence. Scientific order and the append-only recovery journal remain authoritative, and synchronous execution remains an exact fallback.
- Include graph, descriptor, and prediction host-residency estimates in queue admission. Pinned/nonblocking transfer optimization is deliberately not promoted without accelerator evidence.
- Real supplied MACE-MH-1/`omat_pbe` and MACE-MPA-0-medium/`default` CPU/e3nn prepared-vs-direct batch paths match exactly. The bounded CPU control-plane benchmark also reproduces identical DATA6 authority; its pipeline overhead is recorded without a speedup claim.
- Advance the canonical architecture to revision 53 and dependency-graph schema 35. VRAM1/PERF-P4 accelerator-memory and throughput acceptance remains deferred to FINAL-GPU1; PERF-P5 is the next CPU/control-plane implementation gate.

## 0.20.185a0 - 2026-08-15

- Implement PERF-P3 direct local-structure execution with immutable topology caches and bounded coordinate scratch while preserving bitwise feature authority. Rejected larger pair/radial scratch and chunked radial evaluation after measured memory/throughput regression and FP64-byte drift, respectively.
- Harden FOUNDATION-AUDIT1 force-tail reduction with exact final-size preallocation plus an execution-only mmap fallback. The 900,000-atom bounded fixture reduces peak RSS 8.02% with identical audit digest; no audit speedup is claimed.
- Add fail-closed `StageResourceScope` admission across Python, structural, cKDTree, BLAS/OpenMP, PyTorch CPU, and GPU-job concurrency. The 168-atom/300-frame structural fixture improves median wall time 7.42% with identical feature digest.
- Advance the canonical architecture to revision 52 and dependency-graph schema 34. VRAM1 + PERF-P4 is next; all GPU qualification remains deferred to FINAL-GPU1.

## 0.20.184a0 - 2026-08-15

- Implement PERF-P2R CPU/control-plane execution: a parameterized 3/4/5-epoch stage planner, exact incremental exposure authority, authenticated content-addressed DATA8 fixed-file cache, and shared frame-array index.
- On the bounded deterministic DATA8 fixture, authenticated cache hits reproduce the exact fresh authority and reduce median preparation wall time from 79.696 ms to 17.333 ms (4.598x; 78.25% lower). This is not a GPU or production-volume throughput claim.
- Re-anchor the supplied MACE-MH-1 and MACE-MPA-0-medium checkpoints to the previously locked SHA-256 identities; current real-model CPU/e3nn regression passes 27 tests with one source-tree-only skip.
- Add FINAL-GPU1 qualification scheduling: all outstanding MLFF CUDA/CuEquivariance qualification is deferred to one final release-matched workstation run, while CPU/reference and implementation qualification continue during development.
- Reclassify SIZE-FIDELITY1 as implementation-complete but final-release qualification-pending. PERF-P2R/PERF-P3 may proceed only in parameterized form across the complete 3/4/5-epoch, 128/256/512/1024-monitor, 1/2/4-meV/A calibration grid.
- Add `tools/run_mlff_final_gpu_qualification.py`, which verifies locked model identities and records CUDA, PyTorch, MACE/e3nn, CuEquivariance/OpenEquivariance, NVIDIA, and optional LAMMPS readiness without converting absent accelerator capability into a pass.
- Correct default real-test discovery for the supplied MPA-0 filename and add machine-readable FINAL-GPU1 development-host preflight evidence.
- Advance the canonical MLFF architecture to revision 51 and dependency-graph schema 33.

## 0.20.183a0 - 2026-08-15

- Implement SIZE-FIDELITY1 calibration authority and execution planning for the corrected target-size funnel. Calibration runs every hard-coverage-qualified size to 30 epochs for at least three frozen optimizer seeds and retrospectively evaluates candidate coarse endpoints at epochs 3, 4, and 5.
- Require 100% retention of both eventual 30-epoch target finalists through the coarse top-four and epoch-10 top-two screens, zero largest-boundary finalist misses, and exact coarse-monitor/full-development promotion-set equivalence. Winner recall and Spearman rank correlation remain diagnostics rather than substitutes for finalist recall.
- Calibrate coarse monitor sizes 128/256/512/1024 and early practical-equivalence widths 1/2/4 meV/Angstrom. Recommendations prefer the earliest faithful endpoint, then the smallest equivalent monitor, then the smallest tested width at or above the production default.
- Freeze an inference-efficient calibration contract: each checkpoint is inferred once on the full leakage-safe development role; all candidate monitor metrics are reduced from authenticated prediction subsets, so monitor-size calibration does not multiply MACE inference.
- Keep SIZE-FIDELITY1 and PERF-P2R accelerator/scientific runtime qualification open until FINAL-GPU1, while allowing parameterized CPU/control-plane implementation to proceed.
- Advance the canonical MLFF architecture to revision 49 and dependency-graph schema 31.

## 0.20.182a0 - 2026-08-15

- Correct target-size science with SIZE-HALVE1: TARGET-DATA2C v3 materializes every globally materializable rung and coverage becomes hard admission only; all coverage-qualified sizes enter the learning funnel.
- Advance TARGET-DATA2D to exact 3/10/30 successive fidelity. Epoch 3 uses one common leakage-safe target-only coarse role (default 256 configurations) to retain at most four; epoch 10 retains two; epoch 30 selects one under final target/replay/physical authority.
- Authenticate checkpoint, optimizer/scheduler, and Python/NumPy/Torch RNG ancestry across both 3->10 and 10->30 continuations. Generated preflight requires the epoch-3 boundary to lie strictly past LR warm-up and records optimizer updates plus structures presented alongside epochs.
- Preserve the largest hard-coverage ladder boundary within its practical-equivalence band at epoch 3 and epoch 10 so an early tie cannot hide bounded-ladder nonconvergence; final epoch-30 practical equivalence again prefers the smaller size.
- Advance TARGET-DATA2E to v2 full-funnel provenance and add deterministic block-balanced `size_development_coarse` EVAL2 authority. Replay has no epoch-3 work or ranking role and remains diagnostic-only at epoch 10.
- Mark PERF-P2 lazy four-smallest truncation as historical/superseded for generated campaigns. Insert mandatory SIZE-FIDELITY1 calibration before PERF-P2R so the epoch-3/10 survivor rule and 256-frame coarse monitor must demonstrate later-winner recall on exhaustive MACE trajectories before performance optimization. PERF-P2R then optimizes full-ladder coverage reuse, nested corpus/preprocessing caches, same-process target-only boundary evaluation, exact sampler-aware pause/resume, checkpoint-I/O thinning, stage-aware scheduling, and whole-funnel MACE/GPU performance.
- Advance the canonical architecture to revision 48 and dependency-graph schema 30.

## 0.20.181a0 - 2026-08-15

- Complete bounded PERF-P2 by advancing TARGET-DATA2C to `TargetDataLadderPlan.v2` with progressive exact rung materialization, global Stage-A qualification evidence, explicit intentional non-materialization, pool-unavailable sizes, and a versioned monotonicity contract.
- Bind the lazy stop width to the active TARGET-DATA2D shortlist policy (canonical width four), preserve legacy v1 as a readable exhaustive qualification oracle, and reject v1 as stale current campaign authority.
- Keep worker count execution-only for exact single-rung cKDTree scoring. Exhaustive v1 and lazy v2 retain identical Stage-A survivor sizes, survivor memberships, coverage-report digests, and mandatory-obligation status across early-stop and exhaustive-fallback qualification fixtures.
- On the supplied-data-derived forced early-stop fixture, three fresh-process samples reduce median wall time from 7.867 s to 1.556 s (80.23%) and serialized authority from 4,729,481 B to 591,058 B (87.50%). Exhaustive-fallback timing is recorded without a portable speedup claim.
- Advance the canonical architecture to revision 47 and PERF-P3 as the next gate.

## 0.20.180a0 - 2026-08-15

- Complete bounded PERF-P1 with one reusable exact FPS state shared by TARGET-DATA2C quota continuation and DATA7/TARGET-DATA2C deterministic selection; preserve existing FP64 tie/order authority.
- Preallocate the fused TARGET-DATA2C selector matrix, add progressive exact nested coverage with stage-budgeted cKDTree workers, and replace DATA7 dense KxK persistent selected-neighbor storage with an O(K) minimum-distance vector plus bounded pair blocks.
- Qualify exact full-reference selection/coverage equivalence. Median full-reference FPS wall improves 57.61%; a 4000x128/K=512 wide case improves 73.25%; DATA7 K=8192 persistent neighbor state falls from 512 MiB to 64 KiB with 44.58% lower peak RSS and 74.09% lower wall. Four-rung progressive coverage is exact but 10.29% slower on the measured host and is recorded as a remaining optimization target.
- Advance the canonical architecture to revision 46 and PERF-P2 as the next gate.

## 0.20.179a0 - 2026-08-15

- Complete bounded PERF-P0 for exact TARGET-DATA2B construction and persistence without changing the frozen coverage mathematics, target membership, FP64 authority, or scientific digests. Family arrays are canonical little-endian, C-contiguous, read-only NumPy arrays with streamed native-byte identities.
- Add authenticated content-addressed NPY-shard persistence with shared frame-index/weight profiles, atomic manifests and pointers, threshold-controlled read-only mmap restore, fail-closed path/dtype/shape/size/SHA validation, and exact historical-v1 migration reports.
- Reuse exact balanced-weight profiles, compute all required weighted quantiles from one stable ordering per scalar column, dispatch uniform-weight fixed-mass radii through an exact order-statistic path, expose profile-backed bulk family extraction, and retain the historical weighted/cKDTree paths as qualification oracles.
- Qualify the complete supplied 27-source, 37,633-frame, 6,322,344-atom target corpus. All 48 PERF-BASE0 array identities and all legacy/P0 scientific digests match exactly. Five matched isolated runs reduce median construction wall time from 7.541 s to 6.236 s (17.30%).
- At full scale, native v2 persistence measures 0.184 s write, 0.180 s authenticated mmap read, and 17,912,666 bytes versus 10.366 s, 14.382 s, and 42,749,676 bytes for nested JSON v1. PERF-P1 is next.

## 0.20.178a0 - 2026-08-15

- Implement PERF-BASE0 as the frozen post-MH1 numerical/performance oracle. New public records authenticate canonical little-endian array bytes, exact JSON decisions/orders, input corpora, scientific stages, execution telemetry, and old/new comparisons while excluding timing, RSS, I/O, worker, cgroup, and accelerator observations from scientific digests.
- Add fail-closed read/write and comparison APIs plus a stage-local CPU meter for wall/process CPU time, sampled/process peak RSS, major retained temporary arrays, Linux process I/O, throughput, thread-pool/worker settings, and cgroup/runtime identity.
- Add a reproducible LTA benchmark covering the complete supplied target and replay split corpora, compact deterministic regression fixtures, duplicate/tie/nonuniform-weight/missing-mask/triclinic-MIC adversarial cases, exact TARGET-DATA2B-style weighted local radii, and an explicitly bounded exact TARGET-DATA2C/DATA7 FPS prefix with nested coverage reports.
- Preserve scientific honesty for unavailable evidence: no MH-1 checkpoint or GPU was supplied, so DATA6 foundation descriptors/predictions, production DATA2C quota authority, TRAIN2/EVAL2 timing, and GPU/OOM telemetry are recorded as unavailable rather than approximated. PERF-P0 remains the next implementation gate.

## 0.20.177a0 - 2026-08-13

- Implement LOCKED-TEST2 as the one-shot post-SELECT2 locked target test. The exact frozen SELECT2 target-only model is evaluated once on the sealed DATA8/TARGET-DATA2A `locked_interpolation_test` role; locked evidence has no replay, ranking, fallback, retraining, or alternative-selection authority.
- Freeze activation before inference and bind campaign/SELECT2/role/data/model/policy/correlation-block identities. After activation, locked-E bytes are never rematerialized: changed or missing bytes or changed upstream authority fail closed and require a new campaign/protocol identity.
- Default the hard locked target force-RMSE ceiling to the TRAIN2 full target ceiling (30 meV/A for generated defaults), with optional explicit locked-only energy, worst-stratum, P99-force, and stress ceilings. Full EVAL2-style target diagnostics are retained for audit but cannot select another model.
- On failure, keep the SELECT2 candidate frozen for audit and publish nothing. On pass, atomically publish the exact frozen target-only MACE and DEPLOY-authenticated ML-IAP bytes as the final production artifacts and freeze immutable publication provenance. Locked evidence can only accept or reject the already frozen candidate.

## 0.20.176a0 - 2026-08-13

- Implement SELECT2 as the physics-qualified final-development seed selector after DYN-VERIFY2. The static seed order is frozen first with the exact EVAL2 1 meV/A practical-equivalence, paired block-bootstrap, target-stratum/species/tail, maturity, and stable-identity policy; physical evidence can eliminate a candidate but cannot rerank the survivors.
- Bind every final-development seed representative to its selected EVAL2 checkpoint and complete DEPLOY/PES/RELAX/DYN provenance. The first physical passer in the frozen static order is selected; failed higher-ranked candidates remain explicit fallback evidence and `fallback_count` records how many were skipped. Replay and rollout metrics receive zero positive ranking or tie-break credit.
- Freeze the selected target-only MACE model and exact ML-IAP artifact byte-for-byte under `models/select2-frozen/`, with restart validation against campaign, target-corpus, EVAL2, physical-chain, model, and artifact identities. SELECT2 intentionally stops before the one-shot locked test, preserving zero selection authority for locked evidence.

## 0.20.175a0 - 2026-08-13

- Implement DYN-VERIFY2 as the executable finite-temperature structural-dynamics gate after RELAX-VERIFY1. Surviving candidates run their exact DEPLOY-authenticated ML-IAP artifacts in the same authenticated LAMMPS executable on a common candidate-independent grid of up to two DFT-relaxed bases at 300 K and 800 K.
- Freeze the default short-rollout protocol at a 0.5 fs timestep, 0.2 ps Langevin-NVT initialization, 1.0 ps NVE production, 5 fs sampling, deterministic common velocity seeds, and hard numerical diagnostics for NVE drift, minimum pair distance, force finiteness/magnitude, and NVT/NVE temperature stability.
- Add persistent protected-structure qualification: frozen periodic reference bonds, new-bond detection, protected-group displacement/bond/angle distortion, and a 50 fs default persistence window distinguish transient thermal excursions from genuine framework/motif damage. All common base/temperature cases are hard gates.
- Bind DYN physical pass/fail evidence back to TARGET-DATA2D Stage C so the two 30-epoch target-size finalists can finally resolve the production target size; after production-size training, DYN qualifies final-development seed candidates but leaves final ranking to SELECT2.
- Authenticate DYN restart evidence against RELAX/DEPLOY authorities, exact ML-IAP bytes, LAMMPS executable bytes/arguments, rollout policy/case membership, and trajectory/log bytes. Missing or stale deployment/runtime evidence fails closed.

## 0.20.174a0 - 2026-08-13

- Implement RELAX-VERIFY1 after PES qualification. Up to four candidate-independent PES base structures receive matched fixed-cell zero-K DFT relaxations and every PES-qualified target-only candidate is relaxed from the exact same bases with ASE FIRE, a 0.03 eV/A force ceiling, and a 500-step cap.
- Make protected periodic topology a hard safety authority. The generated LTA campaign preserves the explicit `framework` group; the generic verifier resolves any static profile group, compares minimum-image bonded-pair/coordination identities under a frozen 1.20 covalent-radius cutoff scale, treats periodic wrapping as equivalent, and rejects a DFT reference that breaks the protected topology itself.
- Add separate quantitative geometry fidelity gates: protected-group RMS/max displacement <= 0.15/0.40 A, bond RMSE/max error <= 0.08/0.20 A, angle RMSE/max error <= 8/20 degrees, fixed-cell strain norm <= 1e-4, and converged final forces. Every common base must pass; topology success cannot hide a distorted local minimum.
- Add restartable RELAX DFT request/collection provenance, candidate relaxed artifacts, campaign records, generated/example configuration controls, and advance successful TRAIN2 verification only to DYN-VERIFY2.

## 0.20.173a0 - 2026-08-13

- Implement PES-VERIFY1 as the first scientific physical-accuracy gate after deployment parity. The probe cohort is candidate-independent, inherited from DEPLOY-VERIFY1 correlation-block-balanced target evidence, and defaults to up to four bases x four generic bond/angle/coordination/strain modes with symmetric +/-0.04 A atomistic displacements or 1% strain plus one q=0 base point.
- Add a restartable fixed-geometry DFT request workflow. `verify` writes a common ExtXYZ/manifest/POSCAR tree and waits for labels; VASP auto-collection requires identical INCAR/KPOINTS/POTCAR bytes and unchanged requested geometries, while external labeled ExtXYZ requires an explicit DFT-protocol digest.
- Compare the untouched foundation baseline and every target-only deployment candidate against exactly the same DFT probes using centered projected-force increments, restoring-force direction, force-derived stiffness, energy curvature, and strain stress/energy curvature. PES-VERIFY1 v1 requires every generated mode to pass; failed candidates remain evidence and cannot advance.
- Persist immutable policy/probe/request/reference/foundation/candidate identities, expose PES configuration in generated and example campaign TOML, and advance successful TRAIN2 verification only to RELAX-VERIFY1.

## 0.20.172a0 - 2026-08-13

- Implement DEPLOY-VERIFY1 as the TRAIN2/EVAL2 deployment-numerical-parity gate. Only final-development EVAL2 winners are deployment candidates; CV-fold models remain evidence-only.
- Freeze a deterministic correlation-block-balanced deployment probe cohort and compare the exact selected multi-head checkpoint with its explicit target head against the exported target-only MACE model, then compare that target-only model against its ML-IAP LAMMPS `run 0` deployment representation.
- Persist target-head export identity, model/ML-IAP bytes, target-head/dtype/tolerance policy, exact probe membership, LAMMPS executable path and SHA-256, launch arguments, and run-0 prediction identity. Any stale executable/model/probe/EVAL2 authority fails closed and forces fresh parity verification.
- Wire TRAIN2 `verify` to DEPLOY-VERIFY1 and leave the overall verify stage waiting for PES-VERIFY1. Python-only export equality cannot substitute for ML-IAP/LAMMPS deployment parity; unavailable or failing deployment runtime is a hard gate failure.

## 0.20.171a0 - 2026-08-13

- Implement EVAL2 as the executable TRAIN2 target-first static checkpoint evaluator. New immutable target-role/evaluation-plan/checkpoint/metric/bootstrap/run records govern ranking while persistent checkpoint prediction caches remain the inference substrate only.
- Freeze leakage-safe target roles: CV runs use their internal checkpoint-monitor units; target-size/final-development runs use one common TARGET-DATA2A development complement disjoint from the largest nested candidate rung, never the outer monitor.
- Implement the target-only 3+2 shortlist, full target metric reduction (global/per-species/species-macro/tails/worst-stratum, focus/nonfocus groups, composition-centered relative energy, energy and stress where applicable), TRUE_DFT replay hard admissibility with zero ranking credit, deterministic bounded target-ranked rescue, and the 1 meV/A plus paired 2000-replicate/95%-CI/10-block uncertainty policy. A bootstrap result has decision authority only when its confidence interval and raw >1 meV/A point improvement favor the same candidate.
- Correct TARGET-DATA2D Stage-B eligibility to match the frozen 10-of-30 policy: only numerical/operational failure may remove a candidate at epoch 10. Final target thresholds and replay ceilings are diagnostic-only until the completed 30-epoch/full-evaluation stage.
- Wire TRAIN2 `evaluate` to EVAL2. Stage B evaluates the exact epoch-10 endpoint and advances TARGET-DATA2D using target evidence only; Stage C performs complete static checkpoint selection but remains pending physical VERIFY evidence before final target-size selection.

## 0.20.170a0 - 2026-08-13

- Implement TRAIN2B as the executable fixed-budget training runtime. The exact linear/cosine LR multiplier is applied before every optimizer update on one frozen full-trajectory update horizon; MACE validation-driven scheduler mutation and patience termination have no authority in TRAIN2.
- Implement authenticated 10-of-30 -> 30-of-30 continuation. Stage B is a durable successful pause, while Stage C restores live non-EMA parameters, EMA shadow state, RNG state, base-LR identity, update/structure geometry, and the raw checkpoint that carries optimizer state before continuing the original schedule.
- Persist per-epoch TRAIN2 runtime summaries/history with epoch/update/structure counts, normalized progress, phase, instantaneous LR, checkpoint/optimizer-state identities, target validation diagnostics, and the authenticated TRUE_DFT replay diagnostic stream. Replay remains diagnostics-only during training.
- Make TRAIN2 campaign execution stage-aware: Stage-A survivors receive 10-of-30 screening runs, Stage-B finalists can reopen successful 10-epoch executions for exact continuation, and selected production training completes only the selected-size 2 x (3 CV + 1 final) matrix. Historical adaptive training remains unchanged.

## 0.20.169a0 - 2026-08-13

- Implement TRAIN2A as a versioned target-first training-policy authority. New campaigns freeze separate `TrainingBudgetPolicy`, `LearningRateSchedulePolicy`, `CheckpointAdmissibilityPolicy`, and `CheckpointSelectionPolicy` records; historical adaptive-stop protocols retain their original schemas and digest semantics.
- Make TRUE_DFT replay degradation a hard foundation-relative admissibility constraint with zero positive checkpoint/seed ranking or tie-break credit. New checkpoint-selection policy schemas contain target observables only and use stable candidate identity for the final exact tie.
- Introduce v6 training-protocol and production-materialization identities for the complete TRAIN2 policy family, reject mixed historical/new controls, and keep absence of `policy_generation` as an explicit historical-campaign signal.
- Change newly generated campaign configuration to `policy_generation = "train2"` / `checkpoint_strategy = "train2_target_first"`, including frozen deterministic LR-policy parameters and target-first bootstrap/shortlist settings. TRAIN2 `train`, `evaluate`, and `verify` fail closed until TRAIN2B/EVAL2/SELECT2 own their runtime paths rather than silently using historical adaptive behavior.

## 0.20.168a0 - 2026-08-13

- Implement TARGET-DATA2E as an immutable production target-corpus decision/provenance authority. It can materialize only after TARGET-DATA2D reaches an authenticated `selected` outcome; waiting, failed, and bounded-ladder-nonconverged states cannot create a provisional production corpus.
- Freeze exact winning rung membership per label domain, TARGET-DATA2A partition/role lineage, TARGET-DATA2B coverage policy/family/radius/weight identities, all rung membership/evidence digests, FOUNDATION-AUDIT1 domain identity, full Stage-B/Stage-C evidence, and explicit 1 meV/A practical-equivalence comparison records.
- Add restart-safe campaign helpers that persist/reuse TARGET-DATA2E only after selection and fail closed on stale upstream evidence. Ordinary prepare receipts remain valid while Stage-B/C are pending; later TRAIN2/EVAL2/VERIFY gates must materialize/authenticate TARGET-DATA2E before the fixed-size production campaign.

## 0.20.167a0 - 2026-08-13
- Change the newly generated campaign default from three optimizer seeds to the intentional two-seed production geometry: `2 x (3 CV folds + 1 final-development fit) = 8` multi-head runs. Existing campaign files are not rewritten.
- Strengthen TARGET-DATA2D Stage-B/Stage-C evidence identity with optimizer-update count, structures presented, normalized schedule progress, instantaneous learning rate, wall-clock cost, frozen foundation/evaluation-role/TRAIN2-policy identities, and exact Stage-B checkpoint/optimizer ancestry for Stage-C continuation.

- Implement TARGET-DATA2D bounded target-size convergence authority: Stage A now applies the frozen TARGET-DATA2B coverage/extent/mandatory-support evidence across every TARGET-DATA2C label domain and retains the four smallest qualifying rungs, failing closed below three qualifiers.
- Add immutable 10-of-30 and 30-of-30 target-size training evidence schemas plus deterministic target-only practical-equivalence ordering. Stage-B replay is diagnostic-only; Stage-C replay and physical qualification are hard admissibility gates with zero ranking credit.
- Add deterministic anchored 1 meV/A equivalence bands, smaller-size preference, numerical-failure handling, and bounded-ladder non-convergence reporting when the largest qualified boundary remains materially better.
- Bind TARGET-DATA2D Stage-A authority into prepare/restart/preflight/train receipts. Legacy adaptive-stop training is explicitly not accepted as Stage-B/C evidence; TRAIN2/EVAL2/VERIFY gates must later provide exact schedule/restart/qualification evidence.
- Wire the shared `[target_data.size_convergence]` coverage metric/threshold/resolution/leave-one-out/Q01-Q99 policy into TARGET-DATA2B construction and restart identity instead of silently ignoring campaign overrides.

## 0.20.166a0 - 2026-08-13

- Implement TARGET-DATA2C as an immutable deterministic target-size ladder authority with the fixed 128/256/512/1024/2048/4096/8192 default geometry and explicit unavailable-rung records.
- Front-load required TARGET-DATA2B strata plus TARGET-DATA2A correlation-aware development intervals, then fill the ranked order with exact deterministic maximin FPS in a hierarchically normalized fused space spanning every required coverage family.
- Persist per-rung TARGET-DATA2B coverage evidence and separate mandatory-obligation pass/fail evidence, bind the ladder into prepare/restart/preflight/train authority, and leave Stage-A elimination to TARGET-DATA2D.

## 0.20.165a0 - 2026-08-13

- Implement TARGET-DATA2B reference-side empirical-mass coverage authority for MLFF target-size selection.
- Freeze correlation-unit-balanced reference weights, leave-one-out local kNN radii, robust Q01/Q99 extent guards, mandatory condition/event support strata, and distribution-fidelity diagnostics.
- Bind TARGET-DATA2B into campaign prepare/restart, preflight, and train authority checks without yet materializing the TARGET-DATA2C size ladder.

## 0.20.164a0 - 2026-08-13

- Implement FOUNDATION-AUDIT1 as an immutable target-side zero-shot baseline authority frozen before any target training. It authenticates the exact TARGET-DATA2A development domain, DATA5/DATA6/model-sweep lineage, foundation checkpoint bytes, metric policy, and structural-provider identities.
- Reuse completed DATA6 foundation predictions rather than launching a second MACE inference sweep. Persist global energy/force/stress errors, species-macro and per-species force RMSE, exact P90/P95/P99 atomic force-vector tails, component-error quantiles, and available pair-distance/angular/coordination-conditioned force summaries.
- Freeze finite-displacement and zero-K relaxation probe slots as `deferred_protocol` until PES-VERIFY1/RELAX-VERIFY1 define and materialize matched protocols; no physical-probe pass is fabricated. Bind the audit to the prepare restart receipt and make preflight/train fail closed on missing or stale audit authority.

## 0.20.163a0 - 2026-08-13

- Implement TARGET-DATA2A as an immutable lineage-aware target-size role freeze derived from DATA5. Only authenticated development units/frames may feed later target-size evidence; protected outer/CV/locked/challenge roles are excluded.
- Add fail-closed exact/declared near-duplicate correlation-family audits across independent outer and CV evidence roles, deterministic restart/migration authority, and prepare-receipt binding.

## 0.20.162a0 - 2026-08-12

- Fix the GFX3D terminal browser-face failure for multi-density scenes. The universal renderer previously handed every density HDR shell an independent standalone-scale face target and only afterward applied the generic 1,500,000-face browser cap. Four density fields × three HDR shells could therefore prepare successfully and then fail at serialization with millions of aggregate faces. GFX3D now allocates one post-replication density mesh budget across all requested shells before extraction/simplification, using the already-qualified density scene allocator and closed-loop fitter.
- Carry the scene-allocated face target into each sparse density shell's `DensityMeshFaceContract` and topology-preserving simplification policy. Scientific density fields, HDR mass fractions, and contour thresholds are unchanged; only display geometry is fitted. If topology-preserving mesh fitting remains irreducibly over budget, the universal viewer deterministically converts the least-visible/highest-cost shells to the existing HDR node-cloud representation rather than failing after expensive preparation.
- Make `--max-browser-faces` a genuine end-to-end override. The prior CLI constructed a custom density budget but the universal GFX3D preflight retained its unrelated 1.5M face cap. The override now propagates into the universal face allowance and scales the companion density vertex/HTML budgets coherently from the selected browser profile.
- Add render metadata for the density scene allocation plan and closed-loop fit/fallback report. Focused qualification: 97 tests passed across GFX3D CLI/contracts/dependencies/rendering, density scene allocation/fitting, sparse density meshes, and prior hardening regressions.

## 0.20.161a0 - 2026-08-12

- Complete GFX3D-HARDEN6 for the apparent post-admission density stall. Scheduled PAR-DENS field tasks previously re-entered `resolve_density_resource_limits()` under their 9/9/10-worker leases and could launch fresh worker-count-specific PAR-DENS1 FFT/BLAS calibrations concurrently. Those calibrations use process-global native thread controls and occurred before the first per-field progress callback. The authoritative scene `DensityTimeModel` is now context-bound and inherited by every scheduled/nested density helper, so production realization never silently recalibrates after task admission.
- Reuse the exact local-sparse Phase-B execution sidecar (packed CIC source, Gaussian stencil, block routing, and exact support atlas) during atomic-field realization. HARDEN5 rebuilt those already-authenticated objects a second time after the scheduler started. AUTO candidates that are not ultimately approved as `local_sparse` release their sparse sidecars before realization.
- Hoist support-atlas resource/time-model resolution out of the per-source-block FFT dilation loop. Each atlas now resolves the scene authority once rather than rebuilding identical derived resource limits hundreds of times.
- On the supplied Na-LTA `stride=500` four-density smoke with four CPU tokens, Phase-B planning completed at ~11.6 s, admitted tasks immediately emitted `field_realization`/`sparse_field_preparation ... reusing exact Phase-B ...`, all four fields completed at ~24.1 s, and source-scene preparation completed at ~24.5 s. No post-admission idle/calibration interval remained. Focused qualification: 154 tests passed.
- Remaining real density cost is now exposed rather than hidden: Phase-B planning is serial across species and took ~10.2 s in the smoke, while exact realization evaluates ~45.2-45.4 million direct pairs for each Si/Al/Na field and ~181.3 million for O because the adaptive framework-species bandwidths are only ~0.035-0.047 Å. These are separate optimization targets; scientific density bandwidth/grid semantics are unchanged in HARDEN6.

## 0.20.160a0 - 2026-08-12

- Add continuous GFX3D/PAR-DENS density progress before the existing pair-level convolution counter. Every local-sparse field now reports CIC aggregation, Gaussian-stencil resolution, packed-source construction, block routing, exact support-atlas construction, and pre-convolution completion under its stable field key.
- Instrument exact support-atlas realization with source-block progress, selected dilation backend, live worker count, finalization/CSR-build notice, and realized target block/node totals. Progress is execution-only and does not affect scientific/cache identity.
- Add a five-second PAR-DENS scheduler heartbeat while admitted field futures are still running, including active/pending counts and current per-field worker allocations, so a long kernel cannot leave the CLI apparently frozen at `density_scheduler [0/N fields]`.
- Real Na-LTA four-density `stride=500` smoke reached `density_realization [4/4 fields]` with concurrent atlas, direct-pair, worker-reallocation, and scheduler-heartbeat output. Focused qualification: 81 tests passed (60 density-path + 21 GFX3D CLI/hardening).

## 0.20.159a0 - 2026-08-12

- Complete GFX3D-HARDEN4 for the apparent PAR-DENS3 density-realization stall. The scheduler itself was not deadlocked: large adaptive local-sparse GFX3D fields entered the direct tiled executor, but that executor ignored cooperative worker leases and performed its target-coordinate/packed-lookup work on one CPU core per field. Direct sparse tiles remain CPU work; GPU execution remains optional and applies only to FFT tiles selected by the already-approved execution plan.
- Parallelize direct sparse realization *inside each already-approved pair chunk*. Contiguous source-row slices resolve periodic targets and packed destinations concurrently, then the existing stable grouped floating-point reduction executes once in the original canonical pair order. Aggregate pair count and Phase-B scientific/execution ownership are unchanged, and regression coverage requires bitwise-equal packed density values versus one-worker realization.
- Extend the direct transient-memory contract from 96 to 112 bytes per approved pair to conservatively price the shared mapped-index buffer used by the worker-parallel path. Parallelism therefore consumes scheduler-granted CPU tokens without multiplying pair-chunk workspace by worker count.
- Add scheduler admission/completion reporting and low-level sparse-realization progress. Long fields now report task backend, granted workers, memory peak, direct-pair progress, live worker growth, and FFT-tile progress. Direct-only fields explicitly report that GPU activity is not expected.
- On the supplied Na-LTA dump with `stride=500` in the 3-CPU-token qualification container, one Na-density realization fell from about 4.8 s in 0.20.158a0 to 3.8 s, while the four-density preset realization fell from about 20.4 s to 16.8 s. The largest O field automatically grew from one worker to three after sibling fields completed. A forced-direct 8.42-million-pair synthetic regression measured 0.675 s serial versus 0.495 s with four workers (1.36x), with bitwise-identical packed values.

## 0.20.158a0 - 2026-08-12

- Complete GFX3D-HARDEN3 for long-trajectory atomic connectivity and mean-graph preparation. General minimum-image geometry now carries exact integer image labels through the unimodular Minkowski transform instead of reconstructing them afterward through an ill-conditioned inverse/round step; the supplied full Na-LTA trajectory no longer fails in `atomic_mean_graph` with `Could not reconstruct minimum-image vectors from integer image shifts`.
- Replace the object-heavy per-frame connectivity canonicalization/transition hot paths with array-oriented state construction and linear sorted-edge differences while preserving canonical state digests. Bound the raw canonical-state reuse cache to 512 entries so highly fragmented trajectories cannot retain millions of `AtomicEdgeKey` objects as cache keys.
- For fixed fully periodic LTA cells, use the exact cell-list backend with a cached cell/cutoff metric stencil. Heterospecies LTA cutoff registries sharing oxygen as the common species are evaluated in one exact star-shaped neighbor request and then pair-filtered, rather than repeating minimum-image neighbor searches for Si-O, Al-O, and each mobile-ion/O pair.
- When both framework topology and atomic connectivity are requested, compute the broader hysteretic atomic graph once and project the framework pair subset exactly. Qualification on the supplied trajectory preserves framework state digests, frame-state IDs, and transitions versus a separate direct framework computation, while removing the second trajectory-wide geometry pass and the unbounded cross-pass geometry cache introduced in HARDEN2.
- Add a certified fast path for periodic Fréchet means used by atomic mean-graph aggregation. A single-start solution is accepted only when all weighted samples are proven to lie within a conservative strong-convexity ball of the periodic torus; ambiguous/mobile distributions retain the previous exact multi-start/weighted-medoid fallback.
- On a 400-frame real Na-LTA slice with the same scientific definition, cold full-connectivity preparation fell from about 6.59 s in 0.20.157a0 to 1.59 s in 0.20.158a0 with an identical connectivity identity SHA-256. A full 10,001-frame framework + connectivity + Na-trajectory source preparation completed without the former MIC failure: full atomic connectivity resolved in about 41.5 s, framework projection in about 1.3 s, and the mean-graph stage completed in a few seconds. Focused qualification: 191 tests passed.

## 0.20.157a0 - 2026-08-12

- Harden the GFX3D raw LTA dependency source as a true single-flight preparation owner: one failing science preparation is latched and shared across product requests, and CLI diagnostics now preserve the complete causal exception chain instead of reporting only the first product wrapper.
- Repair renderer-neutral sparse atomic-density output by dispatching packed sparse fields through the existing sparse-mesh/node-cloud machinery and enforcing the aggregate GFX3D browser budget rather than assuming a dense `.values` array.
- Stream positive LAMMPS `start`/`stop`/`stride` selection while scanning dump files instead of materializing every discarded atom table. On the supplied 10,001-frame / ~183 MiB Na-LTA dump, `stride=500` retained the same 21 frames and source-frame count while reducing isolated read time from about 9.17 s to 3.03 s and peak RSS from about 1.63 GiB to 253 MiB.
- Reuse exact atomic-connectivity pair geometry between framework-topology preparation and the subsequently requested full atomic-connectivity layer; preserve the existing hysteretic scientific definitions.
- Carry the compact Phase-B adaptive density numerical plan into density realization so registration/numerical policy is not resolved twice; coordinate samples are intentionally not duplicated in the retained plan.
- Add staged GFX3D preparation progress plus fail-fast diagnostics for implausible framework T-O calibration and highly fragmented topology catalogs, making incorrect LAMMPS type maps or damaged frameworks visible before they masquerade as a generic dependency failure.
- Preserve the historical `lta-mixed-alkali-density` preset contract (one density field per present supported species); use explicit `--layer density:Na`/Li/K for substantially cheaper mobile-ion-only views. Focused qualification: 187 tests passed across GFX3D, LAMMPS, framework/topology, sparse density, and density preprocessing.

## 0.20.156a0 - 2026-08-11

- Complete GFX3D-HARDEN1 for existing framework/connectivity/trajectory/density plotting: authenticated automatic topology-cache reuse, renderer-neutral source products, scene-owned cell display, strict camera/periodic validation, trajectory hover parity, and browser-budget preflight before periodic materialization.
- Add dominant-only GFX3D handling for partitioned topology catalogs while leaving the legacy full-category API unchanged.
- Vectorize static-cell projected framework geometry across selected frames; the supplied 10,001-frame Na-LTA fixed-topology framework preparation completes in about 11.23 s, with the projected registration stage about 0.5 s.
- Repair the stale PAR-DENS version assertion and add focused hardening/equivalence regression coverage.

## 0.20.155a0 - 2026-08-11

- Added append-only conventional-MLCV optimizer-seed extension via `extend-seed --seed N`, including exact same-fold authentication, targeted new-seed training, reuse of parent run-local evaluation evidence, and campaign-level AGG1/FINAL1 rebuild.
- Added `train --training-mode/--seed/--selection-size` filters.
- Seed extension now archives superseded campaign-level authority and fails closed after VERIFY1/production freeze. Verified promoted DATA7 artifacts are re-registered in-process so optimizer-only extensions reuse the exact fold-local feature fits even after transient cache cleanup.

## 0.20.154a0 - 2026-08-11

- Fix MLCV-AGG1 outer-fold evaluation for multi-head replay runs. AGG1 is deliberately target-only and reuses the authoritative full-replay result frozen by SELECT1, but the generic checkpoint evaluator previously inferred from the run's replay lineage that replay inputs were mandatory and raised `Replay evaluation requires an evaluation monitor and foundation baseline model.`
- Add a narrow `allow_target_only_evaluation` preparation authorization. It is accepted only together with an explicit target-monitor override and rejects simultaneous replay-monitor inputs, keeping normal replay-aware evaluations fail-closed.
- Record `evaluation_scope:authorized_target_only` in the resulting evaluation notes for auditability. No checkpoint, replay baseline, SELECT1 score, DATA8 membership, or training evidence is changed.

## 0.20.153a0 - 2026-08-11

- Fix MLCV checkpoint reconstruction for qualified FP32/FP64 mixed-buffer MACE state dictionaries; learned-model dtype is no longer incorrectly inferred by demanding that every floating state tensor share one dtype.
- Preserve exact per-key checkpoint/template shape and dtype verification for direct restoration, so valid mixed-buffer states are restored without silent casts.
- Resolve legacy restart-export execution dtype from a uniform checkpoint when possible, otherwise from immutable DATA8 `default_dtype` for states containing only qualified FP32/FP64 tensors; unsupported floating precisions still fail closed.
- Existing DATA8 bundles and trained checkpoints remain reusable; no retraining or DATA8 regeneration is required.
- Qualification: 116 focused checkpoint/MLCV tests passed with one external-data skip; all 11 real/synthetic checkpoint materialization tests passed against MACE 0.3.16.

## 0.20.152a0 - 2026-08-11

- Fix MLCV-SELECT1 bundle-scoped DATA8 replay path resolution: authoritative TRUE_DFT `R_full` is now rebased from its immutable DATA8 staging path onto the promoted runtime tree before existence/hash validation.
- Preserve the existing `R_full` bytes, SHA-256 authority, monitor lineage, checkpoint catalog, and all training evidence; existing DATA8 materialization and trained runs remain reusable.
- Audit SELECT1/AGG1 artifact ownership: job-scoped target/outer artifacts use the job resolver, while bundle-scoped replay artifacts use the runtime rebase resolver; no additional direct replay-full path misuse remains in the conventional-CV evaluator.
- Add regression coverage preventing SELECT1 from bypassing DATA8 runtime rebasing for `R_full`.

## 0.20.151a0 - 2026-08-11

- Fix MLCV-SELECT1 job-scoped DATA8 path resolution: `target_checkpoint_full.xyz` (`V_i_full`/`D_full`) is now resolved beneath the owning `jobs/<job_id>/` directory instead of incorrectly beneath the DATA8 bundle root.
- Fix the same latent MLCV-AGG1 path-resolution defect for job-scoped `fold_evaluation.xyz` outer-CV artifacts.
- Preserve immutable DATA8 artifact digests and existing training/evaluation evidence; this is an evaluation-side runtime-path hotfix and does not require DATA8 regeneration or retraining when the promoted files are intact.
- Add regression coverage for job-scoped relative paths, legacy absolute staging-path rebasing, and real MLCV-MON1 DATA8 target/outer artifact resolution.

## 0.20.150a0 - 2026-08-11

- Complete GFX3D-5 universal renderer-neutral composition: built-in layers emit generic primitives and the common Plotly backend contains no built-in science-family dispatch.
- Remove renderer-only `source_scene` references from prepared built-in layer products.
- Add named layer visibility groups, render priority, reproducible camera presets, scene-wide periodic display replication, universal view controls, and generic browser payload/budget accounting.
- Extend `mdstats-3d` with camera, periodic-image, cell, visibility, axes, background, and viewport controls plus TOML layer priority.
- Requalify the supplied 300 K Na-LTA stride-500 scene: scientific products are exactly identical to 0.20.149a0; a 2x1x1 renderer-neutral view produces 20 traces and 149,896 density faces with explicit payload evidence. Focused qualification: 83 passed.

## 0.20.149a0 - 2026-08-11

- Complete GFX3D-4 with product-level scientific dependency planning for framework topology, atomic connectivity, atomic trajectory, and atomic density instead of one monolithic `FrameworkDynamicsScene` dependency key.
- Add scene-context single-flight caching so concurrent identical dependency misses execute the resolver once, with deterministic dependency-plan collation and cache/timing state excluded from scientific identity.
- Add the lazy LTA GFX3D dependency source: requested products have distinct dependency authority while the existing qualified framework-dynamics scientific owner may batch compatible work once internally; manifest-only mode performs no scientific preparation.
- Requalify the supplied 300 K Na-LTA source at stride 500: all four product keys are served by one qualified source preparation, omitted layers omit their product dependency, and 0.20.148a0 versus 0.20.149a0 mean-framework/Na-trajectory/Na-density hashes plus density-planning authority are exactly identical. Focused GFX3D/framework/renderer qualification: 74 passed.

## 0.20.148a0 - 2026-08-11

- Complete GFX3D-3 with the packaged `mdstats-3d` command and source-tree `tools/mdstats-3d.py` launcher.
- Add strict TOML scene configuration, layer shorthand, source-aware LTA compatibility preset, deterministic precedence, canonical manifest-only mode, and protected HTML/manifest output.
- Convert `examples/plot_lta_mixed_alkali_density.py` into a compatibility shim over the universal CLI while retaining its historical input helpers and default output behavior.
- Add the formal GFX3D CLI specification, concise user guide, and Na-LTA TOML example. Focused GFX3D/legacy qualification: 83 passed; bounded real Na-LTA CLI smoke completed on 21 stride-500 frames and produced a 6.5 MiB self-contained HTML artifact.

## 0.20.147a0 - 2026-08-11

- Complete GFX3D-2 with independent registered framework-topology, atomic-connectivity, atomic-trajectory, and density layer adapters over current qualified scientific products.
- Add shared-context layer preparation with one deduplicated prepared-scene dependency, scientific trajectory/connectivity filtering, and fail-closed density field selection.
- Add a common layer-keyed Plotly composer supporting arbitrary combinations and multiple instances per layer type while retaining the existing legacy renderer as the backend compatibility engine.
- Qualify all 15 non-empty initial layer combinations plus duplicate instances; focused GFX3D/framework/graph qualification: 62 passed.

## 0.20.146a0 - 2026-08-11

- Added GFX3D-1 universal renderer-independent 3-D scene/layer contracts under `mdstats.graphics3d`.
- Added canonical selection/dependency/identity/manifest contracts and deterministic internal layer registry.
- Added renderer-neutral primitive and generic layer-keyed render-result contracts.
- Added compatibility adapters for current framework-dynamics scene/render results without changing scientific plotting behavior.
- Added the canonical GFX3D architecture manual and initial CLI specification skeleton.
- Focused GFX3D/framework/graph qualification: 42 passed.

## 0.20.145a0 - 2026-08-10

- completed PAR-DENS6 end-to-end density qualification and production auto-tuning; the CPU production path is now authorized on the supplied 10,001-frame Na-LTA stress trajectory;
- added hardware-local execution-only density auto-tuning for bounded field concurrency, chunk depth, FFT worker caps, and CPU/GPU selection without allowing scientific resolution/operator changes;
- froze hybrid direct/FFT tile ownership at scene-level Phase-B so live cooperative worker leases can no longer re-plan floating-point reduction paths; this removes the one-ulp O-field worker-count discrepancy found during 10,001-frame qualification;
- added exact worker-count regression coverage for approved hybrid plans and persisted execution-plan authority separately from scientific field identity;
- bounded the provisional basin-prepass triclinic MIC workspace by item blocks, preserving vectorwise minimum-image/basin semantics while avoiding trajectory-wide image-candidate allocation;
- carried optimized sparse-CIC transient workspace into Phase-B scheduler admission, released dead geometry temporaries before stable reduction, and prioritized largest-peak independent fields during admission;
- added PAR-DENS6 stage/RSS/CPU/scheduler telemetry and an authenticated three-scale Na-LTA qualification record with fresh-process timing legs;
- final Na-LTA qualification: 101/1001/10001-frame fixed 64^3 Na/Si/O operator, max |Delta rho| = 0 for all species versus the one-worker reference, identical content identities/integrals/HDR thresholds/executor partitions, median 10,001-frame total-wall speedup 1.1136x, and measured/declared RAM use within the dynamic 80% budget;
- CUDA remains optional and hardware-conditional; this CPU-only packaging host does not claim a GPU throughput factor.

## 0.20.144a0 - 2026-08-10

- Implement PAR-DENS5 as an optional FP64 CUDA density execution backend with runtime-only PyTorch discovery, no new hard GPU dependency, automatic complete CPU fallback, and execution metadata separated from scientific density identity.
- Enforce the GPU resource contract: usable device memory is 80% of currently free VRAM, host staging remains under the PAR-DENS2 host budget, and at most one major scheduled density field owns a GPU at once while batching its tiles internally.
- Add transfer/setup-aware GPU admission plus FP64 CUDA paths for dense CIC deposition, periodic/spectral Gaussian FFT operations, binary support-mask FFT dilation, and hybrid sparse/tiled FFT convolution; direct grouped sparse accumulation remains on the qualified CPU path.
- Requalify the supplied 300 K Na-LTA trajectory on 101 stride-100 frames: GPU-off and auto-on-a-no-CUDA-host executions are bit-identical for Na/Si/O packed fields, integrals, content identities, and HDR thresholds; real-CUDA FP64 equivalence tests are included and conditionally skipped on this packaging host. PAR-DENS6 is now the next density gate.

## 0.20.143a0 - 2026-08-10

- Implement PAR-DENS4 parallel trajectory preprocessing: framework graph reconstruction/lifting and periodic atomic-mean calculations run through bounded scheduler leases with deterministic frame/item-order validation and collation.
- Split hysteretic connectivity into frame-parallel stateless geometric candidate generation plus a deterministic collection-frame-order hysteresis fold; serial and parallel paths preserve exact connectivity-state and transition identities.
- Add an execution-only `AtomicConnectivityGeometryCache` so compatible framework-only and full atomic-connectivity passes reuse exact periodic neighbor requests without changing scientific identity or provenance.
- Hoist trajectory-wide connectivity state lookup and reusable framework geometry outside topology-category loops; independent topology-category scene preparation is admitted concurrently through the single PAR-DENS2 CPU/RAM authority.
- Requalify the supplied 300 K Na-LTA source on 101 stride-100 frames: warm framework-to-full neighbor-geometry reuse reduces the broader connectivity pass from 1.730 s to 1.024 s versus a cold full pass (1.689x) with identical states. Four-worker hysteretic candidate generation remains exact but is overhead-dominated for this small 168-atom/frame case, so parallelism is bounded/optional rather than treated as a universal speedup. PAR-DENS5 is now the next density gate.

## 0.20.142a0 - 2026-08-10

- Implement PAR-DENS3 concurrent density realization through the PAR-DENS2 global scheduler: independent atomic/framework fields execute concurrently only when aggregate CPU/RAM admission permits, with deterministic construction-order collation and dynamic CPU return to surviving fields.
- Parallelize sparse support-atlas source-block construction in bounded memory-aware groups, partition target-owned direct realization by destination block, replace hot repeated scatter with grouped/segmented reductions where practical, and standardize production FFT calls on worker-aware `scipy.fft` using the live scheduler lease.
- Advance density-scene plans to v3 with a more complete worker/storage/executor-neutral scientific approval projection while preserving historical v1 resource-sensitive and v2 PAR-DENS2 digest semantics. Execution-specific hybrid identities, worker counts, backend choices, and calibrated costs remain separately auditable.
- Qualify scalar/support/HDR/mesh worker invariance across serial and parallel dense/sparse paths. The complete density-focused suite passes 351 tests with one optional interactive skip.
- Requalify the supplied 300 K Na-LTA trajectory: a 101-frame/64^3 sparse Na/Si/O scene admits three concurrent fields at four threads, remains bit-identical to one-thread execution, preserves field/scientific identities and HDR levels, and reduces scene preparation from 9.209 s to 8.304 s in the qualification environment (1.109x). PAR-DENS4 is now the next density gate.

## 0.20.141a0 - 2026-08-10

- Close PAR-DENS1 with execution-faithful irregular direct-reduction/support-atlas and worker-aware SciPy FFT calibration; the density time model advances to v3 and wall-time ranking remains advisory.
- Implement PAR-DENS2 `DensitySceneScheduler`: one LD10 CPU/RAM pool, aggregate peak-memory admission, minimum/preferred worker leases, dynamic CPU return, parent ownership, bounded thread/process helpers, and deterministic collation.
- Integrate scheduler authority into density-scene realization without enabling PAR-DENS3 field concurrency; per-field contracts are validated while the existing serial scientific path is preserved.
- Advance density-scene plans to v2 with worker/backend/timing-neutral scientific approval IDs plus separate complete execution-plan IDs; historical v1 resource-sensitive digests retain their old semantics.
- Qualify the supplied 300 K Na-LTA trajectory on a bounded 21-frame/64^3 Na-density smoke: 1-thread and 4-thread fields are bit-identical and share the same scientific approval ID. PAR-DENS3 is now the next density gate.

## 0.20.139a0 - 2026-08-10

- Implement MLCV-MIGRATE1 and close the nine-gate conventional-CV correction. New campaigns freeze the distinct `mlcv_nested_cv` lifecycle authority instead of sharing historical `adaptive_topk` identity.
- Bind lifecycle authority to immutable campaign plus ROLE1/MON1 catalog digests and the run-local top-five contract; TOML edits cannot redirect the same campaign into historical/fold-winner evaluator semantics.
- Recognize transitional 0.20.131-0.20.138 MLCV campaigns created with the `adaptive_topk` spelling and migrate them without reranking, outer-fold reevaluation, physical reverification, or locked-E reuse as a selector.
- Freeze the complete ROLE1-through-VERIFY1 production evidence graph, expose schema-neutral `mlcv_deployment` storage authority, and preserve historical adaptive/committee/multi-fidelity evidence read-only.
- Protect MLCV top-five checkpoints and frozen run representatives from STOR2 compaction; keep committee/production model bytes protected by the verified MLCV protocol freeze.
- Reconcile already-completed 0.20.138 VERIFY1 campaigns on the first 0.20.139 verify touch by authenticating and reusing their published model and locked-E evidence.

## 0.20.138a0 - 2026-08-10

- Implement MLCV-VERIFY1: physical-verification fallback is restricted to qualified FINAL1 final-seed representatives in deterministic final-score order; fold models remain ineligible.
- Freeze the first bounded-NVE passer and permanently end physical fallback before any locked post-freeze test is exposed.
- Activate/materialize locked target test `E` only after the physical winner is frozen, evaluate it target-only on the exact frozen exported bytes, and prohibit seed/checkpoint fallback from locked-test evidence.
- Publish `models/production_best.model` only after the frozen physical passer also satisfies one-shot locked `E`; locked-test failure records campaign failure/review evidence without publishing another model.
- Add `fallback_to_next_qualified_final_seed = true` for new MLCV campaigns while preserving the historical ADAPT-VERIFY1 fallback option.
- Freeze MLCV physical stability thresholds, model dtype, locked-E target ceiling, and retained safety-metric policy into immutable verification authority.

## 0.20.137a0 - 2026-08-10

- Implement MLCV-FINAL1 conventional final-seed authority: only final-development SELECT1 representatives can enter production comparison.
- Treat configured-CV failure as a recipe-level production block; zero-fold campaigns remain explicit `cv_not_performed`.
- Deterministically select one production verification candidate from qualified final seeds using authoritative `D_full + R_full` score and tie-breaking.
- Export all and only qualified final-seed target-head models as the active-learning committee; fold models remain production-ineligible.
- Add `seed_mode = optimizer_only` default and optional deterministic `optimizer_and_cv_partition` robustness sampling without altering final-development membership.
- Keep verified production publication and locked-test activation deferred to MLCV-VERIFY1.

## 0.20.136a0 - 2026-08-10

- Implement MLCV-AGG1 conventional cross-validation aggregation: evaluate each frozen fold representative exactly once on its complete untouched outer CV target fold.
- Keep outer-fold evidence selection-inert: an outer result can pass/fail the fold but cannot select another epoch or checkpoint.
- Require all configured folds per seed to have a SELECT1 representative and satisfy the configured outer target force-RMSE ceiling; mark failures explicitly.
- Report target, representative TRUE_DFT `R_full` replay, and combined fold statistics separately as mean/sample-SD/min/max/range/worst-fold; keep dispersion diagnostic-only.
- Reuse authenticated SELECT1 replay evidence rather than rotating or re-inferring replay data, and mark every fold representative permanently production-ineligible. MLCV-FINAL1 remains the next gate.

## 0.20.135a0 - 2026-08-10

- Implement MLCV-SELECT1: fully evaluate every run-local RANK1 top-five candidate on role-correct complete target validation plus complete TRUE_DFT replay validation, then freeze exactly one representative or explicit no-representative result per run.
- Enforce conventional CV authority: fold checkpoint selection uses `V_i_full` and never the untouched outer fold; final-development selection uses `D_full`; both use `R_full`.
- Apply authoritative target/replay force-RMSE ceilings and configured energy/focus/stress/worst-condition gates before weighted full-score ranking.
- Make `target_stop_fraction` and `replay_stop_multiplier` TOML-configurable again with defaults 0.80/1.20; actual lightweight stop boundaries remain derived from the standard full criteria and score weights.
- Render diagnostic stop labels from the configured factors instead of hard-coded 80%/120% text.
- Route new MLCV campaigns through SELECT1 while preserving historical ADAPT-EVAL1 authority for older pre-MLCV campaigns.

## 0.20.134a0 - 2026-08-10

- Implement MLCV-RANK1: retain up to five deterministic finite lightweight checkpoints independently per training run with zero new inference.
- Make the STOP1 margin relationship explicit and regression-tested: target success is `0.80 * T_full_max`; replay exhaustion is `1.20 * R_full_max`, with `R_full_max = (w_T / w_R) * T_full_max`.
- Preserve historical lightweight-run-champion v1 evidence; new ranking evidence uses schema v2 with candidate-limit and pre-truncation rankable-count metadata.
- Keep rank-one compatibility fields temporarily for the historical evaluator until MLCV-SELECT1 consumes the retained top-five set.

## 0.20.133a0 - 2026-08-10

- Implement `MLCV-STOP1`: 24 meV/A target-success and 36 meV/A replay-exhaustion at default 1:1 weighting are lightweight stopping heuristics only; the 30 meV/A target/replay references no longer disqualify lightweight checkpoints.
- Add `minimum_epochs_before_adaptive_stop = 3` to new campaigns; adaptive target/replay margins cannot terminate earlier, while `max_num_epochs = 30` remains an independent hard ceiling.
- Move foundation replay-feasibility evidence to a one-time complete TRUE_DFT `R_full` validation before epoch 0, persist the frozen RMSE plus authenticated replay-artifact SHA-256, and remove the temporary full loader before the epoch loop.
- Preserve exact restart behavior: a frozen foundation baseline avoids repeated `R_full` inference and a durable terminal stop boundary executes no extra training epoch.
- Advance adaptive-stop policy/state serialization to v2 while preserving v1 policy identity, digest, and historical lightweight 30/30 behavior for old campaigns.
- Correct stale conventional-CV documentation to the current three-seed default (`3 x (3 folds + 1 final) = 12` jobs).
- Deliberately leave run-local top-five ranking/full selection/CV aggregation/final export semantics for `MLCV-RANK1` and later gates.

## 0.20.132a0 - 2026-08-10

- Implement `MLCV-MON1`: CV fold training now monitors deterministic `V_i_light` subsets of nested `V_i_full`; final runs monitor `D_light` subsets of `D_full`; outer CV folds remain untouched by checkpoint selection.
- Stage complete independent TRUE_DFT replay validation as `R_full` and deterministic <=512-configuration `R_light` for per-epoch monitoring, with immutable light/full lineage in `mdstats.mlcv-monitor-catalog.v1`.
- Materialize a deterministic <=256-configuration target-training diagnostic subset for every job and evaluate it each MACE validation epoch through the target head under the selection-inert `target_train_diagnostic` label.
- Persist per-run JSON/CSV/PNG training diagnostics from already logged MACE metrics without reporting-time model inference.
- Advance DATA8 to schema v5 / parser `0.20.132a0` while preserving historical readers.
- Correct the shipped static `campaign.toml.example` to match the already-active three-seed initialization default (`3 x (3 folds + 1 final) = 12` multi-head runs) and add regression coverage against future template/example drift.
- Deliberately leave STOP1/RANK1/full-selection/export semantics unchanged for the later MLCV gates.

## 0.20.131a0 - 2026-08-10

- Implement `MLCV-ROLE1`, the first conventional-CV correction gate, without yet changing monitor/stopping/ranking behavior from the completed adaptive path.
- Add typed MLCV statistical roles and operation guards: outer CV and locked-test evidence now fail closed if passed to checkpoint stopping, checkpoint ranking, or top-K checkpoint-selection APIs.
- Freeze immutable DATA5-derived role lineage for fold gradient training, nested checkpoint selection, outer CV evaluation, final validation `D`, and locked test `E`, bound to DATA5 partition/policy/catalog/CV digests.
- Freeze replay-gradient versus replay-validation lineage separately; authoritative attached replay validation must be TRUE_DFT and geometrically disjoint from replay-gradient training data.
- Persist `mlcv_role_catalog.json` and embed its digest-bearing evidence in DATA8 v4 while retaining readers for historical DATA8 v1-v3 payloads.
- Reduce newly initialized default campaigns from four to three optimizer seeds: multi-head replay now defaults to `3 x (3 CV folds + 1 final) = 12` training jobs; existing campaign identities remain unchanged.
- Repair the outer campaign-evaluation MACE/PyTorch warning-condensation wrapper so setup-time warnings are condensed as intended rather than leaking before the evaluator enters its inner adaptive path.

## 0.20.130a0 - 2026-08-10

- Record a documentation-only nine-gate `MLCV-ROLE1` through `MLCV-MIGRATE1` correction roadmap; executable 0.20.129 adaptive behavior is unchanged in this release.
- Restore conventional nested-CV semantics: fold checkpoint selection uses a training-side nested monitor, while the rotating outer fold is touched only after the fold representative is frozen.
- Reserve 80%/120% target/replay margins for lightweight stopping, move absolute 30 meV/A acceptance to full validation, and plan run-local top-five full checkpoint selection without lightweight hard-threshold disqualification.
- Restrict future production competition to full-development final-seed representatives; fold models become CV evidence only, while qualified final seeds may form an active-learning committee.
- Define `D` as final model-selection validation and locked `E` as one-shot post-freeze evidence; add planned per-run training/target/replay diagnostic plots and explicit seed/partition semantics.

## 0.20.129a0 - 2026-08-09

- Refine newly initialized MLFF campaigns to use multi-head replay fine-tuning as the sole enabled default; naive/native target-only fine-tuning remains fully configurable but opt-in.
- Reallocate the unchanged nominal 16-job default budget to four optimizer seeds, each with three common cross-validation folds plus one final-development fit (`4 x (3 + 1)`).
- Preserve restart/backward compatibility for existing explicit per-method TOML and historical shared `modes`/`seeds` configurations; no adaptive stopping, ranking, evaluation, verification, threshold, monitor, or precision semantics change.
- Update generated/example TOML, the campaign guide, release metadata, and regression tests to freeze the new initialization policy.

## 0.20.128a0 - 2026-08-09

- Implement ADAPT-MIGRATE1 and close the seven-gate adaptive MLFF revision with schema-neutral protocol-freeze authority plus immutable adaptive migration evidence.
- Reconcile completed 0.20.127 adaptive freeze aliases without rerunning scientific work or deleting historical EVAL-MF/committee evidence; ambiguous dual authority fails closed.
- Bind evaluator semantics to immutable campaign protocol identity so adaptive campaigns cannot regain historical EVAL-MF authority, and historical campaigns cannot be silently reinterpreted as `adaptive_topk`.
- Make post-freeze adaptive evaluation immutable/reusable, require schema-valid freeze authority for consequential storage actions, and keep STOR1 reporting read-only via SQLite `mode=ro`.
- Preserve all existing scientific thresholds, monitor sizes, binary learned-model dtype semantics, FP64 scientific arithmetic, storage ownership boundaries, and historical record readability.

## 0.20.127a0 - 2026-08-09

- Implement ADAPT-VERIFY1 score-ordered deployment verification: verify the best fully admissible ADAPT-EVAL1 candidate first and deterministically fall back to the next already fully evaluated candidate only after a hard verification failure.
- Publish exactly one verified target-head model and require its bytes/SHA-256 to be identical to the internal artifact that passed bounded NVE; adaptive fold winners are deployed directly rather than wrapped in a synthetic historical committee.
- Preserve binary learned-model precision through verification/export (`single` FP32, `double` FP64) while keeping mdstats-owned MD state, reductions, drift regression, scoring, and reporting hard-coded FP64.
- Add content-addressed restartable NVE-case evidence plus immutable adaptive verification, deployment-model, and protocol-freeze records; fallback introduces no new target/replay evaluation.
- ADAPT-MIGRATE1 remains the final adaptive-revision closure gate for schema/restart/storage migration and broad historical qualification.

## 0.20.126a0 - 2026-08-09

- Implement ADAPT-EVAL1 top-K authoritative full evaluation and make `adaptive_topk` the generated production checkpoint strategy; historical EVAL-MF strategies remain readable/selectable for compatible old campaigns.
- Materialize the complete common DATA5 outer-monitor target domain separately from the 256-frame online monitor and evaluate finalists on that full target domain plus the complete configured independent TRUE_DFT replay validation/monitor domain.
- Make naive and multi-head replay lightweight scores comparable by evaluating the fixed 512-frame true-replay monitor through the naive target head as validation-only evidence, without replay gradients or an added trainable head.
- Fully evaluate at most five run champions initially, enforce target/replay plus retained safety gates before weighted scoring, and purchase deterministic next-five rescue batches only while no admissible candidate exists.
- Preserve each candidate's binary learned-model inference dtype while retaining FP64 mdstats reductions/statistics; keep foundation-relative replay degradation as a diagnostic rather than the default hard selector.
- ADAPT-VERIFY1 remains the next gate for final verification, fallback, and export.

## 0.20.125a0 - 2026-08-09

- Implemented ADAPT-RANK1 zero-new-inference lightweight ranking from persisted ADAPT-STOP1 epoch metrics and the frozen checkpoint catalog.
- Added weighted target/replay force-RMSE scoring with hard target/replay candidate boundaries applied before ranking; default 1:1 scoring is the arithmetic mean.
- Freeze exactly one `lightweight_run_champion.json` per run with admissible epochs, using deterministic target/replay/epoch/SHA tie breakers; runs with no admissible epoch persist an explicit no-champion outcome.
- Bind lightweight ranking evidence to run/protocol/stop-state/catalog/common-monitor lineage and support exact reconciliation without opening or deserializing checkpoint models.
- ADAPT-EVAL1 remains pending; EVAL-MF is still the production evaluator until the next gate retires successive halving.

## 0.20.124a0 - 2026-08-09

- Implemented ADAPT-STOP1 criterion-driven MLFF training termination using the fixed common
  ADAPT-MON1 monitors with no additional inference.
- Added the 30 meV/A default target force-RMSE boundary, weight-derived replay boundary, 0.80
  target-success margin, 1.20 replay-exhaustion margin, and 30-epoch hard ceiling.
- Added pre-epoch-0 true-replay foundation-baseline feasibility validation and an explicit override
  for deliberately replay-heavier policies.
- Added durable `adaptive_training_stop.json` evidence, fail-closed exact restart semantics, and
  terminal-restart finalization without an extra training epoch.
- ADAPT-RANK1/ADAPT-EVAL1 remain pending; EVAL-MF is still the production evaluator.

## 0.20.123a0 - 2026-08-09

- Implement ADAPT-MON1 fixed common online validation evidence: new campaigns use one deterministic 256-configuration target monitor shared across all competing runs and one deterministic 512-configuration independent TRUE_DFT replay monitor.
- Select target monitor membership only from DATA5 `outer_monitor` evidence with balanced condition/run allocation and source-time systematic coverage; fold-local/locked roles cannot leak into the online monitor.
- Materialize the true-label replay monitor as `shared/replay/online_true_replay_monitor.xyz`; multi-head MACE `pt_valid_file` uses this artifact while replay gradient training remains independently configured, including pseudo-label replay when requested.
- Bind online-monitor policy, exact memberships, parent lineage, and replay-valid artifact into production materialization, DATA8, and training-protocol identities while retaining historical schema readability.
- Preserve the ADAPT-PREC1 model-dtype boundary during monitor inference and hard-coded FP64 mdstats metric arithmetic. ADAPT-STOP1 is still pending, so `max_num_epochs` remains authoritative; EVAL-MF also remains runtime-authoritative until ADAPT-EVAL1.

## 0.20.122a0 - 2026-08-09

- Implement ADAPT-PREC1: new MLFF campaigns expose only `single` (FP32 learned model) and `double` (FP64 learned model); staged `refine` and a user-facing `mixed` model mode are retired.
- Remove executable staged precision schedules from newly generated TOML and new DATA8/optimizer identities, making the historical FP32→FP64 optimizer/EMA promotion path unreachable from new production campaigns.
- Make mdstats-owned critical/scientific arithmetic invariant FP64 under both learned-model modes while preserving the selected model dtype through training, evaluation inference, verification, committee inference, and export.
- Disable evaluation checkpoint/template dtype promotion so FP32 checkpoints are never silently evaluated/exported as FP64 models. Historical staged/refine evidence remains readable for audit/storage but production commands fail closed and require explicit migration.
- Add the normative binary-model-precision specification, update the MLFF architecture/manual/user guide, and qualify binary precision with focused, real-MACE, evaluation/deployment, and broad specification regressions. ADAPT-MON1 remains the next gate.

## 0.20.121a0 - 2026-08-09

- Record the new seven-gate MLFF adaptive-training/evaluation revision (`ADAPT-PREC1` through `ADAPT-MIGRATE1`) without changing runtime behavior in this release.
- Plan binary learned-model precision only (`single` FP32 or `double` FP64), retirement of staged `refine`, and no user-facing mixed-model mode; mdstats-owned scientific fitting/reductions/statistics and persistent simulation bookkeeping remain invariant FP64.
- Freeze evidence-based online monitor defaults for the planned implementation: 256 common condition/trajectory/time-balanced target configurations and 512 fixed true-label replay configurations.
- Plan criterion-driven training with a 30 meV/A default full target force-RMSE ceiling, 0.80 target-stop fraction, weight-derived replay ceiling, 1.20 replay-exhaustion multiplier, and 30 epochs as a hard upper bound.
- Plan zero-new-inference lightweight scoring, one champion per independent run, retirement of production EVAL-MF successive halving, top-five authoritative full evaluation, deterministic next-five rescue, and exact model-dtype propagation through evaluation/verification/export.

## 0.20.120a0 - 2026-08-08

- Implement PAR-DENS0 basin-aware adaptive spread estimation for atomic-density planning. Production density resolution now excludes transition/passage material through authoritative site/Stage-11 adapters when supplied, or a conservative density-independent provisional residence prepass otherwise.
- Add per-basin spread and convergence diagnostics, including accepted/excluded samples, represented residence weights, independent stratified-replicate uncertainty, deterministic represented-time convergence anchors, and bounded escalation.
- Replace the normal compact-basin quadratic weighted-medoid initialization with an O(N)-per-iteration circular/Karcher fast path while retaining the historical multi-start medoid solver as a fail-safe for uncertified noncompact basins.
- Qualify the new defaults on the supplied 10,001-frame 300 K Na-LTA trajectory: 512-effective-frame Na reference 0.0746859880 A versus 0.0746688146 A full-trajectory reference (+0.023%); the two-basin Na ion changes from 0.195859 A global-mixture spread to 0.078787 A production within-basin spread, with 156 passage-boundary samples excluded.
- Preserve low-level one-replicate/global behavior for callers that do not opt in, while atomic-density production defaults use basin_mode=auto, four 128-stratum uncertainty replicates, a 1% deterministic convergence test, and bounded escalation to eight replicate-equivalent coverage levels. PAR-DENS1 is the next gate.

## 0.20.119a0 - 2026-08-08

- Add the normative PAR-DENS0--PAR-DENS6 architecture sequence for long-trajectory atomic/framework density work. The sequence orders basin-aware vibrational-spread correctness before execution cost calibration, CPU/RAM scheduling, parallel density kernels, preprocessing parallelism, optional GPU acceleration, and end-to-end qualification.
- Freeze basin-aware spread semantics: transition/passage/ambiguous/unknown/conflict samples are excluded; multiple occupied basins contribute only within-basin covariance weighted by represented residence time. Existing Stage-11E and explicit site-assignment semantics are reused, with a density-independent provisional prepass only when final density-derived membership would be circular.
- Record the 10,001-frame Na-LTA convergence benchmark and adopt approximately 512 effective stratified frames as the initial coverage candidate, implemented through bounded replicated stratified estimates rather than one large quadratic periodic-medoid solve.
- Freeze performance safeguards for the planned implementation: 90% of scheduler/cgroup-visible CPUs, 80% of available host memory, optional 80% of available GPU VRAM, and no scientific-grid coarsening or precision weakening as an optimization shortcut. Wall-time remains advisory rather than a hard feasibility bound.
- This release is architecture/documentation only; no PAR-DENS runtime behavior is enabled yet.

## 0.20.118a0 - 2026-08-08

- Fix DATA8 canonical `refine` preparation for small target-only workloads such as the default `n512` naive fine-tuning jobs: the replay-calibrated 15,000-update reference floor no longer makes an otherwise valid 30-epoch 80/20 schedule mathematically impossible.
- Keep the three-FP64-epoch floor hard. When the exact canonical 80/20 refine profile already satisfies that epoch floor but 15,000 FP64 updates exceed the entire feasible staged budget, preserve the nominal FP32/FP64 split and bind the achievable FP64 update floor into the resolved training protocol.
- Keep custom staged schedules fail-closed when their configured update floor is infeasible; no general weakening of user-edited precision contracts is introduced.
- Fix `PrecisionSchedulePolicy.resolve(..., require_update_floor=False)` so supplying `updates_per_epoch` no longer accidentally enforces the update floor.
- Add resolver and DATA8 regressions covering the default n512/batch-2 failure, canonical replay-sized behavior, strict custom failure, and update-floor opt-out semantics.

## 0.20.117a0 - 2026-08-08

- Consolidate the MLFF campaign storage-management CLI under one top-level `storage` command: `storage report`, `storage cleanup`, `storage deduplicate`, and `storage archive create|verify|restore`.
- Keep bare `storage` as the read-only report shorthand and transparently normalize the pre-0.20.117 top-level `cleanup`, `deduplicate`, and `archive` spellings for script compatibility without exposing them in top-level help.
- Preserve all STOR1-STOR5 storage semantics, ownership gates, capability planning, archive verification, and scientific/materialization identities; this release changes CLI organization only.

## 0.20.116a0 - 2026-08-08

- Implement STOR5 exact immutable content-addressed hardlink deduplication through `deduplicate [--apply]`, gated by completed verification and protocol freeze.
- Implement authenticated self-contained `tar+gzip` cold archives with per-member hashes, manifest/archive digests, explicit `archive create|verify|restore`, exact staged restore, conflict refusal, and final re-verification.
- Enable `cleanup --tier archive --apply` only after the consequential hot representation is archived, independently read-back verified, and registered; failed archive verification never authorizes hot deletion.
- Dereference campaign-internal hardlinks into archive bytes and prune orphan content-store objects after reclamation so deduplication cannot defeat archive disk savings.
- Preserve all STOR1 ownership protections, production models, selected raw checkpoints, campaign provenance, and diagnostics.
- Restore the historical 0.20.76 legacy-schema JSON fixtures to the source distribution and include `tests/fixtures/` in `MANIFEST.in`, fixing packaged compatibility-test coverage.
- Advance the MLFF architecture dependency graph to revision 34 and close the post-0.20.105 EVAL-MF/PREC/STOR implementation roadmap.

## 0.20.115a0 - 2026-08-08

- Implement STOR4 manual tiered MLFF reclamation (`safe`, `cache`, `recompute`, `compact`, `archive`) with mandatory capability planning and explicit apply authorization for consequential tiers.
- Preserve external inputs, production models, selected production raw checkpoints, protocol/selection/verification records, and diagnostic logs at every STOR4 tier.
- Add cumulative capability reporting for restartability, checkpoint re-evaluation, metric-only recomputation, DATA7 reselection, DATA8 rematerialization, production inference, and verification replay.
- Keep `archive` plan-only until STOR5 provides authenticated reversible archive/restore semantics.
- Advance the MLFF architecture dependency graph to revision 33; STOR5 is the next gate.

## 0.20.114a0 - 2026-08-08

- Implement MLFF STOR3 lifecycle-safe automatic reclamation under the STOR1 ownership boundary, without deleting external inputs, selected production artifacts, active restart state, scientific prediction caches, or authoritative diagnostic/protocol records.
- Add authenticated append-only `results/cleanup-manifest.jsonl` events containing pre-deletion filesystem identities, reasons, reclaimed bytes, preserved capabilities, and an explicit zero-capability-loss contract.
- Reclaim the reconstructable OPT-EVAL3 graph/view cache only after authoritative evaluation is complete; retain evaluation-prediction shards, DATA6/model-sweep predictions, and true-label replay artifacts for later metric-only/reanalysis workflows.
- Change low-disk training behavior so STOR3 safe reclamation runs before active MACE jobs are interrupted; disk pressure never broadens cleanup authority, and active run roots remain excluded.
- Advance the MLFF architecture dependency graph to revision 32. STOR4 manual tiered reclamation is the next gate.

## 0.20.113a0 - 2026-08-08

- Implement MLFF STOR2 authenticated completed-checkpoint compaction: after per-run checkpoint selection, retain the selected full restart-capable checkpoint and replace qualified nonselected optimizer-bearing checkpoints with smaller model-state-only evaluation capsules.
- Bind every capsule to the original checkpoint SHA-256, run/epoch lineage, immutable MACE config digest, reconstruction contract, model-state digest, and capsule byte identity; raw deletion occurs only after atomic capsule write, independent exact reconstruction, campaign-state commit/readback, and re-authentication.
- Make OPT-EVAL1/OPT-EVAL4 and true-label replay refresh representation-aware so later re-evaluation can transparently use capsules while preserving the original checkpoint scientific/cache identity.
- Preserve active/incomplete-run restart state and pre-selection raw checkpoints; unsupported layouts, corruption, ownership ambiguity, non-saving capsules, or reconstruction mismatch fail closed to raw retention.
- Qualify STOR2 on real MACE 0.3.16/e3nn with exact model-state and energy/force/stress equivalence. STOR3 is the next architecture gate.

## 0.20.112a0 - 2026-08-08

- Extend the MACE runtime warning compatibility scope from exact TorchScript deprecations to all warnings originating from MACE/PyTorch, grouping repeated warnings by origin/category/source/message and emitting one compact `MaceRuntimeCompatibilityWarning` summary.
- Recognize and shorten the high-volume MACE/Torch warnings observed during checkpoint evaluation: `torch.jit.load/save/script` deprecations, MACE tensor-copy construction warnings, and TorchScript instance-annotation warnings emitted through `ast.py`.
- Wrap the full campaign `evaluate` command plus checkpoint materialization and target-head export so setup/reconstruction/export warnings are condensed as well as inference warnings. Non-MACE/non-PyTorch warnings continue to be replayed unchanged.
- Preserve the historical TorchScript `warning_codes` compatibility tuple and the frozen MLFF scientific/materialization identities. STOR2 remains the next architecture gate.

## 0.20.111a0 - 2026-08-08

- Implement MLFF STOR1 read-only storage accounting via `mdstats-mlff-campaign storage`, including logical, allocated-physical, and unique-inode byte accounting plus largest file/directory reporting.
- Add explicit campaign artifact ownership/retention families and protected-input cataloging for training data, foundation model, replay data, true labels, and the campaign config.
- Add fail-closed real-path and symlink containment to the pre-existing cleanup/checkpoint-pruning paths; external materialization/checkpoint paths referenced by campaign records no longer confer deletion authority.
- Preserve campaign-owned symlink cleanup without traversing or deleting external symlink targets.
- Keep STOR1 reclamation-free; STOR2 remains the next gate for authenticated completed-checkpoint compaction.

## 0.20.110a0

- Implement MLFF gate PREC3: activate `single`, `double`, and `refine` precision profiles end to end across preparation, preflight, training, checkpoint evaluation, verification, and deployment reporting.
- Replace dtype-based critical-precision guesses with the immutable profile-bound `MaceCriticalPrecisionPolicy`; canonical `single` uses native FP32 critical operations while legacy schedule-free FP32 campaigns retain the historical critical-FP64 wrapper.
- Permit explicit-profile EVAL-MF reconstruction of checkpoints from either staged dtype and evaluate all candidates under the profile-declared evaluation dtype.
- Enforce profile deployment dtype on target-head exports using exact MACE conversion/reload/state verification; `refine` therefore publishes FP64 even when an FP32-stage checkpoint wins.
- Persist `results/precision-profile.json` and embed the precision profile in final evaluation and verification payloads.
- Add real MACE 0.3.16/e3nn qualification for native single/double inference, FP32-candidate evaluation under FP64 refine policy, and FP32-to-FP64 deployment conversion. Real CuEq runtime remains environment-gated because cuequivariance is not available in the release qualification environment.

## 0.20.109a0

- Implement MLFF gate PREC2: exact in-process staged precision transitions at frozen epoch boundaries.
- Promote model parameters/buffers, Adam/AMSGrad floating state, EMA shadow state, and loss/runtime dtype from FP32 to FP64 without restarting the MACE process.
- Preserve optimizer/scheduler trajectory while applying the stage learning-rate scale coherently; canonical refine changes 1.0e-4 to 5.0e-5 at the default FP64 boundary.
- Add a latest-only authenticated exact-continuation companion because MACE 0.3.16 raw checkpoints persist EMA-averaged model weights but not the live model/EMA shadow state.
- Make staged restart select only a raw checkpoint with a matching companion; an unpaired newer raw checkpoint from an interrupted commit is ignored safely.
- Persist authenticated precision-stage transition receipts with pre/post dtype inventories, learning rates, schedule/protocol identity, and source state/checkpoint digests.
- Add real MACE 0.3.16 e3nn force-training qualification plus deterministic restart-equivalence tests. CuEq source/adapter compatibility remains covered, while real CuEq runtime activation is deferred to PREC3 because cuequivariance is not present in the supplied qualification environment.
- Keep staged profile production preflight fail-closed until PREC3 completes end-to-end profile activation and reporting.

## 0.20.108a0

- Implement MLFF PREC1 precision profiles and deterministic staged-schedule identity.
- Add `init --precision single|double|refine`; plain init defaults to canonical single.
- Canonical refine emits explicit 80/20 FP32->FP64 stages with a 0.5 refinement LR scale and refinement floors.
- Resolve precision epoch/update boundaries after DATA8 loader exposure and bind them into training-protocol identity.
- Preserve legacy schedule-free optimizer/protocol digests; represent canonical `single` with an explicit native-FP32 critical-operation policy while keeping execution fail-closed until PREC3.
- Fail closed until PREC2/PREC3 runtime activation rather than silently executing a staged or canonical-single schedule under legacy arithmetic.

## 0.20.107a0

- Complete MLFF gate EVAL-MF2: conservative paired source/temporal-block survivor guards, true-label replay-compatible reserve, and rank-instability expansion on top of EVAL-MF1 nested target/replay evaluation.
- Add comprehensive per-epoch JSON/CSV/Markdown evaluation reporting that merges MACE training history with partial/full independent metrics, survivor reasons, replay degradation, final admissibility, and selected status.
- Qualify the default 10% -> 33% -> 100% policy against a representative 30-checkpoint exhaustive case: winner agreement is exact and nested candidate inference is 10.89 versus 30 full-checkpoint equivalents (63.7% less in that case). Supplied MACE 0.3.16 restoration/graph-cache regressions pass separately.
- Make `checkpoint_strategy = "multi_fidelity"` the generated production default while preserving `bounded` for legacy configs/explicit fast use and `exhaustive` for audit/reference evaluation.
- Advance the MLFF architecture dependency graph to revision 26. Partial screening remains non-authoritative and gains no checkpoint-deletion authority; frozen DATA8/training scientific identities are unchanged. `PREC1` is next.

## 0.20.106a0

- Implement MLFF gate EVAL-MF1 as an opt-in deterministic nested multi-fidelity checkpoint-evaluation strategy. All saved checkpoints enter round 1; target and true-replay monitors use the same configured fractions; only full-fidelity finalists publish authoritative checkpoint-evaluation records.
- Add immutable label-independent monitor ladders with condition/source/trajectory balancing and temporal spreading, plus explicit partial-round screening evidence and auditable survivor rank/outcome/reason records.
- Extend OPT-EVAL2 prediction persistence with authenticated coverage shards so later rounds infer only newly added configurations and cumulative metrics compose prior shards exactly; corrupt shards are rejected and selectively recomputed.
- Preserve the existing OPT-EVAL3 graph/view cache and OPT-EVAL4 prepare/infer/finalize pipeline, and keep the legacy bounded/exhaustive strategies available. The generated TOML remains `checkpoint_strategy = "bounded"` until EVAL-MF2 statistical guard-band and exhaustive-comparison qualification is complete.
- Keep checkpoint-retention authority unchanged in EVAL-MF1: partial screening outcomes do not authorize raw-checkpoint deletion; STOR1--STOR5 remain responsible for later lifecycle storage policy.
- Advance the MLFF architecture dependency graph to revision 25. Frozen DATA8/training scientific identities remain unchanged.

## Architecture revision 24 - planned after 0.20.105a0

- Record `EVAL-MF1`/`EVAL-MF2` as the next MLFF implementation gates: deterministic nested multi-fidelity checkpoint evaluation using the same nominal target/replay monitor fraction at each round, incremental prediction reuse, conservative survivor control, full-fidelity finalist selection, and comprehensive per-epoch reporting.
- Record `PREC1`--`PREC3` between evaluation and storage: explicit `single`/`double`/`refine` profiles, visible staged schedules, in-process FP32-to-FP64 optimizer/EMA promotion, and qualification before activation.
- Record `STOR1`--`STOR5` after staged precision: ownership-scoped storage accounting, lossless completed-checkpoint evaluation capsules, automatic lifecycle-safe cleanup, manual tiered reclamation with explicit capability loss, and optional immutable deduplication/cold archival.
- Freeze the deletion safety boundary: external user-supplied source/training/replay/true-label data are never cleanup targets; final selected production models/checkpoints and inexpensive diagnostic text/log records are retained by default.
- This is an architecture/specification revision only. It does not implement the new evaluator or storage policy and does not change the 0.20.105a0 runtime/scientific compatibility identity.

## 0.20.105a0

- Fix MLFF DATA6 progress timing so batched/sharded completion callbacks are not mistaken for numerical throughput. DATA6 now coalesces progress notification after each persistence drain, samples recent throughput only over real wall-clock windows, and derives ETA from cumulative post-restart work rate.
- Fix the same callback-burst timing defect in universal structural selection progress reporting under threaded execution.
- Harden the shared DATA2/DATA4/DATA8/TRAIN/EVAL/EXPORT/VERIFY progress reporter against instant cache/restart completions poisoning subsequent ETA calculations; immediate reused work becomes a timing baseline and ETA remains `estimating` until timed work exists.
- Add deterministic regression coverage reproducing the observed `recent=1708 frame/s`, `avg=20 frame/s`, `eta=20s` failure mode. At 3,100/36,759 and 20.07 frame/s cumulative throughput, the corrected ETA is about 28 minutes.
- This is a progress-reporting/runtime maintenance release only. It does not change frozen MLFF scientific, DATA8 materialization, checkpoint, prediction-cache, or verification identities.

## 0.20.104a0

- Restore the `tools/` source-checkout front ends omitted from 0.20.100a0--0.20.103a0 source distributions and package them explicitly.
- Port the historical DATA9A3 finalizer to the current immutable `ProductionCorpusPlan` API and make source tools bootstrap the checkout root robustly.
- Regenerate `campaign.toml.example` from the optimized 0.20.103 campaign backend, including OPT-EVAL4 staged evaluation and OPT-CTRL1 telemetry defaults.
- Restore normative MLFF/Stage-11 dependency-graph JSON files and add release-content regression coverage.
- Preserve the frozen MLFF scientific compatibility token at 0.20.99a0.

## 0.20.103a0

- Complete MLFF roadmap stage OPT-CTRL1: persistent thread-local campaign SQLite connections, single-query optional record fetches, grouped parent-side commits, and reduced redundant JSON/record work.
- Add durable strong-stat SHA-256 receipts under the campaign internal directory so unchanged immutable artifacts can be authenticated across restarts without rereading their bytes.
- Prefer process-persistent direct NVML/libnvidia-ml GPU telemetry with `nvidia-smi` fallback, and reduce evaluation/verification polling after calibration when only the hard live-VRAM guard remains.
- Stream replay ExtXYZ configuration-weight realization and reuse one top-level run-directory snapshot across cleanup subpasses.
- Preserve the frozen MLFF scientific compatibility token at 0.20.99a0 and verification-case compatibility at 0.20.85a0.

## 0.20.102a0

- Implement OPT-VERIFY1 bounded-verification optimization.
- Parse verification structures once into immutable templates and reuse them across cases.
- Reuse one private MACE calculator per adaptive verification worker/model identity.
- Replace sampled dense periodic `N x N` minimum-distance matrices with an exact adaptive periodic neighbor-list search.
- Preserve the 0.20.99a0 MLFF scientific compatibility identity and existing verification-case cache identity.

# Changelog

## 0.20.101a0

- Implement OPT-EVAL4 staged checkpoint evaluation: bounded CPU preparation, accelerator-admitted model materialization/conversion/inference, and bounded CPU prediction persistence/metric finalization now overlap across independent checkpoints.
- Keep MACE calculator ownership private to each inference worker and retain the existing process-wide CuEq/OEq/FX conversion guard, adaptive accelerator concurrency calibration, fixed post-calibration GPU estimate, and hard VRAM/RAM safeguards.
- Let cache-only evaluation/relabel work bypass accelerator admission entirely, and apply bounded prepared/finalization queues so prediction arrays cannot accumulate without backpressure.
- Add stage-specific progress/timing diagnostics and automatic CPU prepare/finalize worker controls without changing evaluation metrics, checkpoint selection, replay provenance, prediction/graph cache schemas, or the MLFF compatibility token (still 0.20.99a0).

## 0.20.100a0

- Remove density wall-time estimates and measured elapsed time as hard plotting admission criteria; wall-time targets are advisory diagnostics only.
- Remove wall-time-derived default operation caps for density kernel pairs and field counts while preserving memory, structural, browser, correctness, and explicit expert caps.
- Stop deriving isolated density-mesh worker timeouts from the complete-scene wall target; no implicit timeout is used, while an explicitly requested worker timeout remains an opt-in kill switch.
- Keep `max_wall_time_seconds`, `MDSTATS_MAX_WALL_TIME_SECONDS`, and `--max-wall-time` as backwards-compatible advisory metadata; add `--wall-time-target` as the clearer example CLI alias.
- Preserve the MLFF campaign compatibility token at 0.20.99a0 because this release changes plotting policy only.

## 0.20.99a0

- Implement OPT-EVAL3 stable monitor graph caching: model-independent graph identities, 1 GiB byte-bounded CPU memory reuse, SHA-256-authenticated persistent graph shards, corruption rebuild, and single-flight concurrent misses.
- Pre-index immutable target/replay evaluation views so repeated checkpoints reuse reference arrays, force offsets, focus-species indices, condition IDs, and stress masks instead of walking ASE metadata repeatedly.
- Remove the graph-build device round-trip used only for caching and avoid a redundant device-batch clone for single-model MACE inference, while preserving ensemble isolation, OOM backoff, prediction/cache schemas, and scientific metrics.
- Include the previously requested multi-format trajectory input update for `examples/plot_lta_mixed_alkali_density.py`.


## 0.20.98a0

- Implement OPT-EVAL2 label-independent persistent evaluation predictions, allowing metric/reference-label changes to reuse candidate target/replay inference and survive raw-checkpoint cleanup.
- Reuse authenticated DATA6 target-foundation predictions and frozen foundation-pseudolabel replay outputs; serialize shared foundation miss resolution across concurrent checkpoint workers.
- Advance checkpoint-evaluation records to schema v3 with prediction-artifact digests while retaining v1/v2 compatibility, corruption fail-closed behavior, and existing true-label replay lineage semantics.


## 0.20.97a0

- Implement OPT-EVAL1 fast MACE checkpoint restoration using the completed training model as an architecture template, with exact state/dtype checks, mmap checkpoint loading, CuEq/OEq guarded conversion, and legacy subprocess fallback.
- Reuse an already matching final training `.model` directly and perform qualified multi-head target extraction in-process.
- Add reconstruction/export timing evidence and checkpoint-model cache schema v2 while accepting v1 cache receipts.


## 0.20.96a0

- Fix restart-time `Replay monitor artifact lineage mismatch` for pseudolabel training campaigns evaluated against an independent true-DFT replay monitor.
- Keep the enclosing evaluation record bound to the true-label replay artifact actually evaluated while binding checkpoint admissibility metrics to the frozen DATA8 training replay lineage.
- Migrate 0.20.95a0 cached evaluation rows in place on restart; completed checkpoint inference remains reusable and is not rerun.
- Preserve strict geometry/order authentication of the true-label override, evaluation-policy identities, selection thresholds, and immediate parent-level model reconciliation.

## 0.20.95a0

- Make evaluated-model publication synchronous with per-run checkpoint selection instead of delegating it to a single asynchronous export thread.
- Commit `evaluated_model:<run-id>` immediately after atomic target-head publication, so the parent `models/` directory and durable campaign state agree before evaluation continues.
- Reconcile cached-only fully evaluated runs before launching any new inference tasks; restarting `evaluate` now publishes a missing parent-level model even when there are zero pending checkpoint evaluations.
- Leave `selection:<run-id>` durable when publication fails, keep the selected checkpoint reconstruction cache, and retry publication on the next `evaluate` invocation.
- Preserve the work-conserving GPU queue: empty inference slots are refilled before synchronous selection/export callbacks execute.
- Preserve evaluation metrics, selection policy, checkpoint identities, target-head semantics, and all existing TOML/cache compatibility.

## 0.20.94a0

- Serialize only MACE CuEq/OEq/hybrid graph-rewrite functions during parallel evaluation to prevent overlapping PyTorch-FX traces from raising `NameError: module is not installed as a submodule`, while preserving parallel model I/O and CUDA inference.
- Include the active evaluation/verification worker stage in parallel failure messages.
- Finalize checkpoint selection independently per run as soon as that run's shortlisted evaluations are complete, rather than waiting for the whole campaign-wide queue.
- Immediately publish each selected run target head to `models/<run-id>-target.model`, including fold models, while unrelated runs continue evaluating.
- Retain reconstructed checkpoint-model caches until per-run selection/export can reuse the chosen model, then remove the cache after successful publication.
- Make target-head publication atomic via same-directory staging plus `os.replace`, preserving any previous valid model on failed/interrupted export.
- Drain completed-future waves from the active set and refill all opened slots before potentially slower selection/export callbacks.
- Preserve all scientific evaluation identities, the 0.20.92a0 85th--95th percentile GPU estimator, 0.20.93a0 rolling queue, and existing TOML compatibility.

## 0.20.93a0

- Make evaluation/verification execution a work-conserving rolling queue: every successful completion immediately refills one admitted slot from pending work.
- Refill before parent-side result persistence/progress bookkeeping so fast inference is not serialized behind slower campaign-state commits.
- Refill multiple simultaneous completions independently instead of draining the whole completed wave before submitting replacements.
- Apply controller concurrency increases in the same telemetry iteration rather than waiting through another monitor interval.
- Preserve the 0.20.92a0 five-minute CUDA calibration, 1% activity filter, 85th--95th percentile estimator, fixed post-calibration GPU-utilization projection, live VRAM hard guard, CPU/RAM bounds, training scheduler, and all scientific identities.

## 0.20.92a0

- Shift the evaluation/verification fixed CUDA estimator upward from the 80th--90th percentile band to approximately the 85th--95th percentile band.
- After the 1% activity filter, discard only the highest 5% of retained GPU-utilization and incremental-VRAM samples, then average the next-highest 10% independently.
- Preserve the five-minute single-job calibration, fixed post-calibration GPU-utilization estimate, and live VRAM hard guard.
- Migrate the exact shared 0.20.91a0 generated `inference_gpu_calibration_peak_trim_fraction = 0.10` to the new 0.05 default while preserving phase-specific and other custom overrides.
- Leave training, CPU evaluation/verification, and scientific cache identities unchanged.

## 0.20.91a0

- Keep the five-minute single-job CUDA calibration for evaluation and verification, but replace the raw upper-decile mean with a peak-trimmed upper-band estimator.
- Independently discard the highest 10% of retained GPU-utilization and incremental-VRAM samples, then average the next-highest 10% (approximately the 80th--90th percentile band).
- Freeze the resulting per-job GPU-utilization estimate for the remaining evaluation/verification queue; instantaneous post-calibration GPU-utilization spikes no longer reduce concurrency.
- Retain the live 90% VRAM guard because actual memory saturation can cause allocation failure/OOM; RAM remains capped at 80%.
- Add canonical `inference_gpu_calibration_peak_trim_fraction` and `inference_gpu_calibration_band_fraction` controls while accepting the 0.20.90a0 `*_upper_tail_fraction` key as a compatibility alias for the band width.
- Leave the training scheduler unchanged at its separate 60-second true-epoch policy and CPU evaluation/verification unchanged at its 20-second workload policy.

## 0.20.90a0

- Extend evaluation/verification single-job CUDA calibration from 180 to 300 seconds.
- After the 1% activity filter, summarize GPU utilization and incremental VRAM independently with the highest 10% of retained samples.
- Preserve fixed projection after calibration while retaining the then-existing live GPU/VRAM saturation override.

## 0.20.89a0

- Replace short-window CUDA evaluation/verification admission with one campaign-wide 180-second calibration at concurrency one.
- Sample GPU utilization and incremental VRAM from task launch across the heterogeneous evaluation/verification lifecycle, independently discarding values below a 1% activity floor before averaging.
- Reuse the retained one-job means as fixed per-job estimates for all remaining jobs and jump directly to the largest concurrency projected below the 90% GPU-utilization and VRAM ceilings.
- Preserve calibration across successive short serial jobs when one job finishes before the three-minute window; never wait after the queue has already completed.
- Remove the configured VRAM-per-job guess as a pre-calibration concurrency ceiling; retain it only as a conservative fallback when no measured VRAM sample crosses the activity floor.
- Keep live post-calibration telemetry as a hard saturation override, CPU evaluation/verification on its 20-second workload window, training on its 60-second true-epoch window, and RAM at 80%.
- Preserve evaluation/verification stage progress and add calibration heartbeat detail for elapsed time and retained GPU/VRAM samples.
- Migrate exact shared generated evaluation/verification windows from 0.20.86a0--0.20.88a0 (10, 60, and 20 seconds) to the new 180-second CUDA calibration while preserving explicit phase-specific and other custom values.

## 0.20.88a0

- Start evaluation admission telemetry at the first computation-heavy checkpoint operation (authentication/hash/deserialization), rather than waiting for the later first model forward pass.
- Start verification telemetry at MACE model deserialization/device transfer, or at dynamics initialization when a prebuilt calculator is supplied.
- Average the complete mixed-stage evaluation/verification workload over a 20-second calibration window; stage transitions do not reset the window.
- Keep adaptive training on a separate 60-second true-epoch calibration window and migrate the exact prior generated 180-second training default to one minute.
- Emit per-task evaluation/verification stage transitions and include active-stage summaries in periodic scheduler progress.
- Preserve 90% CPU/GPU/VRAM limits, the 80% RAM limit, scientific cache identities, and legacy configuration overrides.

## 0.20.87a0

- Start evaluation/verification admission telemetry only at an explicit first real model forward pass, excluding checkpoint conversion, monitor loading, calculator construction, and CUDA initialization.
- Require every active worker at a concurrency level to enter true inference before calibration begins, and reset calibration whenever that level changes.
- Replace the previous short warm-up with a trailing 60-second true-inference window and a duration-derived minimum sample count.
- Skip runtime GPU polling during setup and reset stateful CPU counters at true-inference entry.
- Add canonical calibration-window configuration keys while migrating the exact 0.20.86a0 generated 10-second default to 60 seconds and preserving other legacy overrides.
- Preserve the 90% CPU/GPU/VRAM ceilings, 80% RAM ceiling, and all scientific cache identities.

## 0.20.86a0

- Added campaign-wide adaptive parallel checkpoint evaluation across runs and shortlisted checkpoints, including retained one-checkpoint true-label refreshes.
- Added adaptive parallel bounded NVE verification with private calculators for every active case.
- Start CUDA inference with one job and admit another only when fixed-window projections keep both aggregate VRAM and GPU utilization strictly below 90%; admitted jobs use distinct CUDA streams.
- Added affinity- and cgroup-aware CPU telemetry with projected 90% utilization admission.
- Raised package CPU and GPU/VRAM resource defaults from 80% to 90%, including structural selection and density/framework rendering; RAM remains capped at 80%.
- Preserved legacy TOMLs, evaluation scientific identities, and compatible 0.20.85a0 verification-case caches.

## 0.20.85a0

- Added an independent `[paths].replay_true_labels` input while retaining pseudo-label replay as the default training mode.
- Reconstruct exact true-label replay train/monitor splits from the original `mp_replay_selected.extxyz` using authenticated source indices and geometry/order checks.
- Evaluate foundation and fine-tuned models on both the LTA target monitor and true-label replay monitor, persisting the complete model-by-dataset metric matrix.
- Bind training replay lineage and evaluation-label lineage separately so true-label changes invalidate stale pseudo-label evaluations without changing DATA8 training inputs.
- Re-evaluate retained checkpoints after post-evaluation pruning and report reduced refresh coverage instead of failing or claiming deleted checkpoints were refreshed.
- Preserve old campaign TOMLs and pseudo-label-only diagnostic behavior.

## 0.20.84a0

- Corrected foundation-pseudolabel replay semantics: absolute candidate-versus-foundation disagreement is diagnostic only and no longer rejects or ranks checkpoints.
- Keep DFT-labeled target energy/force/stress/focus/worst-condition metrics as the actual checkpoint accuracy gates and primary ranking evidence.
- Retain the replay relative-degradation gate only for genuine `true_dft` replay; preserve a strict foundation self-consistency check for pseudolabel provenance.
- Migrate cached legacy checkpoint evaluations by binding immutable replay-label provenance and discarding ill-conditioned pseudolabel percentage ratios without rerunning MACE inference.
- Extend rejection/evaluation records and CLI messages with replay label mode plus absolute baseline/candidate metrics.


## 0.20.83a0

- Prevent one completed run with no admissible shortlisted checkpoint from aborting evaluation of every other completed model.
- Persist bounded, per-epoch checkpoint rejection evidence with exact mandatory-constraint reason counts and metrics.
- Exclude inadmissible runs from interim export/verification, recompute fold evidence from admissible runs only, and withhold production freeze when required runs fail constraints.
- Improve direct `select_checkpoint` errors with aggregated rejection reasons while preserving fail-closed mandatory gates.


## 0.20.82a0

- Bound DATA9B checkpoint evaluation to a training-history shortlist (default four checkpoints per run) while retaining authoritative mdstats monitor metrics for final selection.
- Add tiered verification: full NVE matrices for deployment/final models and bounded stability smoke tests for fold-only models.
- Cache verification cases, reuse one resident calculator per model, and sample expensive MD diagnostics at a configurable cadence.
- Add conservative post-evaluation pruning of screened-out checkpoints after full evidence is committed; interim evaluation remains restart-preserving.

## 0.20.81a0

- Fixed evaluation passing MACE optimizer checkpoint dictionaries directly to `MACECalculator`, which failed because the dictionary has no `.to()` method.
- Added checksum-bound reconstruction of a deployable whole MACE model through the immutable DATA8 configuration and qualified MACE restart/export path.
- Reconstruction copies rather than hard-links the checkpoint and verifies its SHA-256 before and after, preventing evaluation from mutating restart state.
- Evaluation retains the raw checkpoint for lineage while using the reconstructed model only for inference.
- Target-head export now supports both strict multi-head selection and direct serialization of unambiguous single-head naïve models.
- Added reconstructable model-cache validation and cleanup plus a specific diagnostic for raw training-checkpoint dictionaries.

## 0.20.80a0

- Completed a source-history audit of every serialized MLFF campaign policy, plan, bundle, and parser identity from 0.20.63a0 through 0.20.79a0.
- Fixed legacy feature-metric policies that predate `randomized_projection_seed` and partition policies that predate `cross_validation_seed`; deterministic runtime defaults are supplied while the exact historical serialization identity is preserved.
- Added backward reading for training-execution policy v1, production-materialization plan v2, DATA7 parser identities 0.20.35a0/0.20.63a0, and DATA8 parser identity 0.20.39a0.
- Preserve nested legacy digests through DATA5, DATA7, DATA8, production materialization checkpoint/record, and training-campaign parents instead of triggering cascading false mismatches.
- Added actual 0.20.76a0 serialized fixtures plus round-trip and tamper-rejection regressions.
- Completed-model evaluation can resume without rerunning prepare, preflight, or training; unsupported schemas and modified payloads still fail closed.

## 0.20.79a0

- Added fail-closed backward-compatible loading for digest-valid training-campaign plans written with older nested campaign-policy schemas.
- Validate the exact serialized legacy parent digest in addition to all existing nested policy/run digests, while still rejecting tampered payloads.
- `evaluate` rewrites an accepted legacy top-level campaign plan once into the current canonical schema without changing completed runs, checkpoints, execution records, or prepared DATA3-DATA8 artifacts.

## 0.20.78a0

- Added completion-aware interim evaluation and bounded verification for interrupted campaigns. Completed models are discovered from committed or recoverable run-local execution records without requiring every configured training job to finish.
- A fully completed method/selection/seed variant is evaluated and verified independently while unfinished variants remain pending; this produces complete-variant interim evidence without falsely freezing the full campaign.
- Two or more completed cross-validation folds enable reduced cross-fold evidence with explicit missing-fold/final-model warnings. One completed model falls back to per-model checkpoint metrics and bounded NVE stability tests with an explicit no-cross-validation warning.
- Added interim evaluation filters for training method, optimizer seed, and selection size, plus strict `--require-complete` and `verify --require-frozen` modes.
- Exported interim models are SHA-256 bound to their selected checkpoints, and verification refuses stale evidence when additional runs complete after the interim selection; rerunning `evaluate` refreshes the scope.
- Preserved production semantics: only a fully completed configured campaign can create the protocol comparison, deployment committee, and production freeze. Interim success leaves `evaluate`/`verify` waiting and does not authorize deployment or trigger post-evaluation checkpoint deletion.

## 0.20.77a0

- Made MACE restart progress checkpoint- and attempt-aware: committed epochs no longer move backward, abandoned post-checkpoint rows no longer inflate gradient percentages, and replayed rows are labeled/excluded.
- Added a source-qualified MACE 0.3.16 restart-loop patch that resumes at the epoch after the loaded checkpoint and preserves the corresponding learning-rate/SWA transition; the loaded epoch is checked against the checkpoint filename.
- Added explicit per-method training matrices in the generated TOML: independent manual seed arrays, cross-validation fold counts, and fold-partition seeds for naïve fine-tuning and multi-head replay.
- Added deterministic SHA-256 fold assignment, configurable randomized feature-projection and replay seeds, fixed Python hash seeds for MACE children, and a configurable NVE velocity seed.
- Added final-only training with `cross_validation_folds = 0`; downstream campaign construction, checkpoint evaluation, protocol aggregation, committee export, and verification adapt to the actually configured jobs.
- Preserved legacy `[training].modes`/`seeds` and DATA9A materialization-plan restart records while new plans retain exact method-specific fold identities.

## 0.20.76a0

- Fixed `Ctrl-C`/SIGTERM leaving the nested real-MACE CUDA process alive after the supervised mdstats wrapper exited.
- The precision wrapper now forwards SIGINT, SIGTERM, SIGHUP, and SIGQUIT to the detached MACE process group, waits for graceful exit, and escalates to SIGKILL when necessary.
- Added Linux parent-death protection to both supervision layers so an unexpectedly lost campaign or wrapper parent requests termination of its child.
- Extended the campaign interruption guard beyond SIGINT to SIGTERM and SIGHUP, preserving the same checkpoint-safe interruption record and restart path.
- Added nested child/grandchild process-group regressions proving that wrapper interruption leaves no supervised GPU process behind.

## 0.20.75a0

- Fixed supervised training progress callbacks firing once per one-second cancellation poll; cancellation remains responsive, while visible training updates now default to a 10-second cadence.
- Replaced variance-based scheduler stabilization with a fixed-duration true-epoch averaging window. Natural GPU-utilization and VRAM fluctuations no longer block concurrency promotion indefinitely.
- Scheduler admission now projects the next job from mean resource use over the full calibration window and still requires both projected VRAM and GPU utilization to remain strictly below 90% by default.
- Replaced heavy obsolete-runtime archives with bounded compact diagnostics: retain execution metadata, a capped file inventory, and bounded log tails, then immediately delete obsolete models, checkpoints, results, and logs.
- Cap obsolete-runtime diagnostics at five records per run and automatically remove heavy archives created by older releases at cleanup boundaries.

## 0.20.74a0

- Added conservative campaign-wide garbage collection at train/evaluate/verify boundaries plus a `cleanup --dry-run`/`cleanup` command.
- Remove only unreachable or reconstructable storage: orphaned external records, obsolete materializations/generations, stale promotion trees, post-preflight frame/DATA7 caches, heavy preflight artifacts, and superseded runtime trees with retained diagnostics.
- Added event-history bounding and safe SQLite compaction when no live training child exists.
- Added post-evaluation checkpoint compaction: retain the selected checkpoint and complete metric/selection/catalog evidence, while deleting only evaluated unselected optimizer snapshots.
- Added graceful `Ctrl-C` and low-free-disk interruption of all active MACE process groups, preserving checkpoints and committing resumable `interrupted` records.
- Interrupted attempts no longer consume bounded failure retries; existing checkpoint bytes trigger `--restart_latest` even after a parent commit gap.
- Added active-child PID markers to prevent duplicate campaign parents from launching the same run.
- Recover successful run-local records, or a valid final MACE model plus checksummed checkpoint catalog, when the parent was interrupted before SQLite commit.
- Re-inventory SHA-256 checkpoint bytes before skipping a completed run; changed or missing completed artifacts now fail closed instead of being silently recalculated.
- Added a runtime disk reserve guard that pauses training at durable checkpoints when free space falls below `execution.minimum_free_disk_gib`.

## 0.20.73a0

- Changed adaptive CUDA training to start with exactly one production job and add only one job at a time.
- Added a true-epoch gate based on fresh MACE optimizer records, preventing initialization, graph construction, and validation phases from being mistaken for spare steady-state capacity.
- Added sustained post-epoch calibration: every active job must remain in recent optimizer work for 180 seconds by default, with 12 stable telemetry samples, before another job is considered.
- Added dual next-job projection. The candidate aggregate VRAM and GPU utilization must both remain strictly below their configured 90% admission ceilings.
- Added stable post-add saturation rollback for future replacements; active jobs are never killed, but the target concurrency drops by one when calibrated utilization or VRAM reaches the ceiling.
- Made positive `parallel_training_jobs` values maximum caps rather than permission to bypass adaptive phase/resource admission.
- Reworked MACE progress parsing to incrementally read appended optimizer records instead of rescanning the complete training-results file at every scheduler heartbeat.

## 0.20.72a0

- Added adaptive process-level concurrency for independent production MACE fold/final jobs on one CUDA device.
- Auto mode starts with two jobs when CPU, RAM, and VRAM budgets permit, then admits one additional job only after stable live VRAM measurements.
- Caps aggregate training allocation at 80% of total VRAM by default; a 24 GiB GPU using about 5.7 GiB per job resolves to three concurrent jobs and rejects a fourth.
- Divides native BLAS/OpenMP threads across concurrent MACE parents and their frozen DataLoader workers to prevent host oversubscription.
- Stops admitting queued jobs after the first failure by default, while allowing already-running jobs to finish and persist checkpoints.
- Resumes an existing checkpoint even when the previous parent was interrupted before writing its execution record.

## 0.20.71a0

- Fixed production MACE jobs resolving DATA8-relative foundation, target, and replay paths from `runs/<run-id>` instead of the immutable DATA8 job directory.
- Production training now uses the DATA8 job directory as its working directory while explicitly routing models, checkpoints, logs, and results into the run directory.
- Added campaign-wide pre-launch validation for every immutable MACE input path, preventing a full 16-run matrix from launching with the same deterministic path failure.
- Versioned the training runtime layout and automatically archives/reset failed attempts from the obsolete layout, so exhausted 0.20.70a0 failures can restart without deleting campaign state.
- `--restart_latest` is now added only when a prior checkpoint actually exists.

## 0.20.70a0

- Fixed mixed naïve/replay campaigns falsely failing `production_replay_corpus_not_bound`.
- Production qualification now uses a replay-bound representative whenever the training matrix requests replay, while naïve-only matrices do not require replay.
- The repair reuses completed DATA6-DATA8 artifacts and updates only final qualification state.

## Unreleased

- Make an unchanged plain `prepare` a receipt-verified no-op instead of restarting at DATA6 finalization.
- Defer normalized frame-cache loading until DATA6 recomputation or a changed DATA7/DATA8 variant actually needs trajectory arrays.
- Adopt fully qualified 0.20.68a0 campaigns into the new prepare restart receipt without repeating DATA6, DATA7, or DATA8 work.
- Restore a matching completed DATA6 model-sweep checkpoint without constructing a MACE calculator, running inference, or eagerly rehashing every descriptor/prediction sidecar.
- Reuse the finalized sharded DATA6 bundle when source/frame/DATA4/DATA5 lineage, DATA6 policy, checkpoint identity, sweep plan, sweep checkpoint, and descriptor/prediction manifests match exactly.
- Preserve and directly reuse unchanged per-variant DATA7/DATA8 materializations; rebuild only variants whose frozen plan identity changed or whose live pointer is missing.
- Defer reconstruction/authentication of foundation prediction energies until at least one DATA7 domain actually needs rebuilding.
- Add file-stat input identities, record digests, sweep identity, and DATA8 tree identities to the durable prepare restart receipt.

- Fix `train` failure `Training campaign run IDs must be unique`: `require_replay=False` now binds `ReplayMode.NONE` before DATA8 construction, so nominal `naive_fine_tuning` variants no longer materialize as `multihead_replay`.
- Validate every persisted DATA8 variant label against the mode, selection size, and seed frozen in its jobs; stale aliased variants now stop with a precise ordinary-`prepare` migration instruction.
- Expand duplicate run-ID diagnostics with the colliding logical run and DATA8 bundle prefixes.
- Preserve restart economy: plain `prepare` rebuilds only corrected naïve DATA8 job trees and reuses DATA3-DATA7 plus the completed foundation-model sweep.
- Bind the completed one-epoch preflight record to the exact sorted DATA8 variant/bundle matrix, so a repaired DATA8 generation automatically returns `preflight` to WAITING before training.

- Make the real-MACE preflight genuinely bounded by training on deterministic target/replay subsets rather than traversing the complete ~10k replay corpus.
- Report exact MACE gradient-update progress and percentage, current phase, selected CPU/GPU device, accelerator backend, GPU utilization, and VRAM use during preflight.
- Apply the same exact update-percentage heartbeat to production training runs; replace generic `still running` subprocess messages with concise elapsed/phase diagnostics.
- Preserve protocol freezing: `[training].device = "cuda"` explicitly drives both preflight and production MACE, while CPU campaigns are not silently changed.
- Terminate the detached MACE preflight process group on keyboard interruption so canceled smoke tests do not leave orphan GPU workers.

- Fix MACE 0.3.16 multi-head preflight failures such as `Atomic number 1 not found in atomic_energies_dict for head target_head`: DATA8 now gives `target_head` its own target-only `atomic_numbers` table while retaining the target/replay union at the top level.
- Invalidate pre-0.20.66 DATA8 generations so plain `prepare` rebuilds only the fixed-file job tree while reusing authenticated DATA7 archives and the completed DATA6 foundation sweep.
- Add static per-head E0 coverage checks before launching MACE and surface the final child exception directly in preflight output instead of only pointing to `training.stderr.log`.

- Fix the post-DATA8 production-gate failure reported after `materialized multihead_replay-n512-seed2`: ordinary fixed-cell runs without an explicit strain reference group now use an exact implicit self-reference, while ungrouped variable-cell runs remain unresolved and fail closed.
- Preserve LTA profile-extension coverage under compact production materialization by reconstructing exact species/site-class labels from retained aggregate DATA6 features when per-atom environment objects are intentionally omitted.
- Evaluate inexpensive corpus blockers before DATA7/DATA8 materialization and report unresolved strain by run and reason; successful variant messages now state that the final DATA9A gate is still pending.
- Rebind checksum-verified DATA6 descriptor/prediction sidecars after a lineage-only DATA3/DATA5 rebuild, avoiding repeated MACE inference when frame records, requested roles, checkpoint identity, and policies are unchanged.
- Advance package and affected DATA7/feature-metric campaign identities to `0.20.64a0`, forcing invalid empty-coverage DATA7 artifacts to be regenerated.

- Fix DATA8 MACE extxyz export under ASE 3.29: replace ASE's lossy eight-decimal per-atom floating format with a 17-significant-digit ASE-compatible writer, preserving Cartesian positions and force labels through the mandatory write/read validation.
- Add a regression with non-decimal-aligned coordinates and forces that reproduced `MACE extxyz round trip changed positions` before the fix.
- Preserve large frame-cache arrays as authenticated path/offset references across isolated-worker boundaries instead of pickling their complete payloads; large in-memory arrays spill to temporary read-only NPY members.
- Add authenticated fast-restoration constructors for frame, universal-structural, fitted-feature, and fitted-metric arrays, avoiding redundant whole-array finite/digest scans after SHA-256 verification.
- Reuse one VASP XML control/supplement parse for source metadata, frame normalization, and DATA2 auditing instead of reparsing the same `vasprun.xml`.
- Map requested DATA6 NPZ members directly from stored NPY members, batch descriptor-summary extraction by shard, and preserve legacy shard readers.
- Store DATA7 training weights as lazy columnar native arrays while retaining legacy JSONL archive compatibility.
- Reuse raw pair geometry for structural rules sharing center/neighbor species and write aggregate rows directly into preallocated output buffers.
- Add byte-budgeted authenticated monitor caching and cross-checkpoint CPU MACE graph caching tied to the same live immutable ASE objects and graph policy.
- Avoid per-configuration condition dictionaries when no condition grouping is requested, and remove remaining full-buffer copies from scientific array hashing.

- Replace per-frame DATA6 descriptor/prediction sidecars with configurable immutable multi-frame NPZ shards (production default 128 frames), reducing a 36,759-frame all-descriptor/all-prediction campaign from as many as 73,518 scientific files to 576 shard files.
- Persist global and per-species MACE descriptor summaries inside DATA6 shards so DATA7 no longer rereads and reduces every atomic descriptor tensor.
- Load only requested NPZ members: DATA7 summary fitting never materializes `descriptor_values`, and residual-`E0` fitting reads `energies` without force/stress tensors.
- Write NPY, NPZ, DATA7 ZIP, extxyz, and sidecar artifacts through one-pass hashing writers, eliminating immediate post-write whole-file hash rereads.
- Store normalized frame-cache arrays as independently authenticated read-only NPY members and restore them through memory maps instead of monolithic NPZ copies.
- Persist DATA7 fitted matrices and block center/scale/projection arrays as native NPY members; restore the ZIP_STORED fitted matrix through direct read-only memory mapping while retaining legacy DATA7 archive support.
- Preallocate DATA7 raw/transformed matrices, preserve contiguous views, remove avoidable `vstack`/`column_stack` copies, use masked reductions for standard scaling, and use exact partition-based structural quantiles.
- Batch checkpoint evaluation with adaptive OOM backoff, reuse one candidate MACE provider across target/replay heads, cache authenticated monitor parses and immutable replay-baseline metrics, and accumulate errors through streaming sufficient statistics.
- Validate DATA8 extxyz output against compact source evidence during the write pass rather than rebuilding ASE objects and rereading the complete artifact solely for hashing.
- Add versioned legacy readers, corruption/restart regressions, selective-member access tests, and reproducible storage/memory benchmarks for the optimization.
- Fix an omitted quadratic DATA6 restart/finalization path: `pending_frame_uids` no longer reconstructs the completed-frame set once per requested frame; checkpoint construction is linear and repeated pending queries are constant-time.
- Replace the local campaign scheduler's `list.pop(0)` queue with `deque.popleft()`, eliminating quadratic job-launch shifts as seeds, folds, sizes, and modes grow.
- Replace quadratic label-domain first-fit comparisons, strained-reference discovery, event/interval cross-products, repeated temporal purge scans, and repeated catalog/domain lookups with compatibility buckets and immutable indexes.
- Reuse one selected-neighbor matrix across DATA7 ladder levels, use exact bounded centroid-prefix selection, preallocate feature/reference matrices, and stream evaluation error statistics.
- Route unchanged checkpoint, target, replay, cache, deployment, and qualification file authentication through one stat-identity SHA-256 cache while retaining post-hash mutation detection.
- Add the second full MLFF scaling audit and deterministic benchmarks for interrupted resume, scheduler queues, bounded representative selection, and coverage-neighbor updates.
- Redesign `[DATA6 finalize] building universal structural selection features` as a bounded-memory columnar pipeline; production no longer creates millions of unused per-atom descriptor objects or frame-level name/value tuples.
- Vectorize scalar, radial, angular, and orientational local-structure kernels; cache fixed-cell triclinic MIC setup and per-run aggregation plans; add throughput/RSS progress and runtime worker autotuning.
- Evaluate exact all-atom pair geometry only for `i < j`, mirror it by symmetry, and skip unused integer image-shift reconstruction, preserving numerical feature results while reducing the dominant local kernel.
- Emit structural events in canonical frame order and replace dense same-atom displacement tensors with direct per-atom displacement vectors.
- Persist DATA6 universal arrays and long evidence sequences as checksummed NumPy/JSONL shards, and persist DATA7 as a deterministic NumPy/JSONL ZIP64 archive.
- Use bounded deterministic PCA with implicit missing-indicator products, shared fold descriptor summaries, and one atomic-number scan per trajectory run.
- Reuse one derivative-enabled native MACE graph pass for frames requiring both descriptors and energy/force/stress predictions; retain the two-call compatibility fallback.
- Route serial LTA partition construction through the compact columnar kernel and vectorize robust selection scaling across feature columns.
- Add a full MLFF performance audit, exact-path equivalence tests, real-MACE combined-batch tests, and reproducible structural/MACE benchmark records.
- Replace DATA7's complete repeated-distance farthest-point ordering with exact bounded incremental maximin updates, reducing selection from `O(N^3 d)` to `O(N K d)` for largest requested ladder size `K`.
- Aggregate atomic environments to frame-level summaries, cap every selection queue at the largest requested ladder, and vectorize candidate coverage and selected-neighbor distances.
- Reuse lineage-identical DATA7 scientific artifacts across training seeds, modes, and process restarts while keeping DATA8 output variant-specific.
- Reconstruct foundation energies from authenticated compact DATA6 difficulty/blinded summaries and read prediction sidecars only for missing evidence.
- Build all DATA6 model-evidence domains in one indexed pass, release full force arrays after summarization, and avoid duplicate whole-domain and whole-tree verification passes.
- Stream large DATA6/DATA7 records, cache immutable nested digests, use one-read sidecar verification, and add explicit post-DATA6 phase progress messages.
- Reuse one frame-array index and one checkpoint-bound MACE descriptor-summary cache across overlapping DATA7 domains, while preserving independent fold-local scaling and PCA.
- Hash large DATA7 JSON during atomic streaming writes, retain already parsed bundles for immediate DATA8 assembly, release summary caches before DATA8, and avoid duplicate large-file parse/hash passes.
- Resolve LTA coverage classes through the provider's per-frame environment index so coverage touches only the bounded selected ladder instead of scanning the full atomic-environment corpus.
- Add deterministic prefix-equivalence, bounded-order, shared-cache restart, and 36,759-candidate scaling regressions.
- Replace DATA6's repeated growing full-checkpoint rewrites with a plan-bound
  append-only per-frame recovery journal and one final checkpoint compaction.
- Replace repeated descriptor/prediction tuple scans with hash-set membership,
  making steady-state DATA6 bookkeeping amortized linear in processed frames.
- Recover from journal-only state, legacy checkpoints, invalid-record
  tombstones, and truncated final journal lines without repeated inference.
- Change the generated DATA6 durable-flush interval from 1 to 128 frames while
  retaining `checkpoint_interval = 1` as an explicit maximum-durability option.
- Correct resumed DATA6 throughput and ETA reporting by excluding restored
  frames and reporting smoothed recent plus current-invocation average rates.
- Fix DATA6 native MACE descriptor batching under PyTorch autograd by explicitly disabling force, virial, stress, displacement, Hessian, edge-force, and atomic-stress outputs inside the descriptor-only `torch.no_grad()` scope.
- Preserve gradient-enabled native MACE prediction batching for energy/force/stress evaluation and add a real MACE 0.3.16 regression test comparing batched and serial descriptors.
- Consolidate exact PyTorch `torch.jit.script`/`torch.jit.load` deprecation warnings emitted inside MACE operations into one actionable `MaceRuntimeCompatibilityWarning` per runtime/API combination.
- Preserve and replay every unrelated warning with its original category and source location; nested MACE calls share one capture scope and exceptions propagate unchanged.
- Apply the compatibility scope to checkpoint inspection/evaluation, calculator and descriptor construction, acceleration probes, CLI execution, deployment export, and bounded verification paths.
- Add structured runtime compatibility evidence and focused tests without changing MACE checkpoint or deployment serialization semantics.

## 0.20.63a0 - 2026-08-04

- Add CPU-affinity/cgroup, available-RAM, CUDA, and free-VRAM discovery with configurable 80% safety budgets.
- Run source ingestion, DATA3, raw DATA4, and compact LTA feature construction through bounded trajectory-level worker processes.
- Use fresh one-shot workers to avoid GIL contention, nested BLAS oversubscription, retained native state, and cumulative RSS growth.
- Reserve memory for parent-side catalogs before assigning workers and reduce concurrency automatically when the 80% RAM envelope would be exceeded.
- Replace large LTA process transfers with compact NumPy columns and a representation-level Merkle identity.
- Reuse the immutable LTA frame-to-state index during event detection instead of allocating a duplicate hierarchy.
- Add native MACE graph batching for DATA6, VRAM-derived initial batch sizing, and adaptive CUDA-OOM batch halving.
- Propagate a CPU/RAM-bounded MACE DataLoader `num_workers` setting through DATA8, preflight, and production training.
- Expand campaign progress reporting with explicit CPU/RAM/VRAM plans, worker counts, reserved-memory estimates, per-run completion, elapsed time, ETA, and external-process heartbeats.
- Advance the MLFF dependency graph to schema 25 / architecture revision 21.

## 0.20.62a0 - 2026-08-04

- Refactor MLFF preparation around one normalized VASP decode per source and a checksummed reusable frame cache.
- Add bounded parallel source workers with per-run frame, quality, elapsed-time, log, and ETA progress.
- Remove repeated source-control, trajectory-quality, production-regime, DATA3, and DATA4 XML reads.
- Vectorize force quantiles and mobile/framework oxygen-coordination kernels and precompute static species/pair indices.
- Replace linear frame/run catalog scans with immutable lookup indices across DATA3--DATA9 campaign records.
- Remove duplicate LTA payload ownership from DATA4 and use compact Merkle component identities.
- Persist DATA4 as checksum-verified JSONL shards, restoring 903,192 LTA mobile states without constructing a giant nested JSON object.
- Keep foundation sweeps and cache-restoration paths from loading DATA4 when they do not consume it.
- Split manifest approval from expensive preparation; `prepare --approve-manifest` now approves and returns unless `--continue-after-approval` is explicit.
- Add heartbeat messages for long MACE subprocesses, checkpoint evaluation reuse with hash/policy verification, and stage/substage RSS/progress reporting.
- Validate the full supplied 27-run, 37,633-frame LTA corpus through DATA5 without OOM and preserve representative scientific digests under vectorized kernels.

## 0.20.61a0 - 2026-08-04

- Add fail-safe recovery of trailing interrupted `vasprun.xml` streams in ENS0, DATA2 source audit, and normalized VASP trajectory loading.
- Retain every complete ionic record and recover an unclosed final `<calculation>` only when positions, cell, forces, and energy are all complete and finite.
- Reject malformed XML away from EOF and interrupted streams missing controls, atom identities, or any usable ionic record.
- Record parse completeness, diagnostics, recovered/discarded tail status, and source-audit notes without converting an interrupted run into a hard failure.
- Treat requested-step incompletion and XML interruption as explicit soft-quality warnings while preserving strict frame/label integrity checks.
- Validate the production `LTA_K.700K.init.xml` and `LTA_K.800K.init.xml` streams at 1,379 and 1,354 complete frames, respectively.

## 0.20.60a0 - 2026-08-04

- Add MLFF-DATA2A automatic, reviewable campaign-manifest inference from VASP XML controls and fixed-cell geometry.
- Infer target temperature, thermostat, ensemble, timestep, requested ionic steps, and cell stationarity without requiring repetitive manual assertions.
- Parse LTA hydrostatic, orthorhombic, and shear intent from filenames, including percent-style names such as `hydro+5` and fractional names such as `hydro+0.05`.
- Resolve compatible unstrained references with temperature-aware ranking and promote strain groups only after exact profile-specific polar-stretch and volume verification.
- Preserve failed or ambiguous filename hints as diagnostics while clearing operational strain assertions and reference relationships.
- Recover review metadata from completed portions of truncated XML files while leaving strict source qualification to the later DATA2 production gate.
- Validate all six supplied production LTA strain runs against `LTA_LiNaK.700K.init` with sub-nanostrain residuals.

## 0.20.59a0 - 2026-08-04

- Add MLFF-DATA9B3A frozen MACE acceleration policies for ordinary e3nn and optional cuEquivariance execution.
- Make campaign initialization auto-detect a complete CuEq/CUDA/MACE environment once and write the resolved backend explicitly.
- Add fail-closed `doctor` qualification with a real foundation-model CuEq energy/force/stress smoke and serialized package/runtime evidence.
- Propagate `enable_cueq` and `only_cueq` through DATA6 foundation inference, DATA8 YAML, parser realization, preflight, production training, checkpoint evaluation, and bounded NVE verification.
- Bind acceleration policy and probe identities into optimizer, training protocol, and campaign digests; reject silent fallback and production `only_cueq=true`.
- Advance the MLFF dependency graph to schema 23, architecture revision 19, and add the DATA9B3A specification and user-guide instructions.

## 0.20.58a0 - 2026-08-04

- Add the unified `python tools/mdstats-mlff-campaign.py` UNIX-style interface for DATA2-DATA9B2 preparation, preflight, supervised training, evaluation, committee export, protocol freeze, and bounded verification.
- Replace fragmented top-level workflow artifacts with one TOML configuration, one reviewed manifest, one SQLite orchestration database, compact data/run/model directories, and consolidated benchmark/result records.
- Add digest-bound manifest approval, fail-closed source-quality and ensemble assertions, deterministic status/advance guidance, and source-bound critical-precision wrapper shims.
- Add real one-epoch production-wrapper preflight with target-head extraction and finite prediction round trip, including deterministic process-exit handling for MACE/PyTorch runtime shutdown.
- Promote replay to a production input gate: bind pseudo-labels to the exact foundation checkpoint SHA-256, require train/monitor geometry separation, target-element coverage, explicit label provenance, and minimum corpus sizes unless an exploratory override is recorded.
- Add committee-wide bounded NVE verification with energy-drift, minimum-distance, maximum-force, and actionable failure guidance.
- Classify verification output as `bounded_predeployment` and explicitly keep scientific observable acceptance separate.
- Separate replay-baseline head selection from candidate replay-head selection so a single-head foundation checkpoint can serve as the retention baseline.
- Advance the MLFF dependency graph to schema 22, architecture revision 18, and add the DATA9B3 specification and minimal user guide.

## 0.20.57a0 - 2026-08-04

- Implement MLFF-DATA9B2 supervised MACE execution with bounded retries, restart-latest semantics, immutable logs, and checkpoint revalidation.
- Add automatic target/replay checkpoint evaluation with focus-species, stress, worst-condition, and replay-retention metrics.
- Add fold/seed protocol aggregation, learning curves, deterministic naive-versus-replay comparison, committee target-head export, `ProtocolFreezeRecord`, and sealed-evaluation activation.
- Validate the evaluator and head exporter against the supplied real MACE 0.3.16 multi-head smoke model and retain the production DATA9A gate.

## 0.20.56a0 - 2026-08-03

- Implement MLFF-DATA9B1 campaign and checkpoint control.
- Freeze passed-gate, protocol-matched mode/selection-size/seed/fold job matrices.
- Require the precision-aware `mdstats-mace-train` execution wrapper and save-all externally audited checkpoints.
- Inventory candidate checkpoint bytes by SHA-256 with epoch, path-containment, and duplicate-content checks.
- Bind target/replay monitor metrics to exact checkpoint and artifact identities.
- Apply frozen hard admissibility constraints and deterministic fail-closed checkpoint selection.
- Preserve flat production XML filenames as deterministic run identities during explicit manifest discovery.
- Keep supervised long-running MACE execution, fold/seed aggregation, committee construction, and `ProtocolFreezeRecord` for DATA9B2+.

## 0.20.55a0 - 2026-07-30

- Close MLFF-DATA9A9c production-gate integrity gaps.
- Freeze exact production-corpus plans and derive DATA9A qualification from evidence.
- Bind replay geometry and numerical label payloads independently of staged weights and paths.
- Promote DATA8 through verified generation directories and an atomic pointer switch.
- Make foundation/replay content identities relocatable and materialization loaders self-verifying.
- Generalize optional-extension evidence requirements and remove stale cation/site gate language.

## 0.20.54a0 - 2026-07-30

### Added

- MLFF-DATA9A9b restartable production DATA6--DATA8 materialization.
- Frozen final/fold DATA7 domain and policy plans.
- Exact replay-train/replay-monitor binding and DATA8 job-tree evidence.
- Per-domain DATA7 checkpoints, corruption recovery, and fail-closed downstream invalidation.
- Complete materialization records with reloadable DATA7/DATA8 artifacts.

### Changed

- DATA9B remains closed until a complete DATA9A9b record exists for the production corpus.

# mdstats 0.20.53a0

## MLFF-DATA9A9a restartable production DATA6 model sweep

- Added an exact DATA5-authorized descriptor/prediction plan bound to the DATA6 policy and foundation checkpoint.
- Added atomic per-frame descriptor and prediction sidecars with file and numerical-content digests.
- Added incomplete, complete, and failed restart checkpoints, bounded progress, resume, and corruption recovery.
- Advanced DATA6 to schema v5 and enabled completed sweeps to populate descriptor, residual, and blinded-prediction evidence without repeated foundation inference.
- Added a real MPA-0/Na-LTA interruption-and-resume smoke over two of 1,380 authorized frames.
- Advanced the MLFF dependency graph to schema 18, architecture revision 13.
- Left the full production sweep, DATA7/DATA8 materialization, replay binding, and DATA9B execution to DATA9A9b.

# mdstats 0.20.52a0

## MLFF-DATA9A8 profile-aware observable comparison policies

- Added immutable, recipe/profile-bound observable comparison rules, two-level thresholds, score-uncertainty records, comparison results, and checkpoint-facing acceptance decisions.
- Added profile-aware comparison metrics for scalars, arrays, curves, distributions, peak locations, and exact categorical invariants without moving physical algorithms into the MLFF branch.
- Added condition- and atom-group-scoped aggregation, fail-closed role/capability/result-type checks, and pre-execution policy binding through observable activation evidence.
- Removed misleading flat material-profile and MLFF-generation aliases, cation-named objective/checkpoint properties, legacy partition aliases, and obsolete objective/checkpoint/selection-coverage readers.
- Retained only explicitly justified DATA4/DATA6 historical cache readers pending a dedicated evidence-cache migration decision.
- Advanced the MLFF dependency graph to schema 17, architecture revision 12.

# mdstats 0.20.51a0

## MLFF-DATA9A7e cross-system qualification

- Added immutable cross-system qualification policy, per-case evidence, clean-import evidence, and suite records.
- Added bounded DATA4-DATA7 qualification for generic crystal, amorphous solid, liquid, multiphase interface, and optional LTA-extension workflows.
- Generic qualification now rejects MLFF LTA implementation imports, legacy LTA top-level serialization fields, foreign profile lineage, and missing DATA7 selection evidence.
- Made MLFF LTA profile and selection exports lazy. Importing `mdstats` or using generic DATA4-DATA7 paths no longer imports `mdstats.training_data.lta_profile` or `mdstats.training_data.lta_selection`; accessing an LTA API loads only the requested extension module.
- Fixed a DATA7 profile-extension metric bug where an inner missing-mask accumulator shadowed the per-frame mask list when universal and extension feature blocks were fitted together.
- Added source/wheel and serialization qualification gates and updated the MLFF architecture/dependency graph for DATA9A7e.

# mdstats 0.20.50a0

## MLFF-DATA9A7d optional profile extensions and LTA migration

- adds immutable generic partition- and selection-stage profile-feature catalogs;
- migrates LTA ring, cage, window, site, and crossing payloads behind the optional `lta` extension adapter without changing their numerical algorithms;
- advances DATA4 to schema v3 and DATA6 to schema v4 while retaining DATA4-v1/v2 and DATA6-v1/v2/v3 read compatibility;
- removes LTA-named top-level fields from newly written DATA4/DATA6 evidence while retaining deprecated Python compatibility views;
- derives per-species metric and difficulty features from authorized data instead of a fixed Li/Na/K list;
- adds profile-defined MLFF focus groups for selection, objectives, and checkpoint constraints;
- replaces generic cation-ordering and LTA-site qualification language with structural-realization and optional-extension coverage evidence;
- advances the MLFF dependency graph to schema 15, architecture revision 10.

# mdstats 0.20.49a0

## MLFF-DATA9A7c phase and geometry profiles

- adds immutable phase/geometry selection plans derived only from explicit
  DATA9A7a material contracts;
- differentiates crystalline, amorphous, liquid, and molecular/gas defaults
  without moving numerical geometry into the MLFF branch;
- adds surface, interface, confined, bulk, and cluster atom-group priority
  policies with explicit missing-region warning codes;
- advances DATA6 to schema v3 with exact plan/policy/material-profile lineage
  while retaining DATA6-v1/v2 read compatibility;
- filters universal structural feature and event exposure by the active plan and
  prioritizes profile-defined region groups before generic per-element coverage;
- composes advisory physical-observable call profiles without hiding scientific
  analysis parameters or duplicating analysis algorithms;
- advances the dependency graph to schema 14, architecture revision 9.

# mdstats 0.20.48a0

## MLFF-DATA9A7b universal structural selection providers

- Added analysis-owned universal local-structure features for MLFF selection.
- Added profile/atom-group-aware DATA6 structural catalogs and generic events.
- Added DATA7 universal structural feature fitting and generic per-species environment coverage.
- Preserved DATA6-v1 read compatibility and optional LTA behavior.


# mdstats 0.20.47a0

## MLFF-DATA9A7a material-profile and atom-group contracts

- adds user-declared compositional material profiles with explicit phase,
  geometry, chemistry-modifier, and structural-extension identities;
- adds immutable static, metadata, provider-generated, and composite atom-group
  contracts with phase linkage and acyclic dependency validation;
- adds condition-axis and independence-axis catalogs without claiming that
  observed coverage or independence already exists;
- adds a runtime-checkable declarative `SystemProfileProvider` boundary and a
  digest-bound `MaterialProfileContracts` aggregate;
- advances DATA4 to schema v2 so profile contracts can be cached alongside raw
  features while retaining exact schema-v1 bundle/cache compatibility;
- rejects LTA feature construction under a declared generic profile unless the
  explicit hierarchical LTA extension is present;
- advances the MLFF dependency graph to schema 12, architecture revision 7,
  while leaving universal feature calculation and LTA migration to DATA9A7b-DATA9A7d.

# mdstats 0.20.46a0

## MLFF-DATA9A6c observable evidence and leakage closure

- verifies every caller-supplied collection identity against the arrays actually analyzed and keeps filesystem paths outside relocation-invariant scientific identity;
- requires symmetric reference/candidate trajectory-generation records for complete-lineage evidence and verifies each output collection digest;
- adds analysis-owned canonical result identities for all registered observable results without moving scientific serialization into the MLFF branch;
- adds explicit evidence roles, activation records, comparison-policy ordering, and fail-closed locked-test activation gates;
- corrects runtime/source identity, native-result binding contracts, packaged manual identity, release JSON validity, and source/wheel registry parity testing;
- advances the MLFF dependency graph to schema 11, architecture revision 6, with role-specific locked-test evidence and corrected forbidden dependencies;
- expands the thermomechanical and energetic validation architecture for harmonic free energies, invariance and long-range phonon corrections, convex-hull phase stability, reference-state identity, and thermal-conductivity ownership.

# mdstats 0.20.45a0

## MLFF-DATA9A6b architecture and observable-evidence consistency closure

- strengthens the analysis-owned observable recipe API with construction-time
  dependency validation, machine-checkable input requirements, versioned
  parameter schemas, warning capture, runtime identity, and capability digests;
- binds MLFF observable validation to immutable reference/candidate collection
  identities and candidate model/MD-protocol/runtime lineage;
- revises the MLFF architecture, stage plan, dependency graph, and documentation
  indices so generic material profiles are normative and LTA/ring/site semantics
  are optional enrichment;
- adds a separate thermomechanical and energetic validation architecture for
  EOS, elasticity, thermal response, stress-correlation viscosity, phonons,
  surfaces/interfaces, defects, and migration paths;
- preserves physical-observable algorithm ownership in the corresponding
  analysis modules.

# mdstats 0.20.44a0

## Physical-observable ownership and MLFF validation bridge

- Added an analysis-owned standardized registry for implemented structural, dynamical, spectral, topology, and transport observables.
- Added immutable JSON-safe observable calls and ordered recipes with dependency binding and tamper-evident digests.
- Added a thin MLFF reference/candidate orchestration bridge with advisory crystalline, amorphous, liquid, interface, and generic profiles.
- Kept native result objects and all numerical algorithms in their authoritative analysis modules.
- Added a dedicated structural-observables architecture manual and revised the MLFF, VACF/dynamics, topology-statistics, and framework/ring manuals separately.
- Documented implemented, missing, and planned-but-unimplemented physical validation capabilities.
- Added five focused bridge tests; the existing 266-test general structural/dynamical gate remains passing.

# mdstats 0.20.43a0

## MLFF-DATA9A5 deployment-artifact closure

- Added deterministic semantic FP32/FP64 MACE conversion with digest-recorded complete-model PyTorch serialization.
- Added exact post-reload parameter/buffer conversion verification and semantic state digests.
- Added required-by-default source-versus-reloaded inference probes with dtype-appropriate tolerances.
- Added immutable deployment policies, comparison records, artifacts, and canonical JSON manifests.
- Distinguished FP32-to-FP64 promotion from recovery of lost numerical precision.
- Safety-locked downstream runtime precision claims to false.
- Removed the planned mdstats-side LAMMPS precision qualification stage; LAMMPS is a downstream consumer of the selected model artifact.
- Kept DATA9B gated; production DATA6-DATA8 realization is the next scientific stage.

# mdstats 0.20.42a0

## MLFF-DATA9A5 critical-FP64 execution

- Added a MACE 0.3.16 `ScaleShiftMACE` runtime adapter that keeps the expensive model body in user-selected FP32 or FP64 while reducing atomic energies, virials, and stresses in FP64.
- Forces used for validation, evaluation, and Python/ASE MD are differentiated from the same FP64-accumulated energy and returned as FP64.
- Disabled TF32 under the critical precision policy.
- Added FP64 ASE MD-state auditing for positions, cell, masses, and momenta.
- Added user-facing MACE train/evaluate/head-selection wrappers and a calculator constructor that install the critical adapter explicitly.
- Kept optimization-time force and stress autograd in the selected model dtype because MACE/e3nn 0.3.16 rejects an FP64 scalar seed through the FP32 second-derivative path.
- Added immutable critical-precision and MD-state audit records to the real MACE execution gate.
- Fixed real head enumeration to use the qualified Python module rather than relying on a console script in `PATH`.

# mdstats 0.20.41a0

- Added MLFF-DATA9A4 selectable precision for MACE fine-tuning through `MaceOptimizerPolicy.default_dtype`.
- Bound `float32` versus `float64` into the immutable training-protocol identity and generated MACE configuration.
- Added serialized-model precision inspection for all floating parameters and buffers, with mixed-state and requested-dtype rejection.
- Added immutable foundation-to-trained-model precision-transition evidence.
- Enforced protocol precision during real MACE parser, loader, training, target-head, and evaluation smokes.
- Added a correct single-target-head passthrough for MACE 0.3.16, whose head-selection utility rejects an already single-head model.
- Verified one-epoch transfer from the supplied float64 MPA-0 medium checkpoint to both uniform float32 and uniform float64 models.
- Verified a real 300 K Na-LTA float32 one-epoch CPU smoke with finite energy, force, and stress evaluation output.
- Retained DATA9B as fail-closed until the 2,734-frame production DATA6--DATA8 realization is completed.

# mdstats 0.20.40a0

- Qualified the complete 27-trajectory, 37,632-frame bulk-LTA target corpus through DATA5.
- Added immutable DATA9A3 production qualification and resource records.
- Replaced quadratic DATA5 frame-to-strain lookup with a frame-UID index.
- Added verified serialized-digest reuse for large DATA3--DATA5 artifacts.
- Added fail-closed DATA5 usability gating and explicit temporal-block/weak-independence warnings.
- Kept DATA9B blocked on site coverage, production DATA6/DATA7, DATA8 jobs, and replay-corpus identity.

# mdstats 0.20.39a0

- Added MLFF-DATA9A2 real MACE configuration realization and execution-smoke records.
- Corrected MACE 0.3.16 YAML serialization for `atomic_numbers`, `heads`, nested head `E0s`, and lowercase `universal`.
- Realized preselected target/replay exposure through extended-XYZ `config_weight` scaling and removed unsupported `weight_pt`/`weight_ft` options.
- Added genuine parser, loader dry-run, one-epoch training, checkpoint/head inventory, target-head extraction, and finite evaluation-round-trip gates.
- Added deterministic subprocess thread containment and strict standard-output head parsing.
- Qualified the supplied complete offline dependency bundle, MPA-0 medium checkpoint, and real 300 K Na-LTA trajectory path.

# mdstats 0.20.38a0

- Added DATA9A offline MACE runtime bootstrap and qualification.
- Parse the exact MACE `setup.cfg` dependency contract into immutable records.
- Create isolated environments from explicit local ASE, MACE, build-tool, and dependency artifacts.
- Record the base interpreter, inherited Python paths, installation commands,
  artifact hashes, imported versions, declared-version mismatches, missing
  requirements, and blocking CLI exceptions.
- Added fail-closed MACE CLI smoke records and an offline wheelhouse qualification tool.
- Corrected the MACE dependency model: `python-hostlist`, `GitPython`, and `lmdb` are required by MACE 0.3.16 rather than optional.
- Supplied ASE 3.29.0 and MACE 0.3.16 installation succeeds; genuine CLI execution remains blocked until the missing dependency wheelhouse is supplied.
- Attempted dependency acquisition through the configured internal index and
  public PyPI; neither path could provide the required distributions in this
  execution environment, so no compatibility stubs were introduced.

# mdstats 0.20.37a0

- Added MLFF-DATA9A integration qualification and split DATA9 into qualification and execution gates.
- Added checkpoint-bound foundation-residual atomic-reference fitting while retaining an explicit from-scratch fallback.
- Hardened MACE extended-XYZ validation, replay property/provenance audits, portable staged bundles, and selectable training-ladder sizes.
- Added installed/source MACE qualification records; supplied MACE 0.3.16 compiles and imports at top level, while training import remains blocked by missing runtime dependencies.

# 0.20.36a0 - MLFF-DATA8 MACE artifacts and replay protocol

- Added verified MACE extended-XYZ and sidecar artifacts with explicit E0 mappings and DATA7 training weights.
- Added version-locked MACE v0.3.16 source probes, checkpoint-control policy, and loader dry-run exposure records.
- Added replay train/monitor preparation with geometry-disjoint retention evidence.
- Added immutable training-protocol identities and independent final/cross-validation fixed-file job bundles.
- Kept fold evaluation outside MACE training configs and locked interpolation tests sealed and unmaterialized.

# 0.20.35a0 - MLFF-DATA7 fitted metrics, atomic references, objectives, and deterministic selection - 2026-07-28

- Added canonical final-development and cross-validation-training feature-fit domains derived only from DATA5 evidence.
- Added fold-local and final-domain robust/standard feature metrics, explicit missing indicators, deterministic PCA, and block-dimension normalization.
- Added domain-local atomic-reference-energy fits with rank, singular-value, null-space, residual, and transferability diagnostics.
- Added explicit training-objective, configuration-weight, property-weight, and checkpoint-metric policies.
- Added quota-interleaved deterministic master selection, strict nested training-size ladders, and coverage/redundancy reports.
- Added immutable DATA7 orchestration, serialization, provenance, and tamper rejection.
- Validated the real VASP path with the supplied ASE 3.29.0 source distribution.

# 0.20.34a0 - MLFF-DATA6 LTA/model descriptors and blinded difficulty - 2026-07-28

- Added development-domain selection-grade LTA frame and Li/Na/K atomic-environment descriptors.
- Added lazy optional MACE calculator integration and checkpoint-bound descriptor sidecars.
- Added training-domain-only foundation-model energy, force, stress, and species-force residuals.
- Added blinded prediction catalogs for monitor/calibration/cross-validation evidence and sealed locked-test records.
- Added immutable DATA6 orchestration, serialization, provenance, and tamper rejection.
- Validated the real VASP path with the supplied ASE 3.29.0 source distribution.

# 0.20.33a0 - MLFF-DATA5 statistical partitions and leakage control - 2026-07-28

- Added autocorrelation-aware, condition-bounded `PartitionUnitCatalog` construction.
- Added deterministic outer development, checkpoint-monitor, uncertainty-calibration, locked-test, and purge roles.
- Added feasibility outcomes, calibration deferral, and machine-readable independence grades for replicas, cation orderings, thermodynamic runs, temporal blocks, and unresolved slow states.
- Added independent cross-validation folds with nested checkpoint monitors and same-run purge neighborhoods.
- Added role-specific blinding contracts and exact geometry/label/event/purge leakage audits.
- Added immutable DATA5 serialization and end-to-end ASE 3.29.0 VASP-path tests.
- Corrected DATA4 strain-feature field names used by the integrated VASP workflow.

# 0.20.32a0 - MLFF-DATA4 raw features, LTA states, events, and cache - 2026-07-28

- Added partition-independent thermodynamic, force, stress, cell, strain, density, and selected pair-geometry feature records.
- Added lightweight full-resolution LTA ring/site states for Li, Na, and K, including coordination, site change, ring-plane crossing, and framework-integrity evidence.
- Added event-burst detection before temporal thinning, with protected pre/event/post frame windows.
- Added deterministic canonical-JSON feature caches with source/frame linkage, checksums, replay, and tamper rejection.
- Added `PartitionRoleBudgetPolicy` as a request contract; DATA5 retains ownership of feasibility and role assignment.
- Added real ASE 3.29.0 VASP-path tests using the supplied source archive (`sha256=ef4e2caa38169e3fbbc4164764a060d1877a6692519a4bed82521328eeb0d9aa`).

# 0.20.31a0 - MLFF-DATA3 frame identity, eligibility, conditions, and strain - 2026-07-28

## Added

- Add immutable `FrameData`, `TrainingFrameRecord`, and `TrainingFrameCatalog` contracts.
- Add manifest-bound `source_occurrence_signature` and stable per-frame occurrence UIDs.
- Add label-independent exact geometry fingerprints, label payload digests, and labeled-configuration fingerprints.
- Add exact duplicate and restart-boundary detection across source occurrences.
- Add post-DFT `FrameEligibilityDecision` records with explicit hard reasons and warnings.
- Add source-level target/instantaneous temperature-condition records.
- Add deterministic reference-cell resolution and finite-strain reconstruction under ASE row-vector cell semantics.
- Add polar decomposition, linear, Green-Lagrange, and logarithmic strain records with rotation-separated tensor classes.
- Add source-independent and VASP-integrated DATA3 builders and focused specifications/tests.

## Changed

- Advance the MLFF training-data branch to MLFF-DATA3.
- Keep source-content identity separate from manifest occurrence identity so copied sources cannot collide in frame UID space.
- Treat unavailable optional source-quality assessment as a warning by default, not a reason to block otherwise valid frames.

# 0.20.30a0 - MLFF-DATA2 source and label-domain catalog - 2026-07-28

- Added public `mdstats.training_data` runtime contracts for deterministic JSON/YAML manifests and VASP source discovery.
- Added immutable source compositions, source catalogs, optional trajectory-assessment references, and source-level provenance.
- Added explicit `VaspEnergyLabelPolicy` selection of complete derivative-consistent named energy channels.
- Added decomposed theory, energy-reference, derivative, numerical-quality, and software-provenance identities.
- Added complete-link label-domain construction with overlap-aware PAW compatibility and fail-closed unresolved-domain behavior.
- Added SVD-based structural atomic-reference identifiability reports without using energy labels.
- Added DATA2 specifications, focused tests, release audits, and updated architecture status.

# 0.20.29a0 - MLFF-DATA1 shared correlated-sampling primitives - 2026-07-27

- Add the public source-independent `mdstats.sampling` package.
- Add immutable `AutocorrelationPolicy` and `AutocorrelationEstimate` records using the frozen FFT unbiased-autocovariance initial-positive-sequence estimator.
- Add `FrameInterval`, `CompleteFrameBlockPolicy`, and `CompleteFrameBlockPlan` with gap-safe contiguous runs and balanced all-frame remainder handling.
- Add deterministic balanced round-robin assignment and purged modulo-fold records.
- Refactor Stage 11 STAT1 and SAMP0 to consume the shared primitives while preserving exact numerical values, JSON payloads, signatures, and public APIs.
- Add the MLFF-DATA1 Markdown/PDF specification and focused parity, serialization, gap, remainder, assignment, purge, and public-export tests.
- Advance the MLFF training-data branch to MLFF-DATA2 source and label-domain cataloging.

# 0.20.28a0 - MLFF-DATA0 training-data architecture - 2026-07-27

- Add the canonical `mdstats.training_data` architecture for certified AIMD ingestion, label-domain separation, frame eligibility, leakage-controlled partitioning, deterministic diversity selection, MACE multi-head replay artifacts, and active learning.
- Require independent fresh-model cross-validation jobs; fixed outer validation, uncertainty calibration, and locked tests remain separate evidence domains.
- Separate immutable frame facts from eligibility, partition, selection, exposure, and acquisition decisions.
- Require fold-local feature transforms and training selection during cross-validation.
- Freeze one target electronic-structure label domain per initial MACE bundle, with an optional replay head and disjoint replay-retention monitor.
- Add atomic-reference-energy rank/null-space diagnostics before `E0s: estimated`, canonical stress conventions, source-independent duplicate fingerprints, hierarchical LTA strata, event-before-thinning order, and constructive nested training-set prefixes.
- Distinguish pre-DFT candidate admissibility from post-DFT labeled-frame eligibility and exclude locked tests from active-learning calibration.
- Lock the initial adapter target to `mace-torch==0.3.16` with implementation-time CLI and source snapshots.
- Add nested checkpoint-monitor domains so held-out cross-validation folds never control stopping or checkpoint choice.
- Separate structural E0 identifiability from fold/final training-domain atomic-reference fits and enforce per-domain elemental support.
- Separate geometry fingerprints from label payload digests, add machine-readable partition-independence grades, and define block/species-normalized feature metrics.
- Move partition-critical LTA site/event states before outer partition locking.
- Isolate locked tests in a post-freeze evaluation bundle with no test path in the MACE training configuration.
- Add replay-retention-constrained checkpoint selection and final-committee-bound uncertainty calibration.
- Make active-learning child datasets append-only with inherited existing roles by default.
- Add partition-role feasibility, normative ASE row-cell strain conventions, training-domain difficulty-feature blinding, quota-interleaved selection budgets, explicit objective/weight/checkpoint metrics, and calibration applicability domains.
- Bind cross-validation to the complete naive/replay `TrainingProtocolIdentity`; replay preparation now precedes replay-aware fold jobs.
- Define version-tested MACE target-last checkpoint control, save-all external replay/cation checkpoint auditing, and realized `real_pt_data_ratio_threshold` exposure accounting.
- Restrict the first adapter to fixed-file native MACE training; custom epoch resampling is deferred to an explicit runtime adapter.
- Split sealed test artifacts, protocol freeze, evaluation activation, and evaluation results into distinct records.
- Runtime behavior remains unchanged; MLFF-DATA1 shared sampling primitives is the next implementation gate.

# 0.20.26a0 - Stage 11E-GR3 fixed-kernel scientific grid refinement - 2026-07-27

- Add signed `ScientificGridRefinementPolicy` and exact `stage11_grid_stopping_v1` records over one fixed Cartesian kernel, source, resource policy, and SAMP0 partition.
- Add deterministic factor-two GR1 ladders with the physical $\Delta_{\max}/\sigma_{\min}\le 0.5$ gate and one additional post-gate level needed for two consecutive comparisons.
- Add orthogonal `DensityFieldResolutionCertificate`, `BasinGridConvergenceCertificate`, and `CorridorGridConvergenceCertificate` outcomes.
- Add periodic basin correspondence, overlap/probability/split/merge/ambiguity evidence, corridor bottleneck/width/density/support comparisons, and explicit missing-evidence behavior.
- Add canonical replay, tamper rejection, source/resource/kernel/cross-fit identity checks, and plotting-import isolation.
- Advance the Stage 11 architecture to revision 56; Stage 11E-GR4 is next.

# 0.20.25a0 - Stage 11E-GR2 plotting grid adaptation - 2026-07-27

- Add signed plotting-owned `DensityVisualGridAdaptation` records over common GR0 geometry and optional GR1 replay plans.
- Adapt atomic- and framework-density field production to consume the common selected grid and preserve established values and metadata.
- Preserve visual Gaussian/grid coupling, spread-aware refinement, diagnostics, warnings, dense/local-sparse routing, meshes, and browser/scene admission.
- Add canonical replay, tamper rejection, exact old/new field and metadata oracle comparisons, and analysis-layer rendering-import isolation tests.
- Advance the Stage 11 architecture to revision 55; Stage 11E-GR3 is next.

# 0.20.24a0 - Stage 11E-GR1 common budgeted planning and grid ladders - 2026-07-27

- Add signed `DensityLogicalGridPlan` target/finest-feasible decisions under scientific logical-voxel limits.
- Add exact deterministic nested-grid ladders with separate target-reached, budget-limited, and level-limited outcomes.
- Add backend-independent `DensityFieldReuseKey` cache identities and fail-closed numerical-reuse checks.
- Add backend candidate/selection records that preserve the frozen logical grid and fixed kernel.
- Move the plotting-private finest-budgeted shape helper behind an analysis-owned compatibility adapter, preserving the zero-target sentinel.
- Advance the Stage 11 architecture to revision 54; Stage 11E-GR2 is next.

# 0.20.23a0 - Stage 11E-GR0 common grid geometry and diagnostics - 2026-07-27

- Add immutable triclinic `DensityGridGeometry` records, deterministic shape/interval resolution, JSON replay, and physical-resolution ratios.
- Move cell-equivalence, reciprocal-resolution, periodic Frechet/Karcher mean, and periodic-spread diagnostics into analysis ownership.
- Add analysis-owned periodic Gaussian-stencil moments, CIC covariance, and effective artificial-broadening diagnostics with explicit resource failures.
- Preserve plotting API, class identity, serialized values, metadata, and graph-specific exception translation through compatibility adapters.
- Validate exact plotting-oracle parity, oblique-cell Euclidean geometry, periodic invariance, dense stencil references, and no rendering-layer imports.
- Advance the Stage 11 architecture to revision 53; Stage 11E-GR1 is next.

# 0.20.22a0 - Stage 11E-SAMP0 cross-fit sampling foundation - 2026-07-27

- Add signed complete-system blocks and `EvidenceCrossfitPartition` records bound to one accepted STAT1 regime and immutable E0b catalogs.
- Add disjoint explicit holdout domains and a nested discovery/model-selection alternative that cannot inspect held-out validation evidence.
- Add local autocorrelation, complete-system effective-sample, represented-time, block, and replica diagnostics under `SamplingAdequacyPolicy`.
- Add the exact serialized `stage11_feature_correspondence_v1` cost, type, ambiguity, and outcome contract.
- Add all-block final-refit lineage separation, serialization replay, source mismatch rejection, and focused SAMP0 tests.

# 0.20.21a0 - Stage 11E-STAT2 ensemble-specific admissibility - 2026-07-27

- Add signed `EnsembleAdmissibilityPolicy`, reweighting/approximation provenance,
  per-regime permissions, and `PmfAdmissibilityCertificate` records.
- Keep NVE microcanonical by default, distinguish NVT Helmholtz and NpT Gibbs
  landscapes, and require explicit verified promotion paths.
- Add immutable E0b `EvidenceAdmissibilityOverlay` records with exact regime,
  position, joint-force, and PMF-force masks.
- Integrate full-source STAT2 metadata into `read_vasp_frames` and add
  `assess_vasp_pmf_admissibility`.
- Add focused direct-ensemble, diagnostic fallback, provenance, replay, overlay,
  and public-API tests.

# 0.20.20a0 - Stage 11E-STAT1 production-regime catalog - 2026-07-27

- Add source-observable block construction, change-point detection, stationarity diagnostics, and signed `ProductionRegimeCatalog` records.
- Test declared continuation boundaries rather than trusting them, and keep selection-conditioning provenance explicit.
- Update the STAT0 NVE drift thresholds to 1 meV/(atom ps) for strict quality and 26 meV/(atom ps) for hard failure.
- Replay the real Na-LTA NVE continuation as no detected heating transient but stationarity-ambiguous and diagnostic-only because of measurable drift.

# 0.20.19a0 - Stage 11E-STAT0 trajectory temperature and quality verdict - 2026-07-27

- Add source-general immutable `IonicTemperatureDefinition`, `IonicTemperatureStatistics`, `EnergyConservationStatistics`, `RealizedEnsembleConsistency`, `TrajectoryQualityCheck`, `TrajectoryQualityPolicy`, and `TrajectoryQualityVerdict` records.
- Reconstruct ionic temperature from the exact ENS0 kinetic-energy channel and an explicit active degree-of-freedom definition.
- Add autocorrelation-aware effective sample counts, block means, confidence intervals, and temperature-drift diagnostics.
- Separate catastrophic hard-integrity failures from manageable numerical-quality degradation and classify each check as hard-required, verdict-critical, method-specific, or optional.
- Implement the exact outcomes `strictly_qualified`, `degraded_quality`, and `unqualified`; only the last raises by default.
- Add NVE total-energy drift, residual, jump, energy-identity, full fixed-cell-matrix, and inactive-thermostat consistency diagnostics from exact named source channels.
- Integrate full-source STAT0 metadata into `read_vasp_frames` and add `assess_vasp_trajectory_quality`.
- Validate the real 1,500-step Na-LTA source as degraded but analyzable, with about 320.2 K mean ionic temperature and -0.2046 eV/ps energy drift.

# 0.20.18a0 - Stage 11E-ENS1 ensemble and force-provenance certification - 2026-07-27

- Added signed source-general simulation-control certificates.
- Added deterministic VASP ensemble inference from effective controls rather than `SYSTEM`.
- Added thermostat, barostat, cell, bias, constraint, force-provider, velocity, and continuation provenance.
- Integrated ENS1 metadata into `read_vasp_frames`.
- Added synthetic and real-source focused tests.

# 0.20.17a0 - Stage 11E-ENS0 source-control and energy reconstruction - 2026-07-27

- Add source-general immutable source identity, companion manifest, exact control-value, named energy-channel, and numerical-MD-quality records.
- Add a streaming VASP XML adapter that preserves explicit `<incar>` and effective `<parameters>` controls with original names, paths, typed values, and precedence.
- Retain `SYSTEM` only as `comment_only` metadata; do not use it for ensemble or thermodynamic inference.
- Preserve every named ionic-step energy channel, missing entry, completeness fraction, unit, semantic role, and signed value digest.
- Reconstruct `POTIM`, `NSW`, `EDIFF`, `NELM`, `NELMIN`, `ALGO`/`IALGO`, `PREC`, `LREAL`, `ROPT`, `ENCUT`, `ISYM`, SCF iteration counts, and source-field completeness.
- Bind primary bytes, atom order, frame axis, coordinate/cell payload, companion manifest, program, and version in `SourceTrajectoryBundleIdentity`.
- Integrate ENS0 metadata into `read_vasp_frames` while preserving existing normalized trajectory behavior.
- Add a permanent ENS0 specification, focused synthetic tests, and real 1,500-step Na-LTA source replay.

# 0.20.16a0 Stage 11 architecture revision 44


### Architecture revision 45

- repaired Stage 11 force, cross-fitting, transition-state, E8b, and late-kinetics dependencies;
- separated mechanical force refinement from canonical thermodynamic mean-force validation;
- added thermodynamic-validation evidence blocks and concrete grid/correspondence stopping contracts;
- assigned final event, rate-bound, gating, propagation, and integrated-ground-gate ownership;
- moved baseline implementation bullets out of the normative manual.
- Adopt a partial refactor of the tested atomic-density grid-resolution machinery.
- Plan analysis-owned common grid geometry, periodic spread, reciprocal-resolution,
  artificial-broadening, budgeted planning, and dense/local-sparse feasibility layers.
- Keep plotting's adaptive visual bandwidth/grid policy separate from Stage 11 fixed-kernel
  scientific convergence.
- Add GR0-GR5 implementation stages and separate field, basin, and corridor convergence
  certificates.
- Require budget-limited unconverged ladders to remain unresolved and keep grid convergence
  orthogonal to sampling confidence.
- Add a permanent scientific grid-refinement reuse specification and focused contract tests.

# 0.20.16a0 Stage 11 architecture revision 43

- Add equipartition ionic-temperature reconstruction with signed active ionic degrees of freedom, represented-time mean and standard deviation, autocorrelation-aware confidence, and drift diagnostics.
- Require deep `vasprun.xml` parsing of explicit/effective controls and per-step SCF traces, including `POTIM`, `EDIFF`, `PREC`, `LREAL`, `ROPT`, and `NELM`.
- Add the exact trajectory-quality outcomes `strictly_qualified`, `degraded_quality`, and `unqualified`.
- Permit degraded-quality trajectories to continue with one warning and immutable result flags; reserve default rejection for catastrophic integrity failure.
- Keep execution quality separate from ensemble- and method-specific thermodynamic admissibility.
- Add a permanent trajectory-temperature/quality specification and focused documentation tests.

# 0.20.16a0 Stage 11 architecture revision 42

- Repaired ENS/STAT/E0b dependencies and moved source energy-channel reconstruction
  before conservation analysis.
- Removed assumed-stationarity promotion paths from the architecture and adjacent
  specifications.
- Added cross-fitted basin and transition-corridor sampling validation, orthogonal
  confidence fields, and a separate STAT3 held-out distribution-stability stage.
- Split NVT, NVE, NpT, and biased thermodynamic estimands and restricted MBAR to
  datasets with cross-evaluated reduced potentials or a certified equivalent map.
- Renamed the real fixture to the Na-LTA NVE continuation pilot and moved detailed
  release history into a non-normative status appendix.

## 0.20.16a0 - Architecture ownership and pilot-maintainability refactor - 2026-07-26

- Refactor Stage 11 documentation into Part I structural architecture and Part II registered statistical-site/kinetic architecture.
- Remove the stale duplicate Stage 11C-I roadmap from the framework/ring manual and replace it with a normative structural handoff.
- Replace the duplicated Part II structural chapter with an explicit Part I dependency contract.
- Add permanent architecture-manual ownership/PDF-parity and pilot-common specifications.
- Add private `_pilot_common.py` for canonical JSON, SHA-256 signing, immutable metadata, array digests/accounting, validators, and evidence replacement.
- Preserve all public E8a schemas, exception types, signatures, and scientific gates.
- Regenerate maintained Stage 11 and density-pilot PDF counterparts from current Markdown sources.
- Add focused helper, pilot, API, specification, and clean-archive validation.

## 0.20.15a0 - Stage 11E8a implementation and regression closeout - 2026-07-26

- Mark Stage 11E8a-S0 through S4 implementation complete while retaining the real Na-LTA dossier as `scientifically_partial`.
- Restore the documented deterministic LD6 research defaults: 2,000 periodic phase evaluations, a 4,000,000-node research ceiling, and a 512 MB workspace ceiling subject to active memory.
- Make Phase-A density planning use exact logical-node counts whenever atomic or framework `grid_shape` is explicit, eliminating fictitious maximum-sized mesh failures.
- Preserve runtime-derived production guardrails while isolating hard-limit tests from unrelated earlier caps.
- Make `fast-simplification` research tests skip cleanly in a base installation; production calls still fail with the interactive-extra installation instruction.
- Standardize sparse-storage assertions on the public `max_density_stored_block_values` resource name.
- Validate every test file in bounded groups: 1,493 passed and one optional interactive test module skipped; no regression failure remains.
- Add the closeout specification, architecture revision 39, release audit, test matrix, manifest, checksums, and rebuilt source/wheel artifacts.

## 0.20.14a0 - Stage 11E8a-S4 force-density and path readiness - 2026-07-26

- Add `mdstats.analysis.density.pilot_force_paths` with signed source-bound S4 orchestration.
- Execute the existing Stage 11E3 force-refinement contract without promoting complete physical forces into PMF-admissible equilibrium samples.
- Add signed force-density agreement diagnostics with joint/PMF sample counts, support fractions, local-refinement outcomes, residuals, and spatial-authority gating.
- Add signed Stage 11E6/11E6b transition-path readiness that refuses final segmentation until both the S2 spatial hypothesis and a source-compatible E5 validated frozen-state catalog are authoritative.
- Distinguish missing required evidence from executed-but-blocked evidence: the real dossier becomes `scientifically_partial` with no missing evidence IDs and explicit force-density/path blockers.
- Validate the real 1,500-frame ASE trajectory: 1,440 represented-time joint force samples, zero PMF-admissible samples, 24 provenance-rejected E3 refinements, eight provisional passages, and zero jumps.
- Add public exports, permanent specification, example, focused tests, architecture revision 38, benchmark, release audit, and rebuilt source/wheel artifacts.

## 0.20.13a0 - Stage 11E8a-S3 structural mapping and temporal support - 2026-07-26

- Add `mdstats.analysis.density.pilot_structural_temporal` with signed source-bound S3 orchestration.
- Package and digest-bind the persistent Na-LTA framework topology and 82 primitive rings complete through ring size eight.
- Reconstruct ordered 4R/6R/8R oxygen polygons by local triclinic minimum-image unwrapping and retain their actual serrated boundaries rather than circular or elliptical substitutes.
- Add deterministic attractor-to-ring candidate records with plane distance, polygon clearance, side, and radial fraction relative to the serrated boundary.
- Extend Stage 11E4 with exact coordinate-identical spatial-partition transfer from represented-time discovery quadrature to the full-weight trajectory catalog.
- Execute provisional temporal support over all 36,000 Na samples while preserving unsupported, transition, censoring, return-excursion, and stride distinctions.
- Keep structural and temporal evidence partial when upstream S2 scale/grid topology is unresolved, even when all ring mappings are unique and temporal support is persistent.
- Reduce the remaining E8a blockers to force-density agreement and observed transition paths; add public exports, permanent specifications, examples, focused tests, real ASE replay, architecture revision 37, benchmark, and release audit artifacts.

## 0.20.12a0 - Stage 11E8a-S2 density refinement and attractor lineage - 2026-07-26

- Add `mdstats.analysis.density.pilot_refinement_lineage` with signed bandwidth/grid/reference controls and source-bound S2 orchestration.
- Execute the Stage 11E1 Cartesian bandwidth ladder at 0.40, 0.50, and 0.60 Å and deterministic Stage 11E2 attractor lineage.
- Add central-bandwidth 12³→16³ topology refinement, reusing the identical signed S1 16³ product instead of recomputing it.
- Add a reference-cell sensitivity certificate with exact fixed-cell shortcut and a full alternative-reference registration path for nonidentical cells.
- Keep scale selection and topology fail-closed when saddle adjacency changes; do not promote the persistent 24-basin correspondence to a converged kinetic state model.
- Add public exports, permanent specification, example, focused tests, real ASE 3.29.0 replay, architecture revision 36, benchmark, and release audit artifacts.

## 0.20.11a0 - Stage 11E8a-S1 framework-registered density and attractor pilot - 2026-07-26

- Add `mdstats.analysis.density.pilot_density_attractors` for the first real E1/E2 Na-LTA execution boundary.
- Select all 144 framework atoms with a center-of-geometry matched-reference translation gauge and execute an independent center-of-mass sensitivity gauge.
- Add an exact certified-local-convexity fast path for unique periodic translation means, preserving the exhaustive multiseed fallback outside the certified chart.
- Preserve the full 1.499 ps represented-time measure through deterministic contiguous-bin frame quadrature.
- Execute and source-bind one periodized Na density and one support-restricted attractor catalog with field, topology, and provisional-core evidence.
- Keep structural mapping, reference-cell sensitivity, temporal support, force-density agreement, transition paths, and rates fail-closed.
- Add signed S1 options and gauge-validation records, public exports, permanent specifications, examples, focused synthetic tests, real ASE 3.29.0 replay, architecture revision 35, and release audit artifacts.

## 0.20.10a0 - Stage 11E8a-S0 real-trajectory source bootstrap - 2026-07-25

- Add `mdstats.analysis.density.pilot_execution` for the first executable real-data boundary after the raw 300 K Na-LTA trajectory becomes available.
- Bind the exact raw trajectory bytes by SHA-256 to a physical fixed-cell C0 registration and a compact E0b Na position/force sample catalog, and reject collections whose reader provenance points to another source path.
- Validate the exact 168-atom Na-LTA composition, full periodicity, physical time axis, fixed registered cell, coordinate round trips, and force-work invariance.
- Record source-channel completeness, force availability, untested stationarity, deterministic numerical-payload memory, wall time, artifacts, and signatures without fabricating downstream evidence.
- Keep the E8a dossier fail-closed as `blocked_missing_required_evidence` until the real density, attractor, temporal, force-agreement, path, and network stages are executed.
- Add a permanent specification, public exports, focused source-binding tests, and architecture revision 34. Stage 11E8a-S1 density and attractor pilot gauge is next.

## 0.20.9a0 - Stage 11E8a pilot dossier and execution preflight - 2026-07-25

- Add `mdstats.analysis.density.pilot_audit` with immutable dataset, artifact, evidence, resource, outcome, and report contracts.
- Add the complete E8a required-evidence taxonomy with accepted-frame and unresolved fractions, source digests, explicit blockers, and fail-closed overall status.
- Add a real-ASE audit of the bundled 168-atom Na-LTA reference, 2,000-frame topology summary, primitive-ring catalog, 1,300-frame all-species density benchmark, and plotting summary.
- Preserve those artifacts as legacy or partial evidence only; do not reconstruct E0b--E7 site, force, residence, path, or network conclusions without raw coordinates.
- Add deterministic Markdown/JSON dossier rendering, artifact SHA-256 binding, strict serialization, transactional resource limits, public exports, a permanent specification, and architecture revision 33.
- Record the real pilot as blocked because the raw trajectory and complete serialized E0b--E7 products are absent. Stage 11E8a execution remains mandatory before E8b.

## 0.20.8a0 - Stage 11E7 observed network and transfer validation - 2026-07-25

- Add `mdstats.analysis.density.observed_network` downstream of frozen E5 states and E6b path ensembles.
- Preserve statistical-state instances, canonical transfer correspondence, structural complexes, validated symmetry orbits, and semantic classes as separate identities.
- Create directed periodic observed edges only from successful E6b ensembles and retain event, duration, translation, and structural-path evidence.
- Add exact structural-versus-observed comparison with observed-and-structural, observed-off-structural, structural-unobserved, and unavailable outcomes.
- Add compact transferred state models retaining every source anchor, periodic circular summaries, occupancy/basin statistics, structural identities, and semantic classes without rates or refitting.
- Add immutable final-validation and external-transfer domain metadata with certified periodic metric assignment, radius rejection, ambiguity retention, and explicit off-network, failed, and domain-mismatch outcomes.
- Add deterministic signatures, strict serialization, transactional resource limits, public exports, a permanent specification, architecture revision 32, and real-ASE focused validation. Stage 11E8a is next; Stage 11E-PMF remains optional.

## 0.20.7a0 - Stage 11E6b observed transition-path ensembles - 2026-07-25

- Add `mdstats.analysis.density.transition_paths` downstream of E0b and E6.
- Reconstruct exact registered passage paths with compact sample, frame, physical-time, represented-time, wrapped-fractional, and integer-image provenance.
- Add resolved, cadence-bracketed, target-ambiguous, gap-interrupted, failed-excursion, recrossing, and right-censored first-hit statuses without interpolation.
- Make the integer endpoint image-shift difference part of periodic event and ensemble identity.
- Add optional source-bound ring, sector, ordered coordination, harmonic, aperture, puckering, occupancy, density, PMF, and transformed-force path evidence.
- Add `RegistrationCompatibilityClass` for compatible pooling of independent registrations with explicit state correspondence and unit convention.
- Add single-path, undersampled-ensemble, and resolved-ensemble statuses plus optional support-gated diagnostic path clustering.
- Add local occupancy context and isolated, overlapping, candidate-exchange, candidate-concerted, and unresolved collective-event diagnostics without a many-body model.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 31, and real-ASE focused validation. Stage 11E7 is the next mandatory boundary; Stage 11E-PMF remains optional.

## 0.20.6a0 - Stage 11E6 final hysteretic segmentation and residence statistics - 2026-07-25

- Add `mdstats.analysis.density.final_segmentation` downstream of E0b, E4, E5, and optional E5b.
- Add immutable frozen, selected-moving, and static/dynamic-agreement membership policies without nearest-center filling.
- Add qualified core-entry and basin-retention hysteresis with explicit exit confirmation.
- Add final residence intervals, retained excursions, resolved transitions, recrossings, return excursions, unresolved gaps, assignment conflicts, boundary-induced passages, and right censoring.
- Preserve exact atom, segment, state, and compact sample identities with represented-time accounting.
- Add ion-time, uncensored residence summaries, mean/median residence durations, mean-occupancy bounds, vacancy bounds, and multiple-occupancy bounds.
- Add declared threshold/stride sensitivity runs and stable, unstable, insufficient-event, and ensemble-unavailable certificates.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 30, and real-ASE focused validation. Stage 11E6b is next.

## 0.20.5a0 - Stage 11E5b geometry-conditioned site refinement - 2026-07-25

- Add `mdstats.analysis.density.geometry_conditioning` downstream of frozen E5 states and exact E5a local-coordinate fingerprints.
- Add framework-only predictor tables and reject mobile-ion-derived structural predictors.
- Add one-pass represented-time weighted affine center fits on frozen discovery assignments with rank, condition, residual RMS, and covariance diagnostics.
- Add separate selection and untouched final-validation block scores; retain the dynamic model only when selection improves and validation does not contradict the gain.
- Add rigidly translated nested moving cores/basins, preserving frozen shapes and persistent global state identity.
- Retain static, candidate-dynamic, and selected memberships simultaneously.
- Add atom/segment-local ion, center, boundary, and comoving displacement records with explicit boundary-induced crossing diagnostics.
- Add exclusive assignment-conflict states, overlap fractions, and lower/upper occupancy bounds without double counting.
- Make numerical density tests independent of transient host memory by using a shared explicit synthetic runtime-resource scope while leaving dedicated runtime-resource tests unmodified.
- Restore the unrestricted historical atomic-density module to the release gate by updating obsolete dense-voxel-backoff and render-limit fixtures to the current sparse and browser-admission contracts.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 29, and real-ASE focused validation. Stage 11E6 is next.

## 0.20.4a0 - Stage 11E5a species-dependent coordination fingerprints and classification - 2026-07-25

- Add `mdstats.analysis.density.coordination_fingerprints` downstream of the frozen E5 catalog and registered C0A3 structural view.
- Retain exact state-conditioned physical M--O/M--T sample matrices, persistent atom/image identities, and direct local ion coordinates as the authoritative records.
- Add separate equal-index cyclic DFTs, boundary-measure angular moments, and rank-safe actual-angle least-squares spectra without conflating their measures.
- Add centered-reference and framewise geometry-forward coordination predictions with explicit residual spectra that remain diagnostic rather than exact component separation.
- Add phase-amplitude, circular-resultant, oxygen/gap/sector locking, bilateral, annularity, corrugation, and geometry-consistency evidence.
- Add occupancy-conditioned fingerprint contexts and explicit mixture status without automatically splitting or refitting the frozen E5 state.
- Add conservative point, bilateral, discrete off-center, smooth/corrugated annular, cage, general, and ambiguous structural classes while preserving all plausible structural associations.
- Restore the MSD-specific single-frame compatibility error discovered by the first real-ASE regression run.
- Install and validate against real ASE 3.29.0 from the supplied official source distribution; remove ASE-shim dependence from the release gate.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 28, and focused validation. Stage 11E5b is next.

## 0.20.3a0 - Stage 11E5 joint evidence validation and structural association - 2026-07-25

- Add `mdstats.analysis.density.evidence_validation` as the source-bound validation layer downstream of E0b, E1, E2, E4, optional E3, and C0A3 registered structural geometry.
- Add orthogonal spatial, temporal, force, force-score, stationarity, geometry, curvature, final-validation, and overall-certification statuses without replacing disagreements by one score.
- Compare transformed force covectors only with the Stage-11E3 density-score covector in the same registered coordinate measure.
- Add explicit discovery, selection, final-validation, and optional-refit blocks with independent, selection-conditioned, unavailable, and insufficient-transfer outcomes.
- Add fail-closed structural association to persistent ring, window, and tile/cage objects under an explicit periodic-metric radius, retaining ambiguity and prohibiting nearest-object fallback.
- Add statistical-state records, preliminary structural complexes, opt-in symmetry-orbit candidates, conservative exchangeability checks, and a prohibition on default symmetry augmentation.
- Add distinct `ValidatedFrozenCatalog` and `FinalRefitCatalog` contracts; a final refit inherits the selected decision but never inherits parameter-validation evidence.
- Preserve force-free spatial/temporal validation while prohibiting force-validation claims, and retain one-transition early/late block limitations as insufficient or selection-conditioned evidence rather than rejection.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 27, and focused validation. Stage 11E5a is next.

## 0.20.2a0 - Stage 11E4 provisional assignment and temporal-persistence diagnostics - 2026-07-25

- Add `mdstats.analysis.density.temporal_assignment` as the source-bound temporal-evidence layer downstream of E0b, E1, E2, and optional E3.
- Add immutable raw core, basin, transition-region, supported-background, unsupported, unresolved, and core-overlap memberships with no nearest-center filling.
- Add atom- and segment-aware core visits, preliminary core-entry/basin-retention residences, and explicit jump, return-excursion, unresolved-gap, and right-censored passages.
- Add local periodic-coordinate autocorrelation diagnostics using Geyer's initial-positive-sequence truncation, with frame-only status for irregular physical-time stride.
- Add separate temporal-support and evidence-pattern statuses, including one jump, repeated hopping, short excursions, mixed evidence, and unresolved gaps.
- Add stride-sensitivity, dwell, censoring, short-excursion, and recrossing diagnostics without producing final Stage-11E6 events.
- Preserve spatial membership but prohibit invented continuity for independent ensembles and across E0b source-segment resets.
- Add deterministic signatures, strict serialization, resource preflight, public exports, a permanent specification, architecture revision 26, and focused validation. Stage 11E5 is next.

## 0.20.1a0 - Stage 11E3 local mean-force and harmonic/manifold refinement - 2026-07-25

- Add `mdstats.analysis.density.force_refinement` as the PMF-admissible force-evidence layer downstream of Stage 11E2.
- Add matched-kernel conditional mean-force covectors using the exact Stage-11E1 periodized Gaussian, image truncation, and support mask.
- Add local force covariance, effective sample size, complete-system block standard errors, and source-bound resource preflight.
- Convert registered Cartesian force covectors to the E1 fractional coordinate measure by work invariance before comparison with `DensityScoreCovector`.
- Add represented-time weighted symmetric local force fits with intercepts in lifted periodic residence charts.
- Add stable-point, unstable/saddle, soft-manifold, flat, and unresolved curvature classes, with point centers reported only when identifiable and chart-contained.
- Add residence-basin covariance versus $k_\mathrm{B}TK^{-1}$ diagnostics and density-force residuals without forcing consistency.
- Preserve every Stage-11E2 spatial attractor when forces are unavailable, PMF-inadmissible, under-sampled, rank deficient, ill conditioned, or inconsistent.
- Add deterministic signatures, strict serialization, public exports, a permanent specification, architecture revision 25, and focused validation. Stage 11E4 is next.

## 0.20.0a0 - Stage 11E2 deterministic density attractors and supported basins - 2026-07-25

- Add `mdstats.analysis.density.attractors` as the canonical support-restricted periodic topology layer downstream of Stage 11E1.
- Add deterministic periodic plateau components, negative-curvature isolated modes, derivative-supported one-dimensional ridges, and explicit unresolved flat components.
- Add complete logical-node cell classifications that keep unsupported or omitted sparse regions distinct from scientific background.
- Add deterministic steepest-ascent basin ownership, supported transition boundaries, and supported inter-basin saddle densities without adjacency through unknown space.
- Add isolated-mode and annular local periodic charts plus point-specific and local-ridge-depth provisional cores with explicit fallback provenance.
- Add attractor correspondence, bandwidth lineage, split/merge ambiguity, `SelectionValidationProtocol`, and explicit scale-consensus or competing-hypothesis results.
- Add separate topology-refinement certificates and refinement histories; Stage-11E1 field error is not treated as a topology certificate.
- Add periodic-metric k-means and optional precomputed-distance HDBSCAN comparison adapters that cannot replace the canonical basin catalog.
- Add deterministic signatures, strict serialization replay, resource preflight, public exports, a permanent module specification, architecture revision 24, and focused validation. Stage 11E3 is next.

## 0.19.99a0 - Stage 11E1 periodic species-density estimation - 2026-07-25

- Add `mdstats.analysis.density.species` as the source-bound periodic density estimator downstream of the Stage-11E0b species sample catalog.
- Add explicit physical-Cartesian and reference-material density-domain contracts with fail-closed variable-cell physical pooling.
- Add independent Gaussian kernel covariance and analysis geometry metric records, including Cartesian-to-fractional covariance transformation.
- Add a normalized triclinic Gaussian lattice-image oracle with conservative density, gradient, and Hessian image-tail bounds; no minimum-image Gaussian path is used.
- Add represented-time-weighted number density and probability density with separate ion-time, observation-measure, and mean-occupancy integrals.
- Add density score covectors, metric-raised gradient vectors, density Hessians, local effective sample sizes, and support-gated derivative claims.
- Add exact dense/block-packed logical-field agreement, deterministic periodic gathers, bandwidth ladders, and optional complete-system temporal-block standard errors.
- Add field-error and normalization certificates, transactional resource preflight, strict finite JSON replay, source binding, and tamper-evident signatures.
- Add public analysis/root exports, a permanent module specification, architecture revision 23, and focused validation. Stage 11E2 attractor, basin, lineage, and provisional-core discovery is next.

## 0.19.98a0 - Stage 11E0b registered position-force sample catalog - 2026-07-25

- Add `mdstats.analysis.site_samples` as the compact evidence boundary between C0 registration and later statistical-site discovery.
- Add segment-aware represented-time weighting with explicit trajectory reset boundaries, ensemble semantics, and fail-closed heating/production mixing.
- Add frame-major, species-compact registered position and transformed-force catalogs with immutable source and registration provenance.
- Add exact nested position, force, joint, structural, temporal, connectivity-flicker, and PMF-admissible evidence masks.
- Keep geometric force evidence distinct from equilibrium PMF-force evidence; PMF eligibility requires admissible registration, declared equilibrium, stationary sampling, and declared constant temperature.
- Add topology-regime assignments that exclude transition/flicker frames from structural evidence without discarding position-only records.
- Add lazy structural annotations and explicit fixed-domain registration groups for compatible independent trajectories.
- Add deterministic signatures, strict serialization replay, public exports, a permanent module specification, architecture revision 22, and focused validation.
- Resolve the prior E0b naming collision by renaming deferred scientific-density extraction work D0b-D0d. Stage 11E1 is the next implementation boundary.

## 0.19.97a0 - Stage 11E0a scientific density facade and ownership boundary - 2026-07-25

- Add the canonical `mdstats.analysis.density` package with backend-neutral scientific field and periodic-node protocols.
- Add zero-copy compatibility adapters and deterministic scientific field bundles around current dense and block-sparse numerical fields.
- Add canonical atomic and framework density preparation functions that preserve the current numerical producers and exact field objects.
- Separate `ScientificDensityResourcePolicy` from plotting-owned `DensityRenderingResourcePolicy`; scientific construction consumes no mesh, Plotly, browser, payload, or HTML budget.
- Keep current numerical options and field classes available through lazy analysis compatibility imports while excluding all 3-D render-option classes.
- Record permanent scientific ownership, temporary numerical ownership, resource signatures, and explicit non-consumption of rendering policy.
- Add module-owned specifications, architecture revision 21, public exports, and focused dense/sparse oracle validation.
- Stage 11E0b registered position-force sample catalog is the next implementation boundary.

## 0.19.96a0 - Stage C0B coordinate-consumer migration - 2026-07-24

- Add immutable `mdstats.coordinates.consumer_adapters` products that translate legacy displacement, velocity, density, trajectory, and framework-plotting options into shared C0 source and registration contracts.
- Migrate laboratory/reference-cell displacement preparation to C0A2 while preserving exact optional COG/COM zero-centering and existing estimator signatures.
- Migrate translation-only VACF/velocity preparation while preserving the exact instantaneous COG/COM drift convention and recording independent policy/signature provenance.
- Prepare one source-bound plotting coordinate view before framework averaging, trajectories, atomic density, framework vertex density, or framework edge density; plotting no longer computes a scientific drift vector.
- Preserve material, framework-registered, and laboratory plotting coordinates, legacy public options, and physical pair-geometry ownership.
- Add a bounded compatibility envelope for historically accepted smooth variable-cell deformation without hiding certifiable unimodular basis relabelings.
- Add an eight-ULP round-trip certification floor for very large legacy unwrapped coordinates while leaving returned coordinates unchanged.
- Add immutable metadata, deterministic signatures, public exports, a permanent module specification, architecture revision 20, and focused regression validation.
- Stage 11E0a scientific density facade and ownership boundary is the next implementation boundary.

## 0.19.95a0 - Stage C0A3 registered structural-view integration - 2026-07-24

- Add immutable `RegisteredStructuralGeometryView` records that bind one source collection, C0A2 registration result, compatible C2 ring geometry, and C3 atom-resolved ring boundaries.
- Preserve physical ring coordinates, orthonormal frames, apertures, areas, perimeters, planarity, and T--O distances unchanged while storing registered embeddings in separately named records.
- Transform persistent T/O atom images through the exact affine registration map and certify their registered fractional images against the registered cell.
- Reconstruct registered orthonormal ring frames from transformed oxygen polygons rather than affinely distorting physical frame axes.
- Add registered tile/cage centers, tile-face vertices and normals, and window centers when compatible frame tiling geometry is supplied.
- Add trajectory-only orientation-continuity diagnostics with registration segment resets and no invented continuity for independent ensembles.
- Add fail-closed source binding, unresolved-frame diagnostics, resource preflight, deterministic signatures, strict source-replay serialization, and analysis/root exports.
- Add a module specification, architecture revision 19, and focused validation. Stage C0B consumer migration is the next implementation boundary.

## 0.19.94a0 - Stage 11C3 atom-resolved structural ring boundaries - 2026-07-24

- Add persistent species-independent T/O atom boundary records with exact atom/image identities, local coordinates, ordered neighboring-T chemistry, and generic oxygen-environment signatures.
- Add exact equal-atom cyclic-index spectra with signed even-ring Nyquist handling, raw and normalized amplitudes, phase support, and explicit dihedral transform utilities.
- Add separate arc-length boundary-measure angular moments and rank-safe equal-atom or arc-length-weighted physical-angle fits with explicit rank, condition, regularization, residual, and uncertainty diagnostics.
- Add fail-closed singular-angle handling, oxygen-class splitting, radial symmetry-breaking, and reference-to-frame phase/amplitude continuity diagnostics.
- Add exact-source-bound optional LTA O(1)/O(2)/O(3) alias profiles with coverage, chemistry, and optional S6R alternation validation.
- Add deterministic source replay, strict JSON serialization, resource preflight, analysis/root exports, module specification, and architecture revision 18.
- Add focused synthetic and real LTA validation. Stage C0A3 registered structural-view integration is the next implementation boundary.

## 0.19.93a0 - Stage C0A2 affine registration and coordinate products - 2026-07-24

- Add immutable `RegistrationFitMetric` and `AnalysisGeometryMetric` contracts with independent provenance and coordinate-change rules.
- Add a certified triclinic closest-periodic-image solver using exhaustive integer enumeration bounded by a smallest-singular-value certificate; expose runner-up separation and exact/near ties.
- Add physical, translation-registered, and reference-material affine registration policies under the package row-vector convention.
- Add deterministic persistent reference sets with center-of-geometry, center-of-mass, or explicit positive weights.
- Add matched periodic framework-translation fitting, residual adequacy checks, competing-minimum diagnostics, and fail-closed ambiguity.
- Add segment-aware temporal translation-branch lifting and prohibit invented continuity for independent ensembles.
- Add registered cells, unwrapped Cartesian coordinates, wrapped fractional coordinates, and integer image shifts with round-trip validation.
- Transform forces as affine covectors, validate work invariance, and preserve separate geometric and PMF admissibility statuses for structure-fitted maps.
- Add Stage-C0A2 module specifications, architecture revision 17, focused tests, deterministic serialization, and root-package exports.
- Stage 11C3 atom-resolved structural ring boundary and harmonics is the next implementation boundary.

## 0.19.92a0 - Stage C0A1 source semantics and periodic lattice gauge - 2026-07-24

- Add the root `mdstats.coordinates` package and canonical Stage-C0 source-coordinate contracts.
- Record normalized position, velocity, force-covector, and box-origin frame semantics during source normalization, with backward-compatible inference for older collections.
- Add deterministic source digests, source-field semantics, force-source provenance, and immutable source-coordinate contract signatures.
- Separate geometric force-transform validity from PMF-force admissibility; unknown force provenance no longer blocks position-only analyses or overclaims thermodynamic force evidence.
- Add cell determinant, condition-number, handedness, periodic-axis, and lattice-basis continuity validation.
- Detect nontrivial unimodular basis relabelings, reject them by default, and optionally reconcile them explicitly with retained integer gauge matrices.
- Add explicit-matrix and gauge-bound selected-source-frame reference-cell definitions, initially restricted to full-rank fully periodic 3D cells.
- Add focused Stage-C0A1 tests and module-owned specifications. Stage C0A2 affine registration remains the next implementation boundary.

## Post-release Stage 11 architecture revision 15 - 2026-07-24

- Separate `RegistrationFitMetric`, `AnalysisGeometryMetric`, and KDE covariance so framework alignment cannot change with downstream topology choices.
- Add a segment-continuous `TranslationBranchLift` with explicit lattice branches, reset points, continuity residuals, and fail-closed ambiguity.
- Distinguish the log-density `DensityScoreCovector` from the metric-raised `MetricGradientVector`; compare equilibrium force with the former only.
- Split discovery, model selection, final validation, and optional final refit into an explicit `SelectionValidationProtocol`.
- Add exclusive `AssignmentConflictStatus`, overlap diagnostics, and occupancy bounds for moving geometry-conditioned basins.
- Pool independent-run transition paths by a validated `RegistrationCompatibilityClass` rather than identical member registration signatures.
- Distinguish full-torus Hodge structure from support-subdomain integrability, boundary conditions, circulation generators, and additive-constant scope.
- Expand persistent data contracts, stage deliverables, and adversarial tests for these requirements.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 14 - 2026-07-24

- Define a periodic matched-displacement `ReferenceTranslationGauge` instead of averaging arbitrarily wrapped framework coordinates.
- Add an immutable analysis geometry metric, metric-orthonormal differential topology, and certified closest-lattice-vector minimum-image semantics for triclinic cells.
- Add `OperationalScaleDecision`, `ScaleHypothesisSet`, and `ScaleConsensusCatalog` so downstream stages never choose a bandwidth implicitly.
- Restrict scientific basin and saddle topology to a `SupportedPeriodicCellComplex`; unsupported and unresolved cells cannot create connectivity.
- Add explicit core-depth provenance and fallbacks for isolated single-attractor supported components without an interbasin saddle.
- Add intercept-capable local harmonic force fitting, force-defined center uncertainty, chart containment, and manifold-normal fitting.
- Map registered site centers back to framewise physical coordinates before exact M-O forward-model comparisons.
- Add bias-force provenance, periodic-metric HDBSCAN/k-means comparison, and a frozen one-pass geometry-conditioned refinement protocol.
- Expand persistent data contracts, stage deliverables, and synthetic tests for these requirements.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 13 - 2026-07-24

- Add explicit Gaussian kernel metric/covariance policies and affine covariance transformation under equivalent fixed reference domains.
- Define the normalized triclinic periodized Gaussian, bounded image truncation, fractional-grid quadrature, and fail-closed minimum-image approximation.
- Separate exact equal-atom cyclic-index spectra from boundary-measure angular moments and distinguish Nyquist sign from continuous phase.
- Add a Hessian/eigenspace density-ridge criterion and one canonical periodic cell-complex topology with citations to ridge estimation and discrete Morse theory.
- Require independent field-error and topology-stability certificates; unevaluated sparse blocks remain unknown until safely excluded.
- Preserve individual statistical-state instances before optional validated structural symmetry-orbit grouping; prohibit default symmetry augmentation.
- Add static/dynamic membership, comoving displacement, and boundary-induced crossing diagnostics for geometry-conditioned basins.
- Define first-subsequently-resolved-core transition events with bracketed, ambiguous, multiple-target, and gap-interrupted finite-resolution statuses.
- Require one declared thermodynamic temperature and reweighting provenance for every PMF.
- Reorder the plan so core C0 affine registration precedes Stage 11C3 and a separate C0A3 registered-structural-view integration stage.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 12 - 2026-07-24

- Compose reference-material cell mapping explicitly with optional framework translation registration and define source/registered center coordinate semantics.
- Add immutable explicit-matrix and selected-source-frame reference-cell provenance; restrict initial reference-material registration to fully periodic, full-rank 3D cells.
- Separate geometric force-transform status from PMF-force admissibility so variable-cell affine covectors cannot be misused as certified mean forces.
- Add segment-aware represented-time quadrature and prohibit weighting across restart, rejected-frame, ensemble, thermostat, topology-regime, or trajectory boundaries.
- Add explicit topology-regime identities, connectivity-flicker masks, and a one-compatible-regime gate for initial site discovery.
- Add state-local periodic charts for boundary-crossing modes and certified annular charts for local covariance, force fitting, and transfer models.
- Replace the single extended-attractor core formula with local ridge-normal depth; unsupported general-manifold cores remain unresolved.
- Add ring-harmonic center provenance and fail-closed angular-coordinate validity for near-central projected atoms.
- Relabel the implemented supplied-model documentation as legacy/manual Stage 11E-M1 and Stage 11E-M2 without changing modules or public APIs.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 11 - 2026-07-24

- Separate Stage 11C3 species-independent ring-boundary ownership from Stage 11E5a species-dependent cation coordination.
- Add complementary cyclic-index and physical-angle spectra; the former preserves exact chemical sequences and even-ring Nyquist modes, while the latter must be rank safe and condition audited.
- Add explicit atom-weighted and boundary-measure-weighted harmonics, raw and normalized amplitudes, dihedral phase gauges, circular phase statistics, and undefined-phase states.
- Add `RegisteredStructuralGeometryView` so density-space site association and physical bond geometry cannot be mixed silently.
- Treat direct local displacement and exact ordered M-O/M-T distances as authoritative; off-center residual harmonics are diagnostic rather than an exact component decomposition.
- Add multi-ring/cage structural associations, geometry-forward coordination checks, and occupancy-conditioned fingerprint diagnostics.
- Split Stage 11E5 into joint evidence/association and Stage 11E5a coordination/classification, with Stage 11E5b retained for optional geometry-conditioned moving cores and basins.
- Expand persistent data contracts and validation for underdetermined fits, phase support, affine structural views, ambiguous associations, and occupancy-conditioned mixtures.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 10 - 2026-07-24

- Make the persistent ordered T/O boundary, chemical environment, and exact M-O/M-T distance vector authoritative over circle, ellipse, or truncated-harmonic models.
- Add planned Stage 11C3 atom-resolved chemical ring geometry with optional validated LTA O(1)/O(2)/O(3 aliases.
- Cite experimental Na-A and K-A refinements showing centered S6R cations with alternating three-short/three-long oxygen contacts.
- Add actual-angle ring-boundary, cation-coordination, and off-center residual harmonics; separate S6R `m=3` serration, `m=1` off-centering, and `m=2` elliptic distortion.
- Add structural phase gauges, oxygen-/gap-directed locking, corrugated-annular versus discrete-angular classification, and ring-sector transition-path descriptors.
- Replace the single evidence-tier enum with orthogonal spatial, temporal, force, stationarity, geometry, curvature, and overall-certification statuses.
- Add multi-trajectory registration groups, fixed-cell restrictions for pooled physical Cartesian density, ion-time versus occupancy semantics, bootstrap catalog correspondence, validated-frozen versus final-refit catalogs, and geometry-conditioned moving cores/basins.
- Add concurrent-event and occupancy context, explicit path-equivalence rules, and per-dataset kinetic-adequacy sequencing.
- Expand synthetic validation for serrated rings, centered anisotropic coordination, superposed harmonics, annular corrugation, chemical phase locking, and inequivalent transition sectors.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 9 - 2026-07-24

- Add periodic lattice-basis continuity, source-field frame semantics, and explicit wrapped/unwrapped registered-coordinate products to Stage C0.
- Define represented-time density weighting, physical versus reference-material density measures, and local kernel support with complete-system block uncertainty.
- Generalize isolated density modes to `DensityAttractor` objects so annular and other extended manifolds are not collapsed by plateau tie breaking.
- Separate statistical microstates, structural site complexes, and semantic site classes.
- Add discovery/held-out validation blocks and optional geometry-conditioned site-center regression.
- Make successful passages, failed excursions, recrossings, and periodic transition paths persistent scientific objects.
- Distinguish two basin identities, one observed connection, a resolved transition-path ensemble, an identifiable rate, and a supported kinetic model.
- Add Stage 11E6b transition-path ensembles and Stage 11E9 Markov/semi-Markov/gated-model adequacy.
- Strengthen synthetic validation for repeated hopping, single jumps, short excursions, recrossings, true intermediates, and transition shoulders.
- Keep global PMF reconstruction optional and retain Stage 11F as postponed until the kinetic-adequacy gate passes.
- No production source code changes are included in this planning-only revision.

## Post-release Stage 11 architecture revision 8 - 2026-07-23

- Insert cross-cutting Stage C0 spatial frame registration after source normalization and before analysis-specific coordinate preparation.
- Keep `AtomisticFrameCollection` as immutable physical source truth; no universal drift-, rotation-, or strain-corrected trajectory is created.
- Define row-vector affine registration, registered cells, force-covector transformation, exact time-dependent velocity kinematics, analysis requirement profiles, and fail-closed diagnostics.
- Replace arbitrary periodic Procrustes alignment with fixed-domain translation or reference-material policies for initial site discovery.
- Add nested position, force, joint, temporal, and structural evidence masks plus an explicit equilibrium/stationarity gate.
- Require matched position/force kernels, deterministic density-ascent basins, saddle-derived provisional cores, and bandwidth mode lineages.
- Correct the stage order so provisional temporal evidence precedes joint validation and final hysteretic segmentation.
- Make global Hodge/Poisson PMF reconstruction optional, support-limited, and explicit about periodic harmonic components and disconnected domains.
- Adopt evidence tiers so position-and-time-supported sites remain useful when admissible forces are unavailable.
- Refactor density and registration ownership incrementally, with compatibility adapters and numerical regressions before old plotting or dynamics logic is removed.
- Split the real LTA gate into a 300 K Na-LTA pilot followed by Li/K and thermodynamic comparison.
- No production source code changes are included in this planning-only revision.

## 0.19.91a0 - 2026-07-23

- Add `site_assignment.py` with explicit source-bound geometric basin rules for
  Stage-11E1 site hypotheses evaluated in instantaneous Stage-11B/11C2 frames.
- Classify each selected ion and frame as assigned, annular-assigned, ambiguous,
  transition-region, unassigned, or frame-unresolved without a nearest-state
  fallback.
- Retain periodic site-image labels, ring-local coordinates, finite ordered
  candidate diagnostics, and continuous annular angles.
- Convert the complete outcome sequence into generic residence and transition
  statistics through deterministic auxiliary state IDs.
- Report accepted physical transitions separately, including observed lattice
  translations, exact structural multigraph matches, and explicit off-network
  events.
- Add transactional resource limits, deep immutable results, canonical source
  replay, tamper rejection, public exports, and dedicated Stage-11E2 tests.
- Revise the Stage-11 architecture so Stage 11F rate laws and parameter
  provenance is the next planned stage.

## 0.19.90a0 - 2026-07-23

- Add `ring_site.py` with immutable persistent ring-side anchors, explicit
  species-specific geometric site profiles, ring models, microstates, tile
  exposures, resource limits, canonical replay, and tamper rejection.
- Require exhaustive explicit ring-interface coverage; ring order and framework
  labels select user-supplied hypotheses but never certify a physical minimum.
- Implement no-bound, unresolved, one-sided, bilateral, plane-centered,
  discrete off-center, annular, and explicit general-multiwell regimes.
- Preserve two topological side anchors even when a plane-centered state merges
  them into one physical node.
- Add optional cage-interior candidates at exact natural-tile volume centroids
  without claiming energetic stability.
- Add `site_kinetic_network.py` with translation-labelled bilateral crossings,
  cyclic angular paths, ring-to-cage paths, and explicitly enabled intra-tile
  transfers in a periodic directed multigraph.
- Keep all Stage-11E1 edges structural-only: no barriers, rates, trajectory
  assignments, or energetic certification are inferred.
- Add dedicated LTA, generic-profile, annular, bilateral, two-variant cycle,
  periodic-translation, resource, replay, tamper, and export regressions.
- Revise the Stage-11 architecture so Stage 11E2 trajectory assignment and
  observed residence/transition statistics is next.

## 0.19.89a0 - 2026-07-23

- Add `framework_semantics.py` with immutable generic tile, ring-interface,
  profile-rule, validation, and catalog records.
- Derive every tile face signature from the actual natural-tiling face orders
  rather than trusting free-form source labels.
- Define the generic interface identity from ring order plus the unordered pair
  of adjacent tile signatures while retaining oriented sides and periodic tile
  translations.
- Require explicit conventional profiles; generic semantics remain available
  without automatic framework recognition.
- Add the built-in LTA profile for 6 D4R, 2 beta-cage, and 2 alpha-cage tiles and
  the 24 D4R--alpha 4R, 12 D4R--beta 4R, 16 alpha--beta 6R, and 6 alpha--alpha
  8R interface families.
- Apply local signature rules before multiplicity validation so expected counts
  can reject but never force or repair a classification.
- Add transactional resource limits, canonical profile/catalog serialization,
  deterministic source replay, tamper rejection, and `mdstats.analysis` exports.
- Add LTA, generic, non-LTA rejection, custom-profile, resource, replay, export,
  and full natural-tiling dependency regressions.
- Add the permanent framework-semantics specification and revise the Stage-11
  architecture so Stage 11E species-dependent site-state topology is next.

## 0.19.88a0 - 2026-07-23

- Add `map_ring_geometry_to_frames()` and immutable Stage-11C2 frame, ring,
  option, resource, and catalog records.
- Reuse the exact Stage-11B compatible frame set, projected-framework vertex
  gauges, and global image shifts rather than solving a second periodic gauge.
- Replay fixed Stage-11C1 T/O atom identities and require current T--O--T
  connectivity and minimum-image closure on every mapped ring frame.
- Add reference-sign-aligned normals and proper orthogonal-Procrustes in-plane
  alignment over corresponding O atoms, with tilt and signed rotation metrics.
- Retain instantaneous T/O polygons, O-vertex and O-area centers, two side
  frames, area, perimeter, aperture, covariance, ellipticity, planarity,
  puckering, T--O distances, and Cartesian/fractional center translations.
- Add mapped, partial, and unresolved frame aggregates plus explicit
  reference-unresolved, topology-mismatch, missing-bridge, gauge-failure,
  degenerate-geometry, and upstream-unresolved ring records.
- Add read-only frame-aligned ring metric series, transactional work limits,
  canonical source replay, and tamper rejection.
- Add reference equality, wrapping, trajectory translation, rigid rotation,
  isotropic scaling, small-deformation, one-ring degeneracy, topology/gauge,
  resource, serialization, and export regressions.
- Add the permanent compatible-frame ring-geometry specification and revise the
  Stage-11 architecture so Stage 11D framework semantics is next.

## 0.19.87a0 - 2026-07-23

- Add `build_reference_ring_geometry_catalog()` and immutable Stage-11C1
  reference geometry records for every certified natural-tiling window.
- Bind persistent scientific face and primitive-ring identities to continuous
  lifted T polygons and exactly one bridging oxygen per T--T edge.
- Add O-vertex and projected O-area centroids, ordered closest-fit normals, two
  opposite right-handed side frames, covariance, area, perimeter, planarity,
  puckering, ellipticity, center-aperture, and T--O distance descriptors.
- Validate framework-relevant atomic path replay independently of spectator-only
  connectivity, record complete-state equality, and provide an optional strict
  exact-source policy.
- Preserve missing/ambiguous oxygen bridges, path mismatches, and degenerate
  polygons as explicit unresolved records without partial geometry.
- Add LTA 58-window, 4R/6R/8R count, bridge, center, frame, wrapping, translation,
  scaling, resource, replay, tamper, export, and unresolved-state regressions.
- Split architecture Stage 11C into implemented 11C1 reference geometry and
  planned 11C2 compatible-frame dynamics; add the permanent ring-geometry
  specification and synchronize release records.

## 0.19.86a0 - 2026-07-22

- Add `integrate_ionic_conductivity()` and immutable `IonicConductivityResult`
  for fixed-cell, fully periodic, three-dimensional isotropic Green-Kubo
  conductivity with exact SI conversion.
- Retain total and complete ordered group-pair current correlations, cumulative
  trapezoidal integrals, and running conductivities with constructor-level
  quadrature, unit-conversion, group-sum, charge, and volume invariants.
- Add `estimate_ionic_conductivity_plateau()` and immutable
  `IonicConductivityEstimate` for explicit uniformly sampled intervals with
  slope, residual, span, endpoint-drift, and optional stability diagnostics.
- Add `compute_nernst_einstein_comparison()` and immutable
  `NernstEinsteinComparisonResult`, deriving counts and uniform group charges
  from current provenance and requiring compatible full-3D species diffusion
  signatures.
- Report collective-minus-Nernst-Einstein differences, both directional ratios,
  explicit zero-denominator flags, per-group independent-particle
  contributions, and the summed off-diagonal ordered current contribution.
- Add C2 SI conversion, integration, scaling, truncation, fixed-volume, plateau,
  independent-limit, correlation enhancement/suppression, mismatch, constructor,
  export, and deep-immutability regressions.
- Add the permanent ionic-conductivity specification and synchronize the
  VACF/dynamics architecture manual, README, release records, and audit.

## 0.19.85a0 - 2026-07-22

- Add `compute_charge_current()` and immutable `ChargeCurrentResult` with exactly
  one per-atom or exact-symbol charge source, explicit elementary-charge units,
  required neutrality, zero-charge exclusion from the current-carrying set, and
  complete drift/signature provenance.
- Add optional named species groups as a disjoint exhaustive partition of the
  current-carrying atoms, with validated exact group-current summation.
- Retain periodic-axis flags, instantaneous volume history, and fixed versus
  variable full-cell-matrix provenance; constant determinant alone does not imply
  a fixed cell.
- Add `compute_current_correlation()` and immutable `CurrentCorrelationResult`
  with total scalar, Cartesian, optional tensor, and full ordered positive-lag
  group-pair correlations.
- Add direct and zero-padded FFT backends with matching tensor orientation, exact
  origin counts, lag subsampling, and fail-closed group-sum and tensor-trace
  identities.
- Preserve the raw resolved current without implicit time-mean subtraction,
  detrending, smoothing, or group-pair symmetrization.
- Add C0-C1 charge, neutrality, partition, cell-provenance, direct/FFT, ordered
  cross-term, strict-validation, constructor, export, and deep-immutability
  regressions.
- Add the permanent current-correlation specification and synchronize the
  VACF/dynamics architecture manual, shared velocity specification, README,
  release records, and audit.

## 0.19.84a0 - 2026-07-22

- Add `compute_self_intermediate_scattering()` and immutable
  `SelfIntermediateScatteringResult` as the D3 displacement-scattering
  observable built directly on D0.
- Add real isotropic-magnitude mode with dimension-correct one-, two-, and
  three-dimensional `cos`, cylindrical-`J0`, and spherical-`j0` kernels.
- Add complex explicit-vector mode with exact q ordering, duplicate retention,
  projected q coordinates, and fail-closed rejection of out-of-subspace vector
  components.
- Preserve exact unit values at zero lag and zero q, exact analytic sample-count
  auditing, complete dynamics signatures, and deep result immutability.
- Bound transient phase/kernel arrays through private q chunking without
  changing the explicit `(lag, q)` result allocation or estimator.
- Add ballistic, conjugation, Gaussian, rotated-subspace, direct-kernel,
  van-Hove-transform, block-invariance, constructor, export, and invalid-input
  regressions.
- Expand the permanent displacement-dynamics specification and synchronize the
  VACF/dynamics architecture manual, README, release records, and audit.

## 0.19.83a0 - 2026-07-22

- Add `compute_non_gaussian_parameter()` and immutable `NonGaussianResult` as
  the D2 displacement-cumulant observable built directly on D0.
- Accumulate unbinned projected second and fourth moments in one atom/origin
  blocked pass and apply the rank-correct $d/(d+2)$ prefactor.
- Mark every exact-zero second-moment lag with `alpha2=NaN` and an explicit
  immutable `undefined_mask`, including later lags rather than only lag zero.
- Add direct D1/MSD moment cross-checks, rotated-subspace validation, strict
  moment-overflow rejection, exact sample-count auditing, and deep result
  immutability.
- Add static, fixed-radius, Gaussian, heterogeneous-mixture, later-zero-lag,
  block-invariance, constructor, export, and invalid-input regressions.
- Expand the permanent displacement-dynamics specification and synchronize the
  VACF/dynamics architecture manual, README, release records, and audit.

## 0.19.82a0 - 2026-07-22

- Add `compute_self_van_hove()` and immutable `SelfVanHoveResult` as the D1
  displacement-distribution observable built directly on the D0 prepared bundle
  and atom/origin block iterator.
- Add one-, two-, and three-dimensional projected radial shell measures, exact
  total-sample normalization, final-edge-inclusive bins, and explicit overflow
  counts/probabilities for finite user support.
- Add deterministic automatic complete support through a maximum-radius prepass,
  including a finite numerical support rule for exactly static trajectories.
- Accumulate an unbinned direct projected second moment over all samples,
  including overflow, and validate it against the D0 direct MSD estimator.
- Add strict lag/support/boolean/block validation, complete dynamics-signature
  propagation, deeply immutable arrays and nested metadata, and public exports.
- Add D1 analytic, Gaussian, projection, endpoint, overflow, block-invariance,
  provenance, immutability, and invalid-input regressions.
- Add the permanent displacement-dynamics specification and synchronize the
  VACF/dynamics architecture manual, README, release records, and audit.

## 0.19.81a0 - 2026-07-22

- Add the D0 `DisplacementInputBundle` so measured selection, laboratory or
  reference-cell coordinates, drift subtraction, analysis subspace, and
  `DynamicsInputSignature` are resolved exactly once.
- Add deterministic lag-major, origin-block-major, atom-block-major
  `DisplacementBlock` iteration with immutable arrays and exact sample coverage.
- Add a conservative `DisplacementBlockPlan` that bounds both atom and origin
  dimensions under a hard memory target; the direct MSD path uses a 256 MiB
  default and records the resolved plan in metadata.
- Refactor the direct time-origin-averaged MSD estimator onto D0 while retaining
  the FFT estimator as an independent numerical implementation.
- Add D0 regressions for explicit atom order, projected values, variable-cell
  and drift preparation, block ordering and coverage, strict validation,
  memory-target enforcement, deep immutability, and pre-refactor MSD parity.
- Add the permanent shared-displacement specification and synchronize the MSD
  specification, VACF/dynamics architecture manual, README, and release audit.

## 0.19.80a0 - 2026-07-22

- Add the shared `AnalysisSubspace` contract so projected VACF/MSD transport
  selects a physical orthonormal subspace before applying its rank divisor.
- Reject ambiguous scalar `dimensions=1` or `2` transport calls unless an
  explicit axis subset or projection basis is supplied; preserve full-3D and
  single-Cartesian numerical behavior.
- Add complete `DynamicsInputSignature` provenance with deterministic normalized
  trajectory fingerprints (including masses and cell origins), exact frame/time
  identity, measured and drift-reference atoms, coordinate/reference-cell
  semantics, velocity source, and projection.
- Make public VACF, MSD, transport, diffusion, velocity-spectrum, and VDOS
  results deeply immutable, including nested metadata; freeze shared velocity
  selection and signature arrays without copying the complete trajectory.
- Harden integer/boolean validation and require a uniform selected time grid for
  the existing arithmetic-mean Green-Kubo plateau estimator.
- Add H0 adversarial regressions and synchronize the common, transport,
  reconstruction, diffusion, VACF, MSD, velocity-spectrum, VDOS, and architecture
  specifications.
- Export the H0 shared contracts through both public API layers and list them in
  the corresponding `__all__` declarations.

## 0.19.79a0 - 2026-07-22

- Make the LTA plotting examples use an explicit framework-only hysteretic
  Si/Al--O connectivity definition for topology classification.
- Calibrate formation and breaking cutoffs from the complete four-nearest-O
  tetrahedral shell rather than only the single nearest oxygen.
- Keep mobile-ion--O contacts out of topology-state classification while still
  adding them to the atomic mean-connectivity graph.
- Add auditable progress output and CLI overrides for framework formation and
  breaking cutoffs.
- Add regressions showing that a transiently stretched framework bond remains
  connected when it lies above the formation cutoff but below the breaking
  cutoff.

## 0.19.78a0 - 2026-07-22

- Repair sparse tiled-mesh validation so tile-local pre-simplification cannot poison the global periodic surface.
- Retry invalid tiled extraction with local pre-simplification disabled, then use bounded coarse recontouring or node-cloud fallback instead of raising the raw incidence error.
- Restore the validated pre-simplification mesh when a global simplification candidate fails seam or incidence checks.
- Replace partitioned topology rendering through the general style-bucket renderer with a compact adapter capped at four traces per topology category.
- Keep the balanced 96-trace browser profile and make seven-category framework scenes fit by construction rather than by raising the limit.
- Add focused regressions for invalid local mesh repair, coarse-recontour fallback, and compact grouped topology rendering.

## 0.19.77a0 - 2026-07-22

- Consolidate chronological mesh/topology revision documents into stable module-owned specifications.
- Add normative specs for mesh contracts, render budgets, scene allocation, scene fitting, simplification, execution, and browser acceptance.
- Integrate partitioned topology preparation and grouped legend behavior into `framework_dynamics_spec`.
- Integrate downstream category-consumer rules into `topology_catalog_spec`.
- Absorb the Stage-2 interpreter-hotpath implementation into the permanent hotpath policy.
- Remove superseded Stage-1/2/2--9 and LD9-V0/V2/V3/V4 documents from the package docs.

## 0.19.76a0 - 2026-07-22

- Separated raw contour-extraction limits, shell visual targets, and final
  post-replication browser budgets.
- Added `BrowserMeshProfile` presets (`compact`, `balanced`, `quality`, custom)
  and made `balanced` the interactive default.
- Added a closed-loop density-scene fitter with weighted reallocation, periodic
  QEM retries, target-overshoot compensation, lower-resolution recontouring,
  exact seam/incidence validation, and structured fit reports.
- Scene-owned shell targets no longer raise the standalone 250,000-face error.
- `prepare_framework_dynamics_scene` now accepts `TopologyCatalog` and prepares
  one averaged framework and atomic mean graph per topology category while
  retaining global trajectories and density fields.
- Added grouped one-click Plotly category controls; the dominant category is
  visible and other categories begin as legend-only layers.
- Updated the LTA example to infer hysteretic connectivity, cache the complete
  topology catalog, accept topology or catalog overrides, and expose browser
  mesh profiles.

## 0.19.75a0 - Mesh/topology revision Stage 2 face contracts

- Added immutable `DensityMeshFaceContract` and `DensityMeshFaceReport` records that distinguish raw extraction safety, soft visual targets, and optional standalone terminal limits.
- Made runtime-derived `max_density_mesh_faces` authoritative for raw marching-cubes work while allowing a scene shell to exceed its initial visual target without a premature per-shell exception.
- Added scene-controller contracts to dense and local-sparse framework-dynamics rendering and retained the contract/report in render metadata for the Stage-3 fitting controller.
- Renamed the normative render option to `standalone_final_mesh_faces`; retained `max_mesh_faces` as a serialized and constructor compatibility alias.
- Preserved the standalone 250,000-face hard default and the existing final browser-wide hard budget until closed-loop fitting is implemented.
- Added focused migration, sparse/dense target-miss, exact 582,375-face debt, runtime-limit, and real scene-render tests.
- Added the permanent Stage-2 specification and updated the sparse-mesh, density-contract, framework-dynamics, index, and architecture documentation.

## 0.19.74a0 - Mesh/topology revision Stage 1 regression locks

- Added deterministic fixtures for the reported 301,838- and 314,640-face browser-budget failures, the 582,375-face sparse-shell failure, and a seven-class partitioned framework topology.
- Routed historical sparse-mesh terminal face checks through one private count boundary so the large-shell regression can run without retaining a large triangle fixture.
- Exposed the LTA example's uniform-only topology guard for deterministic regression testing while preserving current behavior.
- Added the permanent Stage-1 specification and architecture status record; closed-loop fitting and category-aware rendering remain deferred to later stages.

## 0.19.73a0 - Exact shortest-translation minimum-image radius

- Replaced the historical perpendicular-cell-height cutoff with one half of the exact shortest nonzero periodic lattice translation.
- Use ASE Minkowski reduction to obtain the shortest periodic vector and validate the integer unimodular transform, periodic-sublattice preservation, transform consistency, and reduced-basis certificate.
- Apply the exact bound consistently to RDF, coordination, connectivity, dense/cell-list neighbors, and Verlet list-radius admission.
- Added skewed-cell and LTA primitive-cell regression tests showing that `r_max=8 A` is valid for a roughly 17.36 A LTA primitive lattice.
- Updated the shared-neighbor and RDF specifications and the periodic-neighbor architecture manual.

## 0.19.72a0 - Interpreter-hotpath Stage 2 array kernels

- Added the consolidated interpreter hot-path patching manual covering completed fixes, patch standards, and the deferred optimization roadmap.

- Replaced cell-list center-by-stencil candidate gathering with bounded array joins, packed pair deduplication, and chunked compiled minimum-image evaluation.
- Batched metric-aware stencil box minimization over candidate offsets while retaining the exact 27 active-set cases.
- Replaced per-center bond-angle generation and histogram accumulation with bounded ragged pair templates and compiled reductions.
- Replaced support-atlas target dictionaries, Python bitset unions, graph BFS, and source-target edge insertion with fixed-width uint64 reductions, sparse connected-components, and sorted CSR construction.
- Replaced ordinary tiled-mesh vertex/face dictionaries with an array-backed occurrence stream and one global sort/unique reconciliation pass; Python clipping is retained only for boundary-crossing triangles.
- Reworked fragmented target-owned direct realization to build vectorized ragged source/stencil schedules per target block and evaluate them in bounded pair chunks.
- Added calibration-independent hybrid-executor tests, Stage-2 equivalence tests, static-loop auditing, focused microbenchmarks, and an explicit compiled-extension boundary for irregular ring/tiling searches.

## 0.19.71a0 - Python interpreter overhead audit and vectorized kernels

- Vectorized packed-bitset packing, unpacking, and row-popcount operations.
- Removed repeated Python row loops from sparse-density planning and realization counts.
- Added package-wide interpreter-overhead audit and performance regression benchmarks.

## 0.19.70a0 - Packed sparse-mesh read-path optimization

- Replaced per-query packed occupancy-bitset decoding with block-grouped vectorized gathering.
- Reduced one fully occupied `33^3` tile gather from 25.7809 s to 0.02135 s on the validation runtime while preserving exact values.
- Added regression coverage requiring one bitset decode per distinct touched active block.
- Added contour tile, candidate-cell, raw-face, and final-face diagnostics to sparse-shell progress messages.
- Corrected the sparse-mesh final workspace check to compare against the resolved runtime workspace limit when no explicit override is supplied.
- Added the LD13 specification and architecture-manual revision.

## 0.19.69a0 - Package-wide structured progress port

- Added `mdstats.progress` with immutable structured events, a minimal port protocol,
  module-side emitters, and text, logging, callback, null, and legacy adapters.
- Added the keyword-only `progress=` port to framework-dynamics preparation/rendering
  and atomic/framework density realization.
- Retained `progress_callback=` as a deprecated string-callback compatibility path.
- Migrated the LTA examples from a private stdout reporter to `TextProgressPort`.
- Added event-schema, adapter, interface, and source-example regression tests.
- Added `docs/specs/progress_spec.{md,pdf}` and updated the density architecture manual.

## 0.19.68a0 - Direct example source-tree bootstrap

- Make the mixed-alkali LTA density example runnable directly from the
  repository `examples/` directory without requiring an editable installation.
- Prefer the adjacent source checkout when the script is inside the repository;
  copied standalone scripts continue to use the installed `mdstats` package.
- Apply the same bootstrap to the retained Na-LTA compatibility filename and
  report the selected import mode in progress output.
- Add focused regression tests for source-tree and copied-script launch modes.

# Changelog

## 0.20.99a0

- Implement OPT-EVAL3 stable monitor graph caching: model-independent graph identities, 1 GiB byte-bounded CPU memory reuse, SHA-256-authenticated persistent graph shards, corruption rebuild, and single-flight concurrent misses.
- Pre-index immutable target/replay evaluation views so repeated checkpoints reuse reference arrays, force offsets, focus-species indices, condition IDs, and stress masks instead of walking ASE metadata repeatedly.
- Remove the graph-build device round-trip used only for caching and avoid a redundant device-batch clone for single-model MACE inference, while preserving ensemble isolation, OOM backoff, prediction/cache schemas, and scientific metrics.
- Include the previously requested multi-format trajectory input update for `examples/plot_lta_mixed_alkali_density.py`.



## 0.20.83a0

- Prevent one completed run with no admissible shortlisted checkpoint from aborting evaluation of every other completed model.
- Persist bounded, per-epoch checkpoint rejection evidence with exact mandatory-constraint reason counts and metrics.
- Exclude inadmissible runs from interim export/verification, recompute fold evidence from admissible runs only, and withhold production freeze when required runs fail constraints.
- Improve direct `select_checkpoint` errors with aggregated rejection reasons while preserving fail-closed mandatory gates.

## 0.20.16a0 - Stage 11 architecture revision 46 planning correction - 2026-07-27

- Separate event-supported networks and empirical rates from optional path/saddle products.
- Split E9 into pre-rate and post-fit adequacy and move G0 gating selection before F0.
- Branch basin THERMO4A from THERMO0--2 without requiring transition-region THERMO3A.
- Add explicit optional PMF, E8a milestone, and M1/M2 branches to a machine-readable DAG.
- Replace obsolete crossfit vocabulary and remove release chronology from the normative manual.
- No runtime scientific algorithm or result changed.


## 0.19.67a0 - Hybrid-aware density scene admission

- Replaced the local-sparse Phase-B nominal all-direct pair plan with the exact LD8 packed-source, block-routing, support-atlas, and hybrid direct/FFT execution plan when the production hybrid backend is selected.
- Phase C now limits and sums actual direct-pair work, accounts separately for calibrated FFT-tile wall time, and records nominal exact contributions only as diagnostics.
- Prevented automatic backend selection from rejecting a feasible hybrid scene merely because the all-direct contribution upper bound exceeds `max_density_kernel_pairs`.
- Added focused regression tests and updated the density planning specification and architecture manual.

## 0.19.66a0 - LTA plotting progress reporting

- Added optional progress callbacks to framework-dynamics scene preparation and 3-D rendering.
- Added coarse frame-registration progress, per-density-field `X/Y` completion, and per-isosurface `X/Y` mesh progress.
- Updated the mixed-alkali LTA example to print elapsed-time stage messages by default and added `--quiet`.
- Progress now covers trajectory parsing, species detection, topology inference/cataloging, runtime-resource resolution, scene preparation, mesh extraction, Plotly assembly, and HTML serialization.

## 0.19.65a0 - LD11 automatic density backend defaults

- Changed the shared production defaults to `smoothing_operator="discrete_periodized_v1"` and `grid_backend="auto"` for atomic, framework-vertex, and framework-edge density fields.
- Made ordinary density preparation resolve the requested scientific grid and Gaussian bandwidth before estimating dense and local-sparse realizations.
- Prevented the dense logical-voxel allowance from silently broadening an automatic field when the same physical resolution is feasible with local-sparse storage.
- Retained explicit dense, explicit local-sparse, and historical `legacy_spectral_v1` dense modes for reproducibility; legacy-spectral auto/sparse combinations remain rejected.
- Added focused default-policy and adaptive-resolution regression tests, including a logical grid larger than the dense allowance that is realized automatically with sparse storage.
- Updated the all-species Na-LTA example to rely on the production defaults without backend/operator arguments.

## 0.19.64a0 - LD10 runtime-derived density resource policy

- Replaced benchmark-fitted density compute caps with one runtime-derived scene budget based on process CPU affinity, cgroup/job constraints, current memory headroom, finite address-space limits, and explicit user policy.
- Defaulted package-owned compute to 80% of detected available memory, 80% of detected CPUs, and a 1,200-second complete-scene wall-time objective.
- Added public API, environment, and example-CLI overrides for maximum memory, threads, and wall time, with memory/thread requests clamped to the actual runtime allocation.
- Added a context-local immutable budget inherited by all density planners, kernels, caches, and child workers, preventing repeated 80% reductions and inconsistent mid-scene host probes.
- Converted legacy per-kernel count, byte, pair, block, cache, workspace, and worker limits to runtime-derived defaults; explicit legacy values are tightening-only.
- Added input-independent synthetic throughput calibration and conservative complete-scene preparation/rendering time admission.
- Added aggregate preparation and rendering peak-memory checks, including retained parent fields, output reserve, serial workspace, and isolated worker-pool workspace.
- Limited isolated shell workers jointly by scene CPU, memory, shell count, and remaining wall time, and propagated per-worker memory/thread/time bounds to child processes and native numerical libraries.
- Kept browser face, vertex, trace, and HTML profiles separate from host-compute admission.
- Added 24 focused runtime-policy and static cap-regression tests; the full suite was not run in the release container because ASE was unavailable.

## 0.19.63a0 - all-species trajectory endpoint legend integration

- Made trajectory start-circle and end-diamond markers visible as separately labeled legend entries whenever trajectory legends are enabled; both remain on by default.
- Assigned independent endpoint legend groups so start and end markers can be toggled separately under Plotly group toggling.
- Updated the 300 K Na-LTA all-species density example to accept command-line paths, use every frame by default, and render trajectories for Si, Al, O, and Na together with the mean framework, atomic mean net, and three HDR density shells per species.
- Added focused renderer assertions for endpoint names, symbols, legend visibility, and independent legend grouping.

## 0.19.62a0 - LD9-V4 bounded shell execution and browser acceptance

- Added bounded parallel fresh-process preparation for independent density shells with deterministic final scene assembly.
- Added explicit native-thread containment for OpenMP, OpenBLAS, MKL, NumExpr, and Accelerate workers to prevent nested oversubscription.
- Added immutable JSON contracts for shell-execution options and reports, including wall time, summed shell time, maximum shell time, and parallel efficiency.
- Added browser acceptance policies and reports that separate functional browser success from physical-WebGL production-default authorization.
- Extended the Chromium validation benchmark with first-frame, orbit, toggle, heap, context-loss, renderer classification, and structured acceptance evidence.
- Recorded a bounded real-mesh three-shell scheduler speedup from 9.997 s serial to 3.701 s with three workers (2.701x, 96.9% parallel efficiency) and identical geometry counts.
- Revalidated the complete self-contained V3 browser scene functionally at 13.392 s first frame, 27.698 FPS orbit, 0.119 s trace toggle, approximately 199 MiB JavaScript heap, and no context loss.
- Retained physical-WebGL production-default authorization as pending because the managed validation environment did not expose renderer identity.
- Preserved all scientific fields, HDR thresholds, topology/fidelity checks, and V3 hard face, vertex, trace, and HTML limits.

## 0.19.61a0 - LD9-V3 hard-budget browser density scenes

- Added deterministic post-replication scene-wide allocation across all requested density shells, with shell importance, minimum reserves, and a 15% topology/fidelity reserve.
- Added periodic-quotient reconstruction for nonwinding seam components, continuous-chart lifting, QEM simplification, recanonicalization, and final seam-pair validation.
- Added fresh-interpreter extract--simplify--release execution for large sparse shells.
- Added compact Plotly mesh arrays, disabled redundant mesh hover payload, and grouped trajectory paths into one line trace per species.
- Added hard pre-serialization enforcement for 300,000 density faces, 200,000 density vertices, 64 Plotly traces, and 40 MiB self-contained HTML.
- Recorded the complete 1,500-frame twelve-shell gate: 286,008 faces, 147,477 vertices, 28 traces, and 26,233,233 HTML bytes; all hard budgets and field-fidelity checks pass.
- Preserved density values, adaptive resolution, the `1e-8` Gaussian-tail cutoff, normalization, HDR thresholds, and trajectory samples.

## 0.19.60a0 - LD9-V2 periodic fidelity-constrained mesh simplification

- Added conservative streaming tile-local presimplification for closed components wholly inside one render tile; tile-boundary and periodic-seam geometry remains exact.
- Added global connected-component target allocation and quadric-error simplification adapted from Garland and Heckbert (SIGGRAPH 1997).
- Added exact protection for seam-touching, small, open, nonmanifold, and topology-sensitive components.
- Added bounded Newton projection toward the immutable scientific contour level, with automatic fallback when projection degenerates triangles.
- Added periodic trilinear scientific-field sampling, corrected sampled surface distance, implicit displacement, gradient-normal degradation, relative scalar residual, topology, and seam-fidelity gates.
- Added hard-target structured failure and calibration-mode achieved-count reporting without relaxing scientific fidelity.
- Added canonical JSON round trips for V2 options, reports, and geometry-bearing results, plus deterministic migration of V1 tiled records to V2 schemas.
- Recorded full-resolution 50% HDR evidence: 565,482 raw V1 faces reduced to 226,636 accepted V2 faces in 50.440 s of species-isolated execution, with maximum peak RSS 0.905 GiB and all fidelity gates passing.
- Retained the 300,000-face scene-wide browser limit for LD9-V3; V2 does not claim final browser readiness because 80% and 95% shells and display replication are not yet budgeted together.

## 0.19.59a0 - LD9-V1 bounded tiled contour extraction

- Replaced the normal nonwinding sparse per-cell marching-cubes path with deterministic bounded render tiles and one Lewiner marching-cubes call per nonempty tile.
- Added exact high-node candidate pruning, periodic logical-cell tile ownership, positive-face scalar halos, partial terminal tiles, and transactional raw/transient resource preflight.
- Added deterministic logical-grid-edge vertex keys, direct endpoint interpolation, canonical seam-plane copies, clipping fast paths, and tile-shape-invariant indexed output on validated fixtures.
- Added a deterministic 16-ULP `float32` display-level guard for point-like CIC contours while retaining the immutable scientific HDR threshold separately.
- Added immutable JSON contracts for extraction options, render tiles, tile plans, per-tile reports, and geometry-bearing extraction results.
- Retained the legacy cell-wise extractor as an explicit migration oracle and preserved winding-shell fallbacks, strict periodic topology validation, scientific HDR thresholds, and hard final face failure.
- Recorded four-species 50% HDR stress evidence: 283,531 crossing cells were processed with 694 marching-cubes calls, a 408.5x call-count reduction; unsimplified geometry remains subject to LD9-V2 simplification before browser acceptance.
- Advanced the next rendering stage to LD9-V2 periodic fidelity-constrained mesh simplification.

## 0.19.58a0 - LD8-S4 production dispatch and downstream numerical reuse

- Migrated normal local-sparse atomic, framework-vertex, and framework-edge density preparation to the LD8-S3 hybrid tiled direct/FFT executor with packed scientific-field output.
- Restricted LD7 fallback to explicit complexity or allocation failures; identity, support, normalization, and scientific invariant errors are never hidden.
- Added exact binary-FFT support dilation with an integer-convolution certificate for production-size stencils while retaining Python-integer bitset dilation as the small-case oracle.
- Added shared exact multi-HDR selection with one bounded value ordering, chunked mass accumulation, and no retained full cumulative-mass array.
- Added lazy contour-support planning from packed block extrema and optional periodic connected components.
- Extended packed fields with downstream sample provenance, multi-HDR, contour-support, and bounded dense-conversion helpers.
- Completed the all-frame, all-species, `1e-8` normal-dispatch gate in 80.515 s of aggregate scientific preparation, 4.219x faster than the recorded 339.686 s LD7 baseline.
- Recorded exact Na/Si/Al/O measure recovery, no fallback, three HDR levels per field, and per-channel peak RSS between 0.969 and 1.218 GiB.
- Advanced the next numerical work to maintenance/calibration only; LD9-V1 tiled browser-mesh extraction is the next planned implementation stage.

## 0.19.57a0 - LD8-S3 hybrid tiled direct/overlap-add FFT realization

- Added immutable JSON-serializable hybrid-executor options, hard limits, per-tile plans, and identity-bound whole-field plans.
- Added deterministic logical-grid compute tiling independent of the 16^3 storage-block layout.
- Added bounded sparse-direct tile scatter and zero-padded three-dimensional FFT linear convolution with periodic overlap-add into the exact S1 packed support.
- Added calibrated direct/FFT crossover selection, explicit executor forcing, byte-bounded exact-stencil spectrum caching, and complete executor provenance.
- Added exact direct repair for rare nonpositive finite-support-boundary FFT nodes, one global normalization, and packed-field output without a global dense logical grid.
- Removed repeated per-source-block `numpy.unique` work from S1 planning by caching axis-level target-count calculations.
- Added fragmented, compact, periodic-boundary, oxygen-heavy, partial-terminal, determinism, cache, identity, and resource-preflight tests against the S2 oracle.
- Recorded focused relative L1 disagreement below 5.4e-16 and 2.81-40.44x speedups over S2; full Na/Si/Al value realization completed in about 2.0-2.15 s per field, 20.08-26.91x faster than the recorded LD7 field baselines.
- Retained LD7 as production dispatch. LD8-S4 must complete the four-species production gate, selector calibration, downstream query reuse, and integration before default migration.

## 0.19.56a0 - LD8-S2 canonical target-owned direct realization

- Added immutable JSON-serializable direct-realization limits and identity-bound execution plans for exact LD8-S2 migration work.
- Added deterministic target-owned block convolution over one global packed CIC source, the exact finite Gaussian stencil, source-independent routing, and the field-specific support atlas.
- Added conservative translated-source interval pruning, bounded vectorized pair chunks, and source sub-chunking when a declared pair limit is smaller than one occupied source block.
- Added immediate preallocated packed target output, one global normalization, deterministic residual correction at the largest positive node, and per-block extrema.
- Added exact support-bitset verification for every completed target block and metadata proving that no complete fine-pair or global target-coordinate array was allocated.
- Added periodic, partial-terminal, randomized, determinism, identity, resource-preflight, small-chunk, and packed-storage tests against LD1-A.
- Recorded bounded production-stencil evidence: relative L1 disagreement of about 1e-18 to 2e-16, with packed retained storage about half the LD1-A flat-node representation.
- Retained LD7 as the production full-field executor because the canonical NumPy S2 oracle is 1.5-3.2x slower than LD1-A on the bounded benchmark; LD8-S3 remains responsible for the hybrid production accelerator.

## 0.19.55a0 - LD8-S0/S1 exact support contracts and planning

- Added immutable source-independent periodic kernel block routing with exact finite-stencil identities, canonical signed offsets, terminal extent classes, packed validity masks, and a byte-bounded clearable cache.
- Added one globally aggregated packed periodic CIC source per field, with canonical block/local order, exact measure conservation, source provenance, JSON round trips, and content identities.
- Added transactional support-atlas planning with target/edge upper bounds, complete fine-pair reference counts, exact bitset-shift counts, lifted-brick workspace bounds, and preallocation failure.
- Added exact source-block padded-bitset support dilation at the retained `1e-8` Gaussian-tail cutoff without complete fine-pair arrays or source-specific global cache reuse.
- Added field-specific periodic target support bitsets, source-to-target CSR metadata, optional periodic block components, explicit modular-Minkowski-sum verification, and canonical serialization.
- Added the packed positive scientific-field contract and fixed-block compatibility adapter while retaining LD7 as the production density-value executor until LD8-S2.
- Recorded full 1,500-frame Na/Si/Al/O support evidence: every target-node count matches the completed LD7 production-cutoff baseline, with only 0.685-2.915 MiB retained per atlas.
- Added focused routing, terminal-block, cache, planner, support-equivalence, packed-source, and packed-field tests. The next numerical stage is LD8-S2; LD9-V1 remains the next rendering stage.

## 0.19.54a0 - LD8-P0 and LD9-V0 evidence contracts

- Added the full-frame production-cutoff benchmark for the canonical `1e-8` Gaussian-tail policy, effective CIC-plus-stencil broadening, block-occupancy/storage profiling, and bounded direct-versus-FFT executor spikes.
- Added hard post-replication browser budgets for density faces, vertices, Plotly traces, and self-contained HTML bytes, with structured pre-serialization failure.
- Added deterministic mesh topology and sampled geometric-fidelity metrics, including symmetric surface distance, normal error, and optional scientific-field residual.
- Added Chromium/WebGL smoke-validation and stress-scene calibration tooling while recording environment or policy failures as evidence rather than silently passing.
- Corrected LD7 group-batch final normalization so floating residuals are applied to the largest positive node rather than an arbitrarily tiny first sparse node.
- Preserved the production density backend and renderer; LD8-S0/S1 and LD9-V1 remain the next implementation stages after evidence review.

## 0.19.53a0 - LD7 full-trajectory sparse-density tractability

- Added deterministic stratified-random temporal subsampling for periodic positional-spread estimation while retaining every selected frame in the final density estimator.
- Added explicit spread-sampling size, seed, strategy, sampled-frame indices, source-frame count, and sampling-fraction provenance.
- Replaced global sparse pair-array materialization with exact two-pass block discovery and bounded block-local streaming accumulation.
- Added deterministic source-group batching, exact sparse-field merging, and group-batched Phase-B target planning for atomic, framework-vertex, and framework-edge fields.
- Added bounded large-field block reduction while retaining the original stable addition path for small/reference-scale fields.
- Demonstrated all-frame 1,300-frame Na-LTA Na/Si/Al/O density preparation in about 125 seconds total under a 4 GiB workspace limit, including roughly 978 million cumulative kernel pairs.
- Preserved dense numerics, the LD1-A reference path, fixed scientific resolution, exact integrated measure, and production mesh/cloud contracts.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v14`.

## 0.19.52a0 - LD6 multilevel density research gate

- Added immutable, schema-versioned multilevel research options, phase profiles, candidate profiles, alternative single-level block profiles, field evidence profiles, and architecture decisions.
- Added bounded positive-node collection, exact alternative block-packing plans, HDR-driven dyadic coarse/fine surrogates, conservative mass-preserving coarse averages, and exhaustive periodic coarse-grid phase sweeps.
- Added explicit field/HDR tolerances, optimistic storage accounting, localized/broad coverage requirements, and deterministic `retain_single_level`, `write_multilevel_specification`, and `insufficient_evidence` outcomes.
- Added representative atomic, framework-vertex, framework-edge, path, multimodal, overlapping, and broad-field benchmarks.
- Recorded the evidence-based `retain_single_level` decision: the completed dense plus single-level block-sparse architecture remains the normative production design, and no multilevel AMR backend is authorized.
- Preserved all production density numerics, LD4 backend selections, LD5 optimization behavior, renderers, and framework-dynamics scene schema unchanged.

## 0.19.51a0 - LD5 sparse density optimization and caching

- Added `DensityOptimizationOptions` with explicit `optimized` and retained LD1-A `reference` sparse evaluation modes, cache control, and pair-chunk sizing.
- Added preallocated vectorized periodic CIC aggregation, chunked canonical pair generation, bounded dense `bincount` reduction for small logical grids, stable sparse reduction for large grids, and exact optimized target-node planning.
- Added a thread-safe least-recently-used cache of immutable canonical stencil supports, bounded to 16 entries and 256 MiB, with exact scientific keys, caller-limit revalidation, clear and inspection APIs, and planning-to-realization reuse.
- Preserved exact active-node and block identities, LD1-A numerical tolerances, LD4 backend-selection semantics, explicit dense behavior, and selectable reference execution.
- Added focused optimization, determinism, cache, resource, planning-reuse, compatibility, and benchmark tests plus localized/broad and cold/warm performance evidence.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v13`.

## 0.19.50a0 - LD4 automatic density backend selection

- Enabled transactional `grid_backend="auto"` for atomic, framework-vertex, and framework-edge density fields with `discrete_periodized_v1`.
- Added exact dense and local-sparse Phase-B candidate estimates before scalar-field allocation, including active support, stored values, blocks, kernel pairs, retained bytes, peak bytes, and estimated work.
- Added deterministic field-local policy anchors for broad and localized fields plus scene-wide combination selection under the existing Phase-C resource limits.
- Preserved requested grid shape, interval, Gaussian bandwidth, broadening metric, kernel tail tolerance, and edge-quadrature policy; auto selection never lowers scientific resolution to fit memory.
- Added schema-versioned candidate and selection records, canonical JSON round trips, serialized selection reasons, and global-override provenance in plans and realized fields.
- Kept explicit `dense` and `local_sparse` forcing unchanged and continued to reject `auto` with `legacy_spectral_v1`.
- Added focused selector, framework-scene, global-resource, determinism, resolution-preservation, compatibility, and failure tests.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v12`.

## 0.19.49a0 - LD3 sparse framework density channels

- Enabled production `grid_backend="local_sparse"` preparation for framework-vertex occupancy and projected or atom-resolved framework-edge arc-length density using `discrete_periodized_v1`.
- Added deterministic, resolution-aware midpoint edge quadrature with `auto` and `explicit` modes, configurable refinement depth, exact segment-weight correction, and orientation-invariant endpoint canonicalization.
- Added structured framework vertex/edge provenance, separate occupancy and arc-length units, exact sparse Phase-B block plans, and realization accounting.
- Reused the LD2 logical-node cloud and periodic mesh renderers for both framework channels without dense materialization or renderer special cases.
- Added focused dense/sparse equivalence, orientation, periodic seam, quadrature convergence, provenance, rendering, planning, and compatibility tests.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v11`.
- Preserved dense atomic and framework-vertex behavior; the new default automatic edge-quadrature policy is an explicit versioned migration, while the former fixed interval remains reproducible with `edge_sample_spacing_mode="explicit"`.

## 0.19.48a0 - LD2-B periodic sparse density meshes

- Added deterministic positive-level candidate-cell discovery, periodic face-connected components, lifted charts, and torus-winding detection for block-sparse density shells.
- Added cell-aware per-owned-cell Lewiner marching cubes with shared-edge interpolation reconstructed from common endpoint values.
- Added whole-triangle canonical image replication and Sutherland-Hodgman clipping, deterministic vertex/face canonicalization, duplicate removal, periodic seam pairing, and logical-cell edge-length validation.
- Added dense canonical and logical-node-cloud fallbacks for winding components, schema-versioned mesh/resource/topology records, and canonical JSON geometry round trips.
- Enabled atomic local-sparse `render_mode="mesh"` and deterministic expanded-cell `match_graph` mesh replication with trace-level provenance.
- Kept framework sparse fields reserved for LD3 and preserved the dense default scientific path and historical dense mesh output.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v10`.

## 0.19.47a0 - LD2-A sparse HDR and logical-node cloud rendering

- Added backend-neutral, schema-versioned density node-cloud preparation through public scalar-field and periodic-node-access contracts.
- Added deterministic two-pass HDR node selection, exact logical-node Cartesian coordinates, bounds, resource accounting, and trace provenance without sparse dense materialization.
- Enabled atomic `local_sparse` voxel-cloud rendering and deterministic expanded-cell `match_graph` replication.
- Retained sparse mesh rejection until LD2-B and framework sparse preparation until LD3.
- Preserved the dense default estimator, dense meshes, and canonical dense voxel-cloud output.

## 0.19.46a0 - LD1-B production atomic block-sparse density

- Added immutable, schema-versioned `PeriodicBlockScalarField3D` storage with deterministic lexicographic block ordering, partial-terminal-block masks, public periodic node access, guarded dense debugging conversion, and canonical JSON round trips.
- Added exact block-packing and sparse-target planning before block-value allocation, with explicit limits for blocks, nonzero nodes, stored block slots, kernel pairs, planning bytes, and accumulation workspace.
- Enabled explicit atomic `grid_backend="local_sparse"` with `discrete_periodized_v1` for atom-index and species selections while keeping dense storage as the default and `auto` reserved for LD4.
- Integrated exact sparse counts into Phase-B/Phase-C scene planning and realization accounting; sparse scientific fields remain intentionally non-renderable until LD2.
- Kept framework-vertex and framework-edge sparse preparation reserved for LD3.
- Added the LD1-B Markdown/PDF specification, updated the governing architecture standard, and added focused packing, mask, gather, serialization, planning, provenance, determinism, storage-reduction, compatibility, and failure-before-allocation tests.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v8`.
- Preserved the dense default path byte-for-byte against `mdstats 0.19.45a0`.

## 0.19.45a0 - LD1-A sparse CIC and canonical reference

- Added sparse-only `PeriodicGaussianStencilSupport` construction without logical dense-stencil allocation.
- Added deterministic periodic CIC aggregation into sorted occupied logical nodes.
- Added stencil-major sparse application of `discrete_periodized_v1` with exact final measure normalization.
- Added auditable highest-density-region threshold, achieved-mass, and tie diagnostics.
- Added a flat-node sparse reference field with public periodic node access and guarded dense debugging conversion.
- Added explicit CIC-contribution, stencil-candidate, kernel-pair, workspace, and dense-debug resource limits.
- Added the LD1-A Markdown/PDF specification, updated the governing architecture standard, and added focused orthogonal, LTA-skewed, periodic-boundary, multi-image, overlapping-source, bimodal, ensemble, identity, determinism, and resource tests.
- Preserved all production dense plotting behavior and kept `grid_backend="local_sparse"` unavailable until LD1-B/LD4.

## 0.19.44a0 - LD0-B effective density broadening

- Added weighted periodic CIC phase covariance and immutable artificial-broadening diagnostics.
- Added covariance-only canonical-stencil moments without dense stencil allocation.
- Enabled explicit `effective_cic_stencil_rms_v1` with `discrete_periodized_v1`; default legacy metric/operator behavior is unchanged.
- Added deterministic bounded effective-width refinement plus explicit, budget-limited, zero-spread, and zero-bandwidth policies.
- Added atomic, framework-vertex, and framework-edge broadening metadata and Phase-B planning provenance.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v7`.

## 0.19.43a0 - LD0-K canonical discrete density kernel

- Added `mdstats.plotting.density_kernel` with the immutable, schema-versioned `PeriodicGaussianStencil` record.
- Added deterministic finite-support integer-image enumeration in the exact Cartesian metric and canonical periodic aggregation.
- Added direct and FFT circular convolution of the same normalized `discrete_periodized_v1` stencil.
- Added the exact zero-bandwidth identity path without Gaussian-stencil allocation during field preparation.
- Added cutoff, normalization, active-offset, periodic-image, covariance, roundoff-clipping, and post-convolution diagnostics.
- Enabled the canonical operator for dense atomic, framework-vertex, and framework-edge density fields while keeping `legacy_spectral_v1` as the unchanged default.
- Added dense-stencil resource planning, scene-wide stencil limits, and mixed-operator planning provenance.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v6`.
- Added the LD0-K Markdown/PDF specification, updated the governing architecture standard, and added focused operator, integration, planning, migration, and compatibility tests.
- Verified exact `0.19.42a0` legacy density, HDR, integral, and marching-cubes compatibility on matched fixtures.

## 0.19.42a0 - LD0-R3 transactional density-scene planning

- Added immutable Phase-A, Phase-B, and scene-level density planning records with canonical JSON serialization.
- Added exact bounded CIC target-node planning without allocating dense scalar fields.
- Added scene-wide sample, planning, storage, mesh-bound, and package-owned peak-memory limits.
- Added one global Phase-C approval before atomic or framework density allocation.
- Attached approval IDs, field planning summaries, and realization accounting to prepared density scenes and fields.
- Advanced the framework-dynamics scene schema to `mdstats.framework-dynamics-scene.v5`.
- Preserved dense CIC, `legacy_spectral_v1`, normalization, HDR, and marching-cubes numerics exactly.

## 0.19.41a0 - LD0-R2 density diagnostics and registration validation

- Added deterministic, metric-aware periodic Fréchet-mean diagnostics with bounded-memory exact weighted-medoid initialization, stable multi-start solving, convergence records, and ambiguity detection.
- Added validity-filtered periodic positional-spread diagnostics and explicit zero-spread / insufficient-valid-mean policies for adaptive density resolution.
- Added a certified reciprocal sampling-lattice resolution diagnostic for orthogonal and skewed cells.
- Added quantitative cell-equivalence validation and reject periodic laboratory-frame density preparation when variable source cells do not share the display-cell periodic identification; laboratory trajectories remain supported.
- Corrected density voxel-cloud coordinates to the logical-node convention `i / N_i`, removing the previous half-grid displacement.
- Added diagnostic metadata to atomic density, framework density, atomic mean graphs, and framework-dynamics scenes, and advanced the scene schema to `mdstats.framework-dynamics-scene.v4`.
- Added the LD0-R2 Markdown/PDF specification, updated the governing architecture standard, and added focused convergence, ambiguity, skew-cell, registration, and compatibility tests.
- Preserved the 0.19.40a0 CIC, legacy spectral smoothing, normalized density arrays, HDR thresholds, integrals, and marching-cubes geometry exactly on matched fixtures.

## 0.19.40a0 - LD0-R1 density contracts and dense adapters

- Added `mdstats.plotting.density_contracts` as the renderer-independent contract boundary for future dense and local-sparse density backends.
- Added shared resolution, kernel, storage, and rendering option records while preserving the existing atomic/framework option constructor surface.
- Added schema-versioned `DensitySourceProvenance`, `PeriodicWeightedSamples3D`, `DensityStorageSummary`, recursively immutable JSON-compatible metadata, and tagged canonical source keys.
- Extended `PeriodicScalarField3D` with backend-neutral scientific identity, storage accounting, lexicographic node iteration, periodic node gather, and JSON-compatible round trips.
- Added `ScalarField3D` and `PeriodicNodeFieldAccess` protocols plus a zero-copy dense adapter.
- Relaxed framework-density and framework-dynamics scene validation from one concrete dense class to the backend-neutral scalar-field contract.
- Reserved and explicitly rejected canonical-operator, effective-broadening, sparse, and automatic-backend requests until their owning architecture gates are implemented.
- Added the LD0-R1 Markdown/PDF specification, updated the governing architecture standard, and added focused contract/compatibility tests.
- Preserved the existing CIC deposition, `legacy_spectral_v1` Gaussian FFT smoothing, normalization, registration, HDR, mesh, and rendering numerics.

## 0.19.39a0

- Derive the default Gaussian bandwidth from the longest realized density-grid interval with `gaussian_to_grid_ratio=2.0`.
- Compute per-atom or per-framework-vertex periodic Cartesian positional standard deviations using minimum-image displacements from a Frechet/Karcher mean.
- Add spread-aware grid and Gaussian refinement when artificial smoothing is large relative to the measured positional SD.
- Bound automatic refinement by the per-field voxel budget and emit explicit warnings when the requested broadening criterion cannot be reached.
- Record resolved grid, Gaussian, SD summaries, adaptive status, and budget limitation in density-field metadata.
- Extend atomic/framework density specifications and focused tests for ratio coupling, periodic SD, adaptive refinement, and budget-limited behavior.

## 0.19.38a0

- Replace fixed 96^3 atomic and framework density defaults with a cell-size-aware target lattice-grid interval.
- Add `grid_interval=0.20` angstrom as the default and resolve `N_i = ceil(|a_i| / grid_interval)` independently for each display-cell vector.
- Preserve explicit `grid_shape` as an override for reproducibility and expert control.
- Add public `resolve_density_grid_shape(...)` and `density_grid_intervals(...)` helpers.
- Record target interval, resolved shape, realized intervals, and resolution policy in density-field metadata.
- Add cubic, triclinic, explicit-override, metadata, and framework-density regression tests.

## 0.19.37a0

- Fix averaged atomic-net vertices that could jump to equivalent periodic images when connectivity components or spanning trees changed between frames.
- Define atomic mean vertices by the metric-aware periodic Fréchet/Karcher mean of the same registered coordinates used by atomic density fields.
- Count atomic edge occupancy by atom pair and recompute displayed image shifts from corrected mean vertices using the Euclidean minimum-image convention.
- Add a regression test for connectivity-gauge changes and validate the Na-LTA plot: all 168 vertices lie within 0.0011 A of their periodic trajectory means and all retained bonds remain between about 1.59 and 2.58 A.

## 0.19.36a0

- Preserve the existing Euclidean Plotly scene metric and document its range/aspect invariant.
- Raise atomic- and framework-density defaults to a 96^3 grid with a 0.35 angstrom Gaussian bandwidth, avoiding systematic ellipticity from under-resolved shells in oblique cells.
- Add an isotropic-shell regression test in the 60-degree LTA primitive cell.
- Regenerate the all-species Na-LTA example with metric-safe density settings.

## 0.19.35a0

- Add Plot-D5 averaged atomic-connectivity overlays to the framework-dynamics scene.
- Introduce `AtomicMeanGraphOptions`, `AtomicMeanGraph`, and `AtomicMeanGraph3DRenderOptions`.
- Extend `prepare_framework_dynamics_scene(...)` and `plot_framework_dynamics_3d(...)` to support species-colored atomic nets with persistent or occupancy-threshold bond retention.
- Add Plot-D5 Markdown/PDF specification plus focused rendering and regression tests.

## 0.19.34a0

- Replace browser-side Plotly `Isosurface` density triangulation with explicit periodic `Mesh3d` shells extracted before HTML serialization.
- Use the Lewiner marching-cubes implementation from scikit-image, with explicit Lorensen-Cline and Lewiner citations in code and plotting specifications.
- Add a sparse `voxel_cloud` density renderer and make it the framework-density default because it reuses the proven `Scatter3d` browser path.
- Add robust handling for highest-density thresholds that round to a float32 plateau maximum.
- Add mesh geometry, no-`Isosurface`, and voxel-fallback regression tests.

## 0.19.33a0

- Fix canonical wrapping of registered mean-framework geometry while preserving translation-labelled edge vectors.
- Recompute final composite 3-D aspect ratios after adding trajectories and density overlays.
- Render density probability-mass shells as explicit toggleable traces with reliable opacity.
- Group selected atomic trajectories under one legend toggle.

## 0.19.32a0 - Framework density Plot-D4

- Added `framework_density.py` with separate normalized framework vertex-occupancy and edge-length density channels.
- Added projected-edge and authoritative atom-resolved-path source policies with periodic lifted geometry and exact arc-length normalization.
- Added uniform midpoint arc-length quadrature, periodic cloud-in-cell deposition, triclinic Gaussian smoothing, and separate physical units for vertex and edge fields.
- Extended `FrameworkDynamicsScene` and the Plotly composite viewer with independently toggleable framework-density traces and conservative default opacity.
- Added material, laboratory, and framework-registered behavior for trajectories and independent ensembles, including variable-cell edge-length measures.
- Added the Markdown/PDF Plot-D4 specification and 11 focused framework-density tests.

## 0.19.31a0 - Periodic atomic-density Plot-D3

- Added `atomic_density.py` with immutable normalized periodic scalar fields for selected atoms and species.
- Added trilinear cloud-in-cell deposition with exact selected-atom normalization and integer-wrapping invariance.
- Added Cartesian-isotropic periodic Gaussian smoothing in reciprocal space for triclinic display cells.
- Added 50/80/95 percent highest-density probability-mass shells and seam-closed Plotly isosurface rendering.
- Added optional transparent raw-sample clouds, independent trajectory/ensemble support, and material/laboratory/framework-registered density coordinates.
- Extended `FrameworkDynamicsScene`, resource preflight, public exports, HTML rendering results, and plotting documentation.
- Added the Markdown/PDF Plot-D3 specification and 12 focused density tests.

## 0.19.30a0 - Registered framework dynamics Plot-D1/D2

- Added `framework_dynamics.py` as a renderer-independent preparation boundary for registered mean-framework geometry and selected atomic trajectories.
- Added deterministic graph-node gauge normalization and exact preservation of periodic edge winding across every selected frame.
- Added material, laboratory, and translation-only framework-registered coordinate modes with explicit reference- or mean-cell display policies.
- Added individual-atom, explicit-group, and species-union selections through `TrajectoryAtomSelection`.
- Added continuous unwrapped paths and folded paths with explicit segment breaks at periodic-cell crossings.
- Added immutable `TrajectoryPathSet` and `FrameworkDynamicsScene` result models plus transactional frame, atom, point, and Plotly-trace limits.
- Added `plot_framework_dynamics_3d()` as a thin composition over the existing Plotly graph renderer, with start/end markers, hover metadata, scene-range expansion, and HTML export.
- Added the Markdown/PDF Plot-D1/D2 specification and 10 focused tests; existing framework and generic 3-D visualization regressions remain green.

## 0.19.29a0 documentation revision - Stage 11 site-state kinetics

- Added `stage11_site_kinetics_architecture.{md,pdf}` as the detailed Stage-11C-I physical and implementation plan.
- Reframed the natural tile graph as the species-independent structural scaffold and introduced the periodic site-state network as the kinetic graph.
- Distinguished persistent oriented ring-side anchors from zero, one, two, multiple, or annular physical ionic microstates.
- Added deterministic ring-order plus adjacent-tile semantic signatures and the LTA D4R/alpha/beta convention profile.
- Added the planned one-sided, bilateral, plane-centered, off-center discrete, annular, and unresolved local free-energy regimes.
- Added Arrhenius, Eyring, Vineyard harmonic-transition-state, Kramers, fluctuating-bottleneck, kinetic Monte Carlo, Transition Path Theory, Milestoning, and Markov-model validation foundations with citations.
- Added separate fast-, slow-, and comparable-timescale ring-breathing policies and explicit non-Markov/semi-Markov fallback.
- Added parameter provenance tiers, uncertainty requirements, and a Stage-11C-I implementation and validation sequence.
- Advanced the framework/ring architecture manual to revision 37 without changing production code.

## 0.19.29a0 - Compatible-frame natural-tile geometry

- Added `tiling_geometry_frames.py` as the Stage-11B mapping boundary for certified natural tiles over compatible trajectories and ensembles.
- Replayed the exact atomic, relevant-subgraph, and projected-framework integer gauges rather than guessing nearest images on the projected net.
- Added trajectory anchor continuity and independent ensemble wrapping without changing intrinsic scientific geometry.
- Added fixed source-bound mapping of scientific tile sides, nonplanar boundary-center fan surfaces, planarity diagnostics, and conservative planar-aperture flags.
- Added dynamic tile volume, volume centroid, surface area, equivalent-sphere radius, Wadell sphericity, diameter, window geometry, and instantaneous cell-volume closure.
- Added explicit per-frame `MAPPED`, `TOPOLOGY_MISMATCH`, `CONNECTIVITY_GEOMETRY_MISMATCH`, and `DEGENERATE_GEOMETRY` states.
- Added frame-aligned tile-metric series with `NaN` for unresolved frames, transactional resource preflight, independent source-binding digests, deterministic replay, and tamper rejection.
- Added 10 focused Stage-11B tests covering real LTA, deformation scaling, periodic wrapping, trajectory continuity, nonplanarity, topology changes, ensemble semantics, resources, replay, and input rejection.
- Framework/ring architecture advanced to revision 36.

## 0.19.28a0 - Natural-tile geometry and conservative cage accessibility

- Added `tiling_geometry.py` with exact source-bound realization of convex natural tiles and scientific face sides.
- Added exact rational tile volumes and volume centroids, plus Cartesian face area, perimeter, aperture witnesses, tile surface area, diameter, equivalent-sphere radius, and Wadell sphericity.
- Added `TopologicalWindow` and two reverse translation-labelled adjacency arcs for every scientific face orbit, including nonzero self-image adjacency.
- Added `cage.py` with explicit spherical probes, periodic obstacle spheres, cage/portal witness assessments, and conservative unresolved semantics for blocked witnesses.
- Added complete metric-derived nearest periodic obstacle-image enumeration without a fixed image shell.
- Added accessible-network component and cycle-voltage rank classification for isolated cages, 1D channels, 2D layers, and 3D networks.
- Added replay-verified canonical persistence, transactional geometry/accessibility resources, and tamper rejection.
- Added `build_lta_natural_tiling_reference()` and a real-LTA geometry gate recovering 10 tiles, 58 windows, 116 directed arcs, exact unit volume, and the certified 6:2:2 tile multiplicities.
- Added 10 focused Stage-11 tests; the widened connectivity-through-Stage-11 boundary passes 250 tests with only four duplicated heavy Na-LTA upstream gates deselected.
- Framework/ring architecture advanced to revision 35.

## 0.19.27a0 - LTA end-to-end natural-tiling ground gate

- Added `lta_natural_tiling.py` as the Stage-10D exact ground gate for the unlabeled LTA net at primitive-ring bounds 8, 10, and 12.
- Added exact strict-convex-planar filtering on top of bounded ring strength, retaining 36 four-rings, 16 six-rings, and 6 eight-rings as scientific faces.
- Recorded all 32 new bounded-strong twelve-rings at K=12 as exact nonplanar exclusions rather than silently ignoring them or promoting them to faces.
- Added canonical convex fan witnesses with exact periodic self-intersection and framework-penetration checks.
- Added exact cyclic face-ray ordering around lifted framework edges and translation-labelled face-side propagation into finite tile shells.
- Recovered the LTA quotient complex `(48, 96, 58, 10)` and tile multiplicities `6[4^6] + 2[4^6.6^8] + 2[4^12.6^8.8^6]`, reducing to ratio `3:1:1`.
- Added generator-based properness certification after exact multiplication-table closure to the complete order-96 net automorphism group.
- Added an LTA-specific exact convex periodic partition certificate using supporting halfspaces, strict rational interior points, exact rational volume closure, and periodic separating-axis tests.
- Added proof-preserving higher-bound reuse only after independent ring, strength, and geometry rebuilds prove identical selected-ring stable keys.
- Added 8 focused Stage-10D tests covering the real LTA gate, K=12 nonface additions, exact volumes, properness, persistence identity, resource preflight, bounds, and tamper rejection.
- Framework/ring architecture advanced to revision 34.

## 0.19.26a0 - Primitive-ring-bound rebuild and stable-key refinement

- Added `natural_tiling_refinement.py` as the Stage-10C full-rebuild orchestration and comparison boundary.
- Added `PrimitiveBoundBuild` validation so ring symmetry, bounded strength, face certificates, compatibility systems, master complexes, partitions, Stage-10B searches, and Stage-10A catalogs must all name the current primitive-ring catalog.
- Added bound-independent stable scientific records for primitive rings, ring orbits, strength results, scientific faces, compatibility systems, master complexes, master partitions, searches, natural tilings, and essential rings.
- Removed dense local IDs and catalog-bound digests from cross-bound scientific comparison while retaining complete per-stage source digests for audit.
- Added exact `ADDED`, `REMOVED`, and `MODIFIED` transition reports and separate natural-tiling outcome comparison.
- Added primitive-ring monotonicity validation: disappearance of a stable ring key between two complete increasing bounds is `INVALID`.
- Added explicit `STABLE`, `CHANGED`, `UNRESOLVED`, and `INVALID` transition states without promoting incomplete upper bounds to convergence.
- Added `stable_tested_suffix_start`, which reports only stability over the supplied final bound suffix and makes no claim about untested larger rings.
- Added transactional bound/record/change resource controls, canonical serialization, transition recomputation, and tamper rejection.
- Added 10 focused Stage-10C tests covering stable cross-digest rebuilds, callback execution, source mismatch, monotonicity, state changes, unresolved propagation, resource preflight, bound ordering, replay, and tamper rejection.
- Framework/ring architecture advanced to revision 33.

## 0.19.25a0 - Natural face selection and master-refinement splitting

- Added `natural_tiling_search.py` as the Stage-10B finite natural-face selection and local splitting backend.
- Defined an exact master-refinement contract: every admissible finite ring cut must already be represented by a valid Stage-9 scientific interface and tetrahedral partition certificate.
- Added full-group face-orbit construction and exhaustive enumeration of every nonempty symmetry-closed selectable orbit subset within transactional resource bounds.
- Restricted certified splitters to source-bound `STRONG_IN_DOMAIN` ring orbits; weak rings are excluded and missing or truncated strength evidence remains unresolved.
- Added fixed-witness unary, pairwise, higher-order, and symmetry-linked compatibility pruning without converting unresolved constraints into false rejection.
- Added exact translation-labelled tetrahedron coarsening across omitted interfaces and a zero-translation-cycle proof for finite lifted tile components.
- Added exact reconstruction of translation-labelled tile shells and complete Stage-9 partition re-certification for every generated coarsening.
- Added Stage-10A properness/candidate certification to the generated complexes and retained every inclusion-maximal viable splitting without an enumeration-order tie-break.
- Added separate finite-search completeness, rejection witnesses, scientific candidate catalogs, canonical serialization, deterministic source replay, and tamper rejection.
- Added 10 focused Stage-10B tests covering cubic one-orbit closure, three independent orbit subsets, noncompact slab rejection, bounded strength, compatibility, resources, witness binding, incomparable maxima, replay, and tamper rejection.
- Framework/ring architecture advanced to revision 32.

## 0.19.24a0 - Natural-tiling candidate and properness certification

- Added `natural_tiling.py` as the Stage-10A certification boundary for caller-proposed Stage-9 periodic cell complexes.
- Added exact scientific face and tile actions under the complete normalized periodic-net automorphism group.
- Added exact composition validation for translation-labelled oriented cell images, including the removed common lattice translation of normalized operation products.
- Added properness classification against complete `PeriodicNetSymmetryDiscovery` results; arbitrary supplied subgroups cannot masquerade as the full automorphism group.
- Kept auxiliary face triangulations and periodic tetrahedral meshes outside scientific tiling identity and symmetry action.
- Added independent primitive-completeness, symmetry, bounded-strength, embedding, compatibility, cell-complex, partition, and properness certification dimensions.
- Added explicit `ELIGIBLE`, `INELIGIBLE`, and `UNRESOLVED` candidate states without collapsing absent evidence into rejection.
- Added separate scientific and evidence digests, deterministic source replay, canonical serialization, and tamper rejection.
- Added ambiguity-preserving catalogs with scientific deduplication, `NONE`/`UNIQUE`/`MULTIPLE` outcomes, and essential-ring extraction only from eligible tilings.
- Added 14 focused Stage-10A tests covering the full 48-operation cubic action, 9,216 exact composition checks, proper/improper/unresolved semantics, resource preflight, evidence-independent identity, ambiguity, replay, and tamper rejection.
- Framework/ring architecture advanced to revision 31.

## 0.19.23a0 - Translation-labelled periodic cell complex and exact partition certificate

- Added `periodic_cell_complex.py` with finite translation-labelled integer chain terms and explicit `boundary_1`, `boundary_2`, and `boundary_3` operators.
- Added source-bound `PeriodicCellComplex` identity with exact verification of $\partial_1\partial_2=0$, $\partial_2\partial_3=0$, two tile-side incidences per face orbit, and three-torus quotient Euler characteristic zero.
- Added lifted tile-shell validation requiring connectedness, exactly two oppositely oriented face incidences per physical edge, nonbranching orientability, and boundary Euler characteristic two.
- Kept local face-sector propagation out of the scientific backend; Stage 9 validates explicit caller-supplied tile shells rather than claiming an unproved discovery rule.
- Added exact rational tetrahedron-pair classification distinguishing disjoint interiors, boundary contact, improper overlap, containment, and coincident interiors.
- Added `PeriodicPartitionCertificate` for explicit periodic tetrahedral meshes with complete periodic broad-phase candidates, exact opposite-oriented facet pairing, selected-witness interface conformity, induced-shell equality, and exact positive unit-domain volume closure.
- Added separate auxiliary vertex, tetrahedron, facet-pair, face-triangle coverage, tile-placement, and resource records.
- Added deterministic source replay and tamper rejection for both scientific complexes and partition certificates.
- Added focused simple-cubic and rational tetrahedral fixtures covering self-image incidence, chain closure, shell topology, overlap semantics, interface conformity, resource failure, replay, and tamper rejection.
- Framework/ring architecture advanced to revision 30.

## 0.19.22a0 - Embedded face placements and exact witness compatibility

- Added `_robust_geometry.py` with exact rational segment--triangle and triangle--triangle intersection, coplanar clipping, exact dimensions, and transverse signs.
- Added `_surface_mesh.py` with deterministic exhaustive boundary-vertex triangulation and Catalan resource preflight.
- Added `face_candidates.py` with source-bound, mesh-independent `FacePlacement` identity and auxiliary `FaceEmbeddingWitness` certificates.
- Added exact periodic disk self-intersection rejection and framework-penetration records without conflating penetration with disk embeddedness.
- Added nonzero algebraic ring--surface intersection as a rigorous linking certificate.
- Added distinct witness-pair outcomes for proven linking, incompatible particular disks, unresolved degeneracy, prescribed shared boundaries, and disjoint-disk unlinking witnesses.
- Added finite unary, pairwise, higher-order, face-symmetry, and witness-equivariance constraints.
- Added deterministic source replay for face, witness-pair, and compatibility-system serialization.
- Added focused rational-coordinate fixtures for planar/nonplanar disks, penetration, Hopf linking, zero-link disk incompatibility, unlinking, shared boundary, higher-order restrictions, resource failure, and tamper rejection.
- Framework/ring architecture advanced to revision 29.

## 0.19.21a0 - Periodic spatial broad phase and exact edge-intersection certificate

- Added private `_periodic_spatial.py` with continuous lifted fractional AABB supports, complete support-derived periodic translation stencils, direct enumeration, and automatic linked-cell candidate generation.
- Added explicit canonical `(object_i, object_j, image_shift)` identities, including nonzero self-image candidates.
- Adapted the classical Quentrec--Brot linked-cell idea to multi-bin extended-object supports with deterministic grid selection and transactional resource limits.
- Added `periodic_edge_intersection.py` with exact rational three-dimensional segment predicates.
- Added exact contact semantics for allowed shared lifted vertices, forbidden proper crossings, endpoint-on-interior contacts, distinct lifted-vertex endpoint collisions, and collinear overlaps.
- Added source-bound, replay-verified `PeriodicEdgeIntersectionCertificate` schema v1.
- Verified direct/linked-cell candidate equivalence and complete detection of nonzero-image crossings.
- Na-LTA is globally certified intersection-free under the authoritative straight-edge embedding.
- Focused Stage-4--8B regression gate passes in four nonoverlapping groups: `75 + 30 + 15 + 16 = 136 passed`.

### Framework/ring architecture revision 28

- Records the implemented query-agnostic periodic spatial broad phase and exact straight-edge certificate.
- Separates candidate workspace from the persistent scientific certificate.
- Defers deformation-aware candidate caching until a time-dependent extended-object consumer exists.

## 0.19.20a0 - Authoritative periodic-net embedding

- Added `periodic_net_embedding.py` with source-bound `PeriodicNetEmbedding` schema v1.
- Added the exact edge-covariance metric $G=C^{-1}$ from all projected quotient-edge vectors, followed by primitive integral normalization.
- Verified exact lattice-metric invariance $A_g^{\mathsf T} G A_g = G$ and exact affine vertex/edge equivariance under the complete discovered symmetry group.
- Made the metric covariant under unimodular lattice-basis changes rather than dependent on an arbitrary identity metric in the source basis.
- Added deterministic unit-volume Cartesian cells from the lower-triangular Cholesky factor of the exact Gram-matrix shape.
- Added explicit `ProjectedEdgeCurveModel.STRAIGHT_SEGMENT` and transient source-bound `EmbeddedStraightEdgeSegment` geometry.
- Added transactional rejection for collided barycentric vertices, singular edge covariance, zero-length projected edges, and coincident distinct straight projected edges.
- Added a ring-independent symmetry-discovery certificate digest so optional primitive-ring symmetry payloads do not alter embedding identity.
- Added vertex, edge, symmetry-order, and exact metric bit-growth resources.
- Na-LTA builds successfully against the complete 96-operation unlabeled $T$-net symmetry group.
- Focused Stage-4--8 regression gate passes in five nonoverlapping groups: `130 passed`.

### Framework/ring architecture revision 27

- Defines the exact rational placement plus primitive integral Gram matrix as the authoritative Euclidean reference.
- Separates Stage-8A vertex/edge degeneracy certification from Stage-8B global periodic crossing certification.
- Records the basis-covariant metric derivation and explicit straight projected-edge model.

## 0.19.19a0 - Stage 7R certification and persistence consolidation

- Split core `PeriodicNetSymmetry` schema v3 from primitive-ring-derived data.
- Added `primitive_ring_symmetry.py` with compact, source-bound `PrimitiveRingSymmetryIndex` schema v1 tied to both the exact symmetry and primitive-ring catalog digests.
- Added `periodic_barycentric.py` with reusable exact rational `PeriodicBarycentricPlacement` schema v1 and explicit vertex/fraction-bit resources.
- Updated automatic symmetry discovery to schema v2 with nested barycentric placement, core symmetry, and optional separate primitive-ring symmetry index.
- Split persistent `RingStrengthResult`/`RingStrengthCatalog` schema v2 from transient `RingStrengthSearchWorkspace` candidate data.
- Added deterministic candidate-set digests and independent source-bound strength verification during deserialization.
- Added explicit `GF(2)` support-matrix and provenance-bit memory guards; resource exhaustion returns `UNRESOLVED_TRUNCATED`.
- Added immutable O(1) atom/edge lookup maps to `PeriodicNetView`.
- Reduced the Na-LTA symmetry payload from about 9.17 MB combined to about 0.83 MB core group plus 1.01 MB catalog-bound ring index.
- Reduced a depth-eight, 3,240-candidate LTA strength result to about 4 KB persistent JSON while retaining deterministic replay.
- Focused Stage-4--7 boundary regression gate passes: `120 passed`.
- Complete suite passes in eight nonoverlapping groups: `635 passed, 28 warnings`; all 55 test files were covered exactly once.

### Framework/ring architecture revision 26

- Defines scientific results, derived indices, search workspaces, and verification certificates as distinct ownership classes.
- Makes reusable exact barycentric placement the shared input to discovery and future embedding.
- Records the cleaned persistence schemas and memory/certificate policies before Stage 8A.

## 0.19.18a0 - Bounded strong-ring classification

- Added `ring_strength.py` with exact bounded strong-ring classification over translated primitive-ring placements.
- Added immutable `EdgeIncidencePlacementDomain`, `RingStrengthDomain`, and `RingStrengthResources` APIs.
- Added source-bound `RingStrengthResult` and `RingStrengthCatalog` schemas with deterministic SHA-256 digests and source-validated deserialization.
- Implemented target-connected physical-edge incidence expansion with monotone finite depth domains.
- Added exact `WEAK_CERTIFIED`, `STRONG_IN_DOMAIN`, `UNRESOLVED_TRUNCATED`, and `UNRESOLVED_SOURCE_INCOMPLETE` status semantics.
- Added exact weak-ring witnesses verified over physical lifted-edge support through the Stage-5 GF(2) cancellation solver.
- Enforced lower-closed, untruncated `PRIMITIVE_NO_SHORTCUT` source completeness through every admitted component size.
- Separated mathematical domain completeness from candidate/search/support resource limits.
- Added deterministic canonical zero-shift batch catalogs.
- Na-LTA depth-one ground result: 36 strong 4-rings; 24 weak and 16 boundedly strong 6-rings; 6 boundedly strong 8-rings.
- Focused Stage-4/5/6/7 regression gate passes: `113 passed`.

### Framework/ring architecture revision 25

- Records bounded Stage-7 strong-ring classification as implemented.
- Defines the edge-incidence-depth placement domain and connected minimum-witness reduction.
- Keeps finite-domain strength distinct from local tile strength and natural-tiling face selection.

## 0.19.17a0 - Exact automatic periodic-net symmetry discovery

- Added `net_symmetry_discovery.py` with exact rational barycentric/star-frame discovery for eligible `PeriodicNetView` objects.
- Added immutable `NetSymmetryDiscoveryOptions`, `BarycentricFrameIncidence`, and `PeriodicNetSymmetryDiscovery` APIs with source-validated serialization.
- Solved the periodic equilibrium placement exactly over `fractions.Fraction`; no float tolerance enters symmetry acceptance.
- Added deterministic source-anchor/frame selection, exhaustive signature-compatible target-frame enumeration, exact integer-unimodular affine action recovery, and complete vertex/multiedge validation.
- Added exact handling of indistinguishable parallel-edge permutations and deterministic reduction to a generator subset before finite group assembly.
- Hardened `PeriodicNetSymmetry` schema to v2 with an exact `composition_translation_table` cocycle for normalized representatives modulo translations.
- Corrected absolute primitive-ring placement composition for nonsymmorphic operations using the translation cocycle.
- Added construction and serialization validation of every cocycle entry.
- Added transactional rejection for barycentric collisions, partial/lower-dimensional periodicity, disconnected or index-greater-than-one lifts, flat local frames, and resource exhaustion.
- Na-LTA ground fixture recovers group order 96, one vertex orbit, three edge orbits, and five primitive-ring orbits of sizes 6, 12, 16, 24, and 24 covering all 82 rings.
- Focused Stage-4/5/6 regression gate passes: `105 passed`; full suite passes in seven nonoverlapping groups: `620 passed, 28 warnings`.

### Framework/ring architecture revision 24

- Records exact automatic Stage-6C symmetry discovery as implemented.
- Adds the normalized-representative translation cocycle as a mandatory symmetry invariant.
- Makes bounded strong-ring classification the next implementation stage.

## 0.19.16a0 - Finite periodic-net symmetry group modulo translations

- Added `net_symmetry.py` with exact finite subgroup assembly from explicit view-bound automorphism generators.
- Added deterministic common-translation gauge normalization at one source anchor vertex.
- Added exact periodic automorphism composition and inverse, including integer lattice matrices and explicit multiedge orientation action.
- Added transactional Cayley-style closure with `max_operations` protection against underconstrained infinite closures.
- Added deterministic operation ordering, multiplication and inverse tables, identity indexing, and canonical result digests.
- Added exact vertex and edge orbit partitions.
- Added optional primitive-ring action tables, ring-key orbits, stabilizers, and exact induced-action homomorphism verification.
- Added source-validated `PeriodicNetSymmetry` serialization.
- Hardened explicit automorphism validation so vertex image shifts vanish along nonperiodic axes.
- Added exact 3x3 integer matrix multiplication and unimodular inversion to the private periodic arithmetic kernel.
- Focused Stage-4/5/6 regression gate passes: `94 passed`; full suite passes: `615 passed, 28 warnings`.

### Framework/ring architecture revision 23

- Records explicit-generator finite group assembly as implemented Stage 6B.
- Splits automatic complete generator discovery into Stage 6C.
- Preserves the distinction between a generated subgroup and the certified full automorphism group.

## 0.19.15a0 - View-bound periodic automorphism validation

- Bound every validated periodic multigraph automorphism to one exact `PeriodicNetView.digest`.
- Changed `build_validated_periodic_automorphism()` to validate against `PeriodicNetView` rather than `PrimitiveRingIndex`.
- Enforced deterministic `NetViewPolicy` vertex and edge signatures; ignored decorations permit exchange but never graph-record collapse.
- Added active-PBC-subspace validation for integer unimodular lattice matrices.
- Kept explicit multiedge permutation/orientation and exact quotient endpoint/image-shift validation.
- Made `PeriodicEdgeImage` dense values explicitly net-view edge positions while retaining the historical `target_edge_index` field name and a `target_edge_position` alias.
- Bridged net-view edge positions and primitive-ring catalog edge indices only through stable `FrameworkEdgeKey`.
- Bound `RingOccurrenceMap` to the exact net-view digest.
- Added tests showing Si/Al and O/S exchanges accepted by the unlabeled view and rejected by the chemically decorated view.
- Added same-topology/different-view rejection and partial-PBC lattice-action tests.
- Focused Stage-4/5/net-view regression gate passes: `88 passed`.

### Framework/ring architecture revision 22

- Records Stage 6A view-bound explicit automorphism validation as implemented.
- Leaves automatic discovery, deterministic translation gauge, group closure, serialization, and orbit/stabilizer catalogs for Stage 6B.

## 0.19.14a0 - Explicit PeriodicNetView signature projection

- Added `periodic_net_view.py` with immutable `NetViewPolicy`, `PeriodicNetComponent`, and `PeriodicNetView` APIs.
- The first backend preserves the exact `FrameworkTopology` vertex/edge orbit sets and changes only deterministic automorphism signatures.
- Added unlabeled-framework and chemically decorated built-in policies with schema-versioned semantic policy digests.
- Preserved parallel framework edges as distinct source records even when their view signatures are equal.
- Added exact source vertex/edge mappings, source graph/topology provenance, and source-validated serialization.
- Added deterministic quotient-component analysis and closed-walk cycle-gain generators.
- Added exact translation rank and full-rank integer subgroup index via determinant divisors/Smith-normal-form theory.
- Strengthened first-backend natural-tiling eligibility to require full 3D PBC, one quotient component, translation rank three, and subgroup index one.
- Added focused synthetic and Na-LTA tests; Stage-4/5 focused regression gate passes: `78 passed`.

### Framework/ring architecture revision 21

- Records `PeriodicNetView` as implemented.
- Clarifies that quotient connectedness plus rank three is insufficient when the translation subgroup has index greater than one.
- Makes automatic symmetry discovery and net-view-owned automorphism records the next implementation stage.

## 0.19.13a0 - Stage 5 periodic infrastructure cleanup and API hygiene

- Source-bound `RingPlacement` by `(topology_graph_digest, PrimitiveRingKey, image_shift)`.
- Source-bound `LiftedEdgeInstanceRef` by `(topology_graph_digest, FrameworkEdgeKey, anchor_shift)`; dense edge indices remain transient index internals.
- Added private `_periodic_graph.py` for exact integer lattice arithmetic proven common across P1-P3.
- Added `periodic_cycle.py` with `CycleParameterization`; physical placement and boundary parametrization are now separate contracts.
- Added supported `canonicalize_primitive_ring_tokens()` and removed P2 dependence on a private primitive-ring helper.
- Added ordered `canonical_edge_instances()` and `translated_edge_instances()` support accessors.
- Hid primitive ring occurrence buckets/records from the supported analysis API.
- Renamed occurrence-map fields to explicit source-position -> target-position semantics.
- Advanced Stage-5 infrastructure remains under `mdstats.analysis` and is no longer re-exported from the package root.
- Updated strength architecture: no independent `max_component_count` in the mathematical GF(2) strength domain.
- Added cross-source identity, cycle parametrization, support translation, and export-boundary regression tests.
- Full suite covered in three nonoverlapping groups: `586 passed, 28 warnings`.

### Framework/ring architecture revision 20

- Freezes the lightweight Stage-5 identity/helper boundary after concrete P1-P3 comparison.
- Records source-safe identity, private periodic arithmetic extraction, cycle parametrization, and the revised strength-domain semantics.
- The next new scientific implementation is `PeriodicNetView`.

## 0.19.12a0 - Stage 5-P3 exact finite primitive-ring support cancellation

- Added `primitive_ring_cancellation.py` as the Stage-5 P3 exact finite GF(2) consumer prototype.
- Added `RingPlacementSupport` over complete physical `LiftedEdgeInstanceRef` basis elements; translated instances of one quotient edge remain distinct.
- Added deterministic `solve_finite_ring_cancellation()` over an explicitly supplied finite set of strictly smaller translated primitive-ring placements.
- Added exact statuses `DECOMPOSITION_FOUND` and `NOT_IN_SUPPLIED_SPAN`; finite negative results are explicitly not strength classifications.
- Added `RingCancellationWitness` with independent exact physical-edge symmetric-difference verification.
- Added Goetzke-Klein and Yuan-Cormack strong-ring attribution in the specification and source comments.
- Added a synthetic weak primitive fixture where one primitive 6-ring is exactly the GF(2) sum of three 4-rings, plus wrong-image and incomplete-candidate controls.
- Added Na-LTA support validation for all 82 represented ring orbits.
- Focused Stage-4R/P1/P2/P3 regression suite passes: `71 passed`.

### Framework/ring architecture revision 19

- Records Stage 5-P3 as implemented and gated.
- Makes exact physical lifted-edge support and finite-span semantics concrete while preserving the rule that no finite negative result becomes a strong-ring theorem without exhaustive domain certification.
- All three Stage-5 consumer prototypes now pass; the next gate is minimal helper extraction/API freeze based only on demonstrated duplication.

## 0.19.11a0 - Stage 5-P2 exact automorphism-induced ring occurrence mapping

- Added `periodic_ring_action.py` as the Stage-5 P2 validation/application prototype; it does not discover symmetry.
- Added exact lifted-vertex action `(i,n) -> (pi(i), A n + tau_i)` with integer unimodular lattice matrices.
- Added explicit `PeriodicEdgeImage` permutations/orientations so parallel edge orbits remain distinguishable.
- Added structural validation of vertex, edge, endpoint, and quotient-image-shift action consistency.
- Added exact `map_lifted_vertex()`, `map_lifted_edge_instance()`, and `map_ring_placement()` operations.
- Added `RingOccurrenceMap` with authoritative ordered vertex/step permutations plus derived start/orientation fields.
- Target ring lookup uses stable `PrimitiveRingKey`; exact lifted-edge-instance verification resolves cyclic/reversed occurrence alignment.
- Added paired Markdown/PDF API specification with Chung-Hahn-Klee and Delgado-Friedrichs/O'Keeffe attribution in specification and source comments.
- Added synthetic rotation/reflection/parallel-edge/composition tests and a Na-LTA gate mapping all 82 ring orbits and 432 ordered steps exactly under a translated identity action.
- Focused Stage-4R/P1/P2 regression suite passes with no ring-catalog algorithm changes.

### Framework/ring architecture revision 18

- Records Stage 5-P2 as implemented and gated.
- Keeps automatic symmetry discovery, `PeriodicNetView` signature enforcement, and group serialization deferred to Stage 6.
- Makes the exact finite modulo-two ring-support cancellation prototype the remaining Stage-5 consumer gate before broad periodic-helper extraction.

## 0.19.10a0 - Stage 5-P0/P1 exact primitive-ring placement index

- Added transient `PrimitiveRingIndex` with stable `PrimitiveRingKey` lookup and
  occurrence-level edge-orbit inverse incidence.
- Added exact source-bound `LiftedEdgeInstanceRef`, `RingPlacement`,
  `PrimitiveRingEdgeOccurrence`, and `RingEdgePlacement` records.
- Added `ring_placements_covering_edge()` using exact quotient-edge image anchors;
  reverse traversal correctly subtracts the canonical edge translation.
- Hardened `PrimitiveRingCatalog` validation so stored lifted vertex walks must be
  continuous with their oriented framework-edge steps.
- Added paired Markdown/PDF API specification with Chung-Hahn-Klee/Klee periodic
  quotient-graph attribution in both specification and source comments.
- Added synthetic and Na-LTA focused tests. The Na-LTA gate retains
  `36 x 4R + 40 x 6R + 6 x 8R = 82` ring orbits and validates all 432 canonical
  ring-step occurrences.
- Verified that the Na-LTA primitive-ring catalog digest, structural-key hash, and
  ring-digest aggregate are unchanged from revision 16.

### Framework/ring architecture revision 17

- Records Stage 5-P0/P1 as implemented and gated.
- Keeps `PrimitiveRingCatalog` as the sole scientific ring result; the new index is
  transient and source-bound.
- Makes automorphism-induced ordered ring-occurrence mapping the next consumer
  prototype before any broad periodic-helper refactor.

### Framework/ring architecture revision 16

- Generalized the extended-object periodic spatial layer to query-specific
  conservative support rules for distance, intersection, penetration, linking,
  containment, and volume overlap.
- Required continuous lifted supports, image-labelled multi-bin occupancy,
  explicit multi-image candidates, and preservation of valid self-images.
- Clarified reuse of the deformation-aware Verlet theorem/kernel without importing
  atomic unique-image/MIC assumptions.
- Separated scientific `FacePlacement` from auxiliary `FaceEmbeddingWitness` and
  removed auxiliary mesh combinatorics from properness identity.
- Added certificate-correct linking semantics and tile interior-overlap/containment
  semantics.
- Added linked-cell and intersection-theoretic linking references.
- Regenerated the architecture manual. No runtime API, schema, or executable
  algorithm changes.

### Framework/ring architecture revision 15

- Restricted the first `PeriodicNetView` backend to signature projection of the
  exact framework graph; graph-changing views now require their own compatible
  primitive-ring catalog.
- Added `PeriodicNetEmbedding` as the explicit symmetry-compatible Euclidean
  realization used for face and tiling topology; distorted trajectory frames no
  longer qualify merely by preserving connectivity.
- Defined the canonical lifted representative that anchors
  `RingPlacement.image_shift` and clarified that persistent ring identity remains
  topology-digest plus `PrimitiveRingKey`.
- Added complete periodic translation stencils and a dedicated automatic
  extended-object linked-cell broad phase with multi-bin occupancy for large-cell
  Euclidean geometry.
- Reused the implemented deformation-aware Verlet validity theorem/kernel for
  fixed-connectivity embedded graph/mesh objects via maximum vertex-displacement
  bounds; atomic and extended-object cell lists/candidate payloads remain separate.
- Separated natural-tiling outcome from multidimensional certification, required
  lower-closed primitive-ring input for strength analysis, and separated
  `PeriodicPartitionCertificate` from scientific `PeriodicCellComplex` identity.
- Regenerated and visually inspected the architecture PDF. This documentation
  revision changes no runtime API, schema, numerical algorithm, or executable
  package version.

### Framework/ring architecture revision 14

- Added `PeriodicNetView` as the explicit periodic multigraph whose automorphism
  group defines properness and natural tiling.
- Separated stable-key physical `RingPlacement` from cyclic
  `CycleParameterization`; dense ring IDs are now explicitly catalog-local and
  invalidated by ring-bound refinement.
- Reworked planned symmetry records for periodic multigraphs to include finite
  representatives modulo translation, deterministic shift gauge, explicit edge
  permutations/orientations, ordered ring-occurrence maps, and stabilizers.
- Split mathematical strong-ring search domains from execution resource limits
  and required all bounded or unresolved status to propagate into face and
  tiling certification.
- Made `EmbeddedFacePlacement` include a selected surface option and replaced a
  pairwise-only conflict graph with a finite compatibility constraint system.
- Deferred public chain algebra to the periodic-cell-complex layer, where
  translation-labelled attaching maps and boundary operators are defined.
- Required an explicit periodic partition certificate for no-overlap/no-void;
  volume closure is now diagnostic only.
- Reordered Stage 5 so consumer prototypes precede common-helper extraction and
  API freeze.
- Regenerated and visually inspected the architecture PDF. This documentation
  revision changes no runtime API, schema, numerical algorithm, or executable
  package version.

### Framework/ring architecture revision 13

- Removed the provisional `RingComplexCatalog` and recast Stage 5 as
  non-scientific periodic-cycle infrastructure.
- Added the planned private `_periodic_graph.py` core, lightweight
  `RingCycleView`, exact `PeriodicEdgeChain`, complete
  `RingBoundaryTransform`, and a nonserialized source-bound
  `PrimitiveRingIndex`.
- Made translated ring placement, shared-boundary queries, and contact relations
  lazy consumer operations rather than a global persistent ring-contact graph.
- Required exact lifted physical edge-instance algebra; quotient incidence
  matrices and modulo-two vectors are now diagnostic or local derived encodings
  only.
- Deferred Stage-5 API freeze until transformed-ring matching for symmetry and
  translated-ring placement for strong-ring analysis have both been prototyped.
- Assigned all finite decomposition-domain bounds to `ring_strength.py`, allowed
  higher-order face compatibility constraints, and removed primitive/supercell
  equivalence from the Stage-5 gate until an explicit periodic-net mapping
  exists.
- Regenerated and visually inspected the architecture PDF. This documentation
  revision changes no runtime API, schema, numerical algorithm, or executable
  package version.

### Framework/ring architecture revision 12

- Added a formal bounded-periodic completeness proof for the implemented
  `SHORTEST_PATH_PAIRS` / `PRIMITIVE_NO_SHORTCUT` algorithm.
- Proved translation-orbit coverage, even/odd shortest-path reconstruction, and
  reduction of bounded primitive classification to the finite induced graph
  $H_K$.
- Updated `primitive_ring_spec.{md,pdf}` to state completeness for all
  lifted-simple, zero-winding primitive-ring translation orbits through the
  requested untruncated size bound.
- Replaced the provisional ring-graph/surface/essential-face pipeline with a
  periodic cell-complex architecture centered on `RingComplexCatalog`, exact
  periodic-net symmetry, bounded strong-ring classification, embedded face
  candidates, periodic cell construction, and natural-tiling selection.
- Made ring adjacency a derived view, moved descriptive ring geometry to a
  parallel branch, and assigned essential-ring status only after an accepted
  natural tiling exists.
- Added primary references for periodic graph symmetry, barycentric placement,
  natural tilings, robust predicates, and spanning-disk complexity; identified
  the periodic completeness and cell-complex constructions as original
  `mdstats` derivations.
- Regenerated and visually inspected the paired architecture and primitive-ring
  PDFs. This documentation revision changes no runtime API or numerical
  implementation.

## 0.19.9a0 - VACF-derived VDOS and running-diffusion example

- Added public `plot_vacf_diffusion()` for one or more `VACFDiffusionResult` objects.
- Added explicit fs/ps/ns time axes and Angstrom^2/ps or cm^2/s diffusion units without mutating stored data.
- Kept finite-time `D(t)` distinct from an accepted plateau or asymptotic coefficient; the plotter performs no tail fit, smoothing, or convergence declaration.
- Added a reproducible watcher-generated VASP `TRAJECTORY` example that computes a mass-weighted VACF-derived VDOS and a uniformly weighted Green-Kubo `D(t)` curve from native velocities.
- Added separate PNG/PDF figure output and CSV data export, plus automatic VDOS display-range selection.
- Added paired Markdown/PDF plotting specifications and focused real-data validation on the supplied 1500-frame Na-LTA trajectory.

## 0.19.8a0 - Watcher-generated VASP CONTCAR trajectory reader

- Added explicit `format="vasp-contcar-trajectory"` dispatch to `read_vasp_frames()` for chronological streams made by concatenating complete VASP MD CONTCAR restart records.
- Required a user-supplied saved-frame `timestep_fs` and preserved source-record timing under `start`, `stop`, and `stride`.
- Parsed POSCAR/CONTCAR lattice scaling, named species, selective dynamics, direct or Cartesian positions, optional lattice velocities, native Cartesian ionic velocities, and the observed three-array predictor-corrector restart section.
- Converted native VASP Cartesian velocities exactly from Angstrom/fs to Angstrom/ps and disabled every finite-difference fallback for this format.
- Added strict record/line diagnostics for missing velocities, truncated snapshots, inconsistent species/counts, and changing embedded POTIM.
- Added standard-mass fallback plus optional `mass_map`, compressed-text support, custom provenance, and downstream VACF/VS2 compatibility.
- Added reproducible `watch_contcar.sh` and `vasp_contcar.sh` examples and documented the exact `cat CONTCAR.* > TRAJECTORY` construction recipe.
- Added paired Markdown/PDF specifications, focused synthetic tests, and real-data acceptance checks on the supplied 168-atom, 1500-frame trajectory.

## 0.19.7a0 - VS2 direct Welch velocity spectrum

- Added public `compute_velocity_spectrum()` for direct one-sided self velocity spectral-density estimation from uniformly sampled trajectory velocities.
- Implemented Welch segment averaging with explicit segment length, fractional or sample-count overlap, DFT-even SciPy windows, optional constant detrending, zero padding, and density normalization.
- Reused the shared VC0 selection, weighting, physical drift-removal, and per-atom request contract.
- Added atom-blocked weighted self-only periodograms, optional Hermitian Cartesian tensor spectra, and request-ordered per-atom outputs without cross-atom products.
- Added SciPy `welch`/`csd` oracle tests, biased-VACF/full-record equivalence, Parseval-compatible normalization, block-invariance, detrending, selection, and invalid-input tests.
- Cited Welch (1967) and SciPy explicitly while distinguishing mdstats-specific atom aggregation, drift semantics, memory planning, metadata, and result validation.
- Updated the paired velocity-spectrum Markdown/PDF specification and VACF dynamics roadmap.
- Ran only the focused VS2 and directly affected downstream tests, as requested.

## 0.19.6a0 - VC0 shared velocity inputs and N3.1 spectrum planning

- Added private `mdstats.analysis._velocity_common` with one resolved `VelocityInputBundle` for uniform sampling, measured/drift selection, weights, framewise drift, and per-atom output mapping.
- Refactored `compute_vacf()` to consume the shared preparation layer without changing its public API, numerical estimator, metadata, warning categories, or selection ordering.
- Added private `AtomSpectrumPlan` and `make_atom_spectrum_plan()` for conservative atom-block memory planning ahead of the direct Welch estimator.
- Documented that VC0 and N3.1 introduce no borrowed external mathematical algorithm: VC0 refactors established mdstats behavior, while N3.1 adapts the package's existing FFT planner and explicit NumPy dtype accounting.
- Added paired Markdown/PDF specifications, roadmap integration, and focused helper/spectral/VACF tests. Per user instruction, no unrelated full-package regression suite was run for this stage.

## 0.19.5a0 - G3/GK4 VACF-to-MSD reconstruction

- Added public `VACFMSDResult` and `reconstruct_msd_from_vacf()` as an optional correlation-to-displacement consistency diagnostic.
- Reconstructed scalar total or Cartesian directional MSD using two cumulative trapezoidal moments and the exact sampled identity `MSD(t) = 2 * [t I0(t) - I1(t)]`.
- Reused the physical equal-positive weighting guard and existing-lag truncation policy from GK1, rejecting mass-weighted and nonuniform explicit VACFs.
- Stored the physical VACF, both cumulative moments, reconstructed MSD, source lag/origin data, drift/backend provenance, and strict immutable consistency checks.
- Kept direct position-based MSD primary and refused to force finite-record agreement, clip negative behavior, interpolate endpoints, fit tails, or declare convergence.
- Cited Einstein, Green, Kubo, Helfand, and SciPy while distinguishing the O(T) sampled rearrangement, result contract, and interpretation policy as mdstats designs.
- Added paired Markdown/PDF GK4 specifications, roadmap integration, public exports, focused tests, release audits, and distribution validation.

## 0.19.4a0 - G2 explicit diffusion estimation and MSD/VACF comparison

- Added public `DiffusionEstimate` and `estimate_diffusion_plateau()` for explicit user-selected intervals of running Green-Kubo self-diffusion curves.
- Used existing lag samples only, reported the interval mean, and added slope, spread, endpoint-drift, residual, and optional slope-tolerance diagnostics without automatic stable-window search or tail fitting.
- Refused to fabricate an independent-sample standard error from serially correlated samples of one running integral.
- Added public `DiffusionComparisonResult` and `compare_msd_vacf_diffusion()` with centered intercept-bearing MSD fits, scalar or Cartesian Einstein factors, and symmetric relative disagreement.
- Added strict compatibility checks for time-averaged laboratory-frame MSD, atom selections, drift conventions, source identity when available, components, and dimensions.
- Cited Einstein, Green, and Kubo while distinguishing the explicit interval estimator, compatibility contract, diagnostics, and comparison measure as mdstats designs.
- Added paired Markdown/PDF G2 specifications, roadmap integration, public exports, focused tests, release audits, and distribution validation.

## 0.19.3a0 - VP1 velocity-spectrum and VDOS plotting

- Added public `plot_velocity_spectrum()` for `VelocitySpectrumResult` and `VDOSResult`.
- Added THz, inverse-centimeter, and meV horizontal coordinates without silently transforming the stored THz-based ordinate density.
- Added total, Cartesian-component, and bounded per-atom projections with strict canonical atom-index selection.
- Added explicit common-scale display normalization that preserves relative selected-curve amplitudes and never mutates scientific result arrays.
- Added result-aware labels distinguishing velocity spectral density from VDOS without making a phonon-DOS claim.
- Added paired Markdown/PDF plotting specifications, roadmap integration, public exports, focused tests, and release validation.

## 0.19.2a0 - N1.6 spectral-bin measure and VS3 VDOS normalization

- Added private `spectral_bin_integral()` for uniform one-sided FFT-bin measures using `df * sum(P_m)` rather than trapezoidal endpoint weighting.
- Added public `VDOSResult` and `compute_vdos()` with explicit `unit_area`, `degrees_of_freedom`, and `none` normalization modes.
- Required explicit degrees-of-freedom targets and refused to infer removed translational, rotational, rigid-body, or constrained modes from atom count alone.
- Added existing-bin low-frequency cropping, roundoff-only negative clipping, and strict rejection of material negative spectral weight.
- Applied one scalar normalization factor to total, Cartesian, and per-atom projections while preserving trace identities.
- Distinguished velocity-derived VDOS from harmonic phonon DOS, optical spectra, and two-phase thermodynamics in code and paired specifications.
- Added N1.6/VS3 tests, public exports, documentation, implementation audit, and release validation.

## 0.19.1a0 - N2.1 validated quadrature and GK1 VACF self diffusion

- Added private `mdstats.analysis._quadrature` with validated, length-preserving cumulative composite trapezoidal integration on uniform or nonuniform monotonic grids.
- Added public `VACFDiffusionResult` and `integrate_vacf_to_diffusion()` for scalar or Cartesian running Green-Kubo self-diffusion curves.
- Enforced physical equal-positive per-atom weighting, rejected mass-weighted and nonuniform-weight VACFs, and normalized exactly by `weight_sum`.
- Added boundary-only `maximum_time_ps` truncation without interpolation, extrapolation, tail fitting, or hidden plateau selection.
- Stored the exact scaled integrand whose cumulative trapezoidal integral reproduces the running curve, with Angstrom^2/ps canonical units and a derived cm^2/s conversion.
- Cited Green, Kubo, and SciPy while distinguishing the mdstats weighting guard, result schema, truncation policy, and deferred plateau interpretation.
- Added paired Markdown/PDF specifications, roadmap status updates, implementation audits, and focused quadrature/transport tests.
- Expanded the complete regression suite to 456 passing tests with 27 expected warnings.

## 0.19.0a0 - VS1 VACF-derived velocity spectrum

- Added `mdstats.analysis._spectral` with exact positive-lag two-sided reconstruction, centered half-Hann/half-Tukey tapers, one-sided density scaling, and `rfft` transforms.
- Added `mdstats.analysis._spectral_units` with canonical THz and derived rad/ps, cm^-1, and meV frequency axes.
- Added public `VelocitySpectrumResult` and `compute_vacf_spectrum()` without recomputing the source VACF.
- Added explicit raw/per-weight normalization, reported/biased finite-origin weighting, zero-padding metadata, and negative-spectrum policies.
- Preserved full tensor time-ordering through `C_ab(-t) = C_ba(t)` and enforced Hermitian frequency-domain tensors.
- Cited Wiener, Khintchine, Harris, Rahman, and SciPy while distinguishing mdstats-specific estimator and result conventions.
- Added paired Markdown/PDF specifications, the integrated VACF/dynamics roadmap, an implementation audit, and focused direct-DFT regression tests.

## 0.18.1a0 - S4R corrected primitive/no-shortcut enumeration

- Replaced the default removed-edge shortest-closure search with bounded shortest-path-pair construction plus the primitive no-shortcut criterion.
- Added a reusable periodic lifted shortest-path index containing exact relative-image distances and all tied predecessor records through the configured half-ring depth.
- Added parity-specific candidate generation: two internally disjoint shortest antipodal paths for even cycles, and two shortest root paths plus one exact lifted closing edge for odd cycles.
- Added certified shortest-pair provenance so primitive classification does not repeat distance queries already proved by candidate construction.
- Retained the previous algorithm as explicit `REMOVED_EDGE_SHORTEST` / `EDGE_SHORTEST_SUBSET` mode; v1 catalogs migrate only under that narrower label.
- Added optional external-shortcut witnesses, transactional source/path/path-pair/candidate/ring limits, explicit method/family metadata, and v2 serialization.
- Corrected the production Na-LTA size-eight result: the default primitive family contains 36 four-rings, 40 six-rings, and 6 eight-rings; the removed-edge subset remains 36 four-rings and 16 six-rings.
- Added an octagon-with-short-detours counterexample proving that the removed-edge method can miss a primitive cycle even when every edge has a shorter replacement path.
- Cited Horton, Vismara, Goetzke-Klein, and Yuan-Cormack in the normative specification and source documentation, while distinguishing the mdstats periodic decorated-multigraph adaptation.
- Expanded the complete regression suite to 418 passing tests with 27 expected warnings.

## 0.18.0a0 - S4 periodic primitive-ring enumeration

- Added `mdstats.analysis.primitive_ring` with immutable removed-edge shortest-path primitive-ring catalogs for periodic decorated framework multigraphs.
- Added lazy lifted-graph breadth-first search between exact periodic endpoint images, removing only one physical edge instance while retaining translated copies.
- Added all-tied-shortest-path predecessor DAGs, transactional state/path/candidate limits, explicit per-edge search diagnostics, and bounded completeness claims.
- Added multigraph-aware two-member rings, nonzero self-image-edge handling, zero-winding and lifted-simple-cycle validation, and canonical identity under cyclic rotation and whole-cycle reversal.
- Added orientation-aware atomic-path expansion that reconstructs the deterministic relation between projected framework gauge and raw atomic-path gauge.
- Added deterministic ring IDs, ring-size counts, vertex/edge incidence indexes, schema-checked serialization, canonical JSON digests, and public package exports.
- Validated the production 300 K Na-LTA framework topology: 52 rings under this exact definition, comprising 36 four-membered and 16 six-membered rings, with all 96 edge searches complete and no resource truncation.
- Added the paired Markdown/PDF S4 specification, revised framework/ring architecture manual, analytical and periodic fixtures, a reproducible Na-LTA example, and an implementation audit.
- Expanded the complete regression suite to 414 passing tests with 27 expected warnings.

## 0.17.0a5 - TS5 topology-statistics plotting and export

- Added `mdstats.plotting.topology_statistics` with exact pair-count PMFs, contact-count series, catalog occupancies and assignments, transition rasters and matrices, residence-length PMFs, contact-occupancy histograms, framework descriptor series, and cross-layer plots.
- Added `mdstats.io.topology_statistics` with canonical JSON output and deterministic long-form CSV tables for atomic, framework, temporal, and combined statistics.
- Kept plotting and export strictly downstream of TS0-TS4 result objects; no catalog or graph descriptor recomputation occurs in TS5.
- Added overwrite-safe export manifests, stable table names, canonical JSON encoding for decorated framework-edge keys, and public package exports.
- Generated twelve PNG/PDF figure pairs and a complete JSON/CSV table set for the 2,000-frame 300 K Na-LTA example.
- Added paired Markdown/PDF plotting and export specifications, an updated architecture manual, focused TS5 tests, and expanded the complete suite to 398 passing tests with 27 expected warnings.

## 0.17.0a4 - TS4 combined atomic/framework topology statistics

- Added `mdstats.analysis.topology_statistics.combined` with exact source alignment, atomic-state/framework-class contingency, cross-layer compression summaries, and trajectory boundary consequence classification.
- Added strict validation of frame indices, frame IDs, semantics, frame-to-connectivity-state assignments, and topology representative source digests.
- Added `stable`, `atomic_only`, `framework_only`, and `coupled` adjacent-boundary categories while keeping ensembles and per-frame identity modes non-temporal.
- Added a compact `CrossLayerSummary` that automatically identifies atomic variability under a uniform framework without inferring chemical mechanisms.
- Validated against the 2,000-frame 300 K Na-LTA catalogs: 72 atomic states map to one framework class; 71 atomic-only transitions, zero coupled transitions, and 1,928 stable boundaries.
- Added paired Markdown/PDF TS4 specification, architecture updates, public exports, serialization, digest validation, and focused tests.

## 0.17.0a3 - TS3 shared temporal topology statistics

- Added `mdstats.analysis.topology_statistics.temporal` with exact trajectory state intervals, changed-state events, adjacency and change matrices, return lags, cumulative event counts, and generic entity-presence episodes.
- Integrated trajectory-only temporal results into atomic-connectivity and framework-topology statistics while keeping ensembles explicitly non-temporal.
- Added gauge-invariant atomic-contact episodes based on `AtomicContactKey` and canonical projected-edge episodes based on `FrameworkEdgeKey`.
- Added explicit left- and right-window censoring flags and a sample-span duration convention for one-frame and multi-frame episodes.
- Advanced atomic and framework topology-statistics serialization schemas to version 2 and retained stable SHA-256 payload validation.
- Validated against the 2,000-frame 300 K Na-LTA catalogs: 72 atomic residence intervals and 71 changed boundaries, but one framework interval and zero framework transitions.
- Added paired Markdown/PDF TS3 specification, implementation audit, public exports, and focused tests.

## 0.17.0a2 - TS2 framework-topology statistics

- Added `mdstats.analysis.topology_statistics.framework` with immutable framework graph descriptors, endpoint-pair counts, whole-path bridge signatures, degree statistics, edge occupancy, and aggregate trajectory-change summaries.
- Added exact per-frame PMFs for vertices, projected edges, components, isolated vertices, self-image edges, parallel edges, and graph cycle-space rank.
- Preserved Stage 2 whole-path orientation identity: complete reversal is equivalent while asymmetric linker order remains distinct.
- Added canonical `FrameworkEdgeKey` occupancy and species-resolved framework-degree statistics evaluated through topology catalog compression.
- Added trajectory-only aggregate projected-edge additions/removals and affected vertex/linker counts without preempting TS3 timelines.
- Validated the implementation against the 2,000-frame 300 K Na-LTA catalog: one topology, 48 vertices, 96 edges, degree four, cycle rank 49, and unit occupancy for all framework edges.
- Added paired Markdown/PDF TS2 specification, implementation audit, public exports, and focused tests.

## 0.17.0a1 - TS1 atomic-connectivity statistics

- Added `mdstats.analysis.topology_statistics.atomic` with immutable atomic contact, degree, occupancy, catalog-diversity, and aggregate trajectory-change statistics.
- Added exact species-pair and total-edge probability mass functions derived once per unique connectivity state.
- Added gauge-invariant `AtomicContactKey` identity so periodic image-gauge changes do not create false contact events or split occupancy records.
- Added per-species degree PMFs, per-frame mean degree, and per-atom population moments without full frame-by-atom expansion.
- Added optional contact-resolved occupancies and trajectory-only aggregate additions/removals grouped by species pair and affected atom.
- Added schema-checked TS1 serialization, SHA-256 payload validation, public exports, and the paired Markdown/PDF TS1 specification.
- Validated the implementation against the 2,000-frame 300 K Na-LTA catalog: 72 states, invariant 96 Si-O and 96 Al-O contacts, Na-O support 110-121, and 40/31 Na-O additions/removals.
- Added focused TS1 tests and updated the topology-statistics architecture and TS0 dependency documentation.

## 0.17.0a0 - TS0 topology-statistics common foundation

- Added `mdstats.analysis.topology_statistics` and the private `_common.py` foundation.
- Added immutable exact discrete count distributions, scalar population summaries, catalog occupancies, Shannon state entropy, and effective state counts.
- Added trajectory-aware visit counts while keeping ensemble occupancy explicitly non-temporal.
- Added immutable frame/sample axes, scalar series, and deterministic state-to-frame descriptor expansion.
- Added schema-checked dictionary serialization, canonical JSON, and stable SHA-256 payload digests.
- Added 22 focused TS0 tests and expanded the complete suite to 344 passing tests with 27 expected warnings.
- Added the TS0 Markdown/PDF specification and integrated the topology-statistics architecture manual into the organized package hierarchy.

## 0.16.0 - Stage 3 exact topology catalog

- Added `mdstats.analysis.topology_catalog` with immutable topology classes, frame groups, trajectory segments, and exact transitions.
- Added catalog and per-frame modes with `UNIFORM`, `PARTITIONED`, and `PER_FRAME` consistency classifications.
- Projected each referenced connectivity state once and reconciled classes by the Stage 2 canonical structural key rather than digest or traversal provenance alone.
- Preserved whole-path orientation identity so complete reverse traversal reconciles while asymmetric linker order remains distinct.
- Added exact atomic-edge and decorated framework-edge transition differences, affected atom/vertex/linker sets, and descriptive transient-segment labels without smoothing.
- Added stable serialization, digest verification, convenience queries, NetworkX delegation, and public package exports.
- Added 26 focused Stage 3 tests, including trajectory, ensemble, LTA, digest-collision, asymmetric-linker, and serialization coverage.
- Expanded the complete regression suite to 322 passing tests with 27 expected warnings.
- Updated the topology-catalog, atomic-connectivity, framework-topology, and framework/ring architecture documents in Markdown and PDF.

## 0.15.0 - whole-path orientation repair

- Repaired `FrameworkPathRule` so endpoint species and linker order are one coupled whole-path pattern.
- Defined reversal equivalence as complete path reversal: `A-O-S-B == B-S-O-A`, while `A-O-S-B != A-S-O-B`.
- Added `OrientedFrameworkEdgePath` and orientation helpers for ring traversal and diagnostics.
- Advanced framework mapping, topology, and visualization adapter schemas to version 2.
- Added asymmetric-linker projection, serialization, reversal, and visualization regression tests.

## 0.14.1 - Semantics-aware neighbor-cache policy

- Added a true `cache_mode="auto"` and made it the high-level default.
- Automatic Verlet reuse now requires a multi-frame `FrameSemantics.TRAJECTORY` selection and an eligible cell-list request.
- Independent ensembles and single-frame selections are stateless by default; explicit `cache_mode="verlet"` remains available as an expert override.
- Added deterministic runtime shutoff after three consecutive completed cache intervals with zero reuse; any successful reuse resets the counter.
- Added frame semantics, cache-resolution reasons, runtime disable reasons, zero-reuse counters, and the configured limit to neighbor-search diagnostics.
- Advanced high-level request and diagnostic schemas to version 2.
- Added ensemble, variable-cell fallback, shutoff, reset, and cross-consumer acceptance tests.
- Updated the periodic-neighbor, internal-neighbor, frame-collection, and deformation-aware cache specifications in Markdown and PDF.
- Expanded the complete regression suite to 289 passing tests.

## 0.14.0 - Stage S4 production periodic-neighbor subsystem

- Added public `NeighborSearchOptions` with deterministic `auto`, `dense`, and `cell_list` selection plus `none` or `verlet` cache modes.
- Integrated one analysis-local exact neighbor executor into RDF, coordination distributions, bond-angle distributions, and distance, hysteretic, and reference atomic connectivity.
- Preserved atomic-connectivity `verlet_cache_options` as a compatibility path while making `neighbor_search_options` the unified interface.
- Added a conservative measured automatic crossover at `32768` estimated dense pair evaluations; users may override the threshold or force a backend.
- Added exact fallback from an unsafe Verlet list radius to stateless cell-list execution and from automatic cell-list complexity to the dense oracle.
- Added unified deterministic provenance for policy choice, actual backends, request digests, candidate efficiency, rebuild/reuse counts, mean and median frames per rebuild, interval margins, singular values, rebuild reasons, and fallback events.
- Added consumer-level dense/cell-list/cache equivalence tests for variable-cell trajectories and all distance-based connectivity definitions.
- Added a reproducible S4 benchmark spanning small and replicated Na-LTA, dense salt, a mixed LTA/salt interface, a skewed cell, and fixed- and variable-cell trajectories.
- Added the normative periodic-neighbor specification in Markdown and PDF and aligned all dependent module specifications.
- Completed the staged S0-S4 plan and promoted the package from `0.14.0a3` to production `0.14.0`.
- Expanded the complete regression suite to 282 passing tests.

## 0.14.0a3 - Stage S3 deformation-aware Verlet reuse

- Added explicit variable-cell reuse through `VerletCacheOptions(deformation_aware=True)` while preserving the fixed-cell S2 default.
- Added affine deformation evaluation with `F = inv(H0) @ Ht` and the smallest singular-value lower bound.
- Added continuous fractional reference coordinates and species-resolved nonaffine displacement maxima.
- Added active species-pair construction and pairwise safety margins `M_AB`.
- Added distinct `cell_deformation_limit`, `nonaffine_displacement_limit`, `fractional_unwrapping_unavailable`, and `nonfinite_deformation_margin` rebuild reasons.
- Added rigid-cell-rotation reuse and explicit configurable cell-condition-number rejection.
- Updated request/cache schemas to version 2 and stored active pair metadata in immutable caches.
- Added variable-cell, adversarial omitted-pair, species-aware, boundary-crossing, rigid-rotation, randomized triclinic, and ill-conditioned-cell tests.
- Expanded the complete regression suite to 272 passing tests with 24 expected warnings.
- Added the S3 normative Markdown/PDF specification and mathematical validity audit.

## 0.14.0a2 - Stage S2 fixed-cell Verlet cache

- Added public `VerletCacheOptions`, `VerletPairCache`, `NeighborCacheStatistics`, and `NeighborSearchSession` objects.
- Added request-keyed immutable candidate caches built by the exact S1 cell list at physical cutoff plus skin.
- Added exact current-frame MIC reevaluation and the conservative fixed-cell rebuild rule `2*d_max >= skin - tolerance`.
- Added periodic boundary-crossing support through reference-relative MIC displacement and conservative rebuild on any cell change.
- Added request-digest invalidation, cache summaries, rebuild reasons, reuse statistics, and candidate/accepted-pair metrics.
- Added opt-in atomic-connectivity caching and one-pass hysteretic/reference nested-threshold classification.
- Added fixed-cell, boundary, threshold, request-change, randomized triclinic, and connectivity-integration tests.
- Added a reproducible fresh-cell-list versus Verlet benchmark and normative S2 specification.
- Kept deformation-aware reuse, RDF/coordination/bond-angle integration, and automatic backend selection deferred to S3-S4.
- Expanded the full regression suite to 259 passing tests.

## 0.14.0a1 - Stage S1 exact triclinic cell list

- Added the explicit private `NeighborSearchBackend.CELL_LIST` backend while retaining `DENSE` as the authoritative oracle and default.
- Added immutable `CellListOptions` with optional lattice reduction, stencil hard limits, and numerical tolerances.
- Added `mdstats/analysis/_cell_list.py` with optional ASE Minkowski reduction, fractional linked cells, perpendicular-height bin heuristics, exact active-set metric-box stencil construction, mixed-PBC traversal, deterministic candidate deduplication, and original-basis MIC evaluation.
- Added cell-list diagnostics reporting bin counts, stencil size, occupied bins, candidate evaluations, and accepted pairs.
- Added dense-equivalence tests for orthogonal, triclinic, highly skewed, mixed-PBC, one-dimensional periodic, nonperiodic, boundary, dense-cluster, multiple-cutoff, permuted-order, and near-safe-cutoff cases.
- Added a reproducible dense-versus-cell-list benchmark and candidate-pruning report.
- Added the normative S1 cell-list backend specification and updated the internal neighbor specification and staged implementation plan.
- Kept trajectory caching, Verlet skins, deformation-aware reuse, automatic backend choice, and consumer-level integration deferred to S2-S4.
- Expanded the full regression suite to 244 passing tests.

## 0.14.0a0 - Stage S0 dense oracle

- Made the blocked dense neighbor implementation explicit through the private `NeighborSearchBackend.DENSE` selection.
- Refactored `build_neighbor_list()` into a stable backend facade and a dedicated dense implementation without changing scientific output.
- Added backend provenance and defensive read-only arrays to `NeighborListResult`.
- Added canonical neighbor-result sorting, structured comparison reports, and exact oracle assertions covering CSR grouping, pair identity, periodic image shifts, vectors, and distances.
- Added deterministic random geometry fixtures for orthogonal, triclinic, mixed-PBC, and boundary-crossing cases.
- Added an independent scalar pair-loop oracle and block-size/repeated-run equivalence tests.
- Added a reproducible dense baseline benchmark and machine-specific runtime/peak-memory report.
- Added the staged cell-list and Verlet-cache plan to package documentation and marked S0 complete.
- Updated and regenerated the internal neighbor specification.
- Expanded the full regression suite to 221 passing tests.

## 0.13.1

- Added the public `NodeDisplayMode` enum with `markers`, `dots`, and `hidden` modes.
- Added renderer-shared `GraphStyle.node_display_mode` and `node_dot_size` fields.
- Added compact color-coded framework vertices through `GraphStyle.framework_default(node_display_mode="dots")`.
- Added edge-only framework views through `GraphStyle.framework_default(node_display_mode="hidden")`.
- Suppressed node artists, periodic ghost markers, node labels, node legends, and Plotly node traces in hidden mode while preserving scientific node keys and edge geometry.
- Added focused 2-D and 3-D tests and Na-LTA compact/edge-only acceptance artifacts.
- Updated and regenerated the graph-style, 2-D renderer, 3-D renderer, framework-adapter, and visualization-index specifications.
- Expanded the full regression suite to 205 passing tests.

## 0.11.0

- Added renderer-independent periodic graph materialization through `PeriodicGraphView` with canonical-cell, local-unwrapped, and expanded-cell display modes.
- Added stable display keys, explicit canonical/replica/ghost node roles, explicit primary/replica/boundary-ghost/cycle-ghost edge roles, and source-to-display mappings.
- Centralized deterministic periodic image assignment and residual winding handling so the 2-D and 3-D backends share one periodic-display contract.
- Added the optional Plotly `plot_decorated_graph_3d()` backend with interactive rotation, hover metadata, endpoint-colored edges, triclinic cell wireframes, equal-aspect scenes, and standalone HTML export.
- Added `plot_atomic_connectivity_3d()` and `plot_connectivity_transition_3d()` convenience wrappers without introducing a second scientific adapter path.
- Added an explicit `periodic=` path to the 2-D renderer while preserving the 0.10.0 compatibility options.
- Added lazy optional-dependency handling through the `interactive` extra; importing `mdstats` does not require Plotly.
- Added canonical-cell, local-unwrapped, expanded-cell, directed/multigraph guard, hover, HTML-export, and optional-dependency tests.
- Added an interactive Na-LTA acceptance gallery covering canonical, orthographic, local, expanded 2x2x1, and framework-plus-Na views.
- Refactored and audited the visualization documentation into per-module Markdown/PDF specifications.
- Expanded the full regression suite to 183 passing tests.

## 0.10.0

- Added the public immutable `DecoratedGraphView` adapter model with stable node and edge keys, validated columnar metadata, optional physical coordinates, periodic shifts, cell, and PBC information.
- Added explicit graph focus, attribute/key filters, complexity reports, and no-silent-sampling safeguards.
- Added reusable chemical palettes, node/edge styles, deterministic metadata rules, labels, and atomic/transition presets.
- Added deterministic physical Cartesian/PCA projections and NetworkX spring, circular, and shell schematic layouts.
- Added the public Matplotlib `plot_decorated_graph_2d()` renderer with batched artists, endpoint-colored edges, legends, labels, PNG/SVG/PDF export, and traceable render metadata.
- Added atomic-connectivity state and transition adapters plus `plot_atomic_connectivity_2d()` and `plot_connectivity_transition_2d()` convenience functions.
- Added frame-consistent periodic display-shift reconstruction without re-evaluating connectivity.
- Added deterministic local periodic node unwrapping and faded display-only ghost endpoints while preserving residual winding and scientific graph identity.
- Added the relaxed Na-LTA POSCAR as a system-integration fixture. The framework test verifies 144 Si/Al/O atoms, 192 T-O edges, degree four on all T sites, and degree two on all framework oxygen atoms.
- Added a reproducible Na-LTA visualization gallery and graph-visualization API/specification audit.
- Expanded the full regression suite to 170 passing tests.

## 0.9.0

- Added the public `atomic_connectivity` module for periodic atomic graph states.
- Added persistent identity-based `ConnectivityScope` selection.
- Added instantaneous, hysteretic, reference-based, and explicit connectivity definitions.
- Added canonical periodic gauge normalization, stable SHA-256 structural digests, and immutable state arrays.
- Added uniform, partitioned, and per-frame state organization.
- Added trajectory connectivity segments and exact added/removed atom-pair transitions.
- Extended the shared neighbor kernel with integer periodic image shifts while preserving RDF, coordination, and bond-angle results.
- Made `PairCutoff` provenance and `PairCutoffRegistry` mappings deeply immutable.
- Added focused tests for scope resolution, triclinic image shifts, gauge invariance, hysteresis, reference ensembles, winding information, serialization, and catalog compression.

## 0.8.0

- Added `PairCutoff` and `PairCutoffRegistry` for auditable, reusable neighborhood definitions.
- Added a private CSR-style shared neighbor kernel with blocked minimum-image geometry, strict cutoffs, deterministic row grouping, and triclinic support.
- Migrated pair RDF and coordination-number distributions onto the shared neighbor system.
- Consolidated coordination cutoff provenance into `CoordinationResult.pair_cutoff`.
- Added `compute_bond_angle_distribution()` with symmetric and asymmetric triplets.
- Added exact/range and combined-species central coordination filters.
- Added angle-, center-, and frame-weighted angle distributions, optional raw angles, and optional per-frame descriptors.
- Added focused cutoff, neighbor, angle, periodic-boundary, triclinic, counting, and filter tests.

## 0.7.0

- Added direct, blocked-FFT, and automatic backends to `compute_msd()`.
- Added a shared internal FFT planning and positive-lag correlation layer used by MSD and VACF.
- Preserved the direct MSD estimator as the numerical reference implementation.
- Added memory-aware atom blocking for long time-averaged MSD calculations.
- Added stable per-atom coordinate centering before the FFT to reduce cancellation from large unwrapped coordinates.
- Added backend, FFT length, block size, and coordinate-centering provenance to MSD result metadata.
- Added direct-versus-FFT equivalence tests for scalar, component, tensor, per-atom, variable-cell, drift-corrected, odd/even, and large-offset trajectories.
- Added an internal FFT utility specification and focused primitive-level tests.
- Audited and synchronized the MSD and VACF specifications with the implemented 0.7.0 APIs and backend behavior.

## 0.6.0 - 2026-07-11

- Added `compute_vacf()` and the raw weighted `VACFResult` data model.
- Added direct and atom-blocked FFT self-correlation backends.
- Added uniform, mass, and explicit atom weighting.
- Added scalar, Cartesian-component, full-tensor, directional, and optional per-atom VACF outputs.
- Added explicit drift removal, trajectory capability guards, and velocity-provenance warnings.
- Added the VACF API and algorithm specification.

## 0.5.0

### Breaking API change

- Replaced `MDTrajectory` with `AtomisticFrameCollection`.
- Replaced `TrajectoryProvenance` with `FrameCollectionProvenance`.
- Replaced `read_lammps_trajectory()` with `read_lammps_frames()`.
- Replaced `read_vasp_trajectory()` with `read_vasp_frames()`.
- Renamed the canonical coordinate field to `fractional_positions`.
- Removed all backward-compatibility aliases.

### Added

- Explicit `FrameSemantics.TRAJECTORY` and `FrameSemantics.ENSEMBLE`.
- Multi-frame independent ensembles without velocities or required times.
- `read_structure_collection()` for multi-file static ensembles.
- Direct ensemble mode for VASP and LAMMPS frame readers.
- `select_frames(..., frame_semantics="ensemble")` and `as_ensemble()`.
- Central temporal-analysis guards and descriptive exceptions.
- Stable `frame_ids` and parent-frame provenance for future clustering and
  active-learning selection.

### Behavioral changes

- Trajectory coordinates are time-unwrapped.
- Ensemble coordinates are wrapped independently in each frame.
- Native velocities are discarded for ensemble semantics.
- MSD rejects ensembles even when source time labels are present.
- RDF and coordination accept trajectories, ensembles, and single structures.

## Documentation audit revision - 2026-07-11

- Audited structural modules against Markdown and PDF specifications.
- Corrected ordinary coordination's unique-species constraint.
- Corrected RDF diagnostic-warning and shared-neighbor ownership descriptions.
- Documented exact dataclass defaults and implemented result/helper methods.
- Clarified explicit bond-angle bin validation and symmetric endpoint-selection constraints.
- Regenerated and render-verified all affected PDFs.
- No numerical source behavior changed; package version remains 0.8.0.

### Stage 11 architecture revision 47

- Require provenance metadata on every thermodynamic result and make independent cross-checks optional verification.
- Split density-derived, force-integrated, and PMF-crosscheck products.
- Add kinetic model-selection/fit/validation partitions and a zero-event rate-candidate edge universe.
- Assign final candidate freezing to GR4 and add source-bundle/model-generation records.
- Upgrade the Stage 11 DAG to typed dependency edges and split E8b product gates.
