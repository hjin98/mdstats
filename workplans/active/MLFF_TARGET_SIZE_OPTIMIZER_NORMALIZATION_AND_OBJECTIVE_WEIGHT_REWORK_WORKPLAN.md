---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 4
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_source_head: 6c8b853b7d42ab6266b21bba5a8136ac24c57b7f
reviewed_executable_commit: 275c3aa294497a410666795dc17b36d17f10c4f9
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
closure_verdict: pass
---

# MLFF target-size optimizer normalization, practical-ceiling selection, objective-weight, and training-policy identity rework

## 0. Software Design closure verdict

**PASS / implementation-ready.**

Revision 4 is the final Software Design closure of the reopened workplan against the current remote source tree. The executable implementation at `275c3aa294497a410666795dc17b36d17f10c4f9` remains nonconformant until the repair obligations below are implemented and validated, but no unresolved design question remains that requires another architecture decision before implementation begins.

The closure review confirms that the principal scientific-method changes already implemented are sound:

- practical-ceiling selection is a valid `SELECTED` result with warning metadata rather than a blocking failure;
- practical equivalence still prefers the smaller finalist;
- optimizer-progress normalization uses the accepted inverse-update LR / EMA transformation;
- one `(N, optimizer-seed)` trajectory continues exactly across `n1 -> n2 -> n3`;
- global objective coefficients, per-configuration weight, and local property masks remain distinct owners;
- MACE's dependency-native weighted energy+force+stress loss is the accepted executable loss family;
- selected-at-ceiling state proceeds through ordinary P4 `TERMINAL_SELECTED` and P5 cross-validation/final-production ownership.

The reopened defects all reduce to one Tier-2 design problem:

> **The same training semantics are currently resolved by multiple partially overlapping configuration paths, while some execution-only values are hashed as scientific state.**

The final repair therefore consolidates configuration normalization and narrows identities. It does **not** add another state machine, compatibility registry, target-size wrapper, warning lifecycle, parallel optimizer authority, or migration layer.

This revision is snapshot-complete and supersedes the previous wording in this file. Implementers should not need earlier revisions or review conversation to determine the required end state.

---

## 1. Objective / problem invariants / non-goals

### 1.1 Governing scientific question

The target-size experiment answers:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

The sole target-data-cardinality independent variable is:

```text
N = number of target configurations used for gradient training
T_N = pi_train[:N]
```

The ordered optimizer-seed set remains the stochastic replicate dimension. Target-size ranking uses only authenticated paired-seed target-side EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

The experiment distinguishes:

- **evidence-supported truncation** — a smaller finalist is practically equivalent to, or better than, a larger finalist;
- **practical-ceiling selection** — configured `Nmax` remains materially superior, so the best permitted size is `Nmax`, while convergence remains unproven inside the configured ladder;
- **insufficient comparison** — malformed, foreign, missing, reordered, or numerically insufficient evidence prevents a valid comparison and remains blocking.

No unconfigured rescue size is invented.

### 1.2 Product invariants

The implementation must preserve all of the following:

- exact nested candidate membership `T_N = pi_train[:N]`;
- configured candidate and evaluation ladders;
- one `P_train / M3` split and one `pi_train / pi_eval` authority;
- paired-seed arithmetic-mean aggregation;
- target-force RMSE ranking;
- practical-equivalence preference for smaller data size;
- one continuous training trajectory per `(N, seed)` across all screening boundaries;
- exact boundary checkpoint ownership and EVAL2 authentication;
- current P4 terminal/currentness ownership;
- P5 cross-validation over exactly frozen `T_selected`;
- fresh final production over exactly frozen `T_selected`;
- no screen/CV checkpoint as final-production parent;
- historical evidence is never silently reinterpreted under corrected scientific semantics.

### 1.3 Non-goals

This repair does **not**:

- change P1/P2 statistical population, split, ordering, or candidate membership;
- redesign the `q -> min(q,4) -> 2 -> 1` funnel;
- introduce curve fitting, derivative estimation, extrapolation, or another convergence detector;
- change the post-selection CV question or final-production ownership;
- add an optimizer family beyond the currently accepted method;
- make worker count or other pure resource scheduling a scientific variable;
- add a second configuration namespace merely to resolve the current inconsistency;
- perform long GPU/full-production qualification during implementation.

---

## 2. Frozen high-level architecture and engineering envelope

The following architecture remains Frozen for this cycle:

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

