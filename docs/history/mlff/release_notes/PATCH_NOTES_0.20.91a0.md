# mdstats 0.20.91a0 patch notes

## Evaluation / verification CUDA scheduling

The five-minute single-job calibration introduced in 0.20.90a0 is retained, but its estimator is made robust against isolated peaks.

After independently filtering GPU-utilization and incremental-VRAM samples below the 1% activity floor, mdstats now:

1. sorts each retained distribution independently;
2. discards the highest 10% of samples;
3. averages the next-highest 10% of samples (approximately the 80th--90th percentile band);
4. freezes those per-job estimates for the remaining evaluation/verification queue.

This prevents one or two transient kernel/allocation peaks from dominating the estimate while remaining substantially more conservative than a full-distribution mean.

## No utilization-spike throttling after calibration

The calibrated GPU-utilization estimate is authoritative after the five-minute calibration. A later instantaneous GPU-utilization reading at or above 90% no longer lowers the target concurrency. High device occupancy is expected during MACE kernels and is not itself unsafe.

The live VRAM guard remains active. If actual device memory reaches the configured VRAM ceiling, future replacements are throttled because continued allocations can fail or OOM. The package-wide RAM ceiling remains 80%.

## Configuration

New canonical controls:

```toml
parallel_inference_calibration_window_seconds = 300.0
inference_gpu_minimum_activity_fraction = 0.01
inference_gpu_calibration_peak_trim_fraction = 0.10
inference_gpu_calibration_band_fraction = 0.10
```

Phase-specific `evaluation_...` and `verification_...` forms are supported. The 0.20.90a0 `*_gpu_calibration_upper_tail_fraction` key remains accepted as a compatibility alias for the band width.

Training is unchanged at its separate 60-second true-epoch scheduler. CPU evaluation/verification is unchanged at its 20-second workload controller. CPU/GPU/VRAM admission ceilings remain 90%; RAM remains 80%.

## Validation

- 81-module MLFF suite in bounded groups: 463 passed, 16 skipped.
- Focused scheduler/version/evaluation suite: 48 passed.
- Added regressions for a 98% post-calibration GPU-utilization spike retaining calibrated concurrency and for the independent live VRAM hard guard.
