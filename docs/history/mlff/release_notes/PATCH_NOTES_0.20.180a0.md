---
title: "mdstats 0.20.180a0"
subtitle: "PERF-P1 shared exact selection and progressive coverage"
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

# Release decision

`mdstats 0.20.180a0` qualifies bounded `PERF-P1`. The release consolidates exact
selection/coverage execution and removes quadratic persistent DATA7 neighbor
state without changing scientific content. `PERF-P2` is next.

# Implemented

- Add `ExactFPSState` with reusable row norms, selected state, lexical UID rank,
  minimum squared distances, and exact continuation.
- Hand the TARGET-DATA2C quota state directly into FPS continuation.
- Bound centroid novelty temporaries while preserving the historical
  subtraction/reduction numerical path.
- Preallocate the fused TARGET-DATA2C FP64 selector matrix and fill family
  column slices directly.
- Add progressive nested TARGET-DATA2B coverage scoring with one family loaded
  and scaled at a time.
- Route cKDTree query workers through the campaign coverage CPU-budget resolver
  [2].
- Replace DATA7's persistent dense KxK selected-distance matrix with one O(K)
  nearest-neighbor-minimum vector plus bounded exact pair blocks.
- Add independent legacy-oracle tests and matched CPU/memory benchmark evidence.

# Exactness

The complete PERF-P0 native reference contains 37,633 target frames and eight
coverage families. PERF-P1 preserves:

- the full 37,633x50 selector matrix byte-for-byte;
- exact FPS order through K=1024;
- all coverage report digests at 128/256/512/1024;
- worker-count invariant coverage digests; and
- regression TARGET-DATA2C and DATA7 content digests.

Scientific benchmark digest:

`ff08ca4aee884f1aaf4bf1969454bb75fc9e875eb8c29d57c46fe0100dadb12e`.

# CPU and memory evidence

| Case | Legacy | PERF-P1 | Result |
|---|---:|---:|---:|
| Full-reference FPS K=1024 | 1.550 s | 0.657 s | **57.61% faster** |
| Wide FPS 4000x128, K=512 | 0.182 s | 0.049 s | **73.25% faster** |
| DATA7 K=8192 wall | 1.954 s | 0.506 s | **74.09% faster** |
| DATA7 K=8192 peak RSS | 1149.89 MiB | 637.22 MiB | **44.58% lower** |
| DATA7 persistent state | 512 MiB | 64 KiB | **8192x smaller** |

The progressive four-rung coverage path is exact but measures 0.709 s versus
0.643 s for repeated legacy scoring on this host, a 10.29% slowdown. No
coverage-speed claim is made.

# Compatibility and limits

PERF-P1 is execution-only Authority Class E. No existing scientific schema is
versioned, and existing content digests remain authoritative. Approximate FPS,
approximate neighbor queries, altered tie tolerance, altered coverage policy,
and changed Stage-A semantics remain forbidden.

No authorizing MACE-MH-1 checkpoint or GPU runtime was supplied. This release
makes no TRAIN2/EVAL2, GPU utilization, GPU memory, OOM, or complete production
campaign performance claim.

# Evidence

- Specification: `docs/specs/training_data/mlff_perf_p1_shared_exact_selection_spec.{md,pdf}`.
- Architecture: `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`.
- Revision note: `ARCHITECTURE_NOTES_MLFF_REV46.{md,pdf}`.
- CPU evidence: `audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.{json,md,pdf}`.
- Qualification: `release/MLFF_PERF_P1_QUALIFICATION_0.20.180a0.json`.

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
