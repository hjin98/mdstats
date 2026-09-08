---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: implementation-reopened
created_date: 2026-09-08
reviewed_date: 2026-09-08
reviewed_candidate_head: 0f1d4dbb35f87e394e2b149d02deb6406519ed71
reviewed_executable_head: c3db340e11eb49748f00becd34c422a819daf38a
implementation_review_verdict: no-pass
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
entrypoint: This file is the sole active implementation authority. All already-accepted multi-size, P5-currentness, optimizer-authority, and generalized-foundation behavior is frozen for this round. Rework is limited to the bounded regression-oracle reconciliation and existing P5 foundation-provider acceptance described below. Archived relatives are historical evidence only.
---

# MLFF multi-size / foundation initialization — final acceptance closure

## 0. Current independent review verdict

**NO-PASS / implementation reopened, narrowly.**

The reviewed candidate is `0f1d4dbb35f87e394e2b149d02deb6406519ed71`; its executable source is unchanged from `c3db340e11eb49748f00becd34c422a819daf38a` because the final commit only records workplan evidence.

The substantive implementation is close to closure. The review found no new defect in the multi-size scientific architecture, P5 currentness/production barrier, optimizer-authority separation, generalized MH-1/MPA-0 foundation architecture, or real P3/P5 materialization wiring.

Two blocking acceptance issues remain:

1. **A required affected regression was omitted and is source-deterministically stale.** `tests/test_mlff_mh1_config1_campaign_defaults.py` was explicitly required by this workplan but is absent from the recorded final regression. Its `test_config1_init_defaults_are_explicit_not_environment_autodetected` still asserts that raw parser output has `args.foundation_family == "mace_mh_1"`, while the accepted parser implementation deliberately uses `None` to represent an omitted legacy flag and resolves the product default inside `command_init`. The test therefore cannot pass as written.
2. **F-REAL1 item 5 was not executed.** The recorded real-model command proves exact MH-1/MPA-0 checkpoint identity, CPU/e3nn loading/inference, and MH-1 selected-head extraction parity, but it omits the existing P5 foundation provider/method owner tests required by Section 7.

The first issue is a **test/workplan-oracle deficiency, not a reason to add parser machinery**. The protected product contract is that bare `init` generates the canonical MH-1 configuration. A raw intermediate `argparse.Namespace` value is delegated Tier-2 representation. Restoring that old assertion with a custom argparse action, duplicate explicitness flag, argv scanner, or synchronized parser state would increase product complexity merely to satisfy an obsolete oracle. The correct repair is to update the stale test to observe the resolved product behavior.

No new workplan, wrapper, registry, compatibility state, or architecture revision is authorized.

---

## 1. Core product/scientific invariants

The following remain Tier-1 product truth:

1. Selected target size is exact prefix membership `T_N = pi_train[:N]`.
2. The frozen target design is one ordered unique-by-N collection. Size is an experiment dimension, never an implicit winner.
3. `cross-validate` atomically freezes the complete selected collection.
4. CV and final production are distinct roles over one shared post-selection method.
5. CV may authorize production only for the exact current TargetBinding, method, CV policy, CV plan, and accepted CV ancestry.
6. Before any new multi-size production job, every frozen size must have current accepted CV ancestry. One invalid member means zero new production jobs for the invocation.
7. Target-size screening and post-selection training have independent optimizer authorities:

```text
[target_data.size_convergence.optimizer_normalization]
    -> screen reference LR/EMA
    -> size-dependent realized lr(N), ema_decay(N)

[training]
    -> post-selection learning_rate / ema / ema_decay
    -> one shared PostSelectionMethodIdentity used by CV and production
```

8. New initialized TOML explicitly contains post-selection `learning_rate = 1.0e-4`, `ema = true`, and `ema_decay = 0.99999`.
9. Foundation family and selected source head are scientific identity; multi-head fallback is forbidden.
10. Supported defaults are MH-1 = `mace_mh_1` / `omat_pbe`, MPA-0-medium = `mace_mpa_0` / `default`.
11. Public initialization supports `init`, `init mh-1`, and `init mpa-0`; bare `init` resolves to MH-1.
12. `k > 1` is a completed training experiment but not an implicit release-selection rule.
13. Production-scale/GPU/LAMMPS qualification remains separate and deferred. Bounded CPU/e3nn evidence is functional acceptance only.

