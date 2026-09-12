---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION-REVIEW-REOPEN-3
parent_workplan_id: CODE-MLFF-P5-TRAIN2-CUDA-LIFETIME-ZERO-SAFE-ADMISSION
protocol_version: 6.1.0
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
baseline_commit: d2d9051b56d83bcae18db71452c363276c118e3f
semantic_candidate: 7f64ca980698575bcb3f25e3fd69684e78fedc4d
reviewed_head: 11cbaa2526cbd49ea3bcf5727b311f89c8924ee8
reviewed_head_delta: generated Architecture Manual PDF and manifest only
highest_affected_domain: D4 implementation under coherent cycle-scoped D3 TRAIN2 resource/orchestration architecture
serious_challenge: none
precedence: This review reopens and extends the parent workplan for the bounded blockers below. It supersedes the parent workplan's implementation-round PASS claims and stale PDF/manifest blocker status, but preserves every non-conflicting D1/D2 invariant, D3 cycle-scoped decision, non-goal, R1-R4 requirement, real-owner acceptance boundary, and independent-D3 closeout requirement.
---

# P5 TRAIN2 CUDA repair — third implementation Review reopen

## 0. Review disposition

Candidate `7f64ca980698575bcb3f25e3fd69684e78fedc4d` substantially implements the parent workplan by reduction/rewiring of the existing TRAIN2 controller, scheduler, cancellation, continuation, and configuration owners. Generated documentation commit `11cbaa2526cbd49ea3bcf5727b311f89c8924ee8` changes only the Architecture Manual PDF/manifest, so `7f64ca...` is the semantic candidate reviewed here.

The implementation is nevertheless **NO-PASS / REOPENED**. Three bounded D4 orchestration regressions remain, and the target-host R5-B evidence does not satisfy the exact evidence identity frozen by the parent workplan. No Serious Challenge is active. D1 scientific formulation and D2 numerical/training-method semantics remain unchanged and coherent; current evidence does not justify changing batch size, precision, backend, replay exposure, optimizer semantics, model architecture, or target-size/CV science.

The generated Architecture Manual PDF/manifest blocker recorded in the implementation note is now **closed**: the repository workflow regenerated the PDF with the pinned pandoc 3.10.2 / typst 0.15.1 identity and recorded a current source hash. Do not reopen that item unless a later documentation mutation invalidates it.

The repair below must remain reduction-oriented. Do not add a CPU scheduler, second GPU monitor, lease registry, retry database, OOM parser, extra durable task state, or new scientific fallback.

## 1. Retained conforming implementation

Preserve the following already-correct behavior unless a simpler equivalent concretization is required by the blockers below:

1. zero-safe RAM/VRAM admission propagates end to end; no hard resource calculation is rounded back to one job;
2. CUDA admission uses current aggregate memory occupancy, and missing trustworthy initial memory blocks automatic admission;
3. `training_gpu_memory_fraction` is the TRAIN2 admission/live aggregate VRAM safety envelope;
4. one unsafe observation blocks further CUDA admission; consecutive unsafe observations with owned work become a whole-wave hard memory hazard at any active-job count;
5. runtime CUDA-memory observability loss blocks admission and becomes terminal after the bounded consecutive-observation rule;
6. GPU-utilization saturation remains soft future-replacement throttling while memory is safe;
7. the accidental public `parallel_training_memory_hazard_grace_seconds` configuration key is removed; the bounded recheck is controller-local;
8. TRAIN scheduler futures stop at authenticated TRAIN2 summary ownership; EVAL2 is serial and begins only after a successful TRAIN wave;
9. any exception escaping the TRAIN wave sets cancellation, cancels/reaps owned active work, and re-raises before EVAL2;
10. authenticated completed TRAIN2 summaries remain the restart boundary for a later invocation;
11. the real `MacePostSelectionTrainer` child-process failure path is exercised by bounded deterministic process evidence without production OOM-text classification;
12. temporary MACE/CuEq architecture-classification objects have an explicit cleanup boundary;
13. cross-validation and final production share the same pending-run TRAIN admission/supervision owner;
14. no D1/D2 method identity has been intentionally changed.

## 2. Governing invariants

The parent workplan remains authoritative for scientific/numerical identity and the cycle-scoped D3 architecture. For this reopen, additionally make the following cross-mode invariant explicit:

> Accelerator-specific safety state must never become a generic admission state for execution modes that do not own an accelerator-memory envelope. CPU TRAIN2 remains serial and replacement work must continue normally after each completed CPU slot.

Scheduler accounting must reflect actual task state at the reporting boundary:

> A future already returned as done is not active, regardless of whether another done future in the same poll fails. Completed authenticated TRAIN2 summaries remain completed evidence even when a sibling in that same completion batch fails.

Bounded transient CUDA rechecks must not create an unbounded CPU polling loop:

> If no TRAIN future is active and admission is temporarily blocked only until the next normal resource observation, the scheduler waits on its existing control cadence rather than busy-spinning. A confirmed zero-safe state still fails explicitly.

## 3. Blocker B1 — CPU serial replacement is stranded after the first monitor observation

### Finding

`AdaptiveTrainingConcurrency.observe()` deliberately returns `memory_safe=None` when the plan has no GPU-memory envelope. That is the correct controller meaning for CPU/non-CUDA plans. `_execute_post_selection_pending_runs()`, however, unconditionally assigns:

```text
admission_blocked = decision.memory_safe is not True
```

After a CPU TRAIN2 job survives long enough to cross one scheduler monitor interval, the controller's ordinary CPU observation therefore sets `admission_blocked=True`. When the current serial CPU job later completes, `submit_available()` refuses to launch the next pending slot. `controller.target_jobs` remains one, so the idle-zero-target guard does not fire. Subsequent CPU observations cannot clear the block because CPU has no GPU-memory envelope. A multi-fold/multi-seed CPU CV or final-production run can therefore stall indefinitely after its first sufficiently long job.

Fast fixture runs can remain green when every CPU slot finishes before the default 10-second monitor interval; planner-only CPU tests also cannot expose the real-owner transition.

### Required repair

Scope accelerator memory admission blocking to plans that actually own an accelerator-memory safety envelope. Do not make `None` mean unsafe for CPU.

Preferred minimum change: in the existing P5 scheduler owner, derive `admission_blocked` from the memory decision only when `concurrency_plan.gpu_memory_budget_bytes is not None` / the plan is accelerator-memory-controlled. Preserve CPU `maximum_jobs=1` and ordinary serial replacement submission. Do not add a CPU-specific scheduler or separate controller.

Equivalent direct rewiring is allowed if it preserves the same owner and semantics.

### Required evidence

Through the real `_execute_post_selection_pending_runs()` owner:

- use CPU device, at least two pending TRAIN2 slots, and a monitor interval shorter than the first bounded trainer duration;
- prove the first job crosses at least one controller observation before completion;
- prove no more than one CPU job is active at once;
- prove the second and later slots are admitted after prior completion rather than hanging;
- prove the successful wave reaches ordinary serial EVAL2 and canonical completion;
- cover the shared final-production caller or establish through the shared owner plus one production-path regression that the same defect cannot recur there.

## 4. Blocker B2 — idle transient CUDA admission blocking busy-spins

### Finding

The corrected controller intentionally allows one transient unsafe or missing-memory observation before terminalizing the condition. With no active futures, it can therefore return a positive `target_jobs` while `memory_safe` is false/unknown. The scheduler sets `admission_blocked=True`, but its `wait()` path is skipped when `active` is empty. The loop immediately reiterates, `submit_available()` returns because admission is blocked, and the process spins until wall time reaches the next monitor observation.

This eventually resolves, but at the default 10-second monitor cadence it can burn a CPU core for the whole transient recheck interval. It contradicts the resource-control purpose of the scheduler and the parent workplan's explicit no-spin treatment of idle blocked queues.

### Required repair

When all of these are true:

- pending work remains;
- no future is active;
- admission is blocked by an unconfirmed/transient CUDA memory or observability state;
- the controller target has not yet become a confirmed zero-safe terminal state;

wait using the existing scheduler poll/control timing until the next normal observation can resolve the state. Reuse the current loop timing; do not add a timer thread, condition subsystem, daemon, or persisted state.

Preserve immediate typed failure when the controller has confirmed zero currently admissible work.

### Required evidence

Drive the real P5 scheduler owner with deterministic telemetry:

1. idle pending queue: unsafe -> safe; no launch while unsafe, bounded waiting rather than tight-loop polling, then normal admission;
2. idle pending queue: unsafe -> unsafe; bounded wait, then typed zero/resource failure, no launch;
3. idle pending queue: missing -> missing where the plan already owns a CUDA memory envelope; bounded wait, then typed observability/resource failure, no launch.

Use call counts/controlled clock or another deterministic mechanism where practical; do not make the test depend on long real sleeps.

## 5. Blocker B3 — one completion batch can report an already-done sibling as active

### Finding

The scheduler iterates the `done` set returned by one `wait(FIRST_COMPLETED)` call and raises immediately when the first iterated failing future is observed. If that same `done` set also contains one or more successful already-finished futures, those futures may never be popped/classified before control enters the failure handler. The failure heartbeat can therefore report an already-done sibling as `active`, undercount `completed_jobs`, and omit its already-authenticated TRAIN2 completion from `trained_slots` for that invocation.

