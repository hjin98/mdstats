---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: active-d3-r2-review-reopen
highest_affected_domain: D1
branch: design/mlff-replay-retention-target-admissibility-rework
analysis_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
implementation_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
protocol_6_4_authority_merge: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
stakeholder_direction_date: 2026-09-18
review_state: d1-r3-ratified-d2-gate-open
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
6. The shipped v2 campaign template explicitly writes the historical foundation-CV values `0.045/0.045`, production target value `0.030`, and replay value `30.0`. A default-only resolver change would therefore leave old generated campaigns trapped at the old standards. The configuration cutover needs schema-aware migration for all changed generated role defaults, not only new Python constants.
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
7. The default **foundation-production** target admissibility ceiling is `0.050 eV/angstrom`, while the two foundation-CV ceilings are intentionally relaxed from the accepted `0.045/0.045` to `0.075/0.075 eV/angstrom`. Current P5 scratch defaults remain unchanged unless separately reopened.
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

**Role-threshold rule:** this cycle now changes all three foundation role defaults deliberately: `tau_cv: 0.045 -> 0.075 eV/angstrom`, `theta_cv: 0.045 -> 0.075 eV/angstrom`, and `tau_prod: 0.030 -> 0.050 eV/angstrom`. The CV ceilings are intentionally more permissive than production checkpoint admission. Existing P5 scratch target defaults remain unchanged. Implementation must preserve role separation and must not leak these foundation defaults into scratch through the shared `[acceptance]` owner.

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
- `D1.DEF.025` foundation role-threshold family: set generated/default `tau_CV = theta_CV = 75 meV/angstrom` and `tau_prod = 50 meV/angstrom`, making CV intentionally more permissive than final production while preserving distinct roles.
- `D1.AX.009` / `D1.AX.010`: preserve fixed-budget CV and fresh production, but define hard replay retention as the catastrophic limit and replay-warning evidence as non-vetoing diagnostic evidence.
- D1 parameter ledger: add/clarify configurable replay warning/hard coordinates and update `tau_prod` default.
- D1 objective wording/ledger: clarify that `1:10:1` is the accepted foundation-P5 global E/F/S property-loss coefficient tuple, not a target/replay balance, per-configuration weight, or property-availability mask; D2/D4 may identify the current qualified realization as native MACE `UniversalLoss`, but D1 must not make that dependency class name the scientific coordinate; do not change the coefficients in this cycle.
- checkpoint/final-publication ordering semantics: replace any imported uncertainty/secondary/maturity authority for P5 checkpoint choice with strict minimum authoritative target RMSE over the hard-admissible set; apply the same rule to `single_best_final_seed`.

The D1 revision must state at least:

1. TRUE_DFT replay is an auxiliary retention/forgetting observable for foundation adaptation, not the deployment target domain.
2. Moderate replay degradation is diagnostic evidence and does not by itself veto a target-competent checkpoint.
3. A separate conservative hard replay limit exists to reject catastrophic forgetting.
4. Replay warning/hard values are configurable policy parameters; defaults `0.050/0.100 eV/angstrom` are stakeholder-selected current defaults, not empirically universal constants.
5. Replay receives no positive ranking/tie-break credit.
6. P5 checkpoint representative quality ordering is minimum authoritative target force-component RMSE among hard-admissible checkpoints.
7. `single_best_final_seed` uses the same strict target-RMSE ordering across already-frozen admissible seed representatives; `all_qualified_final_seeds` remains unranked publication.
8. Foundation final-production target checkpoint quality defaults to `0.050 eV/angstrom`; foundation CV checkpoint competence and held-out force-RMSE acceptance default to `0.075/0.075 eV/angstrom`; all remain configurable by role policy and scratch remains separately governed.
9. Downstream qualification remains separate and may still reject a frozen final publication for deployment/physics reasons.
10. Assessment-threshold/selection-policy changes that cannot influence training do not redefine the realized training trajectory.
11. Current CV authorization is a prerequisite for current final-production assessment/publication, but a change in CV decision policy does not by itself alter the bytes of an already-realized genuinely fresh final-production trajectory. Reuse is allowed only when current CV reclosure accepts and exact final-production training equivalence is proven; if current CV rejects, historical final-production bytes remain historical/nonpublishable.
12. Existing valid measurements may support a new current assessment only through explicit policy-bound reassessment; historical evidence is never rewritten or silently relabeled current.

### D1 challenge/falsification questions

The D1 renewal must explicitly challenge:

- whether `0.100 eV/angstrom` catastrophic replay degradation is too loose to protect inherited capability relevant to claimed target deployment;
- whether target-only ranking can select a checkpoint whose replay behavior, while under the hard ceiling, is scientifically unacceptable for any downstream use actually claimed by mdstats;
- whether raising production target default to `0.050 eV/angstrom` conflicts with observed downstream MD adequacy requirements;
- whether `tau_CV=theta_CV=0.075` is sufficiently discriminating while intentionally more permissive than `tau_prod=0.050`, including the risk that CV could authorize a method whose fresh production later fails the stricter production ceiling;
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

