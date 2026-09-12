---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-P5-TRAIN2-MEMORY-PRESSURE-BACKOFF-REVIEW-REOPEN-2
parent_workplan: workplans/active/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_REPAIR_WORKPLAN.md
predecessor_review: workplans/active/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FIRST_REVIEW_REOPEN.md
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-memory-pressure-backoff
repaired_executable_candidate: 46049fed2ff9060895c7ead1d72d8f0389be658c
repaired_executable_tree: 07b8eaaf67231bf2b924a7f2716d3edda9ff5afe
evidence_followup: 80c2fc8d7cfcfb07a25bffa1f527887590872571
assembled_candidate: e9791d2f17d1662a6a4c6388cc6a596f4b477061
baseline_commit: ba5deca19019d3fb718f957aa9d0838fbf2aa895
highest_affected_domain: D4 execution-lifecycle ownership and final candidate-bound acceptance under coherent D3 TRAIN2 admission/backoff architecture
serious_challenge: none
precedence: This review accepts the first-reopen B1 repair and the intended B2 semantic separation, preserves all previously accepted admission/backoff architecture, but supersedes the claimed implementation-complete disposition because the teardown deadline is still applied outside its owning execution scope and final package/dependency acceptance remains incomplete.
---

# MLFF P5 TRAIN2 memory-pressure backoff — second implementation Review reopen

## 0. Disposition

**NO-PASS / REOPENED** under SSDP 6.2.

No Serious Challenge is active. The parent D3 architecture remains coherent and should not be redesigned: live TRAIN2 pressure is an admission/concurrency fact, persistent multi-job soft-envelope pressure retracts one admission, the effective ceiling is monotone downward, the most recently admitted owned job is the deterministic victim, scientific identity is unchanged, and terminal failure remains outside the adaptation loop.

Candidate `46049fed2ff9060895c7ead1d72d8f0389be658c` closes first-review blocker B1 correctly and removes the original optimizer-liveness coupling identified by B2. The candidate-bound tests also materially strengthen failure-path coverage. However, the B2 repair still applies a trainer-owned teardown bound to a broader future that contains work the trainer does not own or cancel. That scope mismatch can manufacture a false terminal resource failure. In addition, the first reopen explicitly required package/dependency acceptance on the repaired candidate; the evidence follow-up records compilation but not those checks.

The remaining repair is therefore **not** another scheduler, watchdog, timeout knob, or retry layer. It is a reduction/narrowing of the existing teardown boundary plus final evidence closure.

## 1. Accepted closures and surfaces to preserve

### B1 is closed

Preserve the explicit execution-owner cancellation outcome:

- `PostSelectionCancelledError` is a narrow subclass of the existing post-selection execution error hierarchy.
- `MacePostSelectionTrainer` raises it only after observing the requested stop and running its normal child termination/finalization path.
- `demote_most_recently_admitted()` requeues only that explicit outcome.
- `future.exception() is None` remains completion-before-stop.
- unrelated backend/runtime/CUDA/programmer failures remain authoritative failures and escape through the existing global terminal path.

The new real-owner race test correctly demonstrates that an independently failing demotion victim is not requeued and that surviving owned work is stopped by terminal cleanup.

### The intended B2 semantic separation is accepted

Preserve these corrected meanings:

- `parallel_training_epoch_activity_timeout_seconds` is optimizer-progress freshness only;
- it must never be a process-teardown deadline;
- teardown timing belongs to the execution/process owner;
- no second operator-facing timeout is justified.

The zero-optimizer-timeout falsification is valuable and must remain.

### Parent-workplan behavior remains accepted

Preserve all previously accepted behavior:

1. soft aggregate VRAM envelope is an admission/backoff boundary, not terminal infeasibility;
2. persistent pressure at `N > 1` produces one-level `N -> N-1` backoff;
3. one owned job over the soft envelope holds rather than fails solely for crossing it;
4. reverse-most-recent-promotion selects exactly one victim;
5. effective concurrency ceiling is execution-local and monotone downward;
6. unaffected active work survives an ordinary backoff;
7. demoted work retains frozen slot/checkpoint identity and is not counted as scientific failure;
8. no replacement/restart is scheduled before the demoted future has actually returned;
9. foreign occupancy constrains mdstats but is never cancellation-owned by mdstats;
10. completed folds remain exactly-once evidence and EVAL2 remains downstream of a successful TRAIN wave;
11. no threshold inflation, second scheduler, retry wrapper, persisted hardware profile, or new scientific identity has been introduced.

The 24.0 GiB / 21.6 GiB / approximately 22.2 GiB deterministic challenge and the controller-level fresh-evidence `3 -> 2 -> 1` cascade remain applicable design evidence, subject to rerun on the final executable candidate after the repair below.

