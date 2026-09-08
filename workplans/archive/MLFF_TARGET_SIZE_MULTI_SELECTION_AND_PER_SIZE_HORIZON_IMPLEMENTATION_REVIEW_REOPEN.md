---
kind: implementation-workplan-review-amendment
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON-IMPLEMENTATION-REVIEW-REOPEN
parent_workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON
protocol_version: 5.16.0
status: implementation-reopened
reviewed_date: 2026-09-08
reviewed_branch: plan/mlff-target-size-multi-selection-reviewed
reviewed_head: 28847ede101a6f87a482643d6a4cc5d415bc02ca
reviewed_implementation_commit: f4a0e7722aebc860eec678f7592c338c5683094e
implementation_review_verdict: no-pass
precedence: This amendment reopens the parent workplan only for the bounded P5 CV-currentness and collection-wide production-admission repair below. Every non-conflicting product invariant, Frozen architecture decision, compatibility rule, simplicity constraint, and acceptance requirement in the parent remains binding. No high-level architecture change is authorized.
---

# Multi-size target selection — implementation review reopen

## 0. Review verdict

**NO-PASS / implementation reopened.**

The submitted implementation is structurally close to the accepted design and no high-level redesign is required. The review found one genuine blocking defect family at the existing P5 CV-currentness / final-production admission boundary.

The defect violates the parent workplan's R4, Section 3.5, Section 7.1, O8/O10, Frozen requirements 13 and 20, and A9/A12: a production invocation may treat stale or semantically inconsistent CV evidence as current, and the collection-wide preflight does not perform the same semantic authorization that each per-size production owner performs later. Therefore the required guarantee "if any selected size has missing/stale/corrupt/incomplete/rejected CV, start zero new production jobs" is not established.

This is an implementation nonconformance, not a design deficiency. Repair the existing owners directly; do not add a second currentness registry, wrapper binding, preflight state machine, compatibility layer, or collection-level evidence object.

## 1. Blocking finding — P5 CV currentness is incomplete before production admission

### 1.1 Current CV-plan resolution omits current method/policy identity

`campaign_post_selection_runtime.resolve_current_cv_plan(context)` currently loads the binding-keyed CV-plan pointer and authenticates selected binding, P1 relation/projection, and replay lineage through `validate_post_selection_cv_plan(...)`.

It does **not** reject the plan when either of these current role identities changed:

```text
plan.method_identity_digest    != context.method.content_digest
plan.cv_policy_identity_digest != context.cv_policy.content_digest
```

The second omission is especially important. `CvValidationPolicyIdentity` contains more than the frozen H_cv snapshot: fold count, partition seed, fold construction, monitor/purge allocation, acceptance metric/threshold, aggregation/dispersion policy, and required CV seeds are also scientific/methodological CV-policy inputs. A post-freeze edit to one of those non-horizon fields is a new CV question and must not let old accepted evidence authorize production.

Frozen H_cv behavior remains unchanged: later edits to the generic configured CV epoch default do not rewrite the frozen per-size H_cv. The repair must compare against the **resolved current per-size CV policy**, whose horizon is already overridden by the frozen entry.

### 1.2 Acceptance authorization does not fully prove policy ancestry

`post_selection_cv_acceptance.require_cv_acceptance_for_method(...)` currently checks:

- acceptance -> exact plan digest;
- acceptance -> current method digest;
- acceptance -> selected binding digest;
- `accepted == True`.

It does not verify that `acceptance.cv_policy_identity_digest` equals the supplied plan's `cv_policy_identity_digest`.

A campaign acceptance is defined as evidence for one exact CV plan/method/policy/binding. The authorization owner must prove that relation rather than rely on a caller having constructed the record correctly in the past.

### 1.3 The collection-wide barrier checks only the acceptance record and boolean

`campaign_post_selection_runtime._cv_admission_blockers(contexts)` currently resolves only `resolve_current_cv_acceptance(context)` and tests whether the record exists and has `accepted=True`.

It does not resolve/authenticate the current CV plan and does not invoke the existing semantic acceptance guard before the public `train-production` loop begins.

Consequences:

1. a binding-current `accepted=True` record can pass preflight even when its CV plan is missing, unreadable, stale, or semantically inconsistent;
2. a CV-only policy change can leave old accepted evidence reachable by the same TargetBinding and allow production without re-cross-validation;
3. for a multi-size design, a defective later size can be discovered only inside `execute_final_production()` after an earlier size has already started or published new production work, violating the zero-new-job collection barrier.

The existing A12 integration test covers a **missing acceptance** on N2, but not the stale/corrupt/currentness cases explicitly required by A12. Its green result therefore does not close the accepted production-admission claim.

## 2. Required repair — alter the existing currentness path, do not add machinery

### R1 — make `resolve_current_cv_plan(context)` role-current

Strengthen the existing resolver so a stored/current pointer is returned as a current CV plan only when all existing structural/currentness checks pass **and**:

```text
plan.method_identity_digest == context.method.content_digest
plan.cv_policy_identity_digest == context.cv_policy.content_digest
```

Keep the existing binding, relation/projection, and replay-lineage validation. A mismatch must fail closed as stale methodological evidence and require `cross-validate` under the newly resolved method/policy.

Do not encode method or CV policy into `TargetBinding`; that would regress the R1 role decomposition. The check belongs at CV-role currentness.

