# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — Serious Challenge to accepted P5 D1/D2 semantics plus identified D4 conformance blockers; implementation is not current behavior until G0 is accepted  
**Current authority:** `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md`, current MLFF training-data architecture/specifications  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Review state:** third workplan review incorporated; no D3/D4 gate may bypass G0

## 1. Disposition

The current post-selection foundation-adaptation method is **NO-PASS / SERIOUS CHALLENGE** at D1 before D2.

Accepted D1 currently states both that the executable training method uses weighted energy+forces+stress loss and that every post-selection fold obtains its checkpoint monitor from training-eligible evidence. Accepted D2 concretizes those choices. The stakeholder-selected restoration instead requires native MACE `UniversalLoss` and one campaign-common protected target checkpoint monitor outside `T_selected`. These are upstream method changes, not a local loss-string or CV-plan repair.

The review also found a separate **D4 blocker under coherent current D1**: foundation-model fine-tuning is supposed to use checkpoint-bound foundation-residual atomic-reference fitting, but current P5 policy resolution defaults to from-scratch total-energy E0 fitting and its residual execution path does not provide the required foundation predictions/reference E0s. That defect must be repaired without weakening the accepted foundation-residual rule.

The plan remains deliberately reductive. Remove wrong/retired semantics, reconnect existing owners, and reuse qualified native MACE behavior. Do not create a custom loss, second sampler, shadow trainer, parallel identity registry, or compensating wrapper where owner rewiring/removal suffices.

## 2. Frozen cycle decisions

For **foundation-model P5 adaptation** (`naive_fine_tuning` and `multihead_replay`), the proposed accepted end state is:

```text
loss family                     native MACE UniversalLoss
huber_delta                     0.01, explicitly bound
global E:F:S coefficients       1:10:1
general config_weight in P5     neutral transport only; not a P5 loss layer
target:replay training scalar   none
atomic-reference mode           foundation_residual
replay-label default            TRUE_DFT
implicit target duplication     forbidden
force_mh_ft_lr                  true for multihead replay
checkpoint target monitor       one protected campaign-common 256-frame monitor
CV fold default                 3
held-out CV evidence            unavailable to fitting/checkpoint choice
replay degradation criterion    unchanged
production-scale GPU qualification deferred to final release
```

This workplan does **not** automatically change:

- P3 target-size screening loss/exposure semantics;
- P5 scratch-training loss semantics;
- target-size membership/order/reducer semantics;
- replay geometry split;
- TRUE_DFT default;
- target/replay acceptance thresholds;
- current optimizer-seed population;
- final-release GPU qualification policy.

A successful assembled restoration establishes that the **assembled restored method** works. Because loss, target-monitor topology, retired head scaling, default CV geometry, and D4 E0 conformance are corrected together, it does not by itself prove which individual change caused replay-retention recovery.

## 3. Governing invariants

### 3.1 Evidence roles

- P1/P2/P3 and frozen `T_N` / `T_selected` remain upstream and are preserved unless a direct dependency is demonstrated.
- Checkpoint-monitor evidence is development/model-control evidence. It supplies no gradients and is neither held-out CV evidence nor target-size authority.
- Held-out CV evidence cannot affect target membership, fitting, fitted preprocessing/E0, stopping, checkpoint choice, or monitor construction.
- Final production starts a fresh lineage and must use the same shared foundation-adaptation/checkpoint method validated by CV.
- One common target monitor is reused across every selected size, CV fold, CV seed, and final-production seed/run. Fold-specific, final-specific, or M3-specific target checkpoint parents define a different method.
- Sharing one monitor across folds correlates checkpoint/model-control decisions; D1 must state that limitation explicitly. Held-out fold evaluations remain the CV acceptance evidence.

### 3.2 Protected statistical separation

Exact frame disjointness is necessary but not sufficient. Incompatible evidence roles must also respect the canonical P1 split-exclusion authority covering:

```text
correlation_unit
geometry_duplicate
protected_event
replica_lineage
structural_realization
```

The restoration may not redefine that relation taxonomy or recompute it ad hoc downstream.

### 3.3 Replay

- TRUE_DFT replay remains the canonical training default when canonical labels exist.
- Foundation pseudo-label replay remains explicit opt-in.
- Pseudo-label training still requires an independent TRUE_DFT replay monitor.
- Changing replay label mode over the same prepared source/split must not change replay geometry membership.
- Replay retention remains an admissibility constraint, not target-size ranking credit.
- Existing target-force and replay-degradation thresholds are not relaxed to manufacture a pass.

