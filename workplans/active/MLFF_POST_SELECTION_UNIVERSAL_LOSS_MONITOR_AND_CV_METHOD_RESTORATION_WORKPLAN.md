# MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION — restore post-selection fine-tuning semantics

**Status:** active — G0 D1/D2 closed PASS and stakeholder-ratified on 2026-09-14; independent D3/D4 implementation-plan review completed with remaining handoff gaps closed; G1/G1A/G1B still gate executable implementation  
**Current authority:** accepted branch D1/D2 in `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md`; repository-integrated D3/D4 remain the baseline to be reconciled against them  
**Target branch/base:** `fix/mlff-post-selection-method-restoration` from `1b6b6f83918d31c4b27a0e60d7bc047ef58b6067`  
**Protocol:** SSDP 6.3  
**Review state:** D1/D2 independent re-review PASS at `f310b4c15c6b0465b34013d329847abdb208bae2`; stakeholder ratification received; this revision incorporates the independent pre-implementation D3/D4 plan review and closes the remaining authority, identity, monitor-lineage, final-publication, and invalidation gaps before G1A/G1B

## 1. Disposition

The upstream Serious Challenge is **resolved for this restoration branch**. The repaired D1/D2 pair passed independent falsification and the stakeholder explicitly authorized progression into D3/D4 closure. The 2026-09-13 D1/D2 papers remain the repository-integrated baseline until this branch is integrated, but downstream branch design and implementation must now conform to the accepted restoration authority rather than the superseded P5 method.

The remaining problem is a bounded **D3/D4 conformance restoration**, not a new scientific redesign. Current integrated architecture/code still contains descendants of the superseded method: weighted-stress foundation P5 realization, selected-only fold checkpoint monitors, M3 final checkpoint/publication routing, inert/retired weighting layers, generic from-scratch E0 routing for foundation adaptation, and currentness identities that do not yet bind all accepted numerical semantics.

The D1/D2 reconciliation and the independent D3/D4 implementation-plan review together expose the following downstream requirements that must be explicit before implementation:

1. foundation-residual E0 conformance must validate **composition-level transfer identifiability**, not merely fit rank or elemental-column presence;
2. current two-head stochastic exposure binds the pre-shuffle corpus layout `replay/pt_head || target` under the accepted seed;
3. the common target monitor is **exactly 256 configurations or P5 is infeasible**—there is no shrink-to-fit success state;
4. one numeric `huber_delta=0.01` has property-specific dimensional meanings that runtime evidence/specification must preserve without inventing three independent knobs;
5. current specifications expose both `PostSelectionMethodIdentity` and the older broad `TrainingProtocolIdentity`; restored P5 must have **one** method authority, with the latter explicitly narrowed/retired from current P5 rather than left as a competing protocol authority;
6. `PostSelectionMethodIdentity` and `PostSelectionFittedPreparation` must stop binding the whole `TargetSizeCommonTrainingPolicy.content_digest`; P3-only objective/weighting/harness fields cannot remain hidden P5 currentness parents;
7. the exact common-monitor membership is not merely an execution argument: one immutable common-monitor record must be constructed once and its **same digest** bound by every current CV and final-production plan that consumes it;
8. current final-production/publication code still binds and evaluates P3 `M3` to rank final seeds; accepted P5 authority leaves M3 as P3 evidence only, so P5 final publication must use the already-frozen representative's authenticated common-monitor target metric instead;
9. the current global `MACE_EXECUTABLE_LOSS_FAMILY="stress"` and shared execution-semantics surfaces also serve unchanged P3/scratch paths; fixing foundation P5 must be **mode-specific** and must not globally flip or globally stale unchanged P3 semantics;
10. common-monitor membership construction and protected-relation qualification are distinct: the deterministic sampler operates on the exact label-usable neutral `OUTER_MONITOR` parent, then relation separation is checked; relation conflicts are not repaired by deleting/replacing sampled frames or resampling;
11. canonical replay omission already resolves TRUE_DFT on the single-source interface, while legacy split-file compatibility can still imply pseudo semantics; any current legacy route must require unambiguous explicit label mode rather than silently reintroducing a pseudo default; and
12. the accepted foundation-P5 exposure is the qualified **single-process** path. Multihead and naive foundation modes must both realize their accepted `drop_last=true` geometry, while distributed foundation P5 remains fail-closed until separately proven equivalent.

The plan remains deliberately reductive. Remove wrong/retired semantics, reconnect existing owners, and reuse qualified native MACE behavior. Do not create a custom loss, second sampler, second E0 solver, shadow trainer, parallel identity registry, or compensating wrapper where owner rewiring/removal suffices.

## 2. Frozen cycle decisions

For **foundation-model P5 adaptation** (`naive_fine_tuning` and `multihead_replay`), the accepted branch end state is:

```text
P5 method authority              PostSelectionMethodIdentity family only
loss family                      native MACE UniversalLoss
huber_delta numeric value        0.01, explicitly bound
energy Huber threshold           0.01 eV/atom
force base Huber threshold       0.01 eV/Angstrom
stress Huber threshold           0.01 eV/Angstrom^3
global E:F:S coefficients        1:10:1
general config_weight in P5      neutral transport only; not a P5 loss layer
target:replay training scalar    none
atomic-reference mode            foundation_residual
E0 transfer rule                 composition-level null-space identifiability
replay-label default             TRUE_DFT
pre-shuffle two-head layout      replay/pt_head || target
implicit target duplication      forbidden
force_mh_ft_lr                   true for multihead replay
checkpoint target monitor        one protected campaign-common exact 256-frame monitor
common-monitor plan lineage      identical immutable monitor-record digest in CV/final plans
monitor shortfall                P5 infeasible; no shrink/fallback
CV fold default                  3
held-out CV evidence             unavailable to fitting/checkpoint choice
final single-best seed metric    frozen representative common-monitor target metric
P3 M3 role in P5                 none; remains P3 evidence / downstream probe only
foundation P5 execution          qualified single-process path only
replay degradation criterion     unchanged
production-scale GPU qualification deferred to final release
```

This workplan does **not** change:

- P3 target-size screening loss/exposure semantics;
- P5 scratch-training loss semantics;
- target-size membership/order/reducer semantics;
- replay geometry split;
- TRUE_DFT default already established on the canonical single-source replay interface;
- target/replay acceptance thresholds;
- current optimizer-seed population;
- M3's P3 target-size evidence identity or legitimate downstream qualification use as a development probe; or
- final-release GPU qualification policy.

A successful assembled restoration establishes that the **assembled restored method** works. Because loss, target-monitor topology, retired head scaling, default CV geometry, E0 conformance, stochastic exposure identity, and currentness are corrected together, it does not by itself prove which individual change caused replay-retention recovery.

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

The restoration may not redefine that relation taxonomy or recompute it ad hoc downstream. In particular, the selected-only `SelectedRelationProjection` is sufficient for selected-fold allocation but **not** by itself for proving target-versus-common-monitor separation because it deliberately excludes frames outside `T_selected`. Common-monitor separation must use the canonical P1 relation owner over the joint monitor/target universe or an equivalent canonical component mapping that can expose cross-role relations.

### 3.3 Replay

- TRUE_DFT replay remains the canonical training default when canonical labels exist.
- Foundation pseudo-label replay remains explicit opt-in.
- Pseudo-label training still requires an independent TRUE_DFT replay monitor.
- Changing replay label mode over the same prepared source/split must not change replay geometry membership.
- Replay retention remains an admissibility constraint, not target-size ranking credit.
- Existing target-force and replay-degradation thresholds are not relaxed to manufacture a pass.
- A legacy compatibility route may preserve an explicitly requested historical pseudo mode, but omission on a current path may not silently select pseudo labels.

### 3.4 Weight and objective taxonomy

Keep four concepts separate:

1. global energy/force/stress coefficients for the method that owns them;
2. general `ConfigurationWeightPolicy` / `config_weight` for methods that actually consume it;
3. target-versus-replay **training-head scalar** weights, retired by this restoration; and
4. checkpoint/adaptive-stop `target_score_weight` / `replay_score_weight`, which remain separately owned.

Retiring item 3 does not delete item 4 and does not globally delete item 2.

