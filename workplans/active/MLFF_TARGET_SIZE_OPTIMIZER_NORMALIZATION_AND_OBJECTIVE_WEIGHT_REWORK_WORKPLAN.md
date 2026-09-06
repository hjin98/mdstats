---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-05
amended_date: 2026-09-05
review_revision: 2
reviewed_source_branch: fix/mlff-prepared-common-atomic-reference-order
reviewed_code_baseline: aeba206cc1a172a87618b14ff4ae23ef0b560613
reviewed_plan_head: 14fd249006d225608876b3df0c11ccce1c2a6d60
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
---

# MLFF target-size optimizer normalization, practical-ceiling selection, and objective-weight rework

## Status and authority

**PASS / implementation-ready after final Software Design closure review.**

This document is the snapshot-complete current implementation authority for this bounded rework. It preserves the accepted V7 target-size architecture except where it explicitly amends it below. In particular, it supersedes earlier V7/P2 wording that treats `nonconverged_at_configured_ceiling` as a blocking target-size failure.

The rework has three coupled purposes:

1. remove the optimizer-progress confound from the target-size convergence experiment by normalizing learning-rate amplitude and EMA update time against one configurable reference size;
2. correct the executable MACE loss/weight realization so the configured mdstats objective is the objective actually optimized; and
3. change configured-ceiling semantics so a materially best practical upper limit is a valid selected size with a non-blocking warning, not a hard stop that prevents post-selection training.

The third item is a product-semantic change, not an error-handling relaxation. The configured target-size ceiling is a practical resource/data limit. The experiment should prefer a smaller size when the evidence supports a plateau or an interior/reflection optimum; when accuracy is still materially improving at the configured practical ceiling, the scientifically honest result is to select that ceiling and record that convergence was not demonstrated within the affordable ladder.

No implementation may reinterpret old fixed-LR/fixed-EMA/old-loss or old blocking-ceiling evidence as if it were produced by this corrected methodology.

---

## 1. Problem / product invariants

### 1.1 Target-size scientific question

The target-size experiment asks:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

A candidate remains exactly:

```text
T_N = pi_train[:N]
```

`N` remains the sole target-size independent data-cardinality variable. The ordered optimizer-seed set remains the stochastic replicate dimension. Ranking remains target-side EVAL2 evidence only.

The experiment must distinguish two different conclusions:

- **evidence-supported truncation**: a smaller size is practically equivalent to, or better than, the larger finalist, so there is direct evidence to stop below the ceiling;
- **practical-ceiling selection**: the largest configured candidate remains materially superior at the terminal comparison, so convergence was not demonstrated within the available ladder, but the best permitted target size is still well defined and usable.

The second conclusion is not an operational or methodological failure. It is a selected result with a warning that the selected size is budget-limited rather than convergence-limited.

### 1.2 Practical-equivalence semantics remain authoritative

The existing practical-equivalence threshold remains the definition of a plateau for target-size ranking.

At the terminal comparison:

- if two finalists differ by no more than `practical_equivalence_mev_per_a`, the smaller finalist is preferred;
- if a smaller finalist has lower target-force RMSE, it is preferred normally;
- if the configured `Nmax` is lower in paired-mean target-force RMSE than every other successful terminal finalist by **more than** the practical-equivalence threshold, `Nmax` is selected and the result carries a non-convergence warning.

Thus a raw numerical improvement at `Nmax` that is inside the practical-equivalence band is treated as a plateau, not as unresolved convergence.

No additional curve-fitting, derivative test, monotonicity model, reflection detector, or trend extrapolator is required. The existing terminal ranking evidence already expresses the needed decision: practical equivalence favors the smaller size; a genuinely lower interior finalist wins; only material superiority at `Nmax` produces the ceiling warning.

### 1.3 Blocking outcomes remain genuinely blocking

A selected-at-ceiling warning must not be confused with incomplete or invalid evidence.

The following remain blocking scientific/execution outcomes under their existing owners:

- too few complete comparable terminal candidates;
- malformed, missing, duplicated, reordered, or lineage-incompatible boundary evidence;
- authenticated numerical failures that leave the reducer unable to make the required comparison;
- ordinary execution, persistence, corruption, configuration, or orchestration failures.

The reducer must never fabricate a ceiling selection when the terminal comparison is incomplete.

### 1.4 No rescue beyond the configured ladder

