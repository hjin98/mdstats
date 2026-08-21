---
kind: implementation-workplan
workplan_id: DOC-MLFF-SIMPLIFY1
plan_revision: 1
status: FUTURE_DEFERRED
analysis_base_ref: feat/mvsel2-forward-lazy
activation_condition: complete the current real MLFF campaign and resolve genuine blocking defects first
---

# DOC-MLFF-SIMPLIFY1 — MLFF production-path simplification

## Objective

Reduce the MLFF subsystem's failure surface, runtime overhead, and maintenance burden after the current production campaign has demonstrated acceptable functionality.

The governing rule is the Minimum Mechanism Principle:

> When a simple and a complex implementation satisfy the same material requirements, use the simple implementation. Complexity must justify itself by providing a material capability.

This work is deliberately deferred until the current production campaign is working. Do not interrupt campaign completion with speculative cleanup or redesign.

## Diagnosis

The MLFF subsystem is substantially feature-complete, but accumulated development has produced excessive control-plane complexity:

- very large campaign orchestration modules;
- multiple historical DATA/state generations;
- parallel selector/repair/state authorities;
- compatibility and migration logic distributed through normal execution;
- qualification/finalization machinery beyond the material product checks;
- scientific validation, checkpoint handling, evaluation, export, resume, backend selection, and migration concerns composed too closely;
- likely redundant materialization, conversion, hashing, reconstruction, and state-management paths;
- many potential failure points unrelated to the core scientific operation.

The immediate implementation gap is operational rather than conceptual: the exact current production path must first work end-to-end.

## Preconditions

Do not activate this workplan until:

1. the real MLFF campaign has been run through the current production path;
2. genuine blocking defects encountered during that run have been fixed at their owning layer;
3. MVSEL2/REPAIR2 has been exercised by the real campaign sufficiently to establish that its functional behavior is acceptable;
4. downstream training/evaluation/export behavior is functional enough that simplification can preserve a known-good reference behavior.

The production campaign itself is the primary qualification. Do not create a separate synthetic qualification framework for this work.

## Invariants

The simplification must preserve all material behavior, including:

- accepted target/replay dataset semantics;
- target coverage and subset-selection semantics;
- MVSEL2/REPAIR2 selected-set behavior and restart correctness;
- foundation-model and head semantics;
- target/replay evaluation behavior and hard acceptance thresholds;
- numerical precision policy;
- scientific model checks, including topology/relaxation integrity where required;
- checkpoint authenticity and restart safety;
- supported backend/runtime behavior;
- production model export/deployment requirements;
- deterministic or explicitly specified stochastic behavior;
- compatibility only where compatibility is still intentionally supported.

Scientific validation is product behavior and must not be deleted merely because it is validation.

## Planned simplification

### 1. Establish one current production authority per domain

After production confirmation, reduce normal execution to one current authority for each major stateful domain.

Target selector path:

```text
MVIDX
  -> MVSEL2
  -> REPAIR2
  -> MVSTATE2
```

Remove MVSEL1/REPAIR1/legacy state dispatch from the normal current path once it is no longer required.

Historical implementations may remain only when they have a concrete role such as:

- one-time migration;
- compatibility with an intentionally supported artifact;
- focused reference/oracle testing.

They must not remain parallel runtime authorities by default.

### 2. Collapse compatibility to explicit normalization boundaries

For each historical artifact class, choose exactly one policy:

```text
READ/MIGRATE
REBUILD
REJECT
```

Legacy artifacts that must remain readable should be normalized once into the current representation.

Derived caches should normally follow:

```text
validate -> reuse
otherwise -> rebuild
```

Avoid distributed compatibility branches throughout current algorithms.

### 3. Thin the campaign orchestrator

The CLI/campaign core should coordinate the workflow rather than implement domain behavior.

Target conceptual shape:

```text
prepare_data()
select_data()
train()
evaluate()
export()
```

