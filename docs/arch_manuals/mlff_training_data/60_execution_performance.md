# Part VI - Bounded execution, restart, and performance architecture

## Purpose and authority

Execution optimization is acceptable only when it preserves the scientific/statistical authorities defined in Parts I-V and improves measured throughput, memory behavior, storage behavior, or restart cost. Utilization is diagnostic; scientific digests, exact decision traces, and authoritative records decide correctness.

Worker count, queue depth, query-block size, cache location, file-backing threshold, storage path, and similar execution choices do not enter scientific identity unless a current specification explicitly makes them part of the scientific algorithm.

The central rule is:

> change how exact work is scheduled or represented, not what scientific evidence is consumed or what authoritative decision is produced.

## Work/span and single-level parallelism

For serial work \(T_1\), critical path \(T_\infty\), and \(P\) admitted CPU lanes,

$$
T_P\ge\max\!\left(\frac{T_1}{P},T_\infty\right).
$$

Independent work is exposed at the highest useful level. Nested numerical parallelism is suppressed while outer work can fill the resource budget:

$$
P_{\mathrm{outer}}P_{\mathrm{native}}\le P_{\mathrm{budget}}.
$$

For native kernels such as cKDTree, BLAS, or OpenMP, a campaign resource scope owns native-thread admission. Individual workers do not independently oversubscribe the machine.

## DATA6-to-DATA8 materialization boundary

DATA6 is the last preparation stage that owns the MACE accelerator model. After its final descriptor/prediction consumer, production explicitly releases calculator/model references and unused CUDA allocator state. DATA7/DATA8 are CPU/I/O stages and advertise no GPU jobs. Heavy frame-cache restoration and foundation-energy reconstruction remain lazy until a materialization variant actually misses the completed-artifact reuse path.

DATA7 exposes canonical final/fold domains as the outer parallel unit. Each domain retains independent fitted scaler, PCA, E0, weighting, selection, and coverage state. Immutable frame arrays and authenticated descriptor shards may be shared, but task-local mutable extraction state is not shared between concurrent domains. Outer DATA7 work is admitted through the deterministic resource queue using the live runtime CPU budget and a conservative peak incremental-memory estimate; inner BLAS/OpenMP/PyTorch widths are one while multiple domains are available. Workers publish authenticated immutable DATA7 cache generations and return compact receipts. Only the coordinator mutates production records/checkpoints, in canonical domain order.

Target-size screening is treated as a distinct reuse topology. Campaign preparation owns one nonpersistent namespace resolver that maps each canonical DATA7 `training_domain_digest` to its authenticated coverage authority and materializes REPAIR2 prefixes lazily only for requested `(training domain, size)` pairs. Synthetic coverage IDs are confined to that lookup boundary; DATA7 plans remain keyed by canonical training-domain digest and final-development evaluation cohorts by source label-domain ID. The fixed pre-selection evaluation complement is always the authenticated final-coverage frame set minus the maximum-qualified prefix, so the comparison cohort cannot shrink across `n1/n2/n3` continuation. `ProductionMaterializationPlan` itself rebuilds the canonical DATA5/CV feature-domain topology; callers cannot inject a convenient alternate domain set.

The expensive DATA7 fitted metric/E0/weight core is selection-size invariant, so target-size variants may reuse that core through a reconstructible execution-only index to a fully authenticated DATA7 carrier artifact. The fitted-core index authenticates both the execution recipe and the actual fitted-result digest; publication is create-once/validate-winner, and divergent results for one recipe fail closed. A stale carrier that fails the exact foundation-prediction/reference/lineage reuse contract is discarded and refit rather than promoted to a scientific failure. Reuse admission uses a separate conservative RAM estimate for carrier load, selection/coverage realization, and archive output instead of charging the hypothetical full fit. Size-specific selection and coverage are then realized normally, and the resulting full `Data7PreparationBundle` remains the sole scientific authority. Full shared DATA7 publication likewise requires any concurrently computed winner to match the local bundle digest and deterministic archive SHA. The shared full-artifact recipe is v2 and excludes DATA8-only evaluation membership/target-study outcome state while retaining the exact prescribed training prefix and selection policy. Legacy full-artifact v1 recipes remain read-compatible; reconstructible fitted-core v1 indices are cache misses.

