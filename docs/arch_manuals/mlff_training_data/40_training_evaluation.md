# Part IV - Training, replay, evaluation, and production integration

## Purpose and boundary

This chapter defines the D3 component and lifecycle structure that realizes the accepted training, replay, checkpoint, cross-validation, and final-production method. Scientific training semantics are D1; the numerical method is D2. D3 owns software owners, interfaces, dependency direction, persistent products, currentness fences, and execution seams that keep those semantics from being redefined by orchestration.

Target membership and the target-size decision are upstream. This chapter cannot create a second membership or size authority.

## Post-selection method ownership

Restored P5 has one current method authority: `PostSelectionMethodIdentity`. The broad DATA8-era `TrainingProtocolIdentity` remains only where separately current non-P5 consumers still use it and/or as historical compatibility provenance. It cannot independently authorize restored P5.

The current P5 dependency graph is:

```text
frozen TargetBinding
  -> PostSelectionMethodIdentity
  -> role policy (CV or final production)
  -> role plan
  -> fitted P5 preparation
  -> PostSelectionMaterialization
  -> run/checkpoint/evaluation evidence
  -> CV acceptance or final publication
```

The method identity is a projection of real method-bearing component owners. It must not bind the whole P3 `TargetSizeCommonTrainingPolicy` merely because current code packages P3 objective/weighting/harness settings together. P3-only changes therefore do not stale foundation-P5 evidence unless a genuinely shared component changed.

Role policies authorize work but contain no realized fold membership, monitor membership, fitted E0 result, checkpoint, evaluation result, M3 membership, or other descendant.

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

## Checkpoint and evaluation ownership

Checkpoint selection is a dedicated owner downstream of training evidence and upstream of held-out evaluation. It consumes only the evidence classes authorized by D1/D2. A held-out post-selection fold cannot participate in choosing the checkpoint on which it is later evaluated.

Target checkpoint/adaptive-stop evidence consumes the common `M_mon`. Target/replay score weights and replay-degradation/admissibility policy remain separately owned and are not the retired target/replay training-head scalars.

Checkpoint admissibility is split along the P5 lineage. `PostSelectionMethodIdentity` owns only the shared constraints (replay retention and TRUE_DFT evidence, finite metrics, physical/integrity gates); the CV and final-production role policies each own their checkpoint target-force ceiling. One owner composes shared constraints and the role ceiling into the single effective admissibility policy of a run, after authenticating that the run's role plan binds the current method and role-policy digests; it does so before preparation/training and again before candidate evaluation. That plan-bound lineage (role plan -> run identity/root -> fold acceptance or run evidence) is P5's per-run protocol ancestry: no `TrainingProtocolIdentity`, generic EVAL2 plan, or per-checkpoint role field duplicates it. A role-only ceiling edit therefore moves one role policy and its descendants; a shared-constraint edit moves the method and both roles. *(Proposed with the threshold-separation D1/D2 revision.)*

The EVAL2 owner authenticates the selected checkpoint, exact evaluation membership, target head, prediction inputs, and metric lineage before durable publication. Device batching and provider reuse are execution strategies only when they preserve the D2 numerical result under its equivalence contract.

A no-admissible-checkpoint outcome remains a typed method failure. D3 does not provide a fallback route to an inadmissible checkpoint.

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

A foundation-P5 fitted preparation authenticates:

```text
owner plan/run ancestry
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

The common monitor and held-out evaluation may contribute geometry/composition classes required for the transfer test, but their labels do not enter the E0 fit. The exact common-monitor record must exist before a current foundation-P5 preparation/run can authenticate, because its composition classes are governed transfer consumers.

P3 `objective_policy`, fitted configuration-weight tables, and inert fitted-weight digests are not foundation-P5 preparation parents. Historical weight-bearing foundation preparations may remain readable but are never reinterpreted as current.

## Post-selection cross-validation integration

Cross-validation operates once per frozen target binding and uses fresh run lineages. For each selected size the D3 graph is:

```text
TargetBinding_i
  + common M_mon record
  + current P1 separation evidence
  -> PostSelectionMethodIdentity
  -> CV policy for i
  -> selected-only fold plan (train + outer-eval + purge)
  -> fold-local fitted preparation using authorized training membership
  -> required fold/seed runs using external M_mon
  -> frozen representative per run
  -> held-out fold evaluation
  -> per-size CV verdict
