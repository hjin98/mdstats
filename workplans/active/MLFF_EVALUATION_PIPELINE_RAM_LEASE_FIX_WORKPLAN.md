---
kind: implementation-workplan
workplan_id: MLFF-EVAL-PIPELINE-RAM-LEASE-FIX
protocol_version: 5.8.0
---

# MLFF Evaluation Pipeline RAM Lease Fix Workplan

## Current status

**REWORK REQUIRED after post-implementation Software Design review.**

Implementation commit `6435898792d1f585157654e653781c0dba150667` correctly established the core launch-local RAM lease architecture, but independent review found one blocking forward-progress defect plus several acceptance gaps. This revision preserves the accepted architecture and narrows rework to the affected scheduler/backpressure and validation surfaces.

The reviewed implementation must not be treated as closed until the rework gates below pass on the assembled candidate.

## Objective and protected concerns

Repair the deterministic staged-evaluation resource-admission deadlock introduced by the PERF1 nested inference topology without weakening bounded-memory execution, static-inference optimization, target-size scientific behavior, or the one-outer-owner evaluation architecture.

The original production failure is not a TARGET-SIZE-V5 ranking/checkpoint defect. In `_run_staged_evaluation_tasks(...)`, evaluation intentionally collapses the outer inference scheduler to one owner while assigning that owner an inner `joint_model_jobs` ceiling derived from the pre-collapse concurrency plan. Before this work, the staged byte ledger treated that theoretical ceiling as mandatory working-memory preallocation. Under the reported geometry, the global RAM budget is about 37.2 GiB, the automatic staged-pipeline budget is about 18.6 GiB, the default estimate is 4 GiB/job, and the theoretical joint ceiling is 8 jobs. A fixed 32 GiB inference reservation therefore cannot fit.

The reviewed implementation correctly changed inference admission to descend from the theoretical job ceiling to the largest currently admissible launch-local width and propagated a scoped RAM/job lease into nested static inference. The remaining blocker is earlier in the producer path: minimum inference headroom is protected only after `ready_inference` is already non-empty. With multiple preparation workers, concurrent unclassified preparations can consume the whole ledger before the first inference-ready result is observed, manufacturing an avoidable no-progress state.

Protected concerns:

- Preserve exactly one outer evaluation inference owner; do not restore parallel outer checkpoint/model owners as a workaround.
- Preserve the existing joint static-inference batch/model-shell optimizer and its RAM/VRAM/OOM learning.
- Preserve the global RAM policy and stricter staged-pipeline RAM sub-budget; do not widen or disable either bound.
- Preserve real retained prepared/finalize/shared-residency accounting and bounded pipeline backpressure.
- Preserve preparation -> inference -> finalization overlap whenever resources genuinely permit it.
- Preserve cache-only bypass and restart/reuse behavior.
- Preserve target-size ranking, target/replay semantics, seed policy, screen/production horizons, checkpoint authority, metrics, numerical/scientific policies, data identity, and persisted campaign authority.
- Preserve dynamics staged-pipeline behavior except where the shared scheduler must enforce the same forward-progress/resource truth more correctly.
- Full long-running production GPU qualification remains separate from functional acceptance and is deferred to FINAL-GPU1; bounded CUDA-path regression/smoke coverage remains required only if affected.

## Engineering envelope and product design

### 1. Single RAM owner and forward-progress invariant

The staged pipeline owns its RAM sub-budget. Nested static inference consumes an explicit runtime lease from that owner and must never independently assume that the whole process-global RAM budget is available.

For every nonterminal scheduler state that contains work which may still require inference, the scheduler must preserve a path to at least one minimum runnable inference operation. Once inference-ready work exists, exactly one of the following must be true:

1. an admissible inference owner can launch;
2. an active owned operation exists whose completion can release the blocking resource while the scheduler waits; or
3. the scheduler terminates with a specific causal resource-admission error representing a genuinely irreducible state.

The scheduler itself must not create case (3) by over-admitting earlier preparation. A known byte-ledger/resource block must never collapse into the generic pipeline-stall invariant error.

### 2. Exact RAM-lease coordinate

The **outer inference lease** is the incremental RAM envelope available to the inference stage inside the already-accounted staged pipeline. It covers the inference working set owned by the staged inference reservation, including incremental private-provider-pool growth and inference execution/transient memory.

