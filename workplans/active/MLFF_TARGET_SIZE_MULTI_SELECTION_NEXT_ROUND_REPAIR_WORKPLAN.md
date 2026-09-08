---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: implementation-reopened
created_date: 2026-09-08
reviewed_date: 2026-09-08
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
implemented_head: 33ef00d3294c3121021a326603000356379822f7
implementation_review_verdict: no-pass
supersedes:
  - MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_WORKPLAN.md
  - MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_IMPLEMENTATION_REVIEW_REOPEN.md
  - MLFF_TARGET_SIZE_MULTI_SELECTION_POST_SELECTION_OPTIMIZER_DEFAULTS_REVIEW_ADDENDUM.md
entrypoint: This file is the sole active implementation authority. The source repair is accepted in substance; the workplan is reopened only for the bounded real-owner acceptance and final regression/integration closure below. Archived relatives are historical evidence, not additional implementation entry points.
---

# MLFF multi-size target selection — next-round repair workplan

## 0. Independent implementation review verdict

**NO-PASS / implementation reopened for acceptance closure only.**

The submitted implementation at `33ef00d3294c3121021a326603000356379822f7` correctly repairs the two source-level defect families that motivated this round:

1. P5 CV currentness and collection-wide production admission are now checked at the existing owners; and
2. newly initialized campaign configuration explicitly exposes the separate post-selection LR/EMA defaults while preserving target-size-screen optimizer normalization as a distinct authority.

No high-level redesign and no further source mechanism are presently justified.

The remaining blockers are acceptance-integrity gaps:

- mandatory T6 does not exercise the bounded CV/final-production MACE materialization boundary required by this workplan;
- mandatory T7 stops at `_optimizer_policy_for(...)` rather than exercising the real post-selection orchestration/materialization owner; and
- T8 final affected regression/integration has no reviewable execution evidence attached to the assembled candidate.

These are genuine blockers under Protocol 5.16 because a green helper-level test can survive while the production caller/materializer is wrong, and an unexecuted or unevidenced required final regression cannot be accepted by inspection.

Do **not** create another amendment, handoff, wrapper, registry, or test framework. Close these gaps in this file and through the existing production owners/test fixtures.

---

## 1. Problem / product invariants

The following Tier-1 scientific/product invariants remain binding:

1. A selected target size means the exact prefix membership `T_N = pi_train[:N]`.
2. The frozen multi-size design is one ordered unique-by-N collection. Size is an outer experiment dimension, not an implicit reducer or winner.
3. `cross-validate` freezes the complete collection atomically before numerical CV work.
4. CV and production are distinct roles over one shared post-selection training method.
5. CV evidence may authorize production only when it is current for the exact method, CV policy, TargetBinding, and CV plan.
6. Before any new production job for a multi-size invocation, every frozen size must have current accepted CV ancestry. One missing/stale/corrupt/incomplete/rejected size means zero new production jobs for the invocation.
7. Target-size screening and post-selection training have separate optimizer authorities:

```text
Target-size screen
    [target_data.size_convergence.optimizer_normalization]
        reference_target_size
        reference_learning_rate
        reference_ema_decay
    -> size-dependent lr(N), beta(N)

Post-selection CV + final production
    [training]
        learning_rate
        ema
        ema_decay
        other shared optimizer fields
    -> one shared PostSelectionMethodIdentity
```

8. Newly initialized scientific configuration explicitly states material post-selection optimizer defaults.
9. `k > 1` is a completed training experiment, not a release-selection rule; no hidden first/last/best/auto winner exists.
10. Production-scale/GPU qualification remains separate and deferred.

---

## 2. Frozen high-level architecture

Preserve the accepted architecture exactly through this closure round.

### 2.1 Campaign and target-selection authority

- one `CampaignStore` remains the mutable campaign authority;
- selected sizes are one ordered collection, not scalar-plus-list dual state and not per-size subcampaigns;
- one prepared generation is shared by all selected sizes;
- changed prepared scientific identity rolls to a fresh generation with empty selection; unchanged prepare preserves the current design.

