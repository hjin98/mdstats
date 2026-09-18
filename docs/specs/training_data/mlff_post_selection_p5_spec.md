# MLFF post-selection P5 current specification

**Status:** proposed renewed D4 contract; implementation blocked until the accompanying D3 architecture candidate passes independent Review  
**Upstream authority:** ratified D1, stakeholder-ratified D2 target `32508991d472c1c6e4bd8b818b38d0880401845f` / D2 blob `30e6e6336cf41a05879650a3a2d7d583c4ef713a`, and the accompanying D3 MLFF training-data architecture candidate  
**Scope:** current P5 only; P3 target-size screening and P5 scratch retain their separately accepted contracts


## 1. Purpose

This specification freezes the D4 contract required to implement the accepted replay-retention/target-admissibility numerical semantics through the proposed D3 ownership cutover. It reuses current P5 owners and removes policy-overbinding rather than adding a parallel trainer, evaluator, policy graph, evidence store, or compatibility registry.

The post-cutover authority chain is:

```text
TargetBinding + training-only PostSelectionMethodIdentity + training-bearing parents
  -> TrainingTrajectoryIdentity
  -> PostSelectionFittedPreparation
  -> PostSelectionMaterialization
  -> TRAIN2 runtime/checkpoints
  -> sealed training root

checkpoint/model + exact evaluation evidence
  -> EvaluationMeasurementIdentity
  -> immutable target/replay measurements

role assessment plan + hard decision policy + strict P5 selection identity
  -> complete checkpoint assessments
  -> representative
  -> CV/final assessment
  -> publication

replay warning policy + replay measurement
  -> diagnostic evidence only
```

`TrainingProtocolIdentity` is not current P5 authorization. Historical DATA8 payloads remain provenance only. A current role-plan digest is not a training-root or numerical-measurement identity merely because pre-cutover schemas used it that way.

## 2. Current training modes

Current post-selection training modes are semantically disjoint:

```text
scratch
naive_fine_tuning
multihead_replay
```

This specification's restored foundation-adaptation requirements apply to `naive_fine_tuning` and `multihead_replay`.

P5 scratch retains its separately accepted weighted/from-scratch method. P3 target-size screening retains its accepted weighted objective and complete-batch exposure. No foundation-P5 repair may globally change either.


## 3. `PostSelectionMethodIdentity` and training-trajectory identity

`PostSelectionMethodIdentity` remains the sole current P5 training-method identity. Advance its schema generation because pre-cutover schema v3 over-binds assessment-only checkpoint constraints/selection policy.

It SHALL bind only method-bearing trajectory-generating inputs, directly or through named component-policy digests:

```text
method recipe generation
training mode
foundation checkpoint + selected foundation head when applicable
foundation-P5 objective identity
P5 atomic-reference/preparation-policy identity
learning-rate schedule
optimizer settings
replay training-label/exposure policy
extended-XYZ training transport policy
MACE architecture/model-feature identity
checkpoint interval
model dtype
execution device/backend identity where numerically method-bearing
accepted single-process foundation execution identity
```

It SHALL NOT bind `delta_warn`, `delta_hard`, `tau_CV`, `theta_CV`, `tau_prod`, checkpoint admissibility classification, D2.DEF.059A/059B selection identity, CV verdict policy, or publication policy.

For foundation modes the fixed objective remains:

