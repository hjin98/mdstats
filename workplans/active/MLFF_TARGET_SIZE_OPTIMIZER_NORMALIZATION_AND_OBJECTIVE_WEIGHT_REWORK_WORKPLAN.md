---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: rework-required
created_date: 2026-09-05
amended_date: 2026-09-06
review_revision: 7
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_design_handoff_commit: 43a8b5f78880b9faaf4b023e979cb6303b1291e3
reviewed_implementation_commit: 932cbff216f1fddb7b1102594d607975d397941b
reviewed_assembled_source_commit: 08ceafd0acf79c92652cc27d407efc9937c16cd1
architecture_change: narrow-methodological-rework
amends_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
design_handoff_verdict: pass
implementation_review_verdict: no-pass
closure_verdict: no-pass
---

# MLFF target-size optimizer normalization, practical-ceiling selection, objective-weight, and training-policy identity rework

## 0. Current implementation review and authority

**Software Design: PASS / closed.**  
**Implementation: NO-PASS / bounded rework remains.**

Software Design re-reviewed the newly completed implementation at executable commit
`932cbff216f1fddb7b1102594d607975d397941b` and assembled source/documentation commit
`08ceafd0acf79c92652cc27d407efc9937c16cd1` against the accepted Protocol 5.15.0 design.

No Frozen scientific or high-level architectural decision needs revision. The remaining findings are implementation nonconformance to already accepted requirements. This Revision 7 consolidates and supersedes Revision 6 plus
`MLFF_TARGET_SIZE_OPTIMIZER_NORMALIZATION_AND_OBJECTIVE_WEIGHT_REWORK_FINAL_DESIGN_CLOSURE.md`
as the sole current task-specific implementation handoff. Earlier review artifacts remain historical context only.

### 0.1 Concerns now closed by the new implementation

The following previously blocking concerns are now accepted and must be preserved:

1. **Shared live `[training]` optimizer resolution is fail-closed.**
   `resolve_shared_optimizer_settings()` now validates exact boolean/integer/finite-real domains before canonicalization, and the executable `MaceOptimizerPolicy` constructor rejects the same malformed direct values.
2. **Single-writer first-rung crash/retry collision is closed.**
   An unaccepted first-rung materialization can be reclaimed and rematerialized so a retry after worker/validation-batch drift starts fresh at `start_epoch=0` without minting a new scientific generation/context/trajectory; accepted progress remains preserved.
3. **Conditionally inert general `[training].ema_decay` no longer leaks into target-size materialization.**
   With target-size EMA disabled, candidate configuration omits `ema_decay`; with EMA enabled, the realized normalized target-size beta remains present and scientific.
4. **P5 historical-method cutover is exercised through the real final-production authorization owner.**
   Historical-method CV evidence is rejected against the corrected method, while matching corrected evidence is admitted through the same owner before production launch.
5. The previously accepted practical-ceiling reducer, target-size normalization mathematics, objective/configuration/local-weight separation, common-preparation narrowing, seed-neutral target-size scientific projection, binary precision ownership, accepted acceleration replay, P4 selected flow, and fresh P5 final-production architecture remain intact.

### 0.2 Remaining blockers

Only the following issues remain active:

1. **P3 live-writer safety remains incomplete.** The new first-rung cleanup still deletes the deterministic materialization directory whenever accepted progress is absent. Absence of accepted progress proves only that the workspace is not durable scientific authority; it does not prove another live `select-target-size` invocation is not currently using it. Destructive cleanup therefore still needs execution-local single-writer ownership/fencing.
2. **The bounded canonical policy-domain family is only partially closed.** The shared live `[training]` resolver is strict, but target-size optimizer-normalization resolution/deserialization, `TrainingObjectivePolicy`, `ConfigurationWeightPolicy`, and persisted `MaceOptimizerPolicy.from_dict()` still pre-coerce values with `int(...)`, `float(...)`, or `bool(...)` before exact validation.
3. **Pinned-MACE weighted-loss semantic acceptance is not established.** Parser/config projection evidence is insufficient; the actual pinned MACE 0.3.16 weighted energy+force+stress loss path must execute with discriminating non-default coefficients/weights/masks and agree with an independent expected semantic result.
4. **Final assembled functional acceptance is not established.** The reviewed candidate has documentation-build evidence, but not the required final affected-regression plus assembled P2->P5 / real-owner integration acceptance on the final executable candidate.