The configured largest candidate remains the target-size ceiling. The corrected behavior does not invent, extrapolate, or schedule any unconfigured larger size.

Selecting the ceiling with a warning means exactly:

> `Nmax` is the best supported choice within the configured practical budget, while the screen did not establish a plateau before that limit.

It does not claim that `Nmax` is asymptotically converged or that still larger datasets would not improve the model.

---

## 2. Frozen high-level architecture

The following architecture remains Frozen:

```text
canonical frame authority
  -> neutral statistical substrate
  -> one P_train / M3 split
  -> one pi_train / pi_eval
  -> one common deterministic preparation
  -> paired (N, optimizer-seed) screen
  -> exact n1 -> n2 -> n3 continuation
  -> direct M1/M2/M3 EVAL2
  -> one target-size reducer
  -> one N_selected / T_selected
  -> post-selection CV on exactly T_selected
  -> fresh final production on exactly T_selected
```

The following are also Frozen for this cycle:

- exact nested `T_N = pi_train[:N]` membership;
- configured candidate ladder and ceiling;
- configured evaluation ladder and exact direct M1/M2/M3 populations;
- `q -> min(q,4) -> 2 -> 1` successive-halving funnel shape;
- paired optimizer-seed aggregation by arithmetic mean;
- target-force RMSE ranking metric;
- practical-equivalence smaller-size preference;
- one continuous candidate trajectory across `n1 -> n2 -> n3`;
- EVAL2 evaluation of the authenticated configured model state (EMA when enabled);
- P4 currentness/terminal projection ownership;
- P5 post-selection CV and fresh-production ownership;
- final production never resumes from a screen or CV checkpoint;
- full long GPU/production qualification remains deferred to final release.

The only P2 decision-semantic amendment is the disposition of the materially superior configured ceiling: it becomes `SELECTED` with warning metadata instead of a blocking `NONCONVERGED_AT_CONFIGURED_CEILING` current outcome.

No second selector, warning lifecycle, fallback training path, alternate reducer, rescue ladder, or parallel state machine may be introduced.

---

## 3. Target-size optimizer-normalization policy

### 3.1 One configurable reference policy

Introduce one serializable target-size optimizer-normalization policy with a fixed algorithm identity and these defaults:

```text
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

Canonical user-facing configuration:

```toml
[target_data.size_convergence.optimizer_normalization]
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

Validation:

- `reference_target_size` is a positive integer;
- `reference_learning_rate` is finite and strictly positive;
- `reference_ema_decay` is finite and satisfies `0 < beta < 1`;
- the reference size need not be a candidate and need not lie inside the configured ladder.

The numerical reference values are user-configurable. The normalization algorithm/version is specification-owned and is not an arbitrary user plugin string.

### 3.2 Exact batch-aware realization

For the current target-size screen, replay exposure is `none`. Let `B` be the authenticated target-size batch size.

```text
U_ref = ceil(N_ref / B)
U_N   = ceil(N / B)
s_N   = U_ref / U_N
```

Derive:

```text
effective_base_learning_rate(N) = reference_learning_rate * s_N
```

and, when EMA is enabled:

```text
effective_ema_decay(N) = reference_ema_decay ** s_N
```

For an exact doubling of update geometry:

```text
LR_(2N)   = LR_N / 2
beta_(2N) = sqrt(beta_N)
```

No hidden cap, floor, clipping, survivor-dependent rescaling, or candidate-specific override is allowed.

### 3.3 What normalization means

The current TRAIN2 learning-rate schedule already uses normalized update progress. Preserve that shape and change only candidate-specific amplitude.

Normalize only the two update-count clocks established by this design:

- LR amplitude;
- EMA decay.

Keep fixed across candidates:

- epoch/fidelity boundaries and number of dataset passes;
- batch size;
- LR phase fractions and normalized-progress multiplier shape;
- Adam/AMSGrad settings and moment coefficients;
- weight decay;
- gradient clipping;
- model precision and architecture;
- acceleration policy;
- optimizer-seed set;
- objective/configuration/property weighting policy.

This is a first-order optimizer-progress normalization, not a claim of exact optimizer-path equivalence. Differences from minibatch noise, Adam history, and finite discretization of the analytic LR curve are accepted residuals, not additional variables to compensate with more machinery.

### 3.4 One realization per full candidate trajectory

For each `(N, optimizer_seed)`:

- derive `s_N`, effective LR, and effective EMA once from the full candidate geometry;
- bind them into the authenticated candidate realization;
- use exactly the same realized values through all `n1 -> n2 -> n3` continuation;
- never recompute normalization from the survivor set or active rung.

`execution_epoch_limit` remains the rung pause mechanism; it must not redefine the full schedule.

### 3.5 Screen control versus post-selection training

Normalization is a control of the target-size comparison experiment. It does not make screen checkpoints production parents and does not require final production to inherit a candidate-specific screen LR/EMA realization.

Post-selection CV/final production start fresh under their own accepted method/role policy. The architecture documentation must distinguish the coverage-normalized size-comparison protocol from the fresh post-selection training run.

---

## 4. P2 terminal-decision policy and identity

### 4.1 Preserve P2 membership science; amend terminal disposition

Optimizer normalization itself belongs to P3 execution-scientific identity and must not change P_train/M3, pi_train/pi_eval, candidate qualification, hard-support obligations, or M1/M2/M3 membership.

The configured-ceiling decision rule, however, **is P2 target-size scientific policy** because it changes which terminal evidence produces `N_selected`. Therefore current P2 policy/definition identity must explicitly bind the corrected terminal-decision semantics.

The implementation may use a fixed policy/version token such as:

```text
practical_equivalence_then_practical_ceiling.v2
```

or an equivalently explicit schema/algorithm version. The exact symbol name is delegated. The required semantic identity is not.

Changing from the old blocking-ceiling rule to the new practical-ceiling rule must change the P2 scientific policy/experiment-definition identity so old reducer evidence cannot be replayed under the new meaning.

### 4.2 Current terminal decision table

At the terminal boundary, after the existing exact paired-seed aggregation and practical-equivalence ranking:

#### A. Plateau / practical equivalence

If `Nmax` is numerically best but a smaller finalist is within the practical-equivalence threshold, select the smaller finalist with ordinary `SELECTED` semantics and no ceiling non-convergence warning.

#### B. Interior/reflection winner

If a smaller finalist has the best terminal score according to the existing ranking, select that finalist normally. No extra reflection-point classifier is needed.

#### C. Practical ceiling remains materially superior

If `Nmax` is present in the successful terminal comparison and is materially superior to every other successful terminal finalist by more than the practical-equivalence threshold:

```text
status = SELECTED
selected_target_size = Nmax
selected_membership_digest = candidate_digest(Nmax)
terminal_reason_codes includes "nonconverged_at_configured_ceiling"
```

The reason code is a **non-blocking scientific warning** because the primary reducer disposition is `SELECTED`.

The human-readable meaning is:

> The configured practical ceiling is the best evaluated permitted size; target-size convergence was not demonstrated within the configured ladder.

#### D. Insufficient comparison

If the terminal matrix does not contain enough authenticated comparable successful candidates, retain `INSUFFICIENT_COMPARISON` or the existing appropriate failure disposition. Do not select `Nmax` merely because it is the last surviving numeric size.

### 4.3 No new selected-with-warning status

Do not add a new reducer status or campaign lifecycle solely to represent the warning.

`SELECTED` plus existing terminal diagnostic metadata is sufficient and is preferred because:

- downstream consumers already authorize post-selection work from selected state;
- selected membership remains bound exactly once;
- warning severity is encoded by the selected disposition plus reason metadata;
- no duplicate terminal-state transition or P5 admission path is needed.

`terminal_reason_codes` is the preferred existing metadata carrier. For `SELECTED`, any configured-ceiling non-convergence code is diagnostic/warning metadata, not a failure reason.

The historical enum/value `NONCONVERGED_AT_CONFIGURED_CEILING` may remain readable only if needed for historical compatibility. The corrected current reducer must not emit it. An old generation carrying that old status is not retroactively converted into a selection; the corrected methodology requires new evidence under the new identity.

### 4.4 P4/P5 downstream consequences

A selected-at-ceiling result must follow the exact same authoritative path as any other selection:

```text
P2 reducer SELECTED with Nmax + warning
  -> P3 terminal head
  -> P4 TERMINAL_SELECTED projection
  -> exact N_selected / T_selected binding
  -> P5 post-selection CV
  -> fresh final production if CV accepts
```

The warning must not route the campaign into `TERMINAL_SCIENTIFIC_FAILURE`, must not make lifecycle `advance` stop, and must not block `load_current_selected_training_context()`.

