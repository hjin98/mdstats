# MLFF_EVAL2_ADMISSION_SERIAL_FLOOR_FIX — MLFF EVAL2 adaptive-admission serial-floor fix

**Status:** active — independent review reopened bounded rework  
**Current authority:** `mdstats/training_data/inference_parallel.py`, `mdstats/training_data/_campaign_cli_core.py`, and the accepted MLFF architecture/specification set  
**Target branch:** `fix/mlff-eval2-admission-serial-floor`  
**Current branch head before this workplan revision:** `7f0c3db910bcaff7eee5a0a26b7a3389d2052054`  
**Implementation merge-base/provenance:** `7da80aec5fa7145fc1652bc7c0eb4c4a63527112` for the current implementation line; this supersedes the stale earlier `main@d718d6ce...` implementation-record statement  
**Owner:** implementation agent  
**Qualification policy:** implementation acceptance is functional unit/regression/integration evidence only. Full production GPU/resource/performance qualification remains release-closeout work and is not part of this implementation cycle.

## Objective

Repair EVAL2 adaptive CUDA admission so that soft GPU-utilization and VRAM safety envelopes regulate **additional concurrency** without falsely proving that a viable single inference job is globally inadmissible.

The original failure occurred after an uncached one-slot CUDA calibration job completed successfully. Its measured demand crossed the configured 90% GPU-utilization and/or soft VRAM envelope, the controller converted that soft limit into target concurrency `0`, and the scheduler aborted the remaining queue. That is an ownership/semantic error: successful execution proves serial viability for the applicable job/resource profile, so a soft parallel-expansion ceiling may cap concurrency at one but cannot transform success into terminal infeasibility.

The implementation already repairs the principal post-calibration serial-floor defect. Independent review found one remaining blocking conformance gap: **absence of a live GPU telemetry sample is still treated as proof that the first CUDA job cannot be attempted**, even when CUDA/device availability is otherwise established. This workplan revision freezes the required correction and the evidence needed to close it.

## Current-state evidence and root cause

The original failing EVAL2 run had this material sequence:

1. CUDA resource policy reported an RTX 3090 with approximately 21.6 GiB soft VRAM admission budget, a 90% utilization ceiling, and an inferred worker ceiling of 24.
2. Cached `n512-seed1` and `n512-seed2` results were reused.
3. The first uncached `n1024-seed1` task launched alone as CUDA calibration and completed successfully with a valid result.
4. Before `n1024-seed2` launched, adaptive admission reported that no future inference job was admissible and aborted the queue.

The accepted diagnosis remains:

- target/effective concurrency;
- instantaneous **additional** launch capacity; and
- actual execution/device failure

are distinct states and must not be conflated.

The implemented branch has already repaired the main soft-limit paths:

- one-job soft VRAM projection no longer hard-rejects solely because it exceeds the fractional envelope;
- successful calibration retains a serial floor of one;
- early measured-VRAM and post-calibration live-VRAM re-clamps throttle future launches rather than producing a soft target-zero terminal state;
- the exact cached-`n512` -> high-demand `n1024-seed1` -> serial `n1024-seed2` staged EVAL2 reproducer passes;
- safe low-demand calibration can still promote above one.

### Remaining blocking defect found by independent review

`build_inference_concurrency_plan(...)` still raises when `gpu_sample is None` with the semantic claim that live VRAM telemetry is required to prove one-job feasibility.

That is too strong. `gpu_sample is None` can result from telemetry-path failure or unavailability — for example NVML initialization/query failure or an unavailable/failed `nvidia-smi` fallback — without proving that PyTorch/MACE CUDA execution itself is unavailable. A missing sample is therefore **absence of expansion/headroom evidence**, not by itself execution-failure evidence.

The existing new regression that expects this preflight failure is incorrect and must be replaced.

## Independent-review reopen and frozen corrections

This is an **implementation nonconformance**, not a redesign of the accepted serial-floor architecture. Reopen only the affected surface.

The revised implementation must preserve all previously accepted decisions and additionally satisfy these corrections:

1. **Telemetry availability is distinct from CUDA/device availability.** A failed/missing telemetry sample does not by itself establish that CUDA execution is unavailable.
2. When CUDA/device availability is independently established but no live GPU telemetry sample is available, the planner must enter a conservative **one-slot, no-evidence-for-parallel-expansion** posture rather than fail before the first execution attempt.
3. The first real CUDA execution remains authoritative for true execution infeasibility. A genuine CUDA OOM/device execution error remains terminal/scoped under the existing execution-failure contract.
4. Without telemetry evidence, the controller must not invent safe parallel headroom. Concurrency remains one until valid evidence supports expansion.
5. If telemetry becomes available later, it may be incorporated under the existing calibration/live-reclamp policy without changing the serial-floor invariant.
6. Genuine device absence/unavailability remains a hard failure. The implementation must distinguish that state using the existing resource/device authority rather than using `gpu_sample is None` as its proxy.
7. The earlier post-calibration missing/stale-telemetry behavior remains conservative and nonterminal; the preflight path must now obey the same protected concern.
8. The exact target-size integration acceptance in G4 must be executed and recorded explicitly; the prior implementation record skipped G4 and therefore did not establish that evidence.
9. The implementation record must use current branch provenance rather than the stale earlier `main@d718d6ce...` statement.
10. Previously valid evidence may be reused only where this change cannot plausibly invalidate it. Final G6 affected-surface regression/integration must be fresh after the repair.

## Governing invariants

The implementation is accepted only if all of the following hold:

1. Soft GPU-utilization and fractional VRAM thresholds regulate **additional concurrency**, not whether one otherwise viable CUDA job may execute.
2. If CUDA work is queued, no inference job is running, the device path is available, and no actual execution failure applies to the queued job/profile, at least one job is launchable.
3. A successfully completed one-slot calibration proves serial viability for its applicable job/resource profile.
4. Successful calibration above a soft utilization or VRAM ceiling results in effective target concurrency `1`, never `0`.
5. `additional_capacity == 0` while one or more jobs occupy the target is transient saturation and must cause wait/re-evaluation, not a terminal error.
6. `maximum_jobs == 1` remains ordinary valid fixed-serial CUDA operation even when soft telemetry exceeds configured expansion thresholds.
7. Terminal inference failure requires actual execution-failure evidence or explicit device/resource unavailability, not soft headroom exhaustion and not mere telemetry absence.
8. **`gpu_sample is None` is not equivalent to device unavailability.** If the device path is otherwise available, missing/stale telemetry yields conservative serial operation.
9. Failure evidence remains scoped to the failed task/profile unless existing scheduler semantics independently justify a broader scope; heterogeneous queued models must not be globally rejected from one profile's failure without evidence.
10. Cached result reuse does not, by itself, prove current CUDA viability.
11. Existing GPU-utilization and VRAM fraction values remain unchanged as expansion safety limits.
12. Running jobs survive controller downshift. No new launch occurs until active count falls below the new target.
13. Target-size scientific ranking, fidelity, checkpoint selection, and result semantics are unchanged.
14. Live VRAM/reservation accounting cannot reduce an idle, execution-viable queue to a terminal zero-capacity state solely from the soft fractional envelope.
15. Safe adaptive ramp above one remains available when calibration and live resource evidence support it.
16. CPU fallback and existing host-RAM safety behavior remain unchanged unless directly required by evidence.
17. Missing telemetry cannot authorize parallel promotion; it can only force conservative serial behavior until evidence returns.

## Architecture and ownership contract

### Resource/device authority

Existing resource/device detection owns whether the requested CUDA path/device is actually available. Telemetry acquisition is a separate observation mechanism.

Required distinction:

- **device unavailable / invalid CUDA path** -> legitimate pre-execution hard failure under existing resource/device semantics;
- **device available, telemetry unavailable** -> conservative serial planning, not terminal infeasibility;
- **device available, telemetry present** -> normal one-slot calibration and adaptive expansion policy;
- **actual CUDA execution/OOM/device error** -> execution-owned terminal/scoped failure.

