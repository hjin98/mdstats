---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-P5-TRAIN2-MEMORY-PRESSURE-BACKOFF-REVIEW-REOPEN-1
parent_workplan: workplans/active/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_REPAIR_WORKPLAN.md
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-memory-pressure-backoff
assembled_candidate: d88955cdf5a68b0e7362818ae0aa1cfe93c4ff00
executable_candidate: 7ad4a62393c5d0056a1383c4be7b33633b9e7372
baseline_commit: ba5deca19019d3fb718f957aa9d0838fbf2aa895
highest_affected_domain: D4 concurrency/resource supervision and acceptance evidence under coherent D3 TRAIN2 architecture
serious_challenge: none
precedence: This review preserves the parent workplan's admission-plus-backoff architecture and all conforming implementation surfaces, but supersedes the implementation-complete disposition. The work remains open for B1-B3 below.
---

# MLFF P5 TRAIN2 memory-pressure backoff — first implementation Review reopen

## 0. Disposition

**NO-PASS / REOPENED** under SSDP 6.2.

The assembled branch correctly repairs the original architectural defect in its main direction: TRAIN2 now has symmetric upward admission and downward backoff, the aggregate VRAM envelope is treated as a soft control boundary, the effective concurrency ceiling is reduced monotonically after disproven concurrency, one most-recently-admitted owned job is selected for demotion, unaffected work is preserved, demoted work retains its frozen slot/checkpoint identity, and the Architecture Manual/history are reconciled with the new policy. No second scheduler, threshold inflation, shell retry loop, persisted hardware-tuning authority, or unconditional serialization was introduced.

No Serious Challenge is active against the parent D3 design. The remaining blockers are D4 implementation/acceptance defects at the boundary between resource demotion and genuine child failure.

## 1. Accepted implementation surfaces to preserve

The following reviewed behavior conforms to the parent workplan and must not be redesigned while repairing the blockers:

1. `AdaptiveTrainingConcurrency` owns one execution-local `effective_ceiling`, initialized from the existing plan and reduced monotonically after persistent multi-job soft pressure.
2. A soft-envelope crossing at owned concurrency greater than one produces one-level backoff instead of immediate whole-wave terminal failure.
3. A soft-envelope crossing at owned concurrency one is a hold/no-promotion state unless an independent hard condition occurs.
4. Backoff victim ownership is reverse-most-recent-promotion using the scheduler's existing active admission order; there is no second victim-selection subsystem.
5. The runtime uses per-job cooperative stop handles for ordinary demotion and retains whole-wave signalling only for terminal/global abort.
6. The scheduler waits for the selected worker future to return before removing active ownership, re-observes GPU telemetry, and only then resumes scheduling.
7. Demoted work returns through the existing pending/checkpoint/restart authority and is not counted as a scientific failure.
8. The new deterministic challenge fixture encodes the observed 24.0 GiB / 21.6 GiB envelope / approximately 22.2 GiB two-job pressure case.
9. The Architecture Manual and TRAIN2 admission history correctly supersede the prior doctrine that a persistent multi-job soft-envelope crossing is itself whole-wave terminal infeasibility.
10. The prior CUDA-lifetime workplan is superseded only for that obsolete whole-wave soft-envelope clause; its non-conflicting admission, observability, restart, and CUDA-lifetime invariants remain binding.

These are reductions/rewirings of the existing control flow and should remain the basis of the repair.

## 2. Blocking finding B1 — demotion currently converts arbitrary ordinary child exceptions into retryable work

### Finding

`campaign_post_selection_runtime._execute_post_selection_pending_runs()` requests a victim stop and then inspects `victim_future.exception()`. The implementation currently behaves as follows:

- no exception: classify the slot as genuinely completed before the stop was observed;
- a `BaseException` that is not an `Exception`: re-raise;
- **any ordinary `Exception`: requeue the victim as a successful resource demotion.**

That last branch is too broad. Scheduler intent to demote a job does not prove that the worker's eventual exception was caused by cooperative cancellation.

