---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: rework-required
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 6
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_plan_head: be5beaffbeda7391d998aca616c5dbb60e44b3d6
reviewed_implementation_commit: 022206646c518582889661c3b38c464b6a7760a7
reviewed_assembled_source_commit: cadf23c488ae61831d7dee8fccdc4eed98aaf8f4
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
closure_verdict: no-pass
---

# MLFF target-size optimizer normalization, practical-ceiling selection, objective-weight, and training-policy identity rework

## 0. Implementation closure verdict

**NO-PASS / reopened for bounded repair and acceptance closure.**

Software Design reviewed implementation commit `022206646c518582889661c3b38c464b6a7760a7`, assembled source/documentation commit `cadf23c488ae61831d7dee8fccdc4eed98aaf8f4`, revision-5 review head `be5beaffbeda7391d998aca616c5dbb60e44b3d6`, Protocol 5.15.0, and the directly related target-size restart, partial-boundary, acceleration-replay, P4-currentness, and P5-final-authorization contracts.

The implementation is directionally correct and closes the major revision-4 ownership defects:

- one canonical shared optimizer-setting resolver feeds P5 method identity and executable `MaceOptimizerPolicy`;
- executable/default parity is corrected for general LR, batch sizes, evaluation interval, EMA enable/decay, AMSGrad, weight decay, and clipping;
- learned-model dtype is resolved through one binary precision authority;
- target-size common preparation no longer owns batch size or learned-model dtype that it does not consume;
- target-size seed-neutral scientific identity excludes general LR, general EMA decay, workers, validation batch size, evaluation interval, optimizer seed, and candidate-local acceleration realization while retaining trajectory-changing optimizer/precision/backend state;
- target-size candidate loader geometry no longer treats `valid_batch_size` as science;
- accepted materializations can be replayed across worker/validation-batch drift without retiring the scientific trajectory;
- P5 has a corrected method-recipe identity cutover;
- practical-ceiling selection, objective/configuration/local-weight separation, native MACE weighted loss, P4 selected flow, and fresh P5 final production remain intact.

Four blockers remain. Three are implementation/identity defects and one is acceptance evidence:

1. **Unaccepted first-rung materialization can collide with execution-only drift.** Materialization/config bytes are written under the scientific trajectory path before any accepted cell progress exists. The path excludes `num_workers`/`valid_batch_size`, while the immutable config records them. A crash after materialization but before accepted completion followed by an execution-only edit can therefore make a scientifically identical first-rung retry fail create-or-verify.
2. **The new canonical optimizer resolver is not fail-closed on the actual configuration domain.** It uses `float(...)`, `int(...)`, and `bool(...)` coercion before exact type/domain validation. Non-finite numeric values can pass comparison-only checks; fractional integer fields can be truncated; booleans can enter integer fields; quoted/non-boolean values can be truth-normalized into booleans. A canonical owner is not complete until it validates exactly what it canonicalizes.
3. **Generic `[training].ema_decay` still leaks into target-size materialization when EMA is disabled.** Target-size seed-neutral identity correctly excludes general EMA decay, but `_mace_config_for_candidate()` writes `optimizer_policy.ema_decay` whenever `effective_ema_decay is None`, which is exactly the EMA-disabled case. Materialization scientific replay compares that field, so changing only general EMA decay can reject an accepted EMA-disabled target-size trajectory even though the field has no target-size scientific effect. This is a direct contradiction between P3 context identity and P3 materialization identity.
4. **Required assembled functional acceptance is not established on the reviewed candidate.** The accessible repository evidence does not establish the required focused/affected regression, real P2->P5 integration, real final-production historical-method rejection, and pinned-MACE 0.3.16 semantic acceptance. Under Protocol 5.15.0 an unexecuted required check is not a pass.

No Frozen high-level architecture change is required. The remaining repair is Tier-2 reduction/alteration at existing owners. Do not add a second optimizer policy, target-size compatibility registry, migration table, alternate materialization identity, warning lifecycle, restart database, or wrapper to reconcile contradictions.

