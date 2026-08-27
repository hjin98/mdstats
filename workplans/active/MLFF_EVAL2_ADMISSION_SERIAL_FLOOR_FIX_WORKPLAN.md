# MLFF_EVAL2_ADMISSION_SERIAL_FLOOR_FIX — MLFF EVAL2 adaptive-admission serial-floor fix

**Status:** active  
**Current authority:** `mdstats/training_data/inference_parallel.py`, `mdstats/training_data/_campaign_cli_core.py`, and the accepted MLFF architecture/specification set on `main`  
**Target branch/base:** `fix/mlff-eval2-admission-serial-floor` from `main@efa8b1b206f75f687ec9b2fb738cfcc089401d68`  
**Owner:** implementation agent  
**Qualification policy:** implementation acceptance is functional unit/regression/integration evidence only. Full production GPU/resource/performance qualification remains release-closeout work and is not part of this implementation cycle.

## Objective

Repair EVAL2 adaptive CUDA admission so that soft GPU-utilization and VRAM safety envelopes regulate **additional concurrency** without falsely proving that a successfully executable single inference job is globally inadmissible.

The observed failure occurs after an uncached one-slot CUDA calibration job completes successfully. Its measured demand crosses the configured 90% GPU-utilization and/or soft VRAM envelope, the controller converts that soft limit into target concurrency `0`, and the scheduler raises:

> `Evaluation resource admission blocked with 1 queued inference task(s): measured single-job CUDA demand exceeds the configured VRAM or GPU-utilization envelope; no future inference job is admissible.`

That is an ownership/semantic error. A completed CUDA job is direct evidence that serial execution of the applicable job/resource profile is viable. Crossing a soft parallel-expansion envelope should therefore cap concurrency at one, not transform successful execution into terminal infeasibility.

The repair must establish a robust **serial floor** while preserving adaptive concurrency greater than one whenever measured headroom safely allows it.

## Current-state evidence and root cause

The failing EVAL2 run has the following material sequence:

1. CUDA resource policy reports an RTX 3090 with approximately 21.6 GiB VRAM admission budget, a 90% utilization ceiling, and an inferred worker ceiling of 24.
2. Cached `n512-seed1` and `n512-seed2` results are reused.
3. The first uncached `n1024-seed1` task launches alone as CUDA calibration and completes successfully after approximately 666.8 s with a valid RMSE result.
4. Before `n1024-seed2` launches, adaptive admission reports no future job admissible and aborts the queue.
5. The queued second task therefore never receives an execution attempt. Later TorchScript warnings are unrelated to this admission failure.

The current `main` source confirms several distinct paths that conflate soft expansion limits with single-job execution viability:

- `build_inference_concurrency_plan(...)` rejects a CUDA plan before calibration when `baseline_used + estimated_job * margin` exceeds the **fractional VRAM admission ceiling**, even though that ceiling is a soft concurrency/safety envelope rather than physical device-memory proof.
- `_finish_cuda_calibration()` computes `safe_jobs` beginning at zero and can set `target_jobs = 0` after a successfully completed calibration solely because the one-job projection crosses a soft utilization or VRAM ceiling.
- `_observe_cuda(...)` can set `target_jobs = 0` during calibration when measured one-job VRAM crosses the configured fractional ceiling.
- Post-calibration live-VRAM logic can also set `target_jobs = 0` when live aggregate/reservation projections cross the same soft ceiling.
- The scheduler subsequently interprets controller zero-capacity/blocked state as proof that **no future inference job** can run, rather than distinguishing temporary zero additional capacity from terminal execution infeasibility.

The earliest violated invariant is therefore not scientific ranking logic. It is admission-state ownership: **target concurrency**, **instantaneous additional launch capacity**, and **actual execution failure** are being represented/interpreted as though they were the same state.

## Final design review and frozen corrections

The final review closes the following gaps before implementation:

1. A controller-global `HARD_BLOCKED` concept is rejected as too broad. Actual execution failure remains execution-owned and task/profile scoped unless current architecture demonstrably requires a typed scoped failure state.
2. **Target/effective concurrency** is distinct from **instantaneous additional launch capacity**. Target `1` with one active job naturally means zero additional slots until that job completes.
3. Zero additional capacity while work is active is ordinary saturation/backpressure, not terminal infeasibility.
4. An explicit idle **serial-floor invariant** is required.
5. `maximum_jobs == 1` is a first-class valid operating mode and must have dedicated regression coverage.
6. Cached evaluation results alone do not establish current CUDA execution viability; the first real CUDA execution remains calibration authority unless an existing explicit warm-observation contract says otherwise.
7. Downshift with multiple active jobs must not cancel already running work; only future launches are gated.
8. Reservation/live-VRAM accounting must not create an idle self-deadlock.
9. Public/test-facing `AdaptiveInferenceConcurrency` compatibility must be preserved where practical; do not force an API redesign merely to implement the semantic repair.
10. Adaptive safe ramp above one must remain functional; this fix must not globally serialize EVAL2.
11. A newly surfaced **preflight false-terminal path** must be repaired as part of the same change: a one-job estimate crossing the soft VRAM fraction cannot by itself prove CUDA execution impossible.
12. Host-RAM admission semantics are not automatically softened by this design. Preserve existing genuine host-memory safeguards unless implementation inspection proves they are also merely parallel-expansion policy.

## Governing invariants

The implementation is accepted only if all of the following hold:

1. Soft GPU-utilization and fractional VRAM thresholds regulate **additional concurrency**, not whether one otherwise viable CUDA job may execute.
2. If CUDA work is queued, no inference job is running, the device path is available, and no actual execution failure applies to the queued job/profile, at least one job is launchable.
3. A successfully completed one-slot calibration proves serial viability for its applicable job/resource profile.
4. Successful calibration above a soft utilization or VRAM ceiling results in effective target concurrency `1`, never `0`.
5. `additional_capacity == 0` while one or more jobs occupy the target is transient saturation and must cause wait/re-evaluation, not a terminal error.
6. `maximum_jobs == 1` remains ordinary valid fixed-serial CUDA operation even when soft telemetry exceeds configured expansion thresholds.
7. Terminal inference failure requires actual execution-failure evidence (for example CUDA OOM/device execution failure) or explicit device/resource unavailability, not soft headroom exhaustion.
8. Failure evidence remains scoped to the failed task/profile unless current scheduler semantics already justify a broader scope; heterogeneous queued models must not be globally rejected from one profile's failure without evidence.
9. Cached result reuse does not, by itself, prove current CUDA viability.
10. Existing GPU-utilization and VRAM fraction values remain unchanged as expansion safety limits.
11. Running jobs survive controller downshift. No new launch occurs until active count falls below the new target.
12. Target-size scientific ranking, fidelity, checkpoint selection, and result semantics are unchanged.
13. Live VRAM/reservation accounting cannot reduce an idle, execution-viable queue to a terminal zero-capacity state solely from the soft fractional envelope.
14. Safe adaptive ramp above one remains available when calibration and live resource evidence support it.
15. CPU fallback and existing host-RAM safety behavior remain unchanged unless directly required by evidence found at G0.

## Architecture and ownership contract

### `mdstats/training_data/inference_parallel.py`

The adaptive controller owns:

- effective/target concurrency;
- interpretation of soft GPU utilization and VRAM telemetry;
- measured per-job estimates;
- reservations/headroom accounting;
- instantaneous **additional** launch capacity;
- nonterminal reasons for holding, throttling, or serial fallback.

It does **not** own proof that a job that has never executed will necessarily OOM merely because a fractional safety envelope is crossed.

Required behavior:

- CUDA initial execution remains one-slot calibration.
- On successful calibration, effective target is always at least one when `maximum_jobs >= 1` and no actual device/execution failure exists.
- If one-job utilization/VRAM exceeds soft thresholds, calibration records that evidence and caps further expansion at one.
- Pre-calibration one-job VRAM estimate crossing the fractional admission budget must select a conservative serial/calibration posture rather than throw solely on that soft fraction. Actual execution remains authoritative for true CUDA OOM.
- Live VRAM/reservation checks apply to launching **additional** work. They may temporarily return zero additional slots while active work/reservations consume capacity, but cannot permanently self-block an idle queue solely from the soft fraction.
- Warm/prewarmed observation paths, if retained, must obey the same serial-floor semantics and cannot set target zero solely from soft telemetry.
- Low-utilization/headroom cases must still ramp toward `maximum_jobs` under the existing adaptive policy.
- Preserve existing public properties/call shapes when feasible. A structured authoritative admission snapshot may be introduced only if it materially reduces duplicated interpretation while maintaining compatibility.

### `mdstats/training_data/_campaign_cli_core.py`

The EVAL2 scheduler owns:

- queue lifecycle;
- active task lifecycle;
- waiting/re-evaluation after completions;
- execution outcomes;
- terminal/retry behavior under existing campaign semantics.

Required behavior:

- Distinguish `target full / no additional slot` from `no job can ever execute`.
- If active jobs occupy the target, wait for completion and reevaluate.
- If soft telemetry prevents another **concurrent** job, continue serially once the active slot is free.
- If the queue is idle with queued CUDA work and no applicable actual execution failure, launch one.
- `_ensure_schedulable` or equivalent logic must not raise the current "no future inference job is admissible" error solely from controller soft-limit state after successful calibration.
- Actual job execution failure continues through existing terminal/retry semantics and must not be hidden by the serial-floor repair.
- Where possible, consume one authoritative controller admission decision rather than independently reconstructing resource semantics from raw telemetry.

## Failure semantics

Do not predict a true CUDA OOM solely from the 90% utilization policy or fractional VRAM safety budget. These are preventive expansion limits.

Actual CUDA allocation/OOM/device failures remain execution failures. The implementation must preserve the existing failure propagation/retry behavior for such cases. If failure typing is strengthened, it must be scoped to the failing task/resource profile and justified by current interfaces rather than introducing a controller-global terminal state by default.

A serial-floor attempt may therefore expose a genuine runtime OOM that previous soft preflight would have predicted. That is acceptable and preferable: the runtime failure is authoritative evidence, whereas the soft fractional threshold is not.

## Diagnostics contract

Progress/error messages must distinguish at least:

- serial fallback because the soft GPU-utilization/VRAM envelope does not permit safe parallel expansion;
- temporary zero additional capacity because active jobs/reservations occupy available slots;
- actual CUDA execution/device failure.

The phrase `no future inference job is admissible` may only remain reachable where real terminal evidence exists. It must not be emitted from soft telemetry alone.

## Scope

Expected directly affected production surface:

- `mdstats/training_data/inference_parallel.py`
- `mdstats/training_data/_campaign_cli_core.py`

Expected affected acceptance surface:

- all tests consuming `build_inference_concurrency_plan`, `AdaptiveInferenceConcurrency`, calibration/finalization hooks, prewarm/warm observation, reservation/admission helpers, and scheduler schedulability logic;
- EVAL2 cached + uncached queue integration;
- target-size selection integration through EVAL2 far enough to prove ranking/materialization continues unchanged;
- diagnostics/help/comments that currently describe the 90%/VRAM envelope as single-job execution prohibition.

G0 must inventory the exact files/functions/tests before edits; this list is intentionally an affected-surface starting point, not permission to ignore discovered consumers.

### Non-goals

- Do not raise or remove the 90% GPU-utilization limit.
- Do not change default VRAM fraction values.
- Do not change target-size ranking, scientific fidelity, checkpoint authority, or size-selection policy.
- Do not redesign EVAL2 broadly.
- Do not introduce a new inference batching strategy.
- Do not rewrite the global resource model.
- Do not globally serialize CUDA inference as a workaround.
- Do not weaken host-RAM safeguards without evidence and explicit reconciliation.
- Do not perform production-scale GPU performance/resource qualification during implementation.

## Implementation authority

### Frozen