```

The default fold count is the current accepted value 3; an explicit current override is admissible only for `K >= 2`. One resolver owns this default.

The size dimension is outside fold/seed machinery. Sibling sizes do not share fold membership, run evidence, pointers, or acceptance records, but they do bind the same common-monitor record. Campaign-level acceptance is all-sizes: every frozen binding must hold current accepted CV ancestry before final production is admitted.

A valid completed sibling remains reusable after another size fails or is interrupted. Scientific rejection is persisted as such; corruption, lineage failure, or execution failure is not converted into a scientific verdict.

## Target binding versus full frozen design entry

The full frozen design entry is an audit/control-plane record and may include selection provenance and role horizons. The role-neutral `TargetBinding` is the scientific target projection consumed by P5/P7 descendants. It contains generation/preparation ancestry, selected `N`, exact `T_N`, and canonical-order identity, but excludes sibling-list position, selection provenance, and role-specific horizons.

This decomposition prevents a production-budget edit from changing accepted CV identity and prevents adding a sibling selected size from changing another size's target identity.

## Fresh final production and publication

Final production begins only after the collection-wide CV admission barrier succeeds. Every production run starts from the accepted initialization/foundation family with fresh optimizer/RNG/run state and trains the complete exact selected target binding under its production policy. Screen and CV checkpoints are not warm-start parents.

Final plans bind the same exact common-monitor record used by accepted CV and current protected-relation separation evidence. M3 is not a P5 checkpoint, ranking, plan, currentness, or publication ancestor. M3 remains P3 evidence and may be consumed by a separately authorized downstream development/qualification probe through the P3 owner.

Per required production seed, the run owner freezes one admissible representative and its authenticated target metric record on the shared `M_mon`. The publication owner then applies the configured policy before downstream qualification:

- `all_qualified_final_seeds`: publish the already-admissible required representatives without cross-seed ranking;
- `single_best_final_seed`: order only already-frozen admissible representatives using their already-authenticated common-monitor target metric records and the accepted target-only representative-ordering semantics, including its deterministic uncertainty/materiality/secondary/maturity/tie rules where applicable.

Single-best publication performs no second target evaluation and no M3 evaluation. Any ordering seed material is deterministically derived from current final-plan/publication ancestry, never process/completion order. The decision persists enough policy and metric-record lineage to reproduce the published member choice.

If the accepted target-only ordering machinery cannot operate on common-monitor records without changing numerical meaning, that is a D2/D3 challenge; D4 cannot replace it with a scalar minimum-RMSE sort.

Downstream qualification consumes the frozen publication and has no API to add, remove, or reorder members.

## Currentness and compatibility

Campaign-store pointers are locators, not authority by themselves. Every public read that exposes a post-selection or production product re-resolves current target binding, P5 method, common-monitor, replay, fitted-preparation, and role-plan lineage and authenticates the pointed object against them.

Current P5 generations must fail closed on materially incompatible historical state including weighted-stress foundation runs, selected-fold target-monitor schemas, M3-dependent P5 plans/publications, from-scratch E0 foundation preparations, replay-layout-incompatible runs, missing transfer evidence, and broad DATA8/`TrainingProtocolIdentity` records used as purported P5 authorization.

Currentness advances at the narrowest real owner. P5-only generation changes do not blanket-invalidate independent P1/P2/P3 evidence or unchanged P3 runtime evidence.

A currentness change never deletes historical evidence merely to make status look clean. It changes which immutable descendant can be exposed as current.

## Downstream qualification boundary

Deployment parity, physical potential validation, uncertainty calibration, and locked testing are downstream consumers of the frozen final publication. Their numerical observables remain owned by their respective analysis/method families. Qualification may pass, reject, wait for reference evidence, or report unavailable capability for the exact frozen product; it cannot rewrite target selection, CV acceptance, production checkpoints, or publication membership.

The currently accepted release path is single-size. A completed multi-size experiment has multiple final products but no D1/D2/D3 rule for selecting one release winner, so consequential qualification is not silently started for that collection.

## Failure and recovery

Execution/restart may recover authenticated incomplete work under the exact same current plan and parent identities. It may not repair semantic drift by rebinding stale checkpoint, replay, method, monitor, fitted-preparation, or target membership state.

Provider lifetime, temporary accelerator state, caches, and materialized transport are owned and retired by their D3/D4 lifecycle owners. Garbage collection is not an ownership mechanism.