---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: implementation-reopened
created_date: 2026-09-08
reviewed_date: 2026-09-08
reviewed_candidate_head: 6f7eecac70f566cbf08969a2fbaa6f08ba22ca4d
implementation_review_verdict: no-pass
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
reviewed_repair_head: 33ef00d3294c3121021a326603000356379822f7
entrypoint: This file is the sole active implementation authority. The accepted multi-size source repairs and generalized foundation architecture are preserved. The candidate is reopened only for the bounded parser-ownership repair, acceptance strengthening, current real-foundation execution evidence, final affected regression/integration, and small test simplification defined below. Archived relatives are historical evidence only.
---

# MLFF multi-size repair, foundation initialization, and final acceptance closure

## 0. Independent review verdict

**NO-PASS / implementation reopened for bounded repair and executable acceptance only.**

The reviewed candidate is:

```text
branch: plan/mlff-target-size-multi-selection-reviewed
head:   6f7eecac70f566cbf08969a2fbaa6f08ba22ca4d
```

The implementation is substantially correct. No new scientific architecture defect, multi-size architecture defect, or foundation-family ownership defect was found. In particular, the existing generalized foundation machinery already provides one canonical family/head identity path for MACE-MH-1 and MACE-MPA-0-medium, and the existing TOML template already derives the narrow model-dependent configuration surface.

The candidate remains open for four material reasons:

1. the new `init [model]` convenience is implemented by a facade argv scanner rather than the real `init` parser/command owner, and the scanner is observably ambiguous for valid global option values;
2. the new P3/P5 optimizer counterfactual test reaches the correct real materializers but does not explicitly prove that its separate campaigns compare the same exact frozen target membership/TargetBinding;
3. the user's requirement to make sure both real foundation models are functional still lacks fresh execution evidence on this candidate; historical real-model evidence is useful but cannot substitute for current bounded execution; and
4. final affected regression/integration/project checks have not executed or been recorded on the assembled candidate. GitHub exposes no attached commit-status checks for the reviewed head.

These are bounded implementation/acceptance issues. They do **not** justify another wrapper, registry, family-specific template, model abstraction, currentness system, scheduler, or architectural redesign.

---

## 1. Product / scientific invariants

The following Tier-1 requirements remain binding:

1. A selected target size means exact prefix membership `T_N = pi_train[:N]`.
2. The frozen multi-size design is one ordered unique-by-N collection. Size is an experiment dimension, not an implicit winner or reducer.
3. `cross-validate` freezes the complete selected collection atomically before numerical CV work.
4. CV and final production are distinct roles over one shared post-selection method.
5. CV evidence may authorize production only when current for the exact method, CV policy, TargetBinding, CV plan, and accepted CV record.
6. Before any new multi-size production job, every frozen size must have current accepted CV ancestry. One missing/stale/corrupt/incomplete/rejected size means zero new production jobs for that invocation.
7. Target-size screening and post-selection training retain separate optimizer authorities:

```text
Target-size screen
    [target_data.size_convergence.optimizer_normalization]
        -> size-dependent realized lr(N), ema_decay(N)

Post-selection CV + final production
    [training]
        -> one shared PostSelectionMethodIdentity
        -> shared lr / ema / ema_decay
```

8. Newly initialized scientific configuration explicitly states material post-selection optimizer defaults.
9. Foundation family and selected source head are scientific identity. A multi-head checkpoint must never silently fall back to another head.
10. Supported default foundation identities are:

```text
MH-1
    family = mace_mh_1
    default selected source head = omat_pbe

MPA-0-medium
    family = mace_mpa_0
    selected source head = default
```

11. Public initialization supports:

```text
init
init mh-1
init mpa-0
```

Bare `init` defaults to MH-1. The positional spelling is convenience only and must normalize into the existing canonical family/configuration authority.
12. `k > 1` remains a completed training experiment, not a release-selection rule.
13. Production-scale/GPU/LAMMPS qualification remains distinct and deferred. Bounded CPU/e3nn real-model smoke is functional acceptance, not production qualification.

---

## 2. Frozen high-level architecture

### 2.1 Multi-size/P5 architecture

Preserve the already accepted architecture:

- one `CampaignStore` is the mutable campaign authority;
- one ordered selected-size collection, not scalar-plus-list dual authority and not per-size subcampaigns;
- one prepared generation shared by all selected sizes;
- changed prepared scientific identity creates a fresh generation with empty selection;
- TargetBinding remains role-neutral;
- method, CV policy, and production policy remain role-specific identities outside TargetBinding;
- existing binding-keyed P5 persistence is reused;
- collection-wide production preflight is transient admission, not persisted state;
- per-size final-production authorization remains a second currentness/race fence;
- serial outer-size orchestration remains acceptable/preferred;
- lifecycle/status remains read-only advisory observation;
- k>1 qualification remains informational/read-only and consequential release qualification fails closed.

### 2.2 Foundation/configuration architecture

There is one canonical foundation route:

```text
public CLI syntax
    -> real init parser / command owner
    -> canonical foundation family/head values
    -> existing _config_template(...)
    -> [foundation] + existing model/path/display compatibility fields
    -> MaceFoundationSpec / inspect_mace_foundation
    -> FoundationPotentialIdentity
    -> existing doctor/acceleration/extraction/P3/P5 owners
```

The generated family-dependent TOML surface remains narrow and centrally owned. For the default heads it includes, as already implemented:

```text
mh-1
    campaign.id = lta-mh1-omat-pbe-finetune
    [foundation].family = mace_mh_1
    [foundation].head = omat_pbe
    [foundation].label = MACE-MH-1
    [model].foundation_name = MACE-MH-1
    [paths].foundation_model = /path/to/mace-mh-1.model

mpa-0
    campaign.id = lta-mpa0-finetune
    [foundation].family = mace_mpa_0
    [foundation].head = default
    [foundation].label = MPA-0-medium
    [model].foundation_name = MPA-0-medium
    [paths].foundation_model = /path/to/mace-mpa-0-medium.model
```

Do not fork the TOML template or create per-family configuration classes. Shared fields remain shared unless real model semantics demonstrate a family-dependent requirement.

MH-1 remains a multi-head foundation and must use exact source-head semantics/extraction where a single training foundation is required. MPA-0 remains single-head and must not be forced through MH-1-specific extraction machinery.

---

## 3. Reviewed implementation accepted in substance

The following source behavior is accepted and should not be reworked unless executable acceptance exposes a concrete defect.

### 3.1 P5 currentness and production admission

The previously repaired P5 currentness model remains correct:

- current CV plan validates current method identity and current CV-policy identity;
- CV acceptance authenticates exact plan/method/CV-policy/binding ancestry plus `accepted == true`;
- collection preflight checks every frozen size before production is marked RUNNING or any new production trainer/final plan is admitted;
- per-size final production repeats authorization immediately before final-plan construction.

Do not move role-specific method/policy identity into TargetBinding.

### 3.2 Optimizer authority split

The generated `[training]` explicitly retains:

```toml
learning_rate = 1.0e-4
ema = true
ema_decay = 0.99999
```

Target-size-screen optimizer normalization remains independently owned by `[target_data.size_convergence.optimizer_normalization]`.

The new acceptance test correctly moved beyond helper-only equality and observes actual MACE configuration files emitted by the P3 and P5 materializers. Preserve that real-owner boundary.

### 3.3 Generalized foundation owner

Current source inspection finds no family-specific architectural fork that must be repaired. The canonical foundation owner already distinguishes:

- MPA-0: single `default` head and its structural checkpoint contract;
- MH-1: multi-head checkpoint including `omat_pbe` plus the MH-1 structural contract.

Existing current tests also already contain real-checkpoint acceptance hooks using `MDSTATS_TEST_MH1_MODEL` and `MDSTATS_TEST_MPA0_MODEL`. Reuse them rather than inventing another real-model harness.

---

## 4. Blocking repair F-CLI1 — move `init [model]` into the real parser owner

### Finding

The candidate implements `init mh-1` / `init mpa-0` in `mdstats/training_data/campaign_cli.py` by scanning argv and using:

```python
init_index = values.index("init")
```

This is the wrong ownership boundary for a parser feature and creates a real ambiguity. For example, a valid global option value can itself be the literal `init`:

```text
--config init init mh-1
```

The facade can mistake the configuration filename for the command token and fail to normalize the actual model argument. Similar option-order sensitivity follows from manually interpreting token position outside argparse.

The facade therefore became more complex while the real core parser still does not describe the public positional syntax.

### Required repair

Reduce the implementation rather than patching the scanner:

1. add one optional positional model argument to the real `init` subparser in `_campaign_cli_core.build_parser()`;
2. accept only the public values needed for this product surface (`mh-1`, `mpa-0`) at that parser/normalization boundary;
3. normalize the positional spelling to the existing canonical `mace_mh_1` / `mace_mpa_0` family before `_config_template(...)` is called;
4. retain existing `--foundation-family` compatibility;
5. if both forms are supplied with equivalent meaning, reduce to one semantic family choice;
6. if both conflict, fail before config/state creation;
7. delete `_INIT_MODEL_FAMILIES`, `_normalize_init_model_argv`, and the facade-specific error handling once the core parser/command owns the feature;
8. restore `campaign_cli.py` to a thin facade over the core public entry point.

A tiny core normalization helper is acceptable only if it reduces duplicated comparison logic in `command_init`; do not create a registry or second configuration object.

### Acceptance

Through the public CLI and real parser:

```text
init
    -> MH-1 default

init mh-1
    -> mace_mh_1 / omat_pbe

init mpa-0
    -> mace_mpa_0 / default
```

Also cover parser robustness that the facade scanner cannot guarantee:

```text
--config init init mh-1
    -> succeeds and writes the requested config named "init"

init --workspace <path> mh-1
    -> parser-owned positional semantics remain correct if argparse accepts this ordering

init mh-1 --foundation-family mace_mh_1
    -> one equivalent semantic choice

init mh-1 --foundation-family mace_mpa_0
    -> fails before config/state creation

init unsupported-model
    -> clear parser/user error
```

Keep the existing legacy direct-parser init tests green.

---

## 5. Acceptance repair T6/T7 — prove the counterfactual compares the same frozen target lineage

### Finding

`tests/test_mlff_post_selection_materialization_acceptance.py` now exercises the real P3/P5 materializers, which is the correct semantic boundary. However, it compares three independently constructed campaigns and currently proves only that each fixture reaches the expected selected size internally. The test does not explicitly assert that the base, screen-mutated, and post-selection-method-mutated cases use the same exact `T_N`, training order, and role-neutral TargetBinding.

For the intended counterfactual, the optimizer policy must be the only changed scientific axis. A test that accidentally compares different target membership/lineage could still produce apparently sensible optimizer differences while weakening the claim.

### Required repair

Keep the current real-owner test and strengthen its oracle; do not add another harness.

Before comparing P3/P5 materializations, resolve the frozen selected design/context for all campaigns and establish at minimum:

- identical selected N;
- identical exact selected membership `T_N` in order;
- identical training-order identity;
- identical role-neutral TargetBinding identity wherever the independent fixture construction is expected to be content-identical.

If a path-only fixture detail makes full TargetBinding digest equality intentionally differ, prove the exact product-semantic target lineage components directly and document why the path detail is non-semantic. Prefer making the fixtures content-identical rather than weakening the oracle.

Then retain the existing real-materialization assertions:

```text
change screen normalization LR/EMA
    -> actual P3 realized optimizer changes
    -> P5 CV/production lr/ema/ema_decay + method identity unchanged

change [training] LR/EMA
    -> actual P5 CV/production lr/ema/ema_decay + method identity change
    -> actual P3 normalized optimizer unchanged

CV vs production
    -> same shared P5 optimizer/method
    -> different frozen H_cv/H_prod budgets
```

Where economical, assert the expected realized P3 LR/EMA values for at least one selected size, not merely collection inequality. Existing dedicated normalization tests remain the formula authority and may be reused rather than re-derived in this integration test.

---

## 6. Test simplification F-TEST1 — remove redundant synthetic foundation coverage

### Finding

`tests/test_mlff_campaign_init_foundation_models.py` adds a synthetic `MaceFoundationInspection` fixture and a family-resolution test. The repository already has stronger canonical coverage in `tests/test_mlff_mh1_id1_foundation_identity.py`, including:

- both family resolutions;
- exact head behavior;
- species checks;
- missing/invalid head failure;
- cross-family structural mismatch failure;
- real mounted-checkpoint identity tests.

The new synthetic resolver test therefore duplicates a weaker version of an existing owner test.

### Required cleanup

Keep the new module focused on the new product surface: `init [model]` public/parser behavior and generated TOML.

Remove or consolidate the redundant synthetic foundation-inspection fixture/test and rely on the existing canonical foundation suite for family/head semantics. Do not create another family fixture hierarchy.

