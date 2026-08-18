# MLFF-PERF7: Single-job GPU calibration for evaluation and verification

Status: implemented in mdstats 0.20.89a0.

## Motivation

Evaluation and bounded NVE verification are heterogeneous pipelines. Checkpoint
hashing/deserialization, deployable-model reconstruction, monitor parsing, device
transfer, short batched inference bursts, dynamics integration, and metric reduction
may alternate between CPU-, IO-, and GPU-dominated work. A short aggregate window can
therefore be dominated by near-idle samples and substantially underestimate the GPU
load of the remaining jobs.

## Required CUDA admission rule

Evaluation and verification SHALL start with exactly one CUDA job whenever more than
one independent job is available. The scheduler SHALL keep CUDA concurrency at one
for a fixed calibration duration of 180 seconds by default. The calibration clock
begins when the first task is submitted, not at a later inference marker, so the
sample covers the actual multi-stage wall-time pattern.

GPU utilization and incremental VRAM SHALL be sampled throughout the calibration.
Incremental values are measured relative to the pre-launch GPU baseline. Samples are
filtered independently:

- incremental GPU utilization below 1% is excluded from the GPU-utilization mean;
- incremental VRAM below 1% of total device memory is excluded from the VRAM mean.

This independent filtering prevents IO/setup gaps from diluting short GPU bursts and
prevents low-kernel model-loading periods from diluting persistent resident VRAM.
If no GPU-utilization sample crosses the floor, the 1% activity floor is used as a
conservative finite fallback. If no VRAM sample crosses the floor, the configured
per-job VRAM estimate is used as the fallback.

The calibration is campaign-wide rather than task-local. If a short job finishes
before 180 seconds, the next queued job is launched at concurrency one and sampling
continues without resetting the calibration clock or retained samples. If the queue
finishes before calibration completes, no artificial wait is introduced because
there are no remaining jobs to parallelize.

## Fixed projection after calibration

After the calibration duration expires, the retained means become the fixed per-job
GPU-utilization and VRAM estimates for the remaining evaluation or verification
queue. The scheduler SHALL compute the largest concurrency that simultaneously
satisfies:

- projected aggregate GPU utilization < configured GPU-utilization ceiling;
- projected aggregate VRAM < configured VRAM ceiling;
- CPU/thread, RAM, explicit job-count, and task-count limits.

The default GPU-utilization and VRAM ceilings remain 90%. The RAM ceiling remains
80%. The configured per-job VRAM estimate SHALL NOT pre-cap CUDA concurrency before
calibration; it is only a fallback when measured incremental VRAM never crosses the
activity floor.

After calibration, the scheduler SHALL NOT repeatedly recalibrate at each new
concurrency level. It reuses the fixed one-job estimate for the remaining queue. Live
telemetry may still act as a hard safety override: if an admitted aggregate level
actually reaches a configured GPU-utilization or VRAM ceiling, future replacements
are throttled without killing already-running work.

## CPU and training behavior

This rule is CUDA-specific. CPU evaluation/verification retains the 20-second
workload-window controller with the 90% CPU-utilization and 80% RAM limits. Training
retains its independent 60-second true-epoch calibration policy.

## Configuration

```toml
[execution]
parallel_inference_calibration_window_seconds = 180.0
parallel_inference_cpu_calibration_window_seconds = 20.0
inference_gpu_minimum_activity_fraction = 0.01
parallel_inference_monitor_interval_seconds = 2.0

inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
inference_cpu_utilization_fraction = 0.90
```

Phase-specific calibration durations remain supported through
`parallel_evaluation_calibration_window_seconds` and
`parallel_verification_calibration_window_seconds`. Phase-specific activity floors
can be set with `evaluation_gpu_minimum_activity_fraction` and
`verification_gpu_minimum_activity_fraction`.

Exact shared generated defaults from earlier releases migrate as follows for CUDA
evaluation/verification: 10 seconds (0.20.86a0), 60 seconds (0.20.87a0), and 20
seconds (0.20.88a0) become 180 seconds. Explicit phase-specific values and other
custom shared values remain authoritative.

## Progress contract

Existing evaluation/verification stage messages remain required. During the
single-job calibration, scheduler heartbeats SHALL additionally report elapsed
calibration time and retained nonzero GPU/VRAM sample counts. After calibration, the
promotion message SHALL report the measured per-job GPU/VRAM estimates and the fixed
projected concurrency.

## Scientific compatibility

All controls in this specification are runtime scheduling policy only. They do not
change dataset, checkpoint, metric, selection, export, replay-label, or verification
scientific identities and therefore do not invalidate scientifically valid caches.
