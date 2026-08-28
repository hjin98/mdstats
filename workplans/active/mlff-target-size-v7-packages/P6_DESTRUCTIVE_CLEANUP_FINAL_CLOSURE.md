---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 6
status: blocked-on-p5
---

# P6 — Destructive cleanup and assembled final closure

## Purpose

Remove the now-unreachable retired architecture, simplify the public/current surface, and perform fresh final acceptance on the assembled V7 implementation.

P6 is not permission to change frozen V7 semantics for easier cleanup. Preserve reusable optimized kernels/reference oracles where V7 still depends on them, but delete obsolete scientific authorities, aliases, migration bridges and tests whose only purpose is retired topology.

## Entry conditions

- P1-P5 accepted and committed.
- V7 is the sole current runtime since P4.
- Post-selection CV/final-production lifecycle is functionally closed since P5.
- Any old code retained after P4 is proven unreachable and listed for explicit disposition.

## Pass P6-A — retired authority/module/API deletion

Delete or unexport as applicable:

- compatibility-domain training eligibility/fanout paths that no longer serve advisory reporting;
- old DATA3 compatibility-domain numerical label identity/current schemas;
- old label-domain partition condition/unit current schemas;
- `TargetDataRoleFreeze` target-size usage and equivalent per-domain role authorities;
- public/persisted FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL target-size plans;
- fixed target-size/ceiling authorities;
- target-size `domain_prefix_digests` and per-domain candidate maps;
- complement/coarse target-size EVAL2 population authorities;
- old target-size candidate per-domain prefix/evaluation materialization fields;
- old preselection DATA5/MLCV target-size/CV coupling;
- V5 prepare-contract/receipt/migration aliases and reconstruction helpers;
- current exports/imports that advertise retired plans as supported current authority.

Retain/refactor optimized sparse/vectorized selection/repair/EVAL2/DATA8/TRAIN2 kernels, reference oracles and useful benchmarks only when they have a current V7 caller or independent supported purpose.

### Verification cycle

1. import/package/public-export tests;
2. structural absence checks for forbidden names/concepts/call edges;
3. tests proving current V7 callers still reach retained optimized kernels;
4. no dead compatibility wrapper retained solely to satisfy removed tests.

## Pass P6-B — test/spec/document cleanup

Replace obsolete topology tests rather than weakening V7 to keep them green.

Delete/rewrite assertions whose only contract is:

- fixed target-size universe;
- prepare must run MVSEL2 -> REPAIR2 -> MVQUAL2 -> target-size;
- old prepare receipt keys;
- label-domain namespace resolution for target-size;
- per-final/CV-domain target-size materialization;
- complement/coarse target evaluation.

Preserve or strengthen behavioral coverage for:

- one public target-size scheduler;
- paired optimizer seeds;
- exact continuation/restart;
- selected-data freeze before CV;
- production horizon independence;
- real DATA8/TRAIN2/EVAL2 owner boundaries;
- numerical failure semantics;
- restart/invalidation;
- optimized-kernel reference/performance equivalence.

Reconcile architecture manuals/specs/config examples and source maps with the actual assembled implementation. Historical snapshots remain historical and must not be presented as current authority.

### Verification cycle

1. docs/spec link/reference/lint/build checks;
2. test collection/import checks after deletions;
3. structural source-map/public API review.

## Pass P6-C — final accepted-contract reconciliation

Before broad tests, inspect the complete assembled diff against the parent V7 workplan and all P1-P5 exit invariants.

Explicitly verify:

- provenance is precise/advisory and separate from numerical label identity;
- neutral substrate has no compatibility-domain partition axis or pre-target CV;
- one P_train/M3 split, one pi_train, one pi_eval/M ladder and one target-size reducer own screening;
- common deterministic preparation is shared across N/seeds;
- only optimizer seeds are screening replicates;
- exact continuation and exact M_i evaluation remain intact;
- current persistence/runtime is V7-only;
- CV consumes exact T_selected and cannot feed back;
- final production is fresh on full T_selected;
- old scientific authorities are absent rather than hidden behind wrappers.

Any material omission is repaired before final functional acceptance. Green tests do not substitute for this conformance pass.

## Pass P6-D — fresh final affected-surface regression

Re-derive the affected surface from the final assembled candidate, not merely from the original plan.

Run:

1. all focused tests still material to the final implementation;
2. complete affected regression across DATA2/DATA3/identity/duplicates/neutral statistical base/selection/DATA7/DATA8/TRAIN2/EVAL2/CLI/persistence/restart/CV/MLCV/final production;
3. broader/full repository suite because the change crosses multiple foundational identities and orchestration boundaries unless a smaller bound is independently demonstrated;
4. repository/project-required checks;
5. documentation build/lint/reference/PDF checks where applicable.

A required check that does not execute is not a pass. Attribute only demonstrably pre-existing unrelated failures.

## Pass P6-E — assembled real-owner integration

Execute the bounded real semantic path on the same final candidate:

```text
config/source ingestion
 -> neutral current substrate
 -> prepare V7 statistical authorities
 -> select-target-size paired screen
 -> persist selected N/T_selected
 -> restart/reopen
 -> create/run post-selected CV
 -> fresh final-production entry
```

Use real config parser, campaign store/SQLite, current CLI/orchestrators, V7 state transitions, materialization ownership and CV/final-production owners. Expensive scientific training/prediction may be bounded/faked below those boundaries.

The evidence must fail if the real current owner is broken; helper-only/proxy paths cannot close the claim.

## Pass P6-F — deterministic/reference/resource closure

Run the bounded non-production qualification needed to ensure the refactor did not degrade engineering fitness:

- deterministic restart/evidence reproduction;
- selection/repair optimized-kernel reference equivalence;
- EVAL2 numerical/reference equivalence;
- bounded CPU/RAM/VRAM/I/O checks where execution/resource machinery changed;
- no accidental repeated-domain/scalar algorithmic regression.

Separately report M-ladder decision-preservation qualification when representative evidence is available; otherwise mark it `deferred/unavailable`.

Do **not** run long target-machine GPU/real-data production qualification as part of implementation closure; that remains deferred to final release.

## Final exit gate

P6 and the complete V7 implementation are accepted only when all of the following are true:

- P1-P5 exit invariants still hold on the assembled final candidate;
- retired current architecture is structurally absent, not merely unreachable through one tested path;
- complete affected regression and required broader checks pass;
- assembled real-owner integration passes through current CLI/persistence/state transitions;
- documentation/public surface matches the implemented architecture;
- no unresolved material conformance defect remains;
- unavailable production-scale qualification is clearly separated from functional acceptance.

Only after this gate may the implementation be presented for independent Software Design review/merge decision.
