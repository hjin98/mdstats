---
kind: implementation-workplan
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-REOPEN
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-06
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_source_commit: fa05c80090e3dfd80aeba61a55ca4d49c3f96195
architecture_change: none-scientific-semantics-realization-repair
design_handoff_verdict: pass
implementation_verdict: no-pass-until-workplan-acceptance
precedence: This workplan reopens implementation conformance after the post-closure MLFF campaign audit. It does not amend the frozen scientific method or high-level architecture. Current architecture/specifications remain product authority; this workplan governs only the transition needed to make the pinned MACE execution actually realize those contracts.
---

# MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-REOPEN — make executed MACE training equal the frozen MLFF method

**Status:** implementation-ready / implementation NO-PASS until all gates close  
**Current authority:** `docs/specs/training_data/mlff_data8_mace_artifacts_spec.md`, `docs/arch_manuals/mlff_training_data_architecture.md`, `docs/arch_manuals/mlff_training_data/`, and their current referenced specifications  
**Target branch/base:** `rework/mlff-target-size-normalization-practical-ceiling` at `fa05c80090e3dfd80aeba61a55ca4d49c3f96195`  
**Pinned dependency boundary:** `mace-torch==0.3.16`, official tag `v0.3.16`  

## 0. Purpose and reopening verdict

A post-closure product-alignment audit found that mdstats authenticates a scientifically correct MACE request but does not fully control what pinned MACE 0.3.16 does after argument parsing. The frozen documentation is substantially self-consistent; the blocking drift is at the dependency execution boundary.

Four behaviors must be closed together because they are one ownership defect: **the method identity currently stops before the dependency finishes resolving the training method**.

1. replay-enabled `multiheads_finetuning` unconditionally rewrites `args.loss` to `"universal"`, despite mdstats requiring native `loss="stress"` / `WeightedEnergyForcesStressLoss`;
2. P5's executable projection does not guarantee `real_pt_data_ratio_threshold=0.0`, permitting hidden target-data duplication under MACE's default threshold;
3. P5's executable projection does not guarantee `force_mh_ft_lr=True`, permitting MACE's multihead branch to overwrite configured LR/EMA values;
4. target-size optimizer normalization freezes `U_N=ceil(N/B)`, while ordinary MACE training loaders use `drop_last=True`; for non-divisible `N/B`, actual target exposure and optimizer-step geometry become floor-like and omit target frames.

These are genuine scientific/method realization defects. They are not permission to redesign the target-size experiment, change the objective, replace multihead replay, or weaken method identity.

**Design verdict after final challenge: PASS / implementation-ready.** The repair can be made by altering the existing MACE compatibility/projection/wrapper owners. No new loss engine, training application, replay system, or parallel method authority is justified.

## 1. Protocol binding

This workplan is bound to Software Development Protocol **5.15.0** and the current remote `software-design` role. Implementation must preserve the protocol's requirements for:

- authority-first conformance: code/tests are evidence, not product authority;
- stage-local regression after each executable gate;
- proxy-proof integration tests for dependency-facing semantic claims;
- numerical/scientific identity, sample membership, normalization, seed, checkpoint, and approximation fidelity;
- active simplicity: prefer changing/reducing existing owners over compensating layers;
- final affected-surface regression plus independent Product Alignment & Engineering Review before closure.

A protocol major-version change during implementation is a reopen condition. A compatible minor update may be adopted only after the implementer rechecks affected protocol references.

## 2. Authority and relative-plan reconciliation

### 2.1 Current product authority

The following current claims are binding:

- DATA8 fixes the first adapter to MACE 0.3.16 and `NATIVE_MACE_FIXED`.
- replay-enabled jobs use MACE multihead fine-tuning, `pt_head` first and target validation last;
- hidden replay balancing is disabled with `real_pt_data_ratio_threshold: 0.0`;
- current target-size, post-selection CV, and final-production paths use explicit global E/F/S coefficients with `loss="stress"`;
- `UniversalLoss` is forbidden because its Huber/configuration-weight semantics do not realize mdstats' declared weighting layers;
- global objective coefficients, per-configuration weights, and local property masks remain separate owners;
- target-size optimizer progress remains `U_ref=ceil(N_ref/B)`, `U_N=ceil(N/B)`, `s_N=U_ref/U_N`, `LR_N=LR_ref*s_N`, `beta_N=beta_ref**s_N`;
- exact nested `T_N`, paired seeds, exact fidelity checkpoints, target-only EVAL2 ranking, P3 restart authority, P4 adoption/currentness, selected-only CV, and fresh final production remain unchanged.

