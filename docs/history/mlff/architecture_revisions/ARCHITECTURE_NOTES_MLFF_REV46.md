---
title: "MLFF Architecture Revision 46"
subtitle: "PERF-P1 shared exact selection and linear-memory DATA7 closure"
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

Revision 46 closes bounded `PERF-P1`. TARGET-DATA2C and DATA7 now share one
exact deterministic FPS state, TARGET-DATA2C builds its fused matrix directly
into one preallocated FP64 array, nested TARGET-DATA2B coverage can advance one
family state across rungs, and DATA7 selected-neighbor coverage no longer keeps
a dense KxK persistent matrix.

The release is `mdstats 0.20.180a0`. `PERF-P2` is next.

# Scientific boundary

PERF-P1 is Authority Class E. Existing scientific schemas and digests do not
change. The release preserves:

- quota-selected prefixes;
- exact FPS order and lexical tie resolution;
- fused-selector bytes;
- TARGET-DATA2B family/rung statistics;
- Stage-A-relevant coverage reports; and
- DATA7 selected membership and nearest-other-selected coverage.

# Exact FPS state

`ExactFPSState` owns immutable selector geometry plus reusable execution state:
row norms, lexical UID rank, selected mask/rank, minimum squared distance, and
selected order. Appending $x_j$ updates candidates from

$$
\lVert x_i-x_j\rVert_2^2
=\lVert x_i\rVert_2^2+\lVert x_j\rVert_2^2-2x_i\cdot x_j.
$$

Quota selection initializes this state and exact FPS continues it directly.
Gonzalez's farthest-first traversal is the standard algorithmic antecedent [1],
but mdstats authority remains its frozen deterministic project order and tie
policy.

# Shared coverage state

`score_target_nested_subsets_coverage` processes one family across nested rungs,
updates nearest-selected reference distance only against newly added selected
points, and releases the family before moving to the next. Exact cKDTree queries
use the campaign CPU-budget worker count rather than a hard-coded serial setting
[2]. Existing one-dimensional Wasserstein statistics remain unchanged [3].

# DATA7 memory correction

The former incremental DATA7 path still retained a dense KxK selected-distance
matrix. Revision 46 replaces it with one FP64 minimum-squared-distance vector
of length K. Bounded old-new and new-new pair blocks update both endpoints, so
all exact pair distances needed for nearest-other-selected coverage remain
considered.

At K=8192, persistent state changes from

$$
8K^2=512\ \text{MiB}
$$

to

$$
8K=64\ \text{KiB}.
$$

# Qualification

The supplied-data oracle is the PERF-P0 native reference: 37,633 frames, eight
coverage families, and a 37,633x50 fused selector matrix. Full selector bytes,
FPS order through K=1024, and coverage-report digests at 128/256/512/1024 are
exactly unchanged.

| Benchmark | Legacy | PERF-P1 | Result |
|---|---:|---:|---:|
| Full-reference FPS K=1024 | 1.550 s | 0.657 s | **57.61% faster** |
| Wide FPS 4000x128, K=512 | 0.182 s | 0.049 s | **73.25% faster** |
| DATA7 K=8192 wall | 1.954 s | 0.506 s | **74.09% faster** |
| DATA7 K=8192 peak RSS | 1149.89 MiB | 637.22 MiB | **44.58% lower** |
| DATA7 persistent state | 512 MiB | 64 KiB | **8192x smaller** |

Four-rung progressive coverage is exact but its median wall time is 10.29%
slower on this host. This is recorded as a PERF-P2+ optimization opportunity,
not represented as a speedup.

# Evidence and next gate

Normative/evidence surfaces are:

- `docs/history/mlff/retired_specs/mlff_perf_p1_shared_exact_selection_spec.{md,pdf}`;
- `audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.{json,md,pdf}`;
- `release/MLFF_PERF_P1_QUALIFICATION_0.20.180a0.json`; and
- canonical architecture revision 46.

`PERF-P2` may change TARGET-DATA2C ladder authority to progressive/lazy
materialization only under its separate Authority Class A contract. PERF-P1's
exact workspace and frozen scientific oracle are its execution baseline.

# References

[1] T. F. Gonzalez, "Clustering to Minimize the Maximum Intercluster
Distance," *Theoretical Computer Science* **38**, 293--306 (1985). DOI:
[10.1016/0304-3975(85)90224-5](https://doi.org/10.1016/0304-3975(85)90224-5).

[2] SciPy developers, "scipy.spatial.cKDTree.query," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html)
(accessed 2026-08-15).

[3] SciPy developers, "scipy.stats.wasserstein_distance," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html)
(accessed 2026-08-15).
