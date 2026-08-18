# MLFF architecture revision 44 - PERF-BASE0 implementation closure

This implementation revision executes the first gate of the frozen post-MH1 performance program. It does **not** change TARGET-DATA2B coverage mathematics, exact deterministic FPS semantics, scientific policy, target/replay membership, or the authoritative MACE-MH-1 / `omat_pbe` / e3nn backend decision. It freezes the evidence boundary required before Class E/S/A optimization work begins.

## Implemented authority

`mdstats.training_data.performance_baseline` introduces versioned, fail-closed records for:

- canonical little-endian C-order numerical-array fingerprints;
- exact JSON order/decision/report references;
- source-artifact and corpus identities;
- deterministic scientific-stage references;
- execution-only wall/process CPU, RSS, I/O, throughput, worker, thread-pool, cgroup, package, and host evidence;
- complete PERF-BASE0 records with separate scientific, execution, and whole-record digests; and
- old/new comparison that requires exact corpus/stage identity while reporting performance ratios separately.

Execution telemetry is structurally excluded from the scientific digest. Later releases may therefore change source version, timestamps, worker settings, wall time, RSS, and host identity while proving exact scientific equivalence.

## Frozen supplied-data baseline

The reproducible benchmark `benchmarks/benchmark_mlff_perf_base0.py` authenticates and processes:

- all 27 supplied LTA VASP XML sources: **37,633 frames**, **6,322,344 atoms**, and **966,777,484 extracted bytes**;
- all authoritative replay train/monitor/outlier splits: **12,000 frames** and **364,370 atoms**, while authenticating every supplied replay-package artifact;
- a compact deterministic exact-regression corpus; and
- adversarial duplicate-point, exact/near-tie, nonuniform-weight, missing-mask, and triclinic mixed-PBC cases.

The realistic exact-kernel reference freezes eight target/stress/cell/mobile/framework/species families totaling **263,398 family elements**, the frozen 1/128 leave-one-out mass rule, correlation-unit-balanced weights, robust scales, q01/q50/q99 extents, and exact local radii. It also freezes an explicitly bounded exact incremental FPS prefix of **K=1,024** over all **37,633** target frames, including nested 128/256/512/1,024 coverage reports. No target frame or radii reference is subsampled.

## Cloud CPU baseline

The measurement host is an Intel Xeon Platinum 8573C container with nine visible logical CPUs, an **8.0-core cgroup quota**, and a **4 GiB memory limit**. OpenBLAS and declared native worker pools were capped at eight threads.

First complete run:

- target XML ingestion: **131.846 s wall**, **134.664 s process CPU**, **285.431 frames/s**;
- replay ExtXYZ ingestion: **7.301 s wall**, **7.362 s process CPU**, **1,643.672 frames/s**;
- exact TARGET-DATA2B-style radii: **5.518 s wall**, **24.195 s process CPU**, **4.385 effective cores**, **47,732.798 family-elements/s**;
- exact K=1,024 FPS plus nested coverage: **6.019 s wall**, **40.434 s process CPU**, **6.718 effective cores**, **170.138 selections/s**; and
- measured process peak during the retained realistic stages: about **561 MiB**.

The scientific authority digest is `44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c`. The primary machine record is `audits/analysis/mlff_perf_base0_lta_cloud_cpu_reference.json`; its execution digest is `2c7614fea8dc60594e176e7c4fa17413922c56d67982e881a8fab0eebbc5b18c` and whole-record digest is `a8573580a906da95ff4e5af3154814bcba8b702174fe81437a1c22f1375da198`. The human report is `benchmarks/mlff_perf_base0_lta_cloud_cpu_2026-08-15.md`.

An independent complete same-host rerun is stored at `benchmarks/mlff_perf_base0_lta_cloud_cpu_repro_run2_2026-08-15.json`. It reproduced the scientific digest exactly while producing execution digest `0d3649ed0dfdb92e3daddb8a7d9a5361b591e0f1e1069156a602afb019fec564`. The authenticated comparison at `audits/analysis/mlff_perf_base0_reproducibility_comparison.json` has digest `c3d31a3922c89d19cc9a5670b9b4ca8f7ffaa65f82cffa8c16a25c0fb50d5e9e` and records `scientific_match=true`. Across the two runs, target ingestion spans 117.054--131.846 s, replay ingestion 7.301--8.455 s, exact radii 5.518--6.265 s, and exact FPS 6.019--9.600 s. These ranges are the initial execution-noise envelope for later matched-condition comparisons.

## Explicit bounded scope

No MACE-MH-1 checkpoint or GPU runtime was supplied. PERF-BASE0 therefore records, rather than fabricates, the absence of production DATA6 structural/foundation-residual families, DATA2C mandatory-quota/exhaustive-ladder authority, DATA6 model inference and GPU telemetry, complete DATA7 selection, DATA8 campaign-bundle materialization, TRAIN2, and EVAL2. The complete target/replay byte identities and all label/cell/species-derived CPU evidence remain authoritative for the implemented bounded scope.

`PERF-P0` is the next implementation gate. It may not change scientific authority unless its v1/v2 migration and exact execution paths compare successfully against this PERF-BASE0 oracle.
