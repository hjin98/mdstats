# MLFF True-Inference Telemetry Gate Specification

Release: **0.20.87a0**  
Stage: **MLFF-PERF5**

> Historical note: this file documents the 0.20.87a0 first-forward gate.
> Current 0.20.88a0 behavior is specified in
> `mlff_mixed_stage_admission_progress_spec.md`: evaluation/verification
> telemetry now starts at the first computation-heavy stage and uses a
> 20-second mixed-stage window.

## 1. Problem

The 0.20.86a0 inference scheduler began its calibration clock when a worker future
was launched. That interval included checkpoint materialization, monitor loading,
MACE calculator construction, CUDA context creation, and other initialization.
GPU utilization during those phases can be near zero, so a short averaging window
could incorrectly project spare capacity and admit another evaluation or
verification job before steady model inference was measured.

## 2. Required execution signal

Every adaptive evaluation or verification worker owns an isolated, thread-local
first-forward signal. Setup code cannot set it. The scientific hot path sets it
immediately before the first operation that invokes the model:

- checkpoint evaluation: immediately before the first batched MACE prediction;
- NVE verification: immediately before the first force or energy evaluation.

Repeated signaling is idempotent. Workers outside the adaptive campaign runner see
a no-op, so the public evaluation and verification APIs remain compatible.

## 3. Admission window

The scheduler SHALL collect no runtime admission sample until every active worker
at the current concurrency level has signaled true inference. It SHALL then collect
a trailing fixed-duration window whose default is 60 seconds. With the default
2-second monitor interval, at least 30 samples are required in addition to elapsed
window coverage.

Any of the following resets calibration:

- active job count changes;
- a newly admitted worker has not reached its first forward pass;
- no active work remains;
- telemetry becomes unavailable.

A promotion therefore cannot reuse measurements from the previous concurrency
level. Jobs that complete before a full window is available are not used to justify
higher CUDA concurrency.

## 4. Resource projections

After the window qualifies, the scheduler computes aggregate mean GPU utilization
and aggregate VRAM use for that true-inference window. It projects one additional
job using observed per-job growth, configured lower-bound estimates, and safety
margins. Both projected VRAM and projected GPU utilization must remain strictly
below their configured ceilings, 90% by default.

CPU execution uses the same first-forward gate. The stateful CPU counter is reset
when all active workers enter true inference, preventing a utilization interval
from spanning initialization. CPU promotion remains bounded by the 90% utilization
ceiling and the unchanged 80% RAM budget.

## 5. Configuration and migration

The canonical shared control is:

```toml
parallel_inference_calibration_window_seconds = 60.0
```

Phase-specific overrides are:

```toml
parallel_evaluation_calibration_window_seconds = 60.0
parallel_verification_calibration_window_seconds = 60.0
```

The old `*_stabilization_seconds` names remain readable. The exact 10-second value
written by the 0.20.86a0 generated template is migrated to 60 seconds automatically.
Other legacy values are preserved. A canonical calibration-window key is always
authoritative and may explicitly request a different duration.

## 6. Scientific compatibility

This change affects runtime scheduling only. It does not enter checkpoint,
evaluation-policy, metric, selection, exported-model, or verification-case digests.
Existing authenticated evaluation records and bounded NVE case caches remain
reusable.

## 7. Required tests

Regression tests SHALL prove that:

- initialization telemetry cannot trigger promotion regardless of duration;
- the window starts at the explicit first-forward signal;
- promotion is impossible before 60 seconds of qualifying telemetry by default;
- all active workers must signal after a concurrency change;
- runtime GPU polling is skipped during setup except for the pre-launch idle baseline;
- evaluation and NVE hot paths emit the signal before their first model operation;
- the old generated 10-second key migrates to 60 seconds;
- canonical and custom legacy overrides remain deterministic.
