# Part VI - Performance and execution architecture

## Performance objective

Optimization is accepted only when it preserves scientific authority and improves measured throughput, memory behavior, or restart cost. CPU percentage is diagnostic rather than the objective. In particular, memory-bound sparse kernels may be optimal below the nominal CPU occupancy target.

For a stage allocated $P$ CPU lanes, define effective occupancy over a bulk interval as

$$
U_P = \frac{\Delta t_{\mathrm{CPU}}}{P\,\Delta t_{\mathrm{wall}}}.
$$

When at least $2P$ independent compute tasks are ready and the kernel is compute-bound, the target is sustained $U_P\gtrsim0.85$ with automatic resource use capped by the configured campaign CPU fraction (90% by default). Throughput and wall time decide between exact-equivalent implementations.

## Work/span model and global scheduling

The campaign adopts a task-parallel work/span view. Let $T_1$ be serial work and $T_\infty$ the critical path. Ideal scheduling cannot beat

$$
T_P \ge \max\!\left(\frac{T_1}{P},T_\infty\right).
$$

Classical work-stealing analysis motivates exposing many independent tasks to a common scheduler; for structured computations, the expected execution bound has the form $T_1/P+O(T_\infty)$ [32]. mdstats does not require a literal Cilk runtime, but adopts the same **work-conserving principle**: idle lanes take ready work from any compatible family/profile/domain instead of waiting for a local loop to finish.

### Single-level parallelism

The default CPU realization SHALL expose parallelism at the highest level that provides enough independent tasks. Nested numerical parallelism is suppressed while the outer queue is populated:

$$
P_{\mathrm{outer}}\times P_{\mathrm{native}}\le P_{\mathrm{budget}},
$$

with $P_{\mathrm{native}}=1$ for cKDTree/BLAS/OpenMP calls when outer parallelism can fill the budget. This avoids oversubscription and the underfilled `one Python driver + briefly threaded native call` pattern observed before FEAS1-PERF3.

Libraries such as `threadpoolctl` can limit BLAS/OpenMP pools, but their controls are process-global and have caveats when manipulated from several Python threads [35]. The scheduler therefore treats native-thread configuration as a stage/resource-scope concern, not something each arbitrary worker toggles independently.

## PARCORE1 - shared deterministic scheduler

`PARCORE1` is implemented in `mdstats 0.20.226a0`. The reusable queue class is `DeterministicWorkQueue`; it is now the common substrate for CPU-heavy independent work. Its execution contract provides:

- `StageResourceScope` CPU and RAM integration;
- separately bounded ready, submitted/in-flight, and completed queues;
- work-conserving dispatch across profiles/families/domains;
- deterministic ordered reducers for FP-sensitive authorities;
- native-thread quarantine when the caller supplies the explicit campaign resource scope;
- exception propagation with deterministic task identity;
- memory-weighted admission/backpressure plus explicit persistent-memory reservations;
- progress/heartbeat snapshots including ready, in-flight, completed, busy-lane, memory, and backpressure state;
- locality/NUMA metadata that does not enter scientific identity.

The executor owns exactly `StageResourceScope.python_workers` executing threads. The queue MAY keep more submitted futures than executing lanes (the current FEAS1 realization permits up to twice the worker count) so an idle worker can immediately pull the next admitted task without waiting for coordinator hand-off. This does not increase the number of simultaneously executing Python lanes and does not authorize nested native parallelism.

Task completion may be out of order; `DeterministicOrderedReducer` commits authoritative FP64 reduction only in the prescribed canonical order whenever arithmetic order is part of exact-equivalence authority. FEAS1 is the first migrated consumer and retains its historical witness-block commit order exactly. Its parallel cKDTree tasks continue to use one native tree worker while the outer queue is populated.

Campaign execution passes an explicit `StageResourceScope`, so native BLAS/OpenMP limits are applied once by the queue-owning coordinator rather than toggled inside workers. Bare library/API calls that do not supply an explicit scope preserve their historical resource-control semantics; the scientific output is identical in either realization. `StageResourceScope.ram_budget_bytes` is execution-only and feeds queue admission.

Locality keys are stored now so future NUMA-aware scheduling can reuse the task model. PARCORE1 does **not** activate NUMA affinity or node-local stealing; those remain measurement-gated execution extensions.

## NEIGHBOR1 - exact neighborhood production and reuse

