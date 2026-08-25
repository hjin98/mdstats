---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK3
protocol_version: 5.5.0
status: active
reopened_date: 2026-08-25
reopened_from_commit: c32fc3fb46f61086c452952bc4f11d88b85b45ca
---

# MLFF Flexible-Fidelity Rework 3 - Reopened Closure Workplan

## 1. Objective and authority

Reopen Rework 3 and close the remaining implementation and acceptance gaps found by independent Software Design review of `feat/mlff-end-to-end-performance-v1` at `c32fc3fb46f61086c452952bc4f11d88b85b45ca`.

This is **not** a new scientific redesign. The accepted flexible-fidelity architecture remains frozen:

```text
0 < n1 < n2 < n3 <= n

default fidelity boundaries = (1, 3, 10)
default full TRAIN2 schedule horizon n = 30
```

The previous Rework 3 completion record (`200 passed, 1 skipped`) is retained only as historical development evidence. It is **not final acceptance evidence** because the reviewed tests did not yet prove the required real persistent invalidation frontiers and genuine A/B/C/D1/D2/D3 product boundaries.

The parent flexible-fidelity workplan, Rework 1, Rework 2, and all frozen decisions from the earlier Rework 3 remain authoritative except where this reopened plan makes the required acceptance mechanics more explicit.

## 2. Diagnosis and protected concerns

Independent review found six remaining closure defects:

1. **Preparation identity is not fully classified.** The large execution-only `model` projection leak was repaired, but `training_backend` remains inside preparation identity even though it is a TRAIN2 training/execution control unless repository evidence proves that it changes authoritative DATA2-DATA8 scientific products. `only_cueq` and `require_available` also require explicit ownership classification.
2. **The required `n1`/`n2`/`n3`/`n` invalidation frontier is still mostly digest/helper-level.** Rework 3 requires real persisted campaign consumers and exact record/stage assertions.
3. **Mandatory A/B/C/D1/D2/D3 integration still mocks semantic owners.** In particular, historical compatibility, current DATA8 discovery, target-size study construction, schedule validation, stage identity, and preflight authorization are replaced in places by monkeypatches or custom stores.
4. **The current dependency graph is semantic but incomplete.** It models `FULL_TRAIN2_SCHEDULE` but does not make the coarse/short/final screens depend on that full schedule identity, despite the frozen invariant that every screen is a pause on one uninterrupted full-`n` schedule.
5. **A broad architecture regression file was substantially reduced during a narrow closure change.** Obsolete revision-34/current-graph assertions should remain retired, but still-current unrelated MLFF invariants must not silently lose regression protection.
6. **The workplan was archived before the above acceptance requirements were actually demonstrated.** Green tests are not sufficient when the required product boundary was replaced by a test double.

Protected concerns:

- scientific selection behavior and selected target size must depend on the configured semantic funnel, not execution realization;
- preparation scientific identity must include every upstream scientific dependency and exclude downstream training, resource, cache, persistence, and presentation controls;
- fidelity/horizon changes must invalidate exactly the dependent state, neither less nor more;
- historical state may be reused only through the already accepted narrow fail-closed compatibility boundary;
- historical target-size evidence must never be relabeled as current flexible-fidelity evidence;
- all screen checkpoints are exact continuation endpoints on the same full TRAIN2 schedule with horizon `n`;
- final-screen `n3` and full-reference `n` are distinct semantic roles even when `n3 == n` physically;
- no production/GPU qualification is required during this repair.

## 3. Engineering envelope

### Functional/scientific

- Preserve `0 < n1 < n2 < n3 <= n` and generated defaults `(1,3,10)/30`.
- Preserve `q -> min(q,4) -> 2 -> 1` target-size funnel behavior, paired-seed target-only ranking, MVQUAL hard admission, and the fixed target-size candidate population.
- Preserve same-trajectory TRAIN2 continuation. `execution_epoch_limit` is a work/pause boundary only; it must not create a shortened scientific schedule.
- Screen evidence must authenticate both its semantic endpoint and the full schedule horizon.
- Production training starts from the selected target size and authorizes the full horizon `n`.