These are Tier-2 repair/evidence obligations. Do not introduce a new scientific authority, compatibility registry, migration database, restart state machine, warning lifecycle, or parallel optimizer-policy hierarchy.

---

## 1. Tier-1 problem and scientific invariants

The target-size experiment asks:

> Within the configured practical target-data budget, what is the smallest nested target-training cardinality whose performance is not materially improved by using more unique target data; and, if no such plateau is demonstrated before the practical ceiling, what is the best permitted size available?

The sole target-data-cardinality independent variable remains:

```text
N = number of target configurations used for gradient training
T_N = pi_train[:N]
```

The optimizer-seed set is the stochastic replicate dimension. Ranking uses authenticated paired-seed target-side EVAL2 evidence at the exact configured fidelity/evaluation boundaries.

Binding product invariants remain:

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
- materially superior configured ceiling is `SELECTED` with `nonconverged_at_configured_ceiling` warning metadata rather than a blocking failure;
- insufficient comparison remains blocking;
- P4 terminal/currentness ownership;
- P5 cross-validation on exactly frozen `T_selected`;
- fresh final production on exactly frozen `T_selected`;
- no screen/CV checkpoint as final-production parent;
- historical evidence is never silently reinterpreted under corrected semantics.

No unconfigured rescue size is invented.

---

## 2. Frozen high-level architecture

The Frozen authority graph remains:

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

- target-size optimizer-progress normalization is screen-specific;
- for batch size `B`, `U_ref = ceil(N_ref/B)`, `U_N = ceil(N/B)`, `s_N = U_ref/U_N`, `LR_N = LR_ref*s_N`, and `beta_N = beta_ref**s_N`;
- there is no hidden cap/floor, survivor-dependent rescaling, or rung-local reconstruction of the normalized scientific trajectory;
- target-size EVAL2 consumes the authenticated configured model state, EMA when enabled;
- general `[training].learning_rate` and general `[training].ema_decay` are not target-size LR/EMA-decay authority;
- realized target-size LR and realized EMA beta are scientific when applicable;
- global E/F/S objective coefficients, configuration weights, and local property availability/modifier weights remain separate semantic layers;
- target-size/P5 executable loss family remains dependency-native MACE weighted energy+force+stress under pinned dependency evidence;
- P3 owns authenticated target-size execution/restart evidence;
- P4 owns campaign terminal/currentness/adoption;
- P5 owns CV and fresh final production;
- accepted logical-cell evidence is durable scientific/restart authority;
- an unaccepted first-rung attempt workspace is execution-local scratch only;
- process liveness is execution state, not scientific identity;
- final production starts fresh;
- long GPU/full-production qualification remains deferred to final release.

Exact helper/module placement, local lock primitive, validation helper shape, fixture layout, and equivalent simpler Tier-2 realization remain delegated.

---

## 3. Accepted implementation state that must be retained

### 3.1 Practical-ceiling reducer

At terminal comparison:

```text
Nmax materially superior by > practical-equivalence epsilon
    -> status = SELECTED
    -> selected_target_size = Nmax
    -> exact membership digest
    -> terminal_reason_codes includes "nonconverged_at_configured_ceiling"
```

A smaller finalist within practical equivalence of a raw-best larger finalist wins. A strictly better smaller finalist wins normally. Insufficient comparison never fabricates selection.

### 3.2 Target-size optimizer normalization and role projection

The configurable reference remains:

```toml
[target_data.size_convergence.optimizer_normalization]
reference_target_size = 1024
reference_learning_rate = 1.0e-4
reference_ema_decay = 0.99999
```

Target-size seed-neutral scientific identity excludes:

- optimizer seed;
- candidate-local acceleration realization/mode;
- general learning rate;
- general EMA decay;
- worker count;
- validation batch size;
- evaluation interval.

It retains trajectory-changing state including training batch size, EMA enablement, AMSGrad, weight decay, gradient clipping, learned-model/critical precision, accepted device/backend/acceleration policy, and full-screen `n3` horizon.

Candidate realization retains exact target membership/count, `ceil(N/B)` update geometry, full-n3 exposure, precision, seed, normalization identity, effective LR/EMA, realized LR schedule, and candidate-local acceleration provenance. `valid_batch_size` remains absent from candidate scientific loader geometry.

