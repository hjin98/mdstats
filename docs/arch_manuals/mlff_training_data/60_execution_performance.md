# Part VI - Performance and execution architecture

## Performance objective and authority

Execution optimization is accepted only when it preserves scientific authority and improves measured throughput, memory behavior, or restart cost. CPU/GPU utilization is diagnostic rather than scientific authority. Memory-bound sparse kernels may be optimal below nominal occupancy targets.

For a stage allocated $P$ CPU lanes, effective occupancy over a bulk interval is

$$
U_P = \frac{\Delta t_{\mathrm{CPU}}}{P\,\Delta t_{\mathrm{wall}}}.
$$

When sufficient independent compute tasks exist and the kernel is compute-bound, automatic execution targets high sustained occupancy while respecting the configured CPU/RAM/GPU/VRAM ceilings. Throughput and wall time decide among exact-equivalent realizations; scientific digests and authoritative records decide correctness.

Worker count, queue depth, query-block size, storage path, cache location, and other execution-only choices SHALL NOT enter scientific identity unless the value changes a declared scientific algorithm.

## Work/span model and single-level parallelism

The campaign follows a task-parallel work/span model. With serial work $T_1$ and critical path $T_\infty$,

$$
T_P \ge \max\!\left(\frac{T_1}{P},T_\infty\right).
$$

Independent work is exposed at the highest level that supplies enough tasks. Nested numerical parallelism is suppressed while the outer queue can fill the budget:

$$
P_{\mathrm{outer}}\times P_{\mathrm{native}}\le P_{\mathrm{budget}}.
$$

For cKDTree, BLAS, OpenMP, and similar native kernels, campaign execution normally uses one native lane per task when outer work is sufficient. Native-thread configuration is owned by the stage/resource scope rather than toggled independently inside arbitrary workers.

## Shared deterministic CPU scheduler

`DeterministicWorkQueue` is the common substrate for CPU-heavy independent work. Its current execution contract provides:

- explicit `StageResourceScope` CPU and RAM ownership;
- separately bounded ready, submitted/in-flight, and completed work;
- work-conserving dispatch across compatible profiles, families, domains, or jobs;
- deterministic task identities and exception propagation;
- deterministic ordered reducers where authoritative FP64 reduction order matters;
- memory-weighted admission/backpressure and explicit persistent-memory reservations;
- queue/executor heartbeat telemetry;
- locality metadata that does not enter scientific identity.

The executor owns exactly the executing Python lanes admitted by the resource scope. It MAY retain more submitted futures than executing lanes to hide coordinator hand-off latency, but simultaneously executing work remains bounded by the resource scope and does not authorize nested oversubscription.

Task completion may be arbitrary. Whenever arithmetic order is part of exact-equivalence authority, authoritative state is committed only in the prescribed canonical order.

Bare library/API calls that do not receive an explicit campaign scope preserve their documented direct-call resource semantics. Campaign orchestration supplies the explicit bounded scope and therefore owns admission, native-thread quarantine, and hard resource ceilings.

## Exact neighborhood production and reuse

`ExactNeighborhoodEngine` is the single exact TARGET-DATA2B/C geometric neighborhood implementation. Query blocks from eligible feature families may execute through the shared deterministic queue. The frozen scaled-distance/radius/tolerance semantics and candidate/witness order remain scientific authority.

Completed blocks are reduced in canonical witness order and streamed into authenticated witness-oriented CSR state. Ragged neighbor temporaries are released after canonical commit. The final CSR uses fixed typed offsets/indices and is admitted against the stage RAM budget before materialization.

The neighborhood store is reconstructible execution state. Its identity binds the semantic reference/candidate ordering, family identity, metric/tolerance policy, cardinalities, and cache-format version. Worker count, block size, queue depth, timing, and progress configuration are excluded.

MVIDX consumes authenticated forward CSR and SHALL NOT perform a second geometric query on a cache hit. Missing, corrupt, or stale forward state is rebuilt through the same exact neighborhood engine rather than a separate geometry implementation.

## Deterministic MVIDX inversion and out-of-core scaling

Required-family candidate-to-witness inversion and hard-obligation inversion are independent exact tasks. Each transpose uses deterministic counting/transpose semantics; canonical family order is restored after arbitrary task completion.

Within-row strict-order validation is vectorized but semantically identical to a row-by-row predicate: every adjacent candidate index inside a CSR row must be strictly increasing.

Campaign MVIDX MUST NOT require a multi-billion-edge inverse payload and a full-family transpose workspace to coexist in anonymous RAM. Large-family inversion therefore supports bounded row-chunk CSR-to-CSC construction and file-backed NPY arrays under explicit RAM and disk admission. Candidate offsets remain canonical unsigned 64-bit arrays and candidate-to-witness indices remain canonical unsigned 32-bit arrays.