### 2.2 Relative engineering lineage

This workplan inherits, without rewriting, the non-conflicting frozen decisions and accepted repairs in:

- `workplans/archive/MLFF_TARGET_SIZE_OPTIMIZER_NORMALIZATION_AND_OBJECTIVE_WEIGHT_REWORK_WORKPLAN.md`;
- `workplans/active/MLFF_TARGET_SIZE_OPTIMIZER_NORMALIZATION_AND_OBJECTIVE_WEIGHT_REWORK_FINAL_DESIGN_CLOSURE.md`;
- `workplans/active/MLFF_TARGET_SIZE_MACE_RESTART_EPOCH_HANDOFF_BUGFIX_WORKPLAN.md`;
- the current P3/P5 packages under `workplans/active/mlff-target-size-v7-packages/`.

The previous weighted-loss acceptance requirement was directionally correct but insufficient to prove the *resolved* `mace.cli.run_train.run()` behavior. This plan closes that specific proof and realization gap.

## 3. Tier-1 invariants — must not change

1. **Native accepted loss:** corrected execution must instantiate pinned MACE's native `WeightedEnergyForcesStressLoss`; do not implement or patch a replacement loss.
2. **No UniversalLoss compatibility trick:** do not square-root weights, pre-scale residuals, duplicate samples, translate objective coefficients, or redefine method identity so `UniversalLoss` appears equivalent.
3. **Multihead replay remains the frozen method:** do not evade the defect by silently replacing the DATA8 `multiheads_finetuning` method with another head-construction mode.
4. **No implicit target duplication:** the effective target membership/count must equal mdstats' explicit exposure authority unless a future accepted design says otherwise. Current replay jobs use threshold zero.
5. **Optimizer values are method values:** LR, EMA enablement/decay, and other identity-bearing optimizer values that mdstats authenticates must be what MACE actually executes.
6. **Frozen target-size update geometry:** `ceil(N/B)` remains the screen normalization definition. Do not change it to floor, pad by duplicate target frames, or restrict the public batch-size domain merely to fit MACE's current loader default.
7. **Historical evidence is not rewritten:** checkpoints/CV/final artifacts generated under materially different realized semantics are not prefixes/equivalents of corrected trajectories.
8. **Restart/continuation remains exact:** the existing raw-MACE restart-epoch correction and P3 predecessor authentication must remain intact.
9. **P5 remains selected-only/fresh-final:** this repair cannot make a screen or CV checkpoint a final-production parent.
10. **GPU qualification remains deferred:** functional CPU/bounded dependency acceptance is required here; full production/GPU qualification remains a final-release activity.

## 4. Scope and affected owners

### In scope

Primary executable owners:

- `mdstats/training_data/post_selection_execution.py` — P5 internal method -> parser-facing MACE projection;
- the corresponding P3/target-size MACE configuration/materialization path under `mdstats/training_data/target_size_execution/` and current campaign orchestration;
- `mdstats/training_data/mace_compatibility.py` — pinned source behavior/probe/version lock;
- `mdstats/training_data/critical_precision_cli.py` — existing qualified MACE process wrapper and source-qualified patch seam;
- existing TRAIN2/runtime-plan/result/currentness owners that already carry executable realization evidence;
- DATA8/P3/P5 tests and target-size optimizer-normalization tests;
- current DATA8/architecture text only where the accepted implementation needs an explicit current-state realization statement.

### Out of scope

- changing target-size ranking, candidate ladders, practical-ceiling logic, seeds, or EVAL2;
- changing global objective coefficients or configuration-weight mathematics;
- replacing MACE 0.3.16 or vendoring/forking MACE;
- introducing a new trainer, replay engine, loss engine, compatibility registry, or method-identity hierarchy;
- production-scale/GPU qualification;
- unrelated campaign configuration cleanup.

## 5. Chosen repair architecture

The existing qualified wrapper is already the mdstats-owned seam that source-qualifies and narrowly adapts pinned MACE behavior (including the restart-epoch correction). Extend **that seam**, plus the existing configuration projections and source probe. Do not create a second wrapper.

The required dependency-facing chain becomes:

```text
frozen mdstats method/policy
  -> authenticated P3/P5 internal config
  -> exact parser-facing MACE config
       - loss = stress
       - force_mh_ft_lr = true when multihead replay is active
       - real_pt_data_ratio_threshold = 0.0 when multihead replay is active
  -> qualified mdstats MACE wrapper
       - source-qualify exact MACE 0.3.16 run_train semantics
       - prevent only the forbidden forced UniversalLoss mutation
       - enforce complete target-size batch coverage where the frozen ceil policy applies
  -> MACE's native get_loss_fn / native optimizer / native trainer
  -> resolved-runtime evidence and checkpoint
```

### 5.1 Loss repair boundary

Pinned MACE's unconditional `args.loss = "universal"` mutation is incompatible with the frozen method. The qualified wrapper may narrowly alter/guard that exact source behavior **before native `get_loss_fn()` is called**, so the dependency receives the already-authenticated `loss="stress"` value.

Constraints:

- reuse the existing source-inspection/exact-marker/fail-closed pattern in `critical_precision_cli.py`;
- qualify exact package/version/source markers before alteration;
- fail closed if the expected MACE source shape changes;
- preserve normal MACE behavior outside the dedicated mdstats qualified wrapper process;
- do not monkeypatch a new loss function or reimplement `get_loss_fn`;
- assert after MACE's mutation point that the resolved loss family is still `stress` before training begins.

### 5.2 Replay and optimizer override controls

For every replay-enabled current P3/P5 executable projection:

- explicitly emit `real_pt_data_ratio_threshold=0.0`;
- explicitly emit `force_mh_ft_lr=True`;
- include both keys in the existing parser-facing allowlist/serialization path rather than bypassing it;
- validate that parser resolution returns the exact values before launch;
- keep these values derived from the existing frozen method/policy; do not create independently configurable shadow knobs.

### 5.3 Target-size complete-batch coverage

For target-size screening executions whose scientific optimizer normalization is defined by `U_N=ceil(N/B)`, the qualified wrapper must prevent MACE's `drop_last=True` behavior from silently changing the target-head exposure/update geometry.

Required end state for a target-only candidate of size `N` and batch size `B`:

- all `N` target frame UIDs are available to the epoch's training loader;
- realized target training batches equal `ceil(N/B)`;
- the final partial batch is retained when `N % B != 0`;
- no target frame is duplicated merely to fill a batch;
- `N % B == 0` remains behaviorally unchanged.

Activation must be **derived from the existing target-size execution role/policy**, not exposed as a new scientific choice. If a process-local transport marker is necessary to reach the qualified wrapper, it is an implementation transport of an already-authenticated policy, not a new user-facing option or scientific authority.

Do not globally alter P5 loader behavior simply because it shares the wrapper. Scope the complete-batch alteration to the target-size normalized screen unless current architecture independently proves the same complete-batch requirement for P5.

If distributed training has a separate sampler-level truncation path, either preserve complete target coverage there too with the same version-qualified seam or fail closed for normalized target-size execution in that unsupported distributed mode. Do not claim `ceil` conformance while another sampler still truncates.

### 5.4 Resolved-runtime evidence

Requested YAML is not sufficient evidence. Extend the **existing** compatibility/runtime/exposure evidence owner to record or assert the minimum resolved facts needed to authenticate the executed method:

- pinned MACE compatibility/source-probe identity;
- resolved loss family / native loss class identity;
- resolved LR and EMA settings after MACE's own argument-mutation region;
- replay threshold and effective target/replay counts/duplication factor;
- target-size batch cardinality and `drop_last` realization when the normalized screen policy applies;
- the existing method/config/runtime-plan digests needed to tie the evidence to the launched job.

Prefer extending an existing `MaceSourceProbe`, loader/exposure realization, TRAIN2 result, or runtime-plan record. Do **not** introduce a parallel scientific method record solely for these fields.

## 6. Historical/currentness cutover

The current branch has artifacts whose requested method identity may say `stress` even though MACE actually trained with `UniversalLoss`. Therefore config equality alone cannot establish compatibility across the repair.

Implementation must make corrected execution distinguishable in the existing currentness/method-authorization chain. Prefer the smallest existing identity-bearing owner that already represents MACE compatibility/qualified runtime behavior.

Rules:

- replay-enabled checkpoints/CV/final evidence produced through the forced-UniversalLoss path cannot authorize corrected replay-enabled continuation/final production;
- evidence affected by target-size truncation cannot be reused when the corrected complete-batch realization changes its trajectory;
- evidence in a configuration where a discovered defect provably could not alter execution may remain compatible only if existing authenticated evidence is sufficient to prove that fact; absence of runtime evidence is not proof;
- do not rewrite old manifests/digests to make them look corrected;
- stale/incompatible current evidence must be rejected through existing P3/P5 currentness and method-digest owners before expensive execution.