Also Frozen:

- practical-ceiling selection is `SELECTED` plus warning metadata;
- insufficient comparison remains a blocking scientific terminal outcome;
- target-size reference LR/EMA normalization is screen-specific;
- final production starts from fresh optimizer/model training state;
- executable loss family is dependency-native MACE weighted energy+force+stress unless real dependency evidence fires the redesign trigger below;
- full GPU/production qualification remains deferred to final release.

The exact function/class/module placement used to realize canonical configuration normalization is **not** Frozen. Existing helpers may be moved, merged, narrowed, or deleted if the resulting ownership is simpler and the product semantics above are preserved.

---

## 3. Accepted implementation retained

### 3.1 Practical-ceiling reducer semantics

At the terminal boundary:

1. If `Nmax` is materially superior to every other successful terminal finalist by more than `practical_equivalence_mev_per_a`, emit:

```text
status = SELECTED
selected_target_size = Nmax
selected_membership_digest = candidate_digest(Nmax)
terminal_reason_codes includes "nonconverged_at_configured_ceiling"
```

2. If `Nmax` is raw-best but a smaller finalist lies inside the practical-equivalence band, select the smaller finalist without the ceiling warning.
3. If a smaller finalist has the best score, select it normally.
4. If comparison is insufficient, do not fabricate a selection.

The warning means the selection is **budget-limited rather than convergence-limited**. It must not claim asymptotic convergence. No `SELECTED_WITH_WARNING` state or new lifecycle is introduced.

The corrected terminal-decision policy/version remains part of P2 policy/definition identity so retired blocking-ceiling evidence is not relabeled under the new semantics.

### 3.2 Optimizer-progress normalization mathematics

The screen normalization policy remains:

```toml
[target_data.size_convergence.optimizer_normalization]
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

For target-size training batch size `B`:

```text
U_ref = ceil(N_ref / B)
U_N   = ceil(N / B)
s_N   = U_ref / U_N

LR_N   = LR_ref * s_N
beta_N = beta_ref ** s_N
```

There are no hidden LR caps/floors. The normalized-progress LR phase shape is unchanged; only amplitude changes. EMA is normalized because target-size EVAL2 consumes EMA state when EMA is enabled.

Epoch/fidelity counts, batch size, optimizer family, moment semantics, weight decay, clipping, precision, architecture, seed population, and objective policy are not candidate-specific tuning knobs. Each `(N, seed)` receives one realization for the full `n3` trajectory and retains it through `n1 -> n2 -> n3` continuation.

### 3.3 Objective / configuration / local-property weight ownership

Retain:

- `TrainingObjectivePolicy` as owner of global energy/force/stress coefficients;
- `ConfigurationWeightPolicy` as owner of per-configuration multiplier;
- local frame property weights as local availability/modifier weights, normally `1.0` when present and `0.0` when absent;
- explicit global coefficients in generated MACE configs;
- dependency-native `loss="stress"` / `WeightedEnergyForcesStressLoss` realization;
- loss-family identity through canonical MACE architecture/training-method identity.

Do not duplicate the global `1:10:1` ratio into local frame property weights.

### 3.4 P4/P5 selected-at-ceiling propagation

Retain the ordinary selected flow:

```text
P2 SELECTED Nmax + warning
  -> P3 terminal head
  -> P4 TERMINAL_SELECTED
  -> exact N_selected / T_selected
  -> P5 cross-validation
  -> fresh final production if CV accepts
