# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — serious upstream D2 challenge; implementation not yet authorized as current behavior  
**Current authority:** `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md`, current MLFF training-data architecture/specifications  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  

## 1. Objective

Restore the post-selection foundation-model fine-tuning/replay method to the historically demonstrated MACE `UniversalLoss` behavior, restore the campaign-common protected 256-frame target checkpoint monitor, retire the current target/replay training-head scalar-weight mechanism, and restore the post-selection CV default to three folds while preserving TRUE_DFT replay, existing target/replay acceptance thresholds, target-size evidence, and the current frozen target memberships.

This is not a local D4 loss-string repair. The accepted D2 paper currently requires weighted energy+forces+stress loss for the MACE method, treats forced `UniversalLoss` as a dependency behavior that must be suppressed, and states that each post-selection fold derives its checkpoint-monitor role from training-eligible evidence. Current implementation/specification follows that authority. Historical and current failure evidence now materially challenge those D2 statements for P5 foundation fine-tuning/replay. Therefore D2 must be reconciled first; D3/D4 may not silently contradict accepted D2.

This workplan is temporary transition coordination and does not itself change current product authority.

## 2. Triggering evidence and problem

Current P5 cross-validation with TRUE_DFT replay showed catastrophic replay forgetting: all observed candidate checkpoints were rejected, target-force error could improve while replay error degraded by hundreds of meV/A, and the current fold-local checkpoint monitors could be extremely small because one split-exclusion component per fold was reserved as the monitor.

Historical reconstruction established that the prior successful foundation fine-tuning path used native MACE `UniversalLoss`; the pinned MACE 0.3.16 multi-head path naturally chooses `UniversalLoss`; the current adapter deliberately rewrites that choice to `stress`; an older campaign-common deterministic 256-frame target monitor already exists over protected `OUTER_MONITOR`; and target/replay scalar weights survived through several schema/configuration layers even though `UniversalLoss` does not realize those scalars as the intended independent target-versus-replay loss weighting.

The repair is deliberately reductive: remove the incorrect loss override, retire the unsupported head-scalar machinery, and reconnect P5 to the existing protected monitor owner rather than adding another loss, sampler, compatibility wrapper, or scheduler.

## 3. Governing invariants

### 3.1 Scientific/statistical invariants

- Held-out CV evaluation remains unavailable to fitting, checkpoint choice, stopping, or target-size choice.
- Target-size screening remains upstream and target-only; P5 replay changes cannot mutate P2/P3 target-size memberships/evidence.
- TRUE_DFT replay remains the canonical default; pseudo-label replay remains explicit opt-in.
- The existing target-force acceptance ceiling and replay-retention ceiling are not relaxed to make the repaired method pass.
- Replay geometry/split identity is independent of whether training labels are TRUE_DFT or foundation pseudo-labels.
- Checkpoint monitoring is model-control/development evidence, not held-out CV evidence and not target-size authority.

### 3.2 Numerical invariants

For P5 foundation-model adaptation, the proposed restored loss identity is:

```text
loss_family   = universal
loss_class    = native MACE UniversalLoss
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

`huber_delta=0.01` is bound explicitly rather than inherited as an invisible dependency default.

Do not conflate three distinct weight concepts:

1. global E/F/S objective coefficients;
2. general scientific `ConfigurationWeightPolicy` / per-configuration weighting where separately accepted and consumed by its owner;
3. target/replay training-head scalar weights.

This workplan retires only item 3 from current P5 UniversalLoss semantics. It does not automatically delete general configuration weighting, checkpoint-ranking weights, replay-retention thresholds, or other separately owned quantities that happen to contain the word `weight`.

### 3.3 Membership/exposure invariants

Under restored P5 UniversalLoss there is no independent mdstats target-versus-replay scalar. Relative aggregate exposure arises from authenticated target and replay memberships and native combined-loader semantics.

Intentional target duplication remains forbidden. `real_pt_data_ratio_threshold=0.0` remains required for the replay-enabled pinned-MACE path. Effective target membership/count must equal authenticated target exposure.

### 3.4 Monitor invariants

Target-size ladder populations originate only from the accepted DEVELOPMENT target-size universe. The restored checkpoint monitor originates only from protected `OUTER_MONITOR` through the existing common deterministic target-monitor owner.

For the common target monitor `M_mon` and every configured target-size prefix `T_N`:

```text
M_mon intersection T_N = empty
```

For every post-selection fold `k`, with gradient-training membership `G_k` and held-out evaluation `E_k`:

```text
G_k intersection E_k     = empty
M_mon intersection G_k   = empty
M_mon intersection E_k   = empty
```

The value 256 appearing as both a possible target-size rung and monitor cardinality is numerical coincidence; no monitor membership may be derived as a rung, prefix, complement, or folded-off part of the target-size ladder.

### 3.5 Identity/currentness invariants

Recorded P5 method identity, generated MACE configuration, materialized memberships, native dependency realization, TRAIN2 runtime evidence, and EVAL2 reconstruction must describe one method.

A trajectory-changing change to loss family, Huber delta, E/F/S coefficients, foundation/head identity, replay label/exposure lineage, optimizer/LR/EMA semantics, precision/backend, or checkpoint policy invalidates materially dependent P5 evidence.

CV-policy identity separately binds fold count, partition seed, monitor identity/policy, CV horizon, required optimizer seeds, and acceptance policy.

Old weighted-stress P5 CV evidence cannot authorize final production under restored UniversalLoss.

## 4. Scope

### Included

- current D1/D2 clauses governing post-selection checkpoint evidence, loss/exposure, and dependency realization;
- P5 CV and final-production method identity/currentness;
- MACE compatibility/critical-precision execution seam;
- replay preparation/materialization where target/replay scalar weighting is represented;
- DATA8/MACE ExtXYZ/cache identities affected only by retired head scaling;
- common protected online target monitor integration;
- P5 fold planning after removal of fold-local checkpoint-monitor allocation;
- CV default fold count;
- configuration, specifications, architecture, user-facing current documentation, tests, qualification, and semantic-history consequences of the accepted change.

### Explicitly excluded unless reopened by evidence

- changing target-size P2/P3 candidate membership/order/reducer;
- automatically changing the P3 target-size screening loss family;
- changing TRUE_DFT replay to pseudo labels;
- changing replay train:monitor geometry split;
- relaxing target/replay acceptance thresholds;
- restoring historical optimizer-seed multiplicity merely for historical resemblance;
- adding a custom loss, custom sampler, alternate trainer, shadow method registry, or parallel monitor implementation;
- production-scale GPU qualification before the established final-release qualification phase.

## 5. Historical Applicability Set

PEM is materially applicable because this cycle restores/replaces mature training machinery.

```yaml
pem_basis:
  accepted_project_state: 1b6b6f83918d31c4b27a0e60d7bc047ef58b6067
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-001
    disposition: APPLICABLE
    reason: P5 MACE method identity and actual dependency realization can drift when model-affecting semantics are reconstructed/overridden in multiple owners.
  - id: SP-001
    disposition: APPLICABLE
    reason: This repair should remove duplicated/incorrect loss, monitor, and head-weight machinery and return responsibility to native/current owners rather than add synchronization wrappers.
  - id: SP-002
    disposition: APPLICABLE
    reason: Retired head-weight fields and stale CV evidence must fail closed at current identity/configuration boundaries.
  - id: SP-003
    disposition: APPLICABLE
    reason: Unaffected prepared memberships and authenticated completed evidence should be preserved rather than recomputed merely because downstream P5 semantics change.
  - id: SP-004
    disposition: APPLICABLE
    reason: Real pinned-MACE parser/loss/loader/TRAIN2/EVAL2 qualification is required; helper/mock-only proof cannot close this repair.
