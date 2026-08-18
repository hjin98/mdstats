# mdstats 0.20.199a0 - optimized multi-view target-data roadmap hardening

## Architecture

- Add `TARGET-DATA2-MVPLAN2`, superseding the planning semantics of revision 65 without changing executable TARGET-DATA2C behavior.
- Correct FEAS1 so full-pool self-coverage is only a consistency check; meaningful diagnostics use cross-support fragility and optimistic cardinality lower bounds against the fixed 16,384 ceiling.
- Require exact sparse bidirectional coverage adjacency, first-class extent/stratum obligations, deterministic FP64 scoring, and stable frame-UID tie breaking.
- Split MV selection into hard coverage construction and density-aware representative filling; diversity cannot outrank coverage or protected obligations.
- Implement REPAIR1 conceptually from coverage multiplicity and deficit-directed shortlists, preserving exact lower-rung prefixes and replacement rank inheritance.
- Carry the established PERF-P2/P2R/P3/P4/P5 incremental-state, cache-reuse, unified-resource-budget, bounded-memory, and streaming-persistence rules into MVPERF1.
- Revise the training funnel so only hard-coverage-qualified target sizes are trained: `q -> min(q,4) -> 2 -> 1` at `3 -> 10 -> 30` epochs, with `q=8` yielding `8 -> 4 -> 2 -> 1`.
- Keep the fixed generated candidate sizes `128..16384`, independent 0.95 hard coverage authority, e3nn source/DATA6 path, and CuEq TRAIN2 path unchanged.
- This is a plan-only release; no runtime selector migration occurs until `TARGET-DATA2C-MVMIGRATE1`.
- Advance architecture to revision 66 / dependency-graph schema 48.