The objective, root cause, governing invariants, ownership split, soft-threshold semantics, serial-floor requirement, actual-failure semantics, scientific non-goals, and functional acceptance obligations in this workplan are frozen.

### Delegated

Implementation-local mechanics are delegated where they preserve all frozen behavior. This includes helper naming, internal data representation, whether admission status is represented through existing properties or a backward-compatible structured decision, and exact test factoring.

### Reopen only on evidence

Reopen only the affected design surface if current source inspection proves one of these frozen assumptions false:

- the scheduler has an independent hard resource contract that legitimately treats the fractional GPU envelope as physical single-job infeasibility;
- a persisted/public API contract requires target zero to encode something materially different from soft admission;
- host and GPU memory admission share an inseparable authority that cannot preserve host safety while repairing CUDA serial semantics;
- a real production consumer depends on current zero-target semantics for correctness rather than merely for throttling.

Do not reopen unrelated MLFF architecture or scientific selection behavior.

## Gates

### G0 — Baseline and affected-surface inventory

**Goal:** Bind implementation to the exact source candidate and recover all semantic consumers before editing.

**Work:**

- Record the branch baseline SHA and confirm it remains based on `main@efa8b1b206f75f687ec9b2fb738cfcc089401d68` or explicitly rebase/reconcile if implementation intentionally starts from a newer `main`.
- Inventory every production/test consumer of:
  - `build_inference_concurrency_plan`;
  - `AdaptiveInferenceConcurrency`;
  - calibration start/finalization and warm/prewarm hooks;
  - additional-admission/reservation helpers and `admission_blocked_reason`;
  - scheduler `_ensure_schedulable` or equivalent queue-fatal logic.
- Reproduce/trace the exact successful-calibration -> soft-zero-target -> scheduler-fatal edge in current source.
- Identify current repository test commands and relevant test modules rather than inventing fixed commands in advance.

**Acceptance:**

- Exact affected surface and test surface are documented in implementation working state.
- No known consumer of target/admission state is omitted.
- The failure edge and preflight soft-VRAM rejection path are independently confirmed or the plan is reopened on contrary evidence.

### G1 — Repair CUDA preflight and controller serial semantics

**Goal:** Make serial viability and soft parallel-expansion headroom distinct throughout the controller.

**Work:**

- Replace the soft-fraction one-job preflight hard rejection with conservative serial/calibration planning when a live CUDA device is otherwise available.
- Preserve genuine device-unavailability and host-RAM guards.
- Ensure every successful CUDA calibration/finalization path retains target concurrency `>= 1` for a viable one-slot plan.
- Remove soft-telemetry transitions to target zero where the meaning is only "do not add another concurrent job".
- Apply the same invariant to early calibration observations, warm/prewarm observations, live-VRAM re-clamping, and reservation accounting.
- Preserve existing adaptive growth above one when safe headroom exists.
- Preserve API compatibility where practical.

**Acceptance:**

Targeted controller/preflight regression proves all of the following:

1. Successful calibration at 95–100% GPU utilization -> target remains `1`; idle serial launch remains possible.
2. Successful calibration beyond the soft VRAM fraction without actual OOM -> target remains `1`; serial remains possible.
3. Estimated one-job VRAM above the fractional budget with a live CUDA device -> no planning failure solely from that soft fraction; conservative serial/calibration mode results.
4. Low-utilization calibration -> ramp above one remains possible.
5. `maximum_jobs == 1` plus soft-limit violation -> valid serial mode.
6. Missing/stale telemetry -> conservative serial behavior rather than terminal soft block, consistent with existing device-telemetry requirements after reconciliation.
7. Warm/prewarmed observation cannot set target zero solely from soft telemetry.
8. Reservation/live-VRAM accounting cannot create idle self-deadlock.
9. Existing host-RAM failure coverage remains green.

Run stage-local affected regression before G2.

### G2 — Repair scheduler transient-versus-terminal handling

**Goal:** Ensure scheduler state transitions respect the controller's serial floor and do not reinterpret zero additional capacity as global infeasibility.

**Work:**