Do not add a second device-availability authority merely for this repair. Reuse the existing resource snapshot/device validation mechanism.

### `mdstats/training_data/inference_parallel.py`

The adaptive controller/planner owns:

- effective/target concurrency;
- interpretation of soft GPU utilization and VRAM telemetry;
- measured per-job estimates;
- reservations/headroom accounting;
- instantaneous **additional** launch capacity;
- nonterminal reasons for holding, throttling, missing-evidence serial mode, or serial fallback.

It does **not** own proof that a job that has never executed will necessarily OOM merely because a fractional safety envelope is crossed or a telemetry sample is absent.

Required behavior:

- CUDA initial execution remains one-slot calibration.
- A soft one-job VRAM estimate crossing the fractional envelope selects conservative serial/calibration rather than hard failure.
- If CUDA/device availability is established and `gpu_sample is None`, construct a valid one-slot plan with no telemetry-derived expansion claim.
- In the no-telemetry preflight posture, do not fabricate GPU total, baseline usage, or utilization measurements. Represent their absence consistently with current public plan types/API; use configured estimates only where already permitted as conservative fallback.
- On successful calibration, effective target remains at least one.
- If one-job utilization/VRAM exceeds soft thresholds, cap further expansion at one.
- Missing/stale telemetry after launch/calibration remains nonterminal and conservative.
- Live VRAM/reservation checks regulate **additional** work and cannot self-block an idle serial queue solely from a soft fractional envelope.
- Low-utilization/headroom cases still ramp above one when valid evidence supports it.
- Preserve existing public properties/call shapes where practical.

### `mdstats/training_data/_campaign_cli_core.py`

The scheduler owns:

- queue lifecycle;
- active task lifecycle;
- waiting/re-evaluation after completions;
- actual execution outcomes;
- terminal/retry behavior under existing campaign semantics.

Required behavior:

- target-full/no-additional-slot is not global infeasibility;
- soft telemetry limits continue serially once the active slot is free;
- an idle queued CUDA workload with available device and no applicable execution failure launches one;
- the same must hold when preflight GPU telemetry is unavailable;
- actual job execution failure remains visible and follows existing failure/retry behavior;
- if telemetry recovers, subsequent controller observations may use it under the existing adaptive policy.

## Failure semantics

Do not predict true CUDA OOM solely from the 90% utilization policy, fractional VRAM safety budget, or absence of a telemetry sample.

Actual CUDA allocation/OOM/device execution failures remain execution failures. A serial-floor attempt may therefore expose a genuine runtime OOM that conservative preflight could not prove. That is acceptable and preferable: runtime failure is authoritative evidence.

Telemetry acquisition failure may be diagnostically reported as reduced observability/conservative serial mode, but must not be misreported as CUDA execution failure unless the actual device/resource authority also establishes device unavailability.

## Diagnostics contract

Progress/error messages must distinguish at least:

- serial fallback because soft GPU-utilization/VRAM evidence does not permit safe parallel expansion;
- conservative serial mode because GPU telemetry is unavailable while the CUDA device path remains available;
- temporary zero additional capacity because active jobs/reservations occupy available slots;
- genuine device/resource unavailability;
- actual CUDA execution/device failure.

`no future inference job is admissible` must remain unreachable from soft telemetry or telemetry absence alone.

## Scope

Expected directly affected production surface:

- `mdstats/training_data/inference_parallel.py`
- `mdstats/training_data/_campaign_cli_core.py` if scheduler behavior/diagnostics require adjustment for no-telemetry plans
- existing resource/device detection only as an authority to distinguish device availability from telemetry availability; do not redesign it without evidence

Expected affected acceptance surface:

- all tests consuming `build_inference_concurrency_plan`, `AdaptiveInferenceConcurrency`, calibration/finalization, reservation/admission, and scheduler schedulability logic;
- no-telemetry planner and scheduler paths;
- EVAL2 cached + uncached integration;
- target-size integration through EVAL2 to ranking/materialization;
- CPU/host-RAM and deploy/static-probe consumers of the planner;
- affected diagnostics/help/comments if they still equate telemetry with execution feasibility.

