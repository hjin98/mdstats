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
review_state: workplan-reviewed-against-baseline-implementation
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

Replay warning status carries **zero ranking credit and zero tie-break authority**.

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

If two checkpoints have bitwise/numerically identical authoritative target RMSE under the accepted stored representation, use one deterministic non-quality tie rule already compatible with the identity model, preferably `(epoch, stable_candidate_identity)` or the minimum stable identity. The tie rule must not introduce a second scientific score.

Current P5 runtime already performs authoritative target and replay evaluation for every durable TRAIN2 checkpoint in `evaluate_post_selection_run_candidates()`. Therefore the current real P5 path can establish a true minimum over all durable checkpoints without introducing approximate shortlist semantics.


The same target-only rule governs `single_best_final_seed`: after each required production seed has already frozen its own hard-admissible representative, the single-best publication member is the representative with minimum authoritative common-monitor target RMSE. Exact ties use the same deterministic non-quality tie rule. `all_qualified_final_seeds` performs no cross-seed ranking and is unchanged.

### 2.5 No-admissible outcome

A run has no representative only when no checkpoint survives hard requirements. Replay warning alone can never create a no-admissible outcome.

A checkpoint whose target RMSE exceeds the role-effective target ceiling remains target-inadmissible. Raising the foundation-production default to `0.050` changes that default policy but does not eliminate the target-quality gate.

---

## 3. D1 authority renewal requirements

The merged Protocol 6.4 D1 is accepted-current and therefore must be explicitly reopened for this cycle. Amend the canonical owner rather than layering policy prose elsewhere.

At minimum reconcile these accepted definitions/axioms:

- `D1.DEF.022` replay lineage: preserve authenticated replay geometry, true-reference monitor, foundation/head and exposure lineage, but separate the **numerical warning/hard decision thresholds** from training/replay-data lineage so a threshold edit cannot redefine an already-realized training trajectory.
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
11. Existing valid measurements may support a new current assessment only through explicit policy-bound reassessment; historical evidence is never rewritten or silently relabeled current.

### D1 challenge/falsification questions

The D1 renewal must explicitly challenge:

- whether `0.100 eV/angstrom` catastrophic replay degradation is too loose to protect inherited capability relevant to claimed target deployment;
- whether target-only ranking can select a checkpoint whose replay behavior, while under the hard ceiling, is scientifically unacceptable for any downstream use actually claimed by mdstats;
- whether raising production target default to `0.050 eV/angstrom` conflicts with observed downstream MD adequacy requirements;
- whether `tau_CV=0.045` with `tau_prod=0.050` is coherent: CV competence may be numerically stricter than production admission, but the roles/estimands remain distinct and this must be intentional rather than accidental;
- whether any current physical/integrity gate implicitly depended on the old `0.030` replay value;
- whether final cross-seed strict target ordering changes publication semantics in a way requiring a distinct D1 publication statement.

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

Specify one deterministic exact binary64 target-RMSE tie rule independent of replay quality and other scientific-quality metrics. Prefer stable checkpoint identity (and for cross-seed publication stable member/seed identity) as a non-quality deterministic tie-break. Do not recreate a tolerance band that can promote a strictly larger target RMSE.

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

Amend `D2.AX.004` currentness so assessment-policy edits stale/rebuild **assessment/verdict descendants** but not authenticated training trajectories whose training-affecting identity is unchanged. Do not declare old verdicts current by monotonic implication: a current verdict must be newly assessed under the current policy. Reuse of an old numeric measurement is permitted only when exact measurement identity/equivalence is proven.

Amend `D2.DEF.060/060A` as needed to distinguish exact training continuation identity from later assessment-policy ancestry without weakening fail-closed restart authentication.

## 5. D3 ownership and dependency repair

### 5.1 Separate three authorities

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

CheckpointAssessmentPolicy
  role target ceiling
  replay warning threshold
  replay catastrophic hard limit
  finite/integrity/physical assessment gates
  strict P5 target-RMSE selection rule identity
        |
        v
  current checkpoint assessment -> representative -> CV/final verdict/publication