Do not create a new orchestration framework. Reuse existing domain modules and move ownership to the narrowest existing component that naturally owns the behavior.

### 4. Reduce campaign-execution responsibility

Separate only genuine ownership boundaries where doing so materially improves clarity and failure isolation.

Likely boundaries:

- training/runtime and restore;
- checkpoint normalization/persistence;
- model evaluation/export.

Do not split code merely to reduce file size. Stop when each remaining component has a coherent responsibility.

### 5. Remove obsolete qualification/process machinery

Audit MLFF `qualify_*`, finalization, evidence, runbook, and historical development helpers.

Retain:

- direct operational commands users still need;
- focused regression tests;
- scientific/model-integrity checks;
- deployment checks that establish real product requirements.

Delete or fold away machinery that merely certifies another internal framework without establishing a distinct material requirement.

### 6. Profile the real production path before performance redesign

Use the successful or partially successful real campaign to identify actual hotspots.

Investigate only measured costs such as:

- repeated large-array scans;
- repeated gain evaluation in MVSEL2 Phase A;
- unnecessary graph touching;
- repeated data materialization;
- redundant large-artifact hashing;
- duplicate checkpoint/model conversion;
- avoidable copies;
- compatibility passes in current execution;
- derived-cache invalidation caused by mismatched identity rules.

Do not build speculative caching, inverse indexes, supervisors, adaptive qualifiers, or new state systems unless measurements show they are the simplest sufficient fix.

### 7. Reduce state and failure surfaces

For every remaining state object, cache, adapter, fallback, compatibility branch, and recovery layer, ask:

1. What material requirement does it satisfy?
2. Is that requirement already satisfied elsewhere?
3. Can the state be derived instead of persisted?
4. Can two authorities be collapsed into one?
5. Can a failure mode be eliminated by deleting the mechanism rather than handling it?

Deletion and negative-LOC revisions are expected and desirable when behavior is preserved.

## Acceptance

The simplification is complete when:

- the same accepted MLFF campaign behavior is reproducible through a materially smaller and clearer production path;
- one current authority exists for selector/state and other major runtime domains;
- legacy compatibility is confined to explicit boundaries;
- normal current execution does not route through obsolete generations unnecessarily;
- no standalone qualification framework is required;
- scientific integrity checks remain intact;
- restart and checkpoint behavior remain correct;
- focused regression/integration tests pass;
- at least one real representative campaign path succeeds after simplification;
- measured runtime or memory does not regress materially without explicit justification;
- the resulting code has fewer independent failure points and is easier to diagnose.

## Implementation sequence

- [ ] Finish the current real campaign and resolve genuine blockers.
- [ ] Record the known-good current behavior and measured hotspots.
- [ ] Map live versus legacy authorities and remove dead current-path branches.
- [ ] Normalize compatibility boundaries.
- [ ] Thin campaign orchestration.
- [ ] Simplify execution/checkpoint/evaluation ownership where justified.
- [ ] Remove obsolete qualification/process helpers.
- [ ] Run focused tests plus a real representative campaign.
- [ ] Update architecture/specifications to describe the simplified accepted state.
- [ ] Archive this workplan with a concise record of completed changes and any deferred items.

## Redesign triggers

Stop adding patches and reconsider the owning design if any of the following appears during implementation:

- a new wrapper is required around another wrapper;
- multiple state representations must be synchronized;
- a compatibility fix introduces current-path branching in several modules;
- a new supervisor/retry/recovery layer is proposed to stabilize an already fragile mechanism;
- a test harness begins to reimplement the production path;
- a performance optimization requires a second large persistent index or duplicated global state without measured necessity;
- the same invariant is enforced independently in multiple layers.

In such cases, prefer deletion, normalization, or redesign over additional machinery.

## Tracking

This document is the implementation ledger for the future simplification pass.

As work is performed, use the implementation checklist above and add only material implementation decisions, discovered blockers, completed outcomes, or justified deferrals.

Detailed transient debugging logs do not belong in this workplan.