---

## 2. Frozen high-level architecture

Preserve without redesign:

- one `CampaignStore` mutable campaign authority;
- one ordered selected-size collection, one prepared generation, no per-size subcampaigns;
- changed prepared scientific identity creates a fresh generation with empty selection; unchanged identity preserves the generation/design;
- TargetBinding remains role-neutral; method/CV/production policy identities remain role-specific;
- existing binding-keyed P5 persistence is reused;
- collection-wide production preflight is transient admission, not new persisted state;
- per-size final production retains its second-line currentness/authorization fence;
- serial outer-size orchestration remains acceptable/preferred; no scheduler is added;
- public observation remains coherent/read-only; k>1 qualification remains fail-closed for consequential release qualification;
- compatibility stays append-only/schema-authentic and does not copy the old role/provenance identity coupling forward.

Foundation/configuration remains one route:

```text
public init syntax
    -> core argparse init owner
    -> canonical family/head resolution in command_init
    -> existing _config_template(...)
    -> [foundation] + existing model/path display fields
    -> MaceFoundationSpec / inspect_mace_foundation
    -> existing doctor / extraction / P3 / P5 owners
```

Do not fork the TOML template or create per-family config classes. MH-1 remains multi-head and uses exact selected-head extraction where the training path requires a singleton foundation; MPA-0 remains single-head and is not forced through MH-1 extraction machinery.

---

## 3. Implementation already accepted — do not churn

### 3.1 P5 currentness and production barrier

Current source correctly:

- rejects a stored CV plan when its method identity differs from current method authority;
- rejects it when its CV-policy identity differs from the resolved current per-size CV policy;
- requires CV acceptance to bind the exact plan, method, CV policy, selected binding, and accepted verdict;
- preflights every frozen size through the same semantic authorization before any production trainer/final-plan admission;
- retains the per-size authorization recheck immediately before final production.

Do not move role-specific identity into TargetBinding or add another currentness owner.

### 3.2 Optimizer authority split and real-owner materialization

The accepted T6/T7 test now proves base, screen-mutated, and method-mutated campaigns have identical selected N, exact ordered `T_N`, training-order identity, and role-neutral TargetBinding before comparing optimizer changes. It then observes actual P3/P5 MACE configuration materialization.

Accepted observed behavior includes:

- screen-only normalization edits change actual P3 realized LR/EMA but not P5 CV/production optimizer or method identity;
- `[training]` LR/EMA edits change actual P5 CV/production method/materialization but not the P3 screen optimizer;
- CV and production share one post-selection method/optimizer while retaining distinct frozen H_cv/H_prod.

The bounded TRAIN2 fixture now uses the runtime plan's learning-rate policy rather than a hard-coded LR; this is a fidelity improvement below the semantic owner, not new product machinery.

### 3.3 `init [model]` ownership

The facade argv scanner has been deleted. The real core `init` subparser owns the optional positional model, and `command_init` reduces positional and legacy `--foundation-family` forms to one canonical family before template generation. Conflicts fail before config/state creation.

Keep this simplified realization. Do **not** restore a facade scanner or add parser-side synchronized explicitness machinery solely to preserve an obsolete raw-Namespace assertion.

### 3.4 Current real foundation evidence already accepted

On executable head `c3db340e11eb49748f00becd34c422a819daf38a`, the locked real checkpoints passed the following bounded CPU/e3nn tests:

```text
MH-1 SHA256
  ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde
  selected head: omat_pbe

MPA-0-medium SHA256
  75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
  selected head: default
```

Recorded command executed four real-asset cells and produced **4 passed, 201 warnings in 14.14s**, covering exact inspection/family/head resolution, CPU/e3nn load, official/native batch inference parity for both models, and MH-1 `omat_pbe` extraction/parity. The extraction qualification explicitly reaches the repository's training-qualified selected-head contract.

