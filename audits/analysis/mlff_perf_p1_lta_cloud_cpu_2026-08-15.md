---
title: "MLFF PERF-P1 CPU Qualification"
subtitle: "Exact shared selection and progressive-coverage benchmark"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
numbersections: true
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Scope

This report measures `mdstats 0.20.180a0` PERF-P1 against embedded pre-P1 exact
oracles. It uses the authenticated PERF-P0 TARGET-DATA2B native reference rather
than re-parsing VASP XML, so the selector/coverage input is identical while XML
I/O is excluded from this gate-local timing.

# Host

| Property | Value |
|---|---|
| CPU | Intel Xeon Platinum 8573C |
| Visible logical CPUs | 9 |
| cgroup CPU quota | 8 cores (`800000 100000`) |
| cgroup memory limit | 4 GiB |
| Python | 3.13.5 |
| OMP/OpenBLAS threads | 8 / 8 |

# Scientific equivalence

| Check | Result |
|---|---|
| Full fused selector matrix | Exact |
| Full exact FPS order through 1024 | Exact |
| Coverage reports at 128/256/512/1024 | Exact |
| Wide 4000x128 FPS order through 512 | Exact |
| DATA7 K=8192 nearest-selected minima | Exact |

Reference content digest:

`4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8`

Scientific evidence digest:

`ff08ca4aee884f1aaf4bf1969454bb75fc9e875eb8c29d57c46fe0100dadb12e`

# Full-reference matched measurements

Five repetitions were recorded for each path over 37,633 frames and a 50-column
selector matrix.

| Stage | Legacy median | PERF-P1 median | Relative change |
|---|---:|---:|---:|
| Selector assembly wall | 0.1039 s | 0.1050 s | +0.98% |
| FPS wall, K=1024 | 1.5503 s | 0.6571 s | **-57.61%** |
| Four-rung coverage wall | 0.6425 s | 0.7086 s | +10.29% |
| Assembly RSS increment | 30.25 MiB | 0.008 MiB | allocator-sensitive reduction |

FPS is materially faster because row norms, selected membership/ranks, and
minimum squared distances persist in one workspace instead of being rebuilt.
Selector assembly is timing-neutral but removes the final concatenation
allocation. Progressive coverage is exact but slower for this four-rung case;
that result is retained as measured rather than normalized away.

# Wide exact FPS

A deterministic synthetic 4000x128 selector matrix isolates the wide-feature
case.

| Path | Wall |
|---|---:|
| Legacy | 0.1821 s |
| PERF-P1 | 0.0487 s |

The PERF-P1 path is **73.25% faster** with identical ordered selection.

# DATA7 K-large memory case

A separate child process measures selected-neighbor coverage for K=8192, D=16,
with rungs 1024/2048/4096/8192.

| Metric | Dense legacy | PERF-P1 | Change |
|---|---:|---:|---:|
| Persistent neighbor state | 512 MiB | 64 KiB | **8192x smaller** |
| Wall | 1.9535 s | 0.5061 s | **-74.09%** |
| Peak RSS | 1149.89 MiB | 637.22 MiB | **-44.58%** |

The final minimum-distance SHA-256 is identical:

`8a6157004024d3c0964e3ca129dd884a555314209f6441d726ec02e0b99781ac`.

# Decision

PERF-P1 satisfies its bounded acceptance gate. Exact deterministic content is
unchanged while the dominant exact FPS path and K-large DATA7 path show material
wall/memory improvements. Progressive coverage reuse is retained for shared-state
architecture and exact worker-budget control, but its observed four-rung
slowdown remains an optimization target rather than a claimed speedup.

Machine-readable evidence:

`audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.json`.
