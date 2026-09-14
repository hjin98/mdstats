# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — Serious Challenge to accepted D1/D2 P5 semantics; implementation is not current behavior until the upstream authority change is independently reviewed and accepted  
**Current authority:** `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md`, current MLFF training-data architecture/specifications  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Review state:** second independent workplan review incorporated; no implementation gate may bypass G0

## 1. Disposition and objective

Current P5 authority is challenged at D1 before D2. Accepted D1 currently states both that the executable training method uses weighted energy+forces+stress loss and that each post-selection fold obtains its checkpoint monitor from training-eligible evidence. Accepted D2 concretizes the same choices. The restoration selected for this cycle instead requires native MACE `UniversalLoss` and one campaign-common protected target checkpoint monitor outside `T_selected`. This is therefore an upstream method revision, not a local loss-string or CV-plan repair.

The proposed end state for P5 foundation-model adaptation is:

```text
loss family                     native MACE UniversalLoss
huber_delta                     0.01, explicitly bound
global E:F:S coefficients       1:10:1
general config_weight in P5     not a scientific weighting layer; neutral transport only
target:replay training scalar   none
replay-label default            TRUE_DFT
implicit target duplication     forbidden
checkpoint target monitor       one protected campaign-common 256-frame monitor
CV fold default                 3
held-out CV evidence            unavailable to fitting/checkpoint choice
replay degradation criterion    unchanged
production-scale GPU qualification deferred to final release
```

The repair is deliberately reductive. Remove wrong/retired semantics, reconnect to current owners, and reuse qualified native MACE behavior. Do not create a custom loss, second sampler, shadow trainer, parallel identity registry, or compensating wrapper where owner rewiring/removal suffices.

A successful assembled restoration demonstrates that the restored method works. Because loss, monitor topology, retired head scaling, and default CV geometry change together, it does not by itself prove that any one of those changes caused the historical/current replay-retention difference.

## 2. Triggering evidence

Current TRUE_DFT post-selection CV produced no admissible checkpoint in the observed campaign: target error could improve while replay degradation rose by hundreds of meV/A. The current P5 monitor can also become extremely small because one split-exclusion component is reserved per fold.

Historical/current-source reconstruction established that:

- prior successful foundation multi-head fine-tuning executed native MACE `UniversalLoss`;
- pinned `mace-torch==0.3.16` natively forces `UniversalLoss` for multi-head fine-tuning;
- current mdstats deliberately rewrites that native choice to `stress`;
- an older fixed 256-frame target-monitor design used deterministic condition/run/time-balanced model-control evidence shared by competing runs;
- current P5 contains live target/replay scalar-weight fields even though UniversalLoss does not consume `config_weight` as an independent scalar;
- current MLCV later introduced a separate fold/final target-monitor subsystem rather than the old common monitor.

These observations motivate the challenge but do not self-authorize the replacement method. G0 owns the upstream adjudication.

## 3. Governing scientific/statistical invariants

### 3.1 Evidence roles

- Target-size P2/P3 evidence remains upstream, target-only, and immutable under replay-only/P5 changes.
- `T_N` and `T_selected` remain exact authenticated target memberships.
- Checkpoint-monitor evidence is development/model-control evidence. It may select/stabilize a checkpoint but is not held-out CV evaluation and is not target-size authority.
- Held-out CV evidence cannot affect fitting, fitted preprocessing/E0, checkpoint choice, stopping, target size, or monitor construction.
- Final production begins a fresh lineage and must execute the same shared P5 training/checkpoint method that CV validated.
- The common target monitor is reused across every selected size, CV fold, CV seed, and final-production seed/run. A fold-specific or final-specific target checkpoint domain would define a different method.
- Sharing one monitor across folds creates correlated model-control decisions. D1 must state this limitation explicitly; held-out outer evaluations remain the independent fold evidence used for CV acceptance.

### 3.2 Replay invariants

- TRUE_DFT replay remains the canonical default when canonical true labels are available.
- Foundation pseudo-label replay remains explicit opt-in and never replaces the mandatory true-reference replay-monitor lineage.
- Switching TRUE_DFT versus pseudo-label training labels over the same source/split must not change replay geometry membership.
- Replay retention remains an admissibility constraint, not positive target-size ranking credit.
- Existing target-force and replay-degradation gates are not weakened to manufacture a pass.