Preserve `D2.DEF.058` form `A_rho(c)=S(c) and r_mon(c)<=tau_rho`, including inclusive binary64 target threshold semantics. Set generated/default `tau_CV` to `0.075 eV/angstrom` and `tau_prod` to `0.050 eV/angstrom`; set the default-force held-out `theta_CV` to `0.075 eV/angstrom` in its existing outer-predicate owner.

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
replay warning                     = 50 meV/angstrom
replay hard                        = 100 meV/angstrom
foundation CV checkpoint ceiling  = 75 meV/angstrom
foundation CV held-out force RMSE = 75 meV/angstrom
foundation production target      = 50 meV/angstrom
```

Require finite positive replay limits and `warning < hard`; require every role threshold to remain finite and positive under its owning units; preserve full binary64 values for decisions. Under the default force outer metric, exact `0.075` passes each CV `<=` predicate and the next representable binary64 value above it fails; exact `0.050` similarly passes the production checkpoint predicate.

### 4.6 Fixed-budget training and assessment equivalence

No target/replay threshold or checkpoint-selection policy in this plan may stop TRAIN2, change LR, epoch count, replay/target sampling, loss, optimizer state or checkpoint persistence.

Amend `D2.AX.004` currentness with distinct dependency classes:

- `delta_warn` changes diagnostic warning/report evidence only;
- `delta_hard` changes hard checkpoint assessments, representatives and dependent CV/final decisions;
- `tau_CV` changes CV checkpoint hard assessments, representatives, dependent outer evaluation/CV verdict, and production authorization;
- `theta_CV` changes only the CV outer pass/fail decision and dependent production authorization, not the checkpoint hard-admissible set or representative;
- `tau_prod` changes production checkpoint hard assessments, representatives and dependent publication decisions;
- strict P5 selection-rule identity changes representatives and dependent outer-evaluation/verdict/publication descendants;
- none of those edits changes an authenticated TRAIN2 trajectory whose training-affecting identity is unchanged.

Do not declare old verdicts current by monotonic implication: a current verdict must be newly assessed under the current hard-decision/selection policy. Reuse of an old numeric measurement is permitted only when exact measurement identity/equivalence is proven.

Amend `D2.DEF.060/060A` as needed to distinguish exact training continuation identity from later assessment-policy ancestry without weakening fail-closed restart authentication. For a pre-cutover interrupted trajectory, continuation may use the historical runtime-plan/protocol identity only after an explicit exact training-equivalence proof; do not rewrite its summaries/config/checkpoints to a new digest.

Amend `D2.AX.005` so current CV authorization remains mandatory for current production assessment/publication, while a historically fresh final-production trajectory may be reused after CV reclosure iff current CV accepts and exact production training-position equivalence is proven. A current CV rejection leaves the historical final trajectory noncurrent regardless of its checkpoint quality.

### 4.7 Required downstream authority reconciliation after D1 ratification

Do not mutate accepted-current D2/D3/D4 authority before Gate B closes. Once exact D1 is ratified, reconcile the canonical descendants rather than leaving this workplan as a shadow owner:

- **D2:** `D2.DEF.058` retains its inclusive `<=` role-checkpoint predicate but resolves `tau_CV=0.075` and `tau_prod=0.050 eV/angstrom`; `D2.DEF.059` resolves default-force `theta_CV=0.075 eV/angstrom`; `D2.AX.004` must distinguish `tau_CV` checkpoint/reselection currentness from `theta_CV` outer-verdict-only currentness; the D2 parameter ledger becomes `75/75/50`; UniversalLoss `L_P5=L_E+10L_F+L_S` remains unchanged.
- **D3:** preserve the existing three role-policy owners and configuration sources, but make threshold-only changes assessment/currentness descendants rather than training-trajectory identity; `theta_CV` must not move checkpoint representative identity.
- **D4 P5 specification:** section 12.1 resolution table becomes foundation `0.075/0.075/0.050` for the default target-force outer metric, scratch remains `0.030`; alternative outer metrics retain their accepted units/default resolution and do not inherit the force-RMSE `0.075`; generated/shipped config and public docs must agree; historical generated default-force `0.045/0.045` receives the migration treatment in section 7.
- **D4 counterexamples/documentation:** retire the old assertion that a foundation checkpoint at `42 meV/angstrom` should fail production. Under the new defaults, `42` is below the `50` production ceiling. Use a discriminating example such as `60 meV/angstrom`: it may satisfy the default `75` CV checkpoint ceiling but must fail the default `50` production checkpoint ceiling. Held-out `theta_CV` remains a separate population/role.
- **Currentness:** a historical CV pass under `45/45` is not simply carried forward as current, despite the new thresholds being looser; publish a new current assessment under `75/75` from reusable exact measurements or recomputed EVAL2 evidence as required.

Archived closeout records remain historical and must not be edited to pretend they originally used `75/75/50`.

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

**Training trajectory identity.** Define one exact role-specific training-position projection and derive the post-selection run/checkpoint root from it. The projection includes every **already-available pre-fit** input capable of changing exact TRAIN2/materialization/restart behavior, including at least:

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

It excludes the fitted-preparation/result digest and every other descendant product, as well as downstream checkpoint-decision, warning, CV outer-acceptance, committee/publication and other post-training policy coordinates. The fitted preparation binds this trajectory identity; materialization/runtime bind the exact fitted-preparation digest; continuation separately authenticates that realized preparation/result/runtime ancestry under D2.DEF.060.

For new records, `run_identity` / checkpoint-root identity must mean this training trajectory position, schema-bumped as needed. Full CV/final plan digests remain assessment/authorization parents, not restart/root identity.

Because replay hard-decision and P5 selection identity are removed from `PostSelectionMethodIdentity`, evolve the role plans to expose narrow assessment/publication projections rather than reusing their full digests as currentness. CV fold assessment binds its hard policy + D2.DEF.059A + outer metric/`theta_CV`; final-seed assessment binds final hard policy + D2.DEF.059A only. Current-CV authorization is a separate precondition for using final-seed evidence, and publication mode/D2.DEF.059B belongs only to aggregate final publication. The warning-only threshold is excluded everywhere except diagnostics.

**Training-owned records.** Rebind the training owners that currently carry full run-plan ancestry:

- `PostSelectionFittedPreparation` authorizing ancestry (replace the full policy-bearing owner-plan dependency with the pre-fit training-trajectory position);
- `PostSelectionMaterialization.run_plan_digest/run_identity`;
- checkpoint catalog/file lineage;
- generated post-selection MACE configuration identity/name;
- TRAIN2 runtime-plan/summary/continuation authentication.

They must bind the pre-fit training-position authority while preserving every training-bearing input listed above. The fitted preparation/result remains a descendant and is authenticated separately by materialization/runtime/continuation. A policy-only edit must reproduce the same training-position digest. A changed pre-fit training-bearing coordinate must not; a changed fitted result under the same position must fail create-or-verify/continuation authentication.

**No pre-training assessment dependency.** `_prepare_post_selection_run()` must not compose current checkpoint admissibility to decide whether replay training/TRUE_DFT runtime monitoring exists. Resolve replay execution from the training method/replay lineage. Construct hard checkpoint admissibility only when EVAL2 assessment begins.

Keep `reject_foreign_run_continuation()` fail-closed on the training trajectory identity. Never satisfy it by ignoring a digest, copying checkpoints, or substituting a different role.

### 5.4 Seal the training root before assessment

The baseline run root mixes two lifecycles: mutable TRAIN2 output and immutable policy verdict. That is incompatible with later policy-only reassessment because `fold-acceptance.json` / `run-evidence.json` are fixed create-once files and the topology anchor is create-once.

Post-cutover, the root under `runs/<training_trajectory_identity>` is **training-only**:

- materialization/config/checkpoints/runtime history live there;
- once TRAIN2 reaches an authenticated terminal training state, freeze the topology and completion anchor **before EVAL2**, while holding the existing run-activity lease so no trainer/storage writer can race the seal;
- advance the run-completion schema/owner narrowly so a complete authenticated `Train2RuntimeSummary` plus its exact checkpoint/runtime boundary is a recognized **training terminal proof**; completion must no longer require `fold-acceptance.json` or `run-evidence.json` to exist;
- EVAL2 and later reassessment read the sealed root but never write assessment state into it.

Current policy-bound CV/final assessment evidence must live in the existing content-addressed post-selection evidence/currentness infrastructure outside the sealed training root. Extend `post_selection_store.py`'s existing CampaignStore pointer seam with one position-addressed assessment pointer form; do not create a second pointer database or filesystem registry.

The deterministic position key is the canonical projection:

```text
selected_binding_digest
assessment_role = cv_fold | final_seed
assessment_position_policy_digest
training_trajectory_identity
optimizer_seed
fold_index for CV, absent for final production
```

For CV, `assessment_position_policy_digest` binds current hard checkpoint policy + D2.DEF.059A + configured outer metric/`theta_CV`. For final seed assessment, it binds current final hard policy + D2.DEF.059A only. Final-seed assessment excludes current-CV authorization, publication mode and D2.DEF.059B; current CV is re-authenticated as an authorization precondition and 059B is bound only by aggregate final publication.

The pointer value is the immutable current assessment-record digest. Publication uses the same commit-time selected-binding stale-generation fence as existing post-selection pointers. Thus a hard-policy/059A change derives a different assessment position; an idempotent retry of the same position resolves the same pointer; warning-only edits do not move it. A 059B/publication-mode-only edit leaves seed assessments current and moves only aggregate publication.

Campaign-level `POINTER_CV_ACCEPTANCE` and final-publication pointers remain aggregate current authorities. The position pointer exists only so interrupted multi-fold/multi-seed assessment can resume without retraining, rerunning already-current assessment work, or scanning the object store.

After cutover:

- stop writing current `fold-acceptance.json` and `run-evidence.json` into training roots;
- retain one completion/topology owner: do not introduce a second training-root manifest format merely to recognize the TRAIN2 terminal proof;
- retain read-only support for those files in already sealed historical roots; a terminal-but-unsealed legacy root has exactly one append-only completion-proof exception under the existing run-activity owner after exact terminal/root-node authentication, with no rewrite of any pre-existing byte;
- a warning-threshold-only change may publish new diagnostic evidence without touching the sealed root or hard-assessment locator;
- a hard-policy/selection change publishes a new assessment record/locator over the same trajectory root.

The storage/topology owner must continue to certify a closed subtree and cold-storage semantics. Preserve the accepted proof contract losslessly: `O_NOFOLLOW` open plus `fstat` regular-file authentication of authority records, non-reclaimable topology/anchor infrastructure, compact-anchor completion independent of terminal assessment-file presence, idempotent reuse of an existing proof instead of reconstruction from a depleted tree, and fail-closed handling of tampered/copied/root-mismatched/partial-conflict proof state. Any EVAL2/reassessment that reads materialization/checkpoint bytes from a sealed run root must acquire the existing `post_selection_run_activity_lease()` for the full root-read/evaluation interval, so archive/dedup/reclamation cannot move those bytes concurrently. Release that lease after all root-dependent numerical reads complete; then publish immutable assessment objects/pointers. If a path must hold both locks, preserve the established order `run-activity lease -> post-selection publication barrier`, never the reverse. Do not add a second reader-lock protocol.

### 5.5 Separate evaluation measurement from assessment policy

Current `post_selection_eval_role_digest()` includes `run_plan_digest` and `run_identity`. That over-binds numeric measurement evidence to policy ancestry.

The current measurement owner must instead bind the exact factors that can change the numeric measurement: checkpoint/model realization, dataset role, exact membership/artifact bytes, metric/reduction policy, head/provider/precision semantics as applicable. Assessment thresholds and full role-plan digest must not be measurement identity.

Policy-bound checkpoint-assessment records may then consume immutable measurement records and produce current rejections/representatives. Warning diagnostics are derived separately from signed replay degradation under the diagnostic-only warning policy. Historical baseline records may be reused only through a source-preserving derivation that proves the old measurement inputs equal the current measurement identity; never copy a scalar without its authenticated checkpoint/population/provider ancestry.

### 5.6 Role target default isolation

Current `[acceptance].maximum_target_force_rmse_ev_per_angstrom` supplies production for every mode and scratch CV. Preserve the single explicit public field. Change only omitted/default resolution:

```text
foundation final production omission -> 0.050
scratch omission -> existing accepted 0.030
explicit value -> preserved as written for the consumers that already own it
foundation CV -> independent 0.075 checkpoint default and 0.075 default-force held-out threshold
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

