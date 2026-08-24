---
kind: implementation-workplan
workplan_id: DATA78-PAR1
protocol_version: 5.2.0
---

# DATA78-PAR1 — DATA7/DATA8 Parallel Materialization and Resource Cleanup

**Status:** complete — accepted for merge and archived
**Current authority:** `docs/specs/training_data/mlff_data7_fitted_metrics_selection_spec.md`, `docs/specs/training_data/mlff_data9a9b_production_materialization_spec.md`, `docs/specs/training_data/mlff_cpu_resource_budget_spec.md`, `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
**Target branch/base:** `feat/data78-parallel-materialization` / supplied source snapshot `e7efde8934303e6c98d404b3fc3dd3b031ad1ef6`

## Objective

Remove avoidable serial work, retained CUDA state, repeated I/O, and underutilized CPU execution from the DATA7/DATA8 production-materialization path without changing scientific fitting, selection, persisted content, restart semantics, or the runtime-discovered 90% CPU budget. Reuse the existing `SystemResourceSnapshot`, `StageResourceScope`, `DeterministicWorkQueue`, content-addressed caches, and canonical checkpoint authority rather than adding a second scheduler.

## Invariants

- CPU capacity is runtime-discovered as `max(1, floor(0.90 * available_threads))`; no host-specific 4/8/16/28 capacity ceiling is introduced.
- RAM, disk, task count, or measured throughput may reduce effective concurrency below the CPU budget.
- DATA6 owns GPU use. After its final consumer, MACE/calculator references are released and DATA7/DATA8 run with `gpu_jobs=0`.
- Completed-materialization reuse remains lazy: heavy frame-data/foundation setup occurs only after a materialization cache miss.
- Raw immutable frame descriptors may be reused across DATA7 domains; fitted scaler/PCA/E0/weight/selection state never crosses domains.
- Parallel completion order never changes canonical DATA7 domain order, checkpoint order, scientific digests, or DATA8 tree layout.
- `max_new_data7_domains` limits newly checkpointed canonical domains, including shared-cache hits.
- Shared caches are reconstructable execution caches, never scientific authorities. Concurrent publishers must atomically publish or validate the winner.
- Large frame arrays/DATA7 matrices are not copied through DATA8 process IPC.
- No speedup may weaken hashing, validation, numerical policy, output bytes, or DATA9A integrity qualification.

## Scope

Primary implementation areas:

- `mdstats/training_data/_campaign_cli_core.py`
- `mdstats/training_data/model_features.py`
- `mdstats/training_data/production_materialization.py`
- `mdstats/training_data/data8_bundle.py`
- existing resource/work-queue helpers as needed without creating a second scheduler
- focused DATA6/DATA7/DATA8/restart/resource tests

Out of scope unless profiling proves necessary:

- changing DATA7 scientific algorithms or fitted-state semantics;
- moving DATA7/DATA8 numerical work to CUDA;
- weakening ASE ExtXYZ round-trip validation;
- a global persistent DAG scheduler;
- GPU qualification beyond lifecycle/unit behavior in this environment.

## Gates

### G0 — Baseline, observability, and ownership seams

**Goal:** freeze the actual cold/warm execution path and expose the hidden setup work.

**Work:**

- add focused timing/progress/resource telemetry around shared frame-data setup, foundation-energy restoration, DATA7 domains, cache publication, DATA8 fixed-file assembly, and verification;
- separate DATA7/DATA8 execution-worker reporting from future MACE DataLoader worker reporting;
- add/extend direct tests for cache/restart and resource invariants.

**Acceptance:**

- warm completed-materialization reuse does not eagerly resolve frame data;
- active materialization reports named setup phases rather than appearing stuck at variant `0/N`;
- focused baseline tests pass unchanged scientifically.

### G1 — DATA6 GPU lifecycle and lazy setup boundary

**Goal:** release CUDA/MACE ownership before CPU-only DATA7/DATA8 while preserving warm reuse.

**Work:**

- add idempotent explicit close/release behavior for `MaceCalculatorProvider`;
- release the provider immediately after the final DATA6 consumer and, when CUDA is available, synchronize/collect/empty unused allocator blocks;
- resolve heavy DATA7/DATA8 prerequisites only after the first active materialization miss, then re-probe live resources.

**Acceptance:**

- provider release is safe and idempotent;
- no DATA7/DATA8 code path depends on a live DATA6 provider;
- warm reuse remains lazy.

### G2 — Concurrency-safe reusable DATA7 cache

**Goal:** make shared DATA7 publication safe for concurrent producers.

**Work:**

- publish each recipe as a staged authenticated content-addressed generation with atomic installation;
- if another producer wins, validate/reuse the winner;
- retain read compatibility with the legacy flat archive/manifest layout; write only the new layout.

**Acceptance:**

- concurrent equivalent publishers converge on one valid generation;
- corrupt/incomplete staging never becomes authoritative;
- legacy cache artifacts remain reusable.

### G3 — DATA7 resource model and deterministic domain parallelism

**Goal:** execute independent missing DATA7 domains concurrently inside the 90% CPU/RAM envelope.

**Work:**

- derive a conservative peak incremental-memory estimate from domain row count, feature-policy dimensions/dtypes, PCA workspace, combined output, and fixed overhead;
- prepare immutable common inputs; make mutable extraction caches task-local;
- submit only the first permitted missing canonical domains, preserving `max_new_data7_domains` semantics;
- run outer domain tasks through `DeterministicWorkQueue` with inner BLAS/OpenMP/PyTorch widths of one and `gpu_jobs=0`;
- workers verify/publish artifacts and return compact receipts; the coordinator alone mutates production records/checkpoints and commits in canonical order.

**Acceptance:**

- serial and parallel outputs are scientifically/content identical;
- RAM admission rejects an intrinsically impossible domain rather than oversubscribing;
- out-of-order completion cannot reorder checkpoint authority;
- multiple affinity budgets demonstrate runtime 90% capacity rather than fixed host counts.

### G4 — DATA7 repeated-work reduction

**Goal:** remove redundant domain-invariant extraction before adding finer nested scheduling.

**Work:**

- profile post-G3 execution;
- convert remaining material Python per-frame feature extraction to bulk/columnar paths where justified;
- reuse only immutable raw descriptors/source tables across overlapping domains.

**Acceptance:**

- fitted domain-local transforms remain isolated;
- no finer `(domain, feature-block)` scheduler is added unless representative profiling shows a material residual bottleneck.

### G5 — DATA8 shared-resource consolidation

**Goal:** remove repeated foundation/replay staging across optimizer variants.

**Work:**

- authenticate immutable foundation/selected-head sources once per preparation session and stage by atomic hardlink/copy;
- deduplicate transformed replay realizations by exact recipe only if the transformation is otherwise repeated materially;
- keep any persistent transformed artifact inside existing reconstructable storage accounting.

**Acceptance:**

- variant seeds do not repeatedly inspect/copy/transform identical shared resources;
- no second foundation-checkpoint cache authority is introduced.

### G6 — Parallel immutable DATA8 fixed-file cache production

**Goal:** parallelize GIL-heavy independent ExtXYZ production without racing production-tree assembly.

**Work:**

- enumerate/deduplicate immutable fixed-file cache misses before tree mutation;
- partition misses into balanced batches based on expected serialized size;
- execute CPU-only fresh-interpreter worker batches with compact path/recipe descriptors and nested native widths of one; never fork the CUDA-initialized parent;
- reconstruct mmap/read-only inputs once per worker batch;
- bound execution by CPU, RAM, task count, configured minimum free disk, and storage throughput;
- assemble each DATA8 tree canonically after cache population.

**Acceptance:**

- fixed-file bytes/sidecars and final DATA8 tree digests match serial reference exactly;
- low-disk admission cannot fail merely because concurrency temporarily amplifies staging;
- production trees are not concurrently mutated by worker processes.

### G7 — Read-path and serializer cleanup

**Goal:** remove remaining duplicate verification/I/O without weakening integrity.

**Work:**

- consolidate DATA7/DATA8 verify-then-read paths into verify-and-return helpers;
- retain one independent DATA9A qualification boundary;
- optimize the high-precision ExtXYZ formatter only if post-G6 profiling still shows it is materially dominant and exact bytes remain unchanged.

**Acceptance:**

- each artifact is not redundantly parsed/hashed inside one qualified load path;
- DATA9A continues to independently reject corrupted promoted artifacts.

### G8 — End-to-end qualification and consolidation

**Goal:** prove correctness, restart safety, resource feasibility, and material throughput improvement.

**Work:**

- qualify serial/parallel scientific/content identity, fresh/warm restart, legacy-cache reuse, cache races, worker failure, interruption after out-of-order completion, constrained RAM, low disk, and several CPU-affinity budgets;
- run the dependency-bundle-backed focused/integrated tests available in this environment;
- benchmark representative cold and warm paths where fixtures are sufficient;
- remove obsolete temporary helpers/duplicate paths and reconcile durable docs only where accepted current contracts changed.

**Acceptance:**

- no scientific/content digest or exact ExtXYZ output regression;
- no resource-budget violation;
- representative end-to-end timing improves materially or an execution width is retained smaller because RAM/I/O throughput is demonstrably limiting;
- unavailable target-GPU/production-scale checks are reported rather than fabricated.

## Redesign triggers

- one DATA7 domain cannot fit by itself inside the configured RAM envelope;
- post-columnar DATA7 remains dominated by an inherently serial fitting operation;
- DATA8 is storage-bound after immutable-cache parallelization, making additional workers counterproductive;
- exact output/determinism cannot be preserved under the proposed concurrency boundary.

## Closeout

When all gates pass:

1. record only accepted durable execution/resource contracts in architecture/specification docs;
2. place correctness evidence under audits/qualification evidence and performance evidence under benchmarks when material;
3. archive this workplan after the transition is accepted;
4. generate a Git patch relative to the supplied source snapshot.

## Implementation status — 2026-08-23

- G0-G1: complete. DATA7/DATA8 active-work progress is separated from future
  MACE DataLoader reporting; completed-materialization reuse remains lazy; the
  DATA6 MACE provider has an explicit idempotent release boundary and best-effort
  CUDA allocator cleanup before CPU-only materialization.
- G2-G3: complete. Shared DATA7 cache generations publish atomically with
  legacy flat-cache read compatibility. Independent final/fold domains execute
  through the existing deterministic work queue with task-local mutable caches,
  conservative peak-RAM admission, single-width inner native libraries, compact
  receipts, and coordinator-owned canonical checkpoint commits.
- G4: reviewed and intentionally closed without a new nested feature-block
  scheduler. Existing structural extraction is columnar and MACE summaries are
  shard-batched; no representative evidence in this environment justified the
  added nested scheduling complexity.
- G5-G6: complete. Immutable foundation/selected-head staging uses atomic
  hardlink/copy, repeated weighted replay realizations are content-addressed,
  DATA8 fixed-file cache misses are deduplicated and balanced across fresh
  CPU-only interpreters, large arrays are transported by mmap/file reference,
  and production-tree assembly remains serial/canonical. DATA8 emits start and
  incremental completion telemetry while worker batches run.
- G7: complete. DATA7/DATA8 verified-load paths return already verified objects
  instead of verify-then-read duplication; independent DATA9A integrity checks
  remain intact. No serializer rewrite was justified after cache/concurrency
  improvements.
- G8: focused and integrated CPU-path qualification is complete in the supplied
  dependency environment. Serial/parallel DATA7 identity, exact DATA8 ExtXYZ
  identity, cache races, legacy cache reuse, RAM admission, low-disk admission,
  fresh subprocess execution, weighted-replay reuse, restart/tamper behavior,
  and provider close semantics are covered by passing tests. Existing baseline
  failures in stale historical specification/preflight tests were reproduced on
  the untouched supplied snapshot and are not attributed to this transition.

## Closeout — 2026-08-23

**Terminal implementation state: accepted for merge and archived.**

- No second scheduler or persistence authority was introduced. DATA7 reuses
  `SystemResourceSnapshot`, `StageResourceScope`, `DeterministicWorkQueue`, and
  ordered reduction; DATA8 reuses the existing authenticated fixed-file cache
  as the only immutable ExtXYZ cache authority.
- Scientific/fitted state remains domain-local. Parallel execution affects only
  execution order, cache population, and resource utilization; canonical
  checkpoint/tree order and exact persisted content remain authoritative.
- The supplied dependency bundle provides ASE/MACE source dependencies for CPU
  qualification, but this container has no CUDA-capable MACE runtime. Actual
  RTX-class VRAM reclamation and workstation-scale end-to-end throughput remain
  target-machine qualification and are not fabricated here.
- The canonical architecture chapter and assembled Markdown were reconciled.
  The repository PDF publication helper requires the unavailable `typst`
  executable, so the derived architecture PDF was not regenerated in this
  environment.
- With those environment-specific qualification boundaries recorded, no
  implementation gate remains open.
