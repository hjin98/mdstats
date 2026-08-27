---
kind: implementation-workplan
workplan_id: MLFF-EVAL-PIPELINE-RAM-LEASE-FIX
protocol_version: 5.8.0
---

# MLFF Evaluation Pipeline RAM Lease Fix Workplan

## Objective and protected concerns

Repair the deterministic staged-evaluation resource-admission deadlock introduced by the PERF1 nested inference topology without weakening bounded-memory execution, static-inference optimization, target-size scientific behavior, or the one-outer-owner evaluation architecture.

The observed failure is not a TARGET-SIZE-V5 ranking/checkpoint defect. In `_run_staged_evaluation_tasks(...)`, evaluation intentionally collapses the outer inference scheduler to one owner while assigning that owner an inner `joint_model_jobs` ceiling derived from the pre-collapse concurrency plan. The staged byte ledger then reserves automatic inference working memory as `estimated_worker_bytes * joint_model_jobs`. Under the reported production geometry, the global RAM budget is about 37.2 GiB, the automatic staged-pipeline budget is about 18.6 GiB, the default estimate is 4 GiB/job, and the inferred joint ceiling is 8 jobs. The resulting 32 GiB inference reservation can never fit. `launch_inference()` silently leaves ready work queued when the byte ledger refuses that reservation; with no active future capable of releasing resources, the watchdog reports only the secondary generic error `Evaluation pipeline stalled with queued work but no active stage.`

Commit `514d70a57a3c954bd777c99eee314019107f9ef2` introduced the coupled one-outer-owner / inner-joint-job topology and widened inference reservation. Existing staged-evaluation tests validate the topology with tiny artificial RAM estimates and therefore do not exercise this production-scale resource composition.

Protected concerns:

- Preserve exactly one outer evaluation inference owner; do not restore parallel outer checkpoint/model owners as a workaround.
- Preserve the existing joint static-inference batch/model-shell optimizer and its RAM/VRAM/OOM learning.
- Preserve the global RAM policy and the stricter staged-pipeline RAM sub-budget; do not fix the defect by widening or disabling either bound.
- Preserve real retained prepared/finalize/shared-residency accounting and bounded pipeline backpressure.
- Preserve preparation -> inference -> finalization overlap whenever resources permit it.
- Preserve cache-only bypass and restart/reuse behavior.
- Preserve target-size ranking, target/replay semantics, seed policy, screen/production horizons, checkpoint authority, metrics, numerical/scientific policies, data identity, and persisted campaign authority.
- Preserve dynamics staged-pipeline behavior except where shared scheduler diagnostics/backpressure must become more correct.
- Full long-running production GPU qualification remains separate from functional acceptance and is deferred to FINAL-GPU1; bounded CUDA-path regression/smoke coverage remains required if touched.

## Engineering envelope and product design

### Single resource owner and forward-progress invariant

The staged pipeline is the owner of its RAM sub-budget. Nested static inference is a consumer of an explicit runtime lease from that owner and must not independently assume that the whole process-global RAM budget is available to it.

For any nonterminal scheduler state with inference-ready work, exactly one of the following must be true:

1. an admissible inference owner can launch;
2. an active owned operation exists that can release the blocking resource and the scheduler is waiting for it; or
3. the scheduler terminates with a specific causal resource-admission error.

A known byte-ledger/resource block must never collapse into the generic pipeline-stall invariant error.

### Exact RAM-lease coordinate

Freeze one coordinate so outer and nested authorities cannot double-count or omit the same memory.

The **outer inference lease** is the incremental RAM envelope available to the inference stage *inside* the already-accounted staged pipeline. It covers the inference working set that the staged inference reservation is intended to own, including incremental private-provider-pool growth and inference execution/transient memory. It does **not** include:

- shared/base runtime residency already charged once by the staged ledger as shared residency;
- prepared payload bytes already charged separately by the ledger;
- finalize payload/working reservations charged separately; or
- other concurrently owned stage reservations already present in the ledger.

The existing static executor already reports private-provider pool residency separately from the caller-owned slot-zero/base provider. That incremental provider coordinate is the one nested inference must constrain against the outer lease. Do not reinterpret the caller-owned base provider as an additional private-provider charge merely to satisfy this repair.