```text
loss_family   = universal
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

D4 SHALL continue the accepted dimensional interpretations and SHALL NOT expose three independent delta knobs.

Define one current role-specific `TrainingTrajectoryIdentity`/digest as the canonical projection of every input capable of changing exact TRAIN2/materialization/restart behavior. It SHALL include at least:

```text
run role and exact gradient/replay-training membership
optimizer seed and planned horizon
training-only PostSelectionMethodIdentity
foundation checkpoint/head and replay-training lineage
fitted/prepared training-state identity
objective/loss, exposure/corpus order, optimizer/LR
precision/backend/model architecture
checkpoint cadence and MACE execution semantics
trainer-consumed validation/preparation artifacts
common-monitor identity when preparation/runtime consumes it
composition-transfer required-composition set
```

Assessment-only inputs SHALL be absent. New run/checkpoint roots and continuation identity derive from `TrainingTrajectoryIdentity`, not the full CV/final assessment plan.

For one-time historical reuse, the existing recovery/currentness owner may prove one legacy schema-v3 method/run lineage training-equivalent by exact comparison of all training-bearing fields while excluding only the retired assessment-only parents. This is a bounded source-preserving derivation, not a general compatibility translator or alias registry.

## 4. P5 preparation-policy identity

Current P5 SHALL expose a preparation-policy identity distinct from `TargetSizeCommonTrainingPolicy.content_digest`.

For foundation modes that identity SHALL bind the selected-head foundation-residual E0 method and accepted composition-transfer policy. It SHALL NOT bind P3 `objective_policy`, P3 configuration-weight fitting policy, P3 candidate-screening controls, or other P3-only harness fields.

For scratch, the representation may bind its separately accepted from-scratch/weight-bearing preparation policy.

A shared implementation type is permitted only if its content identity is mode-disjoint and fail-closed.

## 5. `PostSelectionFittedPreparation`

The current foundation-adaptation fitted-preparation representation SHALL expose these invariants:

```text
training trajectory / training-position ancestry  required
preparation kind / training mode             explicit and authenticated
P5 preparation-policy digest                 required
exact fit membership + membership digest     required
atomic-reference fit record/result           required
selected foundation checkpoint/head          required
foundation prediction/reference-E0 identity  required
required composition-set digest              required
rank/null-space/tolerance/anchor evidence     required
composition-transfer result                  required
```

The role training position is established before fitted preparation. A current fitted preparation binds `TrainingTrajectoryIdentity` together with the common-monitor and required-composition transfer ancestry actually consumed by preparation/runtime. It SHALL NOT bind checkpoint-decision, warning, outer-acceptance, representative-selection or publication policy merely because the role assessment plan carries those coordinates. Its digest is then bound by `PostSelectionMaterialization` and TRAIN2 runtime evidence.

The following are forbidden as current foundation-P5 preparation parents or payloads:

```text
TargetSizeCommonTrainingPolicy.content_digest
P3 objective_policy payload
nontrivial ConfigurationWeightPolicy identity
fitted configuration-weight table
fitted_weights_digest
frame-weight table
```

unless a future accepted D1/D2 method explicitly consumes such fields.

The fixed foundation UniversalLoss objective belongs to `PostSelectionMethodIdentity`/its method-policy projection and executable MACE evidence, not to a P3 `objective_policy` field in fitted preparation.

If scratch and foundation modes share one dataclass/schema, it SHALL be tagged and mode-disjoint:

- scratch may carry its separately accepted weight-bearing/from-scratch fields;
- foundation may carry only shared ancestry plus residual-E0/transfer fields;
- a field forbidden for a mode SHALL cause current-schema validation failure if populated;
- forbidden cross-mode fields SHALL NOT be silently defaulted, ignored, or included in current content identity; and
- historical weight-bearing foundation payloads SHALL remain historical even when readable.

## 6. Foundation-residual E0 execution and transfer

The existing atomic-reference fitter is the only E0 solver.

For foundation modes:

1. resolve the exact selected foundation checkpoint and selected head;
2. obtain target-head foundation predictions/reference E0 inputs from that exact identity;
3. fit residual elemental corrections using only authorized gradient-training labels;
4. persist numerical-rank evidence at the accepted tolerance;
5. determine the unanchored null space after any already-accepted identity-bound anchors;
6. derive every governed target composition class whose energy is consumed by training, common-monitor checkpoint control, or held-out evaluation; and
7. require `c^T v = 0` for every governed composition vector `c` and every free null direction `v`.

For final production, the fit domain is complete exact `T_selected`; for CV it is the fold-authorized gradient-training membership.

Common-monitor and held-out geometry/composition counts may be inspected for transfer feasibility. Their labels SHALL NOT enter the E0 fit.

The exact common-monitor record SHALL exist before a current foundation-P5 fitted preparation/materialization/run can authenticate, because common-monitor composition classes are governed transfer consumers. Manufactured/test composition sets are test oracles only and cannot authorize a current run.

Minimum-norm output, arbitrary zero coefficients, another fold's solution, or a different foundation head do not create transfer identifiability.

## 7. Mode-specific MACE realization

The existing MACE adapter is the one dependency-facing execution seam. It SHALL resolve loss by authenticated training mode.

### 7.1 P3 and P5 scratch controls

P3 target-size screening remains on its accepted weighted objective and complete-batch path. P5 scratch remains on its separately accepted weighted method.

A global `MACE_EXECUTABLE_LOSS_FAMILY` flip to UniversalLoss is forbidden because it would change unaffected method families. If the existing constant is retained, it SHALL be scoped/named so that it cannot claim foundation-P5 authority.

### 7.2 Foundation P5

`naive_fine_tuning` and `multihead_replay` SHALL realize pinned MACE native `UniversalLoss` with the fixed values in section 3. mdstats SHALL not implement a replacement loss, residual pre-scaling trick, square-root weight trick, sample duplication, or second loss engine.

Runtime evidence SHALL authenticate the resolved native loss class and parameters after all pinned-MACE mutation regions.

General `config_weight`/`ref.weight` is neutral transport only for foundation UniversalLoss and SHALL not be a nontrivial scientific/identity layer. Local `config_energy_weight`, `config_forces_weight`, and `config_stress_weight` remain binary property-availability masks.

The native UniversalLoss numerical semantics SHALL match accepted D2, including conditional-force Huber regimes and nine stored Cartesian stress entries.

## 8. Foundation-P5 exposure contract

Current foundation P5 is qualified only for the single-process path.

### 8.1 Multihead replay

The authenticated pre-shuffle layout is fixed:

```text
replay / pt_head dataset || target dataset
```

Then native shuffle/sampler behavior is applied under the accepted seed.

Current execution SHALL bind and verify:

```text
force_mh_ft_lr = true
real_pt_data_ratio_threshold = 0.0
no implicit target duplication
no target/replay training-head scalar balancing
single-process sampler/process identity
batch size
drop_last = true
realized batches per epoch
ordered pre-shuffle corpus/head layout
```

Swapping target/replay block order under the same seed is a different method and SHALL not authenticate as current.

### 8.2 Naive foundation fine-tuning

Naive target-only foundation P5 uses the accepted shuffled `drop_last=true` geometry. It SHALL not inherit P3 complete-batch `drop_last=false` behavior.

### 8.3 Distributed execution

A distributed foundation-P5 route SHALL fail closed until a separately accepted D2-equivalence qualification exists.

## 9. Replay-label contract

The canonical single-source replay interface resolves omitted label mode to TRUE_DFT.

Foundation pseudo-label replay is explicit opt-in and requires an independent TRUE_DFT replay monitor.

A still-current legacy split-file route SHALL require unambiguous label semantics. Explicit supported historical pseudo/true modes may remain readable/executable where still supported; ambiguous omitted legacy semantics SHALL fail closed rather than silently defaulting pseudo.

Changing TRUE_DFT versus pseudo label mode over the same prepared source/split SHALL NOT change replay geometry membership.

### 9.1 Replay transport weights

Source or user replay weight metadata has no current foundation-P5 scientific authority. Every replay transport current foundation P5 hands to MACE - training and monitor views, single-source TRUE_DFT and foundation-pseudolabel, and every supported legacy split-file route - SHALL resolve at the MACE loader boundary to:

```text
config_weight         = 1.0
config_energy_weight  = 1.0 iff the rendered view carries a valid energy label, else 0.0
config_forces_weight  = 1.0 iff the rendered view carries valid force labels, else 0.0
config_stress_weight  = 1.0 iff the rendered view carries a valid stress label, else 0.0
```

The masks derive from the labels actually rendered into that view (for pseudo views, the pseudo stress payload), never from copied source metadata; absent stress stays absent with mask 0 and is not fabricated. The replay renderers owned by `replay.py`/`replay_pseudolabel.py` remove every inherited `config_weight`/`config_*_weight` value and write these masks; the transport field contract and weight policy (`mdstats.replay-transport-weights.neutral-binary-mask.v1`) are bound into the logical replay-view identity. A legacy split file consumed directly is never rewritten in place: replay inspection SHALL reject it before MACE when its MACE-resolved weights differ from the masks above, while a split used only as a geometry/order reference for true-label rematerialization is canonicalized in the derived view.

## 10. Common target-monitor policy and record

Current P5 target checkpoint control uses one campaign-common monitor record.

The monitor policy SHALL bind:

```text
neutral parent role = OUTER_MONITOR
requested size = exactly 256
seed = 161803
accepted D2 stratification/quota/ordering/systematic-selection algorithm
label-domain/label-usability requirements
```

The monitor record SHALL bind:

```text
parent identity/digest
policy digest
requested size = 256
realized size = 256
exact ordered selected frame identities/source indices
stratum/quota evidence required by D2
label-domain identity
exact content/membership digest
```

There is no current short-parent fallback. Fewer than 256 usable eligible frames is typed P5 infeasibility.

The sampler SHALL select exact membership from the label-usable neutral parent first. Protected-relation separation is checked afterward. A relation-conflicting sampled member SHALL cause failure; no deletion, replacement, relation-prefilter, or resampling is permitted.

The selected-only `SelectedRelationProjection` SHALL NOT be used as the sole proof of target-versus-monitor separation. Plan admission SHALL use canonical P1 relation authority capable of exposing cross-role relations between the realized monitor and every governed `T_N`.


## 11. CV policy, fold, training-position, and assessment schemas

The current default fold count remains exactly 3; explicit override requires `K >= 2`. `PostSelectionCvFold` membership contains only gradient training, held-out outer evaluation, and purge/exclusion evidence; no fold-local target checkpoint monitor is current.

A current CV role plan SHALL bind both projections explicitly:

```text
training projection:
  TargetBinding
  training-only PostSelectionMethodIdentity
  exact common-monitor / separation / preparation inputs consumed by training
  fold training membership
  replay training lineage
  seed + horizon
  -> TrainingTrajectoryIdentity

