# mdstats 0.20.222a0 patch notes

## TARGET-DATA2B-FEAS1-PERF2

This release addresses continued low CPU utilization in `TARGET-DATA2B-FEAS1` and missing long-wall progress reporting.

### Execution changes

- FEAS1 now schedules independent witness query blocks concurrently with a shared read-only cKDTree.
- Automatic CPU scheduling balances block workers and native cKDTree workers inside the existing `StageResourceScope` budget.
- New execution-only setting: `[performance].target_coverage_feasibility_block_workers`.
- The 0.20.221a0 `target_coverage_feasibility_family_workers` setting remains a compatibility alias.
- Completed query blocks are reduced strictly in witness order, preserving exact historical FP64 candidate-gain accumulation.
- A process-pool prototype was measured and rejected because IPC of ragged compressed neighborhoods was slower than shared-memory threading.

### Progress changes

- FEAS1 prints family start, block/witness progress, elapsed time, average witness rate, ETA, and periodic heartbeats.
- MVIDX1 now prints per-family block/witness progress, elapsed time, rate, ETA, and accumulated edge count.
- `[performance].progress_interval_seconds` controls the long-wall heartbeat cadence.

### Scientific authority

No scientific schema, coverage metric, radius, candidate ceiling, FEAS1 digest semantics, sparse-index semantics, TARGET-DATA2C selector behavior, or GPU authority changes.
