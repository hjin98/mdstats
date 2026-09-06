---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: rework-required
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 5
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_source_head: cadf23c488ae61831d7dee8fccdc4eed98aaf8f4
reviewed_implementation_commit: 022206646c518582889661c3b38c464b6a7760a7
reviewed_documentation_commit: cadf23c488ae61831d7dee8fccdc4eed98aaf8f4
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
closure_verdict: no-pass
---

# MLFF target-size optimizer normalization, practical-ceiling selection, objective-weight, and training-policy identity rework

## 0. Independent implementation-review verdict

**NO-PASS / reopened for bounded repair and acceptance closure.**

Software Design reviewed implementation commit `022206646c518582889661c3b38c464b6a7760a7` and assembled branch head `cadf23c488ae61831d7dee8fccdc4eed98aaf8f4` against this workplan, Protocol 5.15.0, and the directly related target-size restart/partial-boundary contracts.

The implementation closes the major revision-4 configuration-authority defects correctly:

- one canonical shared optimizer-setting resolver now feeds P5 identity and executable `MaceOptimizerPolicy`;
- executable/default parity is corrected for LR, batch sizes, EMA, EMA decay, AMSGrad, weight decay, clipping, and evaluation interval;
- learned-model dtype is resolved through one binary precision authority;
- target-size common preparation no longer owns batch size or learned-model dtype that it does not consume;
- target-size seed-neutral scientific identity excludes general LR/EMA decay, workers, validation batch size, and evaluation interval while retaining trajectory-changing optimizer/precision/backend state;
- target-size candidate loader geometry no longer treats `valid_batch_size` as science;
- already-published candidate materializations can be replayed across execution-only worker/validation-batch drift without retiring the scientific trajectory;
- P5 carries a corrected method-recipe identity cutover;
- the previously accepted practical-ceiling, objective/weight, native MACE-loss, P4 selected-flow, and fresh-production semantics were not displaced.

Two implementation blockers and one acceptance blocker remain:

1. **Uncommitted first-rung materialization still becomes an execution-only identity collision.** A first-boundary attempt can publish immutable materialization/config bytes before any accepted cell completion exists. The materialization path is keyed by the scientific trajectory digest, which intentionally excludes `num_workers` and `valid_batch_size`, while the immutable MACE config still records those fields as execution provenance. If the process dies after materialization but before accepted progress and the operator changes either execution-only setting, the next scientifically identical fresh first-rung attempt addresses the same path with different config bytes and the immutable create-or-verify owner rejects the attempt. This contradicts the accepted distinction `no accepted boundary yet -> retry first rung fresh` and the revision-4 rule that execution-only drift must not invalidate target-size science.
2. **The new canonical optimizer resolver is not yet a complete validation authority.** It converts numeric values before exact type/domain validation and does not reject non-finite LR/weight-decay/clip values. TOML values such as `nan`, `inf`, a fractional batch size, or a boolean in an integer field can therefore be silently accepted/reinterpreted and enter method identity/execution. Centralizing configuration is only correct if the canonical owner validates exactly what it canonicalizes.
3. **Required assembled functional acceptance is not established on the reviewed candidate.** The accessible GitHub evidence for the implementation commit contains only the documentation-PDF workflow; no focused/affected regression, assembled P2->P5 integration, or required real pinned-MACE semantic acceptance is recorded. Under Protocol 5.15.0 an unexecuted required check is not a pass. In addition, the new old-method P5 cutover test only proves two digests differ; final closure must prove the real final-production authorization owner rejects historical-method CV acceptance before training.

No Frozen high-level architecture change is required. The correct repair is to **reduce the remaining ambiguity at existing owners**: treat unaccepted first-rung materialization as attempt-local scratch just as unaccepted first-rung checkpoint state already is; make the existing canonical resolver strict; then execute the required real-owner regression/integration matrix. Do not add a compatibility registry, alternate materialization identity, migration layer, warning lifecycle, restart database, or second configuration resolver.