The production MACE cancellation path in `post_selection_execution.py` currently raises `PostSelectionExecutionError("Post-selection MACE training was cancelled.")` after it observes the request stop signal and terminates the child process. But backend failures, MACE nonzero exits, CUDA allocation failures, injected trainer failures, and programmer/runtime errors are also ordinary exceptions. A failure that races with the backoff request can therefore be silently reclassified as a retryable demotion and returned to the pending queue.

The new test named `test_an_authoritative_child_failure_is_not_swallowed_by_backoff` does not close this boundary: it exercises a one-active-job CUDA OOM before the demotion path is entered. It does not force the selected multi-job victim to fail independently while/after its stop is requested.

### Why this blocks

This violates the parent invariants that hard/backend failure has independent semantics and that resource demotion is distinct from execution/scientific failure. It also violates SSDP concurrency doctrine: retry/adaptation eligibility must be classified by the owning failure semantics, not inferred from temporal proximity to a scheduler retry decision.

The bug can mask the very OOM/backend failures INV-3 requires to remain authoritative, and can create an indefinite retry loop for a deterministic child defect.

### Required repair

Repair the existing execution-owner contract; do **not** add a retry wrapper, second scheduler, exception-message parser, or parallel failure registry.

1. Make cooperative TRAIN2 cancellation/demotion an explicit outcome owned by `post_selection_execution.py`. Prefer the minimum narrowing of the existing `PostSelectionExecutionError` hierarchy/contract so the MACE trainer can distinguish "the requested stop was observed and the owned child was terminated through the cancellation path" from all other execution failures.
2. Have the existing MACE cancellation branch produce that explicit cancellation outcome only after its normal child termination/finalization path runs.
3. In `demote_most_recently_admitted()`:
   - `future.exception() is None` remains genuine completion-before-stop;
   - only the explicit cooperative-cancellation outcome for that victim may be requeued as demoted/restartable work;
   - every other `Exception` must escape into the existing terminal/global failure path and must **not** be requeued.
4. Keep exactly-once slot/checkpoint semantics unchanged. Do not create a retry identity or a second checkpoint convention.
5. Update deterministic harnesses to use the same explicit cancellation outcome as the production trainer rather than generic `PostSelectionExecutionError` as a stand-in for both cancellation and failure.

### Required falsification

Add a real-owner race test with two active jobs and persistent soft pressure that selects the most-recently-admitted victim, but makes that victim raise an unrelated backend/runtime failure at the demotion boundary. The test must prove:

- the exception propagates causally;
- the victim is not returned to `pending_queue`;
- no second attempt of that slot occurs;
- the global terminal cleanup path stops/reaps remaining owned work;
- no CV acceptance is published.

Retain a paired test proving the explicit cooperative-cancellation outcome still requeues and resumes normally.

## 3. Blocking finding B2 — optimizer liveness freshness is incorrectly reused as the teardown deadline

### Finding

The demotion barrier waits for the victim future with:

`timeout = concurrency_policy.epoch_activity_timeout_seconds`.

That policy field is documented and configured as a **child optimizer-activity freshness bound**, deliberately separate from controller telemetry cadence. Its validation permits zero, and it is independently operator-configurable through `parallel_training_epoch_activity_timeout_seconds`.

It is not the owner of MACE process termination. The actual production stop path already has a distinct execution-owner lifecycle: `MacePostSelectionTrainer` observes the cancellation event and terminates/reaps its child using the existing termination grace contract.

Reusing the epoch-activity freshness number as a teardown deadline creates a false coupling. For example, a configured activity timeout of zero makes an ordinary running victim fail the demotion barrier immediately even if its already-authorized termination path would quiesce correctly milliseconds later. Any activity timeout shorter than the trainer's legitimate termination/reap interval can similarly produce a false `TrainingMemorySafetyError` and mislabel healthy teardown as a CUDA-lifetime defect.

### Why this blocks

