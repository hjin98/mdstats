---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 4
status: blocked-on-p3
---

# P4 — Atomic runtime and persistence cutover

## Purpose

Make V7 the **only reachable current target-size architecture**. P4 is deliberately indivisible at the ownership level: current orchestration, persistence generation, receipt/authentication, restart/invalidation, and target-size authority lookup switch together.

P4 must not leave a supported mixed V5/V7 runtime even temporarily at package exit.

## Entry conditions

- P1-P3 accepted and committed.
- New V7 substrate/statistical/execution paths pass their package-local regression while unreachable from production commands.
- A destructive-generation reset is accepted; old derived state is not migrated/reinterpreted.

## Pass P4-A — new current persistence/contract generation

Define the new current campaign/prepare/target-size persistence generation and record set.

Required end state:

- V7 records authenticate neutral substrate, P_train/M3, pi_train/pi_eval, common preparation, exact candidates, paired-seed study/evidence, selected N/T_selected;
- no current record contains label-domain target-size maps, CV plans, domain prefix digests, complement roles, or old FEAS/MVIDX/MVSEL/REPAIR/MVQUAL authority lineage;
- old V5/current derived records are not translated into V7 objects.

### Verification cycle

1. schema/serialization/digest tests;
2. SQLite round-trip/reopen tests through the real campaign store;
3. negative loading tests for V5-derived state under V7 generation;
4. structural record-key inspection.

## Pass P4-B — atomic prepare/select-target-size orchestration switch

Switch current production orchestration in one coherent change:

```text
current config/parser
 -> V7 neutral substrate
 -> V7 split/orders/preparation/study
 -> V7 candidate materialization/TRAIN2/EVAL2
 -> V7 selected-data freeze
```

At the same time remove current call edges to:

- `TargetDataRoleFreeze`/per-domain target-size role authorities;
- public current FEAS/MVIDX/MVSEL/REPAIR/MVQUAL plans;
- per-domain target-size materialization resolver;
- complement/coarse EVAL2 roles;
- V5 target-size candidate authority/receipt keys.

Preserve the guard that ordinary public `train`/`evaluate` commands cannot become a second screening scheduler.

Forbidden:

- runtime V5/V7 feature flag;
- try-V7/fallback-V5;
- dual authoritative writes;
- V7 wrappers that internally reconstruct old domain maps;
- aliases that reinterpret old schemas as current V7.

### Verification cycle

1. focused orchestration/config tests;
2. source/import structural assertions for forbidden current call edges;
3. bounded real CLI prepare/select-target-size integration using the real store and V7 semantic owners;
4. affected CLI/orchestration regression.

## Pass P4-C — restart/invalidation matrix

Implement and verify the V7 dependency/invalidation semantics.

At minimum:

- same V7 inputs/config reproduce neutral identities, split/orders, preparation, candidate identities, seed set, continuation ancestry and selected data;
- target/evaluation power, fidelity, optimizer-seed-set, split/order, common-preparation or target-size metric changes invalidate target-size descendants appropriately;
- CV-only fold/seed settings do not change/rebuild target-size identity;
- production-only horizon/settings do not change target-size identity;
- old V5 workspace derived state is rejected before candidate reuse with actionable reset/reprepare guidance.

### Verification cycle

1. disk-backed restart/reopen tests;
2. one-change-at-a-time invalidation matrix tests;
3. interrupted boundary resume tests;
4. stale/mismatched authority rejection tests through real loaders/callers, not helper-only proxies.

## Pass P4-D — cutover structural closure

After the switch, prove uniqueness/absence claims structurally:

- current prepare receipt/state keys are V7-only;
- current target-size schemas have no domain maps/CV plans/complement roles;
- current CLI/import/call graph contains no reachable old target-size role/resolver path;
- public exports do not present retired target-size plans as current authority;
- old code may remain only if unreachable and explicitly scheduled for P6 deletion.

Use source/negative assertions where runtime tests cannot prove absence.

## Pass P4-E — package closure

Run fresh stage-local affected regression after all cutover edits.

Required real-owner integration:

```text
real config parser
 -> real CampaignStore/SQLite
 -> current prepare
 -> current select-target-size
 -> V7 materialization/TRAIN2/EVAL2 owners
 -> selected N/T_selected persisted
 -> restart/reopen authentication
```

Expensive training may be bounded/faked below the semantic owners, but the current CLI/store/orchestrator/state transitions under acceptance may not be mocked or bypassed.

## Exit gate

P4 is accepted only when:

> V7 is the sole reachable current target-size runtime and persistence generation, deterministic restart works, old derived state fails closed, and no supported runtime path can mix or fall back to V5 semantics.

Commit/tag the accepted P4 checkpoint before P5. Do not begin P5 while any mixed-generation current path remains.