CLI/status/result views must surface the warning while still presenting the target size as selected and frozen. The next admissible lifecycle command must remain `cross-validate`.

---

## 5. Objective and weighting repair

### 5.1 One canonical objective resolver

Current target-size preparation falls back to `TargetSizeCommonTrainingPolicy()` defaults while post-selection resolves `[objective]`. That is not acceptable even though the defaults currently happen to be the same.

Create or reuse one canonical config-to-objective/common-training resolver so target-size common preparation and post-selection consume the same `TrainingObjectivePolicy` semantics.

At minimum `[objective]` continues to own:

```text
energy_weight
forces_weight
stress_weight
```

with default ratio:

```text
1.0 : 10.0 : 1.0
```

The common/prepared-generation semantic identity must change when this objective/common weighting policy changes. A user override may not be silently ignored by target-size preparation.

### 5.2 Separate global objective coefficients from local weights

Restore these distinct owners:

- `TrainingObjectivePolicy.energy_weight / forces_weight / stress_weight`: global loss-component coefficients;
- `ConfigurationWeightPolicy`: per-configuration modifier;
- frame-local property weights: local property modifier / missing-label mask.

Absent an additional explicit local property-weight rule, frame-local property weights are:

```text
1.0 when the property is present
0.0 when the property is absent
```

Do not copy the global 1:10:1 objective ratio into every per-frame property weight.

If persisted `FrameTrainingWeight` semantics would otherwise change under the same schema, evolve the owning schema/identity so old 1:10:1-per-frame payloads are not silently reinterpreted as local masks.

### 5.3 Emit global objective coefficients explicitly

Every current MACE training config that consumes mdstats weights must explicitly emit the resolved global E/F/S coefficients. This includes:

- target-size candidate training;
- post-selection CV;
- post-selection final production.

No current path may rely on MACE's default `forces_weight=100`.

### 5.4 Use executable MACE loss semantics that honor the declared weighting contract

Pinned MACE 0.3.16 `UniversalLoss` is not a correct realization of the declared mdstats weighting model because:

- its per-config property weights scale residuals inside Huber evaluation, so they are not linearly equivalent to global objective coefficients; and
- it does not consume `config_weight` as the declared configuration-weight policy requires.

The preferred narrow dependency-native realization is MACE's weighted energy+force+stress loss (`loss="stress"`, `WeightedEnergyForcesStressLoss`), whose native helper reductions consume `ref.weight` and local property weights linearly while applying global E/F/S coefficients explicitly.

This is a suggested realization below the product-level weighting contract, not permission to preserve `universal` with compensating patches.

Do not add a custom patched `UniversalLoss`, square-root weighting trick, residual pre-scaling workaround, duplicated-sample approximation, or second mdstats loss engine merely to retain the old loss string.

A real pinned-MACE boundary test must prove the chosen native realization satisfies the declared configuration/property/global weighting semantics. If it does not, stop and reopen the loss-realization design rather than layering another workaround.

### 5.5 Loss family is method identity

The actual executable loss family must be explicit in the relevant MACE/model/training-method identity. Historical checkpoints generated under the old loss semantics cannot be prefixes or equivalents of corrected trajectories.

---

## 6. Identity and invalidation

### 6.1 Normalization identity

The complete optimizer-normalization policy belongs in P3 execution-scientific identity.

Candidate realization must bind or deterministically re-derive at minimum:

```text
normalization_policy_digest
reference_updates_per_epoch
optimizer_progress_scale
effective_base_learning_rate
effective_ema_decay (or explicit None if EMA disabled)
realized_learning_rate_policy_digest
```

Restart validation must reject drift in these values.

### 6.2 Target-size decision identity

The corrected configured-ceiling terminal rule must participate in P2 policy/experiment-definition identity. A current reducer must not be able to consume an old definition whose digest was produced under the blocking-ceiling rule.

### 6.3 Objective/loss identity

Corrected objective, local-weight semantics, and executable loss family must invalidate all descendants whose optimization meaning changes, including as applicable:

- common preparation;
- materialization/config;
- candidate trajectory;
- TRAIN2 checkpoint;
- EVAL2 evidence;
- reducer state;
- post-selection method/CV evidence;
- final-production evidence.

### 6.4 Historical evidence

Historical fixed-LR/fixed-EMA/old-loss/blocking-ceiling evidence may remain readable as history when its old schema remains supported. It must never be migrated by filling defaults or changing a status label so that it authenticates as corrected evidence.