change CV checkpoint ceiling tau_CV
  -> CV hard assessments/representatives + dependent outer evaluation/verdict move
  -> dependent production authorization becomes stale
  -> CV TRAIN2 trajectories and numeric measurements remain current

change CV outer threshold theta_CV
  -> CV outer verdict + dependent production authorization move
  -> CV checkpoint assessment/representative and TRAIN2 trajectory remain current

change production target threshold tau_prod
  -> production assessments/representative/publication move
  -> production TRAIN2 trajectory and sealed training root remain current
  -> accepted CV remains current because its policy did not move

change D2.DEF.059A within-run selection identity
  -> per-run representative and dependent verdict/publication descendants move
  -> numeric measurements and TRAIN2 trajectory remain current

change D2.DEF.059B or publication mode only
  -> aggregate final publication decision moves
  -> final-seed assessments/representatives, numeric measurements and TRAIN2 remain current

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

### 6.2 Foundation role-target defaults

Change the resolved generated/default foundation thresholds to:

```text
CV checkpoint target-force RMSE         = 0.075 eV/angstrom
CV held-out target-force RMSE           = 0.075 eV/angstrom  (default outer metric only)
final-production checkpoint target RMSE = 0.050 eV/angstrom
```

Preserve explicit user values after the migration-generation rules in section 7. Scratch keeps its accepted `0.030` behavior. `acceptance_maximum` continues to follow `acceptance_metric`; the `0.075` generated default applies to the default target-force outer metric and must not be transplanted by units into an alternative metric.

### 6.3 Selection implementation

Replace P5 representative selection with deterministic minimum authoritative target RMSE over hard-admissible candidates. Baseline P5 already evaluates the full durable trajectory, so this is an ordering-only change.

Current P5 calls `select_cv_fold_representative()` -> `order_eval2_admissible_candidates()`, whose practical-equivalence bands, paired bootstrap, secondary target metrics and maturity ordering can promote a strictly worse primary RMSE. Remove that authority from P5. Do not add a `strict_minimum` switch to the old algorithm merely to preserve one function call.

First census non-P5 consumers of `order_eval2_admissible_candidates()` / generic `Eval2RunRecord`. If they legitimately retain the old uncertainty-aware algorithm, leave it scoped there and make the P5 owner directly select the minimum. If P5 is the only live consumer requiring ordering, simplify/retire the obsolete P5 policy fields and identity bindings.

Apply the same strict target ordering in `post_selection_publication.py` for `single_best_final_seed`; advance its decision-policy identity/schema if necessary. `all_qualified_final_seeds` remains unchanged.

### 6.4 EVAL2 measurement and checkpoint evidence

Do not advance `Eval2CheckpointRecord` merely to embed a warning bit whose threshold is diagnostic-only. The existing signed replay degradation is sufficient to derive the current warning. If durable warning reporting is required, persist it in diagnostic evidence whose digest is not an admissibility/selection parent.

The future numeric measurement identity must be assessment-independent and directly bind enough provenance to prove reuse without interpreting a full role plan: checkpoint/model-state identity, exact evaluation artifact/membership, metric/reduction policy, prediction/provider/model realization semantics, head and precision where numerically material. Because current `Eval2TargetMetricRecord.target_role_digest` / `prediction_digest` inherit full run-plan ancestry, advance the measurement schema or role/prediction identity schema when that meaning changes rather than silently reusing the old schema token.

Historical checkpoint/metric records remain immutable/readable under their historical schema. Do not rewrite old `admissible` bits or old rejection reasons in place. A current reassessment may reuse historical numeric values only after an explicit proof of exact measurement equivalence; otherwise recompute EVAL2 from the preserved checkpoint.

### 6.5 Policy assessment evidence and complete candidate-set persistence

Repair both the negative-evidence defect and the successful-run candidate-set gap at the policy-assessment owner, outside the sealed training root.

For final production, evolve the existing `PostSelectionRunEvidence` concept into one outcome-discriminated current assessment schema rather than inventing a parallel negative-result subsystem. It must bind:

```text
training_trajectory_identity
current final-plan / hard-decision / selection-policy ancestry
outcome = representative_selected | no_admissible_representative
complete ordered candidate_record_digests
representative identity/checkpoint/record only when selected
current monitor metric identity as required
```

The constructor must enforce the tagged outcome invariants. A selected representative is one member of the bound candidate set; a no-admissible outcome carries no representative.

