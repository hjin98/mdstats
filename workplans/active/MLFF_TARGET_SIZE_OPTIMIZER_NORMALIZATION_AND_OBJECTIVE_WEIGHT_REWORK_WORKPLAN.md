---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: rework-required
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 3
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_implementation_head: 1b0ba891c0500bacbf7585a6f249c4c82c1a4510
reviewed_executable_commit: 275c3aa294497a410666795dc17b36d17f10c4f9
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
---

# MLFF target-size optimizer normalization, practical-ceiling selection, and objective-weight rework

## Status and independent review verdict

**NO-PASS / reopened for bounded implementation repair.**

Independent Software Design review of implementation commit `275c3aa294497a410666795dc17b36d17f10c4f9` and documentation-only head `1b0ba891c0500bacbf7585a6f249c4c82c1a4510` found that the principal scientific-method changes are implemented correctly, but the target-size training-policy/configuration boundary still contains competing or contradictory authorities. Those identity defects can invalidate a scientifically unchanged completed screen or persist a P3 context that describes different precision/batch/LR semantics from the executable training path. Required final functional regression/integration evidence is also not present on the reviewed remote candidate.

The high-level target-size architecture remains accepted. Do **not** redesign the P1 -> P5 authority graph, add another state machine, add a warning-specific lifecycle, add a target-size LR override wrapper, or create a second configuration digest. The repair is a Tier-2 simplification: consolidate canonical training-policy resolution and narrow P3 scientific identity to fields that actually define the target-size trajectory.

Everything explicitly listed under **Accepted implementation retained** below remains accepted and should not be rewritten merely because this plan is reopened.

---

## 1. Problem / product invariants

The governing target-size question is:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

A candidate remains exactly:

```text
T_N = pi_train[:N]
```

`N` is the sole target-data-cardinality independent variable. The configured ordered optimizer-seed set remains the stochastic replicate dimension. Ranking uses only authenticated paired-seed target-side EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

The experiment distinguishes:

- **evidence-supported truncation**: a smaller size is practically equivalent to, or better than, the larger finalist;
- **practical-ceiling selection**: `Nmax` remains materially superior, so the best permitted size is `Nmax` even though convergence was not demonstrated inside the affordable ladder.

Incomplete, malformed, foreign, or insufficient terminal evidence remains blocking. No unconfigured rescue size is invented.

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

Also Frozen for this cycle:

- exact nested `T_N = pi_train[:N]` membership;
- configured candidate/evaluation ladders and practical ceiling;
- `q -> min(q,4) -> 2 -> 1` funnel;
- paired-seed arithmetic-mean aggregation;
- target-force RMSE ranking and practical-equivalence smaller-size preference;
- one continuous candidate trajectory across `n1 -> n2 -> n3`;
- EVAL2 evaluates the authenticated configured model state, including EMA when enabled;
- P4 owns current terminal projection/currentness;
- P5 owns post-selection CV and fresh final production;
- final production never resumes a screen/CV checkpoint;
- long GPU/production qualification remains deferred to final release.

The only amended P2 terminal decision is: materially superior `Nmax` is `SELECTED` with warning metadata, not a blocking current outcome.

---

## 3. Accepted implementation retained

Independent review found these implementation surfaces substantively conformant. Preserve them while repairing the reopened blockers.

### 3.1 Practical-ceiling reducer semantics

Current P2 behavior is accepted:

- `Nmax` materially superior by more than practical-equivalence epsilon -> `SELECTED`, exact `T_selected`, warning reason `nonconverged_at_configured_ceiling`;
- `Nmax` raw-best but within epsilon of a smaller finalist -> smaller finalist selected, no warning;
- an interior/smaller finalist with the best score -> ordinary selection;
- insufficient comparable evidence -> blocking insufficient-comparison outcome;
- historical blocking-ceiling reducer state is not relabeled into a current selection.

The corrected terminal-decision policy/version participates in P2 policy/definition identity.

### 3.2 Optimizer-normalization mathematics and one-trajectory continuation

The study-wide target-size normalization policy remains:

```toml
[target_data.size_convergence.optimizer_normalization]
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

For authenticated target-size batch size `B`:

```text
U_ref = ceil(N_ref / B)
U_N   = ceil(N / B)
s_N   = U_ref / U_N

