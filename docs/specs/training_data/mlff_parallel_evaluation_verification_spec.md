# MLFF Parallel Staged Evaluation and Downstream Verification Specification

Introduced: **0.20.86a0**  
First-forward correction: **0.20.87a0**  
Mixed-stage correction: **0.20.88a0**  
Stages: **MLFF-PERF4 / MLFF-PERF5 / MLFF-PERF6**

## 1. Scope

This specification governs runtime parallelism for two independent-inference
workloads:

1. authoritative checkpoint evaluation on target and replay monitors; and
2. bounded NVE verification cases across models, structures, and temperatures.

The scheduling policy is runtime-only. It does not modify training data,
checkpoint bytes, evaluation-policy digests, selection criteria, or NVE case
scientific identity.

For the current P6 campaign, the staged-evaluation owner is used for
authenticated selected-checkpoint/final-publication evidence. Deployment,
physical-observable, calibration, and locked-test verification are downstream
consumers of the frozen final publication; this specification does not make
those consumers part of the campaign lifecycle or a target-size fallback.

## 2. Resource ceilings

Automatic resource planning shall use:

- **90%** of effective CPU threads;
- **90%** aggregate GPU utilization;
- **90%** total GPU memory as the VRAM admission ceiling; and
- **80%** of currently available system RAM.

RAM is the only resource that retains the 80% default, preserving baseline
headroom for the operating system and unrelated processes.

Explicit positive job limits are maximum caps and shall not bypass CPU, RAM,
VRAM, or utilization admission.

## 3. CUDA admission

CUDA execution starts with one job. Lightweight queue/thread launch and trivial
path setup are not eligible telemetry. Each worker emits a scheduler-local signal
at its first computation-heavy stage:
checkpoint authentication/deserialization for evaluation, and MACE model loading or
dynamics initialization for verification. The scheduler waits until every active
worker at the current concurrency level has signaled, then samples aggregate device
VRAM and utilization over a trailing 20-second window. Checkpoint reconstruction,
monitor loading, model transfer, inference, NVE integration, and metric reduction
share that window. One additional job may be admitted only when projected aggregate
VRAM **and** projected aggregate GPU utilization are both strictly below their
configured ceilings.

After a promotion, the calibration state resets. Every worker active at the new
level must reach its heavy-work boundary before a new 20-second window begins.
Lightweight launch samples and measurements from the previous concurrency level
cannot be retained or averaged into the next projection.

The projection uses the greater of the configured per-job VRAM estimate and the
observed incremental per-job VRAM, with configurable growth margins. If a stable
post-admission level reaches a ceiling, running work is not killed; the future
replacement target is reduced.

When CUDA telemetry is unavailable, concurrency remains one job. Admitted CUDA
jobs use distinct PyTorch streams and synchronize before result commitment, so
independent inference can overlap rather than merely queueing on one default
stream.

## 4. CPU admission

CPU work is divided into independent outer jobs. It uses the same heavy-work gate;
the stateful CPU counter is reset when all active workers reach their first
computation-heavy stage so its first interval cannot span lightweight launch work.
Native BLAS/OpenMP/PyTorch
thread pools are bounded so the product of active jobs and native threads per job
does not exceed the effective CPU-thread budget. Aggregate host-utilization telemetry is restricted to the process affinity
mask and normalized to a smaller cgroup/scheduler quota when applicable. It is
used to project the next job. Admission requires projected CPU utilization to
remain strictly below the configured ceiling.

RAM estimates are applied before CPU admission and may reduce the job ceiling.

## 5. Evaluation behavior

Each checkpoint is an independent inference task. All shortlisted uncached
checkpoints across the selected campaign scope form one queue, so retained
single-checkpoint runs can execute concurrently across folds, seeds, and
training modes. Cached records remain reusable when all existing scientific and
byte identities match.

Parallel evaluation shall:

- serialize the first immutable-monitor parse per authenticated cache identity
  and reuse it when it fits the configured monitor-cache budget;
- compute each cache-enabled foundation-model/dataset metric once per immutable
  cache key;
- permit candidate-model inference to proceed concurrently;
- materialize and remove checkpoint-model cache entries independently; and
- commit campaign-state records only from the parent scheduler thread.

True-label replay stale-record invalidation remains unchanged.

## 6. Verification behavior

All uncached NVE cases form one independent task queue. Every active case owns a
private ASE `Atoms` object and a private mutable MACE calculator. Calculator
objects shall never be shared between concurrent cases.

Completed case caches remain reusable across 0.20.85a0 through 0.20.88a0 because
parallel scheduling and progress reporting do not alter the integration or
acceptance identity.

## 7. Configuration

Shared controls under `[execution]`:

```toml
parallel_inference_jobs = 0
maximum_parallel_inference_jobs = 0
inference_cpu_utilization_fraction = 0.90
inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
inference_estimated_vram_mib_per_job = 4096.0
inference_estimated_ram_mib_per_job = 4096.0
parallel_inference_calibration_window_seconds = 20.0
parallel_inference_stability_samples = 3
inference_memory_growth_margin = 1.05
inference_utilization_growth_margin = 1.05
parallel_inference_monitor_interval_seconds = 2.0
```

Any shared control may be overridden for one phase by replacing `inference` with
`evaluation` or `verification`. Job caps use
`parallel_evaluation_jobs`, `maximum_parallel_evaluation_jobs`,
`parallel_verification_jobs`, and `maximum_parallel_verification_jobs`.

Legacy TOMLs remain valid. Explicit older resource fractions continue to be
honored; newly generated TOMLs use the revised 90/90/90/80 defaults. The legacy
`parallel_inference_stabilization_seconds` and phase-specific stabilization keys
remain readable. The exact old generated default `10.0` migrates to 60 seconds;
other legacy values remain explicit user choices. A canonical calibration-window
key always takes precedence.

## 8. Qualification requirements

Tests shall cover:

- CUDA one-job startup;
- exclusion of lightweight launch telemetry until the first heavy-work signal;
- inclusion of checkpoint/model loading and later inference in one 20-second window;
- a complete 20-second mixed-stage window before promotion;
- calibration reset after a concurrency-level change;
- promotion only when both VRAM and GPU-utilization projections are below 90%;
- rejection when either projected ceiling is reached;
- CPU/RAM job ceilings with 90% CPU and 80% RAM;
- campaign-wide concurrency across runs and checkpoints;
- unchanged serial/parallel scientific records;
- synchronized monitor and foundation caches; and
- private calculator ownership for parallel verification.