### 3.3 Weight taxonomy

Four distinct concepts must not be conflated:

1. global energy/force/stress coefficients of the P5 loss;
2. general `ConfigurationWeightPolicy` / `config_weight` used by separately accepted methods;
3. target-versus-replay training-head scalar weights, which this restoration retires;
4. checkpoint/adaptive-stop target/replay score weights, which remain separately owned by the stopping/ranking policy.

Retiring item 3 does not delete item 4 and does not globally delete item 2.

For restored UniversalLoss P5, item 2 is also **not an active P5 loss weighting layer**, because pinned MACE UniversalLoss does not consume `ref.weight`. P5 therefore must not fit or identity-bind a `ConfigurationWeightPolicy` that has no executable effect. If the upstream owner decides that nontrivial per-configuration scientific weighting is mandatory for P5, UniversalLoss as proposed here is not an admissible concretization and G0 must remain NO-PASS rather than emulate the weights with a custom loss, property-mask abuse, residual scaling, or sample duplication.

## 4. Proposed D2 numerical method for P5

G0 must make the loss reconstructible mathematically rather than naming only the dependency class.

For pinned MACE 0.3.16 `UniversalLoss` with `delta = 0.01`:

- energy uses Huber loss on per-atom energy residuals;
- stress uses Huber loss on Cartesian stress residuals;
- forces use MACE `conditional_huber_forces`;
- the force Huber delta is multiplied by `[1.0, 0.7, 0.4, 0.1]` according to reference-force norm regimes `<100`, `[100,200)`, `[200,300)`, and `>=300`;
- global energy/forces/stress coefficients multiply the three reduced loss terms outside those nonlinear property reductions;
- local `config_energy_weight`, `config_forces_weight`, and `config_stress_weight` participate inside the nonlinear residual transform and for current P5 are binary availability masks only;
- `config_weight` / `ref.weight` is not consumed by UniversalLoss and therefore cannot carry current P5 scientific weighting authority;
- distributed/reduction behavior must remain equivalent to the accepted native reduction semantics or reopen D2.

The current P5 values are explicitly:

```text
loss_family   = universal
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

A future MACE version may replace the pinned implementation only if it proves these accepted numerical semantics, or after a new D2 revision. Source markers and Python class names are D3/D4 conformance evidence, not timeless D2 axioms.

### 4.1 P5 sample exposure

The restoration uses native pinned-MACE combined-loader semantics unless G0 explicitly changes them:

```text
target dataset + replay dataset -> ConcatDataset
shuffle                         -> enabled under the accepted seed
target/replay head balancing    -> none
intentional duplication         -> none
ratio-driven target duplication -> disabled by real_pt_data_ratio_threshold=0.0
non-LBFGS combined drop_last    -> native true
```

Therefore authenticated corpus membership and realized per-epoch exposure are not identical claims: with `drop_last=true`, at most one final partial combined batch is omitted after shuffle. Runtime evidence must record combined count, head counts, seed/sampler/shuffle policy, batch size, `drop_last`, and batches per epoch. Do not falsely claim every P5 frame is exposed exactly once per epoch.

This P5 exposure rule is separate from P3 target-size screening, whose optimizer-normalization method requires complete target batches and `drop_last=false`.

## 5. Proposed checkpoint-monitor topology

### 5.1 One current target monitor

The current P5 target checkpoint domain shall be one campaign-common monitor `M_mon` selected once from the current neutral statistical substrate's protected `OuterRole.OUTER_MONITOR` population.

```text
NeutralStatisticalBase
  +-- DEVELOPMENT -> target-size U_size -> pi_train -> T_N / T_selected
  +-- OUTER_MONITOR -> deterministic common target checkpoint monitor M_mon
