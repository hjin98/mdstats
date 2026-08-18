# TARGET-DATA2B-FEAS1-PERF2 shared-tree block parallelism and progress

## Scope

TARGET-DATA2B-FEAS1 remains an exact CPU diagnostic authority. This gate changes execution and observability only: scientific schemas, exact cKDTree neighborhoods, FP64 candidate-gain accumulation order, support-mass order, the fixed 16,384 candidate ceiling, and TARGET-DATA2C selection semantics are unchanged.

## Problem

PERF1 removed the serialized Python witness loop and added family-level concurrency, but workstation observation still showed only about 200-500% aggregate CPU during a long FEAS1 run. The remaining bottleneck is that one expensive family is driven by one Python thread issuing 512-witness cKDTree queries. Native `cKDTree(workers=N)` utilization is bursty for these object-returning radius queries, while NumPy neighborhood compression between queries is effectively a separate single-threaded phase. Family-level concurrency cannot solve this when a domain has one or only a few expensive families.

A fork/process block implementation was evaluated and rejected as the automatic backend. It creates visible Python worker processes but must serialize ragged compressed neighborhood arrays back to the deterministic parent reducer. On the eight-thread qualification host that IPC cost made the exact FEAS1 family kernel substantially slower than the native-thread baseline. Process count is therefore not used as a performance proxy.

## Execution contract

FEAS1 executes independent witness query blocks concurrently in a bounded `ThreadPoolExecutor` while all block workers share the same read-only scaled descriptor matrix and cKDTree. Each block may itself use a bounded number of native cKDTree workers. `StageResourceScope` requires `block_workers * tree_workers <= cpu_threads_budget`.

Automatic scheduling uses at most eight block workers and normally at most four native tree workers per block. When at least two blocks and at least four CPU-budget threads are available, automatic mode requires at least two tree lanes and searches bounded factorizations for the highest occupied lane count, preferring about four block workers when products tie. A single-block family may use up to sixteen native tree workers.

The new execution-only setting is `[performance].target_coverage_feasibility_block_workers`. The 0.20.221a0 setting `target_coverage_feasibility_family_workers` is retained as a compatibility alias and must agree if both are positive. `[performance].target_coverage_workers` remains the native tree-worker override.

## Determinism

Query/compression futures may complete out of order. Results are held by witness-block start index and reduced only when the next contiguous block is available. The scheduler counts both running futures and completed-but-not-yet-reducible results against one bounded in-flight window, preventing a slow early block from accumulating an unbounded ragged-neighborhood backlog. Within each block the PERF1 canonical `(witness,candidate)` order is retained. Candidate gain therefore uses the same FP64 `np.add.at` order as the historical exact authority. Degree arrays and support-mass accumulation remain in witness order. Worker/block schedules cannot change the scientific digest.

## Progress and long-wall observability

FEAS1 must emit, at minimum, family start plus block/witness progress containing elapsed wall time, average witness rate, and ETA. The parent wait loop uses the configured `[performance].progress_interval_seconds` as a heartbeat timeout, so a slow in-flight block cannot leave the terminal silent indefinitely. Progress reporting is execution-only and must never change scientific records.

TARGET-DATA2C-MVIDX1 receives matching block-level progress (block count, witness count, elapsed, rate, ETA, and accumulated edge count) because a single sparse-index family can also be a long wall-time operation. Its scientific sparse arrays and digests remain unchanged.

## Qualification requirements

1. Serial and block-parallel FEAS1 reports must be dictionary- and digest-identical across query worker and block-size schedules.
2. Progress callbacks must report block/witness counts, rate, and ETA.
3. MVIDX1 must report block-level progress without changing sparse-index digests.
4. `block_workers * tree_workers` must remain inside `StageResourceScope` CPU budget.
5. No GPU neighborhood backend is authorized; FINAL-GPU1 remains deferred.
6. Performance evidence must compare against a one-driver native-thread cKDTree configuration, not only against the historical scalar Python implementation.
