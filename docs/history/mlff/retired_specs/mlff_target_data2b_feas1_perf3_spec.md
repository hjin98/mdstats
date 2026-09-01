# TARGET-DATA2B-FEAS1-PERF3 global single-level scheduler and campaign progress

**Release:** `mdstats 0.20.223a0`  
**Architecture revision:** 90  
**Scientific authority:** unchanged exact TARGET-DATA2B-FEAS1 v1

## Motivation

Workstation observation of PERF2 showed two defects: the profile-local reporter did not expose how many profiles remained, and nested Python-block x cKDTree-worker scheduling still produced low sustained CPU utilization. The execution scheduler, not the scientific neighborhood definition, is therefore replaced.

## Execution contract

1. FEAS1 builds one deterministic manifest containing every `(domain, family/profile, witness block)` workload.
2. Parallel automatic mode uses one single-level global work queue implemented by a `ThreadPoolExecutor`, with one worker per configured CPU-budget lane.
3. Every parallel exact `cKDTree.query_ball_point` block uses `workers=1`; native-tree nesting is forbidden when global workers > 1.
4. Profile preparation and query blocks share the same executor. Work from all profiles/domains enters one bounded central queue.
5. Queue workers may execute blocks in arbitrary completion order, but each profile buffers results until contiguous witness order is available and performs `np.add.at` reduction only in that order.
6. The canonical packed `(witness,candidate)` reduction remains row-major/candidate-major. FP64 candidate-gain arithmetic order is therefore unchanged.
7. Pending futures are bounded to `2 * global_workers`; pending plus completed-not-yet-reduced blocks are bounded to `4 * global_workers`.
8. Automatic `[performance].target_coverage_feasibility_global_workers = 0` resolves to the complete `cpu_threads_budget`; with the default `cpu_fraction=0.90`, a 32-logical-thread host receives 28 global FEAS1 lanes.
9. PERF2 `target_coverage_feasibility_block_workers` and PERF1 `target_coverage_feasibility_family_workers` are compatibility aliases only. Positive aliases must agree.

## Progress contract

Before expensive execution, FEAS1 must report total profiles, total blocks, total witnesses, global workers, tree workers/task, and queue depth. Interval/milestone reports must include profiles completed/total, profiles prepared/total, active profile count, blocks completed/total, witnesses completed/total, percentage, sampled busy executor lanes, pending/queued task counts, elapsed time, throughput, and global ETA. Every profile completion line must include both completed-profile count/total and the profile's deterministic manifest ordinal.

## Qualification target

The execution objective is a non-starved global queue, not a particular number of Python processes. On the qualification host, 8 global workers over 8 x 25,033-witness profiles achieved 3.811 s evaluator wall time and 29.178 s process CPU time, or 7.66 average cores (95.7% of the eight assigned lanes), versus 7.793 s for serial-profile/native-tree-8 execution.

## Invariants

FEAS1 schemas/digests, exact cKDTree neighborhood relation, support degrees, correlation-unit exclusion, 16,384 ceiling, extent obligations, deterministic output ordering, TARGET-DATA2C scientific selection, and GPU authority are unchanged.
