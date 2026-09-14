# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — G0 D1/D2 closed PASS and stakeholder-ratified on 2026-09-14; pre-implementation D3/D4 reconciliation required before executable changes  
**Current authority:** accepted branch D1/D2 in `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md`; repository-integrated D3/D4 remain the baseline to be reconciled against them  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Review state:** D1/D2 independent re-review PASS at `f310b4c15c6b0465b34013d329847abdb208bae2`; stakeholder ratification received; this revision closes D3/D4 workplan gaps before implementation

## 1. Disposition

The upstream Serious Challenge is **resolved for this restoration branch**. The repaired D1/D2 pair passed independent falsification and the stakeholder explicitly authorized progression into D3/D4 closure. The 2026-09-13 D1/D2 papers remain the repository-integrated baseline until this branch is integrated, but downstream branch design and implementation must now conform to the accepted restoration authority rather than the superseded P5 method.

The remaining problem is a bounded **D3/D4 conformance restoration**, not a new scientific redesign. Current integrated architecture/code still contains several descendants of the superseded method: weighted-stress foundation P5 realization, selected-only fold checkpoint monitors, M3 final checkpoint routing, inert/retired weighting layers, generic from-scratch E0 routing for foundation adaptation, and currentness identities that do not yet bind all newly accepted numerical semantics.

The review of the repaired D1/D2 pair also exposed four downstream requirements that the earlier workplan did not fully encode:

1. foundation-residual E0 conformance must validate **composition-level transfer identifiability**, not merely fit rank or elemental-column presence;
2. current two-head stochastic exposure binds the pre-shuffle corpus layout `replay/pt_head || target` under the accepted seed;
3. the common target monitor is **exactly 256 configurations or P5 is infeasible**—there is no shrink-to-fit success state; and
4. the single numeric `huber_delta=0.01` has property-specific dimensional meanings that runtime evidence/specification must preserve without inventing three independent knobs.

The plan remains deliberately reductive. Remove wrong/retired semantics, reconnect existing owners, and reuse qualified native MACE behavior. Do not create a custom loss, second sampler, second E0 solver, shadow trainer, parallel identity registry, or compensating wrapper where owner rewiring/removal suffices.

## 2. Frozen cycle decisions

For **foundation-model P5 adaptation** (`naive_fine_tuning` and `multihead_replay`), the accepted branch end state is:

```text
loss family                     native MACE UniversalLoss
huber_delta numeric value       0.01, explicitly bound
energy Huber threshold          0.01 eV/atom
force base Huber threshold      0.01 eV/Angstrom
stress Huber threshold          0.01 eV/Angstrom^3
global E:F:S coefficients       1:10:1
general config_weight in P5     neutral transport only; not a P5 loss layer
target:replay training scalar   none
atomic-reference mode           foundation_residual
E0 transfer rule                composition-level null-space identifiability
replay-label default            TRUE_DFT
pre-shuffle two-head layout     replay/pt_head || target
implicit target duplication     forbidden
force_mh_ft_lr                  true for multihead replay
checkpoint target monitor       one protected campaign-common exact 256-frame monitor
monitor shortfall               P5 infeasible; no shrink/fallback
CV fold default                 3
held-out CV evidence            unavailable to fitting/checkpoint choice
replay degradation criterion    unchanged
production-scale GPU qualification deferred to final release
```

This workplan does **not** change:

- P3 target-size screening loss/exposure semantics;
- P5 scratch-training loss semantics;
- target-size membership/order/reducer semantics;
- replay geometry split;
- TRUE_DFT default;
- target/replay acceptance thresholds;
- current optimizer-seed population;
- final-release GPU qualification policy.

A successful assembled restoration establishes that the **assembled restored method** works. Because loss, target-monitor topology, retired head scaling, default CV geometry, E0 conformance, and stochastic exposure identity are corrected together, it does not by itself prove which individual change caused replay-retention recovery.

## 3. Governing invariants

### 3.1 Evidence roles

- P1/P2/P3 and frozen `T_N` / `T_selected` remain upstream and are preserved unless a direct dependency is demonstrated.
- Checkpoint-monitor evidence is development/model-control evidence. It supplies no gradients and is neither held-out CV evidence nor target-size authority.
- Held-out CV evidence cannot affect target membership, fitted preprocessing/E0, stopping, checkpoint choice, or monitor construction.
- Composition **counts/geometry** of monitor and held-out configurations may be inspected only to test E0 transfer feasibility; their labels remain unavailable to the fit.
- Final production starts a fresh lineage and must use the same shared foundation-adaptation/checkpoint method validated by CV.
- One common target monitor is reused across every selected size, CV fold, CV seed, and final-production seed/run. Fold-specific, final-specific, or M3-specific target checkpoint parents define a different method.
- Sharing one monitor across folds correlates checkpoint/model-control decisions; held-out fold evaluations remain the CV acceptance evidence.

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

For restored UniversalLoss P5, item 2 is **not an active P5 loss layer** because pinned MACE UniversalLoss does not consume `ref.weight`. P5 must not fit or identity-bind a nontrivial `ConfigurationWeightPolicy` that has no executable effect. If future D1/D2 authority requires nontrivial per-configuration weighting for foundation-adaptation P5, UniversalLoss becomes inadmissible and D1/D2 reopens; do not emulate weighting through a custom loss, residual scaling, property-mask abuse, or sample duplication.

## 4. Accepted D2 foundation-adaptation method

### 4.1 UniversalLoss numerical identity

For pinned `mace-torch==0.3.16` `UniversalLoss` with numeric `huber_delta=0.01`:

- energy uses Huber loss on per-atom energy residuals with threshold `0.01 eV/atom`;
- stress uses Huber loss on Cartesian stress residuals with threshold `0.01 eV/Angstrom^3`;
- forces use MACE `conditional_huber_forces` with base threshold `0.01 eV/Angstrom`;
- force Huber delta is multiplied by `[1.0, 0.7, 0.4, 0.1]` for reference-force-norm regimes `<100`, `[100,200)`, `[200,300)`, and `>=300 eV/Angstrom`;
- global E/F/S coefficients multiply the three reduced property terms outside those nonlinear property reductions;
- local `config_energy_weight`, `config_forces_weight`, and `config_stress_weight` enter the nonlinear residual transformation and, for current P5, are binary availability masks only;
- `config_weight` / `ref.weight` is not consumed by UniversalLoss; and
- reduction/distributed behavior must preserve the accepted native numerical semantics or reopen D2.

Current foundation-adaptation values are:

```text
loss_family   = universal
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

The three dimensional thresholds are interpretations of one accepted numeric MACE parameter, not three new user-configurable knobs. A unit conversion that changes numerical residual values must convert the corresponding threshold consistently or is a different D2 method.

A future dependency may replace MACE 0.3.16 only after demonstrating the same accepted numerical semantics or after explicit D2 revision. Source markers/class names remain D3/D4 conformance evidence, not timeless D2 axioms.

### 4.2 Native sample exposure

Restored two-head P5 uses the qualified pinned-MACE combined-loader semantics:

```text
replay / pt_head dataset || target dataset -> ConcatDataset
shuffle                                  -> enabled under accepted seed
target/replay head balancing             -> none
intentional duplication                  -> none
ratio-driven target duplication          -> disabled by real_pt_data_ratio_threshold=0.0
force_mh_ft_lr                           -> true
non-LBFGS combined drop_last             -> native true
```

The pre-shuffle index layout is method-bearing for deterministic fixed-seed execution. Swapping the replay and target blocks while keeping membership and seed fixed changes the mapping from shuffled indices to examples, minibatch composition, and potentially the optimizer trajectory. Do not add a target-first reorder wrapper; preserve the native `pt_head`-first realization or explicitly reopen D2.

Authenticated membership and realized per-epoch exposure remain distinct claims: with `drop_last=true`, one final partial combined batch can be omitted after shuffle. Evidence must bind target/replay counts, combined count, ordered pre-shuffle head/corpus layout, seed/shuffle/sampler policy, batch size, `drop_last`, and batches/epoch. Do not claim every P5 frame is necessarily exposed exactly once per epoch.

This is separate from P3 target-size screening, whose optimizer normalization requires complete target batches and `drop_last=false`.

### 4.3 Foundation-residual atomic references and transfer feasibility

Foundation adaptation retains one existing atomic-reference fit owner. Do **not** create a second solver.

- target-head E0s are fitted as elemental corrections to the exact selected/head-qualified foundation prediction baseline;
- CV fits use only that fold's gradient-training membership;
- the common target checkpoint monitor and held-out fold **labels** do not enter the E0 fit;
- final production fits on complete exact `T_selected` only;
- the fit binds exact foundation checkpoint and selected foundation head;
- target-head corrected E0s and replay/pretraining-head foundation E0s remain distinct head-local mappings where required.

The fitted P5 preparation must additionally validate composition transfer. Let `C` be the authorized fit count matrix and `N_free` the unanchored null space after accepted anchors. For every governed target composition vector `c` whose energy is consumed by training, checkpoint monitoring, or held-out evaluation, require

```text
c^T v = 0  for every v in N_free
```

at the accepted numerical-rank tolerance. With no accepted anchor this is equivalent to `c` lying in the row space of `C`. Individual elemental coefficients may be nonunique when the consumed composition-weighted correction remains unique. A missing element is one sufficient failure case, not the complete test.

Monitor/held-out geometry or composition counts may be inspected for this transfer test; their target energy labels may not be borrowed to repair the fit. Minimum-norm output, an arbitrary zero coefficient, another fold's solution, or a different foundation head does not create identifiability.

The transfer result belongs to fitted P5 preparation/run lineage as a consumer of the existing atomic-reference fit record; it is not a new E0 authority. Persist/bind the required composition set or canonical composition-class digest, numerical-rank tolerance, rank/singular/null-space evidence sufficient to reconstruct the decision, accepted anchor/prior identity if any, and per-required-composition or canonical aggregate pass/fail evidence.

Scratch mode retains from-scratch total-energy E0 fitting under its separately accepted method.

Pinned MACE multihead code can derive `pt_head` foundation E0s internally and, for some multi-head foundation tensor shapes, falls back to the first head. That behavior must be source-qualified against mdstats' selected foundation-head identity. If the selected foundation head is not the upstream fallback head, the existing qualified dependency seam must ensure the correct head-qualified mapping or fail closed.

## 5. Common target checkpoint monitor

### 5.1 Current topology and exact cardinality

The current target checkpoint domain is one campaign-common monitor `M_mon` selected once from the protected neutral `OuterRole.OUTER_MONITOR` population:

```text
NeutralStatisticalBase
  +-- DEVELOPMENT   -> U_size -> pi_train -> T_N / T_selected
  +-- OUTER_MONITOR -> deterministic common target checkpoint monitor M_mon