## 7. Implementation gates

### G0 — Reconfirm exact dependency boundary and expand source qualification

**Goal:** make every relied-upon MACE 0.3.16 mutation/truncation behavior explicit and fail-closed before changing execution.

**Work:**

- extend the existing MACE source probe/qualified-wrapper source checks to cover:
  - forced `args.loss = "universal"` under multihead fine-tuning;
  - `force_mh_ft_lr` LR/EMA override branch;
  - `real_pt_data_ratio_threshold` target-duplication branch;
  - every active training-loader/sampler `drop_last` expression relevant to target-size execution;
- bind the exact supported version/tag/source behavior using the existing compatibility policy;
- prove no alternate mdstats trainer bypasses the qualified wrapper for P3 target-size, P5 CV, or final production.

**Acceptance:**

- known-good MACE 0.3.16 source passes the expanded probe;
- deleting/changing each required marker in a fixture causes fail-closed rejection;
- an unsupported MACE version/source shape cannot silently run;
- repository reference search shows one qualified process boundary for the affected current training paths.

### G1 — Close P3/P5 executable configuration projection

**Goal:** remove dependency defaults from the scientific method where MACE already exposes explicit controls.

**Work:**

- add/retain `force_mh_ft_lr=True` and `real_pt_data_ratio_threshold=0.0` in replay-enabled P3 and P5 parser-facing configs;
- update `post_selection_mace_run_configuration()` and its existing pass-through/serialization allowlist rather than adding another translator;
- ensure target-size/Data8 construction and post-selection construction converge on the same semantic values;
- preserve explicit non-default E/F/S objective coefficients and `loss="stress"`.

**Acceptance:**

- parser-level tests with deliberately non-default LR/EMA values prove the resolved parsed values equal mdstats policy;
- a replay fixture whose raw target/replay ratio is below `0.1` still resolves threshold `0.0` and predicts effective target count equal requested target count;
- P3 and P5 emitted configs agree on the frozen keys and do not depend on MACE defaults;
- no test passes merely because mdstats defaults happen to equal MACE's override defaults.

### G2 — Preserve the native weighted loss through real `run_train.run()`

**Goal:** ensure the real replay-enabled training path reaches MACE's native weighted E/F/S loss instead of UniversalLoss.

**Work:**

- extend the existing qualified wrapper source alteration so the exact MACE multihead forced-loss assignment cannot replace an authenticated mdstats `loss="stress"` request;
- keep native MACE `get_loss_fn()` and `WeightedEnergyForcesStressLoss` unchanged;
- add a post-mutation/pre-training assertion or equivalent resolved evidence;
- include the wrapper/compatibility revision in existing method/currentness identity so pre-repair checkpoints cannot masquerade as corrected evidence.

**Acceptance:**

- a bounded real MACE 0.3.16 replay-enabled invocation passes through `mace.cli.run_train.run()` and instantiates `WeightedEnergyForcesStressLoss`;
- the same test uses non-default, distinguishable E/F/S coefficients and a non-unit configuration weight so `UniversalLoss`, missing forwarding, or MACE defaults would produce a different result;
- actual mdstats-exported ExtXYZ metadata supplies configuration/local weights; tests do not manually overwrite those fields after export;
- dependency-computed loss agrees with an independently calculated weighted-MSE oracle;
- source drift or failed patch qualification aborts before training.

### G3 — Make target-size loader realization match `ceil(N/B)`

**Goal:** close the mismatch between frozen optimizer-progress mathematics and MACE's native `drop_last=True` train loader.

**Work:**

- through the same qualified `run_train` seam, retain the final partial target batch only for normalized target-size execution;
- cover all active per-head/combined/sampler truncation points relevant to that path;
- do not duplicate target frames to achieve divisibility;
- bind/transport activation from the existing target-size runtime role rather than user configuration;
- expose enough existing runtime/exposure evidence to verify the realized batch count and target membership.

**Acceptance:**

- deliberately non-divisible example (`N=5`, `B=2` or equivalent) realizes exactly three target batches and exposes all five target UIDs once in the epoch without padding duplicates;
- divisible control case remains unchanged;
- normalized LR/beta calculated from the frozen `ceil` geometry agrees with the realized target-size batch geometry;
- continuation from `n1` to `n2` remains the exact authenticated trajectory and restart-epoch tests remain green;
- any distributed/sampler mode that cannot satisfy the invariant fails closed rather than silently reverting to floor/truncation semantics.