This cleanup is not an independent architecture blocker, but it is part of this round's minimum-complexity closure and should occur while touching the test file for F-CLI1.

---

## 7. Required current real-foundation acceptance F-REAL1

### Finding

Historical qualification establishes that both real checkpoints worked in earlier source states, but the user explicitly requested that both MH-1 and MPA-0 be made sure functional now. The reviewed candidate has no fresh attached execution evidence for the real checkpoints.

This is therefore a **required final functional acceptance item**, not an optional "if convenient" smoke. If the model files are unavailable in one implementation environment, carry this exact acceptance to the nearest model-equipped environment; do not convert absence into a pass.

### Locked real inputs

Use the known locked identities unless the user explicitly supplies a different accepted model revision:

```text
MACE-MH-1
    head: omat_pbe
    sha256: ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde

MACE-MPA-0-medium
    head: default
    sha256: 75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
```

### Required bounded CPU/e3nn evidence

Reuse the existing current tests/harnesses rather than inventing new machinery. At minimum execute the applicable real-asset cells covering:

1. exact checkpoint SHA, direct inspection, family/head resolution:
   - `tests/test_mlff_mh1_id1_foundation_identity.py::test_id1_real_uploaded_checkpoints_inspect_and_resolve_exactly`
2. current MACE/e3nn checkpoint loading for both models:
   - `tests/test_mlff_mh1_dep0_runtime_freeze.py::test_real_mh1_and_mpa0_checkpoints_load_through_e3nn_reference_path`
3. real CPU inference/descriptor path for both models and correct selected heads:
   - `tests/test_mlff_mh1_data6_1.py::test_data6_1_real_uploaded_models_match_official_and_native_batch`
4. MH-1 selected `omat_pbe` extraction/parity where the current training path requires a single extracted head:
   - `tests/test_mlff_mh1_extract1_selected_head.py::test_extract1_real_mh1_omat_pbe_extraction_and_parity`
5. existing P5 foundation provider/method regression relevant to source-family/head propagation, including the current bounded provider owner tests.

Environment variables should point to the two supplied files:

```text
MDSTATS_TEST_MH1_MODEL=<path-to-mace-mh-1.model>
MDSTATS_TEST_MPA0_MODEL=<path-to-mace-mpa-0-medium.model>
```

Record exact commands and pass/fail/skip counts in this workplan. A skip because files are absent is not final closure evidence for F-REAL1.

### Explicit boundary

This acceptance is bounded CPU/e3nn functionality. It does **not** authorize a positive CuEq/GPU/LAMMPS production qualification claim. GPU/deployment qualification remains deferred to the established final-release/user-machine stage.

---

## 8. Final affected regression/integration T8

After F-CLI1, T6/T7 strengthening, and F-TEST1 cleanup, re-derive the affected surface and execute final acceptance on one unchanged candidate.

At minimum cover:

### Initialization/configuration/foundation

- `tests/test_mlff_campaign_init_foundation_models.py` after consolidation;
- `tests/test_mlff_campaign_cli.py`;
- `tests/test_mlff_mh1_config1_campaign_defaults.py`;
- affected foundation identity/head-resolution/head-extraction/inference tests;
- F-REAL1 real-model cells above on a model-equipped environment.

### Optimizer/materialization/currentness

- `tests/test_mlff_post_selection_materialization_acceptance.py`;
- canonical shared optimizer-settings tests;
- target-size optimizer-normalization tests;
- focused P5 CV-plan/currentness/production-authorization tests;
- affected P5 production/restart/publication/store tests.

### Multi-size assembled behavior

