# Part IV - Training, replay, evaluation, and production integration

## Purpose and boundary

This chapter defines the D3 component and lifecycle structure that realizes the accepted training, replay, checkpoint, cross-validation, and final-production method. Scientific training semantics are D1; the numerical method is D2. D3 owns software owners, interfaces, dependency direction, persistent products, currentness fences, and execution seams that keep those semantics from being redefined by orchestration.

Target membership and the target-size decision are upstream. This chapter cannot create a second membership or size authority.


## Post-selection method and dependency ownership

Restored P5 has one current training-method authority: `PostSelectionMethodIdentity`. The broad DATA8-era `TrainingProtocolIdentity` remains only where separately current non-P5 consumers still use it and/or as historical provenance. It cannot independently authorize restored P5.

`PostSelectionMethodIdentity` binds only trajectory-generating method coordinates. Checkpoint warning/hard thresholds, CV outer-acceptance thresholds, within-run representative ordering, and final cross-seed publication ordering are assessment semantics and are not training-method parents.

The post-selection architecture distinguishes four dependency classes without requiring four new concrete types:

```text
TrainingTrajectoryIdentity
  -> fitted preparation / materialization / TRAIN2 runtime
  -> authenticated checkpoint bytes and terminal training proof

EvaluationMeasurementIdentity
  -> immutable target/replay numerical measurements

HardCheckpointDecisionPolicy + fixed representative-selection identity
  -> checkpoint assessments -> representative -> CV/final decision

ReplayWarningDiagnosticPolicy
  -> warning/report evidence only
```

`TrainingTrajectoryIdentity` is the canonical role-specific **pre-fit training-position** projection. It binds every already-available input capable of changing exact TRAIN2/materialization/restart behavior: training role and exact gradient/replay-training membership; optimizer seed and planned horizon; foundation checkpoint/head and replay-training lineage; preparation method/policy plus deterministic preparation inputs such as authorized fit membership, selected-head prediction/reference-E0 input identity, common-monitor/transfer-consumer composition identity, and accepted rank/tolerance/anchor policy; objective/loss, exposure/corpus order, optimizer/LR, precision/backend/model architecture, checkpoint cadence and accepted MACE execution semantics; and any validation artifact consumed by the trainer. It does **not** bind the fitted preparation record/result or another descendant product. Checkpoint-decision thresholds, warning thresholds, CV outer acceptance, representative ordering, committee/publication policy, and other post-training decisions are likewise excluded.

`EvaluationMeasurementIdentity` binds only inputs capable of changing one numerical measurement: exact checkpoint/model state, exact evaluation population/artifact and labels/reference values, metric/reduction/units, head/prediction semantics, provider realization, and numerically material precision/backend semantics. A full role-plan digest or threshold is not a numerical-measurement input merely because an older schema hashed it.

Current CV/final role plans remain authorization/assessment parents. Each binds its role-effective hard-decision policy and the fixed D2 representative-selection identity explicitly, while the warning-only policy remains outside that ancestry. The same plan exposes the training-position projection used by TRAIN2 without making assessment coordinates part of the run root.

The resulting dependency graph is:

```text
frozen TargetBinding + training method + training-bearing parents
  -> TrainingTrajectoryIdentity
  -> fitted P5 preparation
  -> PostSelectionMaterialization
  -> TRAIN2 runtime/checkpoints
  -> sealed training root

checkpoint/model + exact evaluation evidence
  -> EvaluationMeasurementIdentity
  -> immutable target/replay measurements

current role assessment plan
  + hard-decision policy
  + fixed D2 selection identity
  + measurements
  -> checkpoint assessments
  -> representative
  -> CV/final verdict/publication

warning policy + replay measurement
  -> diagnostic evidence only
```

The trajectory position exists before fitting. `PostSelectionFittedPreparation` is its descendant and binds that trajectory identity; materialization/runtime then bind the exact fitted-preparation digest. Continuation/reuse authenticates both the pre-fit trajectory identity and the exact realized fitted-preparation/result/runtime ancestry required by D2.DEF.060. A policy-only edit therefore cannot create a different training trajectory, while a changed fitted result under otherwise identical pre-fit identity is a fail-closed realized-state mismatch rather than a reason to create a cyclic identity.

