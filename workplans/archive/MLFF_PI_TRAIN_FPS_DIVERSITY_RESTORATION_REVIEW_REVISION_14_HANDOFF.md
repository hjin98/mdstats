---
kind: independent-review-handoff
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 14
protocol_version: 6.3.0
status: active
branch: design/mlff-pi-train-fps-diversity-restoration
reviewed_candidate: a616f8aa54a80ff003abeb1a2c6b0e882055e4a7
verdict: NO-PASS
highest_affected_domain: D4
serious_challenge: false
---

# Revision 14 independent-review handoff

## Verdict

Revision 13 closes its intended RAM-routing/COVREF-peak and canonical-HAS defects, but the assembled candidate remains **NO-PASS** because FEAS1/NEIGHBOR1 still bypasses the campaign resource scope.

## Preserve

Do not reopen without contradictory evidence:

- all R11 correctness/ownership repairs;
- R12 exact batched REPAIR2 and restart-cost closure;
- R13 root target-order resource scope, COVREF peak-memory qualification, MVIDX/MVQUAL budget routing, canonical HAS and unchanged scientific build identity.

## Remaining blocker

`target_order/preparation.py::_build()` calls `build_target_coverage_geometry()` without `resource_scope`.

`target_order/feasibility.py::build_target_coverage_geometry()` therefore synthesizes `_default_scope(...)` with `ram_budget_bytes=None`, then calls its deterministic queue with:

```python
manage_resource_scope=resource_scope is not None
```

so the production FEAS1/NEIGHBOR1 stage has neither the finite campaign RAM admission budget nor its declared stage-native thread quarantine.

This contradicts accepted D3 resource architecture requiring long target-order work to execute under the current stage/resource owner, with bounded outer/native nesting and CPU/RAM admission. The architecture is coherent; this is a D4 routing/concretization defect.

## Repair entry point

Use:

`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_14.md`

Required shape:

1. derive one FEAS1/NEIGHBOR1 child `StageResourceScope` from the existing root target-order scope, preserving current FEAS worker/tree widths and inheriting exact CPU/RAM budgets;
2. pass it into `build_target_coverage_geometry(..., resource_scope=...)`;
3. delete the remaining conditional `manage_resource_scope=resource_scope is not None`; use the queue's existing default management instead;
4. add no new resource manager/policy/wrapper;
5. exercise finite-budget FEAS admission/fail-closed behavior and exact scientific equivalence;
6. rerun representative LTA fresh preparation and affected regression;
7. preserve the R13 canonical HAS unless accepted `main` advances.

## Re-review focus

A subsequent independent review should attempt to falsify:

- FEAS1 actually inheriting the campaign root RAM budget;
- native-thread quarantine remaining active for FEAS whether its scope is inherited or synthesized;
- queue memory admission/backpressure being governed by the finite scope;
- exact FEAS1/NEIGHBOR1 and final target-order identities under the routed scope;
- no regression to R11/R12/R13 closures and no new resource owner.