It does **not** include:

- shared/base runtime residency already charged once as staged shared residency;
- prepared payload bytes charged separately by the ledger;
- finalize payload/working reservations charged separately; or
- other concurrently owned stage reservations already present in the ledger.

The existing static executor distinguishes private-provider pool residency from the caller-owned slot-zero/base provider. Preserve that coordinate. Do not re-charge the base provider merely to satisfy this repair.

The existing automatic inference reservation remains conservative. Do not introduce a new public memory decomposition unless a stated redesign trigger fires.

### 3. Joint-model width remains a ceiling

For evaluation, pre-collapse `joint_model_jobs` remains the theoretical inner concurrency ceiling, not mandatory preallocation.

For automatic inference working-memory accounting, choose the largest launch-local width `J >= 1` from the theoretical ceiling downward whose existing inference reservation policy fits the current staged ledger:

```text
for J = theoretical_joint_cap ... 1:
    reservation(J) = existing inference working-reservation policy
                     with automatic default = estimated_worker_bytes * J
    choose first J admitted by the current ledger
```

A positive explicit `evaluation_inference_working_memory_mib` retains its established meaning as a **total inference-stage working-memory override**. It is not reinterpreted per model. If that override makes outer reservation independent of `J`, the nested runtime may still choose a smaller inner operating point from provider/transient evidence; the outer RAM lease remains a hard cap and theoretical `J` remains only an upper bound.

### 4. Nested static-inference authority consumes the lease

The assembled prediction path must bind nested `StaticInferenceRuntimeAuthority` to the launch-local lease while retaining live global RAM/VRAM re-clamping and OOM learning:

```text
maximum_concurrent_model_jobs <= outer leased/candidate J ceiling
live incremental RAM allowance <= min(current safe process-global allowance,
                                      outer inference lease RAM)
```

VRAM remains governed by existing live VRAM authority; this RAM repair does not introduce a staged VRAM lease.

The lease is ephemeral orchestration/runtime state only. It must not change scientific identity, checkpoint/cache identity, serialized campaign state, or static-runtime-profile compatibility identity.

Compatible persisted runtime-profile evidence remains reusable, but **every invocation must re-clamp the reused evidence to the current leased J and RAM envelope before selection or execution**. Evidence produced under a larger previous cap may remain stored but must be ineligible while outside the current lease.

### 5. Prospective progress-headroom reservation — REVIEW1 correction

The prior wording protected minimum inference headroom only once `ready_inference` existed. That is insufficient because `requires_inference(prepared)` is normally known only after preparation completes.

The scheduler must therefore protect one **minimum inference progress envelope prospectively** while work remains unclassified or known inference-requiring and no actual inference reservation already owns that envelope.

Frozen behavior:

- Before launching potentially inference-requiring/unclassified preparation, the staged ledger must leave or explicitly reserve at least `minimum_inference_reservation` for one future inference owner.
- Unclassified prepared work is conservatively treated as potentially inference-requiring until the production `requires_inference(prepared)` decision proves it cache-only.
- Concurrent preparation is allowed only when the sum of currently owned staged reservations/retained payloads, the proposed preparation reservation, and the protected progress envelope fits the pipeline budget.
- A cache-only result may bypass inference and proceed toward finalization; if all remaining work is authoritatively cache-only, the unused inference progress envelope may be released.
- When an inference owner launches, the protected headroom must be **transferred/consumed into the real inference reservation without double-counting**. The scheduler must not book both a permanent guard and the same bytes again as inference working memory.
- When an inference owner is active, its real inference reservation is the progress envelope; an additional synthetic minimum guard is not required for the same owner.
- Completed or active preparation may delay inference only when that operation still owns resources and can genuinely release enough memory. Once no such releaser exists, the state must either launch inference or fail causally.
- The mechanism may be a synthetic ledger reservation, equivalent admission invariant, or another scheduler-local realization, but it must remain explicit enough that the multi-prepare invariant can be tested through the real scheduler.

This policy prevents the reviewed failure geometry:

```text
pipeline budget       = 2 MiB
prepare reservation   = 1 MiB
minimum inference J=1 = 1 MiB
prepare workers        = 2
```