`NEIGHBOR1` is implemented in `mdstats 0.20.227a0`. `ExactNeighborhoodEngine` is the single exact TARGET-DATA2B/C geometric implementation. Query blocks from all eligible families enter the PARCORE1 queue; while outer work is available, every cKDTree task uses one native worker [33]. The frozen scaled-Euclidean radius/tolerance semantics and candidate-frame deduplication order are unchanged.

As soon as a completed block becomes reducible in canonical witness order, FEAS1 now:

1. applies the historical support/capacity reduction in the same FP64 order;
2. appends the same exact row relation to a disk-backed canonical witness-oriented CSR stream;
3. releases the ragged temporary neighbor object.

Thus peak ragged-neighborhood memory scales approximately with active/buffered blocks rather than the complete family:

$$
M_{\mathrm{ragged}} = O(PB\bar d),
$$

where $B$ is query-block size and $\bar d$ is mean neighborhood degree. The final CSR uses `uint64` witness offsets and `uint32` candidate indices. Its exact final allocation is known from streamed row counts/edge count and is admitted against `StageResourceScope.ram_budget_bytes` **before** materialization into RAM.

The cache is reconstructible execution state rather than a new scientific authority. Family identity binds label-domain ID, frame-domain/candidate ordering digest, family digest, candidate/witness cardinalities, frozen metric/tolerance semantics, and cache-format version. Worker count, query-block size, queue depth, timing, and progress settings are deliberately excluded. Native persistence authenticates manifests and each NumPy array by checksum plus scientific array reference; campaign storage records the cache independently of FEAS1 so restart may validate/reuse it.

MVIDX1 adopts authenticated forward CSR directly and performs no geometric query on a cache hit. `target_coverage_sparse_index.py` no longer owns a cKDTree/query-ball implementation. If the cache is missing, corrupt, or stale, MVIDX1 rebuilds forward CSR once through the same global `ExactNeighborhoodEngine`, persists it, and then proceeds. It must never revive the former duplicate serial-family/nested-tree geometry sweep.

`MVIDX-REUSE1` (`0.20.228a0`) parallelizes the remaining inverse/metadata work at the natural independent-component boundary. Required-family inversions and hard-obligation inversion are immutable tasks on `DeterministicWorkQueue`; each task uses the deterministic compiled SciPy CSR-to-CSC counting transpose with one native lane, and canonical required-family order is restored after completion. This avoids nested sparse-kernel parallelism and atomics while allowing the outer queue to occupy the campaign CPU budget. An experimental Python-threaded intra-family degree/prefix/range-fill realization was exact but slower on the frozen authority and was therefore rejected rather than promoted.

The prior row-by-row strict-order validator was also a measured MVIDX hotspot. Revision 95 replaces it with one vectorized adjacent-index comparison and masks pairs crossing CSR row boundaries. The predicate is mathematically identical: every within-row adjacent pair must remain strictly increasing; worker count and queue completion order remain execution-only.

## COVREF-PAR1 - exact reference-radius block scheduling

`COVREF-PAR1` (`0.20.229a0`) removes the remaining one-driver/native-tree pattern from TARGET-DATA2B reference-radius construction. Each family still computes the identical robust scales, scaled coordinates, balanced reference masses, and exact leave-one-out local radius. The scaled matrix and one read-only `cKDTree` are constructed once per family; independent row blocks are then submitted to the stage-wide `DeterministicWorkQueue`, and every task calls the tree with `workers=1`. Results write to disjoint canonical row slices, so task completion order cannot alter the local-radius array. Direct API calls that omit `execution_scope` retain the historical native-tree `query_workers` realization for compatibility and oracle comparison.

Parallel block size is execution-only. The configured `radius_block_size` remains an upper bound, while the queue may reduce it to keep the estimated cKDTree temporary working set near 2 MiB and expose at least four blocks per assigned lane on sufficiently large families. This is especially important for 30k-40k-frame target domains: a fixed 1024-row block would expose only about 36 tasks and develop a large tail on a 28-lane workstation. Block boundaries are not scientific inputs; qualification requires byte-identical radii across block/worker schedules.

The family-adaptation path is also hardened without changing inclusion rules. Pair-geometry records are indexed once by `(frame_uid, rule_id)`, foundation species residuals once by `(frame_uid, atomic_number)`, and target-label scalar channels execute the exact historical `np.allclose` constant-family rejection before robust-statistic/tree work instead of after it. Weight-profile caching remains content-derived execution state, and scaling is materialized once per family and shared read-only by radius tasks.

