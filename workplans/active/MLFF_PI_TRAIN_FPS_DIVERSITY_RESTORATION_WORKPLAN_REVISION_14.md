---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 14
protocol_version: 6.3.0
status: active
created_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_plan_revisions: [13]
reviewed_assembled_candidate: a616f8aa54a80ff003abeb1a2c6b0e882055e4a7
reviewed_r13_implementation_commit: d993f25e28f7d0886ef7628c0a39feeb91adaf33
highest_affected_domain: D4
challenge_state: D4_NO_PASS_FEAS1_RESOURCE_SCOPE_CLOSURE_REQUIRED
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` restoration — Revision 14 FEAS1/NEIGHBOR1 resource-scope closure

## 0. Independent re-review verdict

Fresh independent review of assembled candidate `a616f8aa54a80ff003abeb1a2c6b0e882055e4a7` against Revision 13 and the accepted D1/D2/D3 authority is **NO-PASS**, with one remaining D4 blocker.

Revision 13 successfully closes its two intended findings:

- the campaign RAM budget is now routed through the existing root target-order `StageResourceScope` into COVREF, MVIDX, REPAIR2 and MVQUAL;
- representative COVREF peak RSS is measured under a finite stage budget and remains far inside the envelope;
- the final scientific build remains identical to the R11/R12-correct build;
- the Protocol 6.3 HAS is now represented in the canonical `pem_basis` + `has` interface against the unchanged accepted basis.

However, the R13 evidence itself exposes one still-live target-order stage that bypasses the restored resource owner: **FEAS1/NEIGHBOR1**.

No D1/D2/D3 authority change is required. The accepted execution architecture is coherent; the D4 preparation path is incomplete.

## 1. Protected accepted state

Preserve without redesign:

- every R11 correctness/ownership closure;
- R12 `_StateBatch` exact REPAIR2 optimization, scientific identity, and restart-cost closure;
- R13 root `TARGET-ORDER` resource scope and finite-budget COVREF/MVIDX/MVQUAL routing;
- R13 canonical HAS and accepted PEM basis;
- one exact `P_train`, one complete `pi_train`, exact nested `T_N`;
- sole TargetCoverageReference, canonical obligations, one shared FEAS1/NEIGHBOR1 relation, MVIDX representation, MVSEL2/REPAIR2 order ownership, independent MVQUAL;
- prepare-owned construction/publication and prepared-generation/CampaignStore currentness;
- no new resource manager, selector, repair algorithm, persistence/currentness owner, cleanup owner, or compatibility path;
- final production GPU qualification remains deferred to the complete release package on the stakeholder machine.

## 2. Blocking finding B14-1 — FEAS1/NEIGHBOR1 still bypasses the campaign resource scope

### 2.1 Concrete routing defect

Current `target_order/preparation.py::_build()` invokes:

```python
build_target_coverage_geometry(
    reference,
    build_directory=scratch / "geometry",
    policy=feas_policy,
    global_workers=workers,
    progress_callback=progress,
)
```

with no `resource_scope`.

`build_target_coverage_geometry()` therefore falls back to `_default_scope(...)`, whose `ram_budget_bytes` is explicitly `None`.

The FEAS1 queue then constructs `DeterministicWorkQueue(..., manage_resource_scope=resource_scope is not None)`. On the production path `resource_scope` is `None`, so FEAS1 not only loses the campaign RAM budget but also explicitly declines the queue's `stage_resource_scope()` native-thread quarantine.

This is not merely a telemetry gap. The accepted execution architecture requires:

- target-order sparse execution under the current stage/resource owner;
- outer/native nesting bounded by the stage CPU budget;
- long-stage CPU/RAM/scratch work admitted against the stage plan;
- deterministic queue memory reservations/backpressure to be governed by the finite RAM budget where one exists.

The FEAS1 queue already carries per-task `estimated_memory_bytes`; it simply receives no finite campaign budget in the current production route.

### 2.2 Why Revision 13 cannot close the whole restoration while this remains

R13 correctly proved COVREF is inside its finite inherited budget and that the whole representative prepare happens to peak below the root budget. Those observations do not establish FEAS1 admission semantics:

- empirical whole-process headroom is not a substitute for the D3 rule that new long-stage work is admitted under its resource owner;
- a queue with `ram_budget_bytes=None` cannot backpressure or fail closed against the campaign RAM policy;
- `manage_resource_scope=False` leaves FEAS1's native-thread suppression dependent on ambient process state rather than its own declared stage scope.

Revision 13's evidence explicitly reports this as the one target-order stage the restored route does not reach. That newly surfaced contradiction is material and cannot be deferred merely because Revision 13 did not originally enumerate FEAS1.

## 3. Required repair — complete the existing resource edge, remove the remaining polarity exception

### 3.1 Preparation owner

At `target_order/preparation.py::_build()`:

1. derive a FEAS1/NEIGHBOR1 child `StageResourceScope` from the existing root `resource_scope` when it is present;
2. preserve the existing FEAS1 width semantics: `python_workers=workers`, `tree_workers=1` for the current production path, `blas_threads=1`, `native_openmp_threads=1`, and the same root CPU available/budget values;
3. inherit `ram_budget_bytes` exactly from the root scope;
4. pass that child scope into `build_target_coverage_geometry(..., resource_scope=feas_scope)`;
5. do not create a second resource snapshot, RAM fraction, worker policy, or coordinator.

If no root scope is supplied by an isolated direct caller, the existing FEAS1 default scope may remain the local fallback.

### 3.2 FEAS1 owner

In `target_order/feasibility.py`, delete the remaining conditional override:

```python
manage_resource_scope=resource_scope is not None
```

and let `DeterministicWorkQueue` use its existing default `manage_resource_scope=True`.

Reason: the queue's scope describes the stage's actual Python/tree/BLAS/OpenMP nesting regardless of whether that scope was supplied by the caller or synthesized locally. Budget provenance and native-thread quarantine are independent concerns; the conditional is the last surviving instance of the coupling R13 already removed from MVIDX and MVQUAL.

Do not replace it with another flag or wrapper.

## 4. Required falsification

Add/extend real-owner tests that establish:

1. production `_build_current_target_training_order()` -> `prepare_target_training_order()` -> FEAS1 reaches the same finite root RAM budget;
2. FEAS1's child scope has the exact root CPU available/budget and RAM budget while preserving the existing worker/tree widths;
3. the FEAS1 deterministic queue enters with finite `memory_budget_bytes` and manages its own resource scope;
4. a deliberately small finite budget reaches FEAS1 queue admission and fails closed without host exhaustion or partial geometry publication;
5. direct FEAS1 execution with a locally synthesized scope also applies its own native-thread limits after the conditional override is removed;
6. serial/bounded-parallel FEAS1/NEIGHBOR1 scientific products remain digest-identical under the resource routing;
7. final target-order build/selection/repair/order/MVQUAL identities remain unchanged.

A test double may observe the queue/scope only below the real production/FEAS1 owner and must delegate real queue behavior.

## 5. Representative acceptance evidence

Rerun the same current LTA substrate after the repair and record:

- finite FEAS1/NEIGHBOR1 stage RAM budget inherited from the campaign scope;
- FEAS1 worker/tree/native-thread disposition;
- queue memory budget, peak accounted memory, and backpressure/fail-closed disposition where observable;
- external process RSS peak across FEAS1/NEIGHBOR1, with entry/exit for interpretation;
- whole-prepare peak RSS and wall time;
- complete scientific build identity, REPAIR2 trace/order, Phase-A transition and MVQUAL sizes versus R13;
- no material regression of the already-accepted R12 performance closure.

No arbitrary new time SLA is introduced. If the finite budget is non-constraining, scientific identity must be unchanged. If the current representative workload cannot fit the accepted campaign resource policy, stop and raise a focused D3 resource Challenge rather than bypassing the budget.

## 6. Evidence preserved as applicable

Preserve without rerunning unless the FEAS1 scope change invalidates the regime:

- R11 correctness/ownership evidence;
- R12 bitwise REPAIR2 scalar/native equivalence and current-scale optimization evidence;
- R12 restart-cost closure;
- R13 COVREF finite-budget peak-RSS evidence;
- R13 canonical HAS against accepted `main` `e72090e21cec5311ce87745b03603f8783cd15a7`;
- R13 MVIDX/MVQUAL resource-scope behavior, except where final integration needs to confirm no affected regression;
- baseline-equal unrelated regression failures already attributed outside this scope.

Accepted `main` is unchanged at review time, so no PEM-basis refresh is required.

## 7. Final regression and closeout

After all executable edits:

- rerun `tests/test_mlff_target_order_real_owner.py`;
- rerun all tests materially depending on FEAS1/NEIGHBOR1, target-order preparation, resource scopes, deterministic queue behavior, MVIDX adoption, MVQUAL and campaign prepare routing;
- preserve baseline-equal unrelated failures with explicit attribution; do not skip/xfail them to manufacture green;
- re-run the representative fresh `prepare` because FEAS1 execution semantics/resource management changed;
- perform the Protocol 6.3 closeout-learning assessment. The current observation does not by itself require PEM mutation; update PEM only if admission criteria are independently met.

No CI status is attached to the R13 assembled candidate at review time; implementation-recorded test/benchmark results remain evidence to assess, not CI-attested facts.

## 8. Re-review gate

A fresh independent review may PASS only when:

1. every R11/R12/R13 accepted closure remains intact;
2. the campaign root CPU/RAM scope reaches FEAS1/NEIGHBOR1 through the existing resource-scope interface;
3. FEAS1 no longer disables its own declared native-thread resource scope based on scope provenance;
4. finite-budget queue admission/backpressure/failure behavior is exercised at the real FEAS1 owner;
5. representative FEAS1 and whole-prepare execution remain inside the accepted resource envelope;
6. exact FEAS1/NEIGHBOR1 and final target-order scientific identities remain unchanged;
7. affected final regression introduces no new failure;
8. no new resource-policy/selector/persistence/currentness/cleanup/compatibility owner exists;
9. canonical HAS/PEM basis remains valid or is refreshed if the accepted basis advances.

Until all nine conditions hold, the restoration remains **ACTIVE / D4 NO-PASS** and must not be closed or archived.