This violates one-owner/one-meaning architecture and INV-3/INV-6: terminal teardown failure must be evidence about the owned teardown lifecycle, not a timeout borrowed from optimizer-progress freshness. It also makes an unrelated liveness-tuning value change resource safety semantics.

### Required repair

Do not add another user-facing timeout knob.

1. Remove `epoch_activity_timeout_seconds` as the authority for demotion teardown completion.
2. Preserve the existing `MacePostSelectionTrainer` child-termination/reaping path as the owner of normal cooperative stop duration; the scheduler must allow that owner to reach its terminal cancellation/completion outcome.
3. If an outer scheduler bound is still required to detect a trainer that never returns, derive it from an **existing execution/termination supervision contract** and ensure it cannot expire before the owned trainer's legitimate terminate/reap bound. Do not reuse optimizer epoch freshness and do not create a second termination policy surface.
4. Keep the scheduler's post-return telemetry re-observation and no-replacement-before-teardown rule unchanged.

### Required falsification

Add tests proving semantic independence:

- setting `parallel_training_epoch_activity_timeout_seconds = 0` must not make a cooperative backoff fail merely because worker teardown is not instantaneous;
- a cooperative stop that completes within the existing execution-owner termination contract must back off/requeue successfully even when optimizer liveness configuration is shorter;
- a genuinely non-quiescing owned worker must still reach a causal terminal teardown failure through the correct termination/supervision authority.

## 4. Blocking finding B3 — candidate-bound implementation/qualification evidence is absent

### Finding

The executable implementation candidate is `7ad4a62393c5d0056a1383c4be7b33633b9e7372`; assembled branch head `d88955cdf5a68b0e7362818ae0aa1cfe93c4ff00` adds generated documentation only.

The branch contains extensive new/changed tests, but no candidate-bound functional acceptance record was added for this workplan. GitHub reports no Python test/check status for the executable candidate; the only branch workflow realization visible to review is the successful documentation-PDF build. Therefore the parent workplan's Acceptance Criterion 13 and Section 19 completion-evidence contract are not yet satisfied.

Older baseline qualification cannot close this gap because the scheduler/runtime executable behavior changed materially in this candidate.

Per project policy, the final physical-GPU CUDA-lifetime challenge may remain deferred to the consolidated final-release GPU qualification. That deferral is not itself a blocker if explicitly recorded. The deterministic real-owner fixture and affected CPU/host test evidence, however, must exist for this executable candidate before review closure.

### Required evidence after B1/B2 repair

On the repaired executable candidate, record exact commands, commit/tree identity, exit status, and pass counts for at least:

1. focused controller/runtime surface:
   - `tests/test_mlff_p5_train2_memory_backoff.py`;
   - `tests/test_mlff_training_parallel_scheduler.py`;
   - `tests/test_mlff_p5_train2_zero_safe_admission.py`;
2. all affected post-selection TRAIN2/CV restart, failure-propagation, cancellation, EVAL2 phase-boundary, and CUDA-lifetime regression suites touched by `campaign_post_selection_runtime.py`, `training_parallel.py`, and `post_selection_execution.py`;
3. an assembled real-owner cross-validation challenge proving the 24.0/21.6/22.2 GiB control sequence reaches `2 -> 1`, preserves the survivor, requeues only the explicitly cancelled victim, and completes exactly once;
4. the ordinary project compilation/package/dependency checks required by the current mdstats acceptance practice when executable source changes.

Record whether physical-GPU E2 was executed or explicitly deferred under the standing final-release GPU policy. Do not claim the deterministic telemetry fixture as physical CUDA-lifetime evidence.

## 5. Global-invariant assessment

### Core problem of concern

The implementation now addresses the original concern at the correct abstraction: excessive **concurrency** is handled by reducing concurrency rather than declaring the scientific workload infeasible. Preserve this.

B1 is a causality leak at the next boundary down: "scheduler asked for demotion" is being used as evidence that "the worker failed because of demotion." That inference is not valid. The execution owner must state the cancellation outcome explicitly.

