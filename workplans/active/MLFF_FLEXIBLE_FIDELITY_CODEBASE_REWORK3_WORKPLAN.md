---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK3
protocol_version: 5.6.0
status: active
reopened_date: 2026-08-25
reopened_from_commit: 45c3cfb65738dbe1b63149cf421f213861fb5cf3
prior_reopen_from_commit: c32fc3fb46f61086c452952bc4f11d88b85b45ca
reconciled_from_protocol: 5.5.0
---

# MLFF Flexible-Fidelity Rework 3 - Protocol 5.6 Reopened Acceptance Closure

## 1. Objective and authority

Reopen the existing Rework 3 closure contract against `feat/mlff-end-to-end-performance-v1` at `45c3cfb65738dbe1b63149cf421f213861fb5cf3` and finish the remaining acceptance/implementation gaps found by independent Software Design review.

This is **not** Rework 4 and is **not** a scientific redesign. The accepted flexible-fidelity architecture remains frozen. This revision explicitly adopts Protocol 5.6 for the still-open work after reconciling the new proxy-proof acceptance obligations with the existing Rework 3 contract.

The parent flexible-fidelity workplan, Rework 1, Rework 2, and earlier Rework 3 frozen product decisions remain authoritative except where this reopened plan tightens acceptance mechanics. Prior green test counts and earlier completion claims remain historical evidence only; they are not final acceptance authority.

Current scientific policy remains:

```text
0 < n1 < n2 < n3 <= n

default fidelity boundaries = (1, 3, 10)
default full TRAIN2 schedule horizon n = 30
```

## 2. Frozen product doctrine and scientific design

Implementation must preserve the repository's established engineering hierarchy and the accepted MLFF architecture. In particular:

- product/scientific correctness and required capability take precedence over implementation convenience or test economy;
- minimum justified product/system complexity is preferred only inside the engineering-sufficient solution space;
- development/test economy may reduce execution cost only after product and acceptance confidence are preserved;
- `TargetSizeStudyPolicy` owns `(n1,n2,n3)` and TRAIN2 budget/schedule policy owns `n`;
- every screen is an exact pause/continuation endpoint on one uninterrupted full-`n` TRAIN2 schedule, not an independent shortened schedule;
- target-size evidence binds both the semantic endpoint and the full schedule horizon;
- final-screen `n3` and full-reference `n` remain distinct semantic roles even when `n3 == n`; one physical endpoint may satisfy both only when the real consumer validates both roles and schedules no duplicate work;
- preserve fixed candidate ladder, MVQUAL hard admission, paired-seed target-only ranking, and `q -> min(q,4) -> 2 -> 1` promotion behavior;
- preparation scientific identity is a positive semantic projection: it includes true DATA2-DATA8 scientific dependencies and excludes downstream TRAIN2, execution/cache, persistence, resource, and presentation policy;
- historical compatibility is limited to the authenticated immediate fixed-fidelity predecessor and fails closed outside that narrow boundary;
- historical target-size evidence is never relabeled as current flexible-fidelity evidence;
- full production/GPU qualification remains deferred and is not required to close this bounded functional repair.

## 3. Current-state diagnosis at `45c3cfb...`

The latest candidate contains useful partial corrections that should be preserved unless direct evidence proves them wrong:

1. `_PREPARATION_CONFIG_PROJECTION_FIELDS` was narrowed so `acceleration` retains only `backend`; `training_backend`, `only_cueq`, and `require_available` are classified as downstream/execution controls. This is directionally consistent with the frozen design.
2. The current dependency graph now contains explicit `FULL_TRAIN2_SCHEDULE -> COARSE_SCREEN/SHORT_SCREEN/FINAL_SCREEN` `identity_requires` edges.
3. Some current architecture regression assertions were restored.

Those product/source changes do **not** close Rework 3 because the acceptance boundary is still wrong or incomplete:

### 3.1 O18R remains only partially accepted

Current tests establish digest/projection behavior and a real `CampaignStore` stage-marker response, but do not yet prove authenticated **completed prepare + preflight + DATA7/DATA8 reuse** through the normal reuse/restart consumers for every required downstream/execution-only control. Individual model execution/cache controls are still primarily digest-level coverage.

### 3.2 O20R persistent frontiers remain unaccepted

