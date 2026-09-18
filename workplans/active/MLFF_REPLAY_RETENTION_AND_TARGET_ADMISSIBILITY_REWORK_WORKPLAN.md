---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: active-authority-reopen-pending
highest_affected_domain: D1
branch: design/mlff-replay-retention-target-admissibility-rework
analysis_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
implementation_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
protocol_6_4_authority_merge: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
stakeholder_direction_date: 2026-09-18
review_state: third-pass-baseline-reconciled-awaiting-d1-d2-renewal
---

# MLFF Replay Retention and Target Admissibility Rework Workplan

## 0. Lifecycle state and baseline review disposition

Protocol 6.4 D1/D2 renewal is complete and merged to `main` at `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`. This workplan is now active on branch `design/mlff-replay-retention-target-admissibility-rework`, but implementation remains blocked until this new replay/target-policy change itself passes the required D1 then D2 renewal under Protocol 6.4.

The accepted Protocol 6.4 baseline currently still states the old method: replay retention is a hard shared admissibility constraint; `tau_prod` defaults to `0.030 eV/angstrom`; and P5 representative/final single-best ordering may use practical-equivalence, bootstrap, secondary target metrics, and maturity semantics. The stakeholder direction below therefore **reopens accepted D1/D2**; it is not already authorized merely because the preceding Protocol 6.4 reconstruction closed PASS.

Baseline implementation review against `a759e81...` found four architectural consequences that this plan must repair explicitly:

1. `PostSelectionMethodIdentity` binds both `shared_checkpoint_constraints_digest` **and** `checkpoint_selection_policy_digest`; changing either replay thresholds or the representative-ordering rule currently changes TRAIN2 `training_protocol_digest` even though neither can affect optimizer updates.
2. CV/final run identity is hashed from the complete role-plan digest. A role-only target-threshold edit therefore changes the run namespace and currently prevents direct reuse of an otherwise identical completed TRAIN2 trajectory.
3. `post_selection_eval_role_digest()` includes full `run_plan_digest` and `run_identity`. Consequently policy-only plan changes also change target/replay metric-record ancestry even when checkpoint bytes, evaluation population, provider realization, and metric policy are identical.
4. `single_best_final_seed` reuses the same uncertainty/materiality/secondary/maturity ordering as within-run P5 representative selection. If the accepted rule becomes strict minimum authoritative target RMSE, both P5 checkpoint-ranking surfaces must converge on that rule; `all_qualified_final_seeds` remains unchanged.

A second baseline pass found six additional closure requirements:

5. The replay warning threshold is diagnostic-only. Letting a warning-threshold edit stale admissibility, representative choice, CV acceptance, production authorization, or publication membership would recreate the same over-binding defect at a new layer.
6. The shipped v2 campaign template explicitly writes both the historical production target value `0.030` and replay value `30.0`. A default-only resolver change would therefore leave old generated campaigns trapped at the old standards. The configuration cutover needs schema-aware migration, not only new Python defaults.
7. Historical EVAL2 target metric records do not independently bind a clean checkpoint/artifact/provider measurement identity: their `target_role_digest` and `prediction_digest` include old run-plan ancestry, and raw predictions are not persisted. Historical scalar reuse is lawful only where complete old measurement ancestry can actually be reconstructed; otherwise EVAL2 must be recomputed from preserved checkpoints without TRAIN2 retraining.
8. Successful final-production `PostSelectionRunEvidence` binds only the selected representative, not the complete candidate-record set. Under a changed selection rule, old production candidates cannot be discovered authoritatively by reverse-scanning the content store. Future terminal run evidence must bind the complete assessed candidate set; historical production may require EVAL2 recomputation.
9. The plan left exact target-RMSE ties under-specified. Protocol 6.4 D2 must freeze deterministic non-quality tie keys separately for within-run checkpoints and cross-seed publication.
10. A clean training-position identity does not by itself locate sealed historical run roots whose directory names are old full-plan-derived run identities. The one-time cutover must derive any legacy source root from authenticated historical plan/run evidence, never from directory scanning, copying, renaming, or weakening completion-manifest ownership.

A third baseline pass found six more structural requirements:

11. Current `_prepare_post_selection_run()` resolves `context.checkpoint_admissibility(run_plan)` before continuation/materialization recovery and uses that assessment policy merely to decide replay execution. A changed hard policy can therefore block an otherwise identical trajectory before reuse. Replay execution/monitor transport must be resolved from the training method/replay lineage; hard admissibility must not be consulted until EVAL2.
12. `PostSelectionFittedPreparation.owner_plan_digest`, `PostSelectionMaterialization.run_plan_digest`, checkpoint catalogs/records, TRAIN2 runtime summaries and continuation checks still bind full run-plan/method ancestry. Correcting only `run_identity` is insufficient: every training/restart owner must bind the training-position authority rather than policy-bearing assessment ancestry.
13. Run roots are create-once topology-sealed only after `fold-acceptance.json` or `run-evidence.json` is written. Reassessing the same trajectory under a new policy cannot lawfully overwrite those fixed files or append new assessment state to the sealed root. Training-root completion and policy assessment need separate durable lifecycles.
14. A global campaign-schema v3 bump is broader than necessary and would perturb unrelated config parsing. The migration discriminator should be a narrow post-selection checkpoint-policy generation marker inside the existing campaign-v2 contract.
15. `FinalProductionPlan` binds the historical CV authorization even though CV verdict bytes cannot influence already-produced final TRAIN2 bytes. D1/D2 must explicitly decide when a historically fresh final-production trajectory may be reassessed after the current CV policy is reclosed; a current CV rejection must still block current production publication.
16. Foundation P5 preparation consumes common-monitor and held-out composition-transfer requirements before training. The training-position projection must preserve every preparation/validation input capable of changing exact materialization or continuation, not merely gradient membership.

The current P5 runtime already fully evaluates every durable TRAIN2 checkpoint before selecting its representative: `post_selection_checkpoint_candidates()` authenticates the entire saved trajectory and `evaluate_post_selection_run_candidates()` evaluates every returned checkpoint. Therefore this workplan does **not** need a new shortlist/rescue/evaluation-purchase mechanism for P5. Generic EVAL2 shortlist machinery may remain for other consumers unless independently affected.

The stakeholder-directed outcome is:

1. TRUE_DFT replay degradation remains a required diagnostic observable.
2. Replay degradation greater than `0.050 eV/angstrom` produces a diagnostic warning, not rejection.
3. Replay degradation greater than `0.100 eV/angstrom` is a conservative catastrophic-forgetting hard rejection.
4. Both replay thresholds are configurable policy parameters; `0.050` and `0.100 eV/angstrom` are generated/current defaults, not universal physical constants.
5. P5 checkpoint quality ranking is only authoritative target force-component RMSE. Among checkpoints satisfying hard requirements, the checkpoint with the lowest target RMSE is the representative. Replay margin, warning status, secondary target metrics, maturity/refinement phase, practical-equivalence bands, and bootstrap uncertainty may not promote a strictly worse target RMSE.
6. `single_best_final_seed`, when configured, applies the same strict target-RMSE rule to the already-frozen admissible per-seed representatives. `all_qualified_final_seeds` remains publication-without-ranking.
7. The default **foundation-production** target admissibility ceiling rises from `0.030` to `0.050 eV/angstrom`. Current foundation-CV defaults remain `0.045/0.045`; current P5 scratch defaults remain unchanged unless separately reopened.
8. An assessment-policy-only revision must not invalidate or retrain an otherwise identical authenticated TRAIN2 trajectory.
9. Old EVAL2 measurements should be reassessed under the new policy when their exact checkpoint/evaluation/provider/metric ancestry remains valid; historical records are never mutated in place.

No D4 implementation may begin before Gates B and C close on the renewed D1/D2 authority.

## 1. Trigger and problem statement

### 1.1 Observed production trajectory

A real 40-epoch final-production TRAIN2 trajectory on selected target size `N=512` produced a healthy target-learning curve but was rejected because no saved checkpoint simultaneously passed the old `0.030 eV/angstrom` target ceiling and old `0.030 eV/angstrom` foundation-relative replay-degradation ceiling.

The independently recovered TRUE_DFT replay foundation baselines were:

```text
0.07934332031091848 eV/angstrom
0.07934333438787265 eV/angstrom
```

They are numerically equivalent for this decision, giving approximately:

```text
R0_replay = 0.07934333 eV/angstrom
```

Key TRAIN2 diagnostic points were:

```text
epoch 6: target = 0.0309198, replay = 0.1071669, degradation ~= 0.0278236
epoch 7: target = 0.0299156, replay = 0.1146174, degradation ~= 0.0352741
epoch 21: target = 0.0246485, replay = 0.1550590, degradation ~= 0.0757157
epoch 40: target = 0.0290870, replay = 0.1684228, degradation ~= 0.0890794
```

Thus the old replay hard gate rejected every target-competent checkpoint, even though the target curve had a clear, physically interpretable minimum around epoch 21 and no checkpoint approached `0.100 eV/angstrom` replay degradation.