### Persistence/restart

- Reuse decisions must be made by the real current campaign identity, receipt, store, and orchestration consumers.
- A change to fidelity or horizon must not force DATA2-DATA8 scientific recomputation when their authoritative bytes/membership/topology are unchanged.
- A preparation-owned scientific change must fail closed at the narrowest correct upstream boundary.
- Rejected live TRAIN2 state may be preserved only as forensic/history state; it must not remain current executable authority.

### Test/resource

- Use bounded synthetic fixtures and fake heavy external MACE work.
- Do not run full production training, long real-data qualification, or GPU performance qualification.
- A test double may replace expensive external computation or unavailable source materialization, but it may not replace the semantic owner whose integration behavior is the subject of the test.

## 4. Product design and ownership

The product design remains the existing architecture. This reopening changes only incomplete implementation/acceptance details.

### 4.1 Preparation scientific identity

There is one positive preparation-scientific projection. It contains only configuration that can change authoritative preparation products through DATA8.

Known classification at handoff:

- **Preparation-scientific and retained:** fields that change source/evidence/partition/selection/materialization scientific content; resolved foundation inference device/dtype where existing DATA6 identity already treats them as scientific; the foundation inference backend if it changes authoritative DATA6 feature values.
- **TRAIN2/downstream and excluded:** `training.max_num_epochs`, target-size `fidelity_epochs`, TRAIN2 learning-rate/checkpoint/stopping policy, `acceleration.training_backend`, and downstream evaluation/verification/presentation controls.
- **Execution/cache realization and excluded from preparation-scientific identity:** `model.max_new_frames`, `inference_batch_size`, `maximum_inference_batch_size`, `estimated_inference_memory_mib_per_frame`, `batch_calibration_stress_structures`, `vram_max_device_fraction`, `vram_reserve_gib`, `batch_throughput_tolerance_fraction`, `pipeline_enabled`, `persistence_queue_depth`, `checkpoint_interval`, and `artifact_shard_size`.
- **Must be explicitly traced before final classification:** `acceleration.only_cueq` and `acceleration.require_available`. They are presumed execution/availability controls and therefore excluded **unless** direct repository evidence shows that changing them can change an authoritative DATA2-DATA8 scientific product after backend resolution. If they only constrain availability or choose whether execution is permitted, they are not preparation identity.

Do not solve execution-cache compatibility by widening preparation scientific identity. If an execution/cache artifact needs its own compatibility digest, use the already owning cache/materialization identity or a minimal local realization identity.

### 4.2 Fidelity and horizon ownership

- `TargetSizeStudyPolicy` owns `(n1,n2,n3)`.
- TRAIN2 budget/schedule policy owns `n`.
- Target-size evidence binds the semantic endpoint and the full schedule horizon.
- Therefore a tuple or horizon change may require a fresh target-size study/evidence while still preserving preparation scientific products.
- No old target-size evidence may be mechanically rewritten to match a new tuple or horizon.

### 4.3 Integration-test ownership rule

For the mandatory assembled tests, the following mechanisms are **semantic owners and must remain real** unless the implementation first proves a specific function is merely an external-compute transport wrapper:

- current TOML generation/parsing/normalization (`_config_template`, `_load_config`, validators);
- `CampaignStore` persistence and reopen behavior;
- preparation config digest and receipt compatibility;
- `_prepare_contract_signature`;
- `_historical_prepare_inputs_match_current`;
- `_current_data8_entries`;
- `_target_size_materialization_variants`;
- `_ensure_target_size_study`;
- target-size study serialization/validation/reduction;
- `_validate_train2_data8_matrix` and current schedule/materialization identity checks;
- `_stage_config_digest` and stored stage metadata;
- `_require_train2_preflight_authorization` or its real successor;
- restart/next-operation/status consumers;
- current invalidation/forensic-state owner.

**Forbidden:** monkeypatching one of the above to return the result the test is intended to prove.

**Allowed:** fake the actual MACE subprocess/train call, bounded prediction/evaluation values, heavyweight model loading, or unavailable large source-data production, provided the fake is below the semantic authorization/identity boundary and the real product still decides *what* work is authorized and *whether* state is reusable.