When target-size EMA is disabled, candidate configuration must omit or scientifically ignore any inert generic EMA decay; the current accepted realization omits the key. When EMA is enabled, candidate configuration must carry the realized normalized beta and authenticate it strongly.

### 3.3 Objective/loss ownership

Retain:

- `TrainingObjectivePolicy` as owner of global energy/force/stress coefficients;
- `ConfigurationWeightPolicy` as owner of per-configuration multiplier;
- local property weights as availability/local modifiers, normally `1.0` present and `0.0` absent;
- explicit global coefficients in generated MACE configs;
- dependency-native `loss="stress"` / `WeightedEnergyForcesStressLoss` realization;
- no duplication of the global objective ratio into local property masks.

### 3.4 Canonical shared optimizer/live execution resolution

One resolved live configuration value feeds P5 method identity and real execution for general LR, training batch size, validation batch size, evaluation interval, EMA enable/decay, AMSGrad, weight decay, gradient clipping, and supported optimizer family.

Effective omitted defaults remain:

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

The live resolver now rejects malformed/non-finite/exact-type violations before identity/execution. `MaceOptimizerPolicy` direct construction now enforces the same domain. Preserve this closure.

Optimizer seed, role-specific epoch budgets, worker count, target-size normalization references, candidate `N`, CV fold state, and acceleration realization remain outside shared method resolution. Learned-model dtype remains owned by the binary precision authority.

### 3.5 Common-preparation narrowing and restart/replay

Batch size and learned-model dtype are not common-preparation identity because common fitting consumes neither. Objective/configuration-weight/E0/harness inputs remain common-preparation identity.

Accepted partial-boundary progress is immutable scientific evidence and must be authenticated/reused. Later rungs resolve the exact authenticated predecessor through the existing P3 resume owner. Candidate-local acceleration replay retains the realization that actually executed the accepted trajectory without promoting later compatible realization drift into global screen identity.

### 3.6 P5 method cutover

The corrected method recipe remains `mdstats.post-selection-method.2026-09.v2` or an explicitly newer equivalent method identity. Historical pre-cutover CV evidence cannot authorize corrected final production. The new real-owner authorization acceptance is considered closed and must remain in regression coverage.

---

## 4. Remaining blocker A — live-writer-safe first-rung scratch reclamation

### 4.1 Current defect

The current implementation correctly treats an unaccepted first-rung materialization as scratch in a serial retry, but the cleanup decision is effectively:

```text
materialization exists
AND accepted progress path does not exist
    -> delete materialization directory
```

That is insufficient under concurrent invocations. Absence of accepted progress does not prove the workspace is stale; another live `select-target-size` process may currently own it and be training from it.

A second invocation can therefore delete or replace the first invocation's live workspace before either publishes accepted evidence.

### 4.2 Required end state

Before destructive cleanup/rematerialization of an unaccepted first-rung workspace, the execution path must establish exclusive live ownership of the logical cell/workspace.

Required behavior:

- **Accepted progress/completion exists:** authenticate/reuse through existing P3 recovery; never delete its parent materialization merely to rerun the cell.
- **No accepted progress and another live writer owns the same cell/workspace:** do not delete, overwrite, or launch a duplicate scientific execution. Wait/reconcile, fail cleanly as already/in-progress, or use an existing equivalent single-writer exclusion.
- **No accepted progress and no live writer owns the cell:** prior first-rung materialization/checkpoint artifacts are stale attempt scratch and may be removed/recreated for a fresh `start_epoch=0` attempt.
- **Writer exits/crashes:** execution-only ownership releases without scientific-state migration so a later invocation can reclaim stale scratch.
- After accepted cell publication, existing immutable/replay authority resumes; live ownership may not become a second durability authority.

### 4.3 Simplicity boundary

Prefer the minimum repository-native execution-local exclusion. If none exists, a narrow advisory lock/ownership scope around the logical cell or attempt workspace is acceptable.

Do not add:

- a persisted liveness database or lease state machine;
- a new scientific attempt identifier;
- a materialization compatibility registry;
- a mutable latest-materialization pointer;
- a broad cleanup daemon;
- process-liveness meaning to campaign scientific/currentness fields;
- a second restart authority;
- a coarse campaign-wide lock across expensive MACE work unless an already-existing exclusion demonstrably provides the required semantics without degrading the accepted execution architecture.

### 4.4 Required acceptance