### Non-goals

- Do not raise/remove the 90% GPU-utilization limit.
- Do not change default VRAM fraction values.
- Do not change target-size ranking, scientific fidelity, checkpoint authority, or size-selection policy.
- Do not redesign EVAL2 broadly.
- Do not introduce a new inference batching strategy.
- Do not rewrite the global resource model.
- Do not globally serialize CUDA inference.
- Do not weaken host-RAM safeguards.
- Do not treat missing telemetry as permission for parallel expansion.
- Do not perform production-scale GPU performance/resource qualification during implementation.

## Implementation authority

### Frozen

The objective, ownership split, soft-threshold semantics, serial floor, missing-telemetry semantics, actual-failure semantics, scientific non-goals, and acceptance obligations in this revised workplan are frozen.

### Delegated

Implementation-local mechanics are delegated where they preserve all frozen behavior: helper naming, internal representation of missing telemetry, exact test factoring, and whether a backward-compatible decision/status object is useful.

### Reopen only on evidence

Reopen only the affected design surface if source evidence proves one of these assumptions false:

- the existing resource/device authority cannot establish CUDA-device availability independently of telemetry acquisition;
- a persisted/public API contract makes a valid no-telemetry one-slot plan impossible without incompatible change;
- a real production consumer requires live telemetry for a safety property stronger than the current soft parallel-expansion policy;
- host/GPU admission authorities are inseparable in a way that prevents preserving host safety while allowing one serial CUDA attempt.

Do not reopen unrelated MLFF architecture or scientific selection behavior.

## Gates

### G0 — Rebind baseline and affected surface

**Goal:** Bind rework to the current assembled candidate and correct provenance.

**Work:**

- Record current branch head and implementation merge-base/provenance.
- Re-derive all consumers of `build_inference_concurrency_plan`, `AdaptiveInferenceConcurrency`, telemetry acquisition, resource/device availability, scheduler admission, and deploy/static probe planning.
- Trace how `gpu_sample=None` arises and prove which mechanism independently establishes device availability.
- Identify which prior evidence remains valid and which must be rerun.

**Acceptance:**

- No telemetry path is mistaken for device-availability authority.
- Affected production/test surface is explicit.
- Workplan implementation record no longer contains stale base provenance.

### G1 — Repair missing-telemetry preflight semantics

**Goal:** Make telemetry absence conservative rather than terminal when CUDA/device availability is independently established.

**Work:**

- Remove the unconditional `gpu_sample is None -> ValueError` preflight behavior.
- Reuse existing device/resource availability authority to decide whether a CUDA path is actually unavailable.
- For available CUDA + missing telemetry, create a one-slot conservative calibration plan.
- Do not claim safe parallel headroom until valid telemetry/calibration evidence supports it.
- Preserve the already-repaired soft-VRAM serial floor and host-RAM safeguards.
- Replace the regression that currently expects missing telemetry to fail preflight.

**Acceptance:**

Targeted regression proves:

1. CUDA/device available + `gpu_sample=None` -> valid plan, `initial_jobs == 1`.
2. The plan does not invent telemetry-derived total/used/utilization evidence.
3. Missing telemetry does not permit initial concurrency above one.
4. Genuine device unavailability still fails under the existing device/resource contract.
5. Existing soft-VRAM-over-envelope preflight -> one-slot calibration remains green.
6. Existing host-RAM one-job failure remains green.
7. Successful high-utilization/high-VRAM calibration still floors at one.
8. Low-demand calibration with valid telemetry can still promote above one.
9. `maximum_jobs == 1` remains valid serial operation.
10. Post-calibration missing/stale telemetry remains nonterminal.

Run focused and stage-local affected regression before G2.

### G2 — Prove scheduler execution with missing preflight telemetry

**Goal:** Establish the real semantic owner path: an available CUDA device must actually receive a first inference attempt even when preflight telemetry is unavailable.

**Work:**