### 3.4 Weight taxonomy

Keep four concepts separate:

1. global P5 energy/force/stress coefficients;
2. general `ConfigurationWeightPolicy` / `config_weight` for methods that actually consume it;
3. target-versus-replay **training-head scalar** weights, retired by this restoration;
4. checkpoint/adaptive-stop `target_score_weight` / `replay_score_weight`, which remain separately owned.

Retiring item 3 does not delete item 4 and does not globally delete item 2.

For restored UniversalLoss P5, item 2 is **not an active P5 loss layer** because pinned MACE UniversalLoss does not consume `ref.weight`. P5 must not fit or identity-bind a nontrivial `ConfigurationWeightPolicy` that has no executable effect. If D1/D2 decides nontrivial per-configuration weighting is scientifically mandatory for foundation-adaptation P5, this UniversalLoss proposal is inadmissible and G0 remains NO-PASS; do not emulate weighting through a custom loss, residual scaling, property-mask abuse, or sample duplication.

## 4. Proposed D2 foundation-adaptation method

### 4.1 UniversalLoss numerical identity

G0 must define the method mathematically rather than naming only a dependency class. For pinned `mace-torch==0.3.16` `UniversalLoss` with `delta=0.01`:

- energy uses Huber loss on per-atom energy residuals;
- stress uses Huber loss on Cartesian stress residuals;
- forces use MACE `conditional_huber_forces`;
- force Huber delta is multiplied by `[1.0, 0.7, 0.4, 0.1]` for reference-force-norm regimes `<100`, `[100,200)`, `[200,300)`, and `>=300`;
- global E/F/S coefficients multiply the three reduced property terms outside those nonlinear property reductions;
- local `config_energy_weight`, `config_forces_weight`, and `config_stress_weight` enter the nonlinear residual transformation and, for current P5, are binary availability masks only;
- `config_weight` / `ref.weight` is not consumed by UniversalLoss;
- reduction/distributed behavior must preserve the accepted native numerical semantics or reopen D2.

Current foundation-adaptation values are explicitly:

```text
loss_family   = universal
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

A future dependency may replace MACE 0.3.16 only after demonstrating the same accepted numerical semantics or after explicit D2 revision. Source markers/class names remain D3/D4 conformance evidence, not timeless D2 axioms.

### 4.2 Native sample exposure

Unless G0 explicitly revises it, restored P5 uses the qualified pinned-MACE combined-loader semantics:

```text
target dataset + replay dataset -> ConcatDataset
shuffle                         -> enabled under accepted seed
target/replay head balancing    -> none
intentional duplication         -> none
ratio-driven target duplication -> disabled by real_pt_data_ratio_threshold=0.0
force_mh_ft_lr                  -> true
non-LBFGS combined drop_last    -> native true
```

Authenticated membership and realized per-epoch exposure are therefore distinct claims: with `drop_last=true`, one final partial combined batch can be omitted after shuffle. Evidence must bind counts, seed/shuffle/sampler policy, batch size, `drop_last`, and batches/epoch. Do not claim every P5 frame is necessarily exposed exactly once per epoch.

This is separate from P3 target-size screening, whose optimizer normalization requires complete target batches and `drop_last=false`.

### 4.3 Foundation-residual atomic references remain mandatory

The restoration does **not** reopen the accepted foundation-residual E0 rule. For foundation adaptation:

- target-head E0s are fitted as elemental corrections to the exact selected/head-qualified foundation prediction baseline;
- CV fits use only that fold's gradient-training membership;
- the common target checkpoint monitor and held-out fold labels do not enter the E0 fit;
- final production fits on the complete exact `T_selected` training membership;
- the fit binds the exact foundation checkpoint **and selected foundation head**;
- target-head corrected E0s and replay/pretraining-head foundation E0s remain distinct head-local mappings where the dependency requires them.

Scratch mode retains from-scratch total-energy E0 fitting under its separately accepted method.

Pinned MACE multihead code can derive `pt_head` foundation E0s internally and, for some multi-head foundation tensor shapes, falls back to the first head. That behavior must be source-qualified against mdstats' selected foundation-head identity. If the selected foundation head is not the upstream fallback head, the existing qualified dependency seam must supply/ensure the correct head-qualified E0 realization or fail closed. Do not silently accept first-head E0s and do not create an unrelated second foundation-model identity owner.

## 5. Common target checkpoint monitor

### 5.1 Current topology

The proposed target checkpoint domain is one campaign-common monitor `M_mon` selected once from the current neutral statistical substrate's protected `OuterRole.OUTER_MONITOR` population:

```text
NeutralStatisticalBase
  +-- DEVELOPMENT   -> U_size -> pi_train -> T_N / T_selected
  +-- OUTER_MONITOR -> deterministic common target checkpoint monitor M_mon