The current frontier test constructs a real store but then directly invokes `_invalidate_train2_downstream_state(...)`. That proves helper behavior, not that the normal durable restart/reconciliation owner detects the changed TOML/config, authenticates upstream state, selects the exact invalidation frontier, and invokes the correct downstream transition. The persisted baseline is also shallower than the required prepare/preflight/DATA7/DATA8/target-study/TRAIN2 lineage.

### 3.3 O21R assembled A/B/C/D1/D2/D3 remain unaccepted

- A/B still monkeypatch `_require_train2_preflight_authorization`, so real preflight authorization is not established.
- C remains a helper-level `build_size_fidelity_execution_plan(...)` proof instead of persisted target-size -> real SIZE-FIDELITY consumer integration.
- D1/D2 still use custom migration-store/test doubles and monkeypatch semantic owners such as historical compatibility, DATA8 discovery/materialization variants, target-study construction, schedule/matrix validation, and stage digest.
- D3 still uses a reduced custom store and monkeypatched preparation digest/contract behavior instead of real preparation receipt/digest/restart ownership.

### 3.4 O19R is partially closed

The full-schedule graph defect is fixed. Architecture regression restoration remains incomplete or insufficiently demonstrated for independent current invariants, especially structural policy-independence of frame facts, sealed evaluation/locked-test non-retroactivity, retained checkpoint semantics, and exact current publication/version contracts where normative.

### 3.5 O22R final closeout is not established

No fresh same-candidate closeout record proves the complete affected regression plus genuine A/B/C/D1/D2/D3 after the still-required acceptance changes. The old completion count cannot be reused as final authority.

No current finding fires a scientific redesign trigger. The remaining work is implementation/test-contract nonconformance under the same frozen design.

## 4. Protocol 5.6 proxy-proof acceptance overlay

This section is controlling for every material integration/acceptance claim below.

### 4.1 Semantic owner under acceptance

For a claim to close, the production owner/path whose behavior constitutes the claim must execute for real. For this workplan the semantic-owner surface includes, as applicable:

- current TOML generation/parsing/normalization: `_config_template`, `_load_config`, validators/current normalization;
- `CampaignStore` durable persistence, close/reopen, and current record/stage behavior;
- preparation config digest, authenticated prepare receipt, and completed-prepare reuse;
- `_prepare_contract_signature`;
- `_historical_prepare_inputs_match_current`;
- `_current_data8_entries`;
- `_target_size_materialization_variants`;
- `_ensure_target_size_study`;
- target-size serialization, validation, evidence persistence, reduction, and selection freeze;
- `_validate_train2_data8_matrix` and the real TRAIN2 schedule/materialization/continuation identity owners;
- `_stage_config_digest` and stored stage metadata;
- `_require_train2_preflight_authorization` or its real successor;
- the normal restart/reconciliation/next-operation/status consumer that detects configuration/state changes;
- the current invalidation/forensic-state owner as reached through that normal consumer;
- the real SIZE-FIDELITY checkpoint/execution planning consumer;
- PERF-P2R/production authorization consumers when they are part of the asserted path.

### 4.2 Allowed test-double boundary

Test doubles may replace only dependencies below/outside the claimed owner boundary, including:

- actual MACE training subprocess/external trainer execution;
- expensive prediction/evaluation values after the real product has authorized the work;
- heavyweight model loading or unavailable large source-data computation when the fixture already contains authenticated bounded products and the product owner under test still executes;
- GPU/accelerator execution;
- reduced/synthetic data volume and reduced bounded workloads that preserve the same semantic contract.

The real product must still decide **what** work is authorized, **whether** persisted state is current/reusable, **which** candidate advances, **which** checkpoint/schedule is valid, and **what** operation comes next.

### 4.3 Forbidden substitutions

The following cannot close the corresponding owner claim:

- monkeypatching/stubbing a semantic owner above to return the desired answer;
- directly calling `_invalidate_train2_downstream_state` as proof that normal restart/reconciliation detects and invalidates the right frontier;
- seeding post-decision/post-transition state and skipping the production transition that is the acceptance claim;
- replacing `CampaignStore` with a custom/minimal/in-memory store when persistence/restart/recovery behavior is the claim;
- reimplementing historical compatibility, identity, schedule validation, authorization, or orchestration logic in the fixture;
- asserting a helper plan/result as proof that the assembled production consumer uses it correctly;
- calling a downstream helper directly when the caller/orchestrator/restart/authorization decision is the claim.