These TRAIN2 values are trajectory diagnostics. Current EVAL2 remains the authoritative full checkpoint assessment domain; the observed production failure independently establishes that no checkpoint was admissible under the old EVAL2 policy.

### 1.2 Historical method context

Repository history shows replay degradation has not always had the same scientific role:

- earlier adaptive selection retained foundation-relative replay degradation as a diagnostic rather than the default hard selector;
- later MLCV revisions used replay values as training-control/selection evidence;
- the TRAIN2A revision promoted replay degradation to a hard admissibility constraint with zero ranking credit;
- the 2026-09-14 post-selection restoration deliberately preserved existing replay thresholds because threshold redesign was outside that restoration's scope;
- the restoration workplan explicitly required reopening D1/D2 if correctly restored TRUE_DFT replay still produced material forgetting inconsistent with the accepted gates.

The current real production result activates that reopen condition. This is therefore not a request for a D4 constant patch. The earliest owner is D1/D2.

### 1.3 Baseline ownership defects relevant to migration

At `a759e81...`, the executable ancestry over-binds assessment semantics at three distinct levels.

**Method identity.** `PostSelectionMethodPolicies._shared_checkpoint_constraints()` contains the replay degradation budget, and `PostSelectionMethodIdentity` hashes both `shared_checkpoint_constraints_digest` and `checkpoint_selection_policy_digest`. That method digest becomes the TRAIN2 `training_protocol_digest` and is embedded in the materialized MACE configuration. Replay threshold and checkpoint-ordering edits therefore look like training-method edits even though current TRAIN2 is fixed-budget and these policies do not change gradient updates.

**Run identity.** `FinalProductionPlan` / `PostSelectionCvPlan` bind role policy; `FinalProductionRunPlan` / `PostSelectionCvFoldRunPlan` derive `run_identity` from the complete plan digest. A production target-threshold edit changes the production policy -> final plan -> run identity even when every training-affecting coordinate is identical. The existing `reject_foreign_run_continuation()` correctly rejects cross-run continuation, so this must be solved by correcting identity ownership rather than weakening that guard.

**Evaluation measurement identity.** `post_selection_eval_role_digest()` currently hashes `run_plan_digest` and `run_identity` into metric role identity. A policy-only plan edit thus makes an otherwise identical checkpoint-on-identical-monitor measurement look unrelated. That blocks exact measurement reuse unless the assessment-independent evaluation identity is separated or an explicit source-preserving reassessment derivation is defined.

The repair must therefore separate **training trajectory identity**, **evaluation measurement identity**, and **assessment/selection policy identity**. Removing only the old `0.030` replay constant from one schema is insufficient.

---

## 2. Protected scientific outcome

### 2.1 Observables

For checkpoint `c`, define authoritative target force-component RMSE on the governed checkpoint-monitor target domain as

```text
T(c) = target force-component RMSE of checkpoint c
```

and TRUE_DFT replay degradation on the exact authenticated replay monitor as

```text
DeltaR(c) = R_replay(c) - R_replay(foundation)
```

where candidate and foundation replay RMSE are evaluated on the exact same replay domain with the accepted metric/provider semantics.

Signed degradation is retained. A negative value remains an improvement, not zero-clipped loss.

### 2.2 Replay classification

For replay-enabled foundation adaptation, define two configurable thresholds:

```text
delta_warn_default = 0.050 eV/angstrom
delta_hard_default = 0.100 eV/angstrom
```

Required relation:

```text
0 < delta_warn < delta_hard
```

Classification is exact:

```text
DeltaR <= delta_warn
    normal replay retention

delta_warn < DeltaR <= delta_hard
    admissible checkpoint + replay-degradation diagnostic warning

DeltaR > delta_hard
    hard rejection: catastrophic replay forgetting
```

Therefore exact equality at `0.050` does not warn and exact equality at `0.100` does not reject.

Replay warning status carries **zero ranking credit and zero tie-break authority**. It also carries **zero hard-currentness authority**: changing only `delta_warn` may change emitted or persisted diagnostic-warning evidence, but must not change the hard-admissible set, representative, outer-fold purchase, CV acceptance, production authorization, or publication membership.

Missing required TRUE_DFT replay evidence, invalid replay lineage, nonfinite replay metrics, or other integrity failures remain hard failures. This revision changes only the interpretation of finite authenticated replay degradation.

### 2.3 Target quality

For foundation final production, change the generated/default production checkpoint target-force ceiling from:

```text
0.030 eV/angstrom
```

to:

```text
0.050 eV/angstrom
```

The value remains configurable and role-specific. It is checkpoint/model-control evidence, not external deployment qualification.

**Narrow-scope rule:** accepted Protocol 6.4 foundation-CV defaults remain `tau_cv = 0.045 eV/angstrom` and `theta_cv = 0.045 eV/angstrom`. Existing P5 scratch target defaults remain unchanged. The only target-default change in this cycle is foundation final production `tau_prod: 0.030 -> 0.050 eV/angstrom`. Implementation must not broaden that edit through the current shared `[acceptance]` default owner.

Preserve the existing public field for an explicit user production/scratch target ceiling. The resolver may need a mode-aware **omitted-value default** so foundation production resolves `0.050` while scratch retains its accepted default; do not add a second synonymous public target-threshold field solely to obtain this isolation.

### 2.4 Representative selection

The representative-selection rule is simplified.

Let `H` be the checkpoints satisfying all hard candidate requirements, including:

- finite/authenticated target metric;
- valid TRUE_DFT replay evidence when replay is enabled;
- `DeltaR(c) <= delta_hard`;
- the role-effective target admissibility ceiling;
- existing required integrity/physical gates, if any.

Then select:

```text
c_star = argmin over c in H of T(c)
```

No secondary quality observable may override a strictly lower `T(c)`.

In particular, the following must not promote a checkpoint with higher authoritative target RMSE:

- replay degradation margin below the hard ceiling;
- replay warning/no-warning status;
- worst-stratum/species/tail target metrics;
- refinement/maturity phase;
- practical-equivalence bands;
- paired bootstrap uncertainty classification;
- checkpoint epoch except as a deterministic exact-tie fallback.

If two checkpoints have exactly identical authoritative binary64 target RMSE under the accepted stored representation, freeze the **within-run** tie key as ascending `(epoch, checkpoint_sha256)`. Epoch and SHA are consulted only after exact target-RMSE equality and therefore have no scientific ranking authority.

Current P5 runtime already performs authoritative target and replay evaluation for every durable TRAIN2 checkpoint in `evaluate_post_selection_run_candidates()`. Therefore the current real P5 path can establish a true minimum over all durable checkpoints without introducing approximate shortlist semantics.

The same target-only rule governs `single_best_final_seed`: after each required production seed has already frozen its own hard-admissible representative, the single-best publication member is the representative with minimum authoritative common-monitor target RMSE. If two seed representatives have exactly identical authoritative target RMSE, freeze the **cross-seed** tie key as ascending `(optimizer_seed, representative_checkpoint_sha256)`. `all_qualified_final_seeds` performs no cross-seed ranking and is unchanged.

### 2.5 No-admissible outcome

A run has no representative only when no checkpoint survives hard requirements. Replay warning alone can never create a no-admissible outcome.

A checkpoint whose target RMSE exceeds the role-effective target ceiling remains target-inadmissible. Raising the foundation-production default to `0.050` changes that default policy but does not eliminate the target-quality gate.

---

## 3. D1 authority renewal requirements

The merged Protocol 6.4 D1 is accepted-current and therefore must be explicitly reopened for this cycle. Amend the canonical owner rather than layering policy prose elsewhere.

At minimum reconcile these accepted definitions/axioms:

- `D1.DEF.022` replay lineage: preserve authenticated replay geometry, true-reference monitor, foundation/head and exposure lineage, but remove replay warning/hard **decision thresholds** from training/replay-data lineage. If `Q_r` is retained, narrow it to replay evidence/monitor qualification that can affect evidence validity; warning/hard checkpoint-decision policy must be a separate descendant so threshold edits cannot redefine an already-realized training trajectory.
- `D1.DEF.025` foundation role-threshold family: change only the generated/default `tau_prod` from `30` to `50 meV/angstrom`; retain `tau_CV = theta_CV = 45 meV/angstrom` in this cycle.
- `D1.AX.009` / `D1.AX.010`: preserve fixed-budget CV and fresh production, but define hard replay retention as the catastrophic limit and replay-warning evidence as non-vetoing diagnostic evidence.
- D1 parameter ledger: add/clarify configurable replay warning/hard coordinates and update `tau_prod` default.
- checkpoint/final-publication ordering semantics: replace any imported uncertainty/secondary/maturity authority for P5 checkpoint choice with strict minimum authoritative target RMSE over the hard-admissible set; apply the same rule to `single_best_final_seed`.

The D1 revision must state at least:

1. TRUE_DFT replay is an auxiliary retention/forgetting observable for foundation adaptation, not the deployment target domain.
2. Moderate replay degradation is diagnostic evidence and does not by itself veto a target-competent checkpoint.
3. A separate conservative hard replay limit exists to reject catastrophic forgetting.
4. Replay warning/hard values are configurable policy parameters; defaults `0.050/0.100 eV/angstrom` are stakeholder-selected current defaults, not empirically universal constants.
5. Replay receives no positive ranking/tie-break credit.
6. P5 checkpoint representative quality ordering is minimum authoritative target force-component RMSE among hard-admissible checkpoints.
7. `single_best_final_seed` uses the same strict target-RMSE ordering across already-frozen admissible seed representatives; `all_qualified_final_seeds` remains unranked publication.
8. Foundation final-production target checkpoint quality defaults to `0.050 eV/angstrom`, configurable by policy; foundation CV remains `0.045/0.045` and scratch remains separately governed.
9. Downstream qualification remains separate and may still reject a frozen final publication for deployment/physics reasons.
10. Assessment-threshold/selection-policy changes that cannot influence training do not redefine the realized training trajectory.
11. Current CV authorization is a prerequisite for current final-production assessment/publication, but a change in CV decision policy does not by itself alter the bytes of an already-realized genuinely fresh final-production trajectory. Reuse is allowed only when current CV reclosure accepts and exact final-production training equivalence is proven; if current CV rejects, historical final-production bytes remain historical/nonpublishable.
12. Existing valid measurements may support a new current assessment only through explicit policy-bound reassessment; historical evidence is never rewritten or silently relabeled current.

### D1 challenge/falsification questions

The D1 renewal must explicitly challenge:

- whether `0.100 eV/angstrom` catastrophic replay degradation is too loose to protect inherited capability relevant to claimed target deployment;
- whether target-only ranking can select a checkpoint whose replay behavior, while under the hard ceiling, is scientifically unacceptable for any downstream use actually claimed by mdstats;
- whether raising production target default to `0.050 eV/angstrom` conflicts with observed downstream MD adequacy requirements;
- whether `tau_CV=0.045` with `tau_prod=0.050` is coherent: CV competence may be numerically stricter than production admission, but the roles/estimands remain distinct and this must be intentional rather than accidental;
- whether any current physical/integrity gate implicitly depended on the old `0.030` replay value;
- whether final cross-seed strict target ordering changes publication semantics in a way requiring a distinct D1 publication statement;
- whether D1.AX.010 fresh-production semantics permit reassessment of an already-realized fresh final trajectory after current CV reauthorization, provided no CV trajectory/checkpoint initialized that production run and every training-bearing parent is exact.

If those challenges establish a different accepted D1 rule, reconcile this plan before D2/D3 implementation.

## 4. D2 numerical-method renewal requirements

Reopen the accepted Protocol 6.4 numerical kernel. The principal current owners are `D2.DEF.057-059`, `D2.AX.004-005`, `D2.DEF.060/060A`, and the parameter ledger.

### 4.1 Replay numerical definitions

Replace the old single-budget clause in `D2.DEF.057` with exact authenticated replay classification:

```text
DeltaR = R_candidate - R_foundation
warning = DeltaR > delta_warn
hard_failure = DeltaR > delta_hard
```

with identical checkpoint/replay-domain/provider/metric semantics for both RMSE terms and exact current `Q_r` evidence. No epsilon, rounding-before-comparison, percentage normalization, absolute-value transform or relative fraction is introduced. Equality at either threshold passes the corresponding strict-`>` predicate.

`S(c)` remains the hard shared constraint conjunction, but finite authenticated replay contributes hard failure only for missing/invalid evidence, nonfinite metrics, or `DeltaR > delta_hard`; `delta_warn < DeltaR <= delta_hard` contributes diagnostic warning only.

### 4.2 Role-effective target predicate

Preserve `D2.DEF.058` form `A_rho(c)=S(c) and r_mon(c)<=tau_rho`, including inclusive binary64 target threshold semantics. Change generated/default `tau_prod` to `0.050 eV/angstrom`; leave `tau_CV` default `0.045` in this cycle.

### 4.3 Strict P5 target ordering

For the P5 full-checkpoint path:

```text
H = every fully evaluated checkpoint satisfying hard gates
winner = argmin_c in H r_mon(c)
```

The current P5 runtime already fully evaluates all durable checkpoints, so no new shortlist/rescue approximation is authorized. Practical-equivalence bands, paired bootstrap, secondary target metrics and refinement/maturity may remain as diagnostics or for unaffected non-P5 consumers, but cannot affect P5 representative identity.

For `single_best_final_seed`, apply the same ordering to already-frozen admissible per-seed representatives using their already-authenticated common-monitor metric records. No new target evaluation occurs. `all_qualified_final_seeds` remains unchanged.

### 4.4 Exact ties

Freeze exact binary64 ties rather than delegating them to D4:

- within one run: ascending `(epoch, checkpoint_sha256)`;
- across already-frozen production-seed representatives under `single_best_final_seed`: ascending `(optimizer_seed, representative_checkpoint_sha256)`.

These dimensions are consulted only after exact equality of authoritative target RMSE. No tolerance band, replay value, secondary target metric, maturity state or stochastic bootstrap may enter either tie.

### 4.5 Threshold units and validation

Public replay configuration may use meV/angstrom; internal policy values remain eV/angstrom. Defaults:

```text
replay warning = 50 meV/angstrom
replay hard    = 100 meV/angstrom
foundation production target = 50 meV/angstrom
```

Require finite positive replay limits and `warning < hard`; preserve full binary64 values for decisions.

### 4.6 Fixed-budget training and assessment equivalence

No target/replay threshold or checkpoint-selection policy in this plan may stop TRAIN2, change LR, epoch count, replay/target sampling, loss, optimizer state or checkpoint persistence.

Amend `D2.AX.004` currentness with distinct dependency classes:

- `delta_warn` changes diagnostic warning/report evidence only;
- `delta_hard` changes hard checkpoint assessments, representatives and dependent CV/final decisions;
- role target ceilings change their role's hard assessments and dependent decisions;
- strict P5 selection-rule identity changes representatives and dependent outer-evaluation/verdict/publication descendants;
- none of those edits changes an authenticated TRAIN2 trajectory whose training-affecting identity is unchanged.

Do not declare old verdicts current by monotonic implication: a current verdict must be newly assessed under the current hard-decision/selection policy. Reuse of an old numeric measurement is permitted only when exact measurement identity/equivalence is proven.

Amend `D2.DEF.060/060A` as needed to distinguish exact training continuation identity from later assessment-policy ancestry without weakening fail-closed restart authentication. For a pre-cutover interrupted trajectory, continuation may use the historical runtime-plan/protocol identity only after an explicit exact training-equivalence proof; do not rewrite its summaries/config/checkpoints to a new digest.

Amend `D2.AX.005` so current CV authorization remains mandatory for current production assessment/publication, while a historically fresh final-production trajectory may be reused after CV reclosure iff current CV accepts and exact production training-position equivalence is proven. A current CV rejection leaves the historical final trajectory noncurrent regardless of its checkpoint quality.

## 5. D3 ownership and dependency repair

### 5.1 Separate four dependency classes

The revised architecture must distinguish:

```text
TrainingTrajectoryIdentity
  training mode / foundation-head / gradient memberships
  objective + exposure + optimizer/LR + horizon/seed
  precision/backend/model architecture + checkpoint cadence
        |
        v
  authenticated TRAIN2 trajectory/checkpoint bytes

EvaluationMeasurementIdentity
  exact checkpoint/model state
  exact target or TRUE_DFT replay population/artifact
  metric policy/provider realization required for numerical meaning
        |
        v
  immutable numeric target/replay measurements

HardCheckpointDecisionPolicy
  role target ceiling
  replay catastrophic hard limit
  finite/integrity/physical hard gates
  strict P5 target-RMSE selection rule identity
        |
        v
  hard checkpoint assessment -> representative -> CV/final verdict/publication

ReplayWarningDiagnosticPolicy
  replay warning threshold only
        |
        v
  warning/report evidence only
```

These need not become four new classes. Prefer reusing existing owners and exposing separate dependency digests/projections where one resolver already owns the values. The architectural requirement is semantic separation, not type proliferation. In particular, the warning threshold must have no edge into hard checkpoint decision, representative, CV acceptance, production authorization or publication membership.

### 5.2 Narrow `PostSelectionMethodIdentity`

At baseline, `PostSelectionMethodIdentity` hashes two assessment-only coordinates:

```text
shared_checkpoint_constraints_digest
checkpoint_selection_policy_digest
```

Neither may remain in the TRAIN2 training-protocol identity after this revision if they contain only post-training assessment/selection semantics. Preserve genuinely training-bearing method fields. TRUE_DFT replay-monitor/data lineage may remain authenticated as required evaluation evidence without placing warning/hard numbers or target-ordering policy inside the training digest.

