---
kind: implementation-workplan-review-addendum
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-POST-SELECTION-OPTIMIZER-DEFAULTS-REVIEW-ADDENDUM
parent_workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON
review_amendment_id: MLFF-TARGET-SIZE-MULTI-SELECTION-AND-PER-SIZE-HORIZON-IMPLEMENTATION-REVIEW-REOPEN
protocol_version: 5.16.0
status: implementation-reopened
reviewed_date: 2026-09-08
reviewed_branch: plan/mlff-target-size-multi-selection-reviewed
precedence: This addendum adds one bounded configuration/default obligation to the existing reopened implementation review. It does not change the frozen multi-size architecture or the existing CV-currentness repair requirements.
---

# Post-selection LR/EMA default separation — review addendum

## 0. Verdict

**The execution architecture is correct; generated configuration is incomplete.**

Target-size screening and post-selection CV/final production already have separate optimizer authorities:

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
    -> CV and final production execute the same validated method
```

The numerical defaults currently happen to coincide at the reference point (`1.0e-4`, `0.99999`), but this does **not** make them one authority. Equality of default values is permitted; semantic coupling is not.

The remaining gap is initialization: `_config_template(...)` explicitly emits `[training].learning_rate = 1.0e-4`, but does not emit `[training].ema` or `[training].ema_decay`. Those values therefore resolve only through hidden built-in defaults (`ema = true`, `ema_decay = 0.99999`) even though they materially define the post-selection training method.

For a scientific training workflow, new campaign initialization should expose these method-defining defaults directly in the generated TOML so the initialized configuration is self-describing and reproducible without knowledge of resolver internals.

## 1. Reviewed implementation facts

### 1.1 Screen LR/EMA are size-dependent and screen-owned

`target_size_execution.schedule.TargetSizeOptimizerNormalizationPolicy` owns:

```text
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999

s_N     = ceil(N_ref/B) / ceil(N/B)
lr(N)   = reference_learning_rate * s_N
beta(N) = reference_ema_decay ** s_N
```

`target_size_execution.candidate` then materializes the screen MACE configuration using the realized per-size values rather than `[training].learning_rate` / `[training].ema_decay`.

This is correct and must remain unchanged.

### 1.2 CV and final production share one separate post-selection optimizer method

`training_settings.resolve_shared_optimizer_settings(...)` is the canonical owner for the shared post-selection optimizer semantics and resolves, among other fields:

```text
learning_rate = [training].learning_rate, default 1.0e-4
ema           = [training].ema, default true
ema_decay     = [training].ema_decay, default 0.99999
```

`campaign_post_selection_runtime` builds CV and final-production optimizer policies through the same `_optimizer_policy(...)` execution owner, and `post_selection_execution` writes MACE `lr`, `ema`, and `ema_decay` from that policy.

Therefore CV and final production already use a common post-selection LR/EMA method that is independent of the target-size screen normalization authority. Preserve this architecture.

### 1.3 Initialization does not fully expose the post-selection defaults

The generated campaign TOML currently emits:

```toml
[training]
learning_rate = 1.0e-4
```

but omits:

```toml
ema = true
ema_decay = 0.99999
```

The example configuration already shows all three explicitly, so initialization and the maintained example are unnecessarily inconsistent.

## 2. Required implementation repair

### R-LR1 — keep the two optimizer authorities independent

Do not route post-selection CV/final production through target-size optimizer normalization, and do not make target-size screening consume `[training].learning_rate` or `[training].ema_decay` as its screen reference values.

The two configuration owners remain:

```text
[target_data.size_convergence.optimizer_normalization]
    reference_learning_rate
    reference_ema_decay

[training]
    learning_rate
    ema
    ema_decay
```

Changing one owner must not silently mutate the other role's realized optimizer settings or identity.

### R-LR2 — emit explicit post-selection defaults from `init`

Alter the existing `_config_template(...)` training section directly so newly initialized configurations include at least:

```toml
[training]
learning_rate = 1.0e-4
ema = true
ema_decay = 0.99999
```

These are the current canonical post-selection defaults and are reasonable conservative fine-tuning defaults for the existing method. Do not invent a second initialization-only default table or duplicate resolver.

The generated comments should state that these values govern post-selection CV and fresh final production, while target-size screening obtains its per-N LR/EMA from the separate optimizer-normalization table.

The built-in resolver defaults remain as compatibility/fail-safe behavior for existing configs that omit the keys; initialization should simply make the current resolved method explicit for new campaigns.

### R-LR3 — no forced numerical inequality

Do **not** change values merely so the screen reference and post-selection defaults are numerically different. Their required property is ownership/identity independence, not arbitrary inequality.

If future scientific evidence warrants retuning either set, each may change independently through its own configuration owner and corresponding scientific review.

## 3. Mandatory acceptance

### A-LR1 — generated-config visibility

Call the real `_config_template(...)` / public `init` path and parse the resulting TOML. Assert that a newly initialized campaign explicitly contains:

```text
training.learning_rate == 1.0e-4
training.ema == true
training.ema_decay == 0.99999
```

and separately contains the target-size optimizer-normalization reference LR/EMA fields.

### A-LR2 — screen independence counterfactual

From one initialized configuration:

1. change only `[training].learning_rate` and `[training].ema_decay`;
2. resolve/materialize the target-size screen candidate under fixed N/batch geometry;
3. prove the screen normalization policy and realized `lr(N)` / `beta(N)` are unchanged.

Then change only the screen `reference_learning_rate` / `reference_ema_decay` and prove the realized screen values change as expected.

### A-LR3 — post-selection independence counterfactual

For a frozen selected size:

1. change only the screen optimizer-normalization reference LR/EMA after selection;
2. resolve the post-selection shared optimizer settings and a bounded CV/final-production MACE configuration;
3. prove CV/final-production `lr`, `ema`, and `ema_decay` are unchanged.

Then change only `[training].learning_rate` / `[training].ema_decay` and prove the post-selection method/executable configuration changes while the target-size screen normalization owner does not.

### A-LR4 — CV/production method consistency

Using the real post-selection owners with bounded numerical doubles below MACE, prove CV and final production receive the same shared post-selection `learning_rate`, `ema`, and `ema_decay`; only their role-specific policies/budgets differ.

This test must exercise the production policy construction/materialization path rather than merely comparing configuration dictionaries.

### A-LR5 — affected regression

Rerun the relevant canonical optimizer-settings, target-size optimizer-normalization, TRAIN2 config-template, P5 CV/production identity/execution, and multi-size integration tests together with the repair suite already required by the implementation-review reopen amendment.

No production-scale/GPU qualification is required.

## 4. Simplicity boundary

This correction should be a direct configuration-template and test update around existing owners.

Do not add:

- a second post-selection optimizer resolver;
- a CV-specific LR/EMA table unless a future scientific design explicitly requires CV to train a different method from production;
- a production-specific duplicate optimizer table;
- aliases between `[training]` and the target-size normalization table;
- initialization-only state or migration machinery.

The current architecture already has the correct separation; the repair is to make initialized configuration truthfully expose it.

## 5. Closure condition

The overall workplan remains **NO-PASS / reopened** until both:

1. the existing CV-currentness / collection-wide production-admission blocker is repaired; and
2. new campaign initialization explicitly emits and tests the separate post-selection LR/EMA defaults described here.

A subsequent Design closure review should falsify both directions of accidental coupling:

```text
change screen reference LR/EMA
    -> post-selection CV/production optimizer unchanged

change [training] LR/EMA
    -> target-size screen normalized optimizer unchanged
```

If those claims and the existing currentness repair close with affected regression, this addendum requires no further architecture change.
