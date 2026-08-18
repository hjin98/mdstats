# MLFF-PERF8: Upper-tail GPU calibration for evaluation and verification

Status: implemented in mdstats 0.20.90a0.

## Motivation

Evaluation and bounded NVE verification are bursty, heterogeneous pipelines. Even a
long single-job calibration can spend substantial time in CPU-, IO-, synchronization-,
or lightly loaded GPU stages. The ordinary mean of all nonzero GPU samples can
therefore underestimate the resource demand during the expensive bursts that matter
for safe concurrent execution.

## Required CUDA admission rule

Evaluation and verification SHALL begin with exactly one CUDA job whenever more than
one independent job remains. CUDA concurrency SHALL stay at one for a campaign-wide
300-second calibration interval by default. If one task finishes before the interval
expires, the next task is launched serially and contributes to the same calibration
clock and sample population. If the queue finishes first, no artificial wait is
introduced.

GPU utilization and incremental VRAM SHALL be sampled from task launch across the
whole heterogeneous lifecycle. Incremental values are measured against the pre-launch
GPU baseline. Samples are filtered independently before estimation:

- incremental GPU utilization below 1% is discarded;
- incremental VRAM below 1% of total device memory is discarded.

After filtering, GPU utilization and incremental VRAM SHALL each be summarized by an
**upper-tail mean**. For a configured upper-tail fraction `f`, sort the retained
samples independently and average the largest `ceil(f*N)` values, with at least one
sample retained whenever `N > 0`. The default is `f = 0.10`, i.e. the mean of the
highest 10% of retained samples. GPU and VRAM upper-tail samples do not need to occur
at the same timestamps.

If no GPU-utilization sample crosses the activity floor, the activity floor itself is
used as a finite fallback. If no incremental-VRAM sample crosses the activity floor,
the configured per-job VRAM estimate remains the fallback.

## Projection after calibration

The upper-tail GPU and VRAM estimates become fixed per-job demands for the remaining
queue. mdstats SHALL select the largest concurrency for which projected aggregate
GPU utilization and VRAM both remain strictly below their configured ceilings,
subject also to CPU/thread, RAM, explicit job-count, and remaining-task limits.
Defaults remain 90% for GPU utilization and VRAM and 80% for RAM.

No repeated calibration is performed at each promoted concurrency level. Live GPU
telemetry remains a hard post-calibration safety override if actual aggregate GPU
utilization or VRAM reaches a configured ceiling.

## CPU and training behavior

This policy is specific to CUDA evaluation and verification. CPU evaluation and
verification retain their 20-second workload window. Training retains its separate
60-second true-epoch calibration policy.

## Configuration

```toml
[execution]
parallel_inference_calibration_window_seconds = 300.0
parallel_inference_cpu_calibration_window_seconds = 20.0
inference_gpu_minimum_activity_fraction = 0.01
inference_gpu_calibration_upper_tail_fraction = 0.10
parallel_inference_monitor_interval_seconds = 2.0

inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
inference_cpu_utilization_fraction = 0.90
```

Phase-specific overrides use the existing prefix convention, for example:

```toml
parallel_evaluation_calibration_window_seconds = 300.0
verification_gpu_calibration_upper_tail_fraction = 0.10
```

Exact shared generated CUDA calibration defaults from older releases migrate to the
new 300-second default: 10 seconds (0.20.86a0), 60 seconds (0.20.87a0), 20 seconds
(0.20.88a0), and 180 seconds (0.20.89a0). Explicit phase-specific values and other
custom shared values remain authoritative.

## Progress contract

Existing evaluation/verification stage transitions remain required. During the
single-job calibration, scheduler heartbeats report elapsed calibration time and the
number of retained nonzero GPU/VRAM samples. The completion message reports both the
full retained sample counts and the upper-tail sample counts used for the final
per-job estimate.

## Scientific compatibility

These controls change runtime scheduling only. Dataset, checkpoint, metric,
selection, replay-label, export, and verification scientific identities are
unchanged; scientifically valid cached results are not invalidated.