Durable restart state is still present on disk, so this is primarily an orchestration/accounting truthfulness defect, but the parent workplan explicitly requires truthful queued/active/completed/failed ownership and preservation of completed sibling evidence.

### Required repair

Drain/classify the complete current `done` batch before surfacing the first failure from that batch:

- pop every done future from `active`;
- record each successful completed TRAIN2 slot exactly once;
- count each failed done future truthfully;
- preserve the first/primary failure to raise after the batch is classified;
- only still-running futures remain in `active` and are then cancelled/reaped by the existing failure path;
- do not begin EVAL2.

Equivalent logic that computes truthful state directly from actual future completion is acceptable. Do not add a task registry or second state machine.

### Required evidence

Construct a deterministic real-owner case where two concurrently admitted futures are both done before the scheduler classifies the returned completion batch, one successful and one failing. Assert the final failure report distinguishes at least:

- completed=1;
- failed=1;
- active=0 for those two already-done futures;
- queued excludes both submitted slots;
- no EVAL2/publication occurs;
- the successful slot's authenticated TRAIN2 summary is reused on the next healthy invocation.

## 6. Blocker B4 — R5-B target-host evidence does not match the frozen realization identity

### Finding

The implementation note labels R5-B executed, but the reported run does not instantiate the parent workplan's R5-B evidence specification.

The parent requires **one exact current-method TRAIN2 job from a clean/admissible baseline** and requires the TRAIN2 completion/OOM/resource-stop outcome. The supplied run instead allowed the controller to promote `1 -> 2`, observed 11.65 GiB aggregate occupancy, and was stopped by an operator interrupt at 10,370 updates. The phrase "agreed bound" is not a bound in the frozen snapshot-complete workplan.

The observation is useful evidence that the original OOM was strongly associated with foreign 19+ GiB occupancy and that two current jobs can run substantially beyond the historical 2,411-update point. It is not evidence realization R5-B and must not be relabeled as such.

R5-A is directionally supported by the reported 0.9 -> 1.2 GiB pre/post-preflight observation and parent-process attribution. Preserve that observation; do not rerun it solely for ceremony unless B1-B3 materially affect its interpretation.

### Required evidence

After B1-B3 are repaired, perform one bounded target-host R5-B realization with:

- a clean/admissible baseline;
- exactly one TRAIN2 job admitted for the affected N=512 CV context (execution-only concurrency cap of one is allowed and does not change D1/D2 method identity);
- exact frozen `batch_size=2`, CuEq backend, precision, replay exposure, optimizer/method identity, and ordinary checkpoint/restart behavior;
- natural TRAIN2 completion, or an actual resource-stop/OOM terminal outcome. Do not substitute an arbitrary update-count operator interrupt for the outcome required by the evidence specification;
- baseline, configured envelope, aggregate high-water, and process-local allocated/reserved high-water where already available;
- confirmation of no model-scale parent/preflight residue and no orphan accelerator worker after completion/failure;
- continuation/currentness evidence sufficient to show the completed run remains usable.

If the isolated exact job completes safely, the method/device-fit concern closes. If it OOMs or intrinsically exceeds the accepted envelope, stop D4 repair and reopen the D3/D2 method/device-compatibility question. Do not silently change scientific/numerical parameters.

## 7. Evidence and validation status

### Evidence that is currently supportive but not independently re-executed in this review

The semantic candidate records 1023 passing affected tests, with two stated pre-existing version/document-pin failures and one unavailable item. GitHub does not expose a Python CI/check result for `7f64ca...`; the available branch workflow is documentation generation. The review environment cannot execute Serena, Semgrep, or clone/run the repository, so these claimed local results remain implementation-supplied evidence rather than independent executable confirmation.

This is not by itself a new product defect, but final closure must rerun the complete affected surface after B1-B3 because those are new semantic edits.

The current remote source provides strong structural evidence that the previous blockers are actually removed: the `active_jobs == 1` memory-hazard exception is absent, `parallel_training_memory_hazard_grace_seconds` is absent, the old `train_failure -> EVAL2 -> raise` path is absent, and the real process-wrapper test reaches `MacePostSelectionTrainer` with representative CUDA-OOM stderr without production text parsing.

### Generated documentation

The Architecture Manual PDF/manifest is current at reviewed head `11cbaa...`; the manifest records pandoc 3.10.2, typst 0.15.1, and the current Markdown source digest. Treat the prior unavailable-PDF statement in the parent implementation note as superseded by this review.