For CV, retain `CvFoldAcceptance` as the fold assessment owner, but store/locate current fold assessments outside the training root after cutover.

Persist every EVAL2 checkpoint assessment before publishing either outcome. Baseline `PostSelectionRunEvidence` does not bind candidate-record digests, so merely storing candidate objects is insufficient for future reselection. Do not discover candidates later by content-store scanning or filename heuristics.

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

### 7.1 Keep campaign schema v2; add one narrow policy-generation discriminator

Do **not** bump the global `mdstats.mlff-campaign-cli.v2` schema for this local P5 policy change. That schema already governs unrelated target-size/config parsing and changing it would broaden the repair unnecessarily.

Add one generated migration discriminator under the existing `[acceptance]` table:

```toml
[acceptance]
post_selection_checkpoint_policy_generation = "p5_target_replay_v2"
```

This field exists only to distinguish the new authored contract from historical TRAIN2 configs whose generated defaults were written explicitly. It is not an independent scientific score and must not be hashed separately from the resolved rule/value identities.

New generated/current fields are:

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

The historical one-number replay field:

```toml
allowed_replay_degradation_mev_per_a = 30.0
```

is invalid when the new policy-generation marker is present.

### 7.2 Historical TRAIN2 replay migration

For a TRAIN2 campaign with **no** new checkpoint-policy marker, exactly the historical generated/default replay field `allowed_replay_degradation_mev_per_a = 30.0`, and no new replay fields:

- recognize it as the superseded generated baseline;
- resolve current replay policy to `50.0/100.0 meV/angstrom`;
- emit a bounded migration/deprecation notice;
- do not retain `30.0` as a hidden hard gate.

If the legacy one-number replay value is non-default/custom, fail with an actionable migration error rather than guessing whether it maps to warning or hard rejection.

If new fields appear without the new marker, or legacy and new replay fields coexist, fail closed with an actionable migration instruction. Do not silently make one source win.

### 7.3 Historical foundation-production target migration

The shipped current template explicitly writes `maximum_target_force_rmse_ev_per_angstrom = 0.030`; omission-only default changes are insufficient.

For **foundation-adaptation TRAIN2 configs without the new marker**:

- absent target field or exact historical generated value `0.030` resolves to the new foundation-production default `0.050`;
- a non-`0.030` finite positive legacy value is preserved as an explicit override.

This deliberately treats exact legacy `0.030` as generated-default ancestry because the old config carries no provenance capable of distinguishing "generated 0.030" from "user retyped exactly 0.030". A user who intentionally wants production `0.030` after cutover must add the new marker and set `0.030` explicitly.

For **scratch** TRAIN2 configs, legacy `0.030` retains its accepted scratch meaning and is not migrated to `0.050`.

Schema-less/pre-TRAIN2 policy generations retain their own historical semantics and are not silently converted into this checkpoint-policy generation.

### 7.4 Historical foundation-CV threshold migration

The shipped current template explicitly writes both foundation-CV generated values as `0.045`, so omission-only default changes are insufficient.

For **foundation-adaptation TRAIN2 configs without the new marker**:

- absent `checkpoint_maximum_target_force_rmse_ev_per_angstrom` or exact historical generated value `0.045` resolves current `tau_CV` to `0.075`;
- a non-`0.045` finite positive checkpoint value is preserved as an explicit override;
- when `acceptance_metric` resolves the default `target_force_rmse_ev_per_angstrom`, absent `acceptance_maximum` or exact historical generated value `0.045` resolves current `theta_CV` to `0.075`;
- for a non-default outer metric, do not apply the force-RMSE `0.045 -> 0.075` migration at all: preserve its existing accepted resolution/units and every explicit `acceptance_maximum` exactly; the new `0.075` default is specific to `target_force_rmse_ev_per_angstrom`;
- exact legacy `0.045` under the default force metric is treated as generated-default ancestry because the historical config has no provenance capable of distinguishing generated `0.045` from a user who retyped exactly `0.045`.

A user who intentionally wants current foundation CV `0.045/0.045` after cutover must use the new marker and set those values explicitly. Scratch retains its accepted threshold resolution and is not migrated to the foundation defaults.

### 7.5 New-generation explicit values and validation

With `post_selection_checkpoint_policy_generation = "p5_target_replay_v2"`:

- explicit foundation CV checkpoint/held-out values, including `0.045`, are lawful intentional overrides and are preserved under their owning units;
- explicit production target `0.030` is a lawful intentional override and is preserved;
- replay warning/hard values are used exactly after validation;
- require finite positive values and `warning < hard`;
- reject booleans, strings, NaN and infinity at the policy boundary;
- omission and explicit current defaults yield identical resolved hard/diagnostic policy identities;
- the retired one-number replay field is rejected;
- generated template, `init` output, shipped example, CLI specification and user guide remain campaign-schema v2 and converge on this marker/field contract;
- shipped `[evaluation]` comments no longer claim refinement reservation, practical-equivalence/bootstrap, secondary metrics or maturity control **P5** representative selection. Generic EVAL2 configuration may remain only for unaffected consumers with its scope stated accurately.
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
target/replay validation artifacts consumed by the trainer
common-monitor lineage consumed by preparation/runtime
composition-transfer required-composition set for governed consumers
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

For the exact baseline `PostSelectionMethodIdentity` schema-v3 method/run lineage, the migration proof must cover all old over-bindings:

1. old `PostSelectionMethodIdentity` -> new training identity, excluding only assessment/selection parents after proving all training-bearing fields equal;
2. old full-plan-derived run/checkpoint root -> current training-position identity, proving role/fold membership/seed/horizon, trainer-consumed validation lineage, preparation/composition-transfer dependencies and every other training-bearing parent equal;
3. old fitted preparation/materialization/checkpoint/runtime ancestry -> current training position, without rewriting the old records;
4. old plan-bound evaluation role -> current measurement identity, proving checkpoint SHA/model state, exact evaluation artifact/membership, metric policy/provider semantics and prediction digest equal where reuse is claimed.

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

After section 6.5 is implemented, future successful and negative production assessments bind the complete candidate set so later policy-only reassessment need not rediscover or re-infer it.

A historical final-production trajectory can become current assessment input only after the current CV plan is reclosed and accepted. If current CV rejects, keep the historical final trajectory as retained training evidence but do not publish a current production representative from it.

### 8.7 Legacy trajectory continuation and run-root locator

A new clean training-position identity does not rename or invalidate a sealed legacy run root.

During the one-time identity migration:

- derive the legacy source run identity/root only from authenticated stored historical CV/final plan and run-position evidence;
- if the historical root is sealed, validate its existing completion/topology ownership records before consuming checkpoints and never mutate it;
- if TRAIN2 is complete but the old policy failed before terminal run evidence/completion anchor, first require that the historical root is terminal-but-unsealed; authenticate the complete runtime summary/checkpoints plus every existing root node, then under the existing run-activity owner publish exactly one append-only topology manifest/anchor using create-once/verify semantics; do not rewrite any pre-existing historical byte, and fail closed on conflicting partial proof state;
- if TRAIN2 is interrupted, resume only after exact training-equivalence proof and continue using the historical materialization/config/runtime protocol identities that created the checkpoint/optimizer/RNG state; do not rewrite them to the new identity mid-trajectory;
- after legacy continuation completes, assess under the current policy outside the training root;
- never locate a legacy run by scanning `runs/`, guessing hashes, newest-mtime choice, or content-store reverse lookup;
- never rename, copy, rewrite or symlink a sealed legacy root merely to make its pathname match the new identity;
- permit at most one immutable per-trajectory reuse binding at the existing currentness owner that records old run identity/root, new training-position identity and the exact equivalence proof. Do not create a registry or shadow run namespace.