An explicitly frozen real-owner/test-double boundary in this workplan is an acceptance decision, not a suggested fixture structure, and **must not be weakened as local reconciliation**.

### 4.4 Proxy-proof counterfactual

For every material acceptance test ask:

> **Could this test remain green while the required production semantic owner is materially broken?**

If yes, that test cannot close the claim. If the required real boundary cannot execute in the bounded environment, record the check as unavailable/blocking or reopen only the affected design on evidence; do not silently substitute a proxy pass.

### 4.5 Targeted anti-bypass guardrail

The final candidate must include a cheap structural/negative guard that protects the identifiable Rework 3 real-owner acceptance set from recurrence of the exact bypass pattern. The guard must, at minimum, fail if the A/B/C/D/frontier acceptance tests monkeypatch/stub the named semantic owners they are intended to accept, or if the frontier acceptance directly substitutes `_invalidate_train2_downstream_state` for the normal restart/reconciliation path.

This is **not** a repository-wide monkeypatch ban. Existing unit tests may mock semantic owners when they are testing a different layer. Exact AST/source technique and whether the assembled acceptance lives in a dedicated test module are delegated, provided the protected acceptance set is unambiguous and the guard is robust rather than prose-only.

## 5. Implementation obligations

### O18R - Finish preparation scientific/execution identity acceptance

**Protected concern:** downstream TRAIN2/execution/cache/presentation controls must not invalidate expensive preparation; true scientific preparation changes must still fail closed.

**Required product state:** preserve the current positive preparation projection unless direct evidence shows a classification error. Expected classification:

- preparation-scientific retained: source/evidence/partition/selection/materialization scientific content, resolved foundation inference device/dtype where existing DATA6 identity treats them scientifically, and foundation inference backend when it changes authoritative DATA6 values;
- downstream/excluded: `training.max_num_epochs`, `fidelity_epochs`, TRAIN2 learning-rate/checkpoint/stopping policy, `acceleration.training_backend`, downstream evaluation/verification/presentation;
- execution/cache excluded: `model.max_new_frames`, `inference_batch_size`, `maximum_inference_batch_size`, `estimated_inference_memory_mib_per_frame`, `batch_calibration_stress_structures`, `vram_max_device_fraction`, `vram_reserve_gib`, `batch_throughput_tolerance_fraction`, `pipeline_enabled`, `persistence_queue_depth`, `checkpoint_interval`, `artifact_shard_size`;
- `acceleration.only_cueq` and `acceleration.require_available` remain excluded if their traced behavior is availability/execution-only, as current source indicates.

Do not widen preparation scientific identity to solve cache/materialization realization compatibility; authenticate such realization at its own owner.

**Required real owner/path:** actual TOML/current normalization -> real `CampaignStore` completed prepare receipt/stage -> real preflight/current reuse/restart compatibility consumer -> real DATA7/DATA8 current-state reuse decision.

**Allowed doubles:** expensive source/model computation below the authenticated reuse boundary.

**Forbidden substitutes:** digest equality alone; a prepare stage marker alone; monkeypatched prepare digest/contract/reuse owner.

**Acceptance:** starting from one bounded authenticated completed prepare+preflight+DATA7/DATA8 fixture, independently change each of:

- `training.max_num_epochs`;
- `n1`;
- `n2`;
- `n3`;
- `training_backend`;
- every execution/cache model field listed above;
- `only_cueq` and `require_available` if still execution-only;
- one presentation-only field.

For every case, the normal durable reuse path must preserve completed preparation/preflight and current DATA7/DATA8 scientific products when authoritative science is unchanged. At least one true preparation-scientific change must prove the inverse and reopen at the narrowest correct upstream boundary.

Digest/projection unit tests remain useful focused coverage but are supplementary only.

### O20R - Prove exact persistent invalidation frontiers for `n1`, `n2`, `n3`, and `n`

**Protected concern:** under-invalidation can reuse scientifically incompatible screen/TRAIN2 state; over-invalidation wastes valid expensive preparation.

Build one reusable bounded baseline through real current config and real `CampaignStore`. Its durable state must contain enough authentic lineage for the normal restart/reconciliation consumer to decide reuse/invalidation:

- complete prepare and authenticated prepare receipt;
- complete preflight plus smoke/matrix identity;
- current DATA7/DATA8 scientific/materialization records;
- current target-size study and screen evidence;
- TRAIN2 schedule/execution/checkpoint/campaign identity sufficient for continuation/invalidation;
- stage config metadata used by normal restart logic;
- at least one unrelated upstream record that must survive;
- existing forensic/history representation for rejected live TRAIN2 state.

For every frontier case: modify actual TOML/config through current normalization, close/reopen the durable store, invoke the **normal restart/reconciliation/next-operation consumer**, and assert the exact frontier. Do not invoke the invalidation helper directly as the acceptance mechanism.

#### O20R-1 `n1`: `(1,3,10)/30 -> (2,3,10)/30`

Preserve prepare receipt/stage, reauthenticated preflight, and unchanged DATA7/DATA8 science. Old target study/evidence and dependent live TRAIN2 state cease to be current authority. Fresh study is `(2,3,10)/30`; first new authorized screen is epoch `2`; no old evidence is relabeled.

#### O20R-2 `n2`: `(1,3,10)/30 -> (1,5,10)/30`

Same frontier. Fresh study restarts from configured `n1=1`; prior coarse evidence is not reused merely because the numerical `n1` matches.

#### O20R-3 `n3`: `(1,3,10)/30 -> (1,3,12)/30`

Same frontier. First new screen is `n1=1`; old final-screen evidence is not current.

#### O20R-4 horizon `n`: `(1,3,10)/30 -> (1,3,10)/40`

Preserve preparation/preflight/DATA7/DATA8 science. Invalidate target-size evidence bound to old horizon and old TRAIN2 schedule/execution/checkpoint/cross-horizon live state. The **real continuation/schedule validator** must reject old 30-horizon state as current 40-horizon authority. Establish full-40 identity; fresh study is `(1,3,10)/40`; first new screen is epoch `1`; status/authorization separates endpoint `1` from schedule horizon `40`.

#### O20R-5 controls

- preparation-scientific change -> fail closed at/before correct prepare boundary;
- execution-only change -> preserve preparation/preflight/DATA7/DATA8 science; only its owning realization/cache may regenerate;
- presentation-only change -> no scientific/target-size/TRAIN2/materialization invalidation.

**Observable acceptance for every row:** assert named preserved records/stages, named invalidated current records/stages, forensic retention where applicable, next authorized operation, next screen epoch, and full schedule horizon. A digest-only or direct-helper matrix is insufficient.

### O21R - Genuine bounded assembled A/B/C/D1/D2/D3 integration

All six cases execute on one final candidate using real normalized config, real `CampaignStore`, real semantic identity/restart/authorization owners, real target-size policy/study reducers, and real relevant downstream consumers. Fake only expensive external computation after real authorization.

#### A - Fresh default `(1,3,10)/30`

Required path:

```text
real generated TOML
 -> real load/validation
 -> real persisted prepare/preflight-compatible state
 -> real preflight authorization
 -> real target-size orchestration authorizes endpoint 1
 -> fake external train/eval only
 -> real evidence persistence/reduction
 -> endpoint 3
 -> endpoint 10
 -> real selected-size freeze
 -> durable close/reopen
 -> real status/restart/next-operation
 -> real production authorization horizon 30
```

Assert authorized endpoints exactly `[1,3,10]`, full schedule horizon 30 for every screen, no later work for eliminated candidates, durable selected size visible in output/status, and production only for selected size at horizon 30.

**Forbidden:** patching `_require_train2_preflight_authorization` or any other owner that decides whether the asserted work is authorized/current.

#### B - Fresh nondefault `(2,5,12)/40`

Use actual TOML values. Assert normalized `(2,5,12)/40`, endpoints `[2,5,12]`, full schedule horizon 40 for every screen, status/progress separates screen endpoint from full horizon, eliminated candidates receive no later authorized jobs, selected size freezes durably, and production horizon is 40.

Per-candidate job assertions must prove elimination prevents later work; merely collecting endpoint numbers globally is insufficient.

#### C - `(1,3,30)/30` coincident final/reference endpoint

This must be real persisted target-size orchestration -> selected authority -> real SIZE-FIDELITY checkpoint/execution consumer, not `build_size_fidelity_execution_plan(...)` in isolation.