Without prospective protection, both preparations may consume 2 MiB before either result becomes inference-ready. With the corrected invariant, the second potentially inference-requiring preparation cannot consume the only remaining 1 MiB progress envelope.

Do not solve this by globally forcing preparation concurrency to one. Serializing preparation is acceptable only when the live RAM equation actually requires it; otherwise existing prepare/infer/finalize overlap and multi-prepare throughput remain protected behavior.

### 6. Causal admission diagnostics

Distinguish at least:

- adaptive/controller admission blocked;
- staged byte-ledger/RAM admission blocked, including minimum J=1 unsatisfied; and
- true unexpected scheduler invariant stall.

A RAM-admission error must expose enough correctly named values to diagnose the failed equation without source inspection:

- queued/ready count;
- pipeline budget;
- current total ledger-owned bytes;
- relevant retained-payload bytes and/or stage reservations when available;
- minimum required inference reservation;
- relevant model-job ceiling/selected width when known.

Do not label aggregate `ledger.total_bytes` as merely `retained` if it includes working/stage reservations. Diagnostic names must reflect the actual accounting coordinate. Do not print secrets or unbounded payload detail.

### 7. Lease and reservation lifecycle

A launch-local lease and its ledger reservation must be released exactly once on every terminal path owned by that launch: success, stage failure, cancellation, `KeyboardInterrupt`, bounded OOM terminal failure, or other propagated exception.

Cache-only bypass must not acquire an inference lease. Task-local/context-local lease state must not survive into later work.

Lifecycle acceptance must establish scheduler-owned cleanup, not merely that a completely new scheduler invocation starts with a fresh ledger.

## Implementation obligations

### O1 — Production-geometry reproducer

**Concern:** Existing tiny-memory topology tests historically missed the 4-GiB/job/half-budget contradiction.

**Required end state:** A deterministic bounded test exercises the real `_run_staged_evaluation_tasks()` owner using production-equivalent arithmetic without allocating production-scale RAM.

**Acceptance:** The theoretical J=8 / 4 GiB-per-job / ~18.6 GiB pipeline geometry descends to the widest admissible J and completes with one outer inference owner.

### O2 — Launch-local RAM-aware joint-width admission

**Required end state:** Automatic evaluation admission chooses the largest current-ledger-admissible `J >= 1`; the theoretical joint width remains only an upper bound.

**Preserve:** explicit total-stage inference-memory override semantics; pipeline/global RAM bounds; one outer evaluation owner.

**Acceptance:** largest-safe-J, exact-fit, one-byte/one-unit-over-boundary, J=1 minimum, and outer peak=1 tests through the real scheduler.

### O3 — Nested-runtime lease binding and profile re-clamp

**Required end state:** Nested static inference receives no larger job ceiling or incremental RAM allowance than the outer lease while retaining existing live global RAM/VRAM clamping and OOM learning.

**Profile requirement:** A compatible profile generated under a larger prior cap cannot select or attempt an operating point outside a smaller current outer lease.

**Acceptance:** Exercise the actual `_predict_model_on_atoms` / static-executor path with a compatible prior profile, then invoke under a smaller `InferenceLease`; assert attempted/selected job width and RAM-admitted operating points remain within the current lease. Constructor-field inspection alone is insufficient for the profile-reuse claim.

### O4 — Prospective starvation-proof producer/backpressure policy

**Concern:** REVIEW1 found that `ready_inference`-conditional headroom protection is too late under multiple concurrent preparations.

**Required end state:** Preparation admission cannot consume the minimum future inference envelope before cache/inference classification is known.

**Required consequences:**

- protect one minimum inference envelope prospectively;
- treat unclassified work as potentially inference-requiring;
- transfer the protected envelope into the actual inference reservation without double-counting;
- preserve work-conserving multi-prepare and stage overlap whenever the RAM equation permits;
- preserve cache-only bypass.

**Required regression — must fail on reviewed commit `6435898...`:** run the real staged scheduler with at least two preparation workers and a tight budget where two simultaneous prepares would fill the budget but one prepare plus J=1 inference fits. Use heterogeneous retained payloads and include a cache-only -> uncached ordering case. The repaired candidate must make forward progress without manufacturing a false irreducible-RAM error.