Newly created post-cutover trajectories use the corrected training-position identity directly, so this compatibility edge is one-time historical migration rather than steady-state dual identity.

## 9. Historical Applicability Set

Project engineering memory is applicable because this cycle changes mature P5 identity/currentness and revisits a documented replay-forgetting recurrence. At baseline `a759e81...`, the repository PEM is present in current main but remains explicitly reconciled only through `4eabe2ae9783c7ff92f3a1093c37502a01380812`; the Protocol 6.4 documentation merge did not itself refresh PEM. Use the evidence-backed entries below and refresh the basis if PEM advances before closeout.

```yaml
pem_basis:
  accepted_project_state: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
  accepted_pem: hjin98/mdstats@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-002
    disposition: APPLICABLE
    reason: Historical continuation must distinguish authenticated training semantics from assessment-only changes and fail closed before an exact restart boundary.

  - id: FF-003
    disposition: APPLICABLE
    reason: Sealed P5 root reads and assessment publication must reuse the existing P5/storage ownership and exclusion order rather than create a second mutation or reader-lock route.

  - id: SP-001
    disposition: APPLICABLE
    reason: Remove assessment coordinates from over-broad training identity and reuse existing pointer/evidence owners rather than add wrappers, shadow registries, or a second checkpoint selector.

  - id: SP-002
    disposition: APPLICABLE
    reason: Training, measurement, assessment, restart, and storage boundaries must remain authenticated and fail closed on real semantic disagreement.

  - id: SP-003
    disposition: APPLICABLE
    reason: Preserve immutable valid TRAIN2 roots and exact measurements when their governing equivalence remains applicable; publish new assessments rather than rewrite history.

  - id: SP-004
    disposition: APPLICABLE
    reason: Acceptance must exercise the real cross-validate/train-production -> TRAIN2 recovery -> EVAL2 -> assessment -> publication owners, including historical-workspace reuse.

  - id: NT-001
    disposition: NOT_APPLICABLE
    reason: The notice is retired; its durable lessons are carried by the current FF/SP entries above and it is not an active authority or recurrence claim for this cycle.
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
12. Foundation CV defaults resolve exactly `0.075/0.075` and P5 scratch remains `0.030`; prove foundation role-default changes cannot leak into scratch.
13. Scratch target semantics remain unchanged unless separately ratified.
14. Editing any role target ceiling (`tau_CV`, `theta_CV`, or `tau_prod`) does not move training identity; it stales only the assessment/verdict descendants governed by the edited role.

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

23. Defaults resolve to replay `50/100 meV/angstrom`, foundation CV `75/75 meV/angstrom` under the default force outer metric, and foundation-production target `50 meV/angstrom`.
24. `warning >= hard` fails.
25. zero, negative, boolean, string, NaN and infinity fail.
26. With `post_selection_checkpoint_policy_generation = "p5_target_replay_v2"`, omission and explicit current defaults yield identical resolved policy identities; explicit CV `0.045/0.045` and explicit production `0.030` remain exactly those intentional values.
27. A historical foundation-adaptation config with no marker migrates generated CV `0.045/0.045 -> 0.075/0.075` under the default force metric and generated production `0.030 -> 0.050`; scratch legacy `0.030` remains `0.030`.
28. A non-default legacy CV checkpoint threshold is preserved as an explicit override; for a non-default outer metric, `acceptance_maximum` retains its accepted pre-amendment resolution/units and is never migrated to `0.075` merely because it is omitted or numerically equals `0.045`.
29. A historical TRAIN2 config with no marker and one-number replay `30.0` migrates to `50/100`; a custom one-number value fails actionable migration.
30. New replay fields without the marker, or mixed retired/new replay authorities, fail closed.
31. Generated template, `init` output, shipped example, CLI spec and guide remain campaign schema v2 and agree on `75/75/50`, the marker/new replay fields, and the continued separation of scratch defaults; P5 comments no longer claim bootstrap/refinement/secondary ordering authority.

### 10.5 Currentness/recovery

32. Editing only replay warning threshold changes warning/report evidence only: it does not relaunch TRAIN2 and does not stale hard assessment, representative, outer evaluation, CV acceptance, production authorization or publication membership.
33. Editing only replay hard limit does not relaunch TRAIN2 but does stale/rebuild hard assessments and dependent representatives/verdicts.
34. Editing only `tau_CV` does not relaunch CV TRAIN2; it rebuilds CV hard assessment/representative and dependent outer verdict/production authorization.
35. Editing only `theta_CV` does not relaunch CV TRAIN2 or change its representative; it rebuilds the outer verdict and dependent production authorization only.
36. Editing only `tau_prod` does not relaunch production TRAIN2; it rebuilds production assessment/representative/publication descendants.
37. Editing LR/loss/exposure/foundation/replay training membership/seed/epoch budget still invalidates affected TRAIN2 evidence as today.
38. Old checkpoint SHA-256 values remain unchanged through reassessment.
39. Old runtime summaries/history are not rewritten.
40. Old EVAL2 measurements are reused only when exact measurement ancestry is provable; otherwise EVAL2 is recomputed from preserved checkpoints with zero TRAIN2 launch.
41. Reassessment creates current verdict/assessment evidence rather than mutating old evidence.
42. Replay-threshold, role-threshold, or strict-selection-policy-only changes leave the resolved training-position identity unchanged.
43. Changing fold gradient membership, seed, horizon, objective, exposure or foundation changes training-position identity and foreign continuation remains rejected.
44. The same checkpoint + exact evaluation artifact + metric/provider policy resolves identical measurement identity across assessment-policy-only edits.
45. Changing checkpoint SHA, monitor membership/artifact, metric policy or provider semantics changes measurement identity and prevents metric reuse.

### 10.6 CV/final integration

46. Every affected historical CV fold, including previously successful folds, is reselected under the strict target-minimum/current hard policy without TRAIN2 retraining.
47. A previously no-admissible fold can obtain a representative from reusable/recomputed EVAL2 evidence; a previously successful fold may change representative. Outer evaluation is reused only for the same representative with proven measurement equivalence, otherwise only the required outer evaluation is rerun.
48. A historical CV verdict is never relabeled current merely by monotonic implication. Reuse its authenticated TRAIN2/measurement evidence where valid, then publish a new current fold/campaign assessment under the new `0.075/0.075` CV policy.
49. An old default-force CV result between `0.045` and `0.075` is newly admissible only through a fresh current assessment; the stored numeric measurement may be reused if exact measurement identity is proven.
50. CV acceptance under `0.075/0.075` authorizes a production attempt but does not guarantee a `<=0.050` production representative; a fresh or reused production trajectory can still end in a current no-admissible result.
51. Final production with completed TRAIN2 resumes at EVAL2 without training relaunch.
52. Final-production all-inadmissible assessment persists all candidate records before terminal failure.
53. A selected warning-bearing representative publishes with a visible warning and no false failure state.
54. A selected representative above the hard replay limit is impossible.
55. `single_best_final_seed` chooses the lower authoritative target RMSE even when the other seed has better replay margin, secondary metrics, maturity or bootstrap evidence.
56. `all_qualified_final_seeds` publishes every already-qualified required representative without cross-seed ranking.
57. Changing D2.DEF.059B or publication mode stales only aggregate final publication decisions, not per-seed assessments/representatives, TRAIN2 trajectories or numeric common-monitor measurements; changing D2.DEF.059A moves the affected per-run representative/assessment descendants.
58. A post-cutover successful production run binds the complete ordered candidate-record set; a no-admissible terminal result binds the same set before failure publication.
59. A historical successful production run whose candidate set is not durably enumerable recomputes EVAL2 from preserved checkpoints rather than scanning the evidence store or retraining.
60. A historical foundation-adaptation config with generated CV `0.045/0.045` and production `0.030` migrates to `0.075/0.075/0.050`; with the new checkpoint-policy marker, explicit `0.045/0.045` and `0.030` remain intentional overrides; scratch legacy `0.030` remains unchanged.
61. Historical replay `30.0` migrates to `50/100`; custom one-number replay fails actionable migration; the new marker rejects the retired one-number field and mixed old/new replay authority.
62. Legacy run-root reuse derives its source locator from authenticated historical plan/run evidence; already sealed roots remain strictly read-only, while a terminal-but-unsealed root may receive only the one authenticated append-only completion manifest/anchor without rename/copy/symlink or rewrite of existing bytes.
63. A completed post-cutover TRAIN2 trajectory publishes its training completion/topology proof under the run-activity lease **before EVAL2**; simulated interruption immediately after the seal resumes at assessment with zero trainer launch.
64. Post-cutover EVAL2/CV/final assessment writes no `fold-acceptance.json`, `run-evidence.json`, or other policy-bound state into the sealed training root; historical root-local records remain read-only compatible.
65. A hard-policy or selection-policy change creates a new external assessment/currentness record over the same sealed trajectory; warning-only change affects diagnostic evidence only; neither mutates root topology.
66. `_prepare_post_selection_run()` resolves replay execution from training method/replay lineage, not current checkpoint-admissibility policy; warning/hard/target/selection edits reach EVAL2 only.
67. The pre-fit training-position identity is identical across assessment-only edits and moves on every exercised pre-fit training-bearing input, including authorized preparation inputs/composition-transfer consumer lineage. Fitted preparation, materialization, checkpoint catalog, MACE config/runtime plan and continuation descend from that identity and separately authenticate the exact realized fitted-preparation/result state.
68. A pre-cutover interrupted trajectory resumes only through exact training-equivalence proof using its historical config/runtime protocol identities; no historical record is rewritten mid-trajectory.
69. Current CV rejection blocks current final-production assessment/publication even if historical final TRAIN2 bytes are reusable; current CV acceptance plus exact production training equivalence permits reassessment with zero trainer launch.
70. Current CV/final assessment is found through the canonical position pointer `(selected binding, role, assessment-position-policy digest, training trajectory, seed, optional fold)` in the existing CampaignStore/post-selection pointer infrastructure. CV uses hard+059A+outer-verdict policy; final seed uses hard+059A only. Warning-only, current-CV-authorization-only and 059B/publication-mode-only edits do not move a final-seed position; 059B moves only aggregate publication.
71. The existing completion/topology/storage tests prove the evolved TRAIN2-terminal seal remains create-once, closed-subtree certifiable, lease-safe, uses opened-descriptor `O_NOFOLLOW`/`fstat` authority authentication, keeps manifest/anchor non-reclaimable, remains valid without hot terminal assessment files, reuses rather than reconstructs existing proof after cold movement, and fails closed on tampered/copied/partial-conflict proof state.
72. Concurrent reassessment versus archive/dedup/reclamation proves the reassessment holds the existing run-activity lease while reading/evaluating root bytes; storage mutation waits, no root byte disappears mid-EVAL2, and publication occurs without lock-order inversion.
73. Shipped example/generated config remain campaign schema v2 and no longer describe bootstrap/refinement/secondary ordering as P5 representative authority.

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
  mdstats/training_data/post_selection_store.py
  mdstats/training_data/campaign_control.py
  mdstats/training_data/train2_runtime.py
  mdstats/training_data/storage/owners.py (only where sealed-run certification/currentness consumes the evolved completion proof)

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
  tests/test_mlff_target_size_p5e_production_and_restart.py
  tests/test_mlff_downstream_integration_closure.py
  tests/test_mlff_storage_reset_core.py
  tests/test_mlff_storage_reset_integration.py
  tests/test_mlff_campaign_observation_coherence.py
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
- pre-training recovery currently depends on current checkpoint-admissibility merely to decide replay execution;
- fitted preparation, materialization, checkpoint catalogs and TRAIN2 runtime ancestry still bind full policy-bearing run/method digests;
- run-root completion is currently coupled to assessment files, so policy reassessment cannot share one sealed root without splitting training and assessment lifecycles;
- global campaign-schema versioning is unnecessary for this local migration; a narrow acceptance-policy generation marker suffices;
- historical final-production reuse requires explicit current-CV reauthorization semantics;
- published PEM at current main remains reconciled only through `4eabe2ae...`, so HAS uses those evidence-backed entries without pretending PEM itself was refreshed by the Protocol 6.4 documentation merge.

Branch opened from exact baseline: `design/mlff-replay-retention-target-admissibility-rework`.

### Gate B - D1 renewal for replay role and production target quality - CLOSED / ACCEPTED

Exact immutable D1 R3 candidate:

`d761171f3c86c3c79b87a90cfc02ac324c261b1a`

Canonical D1 blob:

`612294ec4680db01a18085e13fbfe5dcfa9fb7ed`

Fresh independent Protocol-6.4 D1 Review R3 returned **PASS with no SERIOUS CHALLENGE** at review commit `02ad772ae11d8afb64321de0f22315bf2c2ad705`.

On 2026-09-18 the stakeholder explicitly accepted that exact candidate. Ratification record:

- `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D1_R3_RATIFICATION.md`

The reviewed D1 blob is not rewritten by ratification. It is the accepted branch-local D1 parent for Gate C.

### Gate C - D2 numerical renewal - CLOSED / ACCEPTED

Formally define:

- signed degradation and exact comparisons;
- unit conversions/default validation;
- strict minimum target ordering;
- exact tie rule;
- fixed-budget independence;
- replay warning/rejection numerical oracle;
- old-measurement reassessment equivalence.

Independent D2 Review R1 of `e2b39917ab8c16556eb218d6a41e9682331bbca0` returned **NO-PASS with no SERIOUS CHALLENGE to D1**. The narrow repair now binds exact replay training label/provider semantics and consumption-projected `Q_r`, permits differing evaluator/provider realizations only under accepted numerical equivalence, and closes the new typed failure states. Fresh independent D2 R2 review of semantic candidate `4f161b1c4820de10abe638287b13152147d12fd9` with canonical reviewed D2 blob `3e7fb744fc733f23bbd93a8347246cfa306ebe89` returned **PASS with no SERIOUS CHALLENGE**. Review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_INDEPENDENT_REVIEW_R2.md`.