Assert:

- `final_screen_epoch == reference_training_epoch == 30`;
- both semantic roles are independently validated from current persisted authority;
- physical checkpoint/evaluation epoch 30 appears once per run when reusable;
- no duplicate epoch-30 training is scheduled solely because two semantic roles coincide.

#### D1 - Immediate historical fixed predecessor -> default `(1,3,10)/30`

Use real `CampaignStore` and an authenticated bounded immediate-predecessor representation. Real historical prepare/preflight compatibility, stage digest, DATA8 discovery, target-study construction, matrix/schedule validation, and restart ownership must execute.

Assert unchanged upstream prepare/preflight/DATA7/DATA8 science is reused; historical target-size evidence is rejected as current and never relabeled; fresh current study starts epoch 1; stale live TRAIN2 state is invalidated/forensically retained by the real owner; restart/status points to correct work.

#### D2 - Immediate historical fixed predecessor -> `(2,5,12)/40`

Same real-owner constraints as D1. Unchanged upstream science survives; any execution schedule realization embedding 30 may regenerate only at its own owner; real full-40 schedule identity is established; old 30 schedule/checkpoint is rejected by the real validator; fresh current study starts epoch 2; no historical target evidence is relabeled.

#### D3 - Historical/config preparation-scientific change

Use real `CampaignStore`, real preparation digest/signature/receipt compatibility, and real restart/reuse consumer. Assert fail-closed reopening at the narrowest correct preparation boundary and that stale downstream preflight/DATA7/DATA8/target-size/TRAIN2 state does not remain current authority.

### O19R - Complete current authority and independent architecture regression protection

The full-schedule-to-screen graph requirement is already implemented at `45c3` and should remain protected structurally:

```text
FULL_TRAIN2_SCHEDULE -> COARSE_SCREEN  identity_requires
FULL_TRAIN2_SCHEDULE -> SHORT_SCREEN   identity_requires
FULL_TRAIN2_SCHEDULE -> FINAL_SCREEN   identity_requires
```

Keep current semantic graph language; do not restore obsolete revision-34/schema-26/current-authority fixtures or numeric semantic nodes `SIZE_STUDY_EPOCH3/10/30`.

Finish the pre-Rework-3 versus current regression classification and preserve/restore all still-current independent invariants unless an equivalent canonical test is identified explicitly. At minimum establish direct or clearly mapped equivalent protection for:

- canonical current MLFF-DATA stage order;
- raw frame facts remain policy-independent and structurally exclude eligibility/partition/selection/exposure/acquisition decision fields;
- locked-test evidence is operationally sealed from development/training/checkpoint control;
- held-out/locked validation cannot retroactively alter target-size/training/checkpoint selection;
- current checkpoint fail-closed policy plus retained evaluation-checkpoint semantics where still normative;
- core current manual/spec publication artifacts and version agreement where normative;
- revision-106 history/index synchronization and narrow immediate-predecessor migration/fail-closed language.

Prefer structural graph/schema assertions over weak sentence-presence checks when the invariant is structural. Do not increase test count by restoring obsolete representation details.

### O23R - Install the targeted proxy-proof regression guard

Add structural/negative regression protection for the assembled Rework 3 acceptance set so the exact failure mode cannot silently recur.

The guard must identify the frontier and A/B/C/D acceptance tests and fail when those tests replace the semantic owner they claim to accept. At minimum protect against acceptance-side monkeypatch/stub replacement of:

- `_require_train2_preflight_authorization`;
- `_historical_prepare_inputs_match_current`;
- `_prepare_contract_signature` / preparation digest-owner behavior when preparation compatibility is the claim;
- `_current_data8_entries`;
- `_target_size_materialization_variants`;
- `_ensure_target_size_study`;
- `_validate_train2_data8_matrix` / real schedule-validation owner;
- `_stage_config_digest`;
- real restart/next-operation/status owner;
- `CampaignStore` when durable persistence/restart is the claim.

Also reject direct `_invalidate_train2_downstream_state` substitution inside the persistent-frontier acceptance path.

The guard may use AST/source inspection or another cheap robust mechanism. It must allow legitimate mocks of external expensive computation below the accepted boundary and must not become a repository-wide mock ban.

### O22R - Re-establish fresh final regression and closeout evidence