The campaign resolves TARGET-DATA2B construction workers separately from later coverage-scoring native-tree widths. Automatic COVREF uses the complete configured CPU budget as outer lanes; `StageResourceScope` fixes `tree_workers=1` and `blas_threads=1`, making $P_{\mathrm{outer}}\times P_{\mathrm{native}}=P_{\mathrm{outer}}$ and preventing nested oversubscription.

Direct FEAS1, NEIGHBOR1-rebuild, and MVIDX inversion API calls that do not supply a `StageResourceScope` likewise retain historical host-independent execution semantics: their implicit scopes do not synthesize hard RAM ceilings from momentary shared-host/cgroup free-memory readings. Campaign execution, which owns the resource contract, continues to pass explicit RAM-bounded scopes and therefore remains fail-closed under declared memory limits. This distinction prevents transient unrelated host load from turning an otherwise identical direct scientific call into a scheduler-admission failure.

## Memory budget and persistence

CPU admission is necessary but insufficient. The scheduler SHALL track an estimated memory budget

$$
M_{\mathrm{stage}} =
M_{\mathrm{trees}}+M_{\mathrm{scaled}}+M_{\mathrm{inflight}}+
M_{\mathrm{buffered}}+M_{\mathrm{sparse}}+M_{\mathrm{scratch}}.
$$

New work is admitted only if both CPU and memory budgets permit it. Completed sparse blocks may spill to mmap-compatible uncompressed arrays so neighborhood reuse does not require retaining the complete graph in Python objects. Compression is optional and must be benchmarked because decompression can erase the saved neighborhood-search time.

## NUMA-ready locality

A flat work queue is appropriate for the single-socket workstation but can inflate work on multi-socket EPYC/HPC nodes through remote-memory traffic and cache loss. NUMA-aware task runtimes explicitly address this locality problem [36]. PARCORE1 therefore reserves a locality extension:

- node-local queues and data shards;
- worker affinity to the owning NUMA node;
- local stealing first;
- cross-node stealing only to avoid idle lanes.

NUMA mode is execution-only and will be activated only after measured qualification on a suitable host.

## Vectorization and exact numerical kernels

The optimization program prefers array kernels that replace repeated Python object traversal without changing arithmetic authority.

### Ragged sparse gather

MVSEL/MVQUAL SHALL replace Python `list-of-slices -> concatenate -> repeat` patterns with offset-derived vectorized CSR gathers. Candidate/witness ordering is retained exactly.

### Bounded-integer reductions

Species IDs, candidate IDs, and other bounded non-negative integer labels SHOULD use direct indexed reductions such as `numpy.bincount` when the semantic operation is counting or weighted summation [37]. This replaces repeated `unique + boolean mask` scans in FOUNDATION-AUDIT1, EVAL2, and sparse telemetry.

### Stamp-array membership

REPAIR1 repeated set intersections SHOULD use epoch/stamp arrays for bounded witness IDs:

$$
\mathrm{overlap}(j)=\mathbf 1[\mathrm{stamp}[j]=e],
$$

#### REPAIR-PAR1 realized proposal kernel

`REPAIR-PAR1` retains the sequential repair iteration and canonical winner authority. For each immutable iteration state, fused removal metrics scan each sparse family once; replacement frontiers are scored with canonical ragged-CSR gathers and thread-private epoch/stamp arrays rather than repeated `intersect1d`/`isin` calls. An inverse candidate-rank map replaces repeated linear future-rank searches. Proposal tasks may execute through PARCORE1 only when an execution-only sparse-edge work estimate exceeds the measured break-even threshold; smaller rungs remain serial. Completion order is never authoritative: proposal results are reduced in the historical removal-shortlist order using the unchanged objective/tie hierarchy. The selected replacement's representative contribution is recomputed by the historical scalar arithmetic before persistence, preserving the complete repair trace exactly. Worker count, adaptive threshold, queue depth, and stamp epochs are execution state and do not enter content identity.


where the current removed-witness set is stamped with epoch $e$. This turns repeated sorting/intersection work into direct indexed gathers.

### Batched resampling/statistics

Independent bootstrap replicates and repeated quantiles SHOULD be processed in bounded vectorized batches. Static composition/species codes and other invariant indexing metadata are computed once per dataset/checkpoint domain and reused.