A one-time projection from the baseline `PostSelectionMethodIdentity` schema v3 may prove an existing historical method record training-equivalent to the new training identity by comparing every training-bearing field exactly and explicitly excluding only the retired assessment-only parents. This projection belongs in the existing currentness/recovery owner; it is not a general-purpose compatibility translator.

### 5.3 Freeze the training-trajectory / assessment-position split

Current `post_selection_run_identity()` hashes the complete CV/final plan digest. That is the wrong steady-state owner because the same filesystem root also carries training bytes and policy-bound terminal verdict files.

This workplan freezes one architecture rather than leaving two alternatives.

**Training trajectory identity.** Define one exact role-specific training-position projection and derive the post-selection run/checkpoint root from it. The projection includes every input capable of changing exact TRAIN2/materialization/restart behavior, including at least:

```text
run role
selected/fold gradient membership
optimizer seed + planned horizon
training-only PostSelectionMethodIdentity
objective / optimizer / LR / exposure / precision / backend / architecture
foundation checkpoint/head and replay-training lineage
target/replay validation artifacts when consumed by the trainer
common-monitor identity where preparation/runtime consumes it
composition-transfer required-composition set derived from governed consumers
checkpoint cadence and MACE execution semantics
```

It excludes only downstream checkpoint-decision, warning, CV outer-acceptance, committee/publication and other post-training policy coordinates.

For new records, `run_identity` / checkpoint-root identity must mean this training trajectory position, schema-bumped as needed. Full CV/final plan digests remain assessment/authorization parents, not restart/root identity.

**Training-owned records.** Rebind the training owners that currently carry full run-plan ancestry:

- `PostSelectionFittedPreparation.owner_plan_digest`;
- `PostSelectionMaterialization.run_plan_digest/run_identity`;
- checkpoint catalog/file lineage;
- generated post-selection MACE configuration identity/name;
- TRAIN2 runtime-plan/summary/continuation authentication.

They must bind the training-position authority while preserving every training-bearing field listed above. A policy-only edit must reproduce the same training-position digest. A changed training-bearing coordinate must not.

**No pre-training assessment dependency.** `_prepare_post_selection_run()` must not compose current checkpoint admissibility to decide whether replay training/TRUE_DFT runtime monitoring exists. Resolve replay execution from the training method/replay lineage. Construct hard checkpoint admissibility only when EVAL2 assessment begins.

Keep `reject_foreign_run_continuation()` fail-closed on the training trajectory identity. Never satisfy it by ignoring a digest, copying checkpoints, or substituting a different role.

### 5.4 Seal the training root before assessment

The baseline run root mixes two lifecycles: mutable TRAIN2 output and immutable policy verdict. That is incompatible with later policy-only reassessment because `fold-acceptance.json` / `run-evidence.json` are fixed create-once files and the topology anchor is create-once.

Post-cutover, the root under `runs/<training_trajectory_identity>` is **training-only**:

- materialization/config/checkpoints/runtime history live there;
- once TRAIN2 reaches an authenticated terminal training state, freeze the topology and completion anchor **before EVAL2**;
- use the existing complete `Train2RuntimeSummary` and authenticated checkpoint/runtime boundary as the terminal training proof rather than requiring an assessment verdict to exist;
- EVAL2 and later reassessment read the sealed root but never write assessment state into it.

Current policy-bound CV/final assessment evidence must live in the existing content-addressed post-selection evidence/currentness infrastructure outside the sealed training root. Each fold/final position needs a deterministic policy-bound locator/currentness record so restart can find the exact current assessment without scanning the object store. Extending the existing current-pointer/position owner is allowed; creating a second evidence store is not.

After cutover:

- stop writing current `fold-acceptance.json` and `run-evidence.json` into training roots;
- retain read-only support for those files in historical roots;
- a warning-threshold-only change may publish new diagnostic evidence without touching the sealed root or hard-assessment locator;
- a hard-policy/selection change publishes a new assessment record/locator over the same trajectory root.

The storage/topology owner must continue to certify a closed subtree and cold-storage semantics. Reassessment may consume only checkpoint/materialization bytes still available through an authenticated storage owner.

### 5.5 Separate evaluation measurement from assessment policy### 5.4 Separate evaluation measurement from assessment policy

Current `post_selection_eval_role_digest()` includes `run_plan_digest` and `run_identity`. That over-binds numeric measurement evidence to policy ancestry.

The current measurement owner must instead bind the exact factors that can change the numeric measurement: checkpoint/model realization, dataset role, exact membership/artifact bytes, metric/reduction policy, head/provider/precision semantics as applicable. Assessment thresholds and full role-plan digest must not be measurement identity.

Policy-bound checkpoint-assessment records may then consume immutable measurement records and produce current warnings/rejections/representatives. Historical baseline records may be reused only through a source-preserving derivation that proves the old measurement inputs equal the current measurement identity; never copy a scalar without its authenticated checkpoint/population/provider ancestry.

### 5.6 Role target default isolation

Current `[acceptance].maximum_target_force_rmse_ev_per_angstrom` supplies production for every mode and scratch CV. Preserve the single explicit public field. Change only omitted/default resolution:

```text
foundation final production omission -> 0.050
scratch omission -> existing accepted 0.030
explicit value -> preserved as written for the consumers that already own it
foundation CV -> its existing independent 0.045 checkpoint default
```

Use the existing mode-aware role-policy resolver. Do not add a duplicate production-target knob.

### 5.7 Shared replay assessment policy

Replay hard limit is a shared checkpoint-decision coordinate for CV/final replay-enabled foundation adaptation. It moves hard checkpoint assessments, representatives and dependent CV/final decisions in both roles while leaving the training trajectory current.

Replay warning threshold is a separate diagnostic-only coordinate. It must not be included in a digest whose change stales hard admissibility, representative selection, CV acceptance, production authorization or publication membership. Resolve both values once from the same configuration owner, but preserve distinct dependency projections. This does not require a second policy graph: one resolver may expose a hard-decision digest plus a diagnostic-warning digest/value.

### 5.8 Publication ordering

`single_best_final_seed` currently imports the old EVAL2 uncertainty/secondary/maturity ordering and has a dedicated decision-policy identity. Update that decision-policy identity/schema as needed so strict minimum target RMSE is reconstructable from publication evidence. `all_qualified_final_seeds` is unaffected.

### 5.9 No second policy graph

Do not add a shadow replay-policy registry, checkpoint-selection wrapper, mutable alias, second cache keyed only by thresholds, or second evidence store. The one training-position projection required by section 5.3 is the replacement restart/root owner, not a parallel training protocol. Current role plans remain assessment/authorization parents and existing evidence/currentness infrastructure owns assessment locators.

### 5.10 Currentness model

Expected steady-state invalidation:

```text
change replay warning threshold
  -> replay warning/report evidence only
  -> hard checkpoint assessment, representative, outer evaluation, CV acceptance,
     production authorization, publication membership, numeric measurements and
     TRAIN2 trajectory remain current

change replay hard threshold
  -> checkpoint assessments/representative + dependent verdict/publication move
  -> numeric measurements and TRAIN2 trajectory remain current

change production target threshold
  -> production assessments/representative/publication move
  -> production TRAIN2 trajectory and sealed training root remain current
  -> accepted CV remains current because its policy did not move

change strict P5 selection rule identity
  -> representative/verdict/publication descendants move
  -> numeric measurements and TRAIN2 trajectory remain current

change LR/loss/exposure/foundation/training membership/seed/horizon,
or another training-position input such as required preparation/validation lineage
  -> training trajectory identity moves; restart/reuse fails closed as today

change evaluation population/metric/provider semantics
  -> numeric measurement identity moves; reassessment cannot reuse stale measurements
```

This separation must be reconstructable from persisted ancestry without consulting this workplan.

## 6. D4 implementation contract

Implementation begins only after Gates B and C close on accepted amended D1/D2 and Gate D freezes the required D3 identity/currentness repair.

### 6.1 Hard admissibility versus replay diagnostics

Replace the single replay budget in `CheckpointAdmissibilityPolicy` with the catastrophic hard limit only:

```text
replay_degradation_hard_limit_ev_per_angstrom = 0.100
```

The role-effective target ceiling, TRUE_DFT requirement, finite checks and existing hard physical/integrity gates remain in that hard-decision policy. Advance its schema because hard replay semantics materially change.

Resolve the soft threshold separately as diagnostic-only configuration:

```text
replay_degradation_warning_ev_per_angstrom = 0.050
```

Do **not** put the warning threshold into the hard-admissibility policy digest, representative-selection digest, CV acceptance identity, production authorization, or publication-membership identity. Whether D4 represents the warning coordinate as a tiny diagnostic policy object or a diagnostic projection from the existing resolver is delegated; it must have no decision edge.

Expose hard failures and warning diagnostics separately, conceptually:

```text
failure_reasons(...)
diagnostic_warnings(...)
```

Recommended codes:

```text
warning:
  replay_degradation_warning_threshold_exceeded

hard rejection:
  replay_catastrophic_forgetting_limit_exceeded
```

A checkpoint above the hard limit may carry both the warning and rejection because both predicates are true.