B2 is an ownership leak in the opposite direction: optimizer-progress freshness is being made authoritative for process teardown. Teardown timing belongs to execution/process supervision.

Together they show the remaining repair is not another scheduling algorithm. It is a narrowing of two existing interface meanings so resource adaptation, execution failure, and process lifetime remain distinct.

### High-level architecture

The accepted architecture remains:

`live TRAIN2 telemetry -> existing adaptive controller -> ADMIT / HOLD / one-step BACKOFF -> existing per-job execution owner -> explicit completion/cancellation/failure outcome -> teardown barrier -> re-observe -> existing queue/checkpoint authority`

Terminal/global abort remains outside that adaptation loop.

Do not introduce a retry manager, watchdog, new queue, new persistence schema, new hardware profile, or duplicated cancellation state to fix B1/B2.

## 6. Re-review acceptance gate

A subsequent SSDP 6.2 Review may PASS only when all of the following are true on one candidate-bound state:

1. B1 is closed: only explicit cooperative cancellation is retryable/requeueable after demotion; unrelated ordinary exceptions remain authoritative failures.
2. B2 is closed: demotion teardown no longer depends on optimizer epoch-activity freshness; the lifecycle owner and timeout meaning are coherent.
3. The new race/failure and timeout-independence falsification tests pass through the real scheduler/execution ownership seams.
4. All previously accepted parent-workplan behaviors remain conforming: soft-boundary backoff, LIFO victim, monotone ceiling, survivor preservation, exactly-once restart/accounting, foreign occupancy ownership, single-job hold, and no re-promotion.
5. Candidate-bound focused and affected-regression evidence required by B3 is recorded and passing.
6. Documentation remains aligned with the repaired executable semantics; generated documentation is refreshed if source documentation changes.
7. Physical-GPU qualification is either recorded if performed or explicitly deferred to the final-release GPU qualification package under project policy.
8. No D1/D2 scientific method identity, training labels, fold/seed membership, horizons, checkpoint identity, evaluation authority, or publication semantics change.

Until those conditions are satisfied, the parent workplan remains **NO-PASS / REOPENED**.

## 7. Implementation response to B1/B2/B3 (candidate-bound)

Repaired executable candidate: `46049fed` on `fix/mlff-p5-train2-memory-pressure-backoff`, tree `07b8eaaf67231bf2b924a7f2716d3edda9ff5afe`. Environment: conda env `mace`, Python 3.11, PyTorch 2.13.0+cu126, mace-torch 0.3.16, 32 CPU cores.

### B1 closure

- `post_selection_execution.py` declares `PostSelectionCancelledError(PostSelectionExecutionError)` - a narrowing of the existing execution-error contract, exported in `__all__` - and the MACE cancellation branch raises it *after* `_terminate_post_selection_process` and the `status="cancelled"` finalization emit. Every other execution failure keeps `PostSelectionExecutionError` or its own type.
- `demote_most_recently_admitted()` now requeues only that explicit outcome. `future.exception() is None` remains completion-before-stop; anything else increments `failed_count` and is re-raised into the pre-existing terminal/global path. No exception-message parsing, retry wrapper, second scheduler, or parallel failure registry was added.
- The deterministic harness raises the same explicit outcome as the production trainer.

### B2 closure

- `epoch_activity_timeout_seconds` no longer appears in the demotion barrier; it remains solely the child optimizer-activity freshness bound passed as `optimizer_activity_timeout_seconds`.
- `MacePostSelectionTrainer.cancellation_teardown_seconds` derives the barrier bound from the owner's own contract - `2 * poll_interval + 2 * terminate_grace` - which cannot expire before the escalating SIGINT/SIGTERM/SIGKILL sequence it already authorizes. The scheduler reads that declared bound via the trainer object; an owner declaring none keeps sole authority and the barrier stays unbounded. No new operator knob and no second termination policy surface.

### B3 evidence actually executed