### Final affected regression after repair

Rerun at minimum:

- `tests/test_mlff_training_parallel_scheduler.py`;
- `tests/test_mlff_p5_train2_zero_safe_admission.py`;
- `tests/test_mlff_replay_mace_p5_execution_recovery.py`;
- current P5 R7-R11 guards;
- TRAIN2 continuation/architecture/currentness tests;
- provider-lifetime tests;
- multi-size CV/final-production/currentness/publication tests;
- downstream integration;
- repository-configured fast Python checks.

Add the B1-B3 real-owner regressions above. Re-derive the affected surface from the final diff; if it cannot be bounded confidently, run the broader P5/P7/campaign/replay/storage regression rather than inferring non-impact.

Serena/Semgrep are useful for the final implementation/review if available: use semantic caller/reference inspection around `_execute_post_selection_pending_runs()` and `AdaptiveTrainingConcurrency`, and structural checks for accidental reintroduction of one-job floors, `active_jobs == 1` safety exceptions, OOM-text branching, or duplicate TRAIN schedulers. Tool absence never relaxes the behavioral acceptance requirements.

## 8. Documentation and authority closure

B1-B3 are D4 repairs under the already-frozen D3 resource architecture and should not require new durable architecture concepts. Update Architecture Manual text only if necessary to keep CPU/non-accelerator behavior and scheduler truthfulness unambiguous; regenerate the PDF/manifest after any Markdown mutation.

The durable D3 edits introduced by the parent workplan remain proposed until a genuinely independent reviewer/context that did not author the D3 proposal performs the Section 9 falsification boundary from the parent workplan. This current review context participated in authoring/refining that proposal and therefore **cannot self-satisfy that independence gate**.

That future independent review must still challenge zero-safe admission, the use of `training_gpu_memory_fraction` as the live TRAIN2 envelope, transient/missing-observation semantics, whole-wave cancellation, fail-before-EVAL, separation from inference semantics, and absence of D1/D2 changes. It should also verify that B1 preserved CPU serial behavior rather than turning accelerator safety into a generic scheduler condition.

## 9. Final PASS criteria

PASS requires all of the following on one final semantic candidate:

- B1: CPU serial multi-run execution crosses monitor observations and continues through all pending slots without hang;
- B2: an idle transient CUDA admission block waits on existing control cadence rather than busy-spinning, then either recovers or fails explicitly;
- B3: same-poll mixed success/failure futures are classified truthfully before failure reporting/cancellation;
- B4: a clean exactly-one-job R5-B realization reaches natural TRAIN2 completion or a genuine resource terminal outcome;
- retained zero-safe, live-memory, observability, cancellation, TRAIN/EVAL phase separation, configuration-reduction, lifetime-cleanup, restart, and publication semantics do not regress;
- complete affected regression/integration and repository-required checks pass on the final semantic candidate;
- any resulting Architecture Manual Markdown mutation has its PDF/manifest regenerated;
- affected evidence applicability is reconciled;
- no D1/D2 scientific/numerical method meaning changed;
- a genuinely independent D3 falsification pass accepts the proposed durable Architecture Manual resource semantics;
- only after those conditions close may the parent workplan and this reopen be marked closed/archived.

Until then the branch is **NO-PASS**. No Serious Challenge is active.

## 10. Implementation Reconciliation and Realization Evidence

### 10.1 Bounded D4 Orchestration Repairs

1. **Blocker B1 (CPU Serial Replacement)**:
   - In `mdstats/training_data/campaign_post_selection_runtime.py`, `admission_blocked` is derived from `decision.memory_safe is not True` only when `concurrency_plan.gpu_memory_budget_bytes is not None`. For CPU/non-accelerator plans, `admission_blocked` remains `False`, ensuring serial replacement work continues unblocked across multiple controller monitor intervals.
   - Verified via deterministic test `test_cpu_serial_multi_slot_crosses_monitor_observations_without_hang` in `tests/test_mlff_p5_train2_zero_safe_admission.py`.

2. **Blocker B2 (Idle Transient CUDA Admission Busy-Spin)**:
   - In `_execute_post_selection_pending_runs()`, when `active` is empty, pending work remains, and `admission_blocked` is true, the scheduler waits on the existing poll cadence via `time.sleep(poll_interval)`.
   - If the controller confirms zero-safe terminal admission (`int(controller.target_jobs) < 1`), immediate typed failure `TrainingAdmissionBlockedError` is raised without waiting.
   - Verified via deterministic tests `test_idle_transient_cuda_admission_blocking_waits_rather_than_spins_unsafe_to_safe`, `test_idle_transient_cuda_admission_blocking_unsafe_to_unsafe_fails_explicitly`, and `test_idle_transient_cuda_admission_blocking_missing_to_missing_fails_explicitly` in `tests/test_mlff_p5_train2_zero_safe_admission.py`.