After all executable/test-contract changes are complete:

1. reconcile every still-current parent/Rework1/Rework2/Rework3 obligation against the assembled candidate;
2. re-derive the complete affected surface from the final diff and callers/consumers;
3. run focused O18R/O20R/O21R/O19R/O23R checks;
4. run the complete affected-surface regression on the same commit;
5. run genuine A/B/C/D1/D2/D3 on that same commit;
6. run repository-required checks and the broader/full suite when final impact cannot be bounded confidently;
7. record exact commands and result counts in this workplan completion record or existing repository-standard closeout location;
8. record every unavailable/skipped required check by exact identity and reason; an unexecuted required check is not passed.

Failures touching revision 106, flexible fidelity, preparation identity, historical compatibility, restart/reuse, DATA7/DATA8, target-size persistence, TRAIN2 schedule/continuation, SIZE-FIDELITY, PERF-P2R, progress/status, or architecture protection changed here are affected until the failure itself proves otherwise.

Minimum affected suites include current equivalents of:

- `tests/test_mlff_flexible_fidelity.py` and any dedicated real-owner acceptance module;
- campaign CLI/store/config/status/advance/restart suites;
- prepare/preflight/materialization reuse suites;
- target-size topology/persistence suites;
- TRAIN2 runtime/continuation/schedule identity suites;
- SIZE-FIDELITY and PERF-P2R suites;
- historical migration/reuse suites;
- progress-format suites;
- current architecture/dependency/specification suites;
- every caller/consumer changed by the final implementation diff.

Old `200 passed, 1 skipped` or other pre-reopen counts cannot be copied forward as final evidence.

## 6. Protocol 5.6 acceptance matrix

| Claim | Required real owner/path | Allowed doubles | Forbidden substitution | Observable pass condition |
| --- | --- | --- | --- | --- |
| O18 preparation reuse | real config -> `CampaignStore` prepare receipt/preflight -> normal reuse/restart -> DATA7/DATA8 current-state decision | expensive source/model compute below reuse boundary | digest/stage-marker only; patched prepare compatibility | every downstream/execution field preserves authenticated upstream science; true scientific change fails closed |
| `n1` frontier | durable config change -> reopen -> normal restart/reconciliation/invalidation owner | external train/eval | direct invalidation helper | upstream survives; old study/TRAIN2 current authority resets; next screen 2 on horizon 30 |
| `n2` frontier | same | external train/eval | digest/helper only | fresh study from epoch 1; no prior coarse evidence relabeled |
| `n3` frontier | same | external train/eval | digest/helper only | exact tuple frontier; first new screen epoch 1 |
| horizon `n` frontier | same + real continuation/schedule validation | external train/eval | fake schedule-match/validator | upstream survives; old 30 rejected; fresh study epoch 1 on full 40 |
| A | real fresh config/store/preflight/target-size/restart/production consumers | actual training/eval | fake preflight authorization | 1/3/10; elimination no-later-work; durable selection; production 30 |
| B | same | actual training/eval | helper policy plan | 2/5/12 on full 40; endpoint/horizon separated; elimination no-later-work; production 40 |
| C | persisted target-size authority -> real SIZE-FIDELITY consumer | physical train/eval | helper-only execution plan | two semantic roles; one reusable physical epoch-30 endpoint |
| D1 | real historical store/receipt/stage/DATA8/study/schedule/restart owners | expensive compute | fake historical match/DATA8/study/stage digest | upstream reused; historical evidence rejected; fresh epoch 1 |
| D2 | same + real horizon validator | expensive compute | fake schedule validation | upstream reused; old 30 rejected; fresh epoch 2 on 40 |
| D3 | real preparation digest/signature/receipt/restart | expensive compute | custom store or monkeypatched digest/contract | scientific change fails closed at correct prepare boundary |
| O19 architecture | canonical graph/manual/spec + structural tests | none needed | sentence-presence proxy for structural invariant | current independent invariants remain protected; obsolete numeric/current-authority nodes absent |
| O23 anti-bypass | identifiable assembled acceptance set + structural negative guard | permitted external-compute mocks | owner replacement/direct invalidation helper in claimed acceptance | guard fails on forbidden bypass and permits below-owner fakes |

For every row, apply the counterfactual: if the required owner can break while the test remains green, the row is **not accepted**.

