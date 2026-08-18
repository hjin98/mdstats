# REPAIR-PAR1 deterministic parallel proposal specification

**Release:** `mdstats 0.20.231a0`  
**Architecture:** revision 98 / dependency-graph schema 78  
**Status:** implemented exact-equivalence performance hardening

## Frozen contract

1. REPAIR1 sequential iteration, removal shortlist ordering, objective tuple, tie hierarchy, accepted/rejected swap trace, terminal order, and persisted scientific schemas remain unchanged.
2. `execution_mode="reference"` retains the historical scalar proposal scorer as the scientific oracle.
3. Proposal tasks may inspect only the immutable repair state for the current iteration; only the canonical winner is applied, sequentially, after proposal reduction.
4. Fused sparse removal metrics, canonical ragged-CSR frontier gathers, epoch/stamp membership, and the inverse candidate-rank map are execution-only exact transforms.
5. Arbitrary worker completion SHALL be reduced in the historical removal-shortlist order with the unchanged objective/tie comparator.
6. The selected replacement representative contribution SHALL be recomputed with the historical scalar/stamp arithmetic before the swap record is persisted.
7. Proposal worker count, adaptive sparse-work threshold, queue depth, scratch epochs, and task partitioning SHALL NOT enter repair content identity.
8. Native numerical layers SHALL remain single-threaded inside parallel proposal tasks to prevent nested oversubscription.
9. Small proposal batches MAY remain serial when measured executor overhead exceeds useful concurrency; this is an execution choice, not a policy change.
10. No parallel repair-state mutation, approximate set membership, changed target size, altered selector prefix, altered obligation predicates, or changed repair objective is authorized.

## Qualification

The release SHALL demonstrate exact complete-plan/trace equality between the scalar reference and optimized 1/2/4-worker realizations; exact scalar/vectorized proposal equality on every tested removal; exact inverse-rank displacement behavior; unchanged TARGET-DATA2 authority; and same-host evidence that vectorized proposal scoring improves the scalar path while large sparse proposal sets gain additional deterministic worker scaling.

The next gate is `MVQUAL-PAR1`.