```

Current P5 requires **exactly 256 usable configurations**. The number has no relationship to a target-size rung beyond numeric coincidence.

For every configured target prefix and P5 run:

```text
M_mon intersect T_N                 = empty
M_mon intersect gradient_training   = empty
M_mon intersect held_out_evaluation = empty
```

No monitor frame may belong to a canonical P1 split-exclusion component containing any frame of `T_selected`; configured-ladder qualification also checks every configured `T_N`.

If the neutral partition cannot provide 256 usable, relation-clean, checkpoint-label-compatible frames with the required coverage, current P5 is **infeasible**. There is no smaller-monitor success state, `DEVELOPMENT` fallback, relation splitting, or duplication to reach 256.

### 5.2 Preserve sampler capability, not legacy DATA5 authority

Historical `OnlineMonitorPolicy` provides the useful sampling capability: balanced condition/run quotas plus deterministic systematic source-time spreading with seed 161803. The current historical implementation interface `build_target_online_monitor(data5_bundle, ..., label_domain_id, ...)`, however, is tied to retired DATA5/label-domain authority.

Transfer the sampling capability to the current neutral outer-partition/frame authority. Do not reactivate `label_domain_id`, pre-target-size DATA5 CV, or retired role-budget ownership. Advance current target-monitor records so their parent identity is the neutral outer partition/frame authority. Historical DATA5 monitor records remain historical/read-compatible only.

### 5.3 Collapse competing MLCV target-monitor machinery

Current `mlcv_monitors.py` owns a later fold/final target-full/target-light mechanism. Reconcile it rather than running two target-monitor systems:

- retire fold-specific and final-specific target checkpoint-parent construction;
- preserve TRUE_DFT replay full/light monitoring;
- preserve selection-inert training diagnostics;
- make every CV/final run reference the same common target-full membership;
- any lightweight target monitor used for stopping is only a deterministic subset of the common target monitor, never a new parent; and
- remove duplicated target-side sampling responsibility once the common sampler owns it.

### 5.4 Retire M3 as final-production checkpoint monitor

`M3` remains unchanged P3 target-size development/model-selection evidence. P5 final production must not use M3 for checkpoint selection/stopping, and no M3 identity may be rewritten or reclassified to pretend it is `OUTER_MONITOR` evidence. Final production uses the same `M_mon` target checkpoint evidence as CV.

## 6. CV/final topology and schema cutover

### 6.1 CV fold structure

Current `PostSelectionCvFold` structurally owns a selected-only checkpoint monitor and partitions `T_selected` into train + monitor + outer evaluation + purge. The current-generation schema must advance.

Restored fold accounting is:

```text
T_selected -> gradient training + held-out outer evaluation + accepted purge/exclusion
```

`M_mon` is external to `T_selected` and is referenced by the plan/run lineage, not owned as fold membership. The existing outer-fold and purge algorithms/memberships remain unchanged; removal of the selected-only monitor reservation returns all non-outer/non-purge selected components to gradient training.

Historical selected-only fold-monitor schemas remain readable provenance but cannot authorize current restored runs. No migration may reinterpret an old fold-local membership as the new common monitor.

### 6.2 Default folds

Change the one authoritative current P5 default from 5 to 3 while preserving:

- `K >= 2`;
- explicit override;
- all-required-fold/all-required-seed acceptance; and
- current optimizer-seed policy.

Do not revive retired DATA5 `cross_validation_folds` or `checkpoint_monitor_minimum_units_per_fold` merely because historical defaults contain three.

### 6.3 Final production

Fresh final production consumes the same foundation-adaptation loss/exposure method, common target monitor/checkpoint policy, replay-retention policy, selected-head foundation-residual E0 rule plus composition-transfer validation, and currentness semantics that CV validated. Only production horizon/seeds/publication policy remain role-specific.

## 7. D3 ownership, identity, fitted preparation, and currentness

### 7.1 Identity DAG

```text
accepted branch D1/D2 P5 method
 -> existing shared PostSelectionMethodIdentity owner
 -> CV/final role policy
 -> selected/replay/common-monitor/fitted-P5 lineage
 -> run plan
 -> DATA8 materialization
 -> MACE adapter / TRAIN2 runtime evidence
 -> checkpoint selection / EVAL2 interpretation