- Add/repair scheduler integration through the real adaptive/staged execution owner.
- Begin with `gpu_sample=None` while device availability remains established.
- Prove one CUDA inference task launches.
- If the task succeeds, prove queue progress continues serially unless later valid evidence permits expansion.
- If telemetry recovers after launch/completion, prove it can be consumed without corrupting the serial-floor state.
- Preserve actual execution-error propagation.

**Acceptance:**

- No preflight admission exception occurs solely because telemetry is missing.
- One and only one CUDA job launches initially.
- Successful execution permits queued work to continue.
- A real execution failure still propagates through existing scheduler semantics.
- Test doubles may replace telemetry and inference execution, but the test must traverse the real scheduler/orchestration owner; a planner/controller-only unit test is insufficient.

### G3 — Preserve already-valid adaptive concurrency behavior

**Goal:** Ensure the missing-telemetry correction does not regress the accepted serial-floor repair or safe parallelism.

**Work / acceptance:**

- Retain exact cached `n512` -> high-demand `n1024-seed1` -> `n1024-seed2` serial continuation regression.
- Retain low-demand promotion above one.
- Retain reservation/live-VRAM re-clamp, downshift-with-active-jobs, no-cancellation, refill, idle self-deadlock, and `maximum_jobs==1` coverage.
- Retain genuine host-RAM terminal evidence behavior.

Prior evidence may be reused if G1/G2 edits cannot plausibly affect a scenario; otherwise rerun the affected scenario.

### G4 — Explicit EVAL2 and target-size integration closure

**Goal:** Close the acceptance-evidence gap identified by review and prove scientific result flow is unchanged.

**Work:**

- Run relevant EVAL2 integration with cached + uncached mixtures.
- Run target-size selection integration far enough through EVAL2 to prove evaluation results reach ranking/materialization.
- Compare ranking/result identity against unchanged fixtures/oracles where available.
- Include a no-telemetry-at-preflight variant if the existing integration harness can express it without replacing the real ranking/materialization owner.
- Verify CPU/non-CUDA fallback and deploy/static-probe planner consumers remain unaffected.

**Acceptance:**

- EVAL2 reaches normal result collection/materialization with no telemetry-derived hard admission failure.
- Target-size ranking/fidelity/output identity is unchanged.
- CPU/non-CUDA and deploy/static-probe affected tests remain green.
- The implementation record names the concrete G4 tests/evidence; G4 may not be silently skipped or folded into an unlabeled aggregate count.

### G5 — Compatibility and diagnostics audit

**Goal:** Close status/API/documentation drift.

**Work:**

- Reinspect all consumers from G0.
- Preserve backward-compatible call shapes where practical.
- Ensure comments/status/help/specification text distinguish telemetry absence from device unavailability.
- Confirm no duplicate resource/device authority was introduced.

**Acceptance:**

- No stale statement says live telemetry is required to prove single-job CUDA execution viability when the device is otherwise available.
- No consumer depends on an undocumented incompatible API change.
- Soft telemetry and missing telemetry cannot reach a false global-infeasibility diagnostic.

### G6 — Fresh final affected-surface regression and integration closure

**Goal:** Establish functional closure after the reopened repair.

**Work:**

- Re-derive affected surface from the final diff.
- Run focused checks for all changed mechanisms.
- Run complete affected-module regression for every old/new module touched by G1/G2 changes.
- Run real-consumer EVAL2 and target-size integration, including G4 evidence.
- Run repository-required checks appropriate to the bounded diff; broaden if impact cannot be bounded confidently.
- Reconcile every frozen workplan obligation against the assembled candidate.

**Acceptance:**

- All focused, affected regression, integration, and repository-required checks pass.
- Available CUDA + missing telemetry no longer blocks the first serial execution attempt.
- Genuine device unavailability remains terminal under the correct authority.
- No soft GPU utilization/VRAM or telemetry-absence path can create terminal idle queue infeasibility.
- Adaptive `>1` concurrency remains demonstrably functional under valid safe-headroom evidence.
- Actual execution failure remains observable and correctly propagated.
- Target-size result/ranking semantics remain unchanged.
- No production GPU qualification claim is made.