## 5. Implementation obligations

### O18R - Finish preparation scientific/execution identity repair

**Protected concern:** execution and TRAIN2 controls must not invalidate expensive preparation; true scientific preparation dependencies must still fail closed.

**Required end state:**

1. `acceleration.training_backend` is absent from preparation scientific identity unless concrete code evidence demonstrates that it changes authoritative DATA2-DATA8 products. Current design classifies it as downstream TRAIN2 and therefore expects removal.
2. `only_cueq` and `require_available` are traced to their consumers and classified by behavior, not by configuration section name.
3. The already removed model execution/cache fields remain excluded.
4. No negative "hash everything except..." filter is introduced. Keep a positive semantic projection.

**Required actions:**

- Trace every remaining field in `_PREPARATION_CONFIG_PROJECTION_FIELDS` to the first owner that consumes it.
- For `training_backend`, remove it from preparation projection unless the trace reaches DATA2-DATA8 scientific construction before TRAIN2.
- For `only_cueq` / `require_available`, record the classification in code comments/tests only to the extent needed to prevent future ownership drift; do not create a new registry or evidence framework.
- If an excluded field changes a reconstructible cache/materialization realization, authenticate that at the cache/materialization owner instead of invalidating preparation scientific state.

**Acceptance:**

A real `CampaignStore` completed-prepare/preflight fixture must be reused after each of these independent changes when scientific preparation inputs are unchanged:

- `training.max_num_epochs`;
- each of `n1`, `n2`, `n3`;
- `training_backend`;
- every already classified model execution/cache field above;
- `only_cueq` and `require_available` if classified execution-only;
- a presentation-only field.

At least one preparation-owned scientific control must independently prove the inverse: completed prepare reuse fails and the campaign reopens at the correct upstream boundary.

Digest equality unit tests may supplement these checks; they do **not** satisfy this acceptance by themselves.

### O20R - Prove exact persistent invalidation frontiers for `n1`, `n2`, `n3`, and `n`

**Protected concern:** over-invalidation wastes expensive preparation; under-invalidation can reuse scientifically incompatible training/evidence.

**Fixture requirement:** build one bounded baseline campaign using the real config loader and real `CampaignStore`. The persisted baseline must contain, as applicable:

- complete prepare stage and authenticated prepare receipt;
- complete preflight stage and smoke/matrix identity;
- current DATA7/DATA8 scientific records/materialization metadata sufficient for normal reuse consumers;
- a current target-size study with screen evidence;
- TRAIN2 schedule/execution/checkpoint or campaign records sufficient to exercise invalidation;
- stage config metadata used by normal restart logic;
- at least one unrelated scientific/upstream record that must survive;
- forensic/history behavior for invalidated live TRAIN2 records.

Do not use a custom in-memory store in place of `CampaignStore` for the acceptance matrix.

For each case, modify TOML/config through current normalization, reopen the durable store, invoke the normal reuse/restart/invalidation consumer, then assert the exact frontier.

#### O20R-1 - Change `n1` only

Example: `(1,3,10)/30 -> (2,3,10)/30` with a valid strict ordering.

Required result:

- preserve prepare receipt/stage;
- preserve preflight stage/smoke after current re-authentication;
- preserve DATA7/DATA8 scientific products whose bytes/topology are unchanged;
- invalidate the old target-size study and all old screen evidence as current authority;
- invalidate live TRAIN2 execution/checkpoint/training-campaign state that depended on the old study;
- preserve rejected live state only under existing forensic/history semantics;
- create/load a fresh study with configured tuple `(2,3,10)` and horizon `30`;
- first new screen authorization is exactly epoch `2`;
- no old epoch-1/3/10 evidence is relabeled into the new study.

#### O20R-2 - Change `n2` only

Example: `(1,3,10)/30 -> (1,5,10)/30`.

Required result is the same frontier as above: preparation/preflight/DATA7/DATA8 survive, fidelity-dependent study/evidence and TRAIN2 downstream state reset, and the fresh funnel restarts from configured `n1 = 1`. Do **not** reuse prior coarse evidence merely because old and new `n1` are numerically equal; the accepted compatibility rule resets fidelity-dependent target-size evidence for a tuple change.