- Update `_ensure_schedulable` and/or the queue launch loop so target saturation and soft no-additional-slot conditions wait for active work and reevaluate.
- Ensure an idle queued CUDA workload with no applicable execution failure launches one job.
- Preserve actual execution failure/retry behavior.
- Add the exact EVAL2 regression sequence:
  - `n512-seed1` cached;
  - `n512-seed2` cached;
  - `n1024-seed1` uncached calibration succeeds while exceeding a soft utilization/VRAM ceiling;
  - `n1024-seed2` subsequently launches after the first job completes;
  - remaining queue drains serially.

**Acceptance:**

- Exact regression emits no admission `RuntimeError` from soft telemetry.
- Concurrency remains one after the high-demand calibration.
- No second CUDA job launches concurrently when soft policy forbids expansion.
- The next queued task launches after the active task completes.
- Existing execution-failure tests still terminate/retry as previously specified.

Run stage-local affected regression before G3.

### G3 — Parallelism and dynamic-downshift non-regression

**Goal:** Prove the serial-floor fix has not converted adaptive admission into unconditional serialization or broken active-job handling.

**Work:**

- Exercise a low-demand calibration that safely promotes above one.
- Exercise reservation accounting and live-VRAM re-clamp at promoted concurrency.
- Exercise downshift from `>1` to `1` while multiple jobs are already active.
- Exercise concurrent completions and replacement admission.

**Acceptance:**

- Safe headroom still permits concurrency greater than one.
- Reservations prevent unsafe overlaunch.
- A downshift never cancels already running jobs.
- No replacement launches until active count falls below the new target.
- Once active count permits, serial/reduced-target progress resumes without terminal soft blocking.

Run stage-local affected regression before G4.

### G4 — EVAL2 and target-size integration

**Goal:** Validate assembled functional behavior through the real consumer path without changing scientific selection semantics.

**Work:**

- Run relevant EVAL2 integration tests with cached + uncached mixtures.
- Run target-size selection integration far enough through EVAL2 to prove evaluation results reach ranking/materialization.
- Compare expected ranking/result identity against unchanged fixtures/oracles where available.
- Verify CPU fallback/resource-governor paths remain unaffected.

**Acceptance:**

- EVAL2 queue reaches normal result collection/materialization with no soft-admission hard failure.
- Target-size ranking/fidelity semantics remain unchanged.
- CPU and non-CUDA affected tests remain green.

### G5 — Compatibility and diagnostics audit

**Goal:** Close API/documentation/status drift after executable behavior is stable.

**Work:**

- Reinspect all controller/scheduler consumers found at G0.
- Retain backward-compatible properties/call shapes unless a justified contract change was necessary.
- Reconcile comments, status strings, help/specification text, and architecture text that describe soft GPU thresholds as single-job execution prohibition.
- Ensure diagnostics distinguish serial fallback, temporary saturation, and actual terminal execution failure.
- Confirm no duplicate resource authority was introduced.

**Acceptance:**

- No stale semantics remain in affected durable documentation/comments/help.
- No consumer relies on an undocumented incompatible API change.
- `no future inference job is admissible` is unreachable from soft telemetry alone.

### G6 — Final affected-surface regression and integration closure

**Goal:** Establish functional closure of the assembled candidate.

**Work:**

- Re-derive the affected surface from the final diff rather than relying only on G0 inventory.
- Run focused tests for all changed mechanisms.
- Run complete affected-module regression for every old or new module touched by the implementation.
- Run relevant real-consumer integration tests across EVAL2/target-size orchestration.
- Run repository-required checks appropriate to the bounded diff; broaden if impact cannot be bounded confidently.
- Reconcile every frozen workplan obligation against the assembled candidate and inspect for unintended target-zero paths, duplicated authority, stale diagnostics, and scientific drift.

**Acceptance:**

- All focused, affected regression, integration, and repository-required checks pass.
- No affected controller/scheduler code path can convert soft GPU utilization/VRAM headroom exhaustion into terminal idle queue infeasibility.
- Adaptive `>1` concurrency remains demonstrably functional under safe headroom.
- Actual execution failure remains observable and correctly propagated.
- No production GPU qualification claim is made from these tests.

