# TARGET-DATA2B-FEAS1-PERF1 exact CPU execution hardening

**Release:** `mdstats 0.20.221a0`  
**Architecture revision:** `88`  
**Dependency graph schema:** `70`

## Scope

This gate changes execution only. TARGET-DATA2B coverage geometry, FEAS1 scientific report schemas and digests, the fixed `16384` candidate ceiling, MVIDX1 sparse graph semantics, and downstream target-selection policy are unchanged.

## Exact vectorized neighborhood reduction

For every bounded cKDTree query block, geometric neighbor rows are mapped to candidate-frame ownership and packed as int64 `(local witness row, candidate frame)` keys. `np.unique` establishes the canonical witness-major/candidate-major unique relation. Candidate gains use unbuffered `np.add.at` in that canonical order, matching the historical scalar per-witness update order. Self-excluded and correlation-unit-excluded candidate degrees are computed by vectorized counts.

Support masses are accumulated once after the complete family degree arrays are known. `np.add.accumulate` consumes weights in original witness order for each support class, so query block partitioning cannot regroup scientific FP64 sums.

## Bounded parallelism

FEAS1 may execute independent feature families concurrently. `StageResourceScope` must bound `family_workers * tree_workers` to the configured CPU budget. Automatic scheduling prefers several independent family lanes when available and assigns the remaining budget to cKDTree workers. The execution-only setting `target_coverage_feasibility_family_workers` may override family concurrency.

No GPU neighborhood backend is authorized. CUDA execution would constitute a new numerical distance/threshold realization and requires separate equivalence qualification.

## MVIDX1 reuse

MVIDX1 consumes the same canonical vectorized block compressor and writes the returned candidate stream directly to its sparse witness-row payload. Persisted edge order, uint32/uint64 arrays, hashes, and inverse adjacency are unchanged.

## Qualification

Acceptance requires exact FEAS1 dictionary/content-digest identity across tree-worker, query-block, and family-worker schedules; exact MVIDX1 graph identity across worker/block schedules; regression-clean MVSEL1, REPAIR1, and MVPERF1; and compile/import integrity. Performance evidence is non-scientific.