assessment projection:
  TargetBinding
  exact common-monitor record
  current hard checkpoint-decision policy digest
  fixed D2.DEF.059A strict-selection identity
  configured CV outer metric + theta_CV policy
  training_trajectory_identity
  fold/seed position
  -> CV assessment-plan digest
```

The warning-only replay policy SHALL NOT be an assessment-plan parent. Every sibling selected size/fold/seed in the campaign binds the same common-monitor record but has its own training/assessment position.

Held-out labels remain unavailable to fitting, checkpoint selection, adaptive stop, common-monitor construction, or final-publication ranking.


## 12. Checkpoint/adaptive-stop policy

### 12.1 Resolved hard and diagnostic policy

Advance the role-policy/checkpoint-policy generation. The default foundation values are:

| Coordinate | Foundation CV | Foundation production | Comparator / role |
|---|---:|---:|---|
| target checkpoint ceiling | `0.075 eV/angstrom` | `0.050 eV/angstrom` | inclusive binary64 `<=` |
| default-force CV outer threshold | `0.075 eV/angstrom` | n/a | inclusive binary64 `<=` |
| replay warning | `0.050 eV/angstrom` | `0.050 eV/angstrom` | strict binary64 `>`, diagnostic only |
| replay catastrophic hard limit | `0.100 eV/angstrom` | `0.100 eV/angstrom` | strict binary64 `>`, hard failure |

Scratch retains its separately accepted `0.030` target-threshold behavior.

`CheckpointAdmissibilityPolicy` SHALL contain the catastrophic replay hard limit, role-effective target checkpoint ceiling, TRUE_DFT requirement, finite/evidence-validity requirements, and existing physical/integrity hard gates. It SHALL NOT contain the replay warning threshold as a hard-decision parent.

The configuration owner resolves one replay policy family but exposes two dependency projections:

```text
hard replay decision digest -> delta_hard and hard descendants
warning diagnostic digest    -> delta_warn and warning/report descendants only
```

Recommended diagnostic/rejection codes are:

```text
replay_degradation_warning_threshold_exceeded
replay_catastrophic_forgetting_limit_exceeded
```

A checkpoint above the hard limit may carry both warning and rejection. Missing, stale, unauthenticated, incompatible, or non-finite required TRUE_DFT replay evidence remains a hard evidence failure independent of the numeric degradation value.

### 12.2 Role target resolution

For foundation modes:

```text
[post_selection.cv].checkpoint_maximum_target_force_rmse_ev_per_angstrom
  omitted/current default -> 0.075