For restored UniversalLoss foundation P5, item 2 is **not an active P5 loss layer** because pinned MACE UniversalLoss does not consume `ref.weight`. P5 must not fit or identity-bind a nontrivial `ConfigurationWeightPolicy` that has no executable effect. The existing general `[objective]` / `[weighting]` configuration may continue to govern P3/scratch where accepted; foundation P5 must not inherit those P3-only values merely because current code packages them in `TargetSizeCommonTrainingPolicy`.

The current foundation-P5 objective is fixed by D2 at UniversalLoss with `1:10:1` and numeric delta `0.01`. A future dedicated foundation-P5 override would be an upstream method change; existing P3 objective overrides are not such an override and must not be rejected simply because P5 excludes them.

### 3.5 Identity and invalidation economy

- `PostSelectionMethodIdentity` is the sole current P5 method-semantic identity. `TrainingProtocolIdentity` may remain for separately current non-P5 consumers or historical readability, but it cannot independently authorize restored P5.
- Exact realized monitor membership, fold membership, E0 fit result, and composition-transfer result are descendants, not pre-work method fields.
- A P3-only policy change must not stale accepted P5 descendants unless a real shared component changed. Conversely, every true foundation-P5 method change must invalidate dependent P5 evidence.
- Shared source probes may be enriched, but a P5-only semantic repair must not blanket-invalidate unchanged P3 TRAIN2/EVAL2 evidence merely because one global token was advanced.

## 4. Accepted D2 foundation-adaptation method

### 4.1 UniversalLoss numerical identity

For pinned `mace-torch==0.3.16` `UniversalLoss` with numeric `huber_delta=0.01`:

- energy uses Huber loss on per-atom energy residuals with threshold `0.01 eV/atom`;
- stress uses Huber loss on Cartesian stress residuals with threshold `0.01 eV/Angstrom^3` and reduces all nine stored Cartesian tensor entries;
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

For `naive_fine_tuning`, `N_r=0` and the accepted target-only shuffled path likewise uses the foundation-P5 `drop_last=true` update geometry. This is separate from P3 target-size screening, whose optimizer normalization requires complete target batches and `drop_last=false`.

The accepted foundation-P5 path is single-process. A distributed sampler/process group is not silently equivalent; current foundation P5 must reject that route until an explicit D2-equivalence qualification exists.

### 4.3 Foundation-residual atomic references and transfer feasibility

Foundation adaptation retains one existing atomic-reference fit owner. Do **not** create a second solver.

- target-head E0s are fitted as elemental corrections to the exact selected/head-qualified foundation prediction baseline;
- CV fits use only that fold's gradient-training membership;
- the common target checkpoint monitor and held-out fold **labels** do not enter the E0 fit;
- final production fits on complete exact `T_selected` only;
- the fit binds exact foundation checkpoint and selected foundation head;
- target-head corrected E0s and replay/pretraining-head foundation E0s remain distinct head-local mappings where required; and
- no new absent-element prior/anchor is introduced by this restoration.

The fitted P5 preparation must additionally validate composition transfer. Let `C` be the authorized fit count matrix and `N_free` the unanchored null space after any already-accepted, identity-bound anchors. For every governed target composition vector `c` whose energy is consumed by training, checkpoint monitoring, or held-out evaluation, require

```text
c^T v = 0  for every v in N_free
```

at the accepted numerical-rank tolerance. With no accepted anchor this is equivalent to `c` lying in the row space of `C`. Individual elemental coefficients may be nonunique when the consumed composition-weighted correction remains unique. A missing element is one sufficient failure case, not the complete test.

Monitor/held-out geometry or composition counts may be inspected for this transfer test; their target energy labels may not be borrowed to repair the fit. Minimum-norm output, an arbitrary zero coefficient, another fold's solution, or a different foundation head does not create identifiability.

The transfer result belongs to fitted P5 preparation/run lineage as a consumer of the existing atomic-reference fit record; it is not a new E0 authority. Persist/bind the required composition set or canonical composition-class digest, numerical-rank tolerance, rank/singular/null-space evidence sufficient to reconstruct the decision, accepted anchor/prior identity if any, and per-required-composition or canonical aggregate pass/fail evidence.

Scratch mode retains from-scratch total-energy E0 fitting under its separately accepted method.

Pinned MACE multihead code can derive `pt_head` foundation E0s internally and, for some multi-head foundation tensor shapes, falls back to the first head. That behavior must be source-qualified against mdstats' selected foundation-head identity. If the selected foundation head is not the upstream fallback head, the existing qualified dependency seam must ensure the correct head-qualified mapping or fail closed.

## 5. Common target checkpoint monitor

### 5.1 Membership owner, parent, and exact cardinality

The current target checkpoint domain is one campaign-common monitor `M_mon` selected once from the protected neutral `OuterRole.OUTER_MONITOR` population:

```text
NeutralStatisticalBase
  +-- DEVELOPMENT   -> U_size -> pi_train -> T_N / T_selected
  +-- OUTER_MONITOR -> deterministic common target checkpoint monitor M_mon
```

Current P5 requires **exactly 256 usable configurations**. The number has no relationship to a target-size rung beyond numeric coincidence.

The monitor membership record is a deterministic descendant of the exact neutral/frame parent plus the target-monitor sampling policy. It does **not** become a target-size membership and does not need to embed a selected-size identity merely to prove separation. Instead, P5 plan admission separately authenticates the common monitor against the current P1 relation authority and every configured target prefix relevant to the frozen experiment.

For every configured target prefix and P5 run:

```text
M_mon intersect T_N                 = empty
M_mon intersect gradient_training   = empty
M_mon intersect held_out_evaluation = empty
```

No monitor frame may belong to a canonical P1 split-exclusion component containing any frame of the relevant target ladder. The cross-role relation check must use an authority that can see both monitor and target frames; a selected-only projection cannot prove this property.

If the neutral partition cannot provide 256 label-usable protected parent frames, if deterministic monitor construction cannot produce exact 256, or if the resulting exact monitor violates protected separation, current P5 is **infeasible**. There is no smaller-monitor success state, `DEVELOPMENT` fallback, relation splitting, target-frame substitution, deletion/replacement of conflicting sampled members, or resampling to manufacture a pass.

### 5.2 Preserve sampler capability, not legacy DATA5 authority

Historical `OnlineMonitorPolicy` provides the useful sampling capability: balanced condition/run quotas plus deterministic systematic source-time spreading with seed 161803. The current historical interface `build_target_online_monitor(data5_bundle, ..., label_domain_id, ...)`, however, is tied to retired DATA5/label-domain authority.

Transfer the target-sampling capability to the current neutral outer-partition/frame authority. The exact parent used by the D2 sampler is the canonical-label-usable `OUTER_MONITOR` target population. Sampling occurs over that exact parent using the D2 SHA-256 quota ordering `(marker, stratum_key)` and systematic positions; protected-relation separation is checked **after** exact membership is fixed and does not mutate membership.

Do not reactivate `label_domain_id`, pre-target-size DATA5 CV, or retired role-budget ownership. Advance current target-monitor records so their parent identity is the neutral outer partition/frame authority. Historical DATA5 target-monitor records remain historical/read-compatible only.

The current aggregate `OnlineMonitorPolicy` may continue to carry replay/training-diagnostic budgets for other consumers, but P5 method identity must bind only the **target-monitor construction projection** that affects `M_mon` (`target_configurations=256`, seed, target strategy, parent semantics). An unrelated replay/training-diagnostic budget edit must not silently change foundation-P5 method identity.

Target exact-size semantics are role-specific: current target P5 requires requested=`realized`=`256`. Do not globally change replay-monitor short-parent behavior unless its own accepted owner requires it.

### 5.3 One immutable record, many consumers

Construct/publish one immutable common target-monitor record per applicable neutral-parent/policy identity and store it once through the existing content-addressed evidence machinery. Every sibling `PostSelectionCvPlan` and the corresponding `FinalProductionPlan` must bind the **same monitor-record content digest**. Per-run plans may inherit it through their plan digest; materialization must authenticate its target-validation artifact against that exact record.

No new mutable campaign-global monitor registry or pointer is required merely to share the record. If current orchestration can build once and pass/store the immutable record before sibling plan publication, use that direct path.