The corrected screen must establish fresh scientific evidence under the corrected identities.

---

## 7. Implementation obligations by coherent stage

### Stage A - P2 decision semantics and current lifecycle

**Concern:** the configured ceiling is a practical budget boundary, not a requirement that convergence occur before it.

**Required end state:**

- P2 policy/definition identity binds the corrected terminal-selection rule;
- terminal `Nmax` material superiority returns `SELECTED`, exact `T_selected`, and warning code `nonconverged_at_configured_ceiling`;
- plateau/interior cases preserve current smaller-size ranking;
- incomplete comparison remains blocking;
- current reducer never emits blocking `NONCONVERGED_AT_CONFIGURED_CEILING` for new evidence;
- P4 commits selected-at-ceiling through the ordinary terminal-selection transition;
- P5 admits the exact selected ceiling into post-selection CV;
- campaign lifecycle/status/advance treat it as selected and continue to `cross-validate`;
- CLI/result metadata visibly report the warning.

**Likely affected surfaces:**

```text
mdstats/training_data/target_size_experiment.py
mdstats/training_data/campaign_target_size_state.py
mdstats/training_data/campaign_target_size_terminal.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_target_size_view.py
mdstats/training_data/campaign_lifecycle.py
mdstats/training_data/campaign_post_selection.py
```

Avoid adding a warning-specific state machine. Reuse selected state plus diagnostic metadata.

### Stage B - optimizer-normalization policy/config

**Required end state:**

- one versioned normalization policy type;
- one canonical resolver for the nested config table;
- defaults exactly `1024 / 1e-4 / 0.99999`;
- generated/example/user config surfaces expose those values;
- target-size reference LR/EMA come from this policy, not a competing hidden `[training].learning_rate` fallback;
- normalization-only changes do not change P1/P2 membership/common-preparation payloads, apart from the independent fixed P2 decision-policy version introduced in Stage A.

Likely surfaces include:

```text
mdstats/training_data/target_size_execution/schedule.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/_campaign_cli_core.py
campaign.toml.example
```

### Stage C - common objective authority

**Required end state:**

- target-size and post-selection use one resolved objective meaning;
- target-size no longer ignores `[objective]` overrides;
- common/prepared identity binds objective/common weighting policy;
- global objective and local/configuration weighting semantics are separated.

Likely surfaces:

```text
mdstats/training_data/target_size_execution/common.py
mdstats/training_data/objectives.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_prepared_generation.py
```

Prefer reusing/extracting current post-selection resolution rather than creating a parallel parser.

### Stage D - candidate realization and exact continuation

**Required end state:**

- execution context binds normalization policy;
- candidate realization derives exact `U_ref`, `U_N`, scale, effective LR, effective EMA, and realized LR policy identity;
- MACE config and TRAIN2 runtime plan agree on the same realized policy;
- boundary continuation preserves the exact same realization across all rungs;
- restart drift is diagnosed and rejected.

Likely surfaces:

```text
mdstats/training_data/target_size_execution/context.py
mdstats/training_data/target_size_execution/candidate.py
mdstats/training_data/target_size_execution/schedule.py
mdstats/training_data/target_size_execution/execution.py
mdstats/training_data/train2_policy.py
mdstats/training_data/train2_runtime.py
```

### Stage E - MACE objective realization

**Required end state:**

- all current MACE configs emit configured global E/F/S weights;
- local property weights carry corrected local semantics;
- configuration weights are actually consumed by the selected native MACE loss;
- target-size, CV, and final production share the same objective-weight ownership model;
- model reconstruction/EVAL2 identity recognizes the corrected loss family.

Likely surfaces:

```text
mdstats/training_data/target_size_execution/candidate.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/model_features.py
mdstats/training_data/mace_export.py
mdstats/training_data/target_size_execution/export.py
```

Do not refactor retired/unreachable DATA8 paths solely for consistency. If a historical helper is still reachable from a current command or qualification consumer, it is affected and must satisfy the same invariant.

### Stage F - durable cutover/currentness

**Required end state:**

- corrected P2/P3/method identities distinguish new evidence from old evidence;
- stale trajectories/configs/checkpoints/reducer states fail authentication before execution or adoption;
- old blocking-ceiling states remain historical and are not reclassified in place;
- immutable reusable content is reused only when its semantic identity is genuinely unchanged;
- no new migration registry or parallel state authority is introduced.