[post_selection.cv].acceptance_metric
  default -> target_force_rmse_ev_per_angstrom

[post_selection.cv].acceptance_maximum
  omitted under default force metric -> 0.075

[acceptance].maximum_target_force_rmse_ev_per_angstrom
  omitted/current foundation-production default -> 0.050
```

An alternative outer metric keeps its accepted units/default resolver; it SHALL NOT import `0.075` merely because `acceptance_maximum` is omitted. Explicit values are preserved after migration and validation. Scratch fails closed if the foundation-only CV checkpoint field is configured.

Every public threshold value SHALL be finite and positive; replay requires `warning < hard` after canonical conversion. Booleans, strings/quoted numerics, NaN, infinity, and nonpositive values fail before identity construction/execution.

### 12.3 Complete checkpoint assessment and strict representative

Every governed durable P5 checkpoint SHALL receive required measurement/assessment. Hard-admissible checkpoints are ordered exactly by:

```text
(target force RMSE on M_mon, checkpoint epoch, lowercase checkpoint SHA-256)
```

The representative is the lexicographic minimum. Target RMSE is strict primary authority; replay warning/margin, secondary metrics, energy/stress diagnostics, maturity/refinement phase, practical-equivalence bands, bootstrap uncertainty, and historical score weights SHALL NOT override a lower finite target RMSE.

Quality-dependent candidate thinning is forbidden. If no hard-admissible checkpoint exists, persist the complete assessed candidate set and publish the typed no-admissible outcome.

The hard/selection assessment occurs only after authenticated TRAIN2. `_prepare_post_selection_run()` or its successor SHALL resolve replay execution from training method/replay lineage and SHALL NOT consult current checkpoint admissibility merely to decide training/replay runtime construction.


## 13. Final-production plan

A current final-production plan SHALL bind:

```text
TargetBinding identity
training-only PostSelectionMethodIdentity
TrainingTrajectoryIdentity projection for each seed
accepted current CV ancestry
exact common-monitor record + protected-relation evidence
current final hard checkpoint-decision policy digest
fixed D2.DEF.059A within-run selection identity
publication mode and D2.DEF.059B identity when single-best is requested
replay authority/monitor lineage where applicable
```

The replay warning diagnostic digest is not a hard-assessment or publication parent.

The following P5 plan parents remain retired: M3 evaluation size/membership, M3 checkpoint-monitor ancestry, and M3 seed-ranking ancestry.

A historically fresh completed final-production TRAIN2 trajectory may be reassessed under current policy without retraining only after current CV has been reclosed and accepted and exact training-semantic equivalence is proven. Current CV rejection blocks current final assessment/publication from that historical trajectory.


## 14. Final representative and publication contract

Each current final-production seed first freezes its representative under section 12.3.

### `all_qualified_final_seeds`

Publish all already-admissible required seed representatives. No cross-seed numerical ranking is performed.

### `single_best_final_seed`

Consume only already-frozen admissible seed representatives and their authenticated common-monitor target RMSE records. Choose the lexicographic minimum:

```text
(target force RMSE on M_mon, optimizer seed, lowercase checkpoint SHA-256)
```

The target RMSE coordinate is strict primary authority. Replay values/warnings, secondary metrics, maturity, practical-equivalence and bootstrap quantities SHALL NOT affect ordering. Seed and digest are consulted only after exact equality of canonical binary64 target RMSE.

Publication performs no second target evaluation and no M3 evaluation. The publication record SHALL bind the fixed ordering identity and the exact input representative/metric-record lineage needed to reconstruct the decision.


## 15. `PostSelectionMaterialization`, sealed training roots, measurements, and assessment evidence

Current materialization/TRAIN2 evidence SHALL bind the training trajectory rather than the full assessment plan. For foundation modes it includes at least:

```text
TrainingTrajectoryIdentity
training role/mode
training-only P5 method identity and preparation-policy digest
foundation checkpoint + selected head
resolved loss/objective + dimensional semantics
atomic-reference fit ancestry and composition-transfer evidence
target/replay training memberships and exposure order
optimizer/LR/EMA/precision/backend/model architecture
seed + planned horizon + checkpoint cadence
common-monitor / validation / transfer-consumer inputs actually consumed by preparation/runtime
generated MACE training configuration identity
checkpoint/runtime continuation ancestry
```

After authenticated terminal fixed-budget TRAIN2, while holding `post_selection_run_activity_lease()`, publish/reuse the existing typed topology manifest and completion anchor so the run root becomes a sealed training-only subtree. The terminal proof binds the authenticated `Train2RuntimeSummary` and exact checkpoint/runtime boundary and SHALL NOT require `fold-acceptance.json`, `run-evidence.json`, or any other assessment file.

Post-cutover EVAL2 and reassessment SHALL NOT write current assessment state into the sealed run root. They read root-dependent materialization/checkpoint bytes while holding `post_selection_run_activity_lease()` for the full numerical-read interval, then release it before publishing external immutable assessment objects. If the post-selection publication barrier is needed concurrently, acquisition order is run-activity lease then publication barrier.

### 15.1 Assessment-independent measurement records

Advance the target/replay measurement identity/schema wherever current role/prediction digests inherit a full run-plan ancestry. A current measurement record SHALL directly bind all numerically material inputs needed by D2.DEF.060B:

```text
exact checkpoint/model-state identity
exact evaluation artifact/membership and labels/reference values
metric name/definition/units/reduction/aggregation
model/head and prediction semantics
provider/evaluator realization
numerically material precision/backend semantics
```

Assessment thresholds, warning policy, strict-selection policy, CV/publication policy, and full assessment-plan digest SHALL NOT be measurement inputs. Historical records remain immutable. Reuse requires exact D2 measurement-equivalence proof; otherwise recompute EVAL2 from the preserved authenticated checkpoint/evaluation evidence.

### 15.2 Policy assessment records and complete candidate sets

Final production SHALL evolve the existing `PostSelectionRunEvidence` owner into one outcome-discriminated current assessment schema:

```text
training_trajectory_identity
current final assessment-plan / hard-decision / selection ancestry
outcome = representative_selected | no_admissible_representative
complete ordered candidate_record_digests
representative identity/checkpoint/record only for representative_selected
current monitor metric identity as required
```

The constructor SHALL enforce tagged outcome invariants. Every candidate assessment is durably published before the terminal outcome.

CV retains `CvFoldAcceptance` as the fold-assessment owner, but current records are external to the training root.

Extend the existing CampaignStore pointer seam with one position-addressed assessment locator. The canonical key is:

```text
selected_binding_digest
assessment_role = cv_fold | final_seed
current CV/final assessment-plan digest
training_trajectory_identity
optimizer_seed
fold_index for CV, absent for final seed
```

The value is the immutable current assessment-record digest. Existing selected-binding commit-time stale-generation fencing applies. Campaign-level CV-acceptance and final-publication pointers remain aggregate current authorities. Do not add a second pointer database, filesystem registry, content-store scan, or shadow assessment store.

Warning-only evidence may be published separately from signed replay degradation and SHALL NOT move the hard-assessment locator.


## 16. Configuration/public contract and migration

Keep global campaign schema `mdstats.mlff-campaign-cli.v2`. Add one narrow generated discriminator under `[acceptance]`:

```toml
post_selection_checkpoint_policy_generation = "p5_target_replay_v2"
```

Current generated foundation configuration is:

```toml
[post_selection.cv]
checkpoint_maximum_target_force_rmse_ev_per_angstrom = 0.075
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.075

