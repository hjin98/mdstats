# MLFF Mixed-Stage Admission and Progress Specification

Release: **0.20.88a0**  
Stage: **MLFF-PERF6**

## 1. Problem

The 0.20.87a0 scheduler waited for the first model forward pass before collecting
admission telemetry. That excluded misleading idle initialization, but real campaign
runs showed the opposite bottleneck: checkpoint authentication/deserialization,
whole-model reconstruction, monitor materialization, and model loading can dominate
evaluation wall time while batched inference is comparatively short. Waiting for
inference can therefore prevent the scheduler from ever obtaining a qualifying
window and hides where the phase is spending time.

## 2. Workload-start boundary

Adaptive evaluation and verification workers SHALL retain lightweight launch work
outside telemetry. The workload-start event SHALL be emitted at the first
computation-heavy operation:

- checkpoint evaluation through the campaign: before checkpoint SHA-256
  authentication and payload deserialization;
- direct evaluation of an already deployable model: before candidate/monitor
  artifact authentication;
- bounded NVE verification: before MACE model deserialization and device transfer;
- verification with a caller-supplied calculator: before dynamics initialization.

The event is worker-local and idempotent. A later historical first-forward signal is
accepted as a backward-compatible alias but SHALL NOT reset or restart telemetry.

## 3. Mixed-stage calibration window

Evaluation and verification SHALL use a trailing **20-second** window by default.
Once every active worker at the current concurrency level has reached its workload
boundary, telemetry SHALL continue across checkpoint reconstruction, monitor
loading, model transfer, candidate/foundation inference, NVE integration, and
metric reduction. Stage transitions SHALL NOT clear the window.

Calibration SHALL reset when active concurrency changes, a replacement worker has
not yet reached its workload boundary, no active work remains, or telemetry becomes
unavailable. Promotion SHALL still require duration coverage and the corresponding
sample count.

Training is a different workload and SHALL retain a **60-second true-epoch** window.
Evaluation/verification and training windows SHALL be configured independently.

## 4. Resource admission

CUDA starts with one job. The controller SHALL average aggregate VRAM use and GPU
utilization over the mixed-stage window and project one additional job using
observed growth, configured lower-bound per-job estimates, and safety margins.
Projected VRAM and projected GPU utilization must both remain strictly below their
90% ceilings.

The 90% ceilings are soft parallel-expansion envelopes, not single-job execution
proof. A successfully completed one-slot CUDA calibration is direct evidence that
serial execution of the applicable job/resource profile is viable, so the
effective target concurrency after successful calibration SHALL always remain at
least one when at least one job is configured. Measured demand above a soft
envelope SHALL cap additional concurrency (serial fallback) and SHALL NOT be
converted into terminal queue infeasibility; only actual execution failure or
genuine device/resource unavailability may terminate the queue. Absence of
preflight GPU telemetry SHALL select conservative serial execution (initial
concurrency one) without parallel expansion evidence, rather than blocking the
first execution attempt when the device is available. Live VRAM and
reservation checks regulate launching additional work and may transiently return
zero additional capacity while active jobs occupy the target; they SHALL NOT
self-block an idle queue solely from the soft fractional envelope. Host-RAM
admission safeguards are unchanged.

CPU execution SHALL remain bounded by the 90% effective CPU allocation and projected
host-utilization ceiling. All execution modes SHALL retain the 80% available-RAM
budget. Runtime scheduling changes SHALL NOT enter scientific digests.

## 5. Progress contract

Every uncached evaluation or verification task SHALL report meaningful stage
transitions. At minimum, applicable messages include:

- checkpoint authentication, payload read, cache check, reconstruction, and
  reconstructed-model validation;
- target/replay monitor loading;
- candidate and foundation evaluation on the LTA target and true-label replay sets;
- verification structure/model loading, dynamics initialization, bounded NVE
  integration, and stability-metric analysis;
- final evaluation-metric reduction.

The scheduler SHALL print stage transitions without waiting for its periodic status
interval. Periodic scheduler reports SHALL also summarize the current stage of all
active workers so a long stage remains visible.

## 6. Configuration and migration

Canonical defaults are:

```toml
parallel_training_epoch_stabilization_seconds = 60.0
parallel_inference_calibration_window_seconds = 20.0
```

Phase-specific evaluation/verification overrides remain available:

```toml
parallel_evaluation_calibration_window_seconds = 20.0
parallel_verification_calibration_window_seconds = 20.0
```

Migration rules:

- the exact 0.20.87a0 generated shared inference value `60.0` migrates to `20.0`;
- the exact 0.20.86a0 generated legacy inference value `10.0` migrates to `20.0`;
- an explicit phase-specific value remains authoritative, including `60.0`;
- other custom shared or legacy values remain unchanged;
- the exact prior generated training value `180.0` migrates to `60.0`;
- other custom training values remain unchanged.

## 7. Compatibility and tests

The change affects runtime orchestration and progress only. Existing evaluation,
selection, exported-model, and verification-case records remain reusable when their
scientific identities match.

Regression tests SHALL prove that lightweight launch telemetry is excluded, the
first heavy pre-inference stage starts calibration, multiple evaluation stages share
one 20-second window, training resolves to 60 seconds, stage transitions are printed,
concurrency changes reset calibration, and all migration rules remain deterministic.
