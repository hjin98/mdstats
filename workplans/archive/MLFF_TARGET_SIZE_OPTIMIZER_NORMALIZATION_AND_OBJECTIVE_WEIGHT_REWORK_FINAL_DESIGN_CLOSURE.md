---
kind: implementation-workplan-review-amendment
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK-FINAL-DESIGN-CLOSURE
parent_workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: implementation-ready
created_date: 2026-09-06
reviewed_plan_commit: 8e198a196602f62386c5405d2e4fffe4dcb52975
reviewed_implementation_commit: 022206646c518582889661c3b38c464b6a7760a7
design_handoff_verdict: pass
implementation_review_verdict: no-pass-until-repair-and-acceptance
precedence: This amendment is the final Software Design -> Implementation handoff for the parent workplan. It adds and clarifies the bounded obligations below and changes Design readiness to implementation-ready. Every non-conflicting Tier-1 invariant, Frozen decision, repair obligation, forbidden pattern, acceptance requirement, and redesign trigger in the parent workplan at reviewed_plan_commit remains binding.
---

# MLFF target-size optimizer normalization/objective-weight rework — final Software Design closure

## 0. Final Design verdict

**PASS / implementation-ready.**

Software Design completed the final closure review of
`workplans/active/MLFF_TARGET_SIZE_OPTIMIZER_NORMALIZATION_AND_OBJECTIVE_WEIGHT_REWORK_WORKPLAN.md`
at commit `8e198a196602f62386c5405d2e4fffe4dcb52975` under Protocol 5.15.0.

The reviewed implementation remains **NO-PASS** until the parent workplan's repair and acceptance obligations are implemented and pass. This amendment closes **Design**, not Implementation.

No Frozen scientific or high-level architectural decision needs to change. Revision 6 correctly identifies the remaining target-size/P5 contradictions as Tier-2 ownership and validation defects. The final review found two handoff gaps that must be closed before implementation can safely execute Revision 6:

1. destructive cleanup of unaccepted first-rung materialization must distinguish **stale scratch from a workspace currently owned by another live writer**; and
2. fail-closed canonicalization must close the **bounded family of configuration/policy resolvers reworked by this plan**, not only the shared `[training]` optimizer resolver.

The repairs remain reductions/alterations of existing owners. Do not introduce a second scientific authority, compatibility registry, migration database, restart state machine, warning lifecycle, or parallel policy hierarchy.

The parent workplan plus this amendment is the snapshot-complete current implementation handoff. Earlier review conversation and superseded revisions are not needed for implementation.

---

## 1. Final authority classification

### Tier 1A — product/scientific invariants

All Tier-1 invariants in the parent workplan remain unchanged, including:

- `N` / exact `T_N = pi_train[:N]` is the sole target-data-cardinality independent variable;
- configured paired-seed screening, exact fidelity boundaries, target-force-RMSE ranking, practical-equivalence preference for smaller `N`, and practical-ceiling `SELECTED` warning semantics remain unchanged;
- one continuous scientific trajectory per `(N, optimizer_seed)` spans `n1 -> n2 -> n3`;
- P3 owns authenticated target-size execution/restart evidence, P4 owns current campaign adoption/terminal state, and P5 owns CV plus fresh final production;
- global objective coefficients, configuration weights, and local property availability/modifier weights remain separate semantic layers;
- historical evidence is never silently reinterpreted under corrected semantics;
- full production/GPU qualification remains deferred and is not a substitute for functional acceptance.

### Tier 1B — Frozen architecture

The parent workplan's P1 -> P5 authority graph, target-size optimizer-normalization mathematics, immutable accepted-evidence model, exact P5 method-digest authorization, dependency-native weighted MACE loss family, and fresh-final-production rule remain Frozen.

One additional clarification is Frozen for the repair because it follows directly from the existing P3 durability model:

```text
accepted logical-cell evidence
    -> durable scientific/restart authority

unaccepted first-rung attempt workspace
    -> execution-local scratch only
```

**Process liveness is not scientific identity.** Any mechanism used only to prevent two live writers from destructively sharing the same attempt workspace is execution-only and must not enter target-size scientific digests, P2/P3 scientific identity, or historical compatibility semantics.

### Tier 2 — delegated realization

Exact helper placement, cleanup factoring, lock/ownership primitive, strict-validation helper shape, test fixture organization, and conditional spelling of inert `ema_decay` remain delegated. Equivalent simpler realizations are allowed when the Tier-1/Frozen contract and acceptance boundaries below are preserved.

---

## 2. Final closure addition A — live-writer-safe first-rung scratch reclamation

### 2.1 Concern

Revision 6 correctly classifies a first-rung materialization created before accepted cell completion/progress as attempt-local scratch. However:

```text
no accepted progress
```

does **not** by itself prove:

