# MLFF post-selection P5 current specification

**Status:** current normative D4 contract for post-selection cross-validation and fresh final production  
**Upstream authority:** `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md`, and current D3 MLFF training-data architecture  
**Scope:** current P5 only; P3 target-size screening and P5 scratch retain their separately accepted contracts

## 1. Purpose

This specification freezes the externally visible D4 contract required to implement the accepted post-selection restoration without inventing parallel method, monitor, E0, publication, or currentness machinery.

The current P5 authority chain is:

```text
TargetBinding
  -> PostSelectionMethodIdentity
  -> role policy
  -> role plan
  -> PostSelectionFittedPreparation
  -> PostSelectionMaterialization
  -> run/checkpoint/evaluation evidence
  -> CV acceptance or final publication
```

`TrainingProtocolIdentity` is not a current P5 authorization record. It may remain for separately current non-P5 consumers and historical provenance. A historical DATA8/`TrainingProtocolIdentity` payload that deserializes does not become current P5.

## 2. Current training modes

Current post-selection training modes are semantically disjoint:

```text
scratch
naive_fine_tuning
multihead_replay
```

This specification's restored foundation-adaptation requirements apply to `naive_fine_tuning` and `multihead_replay`.

P5 scratch retains its separately accepted weighted/from-scratch method. P3 target-size screening retains its accepted weighted objective and complete-batch exposure. No foundation-P5 repair may globally change either.

## 3. `PostSelectionMethodIdentity`

`PostSelectionMethodIdentity` is the sole current P5 method identity. Its current schema generation SHALL advance from the pre-restoration generation because the old payload can authorize a materially different method.

The method identity SHALL bind only method-bearing P5 inputs. It SHALL NOT bind the whole `TargetSizeCommonTrainingPolicy.content_digest`.

The resolved current identity SHALL include, directly or through named component-policy digests:

```text
method recipe generation
training mode
foundation checkpoint + selected foundation head when applicable
foundation-P5 objective identity when applicable
P5 atomic-reference/preparation-policy identity
learning-rate schedule policy
shared checkpoint constraints (replay retention budget/TRUE_DFT requirement,
  finite metrics, required physical gates) - never a role target-force ceiling
checkpoint selection policy
shared optimizer settings
replay training-label/exposure policy
extended-XYZ transport policy
MACE architecture/model-feature identity
checkpoint interval
model dtype
execution device/backend identity where method-bearing
accepted single-process foundation-execution identity
```

For foundation modes the objective identity SHALL resolve exactly:

```text
loss_family   = universal
huber_delta   = 0.01
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

The one numeric `huber_delta=0.01` retains the D2 dimensional interpretations:

```text
energy threshold      0.01 eV/atom
force base threshold  0.01 eV/Angstrom
stress threshold      0.01 eV/Angstrom^3
```

D4 SHALL NOT expose three independent delta knobs.

A P3-only objective, configuration-weight, target-size harness, or unrelated screening change SHALL NOT change foundation-P5 method identity unless a genuinely shared component changed. Conversely, a true P5 foundation, loss, replay-label/exposure, optimizer, checkpoint-policy, precision/backend, or method-bearing execution change SHALL invalidate dependent P5 evidence.

## 4. P5 preparation-policy identity

Current P5 SHALL expose a preparation-policy identity distinct from `TargetSizeCommonTrainingPolicy.content_digest`.

For foundation modes that identity SHALL bind the selected-head foundation-residual E0 method and accepted composition-transfer policy. It SHALL NOT bind P3 `objective_policy`, P3 configuration-weight fitting policy, P3 candidate-screening controls, or other P3-only harness fields.

For scratch, the representation may bind its separately accepted from-scratch/weight-bearing preparation policy.

A shared implementation type is permitted only if its content identity is mode-disjoint and fail-closed.

## 5. `PostSelectionFittedPreparation`

The current foundation-adaptation fitted-preparation representation SHALL expose these invariants:

```text
owner plan/run ancestry                      required
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

The owning role plan/run plan is created before its fitted preparation. A
current fitted preparation binds that owning plan/run ancestry together with
the common-monitor and required-composition transfer ancestry it realizes.
The fitted preparation is therefore downstream of the plan; its digest is
then bound by `PostSelectionMaterialization` and the resulting run evidence.
Current CV and final-production plans SHALL NOT bind a fitted-preparation
digest.

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

## 11. CV policy and fold schemas

The current CV policy generation SHALL remove `checkpoint_monitor_components_per_fold` and any equivalent selected-fold target-monitor budget.

The current default fold count is exactly 3. One resolver owns that default. Explicit override is permitted only for `K >= 2`.

`PostSelectionCvFold` current membership SHALL contain only:

```text
fold gradient-training membership
held-out outer-evaluation membership
purge/exclusion membership/evidence
```

It SHALL NOT contain selected-only checkpoint-monitor membership/components.

The CV plan/run-plan SHALL bind:

```text
TargetBinding identity
PostSelectionMethodIdentity digest
CV policy digest
exact common-monitor record digest
current monitor-vs-target protected-relation separation evidence
fold membership identity
replay authority/monitor lineage where applicable
```

Every sibling selected size, fold, and seed within the same current campaign/method SHALL bind the same common-monitor record digest.

Held-out labels SHALL remain unavailable to fitting, checkpoint selection, adaptive stop, common-monitor construction, or final-publication ranking.

## 12. Checkpoint/adaptive-stop policy

### 12.1 Role-effective checkpoint admissibility

Target-force checkpoint ceilings are role policy, not method identity. `CvValidationPolicyIdentity` (schema `mdstats.post-selection-cv-policy-identity.v3`) and `FinalProductionPolicyIdentity` (schema `mdstats.post-selection-final-production-policy-identity.v2`) each carry `checkpoint_maximum_target_force_rmse_ev_per_angstrom` in eV/angstrom. `PostSelectionMethodIdentity` (schema `mdstats.post-selection-method-identity.v3`) carries `shared_checkpoint_constraints_digest` instead of the retired target-bearing `checkpoint_admissibility_policy_digest`.

Resolution SHALL be:

| Mode | CV checkpoint ceiling | CV `acceptance_maximum` default | Production checkpoint ceiling |
|---|---|---|---|
| `naive_fine_tuning`, `multihead_replay` | fixed `0.045` | `0.045` | `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, default `0.030` |
| `scratch` | `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, default `0.030` | `0.030` | same key, default `0.030` |

An explicit `[post_selection.cv].acceptance_maximum` is used as written. Its units follow `acceptance_metric`; it never supplies the checkpoint ceiling. `[acceptance].maximum_target_force_rmse_ev_per_angstrom` keeps its generic/non-P5 meaning and is not rewritten.

Each run SHALL be judged under one effective `CheckpointAdmissibilityPolicy` composed from the method's shared constraints and its role policy's ceiling. Before a run's preparation/training and before its checkpoint candidates are evaluated, the runtime SHALL verify that the run plan's `method_identity_digest` and role-policy digest (`cv_policy_identity_digest` or `final_production_policy_digest`) equal current authority and SHALL fail closed otherwise; a run of one role can never be judged under the other role's policy.

P5 binds that effective policy through the existing per-run lineage rather than a DATA8 `TrainingProtocolIdentity` or a generic `Eval2EvaluationPlan`: the role plan binds the method and role-policy digests, run identity and run root derive from the plan, and fold acceptance/run evidence bind the run-plan digest. Checkpoint records carry no additional role field. A role-ceiling change therefore yields a different plan and run position; stored candidate classifications are never re-thresholded under another ceiling.

Retired target/replay **training-head scalar** weights have no current P5 field in config, plan, materialization, runtime evidence, or content identity.

Existing target/replay checkpoint/adaptive-stop score weights remain separate current owners. Their semantics are not changed by retirement of training-head weights.

Stage/order requirement: implementation may preserve/regression-protect these score/admissibility policies before common-monitor construction exists, but current target-monitor routing cannot authenticate until the exact common monitor is constructed and bound. No temporary fold/M3 target-monitor owner is permitted.

## 13. Final-production plan

The current final-production plan SHALL bind:

```text
TargetBinding identity
PostSelectionMethodIdentity digest
final-production policy digest
accepted current CV ancestry
exact common-monitor record digest
current monitor-vs-target protected-relation separation evidence
replay authority/monitor lineage where applicable
production seed/run identity
```

The following P5 plan fields/parents are retired:

```text
m3_evaluation_size
m3_membership_digest
M3 target checkpoint-monitor ancestry
M3 final-seed ranking ancestry
```

Historical payloads may remain readable as history but cannot authorize current production.

## 14. Final representative and publication contract

Each current final-production seed freezes one admissible representative and its already-authenticated target metric record evaluated on the exact shared common monitor.

Publication supports:

### `all_qualified_final_seeds`

Publish all already-admissible required final representatives. No cross-seed ranking is performed.

### `single_best_final_seed`

The publication owner SHALL:

1. consume only already-frozen admissible final representatives;
2. consume each representative's already-authenticated target metric record on the exact shared common monitor;
3. reuse the accepted target-only representative-ordering semantics, including primary force-RMSE bands, uncertainty/bootstrap/materiality logic, secondary target metrics, maturity/lower-LR preference, and deterministic stable tie semantics where applicable;
4. derive any ordering seed material deterministically from current final-plan/publication ancestry, never process or completion order;
5. perform no second target evaluation; and
6. perform no M3 evaluation.

