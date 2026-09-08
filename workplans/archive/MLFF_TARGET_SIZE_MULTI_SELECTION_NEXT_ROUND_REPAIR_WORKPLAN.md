---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-MULTI-SELECTION-NEXT-ROUND-REPAIR
protocol_version: 5.16.0
status: closed
created_date: 2026-09-08
reviewed_date: 2026-09-08
reviewed_candidate_head: 0f1d4dbb35f87e394e2b149d02deb6406519ed71
reviewed_executable_head: c3db340e11eb49748f00becd34c422a819daf38a
closure_reviewed_date: 2026-09-08
closure_review_status: pass
closure_reviewed_candidate_head: 1229c53497a46d2ea7904aad559c80c641d242a2
closure_reviewed_executable_head: d564497a05f122ceec3debe24a4dafa80a52ecf5
implementation_review_verdict: pass
branch: plan/mlff-target-size-multi-selection-reviewed
implementation_base_head: e2b3c20dee4832eb62416ccfb630b05136fa4313
entrypoint: Archived closed implementation workplan. It is historical evidence only and no longer defines an active implementation entry point.
---

# MLFF multi-size / foundation initialization — final acceptance closure

## 0. Prior independent review verdict that triggered the final round

**NO-PASS / implementation reopened, narrowly.**

The reviewed candidate was `0f1d4dbb35f87e394e2b149d02deb6406519ed71`; its executable source was unchanged from `c3db340e11eb49748f00becd34c422a819daf38a` because the final commit only recorded workplan evidence.

The substantive implementation was close to closure. The review found no new defect in the multi-size scientific architecture, P5 currentness/production barrier, optimizer-authority separation, generalized MH-1/MPA-0 foundation architecture, or real P3/P5 materialization wiring.

Two blocking acceptance issues remained:

1. **A required affected regression was omitted and was source-deterministically stale.** `tests/test_mlff_mh1_config1_campaign_defaults.py` was explicitly required by this workplan but was absent from the recorded final regression. Its `test_config1_init_defaults_are_explicit_not_environment_autodetected` still asserted that raw parser output had `args.foundation_family == "mace_mh_1"`, while the accepted parser implementation deliberately used `None` to represent an omitted legacy flag and resolved the product default inside `command_init`.
2. **F-REAL1 item 5 was not executed.** The recorded real-model command proved exact MH-1/MPA-0 checkpoint identity, CPU/e3nn loading/inference, and MH-1 selected-head extraction parity, but omitted the existing P5 foundation provider/method owner tests required by Section 7.

The first issue was a **test/workplan-oracle deficiency, not a reason to add parser machinery**. The protected product contract is that bare `init` generates the canonical MH-1 configuration. A raw intermediate `argparse.Namespace` value is delegated Tier-2 representation. Restoring that old assertion with a custom argparse action, duplicate explicitness flag, argv scanner, or synchronized parser state would increase product complexity merely to satisfy an obsolete oracle. The correct repair was to update the stale test to observe the resolved product behavior.

No new workplan, wrapper, registry, compatibility state, or architecture revision was authorized.

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

## 3. Implementation accepted — do not churn

### 3.1 P5 currentness and production barrier

Current source correctly:

- rejects a stored CV plan when its method identity differs from current method authority;
- rejects it when its CV-policy identity differs from the resolved current per-size CV policy;
- requires CV acceptance to bind the exact plan, method, CV policy, selected binding, and accepted verdict;
- preflights every frozen size through the same semantic authorization before any production trainer/final-plan admission;
- retains the per-size authorization recheck immediately before final production.

Do not move role-specific identity into TargetBinding or add another currentness owner.

### 3.2 Optimizer authority split and real-owner materialization

The accepted T6/T7 test proves base, screen-mutated, and method-mutated campaigns have identical selected N, exact ordered `T_N`, training-order identity, and role-neutral TargetBinding before comparing optimizer changes. It then observes actual P3/P5 MACE configuration materialization.

Accepted observed behavior includes:

- screen-only normalization edits change actual P3 realized LR/EMA but not P5 CV/production optimizer or method identity;
- `[training]` LR/EMA edits change actual P5 CV/production method/materialization but not the P3 screen optimizer;
- CV and production share one post-selection method/optimizer while retaining distinct frozen H_cv/H_prod.

The bounded TRAIN2 fixture uses the runtime plan's learning-rate policy rather than a hard-coded LR; this is a fidelity improvement below the semantic owner, not new product machinery.

### 3.3 `init [model]` ownership