```

Requested and normally realized cardinality is 256. The numeric coincidence between a 256 target-size rung and a 256 monitor budget has no semantic meaning.

For every configured target prefix and every P5 fold:

```text
M_mon ∩ T_N = empty
M_mon ∩ G_k = empty
M_mon ∩ E_k = empty
```

Exact frame disjointness is necessary but not sufficient. Consume the canonical P1 split-exclusion relation authority and prove that no selected monitor frame is in a split-exclusion component that also contains any frame of `T_selected` (and, for configured-ladder qualification, any frame of every configured `T_N`). This check must use the existing relation owner for correlation units, duplicate geometry, protected events, replica lineage, and structural-realization lineage; P5 must not invent a second relation taxonomy.

If the current neutral outer partition permits a monitor/training split that violates this relation-level invariant, reopen the P1 partition/statistical-design owner instead of weakening the relation or silently falling back to DEVELOPMENT.

### 5.2 Preserve sampler semantics, not legacy DATA5 authority

The historical `OnlineMonitorPolicy` sampling rule is useful evidence: balanced condition/run quotas plus deterministic systematic temporal spreading with seed 161803. But the existing `build_target_online_monitor(data5_bundle, ..., label_domain_id, ...)` interface is tied to retired DATA5/label-domain authority and is not a valid current parent interface.

Implementation shall refactor/reconnect that existing sampler logic so its current parent is the accepted neutral outer partition/frame authority. Do not reactivate `label_domain_id`, pre-target-size DATA5 CV, or retired DATA5 role-budget authority. Do not create a second target sampler.

The current target-monitor record generation must bind the current neutral parent/outer-partition identity. Historical DATA5 monitor records remain readable historical evidence and cannot authorize current P5.

### 5.3 Current MLCV monitor machinery

`mlcv_monitors.py` currently owns a different per-run target-full/target-light construction. Reconcile it rather than running two target-monitor systems:

- retire fold/final-specific target checkpoint-parent construction;
- preserve TRUE_DFT replay full/light monitoring;
- preserve selection-inert training-diagnostic monitoring;
- make every run reference the same common target full membership;
- any lightweight target monitor used for stopping must be a deterministic subset of the common target monitor, never a new fold/final parent. With the current 256 light budget and a 256 common target monitor, it may equal the full common membership;
- remove duplicated target-side quota/systematic sampling code once responsibility has returned to the one current common sampler, unless a still-distinct training-diagnostic use justifies a shared primitive.

## 6. CV and final-production topology

### 6.1 Current fold generation

Current `PostSelectionCvFold` structurally requires a selected-only checkpoint monitor and treats training + monitor + outer evaluation + purge as a partition of `T_selected`. That schema must advance.

The current-generation fold shall account only for:

```text
T_selected -> gradient training + held-out outer evaluation + accepted purge/exclusion
```

The common target monitor is external to `T_selected` and is referenced by the CV plan/run lineage rather than owned by each fold.

Historical fold-local schemas may remain readable for provenance, but they cannot authorize restored current runs. No compatibility migration may reinterpret an old selected-only checkpoint membership as the new common monitor.

### 6.2 Default folds

Change the one authoritative current P5 default from 5 to 3. Preserve:

- `K >= 2`;
- explicit configured override;
- all-required-fold/all-required-seed acceptance;
- current optimizer-seed policy unless separately revised.

Do not resurrect retired `role_budget.py` / DATA5 `cross_validation_folds` or `checkpoint_monitor_minimum_units_per_fold` as current P5 authority merely because those historical defaults contain the number three.

### 6.3 Final production

Fresh final production must consume the same shared P5 loss, replay-exposure semantics, common target monitor/checkpoint policy, and replay-retention method validated by CV. Only production horizon/seeds/publication policy remain role-specific.

## 7. Identity and currentness requirements

The implementation must preserve the DAG:

```text
accepted D1/D2 P5 method
 -> shared P5 method identity
 -> CV/final role policy
 -> current selected/replay/common-monitor lineage
 -> run plan
 -> DATA8 materialization
 -> TRAIN2 runtime/checkpoint evidence
 -> EVAL2 / checkpoint-selection evidence