Production qualification: **deferred**. Do not run long real-data/GPU production qualification under this workplan.

## 7. Implementation authority

### Frozen

- all scientific/product design in Section 2;
- the real-owner/test-double boundaries in Sections 4-6;
- exact same-trajectory full-`n` continuation;
- immediate-predecessor-only historical compatibility and no historical evidence relabeling;
- positive preparation-scientific identity and downstream/execution/presentation exclusion;
- required stage-local/final affected regression and assembled integration;
- production/GPU qualification separation.

### Delegated

- exact helper/fixture names and organization;
- whether the reusable genuine campaign fixture lives in the existing flexible-fidelity test module or a dedicated acceptance module;
- exact AST/source mechanism for O23R;
- exact bounded fake trainer/evaluator implementation;
- minimal cache/materialization realization identity if a real owning cache requires it;
- equivalent graph-test formulation that preserves the explicit semantic dependency.

Delegated mechanics must not move or replace a frozen semantic owner boundary.

### Reopen only on evidence

Return to Software Design only if direct repository/assembled-integration evidence proves one of these frozen premises false:

- `training_backend`, `only_cueq`, or `require_available` changes authoritative DATA2-DATA8 scientific products;
- fidelity/horizon values are embedded in an authoritative preparation scientific product such that upstream scientific reuse is actually invalid;
- the immediate predecessor lacks sufficient authentic information for the currently accepted narrow D1/D2 compatibility path;
- genuine assembled integration exposes a scientific/state-machine defect that invalidates the frozen funnel or same-trajectory continuation premise;
- the real acceptance boundary cannot be exercised without changing a frozen material product/acceptance decision.

A difficult fixture, inconvenient test seam, failing helper test, or desire to reduce test effort is not a redesign trigger.

## 8. Initially expected affected behavioral surface

Primary product/state surface:

- `mdstats/training_data/_campaign_cli_core.py`;
- preparation projection/digest/receipt and completed-prepare/preflight reuse;
- historical compatibility/re-authentication;
- DATA7/DATA8 current discovery, matrix/materialization/schedule identity;
- target-size study construction/persistence/reduction;
- TRAIN2 schedule/checkpoint continuation and invalidation;
- preflight authorization;
- restart/next-operation/status consumers;
- SIZE-FIDELITY coincident endpoint planning;
- PERF-P2R production authorization if reached by final frontier corrections.

Primary test surface:

- `tests/test_mlff_flexible_fidelity.py`;
- any dedicated real-owner flexible-fidelity acceptance/anti-bypass module;
- campaign/store/restart/materialization suites discovered from real callers;
- TRAIN2 runtime/continuation suites;
- SIZE-FIDELITY/PERF-P2R suites;
- historical migration/preflight reuse suites;
- progress-format suites;
- `tests/test_mlff_data0_architecture_specification.py` and related current architecture/spec suites.

Current authority/documentation:

- `docs/arch_manuals/mlff_training_data_dependency_graph.json`;
- revision-106 architecture/manual/spec source only where structural wording/assertions require synchronization;
- tracked generated descendants only when their authoritative source changes.

This is provisional; O22R must re-derive the final affected surface from the assembled diff.

## 9. Gated implementation sequence

### R3R-W0 - Protocol 5.6 reopen and acceptance-boundary classification

- keep this same Rework 3 active;
- preserve the product corrections already present at `45c3` unless contradicted by direct evidence;
- classify every current frontier/A/B/C/D acceptance test by claim, real owner, allowed doubles, forbidden substitutions, and observable result;
- identify current direct-helper/custom-store/owner-mock substitutions and remove their acceptance authority rather than merely renaming them.

**Gate:** no material acceptance claim has an unidentified semantic owner or ambiguous double boundary.

### R3R-W1 - Complete O18R real reuse acceptance

Finish authenticated completed-prepare/preflight/DATA7/DATA8 reuse tests for every classified downstream/execution/presentation control plus one real scientific fail-closed control. Run focused checks and stage-local affected prepare/preflight/materialization/restart regression.

**Gate:** O18R closes semantically and functionally through real owners; digest-only evidence is supplemental.

### R3R-W2 - Replace proxy frontiers/integration with genuine persisted acceptance