DATA8 separates immutable fixed-file production from production-tree assembly. Unique ExtXYZ cache misses are enumerated first, then balanced across fresh CPU-only interpreter batches when the estimated byte volume is large enough to amortize fresh-interpreter startup; small batches remain on the serial producer. The large read-only context is serialized once with mmap/file references; worker messages carry compact context paths and recipe digests rather than dense arrays. Fixed-file cache generations use atomic publish-or-validate-winner semantics. CPU, RAM, task count, configured free-disk reserve, and both estimated and measured worker-context spill bound concurrency; insufficient transient headroom reduces execution to the serial producer before subprocess launch. After cache population, the production tree, YAML, scripts, protocol identities, tree digest, and promotion are assembled canonically in the parent process.

Externally owned foundation, selected-head, and replay inputs cross an authenticated inode-independent copy boundary into mdstats-owned content-addressed snapshots before reuse. Hardlinking is reserved for mdstats-owned immutable snapshots/cache generations and their consumers. Optimizer-invariant weighted replay and MLCV TRUE_DFT replay-light realizations are content-addressed execution caches, so seed variants do not repeat identical corpus transformations/scans. Shared DATA7/DATA8 caches are reconstructible execution state. Cache layout, worker count, batch assignment, and completion order do not enter scientific identity. Legacy DATA7 flat cache generations and PAR1 lexically ordered checkpoint digests remain read-compatible; current writes use atomically installed content-addressed generations and canonical `plan.domains` checkpoint order.

## Deterministic resource-bounded work queue

CPU-heavy independent tasks use a shared deterministic queue abstraction with explicit CPU and memory ownership. Its architectural responsibilities are:

- bound executing, ready, in-flight, and buffered work;
- reserve persistent memory before admitting temporaries;
- propagate deterministic task identities and exceptions;
- allow arbitrary completion order where scientific order is irrelevant;
- restore canonical reduction/commit order where FP64 arithmetic or record order is authoritative;
- expose progress/resource telemetry without placing telemetry in scientific identity.

Task submission may run ahead of execution to hide hand-off latency, but simultaneous execution remains bounded by the declared resource scope.

## One product-scale authority per semantic input

The fixed target-size population does not permit one full descriptor/graph/selector copy per rung. Per required training domain, the product-scale execution model is:

```text
one fitted DATA7 selection-input authority
one exact neighborhood/MVIDX authority
one MVSEL2/REPAIR2 master order
one compact MVSTATE2 continuation state when persisted
prefix metadata/views for candidate rungs
MVQUAL evidence for required prefixes
training artifacts only for candidates authorized by the size funnel
```

This is an architectural resource invariant, not merely an optimization preference. A realization whose memory/storage scales approximately with eight independent copies of the target-selection state is non-conforming even if it eventually produces the same scientific result.

## Exact neighborhood production and reuse

The exact neighborhood engine is the sole geometric producer for the multi-view relation. Query blocks may execute independently through the bounded queue, but completed blocks are committed in the canonical witness/family order required by the scientific representation.

The resulting sparse store is authenticated by semantic inputs such as candidate/reference ordering, family identity, fitted metric/scaling, radius/tolerance semantics, and cache-format identity. Worker count, block size, queue depth, and cache location are excluded.

MVIDX1 consumes this authenticated exact relation and does not repeat geometry when a compatible forward relation exists. Missing, stale, corrupt, or incompatible reconstructible state is rebuilt from the same authoritative inputs.

## Deterministic out-of-core MVIDX

Large candidate-to-witness inversions must be bounded in anonymous RAM. Exact row-chunk transpose/inversion and file-backed typed arrays are permitted when they produce the same authoritative sparse arrays as the in-memory realization.

The execution layer therefore preflights RAM and scratch/disk capacity, bounds concurrent inversions, and may use mmap/NPY-compatible arrays for large products. Candidate offsets and candidate-to-witness indices use the current specified canonical types and ordering.