#### O20R-3 - Change `n3` only

Example: `(1,3,10)/30 -> (1,3,12)/30`.

Required result is the same tuple-change frontier and first new authorization at `n1 = 1`. No old final-screen evidence is retained as current evidence.

#### O20R-4 - Change `n` only

Example: `(1,3,10)/30 -> (1,3,10)/40`.

Required result:

- preserve preparation/preflight/DATA7/DATA8 scientific products;
- invalidate target-size screen evidence that authenticated the old full schedule horizon;
- invalidate old TRAIN2 schedule/execution/checkpoint state and all cross-horizon dependent live state;
- reject a 30-horizon checkpoint/materialization as current 40-horizon authority;
- establish a full-40 schedule identity;
- create/load a fresh target-size study with `(1,3,10)` and horizon `40`;
- first new screen authorization is `n1 = 1` on the full-40 schedule;
- demonstrate that the stage endpoint shown/authorized is `1`, while schedule horizon remains `40`.

#### O20R-5 - Control cases

- **Preparation-owned change:** reuse must fail closed at or before prepare; downstream state cannot remain current.
- **Execution-only change:** preparation/preflight/DATA7/DATA8 scientific state remains reusable. Only the execution/cache artifact that owns the changed realization may be recreated if required.
- **Presentation-only change:** no scientific preparation, target-size, TRAIN2, or materialization state is invalidated.

**Acceptance format:** one parameterized or explicit matrix is acceptable, but each case must assert named preserved records/stages, named invalidated current records/stages, next authorized operation, next authorized screen epoch, and schedule horizon. A digest-only matrix is insufficient.

### O21R - Genuine bounded assembled A/B/C/D1/D2/D3 integration

All six mandatory cases must run on the final candidate through real configuration, `CampaignStore`, real semantic identity, real orchestration/restart/status consumers, and real target-size policy/study reducers. External heavy MACE compute may be faked below the authorization boundary.

#### Case A - Fresh default `(1,3,10)/30`

Required path:

```text
real generated TOML
 -> _load_config / validation
 -> real persisted prepare/preflight-compatible state
 -> real preflight authorization
 -> command/orchestrator authorizes coarse endpoint 1
 -> fake external train/evaluate only
 -> real evidence persistence/reduction
 -> short endpoint 3
 -> final-screen endpoint 10
 -> selected target size frozen
 -> durable store close/reopen
 -> real status/restart/next-operation consumer
 -> production authorization horizon 30
```

Assertions:

- authorized endpoints are exactly `[1,3,10]`;
- all screen executions retain full schedule horizon `30`;
- candidates eliminated at coarse receive no short/final work;
- candidates eliminated at short receive no final work;
- selected size is persisted and printed/status-visible;
- production uses only selected size and full horizon `30`.

#### Case B - Fresh nondefault `(2,5,12)/40`

Use actual TOML values, not an in-memory policy-only construction.

Assertions:

- normalized configuration is exactly `(2,5,12)` and `40`;
- real authorization endpoints are `[2,5,12]`;
- every screen run is on full schedule horizon `40`;
- progress/status differentiates authorized endpoint from schedule horizon, e.g. screen endpoint `2` must not be reported as `2/40` if that presentation implies a 40-epoch screen target; the output must expose semantic stage/endpoint and separate `schedule_horizon=40` (equivalent wording allowed);
- eliminated candidates receive no later work;
- durable selected size freezes;
- production authorizes full horizon `40`.

#### Case C - `(1,3,30)/30` coincident final/reference endpoint

This case must not remain a helper-only `build_size_fidelity_execution_plan` test.

Required path:

- real TOML/config and `CampaignStore`;
- real target-size orchestration through 1 -> 3 -> 30 and selection persistence;
- feed the persisted current policy/authority into the real SIZE-FIDELITY execution/checkpoint planning consumer;
- keep final-screen role and full-reference role semantically distinct;
- require only one physical epoch-30 checkpoint/evaluation per run when the owning execution plan can reuse it for both roles.