Build one reusable genuine bounded campaign fixture and use it for O20R plus A/B/C/D1/D2/D3 where appropriate. Run real restart/reconciliation/preflight/historical/DATA8/schedule/SIZE-FIDELITY owners. Fake only external expensive compute. Install O23R targeted anti-bypass protection.

Run focused frontier and A/B/C/D tests, then stage-local affected campaign/restart/TRAIN2/SIZE-FIDELITY/PERF-P2R regression.

**Gate:** all four frontiers and six assembled cases pass; the O23R guard confirms no claimed acceptance replaces its owner.

### R3R-W3 - Finish O19R current authority/regression protection

Keep the corrected full-schedule graph edges, strengthen structural architecture assertions, and restore/map every still-current independent invariant lost in the earlier broad test reduction. Do not restore obsolete current-authority representation.

Run current architecture/dependency/manual/spec tests plus any executable suite invalidated by these test-contract changes.

**Gate:** current authority is semantically complete and no still-current independent invariant is protected only by a weak proxy.

### R3R-W4 - O22R final assembled acceptance

Perform final contract reconciliation and final affected-surface derivation. Run fresh same-commit focused checks, complete affected regression, genuine A/B/C/D1/D2/D3, anti-bypass guard, and repository/broader checks as required. Record exact commands/results.

**Gate:** no required check is failing/unexecuted; every material owner claim is proxy-proof under the counterfactual.

### R3R-W5 - Closeout

Only after W4 passes:

- mark this workplan completed;
- append fresh completion evidence;
- move it to `workplans/archive/`;
- update `workplans/active/README.md` to identify the final accepted candidate/commit.

Do not archive earlier.

### Current gate state at this reopening

- R3R-W0: **reopened / acceptance classification required under Protocol 5.6**;
- R3R-W1: **partially implemented, not accepted**;
- R3R-W2: **failed at `45c3` due proxy/bypass acceptance**;
- R3R-W3: **partially implemented**;
- R3R-W4: **not passed**;
- R3R-W5: **blocked**.

## 10. Design handoff closure

The reviewed gaps map losslessly to implementation obligations and proxy-proof evidence:

```text
O18 incomplete real reuse
    -> O18R genuine completed prepare/preflight/DATA7/DATA8 reuse path
    -> independent downstream controls + scientific inverse

O20 direct invalidation helper
    -> O20R durable config change + reopen + normal restart/reconciliation owner
    -> exact persistent frontier + next operation/screen/horizon

A/B fake preflight
    -> real preflight authorization with fake trainer only
    -> authorized work/freeze/restart/production assertions

C helper-only plan
    -> persisted target-size authority + real SIZE-FIDELITY consumer
    -> two semantic roles / one physical endpoint

D1/D2 custom stores + owner mocks
    -> real CampaignStore + real historical/DATA8/study/schedule/restart ownership
    -> bounded authenticated migration result

D3 mini store + digest mocks
    -> real prepare digest/signature/receipt/restart
    -> fail-closed preparation frontier

repeated bypass risk
    -> O23R targeted structural anti-bypass guard
    -> acceptance cannot remain green when claimed owner is replaced

partial architecture regression
    -> O19R structural current-invariant protection
    -> no obsolete representation restoration

missing final evidence
    -> O22R same-candidate fresh affected regression/integration
    -> exact recorded closeout evidence
```

No material user requirement, frozen scientific decision, preservation constraint, known cross-module consequence, or required acceptance boundary is intentionally delegated away.

## 11. Risks / redesign triggers

Primary risk is another false-positive green suite caused by replacing the exact production decision/state owner under acceptance. Protocol 5.6 owner boundaries and O23R exist specifically to prevent that recurrence.

Secondary risks are over-broad fixture construction that becomes a parallel campaign implementation, and over-broad anti-mock checks that forbid legitimate external-compute doubles. Prefer one real reusable persisted fixture and one narrowly targeted structural guard.

If a trigger in Section 7 fires, reopen only the affected design surface and preserve unrelated accepted product decisions/evidence.

## Frozen implementation principle

> **Acceptance must execute the production semantic owner whose behavior constitutes the claim; test doubles may replace expensive or external dependencies only below or outside that boundary. Evidence that could remain green while the required owner is materially broken cannot close the claim. Preserve the frozen flexible-fidelity science and exact persistence/restart semantics while enforcing this boundary without production-scale/GPU cost.**
