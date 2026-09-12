# MLFF P5 TRAIN2 Memory-Pressure Backoff and Terminal-Infeasibility Repair Workplan

**Status:** Active / implementation-ready  
**Protocol classification:** SSDP 6.2 D3/D4 — architecture, concurrency, resource ownership, runtime orchestration, qualification  
**Implementation branch:** `fix/mlff-p5-train2-memory-pressure-backoff`  
**Baseline branch:** `fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission`  
**Baseline commit:** `ba5deca19019d3fb718f957aa9d0838fbf2aa895`

## 1. Problem statement

Post-selection TRAIN2 cross-validation can currently terminate the entire owned training wave when aggregate GPU memory usage persistently exceeds the scheduler's soft training envelope, even though the device has not produced a CUDA out-of-memory error and the workload remains feasible at lower concurrency.

Observed challenge case on a 24 GiB GPU:

- TRAIN2 admitted two owned jobs concurrently.
- Aggregate VRAM rose to approximately 22.2 GiB.
- Configured scheduler training envelope was approximately 21.6 GiB (90% of 24 GiB).
- GPU utilization remained below the configured 90% utilization admission ceiling.
- Both jobs were making forward progress.
- No CUDA OOM occurred.
- After consecutive control observations above the soft envelope, `_execute_post_selection_pending_runs()` raised `TrainingMemorySafetyError`, cancelled the owned wave, and discarded feasible progress.

This behavior is consistent with the current hard-hazard interpretation in the existing TRAIN2 scheduler design, but the runtime evidence falsifies that interpretation. The soft admission envelope correctly proves that the current concurrency is unsafe to continue or expand; it does **not** prove that the underlying training workload is infeasible.

The defect is therefore architectural rather than a threshold-tuning bug: the controller supports adaptive upward admission but lacks the symmetric resource-driven downward transition required when later live telemetry disproves an admitted concurrency level.

## 2. Governing architectural correction

The TRAIN2 scheduler shall become a bounded **admission + backoff** controller.

> **Resource infeasibility may not be declared until owned TRAIN2 concurrency has first converged to the minimum executable concurrency. A persistent soft admission-envelope violation at concurrency `N > 1` proves that concurrency `N` is unsafe, not that the underlying training run is infeasible.**

The existing scheduler, telemetry, hysteresis, CUDA-lifetime protections, run identity, result publication rules, and scientific semantics remain authoritative. This work repairs the owning control logic; it must not add a second scheduler, retry wrapper, shell-level recovery loop, or parallel control path.

## 3. Scope and owning layers

Primary implementation owners:

- `mdstats/training_data/training_parallel.py`
  - adaptive concurrency controller semantics;
  - resource decision state;
  - effective concurrency ceiling;
  - memory-pressure/backoff policy classification.
- `mdstats/training_data/campaign_post_selection_runtime.py`
  - active TRAIN2 ownership;
  - per-job cancellation/demotion;
  - worker quiescence and CUDA teardown ordering;
  - requeue and scheduler resumption;
  - terminal error scope;
  - observable scheduler state.

Required architecture documentation owner:

- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`

Related prior repair authority to reconcile rather than duplicate:

- `workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md`
- its associated review/reopen documents.

The prior design remains valid for admission, observability, hysteresis, CUDA-lifetime ownership, and pre-OOM intervention. Only the clause that promotes sustained multi-job soft-envelope violation into whole-wave terminal failure is superseded by this workplan.

## 4. Frozen invariants

### INV-1 — Minimum-concurrency feasibility

Terminal memory infeasibility may only be concluded after the scheduler has reduced owned TRAIN2 concurrency to the minimum executable concurrency and the remaining workload is still genuinely unsafe or fails with an authoritative backend/device memory failure.

### INV-2 — Admission envelope is a soft control boundary

The configured TRAIN2 aggregate VRAM envelope governs:

- new admission;
- hold decisions;
- downward backoff;
- re-promotion prohibition after a disproven level.

Crossing this envelope alone is not a terminal scientific or execution failure.

### INV-3 — Hard failure has independent semantics

`TrainingMemorySafetyError` remains a terminal safety mechanism, but its causal basis must be independent of a multi-job soft-envelope breach. Terminal memory failure is permitted only when at least one of the following is true:

1. a single owned TRAIN2 job remains and an existing authoritative hard-safety condition demonstrates that continuing that single job is unsafe;
2. the backend/device reports an actual CUDA OOM or equivalent authoritative allocation failure;
3. teardown/reclamation fails such that mdstats cannot re-establish a safe owned execution state and the failure is causally attributable to owned TRAIN2 lifetime/resource cleanup;
4. another already-established hard-failure invariant from the baseline architecture applies.

Do **not** invent a new arbitrary percentage threshold merely to create a hard boundary.

### INV-4 — Failure scope matches failure cause

Aggregate pressure caused by concurrency must be repaired by reducing concurrency. It must not invalidate unrelated owned jobs that can safely continue.

### INV-5 — Deterministic ownership and demotion

When concurrency must be reduced, exactly one owned TRAIN2 job is demoted per backoff step. The victim is the **most recently admitted currently active owned job** (reverse-most-recent-promotion). This reuses the scheduler's existing admission ordering and does not introduce a new victim-selection subsystem.

### INV-6 — CUDA teardown precedes scheduler reuse

A demoted job is not considered gone when its Python future merely reports cancellation or when a scheduler flag is set. The scheduler must establish the full lifecycle:

`demotion requested -> owned worker cooperatively stops -> worker terminates/quiesces -> CUDA-owned process/object lifetime is released -> device state is re-observed -> scheduler may resume/requeue/admit`

No replacement admission may occur before this boundary is satisfied.

### INV-7 — Disproven concurrency is monotone downward within the execution scope

If live telemetry disproves concurrency `N`, the effective ceiling for the current campaign/device execution scope becomes at most `N - 1`. The same run must not immediately oscillate back to `N`.

Initial repair policy is deliberately monotone: no automatic re-promotion to a concurrency level already disproven in the same execution scope. Do not add timers, cooldown machinery, or speculative recovery logic unless later evidence requires it.

### INV-8 — Scientific semantics are unchanged

This repair must not change:

- selected target sizes;
- folds or seeds;
- CV or production horizons;
- checkpoint identity;
- training labels or replay semantics;
- evidence ranking/reduction;
- result acceptance criteria;
- publication authority;
- exactly-once completed-fold accounting.

A scheduler demotion is a resource-control transition, not a scientific training failure.

### INV-9 — Estimate error is not execution failure

The scheduler's per-job initial VRAM estimate is advisory admission input. If live aggregate telemetry later exceeds the estimate, that proves the estimate or admitted concurrency was optimistic. It does not by itself justify terminal failure.

## 5. Required controller behavior

The existing adaptive controller shall support four conceptual outcomes. Exact internal names are implementation choices; do not add an abstraction solely to mirror these labels.

### ADMIT

Permit a new TRAIN2 job only when all existing admission invariants and live resource projections allow it and the requested concurrency does not exceed the current effective ceiling.

### HOLD

Do not admit another job when telemetry is incomplete, transiently elevated, or above the soft envelope at the current minimum feasible concurrency. Existing safe work may continue.

### BACKOFF

After the baseline persistence/hysteresis requirement confirms a soft-envelope violation while more than one owned TRAIN2 job is active:

- retract one prior admission;
- demote the most recently admitted active owned job;
- reduce effective ceiling by one level;
- wait for owned teardown/reclamation;
- return the demoted run to pending/restartable state;
- continue surviving owned work.

For example:

- `3 -> 2` when concurrency 3 is disproven;
- after settling and new persistent evidence, `2 -> 1` if concurrency 2 is also disproven.

Backoff must be one level at a time so each transition has observable causal evidence.

### TERMINAL_UNSAFE

Enter terminal memory failure only when no lower owned concurrency state remains capable of resolving the safety problem or another independent hard failure applies under INV-3.

## 6. Cancellation and worker ownership repair

The current runtime has a global `cancellation_event` suitable for whole-wave terminal abort. It must **not** be reused as the only mechanism for routine scheduler backoff, because it cannot express "stop exactly one owned job and preserve the others."

Repair the ownership at the existing execution layer:

1. Give each admitted TRAIN2 job a scheduler-owned cooperative stop/demotion signal or equivalent existing per-job control handle.
2. Preserve the global cancellation mechanism for terminal/global abort only.
3. The demoted worker must exit through the same resource-finalization path that guarantees MACE/PyTorch/CUDA lifetime release.
4. The scheduler must observe worker completion/quiescence before treating the slot as released.
5. Do not use `Future.cancel()` as proof of worker termination; once execution has begun, cancelling the future is not equivalent to reclaiming CUDA state.
6. Do not implement a catch-and-retry wrapper around `_execute_post_selection_pending_runs()`.

If the existing worker path already contains a suitable scoped cancellation primitive, rewire it. Add the minimum missing control state only when the current ownership surface cannot represent per-job demotion.

## 7. Demoted-run state semantics

A memory-pressure demotion is neither success nor scientific failure.

Required accounting:

- completed folds remain completed;
- the surviving active job remains active and may complete normally;
- the demoted run returns to the pending/restartable queue after teardown;
- partial, non-authoritative work from the demoted attempt must not be published as a completed fold;
- demotion must not increment `failed_jobs`;
- the task must not be duplicated or lost;
- when later restarted, the run must use the repository's existing checkpoint/restart authority rather than a new retry checkpoint convention;
- final evidence reduction remains by frozen slot identity exactly as before.

## 8. Effective concurrency ceiling

Maintain one scheduler-owned effective concurrency ceiling initialized from the existing concurrency plan.

On persistent pressure at active concurrency `N > 1`:

`effective_ceiling = min(effective_ceiling, N - 1)`

The ceiling is scoped to the current post-selection execution/device context. It is runtime control state, not durable scientific evidence and not campaign configuration.

Do not persist a speculative learned hardware profile as part of this repair.

## 9. Telemetry and operator-facing diagnostics

Retain existing TRAIN2 scheduler reporting, but make the decision state causally explicit.

At minimum, logs must distinguish:

- physical device VRAM used/total;
- configured soft training envelope;
- current active owned TRAIN2 concurrency;
- current effective ceiling;
- whether admission is allowed/held;
- persistent pressure/backoff decision;
- demoted slot/run identity;
- pre-demotion VRAM observation;
- worker teardown completion;
- post-teardown VRAM observation or clearly reported inability to obtain it;
- terminal hard-failure reason when applicable.

Representative causal message:

`last_decision=backoff 2->1: aggregate VRAM 22.2 GiB remained above soft 21.6 GiB envelope; demoting most recently admitted slot=<...>`

Do not report scheduler demotion as `failed_jobs=1`.

## 10. Architecture documentation update

Revise `docs/arch_manuals/mlff_training_data/60_execution_performance.md` so the documented architecture explicitly states:

1. TRAIN2 has symmetric upward admission and downward backoff.
2. The aggregate VRAM training envelope is a **soft admission/backoff boundary**.
3. Persistent soft-envelope violation with `N > 1` causes deterministic one-job demotion, not whole-wave cancellation.
4. Terminal memory infeasibility requires minimum-concurrency exhaustion or another independent hard condition.
5. Reverse-most-recent-promotion defines demotion ownership.
6. CUDA teardown/reclamation precedes requeue or further admission.
7. A disproven concurrency level lowers the effective ceiling monotonically for the current execution scope.
8. Resource demotion is distinct from scientific run failure.
9. Estimated per-job VRAM is advisory; live telemetry is authoritative for runtime adaptation.

Remove or amend contradictory text from the prior hard-live-VRAM-guard doctrine instead of adding a second contradictory section.

## 11. Implementation sequence

### P1 — Separate soft pressure from terminal memory failure

At the existing controller/runtime decision point, separate:

- soft-envelope pressure;
- hard single-job/backend/device failure.

Preserve the existing persistence/hysteresis rule for soft pressure.

### P2 — Add downward controller transition

Extend the existing adaptive concurrency control state so persistent soft pressure at `N > 1` returns a backoff/demotion decision instead of terminal memory hazard.

Do not change the initial admission model except where required to consume the new effective ceiling.

### P3 — Track admission order at the owning scheduler layer

Use existing task/admission sequence to identify the most recently admitted currently active job. Avoid a separate priority/victim framework.

### P4 — Implement scoped cooperative demotion

Wire a per-job stop path through the existing TRAIN2 worker ownership. Preserve global cancellation for terminal abort.

### P5 — Establish teardown barrier

After requesting demotion:

- wait for the selected worker to quiesce/exit;
- execute existing finalization/resource cleanup;
- remove it from active ownership only after that lifecycle boundary;
- re-observe aggregate GPU state;
- only then make subsequent scheduling decisions.

### P6 — Requeue without scientific failure

Move the demoted task back to pending/restartable state with exactly-once slot identity preserved. Do not count it as a failed run.

### P7 — Reduce effective ceiling

After `N -> N-1`, clamp the execution-scope ceiling to `N-1` and prohibit re-promotion to `N` for the rest of the execution.

### P8 — Preserve true terminal behavior

Verify that genuine single-job unsafe/OOM conditions still cancel the relevant owned execution and raise the existing causal safety error.

### P9 — Update documentation and tests in the same change set

No implementation is complete while the architecture manual still states the superseded whole-wave policy.

## 12. Required tests and qualification

### Q1 — Persistent soft breach at concurrency 2

Fixture:

- one job is safe;
- second job is admitted;
- live VRAM remains above soft envelope for the existing persistence window;
- no hard/OOM condition exists.

Expected:

- `2 -> 1` backoff;
- only the most recently admitted active job is demoted;
- surviving job continues;
- demoted job becomes pending/restartable;
- no terminal `TrainingMemorySafetyError`;
- effective ceiling becomes 1.

### Q2 — Cascaded backoff from concurrency 3

Expected sequence:

- persistent unsafe telemetry at 3 causes `3 -> 2`;
- scheduler waits for teardown and settles;
- if pressure remains persistently unsafe at 2, `2 -> 1`;
- no direct `3 -> 1` unless an independent terminal/global failure requires abort.

### Q3 — Soft envelope exceeded at concurrency 1

If no hard condition exists:

- hold at 1;
- do not promote;
- do not terminally fail solely because the soft envelope was crossed.

### Q4 — Genuine hard unsafe condition at concurrency 1

Expected:

- existing terminal safety exception remains causal and explicit;
- global/owned cancellation follows the established terminal path.

### Q5 — Transient spike

A soft-envelope spike shorter than the existing persistence requirement must not cause demotion.

### Q6 — Victim determinism

Given active admission order A then B, a `2 -> 1` backoff must demote B and preserve A.

At concurrency A, B, C, a `3 -> 2` backoff must demote C.

### Q7 — No oscillation

After a pressure-driven `2 -> 1`, later low telemetry in the same execution must not re-promote to 2.

### Q8 — Accounting integrity

Across demotion/restart:

- no duplicate completed slot;
- no lost slot;
- demotion does not increment failed count;
- final number of completed runs equals planned runs exactly once.

### Q9 — Teardown barrier

Instrumented test must prove that scheduler replacement/restart is ordered after the demoted worker's completion/finalization boundary rather than only after a future cancellation request.

### Q10 — Foreign occupancy

Foreign GPU usage must remain part of aggregate telemetry as in the baseline. The controller may reduce/hold owned concurrency in response to aggregate pressure, but it must not claim ownership of foreign processes or attempt to terminate them.

### Q11 — Reclamation does not occur

If the demoted worker terminates but VRAM remains high:

- do not blindly admit a replacement;
- re-evaluate at the lower owned concurrency;
- distinguish residual foreign/parent baseline occupancy from an owned CUDA-lifetime leak;
- if the remaining single owned job is genuinely unsafe under an authoritative hard condition, fail causally;
- if teardown itself failed to release owned CUDA lifetime, surface that owning-layer defect rather than looping retries.

### Q12 — Checkpoint/restart integrity

Force demotion after partial training and verify the run cannot publish incomplete evidence and resumes only through existing checkpoint/restart authority.

## 13. Integration challenge reproducing the observed defect

Construct deterministic resource telemetry equivalent to the observed 24 GiB device case:

- total VRAM: 24.0 GiB;
- baseline scheduler envelope: 21.6 GiB;
- concurrency 1 remains feasible;
- scheduler promotes to concurrency 2;
- aggregate VRAM reaches approximately 22.2 GiB for the existing consecutive-observation window;
- GPU utilization remains below the utilization admission ceiling;
- no CUDA OOM occurs.

Expected result:

1. no whole-wave `TrainingMemorySafetyError` solely because 22.2 GiB exceeds 21.6 GiB;
2. controller emits a causal `2 -> 1` backoff decision;
3. most recently admitted job is demoted;
4. other active job continues;
5. scheduler proves worker teardown before reuse;
6. demoted task is requeued;
7. execution completes all planned folds exactly once at the reduced effective ceiling.

## 14. CUDA-lifetime qualification

The implementation must provide evidence for this lifecycle, not infer it:

`demotion requested -> worker stop observed -> worker finalizer/process exit observed -> CUDA lifetime released/reconciled -> GPU telemetry re-observed -> scheduler resumes`

A task/future state change alone is insufficient evidence.

CPU-only/unit mocks may validate controller logic, but they cannot close the CUDA-lifetime qualification requirement by themselves.

Per project release policy, final real-GPU qualification may be deferred to the consolidated release qualification pass; however, the implementation must leave a deterministic challenge fixture and explicit evidence checklist ready for that pass.

## 15. Falsification passes

### F1 — Threshold tuning false fix

Demonstrate that merely raising the 90% envelope is neither required nor accepted as the repair. The controller must adapt downward at the existing soft boundary.

### F2 — Hidden whole-wave cancellation

Verify no shared global cancellation signal is triggered by ordinary backoff.

### F3 — Scheduler-side cancellation without CUDA teardown

Verify a demoted running worker cannot remain alive while its task has already been returned to pending/restarted.

### F4 — Oscillation

Prove a disproven concurrency level cannot be re-entered in the same execution scope.

### F5 — Scientific evidence leakage

Prove a demoted partial run cannot be classified as completed or feed post-selection evidence reduction.

### F6 — Genuine OOM masking

Cause an authoritative single-job OOM/hard failure and verify the new backoff semantics do not swallow or indefinitely retry it.

### F7 — Foreign-process interference

Demonstrate aggregate foreign VRAM can force owned concurrency downward without mdstats attempting to cancel foreign processes.

## 16. Explicit non-solutions

The implementation must not solve this defect by:

- increasing the 90% VRAM envelope until the observed run passes;
- suppressing `TrainingMemorySafetyError` without introducing correct backoff semantics;
- catching and restarting the whole command/wave;
- serializing all TRAIN2 workloads unconditionally;
- retrying both cancelled jobs after leaving controller state unchanged;
- disabling aggregate VRAM safety checks;
- treating TorchScript deprecation warnings as causal;
- adding an external watchdog or second scheduler;
- persisting speculative hardware tuning state;
- relying on `Future.cancel()` as CUDA teardown;
- inventing a second checkpoint format or retry identity.

## 17. Acceptance criteria

Implementation passes only when all are satisfied:

1. Persistent soft-envelope violation at owned concurrency `N > 1` causes controlled `N -> N-1` backoff rather than terminal whole-wave failure.
2. Terminal resource infeasibility cannot be declared before the controller has converged to minimum owned concurrency, absent an independent authoritative hard failure.
3. Soft admission/backoff boundary and hard terminal safety semantics are distinct in code, tests, logs, and documentation.
4. Exactly one deterministic victim is demoted per backoff step.
5. Unaffected active jobs continue running.
6. A demoted task returns to pending/restartable state without being counted as a scientific failure.
7. Worker/CUDA teardown is established before replacement scheduling or restart.
8. A disproven concurrency level is not retried in the same execution scope.
9. All planned CV folds complete exactly once under the deterministic integration fixture.
10. Genuine single-job hard memory failure still raises a causal terminal error.
11. The supplied 24 GiB / 21.6 GiB envelope / 22.2 GiB live-pressure challenge completes through `2 -> 1` adaptation without terminal failure solely due to the soft-envelope crossing.
12. Foreign occupancy remains observable but outside mdstats cancellation ownership.
13. Controller tests, runtime integration tests, teardown-order tests, and challenge fixture evidence are recorded.
14. Architecture documentation and active workplan agree with the implemented behavior.
15. No duplicate controller, wrapper retry loop, or threshold-only workaround is introduced.

## 18. Expected architecture after repair

```text
                 safe telemetry
          +---------------------------+
          |                           v
      concurrency 1  --->  concurrency 2  --->  concurrency 3
          ^                  |                  |
          |                  | soft pressure    | soft pressure
          +------------------+<-----------------+
                 controlled backoff
```

Terminal memory failure sits outside this adaptation loop and is entered only when no resource-safe owned concurrency state remains or another independent hard failure applies.

## 19. Implementation completion evidence

The implementation handoff/review must include:

- changed owning-layer code paths;
- controller decision tests;
- per-job demotion/cancellation ownership tests;
- exactly-once queue/result tests;
- teardown-order evidence;
- deterministic 24 GiB challenge fixture result;
- architecture-manual reconciliation;
- statement of whether real-GPU CUDA-lifetime qualification was executed now or deferred to final release qualification under project policy.

Do not close this workplan on unit tests alone if teardown/resource ownership remains unproven.