## Required test scenarios

Implementation may factor these across existing/new test modules, but the behavioral claims are mandatory:

1. High-utilization successful calibration -> serial target one.
2. High-soft-VRAM successful calibration -> serial target one.
3. Preflight estimate above soft VRAM fraction -> serial/calibration, not hard failure.
4. **Available CUDA + missing preflight telemetry -> serial plan, not hard failure.**
5. **Real scheduler with available CUDA + missing preflight telemetry -> first CUDA job launches.**
6. **Missing telemetry does not authorize parallel promotion.**
7. **Genuine device unavailability remains a hard failure under device/resource authority.**
8. Low-utilization calibration with valid evidence -> adaptive promotion greater than one.
9. `maximum_jobs == 1` -> stable valid serial operation.
10. Post-calibration telemetry unavailable/stale -> conservative behavior without invented terminal evidence.
11. Active jobs consume target -> zero additional capacity transiently; next launch occurs after completion.
12. Downshift while multiple jobs active -> no cancellation; replacement throttling only.
13. Reservations/live-VRAM bookkeeping -> no idle self-deadlock.
14. Actual CUDA execution failure -> remains terminal/scoped according to existing campaign semantics.
15. Cached-only prefix -> does not silently count as real CUDA calibration.
16. Exact cached `n512` -> successful high-demand `n1024-seed1` calibration -> `n1024-seed2` serial continuation.
17. Multi-job EVAL2 -> reservations, ramp, live re-clamp, downshift, and concurrent completions remain functional.
18. Target-size integration -> result/ranking identity remains unchanged and evidence is explicitly recorded under G4.
19. CPU fallback, host-RAM guard, and deploy/static-probe affected consumers remain green.

## Verification strategy

Use the repository's actual test commands discovered during G0. Prefer focused tests first, then stage-local affected regression, then final affected-surface regression/integration.

Test doubles may provide deterministic telemetry and inference behavior at unit level. For the material missing-telemetry scheduler claim, acceptance must traverse the real orchestration owner sufficiently to prove queue lifecycle and fatal/nonfatal interpretation. A planner/controller-only proxy cannot establish that claim.

Likewise, G4 target-size acceptance must traverse the real target-size/EVAL2 result-flow owner far enough to establish ranking/materialization identity; controller tests or an unlabeled aggregate pytest count are insufficient evidence.

Production-scale GPU performance/resource qualification remains outside this implementation cycle.

## Risks and mitigations

### Risk: missing telemetry is confused with device absence

**Mitigation:** use existing resource/device availability authority; keep telemetry as observational evidence only. Add paired tests for available-device/no-telemetry versus genuine device unavailable.

### Risk: no-telemetry path accidentally permits unsafe parallelism

**Mitigation:** freeze initial concurrency at one until valid calibration/live evidence supports promotion.

### Risk: serial floor attempts a job that truly cannot fit physical VRAM

**Mitigation:** runtime CUDA OOM/device failure remains authoritative and terminal/scoped under existing semantics.

### Risk: overcorrection disables useful parallelism

**Mitigation:** retain low-demand promotion and multi-job reservation/downshift regressions.

### Risk: host-RAM safety is weakened accidentally

**Mitigation:** preserve host-RAM admission guards and include host-memory regression in G1/G6.

### Risk: acceptance is claimed from proxy or aggregate tests

**Mitigation:** G2 requires the real scheduler owner; G4 requires explicit target-size/EVAL2 result-flow evidence; G6 records both.

## Rollback

No data migration, persisted-state schema change, or scientific result-format change is intended. If the bounded repair fails acceptance, revert the rework commit(s) while retaining the previously accepted design record. Do not preserve partial semantics that make telemetry a second device-availability authority.

## Implementation record and reopen state

### Previous implementation evidence retained

