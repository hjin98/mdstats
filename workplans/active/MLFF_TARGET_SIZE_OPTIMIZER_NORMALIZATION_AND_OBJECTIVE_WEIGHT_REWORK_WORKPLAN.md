---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-05
reviewed_source_branch: fix/mlff-prepared-common-atomic-reference-order
reviewed_source_head: aeba206cc1a172a87618b14ff4ae23ef0b560613
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
---

# MLFF target-size optimizer-normalization and objective-weight rework

## Status

**PASS / implementation-ready.**

This workplan is a narrow methodological correction to the current V7 target-size screen plus an adjacent correction to the MACE objective realization that the same review proved is currently wrong. It does **not** reopen the P1/P2 target population, candidate/evaluation orders, successive-halving reducer, paired optimizer-seed design, EVAL2 ranking metric, exact fidelity continuation, post-selection CV topology, or fresh-production topology.

The target-size screen remains a controlled data-cardinality experiment. The correction is that candidate cardinality must not also buy proportionally more first-order optimizer progress merely because a fixed epoch contains more mini-batches. The screen therefore gains one study-wide, configurable optimization-normalization policy whose candidate realization is a deterministic consequence of exact update geometry.

The same review also found that the intended energy/force/stress objective is not faithfully realized at the current MACE boundary: target-size and post-selection configs omit the global objective coefficients, while the common preparation writes the global objective ratios into MACE per-configuration property weights. Under pinned MACE 0.3.16 `UniversalLoss`, those two weight classes are not interchangeable. That defect must be corrected in the same implementation cycle before the rerun produces new target-size evidence.

Diagnosed and frozen against `fix/mlff-prepared-common-atomic-reference-order` at `aeba206cc1a172a87618b14ff4ae23ef0b560613` under Software Development Protocol 5.15.0.

---

## 1. Problem statement and Tier-1 invariants

### 1.1 Scientific problem invariant

The governing question remains:

> What is the smallest target-training cardinality whose nested training population is sufficiently complete that increasing the amount of **unique target data** no longer yields a practically meaningful improvement on the authorized target-side evaluation population?

`N` remains the sole target-size independent variable. A candidate is still exactly:

```text
T_N = pi_train[:N]
```

and the reducer still compares only authenticated paired-seed EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

The methodological correction is that an increase in `N` must not simultaneously grant a proportionally larger first-order optimizer-time budget simply because the same number of epochs now contains more updates.

### 1.2 Frozen high-level architecture

The following V7 architecture remains Frozen:

```text
canonical frame authority
  -> neutral statistical substrate
  -> P_train / M3 split
  -> pi_train / pi_eval
  -> one common deterministic preparation
  -> paired (N, optimizer-seed) screen
  -> exact n1 -> n2 -> n3 continuation
  -> direct M1/M2/M3 EVAL2
  -> one reducer
  -> N_selected / T_selected
  -> post-selection CV
  -> fresh final production
```

No second selector, alternate candidate membership, rescue size, per-rung restart, checkpoint tie-break, or parallel training engine may be introduced.

### 1.3 Methodological amendment to the parent wording

The parent V7 plan describes non-`N` scientific choices as fixed across candidates. This amendment makes the following precision explicit:

- **study-wide policy choices remain fixed** across candidates;
- effective learning-rate amplitude and EMA decay are **not free candidate choices**;
- they vary deterministically with `N` through one frozen normalization rule and exact update geometry;
- therefore `N` remains the sole independent experimental variable.

The effective optimizer values are descendants of `N`, just as `updates_per_epoch` and `planned_updates` already are. They are not additional tunable dimensions.

### 1.4 Non-goals

Do not use this work to:

- change candidate-size or evaluation-size ladders except through their existing config;
- change `fidelity_epochs` or the successive-halving funnel;
- add adaptive epochs or matched-update epoch inflation;
- tune a separate LR/EMA value per candidate;
- add an LR cap/floor that silently breaks the normalization rule;
- rescale Adam moment coefficients, AMSGrad, gradient clipping, or weight decay without a separate evidence-backed design change;
- change precision, architecture, acceleration backend, seed population, target/evaluation membership, E0 fitting algorithm, or EVAL2 ranking semantics;
- resume final production from a screen checkpoint;
- run full production/GPU qualification in place of regression/integration testing. Full GPU qualification remains deferred to final release.

