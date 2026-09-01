---
title: "MLFF Architecture Revision 45"
subtitle: "PERF-P0 exact native TARGET-DATA2B closure"
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

Revision 45 closes bounded `PERF-P0`, the first implementation gate after the
`PERF-BASE0` oracle. It advances TARGET-DATA2B storage and exact execution only.
The coverage policy, target membership, FP64 authority, fixed-mass rule,
leave-one-out convention, tie behavior, and downstream scientific decisions are
unchanged.

The authoritative release is `mdstats 0.20.179a0`. `PERF-P1` is next.

# Implemented authority

## Native scientific arrays

TARGET-DATA2B family references now own canonical little-endian, C-contiguous,
read-only NumPy arrays:

```text
frame_indices : <i8 [N]
values        : <f8 [N,D]
weights       : <f8 [N]
scales        : <f8 [D]
local_radii   : <f8 [N]
```

Every array is authenticated by dtype, shape, byte count, and streamed SHA-256
of canonical native bytes. SHA-256 follows FIPS 180-4 [3].

## Native persistence

`mdstats.training_data.target_coverage_store` writes content-addressed NPY
shards with an authenticated manifest and campaign pointer. NPY was selected
because it preserves dtype and shape and supports memory mapping without
expanding arrays through Python scalar objects [1,2].

The store:

- deduplicates identical frame-index/weight profiles across families;
- writes through a temporary directory and atomically promotes the completed
  record;
- validates pointer, manifest, relative path, file size, file SHA-256, dtype,
  shape, and array-byte identity on read;
- restores large arrays through read-only mmap above a configured threshold;
  and
- excludes mmap paths, thresholds, query block sizes, worker counts, timing,
  and host observations from scientific identity.

Historical inline `mdstats.target-coverage-reference.v1` remains readable. It is
promoted to v2 only after exact elementwise comparison produces a passing
`TargetCoverageMigrationReport`.

# Exact execution realization

The scientific definition is retained while removing redundant work:

1. Correlation-unit-balanced frame weights are cached by exact domain,
   membership, unit, weighting, and leave-one-out identity.
2. Each scalar column is stably ordered once; all required weighted quantiles
   are derived from the same cumulative mass. Quantile conventions are stated
   explicitly because software packages do not share one universal definition
   [4].
3. Uniform weights use an exact fixed-rank neighbor dispatch. The historical
   cumulative-weight implementation remains the oracle for duplicates and
   ties.
4. Profile families expose columnar value/missing arrays rather than repeated
   Python tuple construction.
5. A bounded dense exact kernel is retained for qualification. SciPy `cKDTree`
   remains production authority; no approximate-neighbor path is introduced
   [5,6].

For a uniform valid population of size $N$, leave-one-out mass
$M_i = 1 - 1/N$, and target fraction $\beta$, the required neighbor rank is

$$
k = \left\lceil \beta (N-1) \right\rceil .
$$

This is an execution dispatch for the frozen cumulative-mass rule, not a new
coverage definition.

# Supplied-data qualification

The exact benchmark uses all 27 supplied target XML sources:

| Quantity | Authority |
|---|---:|
| Target frames | 37,633 |
| Target atoms | 6,322,344 |
| Coverage families | 8 |
| Family elements | 263,398 |
| Numerical arrays compared | 48 |

All 48 array identities match the PERF-BASE0 `target_data2b_exact_radii` stage.
All five historical-path and five PERF-P0 runs share scientific digest

`2f04aba96b876a10e62b7b0c22f26b544836005d11bc893177d4b29cbe4a3f82`.

## Exact construction

| Path | Median wall | Observed range | Median process CPU | Median peak RSS |
|---|---:|---:|---:|---:|
| Pre-P0 | 7.541 s | 6.826--9.926 s | 27.091 s | 329.47 MiB |
| PERF-P0 | 6.236 s | 5.818--8.253 s | 26.043 s | 328.50 MiB |

The matched median wall reduction is

$$
100\left(1-\frac{6.236470132}{7.541068095}\right)=17.30\%.
$$

The full observed range is retained because host scheduling noise is material.

## Persistence

\begin{center}
\small
\begin{tabular}{lrrrr}
\toprule
Representation & Write wall & Read wall & Bytes & Read RSS increment \\
\midrule
Nested JSON v1 & 10.366 s & 14.382 s & 42,749,676 & 189.35 MiB \\
Native NPY v2 & 0.184 s & 0.180 s & 17,912,666 & 28.02 MiB \\
\bottomrule
\end{tabular}
\end{center}

At complete supplied-data scale, native v2 is 56.22x faster to write, 79.70x
faster to read, and 58.10% smaller. Both restored references have content digest

`4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8`.

The migration report contains no difference paths and has digest

`bbe21f1c20beaefb7c837ec20330365853727366f07e4b8a795745aa048bfd88`.

# Evidence and limits

Normative and measured evidence is stored in:

- `docs/history/mlff/retired_specs/mlff_perf_p0_native_target_coverage_spec.{md,pdf}`;
- `audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.{json,md,pdf}`; and
- `release/MLFF_PERF_P0_QUALIFICATION_0.20.179a0.json`.

No authorizing MACE-MH-1 checkpoint, GPU runtime, or complete production campaign
bundle was supplied. This revision does not claim production DATA6
model-derived families, complete TARGET-DATA2C/DATA7 authority, DATA8
materialization, TRAIN2/EVAL2 timing, GPU memory, or OOM evidence.

`PERF-P1` must reuse exact FPS state and progressive coverage state across
TARGET-DATA2C and DATA7 while preserving the PERF-BASE0/P0 oracle.

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