This revision is snapshot-complete for the remaining work. Earlier accepted scientific-method sections are restated below so an implementer does not need review conversation to determine what must remain unchanged.

---

## 1. Tier-1 problem and scientific invariants

The target-size experiment answers:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

The sole target-data-cardinality independent variable is:

```text
N = number of target configurations used for gradient training
T_N = pi_train[:N]
```

The ordered optimizer-seed set is the stochastic replicate dimension. Ranking uses authenticated paired-seed target-side EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

The experiment distinguishes:

- **evidence-supported truncation**: a smaller finalist is practically equivalent to, or better than, a larger finalist;
- **practical-ceiling selection**: configured `Nmax` remains materially superior, so `Nmax` is the best permitted size while convergence remains unproven inside the configured ladder;
- **insufficient comparison**: malformed, foreign, missing, reordered, or numerically insufficient evidence prevents a valid comparison and remains blocking.

No unconfigured rescue size is invented.

Product invariants that remain binding:

- exact nested `T_N = pi_train[:N]` membership;
- one P1 canonical frame authority and one neutral statistical substrate;
- one `P_train / M3` split and one `pi_train / pi_eval` authority;
- configured candidate/evaluation ladders;
- `q -> min(q,4) -> 2 -> 1` successive-halving topology;
- paired-seed arithmetic-mean aggregation;
- target-force RMSE ranking;
- practical-equivalence preference for smaller data size;
- one continuous scientific trajectory per `(N, optimizer_seed)` across `n1 -> n2 -> n3`;
- exact authenticated boundary checkpoint/EVAL2 evidence;
- current P4 terminal/currentness ownership;
- P5 cross-validation on exactly frozen `T_selected`;
- fresh final production on exactly frozen `T_selected`;
- no screen or CV checkpoint as final-production parent;
- historical evidence is never silently reinterpreted under corrected scientific semantics.

---

## 2. Frozen high-level architecture

The high-level authority graph remains Frozen:

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

- materially superior configured ceiling is `SELECTED` with warning metadata, not a blocking failure;
- insufficient comparison remains blocking;
- target-size optimizer-progress normalization is screen-specific;
- target-size EVAL2 consumes the authenticated configured model state, EMA when enabled;
- objective/global component coefficients, configuration weights, and local property masks remain separate owners;
- executable target-size/P5 loss family remains dependency-native MACE weighted energy+force+stress under the accepted pinned dependency evidence;
- P3 remains target-size execution/restart evidence owner;
- P4 remains campaign terminal/currentness/adoption owner;
- P5 remains cross-validation/fresh-production owner;
- final production starts fresh;
- long GPU/full-production qualification remains deferred to final release.

The exact helper/function/module structure used to implement the remaining repair is Tier 2 and may be simplified. A local API inconvenience is not a redesign trigger.

---

## 3. Accepted implementation that must be retained

### 3.1 Practical-ceiling reducer

At the terminal comparison:

```text
Nmax materially superior by > practical-equivalence epsilon
    -> status = SELECTED
    -> selected_target_size = Nmax
    -> exact membership digest
    -> terminal_reason_codes includes "nonconverged_at_configured_ceiling"
```

If a smaller finalist is within practical equivalence of a raw-best larger finalist, prefer the smaller finalist. If a smaller finalist is strictly best, select it normally. If comparison is insufficient, do not fabricate selection.

The ceiling warning means **budget-limited rather than convergence-limited**. It does not claim asymptotic convergence. No `SELECTED_WITH_WARNING` lifecycle exists.

### 3.2 Target-size optimizer normalization

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

No hidden cap/floor or survivor-dependent recomputation is allowed. One `(N, seed)` realization is derived from the full `n3` geometry and remains unchanged through all rungs. General `[training].learning_rate` and `[training].ema_decay` are P5/general-training settings and are not target-size LR/EMA-decay authority.

### 3.3 Weight/loss ownership

Retain:

- `TrainingObjectivePolicy` as owner of global energy/force/stress coefficients;
- `ConfigurationWeightPolicy` as owner of per-configuration multiplier;
- local property weights as availability/local modifiers, normally `1.0` present and `0.0` absent;
- explicit global coefficients in generated MACE configs;
- dependency-native `loss="stress"` / `WeightedEnergyForcesStressLoss` realization;
- loss-family identity through canonical MACE method/architecture ownership.

Do not duplicate the global `1:10:1` ratio into local per-frame property weights.

### 3.4 One canonical shared optimizer-setting resolution

The implemented canonical owner is accepted in principle. One resolved value must feed P5 method identity and real execution for:

- general learning rate;
- training batch size;
- validation batch size;
- evaluation interval;
- EMA enable/disable;
- EMA decay;
- AMSGrad;
- weight decay;
- gradient clipping;
- supported optimizer family.

Effective omitted defaults remain the executable campaign defaults:

```text
learning_rate    = 1.0e-4
batch_size       = 2
valid_batch_size = 2
eval_interval    = 1
ema              = true
ema_decay        = 0.99999
amsgrad          = true
weight_decay     = 1.0e-6
clip_grad        = 10.0
```

Optimizer seed, role-specific epoch budgets, worker count, target-size normalization references, candidate N, CV fold state, and acceleration realization remain outside this shared resolution.

Learned-model dtype remains owned by the canonical binary precision authority.

### 3.5 Common-preparation narrowing

`batch_size` and learned-model dtype are **not** common-preparation scientific identity because common fitting consumes neither. They remain P3 execution-scientific state where they change training. Objective/configuration-weight/E0/harness inputs remain common-preparation identity.

### 3.6 Target-size role projection

Target-size seed-neutral scientific identity excludes:

- optimizer seed;
- candidate-local acceleration realization/mode;
- general learning rate;
- general EMA decay;
- worker count;
- validation batch size;
- evaluation interval.

It retains fields that change the target-size scientific trajectory, including:

- training batch size;
- EMA enabled/disabled;
- AMSGrad;
- weight decay;
- gradient clipping;
- learned-model dtype / critical precision;
- accepted device/backend/acceleration policy;
- full-screen `n3` horizon.

Candidate realization retains exact target membership/count, `ceil(N/B)` update geometry, full-n3 exposure, precision, seed, normalization identity, effective LR/EMA, realized LR schedule, and candidate-local acceleration provenance. `valid_batch_size` remains absent from candidate scientific loader geometry.

### 3.7 P5 method cutover

P5 corrected method identity remains `mdstats.post-selection-method.2026-09.v2` or an equivalent newer identity if implementation legitimately advances it. Historical pre-cutover CV/final evidence must not authorize a corrected method. P5 final production must require CV acceptance whose exact method digest equals the method it is about to execute.

---

## 4. Relationship to existing restart/partial-boundary contracts

These existing contracts remain authoritative and constrain the repair.

### 4.1 Partial-boundary progress

Already **accepted** immutable progress for a logical `(screen, boundary, N, seed)` cell is scientific evidence. It must be deeply authenticated and reused. The scheduler executes only missing active cells. Genuine conflicting accepted evidence remains a hard error.

Do not delete or overwrite accepted progress to make restart easier.

### 4.2 First-boundary absence

Before any boundary completion for a cell is accepted, there is no continuation authority. An interrupted first-rung attempt is attempt-local scratch and must be retried fresh. Existing first-boundary checkpoint handling already follows this model by removing stale uncommitted checkpoint workspace before the retry.

The remaining materialization repair must follow the same authority distinction rather than create a new one.

### 4.3 Later-rung continuation

For `n2`/`n3`, existing authenticated predecessor snapshot/continuation ownership remains unchanged. A missing current-boundary survivor continues from its exact accepted previous boundary. An already completed current-boundary cell does not run again.

### 4.4 Candidate-local acceleration provenance

