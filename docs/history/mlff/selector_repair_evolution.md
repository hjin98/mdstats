# Historical narrative: multi-view selector and repair evolution

**Status:** non-normative history  
**Current authority:** `docs/arch_manuals/mlff_training_data/50_target_multiview.md` and the current specifications indexed by `docs/specs/training_data/README.md`

## Why this history is retained

The current target-subset architecture is easier to understand if one design lesson is preserved: exact multi-view subset construction initially carried substantially more inverse/marginal state than production-scale workloads could tolerate. The current forward/lazy chain is the result of removing that state while preserving exact scientific decisions.

This document records rationale only. Historical schema names do not define current compatibility behavior.

## Early progressive selector

The first multi-view selector generation established several durable ideas:

- hard scientific coverage had to be evaluated per required view rather than hidden in a weighted average;
- target subsets should be nested prefixes of one deterministic order;
- hard obligations, correlation/provenance structure, representative utility, diversity, and stable ties needed explicit identities;
- repair had to preserve protected lower prefixes and hard coverage.

The initial realization maintained eager/inverse structures and complete candidate-marginal state so that coverage changes could be propagated after each selected candidate. That made correctness easy to reason about at small scale, but product-scale candidate/witness relations made the memory traffic, inverse arrays, and repeated updates expensive.

## Repair and state-reuse experiments

A first repair design introduced active-shell deficit exchange: remove only candidates whose unique support and hard obligations were safe, then replace from the deficit frontier under deterministic objective/tie rules.

A later state-reuse design attempted to persist and reuse selector mutable state at materializable rungs. It demonstrated that selected-set equality alone is not enough to guarantee identical continuation arithmetic after repair divergence. Persisted state has to be authenticated against the exact selected prefix and primitive sparse identities, and post-divergence state cannot be reconstructed by informal reconciliation of two different mutation histories.

Those lessons survive; the old state format does not.

## Forward/lazy redesign

The production redesign retained the scientific ordering policy but changed the representation:

- selector and repair consume candidate-forward sparse rows;
- complete candidate marginal arrays are not maintained as durable state;
- the hard phase uses exact staged scans/filters;
- the representative phase uses an exact rebase and conservative lazy upper bounds;
- stale candidates are refreshed until the winner is certified;
- full-forward scoring remains the exact oracle/fallback;
- continuation state contains only compact reconstructible scientific state;
- independent qualification recomputes hard predicates rather than trusting selector counters.

This moved the scaling focus from inverse propagation and eager global marginal maintenance to exact on-demand sparse work.

## Current-generation decision

The architecture reset removed historical generation compatibility as a product requirement. New campaigns have one current FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL chain.

MVSEL1, REPAIR1, MVSTATE-REUSE1, and migration envelopes remain useful names only when interpreting historical evidence or Git history. They are not alternate current modes, and old campaign state that cannot validate as current is re-prepared rather than migrated.

## Durable lessons

1. Exact scientific ranking can be preserved while radically changing sparse representation and scheduling.
2. A deterministic sequential authority does not imply a completely serial implementation; independent exact scoring can still be vectorized or parallelized.
3. Persistent continuation state should contain only what must be authoritative; large reconstructible caches should remain reconstructible.
4. Repair state after an accepted swap is part of an ordered mutation history, not merely a selected-ID set.
5. Independent qualification is worth keeping even after selector correctness improves because it separates decision logic from verification evidence.
6. Production-scale feasibility must be evaluated using realistic candidate/witness cardinalities and memory traffic, not only small-fixture complexity.
