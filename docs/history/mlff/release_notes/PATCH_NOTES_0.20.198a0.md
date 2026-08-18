# mdstats 0.20.198a0 - multi-view target-data optimization roadmap freeze

## Architecture

- Freeze `TARGET-DATA2-MVPLAN1`, the planned replacement for inefficient random/semi-random target ordering.
- Set the planned generated target-size ceiling to 16,384, yielding eight fixed power-of-two candidates from 128 through 16,384.
- Preserve TARGET-DATA2B hard coverage at 0.95 and keep support/extent/stratum/mandatory requirements independent of selector internals.
- Add full-pool feasibility/support-mismatch diagnosis before subset optimization.
- Define deterministic robust multi-view selection, unique-contribution redundancy, deficit-directed repair, exact nested prefixes, independent audit, and exact-equivalence performance hardening.
- Clarify that `8 -> 4 -> 2 -> 1` is candidate-count reduction at 3 -> 10 -> 30 epochs, not dataset-size halving.
- Plan a minimum of four hard-coverage-qualified candidates before the 10-epoch stage; no coverage-failing candidate may survive the 3-epoch screen.
- Keep revision-64 dynamic rescue executable until the final migration gate; no implementation behavior changes in this planning release.
- Break implementation into nine ordered gates from FEAS1 through MVMIGRATE1.
- Advance canonical MLFF architecture to revision 65 and dependency-graph schema 47.