```

The warning remains visible in CLI/status/result projections but is not an authorization branch.

---

## 4. Final closure finding: one configuration authority, role-specific projections

The closure review found three manifestations of the same underlying defect family.

### 4.1 Common-preparation policy contains fields it does not consume

`TargetSizeCommonTrainingPolicy` currently carries `batch_size` and `default_dtype`, but `build_target_size_common_preparation()` does not use either value to fit or construct any common scientific product. Common preparation consumes objective policy, configuration weighting, atomic-reference policy, harness-validation membership size, applicable foundation/reference inputs, and model-construction inputs; batch size and learned-model dtype do not affect the common fitted state.

Therefore `batch_size` and `default_dtype` are **not common-preparation authority**. Keeping them there causes unrelated batch/precision edits to invalidate prepared/common science and creates a second description of execution state.

The correct repair is removal/narrowing, not synchronization.

### 4.2 Target-size seed-neutral identity hashes irrelevant generic optimizer fields

The current seed-neutral projection removes seed and acceleration-realization identifiers but hashes most of `MaceOptimizerPolicy`, including fields that are either replaced by target-size-specific authorities or are execution-only for the screen.

In particular:

- generic `learning_rate` is not the target-size LR authority; normalized `LR_N` is;
- generic `ema_decay` is not the target-size EMA-decay authority; normalized `beta_N` is;
- `num_workers` is resource realization;
- `valid_batch_size` affects fixed non-controlling validation/harness execution, not gradient trajectory or target-size ranking authority;
- generic `eval_interval` is not emitted by the current target-size candidate MACE configuration and cannot define target-size scientific identity.

These fields must not retire an otherwise identical target-size screen.

### 4.3 P5 method identity and executable optimizer are not the same policy

`resolve_shared_optimizer_settings()` and `_optimizer_policy()` currently resolve overlapping fields independently and with different defaults. The executable resolver also fails to propagate several supported user-configurable optimizer fields into `MaceOptimizerPolicy`, so those fields can alter P5 method identity without altering actual training.

Reviewed examples include:

- method identity defaults `batch_size=4`, `valid_batch_size=4`, while executable campaign training defaults them to `2`;
- method identity defaults `ema_decay=0.99`, while executable `MaceOptimizerPolicy` uses `0.99999` when omitted;
- method identity defaults `weight_decay=5e-7`, while executable `MaceOptimizerPolicy` uses `1e-6`;
- explicit `[training].ema`, `ema_decay`, `amsgrad`, `weight_decay`, and `clip_grad` can enter P5 method identity while the current generic executable resolver ignores them.

This violates the fundamental requirement that method identity describe the method that actually executes. The final repair must close the **whole optimizer-settings family**, not patch individual fields one at a time.

---

## 5. Canonical field-ownership matrix

This matrix is the required semantic end state. Exact helper names and module placement remain delegated.

| Field / semantic | Canonical owner | Common-preparation identity | Target-size P3 scientific identity | Target-size launch/runtime | P5 method identity / execution |
|---|---|---|---|---|---|
| general `[training].learning_rate` | shared post-selection/general training policy | No | No | ignored for screen LR | Yes |
| target-size `reference_learning_rate` | optimizer-normalization policy | No | Yes, through normalization/realization | Yes | No |
| `batch_size` | canonical shared training-setting resolver | No | Yes; defines `ceil(N/B)` | Yes | Yes |
| `valid_batch_size` | canonical shared training-setting resolver | No | No | execution/materialization provenance | Yes under current P5 contract |
| `num_workers` | execution/resource policy | No | No | Yes, execution-only | execution-only; not method identity |
| `eval_interval` | role-specific training policy | No | No for current target-size screen | no new target-size scientific use | Yes under current P5 contract |
| EMA enabled/disabled | canonical shared optimizer semantics | No | Yes | Yes | Yes |
| general `[training].ema_decay` | shared post-selection/general training policy | No | No | not target-size EMA authority | Yes |
| target-size `reference_ema_decay` | optimizer-normalization policy | No | Yes, through normalization/realization | Yes when EMA enabled | No |
| `amsgrad` | canonical shared optimizer semantics | No | Yes | Yes | Yes |
| `weight_decay` | canonical shared optimizer semantics | No | Yes | Yes | Yes |
| `clip_grad` | canonical shared optimizer semantics | No | Yes | Yes | Yes |
| learned-model dtype | canonical binary precision policy | No | Yes | Yes | Yes |
| device / acceleration backend / critical precision | existing canonical backend/precision owners | No | retain current execution-scientific ownership | Yes | retain current P5 ownership |
| target-size `n3` | target-size screen schedule | No | Yes | Yes | No |
| P5 CV/final epoch budgets | P5 role-specific policies | No | No | No | role-specific P5 identity/execution |
| acceleration realization digest | execution realization/provenance | No | No in global seed-neutral identity; candidate-local historical provenance only | candidate-local | existing P5 qualification/execution ownership |

Two consequences are mandatory:

1. A field may be represented in more than one descendant digest only when every occurrence is derived from the **same canonical resolved value**. Duplicated hashing is not itself a second authority; duplicated independent resolution is.
2. A value that is execution-only for target-size may still be persisted in an immutable materialization as historical execution provenance. Persisting it does not make it current scientific identity.

---

## 6. Implementation obligations and delegated solution space

### 6.1 Consolidate canonical shared optimizer-setting resolution

**Concern.** P5 identity and executable training can describe different methods, while target-size consumes a broad generic optimizer carrier with fields it does not scientifically own.

**Required end state.** Establish one pure canonical resolution of the shared optimizer semantics actually configurable by the campaign. Every consumer that claims those semantics must derive from it.

At minimum canonically resolve and validate:

- general learning rate;
- batch size;
- validation batch size;
- EMA enable/disable;
- EMA decay;
- AMSGrad;
- weight decay;
- gradient clipping;
- evaluation interval where that role uses it;
- the existing optimizer-family restriction.

Precision and acceleration may remain under their existing dedicated owners, but downstream optimizer construction must consume those canonical resolved results instead of independently inferring incompatible defaults.

The shared resolver must **not** absorb optimizer seed, role-specific epoch budget, worker count, target-size normalization reference LR/EMA, candidate N, CV fold state, or acceleration realization digest.

**Default policy.** Do not invent new defaults. Where no durable user-facing specification overrides the behavior, preserve the current effective executable campaign behavior as product truth and make identity match it. In particular, the current executable/default campaign path establishes `batch_size=2` and `valid_batch_size=2`, while the generic `MaceOptimizerPolicy` supplies the effective EMA/regularization defaults actually executed when configuration omits those fields. Identity-only defaults that were never applied by execution are not authoritative merely because tests copied them.

Explicit supported configuration values must, after this repair, change both resolved identity and actual execution.

**Delegated realization.** A single lower-level resolver function, a narrowed existing resolver, or another minimal canonical representation is acceptable. Moving pure resolution code to break import cycles is allowed. Do not create parallel identity and execution resolvers that must be synchronized.

**Acceptance.** Use deliberately non-default distinct values and prove that canonical resolution, P5 method identity, constructed `MaceOptimizerPolicy`, generated internal MACE config, and executable MACE projection agree on every shared scientific optimizer field. Repeat with fields omitted and prove default parity.

### 6.2 Narrow common-preparation policy to quantities common preparation actually owns

**Required end state.** Remove `batch_size` and `default_dtype` from `TargetSizeCommonTrainingPolicy` scientific content, or perform an equivalent narrowing that makes common-preparation identity independent of them.

Common preparation continues to own only quantities that affect its actual fitted/common products, including as applicable objective policy, configuration-weight policy, atomic-reference policy, replay/foundation inputs genuinely used by the common fit, fixed harness membership policy, and other model-construction inputs genuinely consumed by the common product.

A batch-size or learned-model dtype edit must **not** require rebuilding P1/P2/common fitted science merely because those values were redundantly stored there. They must still invalidate the appropriate P3 execution/trajectory descendants because they change training execution semantics.

**Simplification requirement.** Do not repair this by teaching common preparation to consume batch/dtype merely to justify the existing fields. Remove the unnecessary authority instead.

**Compatibility.** Advance the serialized common-policy schema because the payload shape/meaning changes. Historical common/prepared evidence remains historical; do not fill removed fields on read and call it current. `preparation_configuration_identity()` must naturally stop treating batch/dtype as preparation-owned once the common-policy digest is narrowed.

**Acceptance.** Prove batch-only and dtype-only edits leave common-policy/common fitted identity unchanged; objective/config-weight/E0/harness changes still invalidate common preparation; P3 execution identity still changes for scientific batch/dtype changes. Revise tests that encoded the old incorrect common ownership rather than preserving them with adapters.

### 6.3 Build one target-size optimizer-template projection used by live execution and reconstruction

One canonical target-size optimizer-template projection must be used by fresh screen construction, restart authority construction, active candidate resume validation, and terminal/currentness reconstruction.

It derives from:

- canonical shared scientific optimizer settings where they genuinely apply to the screen;
- canonical binary precision/backend owners;
- target-size screen schedule;
- target-size optimizer-normalization policy.

Target-size effective LR and EMA decay come only from the normalization policy plus authenticated update geometry.

The target-size seed-neutral scientific projection must exclude at least:

- `seed`;
- acceleration realization digest / resolved realization mode;
- generic `learning_rate`;
- generic `ema_decay`;
- `num_workers`;
- `valid_batch_size`;
- `eval_interval`.

It must retain or derive the scientific fields that actually change the target-size training trajectory, including:

- `batch_size`;
- EMA enabled/disabled;
- AMSGrad;
- weight decay;
- gradient clipping;
- learned-model dtype / critical precision;
- device/backend/acceleration policy under the current scientific-backend contract;
- full-screen `n3` horizon derived from the screen schedule rather than `[training].max_num_epochs`.

Advance the implementation-owned target-size seed-neutral projection algorithm/schema token so old broad-policy evidence cannot authenticate under the corrected projection.

`TargetSizeCandidateRealization` continues to bind exact membership/count lineage, scientific training batch size, `ceil(N/B)` geometry, full-`n3` exposure, precision, seed, normalization identity/effective LR/effective EMA, and candidate-local acceleration provenance. Remove `valid_batch_size` from candidate scientific loader-geometry/currentness identity.

**Acceptance.** Through the real context/trajectory owners prove:

- general `[training].learning_rate`, general `[training].ema_decay`, `num_workers`, target-size `valid_batch_size`, and `eval_interval` do not move target-size scientific currentness;
- target-size reference LR/EMA move P3/trajectory identity;
- batch size, EMA enabled, AMSGrad, weight decay, clip gradient, dtype/backend move P3/trajectory identity;
- live and terminal/restart reconstruction produce the same canonical target-size template;
- candidate MACE config and TRAIN2 runtime use the same realized effective LR/EMA.

### 6.4 Separate target-size scientific replay validation from materialization-local execution provenance

Even after execution-only fields are removed from target-size context/trajectory identity, current `validate_target_size_materialization()` re-derives the complete immutable MACE config from the current optimizer policy. A mid-screen `num_workers` or `valid_batch_size` edit can therefore still reject a scientifically valid materialization during real resume.

**Required end state.** A previously published candidate materialization remains scientifically valid when only target-size execution-only launch settings change.

Its immutable config may retain the exact execution values used when it was created. Those values are historical execution provenance, not a requirement that the current invocation resolve the same value.

Restart validation must:

- re-derive and compare every **scientific** MACE/config field against current accepted authority;
- authenticate persisted execution-only values as valid materialization content;
- not require execution-only persisted values to equal current invocation resource settings;
- preserve exact scientific trajectory, checkpoint ancestry, and `n1 -> n2 -> n3` continuation.

For an already materialized trajectory, continuing with its persisted execution-only launch values or cleanly applying current execution-only values at launch is acceptable; prefer the simpler existing-owner realization. What is forbidden is making execution-only drift scientific invalidation or adding a registry/migration layer solely to reconcile it.

Do not weaken materialization authentication generally. Membership, common preparation, scientific optimizer fields, realized LR/EMA, architecture, objective/loss, precision, target/harness artifacts, and checkpoint lineage remain strongly authenticated.

**Real-owner acceptance.** Execute a cell through `n1` under execution settings A; change only `num_workers` and/or target-size `valid_batch_size`; reconstruct the real restart authority; resume through `resolve_target_size_candidate_for_resume()` into `n2`; prove no new scientific trajectory/common generation is created and continuation ancestry remains exact. Companion negatives must reject scientific batch/dtype/EMA-enable/AMSGrad/weight-decay/clip/reference-LR/reference-EMA drift before training.

### 6.5 Make P5 method identity and executable optimizer one method

`PostSelectionMethodIdentity` and every P5 CV/final run must consume the same canonical shared optimizer settings:

```text
configuration
  -> one canonical resolved value
      -> P5 method identity
      -> executable MaceOptimizerPolicy
      -> generated MACE config
      -> TRAIN2 runtime
