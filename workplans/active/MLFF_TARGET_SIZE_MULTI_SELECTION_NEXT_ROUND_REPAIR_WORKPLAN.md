---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: implementation-complete
created_date: 2026-09-08
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
reviewed_code_candidate: f4a0e7722aebc860eec678f7592c338c5683094e
reviewed_head: 28847ede101a6f87a482643d6a4cc5d415bc02ca
supersedes:
  - MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_WORKPLAN.md
  - MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_IMPLEMENTATION_REVIEW_REOPEN.md
  - MLFF_TARGET_SIZE_MULTI_SELECTION_POST_SELECTION_OPTIMIZER_DEFAULTS_REVIEW_ADDENDUM.md
entrypoint: This file is the sole active implementation authority for the next repair round. The superseded parent/review artifacts are historical evidence only and need not be reconciled by the implementer.
---

# MLFF multi-size target selection — next-round repair workplan

## 0. Objective and current verdict

The multi-size target-selection implementation is substantially aligned with the accepted scientific and architectural design. Independent review found two bounded remaining repair families:

1. **P5 CV currentness / collection-wide production admission** is incomplete: stale or semantically inconsistent CV evidence can still appear accepted before production, and the collection preflight does not yet prove the same complete per-size authorization that final production requires.
2. **Post-selection optimizer defaults are not fully explicit at campaign initialization**: CV/final-production LR and EMA are already owned separately from the size-normalized target-size screen, but newly generated TOML exposes `learning_rate` while leaving `ema` and `ema_decay` to hidden resolver defaults.

No high-level redesign is authorized or required. Repair the existing owners directly, preserve the already-correct architecture, and close with affected regression/integration.

## 1. Problem / product invariants

The implementation must preserve these Tier-1 product/scientific invariants:

1. A selected target size means the exact prefix membership `T_N = pi_train[:N]`; no downstream stage may silently substitute another membership.
2. The frozen multi-size design is an ordered unique-by-N collection. Duplicate N replaces that entry in place; new distinct N appends; reset clears the provisional collection.
3. `cross-validate` atomically freezes the whole selected collection. Size is an outer experiment dimension for CV and production, not a hidden reducer or implicit winner.
4. CV and production are distinct roles over the same post-selection training method. CV evidence must be current for the exact method, exact CV policy, exact TargetBinding, and exact CV plan before it may authorize production.
5. Before **any new production work** for a multi-size invocation, every frozen size must have current accepted CV ancestry. If one size is missing/stale/corrupt/incomplete/rejected, start zero new production jobs for that invocation.
6. Target-size screening asks a different controlled question from post-selection training. Its optimizer LR/EMA are size-normalized under the screen-specific normalization authority; CV and production use a separate post-selection optimizer authority.
7. Newly initialized scientific configuration must explicitly expose material post-selection optimizer defaults so the generated TOML is self-describing and reproducible.
8. k>1 remains a training experiment, not an implicit release-selection mechanism. No cross-size winner/reducer/qualification shortcut is introduced.
9. Production-scale/GPU qualification remains separate and deferred; bounded functional/regression/integration testing is required here.

## 2. Frozen high-level architecture

The following architecture is already accepted and remains Frozen for this repair cycle:

### 2.1 One campaign, one collection authority

- One `CampaignStore` remains the mutable campaign authority.
- Selected target sizes are one ordered collection, not scalar-plus-list dual state and not per-size subcampaigns.
- One prepared generation is shared by all selected sizes.
- Changed prepared scientific identity creates a fresh generation with an empty selection; unchanged prepare preserves the current design.

### 2.2 Role-neutral target lineage and role-specific policy identity

Per selected size:

```text
FrozenEntry_i  # orchestration/audit
    N_i
    exact T_i
    training order
    H_cv_i
    H_prod_i
    selection provenance

TargetBinding_i  # role-neutral scientific target lineage
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

Do not put method, CV policy, production policy, selection source, or auto-diagnostic provenance into `TargetBinding` merely to repair currentness.

### 2.3 Existing binding-keyed P5 persistence

- Reuse the existing binding-keyed P5 store and pointer namespaces.
- Do not add another currentness registry, collection evidence object, wrapper binding, preflight state machine, or synchronized compatibility authority.
- The collection-wide production gate is an admission check over the existing per-size authorities; it is not new persisted state.

### 2.4 Separate optimizer owners

The intended configuration/identity split is:

```text
Target-size screen
    [target_data.size_convergence.optimizer_normalization]
        reference_target_size
        reference_learning_rate
        reference_ema_decay
    -> per-N update geometry
    -> lr(N)
    -> beta(N)

Post-selection CV + final production
    [training]
        learning_rate
        ema
        ema_decay
        other shared optimizer fields
    -> one shared PostSelectionMethodIdentity
    -> same method executed by CV and final production
```

Numerical equality of defaults across the two owners is allowed. Semantic coupling is not.

### 2.5 Scheduling and qualification

- Serial outer-size orchestration remains acceptable/preferred; do not add a new scheduler.
- Existing per-size production authorization remains a second-line race/currentness fence even after collection preflight is strengthened.
- k>1 qualification remains read-only/informational; consequential qualification must fail before opening attempt/locked evidence.

## 3. Repair family A — complete P5 CV currentness before production

### A1. Make current CV-plan resolution role-current

Strengthen the existing `campaign_post_selection_runtime.resolve_current_cv_plan(context)` path so a stored pointer is considered current only when all existing binding/P1/replay/plan validation succeeds **and**:

```text
plan.method_identity_digest == context.method.content_digest
plan.cv_policy_identity_digest == context.cv_policy.content_digest
```

The current per-size CV policy already resolves the frozen `H_cv`; compare against that resolved policy. A mismatch means stale methodological evidence and requires rerunning CV.

Do not move these identities into `TargetBinding`.

### A2. Complete acceptance ancestry validation

Strengthen the existing `post_selection_cv_acceptance.require_cv_acceptance_for_method(...)` authorization so it also requires:

```text
acceptance.cv_policy_identity_digest == plan.cv_policy_identity_digest
```

Retain the existing exact-plan, method, selected-binding, and `accepted == True` checks. Do not create another acceptance type.

### A3. Make collection preflight reuse the real per-size authorization

Rework `_cv_admission_blockers(contexts)` (or an equivalent existing owner if locally simplified) so **every frozen size is fully authorized before any production work begins**:

1. resolve/authenticate its current CV plan;
2. resolve/authenticate its current CV acceptance;
3. reject missing/unreadable/stale/corrupt plan or acceptance;
4. invoke the corrected existing semantic acceptance authorization against the context's current method and binding;
5. gather all known blocking N/reasons;
6. succeed only when every frozen size passes.

`execute_current_train_production()` must not mark production RUNNING, publish a new final plan/publication, or invoke a production trainer until this full preflight succeeds.

Do not duplicate a second weaker set of digest comparisons in the barrier; reuse the corrected real owner(s).

### A4. Preserve the per-size second-line guard

`execute_final_production(context)` must continue to re-check exact CV authorization immediately before final-plan construction/publication. The collection barrier prevents partial admission; the per-size guard remains the race/currentness fence after preflight.

## 4. Repair family B — explicit post-selection LR/EMA defaults at initialization

### B1. Preserve optimizer-authority independence

Do not route CV/final production through target-size optimizer normalization, and do not make target-size screening consume `[training].learning_rate` or `[training].ema_decay` as its normalization reference.

The target-size screen continues to realize its MACE configuration from the per-N normalized LR/EMA values. CV/final production continue to resolve their optimizer from the canonical shared `[training]` settings.

### B2. Emit explicit post-selection defaults from `init`

Alter the existing `_config_template(...)` training section directly so newly initialized configurations explicitly contain:

```toml
[training]
learning_rate = 1.0e-4
ema = true
ema_decay = 0.99999
```

These are the existing canonical resolved defaults and are the current accepted conservative fine-tuning defaults. The generated comments should state that they govern post-selection CV and fresh final production, while the screen derives per-N LR/EMA from `[target_data.size_convergence.optimizer_normalization]`.

Keep the built-in resolver defaults for compatibility with existing historical configs that omit these keys. Do not create an initialization-only default table or migration layer.

### B3. Do not force artificial numerical inequality

Do not change either default set merely so the two owners have different numbers. Independence is proved by ownership and counterfactual behavior, not by arbitrary value inequality.

## 5. Mandatory acceptance

Acceptance must exercise real semantic owners with bounded numerical doubles only below the expensive MACE boundary.

### T1. Single-size CV-policy currentness

Through the public post-selection owner:

1. create/freeze one selected size;
2. run accepted CV under policy A;
3. change a **non-horizon** CV-policy field such as `acceptance_maximum`, `fold_count`, or `partition_seed` without rerunning CV;
4. call real `train-production`;
5. prove failure occurs before any production trainer request and before a new final-production plan/publication becomes current;
6. rerun `cross-validate` under policy B and prove production can then proceed.

Retain the positive regression that later edits to generic configured CV/production epoch defaults do not rewrite already frozen per-size `H_cv/H_prod`.

### T2. Collection-wide stale/corrupt late-member barrier

With two frozen sizes whose CV was initially accepted, invalidate only the later size below the owner boundary while leaving the earlier size apparently usable. Cover at least one materially strong case such as:

- current CV-plan pointer naming a missing/unreadable object;
- acceptance and plan carrying inconsistent policy ancestry;
- self-consistent stale CV evidence under the same TargetBinding that no longer matches the resolved current role policy.

Call the real public `train-production` and prove:

- zero new production trainer invocations for all sizes;
- no new final-production plan/publication becomes current for the earlier size;
- all known blocking N/reasons are surfaced;
- existing immutable historical evidence remains untouched.

A unit-only call to `_cv_admission_blockers` is insufficient for this claim.

### T3. Exact acceptance-policy ancestry

Construct/reuse a validly serialized `CvCampaignAcceptance` with current selected binding and `accepted=True`, but with `cv_policy_identity_digest` inconsistent with the referenced/current plan. The real authorization path must reject it before production admission.

### T4. Generated-config visibility

Call the real `_config_template(...)` or public `init` path and parse the resulting TOML. Assert a new campaign explicitly contains:

```text
training.learning_rate == 1.0e-4
training.ema == true
training.ema_decay == 0.99999
```

and separately contains the target-size optimizer-normalization reference LR/EMA fields.

### T5. Screen independence counterfactual

From one initialized configuration:

1. change only `[training].learning_rate` and `[training].ema_decay`;
2. resolve/materialize a target-size candidate at fixed N/batch geometry;
3. prove the screen normalization policy and realized `lr(N)` / `beta(N)` are unchanged;
4. then change only `reference_learning_rate` / `reference_ema_decay` and prove the realized screen values change as expected.

### T6. Post-selection independence counterfactual

For a frozen selected size:

1. change only the screen normalization reference LR/EMA;
2. resolve the post-selection shared optimizer settings and bounded CV/final-production MACE configuration;
3. prove CV/final-production `lr`, `ema`, and `ema_decay` are unchanged;
4. then change only `[training].learning_rate` / `[training].ema_decay` and prove the post-selection method/executable configuration changes while the screen normalization owner does not.

### T7. CV/production shared-method consistency

Using real post-selection policy construction/materialization with MACE replaced only below the semantic owner, prove CV and final production receive the same shared post-selection `learning_rate`, `ema`, and `ema_decay`; only role-specific budgets/policies differ.

### T8. Final affected regression/integration

After all executable edits, rerun at least:

- focused P5 CV-plan/currentness/production-authorization tests;
- canonical shared optimizer-settings tests;
- target-size optimizer-normalization tests;
- TRAIN2 generated-config/init tests;
- `tests/test_mlff_target_size_multi_size_integration.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- affected P5 production/restart/publication/store tests;
- affected lifecycle/storage/qualification regression touched by the repair;
- assembled `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` integration;
- `python -m compileall mdstats tests` or repository-equivalent syntax check.

