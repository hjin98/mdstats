# MLFF peak-trimmed fixed CUDA calibration

Status: implemented in mdstats 0.20.91a0.

## Scope

This policy applies only to CUDA checkpoint evaluation and bounded NVE verification.
Training retains its independent 60-second true-epoch scheduler. CPU evaluation and
verification retain the 20-second workload controller.

## Calibration

1. Start exactly one CUDA evaluation/verification job.
2. Sample aggregate GPU utilization and device memory for 300 seconds from task launch.
3. Express GPU utilization and VRAM growth relative to the pre-launch baseline.
4. Filter the two resources independently; discard samples below the configured 1%
   activity floor.
5. Sort each retained distribution from highest to lowest.
6. Discard the highest 10% of retained samples (`floor(N * peak_trim_fraction)`).
7. Average the next-highest 10% (`ceil(N * band_fraction)`, at least one sample).
   With normal sample counts this is approximately the 80th--90th percentile band.
8. Use the resulting GPU and VRAM values as fixed per-job estimates and choose the
   largest concurrency whose projected aggregate demand remains below the configured
   90% ceilings, also respecting CPU/RAM and explicit job caps.

GPU utilization and VRAM are intentionally ranked independently because compute peaks
and allocation peaks need not occur at the same stage. If no retained VRAM sample
crosses the activity floor, the configured VRAM-per-job estimate remains fallback-only.

## Post-calibration behavior

The calibrated GPU-utilization estimate is authoritative for the remaining queue. A
subsequent instantaneous 90--100% GPU-utilization sample does not reduce concurrency.
High occupancy is not itself unsafe and MACE evaluation naturally produces short
kernel bursts.

Live VRAM is different: if actual device memory reaches the configured memory ceiling,
mdstats throttles future replacements by one job because continued allocation can fail
or OOM. The package-wide RAM limit remains 80%.

## Configuration

```toml
parallel_inference_calibration_window_seconds = 300.0
inference_gpu_minimum_activity_fraction = 0.01
inference_gpu_calibration_peak_trim_fraction = 0.10
inference_gpu_calibration_band_fraction = 0.10
inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
```

Phase-specific `evaluation_...` and `verification_...` forms are supported. The
0.20.90a0 `inference_gpu_calibration_upper_tail_fraction` and phase-specific forms
remain readable as compatibility aliases for `*_gpu_calibration_band_fraction`.

## Scientific identity

These controls affect runtime scheduling only. They do not alter model predictions,
metric definitions, evaluation identities, checkpoint selection identities, or cached
scientific records.
