---
kind: implementation-workplan-final-review-closure
workplan_id: CODE-MLFF-P5-TRAIN2-MEMORY-PRESSURE-BACKOFF-FINAL-REVIEW-CLOSURE
parent_workplan: workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_REPAIR_WORKPLAN.md
predecessor_reviews:
  - workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FIRST_REVIEW_REOPEN.md
  - workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_SECOND_REVIEW_REOPEN.md
protocol_version: 6.2
status: closed-pass
review_verdict: pass
implementation_branch: fix/mlff-p5-train2-memory-pressure-backoff
baseline_commit: ba5deca19019d3fb718f957aa9d0838fbf2aa895
executable_candidate: 04bd758b3f72ae021d4d84cceeef4ab11540f63c
executable_tree: fbc3bdfef2a69df9e6debfb5ffb5606ec6936823
evidence_commit: 745d8b25455d02f3a39205b0eb771d034434c505
evidence_tree: 7734fe6949d90b12a2f6adb47efe3e8adaee8380
assembled_candidate: 8809f054df49bb24abb9f79572928585a44ba65e
assembled_tree: 455901ac02d86a0e48ebe5a4806c4e76fff018ac
highest_affected_domain: D4 concurrency/resource supervision under accepted D3 TRAIN2 admission/backoff architecture
serious_challenge: none
precedence: This final independent SSDP 6.2 Review supersedes the active/reopened lifecycle status recorded inside the archived parent and predecessor review snapshots. The workplan is closed PASS. Current TRAIN2 architecture is owned by the Architecture Manual; these workplan/review artifacts are historical coordination and evidence records.
---

# MLFF P5 TRAIN2 memory-pressure backoff — final SSDP 6.2 Review closure

## 0. Disposition

**PASS / CLOSED** under SSDP 6.2.

No Serious Challenge is active. The accepted D3 correction remains coherent and the final D4 candidate conforms: excessive mdstats-owned TRAIN2 concurrency is repaired by bounded one-step concurrency backoff rather than by declaring the scientific workload infeasible; the soft VRAM envelope remains a control boundary; hard failures retain independent semantics; full owned-future quiescence precedes reuse; and the scientific method/evidence identity is unchanged.

The second-review blockers B4 and B5 are closed on executable candidate `04bd758b3f72ae021d4d84cceeef4ab11540f63c`. Later commits only record candidate-bound evidence and regenerate documentation PDF/manifest; no later executable edit invalidates that realization.

## 1. Review authority and scope

This review reconstructed and challenged:

- the parent memory-pressure backoff workplan and INV-1 through INV-9;
- the first review/reopen B1-B3;
- the second review/reopen B4-B5;
- the non-conflicting TRAIN2 CUDA-lifetime/zero-safe-admission authority;
- `training_parallel.AdaptiveTrainingConcurrency`;
- `campaign_post_selection_runtime._execute_post_selection_pending_runs()` and the run owner beneath it;
- `post_selection_execution.MacePostSelectionTrainer` and `_terminate_post_selection_process()`;
- real-owner deterministic backoff, failure, restart, phase-boundary, and teardown tests;
- the Architecture Manual and TRAIN2 admission semantic history;
- candidate-bound compilation, dependency, wheel-build, and generated-document evidence.

The review tested the assembled candidate rather than accepting implementer summaries or the latest diff alone.

## 2. Blocking findings — all closed

### B1 — arbitrary child exception reclassified as demotion: CLOSED

`PostSelectionCancelledError` remains the only retryable/requeueable cancellation outcome. A demotion victim that instead raises an unrelated backend/runtime/CUDA/programmer failure is counted as failed and propagates through the existing terminal/global cleanup path. The multi-job race falsification proves no requeue, no second attempt, remaining owned work cleanup, and no CV acceptance.

### B2/B4 — teardown timeout ownership/scope: CLOSED

The repaired candidate removes the scheduler-side finite timeout entirely from the whole run future. This is the correct reduction:

- `demote_most_recently_admitted()` requests the existing per-slot stop and waits for the full victim future with no scheduler deadline;
- no optimizer-liveness cadence, controller cadence, or trainer-derived subprocess bound times ancestor/pre-trainer work;
- subprocess termination timing remains solely inside `_terminate_post_selection_process()` through the existing SIGINT -> grace -> SIGTERM -> grace -> SIGKILL/reap path;
- the retired `cancellation_teardown_seconds` policy surface is removed rather than left as dead machinery;
- the same existing cancellation event is observed at recoverable run-entry and pre-training boundaries, avoiding unnecessary work without creating a second cancellation mechanism;
- the victim future must return before active ownership is removed, the device is re-observed, and any restart/admission can occur.

The new pre-trainer falsification selects the most-recently-admitted victim while it has not entered the trainer, reaches real `2 -> 1` backoff, observes the stop without any child ownership, produces no false teardown failure, permits no replacement while the first future remains alive, and completes both folds exactly once after ordinary requeue/restart.

### B5 — package/dependency/final candidate evidence: CLOSED

The final executable candidate has candidate-bound evidence for focused behavior, affected regression, compilation, dependency integrity, and wheel build. Physical-GPU CUDA-lifetime qualification remains explicitly deferred to the consolidated final-release qualification package under standing project policy and is not misrepresented by deterministic fixture telemetry.

## 3. Parent invariant assessment

- **INV-1 minimum-concurrency feasibility — PASS.** Multi-job soft pressure reduces owned concurrency; soft pressure alone at one owned job holds rather than manufactures terminal infeasibility.
- **INV-2 soft admission envelope — PASS.** The configured aggregate VRAM envelope governs admission/hold/backoff and does not itself become a scientific/execution verdict.
- **INV-3 hard failure independence — PASS.** Backend/device failures, resource-observability failures, and owning-layer teardown/reclamation failures remain outside the soft-pressure adaptation loop and retain causal terminal semantics.
- **INV-4 failure scope — PASS.** Ordinary concurrency pressure demotes one owned victim and preserves unaffected work.
- **INV-5 deterministic demotion — PASS.** Reverse-most-recent-promotion remains the sole victim rule.
- **INV-6 teardown before reuse — PASS.** The full owned future is the scheduler reuse barrier; device telemetry is re-observed only after that future returns.
- **INV-7 monotone disproven concurrency — PASS.** Execution-local effective ceiling cannot re-enter a live-telemetry-disproven level.
- **INV-8 scientific semantics unchanged — PASS.** No target-size, label/replay, fold/seed, horizon, checkpoint, EVAL2, evidence-ranking, acceptance, or publication identity is changed.
- **INV-9 estimates advisory/live telemetry authoritative — PASS.** Optimistic per-job estimates trigger runtime adaptation rather than failure merely for being wrong.

## 4. Required challenge/falsification coverage

The final candidate preserves and/or adds evidence for:

- persistent `2 -> 1` pressure backoff at 24.0 GiB total / 21.6 GiB soft envelope / approximately 22.2 GiB aggregate live use;
- fresh-evidence cascaded `3 -> 2 -> 1` controller behavior;
- single-job soft-pressure hold;
- transient spike tolerance;
- deterministic LIFO victim selection at two and three jobs;
- no re-promotion after a disproven level;
- exactly-once accounting and checkpoint/restart after partial work;
- foreign occupancy constraining admission without foreign-process ownership;
- unreclaimed aggregate pressure causing lower-concurrency re-evaluation rather than blind replacement;
- authoritative child failure racing demotion and remaining terminal;
- zero optimizer-activity timeout having no teardown authority;
- absence of any scheduler-side deadline on the whole owned future;
- a genuine pre-trainer demotion boundary with no false teardown failure;
- real process-owner SIGINT/SIGTERM/SIGKILL escalation/reap evidence.

No falsification produced a counterexample to the accepted D3 architecture.

## 5. Candidate-bound acceptance evidence

Recorded against executable candidate `04bd758b` / tree `fbc3bdfef2a69df9e6debfb5ffb5606ec6936823`:

1. `tests/test_mlff_p5_train2_memory_backoff.py` — **12 passed**, exit 0.
2. `tests/test_mlff_training_parallel_scheduler.py tests/test_mlff_p5_train2_zero_safe_admission.py` — **57 passed**, exit 0.
3. 45 materially affected suites — **1394 passed, 3 failed, 1 skipped**. The three failures preserve the same pre-existing unrelated identities previously reproduced on the baseline: stale pinned OPT-CTRL1 release text, retired OPT-CTRL1 roadmap text, and the already-authorized `--restart_latest` continuation seam. The standing host-unavailable LAMMPS/MACE callback remains outside this TRAIN2 backoff semantic change and is retained for target-machine qualification rather than hidden or rewritten.
4. Architecture specification suite — **9 passed**, exit 0.
5. `python -m compileall -q mdstats tests` — exit 0.
6. `conda run -n mace pip check` — **No broken requirements found**, exit 0.
7. `conda run -n mace python -m build --wheel --no-isolation` — exit 0; wheel built successfully.
8. The pre-existing shared-fixture environment race was reproduced on the stashed baseline under load and corrected only in test machinery by serializing the process-global environment publication window; training itself remains concurrent. This does not change product semantics or mask a product failure.
9. Documentation-PDF CI on evidence commit `745d8b25455d02f3a39205b0eb771d034434c505` completed successfully and produced the assembled documentation-only head `8809f054df49bb24abb9f79572928585a44ba65e`.

The two commits after `04bd758b` change only the second-review evidence record and generated PDF/manifest, so the functional evidence remains applicable to the final executable subject.

## 6. Architecture and complexity assessment

The final solution is the preferred reduction/rewiring:

```text
live TRAIN2 telemetry
  -> existing AdaptiveTrainingConcurrency
  -> ADMIT / HOLD / one-step BACKOFF
  -> existing per-job stop handle
  -> existing run/execution owner
  -> completion / explicit cancellation / genuine failure
  -> full future quiescence
  -> re-observe device
  -> existing pending/checkpoint authority
```

Process-specific termination remains inside the process owner. Terminal/global abort remains outside the adaptation loop.

No new scheduler, watchdog, retry manager, timeout configuration surface, queue, persistence schema, hardware profile, checkpoint identity, or scientific fallback was introduced. The second-review repair specifically removes a wrongly scoped timeout rather than compensating for it with another mechanism.

## 7. Documentation and residual nonblocking note

The Architecture Manual is aligned with the final behavior: soft-boundary backoff, per-job ownership, unbounded whole-future scheduler barrier, process-owner child termination, pre-trainer use of the same stop handle, monotone effective ceiling, hard-failure separation, and unchanged scientific semantics are all represented. Generated Markdown/PDF/manifest state is current.

One **nonblocking wording drift** remains in the internal `PostSelectionCancelledError` docstring: it describes the outcome as an owned child having been reaped, while the now-valid pre-trainer cancellation path can raise the same explicit retractable-cancellation type before a child exists. Runtime semantics are unambiguous and safe—the type means the current attempt ended because the caller's cooperative stop was authoritatively observed and no live child remains—but the docstring is narrower than its valid call-site domain. This does not justify reopening the completed resource repair or introducing another exception type. It may be generalized in ordinary maintenance without changing behavior.

## 8. Qualification disposition

Real physical-GPU CUDA-lifetime qualification is **deferred** to the consolidated final-release GPU qualification package under standing project policy. The deterministic resource tests are functional/controller evidence only and are not claimed as physical CUDA evidence.

This deferral is an explicit remaining release-qualification obligation, not an implementation blocker for this workplan.

## 9. Final closeout

**PASS. No third reopen.**

The parent workplan and both review/reopen snapshots are closed and archived with this record. Current architecture lives in the Architecture Manual; semantic history records why the hard whole-wave interpretation was replaced. Future work must reopen this architecture only if new evidence falsifies one of the accepted invariants above, such as a real owner-lifetime leak, an actual lower-concurrency infeasibility, or a contradiction between process teardown and observed CUDA lifetime.