```

These need not become three new classes. Prefer reusing existing digests/records and narrowing their parents. The architectural requirement is semantic separation, not type proliferation.

### 5.2 Narrow `PostSelectionMethodIdentity`

At baseline, `PostSelectionMethodIdentity` hashes two assessment-only coordinates:

```text
shared_checkpoint_constraints_digest
checkpoint_selection_policy_digest
```

Neither may remain in the TRAIN2 training-protocol identity after this revision if they contain only post-training assessment/selection semantics. Preserve genuinely training-bearing method fields. TRUE_DFT replay-monitor/data lineage may remain authenticated as required evaluation evidence without placing warning/hard numbers or target-ordering policy inside the training digest.

A one-time baseline-v3 projection may prove an existing historical method record training-equivalent to the new training identity by comparing every training-bearing field exactly and explicitly excluding only the retired assessment-only parents. This projection belongs in the existing currentness/recovery owner; it is not a general-purpose compatibility translator.

### 5.3 Correct run identity without weakening continuation guards

Current `post_selection_run_identity()` hashes the complete CV/final plan digest. Since those plans bind assessment policy, policy-only edits currently create a foreign run even when training inputs are identical.

Repair by making the run/checkpoint namespace depend on an exact **training-position projection** rather than the full assessment plan. The projection must include every coordinate capable of changing TRAIN2 bytes (role, selected/fold gradient membership, training method, seed, horizon, preparation/exposure, etc.) and exclude only post-training assessment policy.

Keep full CV/final plans as assessment/verdict authorization parents. Keep `reject_foreign_run_continuation()` fail-closed for genuinely different training positions. Do not copy checkpoints into a newly invented run merely to bypass identity mismatch and do not globally ignore plan digests.

If D3 chooses to retain full-plan `run_identity` for bookkeeping, then introduce the minimum separate authenticated training-trajectory identity used by checkpoint/restart ownership; do not weaken either identity. The required invariant is that a policy-only edit resolves to the **same training trajectory owner** while a training-bearing edit never does.

### 5.4 Separate evaluation measurement from assessment policy

Current `post_selection_eval_role_digest()` includes `run_plan_digest` and `run_identity`. That over-binds numeric measurement evidence to policy ancestry.

The current measurement owner must instead bind the exact factors that can change the numeric measurement: checkpoint/model realization, dataset role, exact membership/artifact bytes, metric/reduction policy, head/provider/precision semantics as applicable. Assessment thresholds and full role-plan digest must not be measurement identity.

Policy-bound checkpoint-assessment records may then consume immutable measurement records and produce current warnings/rejections/representatives. Historical baseline records may be reused only through a source-preserving derivation that proves the old measurement inputs equal the current measurement identity; never copy a scalar without its authenticated checkpoint/population/provider ancestry.

### 5.5 Role target default isolation

Current `[acceptance].maximum_target_force_rmse_ev_per_angstrom` supplies production for every mode and scratch CV. Preserve the single explicit public field. Change only omitted/default resolution:

```text
foundation final production omission -> 0.050
scratch omission -> existing accepted 0.030
explicit value -> preserved as written for the consumers that already own it
foundation CV -> its existing independent 0.045 checkpoint default
```

Use the existing mode-aware role-policy resolver. Do not add a duplicate production-target knob.

### 5.6 Shared replay assessment policy

Replay warning/hard values are shared checkpoint-assessment coordinates for CV/final replay-enabled foundation adaptation. They must move assessment descendants in both roles while leaving the training trajectory current. Bind them once through the existing policy-resolution owner; do not synchronize copies in CV and production policy classes.

### 5.7 Publication ordering

`single_best_final_seed` currently imports the old EVAL2 uncertainty/secondary/maturity ordering and has a dedicated decision-policy identity. Update that decision-policy identity/schema as needed so strict minimum target RMSE is reconstructable from publication evidence. `all_qualified_final_seeds` is unaffected.

### 5.8 No second policy graph

Do not add a generic P5 `TrainingProtocolIdentity`, generic `Eval2EvaluationPlan`, shadow replay-policy registry, checkpoint-selection wrapper, mutable alias, or second cache keyed only by thresholds. Current P5 authority remains role plan/run plan + existing method/policy/evidence owners, with the over-broad dependencies reduced.

### 5.9 Currentness model

Expected steady-state invalidation:

```text
change replay warning threshold
  -> checkpoint assessments/warnings + dependent verdict/publication move
  -> numeric measurements and TRAIN2 trajectory remain current