Re-derive the final affected surface from the assembled candidate. If impact is broader than these named suites, include the additional affected regression rather than treating this list as a ceiling.

Production-scale/GPU qualification is **deferred** and is not required for this repair.

## 6. Expected affected surface

Likely direct owners/consumers include:

```text
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/post_selection_cv_acceptance.py
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/training_settings.py          # inspect/preserve canonical defaults; change only if genuinely needed
mdstats/training_data/post_selection_execution.py   # regression/identity consumer
mdstats/training_data/post_selection_identity.py    # regression/identity consumer
mdstats/training_data/target_size_execution/schedule.py   # regression/preserve screen owner
mdstats/training_data/target_size_execution/candidate.py  # regression/preserve realized screen values
campaign.toml.example                               # reconcile only if generated/default docs drift
relevant architecture/user-guide docs              # update only if current behavior text is stale
```

Tests should be added/strengthened near the existing P5 currentness, optimizer-settings, target-size normalization, config-template, and multi-size integration suites rather than creating a parallel test harness.

## 7. Implementation authority

### Frozen

- exact target membership and ordered multi-size collection semantics;
- whole-collection freeze;
- role-neutral `TargetBinding` decomposition;
- one shared post-selection method validated by CV and executed by production;
- role-specific CV/production policy identities and frozen per-size horizons;
- collection-wide zero-new-production admission barrier;
- one CampaignStore and existing binding-keyed P5 persistence;
- separate target-size normalization authority versus shared post-selection optimizer authority;
- no implicit multi-size release winner/qualification;
- no heavy/GPU qualification during this repair.