Chunk size, file-backing threshold, and inversion concurrency are execution-only. In-memory and out-of-core paths must satisfy the same scientific content/equivalence contract.

## MVSEL2 exact forward/lazy execution

MVSEL2 rank authority remains sequential because each accepted candidate changes the scientific state. Execution acceleration is concentrated in exact candidate-row evaluation, staged lexicographic filtering, vectorized sparse gathers, and a certified lazy representative frontier.

A stale lazy score is only an upper bound. A candidate can be excluded without refresh only when the bound proves it cannot defeat the best exact contender under the frozen tolerance. Otherwise it is refreshed exactly. Authoritative contender comparison and state mutation remain canonical.

MVSEL2 maintains compact witness multiplicity, covered mass, obligation/correlation counts, and representative state. It does not require complete product-scale candidate marginal arrays or normal-path witness-to-candidate inverse propagation.

## REPAIR2 exact active-shell execution

REPAIR2 keeps authoritative repair iteration, admissibility predicates, objective/tie hierarchy, accepted/rejected trace, and winner application deterministic.

Independent proposal scoring inside one immutable pre-swap state may execute concurrently when measured work justifies it. Vectorized candidate-row gathers, stamp arrays, bounded-ID indexing, and fused sparse scans are valid preparation optimizations. The accepted winner and authoritative mutation are committed in the frozen deterministic order.

Repair operates on the one master order and protected prefixes. It does not create independently repaired dataset copies for individual target-size rungs.

## MVSTATE2 restart boundary

MVSTATE2 is the only current selector/repair continuation-state family. Its persistent bundle is compact and reconstructible from the selected prefix plus authenticated primitive identities.

Persisted state may include:

- selected order/prefix identity;
- per-family witness multiplicity and covered mass;
- obligation and correlation counts;
- representative utility/state required by the current exact continuation contract;
- manifest identities binding dataset/domain, MVIDX, policy, ordering, and schema.

Ephemeral lazy queues and product-scale candidate marginal arrays are reconstructed rather than treated as durable authority.

Restoration authenticates payloads and recomputes continuation invariants from the selected prefix. State from unsupported historical generations is not deserialized or migrated into current authority; the current state is reconstructed from current inputs or the campaign is re-prepared.

## MVQUAL independent execution

Same-prefix MVQUAL jobs are independent and may execute concurrently. Their completion order is non-authoritative; persisted comparison order is canonical.

MVQUAL may share authenticated primitive sparse inputs but recomputes the hard predicates independently of selector/repair counters. Parallelism, vectorization, or cache reuse cannot turn selector-internal state into qualification evidence.

## Target-size funnel materialization

The configurable `n1/n2/n3` size study materializes training state only for candidates still authorized by the production funnel:

```text
qualified population
  -> coarse (`n1`) candidates
  -> at most four short (`n2`) continuations
  -> two final-screen (`n3`) continuations
  -> one selected size or typed failure
```

Continuation authenticates model, optimizer, RNG, and protocol parentage. Eliminated candidates are not trained further in ordinary production.

Exhaustive training of the full candidate population to final fidelity is release/algorithm qualification only and must use a bounded dedicated qualification design. It is not permitted to become an unbounded default campaign artifact generator.

## Replay indexing and bounded parsing

The selected replay source remains external scientific authority. A replay source index may store authenticated source-byte identity, frame offsets/lengths, atom counts, and source-order geometry identity to permit sparse monitor access and bounded chunk parsing.

The index is reconstructible execution state. It cannot replace replay source, split, label, prediction, monitor, or retention authority. Source mutation or index corruption causes safe reconstruction.

Parser concurrency is introduced only when measurement on representative workload shows benefit and exact persisted replay bytes/identities are preserved.

## Training, evaluation, and verification concurrency

Independent training, checkpoint-evaluation, and deployment-verification jobs may execute concurrently under common CPU/RAM/GPU/VRAM admission where their owning policies permit concurrency.