The existing automatic inference reservation remains conservative. This work does **not** require decomposing the current estimate into a new `(J-1) * provider + transient` formula or introducing a new public memory model. Such a decomposition is a redesign trigger only if implementation evidence proves the existing conservative estimate prevents valid `J=1` operation under normal supported configuration.

### Joint-model width is a ceiling, not an unconditional allocation

For evaluation, the pre-collapse `joint_model_jobs` value remains the theoretical inner concurrency ceiling. It must no longer imply that the pipeline must reserve the maximum theoretical width before any inference may start.

For automatic inference working-memory accounting, resolve a launch-local candidate width `J` from the theoretical ceiling downward and select the largest `J >= 1` whose inference reservation is admissible against the current staged ledger. Use the existing working-reservation semantics rather than inventing a parallel memory policy. Conceptually:

```text
for J = theoretical_joint_cap ... 1:
    reservation(J) = existing inference working-reservation policy
                     with automatic default = estimated_worker_bytes * J
    choose first J for which current ledger can admit reservation(J)
```

With the reported geometry this converts an impossible 8-job/32-GiB reservation into the largest width that can coexist with the current retained pipeline state (approximately J=4 before other retained payloads are considered), rather than failing to launch at all.

A positive explicit `evaluation_inference_working_memory_mib` remains an authoritative total inference-stage working-memory override under its existing semantics. The repair must not silently reinterpret it as a per-model value. When that override makes reservation independent of `J`, the nested runtime authority may still select a smaller admissible inner operating point from its own provider/transient evidence; the outer lease remains a hard RAM cap and the theoretical `J` remains only an upper bound.

### Nested static-inference authority consumes the lease

The assembled prediction path currently creates a `StaticInferenceRuntimeAuthority` from freshly detected process-global resources. Under staged evaluation, that authority must also consume the launch-local outer lease.

Required nested bounds:

```text
maximum_concurrent_model_jobs <= outer leased/candidate J ceiling
live incremental RAM allowance <= min(current safe process-global allowance,
                                      outer inference lease RAM)
```

VRAM remains governed by the existing live VRAM authority unless a later design explicitly introduces a staged VRAM sub-lease; this RAM repair must not invent one unnecessarily.

The lease is orchestration/runtime state only. It must not alter scientific identity, checkpoint/cache identity, serialized campaign state, or static-inference runtime-profile compatibility identity. Compatible persisted runtime-profile evidence may be reused, but every invocation must re-clamp/filter that evidence against the current leased `J` and RAM allowance before selection. A compatible profile must never bypass a smaller current outer lease.

Prefer an existing worker/task-local inference execution context or an equivalent scoped mechanism to transport the lease. Do not add process-global mutable lease state that can leak across concurrent tasks.

### Progress-safe backpressure

Prepared-buffer admission must not create an avoidable state in which inference-ready work exists but all remaining pipeline RAM has been consumed by additional preparation.

Implementation must preserve enough headroom for the minimum runnable inference operation once inference-ready work exists, or equivalently stop/sequence further preparation so the existing ready inference can acquire a valid lease. Cache-only prepared work should continue to bypass inference and may be finalized to release retained memory. If the retained payload of the first uncached ready item plus a minimum J=1 inference reservation is genuinely impossible under the configured pipeline budget, fail immediately and causally rather than waiting for a resource release that cannot occur.

The exact internal backpressure mechanism is delegated; the forward-progress invariant is frozen.

### Causal admission diagnostics

Distinguish at least:

- adaptive/controller admission blocked;
- staged byte-ledger/RAM admission blocked, including minimum J=1 unsatisfied; and
- true unexpected scheduler invariant stall.

A RAM admission error must expose enough values to diagnose the failed equation without requiring source inspection: queued/ready count, pipeline budget, currently retained/reserved bytes, minimum required inference reservation, and relevant model-job ceiling/selected width when known. Do not print secrets or unbounded payload detail.

### Lease lifecycle

A launch-local lease and its ledger reservation must be released exactly once on every terminal path owned by that launch: success, inference/finalize failure, cancellation, `KeyboardInterrupt`, bounded OOM terminal failure, or other propagated exception. Cache-only bypass must not acquire an inference lease. Stale runtime lease state must not survive into a later task.

## Implementation obligations

### O1 — Production-geometry bug reproducer