[acceptance]
post_selection_checkpoint_policy_generation = "p5_target_replay_v2"
maximum_target_force_rmse_ev_per_angstrom = 0.050
replay_degradation_warning_mev_per_a = 50.0
replay_degradation_hard_limit_mev_per_a = 100.0
```

With the new marker, the retired `allowed_replay_degradation_mev_per_a` is invalid. Explicit current values, including `0.045/0.045/0.030`, are lawful overrides after validation.

For foundation-adaptation TRAIN2 configs without the marker:

- absent replay field or exact historical generated `allowed_replay_degradation_mev_per_a = 30.0` with no new replay fields migrates to current `50/100 meV/angstrom` and emits bounded migration notice;
- a custom legacy one-number replay value, mixed legacy/new replay fields, or new replay fields without the marker fails closed with actionable migration guidance;
- absent production target or exact historical generated `0.030` resolves to current foundation production `0.050`; other finite positive legacy production values are preserved;
- absent foundation CV checkpoint value or exact historical generated `0.045` resolves to `0.075`; other finite positive values are preserved;
- under default `target_force_rmse_ev_per_angstrom` outer metric, absent/exact historical generated `acceptance_maximum=0.045` resolves to `0.075`; a non-default outer metric is not force-RMSE-migrated and retains its accepted units/resolution;
- scratch keeps its accepted `0.030` semantics and is not migrated to foundation defaults.

Schema-less/pre-TRAIN2 generations retain their historical semantics and are not silently converted.

Generated template, `init` output, shipped example, CLI specification and user guide SHALL converge on the marker/current fields and units. Generic EVAL2 configuration for uncertainty/practical-equivalence/secondary/maturity may remain only for unaffected consumers with scope stated accurately; it SHALL NOT be described as P5 representative authority.


## 17. Currentness, historical reuse, and schema cutover

Advance schema/generation tokens at the narrowest changed owners. At minimum the cutover SHALL cover the training-only `PostSelectionMethodIdentity`, `TrainingTrajectoryIdentity`/run-root identity, CV/final assessment-plan ancestry, hard checkpoint-decision policy, strict representative/publication decision identity, assessment-independent measurement identity, final outcome-discriminated assessment evidence, and the narrow checkpoint-policy generation marker.

Do not bump global campaign schema v2 solely for this change.

Steady-state invalidation SHALL match D2.AX.004 exactly:

```text
delta_warn only -> warning/report evidence only
delta_hard      -> checkpoint assessments/representative + dependent verdict/publication
tau_CV          -> CV hard assessment/representative + outer verdict + production authorization
theta_CV        -> CV outer verdict + production authorization only
tau_prod        -> production assessment/representative/publication only
strict order    -> representative/publication descendants only
training input  -> TrainingTrajectoryIdentity and TRAIN2 descendants
measurement input -> EvaluationMeasurementIdentity and measurement descendants
```

A historical verdict is never made current by monotonic implication. Reassessment publishes a new record.

Historical TRAIN2 reuse requires exact training-semantic equivalence. The one-time historical mapping SHALL prove the legacy schema-v3 method projection, full-plan-derived run/root position, fitted preparation/materialization/runtime ancestry, and any measurement reuse separately. It SHALL NOT be implemented as "ignore method digest", pathname scan, newest-mtime choice, content-store reverse lookup, root rename/copy/symlink, or mutable alias registry.

For a completed legacy root lacking the old assessment-coupled terminal anchor, authenticate terminal TRAIN2/checkpoints and seal the root under the new training-completion rule before assessment. For an interrupted root, continue only under exact historical materialization/runtime/protocol/optimizer/RNG ancestry after the training-equivalence proof; do not rewrite that ancestry mid-trajectory.

Every affected historical CV fold/seed is reassessed under current hard/selection policy. Reuse numeric measurements only when D2.DEF.060B proof succeeds; otherwise rerun EVAL2 without retraining. If the representative changes, evaluate the new representative on the exact held-out population. Publish new current fold/campaign assessments.

Historical final production is reassessed only after current CV reclosure accepts. If historical candidate-set provenance is incomplete, rerun full governed-checkpoint EVAL2 from preserved checkpoints. Never infer a winner from an old shortlist or content-store scan.

Unchanged P1/P2/P3/source/replay/common-monitor evidence remains reusable through its real owner when semantics/identity remain applicable.

## 18. MLCV monitor disposition

Current MLCV monitor machinery may continue to own replay monitoring and training diagnostics. It SHALL NOT construct an independent target checkpoint parent for current P5.

Where current `target-light` and `target-full` budgets are both 256, the current target-light membership SHALL directly equal the authenticated common `M_mon` membership rather than invoking a second target sampler.


## 19. Failure behavior

Current P5 SHALL fail closed, with typed/actionable errors, for at least:

- unsupported/ambiguous training mode or stale/competing P5 authority;
- incompatible foundation checkpoint/head, residual-fit ancestry, or composition transfer;
- exact common-monitor shortfall, unusable labels, relation collision, or monitor mismatch;
- invalid/mixed replay-policy generation, invalid threshold type/value/order, or ambiguous custom legacy replay migration;
- missing/stale/unauthenticated/non-finite required TRUE_DFT replay evidence;
- no hard-admissible checkpoint after complete governed-checkpoint assessment;
- incomplete/foreign training trajectory identity or continuation ancestry;
- attempted policy-only root duplication instead of reuse of a training-equivalent trajectory;
- attempted historical scalar reuse without exact measurement-equivalence proof;
- attempted current final assessment/publication without current accepted CV authorization;
- attempted write of current assessment state into a sealed post-cutover training root;
- root-dependent EVAL2/reassessment without the existing run-activity exclusion;
- content-store/run-directory scanning to reconstruct candidate sets or locate legacy roots;
- M3 re-entry into P5 checkpoint/ranking/publication ancestry;
- distributed foundation execution without separate D2-equivalence acceptance; or
- runtime loss/exposure/precision/provider semantics inconsistent with authenticated training/measurement authority.

No compatibility wrapper may convert these into a different current method.


## 20. Required falsification before implementation acceptance

Implementation acceptance SHALL exercise the real P5 owners and reject at least these counterfactuals:

1. changing only replay warning threshold changes TRAIN2, hard admissibility, representative, CV verdict, production authorization, or publication;
2. replay degradation equal to 50 or 100 meV/angstrom triggers the strict warning/hard predicate, or the next binary64 value above either boundary does not;
3. negative replay degradation warns/rejects;
4. a `60 meV/angstrom` target-monitor checkpoint fails default foundation CV or passes default foundation production;
5. exact `75 meV/angstrom` CV checkpoint/outer force-RMSE fails, exact `50 meV/angstrom` production checkpoint fails, or the next binary64 value above either ceiling passes;
6. a non-default CV outer metric inherits force-RMSE `0.075`;
7. a lower-target hard-admissible checkpoint loses to replay margin/warning, secondary metric, maturity, practical-equivalence band, or bootstrap result;
8. exact within-run target ties resolve by anything other than epoch then checkpoint SHA-256;
9. exact cross-seed target ties resolve by anything other than optimizer seed then checkpoint SHA-256;
10. any governed durable checkpoint is omitted/thinned before hard assessment/selection;
11. a no-admissible outcome omits the complete ordered candidate-record set or carries a representative;
12. a selected outcome's representative is not a member of its bound candidate set;
13. `single_best_final_seed` performs a second target/M3 evaluation or imports old uncertainty/secondary/maturity ranking;
14. `all_qualified_final_seeds` performs cross-seed ranking;
15. a policy-only threshold/selection change moves `TrainingTrajectoryIdentity` or launches TRAIN2 when training-bearing inputs are identical;
16. a training-bearing membership/loss/LR/seed/horizon/preparation/precision/backend change fails to move training identity;
17. `PostSelectionFittedPreparation`, materialization, generated MACE config, checkpoint catalog, runtime summary, or continuation still requires full policy-bearing plan identity;
18. pre-training preparation consults current checkpoint admissibility merely to decide replay execution;
19. terminal TRAIN2 cannot seal the run root until assessment files exist, or current EVAL2 writes `fold-acceptance.json`/`run-evidence.json` into a post-cutover sealed root;
20. root-dependent EVAL2/reassessment can race archive/dedup/reclamation because the P5 run-activity exclusion is absent or lock order is reversed;
21. warning-only diagnostics move the hard-assessment position locator;
22. hard-policy/selection change fails to derive a new assessment position over the same training trajectory;
23. a second pointer database, assessment filesystem registry, shadow evidence store, or content-store scan is introduced;
24. a future target/replay measurement digest changes solely because an assessment threshold/full role-plan digest changed;
25. historical scalar equality alone is accepted as measurement equivalence;
26. failure to reuse historical measurement triggers TRAIN2 rather than EVAL2-only recomputation;
27. any affected historical CV fold is skipped because it previously passed;
28. changed historical CV representative reuses the old representative's outer metric;
29. historical final production is reassessed/published before current CV reclosure accepts;
30. historical final candidate winner is inferred from an old shortlist/store scan instead of complete bound evidence or recomputed EVAL2;
31. legacy roots are renamed, copied, symlinked, located by scan/mtime, or have historical hashes/runtime ancestry rewritten;
32. interrupted legacy trajectory continues without exact historical optimizer/EMA/RNG/runtime ancestry plus training-equivalence proof;
33. global campaign schema advances solely for this local policy cutover;
34. legacy generated foundation `0.045/0.045/0.030` defaults fail to migrate as specified, while explicit current values under the new marker are accidentally rewritten;
35. custom legacy one-number replay degradation is guessed into warning/hard meaning instead of failing closed;
36. scratch `0.030` semantics change as collateral;
37. generated template, init output, shipped example, CLI spec, and guide disagree on current `75/75/50` target and `50/100` replay defaults;
38. P3 target-size screening or P5 scratch loss/exposure semantics change as collateral;
39. replay transport masks/label semantics, residual E0 selected-head semantics, common-monitor exact-256 semantics, or composition-transfer requirements regress; and
40. a P5-only generation change blanket-invalidates unchanged P1/P2/P3 evidence.

Focused tests alone do not close the work. Final acceptance also requires affected regression, assembled real-owner `cross-validate` and `train-production` recovery/reassessment paths, repository-required checks, and bounded scientific qualification. Production-scale GPU qualification remains deferred to the final complete release package.

## 21. Documentation boundary

This specification is the pre-code G1B handoff freeze. Later implementation documentation may add examples, concrete schema tokens, generated views, and explanatory history, but it may not change method-bearing schema presence/absence, failure behavior, currentness, public/config semantics, or owner-facing interfaces without reopening G1B and any upstream owner actually affected.
