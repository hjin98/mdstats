---
title: "mdstats 0.20.179a0"
subtitle: "PERF-P0 exact native TARGET-DATA2B"
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

`mdstats 0.20.179a0` qualifies bounded `PERF-P0` for the complete supplied
TARGET-DATA2B workload. The release changes persistence and exact execution
realization only. Coverage mathematics, target membership, FP64 authority,
fixed reference mass, leave-one-out semantics, tie behavior, and downstream
scientific decisions remain unchanged.

# Implemented

- Canonical little-endian, C-contiguous, read-only `<i8` and `<f8` family arrays
  with streamed native-byte SHA-256 identities [3].
- Versioned `target-coverage-reference.v2` family/domain/reference records while
  preserving exact historical v1 readability.
- Content-addressed NPY shards, authenticated manifest and campaign pointer,
  shared frame-index/weight profiles, atomic promotion, and threshold-controlled
  read-only mmap restore [1,2].
- Fail-closed validation of pointer, manifest, relative path, file size, file
  SHA-256, dtype, shape, and canonical array identity.
- Exact v1-to-v2 migration reports. Campaign migration occurs only after
  elementwise equality is established.
- Shared correlation-unit-balanced weight profiles, one stable ordering per
  scalar column for all required weighted quantiles, exact uniform-weight
  fixed-rank radius dispatch, and columnar profile-family extraction. The
  weighted quantile convention remains explicit because quantile definitions
  are not universal [4].
- A bounded dense exact comparison kernel. SciPy `cKDTree` remains production
  authority; no approximate-neighbor path is introduced [5,6].

# Exact supplied-data qualification

| Quantity | Result |
|---|---:|
| Target XML sources | 27 |
| Target frames | 37,633 |
| Target atoms | 6,322,344 |
| Exact families | 8 |
| Family elements | 263,398 |
| Numerical arrays compared | 48 |

All 48 numerical-array identities match PERF-BASE0 exactly. Five isolated
pre-P0 and five PERF-P0 runs share scientific digest

`2f04aba96b876a10e62b7b0c22f26b544836005d11bc893177d4b29cbe4a3f82`.

| Path | Median wall | Range | Median process CPU | Median peak RSS |
|---|---:|---:|---:|---:|
| Pre-P0 exact construction | 7.541 s | 6.826--9.926 s | 27.091 s | 329.47 MiB |
| PERF-P0 exact construction | 6.236 s | 5.818--8.253 s | 26.043 s | 328.50 MiB |

Matched median construction wall time improves by **17.30%**. The observed
range is retained because host scheduling noise is material.

# Persistence qualification

| Representation | Write wall | Read wall | Bytes | Write RSS increment | Read RSS increment |
|---|---:|---:|---:|---:|---:|
| Nested JSON v1 | 10.366 s | 14.382 s | 42,749,676 | 167.77 MiB | 189.35 MiB |
| Native NPY v2 | 0.184 s | 0.180 s | 17,912,666 | 0.12 MiB | 28.02 MiB |

Native v2 is 56.22x faster to write, 79.70x faster to read, and 58.10% smaller.
Both restored references have content digest

`4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8`.

The exact migration report contains no difference paths and has digest

`bbe21f1c20beaefb7c837ec20330365853727366f07e4b8a795745aa048bfd88`.

# Compatibility and limits

Historical inline v1 records remain readable. New campaign writes use native v2.
Worker count, query block size, cache enablement, mmap path/threshold, timing,
and host observations remain execution-only and do not enter scientific digests.

No MACE-MH-1 checkpoint, authorizing GPU runtime, or complete production
campaign bundle was supplied. Production DATA6 model-derived families, complete
TARGET-DATA2C/DATA7 authority, DATA8 materialization, TRAIN2/EVAL2 timing, GPU
memory, and OOM evidence remain unavailable rather than inferred.

`PERF-P1` is next: shared exact FPS and progressive coverage state for
TARGET-DATA2C and DATA7.

# Evidence

- Normative specification:
  `docs/history/mlff/retired_specs/mlff_perf_p0_native_target_coverage_spec.{md,pdf}`.
- Architecture manual:
  `docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`.
- Matched CPU evidence:
  `audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.{json,md,pdf}`.
- Qualification manifest:
  `release/MLFF_PERF_P0_QUALIFICATION_0.20.179a0.json`.

# References

[1] R. Kern, "A Simple File Format for NumPy Arrays," NumPy Enhancement
Proposal 1, 2007. Available at:
[https://numpy.org/doc/1.13/neps/npy-format.html](https://numpy.org/doc/1.13/neps/npy-format.html)
(accessed 2026-08-15).

[2] NumPy developers, "numpy.load," NumPy reference documentation. Available
at:
[https://numpy.org/doc/stable/reference/generated/numpy.load.html](https://numpy.org/doc/stable/reference/generated/numpy.load.html)
(accessed 2026-08-15).

[3] National Institute of Standards and Technology, *Secure Hash Standard
(SHS)*, FIPS PUB 180-4, 2015. DOI:
[10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).

[4] R. J. Hyndman and Y. Fan, "Sample Quantiles in Statistical Packages,"
*The American Statistician* **50**(4), 361--365 (1996). DOI:
[10.1080/00031305.1996.10473566](https://doi.org/10.1080/00031305.1996.10473566).

[5] J. L. Bentley, "Multidimensional Binary Search Trees Used for Associative
Searching," *Communications of the ACM* **18**(9), 509--517 (1975). DOI:
[10.1145/361002.361007](https://doi.org/10.1145/361002.361007).

[6] SciPy developers, "scipy.spatial.cKDTree," SciPy reference documentation.
Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
(accessed 2026-08-15).