change replay hard threshold
  -> checkpoint assessments/representative + dependent verdict/publication move
  -> numeric measurements and TRAIN2 trajectory remain current

change production target threshold
  -> production assessments/representative/publication move
  -> production TRAIN2 trajectory remains current
  -> accepted CV remains current because its policy did not move

change strict P5 selection rule identity
  -> representative/verdict/publication descendants move
  -> numeric measurements and TRAIN2 trajectory remain current

change LR/loss/exposure/foundation/training membership/seed/horizon
  -> training trajectory identity moves; restart/reuse fails closed as today

change evaluation population/metric/provider semantics
  -> numeric measurement identity moves; reassessment cannot reuse stale measurements
```

This separation must be reconstructable from persisted ancestry without consulting this workplan.

## 6. D4 implementation contract

Implementation begins only after Gates B and C close on accepted amended D1/D2 and Gate D freezes the required D3 identity/currentness repair.

### 6.1 `CheckpointAdmissibilityPolicy`

Replace the single replay budget field conceptually with:

```text
replay_degradation_warning_ev_per_angstrom
replay_degradation_hard_limit_ev_per_angstrom
```

Defaults:

```text
0.050
0.100
```

Advance the policy schema because semantics materially change.

Expose separate assessment products, conceptually:

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

### 6.4 EVAL2 checkpoint evidence

Current `Eval2CheckpointRecord` stores degradation, admissibility and rejection reasons but has no durable warning field. Advance narrowly to persist diagnostic warnings, for example:

```text
diagnostic_warnings: tuple[str, ...]
```

Historical records remain immutable/readable under their historical schema.

Do not rewrite old `admissible` bits or old rejection reasons in place. A current reassessment must create current assessment evidence that points to the same authenticated measurement/checkpoint ancestry.

### 6.5 Final-production negative evidence persistence

Repair the already-confirmed production control-flow defect at the same assessment boundary:

- persist preparation/materialization as appropriate;
- persist every evaluated EVAL2 checkpoint assessment;
- only then publish/raise the terminal no-admissible production outcome.

CV already persists negative candidate evidence. Production must not discard computed authoritative metrics before reporting the negative result.

This is required for future policy reassessment and for diagnostic transparency; it does not permit promotion of an inadmissible checkpoint.

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

### 7.1 New public fields

Generated/current configuration should expose two replay fields, preferably under `[acceptance]`:

```toml
replay_degradation_warning_mev_per_a = 50.0
replay_degradation_hard_limit_mev_per_a = 100.0
```

The old generated field:

```toml
allowed_replay_degradation_mev_per_a = 30.0
```

must not remain a current one-number replay authority.

### 7.2 Legacy generated-default migration

For a legacy campaign with exactly the historical generated/default field value `30.0` and neither new field present:

- recognize it as a superseded generated default;
- resolve the new current policy to `50.0/100.0`;
- emit a bounded deprecation/migration notice;
- do not keep `30.0` as a hidden hard gate.

This rule is specifically for recognized historical default configuration so existing campaigns can resume under the newly ratified policy rather than being trapped by a stale generated value.

### 7.3 Legacy custom-value ambiguity

If the old one-number field is explicitly non-default/custom and neither new field is provided, fail with an actionable migration error rather than guessing whether that value should mean warning or hard rejection.

Do not silently reinterpret an intentional old custom value.

### 7.4 Explicit new values

Explicit new values always win when valid. Validate:

```text
finite
positive
warning < hard
```

Omission resolves exactly to the generated defaults and must yield the same policy identity as explicitly writing those defaults.

---

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

For the exact baseline v3 method/run lineage, the migration proof must cover all three old over-bindings:

1. old `PostSelectionMethodIdentity` -> new training identity, excluding only `shared_checkpoint_constraints_digest` and `checkpoint_selection_policy_digest` after proving all training-bearing fields equal;
2. old full-plan-derived run/checkpoint root -> current training-position identity, proving role/fold membership/seed/horizon and all training-bearing parents equal;
3. old plan-bound evaluation role -> current measurement identity, proving checkpoint SHA/model state, exact evaluation artifact/membership, metric policy/provider semantics and prediction digest equal.

Only after those proofs may current assessment reuse the old trajectory/measurement. A mismatch at any layer fails closed.

### 8.4 Reassessment from old measurements

If an old EVAL2 checkpoint record contains authenticated measurements on the exact current checkpoint/domain/provider semantics, reuse:

```text
target metrics
candidate replay RMSE
foundation replay RMSE
signed replay degradation
```

and recompute only warning/admissibility/selection under the new policy.

Expected monotonic cases under the default replay thresholds:

```text
DeltaR <= 0.030
  old pass -> new pass, no warning