## Required test scenarios

Implementation may factor these across existing/new test modules, but the behavioral claims are mandatory:

1. High-utilization successful calibration -> serial target one.
2. High-soft-VRAM successful calibration -> serial target one.
3. Preflight estimate above soft VRAM fraction -> conservative serial/calibration, not soft-fraction hard failure.
4. Low-utilization calibration -> adaptive promotion greater than one.
5. `maximum_jobs == 1` -> stable valid serial operation.
6. Telemetry unavailable/stale -> conservative behavior without invented terminal evidence.
7. Active jobs consume target -> zero **additional** capacity transiently; next launch occurs after completion.
8. Downshift while multiple jobs active -> no cancellation; replacement throttling only.
9. Reservations/live-VRAM bookkeeping -> no idle self-deadlock.
10. Actual CUDA execution failure -> remains terminal/scoped according to existing campaign semantics.
11. Cached-only prefix -> does not silently count as real CUDA calibration unless an explicit existing warm-authority contract permits it.
12. Warm/prewarm telemetry -> cannot create target zero solely from soft limits.
13. Exact cached `n512` -> successful high-demand `n1024-seed1` calibration -> `n1024-seed2` serial continuation reproducer.
14. Multi-job EVAL2 -> reservations, ramp, live re-clamp, downshift, and concurrent completions remain functional.
15. Target-size integration -> result/ranking identity remains unchanged.

## Verification strategy

Use the current repository's actual test commands discovered at G0. Prefer targeted tests first, then stage-local affected regression, then final affected-surface regression and integration as required by the repository development policy.

Test doubles may supply deterministic GPU telemetry/controller inputs for unit-level state-machine coverage. However, scheduler acceptance must traverse the real EVAL2 orchestration owner sufficiently to prove that queue lifecycle and fatal/nonfatal interpretation are correct; a controller-only mock cannot establish that claim.

Production-scale GPU performance/resource qualification is explicitly outside this implementation plan. Do not substitute a heavy production run for missing functional regression, and do not claim GPU qualification from mocked/synthetic tests.

## Risks and mitigations

### Risk: overcorrection disables useful parallelism

**Mitigation:** mandatory low-demand promotion and multi-job reservation/downshift regressions in G3.

### Risk: serial floor attempts a job that truly cannot fit physical VRAM

**Mitigation:** runtime CUDA OOM/device failure remains authoritative and terminal/scoped under existing execution semantics. Diagnostics must distinguish this from soft serial fallback.

### Risk: stale/prewarm telemetry becomes false execution proof

**Mitigation:** cached result reuse is not calibration authority by default; audit every warm/prewarm path and require the same serial-floor invariants.

### Risk: scheduler repair creates a busy loop while no slot is available

**Mitigation:** tests must exercise wait-on-active-completion/re-evaluation rather than immediate spin/retry behavior.

### Risk: host-RAM safety is weakened accidentally

**Mitigation:** preserve host-RAM admission guards unless G0 evidence requires a separately reviewed change; include existing host-memory regressions in G1/G6.

### Risk: heterogeneous model footprints are globalized

**Mitigation:** keep actual failure evidence task/profile scoped; do not let one failed profile prove unrelated queued work impossible without existing explicit authority.

## Rollback

This transition should require no data migration, persisted-state schema change, or scientific result-format change. If implementation fails acceptance, revert the isolated branch commits. Do not retain partial controller/scheduler semantics that create two competing admission authorities.

## Closeout

When all gates pass and the implementation is accepted:

1. reconcile permanent architecture/specification text with the accepted current admission semantics;
2. move durable chronology/evidence to the repository's appropriate history/audit locations if needed;
3. archive this workplan under `workplans/archive/` when useful as lineage;
4. defer full production GPU/resource/performance qualification to final release closeout rather than inserting iterative hardware qualification into this implementation cycle.

## Implementation record