This evidence remains reusable unless implementation changes foundation inspection, extraction, model loading/inference, or family/head semantics.

---

## 4. Blocking repair R-CLI2 — reconcile the stale direct-parser regression by simplifying the oracle

### 4.1 Finding

`build_parser()` now sets the legacy `--foundation-family` argument default to `None`. That is how `command_init` can distinguish an omitted legacy flag from an explicitly supplied flag while also accepting the new positional `model`.

The existing regression still contains:

```python
args = parser.parse_args(["--config", str(target), "init"])
assert args.foundation_family == "mace_mh_1"
```

The recorded final regression omitted this test file. The assertion conflicts directly with current parser source and therefore represents an unclosed required affected regression.

The product requirement is not the raw namespace value. It is:

```text
bare init
    -> generated configuration has family mace_mh_1
    -> selected head omat_pbe
    -> MH-1 default model path
```

### 4.2 Required repair

1. **Keep** the current parser-owned positional implementation and scanner deletion.
2. **Keep** the clean omitted-legacy-flag sentinel (`foundation_family is None`) if it remains the simplest way to distinguish omission from explicit legacy input.
3. Update `test_config1_init_defaults_are_explicit_not_environment_autodetected` so it tests the resolved contract rather than freezing the intermediate namespace representation:
   - parse bare `init` through the real parser;
   - retain the relevant ordinary parser-default check such as backend `e3nn`;
   - execute the real `command_init` through `args.func(args)` or public `campaign_cli.main`;
   - assert generated TOML resolves `foundation.family == "mace_mh_1"`, `foundation.head == "omat_pbe"`, MH-1 default path, and existing backend expectations.
4. Do not add a custom argparse action, second explicitness flag, compatibility wrapper, argv scanner, or duplicate family state just to make the old namespace assertion true.
5. Run the **entire** `tests/test_mlff_mh1_config1_campaign_defaults.py` together with the current init/campaign CLI focused tests.

This section explicitly supersedes the earlier phrase “keep the existing legacy direct-parser init tests green” insofar as that phrase froze the raw `Namespace.foundation_family` value. Preserve the protected behavior, not the obsolete internal representation.

---

## 5. Blocking acceptance R-FOUND2 — execute the existing P5 foundation provider/method owner checks

### 5.1 Finding

F-REAL1 required not only real checkpoint inspection/inference/extraction, but also existing P5 foundation provider/method regression relevant to family/head propagation. The recorded real-model command stopped after the four real-asset tests, and the 329-test final regression did not include the current revision-10 P5 provider/method guard module.

No new test harness is required. Current repository tests already exercise the relevant owner boundary.

### 5.2 Required evidence

At minimum execute and record the current equivalents of:

```text
tests/test_mlff_target_size_p5_r10_guards.py::test_r10a_exact_mode_matrix_and_executable_head_parity
tests/test_mlff_target_size_p5_r10_guards.py::test_r10b_real_foundation_provider_owner_counterfactuals
tests/test_mlff_target_size_p5_r8_guards.py::test_claims_03_04_05_foundation_family_and_head_resolution_guards
```

The purpose is to establish through existing owners that:

- P5 mode construction propagates the exact foundation/head semantics into executable materialization;
- the real foundation-provider owner authenticates bytes/head and fails closed on tampering/unavailable head/provider-construction failure;
- family/head mismatch remains fail-closed, including MH-1 multi-head semantics versus MPA-0 singleton semantics.

If current test names have legitimately changed, use their canonical replacements and record the mapping. Do not add another P5 foundation harness unless these existing tests expose a real uncovered product behavior.

The four locked-model tests from Section 3.4 need not be rerun if this repair changes only tests/documentation or otherwise cannot affect foundation loading/extraction/inference. If foundation executable source changes, rerun the affected real-model cells.

---

## 6. Final functional closure R-T8

### 6.1 Evidence already reusable

The following execution evidence from source head `c3db340e11eb49748f00becd34c422a819daf38a` is accepted for unchanged dimensions:

- init/campaign focused suite: **19 passed**;
- T6/T7 real materialization: **1 passed**;
- P5 CV-currentness/production-restart suite: **38 passed**;
- multi-size assembled integration: **13 passed**;
- real locked MH-1/MPA-0 cells: **4 passed**;
- previously recorded broad affected suite: **329 passed** for the paths actually included;
- `python -m compileall mdstats tests`: **0 errors**;
- repository has no configured standalone ruff/flake8/mypy gate in `pyproject.toml`.

The 329-test result is **not** complete final closure because it omitted the required config-default test file and the P5 foundation-provider/method cells above.

### 6.2 Required final execution

After R-CLI2 and R-FOUND2:

1. run the full `tests/test_mlff_mh1_config1_campaign_defaults.py`;
2. rerun `tests/test_mlff_campaign_init_foundation_models.py` and `tests/test_mlff_campaign_cli.py` so the parser/config surface closes together;
3. execute the P5 foundation/provider cells in Section 5;
4. run `python -m compileall mdstats tests` after the final test/source edits;
5. if any executable product source beyond semantically inert cleanup changes, re-derive the affected surface and rerun every previously accepted suite whose result could plausibly change. Do not rerun unrelated heavy evidence merely because a review cycle occurred.

Record exact commands, final executable/source SHA, result counts, and any reused evidence directly in this workplan. A required test that fails or does not execute remains blocking.

Lifecycle/storage/qualification evidence from prior accepted rounds may be reused if the final repair remains confined to parser test reconciliation/test-only acceptance and does not plausibly affect those owners. If implementation changes those product dimensions, rerun their affected regression instead of assuming reuse.

---

## 7. Simplicity / anti-shortcut constraints

Do not add:

- a new foundation/model registry;
- per-family TOML templates/classes;
- filename-based family/head inference;
- silent multi-head fallback;
- argv preprocessors/scanners;
- custom parser state solely to preserve a stale test's raw namespace value;
- another currentness registry or collection evidence object;
- wrapper bindings/synchronized state;
- another optimizer resolver or CV/production duplicate LR/EMA tables;
- a new scheduler/generic experiment framework;
- another P5 numerical or foundation-provider harness;
- another synthetic foundation fixture hierarchy.

If a newly executed existing test exposes a real source defect, repair the existing semantic owner directly. Otherwise prefer test-oracle correction and evidence completion over product code growth.

---

## 8. Closure conditions

Independent Software Design may PASS and close/archive this workplan when all are true on one final candidate:

### C1 — init semantics and parser ownership

```text
init          -> generated mace_mh_1 / omat_pbe configuration
init mh-1     -> generated mace_mh_1 / omat_pbe configuration
init mpa-0    -> generated mace_mpa_0 / default configuration
matching legacy flag -> same semantic choice
conflicting legacy flag -> failure before config/state creation
config path named "init" / valid option ordering -> no command-token ambiguity
```

The facade scanner remains absent and the direct-parser regression protects resolved product behavior rather than an obsolete namespace representation.

### C2 — multi-size/P5 currentness

Stale/changed CV policy or any invalid frozen member never authorizes new production; collection admission starts zero new production jobs until every member is current/accepted.

### C3 — optimizer authority separation

The already-accepted real P3/P5 materialization counterfactual remains green with identical frozen target lineage, screen/post-selection independence, and shared CV/production post-selection method.

### C4 — both foundation families

Locked MH-1/`omat_pbe` and MPA-0/`default` evidence remains current, and existing P5 provider/method owners pass their family/head/authentication regressions.

### C5 — functional closure

The previously omitted config-default regression and P5 provider/method checks execute successfully; compileall passes; any additional changed affected surface is rerun proportionately.

### C6 — minimum complexity

No new wrapper/registry/duplicate state is introduced merely to reconcile the stale parser test or complete acceptance.

---

## 9. Review routing

This file remains the **only active implementation entry point**. The next implementation round is intentionally small:

1. reconcile the stale config-default test at the resolved-product boundary;
2. execute the existing P5 foundation/provider acceptance cells;
3. execute the bounded final regression required by Section 6 and record it here.

Do not reopen the multi-size or foundation architecture unless those existing tests reveal evidence that a Frozen decision itself is wrong.