### R2 — complete the existing acceptance authorization relation

Alter `require_cv_acceptance_for_method(...)` (renaming only if that materially improves clarity) so it also requires:

```text
acceptance.cv_policy_identity_digest == plan.cv_policy_identity_digest
```

Retain its existing exact-plan, method, binding, and accepted-verdict checks. Do not create a second acceptance type or a parallel production-admission record.

### R3 — make the collection preflight reuse the real per-size authorization

Rework `_cv_admission_blockers(contexts)` so, for **every** frozen context before any production work is admitted, it:

1. resolves the current CV plan through the strengthened `resolve_current_cv_plan(context)`;
2. resolves the current CV acceptance;
3. rejects missing/unreadable plan or acceptance;
4. invokes the strengthened existing acceptance authorization against the context's current method and selected binding;
5. gathers all known blocking N/reasons;
6. returns success only when every frozen size passes the exact same semantic authorization required by final production.

The public `execute_current_train_production()` must not mark production RUNNING, publish a new final plan, or invoke a production trainer until this complete preflight succeeds.

Do not duplicate a weaker set of digest comparisons inside the barrier. Reuse the corrected real owners so the preflight and per-size execution cannot drift into two definitions of "current accepted CV".

### R4 — preserve the existing second-line per-size guard

`execute_final_production(context)` should continue to re-check its own exact CV authorization immediately before building/publishing a final plan. The collection preflight is a stage-admission barrier; it is not a reason to remove the per-size fail-closed guard that protects against races after preflight.

## 3. Mandatory repair acceptance

### A-R1 — single-size CV-policy currentness

Through the real public owners with the existing bounded numerical seam:

1. create/freeze one selected size;
2. run accepted CV under policy A;
3. edit a **non-horizon** CV-policy input such as `acceptance_maximum`, `fold_count`, or `partition_seed` without rerunning CV;
4. call real `train-production`;
5. assert failure occurs before any production trainer request and before a new final-production plan/publication is made current;
6. rerun `cross-validate` under policy B and prove production can then proceed.

Also retain the existing positive regression that later edits to configured generic CV/production epoch defaults do not mutate already frozen H_cv/H_prod snapshots.

### A-R2 — collection-wide stale/corrupt late-member barrier

Use a two-size frozen design whose CV was initially accepted for both sizes. Make only the later size's CV ancestry invalid below the owner boundary while leaving the earlier size apparently usable. At minimum cover one of:

- current CV-plan pointer names a missing/unreadable plan object;
- acceptance and plan carry inconsistent policy ancestry;
- another self-consistent stale CV record is reachable under the same current TargetBinding but is not current for the resolved role policy.

Then call the real public `train-production` and prove:

- zero new production trainer invocations for **all** sizes;
- no new final-production plan/publication is made current for the earlier size;
- all known blocking N values/reasons are reported;
- existing immutable historical evidence remains untouched.

Do not satisfy this with a unit call to `_cv_admission_blockers` alone; the acceptance boundary is the assembled public production owner.

### A-R3 — exact acceptance ancestry

Construct or reuse a validly serialized `CvCampaignAcceptance` whose selected binding is current and `accepted=True` but whose `cv_policy_identity_digest` disagrees with the referenced/current plan. The real authorization path must reject it before production admission.

### A-R4 — affected regression

After repair, rerun at least:

- the focused P5 CV-plan/currentness/production authorization tests;
- `tests/test_mlff_target_size_multi_size_integration.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- affected P5 production/restart/publication/store tests;
- affected lifecycle/storage/qualification regression touched by the repair;
- the assembled `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` integration;
- `python -m compileall mdstats tests` or the repository-equivalent syntax check.

No production-scale/GPU qualification is required for this repair.

## 4. Reviewed surfaces that do not require redesign/reopen

The review found no blocking architectural drift in the following implemented areas:

- ordered unique-by-N collection authority and duplicate-N replacement-in-place;
- per-size H_cv/H_prod snapshots and reset semantics;
- advisory auto recommendation routed through the same merge owner;
- atomic whole-collection freeze;
- corrected v3 TargetBinding decomposition with bounded exact v2 compatibility;
- changed-prepare generation rollover to an empty design;
- binding-keyed multi-size P5 storage rather than per-size subcampaigns;
- serial outer-size orchestration/resource ownership;
- coherent multi-binding lifecycle snapshot;
- multi-size terminal training-experiment state and no implicit winner;
- k>1 qualification fail-closed before session/attempt/locked opening;
- sibling-aware P5 storage/retention structure.

The public CV command's choice to stop admitting later expensive sibling CV work after a rejection is **not** a blocker: parent Section 6.3 explicitly delegates continue-versus-stop after truthful rejection, provided the campaign is not falsely accepted and no size is removed.

## 5. Closure condition

The parent workplan remains reopened until the P5 CV-currentness family above is repaired at the existing owner boundaries and A-R1 through A-R4 pass.

A subsequent Software Design review should specifically falsify:

```text
old CV policy + accepted=True + same TargetBinding
    -> NEVER authorizes current production

any one frozen size with invalid CV ancestry
    -> ZERO new production jobs for the invocation
```

If those claims close and no new genuine blocker is found, close/archive the parent workplan and this amendment together. Do not reopen the frozen multi-size architecture merely to implement this bounded currentness repair.