Assertions:

- `final_screen_epoch == reference_training_epoch == 30`;
- semantic role validation for both remains present;
- required physical checkpoint set contains epoch 30 once;
- no duplicate epoch-30 training work is scheduled solely because two semantic roles exist.

#### Case D1 - Historical completed preflight -> default `(1,3,10)/30`

Fixture must use real `CampaignStore` and an authenticated bounded representation of the immediately preceding fixed-fidelity generation.

Do not monkeypatch historical-input compatibility, stage digest, target-study construction, DATA8 discovery, or schedule validation to force reuse.

Required result:

- historical prepare/preflight inputs authenticate as unchanged;
- prepare/preflight and DATA7/DATA8 scientific products are reused;
- historical fixed-fidelity target-size study/evidence is not relabeled or imported into the current flexible study;
- a fresh current study is created with `(1,3,10)/30`;
- first new authorized screen is epoch `1`;
- old downstream live TRAIN2 state is invalidated/forensically retained according to the existing owner;
- status/restart points to the correct new work.

#### Case D2 - Historical completed preflight -> `(2,5,12)/40`

Use the same real ownership constraints as D1.

Required result:

- unchanged upstream scientific preparation survives;
- scientific DATA7/DATA8 content/membership/topology survives;
- any generated execution schedule realization that embeds the old 30 horizon may be regenerated by its owner without recomputing scientific preparation;
- a full-40 TRAIN2 schedule identity is established;
- old 30-horizon checkpoint/schedule state is rejected as current;
- fresh current study is `(2,5,12)/40`;
- first new authorization is epoch `2` on the full-40 schedule;
- no historical screen evidence is relabeled.

#### Case D3 - Preparation-affecting historical/config change

Use real `CampaignStore`, real preparation digest/receipt validation, and real restart/reuse consumer.

Required result:

- compatibility fails closed;
- the campaign reopens at the narrowest actual preparation boundary required by the changed scientific input;
- stale preflight/DATA7/DATA8/target-size/TRAIN2 state does not remain current authority.

### O19R - Complete current authority/documentation synchronization

**Required dependency-graph correction:**

The current semantic graph already contains `COARSE_SCREEN`, `SHORT_SCREEN`, `FINAL_SCREEN`, and `FULL_TRAIN2_SCHEDULE`. Add explicit dependency semantics showing that each screen execution is authenticated against the full TRAIN2 schedule identity. Preferred edges:

```text
FULL_TRAIN2_SCHEDULE -> COARSE_SCREEN       identity_requires
FULL_TRAIN2_SCHEDULE -> SHORT_SCREEN        identity_requires
FULL_TRAIN2_SCHEDULE -> FINAL_SCREEN        identity_requires
```

An equivalent single shared trajectory node is allowed only if it preserves the same unambiguous ownership with less total complexity.

Update structural tests to require these dependencies, not only graph acyclicity and node presence.

**Architecture regression-protection correction:**

The prior `test_mlff_data0_architecture_specification.py` was reduced substantially. Do not blindly restore obsolete revision-34 graph metadata. Instead:

1. Compare the pre-Rework-3 test file at parent `48a5ef6f807d425c597e3f2f96b0b889a1918bf9` with the current file.
2. Classify each removed assertion as one of:
   - obsolete because revision 106 intentionally replaced the old graph/schema/current-authority representation;
   - still protected by an equivalent test elsewhere;
   - still-current invariant whose protection was accidentally lost.
3. Restore or relocate every still-current lost invariant.

At minimum, preserve direct regression protection for these still-current nonnumeric/nonlegacy concerns unless repository evidence shows a newer canonical test already does so:

- canonical MLFF-DATA stage order;
- frame-fact fields remain policy-independent (no eligibility/partition/selection/exposure/acquisition decision fields embedded as raw frame facts);
- locked-test evidence remains operationally sealed from development/training-control decisions;
- held-out/locked validation cannot retroactively control target-size/training/checkpoint selection;
- current MACE checkpoint-control fail-closed semantics and retained evaluation checkpoints where still normative;
- core current manual/spec publication artifacts exist and agree with current package version where that is an existing repository contract.