**Branch baseline:** `fix/mlff-eval2-admission-serial-floor@3b7124879cda6d82ddcea90e60ecf10cb80e2ab6`, based on local `main@d718d6ce52406fd38a02a45d3fde9bc53e031a74` (newer than the referenced `main@efa8b1b`; accepted reconciliation — the workplan's base reference predates subsequent accepted main work, and implementation intentionally starts from the newer main tip with the frozen workplan commit on top).

### G0 — affected-surface inventory (confirmed)

Production consumers:

- `mdstats/training_data/inference_parallel.py`: `build_inference_concurrency_plan` (CUDA preflight), `AdaptiveInferenceConcurrency` (`_finish_cuda_calibration`, `_observe_cuda` early classification + live-VRAM branches, `complete_first_cuda_job`), `admission_blocked_reason` (only remaining setter: host-RAM live re-clamp in `observe`).
- `mdstats/training_data/_campaign_cli_core.py`: `_run_adaptive_inference_tasks` (`launch`/`fail_if_zero_admission`, one-slot boundary finalization), `_run_staged_evaluation_tasks` (EVAL2 staged loop, `launch_inference`, fatal admission/stall checks, one-slot boundary finalization).
- `mdstats/training_data/deploy_verify.py`: static probe admission via `build_inference_concurrency_plan(task_count=1, ...)` — compatible with the repaired preflight (no API change; covered by `test_mlff_deploy_verify1.py`).

The MACE-training runner and its plan builder are a separate admission path and are unaffected.

No warm/prewarm observation paths exist in current source; the corresponding invariant is vacuously satisfied. Cached tasks bypass the inference pool entirely and never start or complete calibration (`complete_first_cuda_job` remains gated on the first real CUDA job completion; proven by the staged EVAL2 regression).

Failure edge confirmed: staged EVAL2 one-slot plan (`maximum_jobs==1` joint authority) + successful high-demand calibration -> `_finish_cuda_calibration` computed `safe_jobs==0` -> `target_jobs=0` + `admission_blocked_reason` -> scheduler fatal "resource admission blocked ... no future inference job is admissible". Preflight soft-VRAM rejection path confirmed in `build_inference_concurrency_plan`.

### Stage log

- G1 (controller serial floor): preflight soft-VRAM crossing now selects the one-slot calibration posture instead of raising; `safe_jobs` floors at 1; early classification, live-VRAM override, external-baseline re-clamp, and graduated re-clamp never set target zero or a blocked reason. Host-RAM safeguard unchanged. Diagnostics reason strings distinguish serial fallback and transient saturation. Stage regression: `tests/test_mlff_inference_parallel_scheduler.py` 44 passed.
- G2 (scheduler transient-vs-terminal): scheduler fatal paths now reachable only from genuine host-RAM terminal evidence; one-slot calibration boundary now prints `status=cuda-calibration` so serial classification remains visible. Exact EVAL2 reproducer added through the real staged orchestration owner (`test_eval2_cached_prefix_then_high_demand_calibration_continues_serially`): cached n512 prefix -> high-demand n1024-seed1 calibration -> n1024-seed2 serial continuation, no admission error.
- G3 (non-regression): covered by retained green tests — low-demand promotion (target 3), live-VRAM re-clamp at promoted concurrency, downshift with active jobs (active=2 -> target 1, no cancellation), replacement/refill admission, plus new idle-saturation and missing-telemetry non-regression tests.
- G5 (compatibility/diagnostics): plan summary wording corrected to "admission envelope"; spec `mlff_mixed_stage_admission_progress_spec.md` section 4, user guide, and architecture chapter `60_execution_performance.md` (plus its derived assembled manual) reconciled with the serial-floor semantics. `no future inference job is admissible` is no longer present in production code and is unreachable from soft telemetry.
- G6 (final regression): complete affected-module suite (8 modules, 206 tests) green. No production GPU qualification performed or claimed, per the workplan qualification policy.

PDF/provenance note: pandoc/typst are unavailable in the implementation environment; per `docs/README.md` the pushed-Markdown publication driver (CI) rebuilds affected PDF targets on push.
