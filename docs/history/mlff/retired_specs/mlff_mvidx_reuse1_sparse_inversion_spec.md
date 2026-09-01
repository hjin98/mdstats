# MVIDX-REUSE1 stable sparse inversion specification

**Release:** `mdstats 0.20.228a0`  
**Architecture revision:** 95

MVIDX-REUSE1 is an exact-equivalence execution optimization. It does not alter TARGET-DATA2B/C geometry, candidate membership, hard obligations, sparse scientific schemas, MACE-MPA-0/MACE-MH-1 semantics, training, evaluation, or GPU authority.

On a NEIGHBOR1 cache hit, MVIDX consumes authenticated witness-to-candidate CSR and performs only inverse adjacency plus hard-obligation metadata. Independent required-family inversions and the obligation-table inversion are scheduled through `DeterministicWorkQueue` under one `StageResourceScope`. Each individual CSR-to-CSC conversion is the deterministic compiled SciPy counting transpose and is single-native-thread work; outer tasks provide concurrency without nested numerical oversubscription or atomics.

Canonical required-family order is restored after arbitrary task completion order. Worker count, task completion order, timing, and queue telemetry are execution-only. Candidate-to-witness arrays must be byte-identical for every qualified worker schedule.

The historical per-row sorted/unique validator is replaced by one vectorized adjacent-index comparison with CSR-boundary masking. This is the same predicate: comparisons that cross row boundaries are ignored, while every within-row pair must be strictly increasing.

The active CPU qualification uses the supplied MACE-MPA-0 medium checkpoint identity only as campaign provenance. This gate contains no foundation-model-specific logic and applies unchanged to MACE-MH-1.
