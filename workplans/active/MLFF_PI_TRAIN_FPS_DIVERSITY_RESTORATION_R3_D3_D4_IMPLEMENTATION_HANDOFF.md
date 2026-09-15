---
kind: proposed-D3-restoration-architecture-contract
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R3
protocol_version: 6.3.0
status: READY_FOR_INDEPENDENT_D3_REVIEW
r1_authority: accepted
r2_dependency_recovery: closed
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_carrier: 3937881ef00222e80845aa81f5471d89a4a7736c
---

# R3 proposed D3 architecture / D4 implementation contract — current-path MVSEL2 restoration

## 1. Purpose and gate

This contract makes the accepted R1 method and closed R2 dependency map implementation-ready at the architecture boundary. It is **proposed D3**, not self-accepted architecture. It must receive independent Protocol-6.3 D3 review before D4 product-code mutation begins.

D1 authority:
- `docs/methods/mlff_target_training_order_scientific_method.md`

D2 authority:
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`

R2 recovery map:
- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R2_DEPENDENCY_PROVENANCE_MAP.md`

The design objective is not to recreate historical TARGET-DATA topology. It is to rebind the mature exact MVSEL2 capability beneath current P2/preparation/store ownership with the smallest coherent source closure.

## 2. Current-owner architecture

The current architecture remains authoritative around the restored chain:

```text
current resolved target-size policy
        |
        v
U_size -> P_train + M3
        |
        v
prepare target-order evidence on exact P_train
        |
        v
TargetCoverageReference
        |
        +--> FEAS1
        |
        +--> NEIGHBOR1 -> MVIDX1
                          |
                          v
                    MVSEL2 / MVSTATE2
                          |
                  configured REPAIR2
                          |
                exact state reconstruction
                          |
                          v
                  complete TargetTrainingOrder
                          |
          +---------------+---------------+
          |                               |
          v                               v
  current T_N prefixes             independent MVQUAL
          |                               |
          +---------------+---------------+
                          |
                          v
                 current P2 projection
                          |
                          v
                 unchanged P3/CV/production
```

Ownership constraints:

1. `prepare` remains the live-input/build/publication orchestration owner.
2. current campaign/prepared-generation storage remains the currentness/adoption owner.
3. current P2 target-size policy remains the owner of configured candidate sizes, explicit hard-support inputs, and public `TargetTrainingOrder`/qualification projection.
4. `TargetCoverageReference` is the sole selector-specific fitted numerical owner.
5. MVSEL2/REPAIR2 own construction of the one target-training order, not candidate sizes or target-size outcome ranking.
6. MVQUAL owns independent membership admissibility only, not target-size error ranking.
7. P3 training/evaluation/reducer, post-selection CV/replay/production, and `pi_eval/M1/M2/M3` remain unchanged owners.

No selector-specific parallel store, target-size topology, or cleanup/currentness subsystem may be added.

## 3. Current policy/schema cutover

The current executable target-order policy token remains `candidate_independent_priority.v1` until D4 cutover. D3 shall define one new semantically versioned target-order policy/schema identity for the restored multi-view method.

At the D4 cutover:

- existing prepared generations whose target-order identity was produced by `candidate_independent_priority.v1` are incompatible with the new selector semantics and must be treated as stale/reconstructible rather than silently adopted;
- incompatibility is handled through existing prepared-generation/currentness rules, not through a new migration framework;
- old orders are not migrated rank-by-rank into the new method;
- a newly built accepted prepared generation becomes current only through the existing publication/adoption owner.

The exact string/version name is D3/D4 serialization authority; it must be deterministic and unambiguous but does not belong to D1/D2 scientific ranking.

## 4. Restore/rebind source closure

D4 should prefer alteration/rebinding of the recovered mature modules over wrappers or duplicate implementations. The minimum expected capability closure is:

- target coverage/reference construction;
- FEAS1;
- exact neighborhood build and persistence;
- exact sparse index build/restore;
- MVSEL2 full-forward oracle and certified-lazy engine;
- Phase-B witness-term cache/native batch accelerator and bounded worker preflight;
- REPAIR2;
- MVQUAL;
- compact authenticated continuation/checkpoint support required by current restart;
- only the rank journal/history surfaces actually required for restart/observability.

Historical module boundaries may be merged or renamed where current architecture makes that simpler, provided one owner remains and D1/D2 behavior is exact. Do not preserve old files merely for historical symmetry.

### 4.1 TargetCoverageReference / DATA7

Reuse current upstream data/provider identities and current exact `P_train` membership. Restore only selector-input semantics needed by accepted family construction. Any historical DATA7 fitted metric/scaler/PCA/reference owner is removed from the current path; it may not coexist with `TargetCoverageReference`.

Provider-dependent families are conditionally constructed only when their accepted provider is already part of the current protocol. Selector preparation cannot instantiate an unrelated foundation/profile provider solely to enrich coverage.

### 4.2 Canonical obligation builder

Do not copy the historical obligation builder literally. Rewire it to current P2 hard-support policy and accepted R1 canonical-locus semantics:

1. validate source-local IDs inside explicit/automatic namespaces;
2. project each source requirement to exact current `P_train`;
3. form accepted semantic locus `L(o)` independently of minimum/source ID;
4. require exact incidence agreement for accepted same-locus aliases;
5. use `k=max(k_i)` within a canonical locus;
6. retain alias/minimum/source provenance separately;
7. assign one deterministic canonical locus identity;
8. build one MVIDX obligation incidence/count authority.

Do not infer aliasing from identical incidence alone. Current `condition_id` automatic/explicit equivalence may be recognized because accepted current semantics establish the same condition locus. Other semantic domains require equivalent accepted provider meaning before merge.

### 4.3 FEAS1

Retain exact current feasibility/fragility semantics and diagnostics. Replace all historical fixed-ceiling assumptions with current `P_train`/configured-ladder capacity. FEAS1 remains diagnostic/fail-closed and cannot mutate target sizes or thresholds.

### 4.4 NEIGHBOR1 / MVIDX1

Restore exact sparse scientific relations and mature resource behavior:

- exact neighborhood boundary;
- canonical CSR ordering;
- direct forward and inverse family incidence;
- canonical obligation incidence and current correlation-unit codes;
- file-backed/OOC large-array paths;
- bounded anonymous scratch/resource admission;
- packed/shared durable roots or equivalent O(1)-in-family-count mapped-FD representation;
- forward-only restore for MVSEL2/REPAIR2 where witness-oriented roots are not required;
- early rejection/rebuild of obsolete reconstructible per-family cache layouts;
- disk/scratch/descriptor admission and crash-safe publication.

Durable selector sparse products are authenticated reconstructible prepared artifacts beneath existing preparation/store ownership. No path-name accident may make a partial build current.

### 4.5 MVSEL2 execution

Restore one implementation with two exact views:

- scalar/full-forward oracle used for bounded falsification/fallback;
- optimized certified-lazy production path.

The production path shall restore the mature witness-term cache/native candidate-row acceleration before performance is judged. It may parallelize only execution-independent candidate-row scoring/reductions proven to reproduce the accepted binary64 reference. Heap/frontier certification, canonical contender logic, ties, authoritative state mutation, and prefix order remain deterministic scientific control.

The native preflight is execution-only. If native qualification fails or measured speedup is insufficient, fall back to exact serial execution; never alter scientific ranking.

### 4.6 REPAIR2 and continuation

At each configured shell:

- only the active shell is mutable;
- lower configured prefixes are immutable;
- exact accepted objective/limits apply;
- accepted swaps update one master permutation.

After the first accepted swap, discard/rebuild all prefix-dependent selector continuation state whose ancestry precedes the repaired prefix. Reconstruct from primitive sparse authority and exact repaired prefix. Pre-repair history may remain diagnostic but cannot authorize continuation.

After the final configured shell, continue the same optimized exact MVSEL2 engine to `|P_train|`. There is no UID/condition-round-robin/scalar-only substitute suffix.

### 4.7 MVQUAL

MVQUAL must be independently computed from immutable primitive selector evidence. Progressive optimization is allowed only when each family/group state evolves serially across nested configured rungs. Concurrency may occur across independent state owners, not through racing mutation of one progressive family state.

Qualification records project into the existing current P2/public owner; no parallel qualification owner is created.

## 5. Persistence and identity contract

At minimum the prepared selector identity must bind:

- exact current `P_train` / split identity;
- selector input/provider identities and exact fit domain;
- TargetCoverageReference policy/family identities;
- FEAS1 policy identity where needed for reproducibility;
- exact NEIGHBOR/MVIDX scientific identity;
- canonical obligation semantics/incidence/effective minima and governing P2 policy identity;
- MVSEL2 numerical policy/version;
- configured target-size ladder where shell state matters;
- REPAIR2 policy and exact repair-plan/repaired-prefix identity;
- complete final order identity;
- MVQUAL evidence identity per configured prefix.

Execution-only values such as workers, queue depth, cache residence, preflight timing, and mmap path do not enter scientific identity.

Checkpoint/restart identity must make stale pre-repair state impossible to consume after prefix divergence.

## 6. Current-path integration requirements

D4 must integrate the restored chain into the actual current preparation path rather than expose it as an optional alternate route.

Required behavior:

1. one normal preparation invocation builds/reuses the selector evidence and final order;
2. current prepared-generation publication stores enough authenticated information for fresh-process reuse without rebuilding science;
3. target-size selection consumes exact prefixes only;
4. post-selection CV/replay/production consume frozen selected memberships and never reconstruct selector science;
5. manual target-size selection does not run auto-target-size optimization machinery beyond preparation work genuinely required for the selected current order/qualification;
6. invalid/stale historical prepared artifacts fail closed or rebuild through existing currentness mechanisms;
7. no current downstream code is allowed to fall back silently to `candidate_independent_priority.v1` after the new policy becomes current.

## 7. Resource and concurrency contract

- CPU worker budgets come from the current stage resource owner.
- OOC builds account for durable output, scratch/write amplification, and current available storage where observable.
- mapped file descriptors remain bounded independently of family count.
- queue/completion order cannot enter canonical ordering.
- concurrent build/adoption uses existing current prepared-generation ownership; only attempt-owned temporary state may be cleaned after proving no protected generation references it.
- GPU is not required by the restored selector method unless an already-authorized provider requires it. Final production GPU qualification remains deferred to final release per project workflow.