LR_N   = LR_ref * s_N
beta_N = beta_ref ** s_N
```

No hidden cap/floor, survivor-dependent rescaling, or candidate-specific tuning is allowed. The normalized-progress LR shape remains unchanged; only amplitude varies. EMA is normalized because EVAL2 uses EMA state when enabled.

Each `(N, optimizer_seed)` owns one realized full-`n3` schedule/EMA trajectory. `n1` and `n2` are pause/continuation boundaries, not new schedules.

Normalization is a target-size-screen control and does not make screen optimizer state a production parent.

### 3.3 Objective and MACE loss realization

Retain the corrected ownership:

- `TrainingObjectivePolicy` owns the global energy/forces/stress coefficients;
- `ConfigurationWeightPolicy` owns the per-configuration multiplier;
- local per-frame property weights are property-local modifiers/availability masks (`1.0` present, `0.0` absent unless another explicit local rule applies);
- current MACE configs emit global E/F/S coefficients explicitly;
- the current executable MACE loss family is the dependency-native weighted energy+force+stress loss (`loss="stress"` / `WeightedEnergyForcesStressLoss`);
- the executable loss family is bound through the canonical MACE architecture/training-method identity;
- historical `UniversalLoss` trajectories are not compatible prefixes of corrected trajectories.

Do not add a custom patched loss, residual pre-scaling, square-root weight trick, duplicated-sample approximation, or a second mdstats loss engine.

### 3.4 P4/P5 selected-at-ceiling propagation

Retain the ordinary selected path:

```text
P2 SELECTED Nmax + warning
  -> P3 terminal head
  -> P4 TERMINAL_SELECTED
  -> exact N_selected / T_selected binding
  -> P5 cross-validation
  -> fresh production if CV accepts