---

## 2. Confirmed current-code findings

### 2.1 Fixed epochs currently imply size-dependent optimizer work

`mdstats/training_data/target_size_execution/candidate.py::derive_target_size_candidate_realization()` already derives:

```text
structures_per_epoch = target_train_count + replay_train_count
updates_per_epoch = ceil(structures_per_epoch / batch_size)
planned_updates = updates_per_epoch * schedule.n3
```

The current target-size screen uses the same epoch boundaries and the same LR amplitude for every `N`. Therefore doubling `N` at fixed batch size approximately doubles optimizer updates before an endpoint comparison.

The current run demonstrated the concrete effect: 8192 structures over ten epochs planned 40,960 updates, while 16,384 planned 81,920. The observed size curve therefore mixes unique-data benefit with additional optimizer progress.

### 2.2 The TRAIN2 LR schedule shape is already normalized correctly; its amplitude is not

`mdstats/training_data/train2_policy.py::LearningRateSchedulePolicy` advances its analytic schedule by normalized update progress:

```text
p = update_index / (planned_updates - 1)
lr = base_learning_rate * multiplier(p)
```

That schedule shape should be retained. The rework changes only the candidate-specific base amplitude derived from one reference policy.

### 2.3 EMA is part of EVAL2 science and must be normalized

`target_size_execution.execution.target_size_evaluation_model_state()` selects `ema` whenever the target-size optimizer policy enables EMA. `target_size_execution.evaluation.authenticate_train2_checkpoint_provider()` then authenticates and loads the EMA shadow parameters before EVAL2 inference.

EMA therefore constitutes a second update-count-dependent training clock. LR-only normalization would leave a size-dependent EMA horizon and is incomplete.

### 2.4 Current P3 identity already has the right place for N-derived realization

`TargetSizeCandidateRealization` already authenticates candidate-specific update geometry, full-`n3` planned updates, loader geometry, precision realization, seed, and acceleration provenance. Restart validation re-derives these facts and rejects drift.

The new size-dependent LR/EMA realization belongs here. Do **not** mutate the generic `MaceOptimizerPolicy` into a free per-`N` policy and do not create a second candidate-policy hierarchy.

### 2.5 Target-size config currently has no normalization authority

`campaign.toml.example` exposes the candidate/evaluation/fidelity policy under `[target_data.size_convergence]`, while `_optimizer_policy()` resolves `[training].learning_rate` and otherwise inherits `MaceOptimizerPolicy.ema_decay`.

`campaign_target_size_runtime.execute_current_select_target_size()` currently creates:

```text
schedule = build_target_size_screen_schedule(definition.policy.fidelity_epochs)
optimizer_policy = _optimizer_policy(...)
```

so there is no explicit study-wide reference-size/LR/EMA normalization identity.

### 2.6 Current target-size common preparation does not consume the user-facing objective config

`campaign.toml.example` exposes:

```toml
[objective]
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0
```

and post-selection policy resolution already consumes that table. But `build_prepared_target_size_substrate()` currently calls `build_target_size_common_preparation(..., policy=None)`, causing the target-size common preparation to use `TargetSizeCommonTrainingPolicy()` defaults rather than one canonical resolved campaign objective policy.

The defaults happen to be 1:10:1 today, but an explicit user override is not authoritative for target-size preparation. That is a configuration/identity defect and must be repaired rather than obscured by the new normalization policy.

### 2.7 Global and local MACE weights are currently conflated

`TrainingObjectivePolicy` owns the global energy/force/stress objective, defaulting to 1:10:1.

Current common preparation `_fitted_frame_weights()` copies those global coefficients directly into each `FrameTrainingWeight.energy_weight`, `.forces_weight`, and `.stress_weight`, and target export writes them as MACE `config_energy_weight`, `config_forces_weight`, and `config_stress_weight`.

Current target-size `_mace_config_for_candidate()` and post-selection `_post_selection_mace_config()` do not emit global `energy_weight`, `forces_weight`, or `stress_weight`. Pinned MACE therefore falls back to its own CLI defaults; the observed training log reported `UniversalLoss(energy_weight=1, forces_weight=100, stress_weight=1)`.