### 5.4 Collapse competing MLCV target-monitor machinery

Current `mlcv_monitors.py` owns a later fold/final target-full/target-light mechanism. Reconcile it rather than running two target-monitor systems:

- retire fold-specific and final-specific target checkpoint-parent construction;
- preserve TRUE_DFT replay full/light monitoring;
- preserve selection-inert training diagnostics;
- make every CV/final run reference the same common target-full membership;
- target-light is only a deterministic subset of the common target monitor, never a new parent; and
- remove duplicated target-side sampling responsibility once the common sampler owns membership.

For the current cycle, target-light budget and target-full membership are both 256. Prefer the reductive realization `target_light == target_full == M_mon`; do not retain a second target sampler merely to reproduce the same 256 members. A future smaller target-light stopping subset is a checkpoint-control policy change and must remain a deterministic subset of `M_mon`.

### 5.5 M3 boundary

`M3` remains unchanged P3 target-size development/model-selection evidence. Current P5 final production must not use M3 for checkpoint selection, stopping, final-seed ranking, final-publication identity, or P5 currentness. No M3 identity is rewritten or reclassified to pretend it is `OUTER_MONITOR` evidence.

Downstream deployment/qualification may continue to consume a deterministic M3 development cohort when that use is already authorized as a representation/runtime probe. If so, expose it through the P3/target-size evidence owner rather than keeping a P5 final-production helper as a de facto M3 authority.

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

### 6.3 Final production and publication

Fresh final production consumes the same foundation-adaptation loss/exposure method, common target monitor/checkpoint policy, replay-retention policy, selected-head foundation-residual E0 rule plus composition-transfer validation, and currentness semantics that CV validated. Only production horizon/seeds/publication policy remain role-specific.

`FinalProductionPlan` must bind exact `T_selected`, accepted CV ancestry, production policy, replay lineage where applicable, and the exact common-monitor record digest. It must no longer bind `m3_evaluation_size` / `m3_membership_digest` as P5 production ancestry solely because the superseded implementation did.

Each required final seed freezes its representative under the accepted common-monitor/replay-admissibility checkpoint owner. For `all_qualified_final_seeds`, no cross-seed target ranking is needed. For `single_best_final_seed`, rank only the **already-frozen admissible representatives** by their authenticated target-side metric on the same common `M_mon` under the accepted deterministic tie policy. Do not perform an additional M3 evaluation to choose the publication member.

If a distinct final-seed ranking cohort is desired in the future, that is an upstream D1/D2 method change; D3 must not infer one from historical M3 code.

## 7. D3 ownership, identity, fitted preparation, and currentness

### 7.1 Identity DAG

```text
accepted branch D1/D2 P5 method
 -> existing shared PostSelectionMethodIdentity owner
 -> CV/final role policy
 -> selected/replay/common-monitor/fitted-P5 lineage
 -> run plan
 -> PostSelectionMaterialization (current P5 DATA8 projection)
 -> MACE adapter / TRAIN2 runtime evidence
 -> checkpoint selection / held-out EVAL2 interpretation
 -> final publication decision
```

### 7.2 Cycle-scoped D3 ownership decisions

No parallel architecture is introduced. Reconcile the current owners as follows:

- **Shared P5 method identity:** keep the existing `PostSelectionMethodIdentity` family as the only post-selection method owner. Advance its recipe/dependent policy generations as needed; do not add a second P5 identity registry.
- **`TrainingProtocolIdentity`:** explicitly classify the older broad DATA8 protocol identity. If it still has separately current non-P5 consumers, narrow its specification to those consumers. Historical/read-compatible records may remain. It must **not** be a second current authority or authorization route for restored post-selection P5. Do not route the newer `PostSelectionMaterialization` path back through it merely to satisfy stale specification prose.
- **P5 method/preparation policy:** replace the whole-`TargetSizeCommonTrainingPolicy` dependency with a P5-specific projection assembled from existing real component owners. It contains only actual P5 method-bearing inputs: mode-specific loss/objective identity, atomic-reference policy/transfer policy, foundation identity/head, replay-exposure policy, and other genuinely shared P5 inputs. It does not inherit P3-only configuration-weight or harness fields.
- **MACE dependency seam:** keep the current MACE compatibility/adapter seam as the only dependency-facing owner for source qualification, parser arguments, mode-specific loss/loader realization, precision/backend binding, and executable evidence.
- **Common target monitor:** move target monitor membership ownership to one neutral-`OUTER_MONITOR` constructor over current neutral/frame authority. `mlcv_monitors.py` becomes a consumer of that target membership while retaining replay monitoring/training-diagnostic responsibilities; it no longer samples independent target parents.
- **Monitor separation evidence:** keep membership identity separate from the target-ladder relation check. P5 plan admission authenticates exact/protected separation through canonical P1 relation authority and binds the resulting separation evidence/parents without mutating monitor membership.
- **CV plan:** keep `PostSelectionCvPlan` as the CV plan owner, but current fold membership contains only train/eval/purge and the plan explicitly binds the common-monitor record digest.
- **Atomic references:** keep the existing atomic-reference fitter as the sole E0 solver. P5 fitted preparation owns role-specific composition-transfer validation using the fit record plus required geometry/composition classes.
- **Final production/publication:** keep the existing P5 production/publication owners, remove M3 from their P5 ancestry, bind the common-monitor record, and use the frozen common-monitor representative metric for any single-best final-seed policy.
- **M3 downstream probe:** if qualification still uses M3 as a development probe, route it from the P3 target-size evidence owner rather than the P5 production owner.
- **Currentness/pointers:** keep `CampaignStore` and existing currentness machinery as locators/validators over immutable products. Advance only the minimal owning generations and reject stale semantic state rather than migrating old meaning into new schemas.

These are cycle-scoped D3 concretizations of accepted D1/D2. Exact dataclass fields, schema names/version tokens, parser options, helper placement, and storage paths remain D4 unless required below.

### 7.3 Shared method identity requirements

Bind at least:

- method recipe generation and training mode;
- foundation checkpoint/head identity;
- mode-specific loss identity: foundation modes UniversalLoss; P5 scratch/P3 retain their separately accepted weighted objective;
- fixed foundation-P5 numeric `huber_delta=0.01`, global `1:10:1`, force-regime semantics, nine-entry stress reduction, and dimensional interpretation;
- local-property-mask policy;
- P5 sample-exposure semantics including replay/`pt_head`-first then target-second pre-shuffle layout, `force_mh_ft_lr`, no duplication, shuffle/sampler, current single-process restriction, and `drop_last`;
- atomic-reference fit mode, selected foundation-head qualification, and the policy/tolerance governing composition-transfer validation;
- replay label/source/split policy;
- optimizer/LR/EMA/precision/backend semantics; and
- shared checkpoint/admissibility policy plus the **target-monitor construction policy projection**.

Do not bind exact realized monitor membership, fold membership, fit result, composition-transfer result, or plan-specific relation-separation result into the pre-work shared method identity. Those belong to plan/fitted-preparation/evidence lineage.

Do not reuse the entire `TargetSizeCommonTrainingPolicy.content_digest` as P5 method identity after P3/P5 divergence. A change only to P3 `ConfigurationWeightPolicy`, P3 objective coefficients, or target-size harness settings must not change foundation-P5 method identity when no P5 semantic changed.

### 7.4 Fitted P5 preparation

Remove the non-executable `ConfigurationWeightPolicy` layer from restored UniversalLoss foundation P5. If ExtXYZ transport requires `config_weight`, emit/validate neutral `1.0` as transport, without a fitted-weight scientific identity. Do not keep `fitted_weights_digest` / fitted nontrivial weight records in the current foundation-P5 preparation merely to satisfy the superseded schema. P5 scratch may retain its separately accepted weighting preparation.

Foundation-adaptation preparation resolves `FOUNDATION_RESIDUAL` from training mode, not from the generic `AtomicReferenceFitPolicy` default. An explicit incompatible fit mode fails closed. Scratch resolves its separately accepted from-scratch fit.

CV fitted preparation binds fold gradient membership, exact selected-head foundation predictions/E0 mapping, resulting corrected target-head E0 digest, required target composition classes from gradient/common-monitor/held-out geometry, and composition-transfer feasibility evidence. Final fitted preparation binds exact `T_selected`, common-monitor required composition classes, and the corresponding transfer result.