```

The warning remains visible diagnostic metadata and never becomes a separate lifecycle or authorization path.

---

## 4. Reopened blocker family A — one canonical target-size optimizer/training identity

### 4.1 Problem

The implemented screen correctly derives and executes candidate LR from the target-size normalization policy, but the P3 seed-neutral optimizer template is still created through the generic campaign optimizer resolver. That resolver reads `[training].learning_rate` and therefore injects a second independently mutable LR value into P3 screen scientific identity.

Consequences:

- `[target_data.size_convergence.optimizer_normalization].reference_learning_rate` controls actual target-size LR realization;
- `[training].learning_rate` can nevertheless change the reconstructed P3 context digest;
- a completed, scientifically unchanged target-size screen can fail currentness after a post-selection/general LR edit;
- the P3 authority graph carries two LR descriptions even though only one is scientifically active for screening.

This violates the accepted configuration ownership and the parent P3 requirement for one seed-neutral training-policy authority.

### 4.2 Required repair

Consolidate target-size optimizer-template construction at the existing policy-resolution boundary.

Required end state:

1. Target-size P3 has one canonical seed-neutral optimizer/training template constructor/resolver used by both:
   - live screen construction; and
   - terminal/currentness reconstruction.
2. Target-size reference LR and reference EMA values come only from the resolved target-size optimizer-normalization policy.
3. `[training].learning_rate` remains a post-selection/general training-method setting and does **not** participate in target-size P3 identity or target-size currentness.
4. Candidate-specific effective LR/EMA remain deterministic descendants of the normalization policy and authenticated update geometry.
5. Do not special-case the terminal loader, suppress a digest mismatch after the fact, or add a second target-size-LR override object. Fix the owning resolution once.

If the generic `MaceOptimizerPolicy` remains the convenient carrier, construct its target-size template from the target-size resolved scientific policy before hashing/validation. If a field exists only because the generic carrier is broader than the screen contract, prefer excluding/removing that field from the screen identity rather than synchronizing two authorities.

### 4.3 Acceptance

Prove through the real P3 context/currentness owners:

- changing only `[training].learning_rate` leaves target-size P3 context, trajectory/current terminal exposure, and selected target-size currentness unchanged;
- changing only target-size `reference_learning_rate` changes target-size P3 context/trajectory identity and rejects stale screen descendants;
- live screen construction and terminal reload produce the same target-size optimizer-template digest from the same resolved configuration;
- candidate MACE config and TRAIN2 runtime plan still use the same N-derived effective LR/EMA.

---

## 5. Reopened blocker family B — narrow seed-neutral P3 identity to scientific fields

### 5.1 Problem

The current seed-neutral optimizer digest removes seed and acceleration-realization identifiers but still hashes generic execution fields such as `num_workers`. Parent P3 explicitly classifies worker/process count as execution-only when it does not alter scientific trajectory semantics and requires such differences not to change the study-wide context.

This is an ownership defect: process scheduling/resource realization must not retire scientific target-size evidence merely because it changed how the same trajectory was executed.

### 5.2 Required repair

Perform one bounded field-classification pass over the generic optimizer payload at the target-size boundary.

For every field included in the target-size seed-neutral digest, classify it as:

- **scientific trajectory semantics** -> keep it in the P3 identity; or
- **proven execution-only realization** -> exclude it from the P3 scientific digest while allowing runtime launch to use it.

At minimum `num_workers` must not remain scientific identity if it only controls DataLoader worker processes under the accepted deterministic loader semantics.

Preserve fields that genuinely affect training science, including batch/exposure geometry, optimizer moment/regularization parameters, precision/model arithmetic, acceleration backend when scientifically material, and full-screen training-budget/schedule semantics.

Do not create a parallel "screen optimizer identity" registry or a chain of per-field compatibility exceptions. The existing seed-neutral projection is the correct owner; make that projection accurately represent the target-size contract.

If inspection proves another generic field such as validation batch geometry is execution-only for this one-head screen, remove it from scientific identity only with an owner-level test proving no governed target-size trajectory/evaluation semantic depends on it.

### 5.3 Acceptance

- changing only `num_workers` does not change target-size execution-context digest, candidate trajectory digest, or completed-screen currentness;
- the changed worker value still reaches the execution launch where appropriate;
- changing batch size, optimizer regularization, precision, or another retained scientific field changes the appropriate screen identity;
- existing seed neutrality and acceleration-realization neutrality remain intact;
- no P3 caller computes an independent competing digest.

---

## 6. Reopened blocker family C — canonical batch-size and precision resolution

### 6.1 Problem

The implementation currently resolves the same training geometry/precision through multiple defaults:

- generic executable optimizer resolution defaults batch size to `2` and obtains model dtype from the campaign binary precision contract;
- `TargetSizeCommonTrainingPolicy` defaults batch size to `4` and dtype to `float64`;
- its new campaign resolver reads configured batch size but currently retains the dataclass `float64` dtype instead of the resolved campaign model dtype;
- post-selection method resolution independently defaults batch size to `4`.

The shipped example configuration explicitly requests single/FP32 model precision. Under that normal configuration the target-size common-policy identity can therefore state `float64` while the actual executable optimizer is `float32`. When `batch_size` is omitted, common/method and executable paths can likewise disagree on `B`, which is especially material because `ceil(N/B)` defines the normalization scale.

The authority graph must not describe contradictory training science.

### 6.2 Required repair

Consolidate these values through existing canonical campaign policy owners rather than changing literals independently.

Required end state:

1. Resolve the campaign learned-model dtype once through the existing binary precision contract (or one equivalent canonical owner) and reuse that resolved value wherever target-size/P5 training policy identity needs model dtype.
2. Resolve training batch size through one canonical campaign training-policy/default path and reuse it for:
   - target-size common policy when that policy genuinely owns/needs batch geometry;
   - target-size optimizer template and candidate update geometry;
   - post-selection common/method policy;
   - executable optimizer construction.
3. If a field is not actually consumed by common preparation and exists there only as duplicated execution metadata, simplification by removing it from the common-preparation policy is preferable to maintaining synchronized copies, provided the P3 execution context still binds the scientific value exactly once.
4. Do not add downstream equality assertions as the primary repair. Fix resolution ownership so contradictory objects cannot be constructed from the same valid campaign config.

Do not infer a new user-visible default in this review. Reuse the repository's established campaign executable default/initialization contract and make every resolver agree with that one source.

### 6.3 Acceptance

- the shipped `precision_profile="single"`, model/training `float32` example produces the same FP32 model dtype in target-size common/training identity and executable optimizer path;
- `double` produces the same FP64 agreement;
- an omitted `batch_size` resolves one identical effective value everywhere that owns the same training geometry;
- an explicit non-default batch size propagates identically and changes normalization update geometry exactly once;
- incompatible dtype/profile combinations continue to fail before expensive work;
- preparation identity changes only for values common preparation genuinely owns; execution-only edits do not force unrelated P1/P2/common rebuilds.

---

## 7. Reopened documentation correction — loss-family owner

The current normative statistical-design wording says `TrainingObjectivePolicy` binds the loss family. The implementation correctly does not add such a field: global E/F/S coefficients belong to `TrainingObjectivePolicy`, while the executable loss family belongs to the canonical MACE architecture/training-method identity.

Correct the normative documentation to state that ownership accurately.

Do **not** make the implementation match the mistaken sentence by adding a redundant `loss_family` field to `TrainingObjectivePolicy`.

Regenerate tracked derived documentation only through the repository's existing source -> generated-document workflow after the authoritative Markdown is corrected.

---

## 8. Required functional closure after repair

The reviewed remote implementation commit exposes only documentation-generation check evidence; no executed functional regression/integration result is available for the required rework suite. Protocol 5.15 functional acceptance therefore remains open even if source repair is correct.

### 8.1 Focused scientific/method tests

Run and require execution (not skip) of the applicable tests covering:

```text
tests/test_mlff_target_size_optimizer_normalization.py
tests/test_mlff_target_size_terminal_decision_policy.py
tests/test_mlff_target_size_mace_objective_realization.py
tests/test_mlff_target_size_corrected_identity_cutover.py
```

The pinned-MACE semantic test must execute in an environment with the supported pinned MACE 0.3.16 dependency; a skipped import does not close the loss-semantics claim.

Add/adjust focused tests for the reopened configuration/identity blockers:

- `[training].learning_rate` independence from target-size P3 identity/currentness;
- normalization-reference LR dependence;
- `num_workers` execution-only independence;
- canonical FP32/FP64 parity across common and executable training identity;
- canonical omitted/explicit batch-size parity across screen/common/post-selection/executable owners.

### 8.2 Existing affected regression

Rerun affected families at minimum:

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
tests covering campaign prepared-generation configuration identity
tests covering campaign lifecycle/status/advance
tests covering post-selection identity/execution/materialization
tests covering MACE executable config/model reconstruction
tests covering TRAIN2 policy/runtime continuation
tests/test_mlff_doc_arch1_specification.py
```