### G4 — Resolve runtime evidence and currentness cutover

**Goal:** make “what MACE actually executed” part of the evidence used to admit/reject training artifacts.

**Work:**

- extend existing runtime/exposure/compatibility records with the resolved facts from Section 5.4;
- ensure the correction changes the existing method/runtime identity or authorization digest at the smallest proper owner;
- reject incompatible old replay-enabled CV/final evidence and any materially affected target-size trajectory;
- preserve historical files as history; do not migrate their scientific meaning;
- keep P3 restart identity, P4 adoption, and P5 final authorization single-owner.

**Acceptance:**

- synthetic/current fixtures show pre-repair realized-semantics evidence cannot authorize corrected continuation/final production;
- matching corrected evidence does authorize through the same existing owner;
- changing resolved loss/LR/EMA/duplication/batch semantics invalidates the appropriate method/currentness identity;
- execution-only source-probe detail that does not change semantics does not create gratuitous scientific drift unless already required by the compatibility policy.

### G5 — Affected-surface regression and end-to-end bounded integration

**Goal:** prove the repair did not break adjacent campaign behavior.

**Required focused regression includes at least:**

- `tests/test_mlff_mace_executable_config.py` and all current P3/P5 executable-serialization guards;
- `tests/test_mlff_target_size_mace_objective_realization.py` upgraded/retained as a proxy-proof exporter -> real MACE loss test;
- target-size optimizer-normalization policy/identity tests, including non-divisible `N/B`;
- target-size first-rung, partial-boundary, restart, restart-epoch handoff, and acceleration-replay tests;
- post-selection CV planning/execution/currentness/final-production authorization tests;
- MACE compatibility/source-probe tests;
- configuration/objective/configuration-weight regressions from the normalization/objective-weight rework.

**Bounded integration:**

Run one small real-MACE CPU path for each distinct semantic boundary, using tiny data and short epochs rather than production qualification:

1. target-size normalized training with non-divisible `N/B`;
2. replay-enabled training through the true multihead branch with target/replay ratio below MACE's native balancing threshold, non-default LR/EMA settings, and non-default weighted objective;
3. one post-selection CV/final authorization chain far enough to prove corrected runtime identity reaches the existing P5 owners.

The integration must execute the production orchestration/projection/wrapper owners. Replacing those owners with a fake trainer is not acceptance of the defect.

**Final regression:** after all edits, re-derive the transitive affected surface and run all tests for every modified/affected module. If that surface cannot be bounded confidently, run the broader MLFF test suite. Required tests that skip because MACE 0.3.16 is absent are **not a pass** for closure.

### G6 — Documentation/current-state reconciliation

**Goal:** ensure current documentation says exactly how the frozen method is realized after the repair without turning the workplan into product authority.

**Work:**

- update DATA8/current architecture only where needed to state the accepted qualified-runtime realization, including explicit multihead LR/replay controls and complete-batch target-size normalization behavior;
- keep method papers/reference statements scientifically unchanged unless the implementation review exposes a genuine existing contradiction;
- do not copy implementation trivia or source-patch mechanics into scientific method descriptions beyond what is required to explain the dependency boundary;
- record chronology in history/changelog as appropriate after acceptance.

**Acceptance:**

- architecture, specifications, code, tests, and pinned MACE behavior form one self-consistent chain;
- no current document claims UniversalLoss, hidden target duplication, or floor/truncated target-size update geometry is accepted;
- no historical snapshot is edited into current authority.

### G7 — Final Product Alignment & Independent Engineering Review

**Goal:** perform the requested closure review after the assembled implementation exists.

This is a genuine independent challenge, not a restatement of implementation notes.

**Product-alignment review must:**

- re-read current architecture/specification authority and the pinned MACE 0.3.16 source;
- trace each frozen scientific claim into the final production code path, not comments;
- verify the resolved runtime evidence proves actual loss, optimizer, replay exposure, and target-size loader semantics;
- re-check target-size membership/ranking/restart, P5 selected-only CV, and fresh-final invariants for collateral drift;
- search for alternate trainers/translators/config paths that bypass the repair;
- inspect historical/currentness cutover so incompatible old evidence cannot re-enter through replay/restart/publication;
- classify every observed deviation as blocking or non-blocking against Tier-1/Frozen authority.