```

Requested and normally realized size is 256. The number 256 has no relationship to a target-size rung beyond numeric coincidence.

For every configured target prefix and P5 run:

```text
M_mon ∩ T_N = empty
M_mon ∩ gradient_training = empty
M_mon ∩ held_out_evaluation = empty
```

In addition, no monitor frame may belong to a canonical P1 split-exclusion component that contains any frame of `T_selected`; configured-ladder qualification also checks every configured `T_N`.

If the neutral partition cannot provide a relation-clean monitor, reopen the P1/statistical-design owner rather than weakening relations or silently falling back to DEVELOPMENT.

### 5.2 Preserve sampler capability, not legacy DATA5 authority

Historical `OnlineMonitorPolicy` provides the useful sampling capability: balanced condition/run quotas plus deterministic systematic source-time spreading with seed 161803. The current historical implementation interface `build_target_online_monitor(data5_bundle, ..., label_domain_id, ...)`, however, is tied to retired DATA5/label-domain authority.

Transfer the sampling capability to the current neutral outer-partition/frame authority. Do not reactivate `label_domain_id`, pre-target-size DATA5 CV, or retired role-budget ownership. Advance current target-monitor records so their parent identity is the neutral outer partition/frame authority. Historical DATA5 monitor records remain historical/read-compatible only.

### 5.3 Collapse competing MLCV target-monitor machinery

Current `mlcv_monitors.py` owns a later fold/final target-full/target-light mechanism. Reconcile it rather than running two target-monitor systems:

- retire fold-specific and final-specific target checkpoint-parent construction;
- preserve TRUE_DFT replay full/light monitoring;
- preserve selection-inert training diagnostics;
- make every CV/final run reference the same common target-full membership;
- any lightweight target monitor used for stopping is only a deterministic subset of the common target monitor, never a new parent;
- remove duplicated target-side sampling responsibility once the common sampler owns it.

### 5.4 Retire M3 as final-production checkpoint monitor

Current final-production materialization uses frozen target-size `M3` as its target validation/checkpoint monitor. That is incompatible with the restored shared P5 checkpoint method.

Under this restoration:

- `M3` remains unchanged P3 target-size development/model-selection evidence;
- P5 final production must **not** use M3 for checkpoint selection/stopping;
- final production uses the same `M_mon` target checkpoint evidence as CV;
- no M3 identity is rewritten or reclassified to pretend it is `OUTER_MONITOR` evidence.

## 6. CV/final topology and schema cutover

### 6.1 CV fold structure

Current `PostSelectionCvFold` structurally owns a selected-only checkpoint monitor and partitions `T_selected` into train + monitor + outer evaluation + purge. The current-generation schema must advance.

Restored fold accounting is:

```text
T_selected -> gradient training + held-out outer evaluation + accepted purge/exclusion
```

`M_mon` is external to `T_selected` and is referenced by plan/run lineage, not owned as fold membership.

Historical selected-only fold-monitor schemas remain readable provenance but cannot authorize current restored runs. No migration may reinterpret an old fold-local membership as the new common monitor.

### 6.2 Default folds

Change the one authoritative current P5 default from 5 to 3 while preserving:

- `K >= 2`;
- explicit override;
- all-required-fold/all-required-seed acceptance;
- current optimizer-seed policy.

Do not revive retired DATA5 `cross_validation_folds` or `checkpoint_monitor_minimum_units_per_fold` merely because historical defaults contain three.

### 6.3 Final production

Fresh final production consumes the same foundation-adaptation loss/exposure method, common target monitor/checkpoint policy, replay-retention policy, foundation-residual E0 rule, and currentness semantics that CV validated. Only production horizon/seeds/publication policy remain role-specific.

## 7. Identity, fitted preparation, and currentness

### 7.1 Identity DAG

```text
accepted D1/D2 P5 method
 -> shared foundation-adaptation method identity
 -> CV/final role policy
 -> selected/replay/common-monitor/foundation-fit lineage
 -> run plan
 -> DATA8 materialization
 -> TRAIN2 runtime/checkpoint evidence
 -> checkpoint selection / EVAL2 interpretation