**Concern / rationale:** Existing topology tests use 1 MiB/job and cannot expose the 4-GiB-per-job/half-pipeline-budget contradiction.

**Required end state:** A deterministic bounded test reproduces the resource arithmetic of the reported failure without allocating production-scale RAM.

**Required consequences / constraints:** Exercise the real `_run_staged_evaluation_tasks()` scheduler owner. Do not patch the ledger/J resolver/launch decision to manufacture the expected result.

**Acceptance evidence:** The pre-fix shape would strand ready inference; the repaired scheduler launches at a smaller admissible width and completes without the old generic stall.

### O2 — Launch-local RAM-aware joint-width admission

**Concern / rationale:** Theoretical inner concurrency is currently treated as a mandatory reservation.

**Required end state:** Automatic evaluation admission chooses the largest current-ledger-admissible `J >= 1`; one outer owner remains authoritative.

**Required consequences / constraints:** Preserve explicit working-memory override semantics. Do not remove the multiplied automatic accounting, remove the pipeline budget, or increase the budget solely to make the old maximum fit.

**Acceptance evidence:** Boundary tests for largest safe J, exact fit, one-byte/one-unit over boundary, J=1 minimum, and one-outer-owner peak concurrency.

### O3 — Nested-runtime lease binding

**Concern / rationale:** The nested static runtime currently rediscovers a larger global RAM allowance and can therefore disagree with the staged owner.

**Required end state:** The nested `StaticInferenceRuntimeAuthority` receives a maximum model-job ceiling and incremental RAM allowance no greater than the outer lease while retaining existing live global RAM/VRAM re-clamping and OOM learning.

**Required consequences / constraints:** The lease is runtime-only; no scientific/configuration/cache/checkpoint/runtime-profile schema identity churn. Existing compatible profile evidence above the current lease remains stored evidence but cannot be selected while outside the current cap.

**Acceptance evidence:** Tests prove selected/attempted inner jobs and RAM admission never exceed the outer lease, including a reused compatible profile created under a larger prior cap.

### O4 — Starvation-proof producer/backpressure policy

**Concern / rationale:** Even a valid J=1 can be stranded if preparation fills the ledger first.

**Required end state:** Once inference-ready work exists, additional preparation cannot consume the RAM required for forward progress unless an active operation can first release sufficient bytes.

**Required consequences / constraints:** Keep pipeline buffers bounded and work-conserving. Preserve prepare/infer/finalize overlap when headroom exists. Preserve cache-only fast path.

**Acceptance evidence:** Multi-prepare tests with heterogeneous retained payloads and cache-only -> uncached ordering show forward progress and no avoidable no-future deadlock.

### O5 — Fail-fast irreducible resource error and diagnostics

**Concern / rationale:** The generic stall masks a deterministic RAM equation failure.

**Required end state:** If minimum J=1 plus already-required retained state cannot fit and no active owner can release memory, terminate immediately with a specific RAM-admission `CampaignCliError` containing the causal budget/reservation facts.

**Required consequences / constraints:** Retain the generic stall only for an actual scheduler invariant/programming failure.

**Acceptance evidence:** Explicit impossible-admission test asserts causal class/message values; separate invariant test (if an existing one exists) remains distinct.

### O6 — Lease cleanup and cancellation correctness

**Concern / rationale:** Scoped reservations must not leak after exceptions or cancellation.

**Required end state:** Every acquired inference lease is released exactly once and nested runtime state is cleared on all terminal paths.

**Required consequences / constraints:** Preserve existing sibling-failure, external-process cancellation, and `KeyboardInterrupt` semantics.

**Acceptance evidence:** Failure/cancellation tests assert ledger/resource state returns to the expected retained baseline and a subsequent task can be admitted; existing cancellation regressions remain green.

### O7 — Scientific and persistence non-regression

**Concern / rationale:** This defect is orchestration/resource policy, not target-size science or campaign identity.

**Required end state:** No target-size decision rule, epoch boundary, seed semantics, training/evaluation metric, target/replay membership, checkpoint identity, persisted authority, prediction cache identity, or screen/production horizon semantics change.

**Acceptance evidence:** Affected target-size/evaluation regression and assembled bounded integration through the real caller path; structural diff review confirms no unauthorized identity/schema changes.

### O8 — Shared staged-runner compatibility

**Concern / rationale:** `_run_staged_evaluation_tasks()` also serves dynamics.