- `tests/test_mlff_target_size_multi_size_integration.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- assembled `prepare -> select N1 -> select N2 -> cross-validate -> train-production -> reload/status` through real owners with bounded numerical doubles;
- generation rollover and stale-publication/currentness integration inherited from the multi-size contract;
- affected lifecycle/storage/qualification regression.

### Repository/project checks

- project-configured fast lint/type/static checks actually supported for the touched Python surface;
- `python -m compileall mdstats tests` or repository-equivalent syntax validation.

If the affected surface cannot be bounded confidently after the parser/test edits, run the broader supported repository suite.

A required command that does not execute is incomplete evidence, not a pass. Newly introduced failures or failures plausibly intersecting this affected surface block closure. Demonstrably pre-existing unrelated failures may be attributed precisely.

Record exact commands, candidate SHA, environment essentials, and concise result summaries under Section 10. Do not create another handoff/evidence file merely to hold these results.

---

## 9. Simplicity and anti-shortcut constraints

Do not add:

- another foundation/model registry;
- per-family TOML templates or config classes;
- filename-based family/head inference;
- silent multi-head fallback;
- another argv preprocessor/scanner to repair the current scanner;
- another currentness registry or collection evidence object;
- wrapper bindings or synchronized state;
- another post-selection optimizer resolver;
- CV-specific/production-specific duplicate LR/EMA tables;
- a new scheduler/generic experiment framework;
- another P5 numerical harness;
- another synthetic foundation fixture hierarchy duplicating the canonical foundation tests.

The preferred F-CLI1 repair is **reduction**: move the public positional into the parser that already owns init syntax and remove the facade scanner.

If the stronger acceptance tests expose a genuine production-owner defect, alter that existing owner directly.

---

## 10. Implementation evidence — to be filled by Implementation

Do not mark this plan complete until evidence is recorded here for the final candidate.

Record:

```text
final_candidate_head: <sha>
python: <version>
mace: <version>
torch: <version>
e3nn: <version>
real_mh1_sha256: <sha or unavailable>
real_mpa0_sha256: <sha or unavailable>
```

Then record exact commands and concise outcomes for:

1. F-CLI1/init/config focused tests;
2. T6/T7 real-materialization acceptance;
3. P5 currentness/zero-new-production regression;
4. multi-size assembled integration;
5. F-REAL1 real MH-1/MPA-0 bounded CPU/e3nn acceptance;
6. final affected regression;
7. project static/lint/type checks actually configured;
8. compileall/syntax check.

If an external model-equipped run is needed, record its exact command/environment and merge the result here before final independent review.

---

## 11. Next independent review closure conditions

The next Software Design review may PASS and close/archive this plan only when all of the following are true on the final assembled candidate:

### C1 — parser ownership and init semantics

```text
init
    -> canonical MH-1 default

init mh-1
    -> canonical mace_mh_1 / omat_pbe config

init mpa-0
    -> canonical mace_mpa_0 / default config

valid global option values / option ordering
    -> cannot confuse model normalization

conflicting positional + --foundation-family
    -> fails before config/state creation
```

The facade argv scanner is gone; no replacement scanner/registry was added.

### C2 — exact counterfactual target lineage

The optimizer-independence acceptance explicitly proves the compared campaigns use the same exact selected N/T/training-order/role-neutral target lineage before attributing changes to optimizer policy.

### C3 — real materialization authority split

```text
change screen normalization LR/EMA
    -> actual P3 optimizer changes
    -> actual P5 CV/production optimizer + method do not

change [training] LR/EMA
    -> actual P5 CV/production optimizer + method change
    -> actual P3 normalized optimizer does not

CV vs production
    -> same P5 shared method/optimizer
    -> distinct frozen role horizons
```

### C4 — stale CV never authorizes production

```text
stale/changed CV policy + accepted-looking old evidence
    -> never authorizes current production

any one frozen size with invalid CV ancestry
    -> zero new production jobs for the invocation
```

### C5 — both real foundation families current

On the final candidate and exact locked model files:

```text
MH-1 / omat_pbe
    -> inspect + resolve + CPU/e3nn load/inference + required selected-head extraction pass

MPA-0 / default
    -> inspect + resolve + CPU/e3nn load/inference pass
```

No cross-family fallback or head ambiguity is tolerated.

### C6 — final functional closure

All required affected regression/integration/project checks execute on the final candidate and are recorded in Section 10. No required check is silently converted to inspection evidence.

### C7 — simplicity

The final change does not leave redundant argv-normalization machinery or redundant synthetic family-test ownership. No new architectural mechanism was introduced to close a parser/test/evidence gap.

---

## 12. Review routing

All currently known remaining work is now contained in this workplan. No additional review amendment or sibling workplan is needed for the known issues above.

Route the next step to **Software Implementation** on the same branch. Implementation should repair F-CLI1, strengthen T6/T7, simplify the duplicate synthetic foundation test, execute F-REAL1 and T8, and record evidence in this file.

If those steps expose a genuine contradiction in the Frozen architecture, reopen only that affected design surface. Otherwise, do not reopen architecture merely because an executable check fails; repair the existing owner under this plan.