Re-derive the final affected surface from the repaired assembled implementation. If resolution/helper consolidation changes callers beyond this map, include those callers. If the affected boundary cannot be confidently bounded, run the full relevant MLFF regression suite.

### 8.3 Real-owner integration

Using bounded expensive numerical substitution only below the accepted owners:

- build/execute/reload a real target-size current generation through P3/P4;
- prove the same canonical target-size policy resolution is used on initial execution and terminal exposure;
- prove selected-at-ceiling warning still proceeds to P5;
- prove a post-selection-only LR edit does not retire target-size selection;
- prove a target-size normalization edit does retire incompatible P3 descendants;
- prove the executable candidate config and TRAIN2 plan agree on batch, dtype, LR, and EMA realization.

Full long GPU production qualification remains deferred and is not a substitute for these tests.

---

## 9. Compatibility and invalidation policy

This remains a scientific-method change, not a migration of old evidence.

- historical fixed-LR/fixed-EMA/old-loss/blocking-ceiling evidence may remain readable under its historical schema when supported;
- it must never authenticate as corrected current evidence;
- do not repair old evidence by filling the new normalization digest, rewriting a status, or supplying new policy defaults;
- corrected objective/loss/normalization/terminal-decision changes invalidate only descendants whose scientific meaning changes;
- post-selection-only settings must not invalidate a completed target-size result;
- execution-only resource settings must not become scientific invalidation keys;
- content-addressed immutable artifacts may be reused only when their semantic parents are genuinely unchanged.

Prefer natural existing digest/schema/generation invalidation. Do not add a migration registry or compatibility wrapper for this repair.