```

### 7.1 Shared method identity

Bind at least:

- method recipe generation;
- training mode;
- foundation/head identity;
- UniversalLoss numerical identity including delta and global coefficients;
- local-property-mask policy;
- P5 sample-exposure semantics;
- replay label/source/split policy;
- optimizer/LR/EMA/precision/backend semantics;
- shared checkpoint/admissibility policy including the common-monitor construction policy.

Do **not** bind exact realized monitor membership into a pre-work method identity. Exact monitor parent/membership/digest belongs to plan/evidence lineage.

Do not reuse the whole `TargetSizeCommonTrainingPolicy.content_digest` as P5 shared method identity after P3/P5 semantics diverge. Reuse its real component owners where applicable (for example objective coefficients or accepted atomic-reference policy) and project only components actually consumed by P5. Do not create a second general registry.

### 7.2 P5 fitted preparation

Current P5 preparation fits `ConfigurationWeightPolicy` and records a fitted-weight digest. Reconcile it so restored P5 does not fit or currentness-bind a non-executable configuration-weight method. If ExtXYZ transport requires `config_weight`, emit/validate a neutral value (`1.0`) without giving it scientific identity.

Binary local property masks remain material and must still be authenticated.

### 7.3 CV policy/plan

CV policy binds fold count, partition seed, construction algorithm, purge semantics, CV horizon, required seeds, acceptance rule, and any CV-only policy. It no longer contains `checkpoint_monitor_components_per_fold`.

Advance current CV policy/fold/plan schema or generation so historical fold-local plans cannot be accepted as current common-monitor plans.

### 7.4 Runtime cutover

Advance the existing P5 method/currentness/run identity as needed. Old weighted-stress/fold-local-monitor artifacts are stale not only as final verdicts but as executable continuation:

- old TRAIN2 checkpoints/workspaces cannot resume as restored UniversalLoss runs;
- old DATA8 P5 materializations cannot be reused as current;
- old MLCV target-monitor catalogs cannot authorize current runs;
- old CV verdicts cannot authorize restored final production.

Unaffected P1/P2/P3 evidence, frozen target memberships, and other independent prepared evidence remain reusable.

## 8. Scope and non-goals

### Included current surfaces

At minimum census/reconcile:

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
mdstats/training_data/mace_compatibility.py
mdstats/training_data/critical_precision_cli.py
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
current affected tests / generated config / qualification owners
```

Reference-census at least:

```text
UniversalLoss
WeightedEnergyForcesStressLoss
MACE_EXECUTABLE_LOSS_FAMILY
huber_delta
config_weight / ConfigurationWeightPolicy
config_energy_weight / config_forces_weight / config_stress_weight
target_head_weight / replay_head_weight / target_weight / head_weight
target_score_weight / replay_score_weight
checkpoint_monitor_components_per_fold
OnlineMonitorPolicy / build_target_online_monitor
MlcvMonitorPolicy / MlcvRunMonitorRecord
online_monitor_policy_digest / target_online_monitor_record_digest
fold_count / cross_validation_folds
checkpoint_monitor_minimum_units_per_fold
DATA5 / label_domain_id uses on current P5 paths
```

### Explicitly excluded unless reopened by evidence

- target-size P2/P3 membership/order/reducer changes;
- changing P3 loss family merely to match P5;
- changing replay geometry split;
- changing TRUE_DFT default to pseudo labels;
- relaxing target/replay acceptance gates;
- restoring historical optimizer-seed multiplicity solely for resemblance;
- replacing native MACE with a custom trainer/loss/sampler;
- production-scale GPU qualification before final release.

## 9. Historical Applicability Set

PEM is materially applicable because this cycle restores/replaces mature training machinery.

```yaml
pem_basis:
  accepted_project_state: 1b6b6f83918d31c4b27a0e60d7bc047ef58b6067
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-001
    disposition: APPLICABLE
    reason: Actual MACE realization can drift from recorded method identity when model-affecting semantics are duplicated or overridden.
  - id: FF-002
    disposition: APPLICABLE
    reason: The method-generation cutover must prevent old stress/fold-local TRAIN2 continuation state from becoming current UniversalLoss authority.
  - id: SP-001
    disposition: APPLICABLE
    reason: Remove duplicated/incorrect loss and target-monitor machinery and return responsibility to real owners.
  - id: SP-002
    disposition: APPLICABLE
    reason: Retired fields, historical schemas, and stale run evidence must fail closed at current identity boundaries.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve independent immutable P1/P2/P3/selected evidence rather than recomputing it.
  - id: SP-004
    disposition: APPLICABLE
    reason: Real pinned-MACE and real current monitor/currentness paths are required; helper/mock-only proof is insufficient.
```