Do **not** restore assertions that require the current dependency graph to report historical `architecture_revision == 34`, old `schema_version == 26`, or superseded node names simply to increase test count.

**Current-language structural checks:**

- current authority must not contain numeric semantic node names `SIZE_STUDY_EPOCH3`, `SIZE_STUDY_EPOCH10`, `SIZE_STUDY_EPOCH30`;
- current documentation may mention historical fixed `(3,10,30)` only in explicitly historical/compatibility context;
- revision 106 history/index remains synchronized;
- migration language retains the narrow immediate-predecessor exception and fail-closed behavior.

### O22R - Re-establish final regression and executable closeout evidence

After all executable changes are complete:

1. Reconcile every parent/Rework1/Rework2/Rework3 obligation against the assembled candidate.
2. Re-derive the affected surface from the actual final diff and callers/consumers.
3. Run fresh focused tests for O18R, O20R, O21R, and O19R structural assertions.
4. Run the complete affected-surface regression on the same commit.
5. Run A/B/C/D1/D2/D3 on that same commit.
6. Run repository-required checks. If final impact cannot be bounded confidently, run the broader/full available suite.
7. Record the exact commands and result counts in this workplan completion record or an existing repository-standard closeout location. If any check is skipped/unavailable, record its exact test/command and reason.
8. A failure that touches revision 106, flexible fidelity, preparation identity, historical compatibility, campaign restart, DATA7/DATA8 reuse, TRAIN2 schedule identity, SIZE-FIDELITY, PERF-P2R, progress/status, or an architecture assertion changed in this repair is **affected** and blocks closure unless proven otherwise from the failure itself.

Minimum affected suites include the repository's current equivalents of:

- `tests/test_mlff_flexible_fidelity.py`;
- campaign CLI/store/config/status/advance/restart tests;
- prepare/preflight/materialization reuse tests;
- target-size topology/persistence tests;
- TRAIN2 runtime/continuation/schedule identity tests;
- SIZE-FIDELITY tests;
- PERF-P2R tests;
- historical migration/reuse tests;
- progress reporting format tests;
- current MLFF architecture/dependency-graph/specification tests;
- any test containing a caller/consumer changed by the final diff.

The old `200 passed, 1 skipped` record may not be copied forward as final evidence. Fresh results are required after the reopened executable/test-contract changes.

## 6. Implementation authority

### Frozen

Implementation must not change without a genuine redesign trigger:

- `0 < n1 < n2 < n3 <= n`;
- defaults `(1,3,10)/30`;
- independent ownership of screen boundaries and full TRAIN2 horizon;
- exact same-trajectory continuation;
- fixed candidate ladder, MVQUAL admission, `q -> min(q,4) -> 2 -> 1`, paired seeds, target-only ranking;
- target-size evidence binds semantic endpoint plus full schedule horizon;
- final-screen `n3` and reference `n` remain separate semantic roles;
- historical compatibility is limited to the immediate fixed-fidelity predecessor and requires re-authentication;
- historical target-size evidence is never relabeled as flexible evidence;
- preparation scientific identity is positive and excludes downstream/execution/presentation policy;
- production/GPU qualification is deferred.

### Delegated

Implementation may choose:

- exact helper names and fixture builders;
- whether execution-cache realization compatibility uses an existing owner digest or one minimal new local digest;
- whether frontier tests are parameterized or separate;
- exact bounded fake MACE/prediction implementation;
- equivalent semantic graph realization if it is simpler and preserves explicit full-schedule-to-screen dependency.

These mechanics are delegated only if all semantic owners and acceptance boundaries above remain real.

### Reopen only on evidence

Return to Software Design only if evidence proves one of the following:

- `training_backend`, `only_cueq`, or `require_available` genuinely changes authoritative DATA2-DATA8 scientific products and therefore must remain in preparation identity;
- a fidelity or horizon change cannot preserve preparation/DATA7/DATA8 scientific state because an authoritative scientific product actually embeds that downstream value;
- the immediate predecessor historical receipt lacks enough evidence to authenticate a required D1/D2 reuse, requiring a narrower supported-compatibility decision;
- genuine assembled integration exposes a scientific/state-machine defect that invalidates a frozen funnel or continuation premise.

