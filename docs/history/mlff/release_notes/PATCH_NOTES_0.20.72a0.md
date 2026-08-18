# mdstats 0.20.72a0 adaptive GPU training concurrency

## Motivation

A single MACE fine-tuning process on the tested RTX 3090 used about 5.7 GiB of 24 GiB VRAM while GPU utilization remained below 25%. The previous campaign executor serialized all 16 independent fold/final jobs, leaving substantial device capacity idle.

## Runtime policy

Production training now schedules independent MACE processes concurrently without sharing mutable model, checkpoint, log, or result directories. Automatic CUDA mode:

1. detects CPU affinity/cgroup quota, currently available RAM, and live GPU allocation;
2. starts with two jobs only when all three resource budgets permit;
3. samples aggregate VRAM during a warm-up window;
4. admits one additional job only when allocation is stable and the predicted next-job total remains below the configured ceiling;
5. throttles future replacement launches if observed allocation crosses that ceiling.

The default GPU ceiling is 80% of total VRAM. With 24 GiB total, approximately 0.4 GiB baseline allocation, and 5.7 GiB observed per process, three jobs predict about 18.4 GiB including the growth margin. A fourth would exceed the 19.2 GiB budget and is not admitted.

Native BLAS/OpenMP threads are divided across concurrent MACE parents and their frozen DataLoader workers. Host-RAM admission uses a configurable per-process estimate. One failed run stops admission of queued runs by default, while active runs finish and preserve their checkpoints.

## Restart behavior

This release changes runtime scheduling only. Existing DATA3-DATA8 artifacts, passed preflight evidence, completed runs, and checkpoints remain valid. A checkpoint is now resumed even if the previous mdstats parent was interrupted before it persisted a `TrainingRunExecutionRecord`. Install the wheel and rerun `train`; do not rerun `prepare` or `preflight`.

## Configuration

```toml
[execution]
parallel_training_jobs = 0
minimum_parallel_training_jobs = 2
maximum_parallel_training_jobs = 4
training_gpu_memory_fraction = 0.80
estimated_training_vram_mib_per_job = 6144.0
estimated_training_ram_mib_per_job = 8192.0
parallel_training_ramp_up_seconds = 120.0
parallel_training_stability_samples = 4
parallel_training_stability_relative_tolerance = 0.08
parallel_training_memory_growth_margin = 1.05
parallel_training_monitor_interval_seconds = 10.0
stop_scheduling_after_failure = true
```

`parallel_training_jobs = 0` is adaptive. A positive value is a requested cap and remains clipped by current CPU, RAM, and VRAM safety limits.