A test that leaves `parallel_evaluation_prepare_jobs=1` does **not** close this obligation.

### O5 — Genuine irreducible admission error and truthful diagnostics

**Required end state:** If the minimum J=1 inference plus already-required retained/owned state genuinely cannot fit and no active owner can release sufficient memory, fail immediately with a causal `CampaignCliError`; retain the generic pipeline stall only for an actual invariant/programming failure.

**Acceptance:**

- explicit genuine-J=1-impossible case;
- separate avoidable multi-prepare case that must now progress;
- assertions on diagnostically correct budget/ledger/minimum-reservation terminology and values.

### O6 — Lease cleanup and cancellation correctness

**Required end state:** Every acquired inference lease/reservation is released exactly once and nested runtime state clears on every terminal path.

**Acceptance must cover scheduler ownership directly:**

- success where later work in the **same scheduler invocation** can reuse released capacity;
- inference/stage exception;
- bounded OOM terminal failure path where applicable to the touched runtime;
- sibling failure/cancellation;
- `KeyboardInterrupt`;
- cache-only bypass proves no inference lease was acquired.

Tests may instrument ledger `reserve`/`release` or lease context through call-through observation, but must not replace/reimplement scheduler logic. After the terminal path, observed inference ownership must return to the expected retained baseline and task-local lease state must be clear. Starting a wholly new scheduler invocation alone is insufficient proof of old-ledger cleanup.

### O7 — Scientific, persistence, and identity non-regression

No target-size decision rule, epoch boundary, seed semantics, training/evaluation metric, target/replay membership, checkpoint identity, persisted authority, prediction-cache identity, runtime-profile compatibility identity, or screen/production horizon semantics may change.

**Acceptance:** affected target-size/evaluation regression plus structural diff review for unauthorized identity/schema changes.

### O8 — Shared staged-runner compatibility

Evaluation-specific joint RAM leasing must not accidentally change dynamics job-count/resource semantics. Any shared progress-headroom logic must remain correct for dynamics and authenticated-receipt/cache-only bypass.

**Acceptance:** dynamics overlap, authenticated-receipt bypass, failure cancellation, interruption, low-CPU/serial, and any newly affected multi-prepare shared-runner tests.

### O9 — Authentic assembled cache-only -> uncached target-size/evaluation path

**Concern:** REVIEW1 found lower-level cache-only and uncached tests plus a separate real target-size-owner test, but not the exact assembled transition required by Gate B.

**Required end state:** A bounded authentic target-size/evaluation caller invocation reaches the real staged scheduler with at least one authoritatively cache-only/reused evaluation followed by at least one inference-requiring evaluation, then completes finalization/publication.

**Semantic owner boundary:** the real target-size/evaluation orchestration and real `_run_staged_evaluation_tasks()` must execute. The production cache-bypass decision, scheduler admission/lease decision, and publication/finalization transition may not be patched or reimplemented.

**Allowed doubles:** expensive MACE numerical prediction, accelerator execution, and large datasets may be replaced below that boundary with deterministic bounded fixtures.

**Acceptance:** prove the cached endpoint bypasses inference/lease acquisition, the uncached endpoint obtains the current lease through the real scheduler, and both reach the authentic publication/result path without the old stall.

### O10 — Final regression/check evidence

Repository/project-required checks and the complete affected-surface regression must actually execute on the final assembled candidate. A missing GitHub status by itself does not require CI if equivalent repository-approved local checks exist, but an unexecuted required check is not a pass.

Record enough command/CI result evidence to identify what ran and whether it passed. Do not substitute semantic review or a production run for missing regression/integration coverage.

## Implementation authority

### Frozen

- One outer evaluation inference owner.
- Theoretical joint-model width is an upper bound, not mandatory preallocation.
- The staged pipeline owns its RAM sub-budget; nested static inference consumes a scoped incremental RAM lease.
- Shared/base residency already charged once by the staged ledger is outside the incremental inference lease; private provider-pool growth and inference execution/transient memory are inside it.
- Automatic inference reservation retains existing conservative semantics; explicit inference working-memory overrides remain total-stage overrides.
- No widening/removal of RAM bounds and no deletion of provider/job RAM accounting as a shortcut.
- **One minimum inference progress envelope is protected prospectively before unclassified concurrent preparation can consume it.**
- The protected envelope is transferred into an actual inference reservation without double-counting.
- Forward-progress and causal-resource-failure semantics.
- Runtime-only lease; no scientific/persisted/profile-compatibility identity change.
- Compatible static-inference profiles are re-clamped to the current lease on every invocation.
- Lease/reservation cleanup on every terminal path.
- Full production GPU qualification deferred; bounded functional CUDA checks only if affected.