```

### 7.2 Cycle-scoped D3 ownership decisions

No parallel architecture is introduced. Reconcile the current owners as follows:

- **Shared method identity:** keep the existing `PostSelectionMethodIdentity` family as the only post-selection method owner. Advance its recipe/dependent policy generations as needed; do not add a second P5 identity registry.
- **MACE dependency seam:** keep the current MACE compatibility/adapter seam as the only dependency-facing owner for source qualification, parser arguments, loss/loader realization, precision/backend binding, and executable evidence.
- **Common target monitor:** move current target monitor membership ownership to one neutral-`OUTER_MONITOR` constructor over current neutral/frame authority. `mlcv_monitors.py` becomes a consumer of that target membership while retaining replay monitoring/training-diagnostic responsibilities; it no longer samples independent target parents.
- **CV plan:** keep `PostSelectionCvPlan` as the CV plan owner, but current fold membership contains only train/eval/purge. The common monitor is an external plan/run lineage reference, not a fold role.
- **Atomic references:** keep the existing atomic-reference fitter as the sole E0 solver. P5 fitted preparation owns role-specific composition-transfer validation using the fit record plus required geometry/composition classes.
- **Final production:** keep the existing P5 production owner. It consumes the same shared method identity and common target monitor and fits/validates E0 on exact `T_selected`; it never substitutes M3.
- **Currentness/pointers:** keep `CampaignStore` and existing currentness machinery as locators/validators over immutable products. Advance generations and reject stale semantic state rather than migrating old meaning into new schemas.

These are cycle-scoped D3 concretizations of accepted D1/D2. Exact dataclass fields, schema names/version tokens, parser options, helper placement, and storage paths remain D4 unless required below.

### 7.3 Shared method identity requirements

Bind at least:

- method recipe generation and training mode;
- foundation checkpoint/head identity;
- UniversalLoss numerical identity for foundation-adaptation modes, including dimensional threshold interpretation;
- local-property-mask policy;
- P5 sample-exposure semantics including replay/`pt_head`-first then target-second pre-shuffle layout, `force_mh_ft_lr`, no duplication, shuffle/sampler, and combined `drop_last`;
- atomic-reference fit mode, selected foundation-head qualification, and the policy/tolerance governing composition-transfer validation;
- replay label/source/split policy;
- optimizer/LR/EMA/precision/backend semantics; and
- shared checkpoint/admissibility policy and common-monitor construction policy.

Do not bind exact realized monitor membership, fold membership, fit result, or composition-transfer result into the pre-work shared method identity. Those belong to plan/fitted-preparation/evidence lineage.

Do not reuse the entire `TargetSizeCommonTrainingPolicy.content_digest` as P5 method identity after P3/P5 divergence. Reuse real component owners only where their semantics are genuinely shared.

### 7.4 Fitted P5 preparation

Remove the non-executable `ConfigurationWeightPolicy` layer from restored UniversalLoss P5. If ExtXYZ transport requires `config_weight`, emit/validate neutral `1.0` without scientific identity. Binary local property masks remain authenticated.

Foundation-adaptation preparation resolves `FOUNDATION_RESIDUAL` from training mode, not from the generic `AtomicReferenceFitPolicy` default. An explicit incompatible fit mode fails closed. Scratch resolves its separately accepted from-scratch fit.

CV fitted preparation binds fold gradient membership, exact selected-head foundation predictions/E0 mapping, resulting corrected target-head E0 digest, required target composition classes from gradient/common-monitor/held-out geometry, and composition-transfer feasibility evidence. Final fitted preparation binds exact `T_selected`, common-monitor required composition classes, and the corresponding transfer result.

### 7.5 Currentness cutover

Advance existing P5 method/run/materialization/evidence generations as required. Old artifacts become stale when they can differ in any accepted method-bearing dimension, including:

- weighted-stress rather than UniversalLoss foundation P5;
- fold-local/final-local/M3 target monitor topology;
- live head-scalar/config-weight P5 semantics;
- from-scratch E0 foundation preparation;
- foundation-residual records/preparations without required composition-transfer validation;
- target-first rather than replay-first two-head pre-shuffle layout;
- incompatible dimensional Huber/unit interpretation; or
- incompatible CV schema/default/currentness ancestry.

Old TRAIN2 checkpoints/workspaces cannot resume as restored foundation-adaptation runs, old DATA8 P5 materializations cannot be reused as current, old MLCV target-monitor catalogs cannot authorize current runs, and old CV verdicts cannot authorize restored final production. Preserve independent P1/P2/P3 evidence and frozen target memberships.

## 8. Scope and non-goals

### 8.1 Minimum affected-surface census

```text
docs/methods/mlff_scientific_method.md
docs/methods/mlff_numerical_algorithmic_method.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
docs/arch_manuals/mlff_training_data_architecture.md generated/aggregate view
docs/specs/training_data/** affected P5 specifications
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

Reference census includes at least:

```text
UniversalLoss / WeightedEnergyForcesStressLoss / MACE_EXECUTABLE_LOSS_FAMILY
huber_delta and canonical energy/force/stress units
config_weight / ConfigurationWeightPolicy
config_energy_weight / config_forces_weight / config_stress_weight
target_head_weight / replay_head_weight / target_weight / head_weight
target_score_weight / replay_score_weight
AtomicReferenceFitMode / foundation_residual / foundation E0/head extraction
rank / singular_values / null_space_dimension / relative_singular_value_tolerance
composition-count rows / required composition classes / transfer-feasibility evidence
force_mh_ft_lr / real_pt_data_ratio_threshold
pt_head_sorted_first / replay-first-target-second pre-shuffle layout
MACE_EXECUTION_SEMANTICS_VERSION / method recipe generation
checkpoint_monitor_components_per_fold
OnlineMonitorPolicy / build_target_online_monitor
MlcvMonitorPolicy / MlcvRunMonitorRecord
exact 256 monitor cardinality / no shrink fallback
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
- adding a user-facing corpus-order knob;
- adding three independent user-facing Huber-delta knobs;
- custom trainer/loss/sampler/E0 solver;
- semantic migration that reinterprets old fold-monitor or monitor-parent records as current; or
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
    reason: Old stress/fold-local/from-scratch-E0/target-first TRAIN2 state must not become continuation authority after the generation cutover.
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

The D1/D2 branch authority advanced during this cycle, but the accepted PEM basis did not. These HAS dispositions were rechecked against the accepted D1/D2 repairs and remain applicable. Refresh again if accepted memory or governing authority materially advances before closeout.

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
  -> preserve existing residual-fit owner
  -> route foundation modes through selected-head residual inputs
  -> add composition-transfer validation as fitted-preparation evidence, not a second solver

native combined-loader exposure
  -> preserve pt_head/replay-first then target-second ordered index layout
  -> bind through existing replay-exposure/MACE execution semantics owners
  -> no reorder wrapper or new sampler

current authenticated run/restart/currentness machinery
  -> preserve
  -> advance generations so incompatible old state cannot resume
```

## 11. Gates and implementation staging

### G0 — D1/D2 adjudication — **CLOSED / PASS**

Completed obligations:

1. D1 foundation-adaptation objective changed to robust UniversalLoss semantics for `naive_fine_tuning` / `multihead_replay`, while P3 and P5 scratch remain separately owned.
2. D1 weighting semantics now exclude nontrivial P5 general configuration weighting and training-head scalar weighting while preserving binary property masks and checkpoint score weights.
3. D1 target checkpoint semantics now use one protected campaign-common exact 256-frame monitor outside `T_selected` across CV/final.
4. Held-out/locked prohibitions are preserved.
5. Foundation-residual E0 semantics are selected-head-qualified and use composition-level transfer identifiability.
6. D2 defines exact UniversalLoss mathematics, dimensional Huber thresholds, replay-first stochastic exposure, monitor construction, CV topology, and E0 null-space transfer rule.
7. Unaffected P1/P2/P3 semantics were restored losslessly after review found compression drift.
8. Independent D1/D2 re-review returned PASS and the stakeholder ratified progression on 2026-09-14.

**Acceptance:** satisfied for this branch. Repository integration remains a later lifecycle action.

### G1 — Complete authority/API/evidence census

Classify every affected reference as current authority, implementation/API, guide/config, compatibility reader, historical evidence, or unrelated concept. Include public exports, legacy DATA5/role-budget symbols, M3 final-monitor routing, atomic-reference defaults, composition-transfer evidence, source-probe/exposure ordering, and foundation-head/E0 extraction.

**Acceptance:** one current owner for each semantic; compatibility disposition explicit; no historical path is accidentally reactivated; the affected-surface census above is updated if new current consumers are found.

### G1A — D3 architecture reconciliation — **must precede executable implementation**

Amend/review the canonical D3 training-data architecture before D4 code changes. At minimum reconcile `40_training_evaluation.md`, `80_ownership_and_decisions.md`, and the generated/aggregate architecture view so they state:

- the existing shared `PostSelectionMethodIdentity` remains the sole method owner;
- the existing MACE adapter remains the sole dependency-facing execution seam;
- one neutral-`OUTER_MONITOR` constructor owns common target-monitor membership;
- post-selection fold membership is selected-only **train + outer-evaluation + purge**, while the common monitor is external lineage referenced by plan/run consumers;
- `mlcv_monitors.py` no longer owns independent target-parent sampling but retains replay monitoring and selection-inert diagnostics;
- the existing atomic-reference fitter remains the sole E0 solver and fitted P5 preparation owns composition-transfer validation;
- final production consumes the same method/common-monitor topology and never routes M3 into checkpoint control; and
- generation/currentness boundaries reject old method-bearing artifacts rather than semantically migrating them.

Do not encode source-line helper names into D3 unless they are durable owners/interfaces. Do not add a second monitor, method, E0, or currentness owner.

**Acceptance:** D3 is jointly faithful to accepted D1/D2, has one acyclic owner/control graph, and is independently reviewed before executable D4 work begins. Any inability to express the accepted method with one coherent owner graph reopens D3 rather than spawning compensating D4 machinery.

### G1B — D4 specification/handoff freeze — **must precede executable implementation**

Reconcile affected current specifications and freeze the implementation contract before code mutation. Exact version numbers remain a D4 choice, but current generations must advance wherever old payloads could authorize a materially different method. Cover at least:

1. post-selection method/exposure generation;
2. MACE execution-semantics/source-probe generation if needed to bind loss/unit/order behavior;
3. CV fold/plan/run-plan generation removing selected-only checkpoint-monitor fields from current fold semantics;
4. common target-monitor policy/record generation with neutral parent identity and exact-256 fail-closed behavior;
5. MLCV run-monitor/catalog generation for shared target membership while preserving replay products;
6. DATA8 P5 materialization/runtime evidence generation;
7. fitted P5 preparation / atomic-reference transfer-evidence generation sufficient to bind required compositions and transfer result; and
8. restart/currentness stamps that invalidate old stress/fold-local/M3/from-scratch-E0/target-first/missing-transfer artifacts.

Public/config contract:

- no new corpus-order knob; current two-head order is fixed by D2;
- no separate energy/force/stress Huber-delta knobs; one numeric `huber_delta` retains property-specific dimensional interpretation;
- an explicitly incompatible foundation `fit_mode` fails with an actionable error rather than being overridden;
- retired training-head scalar fields fail closed in current config;
- historical fold-monitor/monitor-parent schemas may remain readable only as historical provenance and cannot authorize current execution;
- one authoritative P5 fold-default resolver yields 3, with explicit `K>=2` override; and
- insufficient exact monitor support or E0 composition transfer is typed infeasibility, not a fallback path.

**Acceptance:** D4 handoff is specific enough that two independent implementers would produce the same externally visible schemas/failure behavior/currentness semantics while remaining free on private helper decomposition.

### Implementation Stage A — method/exposure/config/identity cutover

After G1A/G1B PASS, implement G2, G3, G8, G9 and the method/exposure portions of G10 as one coherent stage. Run focused tests plus affected regression before proceeding.

### G2 — Restore native UniversalLoss realization

- Remove only the foundation-adaptation UniversalLoss->stress source mutation.
- Keep source qualification, restart/CUDA/precision/runtime repairs and P3 complete-batch patch.
- Multihead replay allows native MACE UniversalLoss and verifies resolved class/parameters.
- Naive foundation fine-tuning explicitly requests UniversalLoss when native routing would not.
- Preserve and verify `force_mh_ft_lr=true` and `real_pt_data_ratio_threshold=0.0`.
- Bind numeric delta/EFS/conditional-force semantics and canonical dimensional interpretations `0.01 eV/atom`, `0.01 eV/Angstrom`, `0.01 eV/Angstrom^3` without creating three config knobs.
- Preserve current two-head `pt_head`/replay-first then target-second pre-shuffle combined index layout and qualify it through the existing source-probe/execution-semantics owner.
- If SWA/another phase can change loss coefficients/family, prove it disabled or bind/qualify that trajectory-changing behavior.

**Acceptance:** real pinned parser + `get_loss_fn()` + training path execute accepted foundation-adaptation loss; LR/EMA are not silently mutated; ordered exposure matches D2; no custom loss/sampler exists.

### G3 — Remove inert P5 configuration weighting and retire head scalars

- Stop fitting/binding `ConfigurationWeightPolicy` in restored UniversalLoss P5.
- Preserve general configuration-weight owners for P3/other methods.
- Neutralize `config_weight=1.0` only when transport requires the key.
- Preserve binary property masks.
- Remove live `target_head_weight`, `replay_head_weight`, and equivalent `target_weight`/`head_weight` semantics from current config, replay preparation, cache identity, materialization, and evidence.
- Current configs specifying retired scalars fail closed with a removal/migration error.
- Historical payloads may remain readable but cannot authorize current P5.

### G8 — Restore CV default three

Change one authoritative current P5 default 5 -> 3; reconcile config/spec/guide/tests; preserve `K>=2`, override, all-required-fold/seed semantics, and current seed population; prove retired DATA5 K=3 authority was not reactivated.

### G9 — Preserve adaptive-stop/checkpoint score semantics

Preserve current `target_score_weight`, `replay_score_weight`, matched foundation replay baselines, signed replay degradation, and default 30 meV/Angstrom degradation budget unless separately changed by accepted authority. Retirement of training-head weights must not alter these policies.

### Implementation Stage B — residual E0 and composition-transfer conformance

Implement G4 using the existing fit owner and add transfer-validation evidence/currentness. Run manufactured null-space cases, wrong-head/label-leakage negatives, and affected P5 regression before monitor/topology work proceeds.

### G4 — Restore foundation-residual E0 conformance and composition transfer

**Goal:** close current D4 E0 violations without changing the accepted D1/D2 rule or writing another solver.

**Work:**

- Resolve atomic-reference mode by training mode: `scratch -> FROM_SCRATCH_TOTAL_ENERGY`; `naive_fine_tuning` / `multihead_replay -> FOUNDATION_RESIDUAL`.
- Reject an explicit incompatible foundation-adaptation `fit_mode` rather than silently overriding it.
- For each CV fold, obtain foundation prediction energies and foundation E0s from the exact checkpoint + selected foundation head over exact gradient-training membership only.
- For final production, fit over complete exact `T_selected` only.
- Supply those inputs to the existing residual-fit owner.
- Build required target composition classes from authorized geometry/count evidence for fold gradient training, common monitor, and held-out evaluation; final requires exact `T_selected` plus common monitor.
- Evaluate `c^T v = 0` for every required composition and every unanchored null direction at the accepted rank tolerance, accounting only for explicitly accepted anchors.
- Bind foundation checkpoint/head identity, fit membership digest, input-prediction/E0 identity, corrected target-head E0 digest, numerical rank/singular/null-space evidence, rank tolerance, accepted anchor identity, required-composition digest, and transfer result.
- Source-qualify pinned MACE `pt_head` E0 handling. A selected multi-head foundation must not silently use another/first head's E0s; use the existing dependency seam to ensure selected-head mapping or fail closed.
- Monitor and held-out target **labels** never enter the fit or anchor construction.

Required discriminating oracles:

```text
fit rows proportional to [1,1], required [1,1] -> PASS despite nonunique elemental coefficients
same null space, required [2,1]                -> FAIL
required composition contains absent element   -> FAIL unless an accepted anchor fixes that direction
wrong foundation head                          -> FAIL
monitor/held-out label used in fit              -> FAIL
```

**Acceptance:** real foundation-adaptation execution uses selected-head residual E0s and every governed composition has an authenticated identifiable correction; scratch remains from-scratch; arbitrary minimum-norm/zero fallback cannot authorize a run.

### Implementation Stage C — common monitor and CV/final topology

Implement G5-G7 and G6 as one topology stage. Stage-local regression must cover historical-read/current-reject behavior, exact monitor reconstruction, outer/purge membership preservation, and final M3 retirement.

### G5 — Move common target sampler onto current neutral authority

- Reuse/refactor the existing balanced condition/run/time systematic sampler.
- Parent it from current `NeutralStatisticalBase` / `NeutralOuterPartition` `OuterRole.OUTER_MONITOR` plus canonical frame authority.
- Require exact requested/realized count 256; parent support below 256 or inability to select 256 usable relation-clean frames is typed P5 infeasibility.
- Remove current P5 dependence on `data5_bundle.outer_partition_for_domain(label_domain_id)` and legacy `parent_role=data5_outer_monitor` identity.
- Advance target-monitor record/policy generation as needed.
- Preserve historical DATA5 records only through explicit read compatibility.
- Review public exports; do not silently repurpose a legacy API to mean a new parent contract.

### G6 — Collapse CV/final target-monitor topology

- Advance CV policy/fold/plan and MLCV target-monitor generations.
- Remove `checkpoint_monitor_components_per_fold` and selected-only monitor fields from current fold semantics.
- Preserve exact existing outer-fold and purge algorithms; all remaining selected components become gradient training.
- Retire fold/final target-full parent construction in `mlcv_monitors.py`.
- Retire **M3 as final-production checkpoint monitor** while preserving M3 itself as P3 evidence.
- Preserve replay full/light monitoring and training diagnostics.
- Every CV/final run references the same common target-full membership; target-light is only a deterministic subset.
- Reconcile DATA8 target-monitor artifacts accordingly.

**Acceptance:** no current P5 path can construct/authorize a fold-local, final-specific, or M3 target checkpoint parent; selected fold accounting is exactly train + outer-evaluation + purge and common monitor is external lineage.

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
requested count = 256
realized count = 256
monitor membership digest
exact overlap with every configured T_N and T_selected
split-exclusion-component overlap with every configured T_N and T_selected
```

Do not invent a new generic minimum-run/unit constant. Do not treat `NeutralLeakageReport` as proof of cross-run duplicate/replica/structural-lineage separation when it does not test that claim; use the canonical P1 relation owner as well.

**Acceptance:** exactly 256 realized; zero exact/protected-relation leakage; labels usable; diversity/coverage evidence recorded. Any inability to realize exact 256 or required separation/label usability yields P5 infeasible and no DEVELOPMENT/shrink fallback.

### Implementation Stage D — assembled currentness/runtime/docs/spec integration

Complete G10-G12 after Stages A-C. Reconcile all affected current documentation/specifications/generated views and then run final assembled real-owner integration/affected regression. Production-scale GPU qualification remains deferred.

### G10 — Method identity, runtime evidence, and restart/currentness cutover

Runtime evidence records at least:

```text
training role/mode
foundation checkpoint + selected head identity
loss family/class + numeric UniversalLoss parameters
canonical energy/force/stress residual units + dimensional Huber threshold interpretation
binary property-mask policy
E/F/S coefficients
atomic-reference fit mode + fit membership/input/result digests
rank/singular/null-space/rank-tolerance + accepted anchor identity
required composition-set digest + composition-transfer result
target/replay membership digests and counts
combined count/head counts
ordered pre-shuffle layout = replay/pt_head then target
shuffle/sampler seed and policy
batch size / drop_last / batches per epoch
force_mh_ft_lr / real_pt_data_ratio_threshold / realized duplication factor
LR / EMA / precision / backend
common target-monitor parent/policy/membership digest + exact count 256
replay monitor lineage
fold train/eval/purge membership
method/CV/run-plan digests
```

Advance existing generations as needed. Old stress/fold-local/M3-monitor/from-scratch-E0/target-first/missing-transfer foundation checkpoints, DATA8 materializations, monitor catalogs, and verdicts fail currentness before execution/restart reuse. Preserve independent P1/P2/P3/T_selected evidence.

### G11 — Counterfactual falsification matrix

At minimum falsify:

1. identity says UniversalLoss but runtime resolves stress;
2. runtime UniversalLoss numeric delta/EFS/conditional-force semantics differ;
3. residual units or dimensional Huber interpretation differs while numeric `0.01` is unchanged;
4. D4 invents separate live energy/force/stress delta knobs;
5. P5 still fits/binds nontrivial `ConfigurationWeightPolicy`;
6. non-neutral `config_weight` affects restored P5 trajectory/identity;
7. current config accepts retired target/replay head scalars;
8. replay materialization still applies head-scalar weighting;
9. foundation-adaptation resolves `FROM_SCRATCH_TOTAL_ENERGY`;
10. residual mode runs without exact selected-head foundation predictions/reference E0s;
11. residual E0 fit sees monitor or held-out labels;
12. selected foundation head differs from head used for foundation predictions/E0s;
13. rank-deficient `[1,1]` manifold incorrectly rejects required `[1,1]` transfer;
14. same null space incorrectly accepts required `[2,1]` transfer;
15. absent required element passes without an accepted anchor;
16. minimum-norm/zero fallback is treated as identification;
17. pinned multihead `pt_head` silently uses first/wrong foundation-head E0s;
18. target monitor still consumes legacy DATA5/label-domain authority;
19. monitor realizes fewer than 256 frames but execution continues;
20. current MLCV still builds fold/final target checkpoint parents;
21. final production still uses M3 as checkpoint monitor;
22. common monitor is copied into fold-selected membership rather than external lineage;
23. monitor overlaps or is split-exclusion-related to any configured `T_N`;
24. monitor labels are unusable/incompatible for checkpoint metrics;
25. score/replay-retention weights are deleted with training-head weights;
26. default K falls back to five through another resolver;
27. legacy DATA5 K=3/role-budget semantics become current;
28. TRUE_DFT vs pseudo labels change replay geometry split;
29. MACE target duplication occurs;
30. `force_mh_ft_lr` is false/absent or LR/EMA are mutated;
31. P5 combined-loader sampler/drop_last differs from accepted exposure identity;
32. target/replay memberships and seed are unchanged but target-first pre-shuffle ordering authenticates as current;
33. P3 complete-batch semantics change accidentally;
34. precision/backend changes without identity/evidence change when numerically material;
35. old incompatible checkpoint resumes as current restored run;
36. stale weighted-stress CV authorizes restored final production;
37. exact common monitor differs across CV folds/seeds/selected sizes/final runs;
38. an execution-only field incorrectly invalidates scientific method identity; and
39. a true method field fails to invalidate dependent evidence.

Every case is rejected by a real owner or documented inapplicable with evidence.

### G12 — Real-owner assembled qualification

Exercise the real path:

```text
campaign config
 -> accepted D1/D2-conforming P5 resolver
 -> shared method/exposure identity
 -> foundation/head identity + residual-E0 inputs
 -> composition-transfer feasibility owner
 -> neutral exact-256 common-monitor construction
 -> target/replay materialization
 -> method/CV/run identity
 -> parser-facing MACE config
 -> source-qualified mdstats MACE seam
 -> pinned MACE 0.3.16 UniversalLoss
 -> head-qualified E0 realization
 -> replay/pt_head-first native combined loader
 -> optimizer update
 -> TRAIN2 persistence/restart evidence
 -> adaptive stop/checkpoint evidence
 -> full checkpoint selection
 -> EVAL2 held-out evaluation
 -> fresh final-production representative path
```

Mocks are permitted only below/outside the semantic owner being proved. Static source checks alone cannot close runtime realization claims.

### Implementation Stage E — bounded scientific pilot then full CV

### G13 — Bounded scientific pilot then full CV

Before full CV, record a true pre-update foundation baseline and first several restored checkpoints on representative real LTA data. Record target-monitor RMSE, TRUE_DFT replay RMSE/degradation, resolved loss/dimensional-threshold/exposure identity, selected-head foundation-residual E0 identity, composition-transfer result, corpus counts/order, and exact common monitor identity.

Do not relax gates. Immediate replay degradation on the previous hundreds-of-meV/Angstrom scale falsifies the restored method and reopens D1/D2 rather than triggering another D4 patch.

After pilot PASS, run required three-fold affected qualification and independent Protocol 6.3 Review. Production-scale GPU qualification remains deferred to final release.

## 12. D3/D4 specification and documentation closure obligations

Before declaring implementation complete, reconcile current normative and human-facing surfaces only where materially affected:

- accepted D3 architecture sources and generated aggregate;
- DATA8/MACE realization specification;
- post-selection CV plan/run schema specification;
- online/common-monitor and MLCV monitor specifications;
- adaptive-stop/checkpoint specification;
- campaign CLI/config specification and guide;
- README/example config where user-visible defaults or retired fields are represented;
- public exports for advanced/replaced schema or policy families; and
- semantic history explaining the weighted-stress/fold-local/M3-monitor/head-scalar/from-scratch-E0/target-first lineage replacement.

Generated documentation is derived output and must be regenerated from canonical sources rather than hand-edited as an independent authority.

## 13. Review findings incorporated

Successive independent passes closed or exposed these material requirements:

1. D1, not D2, was the earliest contradictory owner.
2. UniversalLoss makes current P5 general `config_weight` weighting inert.
3. UniversalLoss numerical identity required exact Huber/conditional-force/mask semantics.
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
20. E0 transfer feasibility is a composition-space/null-space condition; individual elemental coefficient uniqueness is neither necessary nor sufficient.
21. One numeric `huber_delta=0.01` corresponds to property-specific thresholds with different physical units; D4 must preserve those dimensional semantics without multiplying config knobs.
22. Unchanged P1/P2/P3 baseline semantics must remain lossless through the restoration; compressed restatement cannot silently remove event-merge, M3 tie, candidate-sufficiency, optimizer-interpretation, or reducer rules.
23. Current two-head MACE orders `pt_head` first; replay-first/target-second pre-shuffle layout is part of deterministic exposure identity under a fixed seed.
24. Exact monitor cardinality is method-bearing: fewer than 256 usable protected frames is P5 infeasibility, not a degraded success state.
25. Current D3 architecture already supplies the right core owners; the restoration should rewire them rather than add parallel method/monitor/E0/currentness machinery.

## 14. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- UniversalLoss cannot express the required foundation-adaptation objective;
- nontrivial P5 configuration weighting is required;
- accepted replay-first native combined-loader exposure is scientifically unacceptable;
- property-specific dimensional Huber semantics cannot be preserved by the execution dependency;
- the protected neutral `OUTER_MONITOR` parent cannot provide exact 256 relation-clean checkpoint evidence for the intended method;
- the composition-level E0 transfer rule itself is scientifically inadequate rather than merely unimplemented;
- P3/P5 cannot legitimately use different loss/exposure methods for the intended conclusions;
- TRUE_DFT replay still causes material forgetting after correct restoration; or
- target/replay acceptance gates are scientifically incompatible with the restored method.

Foundation-residual E0 failure caused by current wiring or missing transfer validation remains a D4 blocker while accepted D1/D2 is coherent. Reopen D3 if one accepted method still requires competing durable owners or if the current owner graph cannot represent the external common monitor/transfer-validation lineage without cycles. Local implementation defects under coherent D1-D3 remain D4 repairs.

## 15. Closeout

Close only after:

1. accepted branch D1/D2 remain independently reviewed and ratified;
2. D3 architecture amendments are reviewed and contain one coherent foundation-adaptation loss/exposure/E0-transfer/monitor/currentness flow;
3. D4 specifications are frozen before code and current schema/failure/currentness behavior is explicit;
4. D4 code/config/public API/tests realize the contract with no inert current fields or parallel owners;
5. exact 256 monitor behavior, composition-transfer E0 feasibility, dimensional Huber semantics, and replay-first stochastic exposure are covered by real-owner evidence;
6. affected old evidence is stale only where materially dependent while independent P1/P2/P3/selection evidence remains usable;
7. semantic history explains replacement of weighted-stress/fold-local/M3-monitor/head-scalar/from-scratch-E0/target-first lineage and the composition-transfer correction;
8. closeout learning/PEM is reconciled only where admission criteria are met; and
9. the plan is archived only after still-current semantics reside in accepted integrated authority.

Central closure invariant:

```text
accepted P5 scientific method
 = accepted P5 numerical method
 = accepted D3 owner/control topology
 = recorded shared method identity
 = authenticated foundation/head + target/replay/common-monitor lineage
 = authenticated residual-E0 + composition-transfer result
 = actual pinned-MACE loss/units/replay-first-loader realization
 = TRAIN2/restart evidence
 = checkpoint/EVAL2 interpretation
```

No current setting may change recorded method identity without changing governed execution, change governed execution without changing recorded identity, or remain current while having no executable/scientific effect.