0.030 < DeltaR <= 0.050
  old replay rejection -> new admissible, no warning

0.050 < DeltaR <= 0.100
  old replay rejection -> new admissible + warning

DeltaR > 0.100
  old replay rejection -> new catastrophic replay rejection
```

Other old rejection reasons remain independently effective.

### 8.5 Existing CV negative outcomes

Current CV all-inadmissible paths persist candidate records. When exact measurements remain current:

- reassess candidates under the new policy;
- choose the minimum-target-RMSE current representative if one now exists;
- purchase only previously absent held-out outer-fold evaluation for that newly selected representative;
- do not retrain the fold.

### 8.6 Existing failed final-production run

The diagnosed production run completed all 40 TRAIN2 epochs, but current code raised before persisting its computed EVAL2 candidate records.

For that workspace after this repair:

```text
TRAIN2 checkpoints/history -> reuse
training -> do not relaunch
EVAL2 -> recompute only because old production candidate assessments were not persisted
representative -> select by current minimum target RMSE among hard-admissible checkpoints
```

After the persistence repair, future policy changes should not require this repeated inference.

---

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
21. Exact target-RMSE ties resolve by the frozen deterministic non-quality tie rule.
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

30. Editing only replay warning threshold does not relaunch TRAIN2.
31. Editing only replay hard limit does not relaunch TRAIN2.
32. Editing only production target ceiling does not relaunch TRAIN2.
33. Editing LR/loss/exposure/foundation/replay training membership/seed/epoch budget still invalidates affected TRAIN2 evidence as today.
34. Old checkpoint SHA-256 values remain unchanged through reassessment.
35. Old runtime summaries/history are not rewritten.
36. Old valid EVAL2 measurements are reused when their measurement ancestry is current.
37. Reassessment creates current verdict/assessment evidence rather than mutating old evidence.
38. A replay-threshold-only or strict-selection-policy-only change leaves the resolved training-position identity unchanged.
39. A production-target-threshold-only change leaves the resolved production training-position identity unchanged while changing production assessment policy.
40. Changing fold gradient membership, seed, horizon, objective, exposure or foundation changes training-position identity and foreign continuation remains rejected.
41. The same checkpoint + exact evaluation artifact + metric/provider policy resolves identical measurement identity across assessment-policy-only edits.
42. Changing checkpoint SHA, monitor membership/artifact, metric policy or provider semantics changes measurement identity and prevents metric reuse.

### 10.6 CV/final integration

43. A previously no-admissible CV fold can obtain a representative from stored candidate metrics without retraining when new policy admits one.
44. Only missing held-out outer evaluation is then executed.
45. A historical CV verdict is never relabeled current merely by monotonic implication. Reuse its authenticated TRAIN2/measurement evidence where valid, then publish a new current fold/campaign assessment under the new replay policy; foundation CV target/outer thresholds themselves remain unchanged.
46. Final production with completed TRAIN2 resumes at EVAL2 without training relaunch.
47. Final-production all-inadmissible assessment persists all candidate records before terminal failure.
48. A selected warning-bearing representative publishes with a visible warning and no false failure state.
49. A selected representative above the hard replay limit is impossible.
50. `single_best_final_seed` chooses the lower authoritative target RMSE even when the other seed has better replay margin, secondary metrics, maturity or bootstrap evidence.
51. `all_qualified_final_seeds` publishes every already-qualified required representative without cross-seed ranking.
52. Changing the strict single-best publication ordering identity stales only dependent publication decisions, not per-seed TRAIN2 trajectories or numeric common-monitor measurements.

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

- remove replay thresholds **and P5 checkpoint-selection policy** from training identity at the accepted owner;
- freeze the dependency graph distinguishing training trajectory, numeric measurement, and assessment policy identities;
- repair run/checkpoint ownership so policy-only role-plan edits resolve to the same training trajectory without weakening foreign-run rejection;
- repair measurement ancestry so policy-only edits do not force inference when checkpoint/population/provider/metric semantics are unchanged;
- prove currentness/recovery can preserve old TRAIN2 without a shadow compatibility subsystem;
- freeze current evidence/schema evolution boundaries;
- reconcile production target default ownership without collateral scratch/CV change.

Independent D3 review required if durable architecture changes.

### Gate E - D4 implementation

Implement by reduction/rewiring at current owners:

- new replay warning/hard policy fields;
- production target default;
- strict target-minimum representative selection;
- durable warning evidence;
- negative-production EVAL2 persistence;
- configuration migration;
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
2. Replay warning default is `0.050 eV/angstrom` and hard catastrophic default is `0.100 eV/angstrom`, both configurable.
3. Foundation final-production target default is `0.050 eV/angstrom`, configurable; foundation CV remains `0.045/0.045` and scratch remains separately governed.
4. Representative selection is minimum authoritative target force RMSE among hard-admissible checkpoints, with deterministic exact-tie handling only.
5. `single_best_final_seed` uses the same strict target-RMSE ordering across already-frozen admissible seed representatives; `all_qualified_final_seeds` is unchanged.
6. Replay warning/margin, secondary target diagnostics, maturity, practical-equivalence and bootstrap uncertainty cannot override a strictly better target RMSE.
7. Replay warning alone never rejects a checkpoint; `DeltaR > 0.100` under defaults rejects as catastrophic forgetting.
8. TRAIN2 remains fixed-budget and threshold/selection-policy independent.
9. Replay assessment thresholds and P5 checkpoint-selection policy are no longer training-trajectory identity.
10. Policy-only role-plan edits do not create a distinct training trajectory owner; genuinely different training positions remain fail-closed for continuation.
11. Evaluation measurement identity does not change solely because assessment policy/run-plan identity changes; reuse still requires exact checkpoint/population/provider/metric equivalence.
12. Existing checkpoint bytes/history/runtime summaries remain immutable and reusable under proven training equivalence.
13. Valid old EVAL2 measurements are reassessed without inference when exact measurement equivalence is proven; historical verdicts are never relabeled current in place.
14. Old CV negative outcomes can be reconsidered without retraining; any newly current CV verdict is freshly published under current policy.
15. The diagnosed final-production workspace can reuse completed TRAIN2 and perform only missing/current EVAL2 work.
16. Future final-production negative outcomes persist all candidate EVAL2 assessments before terminal failure.
17. Legacy generated `30 meV/angstrom` replay configuration does not silently keep the old hard gate; custom legacy values are not guessed.
18. Current method/policy/evidence lineage remains singular and acyclic; no generic P5 protocol graph, compatibility wrapper, shadow registry or duplicated threshold state is added.
19. Focused, affected, real-owner and bounded scientific qualification evidence passes on the exact candidate.
20. Independent assembled Protocol 6.4 review passes.
21. Production-scale GPU qualification remains deferred to the final complete release package.

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