Keep missing/nonfinite TRUE_DFT replay evidence as hard failure codes.

### 6.2 Target default

Change the resolved default for foundation final-production checkpoint target-force RMSE to:

```text
0.050 eV/angstrom
```

Preserve explicit user values.

Do not implicitly change foundation CV or scratch defaults; this workplan explicitly keeps their accepted baseline defaults unchanged.

### 6.3 Selection implementation

Replace P5 representative selection with deterministic minimum authoritative target RMSE over hard-admissible candidates. Baseline P5 already evaluates the full durable trajectory, so this is an ordering-only change.

Current P5 calls `select_cv_fold_representative()` -> `order_eval2_admissible_candidates()`, whose practical-equivalence bands, paired bootstrap, secondary target metrics and maturity ordering can promote a strictly worse primary RMSE. Remove that authority from P5. Do not add a `strict_minimum` switch to the old algorithm merely to preserve one function call.

First census non-P5 consumers of `order_eval2_admissible_candidates()` / generic `Eval2RunRecord`. If they legitimately retain the old uncertainty-aware algorithm, leave it scoped there and make the P5 owner directly select the minimum. If P5 is the only live consumer requiring ordering, simplify/retire the obsolete P5 policy fields and identity bindings.

Apply the same strict target ordering in `post_selection_publication.py` for `single_best_final_seed`; advance its decision-policy identity/schema if necessary. `all_qualified_final_seeds` remains unchanged.

### 6.4 EVAL2 measurement and checkpoint evidence

Do not advance `Eval2CheckpointRecord` merely to embed a warning bit whose threshold is diagnostic-only. The existing signed replay degradation is sufficient to derive the current warning. If durable warning reporting is required, persist it in diagnostic evidence whose digest is not an admissibility/selection parent.

The future numeric measurement identity must be assessment-independent and directly bind enough provenance to prove reuse without interpreting a full role plan: checkpoint/model-state identity, exact evaluation artifact/membership, metric/reduction policy, prediction/provider/model realization semantics, head and precision where numerically material. Because current `Eval2TargetMetricRecord.target_role_digest` / `prediction_digest` inherit full run-plan ancestry, advance the measurement schema or role/prediction identity schema when that meaning changes rather than silently reusing the old schema token.

Historical checkpoint/metric records remain immutable/readable under their historical schema. Do not rewrite old `admissible` bits or old rejection reasons in place. A current reassessment may reuse historical numeric values only after an explicit proof of exact measurement equivalence; otherwise recompute EVAL2 from the preserved checkpoint.

### 6.5 Final-production candidate-set and negative evidence persistence

Repair both the negative-evidence defect and the successful-run candidate-set gap at the same assessment owner:

- persist preparation/materialization as appropriate;
- persist every evaluated EVAL2 checkpoint assessment;
- bind the **complete ordered candidate-record digest set** in terminal run assessment evidence for successful and no-admissible outcomes;
- for a selected run, bind the representative as a member of that candidate set;
- for a no-admissible run, publish a typed terminal methodological outcome that binds the candidate set before surfacing the terminal failure.

Baseline `PostSelectionRunEvidence` does not bind candidate-record digests, so merely storing candidate objects is insufficient for future reselection. Do not discover candidates later by content-store scanning or filename heuristics.

CV already binds candidate digests in current fold-acceptance evidence. Production must achieve the same reconstructability without creating a second evaluator.

This is required for future policy reassessment and diagnostic transparency; it does not permit promotion of an inadmissible checkpoint.

### 6.6 User-visible diagnostics

For every replay-enabled checkpoint, make the following reconstructable and preferably visible in bounded diagnostics:

```text
epoch/checkpoint identity
target RMSE
role target ceiling and target margin
candidate replay RMSE
foundation replay RMSE
signed replay degradation
warning threshold and warning margin
hard replay limit and hard margin
warning codes
hard rejection reasons
selected representative flag
```

A run-level warning should summarize when the selected representative exceeds the replay warning threshold without presenting that warning as a failure.

---

## 7. Configuration migration

### 7.1 Schema-versioned cutover

Bump the current campaign configuration schema from `mdstats.mlff-campaign-cli.v2` to a new v3 contract for newly generated configuration. Continue to read v2 only through an explicit migration resolver; do not mutate campaign TOML in place.

This is a **three-generation parser contract**, not a rename of the existing constant:

```text
schema-less / v1 -> historical pre-v2 normalization only
v2               -> prior modern campaign contract + bounded v2->v3 policy migration
v3               -> current campaign contract
```

Implementation must preserve a distinct named v2 schema token after introducing v3. `_load_config()` must accept v1, v2 and v3 explicitly. Every schema discriminator that currently tests `schema == CAMPAIGN_CLI_SCHEMA` must be audited before changing the current token: in particular, `_normalize_target_size_fidelity_config()` must treat **both v2 and v3** as the modern `fidelity_epochs` contract and reserve the historical fixed-`3/10/30` branch for schema-less/v1 only. A v2 file must never become "historical v1" merely because v3 became current.

The generator/`init` path emits v3 only after this reader compatibility is in place.

New v3 generated/current replay fields are:

```toml
[acceptance]
replay_degradation_warning_mev_per_a = 50.0
replay_degradation_hard_limit_mev_per_a = 100.0
```

The historical one-number field:

```toml
allowed_replay_degradation_mev_per_a = 30.0
```

is invalid in v3.

The existing public target field remains:

```toml
maximum_target_force_rmse_ev_per_angstrom = ...
```

but its omitted/generated default is mode-aware in v3: foundation final production resolves/generates `0.050`; scratch retains its accepted `0.030`; foundation CV retains its separate `0.045` owner.

### 7.2 v2 replay migration

For a v2 TRAIN2 campaign with exactly the historical generated/default replay field `allowed_replay_degradation_mev_per_a = 30.0` and neither new replay field present:

- recognize that value as the superseded v2 generated default;
- resolve current replay policy to `50.0/100.0 meV/angstrom`;
- emit a bounded migration/deprecation notice;
- do not retain `30.0` as a hidden hard gate.

If the v2 one-number replay value is non-default/custom, fail with an actionable migration error rather than guessing whether it maps to warning or hard rejection.

If legacy and new replay fields coexist, fail closed. Do not silently make one "win" while leaving a second visible authority in the file.

### 7.3 v2 foundation-production target migration

The shipped v2 template explicitly writes `maximum_target_force_rmse_ev_per_angstrom = 0.030`; therefore omission-only default changes are insufficient.

For **foundation-adaptation v2** campaigns:

- an absent target field or exact historical generated value `0.030` resolves to the new foundation-production default `0.050`;
- a non-`0.030` finite positive v2 value is preserved as an explicit legacy override;
- the migration affects production target admission only; foundation CV remains `0.045/0.045`.

This deliberately treats an exact v2 `0.030` as the historical generated default because v2 carries no provenance that can distinguish "generated 0.030" from "user retyped the same default". A user who intentionally wants `0.030` after the cutover must migrate the file to v3 and set `0.030` explicitly there.

For **scratch v2** campaigns, `0.030` retains its historical scratch meaning and is not migrated to `0.050`.

Schema-less/v1 historical campaigns retain their own historical policy generation and are not silently converted into this TRAIN2 policy family.

### 7.4 v3 explicit values and validation

Under v3:

- explicit `maximum_target_force_rmse_ev_per_angstrom = 0.030` is a lawful intentional override and must be preserved;
- explicit replay warning/hard values are used exactly after validation;
- require finite positive values and `warning < hard`;
- reject booleans, strings, NaN and infinity at the policy boundary;
- omission and explicit current defaults must yield identical resolved policy identities;
- generated template, `init` output, shipped example, CLI specification and user guide must converge on the same v3 contract;
- the shipped `[evaluation]` comments must no longer claim that refinement reservation, practical-equivalence/bootstrap, secondary metrics or maturity control **P5** representative selection. Generic EVAL2 configuration may remain only for unaffected consumers with its scope stated accurately.

## 8. Reuse and migration of existing training/evidence

### 8.1 Governing invariant

The repair must prove:

```text
A checkpoint-assessment-policy-only change cannot force retraining of an otherwise identical authenticated TRAIN2 trajectory.
```

### 8.2 Do not rewrite history

Never edit old checkpoint bytes, TRAIN2 histories, runtime summaries, materialization records, content digests or historical policy records to make them appear newly generated.

Historical identity remains historical.

Reuse is authorized by proving training-semantic equivalence, not by changing hashes.

### 8.3 Training-equivalence classification

The existing currentness/recovery owner must admit an old trajectory for current reassessment when all trajectory-affecting inputs agree, including at least:

```text
foundation checkpoint/head
training mode
target gradient membership
replay training membership and label mode
objective/loss
residual E0 preparation
exposure semantics
optimizer settings
LR schedule
seed
planned epochs
checkpoint cadence
precision/backend
model architecture
MACE execution semantics
```

and the only difference is assessment-policy ancestry that could not alter training.