### Stage G - documentation synchronization

Update current durable documentation at minimum:

```text
docs/arch_manuals/mlff_training_data/30_statistical_design.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/50_target_size_selection.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
docs/arch_manuals/mlff_training_data_architecture.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/guides/mlff_campaign_cli_user_guide.md
campaign.toml.example
```

Documentation must state clearly:

- configured ceiling is a practical limit;
- a materially superior ceiling is selected with a non-convergence warning;
- practical equivalence still favors the smaller size;
- insufficient comparison remains blocking;
- no unconfigured rescue size is created;
- LR/EMA normalization defaults/formulas;
- EMA is normalized because EVAL2 evaluates EMA when enabled;
- screen normalization is distinct from fresh post-selection optimization state;
- global objective versus local/configuration weighting ownership;
- actual MACE loss family/semantics;
- historical evidence invalidation.

---

## 8. Task-specific acceptance

Functional testing is mandatory after each material stage and again after the assembled implementation. Full production/GPU qualification remains deferred.

### 8.1 Reducer decision tests

Prove at the real P2 reducer owner:

1. `Nmax` materially superior by more than epsilon -> `SELECTED`, `N_selected=Nmax`, exact selected membership digest, warning code `nonconverged_at_configured_ceiling`;
2. `Nmax` raw-best but within epsilon of a smaller finalist -> smaller finalist selected, no ceiling warning;
3. smaller finalist has lower terminal score -> smaller finalist selected normally;
4. `Nmax` is not a terminal finalist -> ordinary finalist selection, no ceiling warning;
5. incomplete/reordered/foreign terminal matrix -> no fabricated selection;
6. numerical failure leaving too few comparable finalists -> insufficient comparison remains blocking;
7. warning metadata survives reducer serialization/replay validation exactly;
8. the terminal-decision policy/version changes P2 policy/definition identity relative to the old rule.

The test fixture must preserve paired arithmetic-mean semantics and the actual practical-equivalence rule; do not prove the new behavior by bypassing `_equivalence_order` or seeding a post-decision reducer state.

### 8.2 P4/P5 owner-boundary acceptance

Using the real current terminal projection/lifecycle/current-selected-context owners with only expensive training/inference below them replaced as allowed:

- drive a reducer to selected-at-ceiling with warning;
- adopt/commit the actual terminal head;
- prove campaign lifecycle is `TERMINAL_SELECTED`, not scientific failure;
- prove exact `N_selected/T_selected` re-derivation succeeds;
- prove `load_current_selected_training_context()` succeeds;
- prove `status`/result view exposes the warning;
- prove lifecycle `next_command`/`advance` routes to `cross-validate`;
- prove historical blocking-ceiling evidence is not silently converted to current selected evidence.

A helper-only assertion that constructs `TargetSizeTerminalProjection` directly is insufficient for this product claim.

### 8.3 Normalization-policy tests

Prove exactly:

1. defaults resolve to `1024 / 1e-4 / 0.99999`;
2. overrides serialize and participate in identity;
3. invalid reference values fail closed;
4. `N_ref` need not be a candidate;
5. `N=N_ref` gives scale 1 and exact reference LR/EMA;
6. half/double update geometry gives expected LR and EMA transformations;
7. non-power-of-two cases use `ceil(N/B)` exactly;
8. no cap/floor is applied.

### 8.4 Mathematical realization tests

For representative N/B pairs prove:

```text
U_ref = ceil(N_ref/B)
U_N = ceil(N/B)
scale = U_ref/U_N
```

and:

```text
effective_base_lr_N * U_N ~= reference_lr * U_ref
(effective_beta_N ** U_N) ~= (reference_beta ** U_ref)
```

at justified floating tolerance.

Separately prove the normalized-progress LR multiplier shape is unchanged. Do not claim exact equality of the discrete sum of scheduled LR values over differently sampled update grids.

### 8.5 Identity/restart tests

Prove:

- changing reference size/LR/EMA changes P3 execution/trajectory identity;
- normalization-only changes leave P2 membership/order/common statistical products unchanged;
- changing the terminal-decision policy changes P2 policy/definition identity;
- changing `[objective]` changes common-preparation/method identity;
- stale fixed-LR trajectories cannot resume;
- changed normalization cannot resume another policy's checkpoint;
- boundary continuation preserves one realized LR/EMA trajectory;
- survivor elimination does not alter the reference or surviving candidate realization.

