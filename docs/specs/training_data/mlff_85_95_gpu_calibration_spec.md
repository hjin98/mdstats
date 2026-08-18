# MLFF 85th--95th percentile fixed CUDA calibration

Status: implemented in mdstats 0.20.92a0.

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
6. Discard the highest 5% of retained samples (`floor(N * peak_trim_fraction)`).
7. Average the next-highest 10% (`ceil(N * band_fraction)`, at least one sample).
   With normal sample counts this is approximately the 85th--95th percentile band.
8. Use the resulting GPU and VRAM values as fixed per-job estimates and choose the
   largest concurrency whose projected aggregate demand remains below the configured
   90% ceilings, also respecting CPU/RAM and explicit job caps.

GPU utilization and VRAM are ranked independently because their peaks need not occur
at the same stage. The upward-shifted band is intentionally more conservative than
the 0.20.91a0 80th--90th percentile default while still removing the most extreme
5% of transient peaks.

## Post-calibration behavior

The calibrated GPU-utilization estimate remains authoritative for the rest of the
queue. Instantaneous post-calibration GPU-utilization spikes do not lower concurrency.
The live VRAM hard guard remains active because actual device-memory saturation can
cause allocation failure/OOM. RAM remains capped at 80%.

## Configuration

```toml
parallel_inference_calibration_window_seconds = 300.0
inference_gpu_minimum_activity_fraction = 0.01
inference_gpu_calibration_peak_trim_fraction = 0.05
inference_gpu_calibration_band_fraction = 0.10
inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
```

Phase-specific `evaluation_...` and `verification_...` forms are supported. The exact
shared 0.20.91a0 generated peak-trim value `0.10` migrates to `0.05`; explicit
phase-specific values and other custom shared values remain authoritative. The
0.20.90a0 `*_gpu_calibration_upper_tail_fraction` aliases remain accepted for band
width.

## Scientific identity

These controls affect runtime scheduling only. They do not alter model predictions,
metric definitions, evaluation identities, checkpoint-selection identities,
verification identities, or cached scientific records.
