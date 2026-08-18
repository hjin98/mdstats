---
title: "MLFF PERF-P0 Matched CPU Qualification"
subtitle: "Complete supplied LTA TARGET-DATA2B workload"
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
  - |-
    \usepackage{needspace}
---

# Decision

`PERF-P0` passes as bounded supplied-data TARGET-DATA2B authority.

- Source release: `mdstats 0.20.179a0`
- Target sources: **27**
- Target frames: **37,633**
- Target atoms: **6,322,344**
- Coverage families: **8**
- Family elements: **263,398**
- PERF-BASE0 numerical-array agreement: **exact, 48/48 arrays**
- Historical/P0 scientific-digest agreement: **exact**

This report is a human-readable projection of
`mlff_perf_p0_lta_cloud_cpu_2026-08-15.json`. The JSON record is authoritative.

# Measurement design

The complete supplied target corpus was ingested and cached once. Historical and
PERF-P0 family construction then ran in isolated matched processes over the same
in-memory scientific arrays. Each path has five retained runs.

The comparison separates:

1. scientific identity: array bytes, family content, and scientific digest; and
2. execution evidence: wall/process CPU time, RSS, worker/thread settings, and
   host state.

Execution evidence is excluded from the scientific digest. No favorable
single-run timing is promoted as authority.

# Scientific equivalence

Every historical/P0 run has scientific digest

`2f04aba96b876a10e62b7b0c22f26b544836005d11bc893177d4b29cbe4a3f82`.

All 48 numerical arrays match the PERF-BASE0 `target_data2b_exact_radii` stage
byte-for-byte. These arrays cover frame indices, values, balanced weights,
robust scales, exact local radii, and q01/q50/q99 extent statistics.

\Needspace{5\baselineskip}
The PERF-P0 benchmark scientific digest is

`ab5e57750a06a3895d6349846238073a7bdca40a1c5270409999bfd6507a1d05`.

\Needspace{5\baselineskip}
Execution digest:

`4265881375205beb954222ac8d0b1372221c4779dcbc5567e9ff3a64d82681a1`.

\Needspace{5\baselineskip}
Whole-record digest:

`cd9240e5c4936e1ac22409df8d56b06f487debd78f150bc3a45f7423d0917db0`.

# Exact family construction

| Path | Median wall | Observed range | Median process CPU | Median peak RSS |
|---|---:|---:|---:|---:|
| Pre-P0 exact path | 7.541 s | 6.826--9.926 s | 27.091 s | 329.47 MiB |
| PERF-P0 exact path | 6.236 s | 5.818--8.253 s | 26.043 s | 328.50 MiB |

The matched median wall improvement is

$$
I_{wall}=100\left(1-\frac{t_{P0}}{t_{pre}}\right)
=100\left(1-\frac{6.236470132}{7.541068095}\right)
=17.30\%.
$$

The overlapping ranges show that operating-system scheduling and page-cache
state remain material. The median result is therefore interpreted with the full
five-run envelope, not as a deterministic speed ratio.

# Persistence

The full reference was serialized and restored through both representations in
isolated processes.

| Representation | Write wall | Read wall | Bytes | Write RSS increment | Read RSS increment |
|---|---:|---:|---:|---:|---:|
| Nested JSON v1 | 10.366 s | 14.382 s | 42,749,676 | 167.77 MiB | 189.35 MiB |
| Native NPY v2 | 0.184 s | 0.180 s | 17,912,666 | 0.12 MiB | 28.02 MiB |

Derived effects:

| Effect | Result |
|---|---:|
| Write speed ratio | 56.22x |
| Read speed ratio | 79.70x |
| Serialized-size reduction | 58.10% |
| Read RSS-increment reduction | 85.20% |

Both restored references have content digest

`4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8`.

The exact v1/v2 migration report has no difference paths and digest

`bbe21f1c20beaefb7c837ec20330365853727366f07e4b8a795745aa048bfd88`.

# Host boundary

The available cloud machine exposes an Intel Xeon Platinum 8573C, nine visible
logical CPUs, an 8-core cgroup CPU quota, and a 4 GiB cgroup memory limit.
Declared native thread pools were capped at eight threads. Python was 3.13.5;
NumPy 2.3.5; SciPy 1.17.0; ASE 3.29.0.

These host and package observations are execution evidence. They do not enter
TARGET-DATA2B scientific identity.

# Limits

- The benchmark covers complete supplied-data label, cell, mobile/framework, and
  species-force families. Production DATA6 model-derived families require the
  authorizing checkpoint and complete campaign bundle and were not fabricated.
- Family construction is isolated from XML ingestion so historical and P0 paths
  receive identical arrays.
- The native read is authenticated and uses read-only mmap at the benchmark
  threshold.
- This gate does not qualify complete TARGET-DATA2C/DATA7 selection, DATA8,
  TRAIN2/EVAL2, GPU memory, utilization, OOM, or backoff evidence.

The normative method, invariants, and migration contract are defined in the
PERF-P0 native target-coverage specification. `PERF-P1` is next.