This is not the declared mdstats 1:10:1 objective.

### 2.8 Pinned MACE 0.3.16 proves that per-config property weights cannot substitute for global coefficients under `UniversalLoss`

Pinned source `mace/modules/loss.py` shows `UniversalLoss` scaling reference and prediction values by `ref.energy_weight`, `ref.forces_weight`, and `ref.stress_weight` **inside** Huber evaluation, then multiplying component losses by the global loss coefficients.

Consequences:

- a per-config property weight changes the residual magnitude and can change the Huber regime;
- it is not a linear replacement for a global 1:10:1 coefficient;
- applying the objective at both levels is not equivalent to applying it once.

Therefore the earlier tempting repair "keep 1:10:1 in every config-property weight and set global MACE coefficients to unity" is explicitly rejected by this final review.

### 2.9 Pinned `UniversalLoss` also does not consume `config_weight`

Pinned MACE 0.3.16 `UniversalLoss.forward()` consumes property weights but not `ref.weight` (`config_weight`). By contrast, the native weighted energy/force/stress helpers multiply `ref.weight` and the local property weights linearly.

This matters because mdstats `ConfigurationWeightPolicy` is scientific policy: condition/evidence weighting must not be persisted and advertised while the selected loss silently ignores it.

The implementation must therefore make the executable loss semantics agree with the declared objective/configuration/property weighting semantics. Do not preserve `UniversalLoss` merely because the old adapter hard-coded it if doing so makes configuration weighting ineffective.

---

## 3. Frozen normalization policy

### 3.1 One configurable study-wide policy

Introduce one serializable target-size optimizer-normalization policy with a stable algorithm identity, conceptually:

```text
method = inverse_updates_per_epoch.v1
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

Required defaults:

```text
N_ref    = 1024
LR_ref   = 1.0e-4
EMA_ref  = 0.99999
```

The three numerical reference values are user-configurable. The algorithm identifier is implementation/specification-owned and is not an arbitrary per-run plugin string.

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
- the reference size need not be a candidate size and need not lie inside the configured candidate ladder.

All generated/default configuration surfaces and user documentation must expose these defaults.

### 3.2 Exact normalization formula

For the current target-size architecture replay exposure is `none`, so exact candidate update geometry is:

```text
U_ref = ceil(N_ref / B)
U_N   = ceil(N / B)
s_N   = U_ref / U_N
```

where `B` is the same authenticated target-size batch size used by the candidate loader.

Derive:

```text
effective_base_learning_rate(N) = reference_learning_rate * s_N
```

and, when EMA is enabled:

```text
effective_ema_decay(N) = reference_ema_decay ** s_N
```

For a clean doubling at fixed batch geometry:

```text
LR_(2N)   = LR_N / 2
beta_(2N) = sqrt(beta_N)
```

For a size below the reference, the same formulas naturally increase LR and decrease EMA decay.

No hidden cap, floor, clipping, or candidate-specific override is permitted. If a configured tiny candidate becomes numerically unstable under the accepted reference policy, that is typed execution/scientific evidence; it is not repaired by silently violating the policy.

### 3.3 What is and is not normalized

Normalize only the two update-count clocks established by this review:

- LR amplitude;
- EMA decay.

Keep fixed across candidates:

- epoch/fidelity boundaries and number of dataset passes;
- batch size;
- LR normalized-progress shape and phase fractions;
- Adam/AMSGrad settings and moments;
- weight decay;
- gradient clipping threshold;
- precision;
- model architecture;
- acceleration policy;
- seed set;
- objective/configuration/property weighting policy.

The method is a first-order optimizer-progress normalization, not a claim of exact stochastic trajectory equivalence. Residual differences from gradient-noise statistics, Adam moment history, and finite discrete sampling of the LR schedule are documented limitations, not hidden variables to be compensated with additional machinery.

### 3.4 Scope relative to post-selection training

The normalization policy is a **target-size-screen policy**, because its purpose is to isolate unique-data sufficiency. It does not cause final production to inherit a screen checkpoint or its candidate-specific optimizer state.

Post-selection CV/final production continue to use their own fresh training plans and optimizer identities. The architecture manual must explicitly distinguish:

- the coverage-normalized target-size comparison protocol; and
- the post-selection training method validated by CV and executed fresh in production.

This amendment supersedes any parent wording that could be read as requiring identical numeric LR amplitude for all target-size candidates or requiring the screen's N-derived LR amplitude to become the fresh-production LR.

---

## 4. Policy ownership, identity, and invalidation

### 4.1 P2 remains unchanged

Do **not** put optimizer normalization into `ResolvedTargetSizePolicy` or the P2 statistical aggregate.

The normalization policy does not alter:

- P_train / M3 membership;
- `pi_train` or `pi_eval`;
- candidate qualification;
- M1/M2/M3 membership;
- hard-support obligations;
- reducer mathematics.

It belongs to P3 execution-scientific identity.

This also prevents a mere optimizer-normalization edit from forcing expensive P1/P2 reconstruction or changing the prepared statistical substrate.

### 4.2 Bind the reference policy once at the P3 execution-context boundary

The P3 execution context must bind the complete normalization-policy digest in addition to the existing schedule/template identities.

The current N-neutral optimizer template remains the study-wide template. For target-size execution its reference LR/EMA fields must be derived from the normalization policy rather than independently resolved from competing config fields.

There must be exactly one precedence rule:

- `[target_data.size_convergence.optimizer_normalization].reference_learning_rate` owns the target-size reference LR;
- `.reference_ema_decay` owns the target-size reference EMA decay;
- `[training].learning_rate` remains a post-selection/general training setting and must not silently override the screen reference;
- the target-size runtime must not carry two independently mutable values that are expected to be equal.

### 4.3 Candidate realization binds the derived values

Bump/evolve the candidate-realization schema and bind at minimum:

```text
normalization_policy_digest
reference_updates_per_epoch
optimizer_progress_scale
effective_base_learning_rate
effective_ema_decay (or explicit None when EMA is disabled)
realized_learning_rate_policy_digest
```

These values must be recomputed from the current accepted parents on restart. Extend realization-drift diagnostics so stale optimization-normalization evidence is named directly rather than reported as generic loader drift.

### 4.4 The full trajectory freezes one realized schedule

For one `(N, optimizer_seed)` trajectory:

- derive the scale once from exact candidate geometry;
- derive the full-`n3` effective LR schedule once;
- derive effective EMA decay once;
- use the same realized values through `n1 -> n2 -> n3` continuation;
- never recompute a rung-local normalization against survivors or active boundary.

`execution_epoch_limit` remains the only rung-varying schedule control.

### 4.5 Incompatible historical evidence fails closed

Existing target-size checkpoints/results produced with the old fixed-LR/fixed-EMA semantics or the wrong executable objective are not admissible ancestors of the corrected screen.

Required behavior:

- old candidate trajectories do not authenticate as new trajectories;
- old materializations/config digests do not authenticate as new materializations;
- old checkpoints are not resumed by a corrected trajectory;
- old EVAL2/reducer evidence remains historical but cannot become current corrected evidence;
- no schema default may silently reinterpret old bytes under the new scientific meaning.

Use schema/version evolution or explicit generation/context incompatibility as appropriate. Do not add migration code whose effect is to bless old scientific evidence under the new methodology.

---

## 5. Objective and weighting repair

### 5.1 Re-establish one canonical objective resolver

Create/reuse one canonical resolver from campaign config to the shared training-objective/common-training policy. Target-size common preparation and post-selection method resolution must consume the same `TrainingObjectivePolicy` semantics.

At minimum `[objective]` continues to own:

```text
energy_weight
forces_weight
stress_weight
```

with current defaults `1.0 / 10.0 / 1.0`.

Do not maintain one target-size default-only objective and a second post-selection config-aware objective.

Because target-size common preparation consumes objective/configuration/property weighting, the prepared-generation configuration identity must bind the common-training-policy/objective-policy digest. Changing `[objective]` must invalidate/rebuild the common preparation rather than reuse stale fitted weights.

This is deliberately different from optimizer normalization: changing normalization alone must not alter the P1/P2/common-preparation scientific payload.

### 5.2 Separate global objective coefficients from local weights

Restore the architectural distinction:

- `TrainingObjectivePolicy.energy_weight / forces_weight / stress_weight` are **global loss-component coefficients**;
- `ConfigurationWeightPolicy` is a per-configuration multiplier policy;
- `FrameTrainingWeight` property fields are local property modifiers/missing-label masks, not copies of the global objective ratio.

Under the current policy, absent an additional property-specific local weighting rule, the local property weight is:

```text
1.0 when that label is present
0.0 when that label is absent
```

while `configuration_weight` remains the independently fitted configuration modifier.

If `FrameTrainingWeight` serialization currently encodes a different meaning, evolve its schema or the owning prepared/common schema so historical 1:10:1-per-frame payloads cannot be silently interpreted as local masks.

### 5.3 Emit the global objective explicitly into every current MACE training config

The current target-size and post-selection MACE configs must explicitly carry the resolved global objective coefficients.

Required current surfaces:

- target-size candidate config;
- post-selection CV config;
- post-selection final-production config (through the same post-selection builder).

No current path may rely on MACE's `forces_weight=100` default.

### 5.4 Use a MACE-native loss whose executable semantics honor the declared weighting contract

Pinned MACE 0.3.16 `UniversalLoss` is incompatible with the current declared configuration-weight semantics because it does not consume `config_weight`, and it applies property weights inside the Huber residual.

The implementation must therefore stop treating `universal` as an unquestioned adapter constant.

The preferred narrow repair is to use the pinned MACE native energy+force+stress weighted loss (`loss="stress"`, which instantiates `WeightedEnergyForcesStressLoss`) because its helper reductions consume `ref.weight` and the local property weights linearly while the global E/F/S coefficients remain explicit. This is the simplest dependency-native realization of the already declared mdstats weighting model and avoids a custom MACE monkeypatch or second loss engine.

Acceptance must prove this behavior against the pinned MACE 0.3.16 implementation before the change is considered complete.

Do **not** implement a custom patched `UniversalLoss`, residual pre-scaling trick, square-root weight approximation, or duplicated sample expansion merely to preserve the old string `universal`. If a real-boundary test disproves that the native weighted energy+force+stress loss realizes the required target/replay/current method semantics, stop and reopen this design rather than inventing a wrapper-level substitute.

### 5.5 Model/execution identity must bind the corrected loss family

Where current architecture/model reconstruction hard-codes or derives `loss="universal"` (including canonical MACE candidate architecture/config reconstruction), update the owning method/protocol identity so the actual executable loss family is explicit and authenticated.

A loss-family change is a method change. Historical checkpoints generated under `UniversalLoss` must never be treated as prefixes or equivalents of the corrected weighted-loss trajectories.

---

## 6. Implementation obligations by owner

### Gate A - configuration and policy authority

Likely affected surfaces:

```text
mdstats/training_data/target_size_execution/schedule.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/_campaign_cli_core.py
campaign.toml.example
docs/guides/mlff_campaign_cli_user_guide.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
```

Required end state:

1. one versioned normalization policy type with the three configurable reference values and fixed algorithm identity;
2. one canonical config resolver with exact validation/defaults;
3. generated config and example config expose the new nested table;
4. target-size runtime constructs its reference optimizer/LR authority from this policy;
5. no hidden fallback to `[training].learning_rate` for target-size reference amplitude;
6. changing only normalization config does not change P2 statistical/prepared membership identity.

### Gate B - common objective/configuration policy authority

Likely affected surfaces:

```text
mdstats/training_data/target_size_execution/common.py
mdstats/training_data/objectives.py
mdstats/training_data/post_selection_identity.py
mdstats/training_data/campaign_target_size_runtime.py
mdstats/training_data/campaign_prepared_generation.py
```

Required end state:

1. target-size and post-selection resolve one shared objective-policy meaning from config;
2. target-size preparation no longer ignores explicit `[objective]` overrides;
3. common/prepared identity changes when the objective/common weighting policy changes;
4. frame-local property weights no longer duplicate the global E/F/S objective coefficients;
5. configuration weights remain independently represented and tested.

Prefer extracting/reusing the existing post-selection objective/configuration resolver over creating another parser.

### Gate C - candidate realization and restart identity

Likely affected surfaces:

```text
mdstats/training_data/target_size_execution/context.py
mdstats/training_data/target_size_execution/candidate.py
mdstats/training_data/target_size_execution/schedule.py
```

Required end state:

1. execution context binds normalization policy;
2. candidate realization derives exact `U_ref`, `U_N`, scale, effective LR, effective EMA, and realized schedule identity;
3. candidate validation/restart re-derives and authenticates those values;
4. drift diagnostics identify normalization changes;
5. reference size is stable even if candidates are eliminated or the configured ladder changes;
6. no survivor set or active boundary enters normalization.

### Gate D - TRAIN2/materialization realization

Likely affected surfaces:

```text
mdstats/training_data/target_size_execution/candidate.py
mdstats/training_data/target_size_execution/execution.py
mdstats/training_data/train2_policy.py
mdstats/training_data/train2_runtime.py
mdstats/training_data/campaign_target_size_runtime.py
```

Required end state:

1. generated candidate MACE config uses `effective_base_learning_rate` and `effective_ema_decay`;
2. candidate TRAIN2 runtime plan receives a learning-rate schedule with the same effective base amplitude and unchanged normalized-progress shape;
3. MACE config, TRAIN2 plan, trajectory realization, and runtime summary cannot disagree on the candidate schedule identity;
4. continuation resumes the exact same realized optimizer/EMA trajectory across boundaries;
5. no rung-local schedule is constructed.

### Gate E - current MACE objective realization

Likely affected surfaces:

```text
mdstats/training_data/target_size_execution/candidate.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/model_features.py
mdstats/training_data/mace_export.py
mdstats/training_data/target_size_execution/export.py
```

Required end state:

1. global configured E/F/S coefficients are emitted explicitly;
2. local property weights have their corrected local semantics;
3. configuration weighting is actually consumed by the selected MACE loss;
4. target-size, CV, and final production use the same objective-weight ownership model;
5. model reconstruction/EVAL2 architecture identity recognizes the corrected loss family without creating a second model-construction path.

Do not edit retired/unreachable DATA8 paths solely for cosmetic consistency. If an old helper is still reached by a current command or qualification consumer, it is affected and must satisfy the same invariant.

### Gate F - durable-state cutover

Required end state:

- current corrected policy/evidence has new identities;
- stale old screen trajectories fail authentication before execution;
- a changed normalization policy cannot resume a checkpoint produced under another reference policy;
- a changed objective/loss policy cannot reuse incompatible common preparation, materialization, checkpoint, CV, or production evidence;
- immutable old evidence remains readable as historical data where current storage policy permits it.

Prefer natural digest/schema invalidation already present in P3/P4/P5 over a new migration registry.

### Gate G - architecture/manual synchronization

Update at minimum:

```text
docs/arch_manuals/mlff_training_data/30_statistical_design.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/50_target_size_selection.md
docs/arch_manuals/mlff_training_data_architecture.md
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
campaign.toml.example
docs/guides/mlff_campaign_cli_user_guide.md
```

Documentation must state:

- the coverage-normalized screen question;
- reference-policy defaults and formulas;
- that LR/EMA variation is deterministic N-derived realization, not another independent variable;
- EMA is normalized because EVAL2 evaluates EMA when enabled;
- screen normalization is distinct from fresh post-selection training;
- global objective coefficients versus local configuration/property weighting ownership;
- the actual MACE loss family and why it is selected;
- historical evidence invalidation.

---

## 7. Required regression and integration evidence

Functional testing is mandatory between gates and again after completion. Full production/GPU qualification is explicitly out of scope for this implementation cycle.

### 7.1 Normalization-policy unit tests

Prove exactly:

1. defaults resolve to `1024 / 1e-4 / 0.99999`;
2. config overrides round-trip through serialization/digest identity;
3. invalid reference size/LR/EMA fail closed;
4. `N_ref` need not be a candidate size;
5. for `N=N_ref`, scale is exactly 1 and effective LR/EMA equal references;
6. for exact half/double update geometry, LR doubles/halves and EMA follows `beta_ref ** scale`;
7. arbitrary non-power-of-two reference/candidate values use `ceil(N/B)` rather than an assumed power-of-two ratio;
8. no cap/floor is applied.

### 7.2 Mathematical realization tests

For representative `N` and batch sizes:

```text
U_ref = ceil(N_ref/B)
U_N = ceil(N/B)
scale = U_ref/U_N
```

must equal the persisted realization exactly within normal float serialization rules.

Prove the EMA epoch-clock invariant numerically:

```text
(effective_beta_N ** U_N) ~= (reference_beta ** U_ref)
```

at tight tolerance.

For LR, prove the intended first-order budget invariant:

```text
effective_base_lr_N * U_N == reference_lr * U_ref
```

within floating tolerance, while separately proving that the normalized-progress multiplier function is unchanged. Do not claim exact equality of the discrete sum of scheduled LRs across different update grids; that finite-grid difference is an accepted approximation of this method.

### 7.3 Identity/restart tests

Prove:

- changing reference size, LR, or EMA changes execution-context/trajectory identity;
- changing only normalization leaves P2 membership/order/common statistical identities unchanged;
- a stale trajectory generated under old fixed-LR semantics is rejected;
- a changed candidate scale cannot resume an old checkpoint;
- boundary 1 -> 3 -> 10 continuation preserves exactly one realized LR/EMA trajectory;
- candidate elimination never changes the reference or surviving candidate's realization.

### 7.4 Objective/config tests

Prove:

- `[objective] = 1:10:1` reaches target-size common policy, post-selection method policy, and emitted MACE configs;
- a non-default objective override changes the same owners consistently;
- global coefficients appear exactly once as MACE global loss coefficients;
- frame-local property weights are `1/0` availability masks unless another explicit local policy applies;
- configuration weights remain independent and nontrivial when the configured strata require them;
- changing `[objective]` invalidates common preparation/prepared identity;
- changing only optimizer-normalization does not.

### 7.5 Pinned-MACE semantic integration test

This is a real dependency-boundary test, not a mocked assertion.

Against pinned MACE 0.3.16:

1. parse a generated corrected target-size config;
2. instantiate the actual loss through MACE's `get_loss_fn`;
3. prove the loss family is the accepted weighted energy+force+stress implementation;
4. prove global weights equal the configured mdstats objective;
5. construct a tiny batch with distinct `config_weight` and local property weights and prove the real loss responds linearly according to the declared weighting contract;
6. prove missing-label local zero masks the property as intended;
7. prove the old `UniversalLoss` behavior is not accidentally reached by the current corrected path.

This test is the acceptance owner for the loss-semantics claim. Config-text inspection alone is insufficient.

### 7.6 Real target-size owner-boundary integration

Using the real P3/P4 current orchestration and the accepted expensive-trainer substitution seam where necessary:

- create at least two candidate sizes on opposite sides of `N_ref`;
- materialize their real candidate configs;
- verify different derived LR/EMA values but identical epoch/pass policy;
- execute at least one real or bounded TRAIN2 continuation sequence through two boundaries;
- authenticate EVAL2 state representation;
- reconcile/adopt through the real current owner;
- verify no alternate current path bypasses normalization.

### 7.7 Affected regression surface

At minimum rerun the affected families covering:

```text
tests/test_mlff_target_size_execution_p3a.py
tests/test_mlff_target_size_execution_p3b.py
tests/test_mlff_target_size_execution_p3c.py
tests/test_mlff_target_size_execution_p3d.py
tests/test_mlff_target_size_execution_p3e.py
tests/test_mlff_target_size_execution_p3f.py
tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
tests/test_mlff_target_size_p4*.py
tests/test_mlff_target_size_p5*.py
tests/test_mlff_bounded_direct_inference*.py
tests covering campaign prepared-generation config identity
tests covering post-selection identity/execution/materialization
tests covering MACE export/realization/real-MACE contracts
tests covering TRAIN2 policy/runtime continuation
```

After the implementation stabilizes, re-derive the affected surface from changed symbols and repository search. If that re-derivation is broader than this list, run the broader regression set. Use the full relevant MLFF suite when the affected boundary cannot be bounded confidently.

---

## 8. Compatibility and schema policy

This is a scientific-method change, not a backward-compatible executable tweak.

Required compatibility posture:

- **read old evidence as historical when its old schema remains supported;**
- **never execute/resume/reduce old evidence as current corrected evidence;**
- no migration may fabricate the new normalization-policy digest or corrected objective/loss identity for old checkpoints;
- schema evolution is required wherever identical serialized field names would otherwise acquire new semantics;
- content-addressed prepared objects may be reused only when their semantic policy digest is genuinely unchanged.

A normalization-policy-only edit should reuse the unchanged prepared statistical substrate if the current generation/state machinery can do so without weakening currentness. If the existing campaign state model cannot safely replace only P3 descendants, prefer a clean new generation that reuses immutable content-addressed components over an ad hoc in-place mutation. Do not create a parallel state machine solely to optimize this transition.

---

## 9. Delegated solution space

The implementer may choose local symbol names, schema version numbers, helper placement, and small refactors provided all Frozen semantics above hold.

Preferred simplifications:

- one normalization policy type;
- one config resolver;
- one objective/common-policy resolver;
- one candidate realization formula;
- one current MACE config path per existing owner;
- existing digest/restart mechanisms rather than new registries;
- MACE-native loss realization rather than a custom patched loss.

Do not preserve obsolete behavior with aliases or wrappers merely to keep old tests green. Update tests that encode the old fixed-LR/fixed-EMA or duplicated-weight semantics.

---

## 10. Redesign/reopen triggers

Stop implementation and reopen Software Design if any of the following is proven:

1. pinned MACE 0.3.16 does not apply EMA once per optimizer update in the current TRAIN2 path, invalidating `beta_ref ** scale`;
2. the accepted target-size loader performs hidden duplication/resampling so `ceil(N/B)` is not the actual update geometry;
3. current target-size replay exposure becomes non-`none` or varies with `N`;
4. the native weighted energy+force+stress MACE loss does not actually honor `config_weight` and local property weights as shown by the real-boundary acceptance test;
5. changing the loss family changes model-construction semantics in a way that cannot be represented by the existing common architecture/method identity;
6. candidate-specific effective LR cannot be carried through one authenticated full-`n3` TRAIN2 trajectory without creating independent rung schedules;
7. the campaign state owner cannot invalidate old P3/P5 scientific descendants safely without either reinterpreting old evidence or constructing a second state authority;
8. a proposed fix requires hidden candidate-specific tuning, empirical LR caps, or another new independent variable.

A trigger is not permission to patch around the problem. It means the accepted architecture no longer suffices and must be reviewed explicitly.

---

## 11. Gated implementation order

Implement in this order, with focused tests after every gate:

1. **Policy/config gate** - normalization policy, defaults, resolver, config generation/docs.
2. **Objective-owner gate** - one config-aware common objective policy; correct global/local weight semantics and prepared identity.
3. **Candidate-identity gate** - derive/bind scale, effective LR, effective EMA, realized schedule; reject stale evidence.
4. **TRAIN2 realization gate** - same full-trajectory LR/EMA across exact continuation boundaries.
5. **MACE loss/config gate** - explicit global objective, MACE-native weighting semantics, current target-size/post-selection config parity.
6. **Current-owner integration gate** - real P3/P4/P5 orchestration, restart/reconciliation, EVAL2 EMA representation.
7. **Documentation gate** - architecture/spec/user guide synchronized to the implemented authority graph.
8. **Final affected-surface regression gate** - re-derive changed symbols/callers and run all affected regression/integration tests.

Do not proceed past a gate whose semantic acceptance test is failing.

---

## 12. Final closure review

The final Software Design review found no remaining unresolved architectural gap in the requested normalization method after the following were made explicit:

- fixed, configurable `N_ref/LR_ref/EMA_ref` policy defaults;
- exact batch-aware inverse-update scaling rather than power-of-two-only arithmetic;
- EMA normalization because EVAL2 evaluates EMA state;
- reference policy lives in P3 execution science, not P2 membership science;
- candidate realization, not generic optimizer policy, owns N-derived effective values;
- one full-trajectory realization survives exact fidelity continuation;
- no hidden LR cap or candidate tuning;
- target-size normalization is distinct from fresh post-selection optimizer state;
- target-size now consumes the explicit `[objective]` config rather than coincidental defaults;
- global objective coefficients and local property/configuration weights have separate ownership;
- pinned MACE `UniversalLoss` cannot be used as though those weight classes were linearly equivalent and cannot silently ignore `config_weight`;
- corrected executable loss semantics are bound into method/protocol identity;
- stale fixed-LR/old-loss evidence is not reusable;
- bounded real-MACE integration and full affected regression are required, while long GPU production qualification remains deferred.

**Verdict: PASS / implementation-ready.**