Do not implement this as a broad "ignore method digest" exception. Compare the semantically relevant owners or introduce the minimum accepted split in identity authority so future records no longer require an exception.

For the exact baseline `PostSelectionMethodIdentity` schema-v3 method/run lineage, the migration proof must cover all three old over-bindings:

1. old `PostSelectionMethodIdentity` -> new training identity, excluding only `shared_checkpoint_constraints_digest` and `checkpoint_selection_policy_digest` after proving all training-bearing fields equal;
2. old full-plan-derived run/checkpoint root -> current training-position identity, proving role/fold membership/seed/horizon and all training-bearing parents equal;
3. old plan-bound evaluation role -> current measurement identity, proving checkpoint SHA/model state, exact evaluation artifact/membership, metric policy/provider semantics and prediction digest equal.

Only after those proofs may current assessment reuse the old trajectory/measurement. A mismatch at any layer fails closed.

### 8.4 Historical measurement reuse is conditional, not presumed

Baseline historical EVAL2 records are not a universally sufficient measurement cache. Their role/prediction digests include old run-plan ancestry, raw predictions are not persisted, and the record itself does not directly expose every checkpoint/artifact/provider parent needed by the new assessment-independent measurement identity.

Therefore:

1. Reuse a historical numeric measurement only when the existing durable run/materialization/checkpoint/evaluation ancestry can be reconstructed and proves exact current measurement equivalence.
2. Never infer equivalence merely because scalar RMSE values match or because the old checkpoint record is readable.
3. If the proof is incomplete, rerun **EVAL2 only** from the authenticated preserved checkpoint and exact current evaluation artifact/provider semantics.
4. Failure to reuse a historical measurement must never by itself trigger TRAIN2 retraining when training-equivalence proof succeeds.

Future post-cutover measurement records must bind the clean measurement identity directly so later hard-policy/selection edits can reassess without inference.

### 8.5 Reclose every affected historical CV fold, not only negative folds

The strict target-minimum selection rule and replay hard-limit change can alter a fold representative even when that fold previously passed. Therefore all affected historical P5 CV folds must be reassessed under the new hard decision/selection policy.

For each fold:

- reuse the authenticated TRAIN2 trajectory when training-equivalent;
- reuse candidate numeric measurements only when section 8.4 proves exact equivalence, otherwise recompute EVAL2 from preserved checkpoints;
- select the strict minimum-target hard-admissible checkpoint under the new rule;
- if the representative is unchanged and the old outer-fold metric has exact current measurement ancestry, reuse that outer measurement;
- if the representative changes, or old outer-measurement equivalence cannot be proven, evaluate only the required outer fold for the newly selected representative;
- publish a new fold/seed/campaign acceptance under current policy.

No old CV acceptance is relabeled current in place. Because this cycle changes shared replay hard-decision and P5 selection semantics, any affected prior CV authorization must be reclosed before it can authorize current final production, even though TRAIN2 itself is reusable.

### 8.6 Historical final-production runs

Baseline successful final-production `PostSelectionRunEvidence` does not bind the complete candidate-record set. Consequently the cutover must not reverse-scan the evidence store to reconstruct a candidate list.

For an old successful final-production trajectory:

- reuse TRAIN2 when training-equivalent;
- if a complete historical candidate set is independently and authentically bound by another durable owner, section 8.4 may permit measurement reuse;
- otherwise recompute full P5 EVAL2 over the preserved durable checkpoints and select under the new rule;
- publish new current run-assessment/representative evidence without rewriting the historical run evidence.

For the diagnosed failed 40-epoch production workspace, old candidate assessments were not persisted at all:

```text
TRAIN2 checkpoints/history -> reuse
training -> do not relaunch
EVAL2 -> recompute
representative -> strict minimum target RMSE among current hard-admissible checkpoints
```

After section 6.5 is implemented, future successful and negative production results bind the complete candidate set so later policy-only reassessment need not rediscover or re-infer it.

### 8.7 Legacy run-root locator during the one-time identity cutover

A new clean training-position identity does not rename or invalidate a sealed legacy run root.

During the one-time v3 identity migration:

- derive the legacy source run identity/root only from authenticated stored historical CV/final plan and run-position evidence;
- validate the existing completion/topology ownership records before consuming checkpoints;
- never locate a legacy run by scanning `runs/`, guessing hashes, newest-mtime choice, or content-store reverse lookup;
- never rename, copy, rewrite or symlink a sealed legacy root merely to make its pathname match the new identity;
- if a durable mapping is required, permit at most one immutable per-trajectory reuse binding at the existing currentness owner that records old run identity/root, new training-position identity and the exact equivalence proof. Do not create a registry or shadow run namespace.

Newly created post-cutover trajectories use the corrected training-position identity directly, so this compatibility edge is one-time historical migration rather than steady-state dual identity.

## 9. Historical Applicability Set

Project engineering memory is applicable because this cycle changes mature P5 identity/currentness and revisits a documented replay-forgetting recurrence. At baseline `a759e81...`, the repository PEM is present in current main but remains explicitly reconciled only through `4eabe2ae9783c7ff92f3a1093c37502a01380812`; the Protocol 6.4 documentation merge did not itself refresh PEM. Use the evidence-backed entries below and refresh the basis if PEM advances before closeout.

```yaml
pem_basis:
  current_project_state: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
  published_pem_reconciled_through: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  candidate_overlay_semantic_candidate: NONE
has:

  - id: FF-002
    disposition: APPLICABLE
    reason: Currentness must distinguish genuinely incompatible historical training semantics from policy-only assessment changes; old incompatible trajectories must still fail closed.

  - id: SP-001
    disposition: APPLICABLE
    reason: Remove the replay threshold from over-broad training identity rather than add compatibility wrappers, shadow policy owners or duplicated checkpoint-selection paths.

  - id: SP-002
    disposition: APPLICABLE
    reason: Method, role-policy, run-plan, assessment and recovery boundaries must remain explicit and fail closed when a true semantic mismatch occurs.

  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve valid immutable selection, replay source/split/cache, common-monitor, foundation, TRAIN2 checkpoint and measurement evidence rather than globally invalidating it.

  - id: SP-004
    disposition: APPLICABLE
    reason: Qualification must exercise the real cross-validate/train-production -> TRAIN2 recovery -> full EVAL2 -> representative -> verdict/publication path, including old-workspace reuse.
```

Also review the post-selection restoration recurrence record that required D1/D2 reopening if correctly restored TRUE_DFT replay still showed material forgetting inconsistent with accepted gates.

---

## 10. Falsification and regression matrix

### 10.1 Replay boundary semantics

1. `DeltaR = 0.050000...` -> admissible, no replay warning.
2. `DeltaR` just above `0.050` and below/equal `0.100` -> admissible + warning.
3. `DeltaR = 0.100000...` -> admissible + warning.
4. `DeltaR` just above `0.100` -> warning + hard catastrophic rejection.
5. Negative replay degradation -> admissible with no warning unless another gate fails.
6. Missing TRUE_DFT evidence -> hard failure unchanged.
7. Nonfinite candidate/foundation replay metric -> hard failure unchanged.

### 10.2 Target default and isolation

8. Foundation final-production omission resolves target ceiling to exactly `0.050 eV/angstrom`.
9. Explicit production target value is preserved exactly.
10. A foundation production checkpoint at `0.049` is target-admissible when other hard gates pass.
11. A checkpoint above the configured target ceiling is target-inadmissible regardless of replay quality.
12. Foundation CV defaults remain exactly `0.045/0.045` in this cycle and P5 scratch default remains `0.030`; prove the production-default edit cannot leak into either.
13. Scratch target semantics remain unchanged unless separately ratified.
14. A production-only target-threshold edit does not move training identity or accepted CV evidence whose governing policy is unchanged.

### 10.3 Selection rule

15. Among two hard-admissible candidates, the lower authoritative target RMSE always wins.
16. A higher-target-RMSE checkpoint cannot win because it has better replay retention.
17. A higher-target-RMSE checkpoint cannot win because it is below warning while the better target checkpoint has a replay warning.
18. A higher-target-RMSE checkpoint cannot win through secondary target metrics.
19. A higher-target-RMSE checkpoint cannot win through refinement/maturity preference.
20. A higher-target-RMSE checkpoint cannot win through practical-equivalence or bootstrap-band logic.
21. Exact within-run target-RMSE ties resolve by ascending `(epoch, checkpoint_sha256)`; exact cross-seed ties resolve by ascending `(optimizer_seed, representative_checkpoint_sha256)`.
22. The real P5 path evaluates all durable checkpoints before claiming the global target minimum.

### 10.4 Configuration

23. Defaults resolve to replay `50/100 meV/angstrom` and production target `50 meV/angstrom`.
24. `warning >= hard` fails.
25. zero, negative, boolean, string, NaN and infinity fail.
26. omitted new fields and explicit default values yield identical policy identity.
27. recognized historical generated `allowed_replay_degradation_mev_per_a = 30.0` migrates to current defaults and does not resurrect the old hard gate.
28. historical non-default one-number replay configuration fails actionable migration unless explicitly converted.
29. generated template, shipped example, CLI spec and guide agree.