```

The PEM is partial and reconciled only through its declared historical horizon. Absence of another lesson is not evidence of non-applicability. Refresh this HAS if the accepted PEM basis materially advances before implementation closeout.

## 6. Capability-transfer map

```text
current forced universal->stress source rewrite
  -> retain source qualification and runtime authentication
  -> remove only the loss-family mutation for restored P5

current fold-local one-component P5 monitor
  -> retire monitor extraction from T_selected
  -> reuse existing OnlineMonitorPolicy/build_target_online_monitor over OUTER_MONITOR

current target/replay head-scalar configuration and weighted replay materialization
  -> retire from current P5 UniversalLoss semantics
  -> retain historical schema read support only where compatibility requires it

current authenticated membership/currentness machinery
  -> preserve and extend only as needed for restored method identity
```

## 7. Gates

### G0 — D1/D2 challenge adjudication and method reconciliation

**Goal:** repair the earliest affected authority before implementation.

**Work:**

- Re-review D1 checkpoint-development versus held-out-evaluation roles. Amend D1 only if current wording cannot represent one campaign-common protected target monitor without changing the scientific estimand.
- Amend D2 Sections 8-9, 14-18, verification oracles, and reproducibility language as required.
- Split target-size-screen objective authority from P5 foundation-adaptation objective authority. Do not leave the current claim that one executable loss family necessarily governs every MLFF training role.
- For P5 foundation fine-tuning/replay, accept native UniversalLoss with explicit `huber_delta=0.01` and global E:F:S `1:10:1`.
- State explicitly that P5 UniversalLoss has no independent target/replay scalar head weight.
- Replace the fold-local checkpoint-monitor construction rule with the campaign-common protected `OUTER_MONITOR` rule.
- Preserve TRUE_DFT as canonical replay-label default, no-hidden-target-duplication semantics, fresh CV/final lineages, held-out evaluation exclusion, and existing acceptance gates.

**Acceptance:**

- Current D1 and D2 are internally coherent and jointly realizable.
- D2 no longer simultaneously requires weighted-stress P5 while the workplan asks D4 to execute UniversalLoss.
- D2 clearly distinguishes P3 target-size screening from P5 foundation adaptation.
- No accepted authority still requires a fold-local monitor from `T_selected` for checkpoint choice.
- Human acceptance required by the D1/D2 authority process is recorded before dependent D3/D4 promotion.

### G1 — Current-authority and affected-surface census

**Goal:** prevent hidden parallel owners and stale current documentation.

**Work:**

Reference-census at least:

```text
UniversalLoss
WeightedEnergyForcesStressLoss
MACE_EXECUTABLE_LOSS_FAMILY
loss="stress"
loss="universal"
huber_delta
target_head_weight
replay_head_weight
head_weight
target_weight
configuration_weight
checkpoint_monitor_components_per_fold
online_target_monitor_configurations
OnlineMonitorPolicy
build_target_online_monitor
fold_count
```

Classify every result as current normative owner, current implementation, current guide/example, historical/release evidence, or unrelated weight concept.

Inspect at minimum:

```text
docs/methods/mlff_scientific_method.md
docs/methods/mlff_numerical_algorithmic_method.md
docs/arch_manuals/mlff_training_data/**
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/mlff_data9a2_real_mace_realization_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/guides/mlff_campaign_cli_user_guide.md
README.md
campaign.toml.example
mdstats/training_data/mace_compatibility.py
mdstats/training_data/critical_precision_cli.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/post_selection_cv_plan.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/replay.py
mdstats/training_data/data8_bundle.py
mdstats/training_data/online_monitor.py
mdstats/training_data/mlcv_monitors.py
```

**Acceptance:**

- Every current owner of changed semantics is mapped.
- Historical source patches/workplans remain historical and are not rewritten as current authority.
- No current README/guide/spec continues to describe retired head-scalar or fold-local-monitor semantics after implementation.
- Weight concepts not owned by this workplan are preserved with explicit reason.

### G2 — Loss realization restoration

**Goal:** make P5 execute the accepted native UniversalLoss method without introducing a custom loss.

**Work:**

- Remove the P5 path's source rewrite that changes native MACE multi-head `UniversalLoss` into `stress`.
- Retain the source-shape/version qualification and unrelated qualified patches.
- For replay-enabled multi-head fine-tuning, allow pinned MACE to select UniversalLoss natively and verify the result.
- For any accepted non-multihead foundation fine-tuning role requiring UniversalLoss where MACE will not select it automatically, request `loss="universal"` explicitly.
- Explicitly bind `huber_delta=0.01` through current method/config identity and runtime evidence.
- Make runtime loss validation role/method aware rather than globally requiring `WeightedEnergyForcesStressLoss`.

Preserve unrelated execution semantics, including target-size complete final batches, restart-epoch repair, TRAIN2 persistence/recovery, membership authentication, CUDA/process-lifetime repairs, `force_mh_ft_lr=True` where applicable, and `real_pt_data_ratio_threshold=0.0` for replay-enabled fine-tuning.

**Acceptance:**

- Real pinned MACE parser + native `get_loss_fn()` resolves UniversalLoss for accepted P5 foundation adaptation.
- P3 remains on its separately accepted method unless G0 explicitly changes it.
- No mdstats custom loss implementation exists.
- Mutating `huber_delta` changes P5 method identity and runtime configuration together.

### G3 — Retire target/replay training-head scalar weighting

**Goal:** remove a current parameter family that has no accepted meaning under restored P5 UniversalLoss.

**Work:**

- Remove `target_head_weight` and `replay_head_weight` from current generated/default/example P5 configuration.
- Remove current resolver ownership and current P5 method/evidence fields representing those scalars.
- Remove target/replay ExtXYZ `config_weight` multiplication or weighted-cache recipes whose sole purpose is those scalars.
- Reconcile `ReplayPreparationPlan` `head_weight`/`target_weight` fields: remove them from the current schema or isolate them strictly to historical read compatibility; do not leave live defaults such as 1/10 or 1/5 under a new name.
- Reconcile DATA8 replay cache/content identities so retired scalar weights cannot alter current UniversalLoss P5 materialization or cache key.
- Current configuration that explicitly supplies retired target/replay training-head scalar fields must fail closed with a migration/removal error rather than silently ignore them.

Do not delete general `ConfigurationWeightPolicy`, checkpoint ranking/score weights, or replay-retention parameters merely because they contain `weight`.

**Acceptance:**

- Current P5 has no independent target/replay scalar parameter or runtime evidence field.
- Counterfactual mutation of a general `ConfigurationWeightPolicy` field that UniversalLoss P5 does not consume cannot silently alter P5 executable identity/trajectory; either it is genuinely consumed and bound, or it is outside P5 identity.
- No current replay materialization scales configurations solely to emulate retired head weighting.
- Legacy serialized records remain readable only to the degree required by current compatibility policy and cannot authorize a current method.

### G4 — Restore campaign-common protected 256-frame target monitor

**Goal:** reconnect P5 checkpoint selection to the existing protected monitor owner and stop consuming selected training cardinality for monitoring.

**Work:**

- Retire `checkpoint_monitor_components_per_fold` from current P5 policy/identity/configuration.
- Remove `_spaced_selection(...checkpoint_monitor_components_per_fold...)` or equivalent fold-local monitor allocation from the P5 CV plan.
- Reuse the existing common target-monitor construction over `OuterRole.OUTER_MONITOR`; do not implement another sampler.
- Preserve the established deterministic condition/run-balanced, time-systematic sampling semantics and seed unless G0 establishes a different accepted owner.
- Bind requested size, realized membership digest, parent outer-partition identity, policy identity, and condition/run stratum census into appropriate CV/checkpoint evidence.
- Fold construction over `T_selected` shall create only gradient-training, held-out evaluation, and accepted purge/exclusion state; the common target monitor is external to `T_selected`.

**Acceptance:**

- Requested target monitor size is 256.
- Exact zero overlap is proven against every configured `T_N`, not only selected `T_N`.
- Exact zero overlap is proven against every fold's gradient-training and held-out evaluation memberships.
- Same accepted parent + policy + seed reconstructs identical monitor membership.
- No one-component/tiny fold-local checkpoint monitor remains in current P5.

### G5 — Monitor-parent adequacy qualification

**Goal:** prove the existing sampler has an adequate parent in the actual LTA campaign instead of assuming cardinality implies diversity.

**Work:**

Produce an actual-data monitor census containing at least:

```text
OUTER_MONITOR parent frame count
independent-unit composition available from existing evidence
condition IDs represented
run IDs represented
available frames per condition/run
selected frames per condition/run
source-index/time span or equivalent temporal spread evidence
requested monitor count
realized monitor count
monitor digest
intersection with every target-size prefix and T_selected
```

Do not introduce a new arbitrary generic minimum-run/minimum-unit constant merely to pass this gate.

**Acceptance:**

- Realized target monitor count is exactly 256 when the protected parent has at least 256 eligible frames.
- Existing condition/run/time systematic sampler materially represents the available protected parent.
- Any inability of the protected parent to provide an adequate monitor reopens the upstream partition/statistical-design owner; P5 must not silently sample DEVELOPMENT or accept a tiny biased monitor.

### G6 — Restore default post-selection CV fold count to three

**Goal:** reduce default CV cost and restore the intended three-fold default without changing explicit-user overrides or conflating CV design with training-method identity.

**Work:**

- Change the one authoritative P5 default from 5 to 3.
- Regenerate/reconcile example configuration, guides, specs, and tests from that owner.
- Preserve `K >= 2` and explicit configured override support.
- Preserve the current required optimizer-seed population unless separately changed by accepted authority.

**Acceptance:**

- Default current P5 CV resolves exactly three folds.
- No second resolver/default silently restores five.
- Changing only `fold_count` changes CV policy/plan identity and downstream CV currentness, not the shared P5 training-method recipe identity.

### G7 — Runtime evidence and method/currentness cutover

**Goal:** prove one method from configuration through dependency realization and prevent stale evidence reuse.

**Work:**

Extend/reconcile existing evidence owners to record at least:

```text
training role
loss family/native class
huber_delta
energy/forces/stress coefficients
foundation/head identity
replay label mode
replay source/split identity
target train count
replay train count
combined count
membership digests
batch size and material drop_last semantics
batches per epoch where meaningful
LR and EMA settings
real_pt_data_ratio_threshold / duplication evidence
common target monitor identity and realized count
fold train/eval memberships
method and CV policy digests
```

No current target/replay training-head scalar evidence field shall remain.

Advance existing P5 method recipe/currentness schema/generation as needed; do not create another registry.

**Acceptance:**

- Weighted-stress P5 CV/final evidence is stale for restored UniversalLoss method.
- Prepared target-size evidence and exact `T_selected` remain reusable unless independently shown dependent on the changed P5 method.
- A true method-field mutation changes identity and blocks stale descendants.
- An inert/retired field cannot retire or authorize current P5 evidence.

### G8 — Counterfactual falsification matrix

**Goal:** ensure tests discriminate the repaired semantics rather than merely seeing expected strings.

At minimum attempt to falsify:

1. generated P5 config says UniversalLoss but wrapper executes stress;
2. method identity says UniversalLoss but runtime class is weighted-stress;
3. Huber delta changes without identity/currentness change;
4. E/F/S coefficients change without executable/evidence change;
5. current config still accepts `target_head_weight`;
6. current config still accepts `replay_head_weight`;
7. replay materialization still scales `config_weight` for target/replay ratio;
8. `ReplayPreparationPlan` retains live current head-scalar semantics;
9. retired scalar changes a P5 cache key/trajectory;
10. general configuration weighting is accidentally removed from a separately owned path;
11. checkpoint ranking/retention score weights are accidentally removed with head weights;
12. P5 monitor is derived from DEVELOPMENT, `T_selected`, fold training, or fold evaluation;
13. a one-component/tiny fold-local monitor returns;
14. common monitor overlaps any configured target prefix;
15. common monitor overlaps fold evaluation;
16. actual protected parent cannot realize 256 but execution silently continues;
17. default fold count falls back to five through another resolver;
18. TRUE_DFT versus pseudo-label selection changes replay geometry split;
19. MACE duplicates target examples;
20. accepted LR/EMA are silently overwritten;
21. stale weighted-stress CV evidence authorizes UniversalLoss final production;
22. a true method-field mutation fails to invalidate evidence;
23. an execution-only field incorrectly changes scientific method identity.

**Acceptance:** every counterfactual is either rejected by the real owner or demonstrated inapplicable with documented reason.

### G9 — Real-owner assembled qualification

**Goal:** close the repair through the production semantic path, not a reimplementation in tests.

Exercise:

```text
campaign configuration
 -> canonical P5 method/CV resolver
 -> target/replay/common-monitor materialization
 -> MACE parser-facing configuration
 -> qualified mdstats execution seam
 -> pinned mace-torch 0.3.16
 -> native UniversalLoss
 -> real combined loader
 -> optimizer update
 -> TRAIN2 persistence/runtime evidence
 -> checkpoint admissibility
 -> EVAL2 reconstruction/evaluation
```

Mocks/doubles are allowed only below/outside the owner whose behavior is being proved.

**Acceptance:** real dependency-facing evidence proves configured identity equals actual executable semantics and membership/exposure semantics.

### G10 — Bounded scientific pilot before full CV

**Goal:** cheaply falsify the restoration before spending a full CV campaign.

**Work:**

Using representative real prepared LTA data and the restored method, record a true pre-update checkpoint before the first optimizer step and the first several epoch boundaries. Measure at least:

```text
target force RMSE
TRUE_DFT replay force RMSE
replay degradation versus frozen foundation baseline
resolved loss identity
resolved corpus counts/exposure evidence
common target-monitor metric
```

Keep target/replay thresholds unchanged.

**Acceptance:** the method remains NO-PASS if replay degradation immediately reproduces the previous hundreds-of-meV/A failure. Do not cure failure by widening the retention gate. If the pilot falsifies the restored method, reopen D2 with the actual evidence rather than layering another D4 compensation.

### G11 — Full affected regression, CV qualification, and independent Review

**Goal:** close the assembled transition only after all affected owners and evidence are reconciled.

**Work:**

- run focused tests after each material executable stage;
- run affected post-selection/replay/monitor/TRAIN2/EVAL2/currentness/configuration regression;
- run broader suite where impact cannot be confidently bounded;
- run three-fold post-selection CV after G10 passes;
- perform independent Protocol 6.3 Review against assembled candidate, current authority, actual dependency realization, HAS/capability transfer, and impact closure;
- reconcile current architecture/specifications/guides/README, semantic history, evidence applicability, workplan status, and PEM only if its admission/reconciliation criteria are actually triggered.

**Acceptance:**

- no Serious Challenge remains unresolved;
- no genuine D1-D4 blocker remains;
- required tests and real-owner qualification pass;
- current docs no longer describe retired P5 semantics;
- stale historical evidence remains recoverable but cannot authorize current behavior;
- production-scale GPU qualification remains explicitly deferred to final release and is not falsely claimed.

## 8. Review-pass findings incorporated before activation

The workplan was independently challenged against accepted head `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067` before publication. The following gaps were found and are closed in the plan rather than deferred as amendments:

1. **D2 is the earliest contradictory owner.** Current D2 explicitly requires weighted energy+forces+stress semantics and explicitly treats forced UniversalLoss as a dependency defect. G0 now makes D2 adjudication mandatory before D4.
2. **Current D2 also owns the wrong monitor topology.** Section 14 explicitly derives a checkpoint-monitor role from fold training-eligible evidence. G0/G4 now amend that owner rather than merely rewiring `post_selection_cv_plan.py`.
3. **P3/P5 loss semantics were previously over-coupled.** The repair now explicitly preserves P3 unless separately reopened, avoiding an unjustified target-size-method change.
4. **Head-weight authority is internally inconsistent.** Campaign config currently resolves target/replay 5:1 while `ReplayPreparationPlan` has live `target_weight`/`head_weight` semantics in replay machinery. G3 requires retirement across config, plan schema, materialization, cache identity, and runtime evidence rather than deleting only two TOML keys.
5. **`weight` is overloaded.** General configuration weighting, target/replay training-head weighting, and checkpoint/retention score weighting are distinct. The plan now contains negative tests to ensure the repair removes only the retired head scalar.
6. **Existing protected monitor machinery should be reused.** The plan forbids another sampler and adds actual-parent adequacy evidence because diversity cannot be inferred from requested count alone.
7. **The active documentation surface is broader than D2/code.** Stage-plan/spec/guide/README references to checkpoint monitor, scoring, and current loss semantics are included in the census and closeout so current docs cannot retain a second truth.
8. **Historical replication is not claimed literally.** Three-fold default is restored, but current optimizer-seed policy remains unchanged; TRUE_DFT is intentionally preserved. The scientific pilot therefore tests the assembled restored method without attributing any improvement solely to one simultaneous change.
9. **Evidence causality is bounded.** Success after simultaneous loss/monitor/head-weight/fold restoration establishes the assembled restored method, not that any one component alone caused the historical/current difference. Discriminating follow-up evidence is required for narrower causal claims.
10. **PEM basis is older/partial.** The HAS is explicitly bound to the accepted PEM publication and must be refreshed if the accepted memory advances; the newer repository head itself is not falsely treated as an accepted PEM publication.

## 9. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- UniversalLoss cannot express the scientifically required P5 objective;
- P5 genuinely requires an independent target/replay scalar after all;
- the native combined loader has unacceptable exposure semantics not representable by authenticated corpus membership;
- the protected `OUTER_MONITOR` parent cannot provide scientifically adequate checkpoint evidence;
- P3/P5 cannot legitimately use different loss families under the intended target-size estimand;
- TRUE_DFT replay still causes material forgetting after the other restored semantics are correctly realized;
- existing target/replay acceptance gates are scientifically incompatible with the restored method.

Reopen D3 when one accepted method still requires multiple competing owners or a new durable structural boundary. Local implementation defects under coherent D1-D3 remain D4 repairs.

## 10. Closeout

When all gates pass:

1. promote accepted D1/D2 amendments through their normal authority process;
2. reconcile D3 architecture to one loss/monitor/identity flow;
3. reconcile D4 specifications, implementation, tests, configuration, guides, and README;
4. preserve affected evidence/currentness and explicitly stale only materially dependent old P5 evidence;
5. record semantic history explaining why weighted-stress/fold-local-monitor/head-scalar P5 was replaced;
6. perform closeout-learning/PEM assessment without manufacturing a new family from one coordinated intervention;
7. archive this workplan only after its still-current semantics live in accepted current authority.

The central closure invariant is:

```text
recorded P5 method identity
  = configured P5 method
  = authenticated target/replay/monitor memberships
  = native MACE executable realization
  = TRAIN2/EVAL2 evidence interpretation
```

No current setting may change recorded scientific/numerical identity without changing actual execution, or change actual execution without changing recorded identity.