## Replay ownership

Replay has one construction owner and a strict lifecycle boundary.

- `doctor` checks prerequisites and reports deferred construction-dependent facts; it does not build replay scientific products.
- `prepare` owns replay authentication, construction/reuse, deterministic split products, required prediction-dependent products when applicable, replay transport, and the independent replay monitor.
- cross-validation, final production, restart, and representative re-evaluation are consumers of the published replay authority. They may reconstruct disposable transport/index views from authenticated parents, but they do not create a new replay split, prediction authority, or qualification lineage.

Target and replay remain separate product families. A replay-only lineage change invalidates the post-selection descendants that consume it without mutating frozen target-size evidence.

The canonical single-source replay interface resolves omission to TRUE_DFT. A still-current legacy split-file route may preserve an explicitly requested supported historical mode, but ambiguous omitted legacy semantics fail closed rather than silently restoring pseudo labels as the current default.

Foundation pseudo-label replay remains explicit opt-in and requires an independent TRUE_DFT replay monitor. Changing replay label mode over the same authenticated source/split does not change replay geometry membership.

## Campaign-common target checkpoint monitor

Checkpoint/adaptive-stop target evidence is one immutable campaign-common exact monitor, `M_mon`, constructed from neutral label-usable `OUTER_MONITOR` evidence and reused across all selected sizes, CV folds/seeds, and final-production seeds/runs.

`M_mon` is external to selected-fold membership. Its immutable record digest is a required ancestor of every current CV plan and final-production plan. Plan admission additionally binds current protected-relation separation evidence against every governed selected target membership.

The construction and separation flow is strictly:

```text
neutral OUTER_MONITOR parent
  -> exact deterministic D2 monitor membership
  -> immutable common-monitor record
  -> P1 cross-role protected-relation separation check
  -> CV/final plan admission
```

No fold-local target monitor, final-specific target monitor, M3-derived target monitor, relation-filtered resample, or fallback monitor is a current P5 owner. If the exact accepted monitor cannot be realized and separated, P5 is infeasible.

Replay monitoring and other diagnostics remain separate evidence products.


## Checkpoint, measurement, assessment, and run-root ownership

Checkpoint assessment is downstream of authenticated TRAIN2 and immutable measurements. Held-out post-selection folds cannot participate in checkpoint selection.

The accepted D2 checkpoint universe is complete: every governed durable checkpoint receives the required current assessment. Hard checkpoint admissibility is composed from the shared finite/evidence/physical constraints, the role target ceiling, and the catastrophic replay limit where replay is enabled. The replay warning threshold is diagnostic-only and has no dependency edge into hard admissibility, representative identity, CV acceptance, production authorization, or publication membership.

The foundation role coordinates have distinct owners and invalidation scopes:

| Coordinate | Current source/owner | Architectural descendants |
|---|---|---|
| CV checkpoint ceiling `tau_CV` | existing foundation CV role-policy resolver | CV checkpoint assessment/representative, dependent outer verdict and production authorization |
| CV outer threshold `theta_CV` | existing CV outer-policy resolver for the configured outer metric | CV outer verdict and dependent production authorization only |
| production checkpoint ceiling `tau_prod` | existing final-production role-policy resolver | production checkpoint assessment/representative/publication |
| replay catastrophic limit `delta_hard` | shared replay hard-decision projection | CV/final checkpoint assessments and descendants that consume them |
| replay warning `delta_warn` | diagnostic projection from the same configuration owner | warning/report evidence only |
| strict P5 ordering identity | accepted D2 fixed-method owner | representative/publication descendants only |

For the default foundation force-RMSE metric, omitted/current generated values resolve to `tau_CV=0.075`, `theta_CV=0.075`, and `tau_prod=0.050 eV/angstrom`. Scratch keeps its separately accepted threshold contract. Alternative CV outer metrics keep their own units and threshold-resolution rules and never inherit the force-RMSE `0.075` by dimensional coincidence.