The facade argv scanner has been deleted. The real core `init` subparser owns the optional positional model, and `command_init` reduces positional and legacy `--foundation-family` forms to one canonical family before template generation. Conflicts fail before config/state creation.

Keep this simplified realization. Do **not** restore a facade scanner or add parser-side synchronized explicitness machinery solely to preserve an obsolete raw-Namespace assertion.

### 3.4 Current real foundation evidence accepted

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

## 4. Repair R-CLI2 — reconcile the stale direct-parser regression by simplifying the oracle

### 4.1 Finding

`build_parser()` sets the legacy `--foundation-family` argument default to `None`. That is how `command_init` can distinguish an omitted legacy flag from an explicitly supplied flag while also accepting the new positional `model`.

The old regression contained:

```python
args = parser.parse_args(["--config", str(target), "init"])
assert args.foundation_family == "mace_mh_1"
```

The product requirement is not the raw namespace value. It is:

```text
bare init
    -> generated configuration has family mace_mh_1
    -> selected head omat_pbe
    -> MH-1 default model path
```

### 4.2 Required repair — completed

1. **Keep** the parser-owned positional implementation and scanner deletion.
2. **Keep** the clean omitted-legacy-flag sentinel (`foundation_family is None`) if it remains the simplest way to distinguish omission from explicit legacy input.
3. Update `test_config1_init_defaults_are_explicit_not_environment_autodetected` so it tests the resolved contract rather than freezing the intermediate namespace representation.
4. Do not add a custom argparse action, second explicitness flag, compatibility wrapper, argv scanner, or duplicate family state just to make the old namespace assertion true.
5. Run the **entire** `tests/test_mlff_mh1_config1_campaign_defaults.py` together with the current init/campaign CLI focused tests.

The implementation removed only the obsolete raw-Namespace assertion. The same test still executes the real init command and asserts the generated MH-1 family/head/path/backend contract.

---

## 5. Acceptance R-FOUND2 — execute the existing P5 foundation provider/method owner checks

### 5.1 Finding

F-REAL1 required not only real checkpoint inspection/inference/extraction, but also existing P5 foundation provider/method regression relevant to family/head propagation. No new test harness was required because current repository tests already exercised the relevant owner boundary.

### 5.2 Required evidence — completed

Executed the current owner tests:

```text
tests/test_mlff_target_size_p5_r10_guards.py::test_r10a_exact_mode_matrix_and_executable_head_parity
tests/test_mlff_target_size_p5_r10_guards.py::test_r10b_real_foundation_provider_owner_counterfactuals
tests/test_mlff_target_size_p5_r8_guards.py::test_claims_03_04_05_foundation_family_and_head_resolution_guards
```

These establish through existing owners that:

- P5 mode construction propagates the exact foundation/head semantics into executable materialization;
- the real foundation-provider owner authenticates bytes/head and fails closed on tampering/unavailable head/provider-construction failure;
- family/head mismatch remains fail-closed, including MH-1 multi-head semantics versus MPA-0 singleton semantics.

The four locked-model tests from Section 3.4 remained reusable because this repair changed only test code and documentation, not foundation executable source.

---

## 6. Final functional closure R-T8

### 6.1 Evidence reused correctly

The following execution evidence from source head `c3db340e11eb49748f00becd34c422a819daf38a` remained valid because the final implementation changed no executable product source:

- init/campaign focused suite: **19 passed**;
- T6/T7 real materialization: **1 passed**;
- P5 CV-currentness/production-restart suite: **38 passed**;
- multi-size assembled integration: **13 passed**;
- real locked MH-1/MPA-0 cells: **4 passed**;
- previously recorded broad affected suite: **329 passed** for the paths actually included;
- `python -m compileall mdstats tests`: **0 errors**;
- repository has no configured standalone ruff/flake8/mypy gate in `pyproject.toml`.

### 6.2 Required final execution — completed

After R-CLI2 and R-FOUND2, Implementation ran the full config/init surface, the existing P5 provider/method owner guards, the complete affected regression, and compileall. Exact evidence is recorded in Section 10.

Lifecycle/storage/qualification evidence from prior accepted rounds remained reusable because the final repair was confined to test-oracle reconciliation and acceptance execution and did not plausibly affect those owners.

---

## 7. Simplicity / anti-shortcut constraints

The final implementation did not add:

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

The only executable-repository change in the final round was deletion of the obsolete raw-Namespace test assertion.

---

## 8. Closure conditions

### C1 — init semantics and parser ownership — PASS