`AUDIT-EVAL-PERF1` applies this contract to EVAL2 with an execution-only bounded metadata cache keyed by the in-memory immutable evaluation view plus ordered correlation-block IDs. The cache stores precomputed composition keys, per-frame species membership, focus masks, and block codes; it does not enter target-role or prediction scientific identity. Paired bootstrap preserves the exact seeded draw stream while grouping draws into a temporary-memory-bounded matrix batch. FOUNDATION-AUDIT1 similarly shares one immutable DATA3 frame index and per-run species-membership map across audit domains and continues to read/authenticate the existing prediction sweep rather than invoking the foundation model.

### Lookup and allocation hygiene

Hot loops SHALL avoid repeated linear `next(...)` searches, rebuilding immutable dictionaries/maps, repeated full-array scaling, unnecessary `concatenate`, and materializing Python objects when contiguous typed arrays suffice. Optimization reviews explicitly look for these patterns.

## Stage-specific optimization map

| Stage | Dominant issue | Planned exact optimization |
|---|---|---|
| TARGET-DATA2B reference-radius/coverage | serial block driver with nested cKDTree workers | global block tasks, one tree worker/task, early constant-family rejection, shared scaled workspaces |
| FEAS1 | global PARCORE1 queue plus implemented streamed exact CSR | retain exact reduction; downstream sparse-kernel work only |
| MVIDX1 | authenticated graph adoption; inverse/validator Python overhead | implemented MVIDX-REUSE1 component-level queue plus vectorized CSR validation |
| MVSEL1 | Python ragged gathers and sparse update overhead | vectorized CSR gather, indexed weights, incremental counters; preserve sequential rank authority |
| REPAIR1 | serial proposal shortlist and repeated intersections | implemented adaptive immutable-state proposal queue, vectorized frontier scoring, stamp arrays, fused sparse scans, O(1) rank map |
| MVQUAL1 | independent same-N rescoring globally queued | PARCORE1 same-N jobs + batched sparse telemetry; canonical post-queue reduction |
| FOUNDATION-AUDIT1 | per-frame/species Python reductions | implemented shared frame/species metadata, reused squared-error work, batched tail quantiles; no new inference |
| EVAL2 CPU analysis | repeated species/composition/focus reconstruction and bootstrap Python loops | implemented cached static reduction metadata, preallocated tails, memory-bounded batched bootstrap |
| REPLAY-UNIFY1 | repeated serial ExtXYZ parsing/materialization | implemented source-SHA-bound byte-offset/natoms index; direct sparse seeks; deterministic bounded chunk parsing |

Existing DATA6 GPU inference, training orchestration, structural FPS/GEMM kernels, and independent trajectory verification are not rewritten merely to increase thread count; they are changed only if runtime profiling identifies a new dominant hotspot.

### REPLAY-PERF1 indexed replay realization

The selected replay ExtXYZ remains the only external replay authority. `ReplaySourceIndex` is reconstructible execution state keyed by the exact source bytes and source-artifact/source-order identities; it is never a substitute scientific authority. The index records frame byte offsets, byte lengths, and atom counts, allowing a requested subset such as the 2,000-frame monitor role to seek directly to those source frames. For a complete source traversal, contiguous frames are parsed in bounded chunks and their already-authenticated source-order geometry identities are reused. Parser chunk size is execution state and MUST NOT enter replay source, split, label, prediction, or view content identity.

ASE ExtXYZ parsing remains serial. REPLAY-PERF1 qualification explicitly tested thread-parallel chunk parsing and found it slower on the available CPU, so concurrency is not introduced merely to increase worker count. Future campaign-level parallelism MAY overlap independent higher-level consumers only if a later profile shows a net gain without changing persisted replay bytes or prediction authority.

## CAMPAIGN-PERF-QUAL1 integrated reprofile and shifted bottleneck

The revision-102 closure profile validates cumulative behavior instead of inferring campaign speed from isolated kernel benchmarks. On a common 8,192-candidate/six-family target-data chain, untouched `0.20.225a0` completes FEAS1 -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVQUAL1 in about 27.26 s. The optimized realization through `0.20.234a0` completes the same scientific chain in a four-lane median of about 11.95 s (~2.28x faster) with exact output digests. Current one/two/four-lane wall times are about 12.91/12.07/11.95 s, so additional outer lanes no longer provide material end-to-end scaling on the qualification CPU.