### 8.6 Objective/config tests

Prove:

- `[objective] = 1:10:1` reaches target-size common policy, post-selection method policy, and MACE configs;
- non-default objective overrides propagate consistently;
- global coefficients appear exactly once at the global MACE loss layer;
- local property weights are availability/local modifiers rather than duplicated global coefficients;
- configuration weights remain independent and nontrivial where policy requires them;
- normalization-only edits do not invalidate common preparation;
- objective edits do invalidate common preparation.

### 8.7 Pinned-MACE real semantic boundary

Against pinned MACE 0.3.16:

1. parse a generated corrected config;
2. instantiate the actual loss through MACE's real loss resolver;
3. prove the selected loss family is the accepted weighted energy+force+stress implementation (or an equivalent native implementation established by the same evidence);
4. prove global E/F/S coefficients equal mdstats resolved objective;
5. use a tiny batch with distinct `config_weight` and local property weights and prove the real loss responds according to the declared weighting contract;
6. prove local zero property weight masks a missing property as intended;
7. prove the corrected path does not accidentally instantiate old `UniversalLoss` semantics.

Config-text inspection alone cannot close this claim.

### 8.8 Real target-size integration

Using the real P3/P4 orchestration and bounded expensive dependency substitution where appropriate:

- materialize at least two candidate sizes on opposite sides of `N_ref`;
- verify distinct derived LR/EMA with identical epoch/pass policy;
- execute at least one continuation sequence through multiple boundaries;
- authenticate EMA/live evaluation state as applicable;
- commit/reconcile through the actual reducer/head/currentness owners;
- cover both an interior/plateau selection and a selected-at-ceiling warning path;
- verify no alternate current route bypasses normalization or the corrected terminal semantics.

### 8.9 Affected regression

At minimum include the affected families covering:

```text
tests/test_mlff_target_size_statistical_authorities.py
tests/test_mlff_target_size_execution_p3a.py
tests/test_mlff_target_size_execution_p3b.py
tests/test_mlff_target_size_execution_p3c.py
tests/test_mlff_target_size_execution_p3d.py
tests/test_mlff_target_size_execution_p3e.py
tests/test_mlff_target_size_execution_p3f.py
tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
tests/test_mlff_target_size_p4*.py
tests/test_mlff_target_size_p5*.py
tests/test_mlff_doc_arch1_specification.py
tests covering campaign lifecycle/status/advance
tests covering prepared-generation config identity
tests covering post-selection identity/execution/materialization
tests covering MACE export/realization/real-MACE contracts
tests covering TRAIN2 policy/runtime continuation
```

Re-derive the final affected surface from the assembled implementation. If broader than this initial map, run the broader affected suite. If impact cannot be bounded confidently, run the full relevant MLFF suite.

---

## 9. Compatibility policy

This is a scientific-method change, not a backward-compatible reinterpretation of existing evidence.

Required posture:

- old evidence may remain readable under its original schema/identity when historical support is retained;
- old evidence must never be resumed/reduced/adopted as corrected evidence;
- old `NONCONVERGED_AT_CONFIGURED_CEILING` states are not rewritten into successful selections;
- the new selected-at-ceiling result must be generated by the corrected reducer under the corrected P2/P3/method identities;
- schema evolution is required wherever identical serialized fields would otherwise acquire materially different meaning;
- content-addressed artifacts may be reused only when their semantic parents are unchanged.

If the existing campaign state model cannot safely replace only the affected descendants, prefer a fresh canonical generation that reuses still-valid immutable content over a new in-place migration mechanism.

---

## 10. Delegated solution space

The implementer may choose local symbol names, schema version numbers, helper placement, and compact refactors provided all Frozen semantics hold.

Preferred simplicity:

- one P2 terminal-decision policy/version identity;
- existing `SELECTED` state plus warning metadata, not a new status/lifecycle;
- one optimizer-normalization policy type and resolver;
- one objective/common-policy resolver;
- one candidate realization formula;
- existing P3/P4/P5 currentness and restart machinery;
- dependency-native MACE loss semantics rather than custom patched loss machinery.

Existing code, enums, serializers, helpers, and tests are Tier-2 realization unless specifically Frozen above. Remove or narrow obsolete blocking-ceiling branches when safe; retain historical readers only where compatibility actually requires them.