The current foundation-P5 preparation identity binds the P5-specific preparation policy projection, not `TargetSizeCommonTrainingPolicy.content_digest`.

### 7.5 Loss/execution identity projection

The current global `MACE_EXECUTABLE_LOSS_FAMILY="stress"` is consumed by unchanged P3 and other weighted-loss paths. Do **not** repair P5 by changing that global value to `universal`.

At the existing MACE seam, resolve executable loss from the authenticated method/mode:

```text
P3 target-size / accepted weighted paths -> stress / WeightedEnergyForcesStressLoss
P5 scratch                               -> its accepted weighted family
P5 naive_fine_tuning                     -> universal / UniversalLoss
P5 multihead_replay                      -> native forced universal / UniversalLoss
```

The implementation may rename/narrow a global constant if that removes ambiguity, but it may not create another method owner. `PostSelectionMethodIdentity` plus the existing MACE seam remains the source of truth for P5.

Likewise, do not blanket-bump a shared `MACE_EXECUTION_SEMANTICS_VERSION` if the only semantic change is foundation-P5-specific and the bump would stale unchanged P3 evidence. Advance P5 method/execution generations at the narrowest owning boundary. A shared source-probe schema may gain evidence fields without manufacturing a scientific change for unaffected consumers.

### 7.6 Currentness cutover

Advance existing P5 method/run/materialization/evidence generations as required. Old artifacts become stale when they can differ in any accepted method-bearing dimension, including:

- weighted-stress rather than UniversalLoss foundation P5;
- fold-local/final-local/M3 target monitor topology;
- M3 final-seed ranking/publication ancestry;
- live head-scalar/config-weight foundation-P5 semantics;
- whole-P3-common-training policy coupling in P5 identity;
- from-scratch E0 foundation preparation;
- foundation-residual records/preparations without required composition-transfer validation;
- target-first rather than replay-first two-head pre-shuffle layout;
- incompatible dimensional Huber/unit interpretation; or
- incompatible CV schema/default/currentness ancestry.

Old TRAIN2 checkpoints/workspaces cannot resume as restored foundation-adaptation runs, old P5 materializations cannot be reused as current, old MLCV target-monitor catalogs cannot authorize current runs, and old CV verdicts cannot authorize restored final production. Preserve independent P1/P2/P3 evidence and frozen target memberships. Avoid invalidating unchanged P3 solely because a shared implementation file or source probe changed.

## 8. Scope and non-goals

### 8.1 Minimum affected-surface census

```text
docs/methods/mlff_scientific_method.md
docs/methods/mlff_numerical_algorithmic_method.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
docs/arch_manuals/mlff_training_data_architecture.md generated/aggregate view
docs/specs/training_data/mlff_data_stage_plan_spec.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/mlff_data9a2_real_mace_realization_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/specs/training_data/mlff_online_monitor_spec.md
docs/specs/training_data/mlff_adaptive_training_stop_spec.md
docs/specs/training_data/** other affected P5 specifications
docs/guides/mlff_campaign_cli_user_guide.md
README.md
campaign.toml.example
mdstats/__init__.py
mdstats/training_data/__init__.py
mdstats/training_data/protocol.py
mdstats/training_data/mace_compatibility.py
mdstats/training_data/critical_precision_cli.py
mdstats/training_data/foundation.py
mdstats/training_data/reference_fit.py
mdstats/training_data/model_features.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/post_selection_cv_plan.py
mdstats/training_data/post_selection_production.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/post_selection_publication.py
mdstats/training_data/post_selection_store.py
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
mdstats/training_data/qualification/deployment.py and any other downstream M3 probe consumer
foundation prediction/reference-E0 provider and current affected tests/qualification owners
```

Reference census includes at least:

```text
PostSelectionMethodIdentity / TrainingProtocolIdentity / PostSelectionMaterialization
TargetSizeCommonTrainingPolicy / common_training_policy_digest
UniversalLoss / WeightedEnergyForcesStressLoss / MACE_EXECUTABLE_LOSS_FAMILY
MACE_EXECUTION_SEMANTICS_VERSION / POST_SELECTION_METHOD_RECIPE_VERSION
huber_delta and canonical energy/force/stress units
config_weight / ConfigurationWeightPolicy / fitted_weights_digest
config_energy_weight / config_forces_weight / config_stress_weight
target_head_weight / replay_head_weight / target_weight / head_weight
target_score_weight / replay_score_weight
AtomicReferenceFitMode / foundation_residual / foundation E0/head extraction
rank / singular_values / null_space_dimension / relative_singular_value_tolerance
composition-count rows / required composition classes / transfer-feasibility evidence
force_mh_ft_lr / real_pt_data_ratio_threshold
pt_head_sorted_first / replay-first-target-second pre-shuffle layout
single-process / distributed sampler / target/combined drop_last
checkpoint_monitor_components_per_fold
OnlineMonitorPolicy / target-monitor policy projection / build_target_online_monitor
MlcvMonitorPolicy / MlcvRunMonitorRecord
exact 256 target-monitor cardinality / no shrink fallback
common-monitor record digest in CV/final plans
SelectedRelationProjection versus cross-role P1 relation proof
M3 final-monitor routing / m3_membership_digest / frozen_m3_development_evidence
final publication representative target metric
online_monitor_policy_digest / target_online_monitor_record_digest
fold_count / cross_validation_folds / checkpoint_monitor_minimum_units_per_fold
ReplayLabelMode / legacy external_pseudolabel default behavior
DATA5 / label_domain_id uses on current P5 paths
```

Affected-surface expansion discovered during implementation is not requirement expansion.

### 8.2 Explicit non-goals

- redesigning target-size ordering/membership/reducer;
- changing P3 loss merely to match P5;
- changing P5 scratch method without separate authority;
- changing replay geometry split or the canonical TRUE_DFT default;
- relaxing target/replay gates;
- restoring historical seed multiplicity solely for resemblance;
- adding a user-facing corpus-order knob;
- adding three independent user-facing Huber-delta knobs;
- custom trainer/loss/sampler/E0 solver;
- a second P5 protocol identity or monitor registry;
- semantic migration that reinterprets old fold-monitor, M3-publication, or monitor-parent records as current;
- blanket invalidation of unchanged P3 evidence for P5-only semantics; or
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
    reason: Old stress/fold-local/from-scratch-E0/target-first/M3-publication TRAIN2 state must not become continuation authority after the generation cutover.
  - id: SP-001
    disposition: APPLICABLE
    reason: Remove duplicated loss/monitor/protocol/weight ownership and return responsibility to real owners.
  - id: SP-002
    disposition: APPLICABLE
    reason: Retired fields, incompatible fit modes, historical schemas, ambiguous replay defaults, and stale run state must fail closed.
  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve independent immutable P1/P2/P3/selection evidence rather than rebuilding or globally invalidating it.
  - id: SP-004
    disposition: APPLICABLE
    reason: Real pinned-MACE and real monitor/currentness/foundation-head/publication paths are required; helper-only proof is insufficient.
```

The D1/D2 branch authority advanced during this cycle, but the accepted PEM basis did not. These HAS dispositions were rechecked against the accepted D1/D2 repairs and this D3/D4 plan review and remain applicable. Refresh again if accepted memory or governing authority materially advances before closeout.

## 10. Capability-transfer map

```text
forced UniversalLoss -> stress rewrite
  -> remove only foundation-adaptation loss mutation
  -> retain source qualification and unrelated runtime repairs
  -> do not globally flip MACE_EXECUTABLE_LOSS_FAMILY used by P3

broad TrainingProtocolIdentity P5 prose
  -> current restored P5 authority is PostSelectionMethodIdentity -> role policy -> plan -> fitted preparation -> PostSelectionMaterialization -> run evidence
  -> narrow TrainingProtocolIdentity to separately current non-P5 consumers / historical readability
  -> no second P5 authorization route

TargetSizeCommonTrainingPolicy used as whole P5 identity
  -> retain it for P3
  -> project only genuinely shared component owners into a P5-specific method/preparation policy
  -> P3-only objective/weight/harness changes do not stale P5

