# mdstats 0.20.223a0 patch notes

## TARGET-DATA2B-FEAS1-PERF3

This release replaces PERF2's profile-local nested block/tree factorization with a campaign-wide single-level exact-neighborhood scheduler. It is an execution/observability hardening release; FEAS1 scientific authority is unchanged.

### Global single-level parallelism

- One `ThreadPoolExecutor` spans every FEAS1 domain/profile and witness block.
- Automatic mode allocates one executor worker per `StageResourceScope` CPU-budget lane (normally 90% of logical CPU threads).
- In parallel mode each exact `cKDTree.query_ball_point` task runs with `workers=1`; nested cKDTree thread pools are eliminated.
- Profile/tree preparation tasks use the same executor, allowing later-profile preparation to overlap active neighborhood work.
- A bounded central queue (`2 x workers` pending, `4 x workers` pending+ready cap) prevents unbounded ragged-neighborhood buffering while keeping enough runnable work to avoid profile-tail starvation.
- Completed blocks may arrive in any order globally, but each profile is reduced strictly in witness order, retaining the exact historical FP64 update sequence.

### Campaign-wide progress

FEAS1 now pre-counts the complete workload and reports:

- profiles completed / total,
- profiles prepared / total and currently active profiles,
- global blocks completed / total,
- global witnesses completed / total and percentage,
- sampled executor busy lanes / configured lanes,
- pending and queued tasks,
- elapsed time, witness throughput, and global ETA.

Profile completion lines use the completion count as the primary fraction and include the deterministic manifest ordinal separately, so `profile 17/68 complete` always means seventeen profiles have completed.

### Configuration

- New: `[performance].target_coverage_feasibility_global_workers = 0`.
- `0` uses the complete configured CPU budget.
- `target_coverage_feasibility_block_workers` and `target_coverage_feasibility_family_workers` remain compatibility aliases and must agree with the new setting if explicitly positive.
- `target_coverage_workers` remains relevant to MVIDX1 and deliberately serial FEAS1 debugging; parallel FEAS1 always uses one native tree worker per global task.

### Qualification evidence

On the available 9-thread host, an eight-profile workload with 25,033 witnesses/profile, eight descriptor dimensions, and 512-witness blocks was timed inside the FEAS1 evaluator:

- profile-serial / native-tree-8: 7.793 s wall, 23.878 s process CPU,
- global-8 / tree-1: 3.811 s wall, 29.178 s process CPU,
- wall-time speedup: 2.04x,
- average global CPU occupancy: 7.61 cores = 95.7% of the eight assigned FEAS1 lanes.

Scientific family reports remain exact/dictionary-identical to serial execution.

### Scientific authority

No scientific schema, coverage metric, local radius, support definition, candidate ceiling, report digest semantics, TARGET-DATA2C selector behavior, or GPU authority changes. GPU neighborhood authority remains unapproved and FINAL-GPU1 remains deferred.