### 2.2 Role-neutral target lineage

Per selected size:

```text
FrozenEntry_i
    N_i
    exact T_i
    training order
    H_cv_i
    H_prod_i
    selection provenance

TargetBinding_i
    current generation
    accepted prepared/P1/P2 lineage
    N_i
    exact T_i
    training-order identity

CV_i
    TargetBinding_i
    + shared method identity
    + CV policy(H_cv_i)
    + exact CV plan/evidence ancestry

Production_i
    TargetBinding_i
    + shared method identity
    + accepted CV ancestry
    + production policy(H_prod_i)
```

Method identity, CV policy, production policy, selection source, and automatic-diagnostic provenance must not be pushed into `TargetBinding` to solve a role-currentness problem.

### 2.3 P5 persistence and production admission

- reuse the existing binding-keyed P5 store and pointer namespaces;
- the collection-wide production gate remains an admission check over existing per-size authorities, not persisted state;
- the existing per-size production authorization remains a second-line race/currentness fence after collection preflight;
- serial outer-size orchestration remains acceptable/preferred; no new scheduler is authorized.

### 2.4 Configuration ownership

The screen normalization table and `[training]` remain independent configuration owners. Equal numerical defaults are allowed; semantic coupling is not. Do not create CV-specific or production-specific duplicate LR/EMA tables unless a future scientific design explicitly changes the shared-method architecture.

### 2.5 Observation and qualification preservation

The existing public lifecycle observer remains a read-only, durable-state/advisory projection; consequential commands re-establish current configuration admission for themselves. This review does **not** authorize new lifecycle currentness machinery merely because an advisory route can subsequently fail admission under an edited config.

For `k > 1`, qualification remains informational/read-only and consequential P7 paths fail before attempts, locked evidence, or release selection are opened.

---

## 3. Source-level repair findings — accepted and frozen for this closure

The following implementation results were independently inspected and are accepted in substance. Do not rework them unless the strengthened real-owner tests expose a defect.

### 3.1 CV plan role-currentness

`campaign_post_selection_runtime.resolve_current_cv_plan(context)` now validates the persisted plan and rejects when either relation is false:

```text
plan.method_identity_digest == context.method.content_digest
plan.cv_policy_identity_digest == context.cv_policy.content_digest
```

This is the correct role boundary; `TargetBinding` remains role-neutral.

### 3.2 Exact acceptance-policy ancestry

`post_selection_cv_acceptance.require_cv_acceptance_for_method(...)` now requires:

```text
acceptance.cv_plan_digest == plan.content_digest
acceptance.method_identity_digest == current method
acceptance.cv_policy_identity_digest == plan.cv_policy_identity_digest
acceptance.selected_binding_digest == current binding
acceptance.accepted == true
```

No second acceptance type or currentness registry was added.

### 3.3 Collection-wide zero-new-production barrier

`_cv_admission_blockers(contexts)` now resolves/authenticates each size's current plan and acceptance, reuses the real acceptance authorization, gathers blockers across the complete collection, and runs before the production stage is marked RUNNING or any per-size production loop begins.

`execute_final_production(context)` still repeats the exact per-size authorization immediately before final-plan construction. Preserve both boundaries.

### 3.4 Explicit post-selection optimizer defaults

The generated `[training]` section now explicitly emits:

```toml
learning_rate = 1.0e-4
ema = true
ema_decay = 0.99999
```

with comments identifying these as post-selection CV/final-production settings and pointing target-size screening to its separate optimizer-normalization table.

The target-size screen continues to materialize its realized per-N learning rate and EMA decay from its own normalization policy. Post-selection materialization continues to emit `lr`, `ema`, and `ema_decay` from the shared post-selection optimizer policy.

---

## 4. Blocking finding R1 — T6 is below its required real materialization boundary

### Problem

The implemented `test_t6_post_selection_independence_counterfactual` compares:

- `resolve_shared_optimizer_settings(...)`, and
- `resolve_target_size_optimizer_normalization_policy(...)`.