Numeric EVAL2 evidence is assessment-independent. The measurement owner authenticates the checkpoint/model state, exact evaluation population/artifact, target/replay labels and references, metric/reduction policy, target head/prediction semantics, provider realization, and numerically material precision semantics before immutable publication. Current checkpoint assessments consume those records; they do not rewrite them when a threshold changes. Historical scalar values are reusable only through the D2 measurement-equivalence proof; otherwise EVAL2 is recomputed from preserved authenticated checkpoints.

Within one training trajectory, checkpoint assessment records bind the complete ordered candidate universe. The current D2 representative is the lexicographic minimum over hard-admissible checkpoints by `(target RMSE, epoch, checkpoint SHA-256)`. No replay warning/margin, secondary metric, maturity, practical-equivalence band, bootstrap quantity, or historical score may outrank a lower target RMSE. A no-admissible-checkpoint result remains a typed current assessment outcome, not a fallback to an inadmissible checkpoint.

Post-cutover run roots are training-only. A root is keyed by `TrainingTrajectoryIdentity` and contains fitted/materialized training state, generated training configuration, checkpoints, runtime history, and the existing completion/topology proof. Once authenticated TRAIN2 reaches its terminal training boundary, the owner seals the root before EVAL2. Current CV/final assessments never write into the sealed root.

Current policy-bound assessments are immutable objects in the existing post-selection evidence/currentness plane. The existing CampaignStore pointer seam is extended with one position-addressed assessment locator whose key is the canonical projection:

```text
selected_binding_digest
assessment_role = cv_fold | final_seed
assessment_position_policy_digest
training_trajectory_identity
optimizer_seed
fold_index for CV, absent for final production
```

The role-specific `assessment_position_policy_digest` is narrower than the full role plan:

- for `cv_fold`, it binds the current CV hard checkpoint-decision policy, D2.DEF.059A within-run ordering identity, configured outer metric and `theta_CV` verdict policy;
- for `final_seed`, it binds only the current final hard checkpoint-decision policy and D2.DEF.059A within-run ordering identity.

The final-seed projection excludes current-CV authorization ancestry, publication mode, and D2.DEF.059B. Current CV acceptance is a separately re-authenticated authorization precondition for using a final-seed assessment, while publication mode/059B are aggregate publication parents over already-frozen seed representatives.

The pointer value is the immutable current assessment-record digest. Campaign-level CV-acceptance and final-publication pointers remain the aggregate current authorities. A warning-only edit does not move a hard-assessment position; a hard-policy or D2.DEF.059A edit does. A D2.DEF.059B/publication-mode-only edit moves only the aggregate final publication decision.

Any EVAL2/reassessment that reads checkpoint/materialization bytes from a sealed root holds the existing P5 run-activity exclusion for the whole root-dependent numerical-read interval. Storage archive/dedup/reclamation therefore cannot move those bytes concurrently. If an operation also needs the post-selection publication barrier, lock ordering is run-activity exclusion first, publication barrier second. D4 may retain the existing concrete lease API; no second reader-lock protocol is permitted.

## MACE adapter seam

The MACE adapter is the single dependency-facing execution seam. It owns current package/source qualification, parser argument realization, loader/exposure realization, checkpoint transport, precision/backend binding, and source-shape/runtime guards required to make the pinned dependency execute the D2 method.

Loss/exposure routing is mode-specific at this seam:

```text
P3 target-size screening        -> accepted weighted objective + complete-batch geometry
P5 scratch                      -> separately accepted weighted method
P5 naive foundation adaptation  -> native MACE UniversalLoss + foundation-P5 exposure
P5 multihead replay adaptation  -> native MACE UniversalLoss + replay-first combined exposure
```

A global loss-family flip is therefore architecturally invalid. Foundation P5 resolves the fixed accepted UniversalLoss values through its P5 method identity; P3/scratch settings remain under their owners.

Foundation P5 uses the accepted single-process realization. A distributed foundation path fails closed until separately qualified as D2-equivalent.

Dependency quirks and exact source probes belong to D4 and qualification evidence, not timeless D3 doctrine. Replacing pinned MACE or the adapter mechanism is admissible only when the replacement proves the same accepted D1/D2 semantics or reopens affected upstream authority.