The remaining four-lane wall-time composition is approximately 45% REPAIR1, 41% MVSEL1, 9% FEAS1 plus neighborhood production, 4% MVQUAL1, and less than 1% MVIDX1. Profiling shows the selector rank-choice routine itself is no longer dominant: 4,096 `_choose_candidate` calls consume about 0.90 s cumulative, while 4,096 exact `_select_and_update` calls consume about 5.20 s, including about 4.57 s in ordered paired sparse decrements.

REPAIR1 exposes a stronger exact-reuse opportunity. On the same fixture it executes about 4,098 additional `_select_and_update` calls (about 5.34 s cumulative in the profile) to reconstruct the already-known selector sparse state before and during repair preparation. Proposal work is materially smaller. This reconstruction is not a new scientific decision; it is deterministic state derivable from the MVIDX authority plus the ordered MVSEL selection. `MVSTATE-REUSE1` therefore becomes the next exact-equivalence gate: persist/authenticate enough terminal selector execution state for REPAIR1 to start from that state directly, while retaining the historical replay path as the qualification oracle.

The closure accepts a modest representative peak-RSS increase (about 306 MiB -> 343 MiB) because it is caused by reusable authenticated sparse execution state, remains far below the explicit campaign budget, and produces no observed queue backpressure. Performance evidence never overrides scientific digests.

## MVSTATE-REUSE1 exact selector-state handoff and CPU closure

Revision 103 implements an authenticated `TargetMultiViewSelectionStateCache` at the MVSEL/REPAIR boundary. MVSEL snapshots the exact mutable selector state at every materializable rung. REPAIR may restore such a checkpoint only while repair has not diverged from the pure selector order. After the first accepted repair swap, the historical mutable repair state is carried forward. This restriction is normative: reconstructing a later repaired state from a pure MVSEL checkpoint plus selected-set differences changed FP64 representative-gain entries by about `1e-17`--`1e-16`, so that shortcut is rejected even though selected IDs were identical.

The cache is reconstructible execution state. Identity binds the reference/MVIDX/MVSEL/policy/sparse-kernel lineage and excludes worker/storage choices. Persistence uses one authenticated uncompressed NPZ array bundle plus a canonical manifest. A fresh campaign passes the in-memory cache directly from MVSEL to REPAIR and persists the same cache for restart; stale, missing, corrupt, or incompatible state falls back to exact historical replay. Post-divergence predetermined additions may batch CSR gather preparation, but candidate-major FP64 mutations remain in the historical order and are state-array qualified.

On the 8,192-candidate/six-family integrated fixture, untouched 0.20.235a0 has a target-chain median near 12.00 s and REPAIR near 5.37 s. MVSTATE-REUSE1 gives about 11.02 s excluding persistence and 4.27 s for REPAIR. The one-time state-cache write is about 0.18 s, yielding a fresh-chain time near 11.19 s and a cumulative speedup of about 2.44x relative to the 27.26 s PERFBASE1-era chain. Peak RSS increases about 5.6% because exact rung state is retained, while remaining far below campaign limits.

The post-gate reprofile finds no further material duplicated reconstructible CPU state: MVSEL and REPAIR are now dominated by the exact sequential sparse-state update arithmetic itself. The CPU optimization program is therefore closed. Further accelerator/runtime qualification belongs to `FINAL-GPU1`.

## Progress and observability contract

Every stage expected to run long enough to appear stalled SHALL expose three layers:

**Scientific progress**

- completed/total domains, profiles, families, blocks, configurations, witnesses, or edges as appropriate;
- global percentage and ETA.

**Executor state**

- busy/allocated workers;
- ready, in-flight, and buffered tasks;
- memory-budget use where measurable.

**Current hot items**

- identities of slow/active families, shards, or proposals;
- local progress for a long single item.

A heartbeat is emitted even when no task completes during the reporting interval. ETA is based on global committed work, not one current profile.

### MLFF progress presentation grammar

As of `0.20.237a0`, every user-facing MLFF progress/heartbeat message SHALL use the same presentation grammar. This is presentation state only and SHALL NOT enter scientific digests or execution-cache identity.

