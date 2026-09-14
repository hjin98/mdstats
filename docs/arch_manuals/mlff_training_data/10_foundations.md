# Foundations and architectural invariants

## Layering invariant

The dependency direction is `D1 -> D2 -> D3 -> D4 -> runtime/generated evidence`. A lower layer may challenge an upstream contract with evidence but may not silently redefine it. Architecture changes that require a new scientific or numerical meaning must reopen the owning upstream document before implementation proceeds.

## Core structural invariants

1. **Immutable evidence ancestry.** Once an upstream evidence identity is consumed downstream, descendants bind that identity rather than mutating it in place.
2. **One semantic owner.** Shared sampling, selection, fitting, reduction, checkpoint, and publication semantics have one owner. Adapters and CLI composition reuse that owner rather than cloning the algorithm.
3. **Candidate-independent work precedes candidate projection.** Shared preparation is fitted once on its authorized domain before per-candidate projection where D2 requires that separation.
4. **P3/P5/P7 lifecycle separation.** Target-size screening, post-selection cross-validation, and final production/qualification are different stages with different evidence permissions.
5. **Fresh production.** Final production is a fresh lineage; screening and CV checkpoints are evidence, not production warm starts.
6. **Backend semantic invariance.** Sequential execution is the semantic reference. Parallel/distributed backends may change scheduling and resource use only when D1/D2 outputs and identities remain equivalent.
7. **Source knowledge stays at the edge.** Source-specific parsing, normalization, and external-code conventions enter through D4 adapters and produce canonical evidence; central orchestration does not rediscover source semantics.
8. **Missing evidence remains explicit.** An unavailable label, relation, artifact, or capability is represented as missing/infeasible/failure according to its owner. Architecture does not synthesize replacement evidence.

## Dependency boundaries

Control-plane components may coordinate owners but must not duplicate their rules. Persistence stores authoritative products and identities but does not infer scientific meaning. Caches accelerate reconstruction only when disposable without loss of authoritative evidence. Generated documents and reports are descendants of canonical sources and never become an independent authority.

## Challenge routing

A discovered contradiction is routed upward to the layer that owns the disputed statement. D4 implementation defects are repaired in D4; D3 integration defects in D3; numerical-method defects in D2; scientific-formulation defects in D1. Lower-layer disagreement is recorded as evidence rather than resolved by weakening the upstream contract.