P5 configuration-weight fitting
  -> retain general owner for methods that consume it
  -> project it out of UniversalLoss foundation P5
  -> neutral config_weight only when transport requires it
  -> no inert fitted-weight identity in current foundation-P5 preparation

fold-local / final-specific / M3 target checkpoint parents
  -> retire from current P5
  -> one neutral-OUTER_MONITOR common target monitor
  -> every CV/final plan binds the same immutable monitor-record digest

M3 final-seed ranking/publication
  -> retire from P5 production/publication lineage
  -> single-best uses frozen representative common-monitor target metric
  -> retain M3 under P3 for target-size evidence and separately authorized downstream probe use

legacy DATA5 common-monitor interface
  -> preserve deterministic balanced sampling capability
  -> current neutral outer-partition/frame parent
  -> preserve exact D2 sampling order, then fail on relation collision rather than resample

current MLCV fold/final target sampler
  -> retire competing target-parent construction
  -> current target-light == target-full == common 256 monitor
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
  -> reject distributed foundation P5 until equivalence is accepted

current authenticated run/restart/currentness machinery
  -> preserve
  -> advance only minimal P5 generations so incompatible old state cannot resume
  -> preserve unchanged P3 evidence applicability
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

Classify every affected reference as current authority, implementation/API, guide/config, compatibility reader, historical evidence, or unrelated concept. Include public exports, legacy DATA5/role-budget symbols, `TrainingProtocolIdentity`, `PostSelectionMethodIdentity`, `TargetSizeCommonTrainingPolicy` coupling, `MACE_EXECUTABLE_LOSS_FAMILY`, shared execution-semantics tokens, M3 final-monitor/final-publication routing, atomic-reference defaults, composition-transfer evidence, source-probe/exposure ordering, replay-label default resolution, and foundation-head/E0 extraction.

For each M3 reference, distinguish:

```text
P3 target-size evidence                 -> preserve
P5 checkpoint / final-seed ranking      -> retire
separately authorized qualification probe -> preserve through P3 owner, not P5 ownership
```

For each `TrainingProtocolIdentity` reference, determine whether it is:

```text
current non-P5 consumer contract
historical compatibility record
stale prose/implementation claiming current P5 authority
```

**Acceptance:** one current owner for each semantic; compatibility disposition explicit; no historical path is accidentally reactivated; no current P5 path has two method identities; the affected-surface census above is updated if new current consumers are found.

### G1A — D3 architecture reconciliation — **must precede executable implementation**

Amend/review the canonical D3 training-data architecture before D4 code changes. At minimum reconcile `40_training_evaluation.md`, `80_ownership_and_decisions.md`, the generated/aggregate architecture view, and any architecture text that still promotes old DATA8 protocol identity so they state:

- `PostSelectionMethodIdentity` remains the sole current P5 method owner;
- `TrainingProtocolIdentity` is narrowed to separately current non-P5 scope and/or historical compatibility and cannot authorize restored P5;
- current P5 materialization lineage is `method -> role policy -> plan -> fitted preparation -> PostSelectionMaterialization -> run evidence`, not a second protocol graph;
- the P5 method/preparation policy is a projection of real component owners and does not bind whole `TargetSizeCommonTrainingPolicy`;
- the existing MACE adapter remains the sole dependency-facing execution seam and resolves loss **by authenticated mode**, without globally changing unchanged P3/scratch semantics;
- one neutral-`OUTER_MONITOR` constructor owns common target-monitor membership;
- one immutable common-monitor record is shared by every selected-size CV plan and final plan; exact monitor membership is external to selected folds;
- monitor membership identity is separate from plan-level protected-relation separation evidence;
- post-selection fold membership is selected-only **train + outer-evaluation + purge**;
- `mlcv_monitors.py` no longer owns independent target-parent sampling; current target-light may directly equal the common 256 target-full membership while replay/diagnostics remain owned there;
- the existing atomic-reference fitter remains the sole E0 solver and fitted P5 preparation owns composition-transfer validation;
- final production/publication consumes the common-monitor metric and contains no M3 P5 checkpoint/ranking/currentness dependency;
- any continuing downstream M3 development probe is owned/routed from P3 evidence; and
- generation/currentness boundaries reject old method-bearing artifacts at the narrowest affected owner rather than globally invalidating unchanged P3 evidence.

Do not encode source-line helper names into D3 unless they are durable owners/interfaces. Do not add a second monitor, method, E0, or currentness owner.

**Acceptance:** D3 is jointly faithful to accepted D1/D2, has one acyclic owner/control graph, resolves `TrainingProtocolIdentity` versus `PostSelectionMethodIdentity` unambiguously, and is independently reviewed before executable D4 work begins. Any inability to express the accepted method with one coherent owner graph reopens D3 rather than spawning compensating D4 machinery.

### G1B — D4 specification/handoff freeze — **must precede executable implementation**

Reconcile affected current specifications and freeze the implementation contract before code mutation. Exact version numbers remain a D4 choice, but current generations must advance wherever old payloads could authorize a materially different method. Cover at least:

1. `PostSelectionMethodIdentity` / P5 preparation-policy generation with no whole-P3-common-training dependency;
2. disposition of `TrainingProtocolIdentity` and the generic DATA8 spec so stale P5 prose cannot authorize restored P5;
3. mode-specific MACE loss/execution realization without flipping a P3-wide loss constant or blanket-staling P3 evidence;
4. MACE source-probe generation only if additional evidence fields are required; adding P5-specific probe evidence alone does not imply changed P3 semantics;
5. CV fold/plan/run-plan generation removing selected-only checkpoint-monitor fields and adding common-monitor record digest / relation-separation ancestry;
6. final-production plan/publication generation removing P5 `m3_evaluation_size` / `m3_membership_digest` ancestry and defining common-monitor-based single-best ranking;
7. common target-monitor policy/record generation with neutral parent identity, exact-256 fail-closed target semantics, exact D2 member ordering/evidence, and historical DATA5 read-only behavior;
8. MLCV run-monitor/catalog generation for shared target membership while preserving replay products and current target-light=`M_mon` simplification;
9. current P5 materialization/runtime evidence generation;
10. fitted P5 preparation / atomic-reference transfer-evidence generation sufficient to bind required compositions and transfer result, with no inert fitted configuration-weight identity for foundation modes; and
11. restart/currentness stamps that invalidate old stress/fold-local/M3-P5/from-scratch-E0/target-first/missing-transfer artifacts while preserving unrelated P3 evidence.

D4 specifications must distinguish the two DATA8-era representations: the broad historical/general `Data8PreparationBundle` / `TrainingProtocolIdentity` contract and the newer current P5 `PostSelectionMaterialization` path. Do not force restored P5 back through the older representation merely to avoid updating stale specification text.

Public/config contract:

- no new corpus-order knob; current two-head order is fixed by D2;
- no separate energy/force/stress Huber-delta knobs; one numeric `huber_delta` retains property-specific dimensional interpretation;
- foundation P5 resolves fixed accepted UniversalLoss `1:10:1` independently of P3 `[objective]` / `[weighting]` configuration; legitimate P3 overrides do not become P5 method fields;
- if a dedicated current P5 field attempts to change accepted `huber_delta`, E:F:S coefficients, corpus order, or distributed exposure, fail closed / require upstream revision rather than silently execute a different method;
- an explicitly incompatible foundation `fit_mode` fails with an actionable error rather than being overridden;
- retired training-head scalar fields fail closed in current config;
- canonical single-source replay omission resolves TRUE_DFT; any still-current legacy split-file route with ambiguous omitted label semantics fails closed rather than silently defaulting pseudo, while explicit historical pseudo compatibility remains readable where supported;
- historical fold-monitor/monitor-parent/M3-P5 schemas may remain readable only as historical provenance and cannot authorize current execution;
- one authoritative P5 fold-default resolver yields 3, with explicit `K>=2` override;
- foundation-P5 distributed execution is rejected until separately qualified; and
- insufficient exact monitor support, protected relation separation, or E0 composition transfer is typed infeasibility, not a fallback path.

**Acceptance:** D4 handoff is specific enough that two independent implementers would produce the same externally visible schemas/failure behavior/currentness semantics while remaining free on private helper decomposition.