That proves the two configuration resolvers are independent, but mandatory T6 requires more: for a frozen selected size, the **actual bounded CV/final-production MACE configuration** must remain unchanged when only screen normalization changes, and must change when the shared `[training]` method changes.

A defect in the public caller or materialization wiring could therefore survive the current T6 while both resolver helpers remain correct.

### Required repair

Strengthen or replace the existing T6 test using the already-existing real-owner P5 fixture. Do not add a parallel harness.

The test must drive enough of the real post-selection path that the MACE configuration produced by production code is the observed artifact. The expensive MACE numerical execution may remain substituted below that boundary.

Prove both directions:

1. **Screen-only mutation**
   - keep the frozen selected N/T and post-selection `[training]` method fixed;
   - change only screen `reference_learning_rate` / `reference_ema_decay`;
   - execute/materialize bounded post-selection CV and final production through the real owners;
   - assert actual materialized P5 `lr`, `ema`, `ema_decay` and shared method identity are unchanged.

2. **Post-selection-method mutation**
   - change only `[training].learning_rate` / `[training].ema_decay` (and rerun the required CV under the changed method before production);
   - assert actual materialized P5 `lr` / `ema_decay` and method identity change as governed;
   - separately prove the target-size-screen normalization owner remains unchanged.

Equivalent two-campaign counterfactuals are acceptable if they preserve the same frozen N/T scientific comparison more cleanly than mutating one campaign in place.

---

## 5. Blocking finding R2 — T7 bypasses the owner under acceptance

### Problem

The implemented `test_t7_cv_production_shared_method_consistency` directly calls:

```text
_optimizer_policy_for(context, planned_epochs=H_cv)
_optimizer_policy_for(context, planned_epochs=H_prod)
```

and compares the resulting policies.

That is useful helper coverage, but it does not establish the workplan's T7 claim: **the real CV and final-production orchestration/materialization paths receive the same shared LR/EMA method**. The current real-owner integration harness records the actual run requests and real materialized MACE config paths, but T7 does not inspect them.

A production-caller defect that substitutes or mutates an optimizer after `_optimizer_policy_for(...)` could leave current T7 green.

### Required repair

Use the existing `PostSelectionHarness` and real public post-selection commands. Keep the numerical double strictly below the production owner.

At minimum:

1. freeze one selected size with deliberately distinct CV and production horizons;
2. run real `cross-validate` with the existing bounded harness;
3. from the actual CV request(s), load the MACE configuration written by `materialize_post_selection_run(...)` and record `lr`, `ema`, `ema_decay`, method identity, and planned epoch budget;
4. run real `train-production` with the same bounded harness;
5. load the actual production MACE configuration(s) from the production request(s);
6. assert CV and production use the same shared `lr`, `ema`, `ema_decay` and method identity;
7. assert the role-specific epoch budgets remain distinct and equal to the frozen H_cv/H_prod values.

Prefer replacing/consolidating the current helper-only T7 assertions rather than layering another redundant test beside them.

---

## 6. Blocking finding R3 — final affected regression/integration evidence is absent

### Problem

T8 is a mandatory functional-acceptance boundary. The implementation commit changes executable production admission/currentness and configuration initialization, but the remote candidate contains no recorded T8 command/results and GitHub exposes no commit-status checks for `33ef00d3294c3121021a326603000356379822f7`.

This review environment could inspect source but could not execute the repository's Conda test environment. Therefore the required final functional closure cannot be inferred from source inspection or from the existence of new test functions.

This does **not** assert that the implementer never ran tests; it means the required evidence is not available to close independent review.

### Required repair

After the T6/T7 acceptance tests are strengthened, run the final assembled affected-surface regression in the repository's required `mace` environment and record the exact commands plus pass/fail summary in **this workplan** under an implementation-evidence section. Do not create a second handoff file.

At minimum execute the still-applicable T8 surface:

- focused P5 CV-plan/currentness/production-authorization tests;
- canonical shared optimizer-settings tests;
- target-size optimizer-normalization tests;
- TRAIN2 generated-config/init tests;
- `tests/test_mlff_target_size_multi_size_integration.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- affected P5 production/restart/publication/store tests;
- affected lifecycle/storage/qualification regression;
- assembled `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` integration through real owners with bounded numerical doubles;
- generation-rollover / stale-publication affected integration inherited from the parent multi-size contract;
- project-configured fast static/lint/type checks that are actually supported for this affected Python surface;
- `python -m compileall mdstats tests` or repository-equivalent syntax check.

Re-derive the final affected surface after the test edits. If it cannot be bounded confidently, run the broader repository suite supported by the environment.

A required command that cannot execute remains incomplete evidence and must be reported as such; do not convert it to an inspection pass.

No production-scale/GPU qualification is required.

---

## 7. Mandatory next-review acceptance

The next independent Design review may close this workplan only when all of the following are established on the final assembled candidate:

### C1 — source repair preservation

The source-level currentness/admission/default repairs in Section 3 remain intact with no new parallel authority or wrapper machinery.

### C2 — real materialization independence

Through actual P5 materialization:

```text
change screen reference LR/EMA
    -> post-selection CV/production MACE lr/ema/ema_decay unchanged

change [training] LR/EMA
    -> post-selection method + actual CV/production MACE lr/ema/ema_decay change
    -> target-size screen normalization authority unchanged
```

### C3 — real CV/production shared method

Actual materialized CV and production configurations for the same frozen design carry the same shared method identity and LR/EMA values, while their frozen role horizons differ as configured.

### C4 — stale CV never authorizes production

The existing T1-T3 real-owner tests remain green:

```text
old/stale CV policy + accepted-looking evidence + same TargetBinding
    -> never authorizes current production

any one frozen size with invalid CV ancestry
    -> zero new production jobs for the invocation
```

### C5 — explicit initialized defaults

A newly generated campaign still explicitly contains post-selection `learning_rate`, `ema`, and `ema_decay`, separately from target-size optimizer-normalization reference values.

### C6 — final functional closure

The T8 affected regression/integration/static evidence executes on the final candidate and is recorded in this workplan.

---

## 8. Expected affected surface for this bounded reopen

The expected source behavior should require little or no additional production-code change unless the stronger tests expose a real defect.

Primary test/evidence surfaces:

```text
tests/test_mlff_target_size_optimizer_normalization.py
tests/test_mlff_target_size_multi_size_integration.py
tests/_mlff_post_selection_fixture.py            # reuse only; change only if needed to expose existing request/config evidence
```

Production owners that the tests must exercise, not bypass:

```text
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/post_selection_cv_acceptance.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/target_size_execution/schedule.py
mdstats/training_data/target_size_execution/candidate.py
```

The final regression surface remains broader as listed in Section 6.

---

## 9. Simplicity and anti-shortcut constraints

This is an acceptance-closure round, not another architecture round.

Do not add:

- another currentness registry;
- wrapper bindings or synchronized state;
- a collection-level CV evidence object;
- a new preflight state machine;
- a second post-selection optimizer resolver;
- CV-specific or production-specific duplicate LR/EMA tables;
- aliases between `[training]` and target-size normalization;
- initialization-only migration state;
- a new scheduler or generic experiment framework;
- a new test harness duplicating `PostSelectionHarness`.

Do not weaken or delete an acceptance assertion to obtain a pass. The repaired test must make the real production owner/materializer observable so a defect there would fail the test.

If the stronger test exposes a production wiring bug, fix that existing owner directly and rerun the complete affected surface. Prefer alteration/removal over additive machinery.

---

## 10. Closure condition

The workplan remains **implementation-reopened / NO-PASS** until R1-R3 and C1-C6 close on one final candidate.

When they close and no new genuine product/Frozen-architecture blocker remains:

1. independent Software Design review may mark PASS;
2. archive this workplan as completed;
3. update `workplans/active/README.md` so there is no stale active implementation entry;
4. preserve production/GPU qualification as the separately deferred activity already governed by current product/release policy.