A difficult fixture, a failing existing helper-level test, or inconvenience regenerating schedule files is **not** a redesign trigger.

## 7. Initially expected affected behavioral surface

Primary executable/state surface:

- `mdstats/training_data/_campaign_cli_core.py`;
- preparation config projection/digest and prepare restart receipt validation;
- historical prepare compatibility and re-authentication;
- DATA7/DATA8 current-entry discovery, semantic matrix identity, and schedule/materialization realization;
- target-size study construction/persistence/reduction;
- TRAIN2 schedule/checkpoint continuation and invalidation;
- preflight authorization;
- status/restart/next-operation consumers;
- SIZE-FIDELITY checkpoint planning for `n3 == n`;
- PERF-P2R production authorization if touched by final frontier changes.

Primary test surface:

- `tests/test_mlff_flexible_fidelity.py`;
- campaign/store/restart/materialization suites discovered from callers;
- `tests/test_mlff_train2b_runtime.py` or current equivalent;
- SIZE-FIDELITY/PERF-P2R suites;
- progress-format tests;
- `tests/test_mlff_doc_arch1_specification.py`;
- `tests/test_mlff_data0_architecture_specification.py`;
- any current historical migration/preflight-reuse tests.

Documentation/current authority:

- `docs/arch_manuals/mlff_training_data_dependency_graph.json`;
- revision-106 architecture source/assembled manual if graph semantics require wording changes;
- revision index/history only if synchronization changes;
- tracked generated PDF/manifest descendants only when their authoritative source changes.

This list is provisional. Final acceptance must re-derive the affected surface from the assembled diff.

## 8. Task-specific acceptance matrix

| Requirement | Must execute through | Forbidden shortcut | Pass condition |
| --- | --- | --- | --- |
| Preparation identity | real config + `CampaignStore` + real prepare reuse | digest equality alone | execution/downstream changes reuse prepare; scientific change fails closed |
| `n1` frontier | durable current campaign + restart/invalidation owner | direct invalidation helper only | upstream survives; old study/TRAIN2 state resets; next epoch is new `n1` |
| `n2` frontier | same | digest-only | fresh study from `n1`; no old screen evidence relabeled |
| `n3` frontier | same | digest-only | same exact tuple-change frontier |
| `n` frontier | same + real schedule identity | fake schedule-match result | upstream survives; old horizon rejected; fresh study begins at `n1` on new full horizon |
| A | real fresh config/store/preflight authorization | fake preflight authorization | 1/3/10 screens, selection freeze, restart/status, production 30 |
| B | same | helper-only policy plan | 2/5/12 screens on full 40, eliminated no-work, production 40 |
| C | real persisted campaign + SIZE-FIDELITY consumer | helper-only execution plan | one physical epoch-30 endpoint, two semantic roles |
| D1 | real historical store/receipt compatibility | fake historical-match/study/DATA8/stage digest | upstream reused; historical evidence rejected; fresh epoch-1 screen |
| D2 | same + new horizon identity | fake schedule validation | upstream reused; old 30 schedule/checkpoint rejected; fresh epoch-2 screen on 40 |
| D3 | real prepare digest/receipt/restart | monkeypatched new digest result | preparation change fails closed at correct upstream boundary |
| Current graph | canonical graph + structural tests | node presence only | each screen explicitly depends on full schedule; no numeric semantic stage nodes |
| Architecture regression | current tests | deleting unrelated protection | still-current independent invariants remain covered |

Production qualification: **deferred**. Do not run long production/GPU qualification as part of this workplan.

## 9. Implementation sequence and gates

### R3R-W0 - Reopen and classify

- Keep this workplan active.
- Trace `training_backend`, `only_cueq`, and `require_available` to actual consumers.
- Identify the exact existing test fixture utilities and real `CampaignStore` paths that can construct bounded prepare/preflight/DATA8/historical state without heavy production data.
- Compare the pre-Rework-3 and current architecture-regression tests and classify removed assertions.