### Implementation Stage A — method/exposure/config/identity cutover

After G1A/G1B PASS, implement G2, G3, G3A, G8, G9 and the method/exposure portions of G10 as one coherent stage. Run focused tests plus affected regression before proceeding.

### G2 — Restore mode-specific native UniversalLoss realization

- Remove only the foundation-adaptation UniversalLoss->stress source mutation.
- Keep source qualification, restart/CUDA/precision/runtime repairs and P3 complete-batch patch.
- **Do not change the global weighted-path `MACE_EXECUTABLE_LOSS_FAMILY` to `universal`.** Narrow/rename it if needed, but P3/P5-scratch accepted weighted paths must remain unchanged.
- Resolve P5 executable loss through the existing `PostSelectionMethodIdentity` + MACE seam by training mode.
- Multihead replay allows native MACE UniversalLoss and verifies resolved class/parameters.
- Naive foundation fine-tuning explicitly requests UniversalLoss when native routing would not.
- Foundation modes realize fixed D2 values `huber_delta=0.01`, E:F:S `1:10:1`; they do not inherit P3 `[objective]` values.
- Preserve and verify `force_mh_ft_lr=true` and `real_pt_data_ratio_threshold=0.0` for multihead replay.
- Bind numeric delta/EFS/conditional-force semantics, full nine-entry stress reduction, binary-mask placement, and canonical dimensional interpretations `0.01 eV/atom`, `0.01 eV/Angstrom`, `0.01 eV/Angstrom^3` without creating three config knobs.
- Preserve current two-head `pt_head`/replay-first then target-second pre-shuffle combined index layout and qualify it through the existing source-probe/execution-semantics owner.
- Verify current single-process `drop_last=true` exposure for **both** multihead replay and naive fine-tuning; do not apply the P3 complete-batch rule to foundation P5.
- Reject distributed foundation-P5 execution until global reduction/exposure/optimizer equivalence is independently accepted.
- If SWA/another phase can change loss coefficients/family, prove it disabled or bind/qualify that trajectory-changing behavior.
- Advance a P5-specific method/execution generation rather than globally invalidating unchanged P3 merely because shared source files changed.

**Acceptance:** real pinned parser + `get_loss_fn()` + training path execute accepted foundation-adaptation loss; LR/EMA are not silently mutated; ordered exposure and drop-last geometry match D2 for both foundation modes; P3/scratch weighted paths remain unchanged; no custom loss/sampler exists.

### G3 — Remove inert P5 configuration weighting, retire head scalars, and decouple P3 policy

- Stop fitting/binding `ConfigurationWeightPolicy` in restored UniversalLoss foundation P5.
- Preserve general configuration-weight owners for P3/P5 scratch/other methods that consume them.
- Neutralize `config_weight=1.0` only when transport requires the key.
- Remove current foundation-P5 fitted-weight records/digests if they have no executable/scientific effect; do not preserve an inert `fitted_weights_digest` solely for schema continuity.
- Preserve binary property masks.
- Replace whole `TargetSizeCommonTrainingPolicy.content_digest` in `PostSelectionMethodIdentity` and current foundation-P5 fitted preparation with a P5-specific policy projection assembled from real component owners.
- P3-only objective, configuration-weight, and harness changes must leave foundation-P5 method identity unchanged; true P5 loss/foundation/replay/optimizer/checkpoint-policy changes must invalidate it.
- Remove live `target_head_weight`, `replay_head_weight`, and equivalent `target_weight`/`head_weight` semantics from current config, replay preparation, cache identity, materialization, and evidence.
- Current configs specifying retired scalars fail closed with a removal/migration error.
- Historical payloads may remain readable but cannot authorize current P5.

### G3A — Preserve TRUE_DFT replay default without legacy ambiguity

- Preserve the already-current canonical single-source rule: replay source + omitted `label_mode` resolves `TRUE_DFT`.
- Pseudo-label replay requires explicit opt-in and an independent TRUE_DFT replay monitor.
- Audit legacy split-file selectors still reachable from current P5. If their omitted mode is ambiguous, require an explicit accepted legacy mode rather than defaulting to `external_pseudolabel`.
- Keep explicit historical `external_pseudolabel` compatibility where supported; do not reinterpret historical payloads as true-label data.
- Switching TRUE_DFT versus pseudo over the same authenticated source/split must preserve exact replay geometry membership and split lineage.

**Acceptance:** no current omission path silently selects pseudo replay; explicit pseudo still works with TRUE_DFT monitor; replay geometry identity is label-mode invariant.

### G8 — Restore CV default three

Change one authoritative current P5 default 5 -> 3; reconcile config/spec/guide/tests; preserve `K>=2`, override, all-required-fold/seed semantics, and current seed population; prove retired DATA5 K=3 authority was not reactivated.

### G9 — Preserve adaptive-stop/checkpoint score semantics

Preserve current `target_score_weight`, `replay_score_weight`, matched foundation replay baselines, signed replay degradation, and default 30 meV/Angstrom degradation budget unless separately changed by accepted authority. Retirement of training-head weights must not alter these policies. For the current 256/256 target-light/full setting, target-side stopping consumes the same `M_mon` membership rather than a separately sampled target parent.

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
- Evaluate `c^T v = 0` for every required composition and every unanchored null direction at the accepted rank tolerance, accounting only for explicitly accepted, identity-bound anchors. Do not invent an absent-element prior in D4.
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

Implement G5-G7 and G6 as one topology stage. Stage-local regression must cover historical-read/current-reject behavior, exact monitor reconstruction, cross-role relation proof, identical monitor-plan lineage, outer/purge membership preservation, and complete P5 M3 retirement.

### G5 — Move common target sampler onto current neutral authority

- Reuse/refactor the existing balanced condition/run/time systematic sampler; do not create another sampler.
- Parent target membership from current `NeutralStatisticalBase` / `NeutralOuterPartition` `OuterRole.OUTER_MONITOR` plus canonical frame authority.
- Form the exact sampler parent by canonical target-label usability first. Do not filter by target relation collisions before sampling, because that would change the D2 sampler population.
- Reproduce the D2 quota-order marker and tie rule exactly: sort strata by `(SHA256(<q>\0quota\0<s>), s)`, then systematic source-time positions with seed `161803`.
- Require exact requested/realized target count 256. Parent support below 256 is typed P5 infeasibility.
- After exact membership is fixed, prove exact and protected-relation separation from every configured relevant `T_N` through canonical P1 cross-role relation authority. A collision is infeasible; do not delete, replace, or resample conflicting members.
- Persist/bind exact ordered monitor membership sufficiently to reconstruct `(run_id, source_frame_index, frame_uid)` and per-stratum available/selected counts from the immutable parent.
- Keep monitor membership identity independent of selected-size identity; bind separation evidence at P5 plan admission.
- Remove current P5 dependence on `data5_bundle.outer_partition_for_domain(label_domain_id)` and legacy `parent_role=data5_outer_monitor` identity.
- Advance target-monitor record/policy generation as needed. Historical DATA5 target-monitor records remain read-compatible historical provenance only.
- Bind only target-monitor policy projection into P5 method identity; do not couple P5 method identity to replay/training-diagnostic monitor budgets.
- Review public exports; do not silently repurpose a legacy API to mean a new parent contract.

### G6 — Collapse CV/final target-monitor topology and retire P5 M3 ancestry

- Advance CV policy/fold/plan and MLCV target-monitor generations.
- Remove `checkpoint_monitor_components_per_fold` and selected-only monitor fields from current fold semantics.
- Preserve exact existing outer-fold and purge algorithms; all remaining selected components become gradient training.
- Build/publish one immutable common-monitor record and make **every sibling CV plan bind the same record digest**.
- `FinalProductionPlan` must bind that same common-monitor record digest plus accepted CV ancestry; it must not bind `m3_evaluation_size` / `m3_membership_digest` as P5 ancestry.
- Retire fold/final target-full parent construction in `mlcv_monitors.py`; for the current 256/256 setting, target-light equals target-full/common `M_mon` without a target-side resampler.
- Retire **M3 as final-production checkpoint monitor and as final-seed publication ranking evidence** while preserving M3 itself as P3 evidence.
- Update `FinalProductionPublicationDecision` and its seed evidence/currentness so `single_best_final_seed` uses each already-frozen representative's authenticated common-monitor target metric. `all_qualified_final_seeds` does not rank seeds.
- If deployment/qualification still needs an M3 development probe, route it from the P3 target-size evidence owner; do not keep P5 publication tied to M3 for that convenience.
- Preserve replay full/light monitoring and training diagnostics.
- Reconcile current P5 materialization target-monitor artifacts accordingly.