```text
init          -> generated mace_mh_1 / omat_pbe configuration
init mh-1     -> generated mace_mh_1 / omat_pbe configuration
init mpa-0    -> generated mace_mpa_0 / default configuration
matching legacy flag -> same semantic choice
conflicting legacy flag -> failure before config/state creation
config path named "init" / valid option ordering -> no command-token ambiguity
```

The facade scanner remains absent and the direct-parser regression protects resolved product behavior rather than an obsolete namespace representation.

### C2 — multi-size/P5 currentness — PASS

Stale/changed CV policy or any invalid frozen member never authorizes new production; collection admission starts zero new production jobs until every member is current/accepted.

### C3 — optimizer authority separation — PASS

The accepted real P3/P5 materialization counterfactual remains current with identical frozen target lineage, screen/post-selection independence, and shared CV/production post-selection method.

### C4 — both foundation families — PASS

Locked MH-1/`omat_pbe` and MPA-0/`default` evidence remains current, and existing P5 provider/method owners pass their family/head/authentication regressions.

### C5 — functional closure — PASS

The previously omitted config-default regression and P5 provider/method checks executed successfully; compileall passed; no additional executable affected surface was introduced.

### C6 — minimum complexity — PASS

No new wrapper/registry/duplicate state was introduced merely to reconcile the stale parser test or complete acceptance.

---

## 9. Review routing

Implementation is complete and this workplan is closed. It is archived as historical engineering evidence. No additional repair round is required.

Do not reopen the multi-size or foundation architecture without new evidence that a Tier-1 product invariant or Frozen high-level decision is violated.

---

## 10. Implementation evidence

```text
final_candidate_head: d564497a05f122ceec3debe24a4dafa80a52ecf5
python: 3.11.15
mace: 0.3.16
torch: 2.13.0+cu126
e3nn: 0.4.4
real_mh1_sha256: ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde
real_mpa0_sha256: 75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638
```

### 10.1 R-CLI2 / init / config surface regression
- Command:
  ```bash
  /home/samjin/miniconda3/envs/mace/bin/python -m pytest \
    tests/test_mlff_mh1_config1_campaign_defaults.py \
    tests/test_mlff_campaign_init_foundation_models.py \
    tests/test_mlff_campaign_cli.py \
    -v
  ```
- Outcome: **30 passed in 5.05s**. Covered bare `init` (resolving `mace_mh_1` / `omat_pbe` and MH-1 default model path in generated configuration), `init mh-1`, `init mpa-0` (`mace_mpa_0` / `default`), disambiguation of config file named `init` (`--config init init mh-1`), option ordering (`init --workspace <path> mpa-0`), matching `--foundation-family`, conflicting `--foundation-family` (fails closed before config/state creation), and parser-level rejection of unsupported models with code 2. Reconciled `test_config1_init_defaults_are_explicit_not_environment_autodetected` to test the resolved configuration contract rather than intermediate namespace representation.

### 10.2 R-FOUND2 / P5 foundation provider and method owner checks
- Command:
  ```bash
  /home/samjin/miniconda3/envs/mace/bin/python -m pytest \
    tests/test_mlff_target_size_p5_r10_guards.py::test_r10a_exact_mode_matrix_and_executable_head_parity \
    tests/test_mlff_target_size_p5_r10_guards.py::test_r10b_real_foundation_provider_owner_counterfactuals \
    tests/test_mlff_target_size_p5_r8_guards.py::test_claims_03_04_05_foundation_family_and_head_resolution_guards \
    -v
  ```
- Outcome: **3 passed, 36 warnings in 6.98s**. Also executed full guard suites:
  ```bash
  /home/samjin/miniconda3/envs/mace/bin/python -m pytest \
    tests/test_mlff_target_size_p5_r10_guards.py \
    tests/test_mlff_target_size_p5_r8_guards.py \
    -n 12
  ```
  producing **33 passed, 52 warnings in 23.92s**. Established that:
  - P5 mode construction propagates exact foundation/head semantics into executable materialization;
  - real foundation-provider owner authenticates bytes/head and fails closed on tampering, unavailable head, or construction failure;
  - family/head mismatch remains fail-closed (MH-1 multi-head vs MPA-0 singleton).