Runtime concurrency never enters the scientific checkpoint score or admissibility policy. Hard GPU/VRAM or RAM limits fail closed rather than silently switching precision/backend, shrinking scientific evidence, or changing model policy.

Positive accelerator qualification is evidence. The architecture does not assume an accelerator path is correct merely because it is available.

## Memory and storage budget

Long stages account for persistent and transient memory:

$$
M_{\mathrm{stage}}=
M_{\mathrm{persistent}}+M_{\mathrm{inflight}}+M_{\mathrm{buffered}}+
M_{\mathrm{sparse}}+M_{\mathrm{result}}+M_{\mathrm{scratch}}.
$$

New work is admitted only when its CPU and memory reservations fit the stage budget. Large reconstructible arrays may use mmap-compatible/file-backed persistence to lower peak RSS or restart cost.

Every persistent cache authenticates its semantic inputs and payload independently. Corrupt/stale reconstructible caches are rebuild events; they are not silently accepted and are not scientific evidence unless another current contract explicitly defines them as such.

Scratch-space admission is part of bounded execution. A stage that can create product-scale temporary files must predict and cap scratch use before production work begins.

## GPU/VRAM admission

GPU jobs are admitted against explicit free-memory and configured-budget evidence. Calibration/measurement windows and utilization estimators are runtime policy owned by the current execution specifications, not by release chronology in this manual.

An execution controller may reduce job concurrency after measured resource pressure. It cannot change the scientific batch/exposure semantics, precision policy, checkpoint evidence, or target/replay membership merely to fit memory unless the owning scientific specification explicitly permits that change.

Adaptive OOM recovery is acceptable only when the recovered execution is protocol-equivalent and the changed execution parameter is non-semantic.

## NUMA-ready locality

A flat queue is appropriate when locality is not limiting. Multi-socket systems may add node-local queues/shards, worker affinity, local stealing first, and cross-node stealing to avoid idle lanes.

NUMA policy is an execution extension. It is activated only after measurement and cannot alter scientific identity, canonical reduction order, or data partition/evidence roles.

## Vectorization and allocation discipline

Performance-critical implementations should avoid:

- repeated linear searches and immutable-map reconstruction;
- repeated full-array scaling when a fitted/scaled authority can be reused;
- unnecessary concatenation or Python-object materialization where typed arrays suffice;
- repeated per-frame/per-species masks that can be safely cached;
- full candidate rescans when exact sparse/local updates suffice;
- duplicate descriptor/graph/materialization per target-size rung.

Useful exact kernels include offset-derived ragged CSR gathers, bounded integer indexed counting/reduction, epoch/stamp arrays, preallocated typed outputs, and cached static reduction metadata.

Optimization reviews must distinguish arithmetic preparation from authoritative arithmetic order. Reordering memory accesses or batching independent work is acceptable only when the authoritative records satisfy the required exact/tolerance contract.

## Progress and observability

Every long-running stage exposes both scientific progress and resource/executor state. At minimum:

1. completed/total work and percent where meaningful;
2. elapsed and ETA when estimable;
3. throughput with an explicit stable unit;
4. active/pending/buffered work or equivalent scheduler state;
5. resource pressure or current hot item when relevant.

A heartbeat is emitted during long periods without task completion. ETA is based on globally committed work.

User-facing MLFF elapsed and known ETA use fixed `HH:MM:SS` formatting; unavailable ETA is `--:--:--`. Presentation state never enters scientific digests or cache identity.

## Performance qualification

A performance change is reviewed against representative target-scale work. Evidence records, as applicable:

- wall and CPU time;
- throughput and measured occupancy/utilization;
- peak RSS/VRAM and scratch/persisted bytes;
- queue occupancy/backpressure;
- output/content digests;
- exact scientific-record equality or the explicitly declared tolerance contract.

Sequential-authority algorithms are checked at sufficient state granularity to detect drift—for example MVSEL2 accepted ranks, REPAIR2 swap trace/state, and MVIDX canonical sparse arrays.

Detailed before/after measurements, failed optimization experiments, release qualification results, and chronology belong in benchmarks/audits/history rather than the current architecture.