## Foundation-residual fitted preparation

The existing atomic-reference fitter remains the sole E0 solver. Foundation P5 routes it through selected-foundation-head residual inputs. Scratch retains its separately accepted total-energy E0 path.

A current foundation-P5 fitted preparation authenticates the training trajectory position that owns it rather than the full policy-bearing CV/final assessment plan. Its required ancestry includes:

```text
TrainingTrajectoryIdentity / exact training position
explicit foundation training mode/kind
P5 preparation-policy identity
exact fit membership
authenticated residual-E0 fit record/result
selected foundation checkpoint/head
foundation prediction/reference-E0 input identity
required composition-set identity
rank/null-space/tolerance/accepted-anchor evidence
composition-transfer result
```

The common monitor and held-out evaluation may contribute geometry/composition classes required for the transfer test, but their labels do not enter the E0 fit. When a common-monitor identity or transfer-consumer composition set is consumed by preparation/runtime it is training-bearing ancestry and therefore belongs in `TrainingTrajectoryIdentity`.

P3 `objective_policy`, fitted configuration-weight tables, inert fitted-weight digests, checkpoint-decision thresholds, replay-warning thresholds, and representative-selection policy are not foundation-P5 preparation parents. Historical weight-bearing or full-plan-bound foundation preparations remain immutable history and may be reused only through the accepted exact training-equivalence derivation.


## Post-selection cross-validation integration

Cross-validation operates once per frozen target binding and uses fresh training positions. For each selected size the D3 graph is:

```text
TargetBinding_i
  + common M_mon record
  + current P1 separation evidence
  + training-only PostSelectionMethodIdentity
  -> role-specific TrainingTrajectoryIdentity per fold/seed
  -> fitted preparation / materialization / fixed-budget TRAIN2
  -> sealed training root
  -> checkpoint/common-monitor measurements
  + current CV hard-decision + strict-selection policy
  -> frozen representative
  -> held-out measurement
  + current theta_CV outer policy
  -> fold/seed assessment
  -> per-size CV verdict
```

The default fold count remains the accepted value 3; explicit current override requires `K >= 2`. The size dimension remains outside fold/seed machinery. Sibling sizes do not share fold membership, training roots, assessment positions, or acceptance records, but they bind the same common-monitor record.

A policy-only change reuses training-equivalent roots and reassesses every governed checkpoint position under current policy. A changed representative purchases only the held-out evaluation required for that new representative; unchanged measurement evidence is reused only when D2 measurement equivalence is proven. No historical fold verdict is relabeled current in place.

Campaign-level production admission remains all-sizes: every frozen binding must hold current accepted CV ancestry. A valid completed sibling remains reusable after another size fails or is interrupted. Scientific rejection is persisted as such; corruption, lineage failure, or execution failure is not converted into a scientific verdict.

## Target binding versus full frozen design entry

The full frozen design entry is an audit/control-plane record and may include selection provenance and role horizons. The role-neutral `TargetBinding` is the scientific target projection consumed by P5/P7 descendants. It contains generation/preparation ancestry, selected `N`, exact `T_N`, and canonical-order identity, but excludes sibling-list position, selection provenance, and role-specific horizons.

This decomposition prevents a production-budget edit from changing accepted CV identity and prevents adding a sibling selected size from changing another size's target identity.


## Fresh final production and publication

Final production begins only after the collection-wide current-CV admission barrier succeeds. Every newly executed production trajectory starts from the accepted initialization/foundation family with fresh optimizer/RNG state and trains the complete exact selected target binding. Screen and CV checkpoints are not warm-start parents.

A historically fresh completed final-production trajectory may be reused for current assessment without retraining only after current CV has been reclosed and accepted and exact D2 training-semantic equivalence is proven. Current CV rejection leaves retained production bytes historical and nonpublishable under current authority.

Each production seed has one training trajectory position and one current assessment position. After fixed-budget TRAIN2 is sealed, the current final hard-decision policy reassesses the complete governed checkpoint universe from current or measurement-equivalent EVAL2 records, recomputing EVAL2 from preserved checkpoints when historical provenance is insufficient. The within-run representative is the exact D2 minimum by `(target RMSE, epoch, checkpoint SHA-256)`.