### 10.5 Currentness/recovery

30. Editing only replay warning threshold changes warning/report evidence only: it does not relaunch TRAIN2 and does not stale hard assessment, representative, outer evaluation, CV acceptance, production authorization or publication membership.
31. Editing only replay hard limit does not relaunch TRAIN2 but does stale/rebuild hard assessments and dependent representatives/verdicts.
32. Editing only production target ceiling does not relaunch TRAIN2.
33. Editing LR/loss/exposure/foundation/replay training membership/seed/epoch budget still invalidates affected TRAIN2 evidence as today.
34. Old checkpoint SHA-256 values remain unchanged through reassessment.
35. Old runtime summaries/history are not rewritten.
36. Old EVAL2 measurements are reused only when exact measurement ancestry is provable; otherwise EVAL2 is recomputed from preserved checkpoints with zero TRAIN2 launch.
37. Reassessment creates current verdict/assessment evidence rather than mutating old evidence.
38. A replay-threshold-only or strict-selection-policy-only change leaves the resolved training-position identity unchanged.
39. A production-target-threshold-only change leaves the resolved production training-position identity unchanged while changing production assessment policy.
40. Changing fold gradient membership, seed, horizon, objective, exposure or foundation changes training-position identity and foreign continuation remains rejected.
41. The same checkpoint + exact evaluation artifact + metric/provider policy resolves identical measurement identity across assessment-policy-only edits.
42. Changing checkpoint SHA, monitor membership/artifact, metric policy or provider semantics changes measurement identity and prevents metric reuse.

### 10.6 CV/final integration

43. Every affected historical CV fold, including previously successful folds, is reselected under the strict target-minimum/current hard policy without TRAIN2 retraining.
44. A previously no-admissible fold can obtain a representative from reusable/recomputed EVAL2 evidence; a previously successful fold may change representative. Outer evaluation is reused only for the same representative with proven measurement equivalence, otherwise only the required outer evaluation is rerun.
45. A historical CV verdict is never relabeled current merely by monotonic implication. Reuse its authenticated TRAIN2/measurement evidence where valid, then publish a new current fold/campaign assessment under the new policy; foundation CV target/outer thresholds themselves remain unchanged.
46. Final production with completed TRAIN2 resumes at EVAL2 without training relaunch.
47. Final-production all-inadmissible assessment persists all candidate records before terminal failure.
48. A selected warning-bearing representative publishes with a visible warning and no false failure state.
49. A selected representative above the hard replay limit is impossible.
50. `single_best_final_seed` chooses the lower authoritative target RMSE even when the other seed has better replay margin, secondary metrics, maturity or bootstrap evidence.
51. `all_qualified_final_seeds` publishes every already-qualified required representative without cross-seed ranking.
52. Changing the strict single-best publication ordering identity stales only dependent publication decisions, not per-seed TRAIN2 trajectories or numeric common-monitor measurements.
53. A post-cutover successful production run binds the complete ordered candidate-record set; a no-admissible terminal result binds the same set before failure publication.
54. A historical successful production run whose candidate set is not durably enumerable recomputes EVAL2 from preserved checkpoints rather than scanning the evidence store or retraining.
55. v2 foundation configuration with generated target `0.030` migrates to production `0.050`; v3 explicit `0.030` remains exactly `0.030`; scratch v2 `0.030` remains unchanged.
56. v2 replay `30.0` migrates to `50/100`; v2 custom one-number replay fails actionable migration; v3 rejects the retired one-number field and mixed old/new replay authority.
57. Legacy run-root reuse derives its source locator from authenticated historical plan/run evidence and preserves the sealed legacy topology without rename/copy/symlink.
58. A v2 campaign containing the modern `fidelity_epochs` tuple loads through the v2-modern parser path after v3 is introduced; it is not routed through schema-less/v1 fixed-`3/10/30` normalization, while the bounded target/replay policy migration still applies.
59. Config-loader tests cover every schema discriminator affected by changing the current campaign schema token, so v2 compatibility is explicit rather than accidental.
60. The v3 shipped example and generated config no longer describe bootstrap/refinement/secondary ordering as P5 representative authority.

### 10.7 Real-run oracle from the observed trajectory

With `R0 ~= 0.07934333 eV/angstrom`:

```text
warning absolute replay level ~= 0.12934333 eV/angstrom
hard absolute replay level    ~= 0.17934333 eV/angstrom
```

TRAIN2 diagnostic expectations:

```text
epoch 7:  DeltaR ~= 0.03527 -> no replay warning
epoch 8:  DeltaR ~= 0.05178 -> replay warning, not replay rejection
epoch 21: DeltaR ~= 0.07572 -> replay warning, not replay rejection
epoch 40: DeltaR ~= 0.08908 -> replay warning, not replay rejection
```

No observed epoch crosses the proposed catastrophic hard limit. The authoritative EVAL2 representative must still be chosen from authoritative EVAL2 target metrics, not these lightweight TRAIN2 target diagnostics.

---

## 11. Affected source and documentation surface confirmed at baseline review

Against `a759e81...`, the minimum affected implementation/documentation surface includes:

```text
D1/D2 authority
  docs/methods/mlff_scientific_method.md
  docs/methods/mlff_numerical_algorithmic_method.md

D3/D4 authority/specification
  docs/arch_manuals/mlff_training_data/40_training_evaluation.md
  docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
  docs/specs/training_data/mlff_post_selection_p5_spec.md
  docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
  docs/guides/mlff_campaign_cli_user_guide.md

Policy/identity/configuration
  mdstats/training_data/train2_policy.py
  mdstats/training_data/post_selection_identity.py
  mdstats/training_data/_campaign_cli_core.py
  campaign.toml.example

EVAL2/selection/runtime/recovery
  mdstats/training_data/eval2.py
  mdstats/training_data/post_selection_cv_acceptance.py
  mdstats/training_data/campaign_post_selection_runtime.py
  mdstats/training_data/post_selection_execution.py
  mdstats/training_data/post_selection_run_identity.py
  mdstats/training_data/post_selection_cv_plan.py
  mdstats/training_data/post_selection_production.py
  mdstats/training_data/post_selection_publication.py
  mdstats/training_data/train2_runtime.py (only where training-protocol/run identity authentication must be narrowed)

Public exports
  mdstats/training_data/__init__.py
  mdstats/__init__.py

Focused tests
  tests/test_mlff_train2a_policy.py
  tests/test_mlff_train2a_specification.py
  tests/test_mlff_train2b_specification.py
  tests/test_mlff_eval2.py
  tests/test_mlff_p5_cv_competence_threshold_separation.py
  tests/test_mlff_p5_cv_no_admissible_outcome.py
  tests/test_mlff_target_size_p5_r6_guards.py
  tests/test_mlff_target_size_p5_r7_guards.py
  tests/test_mlff_target_size_p5_r8_guards.py
  affected scheduler/recovery/integration suites identified transitively
```

Do not treat this list as exhaustive. Re-run transitive symbol/ancestry search immediately before code edits and again during independent assembled review.

---

## 12. Explicit non-goals

This cycle does **not** authorize:

- changing the TRAIN2 learning-rate schedule;
- changing the `512 : ~10,000` target/replay exposure ratio;
- adding target/replay head scalar weights;
- adding a balancing sampler;
- restoring hidden MACE target duplication;
- changing UniversalLoss;
- changing replay geometry membership;
- switching TRUE_DFT replay back to pseudo labels;
- changing E0 transfer semantics;
- changing target-size selection;
- changing CV fold construction;
- changing downstream MD/physical qualification;
- changing GPU scheduler/concurrency behavior;
- creating a second checkpoint-selection or evidence subsystem;
- rewriting historical hashes or evidence records;
- running production-scale GPU qualification before the final complete release package.

LR schedule and target/replay exposure remain a separate D2 investigation motivated by the same trajectory, but they must not expand this narrow policy/currentness repair.

---

## 13. Gate plan

### Gate A - Baseline reconciliation - CLOSED / PASS

Closed against `main` `a759e81...` after Protocol 6.4 D1/D2 renewal merged.

Confirmed:

- accepted D1/D2 still carry old hard replay retention, `tau_prod=0.030`, and imported uncertainty-aware target ordering;
- executable P5 still carries old `0.030` replay hard budget and production default;
- P5 evaluates the full durable checkpoint trajectory already;
- replay threshold **and checkpoint selection policy** are over-bound into `PostSelectionMethodIdentity` / TRAIN2 protocol;
- full role-plan digest over-binds run identity;
- run-plan identity over-binds evaluation metric role identity;
- `single_best_final_seed` imports the same old ordering;
- warning-only currentness needs a diagnostic-only dependency edge;
- v2 generated configs explicitly store old target/replay defaults and therefore require schema-aware migration;
- old EVAL2 records do not universally prove clean measurement identity;
- successful production evidence does not bind the full candidate set;
- positive as well as negative historical CV outcomes require reselection under the new rule;
- legacy sealed run roots require authenticated locator migration;
- published PEM at current main remains reconciled only through `4eabe2ae...`, so HAS uses those evidence-backed entries without pretending PEM itself was refreshed by the Protocol 6.4 documentation merge.

