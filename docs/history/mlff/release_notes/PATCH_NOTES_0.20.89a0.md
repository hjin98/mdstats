# mdstats 0.20.89a0 Patch Notes

## Evaluation/verification CUDA scheduler

- CUDA evaluation and bounded NVE verification now begin with exactly one job.
- That single-job calibration lasts 180 seconds by default and is campaign-wide:
  if a short task ends, the next task continues serially without resetting the
  clock or retained observations.
- GPU telemetry begins at task launch so the calibration represents the full
  heterogeneous wall-time pattern rather than an arbitrarily chosen internal
  stage.

## Near-zero filtering

- GPU utilization is converted to incremental utilization relative to the
  pre-launch baseline. Values below 1% are discarded before averaging.
- VRAM is converted to incremental resident memory relative to the pre-launch
  baseline. Values below 1% of total device memory are independently discarded.
- Independent filtering avoids CPU/IO gaps diluting short GPU bursts while still
  retaining model-resident VRAM during low-kernel stages.
- If no GPU-utilization observation crosses the floor, the 1% floor is used as a
  conservative finite estimate. If no VRAM observation crosses it, the configured
  per-job VRAM estimate is used as fallback.

## Fixed projection

- The retained one-job means become fixed per-job estimates for the rest of the
  evaluation/verification queue.
- The scheduler immediately selects the largest concurrency whose projected GPU
  utilization and VRAM both remain strictly below 90%, additionally bounded by
  CPU, RAM, explicit job caps, and task count.
- The configured VRAM-per-job estimate no longer pre-caps measured CUDA
  concurrency before calibration.
- No repeated per-concurrency recalibration is performed. Live telemetry remains
  only as a hard saturation override if an admitted level reaches a configured
  ceiling.

## Unchanged policies

- CPU evaluation/verification retains its 20-second workload window and 90% CPU
  ceiling.
- Training retains its separate 60-second true-epoch calibration.
- RAM remains capped at 80%.
- Existing evaluation/verification stage progress remains enabled; scheduler
  heartbeat messages expose elapsed calibration time and retained nonzero sample
  counts.

## Compatibility

- Exact shared generated evaluation/verification defaults from 0.20.86a0,
  0.20.87a0, and 0.20.88a0 (10, 60, and 20 seconds) migrate to 180 seconds for
  CUDA evaluation/verification.
- Explicit phase-specific calibration values and other custom shared values remain
  authoritative.
- Scientific dataset, checkpoint, evaluation, selection, replay-label, export, and
  verification identities are unchanged.