Chunk size, file-backing threshold, and concurrent inversion count are execution-only. Out-of-core and in-memory paths SHALL be byte-equivalent for the authoritative sparse arrays and content digest. Required disk capacity is preflighted before inversion. Durable authenticated state is re-opened before transient build paths are removed.

The producer/consumer driver SHALL respect bounded ready/in-flight/completed queue capacity even when the number of required families exceeds queue slots. It submits only admitted work, drains completions, and refills deterministically; it does not eager-submit an unbounded family set.

## Exact reference-radius construction

TARGET-DATA2B reference-radius construction uses one shared read-only scaled matrix/tree per family and independent row blocks through the deterministic queue. Each queued cKDTree operation uses one native worker while outer work is available.

Execution may reduce a configured maximum block size to improve lane occupancy and bound query temporaries. Block boundaries are not scientific inputs; local radii and downstream reference arrays SHALL remain byte-identical across qualified block/worker schedules.

Pair/species lookup structures, constant-family rejection, and cached scaling may remove repeated object traversal or unnecessary computation only when inclusion rules and numerical results remain unchanged.

## Exact forward/lazy selector and qualification kernels

MVSEL/MVQUAL use typed ragged-CSR gathers and indexed reductions to replace repeated Python object traversal. Candidate/witness ordering remains canonical.

The MVSEL rank authority remains sequential. MVSEL2 evaluates exact candidate-to-witness rows on demand during hard coverage, then uses an outward-rounded certified lazy representative frontier after one exact Phase-B rebase. A stale bound is excluded only when it is strictly below the best exact score minus the frozen tolerance. Vectorization MAY combine independent row evaluation and telemetry work, but authoritative FP64 row reductions, contender filters, and state mutations remain canonical.

MVSEL2/REPAIR2 mutation touches only the selected candidate's forward witness and obligation incidence. It does not maintain complete candidate marginal arrays or traverse witness-to-candidate inverse adjacency. MVIDX1 remains unchanged on disk; its forward-only v2 runtime view avoids mapping inverse arrays.

Required hard-obligation state and coverage counters may be maintained incrementally if qualification proves equality to reconstruction from the canonical sparse relation.

Same-N MVQUAL rescoring jobs are independent and may execute concurrently. Completion order is non-authoritative; comparison and persisted result order are reconstructed canonically. Campaign jobs use bounded native numerical lanes and memory admission to avoid nested oversubscription.

## Deterministic repair execution

REPAIR retains the sequential repair iteration, objective, tie hierarchy, accepted/rejected trace, and winner application as authority. Immutable proposal scoring may execute concurrently when measured work exceeds the execution-only break-even threshold.

Proposal kernels may use vectorized CSR gathers, fused sparse scans, stamp-array membership, and O(1) candidate/rank maps. Parallel proposal completion is reduced in historical shortlist order. Before a winning swap is persisted, any arithmetic whose exact historical order is authoritative is recomputed in that order.

## Selector-to-repair exact state reuse

`TargetMultiViewSelectionStateCache` is authenticated reconstructible state at the MVSEL/REPAIR boundary. MVSEL may snapshot exact mutable selector state at materializable rungs. REPAIR may restore such a checkpoint only while repair state is identical to the pure selector order.

After the first accepted repair swap, repair carries the historical mutable state forward. It SHALL NOT synthesize a later repaired state by reconciling a pure MVSEL checkpoint with selected-set differences when that operation changes FP64 state, even if selected candidate IDs happen to match.

Cache identity binds the reference/MVIDX/MVSEL/policy/sparse-kernel lineage and excludes worker/storage choices. Missing, stale, corrupt, or incompatible state falls back to exact historical replay. Post-divergence CSR gather preparation may be batched, but authoritative candidate-major FP64 mutations remain in canonical order.

For the current v2 chain, MVSTATE2 replaces the v1 eager cache. Its native bundle contains only selected order, per-family witness multiplicity and coverage mass, obligation counts, correlation counts, and representative utility. The lazy queue is reconstructed by exact rebase. Restore authenticates the manifest and array bundle, rejects v1/stale/tampered/truncated artifacts, and recomputes continuation invariants from the selected prefix before use.

## Replay-source indexing and materialization

The selected replay ExtXYZ remains the external replay authority. A `ReplaySourceIndex` may record authenticated source-byte identity, frame byte offsets/lengths, atom counts, and source-order geometry identity so sparse monitor subsets can seek directly to requested frames and complete traversals can parse bounded contiguous chunks.

The index is reconstructible execution state and SHALL NOT replace replay source, split, label, prediction, or retention authority. Parser chunk size and index location are execution-only. Source mutation or index corruption causes safe reconstruction.

Parser concurrency is not introduced merely to increase worker count. It is permitted only when measured on the relevant workload and exact persisted replay bytes/identities are preserved.