The publication owner consumes only the already-frozen hard-admissible seed representatives and their authenticated common-monitor target measurements:

- `all_qualified_final_seeds` publishes all required admissible representatives without cross-seed ranking;
- `single_best_final_seed` chooses the lexicographic minimum by `(target RMSE, optimizer seed, checkpoint SHA-256)`.

Publication performs no second target evaluation and no M3 evaluation. Replay warning/margin, secondary metrics, maturity, practical-equivalence bands, and bootstrap quantities have no cross-seed ordering authority. Publication membership is frozen before downstream qualification.


## Currentness and compatibility

Campaign-store pointers are locators, not authority by themselves. Every public read resolves current target binding, training method, training trajectory, measurement ancestry, assessment policy, common-monitor/replay lineage, and the pointed immutable object needed for that product.

Currentness advances at the narrowest real owner:

- warning-only replay-policy changes move warning/report evidence only;
- replay hard-limit changes move checkpoint assessments/representatives and dependent verdict/publication, not TRAIN2 or authenticated replay measurements;
- `tau_CV` changes move CV hard assessments/representatives, dependent outer verdict and production authorization, not CV TRAIN2/measurements;
- `theta_CV` changes move only CV outer verdict and dependent production authorization;
- `tau_prod` changes move production assessment/representative/publication, not production TRAIN2 or accepted CV;
- a D2.DEF.059A within-run ordering change moves checkpoint representative and dependent verdict/publication descendants but not TRAIN2 or numeric measurements;
- a D2.DEF.059B/publication-mode-only change moves only aggregate final publication descendants, not per-seed assessments;
- a pre-fit training-bearing method/membership/seed/horizon/preparation-input/runtime change moves `TrainingTrajectoryIdentity`; a changed fitted-preparation/result under the same pre-fit identity is detected separately by realized-state authentication and remains fail-closed for continuation;
- a numerical-evaluation population/metric/provider/precision change moves `EvaluationMeasurementIdentity` and forbids stale measurement reuse.

A historical verdict/classification never becomes current by monotonic threshold implication. Reassessment publishes a new immutable assessment. Existing checkpoint bytes/history/runtime summaries remain immutable.

The one-time cutover from policy-overbound historical identities is a source-preserving equivalence mapping at the existing recovery/currentness owner, not a steady-state compatibility subsystem. It may bind one authenticated legacy root to one current training trajectory after exact proof. An already sealed historical root is strictly read-only. A terminal-but-unsealed historical root may receive exactly one append-only completion topology/anchor publication under the existing P5 run-activity owner after its terminal TRAIN2/checkpoint/runtime state and every existing root node are authenticated; no pre-existing historical byte may be rewritten, and any conflicting partial proof fails closed. The migration must not scan, rename, copy, symlink, or otherwise mutate historical training state and must not become a general alias registry.

P5-only generation changes do not blanket-invalidate independent P1/P2/P3 evidence. Unsupported historical generations remain readable history or fail closed as appropriate; they do not become a backdoor into current authority.

## Downstream qualification boundary

Deployment parity, physical potential validation, uncertainty calibration, and locked testing are downstream consumers of the frozen final publication. Their numerical observables remain owned by their respective analysis/method families. Qualification may pass, reject, wait for reference evidence, or report unavailable capability for the exact frozen product; it cannot rewrite target selection, CV acceptance, production checkpoints, or publication membership.

The currently accepted release path is single-size. A completed multi-size experiment has multiple final products but no D1/D2/D3 rule for selecting one release winner, so consequential qualification is not silently started for that collection.

## Failure and recovery

Execution/restart may recover authenticated incomplete work under the exact same current plan and parent identities. It may not repair semantic drift by rebinding stale checkpoint, replay, method, monitor, fitted-preparation, or target membership state.

Provider lifetime, temporary accelerator state, caches, and materialized transport are owned and retired by their D3/D4 lifecycle owners. Garbage collection is not an ownership mechanism.