The publication record SHALL persist enough ordering-policy identity and input metric-record lineage to reproduce the chosen member.

A raw scalar `min(RMSE)` replacement is nonconforming unless D2/D3 is explicitly revised.

M3 remains P3 evidence and may support a separately authorized downstream development/qualification probe through the P3 owner only.

## 15. `PostSelectionMaterialization` and runtime evidence

Current P5 materialization/runtime evidence SHALL bind enough information to authenticate the actual method. For foundation modes this includes at least:

```text
training role/mode
P5 method identity and P5 preparation-policy digest
foundation checkpoint + selected head identity
resolved native loss family/class + numeric parameters
canonical residual units and dimensional Huber interpretation
conditional-force regime and nine-entry stress reduction identity
binary property-mask policy
E:F:S coefficients
atomic-reference fit mode + fit membership/input/result digests
rank/null-space/tolerance/anchor evidence
required composition-set digest + transfer result
target/replay membership digests and counts
combined count/head counts
ordered pre-shuffle layout
shuffle/sampler seed and policy
single-process identity
batch size / drop_last / batches per epoch
force_mh_ft_lr / real_pt_data_ratio_threshold / realized duplication factor
LR / EMA / precision / backend
common-monitor parent/policy/record/membership digest with exact count 256
plan-level protected-relation separation evidence
replay monitor lineage
fold train/eval/purge membership where applicable
method/CV/final/run-plan digests
final publication metric lineage where applicable
```

Materialization and run evidence are downstream of the owning plan/run plan
and bind the resulting fitted-preparation digest. They do not become parents
of the CV or final-production plan through that binding.

Transport formats such as extended XYZ carry only fields needed by their consumer; longer ancestry remains in authenticated sidecars/records rather than becoming a second authority.

## 16. Configuration/public contract

Current configuration behavior is frozen as follows:

- no user-facing corpus-order knob;
- no three-property Huber-delta knob family;
- foundation P5 objective is fixed by accepted D2 and independent of P3 `[objective]`/`[weighting]` overrides;
- a dedicated P5 field attempting to change accepted delta, E:F:S, corpus order, or distributed exposure fails closed / requires upstream revision;
- explicitly incompatible foundation E0 fit mode fails with an actionable error rather than being silently overwritten;
- retired target/replay training-head scalar fields fail closed in current config;
- canonical replay omission resolves TRUE_DFT;
- ambiguous omitted legacy split-file replay semantics fail closed;
- current P5 fold default resolves to 3 and explicit overrides require `K >= 2`;
- role target-force ceilings and the CV outer default resolve as in section 12.1, and an explicit `acceptance_maximum` is never rewritten;
- foundation distributed execution fails closed;
- exact-monitor shortfall, relation collision, unusable monitor labels, or failed composition transfer are typed infeasibility/failure, not fallback paths.

## 17. Currentness and schema cutover

Schema/generation tokens SHALL advance at the narrowest owner wherever the pre-restoration payload could authorize a materially different method. At minimum the cutover SHALL cover, as applicable:

```text
PostSelectionMethodIdentity
P5 preparation-policy identity
PostSelectionFittedPreparation
CV policy/fold/plan/run-plan schemas
common target-monitor policy/record as needed for exact-256 no-fallback semantics
MLCV target-monitor catalog/run-monitor schemas where they currently encode independent target sampling
final-production plan
final-publication decision
PostSelectionMaterialization/runtime evidence
restart/currentness stamps
```

The exact token strings are delegated D4 implementation details provided the cutover is unambiguous and tested.

The threshold-separation cutover advances `PostSelectionMethodIdentity` to v3, the CV policy to v3, and the final-production policy to v2. Pre-cutover P5 CV/final plans, fold verdicts, and run evidence become stale once; unaffected P1/P2/P3, frozen-selection, common-monitor, replay, and source/cache evidence remain reusable. Plan, run-plan, fold-acceptance, checkpoint-record, and EVAL2 schemas do not advance because only ancestor digest values change.

Old foundation weighted-stress trajectories, fold-local checkpoint-monitor plans, M3-dependent P5 plans/publications, from-scratch-E0 foundation preparations, target-first replay exposure records, missing-transfer preparations, and broad DATA8/`TrainingProtocolIdentity` P5 records SHALL fail currentness before execution/restart reuse.

Replay views and legacy true-label rematerializations produced before the section 9.1 transport contract (v1 view/receipt/materialization schemas) SHALL NOT be reused as current; they are rematerialized from their unchanged authenticated parents. That view-only cutover preserves the replay source, geometry split, true-label cache, foundation-prediction cache, and pseudo qualification, and SHALL NOT trigger foundation re-inference or a scientific resplit. The ordinary `prepare` publication converges the current replay aliases on the repaired views; post-selection readers rematerialize the same views from the published parents.