**Gate:** no unclassified preparation-projection field and no unidentified semantic owner required by A/B/C/D1/D2/D3.

### R3R-W1 - Preparation identity repair

Implement O18R only.

Then run:

- focused projection/receipt tests;
- real completed-prepare reuse controls for execution/downstream/presentation changes;
- real fail-closed preparation-owned control;
- stage-local campaign/preflight/materialization regression affected by the change.

**Gate:** semantic and functional closure before adding frontier/integration fixtures on top of this behavior.

### R3R-W2 - Persistent frontier and assembled integration

Implement O20R and O21R.

Order work so the reusable real persisted fixture is built once and shared where appropriate rather than reimplementing campaign semantics inside tests.

Run focused frontier matrix and A/B/C/D1/D2/D3, followed by stage-local affected campaign/restart/TRAIN2/SIZE-FIDELITY/PERF-P2R regression.

**Gate:** all four independent frontiers plus all six assembled cases pass without forbidden semantic-owner mocks.

### R3R-W3 - Current authority and regression-protection synchronization

Implement O19R after executable behavior is stable.

- add full-schedule-to-screen graph dependencies;
- update structural tests;
- restore/relocate still-current architecture regression assertions lost in the prior reduction;
- regenerate tracked documentation descendants only if authoritative source changed.

Run documentation/architecture tests plus any executable tests invalidated by test-contract edits.

**Gate:** current authority is semantic and complete; no unrelated still-current regression invariant was silently discarded.

### R3R-W4 - Final assembled acceptance

Implement O22R.

- final conformance reconciliation;
- final affected-surface derivation;
- fresh affected regression;
- fresh A/B/C/D1/D2/D3 on same commit;
- repository-required/broader suite as required by impact;
- exact closeout commands/results recorded.

**Gate:** no required affected check unexecuted or failing; no acceptance claim relies on a forbidden mock or obsolete earlier result.

### R3R-W5 - Closeout

Only after R3R-W4 passes:

- set workplan status to completed;
- append the fresh completion record;
- move this file back to `workplans/archive/`;
- update `workplans/active/README.md` to state that the reopened Rework 3 candidate, not commit `c32fc3fb...`, supplies final flexible-fidelity closure evidence.

Do not archive earlier.

## 10. Design handoff closure

The independent-review findings map losslessly to implementation and executable acceptance:

- residual preparation-identity uncertainty -> O18R -> real completed-prepare reuse/fail-closed controls;
- missing exact `n1/n2/n3/n` frontier -> O20R -> durable four-case record/stage matrix;
- helper/mocked assembled acceptance -> O21R -> explicit real-owner/no-mock contract for A/B/C/D1/D2/D3;
- incomplete full-schedule graph semantics -> O19R -> explicit schedule-to-screen identity edges and structural assertions;
- reduced unrelated architecture regression -> O19R -> assertion-by-assertion classification and restoration of still-current protections;
- premature `200 passed, 1 skipped` closeout -> O22R -> fresh same-candidate affected regression and assembled integration with exact evidence.

No known material review finding is intentionally deferred. No scientific funnel decision is reopened.

## 11. Risks and redesign triggers

- **Positive projection omission risk:** removing a field from preparation identity is unsafe if it truly changes scientific DATA2-DATA8 products. Consumer tracing and the preparation-owned control protect against this.
- **Fixture self-implementation risk:** a large synthetic fixture can accidentally reimplement compatibility/orchestration. Keep fixtures to data construction; call real owners for decisions.
- **Cache/scientific identity conflation:** regenerated schedule or shard/cache bytes do not imply scientific preparation invalidation. Authenticate realization at its owner.
- **Historical evidence insufficiency:** if the accepted immediate-predecessor path cannot be authenticated from persisted evidence, fail closed and reopen only that compatibility decision rather than inventing permissive migration.
- **Regression weakening:** do not delete old assertions merely because they fail after documentation evolution; first determine whether the protected invariant is obsolete or the current implementation/documentation is wrong.