This revision is snapshot-complete and supersedes revision 5 as the current implementation authority.

---

## 1. Tier-1 problem and scientific invariants

The target-size experiment answers:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

The sole target-data-cardinality independent variable remains:

```text
N = number of target configurations used for gradient training
T_N = pi_train[:N]
```

The optimizer-seed set is the stochastic replicate dimension. Ranking uses authenticated paired-seed target-side EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

The experiment distinguishes:

- **evidence-supported truncation**: a smaller finalist is practically equivalent to, or better than, a larger finalist;
- **practical-ceiling selection**: configured `Nmax` remains materially superior, so `Nmax` is the best permitted size while convergence remains unproven inside the configured ladder;
- **insufficient comparison**: malformed, foreign, missing, reordered, or numerically insufficient evidence prevents valid comparison and remains blocking.

No unconfigured rescue size is invented.

Binding product invariants:

- exact nested `T_N = pi_train[:N]` membership;
- one P1 canonical frame authority and neutral statistical substrate;
- one `P_train / M3` split and one `pi_train / pi_eval` authority;
- configured candidate/evaluation ladders;
- `q -> min(q,4) -> 2 -> 1` successive-halving topology;
- paired-seed arithmetic-mean aggregation;
- target-force RMSE ranking;
- practical-equivalence preference for smaller data size;
- one continuous scientific trajectory per `(N, optimizer_seed)` across `n1 -> n2 -> n3`;
- exact authenticated boundary checkpoint/EVAL2 evidence;
- P4 terminal/currentness ownership;
- P5 cross-validation on exactly frozen `T_selected`;
- fresh final production on exactly frozen `T_selected`;
- no screen/CV checkpoint as final-production parent;
- historical evidence is never silently reinterpreted under corrected semantics.

---

## 2. Frozen high-level architecture

The authority graph remains Frozen:

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

- materially superior configured ceiling is `SELECTED` with warning metadata, not a blocking failure;
- insufficient comparison remains blocking;
- target-size optimizer-progress normalization is screen-specific;
- target-size EVAL2 consumes the authenticated configured model state, EMA when enabled;
- objective/global coefficients, configuration weights, and local property masks remain separate owners;
- target-size/P5 executable loss family remains dependency-native MACE weighted energy+force+stress under the pinned dependency evidence;
- P3 owns target-size execution/restart evidence;
- P4 owns campaign terminal/currentness/adoption;
- P5 owns cross-validation and fresh final production;
- final production starts fresh;
- long GPU/full-production qualification remains deferred to final release.

The exact helper/function/module layout is delegated Tier 2. Refactor or delete current machinery when necessary to restore these semantics; do not preserve a contradictory helper merely because tests currently import it.

---

## 3. Accepted revision-4 implementation that must be retained

### 3.1 Practical-ceiling reducer

At terminal comparison:

```text
Nmax materially superior by > practical-equivalence epsilon
    -> status = SELECTED
    -> selected_target_size = Nmax
    -> exact membership digest
    -> terminal_reason_codes includes "nonconverged_at_configured_ceiling"
```

A smaller finalist within practical equivalence of a raw-best larger finalist wins. A strictly better smaller finalist wins normally. Insufficient comparison never fabricates selection. The ceiling warning means budget-limited rather than convergence-limited and does not create a new lifecycle.

### 3.2 Target-size optimizer normalization

The screen normalization policy remains:

```toml
[target_data.size_convergence.optimizer_normalization]
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

For training batch size `B`:

```text
U_ref = ceil(N_ref / B)
U_N   = ceil(N / B)
s_N   = U_ref / U_N
LR_N   = LR_ref * s_N
beta_N = beta_ref ** s_N
```

No hidden cap/floor or survivor-dependent recomputation is allowed. One `(N, seed)` realization is derived from full `n3` geometry and is preserved through all rungs.

General `[training].learning_rate` and `[training].ema_decay` are P5/general-training settings. They are **not target-size LR/EMA-decay authority**. Target-size LR/EMA are the normalization policy and candidate realization.

### 3.3 Objective/loss ownership

Retain:

- `TrainingObjectivePolicy` as owner of global energy/force/stress coefficients;
- `ConfigurationWeightPolicy` as owner of per-configuration multiplier;
- local property weights as availability/local modifiers, normally `1.0` present and `0.0` absent;
- explicit global coefficients in generated MACE configs;
- dependency-native `loss="stress"` / `WeightedEnergyForcesStressLoss` realization;
- loss-family identity through canonical MACE method/architecture ownership.

Do not duplicate the global objective ratio into local frame property weights.

### 3.4 Canonical shared optimizer-setting resolution

One resolved value feeds P5 method identity and real execution for:

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

Effective omitted campaign defaults remain:

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

Optimizer seed, role-specific epoch budgets, worker count, target-size normalization references, candidate N, CV fold state, and acceleration realization remain outside this shared resolution. Learned-model dtype remains owned by the binary precision authority.

### 3.5 Common-preparation narrowing

Batch size and learned-model dtype are not common-preparation scientific identity because common fitting consumes neither. They remain P3 execution-scientific state where they change training. Objective/configuration-weight/E0/harness inputs remain common-preparation identity.

### 3.6 Target-size role projection

Target-size seed-neutral scientific identity excludes:

- optimizer seed;
- candidate-local acceleration realization/mode;
- general learning rate;
- general EMA decay;
- worker count;
- validation batch size;
- evaluation interval.

It retains scientific trajectory-changing fields including:

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

The corrected P5 method recipe remains `mdstats.post-selection-method.2026-09.v2` or an equivalently newer explicit method identity. Historical pre-cutover CV/final evidence must not authorize corrected production. Final production requires CV acceptance whose exact method digest equals the method it is about to execute.

---

## 4. Relationship to existing restart and replay plans

### 4.1 Partial-boundary authority

Accepted immutable progress for a logical `(screen, boundary, N, seed)` cell is scientific evidence. It must be authenticated and reused. The scheduler executes only missing active cells. Genuine conflicting accepted evidence remains a hard error. Never delete/overwrite accepted progress to simplify restart.

### 4.2 First-boundary absence

Before a boundary completion for a cell is accepted, there is no continuation authority. An interrupted first-rung attempt is attempt-local scratch and must retry fresh. Existing first-rung checkpoint handling already applies this distinction. Materialization created only for an unaccepted first attempt must obey the same authority boundary.

### 4.3 Later-rung continuation and restart-epoch handoff

For `n2`/`n3`, the accepted restart-epoch workplan remains authoritative: resolve the exact authenticated predecessor through the existing P3 resume owner and use the one production `mdstats-mace-train` wrapper. Do not create fresh/resume wrapper variants, guessed restart epochs, or duplicate persisted restart metadata.

### 4.4 Candidate-local acceleration replay

The accepted acceleration-replay workplan remains authoritative: a published trajectory retains the acceleration realization that actually executed it without making later compatible realization drift global screen identity. The repairs below must not reintroduce current acceleration realization into global target-size scientific currentness.

---

## 5. Blocking repair A — classify unaccepted first-rung materialization as attempt scratch

### 5.1 Diagnosis

Current first-rung execution performs:

```text
build scientific trajectory
 -> materialization_directory = materialization_root / trajectory_digest
 -> materialize target/config
 -> reset/create uncommitted TRAIN2 checkpoint workspace
 -> train/evaluate
 -> publish accepted cell completion/progress
```

The trajectory digest intentionally excludes `num_workers` and `valid_batch_size`. The immutable MACE config records them as historical execution provenance. Thus this state is legal today:

```text
scientific trajectory S, execution settings A
 -> materialization/config A written at path keyed by S
 -> crash before accepted completion/progress