## 8. D4 implementation sequence

After D3 independent PASS/acceptance, implement in this order so defects remain local and evidence-bearing:

1. policy/schema/currentness cutover skeleton and canonical-obligation builder;
2. TargetCoverageReference current-domain rebinding + FEAS1;
3. exact NEIGHBOR1/MVIDX scientific sparse substrate and OOC/packed persistence;
4. scalar/full-forward MVSEL2 oracle;
5. optimized certified-lazy Phase B plus mature native execution closure;
6. REPAIR2 and post-repair reconstruction;
7. independent MVQUAL and current P2 projection;
8. current prepare/CampaignStore publication/reload wiring;
9. restart/history surfaces actually required by current lifecycle;
10. integration/qualification/performance closure.

Avoid temporary old/new selector routers when direct replacement under current owner is possible.

## 9. Mandatory D4 tests and falsification

D4 must include the D2 oracle set plus architecture-specific tests:

### 9.1 Semantic/oracle

- dense/direct vs NEIGHBOR exact adjacency including tolerance boundary;
- direct coverage vs MVIDX mass;
- full-forward vs optimized rank equality every rank on bounded adversarial fixtures;
- canonical obligation alias/max-min metamorphics;
- minimum-2 one-vote progression;
- different-locus identical-incidence preservation;
- REPAIR2 proposal/swap equality, lower-prefix immutability, exact hard deficit;
- cold primitive replay vs post-repair warm-cache continuation;
- independent MVQUAL equality and monotonicity;
- complete suffix beyond configured `N_max` uses the same selector.

### 9.2 Identity/currentness/restart

- old `candidate_independent_priority.v1` prepared generation is stale under new policy;
- fresh-process load of the new prepared generation performs no scientific rebuild;
- interrupted build cannot become current;
- corrupted/mismatched reference/MVIDX/checkpoint/repair identity fails closed;
- interruption/resume strictly beyond `N_max` yields byte/semantic-identical complete order;
- stale pre-repair checkpoint/journal after divergence is rejected/discarded/rebuilt.

### 9.3 Storage/resources

- many-family constrained `RLIMIT_NOFILE` regression proves O(1)-in-family-count mapped FDs;
- forced low disk/ENOSPC/write failure publishes no partial accepted selector artifact;
- anonymous RAM remains bounded on representative OOC construction;
- obsolete per-family persistence is rejected/rebuilt early;
- concurrent attempt cleanup cannot remove protected adopted data.

### 9.4 Performance-preservation checkpoint

Before final integration, run an early representative CPU performance check that records:

- configured-prefix MVSEL/REPAIR wall time and evaluated sparse edges;
- Phase-A to Phase-B transition rank;
- Phase-B exact refresh/lazy-certification rate;
- native preflight meters/effective width;
- wall time and evaluated edges per selected rank;
- post-final-repair reconstruction cost;
- substantial suffix work beyond `N_max` when `|P_train|>N_max`;
- peak RSS, mapped FDs, final/scratch disk footprint, and I/O.

This checkpoint is diagnostic. Do not alter D1/D2 because a performance target is missed until the mature optimized execution closure is confirmed active and a material current-envelope defect is demonstrated.

## 10. Final assembled qualification

Final integration qualification must cover the complete current `prepare` critical path through:

```text
live current inputs
 -> selector evidence
 -> coverage/FEAS/NEIGHBOR/MVIDX
 -> configured MVSEL/REPAIR/MVQUAL
 -> final repaired-prefix reconstruction
 -> suffix to complete P_train order
 -> prepared-generation publication
 -> fresh-process reload
 -> downstream select/CV/production consumption without rebuild
```

The final production-scale GPU qualification remains deferred to the final release package for the stakeholder's machine. CPU/scientific correctness and representative performance qualification are not deferred.

## 11. Forbidden implementation shortcuts

D4 may not:

- retain current scalar/UID order as a hidden fallback after cutover;
- run full-forward scoring as the unqualified production algorithm merely because it is easier to implement;
- infer obligation aliases from incidence equality alone;
- double-vote same-locus aliases;
- recreate historical label-domain/fold or fixed-size topology;
- append a UID suffix after the last configured shell;
- lower 0.95, extent support, or explicit minima to make preparation pass;
- add migration/rescue/wrapper machinery when stale reconstructible state can simply be rejected and rebuilt;
- introduce a second fitted selector reference, order owner, qualification owner, prepared store, or cleanup authority;
- silently change arithmetic association/tolerance to gain speed.

## 12. Review/acceptance criterion

Independent D3 review should PASS only if the architecture preserves the accepted D1/D2 method, uses current owners rather than parallel historical topology, retains the mature performance/resource closure, and gives D4 a deterministic bounded implementation contract with no unresolved semantic ownership.

On D3 PASS and stakeholder acceptance where required, D4 implementation is authorized by this workplan. Until then, repository product code remains unchanged.