```

No independently defaulted second route is permitted. Role-specific epoch budgets and optimizer seeds remain outside shared method settings exactly as today.

P5 learned-model dtype must come from the same binary precision authority as executable optimizer construction. Do not independently default P5 identity to FP64 while campaign execution resolves FP32.

If a user explicitly sets a supported shared optimizer field, it must affect both identity and execution. Verify at least learning rate, batch size, validation batch size, eval interval, EMA enabled, EMA decay, AMSGrad, weight decay, and clip gradient.

**Identity cutover.** The corrected execution semantics require an implementation-owned P5 method-recipe/optimizer-resolution identity revision. This is mandatory even when a particular old `shared_optimizer_settings_digest` happened to contain the intended value, because old P5 evidence may have executed different effective values than its identity claimed. A method-recipe version bump or equivalent canonical identity token is acceptable. Do not rewrite old CV/final evidence in place.

**Acceptance.** Prove omitted defaults resolve identically in method identity and executable optimizer; each explicit shared-field mutation changes both identity and executable config consistently; `num_workers` remains outside P5 method identity; CV/final role budgets remain independent; old method-recipe evidence cannot authorize corrected runs.

### 6.6 Preserve objective/loss repair while changing policy resolution

Canonical optimizer consolidation must not regress the accepted objective/loss repair:

- `[objective]` resolves through one shared objective resolver for screen and P5;
- global coefficients occur exactly once at the global loss layer;
- configuration weights remain independent;
- local property weights remain masks/local modifiers;
- target-size and P5 generated configs use the same accepted executable loss family;
- pinned MACE 0.3.16 real-loss acceptance must actually execute in the supported acceptance environment.

Documentation must state that `TrainingObjectivePolicy` owns global component coefficients while executable loss-family identity belongs to the canonical MACE method/architecture owner. Do not add a duplicate loss-family field to `TrainingObjectivePolicy` to preserve incorrect prose.

---

## 7. Compatibility, schemas, and invalidation

### 7.1 Target-size common-policy cutover

Advance the common-policy schema/version when removing non-consumed fields. Historical common/prepared generations remain historical. Current commands must not deserialize them, fill removed fields, and call them current.

A corrected current generation may need fresh prepared/current derived state. Reuse semantically unchanged content-addressed lower-level artifacts where existing ownership already permits it; do not add migration machinery merely to preserve a derived generation. P1/P2 statistical identities are unchanged by this repair.

### 7.2 Target-size seed-neutral policy cutover

Advance the implementation-owned target-size seed-neutral optimizer-projection algorithm/schema token. Old P3 screen evidence produced under the broad generic projection must not authenticate as corrected evidence. Do not reinterpret a historical execution-context digest by dropping fields during deserialization.

### 7.3 P5 method-recipe cutover

Advance P5 method recipe/optimizer-resolution identity so historical evidence whose identity did not match actual execution cannot authorize corrected CV/final production. No historical CV acceptance, final-production plan, or publication is rewritten.

### 7.4 Schema discipline

Version serialized schemas when the same serialized fields would otherwise acquire changed meaning. Do not bump unrelated schemas mechanically when ordinary content identity already changes safely and field meaning is unchanged.

---

## 8. Implementation authority

### Frozen

Frozen product/design authority is limited to:

- the scientific target-size question and exact `T_N` definition;
- the P1 -> P5 high-level authority graph;
- practical-ceiling terminal semantics;
- inverse-update LR/EMA normalization mathematics;
- one continuous target-size trajectory per `(N, seed)`;
- objective/configuration/local-weight separation;
- dependency-native weighted MACE loss family under current accepted dependency evidence;
- post-selection CV then fresh final production;
- field-ownership semantics in Section 5;
- historical evidence is not reinterpreted under corrected method semantics.

### Delegated

Tier-2 realization that may be simplified/replaced includes:

- exact name/module/type of the canonical shared optimizer resolver;
- whether pure precision/config helpers move to a lower-level module to avoid import cycles;
- exact target-size projection helper name;
- exact materialization-validation factoring between scientific fields and execution provenance;
- exact schema/version constant names;
- test fixture organization;
- internal caller signatures made obsolete by consolidation.

Delete or narrow existing helpers when the canonical resolver makes them redundant. Do not preserve parallel paths solely for internal-test compatibility.

### Reopen only on evidence

Reopen the affected design surface only if implementation evidence proves one of these Frozen assumptions false:

1. target-size validation batch geometry or eval interval actually mutates parameter trajectory, LR schedule, checkpoint admissibility, or ranking;
2. `num_workers` changes deterministic scientific trajectory semantics under the qualified loader and that dependence cannot be eliminated by existing deterministic execution guarantees;
3. common preparation actually consumes batch size or learned-model dtype in a mathematically necessary fitted quantity;
4. one canonical shared optimizer-semantic resolver cannot serve P3 and P5 without changing their Frozen method families rather than merely projecting role-specific fields;
5. pinned MACE 0.3.16 no longer realizes the accepted weighted loss semantics under actual generated configs;
6. corrected historical-evidence invalidation cannot be represented by existing content/method identities without a genuinely new product-level persistence contract.

A failure to fit the current helper layout is not a redesign trigger. Refactor Tier-2 layout instead.

---

## 9. Affected surface and task-specific acceptance

The final affected surface must be re-derived after implementation. At minimum inspect and test:

### 9.1 Configuration / identity owners

- `_campaign_cli_core._optimizer_policy()` and any replacement/consolidated pure resolver;
- binary model precision resolution used by optimizer and P5 method identity;
- `post_selection_identity.resolve_shared_optimizer_settings()` or its replacement;
- `resolve_post_selection_method_policies()` and `resolve_post_selection_method_identity()`;
- `TargetSizeCommonTrainingPolicy` and `resolve_target_size_common_training_policy()`;
- prepared-generation configuration identity;
- target-size optimizer-normalization resolver;
- target-size seed-neutral optimizer projection/context construction.

### 9.2 Target-size execution / restart

- candidate realization and loader-geometry identity;
- candidate MACE config generation;
- materialization validation;
- restart authority and `replay_optimizer_policy_for_trajectory()`;
- `resolve_target_size_candidate_for_resume()`;
- live screen construction;
- terminal/currentness reconstruction;
- TRAIN2 runtime-plan parity;
- P4 terminal validation/result exposure.

### 9.3 P5 execution

- P5 fitted preparation after common-policy narrowing;
- internal/executable MACE config generation;
- `_optimizer_policy_for()` or equivalent execution construction;
- CV method/currentness identity;
- final-production method/currentness identity;
- checkpoint selection/admissibility paths whose method digest changes.

### 9.4 Focused acceptance cases

**A. Canonical shared optimizer parity.** Use deliberately distinct non-default values. Through real owners assert resolved method settings, P5 method identity, `MaceOptimizerPolicy`, internal MACE config, and executable MACE projection agree for every shared field. Repeat with fields omitted and prove default parity.

**B. Common-preparation narrowing.** Prove batch/dtype changes do not alter common fitted identity, while objective/config-weight/E0/harness changes still do.

**C. Target-size role projection.** Prove general LR / general EMA decay / workers / target valid-batch / eval interval are absent from target-size scientific currentness; target-size reference LR/EMA, scientific batch, EMA enable, AMSGrad, weight decay, clip gradient, dtype/backend remain effective identity; `U_ref`, `U_N`, effective LR, effective EMA and realized schedule remain exact.

**D. Active-screen restart across execution-only drift.** Execute/replay the real `n1 -> n2` continuation owner while changing only target-size execution-only settings between invocations. The survivor must resume without new scientific identity. Negative scientific-drift cases must reject.

**E. P5 method/execution identity cutover.** Prove old method-recipe evidence cannot authorize corrected runs. New CV/final method identity and executable config must be one method.

**F. Practical-ceiling end-to-end retention.** Drive the real reducer to selected-at-ceiling with warning, adopt the real P3 terminal head, reach P4 `TERMINAL_SELECTED`, load exact selected training context, and route lifecycle to `cross-validate`.

**G. Pinned MACE semantic acceptance.** Run the real MACE 0.3.16 parser/loss test and prove weighted energy+force+stress behavior, global coefficients, configuration weights, and local masks. A skipped required MACE test is not final acceptance evidence.

### 9.5 Minimum affected regression

At minimum run/reconcile the affected versions of:

- `tests/test_mlff_target_size_statistical_authorities.py`;
- `tests/test_mlff_target_size_execution_p3a.py` through P3F and later P3 closure suites;
- target-size realized-MACE-architecture suites;
- target-size first-boundary interruption/restart suites;
- P3 head-pointer/reconciliation suites;
- `tests/test_mlff_target_size_p4*.py`;
- `tests/test_mlff_target_size_p5*.py`;
- `tests/test_mlff_mace_executable_config.py`;
- binary/critical precision suites;
- TRAIN2 policy/runtime/continuation suites;
- prepared-generation identity/currentness suites;
- campaign lifecycle/status/advance suites;
- post-selection identity/materialization/execution/CV/final-publication suites;
- objective/weight/export suites;
- `tests/test_mlff_doc_arch1_specification.py` and affected documentation integrity checks.

Then re-derive transitive affected surface from the assembled implementation and run broader MLFF regression if ownership expansion makes the boundary uncertain.

Production qualification remains **deferred**. Do not run long data-heavy GPU qualification as an implementation gate.

---

## 10. Documentation obligations

Reconcile current normative/user-facing documentation where this corrected contract changes what readers must know. At minimum cover target-size optimizer normalization, training/evaluation method identity, target-size currentness, MACE artifact/config specification, campaign CLI/config specification/example, user guide, and the architecture wording that incorrectly assigns executable loss-family ownership to `TrainingObjectivePolicy`.

Current documentation must explain:

- one canonical optimizer-setting resolution rather than independent identity/execution defaults;
- target-size LR/EMA authority is the normalization policy, not general `[training]` LR/EMA-decay;
- batch size is P3 scientific execution identity but not common-preparation identity;
- workers and target-size validation batch geometry are not target-size scientific currentness;
- P5 method identity equals actual executable optimizer semantics;
- historical evidence under the old policy-resolution semantics is not silently reused.

Do not turn architecture manuals into implementation chronology. Rewrite current-state wording coherently.

---

## 11. Implementation sequence and gates

### Gate 1 — canonical configuration semantics and common-policy reduction

- establish one shared optimizer-semantic resolver/default authority;
- route current executable optimizer construction through it;
- remove batch/dtype from common-preparation scientific policy;
- apply required common-policy schema cutover;
- add focused parity/narrowing tests.

Exit only when canonical resolution has one value per semantic field and common preparation no longer owns unused execution state.

### Gate 2 — target-size role projection and restart semantics

- build one target-size optimizer-template projection used by live/restart/terminal reconstruction;
- narrow seed-neutral target-size scientific identity;
- remove valid-batch from candidate scientific loader geometry;
- preserve effective LR/EMA realization;
- repair materialization/restart validation so execution-only drift does not become scientific invalidation;
- run real `n1 -> n2` restart tests plus scientific-drift negatives.

Exit only when a target-size screen can survive execution-only resource drift while rejecting real method drift.

### Gate 3 — P5 method/executable parity and identity cutover

- route P5 identity and actual optimizer construction through the canonical shared settings;
- route dtype through canonical binary precision authority;
- bump P5 method recipe/optimizer-resolution identity;
- prove explicit and default parity through internal and executable MACE configs;
- prove old evidence cannot authorize corrected runs.

Exit only when P5 identity is literally the method that executes.

### Gate 4 — assembled P2 -> P5 integration and documentation

- retain objective/loss semantics;
- retain practical-ceiling selected-warning flow;
- reconcile current documentation;
- run focused owner integrations and documentation checks.

### Gate 5 — final affected-surface regression

- re-derive all transitive callers/consumers changed by resolver/schema/API simplification;
- run all affected regression/integration suites;
- run real pinned-MACE semantic acceptance in the supported MACE environment;
- inspect for obsolete helper/default paths that should be removed rather than left as dormant competing authorities.

Implementation is accepted only after every material required check actually executes and passes, or a genuine environment limitation is explicitly classified and the work remains open.

---

## 12. Forbidden repair patterns

Do not close this work by:

- adding a target-size terminal-loader exception for mismatched optimizer digests;
- hard-coding equality between `[training].learning_rate` and target-size reference LR;
- copying values between independently resolved P5 identity and executable policies after the fact;
- retaining batch/dtype in common policy and forcing common preparation to "use" them artificially;
- introducing a second target-size optimizer dataclass solely to shadow the generic policy without replacing a broader authority;
- adding a materialization compatibility registry or migration table for worker/valid-batch drift;
- weakening scientific materialization authentication to ignore genuine optimizer/precision/objective changes;
- adding `SELECTED_WITH_WARNING` or another warning-specific lifecycle;
- broadening prepared-generation identity to arbitrary `[training]` configuration;
- preserving obsolete internal tests by aliases/adapters when their assertions encode incorrect ownership;
- treating skipped required MACE acceptance as a pass;
- running long production/GPU qualification in place of functional regression.

If clean implementation reveals another competing configuration owner in this same affected field family, consolidate it under this plan rather than adding a local reconciliation patch. That is affected-surface discovery, not a new product requirement.

---

## 13. Final closure statement

The reopened design is now closed for implementation.

No Frozen high-level architecture change is required. The remaining work is a bounded Tier-2 simplification and identity repair:

```text
one canonical configuration normalization
    -> common-preparation projection containing only common-fit science
    -> target-size scientific projection + execution-only launch provenance
    -> P5 method projection
    -> real executable optimizer/configs
```

The implementation should solve the configuration-authority family once, delete or narrow superseded resolution paths, and prove parity through the real target-size restart and P5 execution owners.

**Software Design verdict: PASS / implementation-ready.**