Branch opened from exact baseline: `design/mlff-replay-retention-target-admissibility-rework`.

### Gate B - D1 renewal for replay role and production target quality

Formally amend and independently review:

- replay warning vs catastrophic rejection semantics;
- target-only minimum-RMSE representative rule;
- configurable defaults `0.050/0.100` replay and `0.050` foundation-production target;
- downstream qualification separation;
- evidence-reuse interpretation.

Close only after independent Protocol 6.4 D1 falsification PASS and explicit stakeholder ratification of this new amendment.

### Gate C - D2 numerical renewal

Formally define:

- signed degradation and exact comparisons;
- unit conversions/default validation;
- strict minimum target ordering;
- exact tie rule;
- fixed-budget independence;
- replay warning/rejection numerical oracle;
- old-measurement reassessment equivalence.

Independent Protocol 6.4 D2 review is required after D1 acceptance; D2 may not pre-accept the requested numbers/order by implementation precedent.

### Gate D - D3 authority/currentness reconciliation

Before code edits:

- remove replay hard/diagnostic thresholds **and P5 checkpoint-selection policy** from training identity at the accepted owner;
- freeze the dependency graph distinguishing training trajectory, numeric measurement, hard checkpoint decision, and warning-only diagnostic policy;
- repair run/checkpoint ownership so policy-only role-plan edits resolve to the same training trajectory without weakening foreign-run rejection;
- define the one-time authenticated legacy run-root locator/reuse binding without rename/copy/scan machinery;
- repair measurement ancestry so future policy-only edits can reuse exact measurements, while historical records fall back to EVAL2 recomputation when proof is incomplete;
- bind the complete final-production candidate set in terminal run assessment evidence;
- prove currentness/recovery can preserve old TRAIN2 without a shadow compatibility subsystem;
- freeze current evidence/schema evolution boundaries;
- reconcile v2->v3 target/replay configuration migration without collateral scratch/CV change;
- preserve v2 as a distinct prior-modern parser contract across every schema discriminator; do not let a v3 token bump route v2 through historical v1 normalization.

Independent D3 review required if durable architecture changes.

### Gate E - D4 implementation

Implement by reduction/rewiring at current owners:

- hard replay-limit policy plus diagnostic-only warning threshold;
- foundation-production target default and v2->v3 migration, including explicit v2 parser compatibility;
- strict target-minimum representative selection with frozen exact ties;
- assessment-independent future measurement identity;
- complete production candidate-set binding and negative-production evidence persistence;
- one-time legacy trajectory/run-root reuse;
- currentness/recovery narrowing;
- diagnostics and docs.

Do not introduce a new parallel trainer/evaluator/policy graph.

### Gate F - Focused and affected regression

Execute the complete matrix in section 10 through real semantic owners.

Include an old-workspace recovery fixture whose only obsolete ancestry is the former replay threshold binding. Prove zero training launch.
### Gate G - Bounded real scientific qualification

After CPU/real-owner correctness passes, use a bounded representative real-data run to confirm:

- target-minimum selection;
- replay warning behavior;
- no replay rejection below hard limit;
- target gate behavior;
- old-checkpoint recovery where available.

Do not require production-scale GPU qualification here. Per project policy, defer GPU qualification until the final complete release package is ready for the user's machine.

### Gate H - Independent assembled Protocol 6.4 Review and closeout

Independent review reconstructs D1-D4 and attempts to falsify:

- accidental replay ranking credit;
- stale `0.030` hard replay gate;
- stale `0.030` foundation-production target default;
- secondary/uncertainty target ordering overriding raw target minimum;
- retraining on policy-only edits;
- silent legacy custom-config reinterpretation;
- historical evidence mutation;
- scratch/CV collateral changes;
- duplicate policy/currentness machinery;
- missing negative-production EVAL2 persistence.

Close only after affected documentation/history/dependency and PEM learning assessment are reconciled.

---

## 14. Acceptance criteria

The cycle may close only when all of the following are true:

1. A new Protocol 6.4 D1/D2 amendment from baseline `a759e81...` explicitly authorizes the new semantics and passes independent review/ratification.
2. Replay warning default is `0.050 eV/angstrom` and hard catastrophic default is `0.100 eV/angstrom`, both configurable; warning-threshold changes have diagnostic-only currentness.
3. Foundation final-production target default is `0.050 eV/angstrom`, configurable; foundation CV remains `0.045/0.045` and scratch remains separately governed.
4. Representative selection is minimum authoritative target force RMSE among hard-admissible checkpoints, with deterministic exact-tie handling only.
5. `single_best_final_seed` uses the same strict target-RMSE ordering across already-frozen admissible seed representatives; `all_qualified_final_seeds` is unchanged.
6. Replay warning/margin, secondary target diagnostics, maturity, practical-equivalence and bootstrap uncertainty cannot override a strictly better target RMSE.
7. Replay warning alone never rejects a checkpoint; `DeltaR > 0.100` under defaults rejects as catastrophic forgetting.
8. TRAIN2 remains fixed-budget and threshold/selection-policy independent.
9. Replay assessment thresholds and P5 checkpoint-selection policy are no longer training-trajectory identity.
10. Policy-only role-plan edits do not create a distinct training trajectory owner; genuinely different training positions remain fail-closed for continuation.
11. Future evaluation measurement identity does not change solely because assessment policy/run-plan identity changes; reuse still requires exact checkpoint/population/provider/metric equivalence.
12. Existing checkpoint bytes/history/runtime summaries and sealed legacy run roots remain immutable and reusable under proven training equivalence.
13. Historical EVAL2 measurements are reused only when exact measurement equivalence is provable; otherwise EVAL2 is recomputed without TRAIN2 retraining. Historical verdicts are never relabeled current in place.
14. Every affected historical CV fold is reselected under current policy; changed representatives purchase only required outer evaluation, and any newly current CV verdict is freshly published.
15. Historical successful or failed final-production trajectories reuse completed TRAIN2; lack of a durably bound old candidate set causes EVAL2 recomputation, never content-store scanning or retraining.
16. Future final-production terminal evidence binds the complete candidate set for selected and no-admissible outcomes before publication/failure.
17. Campaign schema v3 carries the new replay fields and mode-aware target default; v2 remains a distinct readable prior-modern schema (including its `fidelity_epochs` contract), v2 generated replay `30.0` and foundation target `0.030` migrate by the explicit rules, custom/ambiguous legacy replay values fail closed, and v3 explicit target `0.030` remains configurable.
18. Warning diagnostics are not hard-decision ancestors; changing only the warning threshold cannot move representative/CV/publication membership.
19. Current method/policy/evidence lineage remains singular and acyclic; no generic P5 protocol graph, compatibility wrapper, shadow registry or duplicated threshold state is added.
20. Focused, affected, real-owner and bounded scientific qualification evidence passes on the exact candidate.
21. Independent assembled Protocol 6.4 review passes.
22. Production-scale GPU qualification remains deferred to the final complete release package.

## 15. Reopen conditions

Reopen D1 if evidence shows that:

- `0.100 eV/angstrom` replay degradation permits scientifically unacceptable loss of capability relevant to the actual claimed target deployment;
- `0.050 eV/angstrom` target force RMSE is inconsistent with downstream adequacy evidence;
- replay must participate positively in checkpoint quality ranking rather than only catastrophic protection;
- target-only representative choice is scientifically inadequate.

Reopen D2 if:

- authoritative target RMSE cannot be compared consistently across checkpoints under current evaluation semantics;
- exact full-trajectory evaluation cannot establish the target minimum without a new approximation;
- threshold comparison/reassessment has unresolved precision/domain ambiguity;
- current metric records are insufficient statistics for exact reassessment.

Reopen D3 before adding machinery if:

- training identity cannot be narrowed without duplicated owners;
- currentness requires a persistent compatibility translator/shadow registry;
- old trajectory reuse cannot be proven from current ancestry without weakening genuine method-currentness checks;
- production target default cannot be isolated from scratch/CV through existing role-policy ownership.

D4-local defects remain D4 only when D1-D3 are coherent.

---

## 16. Deferred follow-up outside this workplan

After this narrow policy revision is complete, separately investigate the training trajectory itself:

- current deterministic TRAIN2 LR schedule versus historical near-constant MACE `1e-4` behavior;
- target/replay exposure ratio near `512 : ~10,000`;
- whether TRUE_DFT replay gradient semantics cause shared-backbone interference despite replay-dominant sample exposure;
- whether alternative exposure ratios or accepted regularization improve the target/replay Pareto trajectory.

Those questions can alter optimization and therefore belong to a separate D1/D2/D3 cycle. They must not be used as justification to delay or broaden the replay-admissibility/currentness repair above.