change only execution settings to B
 -> scientific trajectory remains S
 -> first rung should retry fresh
 -> config B addresses same path
 -> immutable create-or-verify rejects different bytes
```

The publisher is not the defect. The defect is treating an unaccepted attempt-local launch workspace as if its path were durable scientific authority.

### 5.2 Required end state

For a first-boundary cell with no authenticated accepted completion/progress:

- no first-rung attempt owns durable continuation authority;
- stale attempt-local materialization/checkpoint workspace may be discarded before the fresh attempt;
- current execution-only settings may be used without changing scientific generation/context/trajectory;
- if accepted cell evidence exists, ordinary recovery owns it and runtime must not execute/rematerialize/delete its durable parent graph;
- immutable create-or-verify semantics remain strict for accepted/canonical artifacts.

Preferred realization: extend the existing first-rung fresh-attempt cleanup boundary to include unaccepted materialization as well as checkpoint scratch. Do not add a materialization identity containing worker/validation-batch settings, compatibility registry, mutable latest pointer, orphan migration table, alternate first-rung state machine, or permissive overwrite mode.

### 5.3 Focused acceptance

Use the production `select-target-size` orchestration:

1. prepare a bounded campaign;
2. enter a first active cell and let real materialization publish;
3. interrupt after materialization exists but before trainer output becomes accepted completion/progress;
4. prove no progress/completion/head was accepted for that cell;
5. change only `num_workers` and/or `valid_batch_size`;
6. invoke `select-target-size` again;
7. prove first rung starts fresh (`start_epoch=0`), stale unaccepted materialization does not block, and no new scientific generation/context/trajectory is created;
8. continue through ordinary owners.

Negative companions:

- accepted progress must be recovered/reused and its materialization must not be deleted;
- genuine scientific drift remains stale/rejected;
- conflicting accepted immutable evidence remains a hard error.

Only numerical MACE work may be substituted below the real orchestration/identity/persistence owner boundary.

---

## 6. Blocking repair B — make canonical optimizer resolution fail-closed

### 6.1 Diagnosis

`resolve_shared_optimizer_settings()` centralizes configuration correctly but currently canonicalizes through `float(...)`, `int(...)`, and `bool(...)` before exact validation. This admits or silently reinterprets values outside the declared scientific domain.

Examples:

- `nan` and positive `inf` can pass sign-only checks for LR/regularization;
- fractional `batch_size`/`valid_batch_size`/`eval_interval` can be truncated by `int(...)`;
- booleans can enter integer fields because Python booleans are integers;
- non-boolean values can be truth-normalized into `ema`/`amsgrad`;
- some conversion errors can escape as raw Python exceptions rather than canonical `TrainingDataInputError`.

### 6.2 Required end state

At the existing canonical owner, reject invalid input before method identity or execution:

- `learning_rate`: finite real, `> 0`;
- `batch_size`: positive integer, not boolean, no fractional/string coercion;
- `valid_batch_size`: positive integer, not boolean, no fractional/string coercion;
- `eval_interval`: positive integer, not boolean, no fractional/string coercion;
- `ema`: actual boolean;
- `ema_decay`: finite real, `0 < value < 1`;
- `amsgrad`: actual boolean;
- `weight_decay`: finite real, `>= 0`;
- `clip_grad`: finite real, `> 0`;
- optimizer family: existing accepted-family validation remains fail-closed.

If `MaceOptimizerPolicy` remains an independently constructible/serialized authority, strengthen its existing constructor with matching finite/domain invariants so direct/persisted construction cannot bypass the canonical domain. Do not create a second validator object.

### 6.3 Focused acceptance

Add negatives for:

- `nan`, `inf`, `-inf` where representable for LR/EMA decay/weight decay/clip gradient;
- fractional batch/validation-batch/eval-interval values;
- booleans in integer fields;
- non-booleans in `ema`/`amsgrad`;
- malformed values that previously raised raw conversion errors.

Failure must occur before method identity, candidate trajectory, materialization, or trainer launch. Retain default and explicit-non-default parity through:

```text
config
 -> canonical resolver
 -> P5 method identity
 -> MaceOptimizerPolicy
 -> internal MACE config
 -> executable MACE projection