### Delegated

- helper/function naming;
- exact internal error text;
- whether existing currentness checks are consolidated into one existing helper or kept in the current owner, provided no duplicate authority is introduced;
- exact placement of generated TOML comments;
- local test fixture organization and bounded MACE doubles below the real owners.

### Reopen only on evidence

Reopen Software Design only if implementation evidence shows one of these Frozen decisions cannot be satisfied without architectural change, e.g.:

- complete CV currentness cannot be represented cleanly through the existing method/policy/plan/acceptance lineage;
- the collection-wide production barrier would require new persisted authority rather than reuse of current owners;
- CV and production genuinely require different scientific optimizer methods rather than the currently accepted shared method;
- target-size normalization and post-selection optimizer semantics cannot remain independently owned without changing the frozen scientific experiment.

Ordinary owner rewiring, validation strengthening, config-template correction, and test repair remain Implementation work.

## 8. Simplicity constraints and implementation sequence

### Stage 1 — repair P5 currentness at existing owners

Strengthen plan currentness, exact acceptance ancestry, and collection preflight together. Close with T1-T3 plus focused affected regression before dependent production-path changes proceed.

### Stage 2 — expose post-selection LR/EMA defaults and prove independence

Update the existing config template directly, add T4-T7, then run T8 final affected regression/integration on the assembled candidate.

Before adding machinery, prefer deleting/replacing a contaminated edge or strengthening the current owner. Do **not** add:

- another currentness registry;
- wrapper bindings or synchronized state;
- a collection-level CV evidence object;
- a new preflight state machine;
- CV-specific or production-specific duplicate LR/EMA tables;
- aliases between `[training]` and target-size normalization;
- initialization-only state/migration machinery;
- a new scheduler or generic experiment framework.

If a proposed repair creates one of those structures, stop and first determine whether direct rewiring/validation of the existing owner can satisfy the same invariant with less total system complexity.

## 9. Closure condition

The next-round implementation is ready for independent Design closure review only when all of the following are true:

```text
old/stale CV policy + accepted-looking evidence + same TargetBinding
    -> never authorizes current production

any one frozen size with invalid CV ancestry
    -> zero new production jobs for that invocation

change screen reference LR/EMA
    -> post-selection CV/production optimizer unchanged

change [training] LR/EMA
    -> target-size screen normalized optimizer unchanged

new campaign init
    -> explicitly writes post-selection learning_rate, ema, ema_decay
```

All other already-reviewed multi-size architecture remains preserved. If these claims close with final affected regression/integration and no new genuine blocker appears, close/archive this workplan.