- Dynamic progress fields appear in the order `status`, `progress`, `elapsed`, `eta`, rate fields, then stage-specific telemetry.
- `elapsed` and known `eta` SHALL be fixed-width `HH:MM:SS`; durations longer than 99 hours retain all hour digits. Unknown/not-yet-estimable ETA SHALL be exactly `--:--:--`. Humanized alternatives such as `39m44s`, `27.9 min`, `10s`, or `estimating` are forbidden in MLFF progress output.
- Counted work SHALL use `progress=completed/total (percent%)`, with thousands separators for large counters. A stage without a meaningful total SHALL report `status=phase; phase=...` rather than inventing a percentage.
- Throughput SHALL carry an explicit stable unit such as `frame/s`, `witness/s`, `task/s`, or `edge/s`. When both are available, the recent/current rate precedes the cumulative average rate.
- Fields SHALL be semicolon-delimited. Stage prefixes such as `[DATA6 sweep]`, `[TRAIN run-id]`, or `[EVALUATION scheduler]` identify the emitter but do not replace the canonical fields.
- Scheduler heartbeats SHALL report the same elapsed/ETA grammar and expose completed progress plus active/pending/queue telemetry rather than using a separate prose-only dialect.
- Cache restoration, phase transitions, and rung events use the same `status=...; progress=...` or `status=phase; phase=...` vocabulary where applicable.

The shared helpers in `mdstats.training_data.progress_timing` own duration, fraction, rate, and timing-field formatting so individual stages do not reintroduce private ETA dialects.

## Performance qualification

Every performance gate is measured at worker counts $1$, $2$, a bounded intermediate count, and automatic full budget. The qualification record includes:

- wall time and CPU time;
- effective occupancy $U_P$;
- throughput in domain-appropriate units;
- peak RSS and persisted bytes;
- queue occupancy/backpressure telemetry;
- output/content digest;
- exact scientific-record equality.

For MVSEL, equivalence is checked after every selected rank on bounded fixtures. For REPAIR, the entire accepted/rejected swap trace is compared. For MVIDX, every CSR/CSC offset and index array is compared between reuse and full-rebuild paths.

### PERFBASE1 frozen baseline authority

`PERFBASE1` is implemented as a measurement-only, versioned record. Scientific-output identity is separated from execution telemetry so later exact-equivalent implementations may change wall time, CPU occupancy, memory layout, worker count, and queue behavior without changing the scientific baseline digest. The record binds the foundation family/variant/checkpoint SHA-256 as an input identity but does not encode MPA-0-specific behavior; MH-1 and other supported foundations use the same record contract.

The revision-92 CPU evidence uses the supplied LTA target archive and unified 12,000-frame replay source plus deterministic synthetic FEAS1/MVIDX1/MVSEL1 workloads. The supplied TARGET-DATA2B radius workload is a fixed 4,100-frame, eight-family representative cache spanning low/high temperature and hydrostatic strain; the complete 27-file target archive is authenticated separately. On the qualification host the automatic CPU budget is three lanes, so the bounded-intermediate schedule aliases the two-lane schedule. Stages that are serial in the current implementation record the requested schedule separately from actual allocated lanes rather than reporting fictitious parallelism.

The canonical evidence is `benchmarks/mlff_perfbase1_lta_cloud_cpu_mpa0_2026-08-17.{json,md}`. All repeated trials preserve exact scientific-output digests. The active MPA-0 medium checkpoint is bound by SHA-256 `75428afe3a1d...fb493e38604fb638`. MACE model inference is not claimed on the cloud host because that runtime was not part of the authoritative measurement environment; Foundation Audit/EVAL2 inference baselines remain explicitly unavailable there rather than being synthesized.

### Multi-billion-edge MVIDX out-of-core hardening

As of `0.20.238a0`, campaign MVIDX MUST NOT require the complete candidate-to-witness inverse edge payload plus full-family SciPy transpose workspace to coexist in anonymous RAM. When the inverse payload for a family exceeds the execution threshold, MVIDX performs deterministic source-row chunk transposes, appends each candidate column in ascending source-row chunk order, and writes the exact `<u4` candidate-witness array directly to an NPY memmap. Candidate offsets remain canonical `<u8`. Chunk size and concurrent family count are execution-only and are admitted under the explicit `StageResourceScope` RAM budget. The out-of-core result SHALL be byte-identical to the in-memory deterministic transpose.

Whole-array NPY memmaps may be hard-linked into the native MVIDX record when source and destination share a filesystem; this is persistence reuse, not scientific identity. The campaign SHALL reload the durable native record before transient build paths are removed. Required inverse disk capacity is preflighted from exact edge cardinality, and MVIDX reports canonical `HH:MM:SS` elapsed/ETA heartbeats during long inversion.
