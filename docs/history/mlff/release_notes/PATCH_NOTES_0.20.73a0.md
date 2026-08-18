# mdstats 0.20.73a0 true-epoch dual-resource scheduler

## Motivation

The 0.20.72a0 scheduler used VRAM as the principal ramp-up signal and began with two jobs. On the RTX 3090, three jobs fit in memory but saturated GPU compute, slowing every job. Initialization also produced deceptively low utilization, so a scheduler could add work before the first process reached its stable training phase.

## Runtime policy

CUDA production training now starts with exactly one job. The controller considers one additional job only when:

1. every active MACE process has produced fresh optimizer records, proving that it is in true epoch compute rather than initialization, graph construction, initial validation, or checkpoint export;
2. all active processes remain in recent optimizer work for the configured stabilization window (180 seconds by default);
3. VRAM and GPU-utilization telemetry are stable over the configured sample window (12 samples by default);
4. the projected aggregate VRAM after adding one job is strictly below the VRAM admission ceiling; and
5. the projected aggregate GPU utilization after adding one job is strictly below the utilization admission ceiling.

Both default ceilings are 90%. Projection subtracts the pre-training baseline, estimates the stable incremental cost per active job, applies a growth margin, and then restores the baseline. A new process is admitted one at a time. After each admission, calibration resets and waits for all active jobs to reach sustained epoch work again.

If a newly calibrated level is already at or above either ceiling, running jobs are not terminated. The target is reduced by one so the scheduler does not replace the excess process after it completes.

## Restart behavior

This release changes runtime scheduling and telemetry only. Existing DATA3-DATA8 artifacts, passed preflight evidence, checkpoints, and completed runs remain valid. Stop the old training parent and its child processes, install the wheel, and rerun `train`. Existing checkpoints resume normally; do not rerun `prepare` or `preflight`.

## Configuration

```toml
[execution]
parallel_training_jobs = 0
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 4
training_gpu_memory_fraction = 0.90
training_gpu_utilization_fraction = 0.90
estimated_training_vram_mib_per_job = 6144.0
estimated_training_ram_mib_per_job = 8192.0
parallel_training_epoch_stabilization_seconds = 180.0
parallel_training_epoch_activity_timeout_seconds = 120.0
parallel_training_epoch_stability_samples = 12
parallel_training_stability_relative_tolerance = 0.10
parallel_training_utilization_stability_absolute_tolerance = 8.0
parallel_training_memory_growth_margin = 1.05
parallel_training_utilization_growth_margin = 1.05
parallel_training_monitor_interval_seconds = 10.0
```

`parallel_training_jobs = 0` enables automatic ceiling selection. A positive value sets only the maximum candidate concurrency; it does not bypass the true-epoch or dual-resource gates.