**Acceptance:** no current P5 path can construct/authorize a fold-local, final-specific, or M3 target checkpoint parent; no current P5 plan/publication/currentness digest depends on M3; selected fold accounting is exactly train + outer-evaluation + purge; every CV/final plan binds the same common monitor record; final single-best ranking uses only frozen common-monitor representative evidence.

### G7 — Qualify actual protected monitor parent and separation

Produce actual LTA evidence with at least:

```text
neutral statistical-base / outer-partition digests
accepted NeutralLeakageReport disposition
P1 split-exclusion evidence digest
OUTER_MONITOR label-usable parent unit/frame counts
condition/run IDs represented
available -> selected counts per condition/run
source-time span/systematic positions
canonical label/property completeness for checkpoint metrics
requested count = 256
realized count = 256
monitor membership digest / ordered member lineage
exact overlap with every configured T_N and T_selected
cross-role split-exclusion-component overlap with every configured T_N and T_selected
relation-separation evidence/parent digest bound by plans
```

Do not invent a new generic minimum-run/unit constant. Do not treat `NeutralLeakageReport` as proof of cross-run duplicate/replica/structural-lineage separation when it does not test that claim; use canonical P1 relation authority as well. Do not use selected-only `SelectedRelationProjection` alone for monitor-versus-target relation proof.

**Acceptance:** exactly 256 realized from the exact label-usable parent; zero exact/protected-relation leakage; labels usable; diversity/coverage evidence recorded; every sibling CV/final plan binds the same common-monitor record and valid current separation ancestry. Any inability to realize exact 256 or required separation/label usability yields P5 infeasible and no DEVELOPMENT/shrink/resample fallback.

### Implementation Stage D — assembled currentness/runtime/docs/spec integration

Complete G10-G12 after Stages A-C. Reconcile all affected current documentation/specifications/generated views and then run final assembled real-owner integration/affected regression. Production-scale GPU qualification remains deferred.

### G10 — Method identity, runtime evidence, and restart/currentness cutover

Runtime evidence records at least:

```text
training role/mode
P5 method identity / P5 preparation-policy digest
foundation checkpoint + selected head identity
loss family/class + numeric UniversalLoss parameters
canonical energy/force/stress residual units + dimensional Huber threshold interpretation
nine-entry stress reduction / conditional-force regime identity
binary property-mask policy
E/F/S coefficients
atomic-reference fit mode + fit membership/input/result digests
rank/singular/null-space/rank-tolerance + accepted anchor identity
required composition-set digest + composition-transfer result
target/replay membership digests and counts
combined count/head counts
ordered pre-shuffle layout = replay/pt_head then target
shuffle/sampler seed and policy
single-process execution identity
batch size / drop_last / batches per epoch
force_mh_ft_lr / real_pt_data_ratio_threshold / realized duplication factor
LR / EMA / precision / backend
common target-monitor parent/policy/record/membership digest + exact count 256
plan-level protected-relation separation evidence
replay monitor lineage
fold train/eval/purge membership
method/CV/final/run-plan digests
final publication metric lineage = frozen common-monitor representative target metric
```

Advance existing generations as needed at the **narrowest real owner**. Old stress/fold-local/M3-P5/from-scratch-E0/target-first/missing-transfer foundation checkpoints, P5 materializations, monitor catalogs, and verdicts fail currentness before execution/restart reuse. Old `TrainingProtocolIdentity` or generic DATA8 records cannot authorize restored P5 merely because they deserialize. Preserve independent P1/P2/P3/T_selected evidence; a P5-specific generation change must not automatically stale unchanged P3 runtime evidence.

### G11 — Counterfactual falsification matrix

At minimum falsify:

1. identity says UniversalLoss but foundation-P5 runtime resolves stress;
2. a global loss-constant change makes P3 resolve UniversalLoss or otherwise changes P3 objective;
3. runtime UniversalLoss numeric delta/EFS/conditional-force semantics differ;
4. stress reduction uses six independent components rather than all nine stored Cartesian entries;
5. binary property-mask placement or force `100/200/300` regime behavior differs from D2;
6. residual units or dimensional Huber interpretation differs while numeric `0.01` is unchanged;
7. D4 invents separate live energy/force/stress delta knobs;
8. legitimate P3 `[objective]` / `[weighting]` change incorrectly changes foundation-P5 method identity;
9. true P5 loss/foundation/replay/optimizer/checkpoint-policy change fails to invalidate P5 identity;
10. P5 still fits/binds nontrivial `ConfigurationWeightPolicy` or inert fitted-weight digest;
11. non-neutral `config_weight` affects restored foundation-P5 trajectory/identity;
12. current config accepts retired target/replay head scalars;
13. replay materialization still applies head-scalar weighting;
14. canonical replay omission does not resolve TRUE_DFT;
15. a still-current legacy omitted replay mode silently defaults pseudo rather than failing/being explicit;
16. TRUE_DFT versus pseudo changes replay geometry split;
17. foundation-adaptation resolves `FROM_SCRATCH_TOTAL_ENERGY`;
18. residual mode runs without exact selected-head foundation predictions/reference E0s;
19. residual E0 fit sees monitor or held-out labels;
20. selected foundation head differs from head used for foundation predictions/E0s;
21. rank-deficient `[1,1]` manifold incorrectly rejects required `[1,1]` transfer;
22. same null space incorrectly accepts required `[2,1]` transfer;
23. absent required element passes without an accepted anchor;
24. minimum-norm/zero fallback is treated as identification;
25. pinned multihead `pt_head` silently uses first/wrong foundation-head E0s;
26. target monitor still consumes legacy DATA5/label-domain authority;
27. target monitor realizes fewer than 256 frames but execution continues;
28. target sampler filters relation-conflicting frames before sampling, deletes/replaces a conflicting sampled member, or resamples instead of failing;
29. target sampler quota-order/tie/systematic-position semantics differ from D2;
30. common-monitor membership record identity incorrectly depends on one selected size rather than neutral parent/policy;
31. common-monitor relation proof uses selected-only projection and misses a monitor-target cross-role relation;
32. sibling CV plans bind different common-monitor record digests;
33. final plan binds a monitor record different from accepted CV;
34. current MLCV still builds fold/final target checkpoint parents or independently resamples target-light 256;
35. common monitor is copied into fold-selected membership rather than external lineage;
36. monitor overlaps or is split-exclusion-related to any configured `T_N`;
37. monitor labels are unusable/incompatible for checkpoint metrics;
38. score/replay-retention weights are deleted with training-head weights;
39. default K falls back to five through another resolver;
40. legacy DATA5 K=3/role-budget semantics become current;
41. MACE target duplication occurs;
42. `force_mh_ft_lr` is false/absent or LR/EMA are mutated;
43. multihead foundation P5 sampler/drop_last differs from accepted exposure identity;
44. naive foundation P5 retains a final partial batch or otherwise differs from accepted `drop_last=true` geometry;
45. distributed foundation P5 is admitted without an accepted equivalence qualification;
46. target/replay memberships and seed are unchanged but target-first pre-shuffle ordering authenticates as current;
47. P3 complete-batch semantics change accidentally;
48. precision/backend changes without identity/evidence change when numerically material;
49. old incompatible checkpoint resumes as current restored run;
50. stale weighted-stress or old `TrainingProtocolIdentity` CV evidence authorizes restored final production;
51. P5 method identity or fitted preparation still binds whole `TargetSizeCommonTrainingPolicy.content_digest`;
52. final production/publication still binds M3 or evaluates M3 to choose final seed;
53. downstream deployment M3 probe forces M3 back into P5 plan/publication identity rather than consuming P3 evidence directly;
54. an execution-only field incorrectly invalidates scientific method identity;
55. a P5-only execution-token bump globally stales unchanged P3 evidence without a real P3 semantic change; and
56. a true method field fails to invalidate dependent P5 evidence.