### Delegated

- Exact helper/data-structure names for the progress guard and lease.
- Whether progress headroom is represented as a synthetic ledger owner, an equivalent explicit admission claim, or another scheduler-local mechanism with identical accounting semantics.
- Exact atomic transfer mechanics from progress guard to actual inference reservation, provided no transient overbooking or double-counting occurs.
- Local refactoring that centralizes duplicated admission arithmetic without expanding public surface.
- Exact diagnostic formatting, provided accounting labels remain truthful and required values are present.

### Reopen only on evidence

Reopen only the affected design surface if implementation evidence proves one of the following:

1. `selected_concurrent_model_jobs` is semantically an exact required width rather than an upper bound in a production consumer.
2. Caller-owned/base-provider residency cannot be separated from incremental private-provider/transient accounting without changing the established static-inference evidence model.
3. The existing explicit inference working-memory override has an authoritative semantic other than total inference-stage working memory.
4. Normal supported automatic configuration makes genuine J=1 execution falsely impossible solely because conservative accounting materially double-counts a component and a decomposition redesign is required.
5. Correct prospective progress protection cannot be represented inside the existing staged-ledger/scheduler ownership model without a public buffering/configuration contract change.
6. The production `requires_inference` classification can be authoritatively known before preparation for all relevant task types; only then may the conservative unclassified-work rule be narrowed without weakening the invariant.

Do not reopen target-size scientific architecture, flexible fidelity, production horizon semantics, or unrelated PERF1 machinery absent independent evidence.

## Expected affected surface

Re-derive from the final diff, but initially expect:

- `mdstats/training_data/_campaign_cli_core.py` — progress-headroom ownership/admission, guard-to-lease transfer, causal diagnostics, cleanup.
- `mdstats/training_data/campaign_execution.py` — only if profile/lease re-clamp requires correction; core lease binding already reviewed as directionally correct.
- `mdstats/training_data/inference_parallel.py` — only if task-local lease lifecycle requires correction; ContextVar transport is already directionally correct.
- `mdstats/training_data/model_features.py` — only if actual static-profile selection/executor admission violates the current lease; no redesign expected.
- `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` — multi-prepare bug reproducer, truthful diagnostics, same-owner cleanup.
- `tests/test_mlff_static_mace_inference.py` — larger-prior-profile -> smaller-current-lease execution test.
- target-size/evaluation topology/integration tests — authentic cache-only -> uncached assembled owner path.
- shared dynamics staged-runner regressions.

Do not modify target-size scientific decision logic or persistence schemas as part of this rework.

## Task-specific acceptance matrix

1. Production geometry: theoretical J=8, ~4 GiB/job, ~18.6 GiB staged budget; largest safe J launches without large allocation.
2. Largest-safe-J exact fit and one-unit-over boundary.
3. One outer evaluation owner remains peak=1 while inner selected cap is propagated.
4. Outer RAM lease hard-bounds nested incremental RAM and model-job width.
5. Compatible runtime profile produced under a larger prior cap is actually re-clamped during execution under a smaller current lease.
6. Cache-only tasks acquire no inference lease and do not contaminate inference calibration/admission.
7. **Two-or-more concurrent preparation workers under a tight budget cannot consume the protected J=1 progress envelope before classification.**
8. Heterogeneous prepared payloads plus cache-only -> uncached ordering make forward progress through the real scheduler.
9. Genuine J=1 impossibility fails causally; avoidable producer-created impossibility does not.
10. Explicit `evaluation_inference_working_memory_mib` retains total-stage semantics.
11. Progress guard and actual inference reservation are never double-counted.
12. Lease/reservation cleanup is demonstrated on success, exception, bounded OOM, sibling cancellation, and `KeyboardInterrupt`, with same-owner/observational evidence rather than only a fresh invocation.
13. Serial/low-CPU and dynamics shared-runner behavior remain valid.
14. Authentic target-size/evaluation caller executes cache-only -> uncached through the real staged scheduler and publication path.
15. Diagnostic fields accurately distinguish aggregate ledger-owned bytes from retained payload bytes/reservations.
16. If CUDA-specific behavior changed, run bounded CUDA-labelled/fake-provider or available non-production accelerator smoke/equivalence checks; no long target-machine qualification.
17. Final assembled affected regression plus repository-required checks execute and pass, or any unavailable required check remains explicitly blocking.