**Independent engineering review must:**

- challenge source-patch fragility, marker qualification, error handling, failure timing, process cleanup, and future-version fail-closed behavior;
- inspect concurrency/restart interaction with the already-installed MACE restart patch;
- verify no new duplicate authority, wrapper, compatibility registry, or loss machinery was added;
- run a final active-simplicity review and remove redundant helpers/branches introduced during repair;
- verify final affected-surface regression/integration evidence was produced on the exact reviewed candidate.

**Closure verdict:**

- **PASS:** no genuine blocking scientific, architectural, numerical, runtime, or evidence issue remains. Update current docs as required, archive this workplan and retained handoff lineage, and record the accepted candidate/evidence.
- **NO-PASS:** keep/reopen this workplan with precise repair instructions tied to the blocking finding. Do not declare closure merely because tests are green.

## 8. Forbidden repair patterns

Do not:

- accept `UniversalLoss` and alter weights to imitate the frozen objective;
- add an mdstats-side replacement loss or fork MACE's loss module;
- switch off `multiheads_finetuning` solely to evade MACE's internal overrides;
- add duplicated target samples to fill final batches or to satisfy replay ratios;
- change `ceil` normalization to `floor` or restrict batch-size configuration merely to avoid the loader defect;
- introduce a second MACE wrapper when `critical_precision_cli.py` is the existing qualified seam;
- introduce a second config translator around `post_selection_mace_run_configuration()`;
- add a new compatibility database or method identity instead of extending the existing compatibility/runtime/currentness owners;
- silently bless or rewrite pre-repair checkpoints as corrected evidence;
- use parser equality, source grep, mocks, or dry-run-only evidence as proof of the real executed loss/loader semantics.

## 9. Expected implementation surface

The implementer should begin with these existing owners and reduce the surface if inspection proves a smaller complete repair:

```text
mdstats/training_data/mace_compatibility.py
mdstats/training_data/critical_precision_cli.py
mdstats/training_data/post_selection_execution.py
mdstats/training_data/target_size_execution/*
mdstats/training_data/campaign_target_size_runtime.py   (only if it is the existing activation/currentness owner)
mdstats/training_data/train2_*                          (only existing evidence/runtime owners actually affected)
tests/test_mlff_mace_executable_config.py
tests/test_mlff_target_size_mace_objective_realization.py
relevant P3/P5/target-size normalization/restart tests
docs/specs/training_data/mlff_data8_mace_artifacts_spec.md
docs/arch_manuals/mlff_training_data/*                  (only accepted current-state consequences)
```

Do not mechanically touch every listed file. Ownership tracing determines the minimal actual diff.

## 10. Final design closure review performed before handoff

The plan was challenged against the frozen architecture, current DATA8 contract, prior target-size normalization closure, actual post-selection projection, existing MACE compatibility/wrapper owners, and exact MACE 0.3.16 runtime source.

### Alternatives rejected

1. **Use generic MACE heads without `multiheads_finetuning`.** Rejected: it changes a currently frozen DATA8 execution-method contract merely to avoid a backend mutation.
2. **Adopt UniversalLoss and compensate weights.** Rejected: explicitly forbidden by DATA8 and scientifically non-equivalent.
3. **Change normalization to floor or require `N % B == 0`.** Rejected: changes the frozen scientific method / shrinks a valid configuration domain to accommodate an implementation accident.
4. **Fork/vendor MACE.** Rejected: larger maintenance surface than the existing version-qualified wrapper seam requires.
5. **Add a new trainer/wrapper around MACE.** Rejected: duplicates the already-qualified `critical_precision_cli.py` boundary and violates active-simplicity policy.

### Residual risks explicitly closed by gates

- source-patch drift -> exact 0.3.16 source probe and fail-closed G0/G2;
- hidden replay duplication -> explicit zero threshold plus real low-ratio integration G1/G5;
- default-value false confidence -> deliberately non-default LR/EMA/objective fixtures G1/G2/G5;
- non-divisible batch geometry -> real partial-batch target-size acceptance G3/G5;
- stale wrong-semantics evidence -> currentness/method cutover G4;
- collateral restart/P5 drift -> regression and independent review G5/G7;
- documentation self-confirmation -> final audit must trace claims into executable code and pinned dependency G7.

**Final Software Design verdict: PASS / implementation-ready.** No frozen scientific or high-level architectural decision needs revision. Implementation remains **NO-PASS** until G0-G7 are satisfied on one assembled candidate.