Every case is rejected by a real owner or documented inapplicable with evidence.

### G12 — Real-owner assembled qualification

Exercise the real path:

```text
campaign config
 -> accepted D1/D2-conforming P5 resolver
 -> single PostSelectionMethodIdentity / P5 preparation-policy projection
 -> foundation/head identity + residual-E0 inputs
 -> composition-transfer feasibility owner
 -> neutral exact-256 common-monitor membership record
 -> cross-role P1 separation evidence
 -> sibling CV plans all binding the same common-monitor digest
 -> target/replay materialization
 -> parser-facing MACE config
 -> source-qualified mdstats MACE seam
 -> pinned MACE 0.3.16 UniversalLoss for foundation modes
 -> head-qualified E0 realization
 -> replay/pt_head-first native combined loader or naive target-only loader
 -> single-process optimizer update
 -> TRAIN2 persistence/restart evidence
 -> adaptive stop/checkpoint evidence on common M_mon
 -> held-out EVAL2 for CV only
 -> fresh final-production representative path using same M_mon
 -> final publication decision with no M3 P5 ancestry
```

Also exercise the unaffected-control paths:

```text
P3 target-size execution remains weighted + complete-batch
P5 scratch remains on its separately accepted weighted method
M3 downstream qualification probe, if retained, resolves from P3 owner only
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
- DATA8/MACE realization specification, explicitly distinguishing current P5 `PostSelectionMaterialization` from broad/historical `TrainingProtocolIdentity` representation;
- post-selection CV/final plan/run schema specification, including common-monitor digest and no P5 M3 ancestry;
- online/common-monitor and MLCV monitor specifications;
- atomic-reference/P5 fitted-preparation specification including composition-transfer evidence;
- adaptive-stop/checkpoint specification;
- final-publication specification/semantic history for common-monitor-based single-best ranking;
- campaign CLI/config specification and guide, including canonical TRUE_DFT default and legacy ambiguity behavior;
- README/example config where user-visible defaults or retired fields are represented;
- public exports for advanced/replaced schema or policy families; and
- semantic history explaining the weighted-stress/fold-local/M3-P5/head-scalar/from-scratch-E0/target-first/whole-P3-policy lineage replacement.

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
26. `TrainingProtocolIdentity` remains broadly specified/exported while newer P5 uses `PostSelectionMethodIdentity`/`PostSelectionMaterialization`; current P5 authority must be singular and the older identity explicitly scoped away from restored P5.
27. `PostSelectionMethodIdentity` and `PostSelectionFittedPreparation` still bind `TargetSizeCommonTrainingPolicy.content_digest`; deleting weight execution without deleting that identity coupling would leave P3-only fields as false P5 currentness parents.
28. Exact common-monitor membership is currently an argument, not an authenticated common plan ancestor; every sibling CV/final plan must bind the same immutable monitor-record digest.
29. Current final publication still authenticates M3 and uses M3 metrics to select final members; accepted P5 authority leaves M3 as P3 evidence, so final P5 seed ranking must use frozen common-monitor representative metrics.
30. Current global `MACE_EXECUTABLE_LOSS_FAMILY="stress"` serves P3 and P5; a global flip would fix one layer by breaking another. Loss routing must be mode-specific at the existing MACE seam.
31. Shared execution-semantics/source-probe revisions must follow dependency impact: P5-only semantics do not justify blanket P3 invalidation.
32. The common monitor sampler and relation-separation check have a strict order: sample exact D2 membership from label-usable `OUTER_MONITOR`, then fail on relation collision; do not relation-filter/resample into a different method.
33. Selected-only relation projection cannot prove cross-role monitor/target separation because it intentionally excludes outside frames.
34. Current target-light and target-full budgets are both 256, so retaining a second target sampler would be needless duplicate machinery; current target-light can equal `M_mon` exactly.
35. Canonical single-source replay already defaults TRUE_DFT, but legacy split-file compatibility still needs explicit disposition so an omitted legacy mode cannot silently restore pseudo as a current default.
36. Current accepted foundation-P5 exposure is single-process and `drop_last=true` for both multihead and naive modes; distributed or P3-style complete-batch substitution is a different D2 method.
37. Generic P3 `[objective]` / `[weighting]` settings must be decoupled, not globally rejected: restored foundation P5 has its own fixed accepted objective while P3 remains configurable under its own authority.
38. M3 may remain useful as a downstream deployment-equivalence probe, but that does not justify retaining M3 inside P5 plan/publication identity; route the probe through P3 authority.

## 14. Reopen conditions

Reopen D1/D2 rather than adding D4 compensation if evidence shows:

- UniversalLoss cannot express the required foundation-adaptation objective;
- nontrivial P5 configuration weighting is required;
- accepted replay-first native combined-loader exposure is scientifically unacceptable;
- property-specific dimensional Huber semantics cannot be preserved by the execution dependency;
- the protected neutral `OUTER_MONITOR` parent cannot provide exact 256 relation-clean checkpoint evidence for the intended method;
- the composition-level E0 transfer rule itself is scientifically inadequate rather than merely unimplemented;
- a distinct final-seed ranking cohort other than the accepted common target monitor is scientifically required;
- P3/P5 cannot legitimately use different loss/exposure methods for the intended conclusions;
- TRUE_DFT replay still causes material forgetting after correct restoration; or
- target/replay acceptance gates are scientifically incompatible with the restored method.

Foundation-residual E0 failure caused by current wiring or missing transfer validation remains a D4 blocker while accepted D1/D2 is coherent. Reopen D3 if one accepted method still requires competing durable owners, if `TrainingProtocolIdentity` and `PostSelectionMethodIdentity` cannot be cleanly scoped without dual P5 authority, or if the current owner graph cannot represent external common monitor/transfer-validation lineage without cycles. Local implementation defects under coherent D1-D3 remain D4 repairs.

## 15. Closeout

Close only after:

1. accepted branch D1/D2 remain independently reviewed and ratified;
2. D3 architecture amendments are independently reviewed and contain one coherent foundation-adaptation loss/exposure/E0-transfer/monitor/final-publication/currentness flow;
3. D4 specifications are frozen before code and current schema/failure/currentness behavior is explicit;
4. restored P5 has one method authority and one current materialization/evidence path; `TrainingProtocolIdentity` has no competing current P5 authority;
5. P5 method/preparation identity no longer binds whole P3 common-training policy or inert foundation-P5 configuration weights;
6. every sibling CV/final plan binds the same exact common-monitor record and valid protected-relation separation evidence;
7. P5 final production/publication has no M3 checkpoint/ranking/currentness ancestry; any retained downstream M3 probe resolves from P3 authority;
8. D4 code/config/public API/tests realize the contract with no inert current fields or parallel owners;
9. exact 256 monitor behavior, composition-transfer E0 feasibility, dimensional Huber semantics, replay-first stochastic exposure, naive/multihead drop-last geometry, and current single-process restriction are covered by real-owner evidence;
10. affected old evidence is stale only where materially dependent while independent P1/P2/P3/selection evidence remains usable;
11. semantic history explains replacement of weighted-stress/fold-local/M3-P5/head-scalar/from-scratch-E0/target-first/whole-P3-policy lineage and the composition-transfer correction;
12. closeout learning/PEM is reconciled only where admission criteria are met; and
13. the plan is archived only after still-current semantics reside in accepted integrated authority.

Central closure invariant:

```text
accepted P5 scientific method
 = accepted P5 numerical method
 = accepted D3 owner/control topology
 = single recorded PostSelectionMethodIdentity
 = authenticated foundation/head + target/replay/common-monitor lineage
 = identical common-monitor record in every CV/final plan
 = authenticated residual-E0 + composition-transfer result
 = actual pinned-MACE mode-specific loss/units/replay-first-loader realization
 = TRAIN2/restart evidence
 = checkpoint/held-out-EVAL2 interpretation
 = final publication decision with common-monitor metric and no P5 M3 ancestry
```

No current setting may change recorded method identity without changing governed execution, change governed execution without changing recorded identity, remain current while having no executable/scientific effect, or invalidate an unrelated upstream method merely because implementation storage/source files are shared.