Exercise the real `select-target-size` / P3 orchestration with bounded numerical work below it:

1. invocation A owns a first-rung cell, publishes materialization, and pauses before accepted completion/progress;
2. invocation B reaches the same current screen/logical cell;
3. prove B neither deletes/mutates A's workspace nor launches duplicate scientific execution;
4. completion branch: A publishes accepted evidence, then B re-reconciles/reuses it;
5. crash branch: A exits without accepted evidence, ownership releases, and a later invocation reclaims stale scratch and starts fresh;
6. preserve the already-passing serial crash/retry with worker/validation-batch drift;
7. preserve accepted-progress immutability, conflict detection, scientific-drift rejection, and create-or-verify semantics.

A test double may replace expensive MACE numerical work only below the production orchestration/ownership/persistence boundary.

---

## 5. Remaining blocker B — complete the bounded canonical policy-domain family

### 5.1 Scope

This is not a repository-wide parser cleanup. Close only the policy family directly owned/redefined by this work:

1. shared optimizer settings and independently constructible/persisted `MaceOptimizerPolicy`;
2. target-size optimizer-normalization reference policy;
3. `TrainingObjectivePolicy` config/current-schema serialization seam;
4. `ConfigurationWeightPolicy` config/current-schema serialization seam.

The shared live `[training]` resolver and direct `MaceOptimizerPolicy` constructor are already corrected. The remaining gap is that adjacent resolvers and `from_dict()` readers still coerce malformed values before validation.

### 5.2 Canonical-domain rules

Validate before lossy normalization:

- real scientific fields: finite real numeric values only; reject booleans and strings; canonicalize to float only after validation;
- integer scientific fields: actual integers only; reject booleans, fractional floats, and numeric strings;
- boolean policy fields: actual booleans only; do not truth-normalize numbers/strings;
- collection elements: validate declared element domains rather than silently casting arbitrary objects;
- current-schema persisted payloads: malformed types must fail; do not turn malformed records into valid current records by `int/float/bool` coercion;
- valid explicitly supported historical schema representations may continue only through an existing explicit compatibility reader; implementation accidents are not compatibility contracts.

High-risk required domains:

- shared LR/EMA decay/weight decay/clip gradient: finite real with existing ranges;
- shared batch sizes/eval interval: positive integer, not bool;
- shared EMA/AMSGrad: actual bool;
- target-size `reference_target_size`: positive integer, not bool;
- target-size `reference_learning_rate`: finite real `> 0`, not bool;
- target-size `reference_ema_decay`: finite real in `(0,1)`, not bool;
- global E/F/S coefficients: finite nonnegative real, not bool, with at least one positive;
- objective group-awareness flag: actual bool;
- focus atomic numbers: positive integer elements, no bool/fraction/string reinterpretation;
- configuration-weight equalization flag: actual bool;
- configuration-weight multipliers/bounds: finite positive real, not bool, preserving normalized-mean/bound constraints.

Do not create a second validator object/hierarchy. Reuse or consolidate small validation helpers where that reduces total complexity.

### 5.3 Required acceptance

- focused deterministic invalid-domain cases for all four owner families;
- current-schema deserialization negatives proving malformed payloads fail before canonical conversion;
- positive resolve/serialize/deserialize identity stability for valid values;
- positive config -> policy -> identity -> executable config -> dependency-facing projection parity;
- bounded property-based coverage when Hypothesis is available and economical for the parser/normalizer domain;
- bounded structural/AST census over these four families for pre-validation `int(...)`, `float(...)`, or `bool(...)` coercion of config/current-schema persisted fields; a focused Semgrep rule is appropriate when available, with known-positive/known-negative rule validation;
- structural zero findings never substitute for runtime tests.

Exit only when malformed values cannot silently become valid current scientific/method identity or execution state.

---

## 6. Acceptance blocker C — pinned MACE weighted-loss semantics

The accepted dependency-native loss architecture is unchanged, but its semantic acceptance must actually execute against pinned MACE 0.3.16.

Use deliberately **non-default and mutually distinguishable** global objective coefficients and configuration weights plus at least one missing-property zero-mask case so the test fails if mdstats forwarding is omitted, MACE defaults are used, global coefficients are duplicated into local weights, or another loss family is selected.

At minimum prove through the real dependency-facing path:

- instantiated loss is `WeightedEnergyForcesStressLoss` / accepted `loss="stress"` semantics, not `UniversalLoss`;
- configured mdstats global E/F/S coefficients reach the dependency loss;
- per-configuration weight and local property masks are consumed at distinct intended layers;
- missing property contributes zero through the local mask rather than by changing the global objective;
- a bounded dependency-calculated loss/reduction agrees with an independently derived expected value or equivalent dependency-grounded semantic oracle.

Parser/config argument equality alone is insufficient for this claim. Required pinned-MACE acceptance must execute rather than skip.

---

## 7. Acceptance blocker D — final assembled functional closure

On the final candidate after all remaining executable edits:

1. reconcile every Tier-1/Frozen obligation above against the assembled source;
2. re-derive the transitive affected surface from the final diff;
3. execute the complete affected regression;
4. execute real-boundary integration through the assembled affected product;
5. run repository/project-required checks;
6. update normative documentation only if current behavior/contracts changed, then regenerate derived PDFs after Markdown is final.

Minimum affected coverage includes final versions of:

- target-size statistical-authority and practical-ceiling tests;
- P3A-P3F and later P3 closure/replay suites;
- canonical optimizer/policy-domain tests;
- execution-only drift restart, serial stale-materialization retry, **concurrent live-writer/reclamation**, and EMA-disabled cases;
- first-boundary interruption/retry and partial-boundary recovery;
- acceleration-realization replay;
- realized-MACE architecture;
- P3 head-pointer/reconciliation;
- affected P4 suites;
- P5 identity/CV/final-production authorization/materialization/execution/publication;
- MACE executable configuration plus the semantic weighted-loss acceptance from Section 6;
- binary/critical precision;
- TRAIN2 policy/runtime/restart/continuation;
- prepared-generation identity/currentness;
- campaign lifecycle/status/advance;
- objective/weight/export;
- affected documentation/specification integrity.

Retain the already-closed real-owner P5 historical-method rejection in final regression. Retain bounded real-owner practical-ceiling flow:

```text
terminal paired-seed reducer evidence
 -> SELECTED Nmax + nonconverged_at_configured_ceiling warning
 -> real P3 terminal head
 -> P4 TERMINAL_SELECTED adoption/currentness
 -> exact N_selected / T_selected
 -> next lifecycle command = cross-validate
```

If the final affected boundary cannot be confidently bounded, run the broader MLFF regression suite.

Production-scale GPU qualification remains **deferred**. It cannot substitute for missing functional regression/integration.

---

## 8. Implementation authority

### Frozen

Frozen authority is limited to:

- Tier-1 scientific question and exact `T_N` membership;
- P1->P5 authority graph;
- practical-ceiling selected-warning semantics;
- inverse-update LR/EMA normalization mathematics;
- one continuous target-size scientific trajectory per `(N, seed)`;
- P3 immutable accepted evidence/restart ownership;
- distinction between accepted progress and unaccepted attempt scratch;
- process liveness excluded from scientific identity;
- target-size general-LR/general-EMA-decay exclusion and realized LR/EMA authority;
- objective/configuration/local-weight separation and accepted MACE loss family;
- one canonical shared optimizer/method semantics;
- P5 exact method-digest CV authorization;
- fresh final production;
- no silent reinterpretation of historical evidence.

### Delegated

Implementation may simplify or replace Tier-2 details including:

- exact execution-local live-writer exclusion primitive;
- exact helper location/factoring for first-rung cleanup;
- exact strict-validation helper shape;
- internal fixture organization;
- redundant helpers made obsolete by canonical resolution;
- diagnostics.

Prefer deletion/narrowing/consolidation over aliases, wrappers, parallel state, or compatibility machinery.

### Reopen Design only on genuine evidence

Reopen only the affected design surface if implementation proves one of these assumptions false:

1. safe stale-scratch reclamation cannot be achieved with existing or ephemeral execution-local ownership and truly requires persistent lease/liveness architecture;
2. accepted P3 evidence can legitimately reference a first-rung materialization before logical-cell acceptance in a way that makes cleanup unsafe;
3. worker count or target-size validation batch size changes deterministic scientific trajectory/ranking semantics;
4. a supported current/historical configuration schema intentionally relies on one of the lossy coercions forbidden above and cannot be preserved through an explicit compatibility boundary;
5. common preparation actually consumes batch size or learned-model dtype;
6. one canonical optimizer/method policy cannot serve P3/P5 through role-specific projection without method-family redesign;
7. pinned MACE 0.3.16 requires a materially different loss/weight ownership architecture;
8. existing exact P5 method-digest authorization cannot prevent historical evidence from authorizing corrected production.