### 10.3 Reused accepted evidence from candidate c3db340 (unchanged executable surface)
- **F-REAL1 Real Checkpoint Acceptance**: **4 passed, 201 warnings in 14.14s** with locked model files on CPU/e3nn (`test_id1_real_uploaded_checkpoints_inspect_and_resolve_exactly`, `test_real_mh1_and_mpa0_checkpoints_load_through_e3nn_reference_path`, `test_data6_1_real_uploaded_models_match_official_and_native_batch`, `test_extract1_real_mh1_omat_pbe_extraction_and_parity`).
- **T6/T7 Real-Materialization Counterfactual**: **1 passed, 7 warnings in 52.04s** with frozen target lineage proofs, exact P3 realized values (`base: 0.0128, True, 0.99872...`, `changed: 0.0004, True, 0.97467...`), and P5 CV/production method/optimizer sharing.
- **P5 CV-Currentness & Production-Restart**: **38 passed, 38 warnings in 496.14s**.
- **Multi-Size Assembled Integration**: **13 passed, 73 warnings in 44.33s**.

### 10.4 Final complete affected regression
- Command:
  ```bash
  /home/samjin/miniconda3/envs/mace/bin/python -m pytest \
    tests/test_mlff_mh1_config1_campaign_defaults.py \
    tests/test_mlff_campaign_init_foundation_models.py \
    tests/test_mlff_campaign_cli.py \
    tests/test_mlff_target_size_p5_r10_guards.py \
    tests/test_mlff_target_size_p5_r8_guards.py \
    tests/test_mlff_post_selection_materialization_acceptance.py \
    tests/test_mlff_target_size_canonical_optimizer_settings.py \
    tests/test_mlff_target_size_optimizer_normalization.py \
    tests/test_mlff_target_size_p5a_selected_context.py \
    tests/test_mlff_target_size_p5b_identity_hierarchy.py \
    tests/test_mlff_target_size_p5c_cv_plan.py \
    tests/test_mlff_target_size_p5d_cv_acceptance.py \
    tests/test_mlff_target_size_p5e_production_and_restart.py \
    tests/test_mlff_target_size_p5f_structure.py \
    tests/test_mlff_target_size_p5g_assembled_integration.py \
    tests/test_mlff_target_size_p5h_publication_decision.py \
    tests/test_mlff_target_size_multi_selection.py \
    tests/test_mlff_target_size_multi_size_integration.py \
    -n 12
  ```
- Outcome: **373 passed, 197 warnings in 181.49s (0:03:01)** across 12 concurrent workers. Zero failures or regressions.

### 10.5 Project static checks & syntax validation
- Static/lint/type gates: None configured in `pyproject.toml` or repository root.
- Bytecode compilation:
  ```bash
  /home/samjin/miniconda3/envs/mace/bin/python -m compileall mdstats tests
  ```
  Outcome: **0 errors**; clean compilation across all modules.

---

## 11. Final independent Software Design closure review

**PASS / workplan closed.**

Reviewed branch head: `1229c53497a46d2ea7904aad559c80c641d242a2`.
Final executable/test candidate: `d564497a05f122ceec3debe24a4dafa80a52ecf5`.

The branch head differs from the executable candidate only by the workplan evidence commit. The final implementation round differs from the prior reviewed state only by deleting the obsolete raw `args.foundation_family == "mace_mh_1"` assertion; no product source, scientific logic, persistence, orchestration, optimizer, or foundation execution code changed.

Independent source review confirms the retained test still executes the real init owner and asserts the generated MH-1 family/head/model-path/backend contract. The parser remains the sole syntax owner, the facade scanner remains absent, and no replacement compatibility or explicitness machinery was introduced.

Independent review of the newly executed P5 guards confirms that they reach the intended semantic owners: exact mode/head materialization, real foundation-provider construction, checkpoint-byte authentication, unavailable-head rejection, provider-construction failure, and independent family/multi-head fail-closed behavior. Combined with the still-current locked real-checkpoint CPU/e3nn evidence, these close the foundation acceptance gap without a new harness.

The final 373-test affected regression and compileall close the previously omitted acceptance surface. Previously accepted multi-size, CV-currentness, optimizer-separation, restart, and real-model evidence remains valid because no executable dimension that could change those results was modified.

No blocking product, scientific, architectural, compatibility, durability, complexity, or acceptance issue remains. The final realization satisfies the Tier-1 product invariants and Frozen architecture with lower complexity than the rejected alternatives: direct parser ownership, one canonical foundation route, one currentness authority, one shared post-selection optimizer method, and no new wrapper/registry/state machinery.

Production-scale GPU/CuEq/LAMMPS qualification is intentionally not claimed by this closure and remains deferred to the established final-release/user-machine qualification stage.