## 2. Blocking finding B4 — the trainer teardown bound is timed against the wrong ownership scope

### Finding

The repaired scheduler resolves:

```python
teardown_bound = getattr(context.trainer, "cancellation_teardown_seconds", None)
```

and, after requesting a backoff, applies that timeout to the **entire submitted future**:

```python
wait((victim_future,), timeout=teardown_bound, return_when=ALL_COMPLETED)
```

But `victim_future` does not represent only `MacePostSelectionTrainer` child supervision. It runs the complete `execute_post_selection_run(...)` path. Before `context.trainer(...)` is entered, `_execute_post_selection_run_locked()` may still be executing:

- `_prepare_post_selection_run()` and continuation/materialization authentication;
- retirement-scratch reconciliation;
- stale checkpoint/materialization detachment when authorized;
- checkpoint-directory creation;
- `materialize_post_selection_run(...)`, including DATA8/export work;
- other run-owned setup preceding the trainer call.

The existing `cancellation_event` is handed onward to the trainer, but these pre-trainer phases do not establish that the trainer has taken ownership of a child process or begun its cancellation-observation loop.

Therefore `MacePostSelectionTrainer.cancellation_teardown_seconds` can only describe the trainer's own **observe-stop -> terminate/reap -> cancellation-finalization** interval. It cannot bound elapsed time from a scheduler stop request to completion of a future that may still be outside the trainer.

A concrete counterexample is admissible under current code:

1. job A is already training;
2. job B has been admitted and is the most recently submitted owned future, but is still preparing/materializing;
3. aggregate live VRAM remains above the soft envelope for the persistence window;
4. the controller correctly requests `2 -> 1` and selects B;
5. the scheduler immediately starts B's trainer-owned teardown clock;
6. B legitimately remains in pre-trainer materialization longer than that bound and has not yet had any opportunity to enter the trainer cancellation path;
7. the scheduler raises `TrainingMemorySafetyError` claiming owned child teardown failed, even though no B child process was yet owned by `MacePostSelectionTrainer` and no trainer teardown contract was violated.

The new tests do not falsify this path: their delayed teardown occurs **inside the substituted trainer**, after the cancellation-aware owner has already been entered. The structural test proves that optimizer freshness is no longer used, but it does not prove that the new deadline's scope matches the future being timed.

### Why this blocks

This is the same one-owner/one-meaning issue as first-review B2 at a narrower boundary. The timeout's *name* and source are now correct, but its **application scope is broader than its authority**.

It violates:

- INV-3: a terminal teardown failure must be independent authoritative evidence, not elapsed time spent in an unrelated pre-trainer phase;
- INV-6: the scheduler must prove the actual owned lifecycle before reuse, but may not call a lifecycle failed before that owner has begun it;
- SSDP 6.2 ownership doctrine: an execution sub-owner's contract cannot govern sibling/ancestor work merely because both execute inside one future;
- the first-reopen acceptance condition that the teardown deadline cannot expire before the owned trainer's legitimate terminate/reap lifecycle.

The defect can recreate the original user-visible failure shape: feasible work is terminated by a controller-side resource error even though the actual lower-concurrency training remains feasible.

### Required repair

Repair the existing ownership flow. **Do not add another scheduler, watchdog, retry manager, user-facing timeout, queue, or persistent state.**

The preferred reduction is:

1. **Remove the trainer-derived finite timeout from `demote_most_recently_admitted()` as a deadline on the whole run future.** The scheduler already has the correct safety barrier: no replacement is admitted until the victim future returns. Waiting for the complete owned future is semantically correct even when that future is still before the trainer.
2. Keep explicit `PostSelectionCancelledError` classification exactly as repaired for B1.
3. Let bounded process termination remain inside the execution/process owner. If production MACE teardown requires a finite failure verdict, enforce/emit that verdict at the `MacePostSelectionTrainer` / `_terminate_post_selection_process` ownership boundary that actually owns the subprocess. The scheduler should receive the resulting cancellation or failure outcome from the future rather than impose a trainer clock on ancestor work.
4. If `cancellation_teardown_seconds` has no owner-local consumer after this reduction, remove it rather than preserving dead policy surface solely for the scheduler.
5. The existing `cancellation_event` may be checked at safe run-phase boundaries to avoid starting unnecessary work after an already-requested demotion, **but only by rewiring the existing signal through the existing run path**. Do not create a second cancellation mechanism. Any pre-trainer cancellation outcome must leave the run root recoverable under the existing materialization/checkpoint authority and must not publish partial fold evidence.
6. Do not weaken the teardown barrier: a demoted slot still cannot be requeued/restarted until its full future has returned, and GPU telemetry must still be re-observed before subsequent admission.