Do not preserve old behavior with wrappers or aliases merely to keep old tests green. Tests asserting the old product semantics must be updated because the accepted product requirement has changed.

---

## 11. Reopen only on evidence

Reopen Software Design only if evidence proves one of these Frozen assumptions false:

1. MACE 0.3.16 does not apply EMA once per optimizer update in the actual TRAIN2 path, invalidating `beta_ref ** scale`;
2. the target-size loader has hidden duplication/resampling so `ceil(N/B)` is not actual update geometry;
3. target-size replay exposure becomes non-`none` or varies with N;
4. the candidate-specific effective LR cannot be carried through one authenticated full-n3 continuation trajectory;
5. the native weighted MACE loss fails the real boundary acceptance for configuration/property/global weights;
6. changing the loss family changes model-construction semantics in a way the existing method/model identity cannot represent;
7. the existing P2/P4/P5 authority graph cannot represent selected-at-ceiling-with-warning without a materially different high-level state architecture;
8. the campaign cannot invalidate old affected scientific descendants without reinterpreting old evidence or creating a competing currentness authority;
9. the implementation would require hidden candidate-specific tuning, empirical LR caps, an unconfigured rescue ladder, or another new independent target-size variable.

A trigger is not permission to patch around the problem. It requires bounded Design reconsideration of only the affected surface.

---

## 12. Gated implementation order

Implement in this order, with semantic/conformance closure plus stage-local affected regression at each material stage:

1. **P2 decision-policy gate** - practical-ceiling selected-with-warning semantics, P2 identity, P4/P5/lifecycle propagation.
2. **Normalization-policy gate** - config/defaults/resolution and identity.
3. **Objective-owner gate** - one config-aware objective/common policy and corrected global/local weight semantics.
4. **Candidate-identity gate** - scale/effective LR/effective EMA/realized schedule and stale-evidence rejection.
5. **TRAIN2 continuation gate** - one full-trajectory realization across exact boundaries.
6. **MACE loss/config gate** - explicit global objective and dependency-native weighting semantics across target-size/CV/production.
7. **Current-owner integration gate** - reducer/head/currentness/post-selection acceptance including ceiling warning.
8. **Documentation gate** - current architecture/spec/user guide synchronized.
9. **Final affected-surface gate** - re-derive and run complete affected regression plus assembled integration.

Do not proceed past a stage whose material semantic or functional closure is failing.

---

## 13. Final closure review

The final Software Design closure review found the following material gaps in revision 1 and closes them here:

- the old plan incorrectly said P2 remained entirely unchanged; corrected terminal disposition is now explicitly P2 scientific decision policy and identity;
- configured-ceiling non-convergence is now correctly modeled as **selected scientific result + warning**, not a hard failure;
- `SELECTED` plus existing diagnostic metadata is sufficient; no new terminal status/lifecycle is justified;
- the practical-equivalence rule now explicitly distinguishes a real plateau from a materially superior ceiling;
- an interior/reflection winner is handled by existing ranking without a new curve classifier;
- genuinely insufficient comparison remains blocking and cannot be converted into a ceiling selection;
- P4/P5/current lifecycle consequences are explicit: selected-at-ceiling must continue into CV and fresh production;
- historical blocking-ceiling evidence is not retroactively blessed; the new decision-policy identity forces corrected evidence;
- fixed configurable `N_ref/LR_ref/EMA_ref` defaults and exact batch-aware inverse-update scaling remain Frozen;
- EMA normalization remains required because EVAL2 evaluates EMA state when enabled;
- target-size normalization remains a screen-control policy rather than production checkpoint inheritance;
- target-size now consumes the explicit configured objective rather than coincidental defaults;
- global objective, local property weights, and configuration weights have separate ownership;
- pinned MACE `UniversalLoss` cannot represent the declared weighting semantics merely by moving coefficients between layers;
- real pinned-MACE loss semantics and real P2/P4/P5 owner boundaries are mandatory acceptance points;
- stale fixed-LR/fixed-EMA/old-loss/old-terminal-decision evidence is not reusable;
- full affected regression/integration is mandatory, while long GPU production qualification remains deferred to final release.

No remaining design blocker was found. The implementation search space is bounded, the changed scientific semantics are identity-safe, and the simplest existing authority path can realize the requested behavior without new state machinery.

**Final verdict: PASS / implementation-ready.**