A renderer-only descendant then removed disallowed `\\operatorname` constructs and replaced the tie-key function names by explicitly defined renderer-safe symbols, with no numerical or decision-semantic change. Representation-repair record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_R2_RENDER_REPAIR.md`.

A second renderer-only repair was required because D2.DEF.027 still used escaped set braces and compound restricted-sum subscripts that triggered the renderer's “Extra open brace or missing close brace” failure. The exact sets and sums are now expressed through named restricted witness sets and simple sums. Repair record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_R2_RENDER_REPAIR_2.md`.

The final renderer-safe D2 ratification target is `32508991d472c1c6e4bd8b818b38d0880401845f`, with D2 blob `30e6e6336cf41a05879650a3a2d7d583c4ef713a`. Its semantic basis remains the independently reviewed D2 R2 target `4f161b1c4820de10abe638287b13152147d12fd9`.

On 2026-09-18 the stakeholder explicitly accepted that exact D2 candidate. Ratification record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_R2_RATIFICATION.md`. The D2 blob remains unchanged by ratification. Gate C is closed; Gate D may proceed.

### Gate D - D3 authority/currentness reconciliation - R2 REVIEW NO-PASS / D4 HANDOFF REOPENED

Before code edits:

- remove replay hard/diagnostic thresholds **and P5 checkpoint-selection policy** from training identity at the accepted owner;
- freeze the dependency graph distinguishing training trajectory, numeric measurement, hard checkpoint decision, and warning-only diagnostic policy;
- evolve CV/final assessment-plan ancestry to bind role-effective hard-decision policy + strict P5 selection identity explicitly after those parents leave the training method, while excluding warning-only policy;
- freeze one training-position identity as the run/checkpoint/restart owner and rebind preparation, materialization, checkpoint catalog, MACE/runtime plan and continuation ancestry to it;
- remove pre-training dependence on current checkpoint-admissibility policy; replay execution comes from training method/replay lineage and hard assessment begins only in EVAL2;
- evolve the existing run completion/topology owner so authenticated terminal TRAIN2 can seal the training root under the run-activity lease before EVAL2;
- move current CV/final policy assessment and deterministic position locators outside the sealed training root into the existing evidence/currentness infrastructure;
- define the one-time authenticated legacy run-root locator/reuse binding without rename/copy/scan machinery, including exact historical continuation semantics;
- repair measurement ancestry so future policy-only edits can reuse exact measurements, while historical records fall back to EVAL2 recomputation when proof is incomplete;
- bind the complete final-production candidate set in outcome-discriminated assessment evidence;
- freeze current-CV reauthorization semantics for historical final-production reuse;
- prove currentness/recovery can preserve old TRAIN2 without a shadow compatibility subsystem or second evidence store;
- reconcile the narrow `post_selection_checkpoint_policy_generation` migration without changing global campaign schema v2, while deliberately migrating foundation CV defaults and preserving collateral scratch semantics.

Fresh independent D3 Review R1 of immutable candidate `119c4067b1852be127134d6b0fb1aae6cace4bd6` returned **NO-PASS** with a **SERIOUS CHALLENGE to the proposed D3 candidate only**; ratified D1/D2 remain coherent. Review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R1.md`.