The accepted PEM is partial. Refresh the HAS if accepted memory or governing authority materially advances before closeout.

## 10. Capability-transfer map

```text
forced UniversalLoss -> stress rewrite
  -> remove only the P5 loss mutation
  -> retain pinned-source qualification and unrelated execution repairs

P5 configuration-weight fitting
  -> retain general owner for methods that use it
  -> project it out of restored UniversalLoss P5
  -> neutral config_weight only if transport requires it

fold-local selected-only checkpoint monitor
  -> retire from current P5 fold policy/schema
  -> common external protected target monitor

legacy DATA5 common-monitor parent interface
  -> preserve deterministic balanced sampler semantics
  -> current neutral OuterRole.OUTER_MONITOR parent and lineage

current MLCV fold/final target sampler
  -> retire competing target checkpoint-parent construction
  -> preserve replay monitor and training diagnostic capabilities

head-scalar replay materialization
  -> retire from current configuration/plan/cache/evidence
  -> historical read compatibility only as required

current authenticated run/currentness/restart machinery
  -> preserve
  -> advance generation so old stress/fold-local state cannot resume as current
```

## 11. Gates

### G0 — Mandatory D1 then D2 adjudication

**Goal:** repair the earliest affected authority before D3/D4 implementation.

**Work:**

1. Amend D1 P5 training/objective language so the accepted foundation-adaptation method is compatible with UniversalLoss, not a universal weighted-stress requirement.
2. Amend D1 P5 weighting semantics: general nontrivial per-configuration weighting is not an active UniversalLoss P5 layer. Preserve it only for separately owned methods. Keep local property weights as binary availability masks.
3. Amend D1 fold semantics so checkpoint selection may use one protected campaign-common monitor outside `T_selected`; state that this monitor is shared across folds/runs and therefore model-control decisions are correlated.
4. Preserve held-out evaluation exclusion and all other unaffected scientific-role semantics.
5. Amend D2 to define the exact UniversalLoss numerical functional and pinned-MACE exposure semantics described in Sections 4 and 4.1.
6. Keep P3 target-size objective/exposure separately owned.
7. Confirm existing score-weight/replay-degradation semantics remain separate from retired training-head weighting.
8. Independently falsify the D1/D2 amendment and obtain required human acceptance before dependent current-authority promotion.

**Acceptance:**

- D1 no longer requires weighted-stress or fold-training-derived checkpoint monitoring for restored P5.
- D1 and D2 are jointly coherent and realizable without hidden/inert weighting fields.
- D2 is reconstructible without reverse-engineering MACE source.
- P3 remains unchanged unless separately and explicitly reopened.
- Any requirement for nontrivial P5 configuration weighting blocks UniversalLoss rather than spawning an emulation workaround.

### G1 — Complete authority/API/evidence census

Classify every affected reference as current authority, current implementation/API, current guide/config, compatibility reader, historical evidence, or unrelated concept. Include public `mdstats.__init__` exports and legacy DATA5/role-budget symbols so the change cannot silently reactivate retired authority or break a public API accidentally.

**Acceptance:** one current owner for every changed semantic; compatibility disposition is explicit; historical release/workplan text remains historical.

### G2 — Restore native UniversalLoss realization

- Remove only the P5 UniversalLoss->stress source mutation.
- Keep source qualification, restart/CUDA/precision/runtime repairs, and P3 complete-batch patch where applicable.
- Replay-enabled multi-head P5 allows native MACE to choose UniversalLoss and verifies the resolved class/parameters.
- Accepted non-multihead foundation fine-tuning requests `loss="universal"` explicitly when native routing would not.
- Bind `huber_delta=0.01`, E/F/S 1/10/1, and exact numerical semantics into identity/evidence.
- If SWA or another phase can change loss coefficients/family, either prove it disabled or bind/qualify its trajectory-changing semantics too.

**Acceptance:** real pinned parser + `get_loss_fn()` + training path execute the accepted P5 loss; no custom loss exists.

### G3 — Remove inert P5 configuration weighting and retire head scalars