```text
no other live invocation currently owns this workspace
```

The current campaign-state CAS protects durable state transitions. It is not, by itself, a process-liveness lease for a long-running cell execution. A repair that simply deletes the deterministic materialization directory whenever accepted progress is absent can therefore replace the old create-or-verify collision with a concurrent-writer race: invocation B could delete a materialization while invocation A is training from it.

This would violate the existing P3 ownership/recovery architecture and the storage/concurrency rule that temporary state may be destructively cleaned only when ownership is established.

### 2.2 Required end state

Before destructive cleanup/rematerialization of an unaccepted first-rung workspace, the execution path must establish that the current invocation exclusively owns the logical cell/workspace for the destructive operation and subsequent attempt.

Required behavior:

- **Accepted progress/completion exists:** authenticate/reuse it through existing P3 recovery owners; never delete its parent materialization merely to rerun the cell.
- **No accepted progress and another live writer owns the same logical cell/workspace:** do not delete, overwrite, or independently launch the same cell. The invocation may wait and then re-reconcile, or fail cleanly as already/in-progress, or use an already-existing equivalent single-writer exclusion if the repository proves it supplies this guarantee.
- **No accepted progress and no live writer owns the cell:** prior first-rung materialization/checkpoint artifacts are stale attempt scratch and may be removed/recreated for a fresh `start_epoch=0` attempt.
- **Writer crashes or exits:** the execution-only ownership mechanism must release without requiring scientific-state migration so a later invocation can reclaim stale scratch.
- After accepted cell publication, ordinary immutable/replay authority resumes; the execution-only ownership mechanism may not become a second durability authority.

### 2.3 Simplicity boundary

Prefer the minimum execution-local exclusion already available in the repository. If none exists, a narrow advisory ownership/lock scoped to the logical cell or attempt workspace is acceptable.

Do **not** add:

- a persisted liveness database or lease state machine;
- a new scientific attempt identifier;
- a materialization compatibility registry;
- a mutable latest-materialization pointer;
- a broad cleanup daemon;
- process-liveness meaning to `CampaignStore` scientific/currentness fields or stage-status rows;
- a second restart authority.

Do not hold or introduce a coarse campaign-wide lock across expensive MACE work merely to avoid reasoning about one cell unless implementation proves an existing campaign-wide exclusion already supplies the required semantics with no material loss of the accepted execution architecture.

### 2.4 Acceptance boundary

Exercise the real `select-target-size` / P3 orchestration owner with bounded numerical work below it.

In addition to Revision 6's post-materialization/pre-completion crash test, add a concurrent-writer case:

1. invocation A owns a first-rung cell, publishes its materialization, and pauses before accepted completion/progress;
2. invocation B enters the same current screen and targets the same logical cell;
3. prove B does not delete or mutate A's live workspace and does not launch a duplicate scientific execution for that logical cell;
4. then exercise one completion path (A publishes accepted evidence and B re-reconciles/reuses it) and one crash path (A terminates without accepted evidence, its execution ownership releases, and a later invocation safely reclaims the stale scratch and starts fresh);
5. prove accepted-progress conflict detection and immutable create-or-verify semantics are unchanged.

A fixture may bound or replace expensive MACE numerical computation, but it may not replace the production orchestration, logical-cell ownership decision, P3 persistence/reconciliation, or cleanup decision being accepted.

---

## 3. Final closure addition B — close the rework-owned canonical configuration family

### 3.1 Concern

Revision 6 correctly requires strict validation of `resolve_shared_optimizer_settings()`, but the same rework contains adjacent canonical config-to-policy seams that still pre-coerce input before their policy objects can reject it.

In particular, the target-size optimizer-normalization resolver currently applies `int(...)`/`float(...)` to `reference_target_size`, `reference_learning_rate`, and `reference_ema_decay` before constructing its validated policy. The shared objective/configuration-weight resolvers likewise normalize numeric/boolean fields with Python coercion.

Leaving these in place would reproduce the same defect family immediately after closing the shared `[training]` owner: canonical identity could still be built from a silently reinterpreted user or persisted value.

### 3.2 Bounded family scope

This is **not** a repository-wide configuration cleanup. Close only the user-facing/persisted policy family whose semantics are directly owned or redefined by this workplan:

1. shared optimizer settings used by P5 and the generic optimizer carrier;
2. target-size optimizer-normalization reference policy;
3. `TrainingObjectivePolicy` config/serialization seam;
4. `ConfigurationWeightPolicy` config/serialization seam.

Do not broaden the implementation into unrelated campaign configuration domains merely because similar coercion exists elsewhere.

### 3.3 Required canonical-domain rules

At these owners, validate the input domain **before lossy normalization**. Canonical conversion after validation is allowed.

General rules:

- real-valued scientific fields accept finite real numeric values but **reject booleans and strings**; convert to canonical float only after type/domain validation;
- integer scientific fields require actual integers, **reject booleans**, and do not truncate fractional floats or parse numeric strings;
- boolean policy fields require actual booleans; do not use truthiness to reinterpret strings/numbers;
- collection elements must satisfy their declared element domain rather than being silently string/int-cast from arbitrary objects;
- malformed values fail with the repository's canonical input/serialization error class before method identity, scientific preparation, materialization, or trainer launch.

Required high-risk domains include:

- shared optimizer LR/EMA decay/weight decay/clip gradient: finite real, existing sign/range constraints;
- shared optimizer batch sizes/eval interval: positive integer, not boolean;
- shared optimizer EMA/AMSGrad: actual boolean;
- target-size `reference_target_size`: positive integer, not boolean;
- target-size `reference_learning_rate`: finite real `> 0`, not boolean;
- target-size `reference_ema_decay`: finite real in `(0, 1)`, not boolean;
- global E/F/S objective coefficients: finite nonnegative real, not boolean, with at least one positive as today;
- objective/group-awareness boolean: actual boolean;
- configured focus atomic numbers: positive integer elements, not boolean/fractional/string reinterpretations;
- configuration-weight enable/equalization boolean: actual boolean;
- configuration-weight multipliers/bounds: finite positive real values, not boolean, preserving the existing normalized-mean/bound constraints.

### 3.4 Persisted canonical payloads

For the current versioned policy schemas, deserialization must not convert a malformed persisted type into a valid canonical value before validation. Valid historical/current numeric JSON representations remain readable according to their existing schema contracts; do not add a migration layer or silently reinterpret malformed payloads.

If a genuinely supported older schema intentionally permitted a different representation, preserve it only through its existing explicit compatibility reader and normalize at that boundary. Historical implementation accidents are not a compatibility contract.

### 3.5 Acceptance

Use focused deterministic boundary cases for the named classes above. Because this is a broad parser/normalizer input-space invariant, bounded property-based testing is also appropriate when Hypothesis is available: generate invalid numeric/boolean/integer type classes and prove they fail before identity/execution; generate valid canonical values and prove stable resolve/serialize/deserialize identity. Preserve explicit regressions for any minimized material counterexamples.

Also perform a bounded structural/AST census over these four resolver families for direct pre-validation `int(...)`, `float(...)`, or `bool(...)` coercion of configuration/persisted fields. A focused Semgrep rule is suitable when available; validate any acceptance-critical structural rule against known-positive and known-negative examples. Structural zero findings alone do not replace runtime tests.

The positive parity chain in Revision 6 remains required:

```text
config
 -> canonical policy resolution
 -> identity
 -> executable policy/config
 -> dependency-facing projection
```

---

## 4. Revision 6 repair C remains correct — conditionally inert general EMA decay

Revision 6's EMA-disabled repair is accepted without architectural change:

- general `[training].ema_decay` is not target-size scientific authority;
- when target-size EMA is enabled, the realized normalized effective beta is scientific and strongly authenticated;
- when EMA is disabled, general EMA decay must not enter target-size scientific configuration/currentness;
- prefer omission of `ema_decay` from the candidate config when `ema=false` if pinned MACE accepts that spelling;
- if the dependency requires an inert key, conditionally exclude only that inert value from scientific materialization comparison when EMA is false;
- never globally de-scientize realized target-size beta when EMA is enabled.

The real `n1 -> n2` restart/currentness acceptance matrix in Revision 6 remains mandatory.

---

## 5. Final acceptance refinements

All Revision 6 acceptance remains binding. Add these anti-proxy details.

### 5.1 Pinned-MACE weighted-loss acceptance must distinguish forwarding from dependency defaults

The required MACE 0.3.16 acceptance must use deliberately **non-default and mutually distinguishable** objective coefficients/configuration weights plus at least one missing-property zero-mask case. The fixture must be constructed so omitting mdstats forwarding, using MACE's default force coefficient, duplicating the global coefficient into local weights, or falling back to another loss family would change the observed result and fail the test.

At minimum establish through the real dependency-facing path:

- the instantiated dependency loss family is the accepted weighted energy+force+stress implementation, not `UniversalLoss`;
- mdstats' configured global E/F/S coefficients reach that loss;
- configuration weight and local property masks are consumed at their intended distinct layers;
- a missing property contributes zero through the local mask rather than through a changed global objective;
- a bounded dependency-calculated loss/reduction agrees with an independently derived expected value or equivalent dependency-grounded semantic oracle.

Parser/exported argument equality alone is insufficient for this semantic claim.

### 5.2 Final affected-surface regression