Independent P1/P2/P3/T_selected evidence remains reusable when its real owner/semantics are unchanged. A P5-only cutover SHALL NOT blanket-stale unchanged P3 evidence.

## 18. MLCV monitor disposition

Current MLCV monitor machinery may continue to own replay monitoring and training diagnostics. It SHALL NOT construct an independent target checkpoint parent for current P5.

Where current `target-light` and `target-full` budgets are both 256, the current target-light membership SHALL directly equal the authenticated common `M_mon` membership rather than invoking a second target sampler.

## 19. Failure behavior

Current P5 SHALL fail closed, with typed/actionable errors, for at least:

- unsupported/ambiguous current training mode;
- stale or competing protocol identity;
- incompatible foundation checkpoint/head;
- missing selected-head residual inputs;
- invalid residual-fit ancestry;
- failed composition transfer;
- insufficient exact common-monitor support;
- unusable monitor labels;
- protected relation collision;
- fold/final monitor digest mismatch;
- retired training-head scalar fields;
- ambiguous legacy replay label mode;
- a directly consumed replay transport whose MACE-resolved weights are not neutral/binary masks;
- runtime loss/exposure mismatch;
- implicit target duplication;
- wrong replay/target pre-shuffle order;
- distributed foundation execution;
- stale historical restart/currentness state; or
- M3 re-entry into P5 checkpoint/ranking/publication ancestry.

No compatibility wrapper may convert these into a different current method.

## 20. Required falsification before implementation acceptance

At minimum, implementation tests/review SHALL reject these counterfactuals:

1. P5 identity says UniversalLoss while runtime resolves stress;
2. fixing foundation P5 globally changes P3/P5-scratch loss semantics;
3. UniversalLoss delta/E:F:S/conditional-force/stress-reduction semantics differ from D2;
4. foundation P5 still binds/fits nontrivial configuration weights;
5. current config accepts retired training-head scalars;
6. canonical replay omission does not resolve TRUE_DFT;
7. ambiguous legacy omission silently resolves pseudo;
8. foundation adaptation uses from-scratch E0 or wrong foundation head;
9. monitor/held-out labels leak into residual fit;
10. a composition outside fit row space passes transfer without accepted anchor;
11. exact monitor realizes fewer than 256 and continues;
12. relation collision causes filtering/replacement/resampling;
13. selected-only relation projection misses cross-role leakage;
14. sibling CV/final plans bind different common-monitor records;
15. selected fold still contains checkpoint-monitor membership;
16. current MLCV builds an independent target checkpoint parent;
17. default K resolves to a value other than 3;
18. target duplication or `force_mh_ft_lr=false` occurs;
19. replay/target pre-shuffle order is reversed under same seed;
20. foundation `drop_last` differs from accepted naive/multihead geometry;
21. distributed foundation execution is admitted;
22. old incompatible checkpoint/preparation/plan resumes as current;
23. P5 identity/preparation still binds whole P3 common-training policy;
24. final plan/publication still binds or evaluates M3 to choose seed;
25. `single_best_final_seed` uses raw scalar-RMSE sorting rather than accepted ordering;
26. final publication reruns target evaluation instead of consuming frozen common-monitor metrics;
27. a P5-only generation change blanket-invalidates unchanged P3 evidence;
28. a true method-bearing change fails to invalidate dependent P5 evidence;
29. inherited source `config_weight` or non-binary `config_{energy,forces,stress}_weight` survives into a current replay view or directly consumed legacy split file and reaches native UniversalLoss;
30. a replay stress mask disagrees with the rendered stress label, or missing stress is fabricated; and
31. a pre-contract replay view is reused as current, or its repair re-runs foundation inference or resplits replay;
32. a foundation CV checkpoint at 42 meV/angstrom fails because a 30 meV/angstrom ceiling survives in method, run, or evaluation ancestry, or a foundation production checkpoint at 42 meV/angstrom is admitted;
33. default scratch begins admitting 42 meV/angstrom because foundation CV changed;
34. a role-only ceiling edit moves `PostSelectionMethodIdentity`, or a shared replay-constraint edit does not;
35. a non-target-force outer metric threshold becomes the checkpoint ceiling; and
36. a run is judged under a role policy its plan does not bind.

## 21. Documentation boundary

This specification is the pre-code G1B handoff freeze. Later implementation documentation may add examples, concrete schema tokens, generated views, and explanatory history, but it may not change method-bearing schema presence/absence, failure behavior, currentness, public/config semantics, or owner-facing interfaces without reopening G1B and any upstream owner actually affected.