```

---

## 7. Blocking repair C — remove conditionally inert general EMA decay from target-size science

### 7.1 Diagnosis

The target-size role projection correctly declares general `[training].ema_decay` non-scientific. With EMA enabled, candidate config uses `trajectory.realization.effective_ema_decay`, so general EMA decay does not leak into the executable candidate.

With EMA disabled, however, `effective_ema_decay` is `None` and `_mace_config_for_candidate()` currently falls back to `optimizer_policy.ema_decay`. `_scientific_candidate_config()` removes only `num_workers` and `valid_batch_size`, so this inert general value remains part of materialization scientific replay.

That creates contradictory currentness:

```text
P3 execution context / trajectory:
    general [training].ema_decay is excluded

P3 materialization replay when ema=false:
    general [training].ema_decay is compared as scientific config
```

A completed `n1` cell with `ema=false` can therefore be rejected at `n2` after changing only general EMA decay, despite identical target-size training/evaluation semantics.

### 7.2 Required end state

When target-size EMA is disabled, general `[training].ema_decay` must not participate in target-size scientific configuration/currentness anywhere.

Prefer the simplest representation:

- **Preferred:** omit `ema_decay` from the target-size candidate MACE config when `ema=false`; the existing MACE translation already projects only present keys, so no new adapter is required.
- If pinned MACE configuration requires an `ema_decay` key even with `ema=false`, keep it only as well-formed inert execution provenance and exclude it **conditionally when EMA is false** from scientific materialization comparison.

When EMA is enabled:

- candidate config must continue to carry the realized target-size `effective_ema_decay` from the normalization policy;
- that realized beta remains scientific and strongly authenticated;
- general `[training].ema_decay` remains irrelevant to target-size science.

Do **not** globally classify `ema_decay` as execution-only, because realized target-size EMA decay is scientific when EMA is enabled. Do not add an EMA compatibility registry, second optimizer policy, or migration mechanism.

### 7.3 Focused acceptance

Real-owner restart cases:

1. run/accept `n1` with `ema=false`;
2. change only general `[training].ema_decay`;
3. reconstruct the real screen/restart authority;
4. resume the survivor through the real `resolve_target_size_candidate_for_resume()` / `select-target-size` path to `n2`;
5. prove generation, execution-context digest, trajectory digest, scientific materialization authority, and continuation ancestry remain current.

Also prove:

- `ema=false -> true` and `true -> false` remain genuine target-size scientific identity changes;
- with EMA enabled, changing target-size `reference_ema_decay` changes the appropriate target-size identity/realization and rejects stale continuation;
- with EMA enabled, changing only general `[training].ema_decay` remains non-scientific;
- materialization replay still strongly authenticates realized effective beta whenever EMA is enabled.

---

## 8. Acceptance blocker D — execute the required assembled evidence

### 8.1 Evidence status

The reviewed repository state does not establish the required assembled functional acceptance. Source inspection is not a substitute for execution. The workplan remains open until required checks actually execute and pass on the repaired candidate.

### 8.2 P5 historical-method cutover through the real authorization owner

Do not stop at asserting old/new method digests differ. Exercise final-production authorization:

1. build/publish bounded valid CV evidence under the historical pre-cutover method identity or an authenticated historical-method fixture;
2. resolve the corrected P5 method;
3. enter the real final-production authorization owner;
4. prove historical-method CV acceptance is rejected on exact method mismatch before final trainer/materialization launch;
5. prove matching corrected-method CV acceptance is admitted through the same owner.

Use the existing exact method-digest authorization; no cutover registry is permitted.

### 8.3 Practical-ceiling retention

Retain a bounded real-owner integration:

```text
terminal paired-seed reducer evidence
 -> SELECTED Nmax + nonconverged_at_configured_ceiling warning
 -> real P3 terminal head
 -> P4 TERMINAL_SELECTED adoption/currentness
 -> exact N_selected / T_selected
 -> next lifecycle command = cross-validate