- Stop fitting `ConfigurationWeightPolicy` in restored P5 preparation.
- Remove it from P5 current method/currentness identity when it is not consumed.
- Preserve general configuration-weight owners for P3/other methods.
- Emit/validate neutral `config_weight=1.0` only if fixed-file transport requires the key.
- Keep binary property masks and bind them.
- Remove live `target_head_weight`, `replay_head_weight`, and equivalent `target_weight`/`head_weight` P5 semantics from current configuration, replay preparation, cache identity, materialization, and runtime evidence.
- Current config specifying retired head-scalar fields fails closed with a removal/migration error.
- Historical payloads may remain parseable but cannot authorize current P5.

**Acceptance:** changing an inert configuration-weight/head-scalar value cannot alter or retire current P5 evidence because no such current method field exists; separately owned weighting remains intact.

### G4 — Move the common target sampler onto current neutral authority

- Reuse/refactor the existing balanced condition/run/time systematic target-sampling implementation.
- Parent it from current `NeutralStatisticalBase` / `NeutralOuterPartition` `OuterRole.OUTER_MONITOR` plus canonical frame authority.
- Remove current P5 dependence on `data5_bundle.outer_partition_for_domain(label_domain_id)` and legacy `parent_role=data5_outer_monitor` identity.
- Advance target-monitor record/policy generation where needed so current records bind neutral parent lineage.
- Preserve historical DATA5 records through explicit read compatibility only.
- Review `mdstats.__init__` public exports; do not silently break or repurpose legacy API semantics.

**Acceptance:** one current target sampler, no current label-domain/DATA5 monitor parent, deterministic 256 membership under the accepted neutral parent.

### G5 — Collapse MLCV target-monitor topology onto the common monitor

- Advance CV policy/fold/plan and MLCV target-monitor record/catalog generations.
- Remove `checkpoint_monitor_components_per_fold` and selected-only checkpoint-monitor fields from current fold semantics.
- Retire fold/final target-full parent construction in `mlcv_monitors.py`.
- Preserve replay full/light monitoring and training diagnostics.
- Each CV/final run references the same common target full monitor; target-light is a deterministic subset only.
- Reconcile DATA8 `target_checkpoint_monitor` / `target_checkpoint_full` materialization so they no longer encode fold-local/final-specific target parents.

**Acceptance:** no current P5 path can construct or authorize a fold-local/final-specific target checkpoint parent; historical monitor catalogs cannot be reinterpreted as current.

### G6 — Qualify actual protected monitor parent and statistical separation

Produce actual LTA evidence containing at least:

```text
neutral statistical-base / outer-partition digests
accepted NeutralLeakageReport disposition
P1 split-exclusion evidence digest
OUTER_MONITOR parent unit/frame counts
independence grades / effective sample evidence already owned upstream
condition and run IDs represented
available -> selected counts per condition/run
source-time span/systematic positions
canonical label/property completeness for every selected monitor frame
requested/realized count
monitor membership digest
exact frame overlap with every T_N and T_selected
split-exclusion-component overlap with every T_N and T_selected
```

Do not invent a new generic minimum-run/minimum-unit constant merely to pass. Do not treat the existing neutral leakage report as sufficient for cross-role replica/duplicate/structural-lineage separation if it does not test those relations; consume the canonical P1 split-exclusion authority for that claim.

**Acceptance:** realized size 256 when parent support permits; no exact or protected-relation leakage into the configured target ladder; monitor labels are usable for the accepted checkpoint metrics; diversity is adequate under actual evidence. Failure reopens the upstream partition/statistical-design owner rather than falling back to DEVELOPMENT.

### G7 — Restore the current CV default to three

- Change one authoritative P5 default 5 -> 3.
- Reconcile config/spec/guide/tests.
- Preserve `K>=2`, explicit override, all-required-fold/seed semantics, and current seed population.
- Prove no legacy DATA5 `cross_validation_folds=3` owner has been reactivated.

### G8 — Preserve adaptive-stop/checkpoint-score semantics

Explicitly preserve current `target_score_weight`, `replay_score_weight`, matched foundation replay baselines, signed replay degradation, and the default 30 meV/A replay-degradation budget unless separately changed by accepted authority. Retirement of training-head weights must not mutate these score/retention semantics.

### G9 — Method identity, runtime evidence, and restart/currentness cutover

