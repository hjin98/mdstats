# mdstats 0.20.93a0 patch notes

## Work-conserving evaluation / verification queue refill

The adaptive evaluation/verification executor is now a true rolling queue after
concurrency has been selected.

Previously, a completed worker was removed from the active set, but its replacement
was not submitted until the next outer scheduler iteration. Parent-side result
persistence, progress bookkeeping, and telemetry could therefore leave an admitted
GPU/CPU slot idle even though pending work remained. Several workers completing in
one `wait(FIRST_COMPLETED)` wave could amplify the idle gap because the entire wave
was finalized before new work was submitted.

0.20.93a0 changes completion handling so that:

1. each successful worker completion immediately opens one executor slot;
2. that slot is refilled from the pending deque before parent-side result commit and
   progress finalization;
3. multiple simultaneous completions are replaced independently, one-for-one;
4. a concurrency increase produced by the adaptive controller is also filled in the
   same telemetry iteration instead of waiting through another monitor interval;
5. failures still stop further admission; already-running independent work is allowed
   to finish under the existing fail-safe behavior.

The fixed CUDA estimator, five-minute calibration, 1% activity filter, 85th--95th
percentile default band, fixed post-calibration GPU-utilization projection, live VRAM
hard guard, CPU policy, RAM policy, and training scheduler are unchanged.

## Validation

A new rolling-queue regression deliberately makes parent-side result finalization
slower than inference. With two workers admitted, the third task must begin while the
first completed task's parent callback is still blocked and while the second original
worker remains active. This directly guards against the idle-slot behavior observed
in the real campaign.

Scientific evaluation identities, checkpoint selection, model predictions,
verification identities, and cached scientific records are unchanged.