A published trajectory may retain the acceleration realization that actually executed it without making a later compatible realization change global screen identity. The new materialization repair must not regress that accepted replay behavior.

---

## 5. Blocking repair A — remove uncommitted first-rung materialization collision

### 5.1 Diagnosis

Current first-rung execution performs, in order:

```text
build scientific trajectory
 -> materialization_directory = materialization_root / trajectory_digest
 -> materialize_target_size_candidate(...)
 -> create/reset uncommitted TRAIN2 checkpoint workspace
 -> train/evaluate
 -> publish accepted cell completion/progress
```

The scientific trajectory digest intentionally excludes `num_workers` and `valid_batch_size`. The immutable candidate MACE config intentionally persists those values as historical execution provenance. The config is published with create-or-verify semantics at a deterministic path inside the trajectory materialization directory.

Therefore this interrupted state is possible:

```text
scientific trajectory S
execution settings A
 -> materialization/config A published under path keyed by S
 -> process dies before any accepted completion/progress for the cell

operator changes only num_workers and/or valid_batch_size to B
 -> scientific trajectory is still S
 -> first rung correctly has no predecessor and should retry fresh
 -> materializer addresses the same S directory
 -> config B differs only in execution provenance
 -> immutable create-or-verify rejects config B
```

The immutable publisher is behaving correctly. The error is the ownership of **unaccepted attempt-local materialization**: the runtime currently leaves it in a location where a future fresh attempt treats it like reusable durable content even though no accepted cell evidence references it.

### 5.2 Required end state

For a first-boundary cell with **no authenticated accepted completion/progress**, all attempt-local artifacts whose only purpose is to launch that unaccepted first-rung attempt must be retryable under current execution-only settings without changing scientific generation/context/trajectory identity.

The simplest accepted repair is:

- use the existing P3 progress/completion authority to determine whether this logical first-boundary cell has accepted evidence;
- if it has accepted evidence, ordinary partial-boundary recovery owns it and the runtime must not execute/rematerialize the cell;
- if it has no accepted evidence and the runtime is about to execute the cell fresh, treat any pre-existing first-attempt materialization workspace at that scientific trajectory location as **uncommitted attempt scratch**, just as the first-rung checkpoint workspace already is;
- remove/recreate that unaccepted attempt-local materialization before rematerialization, or implement an equivalently simple replacement that proves the same ownership distinction without adding persistent state;
- never delete/rewrite a materialization referenced by an authenticated accepted completion;
- preserve immutable create-or-verify semantics for accepted/canonical artifacts.

### 5.3 Preferred simplification

Prefer extending the existing first-rung fresh-attempt cleanup boundary so materialization and TRAIN2 attempt scratch obey one rule:

```text
no accepted logical-cell evidence
    -> no durable first-rung attempt authority
    -> stale attempt-local materialization/checkpoint workspace may be discarded
    -> retry fresh under current execution-only settings

accepted logical-cell evidence exists
    -> recover/authenticate/reuse through existing P3 owners
    -> do not execute or clean its durable parent graph
```

Do **not** add:

- a second materialization identity containing worker/validation-batch settings;
- an execution-only compatibility registry;
- a mutable latest-materialization pointer;
- an orphan migration table;
- an alternate first-rung resume state machine;
- a permissive overwrite mode in the immutable publisher.

The problem is solved by correctly classifying unaccepted attempt scratch, not by weakening immutable evidence.

### 5.4 Required focused acceptance

Add a real-owner test at the production `select-target-size` boundary:

1. prepare a real bounded campaign;
2. enter the first active cell;
3. allow real candidate materialization to publish;
4. interrupt **after materialization exists but before the trainer produces an accepted boundary/completion/progress**;
5. verify no cell progress/completion/head was accepted for that cell;
6. change only `num_workers` and/or `valid_batch_size`;
7. invoke `select-target-size` again;
8. prove the first rung starts fresh (`start_epoch=0`), stale attempt-local materialization does not block the retry, and no new scientific generation/execution-context/trajectory identity is created;
9. let the screen continue successfully through the ordinary owners.