- Principal post-calibration serial-floor repair is present.
- Soft preflight VRAM-fraction crossing selects one-slot calibration rather than hard failure.
- Successful calibration floors target at one instead of zero.
- Early/live VRAM soft limits throttle additional launches instead of creating a terminal soft target zero.
- Exact staged EVAL2 cached-prefix/high-demand-calibration/serial-continuation regression exists and passed.
- Safe low-demand promotion above one and dynamic downshift/reservation behaviors were covered by prior regression.

### Reopened rework closure record

- **Branch provenance:** target branch `fix/mlff-eval2-admission-serial-floor`, implementation merge-base `7da80aec5fa7145fc1652bc7c0eb4c4a63527112`.
- **G0 (baseline & authority rebind):** Confirmed `resources.gpu.available` (backed by `detect_gpu_resources` via PyTorch) as the sole authority for device availability; telemetry (`gpu_sample`) is strictly observational.
- **G1 (preflight & calibration missing-telemetry conformance):** `build_inference_concurrency_plan` now raises `ValueError` only on genuine device unavailability (`not resources.gpu.available`). When `gpu_sample is None` and device is available, it constructs a valid conservative plan with `initial_jobs=1` without fabricating telemetry fields. `_finish_cuda_calibration` keeps `safe_jobs=1` when no telemetry samples are observed and safely incorporates telemetry if observed during calibration. Stage regression: `tests/test_mlff_inference_parallel_scheduler.py` (47 passed).
- **G2 (real scheduler missing-telemetry integration):** Staged evaluation pipeline scheduler (`_run_staged_evaluation_tasks`) traversed with `query_gpu_telemetry -> None`. Tested first job launch, serial continuation across uncached queue, live telemetry recovery during calibration, and real runtime CUDA OOM propagation (`CampaignCliError`). Stage regression: `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` (55 passed).
- **G3 (non-regression):** Retained green tests for cached prefix reproducer, low-demand promotion, reservation/live-VRAM re-clamp, dynamic downshift without cancellation, idle self-deadlock, and host-RAM safeguard.
- **G4 (explicit EVAL2 & target-size integration closure):** Explicitly executed and verified target-size study and evaluation result-flow suites:
  - `tests/test_mlff_target_size_repair1_real_owner.py` (9 passed)
  - `tests/test_mlff_target_size_study_v5.py` (30 passed)
  - `tests/test_mlff_target_size_v5_topology.py` (27 passed)
  - `tests/test_mlff_opt_eval2_prediction_cache.py` (7 passed)
  - `tests/test_mlff_opt_eval3_monitor_graph_view_cache.py` (6 passed)
  - `tests/test_mlff_deploy_verify1.py` (11 passed)
  - `tests/test_mlff_static_mace_inference.py` (47 passed)
  - `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` (55 passed)
  All 192 target-size, cache, deploy, and staged evaluation integration tests passed cleanly.
- **G5 (compatibility & documentation):** Reconciled `mlff_mixed_stage_admission_progress_spec.md` (section 4), `60_execution_performance.md`, `mlff_training_data_architecture.md`, and `mlff_campaign_cli_user_guide.md` to specify that preflight telemetry absence enters conservative serial execution without inventing expansion headroom.
- **G6 (final affected regression):** Complete affected-module suite (8 modules, 212 tests) passed cleanly in 26.32s:
  - `tests/test_mlff_inference_parallel_scheduler.py` (47 passed)
  - `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` (55 passed)
  - `tests/test_mlff_deploy_verify1.py` (11 passed)
  - `tests/test_mlff_static_mace_inference.py` (47 passed)
  - `tests/test_mlff_opt_eval2_prediction_cache.py` (7 passed)
  - `tests/test_mlff_opt_eval3_monitor_graph_view_cache.py` (6 passed)
  - `tests/test_mlff_target_size_repair1_real_owner.py` (9 passed)
  - `tests/test_mlff_target_size_study_v5.py` (30 passed)
  No production GPU qualification performed or claimed, per the workplan qualification policy.

## Closeout

All reopened gates G0-G6 are closed with fresh evidence. Durable specifications, architecture manuals, and user guides have been reconciled. Production GPU/resource/performance qualification remains release-closeout work.
