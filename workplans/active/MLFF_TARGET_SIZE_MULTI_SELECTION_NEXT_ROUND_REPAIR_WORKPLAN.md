---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: implementation-reopened
created_date: 2026-09-08
reviewed_date: 2026-09-08
scope_extension_date: 2026-09-08
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
reviewed_repair_head: 33ef00d3294c3121021a326603000356379822f7
entrypoint: This file is the sole active implementation authority. It preserves the accepted multi-size source repair and adds only the bounded real-owner acceptance closure plus MH-1/MPA-0 initialization and family verification below. Archived relatives are historical evidence only.
---

# MLFF multi-size repair, real-owner acceptance, and foundation-model initialization

## 0. Current verdict and objective

The multi-size source repair is accepted in substance but remains **NO-PASS / implementation-reopened** until real-owner acceptance and final affected regression close.

Already-correct source behavior to preserve:

1. P5 CV currentness checks the current method and current CV policy.
2. CV acceptance proves exact CV-policy ancestry.
3. Multi-size production has a collection-wide zero-new-production admission barrier.
4. Target-size-screen optimizer normalization and post-selection optimizer configuration are separate authorities.
5. Newly initialized TOML explicitly writes post-selection `learning_rate`, `ema`, and `ema_decay`.

This round also adds one bounded user-facing extension:

- both supported foundation families, **MACE-MH-1** and **MACE-MPA-0-medium**, remain first-class functional inputs to the current generalized foundation path; and
- public initialization accepts `init [model]`, where `model` is exactly `mh-1` or `mpa-0`; omitted model defaults to `mh-1`.

No high-level architecture change is authorized. Do not add another model registry, family-specific template, currentness authority, scheduler, test harness, or compatibility state.

## 1. Product/scientific invariants

1. Selected target size remains exact prefix membership `T_N = pi_train[:N]`.
2. The frozen multi-size design remains one ordered unique-by-N collection; size is an experiment dimension, never an implicit winner.
3. `cross-validate` freezes the complete collection atomically.
4. CV and production are distinct roles over one shared post-selection method.
5. CV may authorize production only for the exact current method, CV policy, TargetBinding, CV plan, and accepted CV record.
6. Before any new multi-size production job, every frozen size must have current accepted CV ancestry. One invalid size means zero new production jobs for the invocation.
7. Target-size screening owns its size-normalized optimizer policy; post-selection CV/final production own the shared `[training]` optimizer policy.
8. `k > 1` remains a completed training experiment, not a release-selection rule.
9. Foundation family/head are scientific identity. A multi-head checkpoint must never silently fall back to another head.
10. Supported foundation defaults are:
   - MH-1: canonical family `mace_mh_1`, default selected head `omat_pbe`;
   - MPA-0-medium: canonical family `mace_mpa_0`, selected head `default`.
11. Bare `init` defaults to MH-1. `init mh-1` and `init mpa-0` are CLI convenience syntax only and must normalize into the existing foundation/configuration authority.
12. Production-scale/GPU/deployment qualification remains separate and deferred.

## 2. Frozen architecture

### 2.1 Multi-size and P5 authority

- one `CampaignStore` remains the mutable campaign authority;
- one ordered selected-size collection, not scalar-plus-list dual state;
- one prepared generation shared by all selected sizes;
- changed prepared scientific identity creates a fresh empty generation;
- TargetBinding remains role-neutral; method/CV/production policy identity remains role-specific;
- reuse existing binding-keyed P5 persistence;
- collection production preflight remains transient admission, not persisted state;
- per-size final-production authorization remains the second-line race/currentness fence;
- lifecycle/status remains a durable-state advisory projection and consequential commands re-admit themselves;
- k>1 qualification remains informational/read-only and consequential P7 fails closed.

### 2.2 Foundation-model authority

Reuse the existing generalized path:

```text
public init spelling
    -> canonical family value
    -> existing _config_template(...)
    -> [foundation] family/head/label + existing path/display fields
    -> MaceFoundationSpec / inspect_mace_foundation
    -> exact FoundationPotentialIdentity
    -> existing doctor/acceleration/head-extraction/P3/P5 owners
```

The positional model token is not a second scientific identity. It is only public CLI syntax normalization.

Current generated defaults remain:

```text
mh-1
    family = mace_mh_1
    head = omat_pbe
    label = MACE-MH-1
    default placeholder = /path/to/mace-mh-1.model

mpa-0
    family = mace_mpa_0
    head = default
    label = MPA-0-medium
    default placeholder = /path/to/mace-mpa-0-medium.model
```

There remains exactly one TOML template. Family selection may alter only fields already derived by that template, including campaign identifier, `[foundation]` family/head/label, compatibility display name, and default foundation path placeholder. Do not fork templates or create per-family config classes.

MH-1 remains a multi-head foundation and requires exact selected-head semantics/extraction where the runtime needs a single training foundation. MPA-0 remains single-head and must not be forced through MH-1 extraction machinery.

## 3. Accepted source repair — preserve

`resolve_current_cv_plan(context)` must continue to require current method and CV-policy identity in addition to existing structural/currentness checks.

`require_cv_acceptance_for_method(...)` must continue to require exact plan, current method, exact CV-policy ancestry, current binding, and `accepted == true`.

Every frozen size must pass that same real authorization before production is marked RUNNING or any production trainer/final plan is admitted. Keep the per-size recheck in `execute_final_production`.

Generated `[training]` keeps explicit:

```toml
learning_rate = 1.0e-4
ema = true
ema_decay = 0.99999
```

and target-size-screen normalization remains independently owned by `[target_data.size_convergence.optimizer_normalization]`.

## 4. Blocking acceptance closure R1 — real materialization optimizer independence

Helper-level resolver comparisons are insufficient. Acceptance must inspect actual MACE configuration files written by the existing P3/P5 materializers while substituting only expensive numerical MACE execution below those owners.

Using the existing target-size and `PostSelectionHarness` fixtures, prove:

1. changing only screen reference LR/EMA changes actual target-size-screen MACE LR/EMA but leaves actual post-selection CV/final-production LR/EMA and method identity unchanged;
2. changing only `[training].learning_rate` / `ema` / `ema_decay` changes actual post-selection method and actual CV/final-production MACE LR/EMA while leaving actual screen normalized LR/EMA unchanged;
3. CV and production materializations for one frozen design carry the same shared post-selection optimizer and method identity;
4. their role budgets remain distinct and equal to frozen H_cv/H_prod.

Do not add another P5 numerical test harness.

## 5. Foundation extension F1 — `init [model]`

Public initialization must accept:

```text
init
init mh-1
init mpa-0
```

Rules:

- omitted token -> existing MH-1 default;
- `mh-1` -> canonical `mace_mh_1`;
- `mpa-0` -> canonical `mace_mpa_0`;
- existing `--foundation-family` remains supported;
- positional token plus the same canonical flag reduces to one semantic choice;
- positional token plus conflicting `--foundation-family` fails before config/state creation;
- unsupported positional model remains a parser/user error.

Implement at the narrowest existing public CLI owner and feed the existing core family/template path. Do not duplicate `_config_template` family defaults.

### F1 acceptance

Through public `campaign_cli.main(...)`:

- `init mh-1` writes canonical MH-1 family/head/label/default model placeholder;
- `init mpa-0` writes canonical MPA-0 family/head/label/default model placeholder;
- bare `init` equals MH-1 family defaults;
- conflicting legacy family flag fails without creating configuration;
- existing init regression remains green.

## 6. Foundation extension F2 — both families remain functional

Historical real-model certification is supporting evidence, not a substitute for current source acceptance. The repository already records:

- MPA-0/default current real numerical regression;
- MH-1/omat_pbe exact identity/head resolution, inference, E0, DATA6/DATA7 lineage, selected-head extraction parity, bounded replay training, EVAL/PES lineage, and learned target-head parity;
- GPU/CuEq/LAMMPS deployment portions separately blocked/deferred by runtime availability rather than mdstats architecture.

Current acceptance must preserve the one generalized owner:

- a valid MPA-0 inspection resolves as `mace_mpa_0` / `default`;
- a valid MH-1 multi-head inspection containing `omat_pbe` resolves as `mace_mh_1` / `omat_pbe`;
- cross-family structural mismatch and invalid/missing heads fail closed;
- post-selection foundation identity consumes canonical family/head rather than filename/display label.

If the two supplied real checkpoint files are available in the implementation environment, run bounded current real-asset smoke for both through existing inspection/head/inference owners and record SHA256 plus result. Do not fabricate current real-model execution evidence if those external files are absent.

No GPU qualification claim is authorized by CPU/bounded tests.

## 7. Final affected regression/integration T8

After all executable/test edits, run and record exact commands and summaries in this file. At minimum cover:

- new `init [model]` and family tests;
- existing campaign CLI/init tests;
- affected foundation inspection/head-resolution/head-extraction/inference tests;
- real-materialization optimizer acceptance from Section 4;
- focused P5 CV-plan/currentness/production-authorization tests;
- canonical shared optimizer-settings and target-size optimizer-normalization tests;
- `tests/test_mlff_target_size_multi_size_integration.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- affected P5 production/restart/publication/store tests;
- affected lifecycle/storage/qualification regression;
- assembled multi-size `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` integration;
- generation-rollover/stale-publication integration;
- project-configured fast static/lint/type checks actually supported for the affected Python surface;
- `python -m compileall mdstats tests` or equivalent.

Re-derive the final affected surface. If it cannot be bounded confidently, run the broader supported repository suite. A required command that cannot execute is incomplete evidence, not an inspection pass. Production-scale/GPU qualification remains deferred.

## 8. Simplicity constraints

Do not add:

- another foundation/model registry beyond the existing family authority;
- per-family TOML templates/config classes;
- filename-based scientific family inference;
- silent multi-head fallback;
- another currentness registry or collection evidence object;
- wrapper bindings/synchronized state;
- a second post-selection optimizer resolver;
- a new scheduler/generic experiment framework;
- a second P5 numerical test harness.

A tiny CLI normalization at the existing public facade is acceptable because it removes user spelling before the canonical parser/template/scientific owner sees the request; it must carry no independent model semantics beyond the two explicit public aliases.

If stronger tests expose an owner wiring bug, alter that existing owner directly.

## 9. Closure conditions

Independent Design review may close/archive this plan only when all are true on one final candidate:

```text
stale/changed CV policy + accepted-looking old evidence
    -> never authorizes current production

one invalid frozen size
    -> zero new production jobs

change screen normalization LR/EMA
    -> actual P3 screen changes
    -> actual P5 CV/production optimizer does not

change [training] LR/EMA
    -> actual P5 CV/production method/materialization changes
    -> actual P3 screen normalized optimizer does not

CV vs production
    -> same shared post-selection optimizer/method
    -> distinct frozen role horizons

init or init mh-1
    -> canonical mace_mh_1 / omat_pbe configuration

init mpa-0
    -> canonical mace_mpa_0 / default configuration

both family contracts
    -> resolve through one generalized foundation owner and fail closed on mismatch

final affected regression/integration
    -> executed and recorded on final candidate
```

When these close with no new genuine blocker, archive this workplan and remove the stale active entry. Production/GPU qualification remains separate and deferred.

## 10. Implementation evidence

Not yet complete. The implementation agent must append exact final-candidate commands/results here after the assembled affected-surface run. Historical real-foundation evidence may be cited separately but must not be relabeled as a current test run.