---

## 10. Delegated solution space and anti-shortcuts

The implementer may refactor existing config/policy resolution to achieve one canonical owner. Local names and helper placement remain delegated.

Preferred repair direction:

```text
recover one canonical campaign training-policy resolution
  -> project target-size scientific subset
  -> project post-selection scientific subset
  -> keep execution-only realization outside scientific digests
```

Prefer removal/consolidation over synchronization.

Forbidden shortcuts:

- terminal-loader exceptions that ignore a context mismatch;
- hard-coding `[training].learning_rate` equal to the target-size reference LR;
- copying values between policy objects after independent resolution;
- adding another target-size optimizer-policy wrapper solely to reconcile existing objects;
- broadening prepared-generation identity to include normalization or post-selection-only fields;
- adding a new selected-with-warning reducer/lifecycle;
- adding a duplicate loss-family field solely to satisfy documentation wording;
- weakening stale-evidence checks to make old tests pass.

---

## 11. Reopen only on new design evidence

The following remain genuine bounded Design-reopen triggers after this implementation repair:

1. MACE 0.3.16 does not apply EMA once per optimizer update in the actual TRAIN2 path;
2. target-size loader exposure differs from `ceil(N/B)` because of hidden duplication/resampling;
3. target-size replay exposure becomes non-none or N-dependent;
4. one candidate-specific effective LR/EMA cannot survive the authenticated full-`n3` continuation trajectory;
5. the native weighted MACE loss fails real pinned-dependency acceptance for configuration/property/global weights;
6. corrected loss family changes model construction in a way the existing model/method identity cannot represent;
7. selected-at-ceiling warning cannot be represented by the existing selected P2/P4/P5 architecture without changing Frozen ownership;
8. correct currentness requires a competing authority rather than simplification of the existing one;
9. the method would require hidden candidate-specific tuning, empirical LR caps, an unconfigured rescue ladder, or another independent target-size variable.

The blockers in this review do **not** trigger any of these redesign conditions. They are implementation/configuration-owner nonconformance under the existing architecture.

---

## 12. Repair sequence

Perform the repair in this order, with stage-local focused/affected regression after each material executable stage:

1. **Canonical target-size optimizer-template resolution** — remove generic post-selection LR from screen scientific identity; use target-size normalization reference LR/EMA as the only screen authority.
2. **Seed-neutral identity narrowing** — classify generic optimizer fields and remove proven execution-only worker/resource fields from P3 scientific identity.
3. **Canonical dtype/batch resolution** — eliminate contradictory common/executable/post-selection defaults and projections through one existing campaign owner.
4. **Documentation ownership correction** — fix loss-family ownership wording and regenerate affected tracked derivatives.
5. **Final assembled functional closure** — execute focused tests, pinned-MACE semantic acceptance, affected regression, and real-owner integration on the repaired candidate.

Do not proceed to a closure claim while any stage still permits two authorities for the same target-size training semantic.

---

## 13. Review disposition

### Accepted and preserved

The independent review accepts the implemented:

- practical-ceiling `SELECTED + warning` reducer semantics;
- exact practical-equivalence/interior-winner behavior;
- target-size optimizer-normalization formulas and candidate realization;
- one full trajectory across fidelity boundaries;
- objective/global-vs-local weighting separation;
- dependency-native weighted MACE loss and model/method loss-family identity;
- stale scientific-evidence schema cutover;
- P4/P5 selected-at-ceiling lifecycle propagation and warning reporting.

### Blocking before closure

The workplan remains open because:

1. generic `[training].learning_rate` still contaminates target-size P3 identity despite not owning target-size LR;
2. the seed-neutral digest still includes execution-only `num_workers` and has not completed the parent-P3 field-boundary requirement;
3. target-size common policy and executable optimizer can bind contradictory dtype, and batch defaults are inconsistent across owners;
4. normative documentation misstates loss-family ownership;
5. required functional regression/integration evidence has not been established on the reviewed remote candidate.

These findings all trace to one architectural principle: **one scientific semantic must have one canonical owner**. The repair should reduce duplicate configuration interpretation and shrink identity to the actual target-size contract.

**Verdict: NO-PASS / rework required.**