```

### 7.2 Shared method identity

Bind at least:

- method recipe generation and training mode;
- foundation checkpoint/head identity;
- UniversalLoss numerical identity for foundation-adaptation modes;
- local-property-mask policy;
- P5 sample-exposure semantics including `force_mh_ft_lr`, no duplication, shuffle/sampler, and combined `drop_last`;
- atomic-reference fit mode and foundation-head qualification;
- replay label/source/split policy;
- optimizer/LR/EMA/precision/backend semantics;
- shared checkpoint/admissibility policy and common-monitor construction policy.

Do not bind exact realized monitor membership into a pre-work shared method identity; exact parent/membership/digest belongs to plan/evidence lineage.

Do not reuse the entire `TargetSizeCommonTrainingPolicy.content_digest` as P5 method identity after P3/P5 divergence. Reuse real component owners only where their semantics are genuinely shared.

### 7.3 Fitted P5 preparation

Current P5 preparation fits `ConfigurationWeightPolicy`; remove that non-executable layer from restored UniversalLoss P5. If ExtXYZ transport requires `config_weight`, emit/validate neutral `1.0` without scientific identity. Binary local property masks remain authenticated.

Foundation-adaptation preparation must resolve `FOUNDATION_RESIDUAL` from **training mode**, not rely on the generic `AtomicReferenceFitPolicy` default. An explicit incompatible fit mode for foundation adaptation fails closed rather than silently changing method. Scratch resolves its separately accepted from-scratch fit.

CV fitted preparation binds fold gradient membership, exact foundation predictions/E0 mapping for the selected foundation head, and resulting corrected target-head E0 digest. Final fitted preparation binds full `T_selected` correspondingly.

### 7.4 Currentness cutover

Advance existing P5 method/run/materialization/evidence generations as required. Old weighted-stress/fold-local/M3-monitor artifacts are stale not only as verdicts but as executable continuation:

- old TRAIN2 checkpoints/workspaces cannot resume as restored foundation-adaptation runs;
- old DATA8 P5 materializations cannot be reused as current;
- old MLCV target-monitor catalogs cannot authorize current runs;
- old CV verdicts cannot authorize restored final production;
- old from-scratch-E0 foundation-adaptation preparations cannot authenticate restored foundation runs.

Preserve independent P1/P2/P3 evidence and frozen target memberships.

## 8. Scope and non-goals

### 8.1 Minimum affected-surface census

```text
docs/methods/mlff_scientific_method.md
docs/methods/mlff_numerical_algorithmic_method.md
docs/arch_manuals/mlff_training_data/**
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/mlff_data9a2_real_mace_realization_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/specs/training_data/mlff_adaptive_training_stop_spec.md
docs/guides/mlff_campaign_cli_user_guide.md
README.md
campaign.toml.example
mdstats/__init__.py
mdstats/training_data/__init__.py
mdstats/training_data/mace_compatibility.py
mdstats/training_data/critical_precision_cli.py
mdstats/training_data/foundation.py
mdstats/training_data/reference_fit.py
mdstats/training_data/model_features.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/post_selection_cv_plan.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/post_selection_publication.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/replay.py
mdstats/training_data/data8_bundle.py
mdstats/training_data/online_monitor.py
mdstats/training_data/mlcv_monitors.py
mdstats/training_data/adaptive_stop.py
mdstats/training_data/neutral_substrate/partition.py
mdstats/training_data/neutral_substrate/split_exclusion.py
mdstats/training_data/role_budget.py
foundation prediction/reference-E0 provider and current affected tests/qualification owners
```

Reference-census at least:

```text
UniversalLoss / WeightedEnergyForcesStressLoss / MACE_EXECUTABLE_LOSS_FAMILY
huber_delta
config_weight / ConfigurationWeightPolicy
config_energy_weight / config_forces_weight / config_stress_weight
target_head_weight / replay_head_weight / target_weight / head_weight
target_score_weight / replay_score_weight
AtomicReferenceFitMode / foundation_residual / foundation E0/head extraction
force_mh_ft_lr / real_pt_data_ratio_threshold
checkpoint_monitor_components_per_fold
OnlineMonitorPolicy / build_target_online_monitor
MlcvMonitorPolicy / MlcvRunMonitorRecord
M3 final-monitor routing
online_monitor_policy_digest / target_online_monitor_record_digest
fold_count / cross_validation_folds / checkpoint_monitor_minimum_units_per_fold
DATA5 / label_domain_id uses on current P5 paths
```

Affected-surface expansion discovered during implementation is not requirement expansion.

### 8.2 Explicit non-goals

- redesigning target-size ordering/membership/reducer;
- changing P3 loss merely to match P5;
- changing P5 scratch method without separate authority;
- changing replay geometry split or TRUE_DFT default;
- relaxing target/replay gates;
- restoring historical seed multiplicity solely for resemblance;
- custom trainer/loss/sampler;
- production-scale GPU qualification before final release.

## 9. Historical Applicability Set

PEM is materially applicable because this is mature-method restoration.

```yaml
pem_basis:
  accepted_project_state: 1b6b6f83918d31c4b27a0e60d7bc047ef58b6067
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-001
    disposition: APPLICABLE
    reason: MACE realization can drift from recorded method/foundation-head identity when model-affecting construction is duplicated or falls through upstream defaults.
  - id: FF-002
    disposition: APPLICABLE
    reason: Old stress/fold-local/from-scratch-E0 TRAIN2 state must not become continuation authority after the generation cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: Remove duplicated loss/monitor/weight ownership and return responsibility to real owners.
  - id: SP-002
    disposition: APPLICABLE
    reason: Retired fields, incompatible fit modes, historical schemas, and stale run state must fail closed.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve independent immutable P1/P2/P3/selection evidence rather than rebuilding it.
  - id: SP-004
    disposition: APPLICABLE
    reason: Real pinned-MACE and real monitor/currentness/foundation-head paths are required; helper-only proof is insufficient.
```

Refresh HAS if accepted memory or governing authority materially advances before closeout.

## 10. Capability-transfer map

```text
forced UniversalLoss -> stress rewrite
  -> remove only foundation-adaptation loss mutation
  -> retain source qualification and unrelated runtime repairs

P5 configuration-weight fitting
  -> retain general owner for methods that consume it
  -> project it out of UniversalLoss P5
  -> neutral config_weight only when transport requires it

fold-local / final-specific / M3 target checkpoint parents
  -> retire from current P5
  -> one neutral-OUTER_MONITOR common target monitor

legacy DATA5 common-monitor interface
  -> preserve deterministic balanced sampling capability
  -> current neutral outer-partition/frame parent

current MLCV fold/final target sampler
  -> retire competing target-parent construction
  -> preserve replay monitoring and training diagnostics

head-scalar replay materialization
  -> retire from current config/plan/cache/evidence
  -> historical read compatibility only as required

foundation E0 generic default / incomplete residual path
  -> preserve accepted foundation-residual scientific rule
  -> route foundation-adaptation modes through exact head-qualified residual inputs

current authenticated run/restart/currentness machinery
  -> preserve
  -> advance generation so incompatible old state cannot resume
```

## 11. Gates

### G0 — Mandatory D1 then D2 adjudication

**Goal:** repair the earliest challenged authority before D3/D4 implementation.

**Work:**

1. Amend D1 foundation-adaptation objective language so UniversalLoss is the proposed accepted loss for `naive_fine_tuning` / `multihead_replay`, while P3 and P5 scratch remain separately owned.
2. Amend D1 weighting semantics: nontrivial general per-configuration weighting is not an active UniversalLoss P5 layer; property masks remain binary availability semantics.
3. Amend D1 post-selection checkpoint semantics so one protected campaign-common monitor outside `T_selected` may control checkpoints across CV and final production; state correlation of model-control decisions across folds/runs.
4. Preserve all held-out/locked evidence prohibitions.
5. Preserve D1 foundation-residual E0 semantics; do **not** weaken them to accommodate current D4.
6. Amend D2 to define exact UniversalLoss functional and native sample-exposure semantics in §4.
7. Confirm adaptive score weights/replay-degradation semantics remain separate from retired training-head weighting.
8. Independently falsify the D1/D2 amendment and obtain required human acceptance before current-authority promotion.

**Acceptance:** D1/D2 are jointly coherent, reconstructible, and realizable without inert weighting fields; P3 and P5 scratch are unchanged unless separately reopened; any requirement for nontrivial P5 configuration weighting blocks UniversalLoss rather than spawning an emulation workaround.

### G1 — Complete authority/API/evidence census

Classify every affected reference as current authority, implementation/API, guide/config, compatibility reader, historical evidence, or unrelated concept. Include public exports, legacy DATA5/role-budget symbols, M3 final-monitor routing, atomic-reference defaults, and foundation-head/E0 extraction.

**Acceptance:** one current owner for each semantic; compatibility disposition explicit; no historical path is accidentally reactivated.

### G2 — Restore native UniversalLoss realization

- Remove only the foundation-adaptation UniversalLoss->stress source mutation.
- Keep source qualification, restart/CUDA/precision/runtime repairs and P3 complete-batch patch.
- Multihead replay allows native MACE UniversalLoss and verifies resolved class/parameters.
- Naive foundation fine-tuning explicitly requests UniversalLoss when native routing would not.
- Preserve and verify `force_mh_ft_lr=true` and `real_pt_data_ratio_threshold=0.0`.
- Bind delta/EFS/conditional-force semantics.
- If SWA/another phase can change loss coefficients/family, prove it disabled or bind/qualify that trajectory-changing behavior.

**Acceptance:** real pinned parser + `get_loss_fn()` + training path execute accepted foundation-adaptation loss; LR/EMA are not silently mutated; no custom loss exists.

### G3 — Remove inert P5 configuration weighting and retire head scalars

- Stop fitting/binding `ConfigurationWeightPolicy` in restored UniversalLoss P5.
- Preserve general configuration-weight owners for P3/other methods.
- Neutralize `config_weight=1.0` only when transport requires the key.
- Preserve binary property masks.
- Remove live `target_head_weight`, `replay_head_weight`, and equivalent `target_weight`/`head_weight` semantics from current config, replay preparation, cache identity, materialization, and evidence.
- Current configs specifying retired scalars fail closed with a removal/migration error.
- Historical payloads may remain readable but cannot authorize current P5.

### G4 — Restore foundation-residual E0 conformance

**Goal:** close the current D4 violation of accepted D1 §7.2 without changing the scientific rule.

**Work:**

- Resolve atomic-reference mode by training mode: `scratch -> FROM_SCRATCH_TOTAL_ENERGY`; `naive_fine_tuning` / `multihead_replay -> FOUNDATION_RESIDUAL`.
- Reject an explicit incompatible foundation-adaptation `fit_mode` rather than silently overriding it.
- For each CV fold, obtain foundation prediction energies and foundation E0s from the exact checkpoint + selected foundation head over the exact gradient-training membership only.
- For final production, fit over complete exact `T_selected` only.
- Supply those inputs to the existing residual-fit owner; do not write another E0 solver.
- Bind foundation checkpoint/head identity, fit membership digest, input-prediction/E0 identity, corrected target-head E0 digest, and conditioning evidence.
- Source-qualify pinned MACE `pt_head` E0 handling. A selected multi-head foundation must not silently use another/first head's E0s; use the existing dependency seam to ensure the selected-head mapping or fail closed.
- Monitor and held-out labels must never enter the fit.

**Acceptance:** real foundation-adaptation execution uses the accepted residual fit and head-qualified E0s; scratch remains from-scratch; the current default can no longer route a foundation run through total-energy E0 fitting.

### G5 — Move common target sampler onto current neutral authority

- Reuse/refactor the existing balanced condition/run/time systematic sampler.
- Parent it from current `NeutralStatisticalBase` / `NeutralOuterPartition` `OuterRole.OUTER_MONITOR` plus canonical frame authority.
- Remove current P5 dependence on `data5_bundle.outer_partition_for_domain(label_domain_id)` and legacy `parent_role=data5_outer_monitor` identity.
- Advance target-monitor record/policy generation as needed.
- Preserve historical DATA5 records only through explicit read compatibility.
- Review public exports; do not silently repurpose a legacy API to mean a new parent contract.

### G6 — Collapse CV/final target-monitor topology

- Advance CV policy/fold/plan and MLCV target-monitor generations.
- Remove `checkpoint_monitor_components_per_fold` and selected-only monitor fields from current fold semantics.
- Retire fold/final target-full parent construction in `mlcv_monitors.py`.
- Retire **M3 as final-production checkpoint monitor** while preserving M3 itself as P3 evidence.
- Preserve replay full/light monitoring and training diagnostics.
- Every CV/final run references the same common target-full membership; target-light is only a deterministic subset.
- Reconcile DATA8 target-monitor artifacts accordingly.

**Acceptance:** no current P5 path can construct/authorize a fold-local, final-specific, or M3 target checkpoint parent.

### G7 — Qualify actual protected monitor parent and separation

Produce actual LTA evidence with at least:

```text
neutral statistical-base / outer-partition digests
accepted NeutralLeakageReport disposition
P1 split-exclusion evidence digest
OUTER_MONITOR parent unit/frame counts
independence/effective-sample evidence already owned upstream
condition/run IDs represented
available -> selected counts per condition/run
source-time span/systematic positions
canonical label/property completeness for checkpoint metrics
requested/realized count
monitor membership digest
exact overlap with every configured T_N and T_selected
split-exclusion-component overlap with every configured T_N and T_selected
```

Do not invent a new generic minimum-run/unit constant. Do not treat `NeutralLeakageReport` as proof of cross-run duplicate/replica/structural-lineage separation when it does not test that claim; use the canonical P1 relation owner as well.

**Acceptance:** 256 realized when parent support permits; zero exact/protected-relation leakage; labels usable; diversity adequate under actual evidence. Failure reopens upstream statistical design rather than falling back to DEVELOPMENT.

### G8 — Restore CV default three

Change one authoritative current P5 default 5 -> 3; reconcile config/spec/guide/tests; preserve `K>=2`, override, all-required-fold/seed semantics, and current seed population; prove retired DATA5 K=3 authority was not reactivated.

### G9 — Preserve adaptive-stop/checkpoint score semantics

Preserve current `target_score_weight`, `replay_score_weight`, matched foundation replay baselines, signed replay degradation, and default 30 meV/A degradation budget unless separately changed by accepted authority. Retirement of training-head weights must not alter these policies.

### G10 — Method identity, runtime evidence, and restart/currentness cutover

Runtime evidence records at least:

```text
training role/mode
foundation checkpoint + selected head identity
loss family/class + exact UniversalLoss parameters
binary property-mask policy
E/F/S coefficients
atomic-reference fit mode + fit membership/input/result digests
target/replay membership digests and counts
combined count/head counts
shuffle/sampler seed and policy
batch size / drop_last / batches per epoch
force_mh_ft_lr / real_pt_data_ratio_threshold / realized duplication factor
LR / EMA / precision / backend
common target-monitor parent/policy/membership digest
replay monitor lineage
fold train/eval/purge membership
method/CV/run-plan digests
```

Advance existing generations as needed. Old stress/fold-local/M3-monitor/from-scratch-E0 foundation checkpoints, DATA8 materializations, monitor catalogs, and verdicts fail currentness before execution/restart reuse. Preserve independent P1/P2/P3/T_selected evidence.

### G11 — Counterfactual falsification matrix

At minimum falsify:

1. identity says UniversalLoss but runtime resolves stress;
2. runtime UniversalLoss delta/EFS/conditional-force semantics differ;
3. D2 omits config-weight non-consumption/property-mask nonlinear placement;
4. P5 still fits/binds nontrivial `ConfigurationWeightPolicy`;
5. non-neutral `config_weight` affects restored P5 trajectory/identity;
6. current config accepts retired target/replay head scalars;
7. replay materialization still applies head-scalar weighting;
8. foundation-adaptation resolves `FROM_SCRATCH_TOTAL_ENERGY`;
9. residual mode runs without exact foundation predictions/reference E0s;
10. residual E0 fit sees monitor or held-out labels;
11. selected foundation head differs from head used for foundation predictions/E0s;
12. pinned multihead `pt_head` silently uses first/wrong foundation-head E0s;
13. target monitor still consumes legacy DATA5/label-domain authority;
14. current MLCV still builds fold/final target checkpoint parents;
15. final production still uses M3 as checkpoint monitor;
16. common monitor is copied into fold-selected membership rather than external lineage;
17. monitor overlaps or is split-exclusion-related to any configured `T_N`;
18. monitor cannot realize adequate 256 evidence but execution continues;
19. monitor labels are unusable/incompatible for checkpoint metrics;
20. score/replay-retention weights are deleted with training-head weights;
21. default K falls back to five through another resolver;
22. legacy DATA5 K=3/role-budget semantics become current;
23. TRUE_DFT vs pseudo labels change replay geometry split;
24. MACE target duplication occurs;
25. `force_mh_ft_lr` is false/absent or LR/EMA are mutated;
26. P5 combined-loader sampler/drop_last differs from accepted exposure identity;
27. P3 complete-batch semantics change accidentally;
28. precision/backend changes without identity/evidence change;
29. old incompatible checkpoint resumes as current restored run;
30. stale weighted-stress CV authorizes restored final production;
31. exact common monitor differs across CV folds/seeds/selected sizes/final runs;
32. an execution-only field incorrectly invalidates scientific method identity;
33. a true method field fails to invalidate dependent evidence.

Every case is rejected by a real owner or documented inapplicable with evidence.

### G12 — Real-owner assembled qualification

Exercise the real path:

```text
campaign config
 -> D1/D2-conforming P5 resolver
 -> foundation/head identity + residual-E0 inputs
 -> neutral common-monitor construction
 -> target/replay materialization
 -> method/CV/run identity
 -> parser-facing MACE config
 -> source-qualified mdstats MACE seam
 -> pinned MACE 0.3.16 UniversalLoss
 -> head-qualified E0 realization
 -> native combined loader
 -> optimizer update
 -> TRAIN2 persistence/restart evidence
 -> adaptive stop/checkpoint evidence
 -> full checkpoint selection
 -> EVAL2 held-out evaluation
 -> fresh final-production representative path
```

Mocks are permitted only below/outside the semantic owner being proved.

### G13 — Bounded scientific pilot then full CV

Before full CV, record a true pre-update foundation baseline and first several restored checkpoints on representative real LTA data. Record target-monitor RMSE, TRUE_DFT replay RMSE/degradation, resolved loss/exposure identity, foundation-residual E0 identity, corpus counts, and common monitor identity.

Do not relax gates. Immediate replay degradation on the previous hundreds-of-meV/A scale falsifies the restored method and reopens D1/D2 rather than triggering another D4 patch.

After pilot PASS, run required three-fold affected qualification and independent Protocol 6.3 Review. Production-scale GPU qualification remains deferred to final release.

## 12. Review findings incorporated

Successive independent passes closed these material gaps:

1. D1, not D2, is the earliest contradictory owner.
2. UniversalLoss makes current P5 general `config_weight` weighting inert.
3. UniversalLoss numerical identity needed exact Huber/conditional-force/mask semantics.
4. Historical 256 target sampler has a retired DATA5/label-domain parent interface.
5. Current MLCV has a competing fold/final target-monitor owner.
6. CV and final production must use the same common target checkpoint parent.
7. Current CV schemas encode selected-only fold monitors and require generation cutover.
8. Exact frame disjointness is insufficient; canonical P1 split-exclusion relations also apply.
9. Neutral leakage evidence and P1 relation evidence answer different separation claims and both must be used appropriately.
10. Protected monitor membership does not by itself prove checkpoint-label adequacy.
11. Adaptive score weights are separate from retired training-head weights.
12. Native combined-loader shuffle/drop-last behavior is part of P5 exposure identity.
13. Old executable continuation must be cut off, not only old verdicts.
14. P3/P5 identity was over-coupled through the whole common-training-policy digest.
15. Public monitor API compatibility requires explicit disposition.
16. Current P5 foundation adaptation violates accepted foundation-residual E0 semantics by defaulting through the generic from-scratch policy and lacking residual inputs.
17. Pinned MACE multihead foundation E0 handling can fall back to the first head and therefore requires selected-head conformance qualification.
18. Current final production uses M3 as target checkpoint monitor; restored P5 must retire that routing without changing M3's P3 role.
19. `force_mh_ft_lr=true` is a material preservation condition and must be authenticated alongside no-duplication semantics.

## 13. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- UniversalLoss cannot express the required foundation-adaptation objective;
- nontrivial P5 configuration weighting is required;
- native combined-loader exposure is scientifically unacceptable;
- the protected neutral `OUTER_MONITOR` parent cannot provide adequate relation-clean checkpoint evidence;
- P3/P5 cannot legitimately use different loss/exposure methods for the intended conclusions;
- TRUE_DFT replay still causes material forgetting after correct restoration;
- target/replay acceptance gates are scientifically incompatible with the restored method.

Foundation-residual E0 failure caused by current wiring remains a D4 blocker while the accepted D1/D2 E0 rule is coherent. Reopen D1/D2 for E0 only if discriminating evidence challenges that rule itself.

Reopen D3 if one accepted method still requires competing durable owners. Local implementation defects under coherent D1-D3 remain D4 repairs.

## 14. Closeout

Close only after:

1. D1/D2 amendments are independently reviewed and accepted;
2. D3 has one coherent foundation-adaptation loss/exposure/E0/monitor/currentness flow;
3. D4 specs/code/config/public API/tests realize it with no inert current fields;
4. affected old evidence is stale only where materially dependent while independent P1/P2/P3/selection evidence remains usable;
5. semantic history explains replacement of weighted-stress/fold-local/M3-monitor/head-scalar lineage and the D4 E0 correction;
6. closeout learning/PEM is reconciled only where admission criteria are met;
7. the plan is archived only after still-current semantics reside in accepted authority.

Central closure invariant:

```text
accepted P5 scientific method
 = accepted P5 numerical method
 = recorded shared method identity
 = authenticated foundation/head + target/replay/common-monitor lineage
 = actual residual-E0 + pinned-MACE loss/loader realization
 = TRAIN2/restart evidence
 = checkpoint/EVAL2 interpretation
```

No current setting may change recorded method identity without changing governed execution, change governed execution without changing recorded identity, or remain current while having no executable/scientific effect.