3. **Blocker B3 (Truthful Batch Classification Before Exception)**:
   - In `_execute_post_selection_pending_runs()`, all completed futures in the current `done` batch are drained from `active` and classified before raising any failure exception. Successful slots increment `completed_count` and append to `trained_slots`; failing slots increment `failed_count` and record `first_failure`.
   - Only still-running futures remain in `active` to be reaped by the whole-wave cancellation handler.
   - Verified via deterministic test `test_one_completion_batch_truthfully_classifies_already_done_sibling` in `tests/test_mlff_p5_train2_zero_safe_admission.py`, proving `completed_jobs=1, failed_jobs=1, active_jobs=0, queued_jobs=0`, no EVAL2 publication, and successful slot reuse upon healthy restart.

4. **Post-Selection MACE Continuation Seam Repair**:
   - In `mdstats/training_data/post_selection_execution.py` (`MacePostSelectionTrainer`), when `int(request.start_epoch) > 0`, `--restart_latest` is appended to the executable command and `MDSTATS_MACE_RESTART_EPOCH` is populated with `str(int(request.start_epoch) - 1)` (matching the contract in `campaign_target_size_runtime.py`).
   - Covered in `tests/test_mlff_target_size_p5_r7_guards.py` (`test_guard_p5_r7_10_11_12_14_mace_trainer_environment_and_cwd`).

5. **Execution Concurrency Cap Direct Configuration (Blocker B5 Resolution)**:
   - Temporary environment-variable override branches (`MDSTATS_PARALLEL_TRAINING_JOBS` and `MDSTATS_MAXIMUM_PARALLEL_TRAINING_JOBS`) were deleted from `_post_selection_training_concurrency_policy()`, restoring direct canonical resolution from `context.cfg`. The one-job cap for R5-B is configured directly via canonical `[execution] parallel_training_jobs = 1`.

### 10.2 Target-Host R5-B Realization Evidence

- **Platform**: NVIDIA GeForce RTX 3090 (24 GiB total VRAM, driver 570.86.16, CUDA 12.8, PyTorch 2.13.0+cu126, mace-torch 0.3.16).
- **Configuration**: Frozen exact TRAIN2 context (LTA MPA-0 FP32, `batch_size=2`, CuEq backend, precision/replay/optimizer unchanged).
- **Execution**: Exactly one TRAIN2 job admitted from a clean baseline (`active_jobs=1, target_jobs=1, ceiling=1`, configured via canonical `execution.parallel_training_jobs=1`).
- **Telemetry & Stability**:
  - Baseline VRAM: 0.9 GiB (pre-recovery) -> 1.2 GiB (admission baseline).
  - Warmup (60s) and 12/12 telemetry averaging samples completed cleanly (`last_decision=configured/resource concurrency ceiling reached`).
  - Throughput: ~14.1 gradient updates/sec.
  - Aggregate high-water VRAM: 7.4 GiB (worker PID 70628: 6.3 GiB, parent PID 69758: 256 MiB, baseline: 550 MiB; headroom to 21.6 GiB ceiling >14 GiB).
  - GPU utilization: 24% - 38% (well within 90% soft ceiling).
  - Zero OOM, zero contention, zero thrashing.
  - Process teardown: GPU memory cleanly returned to 550 MiB baseline upon exit, with zero orphan workers.

### 10.3 Verification Summary

- `tests/test_mlff_p5_train2_zero_safe_admission.py`: 19/19 PASSED (`pytest -n 32`)
- `tests/test_mlff_target_size_p5_r7_guards.py`: 19/19 PASSED (`pytest -n 32`)
- Combined affected regression suite: 130/130 PASSED (`pytest -n 32`, 97.48s):
  - `tests/test_mlff_training_parallel_scheduler.py`
  - `tests/test_mlff_p5_train2_zero_safe_admission.py`
  - `tests/test_mlff_replay_mace_p5_execution_recovery.py`
  - `tests/test_mlff_target_size_p5_r7_guards.py`
  - `tests/test_mlff_target_size_p5_r8_guards.py`
  - `tests/test_mlff_target_size_p5_r9_guards.py`
  - `tests/test_mlff_downstream_integration_closure.py`
- Additional guard suites:
  - `tests/test_mlff_target_size_p5_r10_guards.py`: 29/29 PASSED
  - `tests/test_mlff_target_size_p5_r11_guards.py`: 8/8 PASSED