Do not reopen because a current helper API, fixture, or lock API is inconvenient.

---

## 9. Forbidden repair patterns

Do not close this work by:

- weakening immutable create-or-verify semantics;
- deleting/overwriting accepted partial-boundary evidence;
- deleting unaccepted materialization merely because progress is absent without establishing that no other live writer owns the workspace;
- treating stage status, deterministic attempt identity, PID-file existence, or stale lock-file existence by itself as scientific or liveness truth;
- adding worker/validation-batch/general-EMA-decay back into target-size scientific trajectory identity merely to suppress restart conflicts;
- globally treating EMA decay as execution-only when EMA is enabled;
- adding a persisted lease database, compatibility registry, migration table, alternate materialization generation, mutable latest pointer, or second restart database;
- teaching common preparation to consume batch/dtype artificially;
- restoring independent P5 identity/execution defaults;
- fixing only the shared `[training]` resolver while leaving the plan-owned target-size normalization/objective/configuration-weight/current-schema readers free to silently coerce the same malformed type classes;
- weakening current schema integrity by coercing malformed persisted policy payloads into valid records;
- adding a second optimizer validator hierarchy rather than consolidating validation at existing owners;
- permitting non-finite/malformed settings because a dependency may fail later;
- treating parser/config equality as proof of weighted-loss semantics;
- counting skipped pinned-MACE acceptance as pass;
- adding another target-size terminal/warning lifecycle;
- substituting long GPU qualification for functional regression.

If another sibling appears in the same canonical-policy or attempt-scratch/scientific-projection family, repair the shared owner rather than layering another local patch.

---

## 10. Remaining implementation sequence

### Gate R7-A — canonical policy-domain closure

Complete Section 5 as one coherent stage:

- strict target-size normalization config/current-schema deserialization;
- strict objective/configuration-weight config/current-schema deserialization;
- strict persisted `MaceOptimizerPolicy.from_dict()` without pre-coercion of current schema values;
- preserve already-correct live shared optimizer/direct-constructor behavior;
- focused malformed/non-finite/type negatives, positive round-trip/parity, structural family census, and stage-local affected regression.

### Gate R7-B — P3 live-writer ownership closure

Complete Section 4:

- establish execution-local single-writer ownership before destructive first-rung scratch reclamation and execution;
- preserve serial crash/retry repair;
- preserve accepted evidence immutability and scientific-drift rejection;
- add completion and crash concurrent-writer acceptance plus stage-local affected regression.

### Gate R7-C — pinned dependency semantic closure

Execute Section 6 against pinned MACE 0.3.16 with non-default discriminating coefficients/weights/missing-property masks and an independent semantic expected result.

### Gate R7-D — assembled acceptance

Execute Section 7 on one final assembled candidate after all material executable edits.

No long production/GPU qualification is required for this workplan.

---

## 11. Closure criteria

Close this workplan only when all of the following are true:

- no live first-rung writer can have its unaccepted workspace destructively reclaimed by a concurrent invocation;
- stale unaccepted first-rung scratch remains safely reclaimable after owner exit/crash and retries from epoch 0 without changing scientific identity;
- accepted materialization/progress remains immutable and recoverable;
- generic EMA decay remains non-scientific to target-size when EMA is disabled, while EMA enablement and realized/reference beta changes remain scientifically invalidating as appropriate;
- all four plan-owned canonical policy families reject malformed/non-finite/current-schema type violations before identity/execution and valid values round-trip stably;
- P5 corrected method identity and executable optimizer remain one canonical method, and historical-method CV evidence remains rejected by the real final-production owner;
- practical-ceiling selected-warning flow remains intact through P4/P5;
- required pinned-MACE weighted-loss semantic acceptance actually executes and passes;
- final re-derived affected-surface regression and assembled integration execute and pass;
- repository/project-required checks pass;
- no new competing configuration/restart/materialization/liveness authority was introduced.

The architecture and scientific method remain accepted. The remaining work is bounded implementation repair and acceptance closure.

**Software Design verdict: PASS / closed.**  
**Implementation review verdict: NO-PASS / rework-required until R7-A through R7-D close.**