Companion negatives:

- if accepted progress exists, retry must recover/reuse it and must not delete its materialization;
- scientific drift (batch size, dtype, EMA enabled, AMSGrad, weight decay, clip gradient, normalization reference LR/EMA, accepted backend policy) must still invalidate/reject stale science through existing owners;
- a genuine conflicting immutable accepted cell remains a hard error.

This test must not fake materialization or directly seed post-decision state. Only MACE numerical work may be substituted below the real orchestration/identity/persistence owners.

---

## 6. Blocking repair B — make canonical optimizer normalization a strict validation authority

### 6.1 Diagnosis

`resolve_shared_optimizer_settings()` now correctly centralizes shared optimizer configuration, but several fields are converted before exact validation:

- floats are accepted when merely not `<= 0` or `< 0`;
- `nan` and positive `inf` therefore pass some LR/regularization checks;
- integer fields are converted through `int(...)`, so fractional numeric values or booleans can be silently reinterpreted;
- boolean fields are normalized through truthiness rather than requiring an actual boolean value.

The generic `MaceOptimizerPolicy` constructor has similarly permissive finite-domain checks, so downstream construction does not reliably catch the bad canonical value.

This is not a request for a second validator. It is a defect in the new **single canonical validator**.

### 6.2 Required end state

The canonical shared optimizer resolver must reject malformed or non-finite scientific optimizer configuration before identity construction or launch.

Required validation semantics:

- `learning_rate`: real finite number, strictly `> 0`;
- `batch_size`: positive integer, not boolean, no truncation from fractional float;
- `valid_batch_size`: positive integer, not boolean, no truncation;
- `eval_interval`: positive integer, not boolean, no truncation;
- `ema`: actual boolean;
- `ema_decay`: real finite number with `0 < value < 1`;
- `amsgrad`: actual boolean;
- `weight_decay`: real finite number with `value >= 0`;
- `clip_grad`: real finite number, strictly `> 0`;
- optimizer family: existing accepted-family validation remains fail-closed.

If repository-wide `MaceOptimizerPolicy` construction remains a public/serialized owner that can independently admit non-finite values, strengthen that existing constructor consistently rather than leaving two incompatible domains. This is alteration of the existing owner, not new machinery.

### 6.3 Required focused acceptance

Add canonical-owner negatives for at least:

- `nan`, `inf`, `-inf` where representable for LR/EMA decay/weight decay/clip gradient;
- fractional batch/validation-batch/eval-interval values;
- boolean values supplied to integer fields;
- non-boolean values supplied to `ema`/`amsgrad`.

Prove failure occurs before method identity, candidate trajectory, materialization, or trainer launch.

Retain positive tests for explicit non-default settings and omitted-default parity across:

```text
config
 -> canonical resolver
 -> P5 method identity
 -> MaceOptimizerPolicy
 -> internal MACE config
 -> executable MACE projection
```

---

## 7. Acceptance blocker C — execute the required assembled evidence

### 7.1 Current evidence status

The reviewed GitHub candidate records a successful documentation-PDF workflow for implementation commit `022206646c518582889661c3b38c464b6a7760a7`, but no test/status evidence for the required implementation regression/integration matrix. Source inspection cannot substitute for execution.

The workplan remains open until the required checks actually run and pass on the assembled repaired candidate.

### 7.2 Required real-owner P5 historical-cutover acceptance

The current source correctly compares `CvCampaignAcceptance.method_identity_digest` to the method final production would execute. Final acceptance must exercise that owner rather than merely assert that two method digests differ.

Required test:

1. construct/publish a bounded valid CV plan/acceptance under the historical pre-cutover method identity or an otherwise authenticated historical-method fixture;
2. resolve the current corrected P5 method;
3. enter the real final-production authorization path (or its exact authorization owner used by that path);
4. prove the historical acceptance is rejected on method mismatch **before trainer launch/materialization of final production**;
5. prove a matching corrected-method acceptance is admitted through the same owner.