The principal semantic owner remains the real staged evaluation scheduler as invoked by real evaluation/target-size orchestration. Direct helper tests, patched scheduler/ledger decisions, or harness reimplementation cannot close owner-level claims. Call-through instrumentation that observes ownership without replacing production decisions is allowed.

Production qualification remains **deferred**. Long real-data GPU performance/RAM/VRAM qualification remains part of FINAL-GPU1 on the target machine.

## Rework implementation sequence

### Gate R1 — Prospective progress ownership and focused scheduler closure

Repair O4/O5/O6 as one coherent scheduler stage:

- establish prospective minimum inference headroom before unclassified multi-prepare admission;
- transfer that headroom into launch-local inference reservation without double-counting;
- preserve largest-safe-J selection;
- correct RAM diagnostic terminology;
- establish exact reservation/lease cleanup.

Required stage-local evidence before dependent work:

- reviewed-commit-failing multi-prepare reproducer;
- production geometry and J-boundary tests;
- genuine irreducible J=1 test;
- same-owner cleanup/cancellation tests;
- existing staged scheduler and shared dynamics affected regression.

### Gate R2 — Nested profile and assembled target-size/evaluation closure

Close O3 and O9:

- execute compatible larger-cap profile under smaller current lease and prove out-of-lease points cannot be selected/attempted;
- execute authentic cache-only -> uncached target-size/evaluation orchestration through the real staged scheduler and publication path.

Cheap deterministic numerical doubles are allowed only below the frozen semantic-owner boundaries.

### Gate R3 — Final assembled closure

After all executable edits:

1. reconcile every frozen obligation and review finding against the assembled candidate;
2. re-derive the final affected behavioral surface from the final diff;
3. run the complete affected regression set, including target-size/evaluation, static inference, staged scheduler, shared dynamics, and low-resource paths;
4. run repository/project-required checks;
5. account explicitly for any unavailable required check as blocking;
6. perform a final structural review confirming no target-size science, identity, persistence, or configuration-semantics drift.

Only after R1-R3 close may this workplan be marked complete/archived.

## Relationship to active workplans

This workplan repairs a PERF1 staged-evaluation scheduler/resource-authority regression surfaced by target-size screening. It does not supersede `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`; that plan's remaining interruption/restart/automatic-continuation evidence remains independently active. This RAM-lease repair should close before any final-closure scenario that depends on uncached staged evaluation.

The older Repair1 chain remains historical archive material and imposes no active gates.

## Review handoff closure

The post-implementation review preserves the original architecture and reopens only bounded rework:

1. **Blocking implementation nonconformance — prospective forward progress:** headroom protection must begin before concurrent unclassified preparation, not only after `ready_inference` exists.
2. **Acceptance strengthening — lifecycle:** prove scheduler-owned reservation/lease cleanup on terminal paths; a fresh scheduler invocation alone is not proof of old-ledger release.
3. **Acceptance strengthening — profile reuse:** exercise a compatible larger-cap profile under a smaller current outer lease through the actual static execution path.
4. **Acceptance strengthening — assembled integration:** exercise authentic cache-only -> uncached target-size/evaluation orchestration through the real staged scheduler and publication path.
5. **Diagnostic correction:** report ledger accounting using truthful retained/reserved/aggregate terminology.
6. **Final evidence:** execute and record the complete affected regression/repository checks on the final candidate.

No evidence currently requires reopening one-outer-owner evaluation, the launch-local lease coordinate, nested static-inference architecture, target-size science, fidelity/horizon semantics, or persistence identity. The rework is therefore a localized implementation correction plus acceptance closure, not an architectural redesign.