Required repair before a new immutable D3 candidate may be reviewed:

1. remove the cycle between `TrainingTrajectoryIdentity` and `PostSelectionFittedPreparation`: the trajectory/root identity must be derived only from pre-fit training-bearing inputs/policies/authorized memberships and other already-available parents; the fitted preparation is a descendant that binds that trajectory position, and continuation separately authenticates the exact fitted-preparation/result digest required by D2.DEF.060;
2. resolve legacy-root mutability explicitly: already sealed historical roots remain read-only; for terminal-but-unsealed legacy roots either authorize exactly one append-only completion-manifest/anchor publication under the existing run-activity owner without rewriting any pre-existing historical byte, or place the proof at an already accepted external owner. Do not simultaneously require a read-only root and a new in-root seal;
3. narrow final-seed assessment currentness so D2.DEF.059B publication-only policy is not a parent of each per-seed assessment position. Bind D2.DEF.059A + final hard policy to the seed-assessment projection; bind publication mode/059B only at the aggregate publication decision;
4. restore the accepted completion-proof/storage safety invariants weakened by the candidate rewrite: race-safe no-follow opened-descriptor regular-file authentication (or an explicitly equivalent guarantee), topology/anchor owner infrastructure excluded from reclamation, completion independent of terminal assessment-file presence, idempotent reuse of an existing proof rather than reconstruction from a storage-depleted tree, and fail-closed treatment of tampered/copied/self-inconsistent proofs.

R1-D3-1 through R1-D3-4 are incorporated into exact repaired candidate `5d7c62f803fc8757a4068b7b115fadb7a5ec4636`: the identity graph is acyclic, legacy sealing has one explicit append-only exception, final-seed assessment excludes 059B/publication-only ancestry, and the full completion/storage safety contract is restored. Repair binding: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_R1_REPAIR_BINDING.md`.

Fresh independent D3 Review R2 of that exact target returns **NO-PASS with no SERIOUS CHALLENGE to ratified D1/D2 or the repaired D3 architecture**. Review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R2.md`.

The R1 D3 blockers are genuinely closed. One blocking D3->D4 handoff omission remains: the accepted repaired D3 defines post-cutover run roots as training-only and D2.DEF.060B makes held-out evaluation artifact/labels measurement ancestry, but the current executable `PostSelectionMaterialization` still binds `outer_evaluation_artifact` and stores `outer_evaluation.extxyz*` under the run root. The candidate D4 specification/workplan does not explicitly remove or relocate that field. Therefore an evaluation-only held-out artifact/label change can still conflict with the immutable materialization/root even when `TrainingTrajectoryIdentity` and TRAIN2 semantics are unchanged.

Required repair before another immutable Gate-D candidate may be reviewed:

1. make post-cutover `PostSelectionMaterialization` and the sealed run-root topology training-only in fact, not only by name: remove held-out `outer_evaluation_artifact` and `outer_evaluation.extxyz*` from the training materialization/root identity and topology;
2. route held-out outer-evaluation materialization through the existing assessment/evidence owner used by EVAL2, or another already-accepted external P5 evidence surface, so exact population/artifact/labels/provider ancestry is bound by `EvaluationMeasurementIdentity` and the CV assessment path without creating a second store/registry;
3. preserve only the training-bearing projection of held-out geometry needed by preparation, namely the required composition-set/transfer-consumer identity; held-out labels and measurement serialization remain excluded from training identity/preparation;
4. keep historical pre-cutover roots immutable even when they contain legacy outer-evaluation materialization; reuse those bytes only through exact D2.DEF.060B measurement-equivalence authentication and never rewrite them into the new topology;
5. add falsification proving a held-out label/reference/measurement-artifact-only change leaves `TrainingTrajectoryIdentity`, fitted preparation, training materialization, sealed root and TRAIN2 current while moving only `EvaluationMeasurementIdentity`/EVAL2 and dependent outer verdict; also prove post-cutover root certification contains no held-out outer-evaluation artifact.

Gate E remains blocked until this D4 handoff is repaired and a fresh independent Gate-D Review passes the new immutable candidate.

### Gate E - D4 implementation - BLOCKED ON GATE D ACCEPTANCE

Implement by reduction/rewiring at current owners:

- hard replay-limit policy plus diagnostic-only warning threshold;
- foundation CV `75/75` and production `50` role defaults plus local checkpoint-policy generation migration under campaign schema v2;
- strict target-minimum representative selection with frozen exact ties;
- training-position identity cutover across preparation/materialization/checkpoint/runtime owners;
- terminal TRAIN2 sealing through the existing completion/topology owner and run-activity lease;
- external policy assessment/currentness locators with no assessment writes into sealed training roots;
- assessment-independent future measurement identity;
- complete outcome-discriminated production candidate-set evidence;
- one-time legacy completed/interrupted trajectory reuse and current-CV reauthorization;
- currentness/recovery narrowing;
- diagnostics and docs.

Do not introduce a new parallel trainer/evaluator/policy graph.

### Gate F - Focused and affected regression

Execute the complete matrix in section 10 through real semantic owners.

Include old-workspace recovery fixtures whose obsolete assessment ancestry covers the former replay threshold binding and historical generated foundation-CV `0.045/0.045` / production `0.030` defaults. Prove zero training launch whenever training-bearing semantics are otherwise identical.
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
- stale `0.045/0.045` foundation-CV defaults or stale `0.030` foundation-production target default;
- secondary/uncertainty target ordering overriding raw target minimum;
- retraining on policy-only edits;
- silent legacy custom-config reinterpretation;
- historical evidence mutation;
- scratch collateral changes or incorrect CV migration/currentness;
- duplicate policy/currentness machinery;
- missing negative-production EVAL2 persistence;
- assessment files or policy diagnostics written into a post-cutover sealed training root;
- reassessment reading sealed root bytes without the existing run-activity/storage exclusion, permitting concurrent archive/dedup/reclamation races;
- warning/hard/target/selection policy consulted before TRAIN2 recovery;
- training-position identity omitting preparation/validation/composition-transfer inputs that can change materialization;
- current final publication derived from reusable historical production bytes after current CV rejection;
- global campaign-schema bump or second evidence store introduced solely for this local change.

Close only after affected documentation/history/dependency and PEM learning assessment are reconciled.

---

## 14. Acceptance criteria

The cycle may close only when all of the following are true:

1. A new Protocol 6.4 D1/D2 amendment from baseline `a759e81...` explicitly authorizes the new semantics and passes independent review/ratification.
2. Replay warning default is `0.050 eV/angstrom` and hard catastrophic default is `0.100 eV/angstrom`, both configurable; warning-threshold changes have diagnostic-only currentness.
3. Foundation final-production target default is `0.050 eV/angstrom`; foundation CV defaults are `0.075/0.075 eV/angstrom`; all are configurable by role and scratch remains separately governed.
4. Representative selection is minimum authoritative target force RMSE among hard-admissible checkpoints, with deterministic exact-tie handling only.
5. `single_best_final_seed` uses the same strict target-RMSE ordering across already-frozen admissible seed representatives; `all_qualified_final_seeds` is unchanged.
6. Replay warning/margin, secondary target diagnostics, maturity, practical-equivalence and bootstrap uncertainty cannot override a strictly better target RMSE.
7. Replay warning alone never rejects a checkpoint; `DeltaR > 0.100` under defaults rejects as catastrophic forgetting.
8. TRAIN2 remains fixed-budget and threshold/selection-policy independent.
9. Replay assessment thresholds and P5 checkpoint-selection policy are no longer training-trajectory identity; role assessment plans explicitly bind the role-effective hard-decision digest and strict P5 selection identity while excluding warning-only policy.
10. Policy-only role-plan edits do not create a distinct training trajectory owner; genuinely different training positions remain fail-closed for continuation.
11. Future evaluation measurement identity does not change solely because assessment policy/run-plan identity changes; reuse still requires exact checkpoint/population/provider/metric equivalence.
12. Existing checkpoint bytes/history/runtime summaries and sealed legacy run roots remain immutable and reusable under proven training equivalence.
13. Historical EVAL2 measurements are reused only when exact measurement equivalence is provable; otherwise EVAL2 is recomputed without TRAIN2 retraining. Historical verdicts are never relabeled current in place.
14. Every affected historical CV fold is reselected under current policy; changed representatives purchase only required outer evaluation, and any newly current CV verdict is freshly published.
15. Historical successful or failed final-production trajectories reuse completed TRAIN2; lack of a durably bound old candidate set causes EVAL2 recomputation, never content-store scanning or retraining.
16. Future final-production assessment evidence is outcome-discriminated and binds the complete candidate set for selected and no-admissible outcomes before publication/failure.
17. Global campaign schema remains v2; the generated `post_selection_checkpoint_policy_generation = "p5_target_replay_v2"` marker owns the narrow migration. Historical generated foundation CV `0.045/0.045`, production target `0.030`, and replay `30.0` migrate by the explicit rules; non-default CV/production values remain explicit overrides, custom/ambiguous legacy replay values fail closed, and explicit `0.045/0.045/0.030` under the new marker remain configurable.
18. Warning diagnostics are not hard-decision ancestors; changing only the warning threshold cannot move representative/CV/publication membership.
19. New post-cutover run roots are training-only, are sealed under the run-activity lease at authenticated terminal TRAIN2 before EVAL2, and current assessments never mutate their topology.
20. Training-position identity is the singular acyclic **pre-fit** restart/root owner; fitted preparation/materialization/checkpoint/runtime are descendants and exact realized preparation state is separately authenticated for continuation. Assessment-only edits reproduce the identity and every tested pre-fit training-bearing edit changes it.
21. Replay execution/recovery is resolved without current checkpoint-admissibility policy; hard assessment begins only after authenticated TRAIN2 at EVAL2.
22. Current CV/final assessments are deterministically locatable through the existing CampaignStore pointer seam keyed by selected binding + assessment role + narrow assessment-position-policy digest + training trajectory + seed/fold position. Final-seed assessment excludes current-CV authorization and D2.DEF.059B/publication mode; no content-store scan, run-root assessment file, or second evidence store is introduced.
23. Historical interrupted trajectories continue only under exact historical fitted-preparation/runtime/protocol ancestry after explicit training-equivalence proof. Already sealed completed roots are reused without modification; terminal-but-unsealed roots permit only the authenticated append-only manifest/anchor seal and never rewrite existing bytes or hashes.
24. Historical final-production training may be reassessed only after current CV reclosure accepts; current CV rejection blocks current final publication regardless of retained final checkpoint quality.
25. Existing completion/topology/cold-storage ownership remains create-once, closed-subtree certifiable and lease-safe after TRAIN2 becomes a recognized terminal proof, with opened-descriptor no-follow authentication, non-reclaimable owner proof infrastructure, assessment-file-independent completion, idempotent proof reuse and fail-closed tamper handling preserved; every later root-consuming EVAL2/reassessment uses the existing run-activity lease to exclude concurrent storage mutation.
26. Current method/policy/evidence lineage remains singular and acyclic; no compatibility wrapper, shadow registry, duplicated threshold authority, second checkpoint selector, or second evidence store is added.
27. Focused, affected, real-owner and bounded scientific qualification evidence passes on the exact candidate.
28. Independent assembled Protocol 6.4 review passes.
29. Production-scale GPU qualification remains deferred to the final complete release package.

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
- training-root sealing before EVAL2 cannot be represented by the existing completion/topology owner without a second competing storage authority;
- current assessments cannot be located outside the sealed training root through the existing post-selection pointer/currentness infrastructure without a second store;
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