```

### 8.4 Real pinned-MACE semantic acceptance

Run the pinned MACE 0.3.16 parser/loss integration in an environment containing the pinned dependency. It must actually execute, not skip, and prove:

- target-size and P5 configs select the accepted weighted energy+force+stress loss family;
- global E/F/S coefficients equal mdstats objective settings;
- configuration weights and local property masks are consumed under accepted dependency semantics;
- missing-label zero masks behave correctly;
- corrected paths do not silently fall back to `UniversalLoss`.

### 8.5 Final affected-surface regression

At minimum execute the final affected versions of:

- target-size statistical-authority tests;
- P3A through P3F and later P3 closure/replay suites;
- canonical optimizer-setting tests;
- execution-only drift restart tests, including the new unaccepted-materialization and EMA-disabled cases;
- first-boundary interruption/retry and partial-boundary recovery suites;
- acceleration-realization replay tests;
- realized-MACE-architecture tests;
- P3 head-pointer/reconciliation tests;
- affected P4 suites;
- affected P5 suites;
- MACE executable-config tests;
- binary/critical-precision tests;
- TRAIN2 policy/runtime/restart/continuation tests;
- prepared-generation identity/currentness tests;
- campaign lifecycle/status/advance tests;
- P5 identity/CV/final-production authorization/materialization/execution/publication tests;
- objective/weight/export tests;
- affected documentation integrity/specification tests.

After assembly, re-derive the transitive affected surface from the final diff and run broader MLFF regression if the boundary is uncertain. Required real-MACE acceptance may not be counted as passed when skipped.

Production-scale GPU qualification remains **deferred**. Functional acceptance is required; long data-heavy GPU qualification is not.

---

## 9. Implementation authority

### Frozen

Frozen authority is limited to:

- the Tier-1 scientific question and exact `T_N` membership;
- the P1->P5 authority graph;
- practical-ceiling selected-warning semantics;
- inverse-update LR/EMA normalization mathematics;
- one continuous target-size scientific trajectory per `(N, seed)`;
- P3 immutable accepted evidence/restart ownership;
- distinction between accepted partial progress and unaccepted attempt scratch;
- target-size general-LR/general-EMA-decay exclusion and realized LR/EMA authority;
- objective/configuration/local-weight separation and accepted MACE loss family;
- one canonical shared optimizer-setting resolution;
- P5 exact method-digest CV authorization;
- fresh final production;
- no silent reinterpretation of historical evidence.

### Delegated

Implementation may simplify Tier-2 details including:

- exact helper location for strict shared-setting validation;
- exact factoring of first-rung fresh-attempt cleanup;
- exact conditional representation of `ema_decay` when target-size EMA is disabled;
- internal fixture organization;
- redundant old helpers made obsolete by canonical resolution;
- diagnostics.

Prefer deletion/narrowing/consolidation over aliases or adapters.

### Reopen Design only on evidence

Reopen only the affected design surface if implementation proves a Frozen assumption false, including:

1. unaccepted first-rung materialization has an independent scientific durability requirement before logical-cell acceptance;
2. cleanup cannot be safe because an accepted object can legitimately reference that materialization before cell acceptance;
3. worker count or target-size validation batch size changes deterministic scientific trajectory/ranking semantics;
4. general `[training].ema_decay` changes target-size behavior when `ema=false` despite EMA being disabled;
5. common preparation actually consumes batch size or learned-model dtype;
6. one canonical shared optimizer resolver cannot serve P3/P5 through role-specific projection without method-family redesign;
7. pinned MACE 0.3.16 does not realize accepted weighted loss semantics;
8. existing exact P5 method-digest authorization cannot prevent historical method evidence from authorizing corrected final production.

Do not reopen because a current helper API is inconvenient.

---

## 10. Forbidden repair patterns

Do not close this work by:

- weakening immutable create-or-verify semantics;
- deleting/overwriting accepted partial-boundary evidence;
- adding worker/validation-batch/general-EMA-decay back into target-size scientific trajectory identity merely to suppress restart conflicts;
- globally treating EMA decay as execution-only when EMA is enabled;
- adding compatibility registries, migration tables, alternate materialization generations, or a second restart database;
- teaching common preparation to consume batch/dtype artificially;
- restoring independent P5 identity/execution defaults;
- adding a second optimizer validator instead of fixing the canonical owner;
- permitting non-finite/malformed optimizer settings because a dependency may fail later;
- adding another target-size terminal/warning lifecycle;
- treating digest inequality alone as real final-production cutover acceptance;
- counting skipped pinned-MACE acceptance as pass;
- substituting long GPU qualification for functional regression.

If another sibling appears in the same canonical-config or attempt-scratch/scientific-projection family, repair the shared owner under this workplan rather than layering another local patch.

---

## 11. Repair sequence and gates

### Gate R6-A — canonical configuration domain closure

- make the existing shared resolver exact-type and finite-domain fail-closed;
- strengthen `MaceOptimizerPolicy` too if it independently admits outside-domain direct/persisted construction;
- add malformed/non-finite negatives;
- rerun default/explicit parity tests.

Exit only when malformed settings cannot enter identity or execution.

### Gate R6-B — target-size execution-vs-science closure

Treat the two remaining target-size leaks as one ownership family:

- extend first-rung no-authority cleanup to unaccepted materialization scratch;
- remove/conditionally de-scientize generic EMA decay when target-size EMA is disabled;
- preserve accepted materialization immutability;
- preserve realized target-size beta as science when EMA is enabled;
- add post-materialization/pre-completion first-rung interruption acceptance;
- add accepted `n1 -> n2` EMA-disabled general-EMA-decay drift acceptance;
- retain scientific-drift negatives;
- rerun first-boundary, partial-boundary, continuation, acceleration replay, P3/P4 currentness suites.

Exit only when every execution-only/inert value is non-scientific in **both** fresh-attempt and accepted-replay states while true trajectory changes remain strongly invalidating.

### Gate R6-C — P5 real authorization closure

- retain canonical shared settings and method-recipe cutover;
- prove the real final-production owner rejects historical-method CV acceptance before launch;
- prove matching corrected acceptance succeeds;
- rerun P5 CV/final currentness/execution/publication regression.

### Gate R6-D — assembled acceptance

- run practical-ceiling P2->P5 integration;
- run real pinned-MACE 0.3.16 parser/loss semantics;
- run final re-derived affected regression;
- update normative documentation only if repair changes current-state semantics;
- regenerate PDFs only after normative Markdown is final.

No long GPU/full-production qualification is required here.

---

## 12. Closure criteria

Close this workplan only when all of the following are true:

- first-rung retry after unaccepted materialization survives execution-only drift without changing scientific identity;
- accepted materialization/restart survives general EMA-decay drift when target-size EMA is disabled;
- scientific EMA enablement/reference-beta changes still invalidate correctly;
- canonical optimizer settings reject malformed/non-finite values before identity/launch;
- P5 method identity and executable optimizer remain one canonical method;
- real final-production authorization rejects historical-method CV evidence;
- practical-ceiling selected-warning flow remains intact through P4/P5;
- required pinned-MACE semantic acceptance actually executes and passes;
- final affected-surface regression executes and passes;
- no new competing configuration/restart/materialization authority was introduced.

The architecture and scientific method remain accepted. The implementation is close, but the remaining contradictions can still retire valid scientific work or admit invalid method configuration, so closure would be premature.

**Software Design verdict: NO-PASS / rework-required.**
