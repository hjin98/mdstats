---
title: "MLFF PERF-P2 Cloud CPU Qualification"
subtitle: "Lazy TARGET-DATA2C v2 versus exhaustive v1"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.82in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{microtype}
---

# Scope

PERF-P2 is benchmarked against the exhaustive TARGET-DATA2C v1 oracle using
fresh processes per timing sample. The source is the complete PERF-P0 native
37,633-frame target coverage reference. A deterministic frame-index remap
aligns the reference with the DATA2C role-order contract.

The host is an Intel Xeon Platinum 8573C with nine visible logical CPUs, an
8-core cgroup CPU quota, and a 4 GiB cgroup memory limit.

# Scientific equivalence

Two supplied-data-derived cases were tested.

| Case | v1 Stage-A survivors | v2 Stage-A survivors | Survivor evidence |
|---|---|---|---|
| Exhaustive fallback | 2048, 4096, 8192 | 2048, 4096, 8192 | exact |
| Forced early stop | 128, 256, 512, 1024 | 128, 256, 512, 1024 | exact |

The forced early-stop fixture changes local radii to a deliberately permissive
value and removes extent channels only to exercise the safe stop branch. It is
not a production coverage-policy change.

Worker counts 1 and 4 produce the same v2 content digest and scientific
signature.

Scientific benchmark digest:

`ae55c560995791174ac63e2d894ec685d74a02c389eb0a955d87e77cfd9f18f9`.

# Fresh-process CPU measurements

## Forced early stop

| Metric | Exhaustive v1 | Lazy v2 | Change |
|---|---:|---:|---:|
| Median wall | 7.867 s | 1.556 s | **-80.23%** |
| Wall range | 7.602--8.898 s | 1.505--1.713 s | non-overlapping |
| Median peak RSS | 327.07 MiB | 316.23 MiB | -3.31% |
| Master-order entries | 8192 | 1024 | 8x fewer |
| Serialized authority | 4,729,481 B | 591,058 B | **-87.50%** |

v2 stops after materializing 128, 256, 512, and 1024. Rungs 2048, 4096, and
8192 are explicitly recorded as intentionally unmaterialized.

## Exhaustive fallback

v2 materializes all configured rungs because only three qualify. The observed
fresh-process wall ranges overlap and are scheduler-sensitive. The recorded
three-sample medians are 11.003 s for v1 and 8.726 s for v2, but that apparent
median difference is not promoted as a portable performance claim.

# Interpretation

PERF-P2 removes exact work only after the Stage-A survivor set is already
fixed. The strong early-stop timing separation and large reduction in retained
authority size are therefore the relevant performance evidence. The fallback
case establishes that v2 remains scientifically exhaustive when the stop
predicate is not reached.

No GPU or MACE training timing is part of this gate.
