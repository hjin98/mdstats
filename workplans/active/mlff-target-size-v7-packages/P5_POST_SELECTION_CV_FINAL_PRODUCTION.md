---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 5
status: blocked-on-p4
---

# P5 — Post-selection CV and final production

## Purpose

Add the downstream methodological-validation and fresh final-production lifecycle **after** V7 target-size selection has frozen exact `N_selected/T_selected`.

P5 must preserve the one-way dependency:

```text
target-size selection -> selected-data freeze -> CV -> final production
```

No CV configuration, evidence or failure may feed back into the already-frozen target-size result.

## Entry conditions

- P4 accepted and committed; V7 is the sole current target-size runtime/persistence generation.
- Exact selected membership is persisted and restart-authenticated.
- No current CV plan is required to construct or run target-size selection.

## Pass P5-A — post-selection CV authority

Construct CV only from exact `T_selected` plus neutral correlation/duplicate groups.

CV owns its own:

- fold count;
- partition seed;
- fold membership;
- checkpoint-monitor/evaluation roles;
- fold-local preparation required by accepted CV methodology.

Required invariants:

- every CV frame belongs to `T_selected`;
- correlation/group constraints may keep related frames in safe roles but must never add an unselected sibling frame;
- no label-domain fanout is reintroduced;
- target-size identity/state does not contain CV configuration or result lineage.

### Verification cycle

1. exact-membership fold construction tests;
2. adversarial correlated-group leakage fixtures;
3. seed/fold-count determinism tests;
4. negative tests proving group expansion cannot enlarge membership;
5. affected partition/MLCV role regression.

## Pass P5-B — CV training/evaluation integration

Refactor MLCV/DATA7/DATA8 role handling so CV jobs descend from exact selected-data identity rather than old DATA5 label-domain/CV authority.

Required behavior:

- fold-local gradient/monitor/evaluation roles are disjoint according to the accepted CV method;
- fold-local preparation may differ where scientifically required by CV methodology, but cannot mutate common target-size preparation or selected N;
- CV EVAL2 roles are post-selection roles distinct from target-size M1/M2/M3 roles;
- replay evidence obeys its accepted validation/gradient roles.

### Verification cycle

1. focused MLCV role/authorization tests;
2. bounded real DATA7/DATA8/TRAIN2/EVAL2 CV integration through actual role owners;
3. affected MLCV/monitor/checkpoint-selection regression;
4. restart/reopen tests for CV state independent of target-size state.

## Pass P5-C — CV failure semantics

Required outcome:

- CV success accepts the already-frozen method/selected-data combination for final production;
- CV failure is a methodological-validation failure and cannot choose a new N or resume target-size screening;
- if CV reveals a need for a material change to the training method/protocol being converged, that changed method requires a new target-size experiment under new scientific identity.

### Verification cycle

1. failure-state transition tests;
2. negative test proving no target-size reducer/selection mutation is reachable from CV failure;
3. target-size digest/result unchanged under CV fold-count/partition-seed/result changes.

## Pass P5-D — fresh final production

After CV acceptance, construct a fresh final training run:

- use full exact `T_selected` for target gradients;
- start fresh from the accepted foundation/initialization rather than continuing a screening trajectory;
- use the accepted training method/protocol;
- production max epoch/horizon is independent of n3;
- frozen M3 may remain development/model-selection evidence if required by accepted downstream policy;
- downstream replay/outer/calibration/locked evidence retains its defined role and cannot retroactively become target-size evidence.

### Verification cycle

1. exact final-training membership tests;
2. fresh-initialization/no-screen-continuation tests;
3. production-horizon independence tests;
4. bounded real DATA8/TRAIN2 final-production entry integration;
5. affected production scheduling/materialization regression.

## Pass P5-E — package closure

Re-derive the P5 affected surface and run complete stage-local affected regression across CV/MLCV/DATA7/DATA8/TRAIN2/EVAL2/final-production callers.

Required integrated lifecycle:

```text
persisted T_selected
 -> create CV
 -> run bounded CV real-owner path
 -> accept or fail without target-size mutation
 -> on acceptance create fresh final-production run
```

Also verify restart at each lifecycle boundary.

## Exit gate

P5 is accepted only when:

> Cross-validation is entirely downstream of the frozen selected dataset, cannot change target size or enlarge selected membership, and accepted CV leads to a fresh final-production run on the full exact selected dataset with a production horizon independent of screening fidelity.

Commit/tag the accepted P5 checkpoint before P6.