Do not add another cutover table or compatibility layer; the existing exact method-digest authorization is the correct mechanism.

### 7.3 Required practical-ceiling retention

Retain one real-owner bounded integration that drives:

```text
terminal paired-seed reducer evidence
 -> SELECTED Nmax + nonconverged_at_configured_ceiling warning
 -> real P3 terminal head
 -> P4 TERMINAL_SELECTED adoption/currentness
 -> exact N_selected / T_selected loading
 -> next lifecycle command = cross-validate
```

The configuration/restart repair must not regress this accepted flow.

### 7.4 Required pinned-MACE semantic acceptance

Run the real pinned MACE 0.3.16 parser/loss integration in an environment where the pinned dependency is available. It must actually execute, not skip, and prove:

- generated target-size and P5 configs select the accepted weighted energy+force+stress loss family;
- global E/F/S coefficients equal mdstats objective settings;
- configuration weights and local property masks are consumed according to the accepted dependency semantics;
- missing-label zero masks behave correctly;
- corrected paths do not silently fall back to `UniversalLoss`.

### 7.5 Final affected-surface regression

At minimum execute the final affected versions of:

- `tests/test_mlff_target_size_statistical_authorities.py`;
- target-size P3A through P3F and later P3 closure/replay suites;
- `tests/test_mlff_target_size_canonical_optimizer_settings.py`;
- `tests/test_mlff_target_size_execution_only_drift_restart.py`;
- first-boundary interruption/retry tests;
- partial-boundary resume/recovery tests;
- target-size acceleration-realization replay tests;
- target-size realized-MACE-architecture tests;
- P3 head-pointer/reconciliation tests;
- all affected `tests/test_mlff_target_size_p4*.py`;
- all affected `tests/test_mlff_target_size_p5*.py`;
- `tests/test_mlff_mace_executable_config.py`;
- binary/critical precision tests;
- TRAIN2 policy/runtime/restart/continuation tests;
- prepared-generation identity/currentness tests;
- campaign lifecycle/status/advance tests;
- post-selection identity/CV/final-production authorization/materialization/execution/publication tests;
- objective/weight/export tests;
- affected documentation integrity/specification tests.

After the repairs are assembled, re-derive the transitive affected surface from the final diff. If the boundary remains uncertain, run the broader MLFF regression suite. Stage-local focused checks are not a replacement for this final affected regression.

Production-scale GPU qualification remains **deferred**. Functional real-MACE acceptance is required; long data-heavy GPU qualification is not.

---

## 8. Implementation authority

### 8.1 Frozen

Frozen authority is limited to:

- the scientific target-size question and exact `T_N` membership;
- the P1->P5 authority graph in Section 2;
- practical-ceiling selected-warning semantics;
- inverse-update LR/EMA normalization mathematics;
- one continuous target-size scientific trajectory per `(N, seed)`;
- P3 immutable accepted evidence/restart ownership;
- distinction between accepted partial progress and unaccepted attempt scratch;
- objective/configuration/local-weight separation and accepted MACE loss family;
- one canonical shared optimizer-setting resolution;
- field-ownership classification in Sections 3.4-3.6;
- P5 exact method-digest CV authorization;
- fresh final production;
- no silent reinterpretation of historical evidence.

### 8.2 Delegated

Implementation may simplify or replace Tier-2 details including:

- exact helper name/location for strict shared-setting validation;
- exact factoring of the first-rung fresh-attempt cleanup;
- whether uncommitted first-rung materialization cleanup is colocated with existing checkpoint cleanup or factored into one small existing-owner helper;
- internal fixture organization;
- redundant old helpers made obsolete by canonical resolution;
- exact diagnostics.

Prefer deletion/narrowing/consolidation over aliases or adapters.

### 8.3 Reopen Design only on evidence

Reopen only the affected surface if implementation proves one of these Frozen assumptions false:

1. A first-rung materialization with no accepted logical-cell completion must survive as durable authority for a scientific reason not represented by current accepted progress/completion lineage.
2. Deleting/rebuilding unaccepted first-rung materialization cannot be made safe because an independent accepted object can reference it before cell acceptance.
3. `num_workers` or target-size validation batch size actually changes deterministic scientific trajectory/ranking semantics under the qualified runtime.
4. Common preparation mathematically consumes batch size or learned-model dtype after all.
5. One canonical shared optimizer-semantic resolver cannot serve P3/P5 through role-specific projection without changing their Frozen method families.
6. Pinned MACE 0.3.16 does not realize the accepted weighted loss semantics under the actual generated configs.
7. Existing exact method-digest authorization cannot prevent historical P5 evidence from authorizing corrected final production.

Do not reopen because a current helper API is inconvenient.

---

## 9. Forbidden repair patterns

Do not close this review by:

- weakening immutable create-or-verify semantics;
- overwriting or deleting **accepted** partial-boundary progress/materialization;
- adding worker/validation-batch fields back into scientific trajectory identity merely to avoid the orphan collision;
- adding an execution-only compatibility registry, migration table, alternate materialization generation, or second restart database;
- teaching common preparation to consume batch/dtype artificially;
- restoring independent P5 identity/execution defaults;
- adding a second optimizer validator instead of fixing the canonical one;
- allowing non-finite optimizer parameters because a downstream library may eventually fail;
- treating a digest-inequality unit assertion as proof of real final-production historical-evidence rejection;
- treating skipped required pinned-MACE acceptance as pass;
- substituting long GPU qualification for functional regression;
- adding another target-size terminal/warning lifecycle.

If another sibling is found in the same canonical-config or first-rung scratch/accepted-authority family, fix it at that shared owner under this workplan rather than layering another local patch.

---

## 10. Repair sequence and gates

### Gate R5-A — strict canonical configuration validation

- strengthen the existing canonical shared optimizer resolver;
- strengthen the generic optimizer policy constructor too if it independently admits values outside the canonical domain;
- add exact-type/non-finite negatives;
- rerun canonical parity tests.

Exit only when malformed configuration cannot enter identity or execution.

### Gate R5-B — first-rung unaccepted-materialization restart closure

- establish the accepted-progress/no-progress distinction before first-rung materialization reuse;
- make unaccepted first-attempt materialization retryable scratch under execution-only drift;
- preserve accepted progress/materialization immutability;
- add the post-materialization/pre-completion interruption test and scientific-drift negatives;
- rerun first-boundary, partial-boundary, continuation, acceleration-replay, and target-size P3/P4 regression.

Exit only when execution-only drift is non-scientific across **both** accepted replay and unaccepted first-rung retry states.

### Gate R5-C — P5 real authorization closure

- retain canonical shared settings and method recipe cutover;
- add real final-production authorization rejection of historical-method CV acceptance;
- prove matching corrected acceptance succeeds;
- rerun P5 CV/final currentness/execution/publication regression.

### Gate R5-D — assembled acceptance

- run practical-ceiling P2->P5 integration;
- run real pinned-MACE 0.3.16 parser/loss semantic acceptance;
- run the final re-derived affected regression matrix;
- update documentation only if the repair changes current-state wording;
- regenerate affected PDFs only after normative Markdown is final.

No long GPU/full-production qualification is required at this gate.

---

## 11. Final review status

The architecture and scientific method remain accepted. The implementation is close, but it is **not yet closable** because execution-only drift still blocks one legitimate first-rung crash/retry state, the new canonical resolver still admits malformed/non-finite configuration, and required assembled executable evidence is absent on the reviewed candidate.

The remaining repair is deliberately reductive:

```text
existing canonical configuration owner
    -> validate exactly

existing first-rung no-authority distinction
    -> include unaccepted materialization scratch

existing P5 exact method-digest authorization
    -> prove through the real owner

then run final affected regression/integration
```

**Software Design verdict: NO-PASS / rework-required.**
