# mdstats 0.20.178a0 - PERF-BASE0

This release closes the first gate of the frozen post-MH1 optimization roadmap by establishing a numerical-equivalence and CPU-performance oracle before any further optimization is authorized.

## Implemented

- Added public PERF-BASE0 array, JSON, artifact, corpus, scientific-stage, execution-telemetry, record, and comparison authorities.
- Numerical arrays are fingerprinted as canonical little-endian C-order bytes with dtype, shape, byte count, non-finite counts, summary statistics, and SHA-256. Orders, decisions, and reports use authenticated canonical JSON.
- Scientific digests contain only corpus and scientific-stage authority. Wall/process time, RSS, I/O, temporary-array accounting, worker/thread-pool settings, cgroup/host identity, package versions, and accelerator observations are execution-only.
- Added atomic JSON persistence, fail-closed nested-digest validation, exact old/new comparison, and a stage-local wall/CPU/RSS/I/O meter.
- Added `benchmarks/benchmark_mlff_perf_base0.py` for reproducible supplied-data measurement and a Markdown companion report.

## Frozen corpora and exact kernels

- Complete target corpus: 27 VASP XML files, 37,633 frames, 6,322,344 atoms, 966,777,484 extracted bytes.
- Complete authoritative replay splits: 12,000 frames and 364,370 atoms; all supplied replay artifacts are byte-authenticated.
- Compact exact-regression corpus plus adversarial duplicate points, exact/near distance ties, nonuniform correlation-unit weights, missing-family masks, and triclinic mixed-periodicity geometry.
- Eight realistic exact TARGET-DATA2B-style family references totaling 263,398 elements, with frozen balanced weights, scales, q01/q50/q99 extents, and 1/128 leave-one-out local radii.
- Exact deterministic incremental FPS prefix K=1,024 over all 37,633 target frames with nested 128/256/512/1,024 coverage reports. The prefix bound is explicit; no reference-radii target frame is subsampled.

## Cloud CPU baseline

On the available Intel Xeon Platinum 8573C container (8-core CPU quota, 4 GiB cgroup memory, eight declared native threads):

- target XML ingestion: 131.846 s, 285.431 frames/s;
- replay ingestion: 7.301 s, 1,643.672 frames/s;
- exact local-radii stage: 5.518 s, 4.385 effective cores, 47,732.798 family-elements/s;
- exact K=1,024 FPS and nested coverage: 6.019 s, 6.718 effective cores, 170.138 selections/s; and
- retained-stage peak RSS: about 561 MiB.

Scientific digest: `44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c`.

## Bounded authority and compatibility

No MACE-MH-1 checkpoint or GPU was supplied. Production DATA6 model-derived families, DATA2C mandatory-quota/exhaustive-ladder authority, DATA6 GPU inference, complete DATA7, DATA8 campaign materialization, TRAIN2, and EVAL2 are explicitly unavailable in this record. No model result, GPU observation, or campaign decision is synthesized.

Historical records remain readable and no prior scientific policy changes. MACE-MH-1 / `omat_pbe` / e3nn remains the authoritative generated/reference backend. `PERF-P0` is the next gate.

## Qualification

- PERF-BASE0 record/serialization/comparison/meter unit tests pass.
- Existing focused TARGET-DATA2B, TARGET-DATA2C, MH1-CERT1, MH1-DATA6-1, and MPA-0 BASE0 regressions remain green subject to their expected unavailable-model skips.
- A full supplied-data run and independent same-host rerun produce the same scientific digest; timing differences remain execution-only evidence.
- Primary execution digest: `2c7614fea8dc60594e176e7c4fa17413922c56d67982e881a8fab0eebbc5b18c`; rerun execution digest: `0d3649ed0dfdb92e3daddb8a7d9a5361b591e0f1e1069156a602afb019fec564`; comparison digest: `c3d31a3922c89d19cc9a5670b9b4ca8f7ffaa65f82cffa8c16a25c0fb50d5e9e`.
- Same-host wall-time envelope: target XML 117.054--131.846 s, replay 7.301--8.455 s, exact radii 5.518--6.265 s, exact FPS/coverage 6.019--9.600 s.