**Required end state:** Evaluation-specific joint RAM leasing does not accidentally change dynamics job-count/resource semantics. Shared diagnostic/backpressure improvements remain valid for both phases.

**Acceptance evidence:** Existing dynamics overlap, authenticated-receipt bypass, failure cancellation, and interruption regressions plus any newly affected shared scheduler tests.

## Implementation authority

### Frozen

- One outer evaluation inference owner.
- Theoretical joint-model width is an upper bound, not mandatory preallocation.
- The staged pipeline owns its RAM sub-budget; nested static inference consumes a scoped incremental RAM lease from it.
- Shared/base residency already charged once by the staged ledger is outside the incremental inference lease; private provider-pool growth and inference execution/transient memory are inside it.
- Automatic inference reservation uses existing conservative working-memory semantics; explicit inference working-memory overrides retain their current total-stage meaning.
- No widening/removal of RAM bounds and no deletion of provider/job RAM accounting as a shortcut.
- Forward-progress invariant and causal resource failure semantics.
- Runtime-only lease; no scientific/persisted/profile-compatibility identity change.
- Compatible static-inference profiles are always re-clamped to the current lease.
- Lease/reservation cleanup on every terminal path.
- Full production GPU qualification deferred; functional CUDA-path checks only as affected.

### Delegated

- Exact helper/function names and local data structure representing an inference lease.
- Whether the lease is transported by extending an existing context manager/context variable, an execution-plan runtime-only wrapper, or another task-scoped mechanism with equivalent ownership and cleanup semantics.
- Exact descending-search implementation and diagnostic formatting.
- Exact backpressure implementation, provided it enforces the frozen progress invariant without unbounded buffering or unnecessary serialization.
- Refactoring of local scheduler helpers when it reduces duplicated admission arithmetic without expanding public surface.

### Reopen only on evidence

Reopen only the affected design surface if implementation evidence proves one of the following:

1. `selected_concurrent_model_jobs` is semantically an exact required width in a production consumer rather than an upper bound, so safe down-clamping would change required semantics.
2. Caller-owned/base-provider residency cannot be separated from incremental private-provider/transient accounting without changing the established static-inference evidence model.
3. The existing explicit inference working-memory override has a different authoritative semantic than total inference-stage working memory.
4. Normal supported automatic configuration can make a genuine J=1 execution falsely impossible solely because the current conservative estimate double-counts a material component, requiring a justified decomposition redesign.
5. Correct progress-safe backpressure requires a public pipeline-buffering/configuration contract change rather than an internal scheduler correction.

Do not reopen target-size scientific architecture, flexible fidelity, production horizon semantics, or unrelated PERF1 optimization machinery absent independent evidence.

## Affected surface and task-specific acceptance

Initially expected executable surface:

- `mdstats/training_data/_campaign_cli_core.py` — staged byte-ledger admission, launch-local J/lease selection, forward-progress/backpressure, causal blocked-state diagnostics, cleanup.
- `mdstats/training_data/campaign_execution.py` — nested static-inference runtime authority consumes the scoped outer RAM/J lease.
- `mdstats/training_data/inference_parallel.py` — only if the established task/worker context is the clean transport owner for the runtime-only lease.
- `mdstats/training_data/model_features.py` — expected to need no architecture redesign; modify only if required to correctly consume/re-clamp the bounded runtime authority.
- `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` — direct real-owner resource/progress reproductions.
- Existing static-inference runtime-authority/profile tests and target-size/evaluation integration tests affected by the final diff.
- Shared dynamics staged-runner regressions.

Task-specific acceptance matrix:

1. Production-geometry arithmetic: theoretical J=8, about 4 GiB/job, about 18.6 GiB staged budget; no real large allocation; largest safe automatic J launches.
2. Largest-safe-J and exact boundary arithmetic.
3. One outer evaluation owner remains peak=1 while inner selected cap is propagated.
4. Outer RAM lease is the hard nested incremental cap.
5. Compatible cached static-inference profile produced under a larger previous cap is re-clamped and cannot select an out-of-lease point.
6. Cache-only tasks bypass inference; cache-only predecessors followed by uncached work do not contaminate calibration/admission or deadlock.
7. Multiple prepared tasks cannot starve a ready inference task of minimum progress headroom.
8. Genuine J=1 impossibility fails immediately with explicit RAM-admission diagnostics, not generic stall.
9. Positive explicit `evaluation_inference_working_memory_mib` retains current semantics.
10. Lease is released after success, stage exception, bounded OOM terminal path, sibling cancellation, and `KeyboardInterrupt`; subsequent work can proceed.
11. Serial/low-CPU paths and dynamics shared-runner behavior remain valid.
12. Bounded CPU integration through the real target-size/evaluation caller reaches the real staged scheduler and publication path. Expensive MACE numerical prediction may be replaced below that boundary, but the scheduler, admission decision, cache-bypass decision, and caller binding may not be mocked/reimplemented.
13. If CUDA-specific lease propagation is touched, run bounded CUDA-labelled/fake-provider policy tests and available non-production accelerator smoke/equivalence checks. Do not require long target-machine production qualification.

The semantic owner for the principal acceptance claim is the real staged evaluation scheduler as invoked by the real evaluation/target-size orchestration. Test doubles are allowed below that boundary for expensive MACE/GPU numerical execution. Evidence that directly calls a J-selection helper while bypassing `_run_staged_evaluation_tasks()`, or patches the scheduler/ledger to return the desired decision, cannot close the assembled owner claim.

Repository/project-required checks remain mandatory. Re-derive the affected surface from the final diff; if impact through shared resource/controller code cannot be bounded confidently, run the broader available regression suite.

Production qualification: **deferred**. This repair requires bounded functional/resource-geometry and affected CUDA-path validation only. Long real-data GPU performance/RAM/VRAM qualification remains part of FINAL-GPU1 on the target machine.

## Implementation sequence and redesign risks

### Gate A — Resource-owner repair and focused closure

Implement the scoped lease/J admission, nested authority binding, progress-safe backpressure, diagnostics, and exact cleanup as one coherent scheduler/resource behavior change. Add the production-geometry reproducer and focused boundary/profile/cleanup tests first or alongside the change. Close focused tests plus staged scheduler, static-runtime authority/profile, and shared dynamics affected regression before dependent integration work.

### Gate B — Assembled evaluation/target-size integration

Exercise a bounded authentic caller path with the real staged scheduler: representative cache-only completed evaluation(s) followed by an inference-requiring evaluation, then successful finalization/publication. Cheap deterministic data and fake numerical MACE execution are allowed below the scheduler/caller boundary. Verify the old stall is absent and the current lease is honored end-to-end.

### Gate C — Final assembled closure

Reconcile implementation against every frozen obligation, re-derive the final behavioral surface, run the complete affected regression set on the assembled candidate, and run repository-required checks. Attribute only demonstrably pre-existing unrelated failures. Record any unavailable required check as blocking rather than converting it to proxy evidence.

Material redesign risks are limited to the five evidence triggers listed under `Reopen only on evidence`. Performance tuning beyond restoring safe, work-conserving concurrency is not part of this repair.

## Relationship to active workplans

This workplan repairs a PERF1 staged-evaluation scheduler/resource-authority regression that is surfaced by target-size screening. It does not supersede `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`, whose remaining assembled interruption/restart/automatic-continuation evidence remains independently active. The RAM-lease repair should land before or as a prerequisite to any final-closure scenario that must pass through uncached staged evaluation.

The older `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md` and its REVIEW1/REVIEW2 amendments are already explicitly superseded by the final-closure workplan and are archived as historical lineage by the repository-hygiene change accompanying this plan. Their still-valid design/evidence remains reusable but they impose no active gates.

## Handoff closure

The final review closes the four gaps left implicit in the initial proposal:

1. **Lease coordinate:** incremental private-provider growth plus inference transient/working memory is bounded by the outer lease; shared/base/prepare/finalize residency already owned elsewhere is not double-charged.
2. **Forward progress:** prepare buffering cannot starve an already-ready minimum inference operation; genuine impossibility is causal failure.
3. **Profile reuse:** reusable static-inference evidence is always re-clamped to the current outer lease without making the ephemeral lease part of persisted compatibility identity.
4. **Lifecycle:** lease and ledger reservation are released on every terminal/cancellation path and cannot leak between tasks.

No material requirement, protected concern, frozen design decision, known cross-module consequence, or required acceptance claim remains intentionally delegated to implementation-time design discovery.