Revision 6's matrix remains the minimum. Add the concurrent first-rung live-writer/reclamation case and the target-size normalization/objective/configuration-weight strict-domain tests to the affected set. Re-derive the final transitive surface after all implementation edits; if it cannot be bounded confidently, run the broader MLFF regression suite.

Required real-MACE acceptance must execute rather than skip. Long production/GPU qualification remains deferred.

---

## 6. Final implementation sequence

### Gate R7-A — canonical policy-domain closure

Close the entire bounded rework-owned configuration family from Section 3 in one coherent stage:

- strict shared optimizer settings and any independently constructible `MaceOptimizerPolicy` domain;
- strict target-size optimizer-normalization reference resolution;
- strict global objective and configuration-weight config/serialization seams;
- focused malformed/non-finite/type negatives plus positive round-trip/parity;
- bounded structural family check;
- stage-local affected regression.

Exit only when malformed values cannot be silently converted into valid current scientific/method identity.

### Gate R7-B — target-size attempt/scientific-identity closure

Treat the target-size leaks as one P3 execution-vs-science family:

- make first-rung scratch reclamation live-writer safe as Section 2 requires;
- reclaim unaccepted stale materialization/checkpoint scratch only under established execution ownership;
- preserve accepted materialization/replay immutability;
- remove/conditionally de-scientize generic EMA decay only when target-size EMA is disabled;
- preserve realized normalized beta as science when EMA is enabled;
- run crash/retry, live-writer race, partial-boundary, continuation, acceleration-replay, P3/P4-currentness, and scientific-drift tests.

Exit only when execution-only/inert values cannot retire valid science in fresh-attempt or accepted-replay states, no live writer can have its workspace destructively reclaimed, and true trajectory changes remain strongly invalidating.

### Gate R7-C — P5 real authorization closure

- retain the canonical shared method and explicit method-recipe cutover;
- exercise the real final-production authorization owner;
- reject historical-method CV acceptance before final trainer/materialization launch;
- admit matching corrected-method acceptance through the same owner;
- rerun affected P5 CV/final currentness/execution/publication regression.

### Gate R7-D — assembled acceptance

On one final assembled candidate after all executable edits:

- run the practical-ceiling P2 -> P5 real-owner integration;
- run the non-default, semantically discriminating pinned-MACE 0.3.16 weighted-loss acceptance from Section 5;
- run the re-derived complete affected regression;
- run repository-required checks;
- update normative documentation only if current behavior/contracts changed, then regenerate derived PDFs after Markdown is final.

Do not substitute long production/GPU qualification for these functional gates.

---

## 7. Final forbidden patterns

All Revision 6 forbidden patterns remain binding. Additionally, do not:

- delete an unaccepted materialization merely because accepted progress is absent without first establishing that no other live writer owns that workspace;
- treat stage status, deterministic campaign attempt identity, PID-file existence, or stale lock-file existence by itself as authoritative scientific or liveness truth;
- introduce a durable lease/liveness registry unless implementation evidence proves the existing execution architecture cannot safely distinguish live ownership from stale scratch, in which case reopen only that bounded P3 attempt-ownership design surface;
- close `[training]` strict validation while leaving the plan-owned target-size normalization/objective/configuration-weight resolvers free to silently coerce the same malformed type classes;
- weaken current schema integrity by coercing malformed persisted policy payloads into valid current records;
- count MACE parser/config equality as proof of weighted-loss semantics when the real dependency loss path was never exercised.

---

## 8. Reopen Design only on genuine evidence

In addition to Revision 6 triggers, reopen only the affected design surface if implementation proves one of these assumptions false:

1. safe stale-scratch reclamation cannot be achieved with existing or ephemeral execution-local ownership and instead requires persistent lease/liveness architecture;
2. legitimate accepted P3 evidence can reference a first-rung materialization before logical-cell acceptance in a way that makes its cleanup unsafe;
3. a supported configuration/schema contract intentionally relies on the lossy coercions forbidden in Section 3 and cannot be preserved through an explicit compatibility boundary;
4. pinned MACE semantics require a materially different loss/weight ownership architecture than the accepted dependency-native path.

Do not reopen because a current helper shape, fixture, or lock API is inconvenient.

---

## 9. Design closure criteria and handoff

The plan is ready for Implementation because the remaining work now has:

- a complete Tier-1/Frozen boundary;
- explicit treatment of accepted evidence versus unaccepted attempt scratch;
- live-writer-safe destructive-cleanup semantics;
- one bounded canonical configuration-validation family;
- conditionally correct target-size EMA-decay identity;
- exact P5 historical-method authorization acceptance;
- proxy-proof pinned-MACE loss semantics;
- coherent stage-local and final affected regression requirements;
- explicit simplicity constraints and genuine Design-reopen triggers.

There is no unresolved architecture decision that Implementation must invent before beginning.

**Software Design final verdict: PASS / implementation-ready.**