Runtime evidence records at least:

```text
training role / mode
foundation/head identity
loss family/class and exact UniversalLoss parameters
binary property-mask policy
E/F/S coefficients
target and replay membership digests/counts
combined dataset count and head counts
shuffle/sampler seed and policy
batch size / drop_last / batches per epoch
LR / EMA / precision / backend
real_pt_data_ratio_threshold and realized duplication factor
common target-monitor parent/policy/membership digest
replay monitor lineage
fold train/eval/purge membership
method / CV / run-plan digests
```

Advance existing recipe/run/evidence schemas as needed. Old stress/fold-local TRAIN2 checkpoints, DATA8 materializations, MLCV catalogs, and CV verdicts must fail currentness before execution/restart reuse. Preserve independent P1/P2/P3/T_selected evidence.

### G10 — Counterfactual falsification matrix

At minimum falsify:

1. config/identity says UniversalLoss but runtime resolves stress;
2. runtime class is UniversalLoss but delta/EFS/conditional-force semantics differ;
3. D2 omits config-weight non-consumption or property-mask nonlinear placement;
4. P5 still fits/binds nontrivial `ConfigurationWeightPolicy`;
5. non-neutral `config_weight` changes P5 trajectory/identity;
6. current config accepts retired target/replay head scalars;
7. replay cache/materialization still applies head-scalar weighting;
8. target monitor still consumes legacy DATA5/label-domain authority;
9. current MLCV still builds fold/final target checkpoint parents;
10. common monitor is copied into each fold as selected membership rather than external lineage;
11. monitor overlaps or is split-exclusion-related to any configured `T_N`;
12. monitor parent cannot realize adequate 256 evidence but execution silently continues;
13. monitor contains unusable/incompatible labels for checkpoint metrics;
14. score/replay-retention weights are accidentally deleted with training-head weights;
15. default K falls back to five through another resolver;
16. legacy DATA5 K=3/role-budget semantics become current accidentally;
17. TRUE_DFT versus pseudo labels change replay geometry split;
18. MACE target duplication occurs;
19. P5 combined-loader sampler/drop_last differs from accepted exposure identity;
20. P3 complete-batch semantics are accidentally changed by the P5 restoration;
21. LR/EMA/precision/backend are overwritten without identity/evidence change;
22. old stress/fold-local checkpoint resumes as current UniversalLoss run;
23. stale weighted-stress CV authorizes restored final production;
24. exact common monitor differs across CV folds/seeds/selected sizes/final runs;
25. an execution-only field incorrectly invalidates scientific method identity;
26. a true method field fails to invalidate dependent evidence.

Every case is rejected by a real owner or documented as inapplicable with evidence.

### G11 — Real-owner assembled qualification

Exercise the real path:

```text
campaign config
 -> D1/D2-conforming P5 resolver
 -> current neutral common-monitor construction
 -> target/replay materialization
 -> current method/CV/run identity
 -> parser-facing MACE config
 -> source-qualified mdstats MACE seam
 -> pinned mace-torch 0.3.16 UniversalLoss
 -> native combined loader
 -> optimizer update
 -> TRAIN2 persistence/restart evidence
 -> adaptive stop / checkpoint candidate evidence
 -> full checkpoint selection
 -> EVAL2 held-out evaluation
 -> fresh final-production representative path
```

Mocks are permitted only below/outside the owner being proved.

### G12 — Bounded scientific pilot then full CV

Before a full campaign, record a true pre-update foundation baseline and the first several restored checkpoints on representative real LTA data. Record target monitor RMSE, TRUE_DFT replay RMSE/degradation, resolved loss/exposure identity, corpus counts, and common monitor identity.

Do not relax gates. Immediate replay degradation of the previous hundreds-of-meV/A scale falsifies the restored method and reopens D1/D2 rather than triggering another D4 patch.

After pilot PASS, run the required three-fold affected qualification and independent Protocol 6.3 Review. Production-scale GPU qualification remains deferred to final release.

## 12. Second independent review findings incorporated

This revision closes additional gaps found by independently reconstructing accepted D1, current P5/MLCV code, the neutral substrate, and pinned MACE 0.3.16:

1. **D1, not D2, is the earliest contradictory owner.** D1 explicitly requires weighted-stress execution and training-eligible fold monitors. G0 is now mandatory D1 -> D2 reconciliation.
2. **UniversalLoss makes current P5 configuration weighting inert.** It does not consume `ref.weight`; P5 must project nontrivial `ConfigurationWeightPolicy` out rather than carry a no-op identity field.
3. **UniversalLoss numerical identity was under-specified.** D2 must bind per-atom energy Huber, conditional-force Huber regimes/factors, stress Huber, binary masks, reductions, globals, and delta—not just a class name.
4. **The historical target sampler has a legacy parent interface.** Its DATA5/label-domain signature cannot become current authority; only its deterministic sampling capability is transferred to the neutral substrate.
5. **Current MLCV has a competing target-monitor owner.** Its fold/final target full/light construction must be collapsed onto the common monitor while replay monitoring and training diagnostics survive.
6. **The common monitor must govern final production too.** Otherwise CV validates a different checkpoint-selection method from production.
7. **Current CV schemas encode the old topology.** Fold/CV/MLCV generations must advance; old selected-only monitor records remain historical.
8. **Exact disjointness is insufficient.** The P1 split-exclusion authority must also show no monitor/training relation through correlation, duplicates, protected events, replica lineage, or structural realization.
9. **Existing neutral leakage evidence is useful but not a substitute for the full P1 relation check.** Reuse both owners for the claims they actually establish.
10. **Monitor label adequacy must be proven.** Protected membership alone does not guarantee every selected frame supports the accepted checkpoint metrics.
11. **Adaptive score weights are a separate owner.** `target_score_weight` / `replay_score_weight` and the 30 meV/A degradation budget remain current and must not be confused with retired training-head scalars.
12. **Native P5 loader semantics are part of exposure.** Combined `ConcatDataset`, shuffle, seed, no balancing/duplication, and native non-LBFGS `drop_last=true` must be represented; P3's `drop_last=false` rule remains separate.
13. **Old executable continuation must be cut off, not only old verdicts.** Restart/currentness must reject stress/fold-local TRAIN2 and DATA8 state under the restored generation.
14. **P3/P5 policy identity was over-coupled.** Reuse component owners, not an entire P3 common-policy digest containing P5-inert configuration weighting.
15. **Public API compatibility is part of the affected surface.** Legacy exported monitor builders cannot be silently repurposed without an explicit compatibility disposition.

## 13. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- UniversalLoss cannot express the scientifically required P5 objective;
- nontrivial per-configuration weighting is required in P5;
- the accepted native combined-loader exposure is scientifically unacceptable;
- the protected neutral `OUTER_MONITOR` parent cannot provide adequate/independent checkpoint evidence;
- monitor and target populations cannot satisfy canonical P1 split-exclusion constraints;
- P3/P5 cannot legitimately use different loss/exposure methods for the intended conclusions;
- TRUE_DFT replay still causes material forgetting after correct restoration;
- current target/replay acceptance gates are scientifically incompatible with the restored method.

Reopen D3 when one accepted method still needs competing owners or a new durable architecture boundary. Local implementation defects under coherent D1-D3 remain D4 repairs.

## 14. Closeout

The workplan closes only after:

1. D1 and D2 amendments are independently reviewed and accepted through their normal authority process;
2. D3 has one coherent loss/exposure/monitor/currentness flow;
3. D4 specs/code/config/public API/tests realize that flow with no inert current fields;
4. affected old evidence is stale only where materially dependent, while independent P1/P2/P3/selection evidence remains usable;
5. semantic history explains the replaced weighted-stress/fold-local/head-scalar lineage;
6. closeout learning/PEM is reconciled only where admission criteria are met;
7. the active plan is archived only after all still-current semantics reside in accepted authority.

Central closure invariant:

```text
accepted P5 scientific method
 = accepted P5 numerical method
 = recorded shared method identity
 = authenticated target/replay/common-monitor lineage
 = actual pinned-MACE loss and loader realization
 = TRAIN2/restart evidence
 = checkpoint/EVAL2 interpretation
```

No current setting may change recorded method identity without changing governed execution, change governed execution without changing recorded identity, or remain current while having no executable/scientific effect.