## Model inference, evaluation, and verification concurrency

Independent checkpoint-evaluation and bounded verification jobs may execute concurrently under common CPU/RAM/GPU/VRAM admission. Initialization/setup work is excluded or included in utilization calibration according to the current dedicated runtime specification; architecture requires only that the selected calibration policy be explicit, deterministic, and independent of scientific checkpoint metrics.

Runtime parallelism SHALL NOT enter evaluation policy, checkpoint metric, selection, or verification scientific digests. Existing completed verification/evaluation artifacts remain reusable only when their immutable model, structure/data, runtime dependency, and scientific execution identities remain compatible.

GPU admission SHALL fail closed on hard memory limits and SHALL NOT silently change backend/model precision or scientific policy. Positive accelerator qualification is evidence, not an architectural assumption.

## Memory budget and persistence

CPU admission is necessary but insufficient. Long stages track an estimated memory budget including persistent trees/scaled arrays, in-flight temporaries, buffered completions, sparse state, result accumulation, and scratch space:

$$
M_{\mathrm{stage}} =
M_{\mathrm{persistent}}+M_{\mathrm{inflight}}+M_{\mathrm{buffered}}+
M_{\mathrm{sparse}}+M_{\mathrm{result}}+M_{\mathrm{scratch}}.
$$

New work is admitted only when CPU and memory budgets permit it. Large reconstructible arrays may use mmap-compatible uncompressed persistence when that lowers peak memory or restart cost without changing scientific content.

Every persistent execution cache SHALL authenticate its semantic inputs and payload arrays independently. Cache corruption/staleness is a reconstruction event unless the cache itself is explicitly defined as scientific evidence by another contract.

## NUMA-ready locality

A flat work queue is appropriate when memory locality is not limiting. Multi-socket systems may require node-local queues/data shards, worker affinity, local stealing first, and cross-node stealing only to avoid idle lanes.

NUMA behavior is an execution extension only. It SHALL be activated only after measurement on suitable hardware and SHALL NOT alter scientific identity or canonical reduction order.

## Vectorization and allocation hygiene

Performance-critical loops SHOULD avoid repeated linear searches, rebuilding immutable dictionaries, repeated full-array scaling, unnecessary concatenation, Python-object materialization where contiguous typed arrays suffice, and per-frame/per-species mask reconstruction that can be cached safely.

Appropriate exact kernels include:

- offset-derived ragged CSR gathers;
- bounded-integer indexed counting/reduction;
- epoch/stamp arrays for bounded-ID membership;
- bounded batched bootstrap/statistical work that preserves the declared RNG stream;
- preallocated output arrays and static indexing metadata;
- cache-keyed static reduction metadata for repeated checkpoint evaluation.

Optimization changes must distinguish arithmetic preparation from authoritative arithmetic order. Rearranging addresses or batching independent work is acceptable only when the resulting authoritative records satisfy the applicable equivalence contract.

## Progress and observability contract

Every long-running stage SHALL expose:

1. scientific progress: completed/total work, percent where meaningful, and ETA when estimable;
2. executor state: busy/allocated workers, ready/in-flight/buffered work, and resource pressure where measurable;
3. current hot items: identities/local progress for slow active families, shards, jobs, or proposals.

A heartbeat is emitted even when no task completes during the reporting interval. ETA is based on globally committed work rather than one current item.

User-facing MLFF progress uses the common presentation grammar:

- dynamic fields appear in canonical order beginning with status/progress/elapsed/ETA;
- elapsed and known ETA use fixed-width `HH:MM:SS`; durations beyond 99 hours retain all hour digits;
- unavailable ETA is exactly `--:--:--`;
- counted work uses `progress=completed/total (percent%)`;
- throughput carries an explicit stable unit;
- fields are semicolon-delimited;
- scheduler heartbeats expose completed and active/pending/queue state rather than prose-only status.

Presentation state SHALL NOT enter scientific digests or execution-cache identity. Shared timing/progress helpers own formatting so individual stages do not introduce private ETA dialects.

## Performance qualification contract

A performance change is qualified against representative worker schedules and workloads appropriate to the stage. Qualification evidence records, as applicable:

- wall and CPU time;
- occupancy/utilization and throughput;
- peak RSS/VRAM and persisted bytes;
- queue occupancy/backpressure;
- output/content digests;
- exact scientific-record equality or the explicitly declared tolerance contract.

For sequential-authority algorithms, equivalence is checked at the state granularity needed to detect arithmetic drift: for example, MVSEL after each selected rank, REPAIR across the complete swap trace, and MVIDX across every canonical offset/index array.

Detailed measurements, historical before/after comparisons, rejected implementation experiments, and release-by-release optimization chronology belong in `benchmarks/`, `audits/`, `release/`, and `docs/history/mlff/`, not in this architecture chapter.