All commands run from the repository root as `conda run -n mace python -m pytest ... -q -p no:randomly`.

| # | Target | Result |
| --- | --- | --- |
| 1 | `tests/test_mlff_p5_train2_memory_backoff.py` | **11 passed**, exit 0, 129.84s |
| 2 | `tests/test_mlff_training_parallel_scheduler.py tests/test_mlff_p5_train2_zero_safe_admission.py` (`-n 8`) | **57 passed**, exit 0, 67.53s |
| 3 | 41 affected suites touching `campaign_post_selection_runtime.py`, `training_parallel.py`, `post_selection_execution.py` and the shared post-selection fixture (`-n 16`) | **1316 passed, 3 failed, 1 skipped**, 1754.81s |
| 4 | `tests/test_mlff_doc_arch1_specification.py` | **9 passed**, exit 0 |
| 5 | `python -m compileall mdstats`; import of both edited modules | clean |

Item 3's three failures reproduce **byte-identically on the stashed baseline tree** and are pre-existing, unrelated drift:

- `test_mlff_opt_ctrl1_specification.py::test_opt_ctrl1_release_identity_preserves_scientific_compatibility` - asserts the pinned `version = "0.20.140a0"` in `pyproject.toml`;
- `test_mlff_opt_ctrl1_specification.py::test_opt_ctrl1_architecture_and_spec_close_roadmap` - asserts OPT-CTRL1 roadmap text absent from the current manual;
- `test_mlff_target_size_p5f_structure.py::test_p5f_no_screening_continuation_owner_is_reachable_from_post_selection` - flags the long-standing `--restart_latest` MACE wrapper flag.

Item 3's one skip is the standing `UNAVAILABLE/BLOCKING` LAMMPS/MACE callback on this host, deferred to target-machine qualification.

Item 1 includes the B1/B2 falsification set required above:

- `test_a_victim_that_fails_at_the_demotion_boundary_stays_a_failure` - two active jobs, `backoff 2->1` reached, victim raises an unrelated backend failure at the stop boundary; the failure propagates causally, `attempts[victim] == 1` (no requeue, no second attempt), the surviving owned job is stopped and reaped by the terminal path, `failed_jobs=1` / `status=failed`, and `resolve_current_cv_acceptance` is `None`;
- `test_sustained_two_job_pressure_demotes_one_job_and_completes_every_fold` - the paired positive: the explicit cancellation outcome still requeues, resumes from its authenticated TRAIN2 summary, and both folds complete exactly once (the 24.0 / 21.6 / 22.2 GiB challenge, run through the real `execute_post_selection_cross_validation`);
- `test_backoff_survives_a_zero_optimizer_activity_timeout` - `parallel_training_epoch_activity_timeout_seconds = 0.0` with a deliberately non-instantaneous (0.3s) teardown still backs off and requeues;
- `test_a_worker_that_never_quiesces_is_a_causal_terminal_memory_failure` - a child that ignores its stop still reaches `TrainingMemorySafetyError`, now through the execution owner's declared termination bound;
- `test_the_demotion_barrier_reads_only_the_execution_owner_contract` - structural/negative evidence that no liveness or control cadence is the teardown deadline, which runtime tests cannot establish.

### Documentation

`docs/arch_manuals/mlff_training_data/60_execution_performance.md`, the assembled `mlff_training_data_architecture.md` (regenerated with `tools/build_mlff_architecture_manual.py`, byte-identical to the edit), and `docs/history/mlff/train2_admission_evolution.md` ("The fourth falsification") record both narrowings. `mlff_training_data_architecture.pdf` + manifest are regenerated by the `docs-build.yml` CI workflow on push, as they were for the previous candidate; pandoc 3.10.2 / typst 0.15.1 are not installed on this workstation, so local regeneration is **unavailable**.

### Physical-GPU qualification

**Explicitly deferred** to the consolidated final-release GPU qualification package under standing project policy. The deterministic telemetry fixture is not claimed as physical CUDA-lifetime evidence.

