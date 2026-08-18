---
title: "Density Mesh-Execution Specification"
subtitle: "Bounded isolated-worker scheduling, timeout, memory, and deterministic result association"
author: "mdstats"
date: "2026-07-22"
geometry: margin=0.78in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# Purpose and status

**Module:** `mdstats.plotting.density_mesh_execution`  
**Status:** normative and implemented.

This module owns resource-aware scheduling of independent shell-mesh tasks. It does not own mesh algorithms or browser acceptance.

# Public contracts

```python
DensityMeshExecutionOptions(
    max_parallel_shell_workers: int | None,
    worker_native_threads: int = 1,
    worker_timeout_seconds: float | None,
    worker_memory_bytes: int | None,
)
```

```python
DensityMeshExecutionReport(
    isolated_shell_count: int,
    parallel_worker_count: int,
    wall_seconds: float,
    sum_shell_seconds: float,
    maximum_shell_seconds: float,
)
```

# Resolution against runtime resources

Worker count is bounded by:

- requested workers;
- available package threads divided by native threads per worker;
- memory available after parent-retained data and output reserve;
- the number of isolated shell tasks.

The resolved count is

$$
N_w=\min(N_{\mathrm{requested}},N_{\mathrm{thread}},N_{\mathrm{memory}},N_{\mathrm{shell}}).
$$

Worker timeout is capped by the remaining scene wall time. Per-worker memory must remain above the estimated largest shell peak.

# Determinism

Every task and result is associated with a stable shell key. Serial and parallel execution must produce identical shell geometry counts, ordering, names, and legend metadata.

Workers receive immutable requests. The parent must not retain raw geometry from completed workers beyond what is needed for the final shell result.

# Failure semantics

Raise `GraphComplexityError` before launch when the declared memory cannot host one worker. Propagate worker exceptions with shell identity. A timeout identifies the shell and resolved timeout. The scheduler must not convert timeout or worker death into a partial scene.

# Native thread containment

Each worker uses the declared native numerical thread count, normally one. Process parallelism must not multiply uncontrolled BLAS, FFT, or OpenMP threads.

# Focused validation

Tests must cover:

- resource resolution;
- memory and thread clamps;
- timeout clamps;
- serial/parallel count equality;
- stable shell association under out-of-order completion;
- worker failure and timeout propagation;
- report serialization and parallel efficiency.