An alternative implementation is acceptable only if it genuinely aligns the finite timer with the exact cancellation-aware owner interval. Merely renaming/moving the current value while continuing to time the complete run future does not close B4.

### Required falsification

Add a bounded real-owner test that distinguishes **pre-trainer work** from trainer teardown:

- run two owned slots and reach persistent soft pressure;
- hold the most-recently-admitted victim in an existing pre-trainer preparation/materialization seam for longer than the production trainer's nominal cancellation-teardown bound, or otherwise make the phase ordering deterministic without replacing the scheduler/run owner;
- request `2 -> 1` while that victim is still pre-trainer;
- prove no false `TrainingMemorySafetyError` is raised merely because trainer ownership has not begun;
- prove no replacement admission occurs while the victim future is still alive;
- after the victim reaches an existing cancellation-aware boundary, prove it terminates/requeues through the explicit cancellation outcome (or completes before cancellation) without publishing partial CV evidence;
- retain the existing independent-failure race test, zero optimizer-freshness test, and positive 24/21.6/22.2 challenge.

The test double may bound expensive DATA8/MACE work below the real scheduler/run owner, but it must not bypass the ownership boundary under test.

## 3. Blocking finding B5 — the first-reopen package/dependency acceptance obligation remains unexecuted

### Finding

Evidence follow-up `80c2fc8d7cfcfb07a25bffa1f527887590872571` records substantial candidate-bound execution:

- focused backoff suite: 11 passed;
- controller + zero-safe-admission suites: 57 passed;
- 41 affected suites: 1316 passed, 3 failed, 1 skipped;
- architecture documentation specification: 9 passed;
- `python -m compileall mdstats` and edited-module imports: clean;
- physical-GPU qualification explicitly deferred under the standing final-release policy.

The three affected-suite failures are reported as reproducing byte-identically on the stashed baseline and concern unrelated pre-existing assertions (`0.20.140a0` identity text, retired OPT-CTRL1 roadmap text, and the already-authorized `--restart_latest` continuation seam). They are not attributed to this backoff candidate. The one target-host LAMMPS/MACE callback skip is likewise outside the changed TRAIN2 backoff semantics and remains part of the standing target-machine qualification surface.

However, first-review B3 explicitly required the ordinary **compilation/package/dependency** checks used by current mdstats acceptance practice after executable edits. The implementation response records compilation only. It does not record the established mdstats checks:

```text
conda run -n mace pip check
conda run -n mace python -m build --wheel --no-isolation
```

The immediately preceding accepted MLFF candidate used those exact dependency-integrity and package-build checks in its functional acceptance record. Under SSDP 6.2, a required check that did not execute is not a pass.

Because B4 requires another executable edit, the current focused/affected results will also become stale for the final repaired subject. Final closure therefore needs one new candidate-bound acceptance realization after the B4 repair rather than accumulating another partial evidence amendment.

### Required evidence

On the final repaired executable candidate, record commit/tree/clean-state identity, exact commands, exit status, and observations for:

1. the focused backoff suite, including the new pre-trainer cancellation-scope falsification;
2. `tests/test_mlff_training_parallel_scheduler.py` and `tests/test_mlff_p5_train2_zero_safe_admission.py`;
3. the materially affected post-selection TRAIN2/CV/restart/failure-propagation/cancellation/EVAL2/CUDA-lifetime surface used in the first implementation response;
4. the assembled 24.0/21.6/22.2 GiB deterministic real-owner challenge;
5. architecture-document specification checks if documentation changes again;
6. `python -m compileall mdstats tests` (or the repository's equivalent final compile check);
7. `conda run -n mace pip check`;
8. `conda run -n mace python -m build --wheel --no-isolation`.

If the three known baseline-identical affected-suite failures remain, preserve their baseline comparison/provenance rather than modifying product code or weakening tests for this cycle. If their identity changes, reassess them instead of assuming continued irrelevance.

Physical-GPU CUDA-lifetime qualification remains permitted to be **explicitly deferred** to the consolidated final-release GPU qualification package under project policy. Do not relabel deterministic telemetry fixtures as physical GPU evidence.

## 4. Challenge and global-invariant assessment

### Serious Challenge

**None.** The accepted D3 architecture remains adequate and jointly realizable. The new finding is a D4 owner-scope mismatch, not evidence that the admission/backoff architecture is wrong.

### Core problem of concern

The original concern remains correctly framed: when aggregate live memory disproves concurrency `N`, the system must reduce mdstats-owned concurrency rather than declare the scientific training workload infeasible.

Candidate `46049fed` solves the major failure-classification problem and preserves this architecture. B4 matters because a false teardown timer can still convert a valid concurrency backoff into terminal failure for a victim that has not reached the timed owner. The repair must therefore make the existing lifecycle boundaries honest, not add another recovery mechanism.

### High-level architecture after repair

Keep the existing flow:

```text
live TRAIN2 telemetry
  -> AdaptiveTrainingConcurrency
  -> ADMIT / HOLD / one-step BACKOFF
  -> scheduler requests stop on exactly one existing owned future
  -> existing run/execution owner reaches completion / explicit cancellation / genuine failure
  -> full future quiescence is the scheduler reuse barrier
  -> re-observe device
  -> existing pending/checkpoint authority
```

Process-specific termination timing belongs inside the process owner. Terminal/global abort remains outside the adaptation loop.

## 5. Re-review acceptance gate

A subsequent SSDP 6.2 Review may PASS only when one final candidate-bound state establishes all of the following:

1. first-review B1 remains closed: only the explicit cooperative-cancellation outcome is demotion-requeueable;
2. B4 is closed: no trainer/subprocess teardown deadline is applied to pre-trainer/ancestor work outside its ownership scope;
3. a deterministic pre-trainer backoff falsification demonstrates that slow preparation/materialization cannot manufacture a teardown failure;
4. the victim's full future still quiesces before requeue/restart and device re-observation remains before subsequent admission;
5. all parent-workplan behaviors remain conforming: soft-boundary backoff, one-step cascade, LIFO victim, monotone ceiling, survivor preservation, single-job hold, foreign occupancy ownership, exactly-once restart/accounting, and genuine hard-failure propagation;
6. final focused + affected + assembled evidence is bound to the post-B4 executable candidate;
7. dependency integrity and wheel build checks required by B5 pass and are recorded;
8. documentation/current history remain aligned with the final ownership semantics; generated documentation is refreshed if its source changes;
9. physical-GPU qualification is either recorded or explicitly deferred under the standing final-release qualification policy;
10. no D1/D2 scientific method, labels/replay semantics, fold/seed membership, horizons, checkpoint identity, EVAL2 authority, or publication semantics change;
11. no new scheduler, watchdog, retry wrapper, timeout configuration surface, duplicate queue, or persistent tuning state is introduced.

Until these conditions are satisfied, the parent workplan remains **NO-PASS / REOPENED**.

---

## 6. Implementation response — B4/B5 closure

**Executable candidate:** `04bd758b` (tree `fbc3bdfef2a69df9e6debfb5ffb5606ec6936823`), clean working tree, branch `fix/mlff-p5-train2-memory-pressure-backoff`.

### B4 repair (reduction, not re-timing)

- `demote_most_recently_admitted()` now waits `wait((victim_future,), return_when=ALL_COMPLETED)` with **no timeout of any provenance**. `teardown_bound` and its `TrainingMemorySafetyError` branch are deleted. The full-future quiescence barrier, which was already the correct reuse boundary, is the only barrier.
- `MacePostSelectionTrainer.cancellation_teardown_seconds` had no owner-local consumer after that removal and is **deleted**, not kept as dead policy surface. `_terminate_post_selection_process` is documented as the sole owner of child-termination timing; it is bounded by construction (SIGINT, grace, SIGTERM, grace, unconditional SIGKILL + reap).
- The existing per-slot `cancellation_event` is now read at two pre-trainer run-phase boundaries through one helper, `_abort_post_selection_run_if_cancelled`: at run entry and immediately before `context.trainer(...)`. It raises the existing `PostSelectionCancelledError`, so the scheduler classifies it as an ordinary retractable demotion. No second cancellation mechanism, no new event, no new error type, no new configuration key.
- Nothing was added: no scheduler, watchdog, retry wrapper, timeout knob, queue, or persistent state. Net product change is `-24 / +30` lines, most of it comment.

### B4 falsification

`test_a_pre_trainer_victim_is_demoted_without_a_false_teardown_failure` drives the real `execute_post_selection_cross_validation`, the real controller, scheduler and run owner. Only the device probe and MACE numerics are bounded, plus a delegating wrapper that delays the second admitted run's entry into the real run body. It proves, on one execution: `backoff 2->1` occurs; the victim owned no trainer entry at the moment it observed its stop; no `did not quiesce` verdict; `post-demotion` device re-observation precedes any further admission; the victim's second run-body call starts only after its first returned and its single trainer entry belongs to that restart; both folds complete exactly once and acceptance publishes.

Replacements at the correct owners:

- `test_the_process_owner_bounds_its_own_termination_of_a_deaf_child` — a real child process ignoring SIGINT and SIGTERM is still reaped by `_terminate_post_selection_process` inside its own escalation. This replaces the retired scheduler-side terminal-teardown test, whose claim B4 invalidated.
- `test_the_demotion_barrier_imposes_no_deadline_on_the_owned_future` — structural/negative evidence that the barrier contains no `timeout`, no `teardown_bound`, no cadence, and that `cancellation_teardown_seconds` is absent from both owning modules.

Retained unchanged: the independent-failure race test, the zero-optimizer-freshness falsification, and the 24.0 / 21.6 / approximately 22.2 GiB deterministic challenge.

### Pre-existing fixture race, root-caused and fixed

`tests/test_mlff_p5_train2_memory_backoff.py::test_backoff_from_three_demotes_the_third_admitted_job` failed under CPU load with `TRAIN2 continuation has no persisted MACE execution evidence`. Attribution: on the **stashed baseline tree** it reproduces **2 of 6** runs under the same injected load (repeated twice). Cause: the stand-in TRAIN2 child publishes its launch authority through process-global `patch.dict(os.environ, ...)` while several scheduler threads run concurrently, so one child restores the environment a sibling had just published and that sibling's `_Train2Runtime` reads no evidence. The fix serializes only that publication window (`_CHILD_AUTHORITY_ENVIRONMENT_LOCK` entered on the existing `ExitStack`); the training loop stays concurrent. After the fix: **6 of 6** pass under the identical load. No assertion was weakened and no product code was changed for it.

### Evidence actually executed

All from the repository root, `conda run -n mace`, candidate `04bd758b`.

| # | Command | Result |
| --- | --- | --- |
| 1 | `python -m pytest tests/test_mlff_p5_train2_memory_backoff.py -q -p no:randomly` | **12 passed**, exit 0, 126.71s |
| 2 | `python -m pytest tests/test_mlff_training_parallel_scheduler.py tests/test_mlff_p5_train2_zero_safe_admission.py -q -p no:randomly -n 8` | **57 passed**, exit 0, 67.81s |
| 3 | 45 affected suites (every `tests/*.py` referencing `campaign_post_selection_runtime`, `post_selection_execution`, `training_parallel`, or the shared post-selection fixture, plus the architecture specification suite), `-q -p no:randomly -n 16` | **1394 passed, 3 failed, 1 skipped**, 1679.63s |
| 4 | `python -m pytest tests/test_mlff_doc_arch1_specification.py -q -p no:randomly` (also inside item 3) | **9 passed**, exit 0 |
| 5 | `python -m compileall -q mdstats tests` | exit 0 |
| 6 | `conda run -n mace pip check` | `No broken requirements found.`, exit 0 |
| 7 | `conda run -n mace python -m build --wheel --no-isolation` | exit 0, `dist/mdstats-0.20.242a0-py3-none-any.whl` |
| 8 | Baseline-vs-candidate load reproduction of the fixture race (6 runs each) | baseline 4 pass / 2 fail (x2 independent trials); candidate 6 pass / 0 fail |

Item 3's three failures are the same pre-existing, unrelated drift recorded for the previous candidate, with unchanged identity: `test_opt_ctrl1_release_identity_preserves_scientific_compatibility` (pinned `0.20.140a0` text), `test_opt_ctrl1_architecture_and_spec_close_roadmap` (retired OPT-CTRL1 roadmap text), `test_p5f_no_screening_continuation_owner_is_reachable_from_post_selection` (the authorized `--restart_latest` seam). The previous candidate's fourth observed failure, the three-job backoff test, is resolved by the fixture repair above. The one skip is the standing `UNAVAILABLE/BLOCKING` LAMMPS/MACE callback on this host.

### Documentation

`docs/arch_manuals/mlff_training_data/60_execution_performance.md` now states that the scheduler imposes no deadline on the demoted future, that child termination is bounded inside the process owner, and that the same stop handle is read at pre-trainer boundaries as the one cancellation mechanism. `docs/history/mlff/train2_admission_evolution.md` records the scope defect and its reduction. The assembled `mlff_training_data_architecture.md` was regenerated with `tools/build_mlff_architecture_manual.py`; the PDF and manifest are regenerated by `docs-build.yml` in CI, as pandoc/typst are not installed on this workstation.

### Qualification

Physical-GPU CUDA-lifetime qualification remains **explicitly deferred** to the consolidated final-release GPU qualification package under the standing project policy. All telemetry in the evidence above is deterministic fixture telemetry and is not labelled physical GPU evidence.
